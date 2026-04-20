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
import { useI18n } from "@/lib/i18n";

const CHART_COLOR = "var(--accent)";

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
  const { lang } = useI18n();
  return (
    <div
      className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]"
      style={accent ? { borderColor: accent } : undefined}
    >
      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-2 font-display">
        {label}
      </p>
      <p className="font-mono text-2xl sm:text-3xl font-bold text-[var(--foreground)] leading-none">
        {typeof value === "number" ? value.toLocaleString(lang, { maximumFractionDigits: 1 }) : value}
      </p>
      <p className="text-xs text-[var(--muted)] mt-1">{unit}</p>
    </div>
  );
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

const MONTH_KEYS = [
  "summary_month_jan",
  "summary_month_feb",
  "summary_month_mar",
  "summary_month_apr",
  "summary_month_may",
  "summary_month_jun",
  "summary_month_jul",
  "summary_month_aug",
  "summary_month_sep",
  "summary_month_oct",
  "summary_month_nov",
  "summary_month_dec",
] as const;

export default function SummaryPage() {
  const { t, lang } = useI18n();
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
      setError(e instanceof Error ? e.message : t("summary_err_day"));
      setDayData(null);
    } finally {
      setLoading(false);
    }
  }, [dayDate, t]);

  const loadMonth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m = await api<MonthSummaryRaw>(
        `/api/summary/month?year=${monthYear}&month=${monthNum}`,
      );
      setMonthData(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("summary_err_month"));
      setMonthData(null);
    } finally {
      setLoading(false);
    }
  }, [monthYear, monthNum, t]);

  const loadYear = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const y = await api<YearSummaryRaw>(`/api/summary/year?year=${yearOnly}`);
      setYearData(y);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("summary_err_year"));
      setYearData(null);
    } finally {
      setLoading(false);
    }
  }, [yearOnly, t]);

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
        label: t(MONTH_KEYS[row.month - 1] ?? "summary_month_jan"),
        avg_cal: dim > 0 ? row.cal / dim : 0,
        total_cal: row.cal,
      };
    });
  }, [yearData, t]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">{t("summary_headline")}</h1>
        <p className="text-sm text-[var(--muted)] mt-1">{t("summary_subtitle")}</p>
      </div>

      <div className="flex flex-wrap gap-2 p-1 bg-[var(--input-bg)] rounded-[var(--radius-lg)] border border-[var(--border)] w-fit">
        {(
          [
            ["day", "summary_day"],
            ["month", "summary_month"],
            ["year", "summary_year"],
          ] as const
        ).map(([id, labelKey]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-4 min-h-11 rounded-[var(--radius)] text-sm font-medium transition-colors touch-manipulation ${
              tab === id
                ? "bg-[var(--card)] text-[var(--foreground)] shadow-[var(--shadow-1)]"
                : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t(labelKey)}
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
              {t("summary_label_date")}
              <input
                type="date"
                value={dayDate}
                onChange={(e) => setDayDate(e.target.value)}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 min-h-11 text-sm text-[var(--foreground)] font-mono"
              />
            </label>
            <button
              type="button"
              onClick={() => void loadDay()}
              disabled={loading}
              className="px-4 min-h-11 rounded-[var(--radius)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-50 touch-manipulation"
            >
              {t("summary_btn_refresh")}
            </button>
          </div>

          {loading && !dayData && (
            <p className="text-sm text-[var(--muted-foreground)]">{t("summary_loading")}</p>
          )}

          {dayData && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox label={t("summary_card_calories")} value={Math.round(dayData.food.cal)} unit={t("kcal")} />
                <StatBox
                  label={t("protein")}
                  value={Math.round(dayData.food.protein)}
                  unit={t("grams_short")}
                  accent="var(--success)"
                />
                <StatBox
                  label={t("fat")}
                  value={Math.round(dayData.food.fat)}
                  unit={t("grams_short")}
                  accent="var(--warning)"
                />
                <StatBox label={t("carbs")} value={Math.round(dayData.food.carbs)} unit={t("grams_short")} />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                  <h2 className="font-display text-sm font-semibold text-[var(--foreground)] mb-3">
                    {t("summary_card_water")}
                  </h2>
                  <p className="font-mono text-3xl font-bold">{dayData.water}</p>
                  <p className="text-sm text-[var(--muted)] mt-1">
                    {t("summary_water_glasses_ml", { glasses: dayData.water, ml: dayData.water * 300 })}
                  </p>
                </div>
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                  <h2 className="font-display text-sm font-semibold text-[var(--foreground)] mb-3">
                    {t("summary_card_weight")}
                  </h2>
                  <p className="font-mono text-3xl font-bold">
                    {dayData.weight != null ? `${dayData.weight.toFixed(1)}` : "—"}
                  </p>
                  <p className="text-sm text-[var(--muted)] mt-1">{t("common_kg")}</p>
                </div>
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
                  {t("summary_card_food")}
                </h2>
                {dayData.food_items.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                          <th className="pb-2">{t("food_th_dish")}</th>
                          <th className="pb-2 text-right">{t("food_macro_protein")}</th>
                          <th className="pb-2 text-right">{t("food_macro_fat")}</th>
                          <th className="pb-2 text-right">{t("food_macro_carbs")}</th>
                          <th className="pb-2 text-right">{t("food_macro_kcal")}</th>
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
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_food_no_entries")}</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
                  {t("summary_card_trainings")}
                </h2>
                {dayData.training_items.length ? (
                  <div className="space-y-2">
                    {dayData.training_items.map((row, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between gap-3 py-2 border-b border-[var(--border)] last:border-0"
                      >
                        <span className="text-sm min-w-0 flex-1 truncate" title={row.training_name}>
                          {row.training_name}
                        </span>
                        <div className="flex gap-3 text-sm shrink-0">
                          <span className="text-[var(--muted)] font-mono whitespace-nowrap">
                            {row.tren_time} {t("min")}
                          </span>
                          <span className="font-mono font-medium whitespace-nowrap">
                            {Math.round(row.training_cal)} {t("kcal")}
                          </span>
                        </div>
                      </div>
                    ))}
                    <div className="pt-2 flex justify-between font-medium text-sm">
                      <span>{t("summary_day_trainings_total")}</span>
                      <span className="font-mono">
                        {Math.round(dayData.training.cal)} {t("kcal")} · {dayData.training.duration}{" "}
                        {t("min")}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_no_workouts_today")}</p>
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
              {t("summary_year")}
              <input
                type="number"
                value={monthYear}
                onChange={(e) => setMonthYear(Number(e.target.value))}
                className="w-28 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm font-mono"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              {t("summary_month")}
              <select
                value={monthNum}
                onChange={(e) => setMonthNum(Number(e.target.value))}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm"
              >
                {MONTH_KEYS.map((key, idx) => (
                  <option key={key} value={idx + 1}>
                    {t(key)}
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
              {t("summary_btn_refresh")}
            </button>
          </div>

          {loading && !monthData && (
            <p className="text-sm text-[var(--muted-foreground)]">{t("summary_loading")}</p>
          )}

          {monthStats && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox label={t("summary_avg_kcal_per_day")} value={monthStats.avgCal} unit={t("kcal")} />
                <StatBox label={t("summary_avg_protein_per_day")} value={monthStats.avgProtein} unit={t("grams_short")} />
                <StatBox label={t("summary_avg_fat_per_day")} value={monthStats.avgFat} unit={t("grams_short")} />
                <StatBox label={t("summary_avg_carbs_per_day")} value={monthStats.avgCarbs} unit={t("grams_short")} />
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox
                  label={t("summary_train_kcal")}
                  value={Math.round(monthStats.training.cal)}
                  unit={t("summary_train_kcal_month_unit")}
                />
                <StatBox
                  label={t("summary_train_duration")}
                  value={Math.round(monthStats.training.duration)}
                  unit={t("min")}
                />
                <StatBox label={t("summary_train_sessions")} value={monthStats.training.count} unit={t("common_count_pcs")} />
                <StatBox
                  label={t("summary_water_avg_day_label")}
                  value={monthStats.avgGlasses.toFixed(1)}
                  unit={t("summary_glasses_unit")}
                />
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                {t("summary_total_kcal_month")}:{" "}
                <span className="font-mono text-[var(--foreground)]">
                  {Math.round(monthStats.totalCal).toLocaleString(lang)}
                </span>{" "}
                {t("kcal")}
              </p>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-2)]">
                <h2 className="font-display text-sm font-semibold mb-4">{t("summary_weight_by_days")}</h2>
                {monthStats.weightTrend.length ? (
                  <div className="h-64 w-full min-w-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={monthStats.weightTrend}>
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                          tickFormatter={(v) => {
                            try {
                              return new Date(v).toLocaleDateString(lang, {
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
                            `${Number(value ?? 0).toFixed(1)} ${t("common_kg")}`,
                            t("summary_tooltip_series_weight"),
                          ]}
                        />
                        <Bar dataKey="weight" fill={CHART_COLOR} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_no_weight")}</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="font-display text-sm font-semibold mb-3">{t("summary_top_trainings")}</h2>
                {monthStats.top5.length ? (
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    {monthStats.top5.map((row, i) => (
                      <li key={`${row.training_name}-${i}`} className="text-[var(--foreground)]">
                        <span className="font-medium">{row.training_name}</span>
                        <span className="text-[var(--muted)] font-mono ml-2">
                          {Math.round(row.total_cal)} {t("kcal")} · {row.cnt}×
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_no_data")}</p>
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
              {t("summary_year")}
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
              {t("summary_btn_refresh")}
            </button>
          </div>

          {loading && !yearData && (
            <p className="text-sm text-[var(--muted-foreground)]">{t("summary_loading")}</p>
          )}

          {yearData && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatBox
                  label={t("summary_year_label_total_kcal")}
                  value={Math.round(yearData.food.cal)}
                  unit={t("kcal")}
                />
                <StatBox
                  label={`${t("summary_avg_kcal_per_day")} *`}
                  value={
                    yearData.food.cal > 0
                      ? (yearData.food.cal / 365).toFixed(0)
                      : "0"
                  }
                  unit={t("summary_year_avg_note")}
                />
                <StatBox
                  label={t("summary_train_kcal")}
                  value={Math.round(yearData.training.cal)}
                  unit={t("kcal")}
                />
                <StatBox
                  label={t("summary_train_duration_full")}
                  value={Math.round(yearData.training.duration)}
                  unit={t("min")}
                />
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">
                {t("summary_year_label_water")}{" "}
                <span className="font-mono text-[var(--foreground)]">{yearData.water_total}</span>{" "}
                {t("summary_glasses_unit")}
              </p>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-2)]">
                <h2 className="font-display text-sm font-semibold mb-4">
                  {t("summary_avg_kcal_chart_title")}
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
                            t("summary_chart_formatter_kcal_day", { n: Math.round(Number(value ?? 0)) }),
                            t("summary_tooltip_series_avg"),
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
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_no_food")}</p>
                )}
              </div>

              <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
                <h2 className="font-display text-sm font-semibold mb-3">{t("summary_top_trainings_year")}</h2>
                {yearData.top5_training.length ? (
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    {yearData.top5_training.map((row, i) => (
                      <li key={`${row.training_name}-${i}`}>
                        <span className="font-medium">{row.training_name}</span>
                        <span className="text-[var(--muted)] font-mono ml-2">
                          {Math.round(row.total_cal)} {t("kcal")} · {row.cnt}×
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">{t("summary_no_data")}</p>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
