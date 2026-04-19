"use client";

/**
 * Mounts once inside the authenticated app layout. Pulls the user's saved
 * theme & language from the backend and writes them to localStorage so that
 * the inline boot scripts in app/layout.tsx (themeBootstrapScript /
 * I18nProvider's detectInitialLang) pick them up *before paint* on every
 * subsequent navigation. This is what fixes the "dark theme only kicks in
 * after I open the settings page" bug.
 */
import { useEffect } from "react";

import { api } from "@/lib/api";
import { useTheme, type ThemeMode } from "@/lib/theme";
import { useI18n, type Lang } from "@/lib/i18n";

interface ServerSettings {
  theme?: ThemeMode;
  language?: Lang;
  notifications?: boolean;
}

const THEME_KEY = "ppk:theme";
const LANG_KEY = "ppk:lang";
const SYNCED_FLAG = "ppk:settings-synced";

function isThemeMode(v: unknown): v is ThemeMode {
  return v === "light" || v === "dark" || v === "auto";
}
function isLang(v: unknown): v is Lang {
  return v === "ru" || v === "en" || v === "de" || v === "fr" || v === "es";
}

export function SettingsHydrator() {
  const { theme, setTheme } = useTheme();
  const { lang, setLang } = useI18n();

  useEffect(() => {
    let cancelled = false;
    // We want to sync on first authenticated load of every fresh tab so the
    // bootstrap script has fresh values on the next navigation.
    if (typeof sessionStorage !== "undefined" && sessionStorage.getItem(SYNCED_FLAG)) {
      return;
    }
    api<ServerSettings>("/api/settings")
      .then((s) => {
        if (cancelled || !s) return;
        if (isThemeMode(s.theme) && s.theme !== theme) {
          setTheme(s.theme);
          try {
            localStorage.setItem(THEME_KEY, s.theme);
          } catch {}
        }
        if (isLang(s.language) && s.language !== lang) {
          setLang(s.language);
          try {
            localStorage.setItem(LANG_KEY, s.language);
          } catch {}
        }
        try {
          sessionStorage.setItem(SYNCED_FLAG, "1");
        } catch {}
      })
      .catch(() => {
        /* unauthenticated or backend down — no-op, nothing to hydrate */
      });
    return () => {
      cancelled = true;
    };
    // Intentionally only on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
