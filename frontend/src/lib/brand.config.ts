/**
 * Dual-brand configuration (read-only).
 *
 * Не импортировать напрямую в UI-компонентах — только через `brand` из
 * `brand.ts`. Переключение бренда: см. BRAND_ARCHITECTURE.md и правило
 * .cursor/rules/dual-brand-parity.mdc.
 */

export type BrandId = "propitashka" | "profit";

export interface BrandData {
  name: BrandId;
  /** Как имя показывается пользователю в UI и AI-ответах. */
  displayName: string;
  /** Короткая форма для узких мест (sidebar, telegram-шапка). */
  shortName: string;
  /** Одна строка описания продукта. */
  tagline: string;
  /** Директория с ассетами: logo.svg, favicon.ico, og-image.png. */
  logoDir: string;
}

export const BRANDS: Record<BrandId, BrandData> = {
  propitashka: {
    name: "propitashka",
    displayName: "PROpitashka",
    shortName: "ПРОпиташка",
    tagline: "Тёплый дневник питания и тренировок",
    logoDir: "/brand/propitashka",
  },
  profit: {
    name: "profit",
    displayName: "PROfit",
    shortName: "PROfit",
    tagline: "AI-наставник по питанию и тренировкам",
    logoDir: "/brand/profit",
  },
};

export const DEFAULT_BRAND: BrandId = "propitashka";
