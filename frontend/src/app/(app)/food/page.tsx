"use client";

import { useCallback, useEffect, useState } from "react";
import { api, apiUpload } from "@/lib/api";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { Sticker } from "@/components/hand/Sticker";
import { Scribble } from "@/components/hand/Scribble";
import { Highlight } from "@/components/hand/Highlight";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { handleActivityResponse } from "@/lib/streaks";

type Tab = "photo" | "manual" | "repeat";

interface FoodItem {
  name_of_food: string;
  b: number;
  g: number;
  u: number;
  cal: number;
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
  const [tab, setTab] = useState<Tab>("photo");
  const [date] = useState(todayISO);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab");
    if (t === "repeat" || t === "manual" || t === "photo") {
      setTab(t);
    }
  }, []);

  const [foodDay, setFoodDay] = useState<FoodDayResponse | null>(null);
  const [loadingDay, setLoadingDay] = useState(true);
  const [dayError, setDayError] = useState("");

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoDragging, setPhotoDragging] = useState(false);
  const [photoSubmitting, setPhotoSubmitting] = useState(false);
  const [photoError, setPhotoError] = useState("");

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
      setDayError(e instanceof Error ? e.message : "Не удалось загрузить данные");
    } finally {
      setLoadingDay(false);
    }
  }, [date]);

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
      setRepeatError(e instanceof Error ? e.message : "Не удалось загрузить данные");
    } finally {
      setRepeatLoading(false);
    }
  }, []);

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
      setRepeatError(e instanceof Error ? e.message : "Не удалось скопировать");
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
      setRepeatError(e instanceof Error ? e.message : "Не удалось добавить");
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
    if (f) setPhotoFile(f);
  }

  async function submitPhoto() {
    if (!photoFile) {
      setPhotoError("Выберите файл с фото еды");
      return;
    }
    setPhotoError("");
    setPhotoSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("file", photoFile);
      const res = await apiUpload<unknown>(
        `/api/food/photo?food_date=${encodeURIComponent(date)}`,
        fd,
      );
      if (hasErrorPayload(res)) {
        setPhotoError(res.error);
        return;
      }
      handleActivityResponse(res as Parameters<typeof handleActivityResponse>[0]);
      setPhotoFile(null);
      await loadDay();
    } catch (e) {
      setPhotoError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setPhotoSubmitting(false);
    }
  }

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
      setManualError("Укажите хотя бы одно блюдо");
      return;
    }
    if (foods.length !== grams.length) {
      setManualError("Количество блюд и граммов должно совпадать");
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
      setManualError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setManualSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <ScrollReveal>
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              {new Date(date + "T12:00:00").toLocaleDateString("ru-RU", {
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
              Что <Highlight color="oklch(72% 0.15 80 / 0.45)">положим</Highlight>
              <br />
              в тарелку?
            </h1>
          </div>
          <Sticker color="cream" font="arkhip" rotate={-4} size="md">
            фото или руками
          </Sticker>
        </div>
      </ScrollReveal>

      <div className="flex flex-wrap gap-2 p-1 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius-lg)] w-fit relative">
        {(
          [
            ["photo", "Снял — распознаю", "solar:camera-bold-duotone"],
            ["manual", "Записать руками", "solar:pen-bold-duotone"],
            ["repeat", "Как вчера", "solar:refresh-circle-bold-duotone"],
          ] as const
        ).map(([id, label, icon]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`relative flex items-center gap-2 px-4 py-2 rounded-[var(--radius)] text-sm font-medium transition-colors ${
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
            {label}
          </button>
        ))}
      </div>

      {tab === "photo" && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)] space-y-4">
          <div
            role="presentation"
            onDragOver={onPhotoDragOver}
            onDragLeave={onPhotoDragLeave}
            onDrop={onPhotoDrop}
            className={`border-2 border-dashed rounded-[var(--radius-lg)] p-10 text-center transition-colors ${
              photoDragging
                ? "border-[var(--accent)] bg-[var(--color-sand)]/40"
                : "border-[var(--border)] bg-[var(--input-bg)]"
            }`}
          >
            <p className="text-sm text-[var(--muted)] mb-2">
              Перетащите фото сюда или выберите файл
            </p>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              id="food-photo-input"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setPhotoFile(f);
              }}
            />
            <label
              htmlFor="food-photo-input"
              className="inline-block px-4 py-2 text-sm font-medium rounded-[var(--radius)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] cursor-pointer transition-colors"
            >
              Выбрать файл
            </label>
            {photoFile && (
              <p className="mt-3 text-sm text-[var(--foreground)] font-mono truncate max-w-full">
                {photoFile.name}
              </p>
            )}
          </div>
          {photoError && (
            <p className="text-sm text-[var(--destructive)]">{photoError}</p>
          )}
          <button
            type="button"
            onClick={() => void submitPhoto()}
            disabled={photoSubmitting || !photoFile}
            className="w-full py-3 rounded-[var(--radius)] bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {photoSubmitting ? "Отправка…" : "Распознать и сохранить"}
          </button>
        </div>
      )}

      {tab === "manual" && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-6 shadow-[var(--shadow-1)] space-y-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              Блюда (через запятую)
            </label>
            <textarea
              value={manualFoods}
              onChange={(e) => setManualFoods(e.target.value)}
              rows={3}
              placeholder="Овсянка, банан, кофе"
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--accent)] focus:outline-none focus:ring-3 focus:ring-[var(--accent)]/15 resize-y min-h-[88px]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
              Граммы (через запятую, в том же порядке)
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
            {manualSubmitting ? "Сохранение…" : "Добавить в дневник"}
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
                    Последний съеденный день
                  </p>
                  <h3
                    className="text-2xl mt-1"
                    style={{
                      fontFamily: "var(--font-display)",
                      letterSpacing: "-0.02em",
                    }}
                  >
                    {new Date(lastDay.date + "T12:00:00").toLocaleDateString(
                      "ru-RU",
                      { weekday: "long", day: "numeric", month: "long" },
                    )}
                  </h3>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    {lastDay.items.length} блюд ·{" "}
                    {Math.round(lastDay.totals?.total_cal ?? 0)} ккал ·{" "}
                    {Math.round(lastDay.totals?.total_protein ?? 0)}/
                    {Math.round(lastDay.totals?.total_fat ?? 0)}/
                    {Math.round(lastDay.totals?.total_carbs ?? 0)} БЖУ
                  </p>
                </div>
                <Sticker color="sage" font="appetite" rotate={3}>
                  один клик
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
                      {Math.round(it.cal)} ккал
                    </span>
                  </div>
                ))}
                {lastDay.items.length > 6 && (
                  <p className="text-xs text-[var(--muted-foreground)] pt-1">
                    + ещё {lastDay.items.length - 6}
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
                {repeatSubmitting ? "Копируем…" : "Скопировать в сегодня"}
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
                  Твои частые
                </h3>
                <Sticker color="amber" size="sm" rotate={-3} font="arkhip">
                  топ {favorites.length}
                </Sticker>
              </div>
              <p className="text-sm text-[var(--muted)] mb-4">
                Клик = добавить с такими же граммами, как обычно
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
                          {Math.round(Number(f.cal))} ккал · ×{f.times}
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
                  Ещё нечего повторять
                </p>
                <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[46ch]">
                  Добавь пару блюд руками или по фото — и тут появится ленивый
                  способ повторить день.
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
            Сегодня на тарелке
          </h2>
          {foodDay && foodDay.items.length > 0 && (
            <Sticker color="sage" size="sm" rotate={3}>
              {foodDay.items.length} блюд
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
                ["Ккал", foodDay.totals.total_cal, "", "var(--accent)"],
                ["Белки", foodDay.totals.total_protein, "г", "var(--success)"],
                ["Жиры", foodDay.totals.total_fat, "г", "var(--warning)"],
                ["Углеводы", foodDay.totals.total_carbs, "г", "var(--accent)"],
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
                    Ничего не ел?
                  </p>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1.5 max-w-[46ch]">
                    Так и запишем. Когда будет что добавить — сюда же.
                  </p>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                      <th className="pb-2">Блюдо</th>
                      <th className="pb-2 text-right">Б</th>
                      <th className="pb-2 text-right">Ж</th>
                      <th className="pb-2 text-right">У</th>
                      <th className="pb-2 text-right">Ккал</th>
                    </tr>
                  </thead>
                  <tbody>
                    {foodDay.items.map((f, i) => (
                      <tr
                        key={`${f.name_of_food}-${i}`}
                        className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/50"
                      >
                        <td className="py-2 pr-2">{f.name_of_food}</td>
                        <td className="py-2 text-right font-mono text-xs">{Math.round(f.b)}</td>
                        <td className="py-2 text-right font-mono text-xs">{Math.round(f.g)}</td>
                        <td className="py-2 text-right font-mono text-xs">{Math.round(f.u)}</td>
                        <td className="py-2 text-right font-mono text-xs font-medium">
                          {Math.round(f.cal)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
      </ScrollReveal>
    </div>
  );
}
