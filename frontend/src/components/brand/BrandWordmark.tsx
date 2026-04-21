"use client";

/**
 * BrandWordmark — единый компонент рендеринга логотип-текста бренда
 * в навигационных местах (Sidebar, MobileMenu header, MobileTopBar).
 *
 * Почему не literal-ы в каждом из трёх мест:
 *  - Раньше wordmark был захардкожен как `<span>PRO</span> <span>pitashka.</span>`
 *    в трёх разных файлах. При смене бренда на PROfit двухъярусная
 *    композиция (PRO сверху, fit. снизу) выглядела обрубком — тело всего
 *    3 буквы.
 *  - Теперь каждый бренд сам решает, как рендерить свой wordmark
 *    через `brand.wordmarkLayout`:
 *      • "split"   → PRO + body (двухъярусно или inline-baseline).
 *      • "unified" → целиком displayName + акцентная точка в одну строку.
 *  - Компонент инкапсулирует всю типографию, caller передаёт только
 *    размер (`size`) и ориентацию (`orientation`).
 *
 * См. также: `frontend/src/lib/brand.config.ts` → BrandData.wordmarkLayout,
 * `BRAND_ARCHITECTURE.md` §6 (Logo и brand assets).
 */

import { brand } from "@/lib/brand";

/** Размер wordmark-а — масштабирует все кегли синхронно. */
export type BrandWordmarkSize = "sm" | "md" | "lg";

/**
 * Ориентация — имеет значение ТОЛЬКО при `wordmarkLayout === "split"`.
 * При `unified` ориентация игнорируется: wordmark всегда одна строка.
 */
export type BrandWordmarkOrientation = "stacked" | "inline-baseline";

interface Props {
  size?: BrandWordmarkSize;
  /** Для split-бренда: stacked (Sidebar/MobileMenu) vs inline (TopBar). */
  orientation?: BrandWordmarkOrientation;
  /** Доп. классы на корневой элемент — transitions, rotate-on-hover и пр. */
  className?: string;
}

const PREFIX_SIZE: Record<BrandWordmarkSize, string> = {
  sm: "text-[9px]",
  md: "text-[10px]",
  lg: "text-[10px]",
};

const BODY_SIZE: Record<BrandWordmarkSize, string> = {
  sm: "text-xl",
  md: "text-2xl",
  lg: "text-[2.1rem]",
};

const UNIFIED_SIZE: Record<BrandWordmarkSize, string> = {
  sm: "text-lg",
  md: "text-[1.6rem]",
  lg: "text-[2.1rem]",
};

export function BrandWordmark({
  size = "md",
  orientation = "stacked",
  className = "",
}: Props) {
  // ---- UNIFIED (PROfit): одна строка, display-шрифт, точка-акцент ----
  if (brand.wordmarkLayout === "unified") {
    return (
      <span
        className={`inline-block font-bold leading-[0.9] ${UNIFIED_SIZE[size]} ${className}`}
        style={{
          fontFamily: "var(--font-display)",
          letterSpacing: "-0.035em",
        }}
        aria-label={brand.displayName}
      >
        {brand.displayName}
        <span className="text-[var(--accent)]">.</span>
      </span>
    );
  }

  // ---- SPLIT (PROpitashka): PRO мелкий капс + тело display-шрифтом ----
  const prefixCls = `${PREFIX_SIZE[size]} font-semibold uppercase tracking-[0.3em] text-[var(--muted)]`;
  const bodyCls = `${BODY_SIZE[size]} font-bold leading-[0.9]`;
  const bodyStyle = {
    fontFamily: "var(--font-display)",
    letterSpacing: "-0.035em",
  } as const;

  if (orientation === "inline-baseline") {
    // PRO · pitashka. в одну строку с baseline-align (MobileTopBar).
    return (
      <span
        className={`inline-flex items-baseline gap-1 ${className}`}
        aria-label={brand.displayName}
      >
        <span className={prefixCls}>PRO</span>
        <span className={bodyCls} style={bodyStyle}>
          {brand.wordmarkBody}
          <span className="text-[var(--accent)]">.</span>
        </span>
      </span>
    );
  }

  // stacked (Sidebar, MobileMenu): PRO блоком над телом.
  return (
    <span
      className={`inline-block ${className}`}
      aria-label={brand.displayName}
    >
      <span className={`block ${prefixCls}`}>PRO</span>
      <span className={`block ${bodyCls}`} style={bodyStyle}>
        {brand.wordmarkBody}
        <span className="text-[var(--accent)]">.</span>
      </span>
    </span>
  );
}
