"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { Icon } from "@iconify/react";
import { api } from "@/lib/api";
import { useI18n, SUPPORTED_LANGS, type Lang } from "@/lib/i18n";
import { HandDrawnUnderline } from "@/components/hand/HandDrawnUnderline";
import { HandArrow } from "@/components/hand/HandArrow";
import { Sticker } from "@/components/hand/Sticker";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";

type Step = "username" | "code";

const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME || "PROpitashka_bot";
const RESEND_SECONDS = 45;

export default function LoginPage() {
  const router = useRouter();
  const { lang, setLang, t } = useI18n();

  const [step, setStep] = useState<Step>("username");
  const [username, setUsername] = useState("");
  const [code, setCode] = useState(["", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsBotStart, setNeedsBotStart] = useState(false);
  const [resendIn, setResendIn] = useState(0);

  useEffect(() => {
    if (resendIn <= 0) return;
    const intervalId = window.setInterval(() => setResendIn((v) => Math.max(0, v - 1)), 1000);
    return () => window.clearInterval(intervalId);
  }, [resendIn]);

  const requestOtp = useCallback(async () => {
    const name = username.trim().replace(/^@/, "");
    if (!name) return;
    setLoading(true);
    setError("");
    setNeedsBotStart(false);
    try {
      const res = await api<{ sent: boolean }>("/api/auth/request-otp", {
        method: "POST",
        body: JSON.stringify({ telegram_username: name }),
      });
      setStep("code");
      setResendIn(RESEND_SECONDS);
      if (!res.sent) setNeedsBotStart(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setLoading(false);
    }
  }, [username, t]);

  async function handleRequestOTP() {
    await requestOtp();
  }

  async function handleResend() {
    if (resendIn > 0) return;
    await requestOtp();
  }

  async function handleVerifyOTP() {
    const fullCode = code.join("");
    if (fullCode.length < 4) return;
    setLoading(true);
    setError("");
    try {
      const res = await api<{ needs_onboarding: boolean }>(
        "/api/auth/verify-otp",
        {
          method: "POST",
          body: JSON.stringify({
            telegram_username: username.trim().replace(/^@/, ""),
            code: fullCode,
          }),
        },
      );
      router.push(res.needs_onboarding ? "/onboarding" : "/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setLoading(false);
    }
  }

  function handleCodeChange(index: number, value: string) {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;
    const next = [...code];
    next[index] = value;
    setCode(next);
    if (value && index < 3) {
      document.getElementById(`otp-${index + 1}`)?.focus();
    }
    if (!value && index > 0) return;
    if (next.every((d) => d !== "") && next.join("").length === 4) {
      setTimeout(() => handleVerifyOTP(), 50);
    }
  }

  function handleCodeKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      document.getElementById(`otp-${index - 1}`)?.focus();
    }
    if (e.key === "Enter") {
      handleVerifyOTP();
    }
  }

  function handleCodePaste(e: React.ClipboardEvent) {
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 4);
    if (pasted.length >= 4) {
      e.preventDefault();
      setCode(pasted.split(""));
      document.getElementById("otp-3")?.focus();
    }
  }

  return (
    <div className="min-h-[100dvh] relative overflow-hidden" style={{ paddingTop: "var(--safe-top)", paddingBottom: "var(--safe-bottom)" }}>
      {/* Atmospheric mesh background */}
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
              PRO · pitashka
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

          {/* Footer / testimonial-ish */}
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
            {/* Little pointing arrow, visible on desktop */}
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
                {step === "username" ? t("login_step_1") : t("login_step_2")}
              </h2>
              <p className="text-sm text-[var(--muted)] mb-6">
                {step === "username" ? t("login_intro_username") : t("login_intro_code")}
              </p>

              {step === "username" && (
                <div className="space-y-4">
                  <ol className="text-xs text-[var(--muted-foreground)] space-y-1.5 mb-3 leading-snug">
                    <li className="flex items-start gap-2">
                      <span className="font-bold text-[var(--accent)]">1.</span>
                      <span>{t("login_how_1")}</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="font-bold text-[var(--accent)]">2.</span>
                      <span>{t("login_how_2")}</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="font-bold text-[var(--accent)]">3.</span>
                      <span>{t("login_how_3")}</span>
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
                      {t("login_username_label")}
                    </label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none">
                        @
                      </span>
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        onKeyDown={(e) =>
                          e.key === "Enter" && handleRequestOTP()
                        }
                        placeholder={t("login_username_placeholder")}
                        autoFocus
                        autoCapitalize="off"
                        autoCorrect="off"
                        spellCheck={false}
                        className="w-full min-w-0 min-h-11 pl-10 pr-4 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 transition-colors"
                      />
                    </div>
                    <p className="mt-1.5 text-[11px] text-[var(--muted-foreground)]">
                      {t("login_username_appsettings")}
                    </p>
                  </div>
                  <motion.button
                    whileHover={{ scale: loading ? 1 : 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={handleRequestOTP}
                    disabled={loading || !username.trim()}
                    className="w-full min-h-11 py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-[var(--shadow-accent)] touch-manipulation"
                  >
                    {loading ? t("login_sending") : t("login_send_code")}
                  </motion.button>

                  <div className="flex items-center gap-3 my-1">
                    <div className="flex-1 h-px bg-[var(--border)]" />
                    <span className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                      {t("login_or")}
                    </span>
                    <div className="flex-1 h-px bg-[var(--border)]" />
                  </div>

                  <GoogleSignInButton
                    onSuccess={(res) =>
                      router.push(res.needs_onboarding ? "/onboarding" : "/dashboard")
                    }
                    onError={(msg) => setError(msg)}
                  />
                </div>
              )}

              {step === "code" && (
                <div className="space-y-4">
                  <AnimatePresence>
                    {needsBotStart && (
                      <motion.div
                        initial={{ opacity: 0, y: -6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="rounded-[var(--radius)] border-2 border-dashed border-[var(--warning)] bg-[var(--warning)]/5 p-3"
                      >
                        <div className="flex items-start gap-2 mb-2">
                          <Icon
                            icon="solar:info-circle-bold-duotone"
                            width={20}
                            className="text-[var(--warning)] shrink-0 mt-0.5"
                          />
                          <p className="text-sm leading-snug">{t("login_needs_bot_start_body")}</p>
                        </div>
                        <a
                          href={`https://t.me/${BOT_USERNAME}?start=login`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-center gap-2 w-full min-h-11 rounded-[var(--radius)] bg-[var(--warning)] text-white text-sm font-semibold touch-manipulation"
                        >
                          <Icon icon="logos:telegram" width={16} />
                          {t("login_not_found_action")}
                        </a>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div
                    className="grid grid-cols-4 gap-2 sm:gap-3"
                    onPaste={handleCodePaste}
                  >
                    {code.map((digit, i) => (
                      <motion.input
                        key={i}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.07, duration: 0.35 }}
                        id={`otp-${i}`}
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        maxLength={1}
                        size={1}
                        value={digit}
                        onChange={(e) => handleCodeChange(i, e.target.value)}
                        onKeyDown={(e) => handleCodeKeyDown(i, e)}
                        autoFocus={i === 0}
                        className="w-full min-w-0 aspect-square sm:h-16 sm:aspect-auto text-center font-mono text-2xl sm:text-3xl font-bold bg-[var(--input-bg)] border-2 border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/20 transition-colors"
                        style={{ fontFamily: "var(--font-mono)" }}
                      />
                    ))}
                  </div>
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={handleVerifyOTP}
                    disabled={loading || code.join("").length < 4}
                    className="w-full min-h-11 py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-[var(--shadow-accent)] touch-manipulation"
                  >
                    {loading ? t("login_verifying") : t("login_btn_enter")}
                  </motion.button>
                  <div className="flex items-center justify-between text-xs gap-2">
                    <button
                      onClick={() => {
                        setStep("username");
                        setCode(["", "", "", ""]);
                        setError("");
                        setNeedsBotStart(false);
                      }}
                      className="min-h-11 px-2 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors touch-manipulation"
                    >
                      {t("login_back_username")}
                    </button>
                    <button
                      onClick={() => void handleResend()}
                      disabled={resendIn > 0 || loading}
                      className="min-h-11 px-2 text-[var(--accent)] hover:underline disabled:text-[var(--muted)] disabled:no-underline disabled:cursor-not-allowed touch-manipulation"
                    >
                      {resendIn > 0 ? t("login_resend_in", { seconds: resendIn }) : t("login_resend_now")}
                    </button>
                  </div>
                </div>
              )}

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
