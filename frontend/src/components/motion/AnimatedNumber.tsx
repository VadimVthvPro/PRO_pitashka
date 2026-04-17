"use client";

import { animate, useMotionValue, useTransform, motion } from "motion/react";
import { useEffect, useRef } from "react";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  duration?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
}

/**
 * Spring-animated number. Used everywhere metrics are displayed.
 * Animates from previous value to new with smooth easing.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  duration = 1.0,
  className,
  prefix = "",
  suffix = "",
}: AnimatedNumberProps) {
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, (v) => {
    const formatted = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString();
    return `${prefix}${formatted}${suffix}`;
  });
  const prev = useRef(0);

  useEffect(() => {
    const controls = animate(mv, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, mv, duration]);

  return <motion.span className={className}>{rounded}</motion.span>;
}
