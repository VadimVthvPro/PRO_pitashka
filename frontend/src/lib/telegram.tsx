"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        disableVerticalSwipes?: () => void;
        setHeaderColor?: (color: string) => void;
        setBackgroundColor?: (color: string) => void;
        viewportHeight?: number;
        viewportStableHeight?: number;
        colorScheme?: "light" | "dark";
        themeParams?: Record<string, string>;
        onEvent?: (event: string, cb: () => void) => void;
        initData?: string;
        initDataUnsafe?: { user?: { id: number; first_name?: string; username?: string } };
      };
    };
  }
}

/**
 * Inline bootstrap that runs *before* React mounts. We:
 *   - call `ready()` so Telegram doesn't show the loader;
 *   - call `expand()` so we get full vertical space (fixes the
 *     "сайт обрезан снизу" Mini App issue);
 *   - mark the document with `data-tma="1"` so CSS can adapt
 *     (e.g. hide our top bar on Telegram, since TG draws its own header).
 */
export const telegramBootstrapScript = `
(function(){
  function init(){
    var w=window.Telegram&&window.Telegram.WebApp; if(!w) return false;
    try { w.ready(); } catch(e){}
    try { w.expand(); } catch(e){}
    try { w.disableVerticalSwipes && w.disableVerticalSwipes(); } catch(e){}
    document.documentElement.setAttribute('data-tma','1');
    if (w.viewportStableHeight) {
      document.documentElement.style.setProperty('--tg-viewport-height', w.viewportStableHeight + 'px');
    }
    return true;
  }
  if (!init()) {
    var i = setInterval(function(){ if (init()) clearInterval(i); }, 80);
    setTimeout(function(){ clearInterval(i); }, 4000);
  }
})();
`;

export function TelegramMiniAppBridge() {
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;
    try {
      tg.ready();
      tg.expand();
    } catch {}

    function syncHeights() {
      const h = tg?.viewportStableHeight || tg?.viewportHeight;
      if (h) {
        document.documentElement.style.setProperty(
          "--tg-viewport-height",
          `${h}px`,
        );
      }
    }
    syncHeights();
    tg.onEvent?.("viewportChanged", syncHeights);
  }, []);
  return null;
}
