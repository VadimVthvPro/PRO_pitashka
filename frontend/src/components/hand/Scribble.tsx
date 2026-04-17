"use client";

import { motion, useReducedMotion } from "motion/react";

interface ScribbleProps {
  variant?: "empty-plate" | "empty-dumbbell" | "empty-sleep" | "squiggle" | "circle";
  className?: string;
  color?: string;
  strokeWidth?: number;
}

/**
 * Hand-drawn illustrations for empty states. Not icons —
 * a single doodle made of a few rough strokes.
 */
export function Scribble({
  variant = "squiggle",
  className,
  color = "currentColor",
  strokeWidth = 2,
}: ScribbleProps) {
  const reduced = useReducedMotion();

  const paths: Record<string, { viewBox: string; d: string[] }> = {
    "empty-plate": {
      viewBox: "0 0 120 120",
      d: [
        // Plate outline — wobbly ellipse
        "M18 62 C18 36, 48 22, 64 22 C88 22, 104 40, 103 62 C102 82, 80 97, 60 97 C38 97, 18 84, 18 62 Z",
        // Inner circle, slightly off-center
        "M32 61 C34 47, 50 37, 62 38 C78 40, 90 51, 89 63 C88 78, 74 86, 60 86 C46 85, 31 76, 32 61 Z",
        // Little crumb
        "M60 58 L62 58",
        "M70 65 L71 66",
      ],
    },
    "empty-dumbbell": {
      viewBox: "0 0 120 80",
      d: [
        // Bar
        "M30 40 L90 40",
        // Left weight
        "M20 28 Q12 40, 20 52 Q30 52, 30 40 Q30 28, 20 28 Z",
        // Right weight
        "M100 28 Q108 40, 100 52 Q90 52, 90 40 Q90 28, 100 28 Z",
        // Sweat drop floating
        "M62 18 Q58 14, 60 10 Q64 14, 62 18 Z",
      ],
    },
    "empty-sleep": {
      viewBox: "0 0 120 80",
      d: [
        // Moon crescent
        "M35 20 Q55 20, 60 40 Q58 55, 42 58 Q30 60, 22 52 Q50 48, 35 20 Z",
        // Z's — sleepy
        "M70 25 L86 25 L70 40 L86 40",
        "M90 42 L100 42 L90 50 L100 50",
      ],
    },
    squiggle: {
      viewBox: "0 0 120 40",
      d: ["M5 20 Q20 5, 35 20 T65 20 T95 20 T115 15"],
    },
    circle: {
      viewBox: "0 0 80 80",
      d: [
        "M10 40 Q10 15, 42 10 Q70 12, 72 42 Q70 68, 40 72 Q12 68, 10 40 Z",
      ],
    },
  };

  const item = paths[variant] ?? paths.squiggle;

  return (
    <svg
      viewBox={item.viewBox}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {item.d.map((d, i) => (
        <motion.path
          key={i}
          d={d}
          initial={reduced ? false : { pathLength: 0, opacity: 0 }}
          animate={reduced ? undefined : { pathLength: 1, opacity: 1 }}
          transition={{
            duration: 0.9,
            delay: 0.1 + i * 0.12,
            ease: [0.22, 1, 0.36, 1],
          }}
        />
      ))}
    </svg>
  );
}
