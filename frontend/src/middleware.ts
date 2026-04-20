import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/onboarding", "/fonts-preview"];

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// Prefix used in cookie names so parallel stacks (prod/freemium) on the same
// hostname don't collide — HTTP cookies do not scope by port (RFC 6265).
const COOKIE_PREFIX = process.env.NEXT_PUBLIC_AUTH_COOKIE_PREFIX ?? "";
const ACCESS_COOKIE = COOKIE_PREFIX + "access_token";
const REFRESH_COOKIE = COOKIE_PREFIX + "refresh_token";

async function tryRefresh(request: NextRequest): Promise<NextResponse | null> {
  const refreshCookie = request.cookies.get(REFRESH_COOKIE);
  if (!refreshCookie) return null;

  try {
    const refreshRes = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
      method: "POST",
      headers: {
        cookie: `${REFRESH_COOKIE}=${refreshCookie.value}`,
      },
    });

    if (!refreshRes.ok) return null;

    const response = NextResponse.next();
    const setCookies = refreshRes.headers.getSetCookie?.() ?? [];
    for (const cookie of setCookies) {
      response.headers.append("set-cookie", cookie);
    }
    return response;
  } catch {
    return null;
  }
}

function noStore(response: NextResponse): NextResponse {
  response.headers.set("Cache-Control", "no-store, must-revalidate");
  return response;
}

/** Detect any non-navigation HTTP request (RSC prefetch, fetch(), XHR).
 *
 * Telegram's WebKit WebView (Safari) rejects HTML redirects from `fetch()`
 * with "Fetch API cannot load … due to access control checks" because the
 * redirected response (our /login HTML) has no CORS headers and a different
 * Content-Type than the requester expected.
 *
 * The most reliable indicator across browsers is `Sec-Fetch-Dest`:
 *   - "document"   → real top-level navigation (handle with 307 redirect)
 *   - "empty"      → fetch() / XHR / RSC prefetch (handle with 204)
 *   - "iframe"/"image"/etc. → also not a doc navigation
 *
 * We fall back to legacy signals (RSC header, _rsc query, Accept header) for
 * robustness across Next.js versions. */
function isNonNavigationRequest(request: NextRequest): boolean {
  const dest = request.headers.get("sec-fetch-dest");
  if (dest && dest !== "document") return true;

  const mode = request.headers.get("sec-fetch-mode");
  if (mode === "cors" || mode === "no-cors") return true;

  if (request.headers.get("rsc") === "1") return true;
  if (request.headers.get("next-router-prefetch") === "1") return true;
  if (request.headers.get("next-router-state-tree") !== null) return true;
  if (request.headers.get("accept")?.includes("text/x-component")) return true;
  if (request.nextUrl.searchParams.has("_rsc")) return true;

  return false;
}

function clearAuthCookiesAndRedirect(request: NextRequest, to = "/login"): NextResponse {
  const url = new URL(to, request.url);
  if (to === "/login" && request.nextUrl.pathname !== "/") {
    url.searchParams.set("next", request.nextUrl.pathname);
  }
  const response = NextResponse.redirect(url);
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  // Legacy unprefixed cookies potentially leaking from the prod stack on the
  // same hostname — wipe them too so the freemium session starts clean.
  if (COOKIE_PREFIX) {
    response.cookies.delete("access_token");
    response.cookies.delete("refresh_token");
  }
  return response;
}

function emptyNoContent(request: NextRequest): NextResponse {
  const origin = request.headers.get("origin") ?? request.nextUrl.origin;
  return new NextResponse(null, {
    status: 204,
    headers: {
      "cache-control": "no-store",
      "access-control-allow-origin": origin,
      "access-control-allow-credentials": "true",
      "vary": "Origin, RSC, Next-Router-Prefetch, Sec-Fetch-Dest, Accept",
    },
  });
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/fonts/") ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml"
  ) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE);
  const refreshToken = request.cookies.get(REFRESH_COOKIE);
  // If the *prefixed* cookies are missing but we still see unprefixed cookies
  // (prod stack leaked them onto the same host), they are guaranteed invalid
  // here (different JWT_SECRET). Treat the user as unauthenticated.
  const hasStaleUnprefixed =
    COOKIE_PREFIX !== "" &&
    !accessToken &&
    !refreshToken &&
    (request.cookies.has("access_token") || request.cookies.has("refresh_token"));

  const nonNavigation = isNonNavigationRequest(request);

  if (pathname === "/login" && accessToken) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (pathname === "/login" && !accessToken && refreshToken) {
    const refreshed = await tryRefresh(request);
    if (refreshed) {
      const redirect = NextResponse.redirect(new URL("/dashboard", request.url));
      refreshed.headers.forEach((value, key) => {
        if (key.toLowerCase() === "set-cookie") {
          redirect.headers.append("set-cookie", value);
        }
      });
      return redirect;
    }
  }

  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    // On the login page, proactively scrub stale unprefixed cookies so the
    // browser stops sending them to /api/* (which would keep returning 401).
    if (hasStaleUnprefixed) {
      const response = NextResponse.next();
      response.cookies.delete("access_token");
      response.cookies.delete("refresh_token");
      return response;
    }
    return NextResponse.next();
  }

  if (!accessToken) {
    if (refreshToken) {
      const refreshed = await tryRefresh(request);
      if (refreshed) return noStore(refreshed);
      // refresh_token exists but backend says it's invalid — wipe both cookies
      // so we don't re-attempt on every navigation.
      if (nonNavigation) return emptyNoContent(request);
      return clearAuthCookiesAndRedirect(request);
    }

    if (nonNavigation) return emptyNoContent(request);

    if (hasStaleUnprefixed) return clearAuthCookiesAndRedirect(request);

    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return noStore(NextResponse.next());
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|uploads).*)"],
};
