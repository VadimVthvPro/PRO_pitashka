"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@iconify/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Markdown } from "@/components/ai/Markdown";

interface PlanResponse {
  plan: string;
}

interface ActivePlansResponse {
  meal_plan: string | null;
  workout_plan: string | null;
  lang?: string;
}

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

  // Pull whatever plans are already cached on the server, so the user
  // doesn't have to re-generate just because they reloaded the page.
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

  async function generate(kind: "meal" | "workout", refresh = false) {
    if (kind === "meal") {
      setMealError(null);
      setMealLoading(true);
    } else {
      setWorkoutError(null);
      setWorkoutLoading(true);
    }
    try {
      const url = kind === "meal" ? "/api/ai/meal-plan" : "/api/ai/workout-plan";
      const data = await api<PlanResponse>(`${url}${refresh ? "?refresh=true" : ""}`, {
        method: "POST",
      });
      if (kind === "meal") setMealPlan(data.plan ?? "");
      else setWorkoutPlan(data.plan ?? "");
    } catch (e) {
      const msg = e instanceof Error ? e.message : t("plans_err_generate");
      if (kind === "meal") {
        setMealError(msg);
        setMealPlan(null);
      } else {
        setWorkoutError(msg);
        setWorkoutPlan(null);
      }
    } finally {
      if (kind === "meal") setMealLoading(false);
      else setWorkoutLoading(false);
    }
  }

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
        emptyHint={t("plans_meal_empty_hint")}
        t={t}
      />

      <PlanSection
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
        emptyHint={t("plans_workout_empty_hint")}
        t={t}
      />
    </div>
  );
}

function PlanSection({
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
  emptyHint,
  t,
}: {
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
  emptyHint: string;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
  const has = !!plan;
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="w-10 h-10 rounded-full flex items-center justify-center shadow-[var(--shadow-1)] text-white"
            style={{ background: accent }}
          >
            <Icon icon={icon} width={20} />
          </span>
          <div>
            <h2 className="font-display text-lg font-semibold text-[var(--foreground)]">
              {title}
            </h2>
            <p className="text-sm text-[var(--muted-foreground)] mt-0.5">{description}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
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
          className="rounded-[var(--radius)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-3 py-2 text-sm"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)] min-h-[140px]">
        {loading && !plan ? (
          <p className="text-sm text-[var(--muted-foreground)] flex items-center gap-2">
            <Icon icon="ph:circle-notch" width={16} className="animate-spin shrink-0" />
            {t("plans_generating")}
          </p>
        ) : plan ? (
          <Markdown>{plan}</Markdown>
        ) : (
          <p className="text-sm text-[var(--muted-foreground)]">{emptyHint}</p>
        )}
      </div>
    </section>
  );
}
