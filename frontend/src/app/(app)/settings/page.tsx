"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import { api } from "@/lib/api";
import { useTheme, type ThemeMode } from "@/lib/theme";
import { useI18n, SUPPORTED_LANGS, type Lang } from "@/lib/i18n";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { Sticker } from "@/components/hand/Sticker";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { brand } from "@/lib/brand";
import Link from "next/link";
import { useBilling } from "@/lib/billing";

const BOT_USERNAME =
  process.env.NEXT_PUBLIC_BOT_USERNAME ||
  (brand.name === "profit" ? "PROpitashka_test_bot" : "PROpitashka_bot");

/** Провайдер — блок в секции «Аккаунт». `null` = данных ещё нет. */
interface LinkedProvider {
  linked: boolean;
  email?: string | null;
  username?: string | null;
  login?: string | null;
  picture?: string | null;
}
interface AccountResponse {
  user_id: number;
  display_name: string | null;
  providers: {
    telegram: LinkedProvider;
    google: LinkedProvider;
    yandex: LinkedProvider;
  };
}

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
  const { me: billing } = useBilling(60_000);

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
          <h1 className="page-title">{t("settings_title")}</h1>
        </div>
      </ScrollReveal>

      {/* Billing / Подписка */}
      <ScrollReveal delay={0.04}>
        <Link
          href="/billing"
          className="block card-base p-5 sm:p-6 hover:border-[var(--accent)] transition-colors touch-manipulation"
        >
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-full bg-[var(--accent)]/15 flex items-center justify-center flex-shrink-0">
              <Icon icon="solar:star-bold-duotone" width={22} className="text-[var(--accent)]" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-base font-semibold text-[var(--foreground)]">
                  {billing?.plan_name ?? t("settings_subscription")}
                </span>
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">
                  {(billing?.tier ?? "free").toUpperCase()}
                </span>
              </div>
              <div className="text-xs text-[var(--muted-foreground)] mt-0.5">
                {billing?.tier === "free"
                  ? t("settings_subscription_upsell")
                  : billing?.end_at
                    ? t("settings_subscription_active_until", {
                        date: new Date(billing.end_at).toLocaleDateString(lang),
                      })
                    : t("settings_subscription_manage")}
              </div>
            </div>
            <Icon icon="solar:arrow-right-linear" width={18} className="text-[var(--muted)] flex-shrink-0" />
          </div>
        </Link>
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

      {/* Account — linked providers + logout */}
      <ScrollReveal delay={0.22}>
        <AccountSection />
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

/**
 * Блок «Аккаунт»: показывает состояние привязки трёх провайдеров
 * (Telegram / Google / Yandex) и даёт кнопку Выхода.
 *
 * Важно: не позволяем отвязать ЕДИНСТВЕННЫЙ способ входа — иначе
 * пользователь заблокирует сам себя (никак не сможет войти).
 * Эта проверка чисто клиентская (удобство UX); бэкенд в unlink-эндпоинтах
 * всё равно обновляет колонки без дополнительных проверок, считая, что
 * пользователь осознанно принял решение.
 */
