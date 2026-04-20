import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/onboarding", "/fonts-preview"];

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function tryRefresh(request: NextRequest): Promise<NextResponse | null> {
  const refreshCookie = request.cookies.get("refresh_token");
  if (!refreshCookie) return null;

  try {
    const refreshRes = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
      method: "POST",
      headers: {
        cookie: `refresh_token=${refreshCookie.value}`,
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
  // Authenticated pages must never end up in any shared/edge cache, otherwise
  // a logged-out visitor can briefly see a previous user's prerendered HTML
  // before the client-side guard kicks in.
  response.headers.set("Cache-Control", "no-store, must-revalidate");
  return response;
}

/** Detect React Server Component prefetch / payload requests.
 * These are issued via `fetch()` and CANNOT follow HTML redirects safely
 * (Safari & Telegram WebView reject the cross-document load with
 * "access control checks"). For these we must return a plain 401
 * so Next.js can fall back to a hard navigation cleanly. */
function isRscRequest(request: NextRequest): boolean {
  if (request.headers.get("RSC") === "1") return true;
  if (request.headers.get("Next-Router-Prefetch") === "1") return true;
  if (request.nextUrl.searchParams.has("_rsc")) return true;
  return false;
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

  const accessToken = request.cookies.get("access_token");
  const refreshToken = request.cookies.get("refresh_token");
  const rscLikely =
    request.headers.get("rsc") === "1" ||
    request.headers.get("next-router-prefetch") === "1" ||
    request.headers.get("next-router-state-tree") !== null ||
    request.headers.get("accept")?.includes("text/x-component") === true ||
    request.nextUrl.searchParams.has("_rsc");

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
    return NextResponse.next();
  }

  if (!accessToken) {
    if (refreshToken) {
      const refreshed = await tryRefresh(request);
      if (refreshed) return noStore(refreshed);
    }
    // RSC prefetch / payload cannot follow an HTML 307 — Telegram's WebKit
    // WebView raises "Fetch API cannot load … due to access control checks".
    // Return an empty 204 with permissive CORS so the router silently aborts
    // the prefetch; the next real navigation takes the HTML redirect branch.
    if (rscLikely || isRscRequest(request)) {
      const origin = request.headers.get("origin") ?? request.nextUrl.origin;
      return new NextResponse(null, {
        status: 204,
        headers: {
          "cache-control": "no-store",
          "access-control-allow-origin": origin,
          "access-control-allow-credentials": "true",
          "vary": "Origin, RSC, Next-Router-Prefetch, Accept",
        },
      });
    }
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return noStore(NextResponse.next());
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|uploads).*)"],
};
