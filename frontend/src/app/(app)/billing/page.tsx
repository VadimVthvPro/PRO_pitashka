"use client";

import { useEffect, useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import {
  billingApi,
  formatStars,
  quotaLabel,
  useBilling,
  type BillingPayment,
  type BillingPlan,
} from "@/lib/billing";
import { QuotaBar } from "@/components/billing/QuotaBar";

const TIER_BADGES: Record<string, { label: string; color: string }> = {
  free: { label: "FREE", color: "text-[var(--muted-foreground)]" },
  premium: { label: "PREMIUM", color: "text-[var(--accent)]" },
  pro: { label: "PRO", color: "text-[#b85c2b]" },
};

export default function BillingPage() {
  const { me, refetch } = useBilling(15_000);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [payments, setPayments] = useState<BillingPayment[]>([]);
  const [period, setPeriod] = useState<"month" | "year">("month");
  const [error, setError] = useState<string | null>(null);
  const [buyingKey, setBuyingKey] = useState<string | null>(null);

  useEffect(() => {
    billingApi.plans().then(setPlans).catch(() => undefined);
    billingApi
      .history()
      .then((r) => setPayments(r.payments))
      .catch(() => undefined);
  }, []);

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
      setTimeout(refetch, 2000);
    }
  }

  async function handleCancel() {
    if (!confirm("Отключить авто-продление? Текущая подписка доработает до конца срока.")) return;
    try {
      await billingApi.cancel();
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отменить");
    }
  }

  const tierBadge = me ? TIER_BADGES[me.tier] ?? TIER_BADGES.free : TIER_BADGES.free;

  const filteredPlans = plans.filter((p) =>
    p.tier === "free"
      ? false
      : period === "year"
        ? p.plan_key.endsWith("_year")
        : p.plan_key.endsWith("_month"),
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Hero ------------------------------------------------------------ */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative p-5 lg:p-7 rounded-[var(--radius-xl)] bg-[var(--card)] border border-[var(--card-border)] shadow-[var(--shadow-2)] overflow-hidden"
      >
        <div className="absolute -top-10 -right-10 w-60 h-60 rounded-full bg-[var(--accent)]/10 blur-3xl pointer-events-none" aria-hidden />
        <div className="flex items-center gap-2 mb-2">
          <Icon icon="solar:star-bold-duotone" width={18} className="text-[var(--accent)]" />
          <span className={`text-xs font-bold tracking-[0.25em] ${tierBadge.color}`}>
            {tierBadge.label}
          </span>
        </div>
        <h1
          className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[var(--foreground)] leading-[0.95]"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.035em" }}
        >
          {me?.plan_name ?? "Тариф"}
        </h1>
        <p className="mt-2 text-sm text-[var(--muted-foreground)] max-w-[52ch]">
          {me?.tier === "free"
            ? "Ты на бесплатном тарифе. Расширь лимиты и получи доступ к полноценному AI."
            : me?.end_at
              ? `Активен до ${new Date(me.end_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "long", year: "numeric" })}.`
              : "Подписка активна."}
        </p>

        {me && me.tier !== "free" && (
          <button
            onClick={handleCancel}
            className="mt-4 min-h-11 px-4 rounded-full border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition touch-manipulation"
          >
            {me.auto_renew ? "Отключить авто-продление" : "Авто-продление выключено"}
          </button>
        )}
      </motion.div>

      {/* Usage ----------------------------------------------------------- */}
      {me && (
        <section>
          <h2 className="px-1 pb-2 text-sm font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
            Расход лимитов
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {me.usage
              .filter((u) => u.period !== "static")
              .sort((a, b) => quotaLabel(a.key).localeCompare(quotaLabel(b.key), "ru"))
              .map((u) => (
                <QuotaBar key={u.key} item={u} hideIfUnlimited={false} />
              ))}
          </div>
        </section>
      )}

      {/* Plans ----------------------------------------------------------- */}
      <section>
        <div className="flex items-center justify-between gap-3 flex-wrap pb-2 px-1">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
            Тарифы
          </h2>
          <div className="inline-flex p-1 rounded-full bg-[var(--input-bg)] border border-[var(--border)]">
            {(["month", "year"] as const).map((p) => (
              <button
                key={p}
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
        <div className="grid gap-3 sm:grid-cols-2">
          {filteredPlans.map((plan) => {
            const isCurrent = me?.plan_key === plan.plan_key;
            return (
              <div
                key={plan.plan_key}
                className={`relative p-5 rounded-[var(--radius-xl)] border flex flex-col gap-3 ${
                  isCurrent
                    ? "border-[var(--accent)] bg-[var(--color-sand)]"
                    : "border-[var(--card-border)] bg-[var(--card)]"
                }`}
              >
                {isCurrent && (
                  <span className="absolute -top-2 left-4 px-2 py-0.5 text-[10px] rounded-full bg-[var(--accent)] text-[var(--accent-foreground)] font-semibold uppercase tracking-wider">
                    Текущий
                  </span>
                )}
                <div className="flex items-baseline justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-xl font-bold text-[var(--foreground)]">{plan.name}</div>
                    <div className="text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                      {plan.tier}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-[var(--accent)] whitespace-nowrap">
                      {formatStars(plan.price_stars)}
                    </div>
                    {plan.price_usd_cents != null && (
                      <div className="text-xs text-[var(--muted-foreground)]">
                        ≈ ${(plan.price_usd_cents / 100).toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>
                <ul className="flex flex-col gap-1.5 text-sm text-[var(--foreground)]">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Icon icon="solar:check-circle-bold-duotone" width={16} className="text-[var(--accent)] mt-[2px] flex-shrink-0" />
                      <span className="min-w-0">{f}</span>
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => handleBuy(plan.plan_key)}
                  disabled={isCurrent || buyingKey != null}
                  className={`mt-auto w-full min-h-11 rounded-[var(--radius)] font-semibold shadow-[var(--shadow-1)] disabled:opacity-60 touch-manipulation ${
                    isCurrent
                      ? "bg-[var(--input-bg)] text-[var(--muted-foreground)]"
                      : "bg-[var(--accent)] text-[var(--accent-foreground)]"
                  }`}
                >
                  {isCurrent
                    ? "Активен"
                    : buyingKey === plan.plan_key
                      ? "Создаю инвойс…"
                      : `Оплатить ${formatStars(plan.price_stars)}`}
                </button>
              </div>
            );
          })}
        </div>
        {error && (
          <div className="mt-3 p-3 rounded-[var(--radius)] border border-[var(--destructive)]/40 bg-[var(--destructive)]/10 text-sm text-[var(--destructive)]">
            {error}
          </div>
        )}
      </section>

      {/* History --------------------------------------------------------- */}
      <section>
        <h2 className="px-1 pb-2 text-sm font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
          История платежей
        </h2>
        {payments.length === 0 ? (
          <div className="p-4 rounded-[var(--radius)] border border-dashed border-[var(--border)] text-sm text-[var(--muted-foreground)]">
            Платежей пока нет.
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {payments.map((p) => (
              <li
                key={p.id}
                className="flex items-center gap-3 p-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)]"
              >
                <Icon
                  icon={
                    p.status === "paid"
                      ? "solar:check-circle-bold-duotone"
                      : p.status === "refunded"
                        ? "solar:restart-square-bold-duotone"
                        : "solar:clock-circle-bold-duotone"
                  }
                  width={22}
                  className={
                    p.status === "paid"
                      ? "text-[var(--accent)]"
                      : p.status === "refunded"
                        ? "text-[var(--muted)]"
                        : "text-[var(--muted-foreground)]"
                  }
                />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-[var(--foreground)] truncate">
                    {p.plan_key}
                  </div>
                  <div className="text-xs text-[var(--muted-foreground)]">
                    {new Date(p.created_at).toLocaleString("ru-RU")}
                  </div>
                </div>
                <div className="text-sm font-mono whitespace-nowrap">{formatStars(p.stars_amount)}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* FAQ ------------------------------------------------------------ */}
      <section className="p-4 rounded-[var(--radius)] border border-dashed border-[var(--border)] text-sm text-[var(--muted-foreground)] leading-relaxed">
        <p>
          <b>Почему Telegram Stars?</b> Это быстрый и безопасный способ — без карт,
          KYC и комиссий провайдера. Оплата проходит внутри Telegram.
        </p>
        <p className="mt-2">
          <b>Можно ли отменить?</b> Да, в любой момент — текущая подписка
          доработает до конца оплаченного периода, а дальше ты вернёшься на Free.
        </p>
        <p className="mt-2">
          <b>Возврат.</b> В течение 21 дня после оплаты — напиши в поддержку,
          звёзды вернутся на твой баланс Telegram.
        </p>
      </section>
    </div>
  );
}
