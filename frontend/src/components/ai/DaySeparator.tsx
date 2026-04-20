"use client";

import { useI18n } from "@/lib/i18n";

interface DaySeparatorProps {
  date: Date;
}

/**
 * Hand-written day label used to chunk the conversation into days.
 * Uses Arkhip stack so it reads as a margin note rather than a UI element.
 */
export function DaySeparator({ date }: DaySeparatorProps) {
  const { t, lang } = useI18n();
  const label = formatRelativeDay(date, lang, t);
  return (
    <div className="flex items-center gap-3 my-2 select-none">
      <span className="flex-1 h-px bg-[var(--border)]" aria-hidden />
      <span
        className="text-sm text-[var(--muted-foreground)] italic"
        style={{ fontFamily: "var(--font-arkhip-stack, var(--font-display))" }}
      >
        {label}
      </span>
      <span className="flex-1 h-px bg-[var(--border)]" aria-hidden />
    </div>
  );
}

function formatRelativeDay(
  date: Date,
  lang: string,
  t: (k: string, v?: Record<string, string | number>) => string,
): string {
  const today = startOfDay(new Date());
  const target = startOfDay(date);
  const diffDays = Math.round(
    (today.getTime() - target.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (diffDays === 0) return t("ai_day_today");
  if (diffDays === 1) return t("ai_day_yesterday");
  if (diffDays > 1 && diffDays < 7) return t("ai_day_n_days_ago", { n: diffDays });
  try {
    return new Intl.DateTimeFormat(lang || "ru", {
      day: "numeric",
      month: "long",
    }).format(date);
  } catch {
    return date.toDateString();
  }
}

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}
