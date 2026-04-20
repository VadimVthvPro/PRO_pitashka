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
    // RSC prefetch can't follow an HTML redirect — return 401 so the client
    // router silently aborts the prefetch. The next real navigation will
    // hit the redirect path below and land on /login cleanly.
    if (isRscRequest(request)) {
      return new NextResponse(null, {
        status: 401,
        headers: { "Cache-Control": "no-store" },
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
