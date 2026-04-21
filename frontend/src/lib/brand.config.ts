/**
 * Dual-brand configuration (read-only).
 *
 * Не импортировать напрямую в UI-компонентах — только через `brand` из
 * `brand.ts`. Переключение бренда: см. BRAND_ARCHITECTURE.md и правило
 * .cursor/rules/dual-brand-parity.mdc.
 */

export type BrandId = "propitashka" | "profit";

/**
 * Коды языков, которые мы поддерживаем в i18n. Должен совпадать с типом
 * `Lang` из `lib/i18n.tsx` — но brand.config не импортирует i18n, чтобы
 * не создавать циклическую зависимость (i18n использует brand через props).
 */
export type BrandLang = "ru" | "en" | "de" | "fr" | "es";

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
  /**
   * Словоформа для конструкций типа «Спроси {askForm}» / «Ask {askForm}».
   * Разная форма для разных языков (в русском — винительный падеж, в
   * остальных — транслитерация/латинское имя). Отсутствие ключа →
   * fallback на `displayName`.
   */
  askForm: Record<BrandLang, string>;
}

export const BRANDS: Record<BrandId, BrandData> = {
  propitashka: {
    name: "propitashka",
    displayName: "PROpitashka",
    shortName: "ПРОпиташка",
    tagline: "Тёплый дневник питания и тренировок",
    logoDir: "/brand/propitashka",
    askForm: {
      ru: "Пропитошку",
      en: "Propitoshka",
      de: "Propitoshka",
      fr: "Propitoshka",
      es: "Propitoshka",
    },
  },
  profit: {
    name: "profit",
    displayName: "PROfit",
    shortName: "PROfit",
    tagline: "AI-наставник по питанию и тренировкам",
    logoDir: "/brand/profit",
    askForm: {
      // PROfit — не склоняется: "Спроси PROfit", "Ask PROfit" и т.д.
      // Оставлено одинаково на всех языках, т.к. брендовое имя латиницей.
      ru: "PROfit",
      en: "PROfit",
      de: "PROfit",
      fr: "PROfit",
      es: "PROfit",
    },
  },
};

export const DEFAULT_BRAND: BrandId = "propitashka";
