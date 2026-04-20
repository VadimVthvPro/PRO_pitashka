"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import ru from "@/locales/ru.json";
import en from "@/locales/en.json";
import de from "@/locales/de.json";
import fr from "@/locales/fr.json";
import es from "@/locales/es.json";

const dictionaries: Record<Lang, Record<string, string>> = {
  ru,
  en,
  de,
  fr,
  es,
};

export type Lang = "ru" | "en" | "de" | "fr" | "es";

export const SUPPORTED_LANGS: { code: Lang; label: string; native: string }[] = [
  { code: "ru", label: "Russian", native: "Русский" },
  { code: "en", label: "English", native: "English" },
  { code: "de", label: "German", native: "Deutsch" },
  { code: "fr", label: "French", native: "Français" },
  { code: "es", label: "Spanish", native: "Español" },
];

const STORAGE_KEY = "ppk:lang";

type TVars = Record<string, string | number>;

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  /**
   * Returns a localized string for `key`. If `vars` are provided, every
   * `{name}` placeholder in the source string is replaced with `vars.name`
   * (numbers are formatted via `Intl.NumberFormat` for the active locale).
   *
   * Pluralization: if a value is a number AND the dictionary contains
   * sibling keys `<key>_one` / `<key>_few` / `<key>_many` (Russian-style)
   * or `<key>_one` / `<key>_other` (English-style), the appropriate plural
   * form is picked via `Intl.PluralRules`. The picked entry then receives
   * normal `{n}` interpolation.
   */
  t: (key: string, vars?: TVars) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function isLang(value: string | null): value is Lang {
  return value === "ru" || value === "en" || value === "de" || value === "fr" || value === "es";
}

function detectInitialLang(): Lang {
  if (typeof window === "undefined") return "ru";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (isLang(stored)) return stored;
  const nav = window.navigator.language?.slice(0, 2).toLowerCase();
  if (isLang(nav as string)) return nav as Lang;
  return "ru";
}

function interpolate(template: string, vars: TVars, lang: Lang): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => {
    const v = vars[name];
    if (v === undefined || v === null) return `{${name}}`;
    if (typeof v === "number") {
      try {
        return new Intl.NumberFormat(lang).format(v);
      } catch {
        return String(v);
      }
    }
    return String(v);
  });
}

function pickPluralKey(
  baseKey: string,
  count: number,
  lang: Lang,
  dict: Record<string, string>,
): string {
  // Try Intl.PluralRules first; fall back gracefully if it throws.
  let category: Intl.LDMLPluralRule = "other";
  try {
    category = new Intl.PluralRules(lang).select(count);
  } catch {
    /* keep "other" */
  }
  const candidates = [`${baseKey}_${category}`, `${baseKey}_other`, baseKey];
  for (const k of candidates) {
    if (dict[k] !== undefined) return k;
  }
  return baseKey;
}

export function getTranslator(lang: Lang) {
  const dict = dictionaries[lang] || dictionaries.ru;
  const fallback = dictionaries.ru;
  return (key: string, vars?: TVars): string => {
    let actualKey = key;
    // Pluralization: if exactly one numeric var is passed and a plural
    // sibling exists, use it. We treat the var named `n` or `count` as the
    // pluralization driver; otherwise the first numeric var.
    if (vars) {
      const driverName =
        "n" in vars && typeof vars.n === "number"
          ? "n"
          : "count" in vars && typeof vars.count === "number"
            ? "count"
            : Object.keys(vars).find((k) => typeof vars[k] === "number");
      if (driverName !== undefined) {
        const n = vars[driverName] as number;
        actualKey = pickPluralKey(key, n, lang, dict);
      }
    }
    const raw = dict[actualKey] ?? fallback[actualKey] ?? dict[key] ?? fallback[key] ?? key;
    return vars ? interpolate(raw, vars, lang) : raw;
  };
}

export function I18nProvider({
  children,
  initialLang,
}: {
  children: React.ReactNode;
  initialLang?: Lang;
}) {
  const [lang, setLangState] = useState<Lang>(initialLang ?? "ru");

  useEffect(() => {
    setLangState(detectInitialLang());
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      lang,
      setLang,
      t: getTranslator(lang),
    }),
    [lang, setLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    return { lang: "ru", setLang: () => {}, t: getTranslator("ru") };
  }
  return ctx;
}
