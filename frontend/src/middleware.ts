import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/onboarding", "/fonts-preview"];

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function tryRefresh(request: NextRequest): Promise<NextResponse | null> {
  const refreshCookie = request.cookies.get("refresh_token");
  if (!refreshCookie) return null;

  try {
    // Backend refresh-endpoint expects the refresh cookie. Forward it.
    const refreshRes = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
      method: "POST",
      headers: {
        cookie: `refresh_token=${refreshCookie.value}`,
      },
      // Cannot use credentials in edge runtime; cookie is forwarded via header.
    });

    if (!refreshRes.ok) return null;

    // Forward all Set-Cookie headers from backend to client.
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

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow Next internals, API routes, static & public pages
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

  // Already logged in and trying to visit /login → send to dashboard
  if (pathname === "/login" && accessToken) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // On /login without access but with refresh — silently re-auth and redirect.
  if (pathname === "/login" && !accessToken && refreshToken) {
    const refreshed = await tryRefresh(request);
    if (refreshed) {
      // Re-issue as redirect to dashboard, keep Set-Cookie
      const redirect = NextResponse.redirect(new URL("/dashboard", request.url));
      refreshed.headers.forEach((value, key) => {
        if (key.toLowerCase() === "set-cookie") {
          redirect.headers.append("set-cookie", value);
        }
      });
      return redirect;
    }
  }

  // Public paths — allow through
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }

  // Protected paths
  if (!accessToken) {
    if (refreshToken) {
      // Try silent refresh — if succeeds, continue with new cookies set
      const refreshed = await tryRefresh(request);
      if (refreshed) return refreshed;
    }
    const loginUrl = new URL("/login", request.url);
    // Remember where to return after login
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
