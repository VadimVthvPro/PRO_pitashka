"use client";

import confetti from "canvas-confetti";

const WARM_COLORS = [
  "#C4623A", // terracotta
  "#E8B9A0", // terracotta light
  "#D4A030", // amber
  "#6B9E7A", // sage
  "#FAF7F2", // cream
];

/** Fires a warm-palette confetti burst. Use on achievements and goal completion. */
export function fireConfetti(origin: { x?: number; y?: number } = {}) {
  const x = origin.x ?? 0.5;
  const y = origin.y ?? 0.5;

  confetti({
    particleCount: 80,
    spread: 70,
    startVelocity: 40,
    gravity: 0.9,
    ticks: 220,
    origin: { x, y },
    colors: WARM_COLORS,
    scalar: 1.1,
  });

  setTimeout(() => {
    confetti({
      particleCount: 40,
      spread: 100,
      startVelocity: 30,
      gravity: 0.8,
      ticks: 180,
      origin: { x: x - 0.1, y },
      colors: WARM_COLORS,
      scalar: 0.8,
    });
  }, 120);
}
