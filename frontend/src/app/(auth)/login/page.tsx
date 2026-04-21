"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Icon } from "@iconify/react";
import { api } from "@/lib/api";
import { useI18n, SUPPORTED_LANGS, type Lang } from "@/lib/i18n";
import { HandDrawnUnderline } from "@/components/hand/HandDrawnUnderline";
import { HandArrow } from "@/components/hand/HandArrow";
import { Sticker } from "@/components/hand/Sticker";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { brand } from "@/lib/brand";

// Имя Telegram-бота для глубокой ссылки. Если env не задан — fallback
// зависит от бренда: у PROfit отдельный @PROpitashka_test_bot (для
// freemium-среды), у PROpitashka — прод-бот.
const BOT_USERNAME =
  process.env.NEXT_PUBLIC_BOT_USERNAME ||
  (brand.name === "profit" ? "PROpitashka_test_bot" : "PROpitashka_bot");

const BRAND_HERO_PREFIX = `PRO · ${brand.wordmarkBody}`;

/**
 * Уникальный 6-символьный alphanumeric код, который бот присылает в чат.
 * Алфавит в auth_service.py: 23456789ABCDEFGHJKLMNPQRSTUVWXYZ.
 * На фронте: приводим к upper-case, разрешаем только этот алфавит,
 * максимум 6 символов. Так пользователь не сможет «случайно» ввести
 * строчные буквы или 0/O — это сократит количество «ключ не подошёл»
 * ошибок.
 */
const CODE_ALPHABET = /[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]/g;
const CODE_LENGTH = 6;

