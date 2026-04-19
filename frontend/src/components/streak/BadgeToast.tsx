"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Icon } from "@iconify/react";
import { type BadgeDTO, dequeueBadge, useStreakStore } from "@/lib/streaks";
import { fireConfetti } from "@/components/motion/confetti";
import { useI18n } from "@/lib/i18n";

const TIER_STYLES: Record<BadgeDTO["tier"], { bg: string; border: string; labelKey: string }> = {
  bronze: {
    bg: "oklch(72% 0.08 55)",
    border: "oklch(52% 0.1 55)",
    labelKey: "achievements_tier_bronze",
  },
  silver: {
    bg: "oklch(82% 0.02 240)",
    border: "oklch(55% 0.02 240)",
    labelKey: "achievements_tier_silver",
  },
  gold: {
    bg: "oklch(82% 0.15 85)",
    border: "oklch(55% 0.15 80)",
    labelKey: "achievements_tier_gold",
  },
  legend: {
    bg: "oklch(62% 0.2 320)",
    border: "oklch(40% 0.22 320)",
    labelKey: "achievements_tier_legend",
  },
};

export function BadgeToast() {
  const { t } = useI18n();
  const { badgeQueue } = useStreakStore();
  const [current, setCurrent] = useState<BadgeDTO | null>(null);

  useEffect(() => {
    if (current) return;
    if (badgeQueue.length === 0) return;
    const next = dequeueBadge();
    setCurrent(next);
    fireConfetti({ y: 0.3 });
    const dismissTimer = setTimeout(() => setCurrent(null), 5000);
    return () => clearTimeout(dismissTimer);
  }, [badgeQueue, current]);

  const style = current ? TIER_STYLES[current.tier] : null;

  return (
    <AnimatePresence>
      {current && style && (
        <motion.div
          key={current.code}
          initial={{ opacity: 0, y: -30, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 320, damping: 22 }}
          className="fixed top-6 left-1/2 -translate-x-1/2 z-[200] pointer-events-auto"
          role="status"
          aria-live="polite"
        >
          <button
            type="button"
            onClick={() => setCurrent(null)}
            className="flex items-center gap-4 pl-4 pr-5 py-3 rounded-[var(--radius-lg)] border-2 shadow-[var(--shadow-3)] hover:shadow-[var(--shadow-accent)] transition-shadow"
            style={{
              background: "var(--card)",
              borderColor: style.border,
            }}
          >
            <motion.div
              initial={{ rotate: -20, scale: 0.5 }}
              animate={{ rotate: 0, scale: 1 }}
              transition={{ type: "spring", stiffness: 280, damping: 14, delay: 0.1 }}
              className="shrink-0 w-14 h-14 rounded-full flex items-center justify-center text-white"
              style={{ background: style.bg }}
            >
              <Icon icon={current.icon} width={28} />
            </motion.div>
            <div className="text-left">
              <p
                className="text-[10px] uppercase tracking-[0.2em] font-semibold"
                style={{ color: style.border }}
              >
                {t("badge_toast_new_prefix")} {t(style.labelKey)}
              </p>
              <p
                className="text-lg leading-tight"
                style={{
                  fontFamily: "var(--font-display)",
                  letterSpacing: "-0.02em",
                  fontWeight: 700,
                }}
              >
                {current.title}
              </p>
              <p className="text-xs text-[var(--muted)] max-w-[36ch] truncate">
                {current.description}
              </p>
            </div>
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
