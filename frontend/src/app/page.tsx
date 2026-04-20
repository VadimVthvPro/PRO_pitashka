import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const COOKIE_PREFIX = process.env.NEXT_PUBLIC_AUTH_COOKIE_PREFIX ?? "";
const ACCESS_COOKIE = COOKIE_PREFIX + "access_token";

export default async function Home() {
  const cookieStore = await cookies();
  const hasToken = cookieStore.has(ACCESS_COOKIE);
  redirect(hasToken ? "/dashboard" : "/login");
}
