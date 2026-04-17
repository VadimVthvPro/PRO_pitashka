"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import MetricCard from "@/components/dashboard/MetricCard";
import { Plus, Loader2, Droplets, Check } from "lucide-react";

const WATER_TARGET = 8;

interface DashboardData {
  food: { cal: number; protein: number; fat: number; carbs: number };
  food_items: { name_of_food: string; b: number; g: number; u: number; cal: number }[];
  training: { cal: number; duration: number };
  training_items: { training_name: string; tren_time: number; training_cal: number }[];
  water: number;
}

interface Profile {
  user_name?: string;
  daily_cal?: number;
}

function WaterRing({ count, adding, onAdd }: { count: number; adding: boolean; onAdd: () => void }) {
  const progress = Math.min(count / WATER_TARGET, 1);
  const size = 160;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - progress);
  const done = count >= WATER_TARGET;

  return (
    <div className="flex flex-col items-center">
      <div className="relative mb-4" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[-90deg]">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-sand)" strokeWidth={stroke} />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke={done ? "var(--success)" : "var(--accent)"}
            strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-500 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-4xl font-bold text-[var(--foreground)] tabular-nums">{count}</span>
          <span className="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wide">из {WATER_TARGET}</span>
        </div>
      </div>
      <p className="font-mono text-lg font-semibold text-[var(--foreground)]">
        {count * 300} <span className="text-sm font-medium text-[var(--muted)]">мл</span>
      </p>
      <button
        onClick={onAdd}
        disabled={adding}
        className={`mt-4 flex items-center gap-2 w-full justify-center py-3 font-semibold rounded-[var(--radius-lg)] transition-all active:scale-[0.97] disabled:opacity-50 ${
          done
            ? "bg-[var(--success)]/15 text-[var(--success)] border border-[var(--success)]/30"
            : "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] shadow-[var(--shadow-1)]"
        }`}
      >
        {adding ? <Loader2 size={18} className="animate-spin" /> : done ? <Check size={18} /> : <Droplets size={18} />}
        {adding ? "Добавление…" : done ? "Норма выполнена!" : "+ Стакан воды"}
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [waterAdding, setWaterAdding] = useState(false);

  const todayStr = new Date().toISOString().split("T")[0];

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api<DashboardData>("/api/summary/day?date=" + todayStr),
      api<Profile>("/api/users/me"),
    ])
      .then(([summary, prof]) => {
        setData(summary);
        setProfile(prof);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Не удалось загрузить данные"))
      .finally(() => setLoading(false));
  }, [todayStr]);

  async function addWater() {
    setWaterAdding(true);
    try {
      await api("/api/water", { method: "POST" });
      const updated = await api<DashboardData>("/api/summary/day?date=" + todayStr);
      setData(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить воду");
    } finally {
      setWaterAdding(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-[var(--accent)]" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-[var(--destructive)]">{error}</p>
        <button onClick={() => window.location.reload()} className="mt-4 text-sm text-[var(--accent)] hover:underline">
          Попробовать снова
        </button>
      </div>
    );
  }

  const dailyCal = profile?.daily_cal || 2200;
  const proteinTarget = Math.round(dailyCal * 0.3 / 4);
  const fatTarget = Math.round(dailyCal * 0.25 / 9);
  const carbsTarget = Math.round(dailyCal * 0.45 / 4);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold">
          Привет{profile?.user_name ? `, ${profile.user_name}` : ""}!
        </h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {new Date().toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Калории" value={data?.food.cal || 0} target={dailyCal} unit="ккал" color="var(--accent)" />
        <MetricCard label="Белки" value={data?.food.protein || 0} target={proteinTarget} unit="г" color="var(--success)" />
        <MetricCard label="Жиры" value={data?.food.fat || 0} target={fatTarget} unit="г" color="var(--warning)" />
        <MetricCard label="Углеводы" value={data?.food.carbs || 0} target={carbsTarget} unit="г" color="var(--accent)" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Тренировки */}
        <div className="lg:col-span-2 bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
          <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
            Тренировки сегодня
          </h2>
          {data?.training_items.length ? (
            <div className="space-y-2">
              {data.training_items.map((t, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                  <span className="text-sm">{t.training_name}</span>
                  <div className="flex gap-4 text-sm">
                    <span className="text-[var(--muted)]">{t.tren_time} мин</span>
                    <span className="font-mono font-medium">{Math.round(t.training_cal)} ккал</span>
                  </div>
                </div>
              ))}
              <div className="pt-2 flex justify-between font-medium">
                <span>Итого</span>
                <span className="font-mono">{Math.round(data.training.cal)} ккал</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Нет тренировок за сегодня</p>
          )}
        </div>

        {/* Вода — полноценный виджет */}
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
          <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
            <Droplets size={13} className="inline mr-1.5 -mt-0.5" />
            Вода
          </h2>
          <WaterRing count={data?.water || 0} adding={waterAdding} onAdd={addWater} />
        </div>
      </div>

      {/* Еда */}
      <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
        <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
          Еда сегодня
        </h2>
        {data?.food_items.length ? (
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
                {data.food_items.map((f, i) => (
                  <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/50">
                    <td className="py-2">{f.name_of_food}</td>
                    <td className="py-2 text-right font-mono text-xs">{Math.round(f.b)}</td>
                    <td className="py-2 text-right font-mono text-xs">{Math.round(f.g)}</td>
                    <td className="py-2 text-right font-mono text-xs">{Math.round(f.u)}</td>
                    <td className="py-2 text-right font-mono text-xs font-medium">{Math.round(f.cal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted-foreground)]">Нет записей за сегодня</p>
        )}
      </div>
    </div>
  );
}
