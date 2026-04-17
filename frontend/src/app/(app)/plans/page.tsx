"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { ClipboardList, Dumbbell, Loader2 } from "lucide-react";

interface PlanResponse {
  plan: string;
}

export default function PlansPage() {
  const [mealPlan, setMealPlan] = useState<string | null>(null);
  const [workoutPlan, setWorkoutPlan] = useState<string | null>(null);
  const [mealLoading, setMealLoading] = useState(false);
  const [workoutLoading, setWorkoutLoading] = useState(false);
  const [mealError, setMealError] = useState<string | null>(null);
  const [workoutError, setWorkoutError] = useState<string | null>(null);

  async function generateMeal() {
    setMealError(null);
    setMealLoading(true);
    try {
      const data = await api<PlanResponse>("/api/ai/meal-plan", { method: "POST" });
      setMealPlan(data.plan ?? "");
    } catch (e) {
      setMealError(e instanceof Error ? e.message : "Ошибка генерации");
      setMealPlan(null);
    } finally {
      setMealLoading(false);
    }
  }

  async function generateWorkout() {
    setWorkoutError(null);
    setWorkoutLoading(true);
    try {
      const data = await api<PlanResponse>("/api/ai/workout-plan", { method: "POST" });
      setWorkoutPlan(data.plan ?? "");
    } catch (e) {
      setWorkoutError(e instanceof Error ? e.message : "Ошибка генерации");
      setWorkoutPlan(null);
    } finally {
      setWorkoutLoading(false);
    }
  }

  return (
    <div className="space-y-10 max-w-3xl">
      <div>
        <h1 className="page-title">Планы</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Персональные планы на основе вашего профиля
        </p>
      </div>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ClipboardList className="text-[var(--accent)]" size={22} />
            <h2 className="font-display text-lg font-semibold text-[var(--foreground)]">
              План питания
            </h2>
          </div>
          <button
            type="button"
            onClick={() => void generateMeal()}
            disabled={mealLoading}
            className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 inline-flex items-center gap-2 shadow-[var(--shadow-1)]"
          >
            {mealLoading ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Генерируем…
              </>
            ) : (
              "Сгенерировать"
            )}
          </button>
        </div>
        {mealError && (
          <p className="text-sm text-[var(--destructive)]" role="alert">
            {mealError}
          </p>
        )}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)] min-h-[120px]">
          {mealLoading && !mealPlan ? (
            <p className="text-sm text-[var(--muted-foreground)] flex items-center gap-2">
              <Loader2 className="animate-spin shrink-0" size={16} />
              Генерируем…
            </p>
          ) : mealPlan != null ? (
            <pre className="whitespace-pre-wrap text-sm text-[var(--foreground)] font-[family-name:var(--font-body)] leading-relaxed">
              {mealPlan}
            </pre>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">
              Нажмите «Сгенерировать», чтобы получить план питания.
            </p>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Dumbbell className="text-[var(--success)]" size={22} />
            <h2 className="font-display text-lg font-semibold text-[var(--foreground)]">
              План тренировок
            </h2>
          </div>
          <button
            type="button"
            onClick={() => void generateWorkout()}
            disabled={workoutLoading}
            className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 inline-flex items-center gap-2 shadow-[var(--shadow-1)]"
          >
            {workoutLoading ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Генерируем…
              </>
            ) : (
              "Сгенерировать"
            )}
          </button>
        </div>
        {workoutError && (
          <p className="text-sm text-[var(--destructive)]" role="alert">
            {workoutError}
          </p>
        )}
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)] min-h-[120px]">
          {workoutLoading && !workoutPlan ? (
            <p className="text-sm text-[var(--muted-foreground)] flex items-center gap-2">
              <Loader2 className="animate-spin shrink-0" size={16} />
              Генерируем…
            </p>
          ) : workoutPlan != null ? (
            <pre className="whitespace-pre-wrap text-sm text-[var(--foreground)] font-[family-name:var(--font-body)] leading-relaxed">
              {workoutPlan}
            </pre>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">
              Нажмите «Сгенерировать», чтобы получить план тренировок.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
