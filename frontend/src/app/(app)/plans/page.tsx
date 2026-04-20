"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@iconify/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Markdown } from "@/components/ai/Markdown";

interface PlanResponse {
  plan: string;
  lang?: string;
  id?: number | null;
}

interface ActivePlansResponse {
  meal_plan: string | null;
  workout_plan: string | null;
  lang?: string;
}

interface HistoryItem {
  id: number;
  kind: "meal" | "workout";
  lang: string;
  model: string | null;
  is_active: boolean;
  created_at: string;
  preview: string;
  size_bytes: number;
}

interface HistoryResponse {
  kind: "meal" | "workout";
  items: HistoryItem[];
}

type Kind = "meal" | "workout";

export default function PlansPage() {
  const router = useRouter();
  const { t } = useI18n();

  const [mealPlan, setMealPlan] = useState<string | null>(null);
  const [workoutPlan, setWorkoutPlan] = useState<string | null>(null);
  const [mealLoading, setMealLoading] = useState(false);
  const [workoutLoading, setWorkoutLoading] = useState(false);
  const [mealError, setMealError] = useState<string | null>(null);
  const [workoutError, setWorkoutError] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api<ActivePlansResponse>("/api/ai/plans")
      .then((data) => {
        if (cancelled) return;
        setMealPlan(data.meal_plan ?? null);
        setWorkoutPlan(data.workout_plan ?? null);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setBootstrapping(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const generate = useCallback(
    async (kind: Kind, refresh = false) => {
      const setError = kind === "meal" ? setMealError : setWorkoutError;
      const setLoading = kind === "meal" ? setMealLoading : setWorkoutLoading;
      const setPlan = kind === "meal" ? setMealPlan : setWorkoutPlan;

      setError(null);
      setLoading(true);
      try {
        const url = kind === "meal" ? "/api/ai/meal-plan" : "/api/ai/workout-plan";
        const data = await api<PlanResponse>(`${url}${refresh ? "?refresh=true" : ""}`, {
          method: "POST",
        });
        setPlan(data.plan ?? "");
      } catch (e) {
        const msg = e instanceof Error ? e.message : t("plans_err_generate");
        // Важно: НЕ обнуляем существующий план. После 402/503 у юзера
        // должен остаться предыдущий рабочий план — иначе он "пропадает".
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const replacePlanFromHistory = useCallback((kind: Kind, plan: string) => {
    if (kind === "meal") {
      setMealPlan(plan);
      setMealError(null);
    } else {
      setWorkoutPlan(plan);
      setWorkoutError(null);
    }
  }, []);

  function discuss(kind: "meal_plan" | "workout_plan") {
    router.push(`/ai-chat?attach=${kind}`);
  }

  return (
    <div className="space-y-10 max-w-3xl">
      <div>
        <h1 className="page-title">{t("plans_page_title")}</h1>
        <p className="text-sm text-[var(--muted)] mt-1">{t("plans_subtitle")}</p>
      </div>

      <PlanSection
        kind="meal"
        icon="ph:fork-knife-fill"
        accent="var(--accent)"
        title={t("ai_attach_meal_plan")}
        description={t("plans_meal_subtitle")}
        plan={mealPlan}
        loading={mealLoading || bootstrapping}
        error={mealError}
        onGenerate={() => void generate("meal", false)}
        onRegenerate={() => void generate("meal", true)}
        onDiscuss={() => discuss("meal_plan")}
        onPlanReplaced={(content) => replacePlanFromHistory("meal", content)}
        emptyHint={t("plans_meal_empty_hint")}
        t={t}
      />

      <PlanSection
        kind="workout"
        icon="ph:barbell-fill"
        accent="var(--success)"
        title={t("ai_attach_workout_plan")}
        description={t("plans_workout_subtitle")}
        plan={workoutPlan}
        loading={workoutLoading || bootstrapping}
        error={workoutError}
        onGenerate={() => void generate("workout", false)}
        onRegenerate={() => void generate("workout", true)}
        onDiscuss={() => discuss("workout_plan")}
        onPlanReplaced={(content) => replacePlanFromHistory("workout", content)}
        emptyHint={t("plans_workout_empty_hint")}
        t={t}
      />
    </div>
  );
}

function PlanSection({
  kind,
  icon,
  accent,
  title,
  description,
  plan,
  loading,
  error,
  onGenerate,
  onRegenerate,
  onDiscuss,
  onPlanReplaced,
  emptyHint,
  t,
}: {
  kind: Kind;
  icon: string;
  accent: string;
  title: string;
  description: string;
  plan: string | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
  onRegenerate: () => void;
  onDiscuss: () => void;
  onPlanReplaced: (content: string) => void;
  emptyHint: string;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
  const has = !!plan;
  const [historyOpen, setHistoryOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span
            aria-hidden
            className="w-10 h-10 rounded-full flex items-center justify-center shadow-[var(--shadow-1)] text-white shrink-0"
            style={{ background: accent }}
          >
            <Icon icon={icon} width={20} />
          </span>
          <div className="min-w-0">
            <h2 className="font-display text-lg font-semibold text-[var(--foreground)]">
              {title}
            </h2>
            <p className="text-sm text-[var(--muted-foreground)] mt-0.5">{description}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setHistoryOpen((v) => !v)}
            className="px-3 py-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] text-sm font-medium hover:border-[var(--accent)]/40 inline-flex items-center gap-1.5"
            aria-expanded={historyOpen}
          >
            <Icon icon="ph:clock-counter-clockwise" width={16} />
            {t("plans_history")}
          </button>
          {has && (
            <button
              type="button"
              onClick={onDiscuss}
              className="px-3 py-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] text-sm font-medium hover:border-[var(--accent)]/40 inline-flex items-center gap-1.5"
            >
              <Icon icon="ph:chat-circle-dots" width={16} />
              {t("plans_discuss")}
            </button>
          )}
          <button
            type="button"
            onClick={has ? onRegenerate : onGenerate}
            disabled={loading}
            className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 inline-flex items-center gap-2 shadow-[var(--shadow-1)]"
          >
            {loading ? (
              <>
                <Icon icon="ph:circle-notch" width={16} className="animate-spin" />
                {t("plans_generating")}
              </>
            ) : (
              <>
                <Icon icon={has ? "ph:arrow-clockwise" : "ph:sparkle"} width={16} />
                {has ? t("plans_regenerate") : t("plans_generate")}
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div
          className="rounded-[var(--radius)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-3 py-2 text-sm space-y-1"
          role="alert"
        >
          <div>{error}</div>
          {has && (
            <div className="text-xs text-[var(--muted-foreground)]">
              {t("plans_kept_after_error")}
            </div>
          )}
        </div>
      )}

      {historyOpen && (
        <HistoryPanel
          kind={kind}
          onActivated={(content) => {
            onPlanReplaced(content);
            setHistoryOpen(false);
          }}
          onDeletedActive={() => {
            onPlanReplaced("");
          }}
          t={t}
        />
      )}

      {/* Карточка с планом: w-full + overflow-x-auto чтобы длинные таблицы /
          списки не вылезали за границы на мобильных. min-h, без max-h —
          контент рисуется полностью, а скролл принадлежит странице. */}
      <div
        className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] shadow-[var(--shadow-1)] w-full overflow-hidden"
      >
        <div
          className={`p-5 min-h-[140px] ${
            collapsed ? "max-h-48 overflow-hidden relative" : ""
          }`}
        >
          {loading && !plan ? (
            <p className="text-sm text-[var(--muted-foreground)] flex items-center gap-2">
              <Icon icon="ph:circle-notch" width={16} className="animate-spin shrink-0" />
              {t("plans_generating")}
            </p>
          ) : plan ? (
            <div className="overflow-x-auto">
              <Markdown>{plan}</Markdown>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">{emptyHint}</p>
          )}
          {collapsed && plan && (
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[var(--card)] to-transparent" />
          )}
        </div>

        {has && (
          <div className="border-t border-[var(--border)] px-3 py-2 flex justify-end">
            <button
              type="button"
              onClick={() => setCollapsed((v) => !v)}
              className="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] inline-flex items-center gap-1"
            >
              <Icon
                icon={collapsed ? "ph:caret-down" : "ph:caret-up"}
                width={14}
              />
              {collapsed ? t("plans_expand") : t("plans_collapse")}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function HistoryPanel({
  kind,
  onActivated,
  onDeletedActive,
  t,
}: {
  kind: Kind;
  onActivated: (content: string) => void;
  onDeletedActive: () => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await api<HistoryResponse>(`/api/ai/plans/history?kind=${kind}&limit=20`);
      setItems(data.items);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : t("plans_history_load_failed"));
    }
  }, [kind, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function activate(id: number) {
    setBusyId(id);
    try {
      const data = await api<{ id: number; plan: string }>(
        `/api/ai/plans/${id}/activate`,
        { method: "POST" },
      );
      onActivated(data.plan);
      await load();
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : t("plans_history_load_failed"));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(id: number, wasActive: boolean) {
    if (!window.confirm(t("plans_history_delete_confirm"))) return;
    setBusyId(id);
    try {
      await api<{ ok: true }>(`/api/ai/plans/${id}`, { method: "DELETE" });
      if (wasActive) onDeletedActive();
      await load();
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : t("plans_history_load_failed"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius-lg)] p-3 space-y-2">
      <div className="flex items-center justify-between gap-2 px-1">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">
          {t("plans_history_title")}
        </h3>
      </div>
      {loadError && (
        <div className="text-xs text-[var(--warning)] px-1">{loadError}</div>
      )}
      {items === null ? (
        <p className="text-xs text-[var(--muted-foreground)] px-1 py-2">…</p>
      ) : items.length === 0 ? (
        <p className="text-xs text-[var(--muted-foreground)] px-1 py-2">
          {t("plans_history_empty")}
        </p>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {items.map((it) => (
            <li
              key={it.id}
              className="py-2 px-1 flex flex-wrap items-start justify-between gap-2"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
                  <span>{new Date(it.created_at).toLocaleString()}</span>
                  {it.is_active && (
                    <span className="px-1.5 py-0.5 rounded bg-[var(--accent)]/15 text-[var(--accent)] font-medium">
                      {t("plans_history_active_badge")}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--foreground)] mt-1 line-clamp-2 break-words">
                  {it.preview}
                </p>
              </div>
              <div className="flex gap-1 shrink-0">
                {!it.is_active && (
                  <button
                    type="button"
                    onClick={() => void activate(it.id)}
                    disabled={busyId === it.id}
                    className="px-2 py-1 rounded text-xs border border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)]/40 disabled:opacity-50"
                  >
                    {t("plans_history_activate")}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => void remove(it.id, it.is_active)}
                  disabled={busyId === it.id}
                  className="px-2 py-1 rounded text-xs border border-[var(--border)] bg-[var(--card)] hover:border-[var(--warning)]/40 disabled:opacity-50 text-[var(--warning)]"
                  aria-label={t("plans_history_delete")}
                >
                  <Icon icon="ph:trash" width={14} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
