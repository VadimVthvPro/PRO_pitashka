"use client";

import { motion, useReducedMotion } from "motion/react";

interface HandArrowProps {
  className?: string;
  color?: string;
  strokeWidth?: number;
  /** 'curve-right' | 'curve-down' | 'curve-left' | 'squiggle' */
  variant?: "curve-right" | "curve-down" | "curve-left" | "squiggle";
  animate?: boolean;
}

/**
 * Wobbly hand-drawn arrow. Used to point at CTAs, stickers, important bits.
 */
export function HandArrow({
  className,
  color = "currentColor",
  strokeWidth = 2.25,
  variant = "curve-right",
  animate = true,
}: HandArrowProps) {
  const reduced = useReducedMotion();
  const shouldAnimate = animate && !reduced;

  const variants = {
    "curve-right": {
      body: "M5 40 Q30 10, 70 18 Q100 24, 115 38",
      tip: "M103 30 L115 38 L107 50",
      viewBox: "0 0 120 60",
    },
    "curve-down": {
      body: "M20 5 Q30 30, 18 55 Q12 70, 25 90",
      tip: "M15 78 L25 90 L36 80",
      viewBox: "0 0 50 100",
    },
    "curve-left": {
      body: "M115 40 Q90 10, 50 18 Q20 24, 5 38",
      tip: "M17 30 L5 38 L13 50",
      viewBox: "0 0 120 60",
    },
    squiggle: {
      body: "M5 30 Q15 10, 30 30 T60 30 T90 30 Q100 30, 112 28",
      tip: "M100 20 L115 30 L100 40",
      viewBox: "0 0 120 60",
    },
  } as const;

  const v = variants[variant];

  return (
    <svg
      viewBox={v.viewBox}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <motion.path
        d={v.body}
        initial={shouldAnimate ? { pathLength: 0 } : false}
        animate={shouldAnimate ? { pathLength: 1 } : undefined}
        transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.path
        d={v.tip}
        initial={shouldAnimate ? { pathLength: 0, opacity: 0 } : false}
        animate={shouldAnimate ? { pathLength: 1, opacity: 1 } : undefined}
        transition={{ duration: 0.4, delay: 0.9, ease: "easeOut" }}
      />
    </svg>
  );
}