function AccountSection() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [data, setData] = useState<AccountResponse | null>(null);
  const [banner, setBanner] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await api<AccountResponse>("/api/users/me/account");
      setData(d);
    } catch (e) {
      setBanner({ kind: "err", text: e instanceof Error ? e.message : t("error") });
    }
  }, [t]);

  useEffect(() => {
    void load();
    // Если пришли с OAuth redirect'а (yandex link/login), покажем
    // уведомление — эти query-параметры ставятся бэкендом в routers/yandex_auth.py.
    const linked = searchParams.get("auth_linked");
    const error = searchParams.get("auth_error");
    if (linked) {
      setBanner({ kind: "ok", text: t("settings_account_linked", { provider: linked }) });
    } else if (error) {
      setBanner({ kind: "err", text: t("settings_account_link_error") });
    }
    // Intentionally run once; reading searchParams deps leads to loops on client navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const linkedCount = data
    ? Number(data.providers.telegram.linked) +
      Number(data.providers.google.linked) +
      Number(data.providers.yandex.linked)
    : 0;

  const unlink = async (provider: "google" | "yandex") => {
    if (linkedCount <= 1) {
      setBanner({ kind: "err", text: t("settings_account_cannot_unlink_last") });
      return;
    }
    setBusy(true);
    try {
      await api(`/api/auth/${provider}/unlink`, { method: "POST" });
      setBanner({ kind: "ok", text: t("settings_account_unlinked") });
      await load();
    } catch (e) {
      setBanner({ kind: "err", text: e instanceof Error ? e.message : t("error") });
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    if (!window.confirm(t("settings_logout_confirm"))) return;
    setBusy(true);
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {
      // Игнорируем: всё равно чистим клиента и отправляем на /login.
      // Даже если бэк ответил 401 — refresh-кука уже протухла, значит
      // пользователь уже «технически вышел», просто завершаем процесс.
    } finally {
      router.push("/login");
    }
  };

  if (!data) {
    return (
      <section className="card-base p-5 sm:p-6 opacity-60">
        <div className="flex items-center gap-2 mb-2">
          <Icon icon="solar:shield-user-bold-duotone" width={22} className="text-[var(--accent)]" />
          <h2 className="text-base font-semibold">{t("settings_account")}</h2>
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">{t("common_loading_dots")}</p>
      </section>
    );
  }

  const telegram = data.providers.telegram;
  const google = data.providers.google;
  const yandex = data.providers.yandex;

  return (
    <section className="card-base p-5 sm:p-6">
      <div className="flex items-center gap-2 mb-1">
        <Icon icon="solar:shield-user-bold-duotone" width={22} className="text-[var(--accent)]" />
        <h2 className="text-base font-semibold">{t("settings_account")}</h2>
      </div>
      <p className="text-sm text-[var(--muted-foreground)] mb-4">
        {t("settings_account_hint")}
      </p>

      <div className="space-y-3">
        {/* Telegram — привязка только через /start в боте, unlink намеренно отсутствует. */}
        <ProviderRow
          icon="logos:telegram"
          title="Telegram"
          subtitle={
            telegram.linked
              ? telegram.username
                ? `@${telegram.username}`
                : t("settings_account_tg_linked_no_username")
              : t("settings_account_tg_not_linked")
          }
          linked={telegram.linked}
          action={
            telegram.linked ? null : (
              <a
                href={`https://t.me/${BOT_USERNAME}?start=login`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-[var(--accent)] hover:underline touch-manipulation min-h-11 inline-flex items-center px-2"
              >
                {t("settings_account_link")}
              </a>
            )
          }
        />

        {/* Google — link через встроенный GIS-виджет (тот же компонент, что на логине, только mode=link). */}
        <ProviderRow
          icon="logos:google-icon"
          title="Google"
          subtitle={google.linked ? google.email || t("settings_account_linked_nomail") : t("settings_account_google_not_linked")}
          linked={google.linked}
          action={
            google.linked ? (
              <button
                onClick={() => void unlink("google")}
                disabled={busy}
                className="text-sm font-medium text-[var(--destructive)] hover:underline disabled:opacity-50 touch-manipulation min-h-11 px-2"
              >
                {t("settings_account_unlink")}
              </button>
            ) : (
              <div className="w-56">
                <GoogleSignInButton
                  mode="link"
                  onSuccess={async () => {
                    setBanner({ kind: "ok", text: t("settings_account_linked", { provider: "google" }) });
                    await load();
                  }}
                  onError={(msg) => setBanner({ kind: "err", text: msg })}
                />
              </div>
            )
          }
        />

        {/* Yandex — redirect flow. Link-callback возвращает на /settings?auth_linked=yandex. */}
        <ProviderRow
          icon="simple-icons:yandex"
          iconColor="#FC3F1D"
          title="Yandex"
          subtitle={yandex.linked ? yandex.email || yandex.login || t("settings_account_linked_nomail") : t("settings_account_yandex_not_linked")}
          linked={yandex.linked}
          action={
            yandex.linked ? (
              <button
                onClick={() => void unlink("yandex")}
                disabled={busy}
                className="text-sm font-medium text-[var(--destructive)] hover:underline disabled:opacity-50 touch-manipulation min-h-11 px-2"
              >
                {t("settings_account_unlink")}
              </button>
            ) : (
              <a
                href="/api/auth/yandex/authorize?mode=link"
                className="text-sm font-medium text-[var(--accent)] hover:underline touch-manipulation min-h-11 inline-flex items-center px-2"
              >
                {t("settings_account_link")}
              </a>
            )
          }
        />
      </div>

      {banner && (
        <p
          className={`mt-4 text-sm flex items-center gap-2 ${
            banner.kind === "ok" ? "text-[var(--color-sage)]" : "text-[var(--destructive)]"
          }`}
        >
          <Icon
            icon={banner.kind === "ok" ? "solar:check-circle-bold-duotone" : "solar:danger-circle-bold-duotone"}
            width={18}
          />
          {banner.text}
        </p>
      )}

      <div className="mt-6 pt-5 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--muted-foreground)]">
          {t("settings_logout_hint")}
        </div>
        <motion.button
          whileTap={{ scale: 0.96 }}
          onClick={() => void logout()}
          disabled={busy}
          className="inline-flex items-center gap-2 px-4 min-h-11 rounded-[var(--radius)] border border-[var(--destructive)]/40 text-[var(--destructive)] text-sm font-semibold hover:bg-[var(--destructive)]/10 disabled:opacity-50 touch-manipulation"
        >
          <Icon icon="solar:logout-3-bold-duotone" width={18} />
          {t("settings_logout")}
        </motion.button>
      </div>
    </section>
  );
}

function ProviderRow({
  icon,
  iconColor,
  title,
  subtitle,
  linked,
  action,
}: {
  icon: string;
  iconColor?: string;
  title: string;
  subtitle: string;
  linked: boolean;
  action: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-[var(--radius)] border border-[var(--border)]">
      <div className="w-10 h-10 rounded-full bg-[var(--color-sand)]/40 flex items-center justify-center flex-shrink-0">
        <Icon icon={icon} width={22} color={iconColor} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{title}</span>
          {linked && (
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--color-sage)]">
              ✓
            </span>
          )}
        </div>
        <div className="text-xs text-[var(--muted-foreground)] truncate">{subtitle}</div>
      </div>
      <div className="flex-shrink-0">{action}</div>
    </div>
  );
}
