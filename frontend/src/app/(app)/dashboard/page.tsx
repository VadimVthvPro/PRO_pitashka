"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import MetricCard from "@/components/dashboard/MetricCard";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { ScrollReveal, Stagger, StaggerItem } from "@/components/motion/ScrollReveal";
import { WaterWave } from "@/components/water/WaterWave";
import { fireConfetti } from "@/components/motion/confetti";

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

function WaterWidget({
  count,
  adding,
  onAdd,
}: {
  count: number;
  adding: boolean;
  onAdd: () => void;
}) {
  const done = count >= WATER_TARGET;
  return (
    <div className="flex flex-col items-center">
      <WaterWave glasses={count} goal={WATER_TARGET} size={200} />
      <p
        className="display-number text-2xl text-[var(--foreground)] mt-4 tabular-nums"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <AnimatedNumber value={count * 300} /> <span className="text-sm text-[var(--muted)] font-normal" style={{ fontFamily: "var(--font-body)" }}>мл</span>
      </p>
      <motion.button
        whileHover={{ scale: adding ? 1 : 1.02 }}
        whileTap={{ scale: 0.97 }}
        onClick={onAdd}
        disabled={adding}
        className={`mt-5 flex items-center justify-center gap-2 w-full py-3 font-semibold rounded-[var(--radius-lg)] transition-colors disabled:opacity-60 ${
          done
            ? "bg-[var(--success)]/15 text-[var(--success)] border border-[var(--success)]/30"
            : "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] shadow-[var(--shadow-accent)]"
        }`}
      >
        {adding ? (
          <Icon icon="svg-spinners:180-ring" width={18} />
        ) : done ? (
          <Icon icon="solar:check-circle-bold-duotone" width={20} />
        ) : (
          <Icon icon="solar:cup-bold-duotone" width={20} />
        )}
        {adding ? "Добавляем…" : done ? "Норма выполнена!" : "+ Стакан воды"}
      </motion.button>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [waterAdding, setWaterAdding] = useState(false);
  const hitWaterGoal = useRef(false);

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
        if (summary.water >= WATER_TARGET) hitWaterGoal.current = true;
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Не удалось загрузить данные"),
      )
      .finally(() => setLoading(false));
  }, [todayStr]);

  async function addWater() {
    setWaterAdding(true);
    try {
      await api("/api/water", { method: "POST" });
      const updated = await api<DashboardData>("/api/summary/day?date=" + todayStr);
      setData(updated);
      // Fire confetti the first time the daily goal is reached
      if (updated.water >= WATER_TARGET && !hitWaterGoal.current) {
        hitWaterGoal.current = true;
        setTimeout(() => fireConfetti({ y: 0.4 }), 120);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить воду");
    } finally {
      setWaterAdding(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="skeleton h-12 w-72" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-36 rounded-[var(--radius-lg)]" />
          ))}
        </div>
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="skeleton h-56 lg:col-span-2 rounded-[var(--radius-lg)]" />
          <div className="skeleton h-56 rounded-[var(--radius-lg)]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <Icon
          icon="solar:sad-circle-bold-duotone"
          width={56}
          className="mx-auto text-[var(--destructive)] mb-4"
        />
        <p className="text-sm text-[var(--destructive)]">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 text-sm text-[var(--accent)] hover:underline"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  const dailyCal = profile?.daily_cal || 2200;
  const proteinTarget = Math.round((dailyCal * 0.3) / 4);
  const fatTarget = Math.round((dailyCal * 0.25) / 9);
  const carbsTarget = Math.round((dailyCal * 0.45) / 4);

  const now = new Date();
  const hour = now.getHours();
  const greeting =
    hour < 6
      ? "Доброй ночи"
      : hour < 12
      ? "Доброе утро"
      : hour < 18
      ? "Добрый день"
      : "Добрый вечер";

  return (
    <div className="space-y-10">
      {/* Hero */}
      <ScrollReveal>
        <div className="relative rounded-[var(--radius-xl)] mesh-hero p-8 overflow-hidden border border-[var(--card-border)] shadow-[var(--shadow-1)]">
          <motion.div
            aria-hidden
            className="absolute -right-10 -bottom-10 w-64 h-64 rounded-full blur-3xl opacity-30"
            style={{ background: "oklch(58% 0.16 35)" }}
            animate={{ scale: [1, 1.08, 1], rotate: [0, 8, 0] }}
            transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
          />
          <p className="relative text-xs uppercase tracking-widest text-[var(--muted)] mb-2">
            {now.toLocaleDateString("ru-RU", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}
          </p>
          <h1
            className="relative text-5xl md:text-6xl text-[var(--foreground)]"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.025em",
              lineHeight: 0.95,
            }}
          >
            {greeting}
            {profile?.user_name ? (
              <>
                ,<br />
                <span className="text-[var(--accent)]">{profile.user_name}</span>
              </>
            ) : (
              "!"
            )}
          </h1>
        </div>
      </ScrollReveal>

      {/* Metrics */}
      <Stagger className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StaggerItem>
          <MetricCard
            label="Калории"
            value={data?.food.cal || 0}
            target={dailyCal}
            unit="ккал"
            color="var(--accent)"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Белки"
            value={data?.food.protein || 0}
            target={proteinTarget}
            unit="г"
            color="var(--success)"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Жиры"
            value={data?.food.fat || 0}
            target={fatTarget}
            unit="г"
            color="var(--warning)"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Углеводы"
            value={data?.food.carbs || 0}
            target={carbsTarget}
            unit="г"
            color="var(--accent)"
          />
        </StaggerItem>
      </Stagger>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Тренировки */}
        <ScrollReveal className="lg:col-span-2" delay={0.05}>
          <div className="card-base p-6 h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-medium uppercase tracking-widest text-[var(--muted-foreground)]">
                Тренировки сегодня
              </h2>
              <Icon
                icon="solar:dumbbell-large-bold-duotone"
                width={22}
                className="text-[var(--accent)]"
              />
            </div>
            {data?.training_items.length ? (
              <div className="space-y-2">
                {data.training_items.map((t, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05, duration: 0.4 }}
                    className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0"
                  >
                    <span className="text-sm">{t.training_name}</span>
                    <div className="flex gap-4 text-sm">
                      <span className="text-[var(--muted)]">{t.tren_time} мин</span>
                      <span className="font-mono font-medium tabular-nums">
                        {Math.round(t.training_cal)} ккал
                      </span>
                    </div>
                  </motion.div>
                ))}
                <div className="pt-3 flex justify-between font-semibold">
                  <span>Итого</span>
                  <span className="display-number text-xl">
                    <AnimatedNumber value={Math.round(data.training.cal)} /> ккал
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">
                Нет тренировок за сегодня
              </p>
            )}
          </div>
        </ScrollReveal>

        {/* Вода */}
        <ScrollReveal delay={0.1}>
          <div className="card-base p-6 h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-medium uppercase tracking-widest text-[var(--muted-foreground)]">
                Вода
              </h2>
              <Icon
                icon="solar:cup-bold-duotone"
                width={22}
                className="text-[var(--accent)]"
              />
            </div>
            <WaterWidget
              count={data?.water || 0}
              adding={waterAdding}
              onAdd={addWater}
            />
          </div>
        </ScrollReveal>
      </div>

      {/* Еда */}
      <ScrollReveal delay={0.12}>
        <div className="card-base p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-medium uppercase tracking-widest text-[var(--muted-foreground)]">
              Еда сегодня
            </h2>
            <Icon
              icon="solar:plate-bold-duotone"
              width={22}
              className="text-[var(--accent)]"
            />
          </div>
          {data?.food_items.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[10px] font-medium uppercase tracking-widest text-[var(--muted-foreground)]">
                    <th className="pb-3">Блюдо</th>
                    <th className="pb-3 text-right">Б</th>
                    <th className="pb-3 text-right">Ж</th>
                    <th className="pb-3 text-right">У</th>
                    <th className="pb-3 text-right">Ккал</th>
                  </tr>
                </thead>
                <tbody>
                  {data.food_items.map((f, i) => (
                    <motion.tr
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04, duration: 0.35 }}
                      className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/40 transition-colors"
                    >
                      <td className="py-2.5">{f.name_of_food}</td>
                      <td className="py-2.5 text-right font-mono text-xs tabular-nums">
                        {Math.round(f.b)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-xs tabular-nums">
                        {Math.round(f.g)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-xs tabular-nums">
                        {Math.round(f.u)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-xs font-medium tabular-nums">
                        {Math.round(f.cal)}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">
              Нет записей за сегодня
            </p>
          )}
        </div>
      </ScrollReveal>
    </div>
  );
}
