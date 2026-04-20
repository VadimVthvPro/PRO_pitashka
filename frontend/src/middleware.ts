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

/** Detect any non-HTML-navigation request — RSC prefetch, fetch() from client
 * components, XHR. Next.js 16 edge-runtime strips internal RSC headers (`RSC`,
 * `Next-Router-*`) and the `_rsc=` query before middleware sees them, so the
 * only reliable signal left is the `Accept` header: real browser navigation
 * always includes `text/html`, while every fetch()-style call does not. */
function isNonNavFetch(request: NextRequest): boolean {
  const accept = (request.headers.get("accept") || "").toLowerCase();
  if (!accept) return false; // be conservative if header absent
  return !accept.includes("text/html");
}

/** Return a valid, empty RSC payload with reflected CORS. This replaces the
 * previous 307 → /login response for unauthed prefetches, which Telegram's
 * WebKit WebView rejected with "Fetch API cannot load … due to access control
 * checks" (Safari refuses to follow a cross-document HTML redirect issued from
 * a `fetch()` inside a WebApp frame).
 *
 * Why `200` + empty `text/x-component` body: it looks like a successful RSC
 * response with zero nodes, so the Next.js client router just no-ops the
 * prefetch. The real HTML navigation (initiated by the user clicking the
 * link) still takes the `307 → /login` branch below. */
function emptyRscPayload(request: NextRequest): NextResponse {
  const origin = request.headers.get("origin");
  const headers: Record<string, string> = {
    "content-type": "text/x-component; charset=utf-8",
    "cache-control": "no-store",
    "vary": "Origin, Accept",
  };
  if (origin) {
    headers["access-control-allow-origin"] = origin;
    headers["access-control-allow-credentials"] = "true";
  } else {
    // Same-origin request with no Origin header — wildcard is fine and
    // avoids WebKit credential-with-wildcard rejections.
    headers["access-control-allow-origin"] = "*";
  }
  return new NextResponse("", { status: 200, headers });
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
    if (isNonNavFetch(request)) {
      return emptyRscPayload(request);
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
