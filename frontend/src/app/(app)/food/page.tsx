"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { api, apiUploadWithProgress } from "@/lib/api";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";
import { Sticker } from "@/components/hand/Sticker";
import { Scribble } from "@/components/hand/Scribble";
import { Highlight } from "@/components/hand/Highlight";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { handleActivityResponse } from "@/lib/streaks";
import { useI18n } from "@/lib/i18n";

type Tab = "photo" | "manual" | "repeat";

interface FoodItem {
  id?: number;
  name_of_food: string;
  b: number;
  g: number;
  u: number;
  cal: number;
  photo_url?: string | null;
}

interface FavoriteItem {
  name: string;
  times: number;
  b: number;
  g: number;
  u: number;
  cal: number;
  last_date: string;
}

interface LastDayResponse {
  date: string | null;
  items: FoodItem[];
  totals: {
    total_cal: number;
    total_protein: number;
    total_fat: number;
    total_carbs: number;
  } | null;
}

interface FoodDayResponse {
  items: FoodItem[];
  totals: {
    total_cal: number;
    total_protein: number;
    total_fat: number;
    total_carbs: number;
  };
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0]!;
}

function hasErrorPayload(d: unknown): d is { error: string } {
  return typeof d === "object" && d !== null && "error" in d && typeof (d as { error: unknown }).error === "string";
}

