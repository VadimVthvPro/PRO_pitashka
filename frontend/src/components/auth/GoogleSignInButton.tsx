"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

declare global {
  interface Window {
    google?: any;
  }
}

interface Props {
  onSuccess: (res: { needs_onboarding?: boolean }) => void;
  onError?: (msg: string) => void;
  /** "login" — sign-in flow; "link" — attach to current account */
  mode?: "login" | "link";
}

const GIS_SRC = "https://accounts.google.com/gsi/client";

function loadGis(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("GIS load failed")));
      return;
    }
    const s = document.createElement("script");
    s.src = GIS_SRC;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("GIS load failed"));
    document.head.appendChild(s);
  });
}

export function GoogleSignInButton({ onSuccess, onError, mode = "login" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [clientId, setClientId] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api<{ enabled: boolean; client_id: string }>("/api/auth/google/config")
      .then((cfg) => {
        if (cancelled) return;
        setEnabled(cfg.enabled);
        setClientId(cfg.client_id || "");
      })
      .catch(() => !cancelled && setEnabled(false));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!enabled || !clientId || !ref.current) return;
    let cancelled = false;
    (async () => {
      try {
        await loadGis();
        if (cancelled || !window.google?.accounts?.id || !ref.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (resp: { credential: string }) => {
            try {
              const endpoint = mode === "link" ? "/api/auth/google/link" : "/api/auth/google/login";
              const out = await api<{ needs_onboarding?: boolean }>(endpoint, {
                method: "POST",
                body: JSON.stringify({ credential: resp.credential }),
              });
              onSuccess(out);
            } catch (e) {
              onError?.(e instanceof Error ? e.message : "Google sign-in failed");
            }
          },
        });
        window.google.accounts.id.renderButton(ref.current, {
          theme: "outline",
          size: "large",
          shape: "rectangular",
          text: mode === "link" ? "continue_with" : "signin_with",
          width: ref.current.offsetWidth || 320,
        });
      } catch (e) {
        onError?.(e instanceof Error ? e.message : "Google init failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled, clientId, mode, onSuccess, onError]);

  if (enabled === false) return null;
  return <div ref={ref} className="w-full min-h-[40px]" />;
}
