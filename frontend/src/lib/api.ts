const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const PAYWALL_EVENT = "billing:paywall";

interface PaywallDetail {
  code: string;
  message: string;
  [key: string]: unknown;
}

/** Backend отдает 402 при исчерпании квоты или требовании тира. Если
 *  `detail` — JSON с `code: 'quota_exceeded' | 'require_tier'`, мы
 *  диспатчим глобальное событие — модалка-апгрейд (в app layout) его поймает.
 *  В то же время пробрасываем ошибку выше, чтобы вызов в UI знал о провале. */
function maybeEmitPaywall(res: Response, parsed: unknown): void {
  if (res.status !== 402 || typeof window === "undefined") return;
  if (!parsed || typeof parsed !== "object") return;
  const obj = parsed as { detail?: unknown };
  const detail = obj.detail;
  if (!detail || typeof detail !== "object") return;
  const d = detail as PaywallDetail;
  if (d.code === "quota_exceeded" || d.code === "require_tier") {
    window.dispatchEvent(new CustomEvent(PAYWALL_EVENT, { detail: d }));
  }
}

function errorMessage(res: Response, bodyText: string): string {
  try {
    const j = JSON.parse(bodyText) as { detail?: unknown; error?: unknown };
    maybeEmitPaywall(res, j);
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((x: { msg?: string }) => x.msg)
        .filter(Boolean)
        .join(", ") || "Ошибка валидации";
    }
    if (j.detail && typeof j.detail === "object") {
      const d = j.detail as { message?: string; code?: string };
      if (d.message) return d.message;
      if (d.code) return d.code;
    }
    if (j.error != null) return String(j.error);
  } catch {
    /* ignore */
  }
  if (bodyText) return bodyText.slice(0, 400);
  return res.statusText || `Ошибка ${res.status}`;
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const doFetch = () => fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers,
  });

  let res = await doFetch();

  if (res.status === 401 && !path.includes("/auth/")) {
    const ok = await tryRefresh();
    if (ok) {
      res = await doFetch();
    } else {
      redirectToLogin();
      throw new Error("Session expired");
    }
  }

  const text = await res.text();
  if (!res.ok) {
    throw new Error(errorMessage(res, text));
  }
  if (res.status === 204 || !text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const here = window.location.pathname + window.location.search;
  // Avoid loops if we're already on /login (e.g. expired session on the login page).
  if (window.location.pathname.startsWith("/login")) return;
  const target = `/login?next=${encodeURIComponent(here)}`;
  window.location.href = target;
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  init?: Omit<RequestInit, "body">,
): Promise<T> {
  const doFetch = () => fetch(`${API_BASE}${path}`, {
    ...init,
    method: init?.method ?? "POST",
    credentials: "include",
    body: formData,
  });

  let res = await doFetch();

  if (res.status === 401) {
    const ok = await tryRefresh();
    if (ok) {
      res = await doFetch();
    } else {
      redirectToLogin();
      throw new Error("Session expired");
    }
  }

  const text = await res.text();
  if (!res.ok) {
    throw new Error(errorMessage(res, text));
  }
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}
