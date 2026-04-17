"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { type Lang, getTranslator } from "@/lib/i18n";

type Step = "username" | "code";

const LANGS: { code: Lang; label: string }[] = [
  { code: "ru", label: "RU" },
  { code: "en", label: "EN" },
  { code: "de", label: "DE" },
  { code: "fr", label: "FR" },
  { code: "es", label: "ES" },
];

export default function LoginPage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("ru");
  const t = useCallback((key: string) => getTranslator(lang)(key), [lang]);

  const [step, setStep] = useState<Step>("username");
  const [username, setUsername] = useState("");
  const [code, setCode] = useState(["", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleRequestOTP() {
    const name = username.trim().replace(/^@/, "");
    if (!name) return;
    setLoading(true);
    setError("");
    try {
      await api("/api/auth/request-otp", {
        method: "POST",
        body: JSON.stringify({ telegram_username: name }),
      });
      setStep("code");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOTP() {
    const fullCode = code.join("");
    if (fullCode.length < 4) return;
    setLoading(true);
    setError("");
    try {
      const res = await api<{ needs_onboarding: boolean }>("/api/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ telegram_username: username.trim().replace(/^@/, ""), code: fullCode }),
      });
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
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 4);
    if (pasted.length >= 4) {
      e.preventDefault();
      setCode(pasted.split(""));
      document.getElementById("otp-3")?.focus();
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-sm">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-8 shadow-[var(--shadow-1)]">
          <h1
            className="text-center mb-1"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(2.25rem, 8vw, 3rem)",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
              fontWeight: 700,
            }}
          >
            PRO<span className="text-[var(--accent)]">pitashka</span>
          </h1>
          <p className="text-sm text-[var(--muted)] text-center mb-8">
            {t("login_subtitle")}
          </p>

          {step === "username" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
                  Telegram username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRequestOTP()}
                  placeholder={t("login_username_placeholder")}
                  autoFocus
                  className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 transition-colors"
                />
              </div>
              <button
                onClick={handleRequestOTP}
                disabled={loading || !username.trim()}
                className="w-full py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 active:scale-[0.97]"
              >
                {loading ? t("loading") : t("login_send_code")}
              </button>
            </div>
          )}

          {step === "code" && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--success)] text-center">
                {t("login_code_sent")}
              </p>
              <div className="flex justify-center gap-3" onPaste={handleCodePaste}>
                {code.map((digit, i) => (
                  <input
                    key={i}
                    id={`otp-${i}`}
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleCodeChange(i, e.target.value)}
                    onKeyDown={(e) => handleCodeKeyDown(i, e)}
                    autoFocus={i === 0}
                    className="w-14 h-14 text-center font-mono text-2xl font-bold bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 transition-colors"
                  />
                ))}
              </div>
              <button
                onClick={handleVerifyOTP}
                disabled={loading || code.join("").length < 4}
                className="w-full py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 active:scale-[0.97]"
              >
                {loading ? t("loading") : t("login_submit")}
              </button>
              <button
                onClick={() => { setStep("username"); setCode(["", "", "", ""]); setError(""); }}
                className="w-full py-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                {t("login_send_code")}
              </button>
            </div>
          )}

          {error && (
            <p className="mt-4 text-sm text-[var(--destructive)] text-center">{error}</p>
          )}
        </div>

        <div className="flex justify-center gap-4 mt-6">
          {LANGS.map(({ code: lc, label }) => (
            <button
              key={lc}
              onClick={() => setLang(lc)}
              className={`text-xs font-medium transition-colors ${
                lang === lc
                  ? "text-[var(--accent)] font-bold"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
