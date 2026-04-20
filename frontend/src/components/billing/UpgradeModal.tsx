"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@iconify/react";
import { AnimatePresence, motion } from "motion/react";

import {
  billingApi,
  formatStars,
  onPaywall,
  quotaLabel,
  quotaPeriodLabel,
  type BillingPlan,
  type PaywallPayload,
  type QuotaPeriod,
} from "@/lib/billing";

interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
  suggestedPlanKey?: string;
  context?: PaywallPayload | null;
}

function _reasonLine(p: PaywallPayload | null | undefined): string | null {
  if (!p) return null;
  if (p.code === "quota_exceeded" && p.quota_key) {
    const label = quotaLabel(p.quota_key);
    const period = quotaPeriodLabel((p as unknown as { period?: QuotaPeriod }).period ?? "d");
    const used = p.used ?? 0;
    const limit = p.limit ?? 0;
    return `${label} ${period}: ${used}/${limit} — лимит исчерпан.`;
  }
  if (p.code === "require_tier" && p.required_tier) {
    return `Эта функция доступна на тарифе ${p.required_tier}.`;
  }
  return p.message ?? null;
}

export function UpgradeModal({ open, onClose, suggestedPlanKey, context }: UpgradeModalProps) {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [buyingKey, setBuyingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<"month" | "year">("month");

  useEffect(() => {
    if (!open) return;
    setLoadingPlans(true);
    setError(null);
    billingApi
      .plans()
      .then((all) => setPlans(all.filter((p) => p.tier !== "free")))
      .catch((e) => setError(e instanceof Error ? e.message : "Не удалось загрузить тарифы"))
      .finally(() => setLoadingPlans(false));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  async function handleBuy(planKey: string) {
    try {
      setBuyingKey(planKey);
      setError(null);
      const invoice = await billingApi.createInvoice(planKey);
      if (typeof window !== "undefined") {
        window.open(invoice.invoice_url, "_blank", "noopener,noreferrer");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать инвойс");
    } finally {
      setBuyingKey(null);
    }
  }

  const reason = _reasonLine(context);
  const filtered = plans.filter((p) =>
    period === "year" ? p.plan_key.endsWith("_year") : p.plan_key.endsWith("_month"),
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-[var(--foreground)]/40 backdrop-blur-sm"
            aria-hidden
          />
          <motion.div
            initial={{ y: "100%", opacity: 0.5 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: "100%", opacity: 0.5 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            className="fixed left-0 right-0 bottom-0 sm:inset-0 z-[110] flex sm:items-center justify-center sm:p-4 pointer-events-none"
            role="dialog"
            aria-modal="true"
            aria-label="Открыть Premium"
          >
            <div
              className="pointer-events-auto w-full sm:max-w-lg bg-[var(--card)] border border-[var(--card-border)] rounded-t-[var(--radius-xl)] sm:rounded-[var(--radius-xl)] shadow-[var(--shadow-3)] overflow-hidden flex flex-col max-h-[90dvh]"
              style={{ paddingBottom: "max(1rem, var(--safe-bottom))" }}
            >
              <span className="sm:hidden block w-10 h-1 rounded-full bg-[var(--border)] mx-auto mt-2 mb-2" aria-hidden />

              <div className="px-6 pt-3 pb-4 border-b border-[var(--border)] flex items-start gap-3">
                <div className="w-11 h-11 rounded-full bg-[var(--accent)]/15 flex items-center justify-center flex-shrink-0">
                  <Icon icon="solar:star-bold-duotone" className="text-[var(--accent)]" width={24} />
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-bold text-[var(--foreground)]">
                    Открой Premium
                  </h2>
                  {reason && (
                    <p className="mt-1 text-sm text-[var(--muted-foreground)] leading-snug">
                      {reason}
                    </p>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="w-11 h-11 rounded-full flex items-center justify-center hover:bg-[var(--color-sand)] transition touch-manipulation"
                  aria-label="Закрыть"
                >
                  <Icon icon="solar:close-circle-bold-duotone" className="text-[var(--muted)]" width={22} />
                </button>
              </div>

              <div className="px-6 pt-4 pb-2">
                <div
                  role="tablist"
                  aria-label="Период оплаты"
                  className="inline-flex p-1 rounded-full bg-[var(--input-bg)] border border-[var(--border)]"
                >
                  {(["month", "year"] as const).map((p) => (
                    <button
                      key={p}
                      role="tab"
                      aria-selected={period === p}
                      onClick={() => setPeriod(p)}
                      className={`px-4 min-h-9 rounded-full text-sm font-medium touch-manipulation transition-colors ${
                        period === p
                          ? "bg-[var(--accent)] text-[var(--accent-foreground)] shadow-[var(--shadow-1)]"
                          : "text-[var(--muted-foreground)]"
                      }`}
                    >
                      {p === "month" ? "Месяц" : "Год −17%"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="px-6 py-3 overflow-y-auto flex-1 flex flex-col gap-3">
                {loadingPlans && (
                  <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                    Загружаю тарифы…
                  </div>
                )}
                {error && (
                  <div className="p-3 rounded-[var(--radius)] border border-[var(--destructive)]/40 bg-[var(--destructive)]/10 text-sm text-[var(--destructive)]">
                    {error}
                  </div>
                )}
                {!loadingPlans &&
                  filtered.map((plan) => {
                    const suggested = suggestedPlanKey === plan.plan_key;
                    return (
                      <div
                        key={plan.plan_key}
                        className={`relative p-4 rounded-[var(--radius)] border transition-colors ${
                          suggested
                            ? "border-[var(--accent)] bg-[var(--color-sand)]"
                            : "border-[var(--border)] bg-[var(--card)]"
                        }`}
                      >
                        {suggested && (
                          <span className="absolute -top-2 left-4 px-2 py-0.5 text-[10px] rounded-full bg-[var(--accent)] text-[var(--accent-foreground)] font-semibold uppercase tracking-wider">
                            Рекомендуем
                          </span>
                        )}
                        <div className="flex items-baseline justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-base font-bold text-[var(--foreground)] truncate">
                              {plan.name}
                            </div>
                            <div className="text-xs text-[var(--muted-foreground)]">
                              {plan.duration_days} дней · {plan.tier.toUpperCase()}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-[var(--accent)] whitespace-nowrap">
                              {formatStars(plan.price_stars)}
                            </div>
                            {plan.price_usd_cents != null && (
                              <div className="text-[11px] text-[var(--muted-foreground)]">
                                ≈ ${(plan.price_usd_cents / 100).toFixed(2)}
                              </div>
                            )}
                          </div>
                        </div>
                        <ul className="mt-3 flex flex-col gap-1 text-sm text-[var(--foreground)]">
                          {plan.features.slice(0, 4).map((f, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <Icon icon="solar:check-circle-bold-duotone" width={16} className="text-[var(--accent)] mt-[2px] flex-shrink-0" />
                              <span className="min-w-0">{f}</span>
                            </li>
                          ))}
                        </ul>
                        <button
                          onClick={() => handleBuy(plan.plan_key)}
                          disabled={buyingKey != null}
                          className="mt-4 w-full min-h-11 rounded-[var(--radius)] bg-[var(--accent)] text-[var(--accent-foreground)] font-semibold shadow-[var(--shadow-1)] disabled:opacity-60 touch-manipulation"
                        >
                          {buyingKey === plan.plan_key ? "Создаю инвойс…" : `Оплатить ${formatStars(plan.price_stars)}`}
                        </button>
                      </div>
                    );
                  })}

                <Link
                  href="/billing"
                  onClick={onClose}
                  className="mt-2 text-center text-sm text-[var(--muted-foreground)] underline-offset-2 hover:underline min-h-11 flex items-center justify-center touch-manipulation"
                >
                  Все тарифы и FAQ →
                </Link>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/** Провайдер слушает глобальное событие `billing:paywall` и открывает
 *  модалку. Подключается в корневом layout авторизованной зоны. */
export function UpgradeModalProvider() {
  const [open, setOpen] = useState(false);
  const [payload, setPayload] = useState<PaywallPayload | null>(null);

  useEffect(() => {
    const unsub = onPaywall((detail) => {
      setPayload(detail);
      setOpen(true);
    });
    return unsub;
  }, []);

  return (
    <UpgradeModal
      open={open}
      onClose={() => setOpen(false)}
      suggestedPlanKey={payload?.upgrade?.suggested_plan_key}
      context={payload}
    />
  );
}
