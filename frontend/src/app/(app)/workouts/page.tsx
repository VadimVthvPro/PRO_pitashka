"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

interface WorkoutType {
  id: number;
  name: string;
  emoji: string;
  description: string;
  base_coefficient: number;
}

interface WorkoutsDayResponse {
  total_calories: number;
  items: { tren_time: number }[];
}

interface WorkoutSaveResponse {
  training_name: string;
  duration: number;
  calories: number;
  total_today_cal: number;
  total_today_duration: number;
  error?: string;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0]!;
}

export default function WorkoutsPage() {
  const [date] = useState(todayISO);

  const [types, setTypes] = useState<WorkoutType[]>([]);
  const [typesLoading, setTypesLoading] = useState(true);
  const [typesError, setTypesError] = useState("");

  const [dayLoading, setDayLoading] = useState(true);
  const [dayError, setDayError] = useState("");

  const [totalsCal, setTotalsCal] = useState<number | null>(null);
  const [totalsMin, setTotalsMin] = useState<number | null>(null);

  const [modalType, setModalType] = useState<WorkoutType | null>(null);
  const [durationStr, setDurationStr] = useState("30");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const loadTypes = useCallback(async () => {
    setTypesError("");
    setTypesLoading(true);
    try {
      const list = await api<WorkoutType[]>("/api/workouts/types?lang=ru");
      setTypes(list);
    } catch (e) {
      setTypes([]);
      setTypesError(e instanceof Error ? e.message : "Не удалось загрузить типы тренировок");
    } finally {
      setTypesLoading(false);
    }
  }, []);

  const loadDay = useCallback(async () => {
    setDayError("");
    setDayLoading(true);
    try {
      const d = await api<WorkoutsDayResponse>(
        `/api/workouts?date=${encodeURIComponent(date)}`,
      );
      const mins = d.items.reduce((s, it) => s + (it.tren_time || 0), 0);
      setTotalsCal(d.total_calories);
      setTotalsMin(mins);
    } catch (e) {
      setTotalsCal(null);
      setTotalsMin(null);
      setDayError(e instanceof Error ? e.message : "Не удалось загрузить тренировки");
    } finally {
      setDayLoading(false);
    }
  }, [date]);

  useEffect(() => {
    void loadTypes();
  }, [loadTypes]);

  useEffect(() => {
    void loadDay();
  }, [loadDay]);

  function openModal(t: WorkoutType) {
    setModalType(t);
    setDurationStr("30");
    setSubmitError("");
  }

  function closeModal() {
    if (submitting) return;
    setModalType(null);
  }

  async function submitWorkout() {
    if (!modalType) return;
    const duration = parseInt(durationStr, 10);
    if (Number.isNaN(duration) || duration < 1 || duration > 600) {
      setSubmitError("Введите длительность от 1 до 600 минут");
      return;
    }
    setSubmitError("");
    setSubmitting(true);
    try {
      const res = await api<WorkoutSaveResponse>("/api/workouts", {
        method: "POST",
        body: JSON.stringify({
          training_type_id: modalType.id,
          duration_minutes: duration,
          workout_date: date,
        }),
      });
      if (res.error) {
        setSubmitError(res.error);
        return;
      }
      setTotalsCal(res.total_today_cal);
      setTotalsMin(res.total_today_duration);
      setModalType(null);
      await loadDay();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setSubmitting(false);
    }
  }

  const loading = typesLoading || dayLoading;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">Тренировки</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {new Date(date + "T12:00:00").toLocaleDateString("ru-RU", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </div>

      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
          Итого за сегодня
        </h2>
        {(typesError || dayError) && (
          <p className="text-sm text-[var(--destructive)] mb-2">{typesError || dayError}</p>
        )}
        {loading && !typesError && !dayError && (
          <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
        )}
        {!loading && totalsCal !== null && totalsMin !== null && (
          <div className="flex flex-wrap gap-8">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                Калории
              </p>
              <p className="font-mono text-3xl font-bold text-[var(--foreground)]">
                {Math.round(totalsCal)}{" "}
                <span className="text-lg font-medium text-[var(--muted)]">ккал</span>
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                Время
              </p>
              <p className="font-mono text-3xl font-bold text-[var(--foreground)]">
                {totalsMin}{" "}
                <span className="text-lg font-medium text-[var(--muted)]">мин</span>
              </p>
            </div>
          </div>
        )}
      </div>

      {typesLoading && (
        <p className="text-sm text-[var(--muted-foreground)]">Загрузка типов…</p>
      )}
      {!typesLoading && types.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {types.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => openModal(t)}
              className="text-left bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)] hover:border-[var(--accent)] hover:shadow-[var(--shadow-2)] transition-all active:scale-[0.99]"
            >
              <div className="flex items-start gap-3">
                <span className="text-3xl leading-none" aria-hidden>
                  {t.emoji}
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="font-display font-semibold text-[var(--foreground)]">
                    {t.name}
                  </h3>
                  {t.description ? (
                    <p className="text-xs text-[var(--muted-foreground)] mt-1 line-clamp-3">
                      {t.description}
                    </p>
                  ) : null}
                  <p className="text-[10px] font-mono text-[var(--muted)] mt-2">
                    коэф. {t.base_coefficient}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {!typesLoading && types.length === 0 && !typesError && (
        <p className="text-sm text-[var(--muted-foreground)]">Нет доступных типов тренировок</p>
      )}

      {modalType && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--foreground)]/20 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="workout-modal-title"
        >
          <button
            type="button"
            className="absolute inset-0 cursor-default"
            aria-label="Закрыть"
            onClick={closeModal}
          />
          <div className="relative w-full max-w-md bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] shadow-[var(--shadow-2)] p-6 z-10">
            <h2 id="workout-modal-title" className="font-display text-lg font-bold mb-1">
              {modalType.emoji} {modalType.name}
            </h2>
            <p className="text-xs text-[var(--muted-foreground)] mb-4">
              Укажите длительность тренировки в минутах
            </p>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              Длительность (мин)
            </label>
            <input
              type="number"
              min={1}
              max={600}
              value={durationStr}
              onChange={(e) => setDurationStr(e.target.value)}
              className="w-full px-4 py-3 mb-4 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] font-mono text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15"
            />
            {submitError && (
              <p className="text-sm text-[var(--destructive)] mb-4">{submitError}</p>
            )}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={closeModal}
                disabled={submitting}
                className="flex-1 py-2.5 rounded-[var(--radius)] border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--color-sand)]/50 disabled:opacity-50"
              >
                Отмена
              </button>
              <button
                type="button"
                onClick={() => void submitWorkout()}
                disabled={submitting}
                className="flex-1 py-2.5 rounded-[var(--radius)] bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] disabled:opacity-50"
              >
                {submitting ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
