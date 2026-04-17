"use client";

/**
 * Fixed noise/grain overlay across the app — adds tactile paper feel.
 * Dropped once into root layout; <1KB, rendered as single SVG.
 */
export function GrainOverlay() {
  return <div className="grain-overlay" aria-hidden="true" />;
}
