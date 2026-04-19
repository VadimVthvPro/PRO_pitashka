"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { Icon } from "@iconify/react";
import { api } from "@/lib/api";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { Sticker } from "@/components/hand/Sticker";
import { Highlight } from "@/components/hand/Highlight";
import { Scribble } from "@/components/hand/Scribble";

interface Point {
  date: string;
  weight: number;
}

interface ForecastResponse {
  enough_data: boolean;
  points: Point[];
  forecast: Point[];
  trend_kg_per_week: number | null;
  target_weight: number | null;
  days_to_target: number | null;
  latest_weight?: number;
  latest_date?: string;
  message?: string;
}

function WeightChart({
  history,
  forecast,
  target,
}: {
  history: Point[];
  forecast: Point[];
  target: number | null;
}) {
  const all = [...history, ...forecast];
  if (all.length === 0) return null;

  const weights = all.map((p) => p.weight);
  const targetConsidered = target && Number.isFinite(target) ? [target] : [];
  const minW = Math.min(...weights, ...targetConsidered) - 1;
  const maxW = Math.max(...weights, ...targetConsidered) + 1;
  const range = Math.max(0.1, maxW - minW);

  const first = new Date(all[0]!.date).getTime();
  const last = new Date(all[all.length - 1]!.date).getTime();
  const spanMs = Math.max(1, last - first);

  const width = 800;
  const height = 260;
  const padL = 42;
  const padR = 16;
  const padT = 20;
  const padB = 30;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const x = (dateIso: string) => {
    const t = new Date(dateIso).getTime();
    return padL + ((t - first) / spanMs) * chartW;
  };
  const y = (w: number) => padT + chartH - ((w - minW) / range) * chartH;

  const pointsPath = (pts: Point[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.date).toFixed(2)} ${y(p.weight).toFixed(2)}`).join(" ");

  const gridY = [0.25, 0.5, 0.75].map((v) => padT + chartH * v);

  return (
    <div className="card-base p-4 sm:p-6 relative overflow-hidden">
      <div
        className="pointer-events-none absolute -top-20 -right-10 w-64 h-64 rounded-full blur-3xl opacity-20"
        style={{ background: "var(--accent)" }}
        aria-hidden
      />
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto relative">
        {gridY.map((gy, i) => (
          <line
            key={i}
            x1={padL}
            x2={width - padR}
            y1={gy}
            y2={gy}
            stroke="var(--border)"
            strokeWidth="1"
            strokeDasharray="2 4"
            opacity="0.6"
          />
        ))}

        {target != null && (
          <>
            <line
              x1={padL}
              x2={width - padR}
              y1={y(target)}
              y2={y(target)}
              stroke="var(--color-sage)"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
            <text
              x={width - padR}
              y={y(target) - 4}
              textAnchor="end"
              fontSize="11"
              fill="var(--color-sage)"
              fontWeight="600"
            >
              цель · {target} кг
            </text>
          </>
        )}

        {forecast.length > 1 && (
          <motion.path
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            d={pointsPath([history[history.length - 1]!, ...forecast])}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2.5"
            strokeDasharray="6 5"
            strokeLinecap="round"
            opacity="0.6"
          />
        )}

        {history.length > 1 && (
          <>
            <motion.path
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
              d={`${pointsPath(history)} L ${x(history[history.length - 1]!.date)} ${padT + chartH} L ${x(history[0]!.date)} ${padT + chartH} Z`}
              fill="var(--accent)"
              opacity="0.08"
            />
            <motion.path
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
              d={pointsPath(history)}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}

        {history.map((p, i) => (
          <motion.circle
            key={i}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.6 + i * 0.03, type: "spring", stiffness: 300 }}
            cx={x(p.date)}
            cy={y(p.weight)}
            r={3.5}
            fill="var(--card)"
            stroke="var(--accent)"
            strokeWidth="2"
          />
        ))}

        {[minW, (minW + maxW) / 2, maxW].map((w, i) => (
          <text
            key={i}
            x={padL - 6}
            y={y(w) + 4}
            textAnchor="end"
            fontSize="11"
            fill="var(--muted-foreground)"
            fontFamily="var(--font-mono)"
          >
            {w.toFixed(1)}
          </text>
        ))}
      </svg>
    </div>
  );
}

interface JournalEntry {
  date: string;
  weight: number;
  imt: number | null;
}

const todayIso = () => {
  const t = new Date();
  const y = t.getFullYear();
  const m = String(t.getMonth() + 1).padStart(2, "0");
  const d = String(t.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const formatRu = (iso: string) => {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
};

export default function WeightPage() {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [weightInput, setWeightInput] = useState("");
  const [dateInput, setDateInput] = useState(todayIso());
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [forecast, journal] = await Promise.all([
        api<ForecastResponse>("/api/weight/forecast?horizon_days=30"),
        api<{ items: JournalEntry[] }>("/api/weight/list?limit=180"),
      ]);
      setData(forecast);
      setEntries(journal.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addWeight() {
    const w = parseFloat(weightInput.replace(",", "."));
    if (!Number.isFinite(w) || w < 20 || w > 400) {
      setSaveError("Вес 20–400 кг");
      return;
    }
    if (!dateInput || dateInput > todayIso()) {
      setSaveError("Дата некорректна");
      return;
    }
    setSaveError("");
    setSaving(true);
    try {
      await api("/api/weight", {
        method: "POST",
        body: JSON.stringify({ weight: w, date: dateInput }),
      });
      setWeightInput("");
      setDateInput(todayIso());
      await load();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Не сохранилось");
    } finally {
      setSaving(false);
    }
  }

  async function deleteEntry(iso: string) {
    if (pendingDelete !== iso) {
      setPendingDelete(iso);
      window.setTimeout(() => {
        setPendingDelete((curr) => (curr === iso ? null : curr));
      }, 4000);
      return;
    }
    setPendingDelete(null);
    try {
      await api(`/api/weight/${iso}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось удалить");
    }
  }

  const deltas = useMemo(() => {
    const map = new Map<string, number | null>();
    for (let i = 0; i < entries.length; i++) {
      const curr = entries[i]!;
      const prev = entries[i + 1];
      map.set(curr.date, prev ? curr.weight - prev.weight : null);
    }
    return map;
  }, [entries]);

  const trendDirection = useMemo(() => {
    if (!data?.trend_kg_per_week) return "stable";
    if (data.trend_kg_per_week < -0.15) return "down";
    if (data.trend_kg_per_week > 0.15) return "up";
    return "stable";
  }, [data?.trend_kg_per_week]);

  return (
    <div className="space-y-8">
      <ScrollReveal>
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              Честное зеркало
            </p>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(2.5rem, 1.8rem + 3vw, 4rem)",
                letterSpacing: "-0.03em",
                lineHeight: 0.92,
              }}
            >
              Твой{" "}
              <Highlight color="oklch(72% 0.15 80 / 0.5)">
                <span className="px-1">вес</span>
              </Highlight>
            </h1>
          </div>
          {data?.latest_weight && (
            <div
              className="relative inline-flex flex-col items-start gap-1 pr-6"
              style={{ transform: "rotate(-1.5deg)" }}
            >
              <Sticker color="sage" font="arkhip" size="sm" rotate={-2}>
                сейчас
              </Sticker>
              <div
                className="flex items-baseline gap-2"
                style={{ fontFamily: "var(--font-display)" }}
              >
                <span className="display-number text-6xl text-[var(--foreground)]">
                  <AnimatedNumber value={data.latest_weight} decimals={1} />
                </span>
                <span
                  className="text-sm text-[var(--muted)]"
                  style={{ fontFamily: "var(--font-body)" }}
                >
                  кг
                </span>
              </div>
            </div>
          )}
        </div>
      </ScrollReveal>

      <ScrollReveal delay={0.05}>
        <div className="card-base p-5">
          <div className="flex items-center gap-3 mb-3">
            <Icon icon="solar:scale-bold-duotone" width={26} className="text-[var(--accent)]" />
            <p
              className="text-lg"
              style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
            >
              Добавить запись
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-3 items-end">
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
                Вес, кг
              </label>
              <input
                type="number"
                step="0.1"
                inputMode="decimal"
                value={weightInput}
                onChange={(e) => setWeightInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addWeight()}
                placeholder="72.4"
                className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] font-mono tabular-nums focus:border-[var(--accent)] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
                Дата
              </label>
              <input
                type="date"
                value={dateInput}
                max={todayIso()}
                onChange={(e) => setDateInput(e.target.value)}
                className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] focus:border-[var(--accent)] focus:outline-none"
              />
            </div>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => void addWeight()}
              disabled={saving || !weightInput}
              className="px-5 py-2.5 bg-[var(--accent)] text-white font-semibold rounded-[var(--radius)] hover:bg-[var(--accent-hover)] disabled:opacity-50 whitespace-nowrap"
            >
              {saving ? "Сохраняю..." : "Записать"}
            </motion.button>
          </div>
          {saveError && (
            <p className="text-xs text-[var(--destructive)] mt-2">{saveError}</p>
          )}
          <p className="text-xs text-[var(--muted-foreground)] mt-3">
            Записал не сегодня? Поменяй дату — задним числом тоже можно.
          </p>
        </div>
      </ScrollReveal>

      {loading && (
        <div className="card-base p-6">
          <div className="skeleton h-64 w-full rounded-[var(--radius)]" />
        </div>
      )}

      {error && <p className="text-sm text-[var(--destructive)]">{error}</p>}

      {!loading && data && (
        <>
          {data.points.length === 0 ? (
            <ScrollReveal>
              <div className="flex items-center gap-6 py-6">
                <Scribble
                  variant="squiggle"
                  className="w-28 h-28 text-[var(--color-latte)]"
                />
                <div>
                  <p
                    className="text-2xl"
                    style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
                  >
                    Пока пусто
                  </p>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[46ch]">
                    Запиши свой вес — появится график. Взвешивайся раз в 2-3 дня с утра натощак.
                  </p>
                </div>
              </div>
            </ScrollReveal>
          ) : (
            <>
              <ScrollReveal delay={0.1}>
                <WeightChart
                  history={data.points}
                  forecast={data.forecast}
                  target={data.target_weight}
                />
              </ScrollReveal>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <ScrollReveal delay={0.15}>
                  <div className="card-base p-5">
                    <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                      Тренд / неделя
                    </p>
                    <p
                      className="display-number text-3xl mt-1 flex items-center gap-2"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {data.trend_kg_per_week != null ? (
                        <>
                          <span
                            className={
                              trendDirection === "down"
                                ? "text-[var(--color-sage)]"
                                : trendDirection === "up"
                                ? "text-[var(--warning)]"
                                : "text-[var(--foreground)]"
                            }
                          >
                            {data.trend_kg_per_week > 0 ? "+" : ""}
                            {data.trend_kg_per_week.toFixed(2)}
                          </span>
                          <span
                            className="text-sm text-[var(--muted)]"
                            style={{ fontFamily: "var(--font-body)" }}
                          >
                            кг
                          </span>
                        </>
                      ) : (
                        <span className="text-[var(--muted)] text-2xl">—</span>
                      )}
                    </p>
                  </div>
                </ScrollReveal>

                <ScrollReveal delay={0.2}>
                  <div className="card-base p-5">
                    <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                      Цель
                    </p>
                    <p
                      className="display-number text-3xl mt-1"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {data.target_weight ? (
                        <>
                          {data.target_weight}
                          <span
                            className="text-sm text-[var(--muted)] ml-1"
                            style={{ fontFamily: "var(--font-body)" }}
                          >
                            кг
                          </span>
                        </>
                      ) : (
                        <span className="text-[var(--muted)] text-2xl">—</span>
                      )}
                    </p>
                  </div>
                </ScrollReveal>

                <ScrollReveal delay={0.25}>
                  <div className="card-base p-5">
                    <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                      Дней до цели
                    </p>
                    <p
                      className="display-number text-3xl mt-1"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {data.days_to_target ? (
                        <>
                          <AnimatedNumber value={data.days_to_target} />
                          <span
                            className="text-sm text-[var(--muted)] ml-1"
                            style={{ fontFamily: "var(--font-body)" }}
                          >
                            дн.
                          </span>
                        </>
                      ) : (
                        <span className="text-[var(--muted)] text-2xl">—</span>
                      )}
                    </p>
                  </div>
                </ScrollReveal>
              </div>

              {!data.enough_data && data.message && (
                <p className="text-sm text-[var(--muted-foreground)] italic">
                  {data.message}
                </p>
              )}
            </>
          )}
        </>
      )}

      {entries.length > 0 && (
        <ScrollReveal delay={0.3}>
          <div className="card-base overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <Icon
                  icon="solar:notebook-bold-duotone"
                  width={22}
                  className="text-[var(--accent)]"
                />
                <p
                  className="text-lg"
                  style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
                >
                  Журнал записей
                </p>
              </div>
              <span className="text-xs text-[var(--muted-foreground)] tabular-nums">
                {entries.length} зап.
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                    <th className="px-5 py-3 font-medium">Дата</th>
                    <th className="px-3 py-3 font-medium text-right">Вес, кг</th>
                    <th className="px-3 py-3 font-medium text-right">Δ</th>
                    <th className="px-3 py-3 font-medium text-right hidden sm:table-cell">ИМТ</th>
                    <th className="px-5 py-3 w-[1%]" aria-label="Действия" />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((row) => {
                    const delta = deltas.get(row.date);
                    const armed = pendingDelete === row.date;
                    return (
                      <tr
                        key={row.date}
                        className="border-t border-[var(--border)]/60 hover:bg-[var(--color-sand)]/40 transition-colors"
                      >
                        <td className="px-5 py-3 whitespace-nowrap">{formatRu(row.date)}</td>
                        <td className="px-3 py-3 text-right font-mono tabular-nums font-semibold">
                          {row.weight.toFixed(1)}
                        </td>
                        <td className="px-3 py-3 text-right font-mono tabular-nums">
                          {delta == null ? (
                            <span className="text-[var(--muted)]">—</span>
                          ) : delta === 0 ? (
                            <span className="text-[var(--muted)]">0.0</span>
                          ) : (
                            <span
                              className={
                                delta < 0 ? "text-[var(--color-sage)]" : "text-[var(--warning)]"
                              }
                            >
                              {delta > 0 ? "+" : ""}
                              {delta.toFixed(1)}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-3 text-right font-mono tabular-nums hidden sm:table-cell text-[var(--muted-foreground)]">
                          {row.imt != null ? row.imt.toFixed(1) : "—"}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <motion.button
                            whileTap={{ scale: 0.92 }}
                            onClick={() => void deleteEntry(row.date)}
                            className={`text-xs px-2.5 py-1.5 rounded-md transition ${
                              armed
                                ? "bg-[var(--destructive)] text-white"
                                : "text-[var(--muted)] hover:text-[var(--destructive)] hover:bg-[var(--destructive)]/10"
                            }`}
                            title={armed ? "Подтвердить удаление" : "Удалить запись"}
                          >
                            {armed ? (
                              "Подтвердить?"
                            ) : (
                              <Icon icon="solar:trash-bin-trash-linear" width={16} />
                            )}
                          </motion.button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </ScrollReveal>
      )}
    </div>
  );
}
