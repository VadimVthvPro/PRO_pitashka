"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";

// --------------------------------------------------------------------------
// Типы
// --------------------------------------------------------------------------

export type Tier = "free" | "premium" | "pro";
export type QuotaPeriod = "d" | "m" | "static";

export interface UsageItem {
  key: string;
  limit: number;        // -1 = безлимит
  period: QuotaPeriod;
  used: number;
  allowed: boolean;
  reset_at: string | null;
}

export interface BillingMe {
  tier: Tier;
  plan_key: string;
  plan_name: string;
  status: string;
  source: string | null;
  end_at: string | null;
  features: string[];
  usage: UsageItem[];
  auto_renew: boolean;
}

export interface BillingPlan {
  plan_key: string;
  name: string;
  tier: Tier;
  duration_days: number | null;
  price_stars: number;
  price_usd_cents: number | null;
  limits: Record<string, { limit: number; period: QuotaPeriod }>;
  features: string[];
}

export interface StarsInvoice {
  plan_key: string;
  plan_name: string;
  stars_amount: number;
  invoice_url: string;
  invoice_payload: string;
  bot_username: string | null;
}

export interface BillingPayment {
  id: number;
  plan_key: string;
  stars_amount: number;
  status: "pending" | "paid" | "refunded" | "failed";
  created_at: string;
  paid_at: string | null;
  refunded_at: string | null;
}

export interface PaywallPayload {
  code: "quota_exceeded" | "require_tier" | string;
  message: string;
  plan_key?: string;
  tier?: Tier;
  quota_key?: string;
  limit?: number;
  used?: number;
  reset_at?: string | null;
  required_tier?: Tier;
  upgrade?: {
    suggested_plan_key?: string;
    billing_url?: string;
  };
}

// --------------------------------------------------------------------------
// API helpers
// --------------------------------------------------------------------------

export const billingApi = {
  me: () => api<BillingMe>("/api/billing/me"),
  plans: () => api<BillingPlan[]>("/api/billing/plans"),
  history: () => api<{ payments: BillingPayment[] }>("/api/billing/history"),
  createInvoice: (plan_key: string) =>
    api<StarsInvoice>("/api/billing/stars/invoice", {
      method: "POST",
      body: JSON.stringify({ plan_key }),
    }),
  cancel: () => api<{ ok: true }>("/api/billing/cancel", { method: "POST" }),
};

// --------------------------------------------------------------------------
// Хук: текущий тир + usage. Поллит раз в 30 сек + ручной refetch.
// --------------------------------------------------------------------------

export function useBilling(pollMs = 30_000) {
  const [me, setMe] = useState<BillingMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setError(null);
      const data = await billingApi.me();
      setMe(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    refetch();
    if (pollMs > 0) {
      const id = setInterval(() => {
        if (!alive) return;
        refetch();
      }, pollMs);
      return () => {
        alive = false;
        clearInterval(id);
      };
    }
    return () => {
      alive = false;
    };
  }, [pollMs, refetch]);

  return { me, loading, error, refetch };
}

// --------------------------------------------------------------------------
// Глобальный paywall-event: бросаем из api.ts, слушаем в <UpgradeProvider/>
// --------------------------------------------------------------------------

export const PAYWALL_EVENT = "billing:paywall";

export function emitPaywall(detail: PaywallPayload) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(PAYWALL_EVENT, { detail }));
}

export function onPaywall(listener: (detail: PaywallPayload) => void) {
  if (typeof window === "undefined") return () => undefined;
  const handler = (e: Event) => {
    const ce = e as CustomEvent<PaywallPayload>;
    if (ce.detail) listener(ce.detail);
  };
  window.addEventListener(PAYWALL_EVENT, handler);
  return () => window.removeEventListener(PAYWALL_EVENT, handler);
}

// --------------------------------------------------------------------------
// Утилиты форматирования
// --------------------------------------------------------------------------

const QUOTA_LABEL_RU: Record<string, string> = {
  ai_chat_msg: "AI-сообщений",
  ai_photo: "Фото-анализов",
  ai_meal_plan: "Планов питания",
  ai_workout_plan: "Планов тренировок",
  ai_recipe: "AI-рецептов",
  ai_digest: "AI-дайджестов",
  food_manual: "Записей о еде",
  social_post_photo: "Фото-постов",
  history_days: "Дней истории",
};

export function quotaLabel(key: string): string {
  return QUOTA_LABEL_RU[key] ?? key;
}

export function quotaPeriodLabel(period: QuotaPeriod): string {
  if (period === "d") return "сегодня";
  if (period === "m") return "в этом месяце";
  return "";
}

export function formatStars(amount: number): string {
  return `${amount.toLocaleString("ru-RU")} ⭐`;
}
