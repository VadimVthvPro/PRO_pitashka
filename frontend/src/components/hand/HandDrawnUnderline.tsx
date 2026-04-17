"use client";

import { motion, useReducedMotion } from "motion/react";

interface HandDrawnUnderlineProps {
  color?: string;
  strokeWidth?: number;
  className?: string;
  variant?: 1 | 2 | 3 | 4;
  animate?: boolean;
}

/**
 * Rough marker-like underline. Four hand-drawn variants that look
 * deliberately imperfect — never the same stroke twice.
 */
export function HandDrawnUnderline({
  color = "currentColor",
  strokeWidth = 3,
  className,
  variant = 1,
  animate = true,
}: HandDrawnUnderlineProps) {
  const reduced = useReducedMotion();
  const shouldAnimate = animate && !reduced;

  const paths = {
    1: "M3 12 Q40 4, 80 10 T180 11 T280 8 T380 13 T497 9",
    2: "M2 13 C50 6, 100 16, 160 8 S280 14, 370 9 S480 13, 497 10",
    3: "M5 14 Q80 5, 180 11 T350 7 T497 12",
    4: "M2 10 Q30 16, 60 9 T130 13 T220 8 T320 13 T430 9 T497 11",
  } as const;

  return (
    <svg
      viewBox="0 0 500 20"
      preserveAspectRatio="none"
      className={className}
      aria-hidden="true"
    >
      <motion.path
        d={paths[variant]}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={shouldAnimate ? { pathLength: 0 } : false}
        animate={shouldAnimate ? { pathLength: 1 } : undefined}
        transition={{
          duration: 0.9,
          delay: 0.3,
          ease: [0.22, 1, 0.36, 1],
        }}
      />
    </svg>
  );
}
