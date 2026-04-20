"use client";

import { useEffect, useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import { api } from "@/lib/api";
import { useTheme, type ThemeMode } from "@/lib/theme";
import { useI18n, SUPPORTED_LANGS, type Lang } from "@/lib/i18n";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { Sticker } from "@/components/hand/Sticker";

interface SettingsResponse {
  theme: ThemeMode;
  notifications: boolean;
  language: Lang;
}

interface Profile {
  user_name?: string;
  weight?: number;
  height?: number;
  user_sex?: string;
  aim?: string;
  daily_cal?: number;
  bmi?: number;
}

const themeOptions: { value: ThemeMode; icon: string; labelKey: string }[] = [
  { value: "light", icon: "solar:sun-bold-duotone", labelKey: "settings_theme_light" },
  { value: "dark", icon: "solar:moon-bold-duotone", labelKey: "settings_theme_dark" },
  { value: "auto", icon: "solar:laptop-bold-duotone", labelKey: "settings_theme_auto" },
];

const aims = [
  { value: "weight_loss", labelKey: "onboarding_aim_loss" },
  { value: "maintain", labelKey: "onboarding_aim_maintain" },
  { value: "weight_gain", labelKey: "onboarding_aim_gain" },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { lang, setLang, t } = useI18n();

  const [notifications, setNotifications] = useState(true);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileDraft, setProfileDraft] = useState({ weight: "", height: "", aim: "" });
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api<SettingsResponse>("/api/settings").catch(() => null),
      api<Profile>("/api/users/me").catch(() => null),
    ])
      .then(([s, p]) => {
        if (s) {
          if (s.theme && s.theme !== theme) setTheme(s.theme);
          if (s.language && s.language !== lang) setLang(s.language);
          setNotifications(Boolean(s.notifications));
        }
        if (p) {
          setProfile(p);
          setProfileDraft({
            weight: p.weight?.toString() ?? "",
            height: p.height?.toString() ?? "",
            aim: p.aim ?? "",
          });
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("settings_err_load")));
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const flash = (msg: string) => {
    setSavedFlash(msg);
    window.setTimeout(() => setSavedFlash((s) => (s === msg ? null : s)), 2000);
  };

  async function persistSettings(patch: Partial<SettingsResponse>) {
    setSaving(true);
    setError("");
    try {
      await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          theme: patch.theme ?? theme,
          notifications: patch.notifications ?? notifications,
          language: patch.language ?? lang,
        }),
      });
      flash(t("settings_saved"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("settings_err_save"));
    } finally {
      setSaving(false);
    }
  }

  function chooseTheme(next: ThemeMode) {
    setTheme(next);
    void persistSettings({ theme: next });
  }

  function chooseLang(next: Lang) {
    setLang(next);
    void persistSettings({ language: next });
  }

  function toggleNotifications() {
    const next = !notifications;
    setNotifications(next);
    void persistSettings({ notifications: next });
  }

  async function saveProfile() {
    const w = parseFloat(profileDraft.weight.replace(",", "."));
    const h = parseFloat(profileDraft.height.replace(",", "."));
    if (!Number.isFinite(w) || w < 20 || w > 400) {
      setError(t("settings_weight_range"));
      return;
    }
    if (!Number.isFinite(h) || h < 80 || h > 250) {
      setError(t("settings_height_range"));
      return;
    }
    setError("");
    setSaving(true);
    try {
      await api("/api/users/me", {
        method: "PUT",
        body: JSON.stringify({
          weight: w,
          height: h,
          aim: profileDraft.aim || undefined,
        }),
      });
      const fresh = await api<Profile>("/api/users/me");
      setProfile(fresh);
      flash(t("settings_saved"));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("err_save"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <ScrollReveal>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
            {t("settings_profile")}
          </p>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(2.25rem, 1.5rem + 2.5vw, 3.5rem)",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
            }}
          >
            {t("settings_title")}
          </h1>
        </div>
      </ScrollReveal>

      {/* Profile */}
      <ScrollReveal delay={0.05}>
        <section className="card-base p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-4">
            <Icon icon="solar:user-bold-duotone" width={22} className="text-[var(--accent)]" />
            <h2 className="text-base font-semibold">{t("settings_profile")}</h2>
          </div>

          {profile && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5 text-sm">
                <Stat
                  label={t("field_sex")}
                  value={profile.user_sex === "M" ? t("settings_sex_m_short") : t("settings_sex_f_short")}
                />
                <Stat label={t("field_bmi")} value={profile.bmi ? profile.bmi.toFixed(1) : "—"} />
                <Stat label={t("field_daily_kcal")} value={profile.daily_cal?.toString() ?? "—"} />
                <Stat
                  label={t("field_aim")}
                  value={(() => {
                    const a = aims.find((a) => a.value === profile.aim);
                    return a ? t(a.labelKey) : "—";
                  })()}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <FieldGroup label={t("field_weight_kg")}>
                  <input
                    type="number"
                    step="0.1"
                    value={profileDraft.weight}
                    onChange={(e) => setProfileDraft((d) => ({ ...d, weight: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] font-mono tabular-nums focus:border-[var(--accent)] focus:outline-none"
                  />
                </FieldGroup>
                <FieldGroup label={t("field_height_cm")}>
                  <input
                    type="number"
                    value={profileDraft.height}
                    onChange={(e) => setProfileDraft((d) => ({ ...d, height: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] font-mono tabular-nums focus:border-[var(--accent)] focus:outline-none"
                  />
                </FieldGroup>
                <FieldGroup label={t("field_aim")}>
                  <select
                    value={profileDraft.aim}
                    onChange={(e) => setProfileDraft((d) => ({ ...d, aim: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] focus:border-[var(--accent)] focus:outline-none"
                  >
                    <option value="">—</option>
                    {aims.map((a) => (
                      <option key={a.value} value={a.value}>
                        {t(a.labelKey)}
                      </option>
                    ))}
                  </select>
                </FieldGroup>
              </div>

              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={() => void saveProfile()}
                disabled={saving}
                className="mt-4 px-5 py-2.5 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
              >
                {saving ? t("settings_saving") : t("settings_save_profile")}
              </motion.button>
            </>
          )}
        </section>
      </ScrollReveal>

      {/* Theme */}
      <ScrollReveal delay={0.1}>
        <section className="card-base p-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Icon icon="solar:palette-bold-duotone" width={22} className="text-[var(--accent)]" />
              <h2 className="text-base font-semibold">{t("settings_theme")}</h2>
            </div>
            <Sticker color="cream" font="arkhip" size="sm" rotate={-2}>
              {t("live_switch")}
            </Sticker>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {themeOptions.map(({ value, icon, labelKey }) => (
              <motion.button
                key={value}
                whileTap={{ scale: 0.95 }}
                onClick={() => chooseTheme(value)}
                className={`flex flex-col items-center gap-2 py-4 rounded-[var(--radius-lg)] border transition ${
                  theme === value
                    ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]"
                    : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted-foreground)]"
                }`}
              >
                <Icon icon={icon} width={26} />
                <span className="text-xs font-semibold">{t(labelKey)}</span>
              </motion.button>
            ))}
          </div>
          <p className="text-xs text-[var(--muted-foreground)] mt-3">
            {t("settings_theme_hint")}
          </p>
        </section>
      </ScrollReveal>

      {/* Language */}
      <ScrollReveal delay={0.15}>
        <section className="card-base p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-4">
            <Icon icon="solar:global-bold-duotone" width={22} className="text-[var(--accent)]" />
            <h2 className="text-base font-semibold">{t("settings_language")}</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUPPORTED_LANGS.map(({ code, native }) => (
              <motion.button
                key={code}
                whileTap={{ scale: 0.96 }}
                onClick={() => chooseLang(code)}
                className={`px-4 min-h-11 rounded-full text-sm font-medium transition touch-manipulation ${
                  lang === code
                    ? "bg-[var(--accent)] text-white shadow-[var(--shadow-1)]"
                    : "bg-[var(--color-sand)] text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {native}
              </motion.button>
            ))}
          </div>
          <p className="text-xs text-[var(--muted-foreground)] mt-3">
            {t("settings_lang_hint")}
          </p>
        </section>
      </ScrollReveal>

      {/* Notifications */}
      <ScrollReveal delay={0.2}>
        <section className="card-base p-5 sm:p-6 flex items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Icon icon="solar:bell-bold-duotone" width={22} className="text-[var(--accent)] mt-0.5" />
            <div>
              <h2 className="text-base font-semibold">{t("settings_notifications")}</h2>
              <p className="text-sm text-[var(--muted-foreground)]">
                {t("settings_notifications_hint")}
              </p>
            </div>
          </div>
          <motion.button
            whileTap={{ scale: 0.94 }}
            onClick={toggleNotifications}
            aria-pressed={notifications}
            aria-label={t("settings_notifications")}
            className={`relative w-16 h-11 shrink-0 rounded-full transition touch-manipulation ${
              notifications ? "bg-[var(--accent)]" : "bg-[var(--color-sand)]"
            }`}
          >
            <motion.span
              className="absolute top-1.5 left-1.5 w-8 h-8 rounded-full bg-white shadow"
              animate={{ x: notifications ? 20 : 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 28 }}
            />
          </motion.button>
        </section>
      </ScrollReveal>

      {/* Status banner */}
      <div className="min-h-[24px]">
        {savedFlash && (
          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-sm text-[var(--color-sage)] flex items-center gap-2"
          >
            <Icon icon="solar:check-circle-bold-duotone" width={18} />
            {savedFlash}
          </motion.p>
        )}
        {error && (
          <p className="text-sm text-[var(--destructive)] flex items-center gap-2">
            <Icon icon="solar:danger-circle-bold-duotone" width={18} />
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius)] bg-[var(--color-sand)]/40 px-3 py-2">
      <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">{label}</p>
      <p className="font-semibold mt-0.5 truncate">{value}</p>
    </div>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
