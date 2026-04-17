"use client";

import { useCallback, useEffect, useState } from "react";
import { api, apiUpload } from "@/lib/api";

type Tab = "photo" | "manual";

interface FoodItem {
  name_of_food: string;
  b: number;
  g: number;
  u: number;
  cal: number;
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
      <div>
        <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">Питание</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {new Date(date + "T12:00:00").toLocaleDateString("ru-RU", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </div>

      <div className="flex gap-2 p-1 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius-lg)] w-fit">
        {(
          [
            ["photo", "По фото"],
            ["manual", "Вручную"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-4 py-2 rounded-[var(--radius)] text-sm font-medium transition-colors ${
              tab === id
                ? "bg-[var(--card)] text-[var(--foreground)] shadow-[var(--shadow-1)]"
                : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
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

      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
        <h2 className="font-display text-lg font-semibold text-[var(--foreground)] mb-4">
          Сегодня
        </h2>
        {dayError && (
          <p className="text-sm text-[var(--destructive)] mb-4">{dayError}</p>
        )}
        {loadingDay && !dayError && (
          <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
        )}
        {!loadingDay && foodDay && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                ["Ккал", foodDay.totals.total_cal, ""],
                ["Белки", foodDay.totals.total_protein, "г"],
                ["Жиры", foodDay.totals.total_fat, "г"],
                ["Углеводы", foodDay.totals.total_carbs, "г"],
              ].map(([label, val, unit]) => (
                <div
                  key={String(label)}
                  className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2"
                >
                  <p className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                    {label}
                  </p>
                  <p className="font-mono text-lg font-semibold text-[var(--foreground)]">
                    {Math.round(Number(val))}
                    {unit && (
                      <span className="text-sm font-normal text-[var(--muted)] ml-0.5">{unit}</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
            {foodDay.items.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">Пока нет записей</p>
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
    </div>
  );
}
