"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import MetricCard from "@/components/dashboard/MetricCard";
import { Plus, Loader2 } from "lucide-react";

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

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [waterAdding, setWaterAdding] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api<DashboardData>("/api/summary/day?date=" + new Date().toISOString().split("T")[0]),
      api<Profile>("/api/users/me"),
    ])
      .then(([summary, prof]) => {
        setData(summary);
        setProfile(prof);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Не удалось загрузить данные"))
      .finally(() => setLoading(false));
  }, []);

  async function addWater() {
    setWaterAdding(true);
    try {
      await api("/api/water", { method: "POST" });
      const updated = await api<DashboardData>("/api/summary/day?date=" + new Date().toISOString().split("T")[0]);
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

        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)]">
          <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-4">
            Вода
          </h2>
          <p className="font-mono text-4xl font-bold text-[var(--foreground)] leading-none">
            {data?.water || 0}
          </p>
          <p className="text-sm text-[var(--muted)] mt-1 mb-4">
            стаканов ({(data?.water || 0) * 300} мл)
          </p>
          <button
            onClick={addWater}
            disabled={waterAdding}
            className="flex items-center gap-2 w-full justify-center py-2.5 bg-[var(--accent)] text-white font-medium rounded-[var(--radius)] hover:bg-[var(--accent-hover)] transition-colors active:scale-[0.97] disabled:opacity-50"
          >
            {waterAdding ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            Добавить стакан
          </button>
        </div>
      </div>

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
