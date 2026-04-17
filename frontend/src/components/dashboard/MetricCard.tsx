"use client";

import { motion } from "motion/react";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { TiltCard } from "@/components/motion/TiltCard";

interface MetricCardProps {
  label: string;
  value: number;
  target: number;
  unit: string;
  color?: string;
  decimals?: number;
  /** Hero metric: larger type, more breathing room */
  big?: boolean;
  /** Short hand-written note shown under the number */
  note?: string;
}

export default function MetricCard({
  label,
  value,
  target,
  unit,
  color = "var(--success)",
  decimals = 0,
  big = false,
  note,
}: MetricCardProps) {
  const percent =
    target > 0 ? Math.min(Math.round((value / target) * 100), 100) : 0;
  const pctString = `${percent}%`;

  return (
    <TiltCard intensity={big ? 4 : 6} className="h-full">
      <div
        className={`card-base card-hover h-full relative overflow-hidden ${
          big ? "p-7 lg:p-8" : "p-5"
        }`}
      >
        <div
          className={`pointer-events-none absolute rounded-full blur-2xl ${
            big
              ? "-top-12 -right-12 w-56 h-56 opacity-30"
              : "-top-8 -right-8 w-32 h-32 opacity-40"
          }`}
          style={{ background: color }}
          aria-hidden
        />
        <div className="relative flex items-start justify-between mb-3">
          <p
            className={`font-medium uppercase tracking-widest text-[var(--muted-foreground)] ${
              big ? "text-xs" : "text-[10px]"
            }`}
          >
            {label}
          </p>
          {note && big && (
            <span
              className="text-[11px] text-[var(--muted)] shrink-0 pl-2"
              style={{
                fontFamily: "var(--font-arkhip-stack)",
                letterSpacing: "0.02em",
              }}
            >
              {note}
            </span>
          )}
        </div>

        <p
          className={`relative display-number text-[var(--foreground)] leading-none ${
            big ? "text-7xl lg:text-8xl mb-2" : "text-4xl mb-1"
          }`}
          style={{ fontFamily: "var(--font-display)" }}
        >
          <AnimatedNumber value={value} decimals={decimals} />
        </p>
        <p
          className={`relative text-[var(--muted)] ${
            big ? "text-sm mb-5" : "text-xs mb-4"
          }`}
        >
          из {target.toLocaleString("ru-RU")} {unit}
        </p>

        <div
          className={`relative bg-[var(--color-sand)] rounded-full overflow-hidden ${
            big ? "h-2" : "h-1.5"
          }`}
        >
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: pctString }}
            transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
            className="h-full rounded-full"
            style={{ background: color }}
          />
        </div>
        <p
          className={`relative font-mono mt-1.5 tabular-nums ${
            big ? "text-sm" : "text-xs"
          }`}
          style={{ color }}
        >
          {percent}%
        </p>
      </div>
    </TiltCard>
  );
}
