"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

const TARGET_GLASSES = 8;

interface WaterResponse {
  count: number;
  ml: number;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0]!;
}

export default function WaterPage() {
  const [date] = useState(todayISO);
  const [data, setData] = useState<WaterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const w = await api<WaterResponse>(`/api/water?date=${encodeURIComponent(date)}`);
      setData(w);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "Не удалось загрузить данные");
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    void load();
  }, [load]);

  async function addGlass() {
    setAdding(true);
    setError("");
    try {
      const w = await api<WaterResponse>("/api/water", { method: "POST" });
      setData(w);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить стакан");
    } finally {
      setAdding(false);
    }
  }

  const count = data?.count ?? 0;
  const ml = data?.ml ?? 0;
  const progress = Math.min(count / TARGET_GLASSES, 1);

  const size = 200;
  const stroke = 14;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - progress);

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">Вода</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {new Date(date + "T12:00:00").toLocaleDateString("ru-RU", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </div>

      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-8 shadow-[var(--shadow-1)] flex flex-col items-center">
        {error && (
          <p className="text-sm text-[var(--destructive)] mb-6 text-center w-full">{error}</p>
        )}

        {loading && !error && (
          <p className="text-[var(--muted-foreground)] py-12">Загрузка…</p>
        )}

        {!loading && (
          <>
            <div className="relative mb-8" style={{ width: size, height: size }}>
              <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                className="rotate-[-90deg]"
                aria-hidden
              >
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={r}
                  fill="none"
                  stroke="var(--color-sand)"
                  strokeWidth={stroke}
                />
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={r}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth={stroke}
                  strokeLinecap="round"
                  strokeDasharray={c}
                  strokeDashoffset={offset}
                  className="transition-[stroke-dashoffset] duration-500 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-display text-5xl font-bold text-[var(--foreground)] tabular-nums">
                  {count}
                </span>
                <span className="text-sm text-[var(--muted-foreground)] mt-1">
                  из {TARGET_GLASSES} стаканов
                </span>
              </div>
            </div>

            <div className="text-center space-y-1 mb-8">
              <p className="font-mono text-3xl font-semibold text-[var(--foreground)]">
                {ml}{" "}
                <span className="text-lg font-medium text-[var(--muted)]">мл</span>
              </p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Цель: {TARGET_GLASSES * 300} мл ({TARGET_GLASSES}×300 мл)
              </p>
            </div>

            <button
              type="button"
              onClick={() => void addGlass()}
              disabled={adding}
              className="w-full max-w-sm py-4 px-6 rounded-[var(--radius-lg)] bg-[var(--accent)] text-white text-lg font-semibold shadow-[var(--shadow-1)] hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
            >
              {adding ? "Добавление…" : "+ Добавить стакан"}
            </button>

            {count >= TARGET_GLASSES && (
              <p className="mt-6 text-sm font-medium text-[var(--success)]">
                Дневная норма воды выполнена
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
