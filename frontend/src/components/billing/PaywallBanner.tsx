"use client";

import Link from "next/link";
import { Icon } from "@iconify/react";

import { useBilling } from "@/lib/billing";

/** Узкий баннер для Free-юзеров на дашборде. Автоматически прячется,
 *  если юзер уже на Premium или Pro. */
export function PaywallBanner() {
  const { me, loading } = useBilling(60_000);
  if (loading) return null;
  if (!me) return null;
  if (me.tier !== "free") return null;

  return (
    <Link
      href="/billing"
      className="relative flex items-center gap-3 p-4 rounded-[var(--radius)] border border-[var(--accent)]/30 bg-gradient-to-br from-[var(--color-sand)] to-[var(--card)] hover:border-[var(--accent)] transition-colors touch-manipulation"
    >
      <div className="w-11 h-11 rounded-full bg-[var(--accent)]/20 flex items-center justify-center flex-shrink-0">
        <Icon icon="solar:star-bold-duotone" width={24} className="text-[var(--accent)]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-bold text-[var(--foreground)]">
          Открой Premium
        </div>
        <div className="text-xs text-[var(--muted-foreground)] leading-snug">
          200 AI-сообщений в день, безлимитные планы. От 249 ⭐ / месяц.
        </div>
      </div>
      <Icon icon="solar:arrow-right-linear" className="text-[var(--accent)] flex-shrink-0" width={20} />
    </Link>
  );
}
