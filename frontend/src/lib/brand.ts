/**
 * Единая точка доступа к бренду во всём frontend-коде.
 *
 * Источник значения:
 *   1. build-time: NEXT_PUBLIC_BRAND (в Dockerfile ARG, фиксируется при билде)
 *   2. fallback: "propitashka"
 *
 * Для runtime-переключения бэкенд отдаёт `GET /api/brand` — используй
 * `fetchBrand()` ниже, если нужно свежее значение без пересборки
 * (например, при админ-просмотре текущего активного бренда).
 *
 * Правила использования:
 *   - В компонентах пиши `brand.displayName`, никогда не "PROpitashka"
 *   - В метаданных страницы пиши `generateMetadata()` и читай `brand`
 *   - Для AI / backend-контекстов бренд резолвится на бэке сам
 */

import {
  BRANDS,
  DEFAULT_BRAND,
  type BrandData,
  type BrandId,
  type BrandLang,
} from "./brand.config";

function resolveBuildTimeBrand(): BrandId {
  const raw = (process.env.NEXT_PUBLIC_BRAND || "").toLowerCase();
  if (raw === "profit" || raw === "propitashka") return raw;
  return DEFAULT_BRAND;
}

/**
 * Брендовые данные, зафиксированные в момент сборки Next.js.
 * Для runtime-свежести используй `fetchBrand()`.
 */
export const brand: BrandData = BRANDS[resolveBuildTimeBrand()];

/**
 * Свежие брендовые данные из backend. Используй, если нужно 100%
 * актуальное значение без пересборки Next.js (админ-панель, health-check).
 *
 * Кешируется на уровне fetch (revalidate: 60 сек). В клиентских компонентах
 * можно обернуть в useSWR/useQuery.
 */
export async function fetchBrand(baseUrl = ""): Promise<BrandData> {
  try {
    const url = baseUrl ? `${baseUrl}/api/brand` : "/api/brand";
    const res = await fetch(url, { next: { revalidate: 60 } });
    if (!res.ok) return brand;
    const data = (await res.json()) as {
      name: string;
      display_name: string;
      short_name: string;
      tagline: string;
    };
    const id = (data.name?.toLowerCase?.() ?? "") as BrandId;
    if (id in BRANDS) {
      // askForm / wordmarkBody / wordmarkLayout остаются локальными — они
      // зависят от клиента и не меняются между средами. Берём из словаря.
      return {
        name: id,
        displayName: data.display_name ?? BRANDS[id].displayName,
        shortName: data.short_name ?? BRANDS[id].shortName,
        tagline: data.tagline ?? BRANDS[id].tagline,
        logoDir: BRANDS[id].logoDir,
        wordmarkBody: BRANDS[id].wordmarkBody,
        wordmarkLayout: BRANDS[id].wordmarkLayout,
        askForm: BRANDS[id].askForm,
      };
    }
    return brand;
  } catch {
    return brand;
  }
}

/**
 * Словоформа бренда для конструкции «Спроси …» / «Ask …» на указанном
 * языке. Падение на `displayName`, если язык вне поддержанного списка.
 */
export function brandAskForm(lang: string, data: BrandData = brand): string {
  const key = lang.toLowerCase() as BrandLang;
  return data.askForm[key] ?? data.displayName;
}

export type { BrandData, BrandId, BrandLang } from "./brand.config";
