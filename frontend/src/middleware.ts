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
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return noStore(NextResponse.next());
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|uploads).*)"],
};