export default function FoodPage() {
  const { t, lang } = useI18n();
  const [tab, setTab] = useState<Tab>("photo");
  const [date] = useState(todayISO);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get("tab");
    if (tabParam === "repeat" || tabParam === "manual" || tabParam === "photo") {
      setTab(tabParam);
    }
  }, []);

  const [foodDay, setFoodDay] = useState<FoodDayResponse | null>(null);
  const [loadingDay, setLoadingDay] = useState(true);
  const [dayError, setDayError] = useState("");

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoDragging, setPhotoDragging] = useState(false);
  const [photoSubmitting, setPhotoSubmitting] = useState(false);
  const [photoPhase, setPhotoPhase] = useState<"idle" | "uploading" | "analyzing">("idle");
  const [photoProgress, setPhotoProgress] = useState(0);
  const [photoError, setPhotoError] = useState("");
  const [lastRecognized, setLastRecognized] = useState<{ items: FoodItem[]; photo_url: string | null } | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const [manualFoods, setManualFoods] = useState("");
  const [manualGrams, setManualGrams] = useState("");
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualError, setManualError] = useState("");

  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [lastDay, setLastDay] = useState<LastDayResponse | null>(null);
  const [repeatLoading, setRepeatLoading] = useState(false);
  const [repeatSubmitting, setRepeatSubmitting] = useState(false);
  const [repeatError, setRepeatError] = useState("");

  const loadDay = useCallback(async () => {
    setDayError("");
    setLoadingDay(true);
    try {
      const d = await api<FoodDayResponse>(`/api/food?date=${encodeURIComponent(date)}`);
      setFoodDay(d);
    } catch (e) {
      setFoodDay(null);
      setDayError(e instanceof Error ? e.message : t("food_err_load_data"));
    } finally {
      setLoadingDay(false);
    }
  }, [date, t]);

  useEffect(() => {
    void loadDay();
  }, [loadDay]);

  const loadRepeatData = useCallback(async () => {
    setRepeatError("");
    setRepeatLoading(true);
    try {
      const [fav, last] = await Promise.all([
        api<{ items: FavoriteItem[] }>("/api/food/favorites?limit=12"),
        api<LastDayResponse>("/api/food/last-day"),
      ]);
      setFavorites(fav.items);
      setLastDay(last);
    } catch (e) {
      setRepeatError(e instanceof Error ? e.message : t("food_err_load_data"));
    } finally {
      setRepeatLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (tab === "repeat" && favorites.length === 0 && !lastDay && !repeatLoading) {
      void loadRepeatData();
    }
  }, [tab, favorites.length, lastDay, repeatLoading, loadRepeatData]);

  async function repeatDay(source: "yesterday" | "last_meal") {
    setRepeatError("");
    setRepeatSubmitting(true);
    try {
      const res = await api<unknown>(`/api/food/repeat?source=${source}`, {
        method: "POST",
      });
      handleActivityResponse(res as Parameters<typeof handleActivityResponse>[0]);
      await loadDay();
      await loadRepeatData();
    } catch (e) {
      setRepeatError(e instanceof Error ? e.message : t("food_err_copy"));
    } finally {
      setRepeatSubmitting(false);
    }
  }

  async function addFavorite(fav: FavoriteItem, grams: number) {
    setRepeatError("");
    setRepeatSubmitting(true);
    try {
      const res = await api<unknown>("/api/food", {
        method: "POST",
        body: JSON.stringify({
          foods: [fav.name],
          grams: [grams],
          food_date: date,
        }),
      });
      handleActivityResponse(res as Parameters<typeof handleActivityResponse>[0]);
      await loadDay();
    } catch (e) {
      setRepeatError(e instanceof Error ? e.message : t("food_err_add"));
    } finally {
      setRepeatSubmitting(false);
    }
  }

  function onPhotoDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setPhotoDragging(true);
  }

  function onPhotoDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setPhotoDragging(false);
  }

  function onPhotoDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setPhotoDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) pickPhoto(f);
  }

  // Один вход для выбора фото: drag-n-drop, <input type="file">, вставка из буфера.
  // Сразу рвём предыдущий object URL (иначе утечка) и создаём новый для превью.
  function pickPhoto(f: File | null) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setPhotoFile(f);
    if (f) {
      const url = URL.createObjectURL(f);
      previewUrlRef.current = url;
      setPhotoPreview(url);
    } else {
      setPhotoPreview(null);
    }
  }

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
    };
  }, []);

  async function submitPhoto() {
    if (!photoFile) {
      setPhotoError(t("food_err_pick_photo"));
      return;
    }
    setPhotoError("");
    setPhotoSubmitting(true);
    setPhotoPhase("uploading");
    setPhotoProgress(0);
    try {
      const fd = new FormData();
      fd.append("file", photoFile);
      const res = await apiUploadWithProgress<{
        items: FoodItem[];
        photo_url?: string | null;
        error?: string;
      }>(
        `/api/food/photo?food_date=${encodeURIComponent(date)}`,
        fd,
        {
          onProgress: (pct) => {
            setPhotoProgress(pct);
            // Достигли 100% загрузки — сервер теперь разговаривает с Gemini,
            // это может занять 5–15 с. Переходим в индетерминированный режим,
            // чтобы прогресс-бар не «лгал» остановкой на 100%.
            if (pct >= 100) setPhotoPhase("analyzing");
          },
        },
      );
      if (hasErrorPayload(res)) {
        setPhotoError(res.error);
        return;
      }
      handleActivityResponse(res as Parameters<typeof handleActivityResponse>[0]);
      setLastRecognized({
        items: Array.isArray(res.items) ? res.items : [],
        photo_url: res.photo_url ?? null,
      });
      // Сбрасываем локальный файл/превью — сервер уже держит нормализованную
      // копию, и мы её подхватим из /api/food при перезагрузке ленты.
      pickPhoto(null);
      await loadDay();
    } catch (e) {
      setPhotoError(e instanceof Error ? e.message : t("food_err_upload"));
    } finally {
      setPhotoSubmitting(false);
      setPhotoPhase("idle");
      setPhotoProgress(0);
    }
  }

  // Группируем позиции дня по одной «тарелке» (общий photo_url) — чтобы
  // одно фото не рендерилось 4 раза подряд для салата из 4 ингредиентов.
  const groupedDay = useMemo(() => {
    if (!foodDay) return [] as Array<{ key: string; photo_url: string | null; items: FoodItem[] }>;
    const out: Array<{ key: string; photo_url: string | null; items: FoodItem[] }> = [];
    let current: { key: string; photo_url: string | null; items: FoodItem[] } | null = null;
    foodDay.items.forEach((it, idx) => {
      const url = it.photo_url ?? null;
      // Склеиваем только последовательные записи с одним и тем же URL —
      // чтобы ручные вставки не «прилипали» к старым тарелкам.
      if (current && current.photo_url === url && url !== null) {
        current.items.push(it);
      } else {
        current = { key: `${url ?? "manual"}-${idx}`, photo_url: url, items: [it] };
        out.push(current);
      }
    });
    return out;
  }, [foodDay]);

  // Промпт в AI-чат для «спросить про мой день» — бэкенд сам добавит
  // сегодняшний срез КБЖУ как system-контекст, нам нужен только вопрос.
  const dayQuestionPrefill = useMemo(() => {
    if (!foodDay || foodDay.items.length === 0) return t("food_ai_prefill_empty");
    return t("food_ai_prefill_today", { n: foodDay.items.length });
  }, [foodDay, t]);

  async function submitManual() {
    const foods = manualFoods
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const grams = manualGrams
      .split(",")
      .map((s) => parseFloat(s.trim()))
      .filter((n) => !Number.isNaN(n));

    if (foods.length === 0) {
      setManualError(t("food_err_at_least_one"));
      return;
    }
    if (foods.length !== grams.length) {
      setManualError(t("food_err_dish_gram_match"));
      return;
    }

    setManualError("");
    setManualSubmitting(true);
    try {
      const res = await api<unknown>("/api/food", {
        method: "POST",
        body: JSON.stringify({
          foods,
          grams,
          food_date: date,
        }),
      });
      if (hasErrorPayload(res)) {
        setManualError(res.error);
        return;
      }
      handleActivityResponse(res as Parameters<typeof handleActivityResponse>[0]);
      setManualFoods("");
      setManualGrams("");
      await loadDay();
    } catch (e) {
      setManualError(e instanceof Error ? e.message : t("food_err_save_short"));
    } finally {
      setManualSubmitting(false);
    }
  }

  return (
    <div className="space-y-8 relative">
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
              {t("food_hero_what")}
              <Highlight color="oklch(72% 0.15 80 / 0.45)">{t("food_hero_put")}</Highlight>
              <br />
              {t("food_hero_plate")}
            </h1>
          </div>
          <Sticker color="cream" font="arkhip" rotate={-4} size="md">
            {t("food_hero_sub")}
          </Sticker>
        </div>
      </ScrollReveal>

      <div className="flex flex-wrap gap-2 p-1 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius-lg)] w-fit relative">
        {(
          [
            ["photo", "food_tab_snap", "solar:camera-bold-duotone"],
            ["manual", "food_tab_handwrite", "solar:pen-bold-duotone"],
            ["repeat", "food_tab_yesterday", "solar:refresh-circle-bold-duotone"],
          ] as const
        ).map(([id, labelKey, icon]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`relative flex items-center gap-2 px-4 min-h-11 rounded-[var(--radius)] text-sm font-medium transition-colors touch-manipulation ${
              tab === id
                ? "text-[var(--foreground)]"
                : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {tab === id && (
              <motion.span
                layoutId="food-tab-pill"
                className="absolute inset-0 bg-[var(--card)] rounded-[var(--radius)] shadow-[var(--shadow-1)] -z-10"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <Icon icon={icon} width={16} />
            {t(labelKey)}
          </button>
        ))}
      </div>

      {tab === "photo" && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-4 sm:p-6 shadow-[var(--shadow-1)] space-y-4">
          {/* Если файл не выбран — показываем dropzone как раньше.
              Если выбран — показываем crisp-превью 16:9 + кнопки «другое фото/удалить»,
              а при submit поверх превью наплывает прогресс-оверлей. */}
          {!photoPreview ? (
            <div
              role="presentation"
              onDragOver={onPhotoDragOver}
              onDragLeave={onPhotoDragLeave}
              onDrop={onPhotoDrop}
              className={`border-2 border-dashed rounded-[var(--radius-lg)] p-8 sm:p-10 text-center transition-colors ${
                photoDragging
                  ? "border-[var(--accent)] bg-[var(--color-sand)]/40"
                  : "border-[var(--border)] bg-[var(--input-bg)]"
              }`}
            >
              <Icon
                icon="solar:camera-add-bold-duotone"
                width={44}
                className="mx-auto mb-3 text-[var(--accent)]"
                aria-hidden
              />
              <p className="text-sm text-[var(--muted)] mb-3 max-w-[42ch] mx-auto">
                {t("food_dropzone_extended")}
              </p>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                id="food-photo-input"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  pickPhoto(f ?? null);
                  e.target.value = "";
                }}
              />
              <label
                htmlFor="food-photo-input"
                className="inline-flex items-center justify-center gap-2 px-5 min-h-11 text-sm font-semibold rounded-[var(--radius)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] cursor-pointer transition-colors touch-manipulation"
              >
                <Icon icon="solar:gallery-add-bold-duotone" width={18} />
                {t("food_pick_file")}
              </label>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--input-bg)] aspect-[4/3] sm:aspect-[16/9]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photoPreview}
                  alt={t("food_photo_preview_alt")}
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <AnimatePresence>
                  {photoSubmitting && (
                    <motion.div
                      key="overlay"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="absolute inset-0 bg-[color-mix(in_oklab,var(--foreground)_45%,transparent)] backdrop-blur-sm flex flex-col items-center justify-center gap-3 p-4 text-center"
                    >
                      <div className="w-12 h-12 rounded-full border-4 border-white/35 border-t-white animate-spin" aria-hidden />
                      <p className="text-sm font-semibold text-white">
                        {photoPhase === "uploading"
                          ? t("food_photo_uploading", { pct: photoProgress })
                          : t("food_photo_analyzing")}
                      </p>
                      <div className="w-full max-w-[260px] h-1.5 rounded-full bg-white/25 overflow-hidden">
                        {photoPhase === "uploading" ? (
                          <motion.div
                            className="h-full bg-white"
                            initial={false}
                            animate={{ width: `${photoProgress}%` }}
                            transition={{ type: "tween", duration: 0.18 }}
                          />
                        ) : (
                          <motion.div
                            className="h-full w-1/2 bg-white"
                            animate={{ x: ["-100%", "200%"] }}
                            transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
                          />
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <div className="flex flex-wrap gap-2">
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  id="food-photo-input-replace"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    pickPhoto(f ?? null);
                    e.target.value = "";
                  }}
                />
                <label
                  htmlFor="food-photo-input-replace"
                  className={`inline-flex items-center gap-1.5 px-4 min-h-11 text-sm font-medium rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] text-[var(--foreground)] hover:border-[var(--accent)]/40 cursor-pointer transition touch-manipulation ${photoSubmitting ? "opacity-50 pointer-events-none" : ""}`}
                >
                  <Icon icon="solar:gallery-edit-bold-duotone" width={16} />
                  {t("food_photo_replace")}
                </label>
                <button
                  type="button"
                  onClick={() => pickPhoto(null)}
                  disabled={photoSubmitting}
                  className="inline-flex items-center gap-1.5 px-4 min-h-11 text-sm font-medium rounded-[var(--radius)] border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--destructive)] hover:border-[var(--destructive)]/40 disabled:opacity-50 transition touch-manipulation"
                >
                  <Icon icon="solar:trash-bin-minimalistic-bold-duotone" width={16} />
                  {t("food_photo_remove")}
                </button>
                {photoFile && (
                  <span className="inline-flex items-center gap-1.5 px-3 min-h-11 text-[11px] text-[var(--muted-foreground)] font-mono rounded-[var(--radius)] bg-[var(--input-bg)] truncate max-w-[260px]">
                    {photoFile.name}
                  </span>
                )}
              </div>
            </div>
          )}

          {photoError && (
            <p className="text-sm text-[var(--destructive)]">{photoError}</p>
          )}
          <button
            type="button"
            onClick={() => void submitPhoto()}
            disabled={photoSubmitting || !photoFile}
            className="w-full py-3 min-h-[48px] rounded-[var(--radius)] bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all inline-flex items-center justify-center gap-2"
          >
            {photoSubmitting ? (
              <>
                <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" aria-hidden />
                {photoPhase === "uploading"
                  ? t("food_photo_uploading", { pct: photoProgress })
                  : t("food_photo_analyzing")}
              </>
            ) : (
              <>
                <Icon icon="solar:chef-hat-bold-duotone" width={18} />
                {t("food_photo_save")}
              </>
            )}
          </button>

          {lastRecognized && lastRecognized.items.length > 0 && !photoSubmitting && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-[var(--radius)] border border-[var(--success)]/30 bg-[var(--success)]/10 p-3 text-sm"
            >
              <p className="font-medium text-[var(--success)] flex items-center gap-1.5">
                <Icon icon="solar:check-circle-bold-duotone" width={18} />
                {t("food_photo_added", { n: lastRecognized.items.length })}
              </p>
              <p className="text-[var(--muted-foreground)] mt-1 text-xs">
                {lastRecognized.items.map((it) => it.name_of_food).join(", ")}
              </p>
            </motion.div>
          )}
        </div>
      )}

      {tab === "manual" && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)] space-y-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              {t("food_manual_dishes_label")}
            </label>
            <textarea
              value={manualFoods}
              onChange={(e) => setManualFoods(e.target.value)}
              rows={3}
              placeholder={t("food_manual_dishes_placeholder")}
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 resize-y min-h-[88px]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              {t("food_manual_grams_ordered")}
            </label>
            <textarea
              value={manualGrams}
              onChange={(e) => setManualGrams(e.target.value)}
              rows={2}
              placeholder="150, 100, 200"
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 resize-y min-h-[72px] font-mono"
            />
          </div>
          {manualError && (
            <p className="text-sm text-[var(--destructive)]">{manualError}</p>
          )}
          <button
            type="button"
            onClick={() => void submitManual()}
            disabled={manualSubmitting}
            className="w-full py-3 rounded-[var(--radius)] bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {manualSubmitting ? t("food_manual_submitting") : t("food_manual_add")}
          </button>
        </div>
      )}

      {tab === "repeat" && (
        <div className="space-y-5">
          {repeatLoading && (
            <div className="card-base p-6">
              <div className="skeleton h-16 w-full" />
            </div>
          )}
          {repeatError && (
            <p className="text-sm text-[var(--destructive)]">{repeatError}</p>
          )}

          {!repeatLoading && lastDay?.date && lastDay.items.length > 0 && (
            <div className="card-base p-6 relative overflow-hidden">
              <div
                className="pointer-events-none absolute -top-8 -right-8 w-40 h-40 rounded-full blur-3xl opacity-20"
                style={{ background: "var(--accent)" }}
                aria-hidden
              />
              <div className="relative flex flex-wrap items-start justify-between gap-4 mb-4">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                    {t("food_repeat_last_day_title")}
                  </p>
                  <h3
                    className="text-2xl mt-1"
                    style={{
                      fontFamily: "var(--font-display)",
                      letterSpacing: "-0.02em",
                    }}
                  >
                    {new Date(lastDay.date + "T12:00:00").toLocaleDateString(
                      lang,
                      { weekday: "long", day: "numeric", month: "long" },
                    )}
                  </h3>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    {t("food_today_dishes", { n: lastDay.items.length })} ·{" "}
                    {Math.round(lastDay.totals?.total_cal ?? 0)} {t("kcal")} ·{" "}
                    {Math.round(lastDay.totals?.total_protein ?? 0)}/
                    {Math.round(lastDay.totals?.total_fat ?? 0)}/
                    {Math.round(lastDay.totals?.total_carbs ?? 0)} {t("food_macros_abbr")}
                  </p>
                </div>
                <Sticker color="sage" font="appetite" rotate={3}>
                  {t("food_repeat_one_click")}
                </Sticker>
              </div>

              <div className="relative space-y-1.5 mb-5">
                {lastDay.items.slice(0, 6).map((it, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm py-1 border-b border-dashed border-[var(--border)] last:border-0"
                  >
                    <span className="truncate">{it.name_of_food}</span>
                    <span className="font-mono text-xs tabular-nums text-[var(--muted)]">
                      {Math.round(it.cal)} {t("kcal")}
                    </span>
                  </div>
                ))}
                {lastDay.items.length > 6 && (
                  <p className="text-xs text-[var(--muted-foreground)] pt-1">
                    {t("food_more_count", { n: lastDay.items.length - 6 })}
                  </p>
                )}
              </div>

              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={() => void repeatDay("last_meal")}
                disabled={repeatSubmitting}
                className="w-full py-3 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] disabled:opacity-50 shadow-[var(--shadow-accent)] flex items-center justify-center gap-2"
              >
                <Icon icon="solar:refresh-circle-bold-duotone" width={20} />
                {repeatSubmitting ? t("food_repeat_copying") : t("food_repeat_copy_btn")}
              </motion.button>
            </div>
          )}

          {!repeatLoading && favorites.length > 0 && (
            <div className="card-base p-6">
              <div className="flex items-center justify-between mb-4">
                <h3
                  className="text-2xl"
                  style={{
                    fontFamily: "var(--font-display)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  {t("food_favorites_title")}
                </h3>
                <Sticker color="amber" size="sm" rotate={-3} font="arkhip">
                  {t("food_favorites_top")} {favorites.length}
                </Sticker>
              </div>
              <p className="text-sm text-[var(--muted)] mb-4">
                {t("food_favorites_hint_long")}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {favorites.map((f, i) => {
                  const avgGrams = 100;
                  return (
                    <motion.button
                      key={`${f.name}-${i}`}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => void addFavorite(f, avgGrams)}
                      disabled={repeatSubmitting}
                      className="flex items-center justify-between gap-3 px-4 py-3 rounded-[var(--radius)] bg-[var(--input-bg)] border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--card)] disabled:opacity-50 transition-all text-left"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{f.name}</p>
                        <p className="text-[11px] text-[var(--muted-foreground)] font-mono tabular-nums">
                          {Math.round(Number(f.cal))} {t("kcal")} · ×{f.times}
                        </p>
                      </div>
                      <Icon
                        icon="solar:add-circle-bold-duotone"
                        width={24}
                        className="shrink-0 text-[var(--accent)]"
                      />
                    </motion.button>
                  );
                })}
              </div>
            </div>
          )}

          {!repeatLoading && favorites.length === 0 && !lastDay?.date && (
            <div className="flex items-center gap-6 py-8">
              <Scribble
                variant="empty-plate"
                className="w-28 h-28 shrink-0 text-[var(--color-latte)]"
              />
              <div>
                <p
                  className="text-xl"
                  style={{
                    fontFamily: "var(--font-display)",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {t("food_favorites_empty_title")}
                </p>
                <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[46ch]">
                  {t("food_repeat_empty_long")}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      <ScrollReveal>
      <div className="card-base p-6">
        <div className="flex items-center justify-between mb-5">
          <h2
            className="text-2xl text-[var(--foreground)]"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.02em",
            }}
          >
            {t("food_today_title")}
          </h2>
          {foodDay && foodDay.items.length > 0 && (
            <Sticker color="sage" size="sm" rotate={3}>
              {t("food_today_dishes", { n: foodDay.items.length })}
            </Sticker>
          )}
        </div>
        {dayError && (
          <p className="text-sm text-[var(--destructive)] mb-4">{dayError}</p>
        )}
        {loadingDay && !dayError && (
          <div className="space-y-3">
            <div className="skeleton h-20 w-full rounded-[var(--radius)]" />
            <div className="skeleton h-10 w-full rounded-[var(--radius)]" />
          </div>
        )}
        {!loadingDay && foodDay && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                [t("food_macro_kcal"), foodDay.totals.total_cal, "", "var(--accent)"],
                [t("protein"), foodDay.totals.total_protein, t("grams_short"), "var(--success)"],
                [t("fat"), foodDay.totals.total_fat, t("grams_short"), "var(--warning)"],
                [t("carbs"), foodDay.totals.total_carbs, t("grams_short"), "var(--accent)"],
              ].map(([label, val, unit, color]) => (
                <div
                  key={String(label)}
                  className="relative rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2.5 overflow-hidden"
                >
                  <div
                    className="absolute top-0 right-0 w-1 h-full"
                    style={{ background: String(color) }}
                    aria-hidden
                  />
                  <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                    {label}
                  </p>
                  <p
                    className="display-number text-2xl text-[var(--foreground)] tabular-nums"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {Math.round(Number(val))}
                    {unit && (
                      <span className="text-sm font-normal text-[var(--muted)] ml-0.5" style={{ fontFamily: "var(--font-body)" }}>
                        {unit}
                      </span>
                    )}
                  </p>
                </div>
              ))}
            </div>
            {foodDay.items.length === 0 ? (
              <div className="flex flex-col md:flex-row items-start md:items-center gap-6 py-4">
                <Scribble
                  variant="empty-plate"
                  className="w-28 h-28 shrink-0 text-[var(--color-latte)]"
                />
                <div>
                  <p
                    className="text-xl"
                    style={{
                      fontFamily: "var(--font-display)",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {t("food_empty_meals_title")}
                  </p>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1.5 max-w-[46ch]">
                    {t("food_empty_sub_note")}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {groupedDay.map((group, gi) => (
                  <div
                    key={group.key}
                    className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--input-bg)] overflow-hidden"
                  >
                    {group.photo_url && (
                      <div className="relative aspect-[16/9] sm:aspect-[21/9] w-full bg-[var(--card)] overflow-hidden">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={group.photo_url}
                          alt={group.items[0]?.name_of_food ?? ""}
                          className="absolute inset-0 w-full h-full object-cover"
                          loading="lazy"
                        />
                        <div
                          className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/65 via-black/20 to-transparent pointer-events-none"
                          aria-hidden
                        />
                        <Sticker
                          color="cream"
                          size="sm"
                          rotate={-4}
                          className="absolute top-3 left-3"
                        >
                          <Icon icon="solar:camera-bold-duotone" width={14} className="inline mr-1" />
                          {t("food_photo_badge")}
                        </Sticker>
                      </div>
                    )}
                    <div className="divide-y divide-[var(--border)]">
                      {group.items.map((f, i) => (
                        <div
                          key={`${gi}-${f.id ?? i}`}
                          className="flex items-center gap-3 px-3 sm:px-4 py-2.5"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-[var(--foreground)] truncate">
                              {f.name_of_food}
                            </p>
                            <p className="text-[11px] text-[var(--muted-foreground)] font-mono tabular-nums mt-0.5">
                              {t("food_macro_protein")} {Math.round(f.b)} ·{" "}
                              {t("food_macro_fat")} {Math.round(f.g)} ·{" "}
                              {t("food_macro_carbs")} {Math.round(f.u)}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="font-mono tabular-nums text-sm font-semibold text-[var(--foreground)]">
                              {Math.round(f.cal)}
                            </p>
                            <p className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                              {t("food_macro_kcal")}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
      </ScrollReveal>

      {/* Floating «спросить AI о питании».
          Редиректим в /ai-chat с `prefill`, чтобы вопрос подставился в инпут;
          сегодняшний КБЖУ-срез добавляется бэкендом через system-контекст. */}
      <Link
        href={`/ai-chat?prefill=${encodeURIComponent(dayQuestionPrefill)}&context=food`}
        aria-label={t("food_ai_ask_aria")}
        className="fixed z-40 right-4 sm:right-8 bottom-[calc(84px+var(--safe-bottom))] lg:bottom-8 inline-flex items-center gap-2 pl-4 pr-5 py-3 rounded-full bg-[var(--accent)] text-white font-semibold shadow-[var(--shadow-accent)] hover:bg-[var(--accent-hover)] active:scale-95 transition-all touch-manipulation"
      >
        <span className="relative inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/15">
          <Icon icon="solar:chat-round-dots-bold-duotone" width={18} />
          <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[var(--success)] border-2 border-[var(--accent)]" aria-hidden />
        </span>
        <span className="text-sm whitespace-nowrap">{t("food_ai_ask")}</span>
      </Link>
    </div>
  );
}
