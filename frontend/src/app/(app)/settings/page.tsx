"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Moon, Sun, Monitor, Bell, BellOff, Globe, Trash2 } from "lucide-react";

interface Settings {
  theme: "light" | "dark" | "auto";
  notifications: boolean;
  language: string;
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

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({ theme: "auto", notifications: true, language: "ru" });
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [weight, setWeight] = useState("");

  const [error, setError] = useState("");

  useEffect(() => {
    api<Settings>("/api/settings").then(setSettings).catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки настроек"));
    api<Profile>("/api/users/me").then((p) => {
      setProfile(p);
      setWeight(String(p.weight || ""));
    }).catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки профиля"));
  }, []);

  async function saveSettings(patch: Partial<Settings>) {
    const updated = { ...settings, ...patch };
    setSettings(updated);
    setSaving(true);
    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify(updated) });
    } finally {
      setSaving(false);
    }
  }

  async function updateWeight() {
    const w = Number(weight);
    if (w < 20 || w > 500) return;
    setSaving(true);
    try {
      await api("/api/users/me", { method: "PUT", body: JSON.stringify({ weight: w }) });
      const p = await api<Profile>("/api/users/me");
      setProfile(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось обновить вес");
    } finally {
      setSaving(false);
    }
  }

  const themes: { value: Settings["theme"]; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Светлая", icon: Sun },
    { value: "dark", label: "Тёмная", icon: Moon },
    { value: "auto", label: "Авто", icon: Monitor },
  ];

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="font-display text-2xl font-bold">Настройки</h1>

      {/* Profile */}
      <section className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)]">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">Профиль</h2>
        {profile && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-[var(--muted-foreground)]">Рост</span>
                <p className="font-mono font-medium">{profile.height} см</p>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">Пол</span>
                <p className="font-medium">{profile.user_sex === "M" ? "М" : "Ж"}</p>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">ИМТ</span>
                <p className="font-mono font-medium">{profile.bmi?.toFixed(1)}</p>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">Норма ккал</span>
                <p className="font-mono font-medium">{profile.daily_cal}</p>
              </div>
            </div>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="block text-xs text-[var(--muted-foreground)] mb-1">Вес (кг)</label>
                <input
                  type="number"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] font-mono text-sm focus:border-[var(--accent)] focus:outline-none"
                />
              </div>
              <button
                onClick={updateWeight}
                className="px-4 py-2 bg-[var(--accent)] text-white text-sm font-medium rounded-[var(--radius)] hover:bg-[var(--accent-hover)] transition-colors"
              >
                Обновить
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Theme */}
      <section className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)]">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">Тема</h2>
        <div className="grid grid-cols-3 gap-3">
          {themes.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => saveSettings({ theme: value })}
              className={`flex flex-col items-center gap-2 py-4 rounded-[var(--radius-lg)] border transition-all duration-150 ${
                settings.theme === value
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted-foreground)]"
              }`}
            >
              <Icon size={20} />
              <span className="text-xs font-medium">{label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Language */}
      <section className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)]">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
          <Globe size={14} className="inline mr-1.5 -mt-0.5" />
          Язык
        </h2>
        <div className="flex flex-wrap gap-2">
          {[
            { code: "ru", label: "Русский" },
            { code: "en", label: "English" },
            { code: "de", label: "Deutsch" },
            { code: "fr", label: "Français" },
            { code: "es", label: "Español" },
          ].map(({ code, label }) => (
            <button
              key={code}
              onClick={() => saveSettings({ language: code })}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                settings.language === code
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--color-sand)] text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Notifications */}
      <section className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Уведомления</h2>
            <p className="text-sm text-[var(--muted)] mt-1">Push через Telegram</p>
          </div>
          <button
            onClick={() => saveSettings({ notifications: !settings.notifications })}
            className={`p-2 rounded-[var(--radius)] transition-colors ${
              settings.notifications ? "bg-[var(--success)] text-white" : "bg-[var(--color-sand)] text-[var(--muted)]"
            }`}
          >
            {settings.notifications ? <Bell size={18} /> : <BellOff size={18} />}
          </button>
        </div>
      </section>

      {/* Danger zone */}
      <section className="border border-[var(--destructive)]/30 rounded-[var(--radius-lg)] p-6">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--destructive)] mb-2">Опасная зона</h2>
        <button className="flex items-center gap-2 text-sm text-[var(--destructive)] hover:underline">
          <Trash2 size={14} />
          Удалить аккаунт
        </button>
      </section>

      {error && (
        <p className="text-xs text-[var(--destructive)] text-center">{error}</p>
      )}
      {saving && (
        <p className="text-xs text-[var(--muted-foreground)] text-center">Сохранение...</p>
      )}
    </div>
  );
}
