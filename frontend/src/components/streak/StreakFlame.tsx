"use client";

import { motion, useReducedMotion } from "motion/react";
import { useLoadStreak, useStreakStore } from "@/lib/streaks";
import Link from "next/link";

/**
 * Small sidebar / bottomnav flame with the current streak count.
 * - `on_fire`  -> amber, gently flickering
 * - `at_risk`  -> warm red, pulsing faster
 * - `broken` / `none` -> muted, no animation
 */
export function StreakFlame() {
  useLoadStreak();
  const { streak } = useStreakStore();
  const reduced = useReducedMotion();

  if (!streak || streak.current <= 0) {
    return null;
  }

  const { current, status } = streak;
  const colors = {
    on_fire: "text-[var(--warning)]",
    at_risk: "text-[var(--destructive)]",
    broken: "text-[var(--muted)]",
    none: "text-[var(--muted)]",
  }[status];

  const pulseDuration = status === "at_risk" ? 1.2 : 2.4;

  return (
    <Link
      href="/achievements"
      className="group flex items-center gap-2 px-3 py-2 rounded-[var(--radius)] hover:bg-[var(--color-sand)]/50 transition-colors"
      title={
        status === "at_risk"
          ? "Streak в опасности — добавь что-нибудь сегодня"
          : `${current} дней подряд`
      }
    >
      <motion.svg
        width={22}
        height={22}
        viewBox="0 0 24 24"
        fill="currentColor"
        className={`shrink-0 ${colors}`}
        animate={
          reduced
            ? undefined
            : {
                scale: [1, 1.08, 0.98, 1.05, 1],
                rotate: [0, 1, -1, 0.5, 0],
              }
        }
        transition={{
          duration: pulseDuration,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        <path d="M13 3.5c0 2.5-1.5 3.5-2.5 4.5s-2 2-2 4c0 .5.1 1 .3 1.4C7.4 12.5 6 11 6 9c-1 2-1.5 4-1.5 5.5C4.5 18.5 8 21 12 21s7.5-2.5 7.5-6.5c0-4-2.5-6-3.5-8-.7-1.4-2.5-2-3-3z" />
      </motion.svg>
      <div className="flex flex-col leading-tight min-w-0">
        <span
          className="text-xl font-bold tabular-nums"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}
        >
          {current}
        </span>
        <span className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
          {status === "at_risk" ? "на грани" : "подряд"}
        </span>
      </div>
    </Link>
  );
}
