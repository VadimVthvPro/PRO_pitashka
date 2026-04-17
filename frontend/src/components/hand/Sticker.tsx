"use client";

import { motion, useReducedMotion } from "motion/react";
import { ReactNode } from "react";

interface StickerProps {
  children: ReactNode;
  rotate?: number;
  color?: "accent" | "sage" | "amber" | "rust" | "cream";
  size?: "sm" | "md";
  className?: string;
  font?: "display" | "arkhip" | "appetite";
}

/**
 * Skewed little label in a warm color — like a price tag slapped on.
 * Honors reduced-motion: skips the wobble.
 */
export function Sticker({
  children,
  rotate = -3,
  color = "amber",
  size = "md",
  className,
  font = "display",
}: StickerProps) {
  const reduced = useReducedMotion();
  const colors = {
    accent:
      "bg-[var(--accent)] text-white border-[oklch(42%_0.14_35)]",
    sage:
      "bg-[var(--success)] text-white border-[oklch(42%_0.09_155)]",
    amber:
      "bg-[var(--warning)] text-[oklch(25%_0.05_80)] border-[oklch(55%_0.14_80)]",
    rust:
      "bg-[var(--destructive)] text-white border-[oklch(35%_0.14_25)]",
    cream:
      "bg-[var(--color-sand)] text-[var(--foreground)] border-[var(--color-clay)]",
  } as const;

  const sizes = {
    sm: "px-2 py-0.5 text-[10px] leading-tight",
    md: "px-2.5 py-1 text-xs leading-tight",
  };

  const fontStack = {
    display: "var(--font-display)",
    arkhip: "var(--font-arkhip-stack)",
    appetite: "var(--font-appetite-stack)",
  }[font];

  return (
    <motion.span
      animate={
        reduced
          ? undefined
          : { rotate: [rotate, rotate + 1.2, rotate - 0.8, rotate] }
      }
      transition={{
        duration: 6,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      style={{
        display: "inline-block",
        fontFamily: fontStack,
        letterSpacing: "-0.01em",
        rotate: `${rotate}deg`,
      }}
      className={`border-[1.5px] rounded-sm uppercase font-bold tracking-wide shadow-[2px_2px_0_rgba(0,0,0,0.08)] ${colors[color]} ${sizes[size]} ${className ?? ""}`}
    >
      {children}
    </motion.span>
  );
}
