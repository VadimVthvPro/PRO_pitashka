"use client";

import { motion, useReducedMotion } from "motion/react";

interface WaterWaveProps {
  glasses: number;
  goal: number;
  size?: number;
}

/**
 * Animated liquid-filled glass SVG.
 * Level rises with springy ease when glasses change; wave continuously animates.
 *
 * Note: the ambient wave loop (left↔right pan) is intentionally kept on even
 * when the OS-level "reduce motion" preference is on — it's a soft, slow,
 * continuous loop that conveys "this is a liquid", not a flashy distractor.
 * Only the level-rise spring is snapped to an instant transition.
 */
export function WaterWave({ glasses, goal, size = 220 }: WaterWaveProps) {
  const reduced = useReducedMotion();
  const pct = Math.min(glasses / Math.max(goal, 1), 1);
  const fillY = (1 - pct) * 100;

  return (
    <div
      className="relative select-none motion-keep"
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 100 100"
        className="absolute inset-0 w-full h-full drop-shadow-[0_20px_40px_oklch(22%_0.015_55/0.18)]"
        aria-label={`${glasses} из ${goal} стаканов`}
      >
        <defs>
          <clipPath id="glass-clip">
            <path d="M 20 10 L 24 88 Q 24 94, 30 94 L 70 94 Q 76 94, 76 88 L 80 10 Z" />
          </clipPath>
          <linearGradient id="water-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="oklch(72% 0.12 230)" />
            <stop offset="100%" stopColor="oklch(52% 0.16 245)" />
          </linearGradient>
          <linearGradient id="glass-shine" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="oklch(99% 0.004 75 / 0.3)" />
            <stop offset="40%" stopColor="oklch(99% 0.004 75 / 0)" />
            <stop offset="100%" stopColor="oklch(99% 0.004 75 / 0.1)" />
          </linearGradient>
        </defs>

        {/* Glass outline */}
        <path
          d="M 20 10 L 24 88 Q 24 94, 30 94 L 70 94 Q 76 94, 76 88 L 80 10 Z"
          fill="oklch(99% 0.004 75 / 0.5)"
          stroke="oklch(35% 0.012 55)"
          strokeWidth="1.2"
        />

        {/* Water content */}
        <g clipPath="url(#glass-clip)">
          <motion.g
            initial={false}
            animate={{ y: fillY }}
            transition={
              reduced
                ? { duration: 0 }
                : { type: "spring", stiffness: 80, damping: 14, mass: 1 }
            }
          >
            {/* Animated wave path — runs always (ambient liquid feel) */}
            <motion.path
              d="M -20 10 Q 5 4, 30 10 T 80 10 T 130 10 L 130 110 L -20 110 Z"
              fill="url(#water-gradient)"
              animate={{ x: [0, -50] }}
              transition={{
                duration: 4,
                ease: "linear",
                repeat: Infinity,
              }}
            />
            {/* Second wave, offset */}
            <motion.path
              d="M -20 14 Q 5 8, 30 14 T 80 14 T 130 14 L 130 110 L -20 110 Z"
              fill="oklch(62% 0.14 235 / 0.4)"
              animate={{ x: [0, -50] }}
              transition={{
                duration: 6,
                ease: "linear",
                repeat: Infinity,
              }}
            />
          </motion.g>
        </g>

        {/* Glass shine */}
        <path
          d="M 20 10 L 24 88 Q 24 94, 30 94 L 70 94 Q 76 94, 76 88 L 80 10 Z"
          fill="url(#glass-shine)"
          pointerEvents="none"
        />
      </svg>

      {/* Center overlay with numbers */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <div
          className="display-number text-5xl text-foreground"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {glasses}
        </div>
        <div className="text-xs uppercase tracking-widest text-muted mt-1">
          из {goal}
        </div>
      </div>
    </div>
  );
}
