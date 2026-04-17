"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const CHART_COLOR = "var(--accent, #c06240)";

type Tab = "day" | "month" | "year";

interface DaySummary {
  food: { cal: number; protein: number; fat: number; carbs: number };
  food_items: { name_of_food: string; b: number; g: number; u: number; cal: number }[];
  training: { cal: number; duration: number };
  training_items: { training_name: string; tren_time: number; training_cal: number }[];
  water: number;
  weight: number | null;
}

/** Ответ бэкенда /api/summary/month */
interface MonthSummaryRaw {
  year: number;
  month: number;
  food: { cal: number; protein: number; fat: number; carbs: number; days: number };
  training: { cal: number; duration: number; count: number };
  water_total: number;
  top5_training: { training_name: string; cnt: number; total_cal: number }[];
  weights: { date: string; weight: number }[];
}

/** Ответ бэкенда /api/summary/year */
interface YearSummaryRaw {
  year: number;
  food: { cal: number; protein: number; fat: number; carbs: number };
  monthly_food: { month: number; cal: number; protein: number; fat: number; carbs: number }[];
  training: { cal: number; duration: number };
  top5_training: { training_name: string; cnt: number; total_cal: number }[];
  water_total: number;
}

function StatBox({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string | number;
  unit: string;
  accent?: string;
}) {
  return (
    <div
      className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]"
      style={accent ? { borderColor: accent } : undefined}
    >
      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2 font-display">
        {label}
      </p>
      <p className="font-mono text-2xl sm:text-3xl font-bold text-[var(--foreground)] leading-none">
        {typeof value === "number" ? value.toLocaleString("ru-RU", { maximumFractionDigits: 1 }) : value}
      </p>
      <p className="text-xs text-[var(--muted)] mt-1">{unit}</p>
    </div>
  );
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

const MONTH_NAMES = [
  "Янв",
  "Фев",
  "Мар",
  "Апр",
  "Май",
  "Июн",
  "Июл",
  "Авг",
  "Сен",
  "Окт",
  "Ноя",
  "Дек",
];

export default function SummaryPage() {
  const [tab, setTab] = useState<Tab>("day");

  const today = new Date();
  const [dayDate, setDayDate] = useState(() => today.toISOString().split("T")[0]);
  const [monthYear, setMonthYear] = useState(today.getFullYear());
  const [monthNum, setMonthNum] = useState(today.getMonth() + 1);
  const [yearOnly, setYearOnly] = useState(today.getFullYear());

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [dayData, setDayData] = useState<DaySummary | null>(null);
  const [monthData, setMonthData] = useState<MonthSummaryRaw | null>(null);
  const [yearData, setYearData] = useState<YearSummaryRaw | null>(null);

  const loadDay = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await api<DaySummary>(`/api/summary/day?date=${encodeURIComponent(dayDate)}`);
      setDayData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить сводку за день");
      setDayData(null);
    } finally {
      setLoading(false);
    }
  }, [dayDate]);

  const loadMonth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m = await api<MonthSummaryRaw>(
        `/api/summary/month?year=${monthYear}&month=${monthNum}`,
      );
      setMonthData(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить сводку за месяц");
      setMonthData(null);
    } finally {
      setLoading(false);
    }
  }, [monthYear, monthNum]);

  const loadYear = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const y = await api<YearSummaryRaw>(`/api/summary/year?year=${yearOnly}`);
      setYearData(y);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить сводку за год");
      setYearData(null);
    } finally {
      setLoading(false);
    }
  }, [yearOnly]);

  useEffect(() => {
    if (tab === "day") void loadDay();
    else if (tab === "month") void loadMonth();
    else void loadYear();
  }, [tab, loadDay, loadMonth, loadYear]);

  const monthStats = useMemo(() => {
    if (!monthData) return null;
    const { food, training, water_total } = monthData;
    const d = Math.max(food.days, 1);
    const dim = daysInMonth(monthData.year, monthData.month);
    return {
      avgCal: food.cal / d,
      totalCal: food.cal,
      avgProtein: food.protein / d,
      avgFat: food.fat / d,
      avgCarbs: food.carbs / d,
      training,
      avgGlasses: water_total / dim,
      weightTrend: monthData.weights,
      top5: monthData.top5_training,
    };
  }, [monthData]);

  const yearChartData = useMemo(() => {
    if (!yearData) return [];
    return yearData.monthly_food.map((row) => {
      const dim = daysInMonth(yearData.year, row.month);
      return {
        month: row.month,
        label: MONTH_NAMES[row.month - 1] ?? String(row.month),
        avg_cal: dim > 0 ? row.cal / dim : 0,
        total_cal: row.cal,
      };
    });
  }, [yearData]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Прогресс</h1>
        <p className="text-sm text-[var(--muted)] mt-1">Питание, тренировки и динамика</p>
      </div>

      <div className="flex flex-wrap gap-2 p-1 bg-[var(--input-bg)] rounded-[var(--radius-lg)] border border-[var(--border)] w-fit">
        {(
          [
            ["day", "День"],
            ["month", "Месяц"],
            ["year", "Год"],
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

      {error && (
        <div
          className="rounded-[var(--radius-lg)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-4 py-3 text-sm text-[var(--foreground)]"
          role="alert"
        >
          {error}
        </div>
      )}

      {tab === "day" && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Дата
              <input
                type="date"
                value={dayDate}
                onChange={(e) => setDayDate(e.target.value)}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm text-[var(--foreground)] font-mono"
              />
            </label>
            <button
              type="button"
              onClick={() => void loadDay()}
              disabled={loading}
              className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50"
            >
              Обновить
            </button>
          </div>

          {loading && !dayData && (
            <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
          )}

          {dayData && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox label="Калории" value={Math.round(dayData.food.cal)} unit="ккал" />
                <StatBox
                  label="Белки"
                  value={Math.round(dayData.food.protein)}
                  unit="г"
                  accent="var(--success)"
                />
                <StatBox
                  label="Жиры"
                  value={Math.round(dayData.food.fat)}
                  unit="г"
                  accent="var(--warning)"
                />
                <StatBox label="Углеводы" value={Math.round(dayData.food.carbs)} unit="г" />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                  <h2 className="font-display text-sm font-semibold text-[var(--foreground)] mb-3">
                    Вода
                  </h2>
                  <p className="font-mono text-3xl font-bold">{dayData.water}</p>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    стаканов · {dayData.water * 300} мл
                  </p>
                </div>
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                  <h2 className="font-display text-sm font-semibold text-[var(--foreground)] mb-3">
                    Вес
                  </h2>
                  <p className="font-mono text-3xl font-bold">
                    {dayData.weight != null ? `${dayData.weight.toFixed(1)}` : "—"}
                  </p>
                  <p className="text-sm text-[var(--muted)] mt-1">кг</p>
                </div>
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
                  Еда
                </h2>
                {dayData.food_items.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                          <th className="pb-2">Блюдо</th>
                          <th className="pb-2 text-right">Б</th>
                          <th className="pb-2 text-right">Ж</th>
                          <th className="pb-2 text-right">У</th>
                          <th className="pb-2 text-right">Ккал</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dayData.food_items.map((f, i) => (
                          <tr key={i} className="border-t border-[var(--border)]">
                            <td className="py-2">{f.name_of_food}</td>
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
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет записей</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
                  Тренировки
                </h2>
                {dayData.training_items.length ? (
                  <div className="space-y-2">
                    {dayData.training_items.map((t, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0"
                      >
                        <span className="text-sm">{t.training_name}</span>
                        <div className="flex gap-4 text-sm">
                          <span className="text-[var(--muted)] font-mono">{t.tren_time} мин</span>
                          <span className="font-mono font-medium">
                            {Math.round(t.training_cal)} ккал
                          </span>
                        </div>
                      </div>
                    ))}
                    <div className="pt-2 flex justify-between font-medium text-sm">
                      <span>Итого</span>
                      <span className="font-mono">
                        {Math.round(dayData.training.cal)} ккал · {dayData.training.duration} мин
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет тренировок</p>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "month" && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Год
              <input
                type="number"
                value={monthYear}
                onChange={(e) => setMonthYear(Number(e.target.value))}
                className="w-28 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm font-mono"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Месяц
              <select
                value={monthNum}
                onChange={(e) => setMonthNum(Number(e.target.value))}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm"
              >
                {MONTH_NAMES.map((name, idx) => (
                  <option key={name} value={idx + 1}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void loadMonth()}
              disabled={loading}
              className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              Обновить
            </button>
          </div>

          {loading && !monthData && (
            <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
          )}

          {monthStats && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox label="Средние ккал / день" value={monthStats.avgCal} unit="ккал" />
                <StatBox label="Средние белки / день" value={monthStats.avgProtein} unit="г" />
                <StatBox label="Средние жиры / день" value={monthStats.avgFat} unit="г" />
                <StatBox label="Средние углеводы / день" value={monthStats.avgCarbs} unit="г" />
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox
                  label="Тренировки: ккал"
                  value={Math.round(monthStats.training.cal)}
                  unit="ккал за месяц"
                />
                <StatBox
                  label="Длительность"
                  value={Math.round(monthStats.training.duration)}
                  unit="мин"
                />
                <StatBox label="Сессий" value={monthStats.training.count} unit="шт." />
                <StatBox
                  label="Вода (средн. / день)"
                  value={monthStats.avgGlasses.toFixed(1)}
                  unit="стаканов"
                />
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                Всего калорий за месяц:{" "}
                <span className="font-mono text-[var(--foreground)]">
                  {Math.round(monthStats.totalCal).toLocaleString("ru-RU")}
                </span>{" "}
                ккал
              </p>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-2)]">
                <h2 className="font-display text-sm font-semibold mb-4">Вес по дням</h2>
                {monthStats.weightTrend.length ? (
                  <div className="h-64 w-full min-w-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={monthStats.weightTrend}>
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                          tickFormatter={(v) => {
                            try {
                              return new Date(v).toLocaleDateString("ru-RU", {
                                day: "numeric",
                                month: "short",
                              });
                            } catch {
                              return String(v);
                            }
                          }}
                        />
                        <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
                        <Tooltip
                          contentStyle={{
                            background: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius)",
                            boxShadow: "var(--shadow-1)",
                          }}
                          labelFormatter={(v) => String(v)}
                          formatter={(value) => [
                            `${Number(value ?? 0).toFixed(1)} кг`,
                            "Вес",
                          ]}
                        />
                        <Bar dataKey="weight" fill={CHART_COLOR} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет данных о весе</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="font-display text-sm font-semibold mb-3">Топ тренировок</h2>
                {monthStats.top5.length ? (
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    {monthStats.top5.map((t, i) => (
                      <li key={`${t.training_name}-${i}`} className="text-[var(--foreground)]">
                        <span className="font-medium">{t.training_name}</span>
                        <span className="text-[var(--muted)] font-mono ml-2">
                          {Math.round(t.total_cal)} ккал · {t.cnt}×
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет данных</p>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "year" && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Год
              <input
                type="number"
                value={yearOnly}
                onChange={(e) => setYearOnly(Number(e.target.value))}
                className="w-28 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm font-mono"
              />
            </label>
            <button
              type="button"
              onClick={() => void loadYear()}
              disabled={loading}
              className="px-4 py-2 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              Обновить
            </button>
          </div>

          {loading && !yearData && (
            <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
          )}

          {yearData && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox
                  label="Всего ккал (год)"
                  value={Math.round(yearData.food.cal)}
                  unit="ккал"
                />
                <StatBox
                  label="Средние ккал / день *"
                  value={
                    yearData.food.cal > 0
                      ? (yearData.food.cal / 365).toFixed(0)
                      : "0"
                  }
                  unit="* грубо по 365 дням"
                />
                <StatBox
                  label="Тренировки: ккал"
                  value={Math.round(yearData.training.cal)}
                  unit="ккал"
                />
                <StatBox
                  label="Длительность тренировок"
                  value={Math.round(yearData.training.duration)}
                  unit="мин"
                />
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                Вода за год:{" "}
                <span className="font-mono text-[var(--foreground)]">{yearData.water_total}</span>{" "}
                стаканов
              </p>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-2)]">
                <h2 className="font-display text-sm font-semibold mb-4">
                  Средние калории по месяцам (ккал / день)
                </h2>
                {yearChartData.length ? (
                  <div className="h-64 w-full min-w-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={yearChartData}>
                        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                        <Tooltip
                          contentStyle={{
                            background: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius)",
                          }}
                          formatter={(value) => [
                            `${Math.round(Number(value ?? 0))} ккал/день`,
                            "Среднее",
                          ]}
                        />
                        <Line
                          type="monotone"
                          dataKey="avg_cal"
                          stroke={CHART_COLOR}
                          strokeWidth={2}
                          dot={{ fill: CHART_COLOR, r: 3 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет данных о питании</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="font-display text-sm font-semibold mb-3">Топ тренировок за год</h2>
                {yearData.top5_training.length ? (
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    {yearData.top5_training.map((t, i) => (
                      <li key={`${t.training_name}-${i}`}>
                        <span className="font-medium">{t.training_name}</span>
                        <span className="text-[var(--muted)] font-mono ml-2">
                          {Math.round(t.total_cal)} ккал · {t.cnt}×
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">Нет данных</p>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
