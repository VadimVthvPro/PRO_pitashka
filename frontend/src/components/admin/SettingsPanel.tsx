"use client";

/**
 * Admin → Settings.
 *
 * Runtime-editable knobs (AI model, retry budgets, free-tier limits, feature
 * flags) grouped by category. Values are loaded from `/api/admin/settings`
 * and written back with `PUT /api/admin/settings/:key`.
 *
 * Design notes:
 * - Each group gets its own card-base section with a hand-drawn underline
 *   on the title. We deliberately avoid accordion/tabs here — six small
 *   groups fit on one screen and context-switching hurts more than it helps.
 * - Secret values are never displayed. `/api/admin/env-view` returns only
 *   prefix/tail/length, rendered as a small badge strip so the operator can
 *   sanity-check which key is loaded without ever seeing it in plain text.
 * - "Overridden" rows get a small sticker-style pill so you can tell at a
 *   glance which values were edited vs which still follow .env defaults.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type SettingType = "string" | "int" | "float" | "bool";
type SettingGroup = "ai" | "quota" | "features";

interface SettingItem {
  key: string;
  type: SettingType;
  group: SettingGroup;
  description: string;
  default: string | number | boolean;
  value: string | number | boolean;
  overridden: boolean;
  updated_at: string | null;
}

interface EnvView {
  environment: string;
  ai_model_effective: string;
  ai_model_env: string;
  frontend_url: string;
  secrets: Record<
    string,
    { present: boolean; length: number; prefix: string | null; tail: string | null }
  >;
}

const GROUP_META: Record<
  SettingGroup,
  { title: string; icon: string; tone: string }
> = {
  ai: {
    title: "admin_settings_group_ai",
    icon: "solar:magic-stick-3-bold-duotone",
    tone: "var(--accent)",
  },
  quota: {
    title: "admin_settings_group_quota",
    icon: "solar:chart-2-bold-duotone",
    tone: "var(--color-sage)",
  },
  features: {
    title: "admin_settings_group_features",
    icon: "solar:settings-bold-duotone",
    tone: "var(--warning)",
  },
};

export function SettingsPanel() {
  const { t, lang } = useI18n();
  const [items, setItems] = useState<SettingItem[]>([]);
  const [env, setEnv] = useState<EnvView | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, e] = await Promise.all([
        api<{ items: SettingItem[] }>("/api/admin/settings"),
        api<EnvView>("/api/admin/env-view").catch(() => null),
      ]);
      setItems(s.items);
      setEnv(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const groups = useMemo(() => {
    const out: Record<SettingGroup, SettingItem[]> = {
      ai: [], quota: [], features: [],
    };
    items.forEach((it) => out[it.group].push(it));
    return out;
  }, [items]);

  async function save(key: string, value: string | number | boolean) {
    setSavingKey(key);
    try {
      await api(`/api/admin/settings/${key}`, {
        method: "PUT",
        body: JSON.stringify({ value }),
      });
      setToast({ kind: "ok", msg: t("admin_settings_saved", { key }) });
      await load();
    } catch (err) {
      setToast({
        kind: "err",
        msg: err instanceof Error ? err.message : t("error"),
      });
    } finally {
      setSavingKey(null);
      setTimeout(() => setToast(null), 3200);
    }
  }

  if (loading) {
    return (
      <div className="card-base p-8 text-center text-sm text-[var(--muted)]">
        <Icon icon="svg-spinners:180-ring" width={22} className="inline mr-2" />
        {t("common_loading_dots")}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Environment header — shows what's loaded, never raw secrets */}
      {env && <EnvHeader env={env} />}

      {(Object.keys(groups) as SettingGroup[]).map((g) => {
        const list = groups[g];
        if (list.length === 0) return null;
        const meta = GROUP_META[g];
        return (
          <section key={g}>
            <h3 className="flex items-center gap-2 text-sm font-semibold mb-2 px-1">
              <Icon
                icon={meta.icon}
                width={16}
                style={{ color: meta.tone }}
              />
              <span className="relative">
                {t(meta.title)}
                <span
                  className="absolute -bottom-1 left-0 right-0 h-1"
                  style={{
                    background: meta.tone,
                    opacity: 0.25,
                    borderRadius: 2,
                    transform: "skewX(-12deg)",
                  }}
                />
              </span>
            </h3>
            <div className="card-base divide-y divide-[var(--border)]">
              {list.map((it) => (
                <SettingRow
                  key={it.key}
                  item={it}
                  saving={savingKey === it.key}
                  onSave={(v) => save(it.key, v)}
                  t={t}
                  lang={lang}
                />
              ))}
            </div>
          </section>
        );
      })}

      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full shadow-[var(--shadow-2)] text-sm z-50 ${
            toast.kind === "ok"
              ? "bg-[var(--color-sage)] text-white"
              : "bg-[var(--destructive)] text-white"
          }`}
        >
          <Icon
            icon={
              toast.kind === "ok"
                ? "solar:check-circle-bold-duotone"
                : "solar:danger-circle-bold-duotone"
            }
            width={16}
            className="inline mr-1.5 -mt-0.5"
          />
          {toast.msg}
        </motion.div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Env header — metadata-only view of secrets
// ---------------------------------------------------------------------------

function EnvHeader({ env }: { env: EnvView }) {
  const { t } = useI18n();
  const envColor =
    env.environment === "production"
      ? "var(--destructive)"
      : "var(--color-sage)";
  return (
    <section className="card-base p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
          style={{
            background: `${envColor}22`,
            color: envColor,
            border: `1px solid ${envColor}55`,
          }}
        >
          {env.environment}
        </span>
        <span className="text-xs text-[var(--muted)]">
          {t("admin_settings_env_hint")}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {Object.entries(env.secrets).map(([name, info]) => (
          <div
            key={name}
            className="bg-[var(--input-bg)] rounded-lg p-2.5 text-xs"
          >
            <div className="flex items-center justify-between">
              <p className="font-mono font-bold text-[11px]">{name}</p>
              {info.present ? (
                <span className="text-[10px] text-[var(--color-sage)] font-semibold">
                  <Icon icon="solar:check-circle-bold" width={12} className="inline" /> {info.length} {t("admin_settings_chars")}
                </span>
              ) : (
                <span className="text-[10px] text-[var(--destructive)] font-semibold">
                  <Icon icon="solar:close-circle-bold" width={12} className="inline" /> {t("admin_settings_missing")}
                </span>
              )}
            </div>
            <p className="font-mono text-[10px] text-[var(--muted)] mt-0.5 truncate">
              {info.present ? `${info.prefix}…${info.tail?.replace(/^…/, "")}` : "—"}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-[var(--muted-foreground)] leading-relaxed">
        {t("admin_settings_env_disclaimer")}
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Single setting row
// ---------------------------------------------------------------------------

function SettingRow({
  item,
  saving,
  onSave,
  t,
  lang,
}: {
  item: SettingItem;
  saving: boolean;
  onSave: (v: string | number | boolean) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  lang: string;
}) {
  const [draft, setDraft] = useState<string>(String(item.value));

  useEffect(() => {
    setDraft(String(item.value));
  }, [item.value]);

  const dirty =
    item.type === "bool"
      ? false // bool toggles save instantly
      : String(draft).trim() !== String(item.value).trim();

  function commit() {
    if (item.type === "int") onSave(parseInt(draft, 10));
    else if (item.type === "float") onSave(parseFloat(draft));
    else onSave(draft);
  }

  return (
    <div className="px-3 py-3 flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <code className="text-[12px] font-mono font-semibold">{item.key}</code>
          {item.overridden && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--accent)]/15 text-[var(--accent)] font-bold uppercase tracking-wider">
              {t("admin_settings_overridden")}
            </span>
          )}
        </div>
        <p className="text-[11px] text-[var(--muted)] mt-0.5">{item.description}</p>
        <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5">
          {t("admin_settings_default")}: <code>{String(item.default)}</code>
          {item.updated_at && (
            <>
              {" · "}
              {t("admin_settings_updated")}:{" "}
              {new Date(item.updated_at).toLocaleString(lang, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </>
          )}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
        {item.type === "bool" ? (
          <button
            disabled={saving}
            onClick={() => onSave(!item.value)}
            className={`relative w-12 h-7 rounded-full transition ${
              item.value
                ? "bg-[var(--color-sage)]"
                : "bg-[var(--input-bg)] border border-[var(--border)]"
            } ${saving ? "opacity-60" : ""}`}
            aria-pressed={Boolean(item.value)}
          >
            <span
              className={`absolute top-0.5 bg-white shadow rounded-full w-6 h-6 transition-all ${
                item.value ? "left-5" : "left-0.5"
              }`}
            />
          </button>
        ) : (
          <>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && dirty && commit()}
              inputMode={item.type === "int" || item.type === "float" ? "decimal" : "text"}
              className="flex-1 sm:w-48 px-3 py-1.5 text-sm font-mono bg-[var(--input-bg)] border border-[var(--border)] rounded-lg focus:border-[var(--accent)] focus:outline-none"
            />
            <button
              disabled={!dirty || saving}
              onClick={commit}
              className="px-3 py-1.5 text-xs font-semibold bg-[var(--accent)] text-white rounded-lg disabled:opacity-30 active:scale-95 transition"
            >
              {saving ? (
                <Icon icon="svg-spinners:180-ring" width={14} />
              ) : (
                t("admin_settings_save")
              )}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