export default function LoginPage() {
  const router = useRouter();
  const { lang, setLang, t } = useI18n();

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const normalizeCode = (raw: string): string => {
    const matches = raw.toUpperCase().match(CODE_ALPHABET);
    return matches ? matches.join("").slice(0, CODE_LENGTH) : "";
  };

  const verifyCode = useCallback(
    async (value: string) => {
      if (value.length < CODE_LENGTH) return;
      setLoading(true);
      setError("");
      try {
        const res = await api<{ needs_onboarding: boolean }>(
          "/api/auth/verify-otp",
          {
            method: "POST",
            body: JSON.stringify({ code: value }),
          },
        );
        router.push(res.needs_onboarding ? "/onboarding" : "/dashboard");
      } catch (e) {
        // Типичные ошибки бэка — 401 «Код не найден или истёк». Переводим
        // на i18n-ключ `login_invalid_code` с call-to-action.
        setError(t("login_invalid_code") || (e instanceof Error ? e.message : t("error")));
        setCode("");
      } finally {
        setLoading(false);
      }
    },
    [router, t],
  );

  const handleCodeInput = (raw: string) => {
    const normalized = normalizeCode(raw);
    setCode(normalized);
    setError("");
    if (normalized.length === CODE_LENGTH) {
      // Автоподтверждение: когда введены все 6 символов — сразу verify.
      // UX-решение: так же работает OTP в App Store / Telegram Login Widget;
      // пользователю не приходится делать лишний клик.
      void verifyCode(normalized);
    }
  };

  const handleYandex = () => {
    // Переход на бэк, который поднимет consent-экран Яндекса и вернёт
    // пользователя в /api/auth/yandex/callback → cookies → /dashboard|/onboarding.
    window.location.href = "/api/auth/yandex/authorize?mode=login";
  };

  return (
    <div
      className="min-h-[100dvh] relative overflow-hidden"
      style={{ paddingTop: "var(--safe-top)", paddingBottom: "var(--safe-bottom)" }}
    >
      <div className="absolute inset-0 mesh-warm opacity-80" aria-hidden />
      <div
        className="absolute top-[-10%] right-[-15%] w-[60vw] h-[60vw] rounded-full blur-[120px] opacity-40"
        style={{ background: "var(--accent)" }}
        aria-hidden
      />
      <div
        className="absolute bottom-[-20%] left-[-10%] w-[45vw] h-[45vw] rounded-full blur-[120px] opacity-30"
        style={{ background: "var(--color-sage)" }}
        aria-hidden
      />

      <div className="relative z-10 min-h-[100dvh] grid lg:grid-cols-[1.1fr_1fr]">
        {/* ============ LEFT: brand + pitch ============ */}
        <div className="flex flex-col justify-between px-6 py-10 lg:px-16 lg:py-14">
          <div>
            <motion.p
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--muted)]"
            >
              {BRAND_HERO_PREFIX}
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.05 }}
              className="mt-8 text-[var(--foreground)]"
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(3rem, 7vw, 6.5rem)",
                lineHeight: 0.88,
                letterSpacing: "-0.035em",
              }}
            >
              {t("login_hero_eat")}
              <br />
              <span className="relative inline-block">
                {t("login_hero_move")}
                <HandDrawnUnderline
                  color="var(--accent)"
                  strokeWidth={5}
                  variant={2}
                  className="absolute left-0 -bottom-1 w-full h-4"
                />
              </span>
              <br />
              {(() => {
                const s = t("login_hero_count");
                const i = s.indexOf("—");
                if (i === -1) return s;
                return (
                  <>
                    {s.slice(0, i + 1)}
                    <span className="text-[var(--accent)]">{s.slice(i + 1).trimStart()}</span>
                  </>
                );
              })()}
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="mt-10 max-w-md"
            >
              <p
                className="text-lg text-[var(--muted)]"
                style={{ fontFamily: "var(--font-body)" }}
              >
                {t("login_hero_pitch")}
              </p>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.7 }}
            className="hidden lg:flex items-center gap-4 mt-14"
          >
            <Sticker color="cream" font="arkhip" rotate={-3} size="sm">
              {t("login_sticker_honest")}
            </Sticker>
            <p
              className="text-sm text-[var(--muted-foreground)] max-w-sm"
              style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "16px" }}
            >
              {t("login_footer_line")}
            </p>
          </motion.div>
        </div>

        {/* ============ RIGHT: form ============ */}
        <div className="flex items-center justify-center px-6 py-10 lg:px-10">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="w-full max-w-sm relative"
          >
            <div className="hidden lg:block absolute -left-16 top-4">
              <HandArrow
                variant="curve-right"
                className="w-14 h-10 text-[var(--accent)] opacity-70"
              />
              <p
                className="mt-1 text-xs text-[var(--muted-foreground)] pl-2"
                style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "13px" }}
              >
                {t("login_starts_here")}
              </p>
            </div>

            <div
              className="card-base p-5 sm:p-8 relative"
              style={{ background: "var(--card)" }}
            >
              <div
                className="absolute -top-3 -right-3"
                style={{ transform: "rotate(8deg)" }}
              >
                <Sticker color="amber" rotate={8} font="appetite" size="sm">
                  {t("login_one_minute")}
                </Sticker>
              </div>

              <h2
                className="mb-1"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "1.875rem",
                  letterSpacing: "-0.02em",
                }}
              >
                {t("login_title")}
              </h2>
              <p className="text-sm text-[var(--muted)] mb-6">
                {t("login_intro_methods")}
              </p>

              {/* ==== Telegram flow (упрощённый: бот → код → вход) ==== */}
              <div className="space-y-3">
                <ol className="text-xs text-[var(--muted-foreground)] space-y-1.5 leading-snug">
                  <li className="flex items-start gap-2">
                    <span className="font-bold text-[var(--accent)]">1.</span>
                    <span>{t("login_tg_step1")}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="font-bold text-[var(--accent)]">2.</span>
                    <span>{t("login_tg_step2")}</span>
                  </li>
                </ol>

                <a
                  href={`https://t.me/${BOT_USERNAME}?start=login`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full min-h-11 rounded-[var(--radius)] border border-[var(--accent)]/40 text-[var(--accent)] text-sm font-medium hover:bg-[var(--accent)]/10 transition touch-manipulation"
                >
                  <Icon icon="logos:telegram" width={18} />
                  {t("login_open_bot", { bot: BOT_USERNAME })}
                </a>

                <div>
                  <label className="block text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted-foreground)] mb-2">
                    {t("login_tg_code_label")}
                  </label>
                  <input
                    type="text"
                    inputMode="text"
                    autoComplete="one-time-code"
                    autoCapitalize="characters"
                    autoCorrect="off"
                    spellCheck={false}
                    maxLength={CODE_LENGTH}
                    value={code}
                    onChange={(e) => handleCodeInput(e.target.value)}
                    onPaste={(e) => {
                      const pasted = e.clipboardData.getData("text");
                      const normalized = normalizeCode(pasted);
                      if (normalized) {
                        e.preventDefault();
                        handleCodeInput(normalized);
                      }
                    }}
                    placeholder="AB3K7Y"
                    className="w-full min-h-12 text-center font-mono text-2xl tracking-[0.35em] bg-[var(--input-bg)] border-2 border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/20 transition-colors"
                    style={{ fontFamily: "var(--font-mono)" }}
                    disabled={loading}
                  />
                  <p className="mt-1.5 text-[11px] text-[var(--muted-foreground)]">
                    {t("login_tg_code_hint")}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 my-5">
                <div className="flex-1 h-px bg-[var(--border)]" />
                <span className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                  {t("login_or")}
                </span>
                <div className="flex-1 h-px bg-[var(--border)]" />
              </div>

              {/* ==== Google (GIS id_token flow) ==== */}
              <div className="mb-3">
                <GoogleSignInButton
                  onSuccess={(res) =>
                    router.push(res.needs_onboarding ? "/onboarding" : "/dashboard")
                  }
                  onError={(msg) => setError(msg)}
                />
              </div>

              {/* ==== Yandex (Authorization Code flow) ==== */}
              <YandexButton onClick={handleYandex} label={t("login_yandex")} />

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 text-sm text-[var(--destructive)] text-center"
                >
                  {error}
                </motion.p>
              )}
            </div>

            <div className="flex flex-wrap justify-center gap-3 mt-8">
              {SUPPORTED_LANGS.map(({ code: lc, native }) => (
                <button
                  key={lc}
                  onClick={() => setLang(lc as Lang)}
                  className={`min-h-11 px-3 text-[11px] font-bold tracking-widest transition-colors touch-manipulation ${
                    lang === lc
                      ? "text-[var(--accent)]"
                      : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  }`}
                >
                  {native}
                </button>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/**
 * Кнопка «Войти через Яндекс». Внутри делаем запрос к /api/auth/yandex/config,
 * чтобы понять, настроен ли провайдер на бэке: если нет — просто не
 * рендерим кнопку (как это делает GoogleSignInButton).
 */
function YandexButton({ onClick, label }: { onClick: () => void; label: string }) {
  const [enabled, setEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<{ enabled: boolean }>("/api/auth/yandex/config")
      .then((cfg) => !cancelled && setEnabled(cfg.enabled))
      .catch(() => !cancelled && setEnabled(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!enabled) return null;

  return (
    <button
      onClick={onClick}
      className="flex items-center justify-center gap-2 w-full min-h-11 rounded-[var(--radius)] border border-[var(--border)] bg-white text-black text-sm font-medium hover:bg-gray-50 transition touch-manipulation"
      style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.06)" }}
    >
      <Icon icon="simple-icons:yandex" width={16} color="#FC3F1D" />
      {label}
    </button>
  );
}
