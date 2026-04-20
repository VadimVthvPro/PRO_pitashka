"use client";

/**
 * Left-side context rail for the AI chat: shows the user *what the AI sees*
 * before answering — today's intake snapshot + which plans are pinned.
 *
 * The rationale is editorial, not just decorative: the existing chat hides
 * its context window, so users keep asking "почему ты не знаешь сколько я
 * съел" and lose trust. Surfacing the snapshot turns "magic" into "honest
 * personalisation" and aligns with DESIGN_GUIDE.md §0 ("копирайт всегда
 * живой, асимметрия, hand-drawn акцент").
 *
 * On <lg this collapses into a horizontal scroll strip above the conversation
 * (the parent decides; this component just renders content + accepts a
 * `compact` prop for tighter spacing).
 */

import { Icon } from "@iconify/react";

import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { HandDrawnUnderline } from "@/components/hand/HandDrawnUnderline";
import { useI18n } from "@/lib/i18n";

export interface ContextSnapshot {
  calories_in: number;
  calories_burned: number;
  water_glasses: number;
  workout_sessions: number;
  food_items_logged: number;
  active_minutes: number;
}

export type PlanState = "attached" | "available" | "missing";

interface ContextRailProps {
  snapshot: ContextSnapshot | null;
  loading: boolean;
  mealPlan: PlanState;
  workoutPlan: PlanState;
  onToggleMeal: () => void;
  onToggleWorkout: () => void;
  onCreatePlan: (kind: "meal" | "workout") => void;
  compact?: boolean;
}

export function ContextRail({
  snapshot,
  loading,
  mealPlan,
  workoutPlan,
  onToggleMeal,
  onToggleWorkout,
  onCreatePlan,
  compact = false,
}: ContextRailProps) {
  const { t } = useI18n();

  return (
    <aside
      className={[
        "flex flex-col gap-4",
        compact ? "" : "h-full",
      ].join(" ")}
      aria-label={t("ai_rail_aria")}
    >
      <div>
        <div className="relative inline-block">
          <h2 className="font-display text-2xl text-[var(--foreground)]">
            {t("ai_rail_title")}
          </h2>
          <HandDrawnUnderline
            color="var(--accent)"
            strokeWidth={3}
            variant={2}
            className="absolute left-0 -bottom-1 w-full h-2"
          />
        </div>
        <p className="text-xs text-[var(--muted-foreground)] mt-2 leading-relaxed">
          {t("ai_rail_subtitle")}
        </p>
      </div>

      {/* Today snapshot */}
      <div className="card-base p-4">
        <p className="text-[11px] uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
          {t("ai_rail_today")}
        </p>
        {loading ? (
          <RailSnapshotSkeleton />
        ) : snapshot ? (
          <ul className="grid grid-cols-2 gap-3">
            <SnapshotItem
              icon="solar:plate-bold-duotone"
              label={t("ai_rail_kcal_in")}
              value={snapshot.calories_in}
              unit={t("unit_kcal_short")}
            />
            <SnapshotItem
              icon="solar:fire-bold-duotone"
              label={t("ai_rail_kcal_out")}
              value={snapshot.calories_burned}
              unit={t("unit_kcal_short")}
              tone="warm"
            />
            <SnapshotItem
              icon="solar:cup-bold-duotone"
              label={t("ai_rail_water")}
              value={snapshot.water_glasses}
              unit={t("unit_glass_short")}
            />
            <SnapshotItem
              icon="solar:dumbbell-large-bold-duotone"
              label={t("ai_rail_workouts")}
              value={snapshot.workout_sessions}
              unit={t("unit_session_short")}
            />
          </ul>
        ) : null}
      </div>

      {/* Plans */}
      <div className="space-y-2">
        <p className="text-[11px] uppercase tracking-wider text-[var(--muted-foreground)] px-1">
          {t("ai_rail_plans")}
        </p>
        <PlanPillRow
          icon="solar:plate-bold-duotone"
          label={t("ai_attach_meal_plan")}
          state={mealPlan}
          onAttach={onToggleMeal}
          onCreate={() => onCreatePlan("meal")}
        />
        <PlanPillRow
          icon="solar:dumbbell-large-bold-duotone"
          label={t("ai_attach_workout_plan")}
          state={workoutPlan}
          onAttach={onToggleWorkout}
          onCreate={() => onCreatePlan("workout")}
        />
      </div>
    </aside>
  );
}

function SnapshotItem({
  icon,
  label,
  value,
  unit,
  tone = "neutral",
}: {
  icon: string;
  label: string;
  value: number;
  unit: string;
  tone?: "neutral" | "warm";
}) {
  return (
    <li className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
        <Icon
          icon={icon}
          width={14}
          className={tone === "warm" ? "text-[var(--warning)]" : ""}
        />
        <span className="text-[11px] uppercase tracking-wide">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="display-number text-xl">
          <AnimatedNumber value={value} />
        </span>
        <span className="text-[11px] text-[var(--muted-foreground)]">{unit}</span>
      </div>
    </li>
  );
}

function RailSnapshotSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <div className="h-2.5 w-16 rounded-full bg-[var(--input-bg)] animate-pulse" />
          <div className="h-5 w-12 rounded bg-[var(--input-bg)] animate-pulse" />
        </div>
      ))}
    </div>
  );
}

function PlanPillRow({
  icon,
  label,
  state,
  onAttach,
  onCreate,
}: {
  icon: string;
  label: string;
  state: PlanState;
  onAttach: () => void;
  onCreate: () => void;
}) {
  const { t } = useI18n();
  if (state === "missing") {
    return (
      <button
        type="button"
        onClick={onCreate}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-[var(--radius)] border border-dashed border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--card)] transition-colors text-left group"
      >
        <span className="flex items-center gap-2 min-w-0">
          <Icon icon={icon} width={18} className="text-[var(--muted-foreground)]" />
          <span className="flex flex-col min-w-0">
            <span className="text-sm truncate">{label}</span>
            <span className="text-[11px] text-[var(--muted-foreground)]">
              {t("ai_rail_plan_missing")}
            </span>
          </span>
        </span>
        <span className="text-xs text-[var(--accent)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {t("ai_rail_plan_create")}
        </span>
      </button>
    );
  }
  const attached = state === "attached";
  return (
    <button
      type="button"
      onClick={onAttach}
      className={[
        "w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-[var(--radius)] border transition-colors text-left",
        attached
          ? "bg-[var(--accent)]/10 border-[var(--accent)] text-[var(--foreground)]"
          : "bg-[var(--card)] border-[var(--border)] hover:border-[var(--accent)]/50",
      ].join(" ")}
      aria-pressed={attached}
    >
      <span className="flex items-center gap-2 min-w-0">
        <Icon
          icon={icon}
          width={18}
          className={attached ? "text-[var(--accent)]" : "text-[var(--muted-foreground)]"}
        />
        <span className="flex flex-col min-w-0">
          <span className="text-sm truncate">{label}</span>
          <span className="text-[11px] text-[var(--muted-foreground)]">
            {attached ? t("ai_rail_plan_attached") : t("ai_rail_plan_attach_hint")}
          </span>
        </span>
      </span>
      <Icon
        icon={attached ? "solar:check-circle-bold" : "solar:add-circle-line-duotone"}
        width={20}
        className={attached ? "text-[var(--accent)] shrink-0" : "text-[var(--muted-foreground)] shrink-0"}
      />
    </button>
  );
}
