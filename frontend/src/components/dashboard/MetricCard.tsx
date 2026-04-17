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
}

export default function MetricCard({
  label,
  value,
  target,
  unit,
  color = "var(--success)",
  decimals = 0,
}: MetricCardProps) {
  const percent = target > 0 ? Math.min(Math.round((value / target) * 100), 100) : 0;
  const pctString = `${percent}%`;

  return (
    <TiltCard intensity={6} className="h-full">
      <div className="card-base card-hover p-5 h-full relative overflow-hidden">
        {/* Decorative gradient blob behind */}
        <div
          className="pointer-events-none absolute -top-8 -right-8 w-32 h-32 rounded-full opacity-40 blur-2xl"
          style={{ background: color }}
          aria-hidden
        />
        <p className="relative text-[10px] font-medium uppercase tracking-widest text-[var(--muted-foreground)] mb-3">
          {label}
        </p>
        <p
          className="relative display-number text-4xl text-[var(--foreground)] mb-1"
          style={{ fontFamily: "var(--font-display)" }}
        >
          <AnimatedNumber value={value} decimals={decimals} />
        </p>
        <p className="relative text-xs text-[var(--muted)] mb-4">
          из {target.toLocaleString("ru-RU")} {unit}
        </p>
        <div className="relative h-1.5 bg-[var(--color-sand)] rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: pctString }}
            transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
            className="h-full rounded-full"
            style={{ background: color }}
          />
        </div>
        <p
          className="relative text-xs font-mono mt-1.5 tabular-nums"
          style={{ color }}
        >
          {percent}%
        </p>
      </div>
    </TiltCard>
  );
}
