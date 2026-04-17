"use client";

import { motion, useReducedMotion } from "motion/react";
import { ReactNode } from "react";

interface HighlightProps {
  children: ReactNode;
  color?: string;
  className?: string;
}

/**
 * Text wrapped in a hand-drawn marker highlight. Imperfect shape,
 * stays behind the text (z: -1).
 */
export function Highlight({
  children,
  color = "oklch(72% 0.15 80 / 0.45)",
  className,
}: HighlightProps) {
  const reduced = useReducedMotion();
  return (
    <span className={`relative inline-block ${className ?? ""}`}>
      <motion.svg
        aria-hidden="true"
        className="absolute left-[-4%] top-[10%] w-[108%] h-[90%] -z-10"
        viewBox="0 0 120 40"
        preserveAspectRatio="none"
        initial={reduced ? false : { opacity: 0, scaleX: 0 }}
        animate={reduced ? undefined : { opacity: 1, scaleX: 1 }}
        style={{ transformOrigin: "left center" }}
        transition={{ duration: 0.5, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <path
          d="M3 10 Q25 4, 55 8 T118 6 L117 32 Q90 38, 60 34 T4 36 Z"
          fill={color}
        />
      </motion.svg>
      <span className="relative">{children}</span>
    </span>
  );
}
