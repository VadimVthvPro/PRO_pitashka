"use client";

import Link from "next/link";
import { Icon } from "@iconify/react";

import type { UsageItem } from "@/lib/billing";
import { quotaLabel, quotaPeriodLabel } from "@/lib/billing";

interface Props {
  item: UsageItem | undefined | null;
  /** Скрывать бар, если квота безлимитна (-1). По умолчанию true. */
  hideIfUnlimited?: boolean;
  compact?: boolean;
  className?: string;
}

export function QuotaBar({ item, hideIfUnlimited = true, compact = false, className }: Props) {
  if (!item) return null;
  if (item.limit === -1 && hideIfUnlimited) return null;

  const limit = item.limit;
  const used = item.used;
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const almost = pct >= 80;
  const full = pct >= 100 || !item.allowed;

  const label = quotaLabel(item.key);
  const period = quotaPeriodLabel(item.period);

  return (
    <div
      className={`${
        compact ? "p-2" : "p-3"
      } rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)]/60 ${
        className ?? ""
      }`}
      aria-live="polite"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon
            icon={full ? "solar:lock-keyhole-minimalistic-bold-duotone" : "solar:graph-bold-duotone"}
            width={compact ? 16 : 18}
            className={full ? "text-[var(--destructive)]" : "text-[var(--accent)]"}
          />
          <span className={`${compact ? "text-xs" : "text-sm"} font-medium text-[var(--foreground)] truncate`}>
            {label}
          </span>
          <span className={`${compact ? "text-[10px]" : "text-xs"} text-[var(--muted-foreground)] whitespace-nowrap`}>
            {period}
          </span>
        </div>
        <div className={`${compact ? "text-xs" : "text-sm"} font-mono whitespace-nowrap ${full ? "text-[var(--destructive)]" : "text-[var(--foreground)]"}`}>
          {limit === -1 ? "∞" : `${used}/${limit}`}
        </div>
      </div>
      {limit > 0 && (
        <div className="mt-2 h-1.5 rounded-full bg-[var(--input-bg)] overflow-hidden">
          <div
            className={`h-full ${full ? "bg-[var(--destructive)]" : almost ? "bg-[var(--warning,orange)]" : "bg-[var(--accent)]"} transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {full && (
        <Link
          href="/billing"
          className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--accent)] underline-offset-2 hover:underline min-h-9 touch-manipulation"
        >
          Открыть Premium
          <Icon icon="solar:arrow-right-linear" width={14} />
        </Link>
      )}
    </div>
  );
}

export function getUsageItem(usage: UsageItem[] | undefined, key: string): UsageItem | undefined {
  return usage?.find((u) => u.key === key);
}
