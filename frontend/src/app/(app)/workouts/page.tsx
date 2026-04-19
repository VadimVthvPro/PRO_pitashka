"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { WorkoutIcon } from "@/components/workouts/WorkoutIcon";
import { ScrollReveal, Stagger, StaggerItem } from "@/components/motion/ScrollReveal";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { motion, AnimatePresence } from "motion/react";
import { Sticker } from "@/components/hand/Sticker";
import { Highlight } from "@/components/hand/Highlight";
import { Scribble } from "@/components/hand/Scribble";
import { handleActivityResponse, type StreakDTO, type BadgeDTO } from "@/lib/streaks";
import { useI18n } from "@/lib/i18n";

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
  streak?: StreakDTO | null;
  newly_earned_badges?: BadgeDTO[] | null;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0]!;
}

export default function WorkoutsPage() {
  const { t, lang } = useI18n();
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
      setTypesError(e instanceof Error ? e.message : t("workouts_err_types"));
    } finally {
      setTypesLoading(false);
    }
  }, [t]);

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
      setDayError(e instanceof Error ? e.message : t("workouts_err_day"));
    } finally {
      setDayLoading(false);
    }
  }, [date, t]);

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
      setSubmitError(t("workouts_err_duration_long"));
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
      handleActivityResponse(res);
      setTotalsCal(res.total_today_cal);
      setTotalsMin(res.total_today_duration);
      setModalType(null);
      await loadDay();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : t("workouts_err_save_short"));
    } finally {
      setSubmitting(false);
    }
  }

  const loading = typesLoading || dayLoading;

  return (
    <div className="space-y-8">
      <ScrollReveal>
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              {new Date(date + "T12:00:00").toLocaleDateString(lang, {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </p>
            <h1
              className="text-[var(--foreground)]"
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(2.5rem, 1.8rem + 3vw, 4rem)",
                letterSpacing: "-0.03em",
                lineHeight: 0.92,
              }}
            >
              {t("workouts_hero_before")}
              <Highlight color="oklch(72% 0.15 80 / 0.5)">
                <span className="px-1">{t("workouts_hero_em")}</span>
              </Highlight>
            </h1>
          </div>
          <Sticker color="amber" font="appetite" rotate={4} size="md">
            {t("workouts_hero_sub")}
          </Sticker>
        </div>
      </ScrollReveal>

      <ScrollReveal delay={0.05}>
        <div className="card-base card-hover mesh-warm p-6">
          <h2 className="text-xs font-medium uppercase tracking-widest text-[var(--muted-foreground)] mb-4">
            {t("workouts_today_total")}
          </h2>
          {(typesError || dayError) && (
            <p className="text-sm text-[var(--destructive)] mb-2">{typesError || dayError}</p>
          )}
          {loading && !typesError && !dayError && (
            <div className="flex gap-8">
              <div className="skeleton h-12 w-40" />
              <div className="skeleton h-12 w-32" />
            </div>
          )}
          {!loading && totalsCal !== null && totalsMin !== null && (
            <div className="flex flex-wrap gap-10">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
                  {t("workouts_calories_label")}
                </p>
                <p className="display-number text-5xl text-[var(--foreground)]">
                  <AnimatedNumber value={Math.round(totalsCal)} />
                  <span className="text-xl font-medium text-[var(--muted)] ml-2" style={{ fontFamily: "var(--font-body)" }}>
                    {t("kcal")}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
                  {t("workouts_time_label")}
                </p>
                <p className="display-number text-5xl text-[var(--foreground)]">
                  <AnimatedNumber value={totalsMin} />
                  <span className="text-xl font-medium text-[var(--muted)] ml-2" style={{ fontFamily: "var(--font-body)" }}>
                    {t("min")}
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>
      </ScrollReveal>

      {typesLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-[var(--radius-lg)]" />
          ))}
        </div>
      )}
      {!typesLoading && types.length > 0 && (
        <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {types.map((wt) => (
            <StaggerItem key={wt.id}>
              <motion.button
                type="button"
                onClick={() => openModal(wt)}
                whileHover={{ y: -4, scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                transition={{ type: "spring", stiffness: 350, damping: 22 }}
                className="w-full h-full text-left card-base p-5 hover:border-[var(--accent)] hover:shadow-[var(--shadow-2)]"
              >
                <div className="flex items-start gap-4">
                  <div className="shrink-0 w-14 h-14 rounded-[var(--radius)] bg-gradient-to-br from-[var(--color-sand)] to-[var(--color-cream)] flex items-center justify-center text-[var(--accent)]">
                    <WorkoutIcon id={wt.id} size={32} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3
                      className="font-bold text-lg text-[var(--foreground)] leading-tight"
                      style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
                    >
                      {wt.name}
                    </h3>
                    {wt.description ? (
                      <p className="text-xs text-[var(--muted-foreground)] mt-1 line-clamp-2">
                        {wt.description}
                      </p>
                    ) : null}
                    <p className="text-[10px] font-mono text-[var(--muted)] mt-2">
                      {t("workout_coef_short")} {wt.base_coefficient}
                    </p>
                  </div>
                </div>
              </motion.button>
            </StaggerItem>
          ))}
        </Stagger>
      )}

      {!typesLoading && types.length === 0 && !typesError && (
        <div className="flex items-center gap-6 py-8">
          <Scribble
            variant="empty-dumbbell"
            className="w-32 h-20 shrink-0 text-[var(--color-latte)]"
          />
          <p
            className="text-lg text-[var(--muted-foreground)]"
            style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
          >
            {t("workouts_types_loading")}
          </p>
        </div>
      )}

      <AnimatePresence>
        {modalType && (
          <motion.div
            key="workout-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--foreground)]/30 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="workout-modal-title"
          >
            <button
              type="button"
              className="absolute inset-0 cursor-default"
              aria-label={t("common_close")}
              onClick={closeModal}
            />
            <motion.div
              key="workout-sheet"
              initial={{ opacity: 0, y: 32, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 320, damping: 26 }}
              className="relative w-full max-w-md bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-xl)] shadow-[var(--shadow-3)] p-6 z-10"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="shrink-0 w-12 h-12 rounded-[var(--radius)] bg-gradient-to-br from-[var(--color-sand)] to-[var(--color-cream)] flex items-center justify-center text-[var(--accent)]">
                  <WorkoutIcon id={modalType.id} size={28} />
                </div>
                <div>
                  <h2
                    id="workout-modal-title"
                    className="text-2xl font-bold"
                    style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
                  >
                    {modalType.name}
                  </h2>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    {t("workouts_modal_subhint")}
                  </p>
                </div>
              </div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              {t("workouts_modal_duration")}
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
                {t("workouts_modal_cancel")}
              </button>
              <button
                type="button"
                onClick={() => void submitWorkout()}
                disabled={submitting}
                className="flex-1 py-2.5 rounded-[var(--radius)] bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] disabled:opacity-50 active:scale-[0.97] transition-transform"
              >
                {submitting ? t("workouts_modal_saving") : t("workouts_modal_save")}
              </button>
            </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
