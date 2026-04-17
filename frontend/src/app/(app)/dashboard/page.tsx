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
import { handleActivityResponse, type StreakDTO, type BadgeDTO, useLoadStreak, useStreakStore } from "@/lib/streaks";
import { HandDrawnUnderline } from "@/components/hand/HandDrawnUnderline";
import { Highlight } from "@/components/hand/Highlight";
import { HandArrow } from "@/components/hand/HandArrow";
import { Scribble } from "@/components/hand/Scribble";
import { Sticker } from "@/components/hand/Sticker";
import { greeting, heroSubtitle, EMPTY_COPY, CTA } from "@/lib/copy";

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
        <AnimatedNumber value={count * 300} />{" "}
        <span
          className="text-sm text-[var(--muted)] font-normal"
          style={{ fontFamily: "var(--font-body)" }}
        >
          мл
        </span>
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
        {adding ? CTA.add_water_loading : done ? CTA.add_water_done : CTA.add_water}
      </motion.button>
    </div>
  );
}

export default function DashboardPage() {
  useLoadStreak();
  const { streak } = useStreakStore();
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
      const res = await api<{
        count: number;
        ml: number;
        streak?: StreakDTO | null;
        newly_earned_badges?: BadgeDTO[] | null;
      }>("/api/water", { method: "POST" });
      handleActivityResponse(res);
      const updated = await api<DashboardData>(
        "/api/summary/day?date=" + todayStr,
      );
      setData(updated);
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
        <div className="skeleton h-24 w-full max-w-3xl rounded-[var(--radius-xl)]" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="skeleton h-48 lg:col-span-2 rounded-[var(--radius-lg)]" />
          <div className="skeleton h-48 rounded-[var(--radius-lg)]" />
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
        <Scribble
          variant="empty-plate"
          className="w-32 h-32 mx-auto text-[var(--destructive)] mb-4"
        />
        <p className="text-sm text-[var(--destructive)]">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 text-sm text-[var(--accent)] hover:underline"
        >
          {CTA.try_again}
        </button>
      </div>
    );
  }

  const dailyCal = profile?.daily_cal || 2200;
  const proteinTarget = Math.round((dailyCal * 0.3) / 4);
  const fatTarget = Math.round((dailyCal * 0.25) / 9);
  const carbsTarget = Math.round((dailyCal * 0.45) / 4);

  const foodCal = data?.food.cal || 0;
  const trainCal = data?.training.cal || 0;
  const net = Math.round(foodCal - trainCal);
  const left = Math.max(dailyCal - net, 0);

  const now = new Date();
  const hello = greeting();
  const subtitle = heroSubtitle({
    caloriesEaten: foodCal,
    caloriesTarget: dailyCal,
    waterGlasses: data?.water || 0,
    workouts: data?.training_items.length || 0,
  });

  return (
    <div className="space-y-12">
      {/* ============= HERO — asymmetric, hand-drawn accents ============= */}
      <ScrollReveal>
        <div className="relative pt-2">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
            <div className="lg:max-w-[70%]">
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-3">
                {now.toLocaleDateString("ru-RU", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                })}
              </p>
              <h1
                className="text-[var(--foreground)]"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "clamp(2.75rem, 2rem + 4vw, 5rem)",
                  letterSpacing: "-0.03em",
                  lineHeight: 0.92,
                }}
              >
                {hello}
                {profile?.user_name ? (
                  <>
                    ,
                    <br />
                    <span className="relative inline-block">
                      <span className="text-[var(--accent)]">
                        {profile.user_name}
                      </span>
                      <HandDrawnUnderline
                        color="var(--accent)"
                        strokeWidth={4}
                        variant={
                          ((profile.user_name.length % 4) + 1) as 1 | 2 | 3 | 4
                        }
                        className="absolute left-0 -bottom-2 w-full h-3"
                      />
                    </span>
                  </>
                ) : (
                  "!"
                )}
              </h1>
              <p
                className="mt-5 text-lg text-[var(--muted)] max-w-[44ch]"
                style={{ fontFamily: "var(--font-body)" }}
              >
                {subtitle}
              </p>
            </div>

            {/* Right-side live ticker — looks hand-pinned */}
            <div className="relative shrink-0 flex flex-col gap-5">
              <div
                className="relative inline-flex flex-col items-start gap-2 pr-6"
                style={{ transform: "rotate(-1.2deg)" }}
              >
                <Sticker color="cream" font="arkhip" size="sm" rotate={-2}>
                  заметка дня
                </Sticker>
                <div
                  className="flex items-baseline gap-2"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  <span className="display-number text-6xl text-[var(--foreground)]">
                    <AnimatedNumber value={left} />
                  </span>
                  <span className="text-sm text-[var(--muted)]" style={{ fontFamily: "var(--font-body)" }}>
                    ккал до нормы
                  </span>
                </div>
                <p
                  className="text-xs text-[var(--muted-foreground)]"
                  style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "14px" }}
                >
                  съел {Math.round(foodCal)} · сжёг {Math.round(trainCal)}
                </p>
              </div>

              {streak && streak.current >= 2 && (
                <a
                  href="/achievements"
                  className="relative inline-flex items-center gap-3 pl-3 pr-4 py-2 rounded-[var(--radius-lg)] bg-gradient-to-br from-[var(--warning)]/15 to-[var(--accent)]/10 border border-[var(--warning)]/30 hover:border-[var(--warning)]/60 transition-colors"
                  style={{ transform: "rotate(1deg)" }}
                >
                  <Icon
                    icon="solar:fire-bold-duotone"
                    width={28}
                    className={
                      streak.status === "at_risk"
                        ? "text-[var(--destructive)]"
                        : "text-[var(--warning)]"
                    }
                  />
                  <div className="leading-tight">
                    <p
                      className="display-number text-2xl tabular-nums"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {streak.current}
                    </p>
                    <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                      {streak.status === "at_risk" ? "streak горит" : "дней подряд"}
                    </p>
                  </div>
                </a>
              )}
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* ============= METRICS — 1 big + 3 small asymmetric ============= */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 auto-rows-fr">
        <ScrollReveal delay={0.05} className="col-span-2 lg:row-span-2">
          <MetricCard
            label="Съел сегодня"
            value={foodCal}
            target={dailyCal}
            unit="ккал"
            color="var(--accent)"
            big
            note={
              foodCal > 0
                ? `${Math.round((foodCal / dailyCal) * 100)}% нормы`
                : "ещё ничего"
            }
          />
        </ScrollReveal>
        <ScrollReveal delay={0.1}>
          <MetricCard
            label="Белки"
            value={data?.food.protein || 0}
            target={proteinTarget}
            unit="г"
            color="var(--success)"
          />
        </ScrollReveal>
        <ScrollReveal delay={0.15}>
          <MetricCard
            label="Жиры"
            value={data?.food.fat || 0}
            target={fatTarget}
            unit="г"
            color="var(--warning)"
          />
        </ScrollReveal>
        <ScrollReveal delay={0.2} className="col-span-2 lg:col-span-2">
          <MetricCard
            label="Углеводы"
            value={data?.food.carbs || 0}
            target={carbsTarget}
            unit="г"
            color="var(--accent)"
          />
        </ScrollReveal>
      </div>

      {/* ============= BOTTOM ROW — workouts + water ============= */}
      <div className="grid lg:grid-cols-3 gap-6">
        <ScrollReveal className="lg:col-span-2" delay={0.05}>
          <div className="card-base p-6 h-full relative">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Icon
                  icon="solar:dumbbell-large-bold-duotone"
                  width={22}
                  className="text-[var(--accent)]"
                />
                <h2
                  className="text-2xl text-[var(--foreground)]"
                  style={{
                    fontFamily: "var(--font-display)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  Тренировки
                </h2>
              </div>
              {data?.training_items.length ? (
                <Sticker color="sage" size="sm" rotate={3}>
                  {data.training_items.length} шт
                </Sticker>
              ) : null}
            </div>

            {data?.training_items.length ? (
              <div className="space-y-2">
                {data.training_items.map((t, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05, duration: 0.4 }}
                    className="flex items-center justify-between py-2.5 border-b border-dashed border-[var(--border)] last:border-0"
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
                  <span
                    className="display-number text-xl"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    <AnimatedNumber value={Math.round(trainCal)} />{" "}
                    <span
                      className="text-sm text-[var(--muted)] font-normal"
                      style={{ fontFamily: "var(--font-body)" }}
                    >
                      ккал
                    </span>
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-6 py-4">
                <Scribble
                  variant="empty-dumbbell"
                  className="w-24 h-16 shrink-0 text-[var(--color-latte)]"
                />
                <div>
                  <p
                    className="text-lg"
                    style={{
                      fontFamily: "var(--font-display)",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {EMPTY_COPY.workouts_today.title}
                  </p>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[36ch]">
                    {EMPTY_COPY.workouts_today.subtitle}
                  </p>
                </div>
              </div>
            )}
          </div>
        </ScrollReveal>

        {/* Water */}
        <ScrollReveal delay={0.1}>
          <div className="card-base p-6 h-full relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Icon
                  icon="solar:cup-bold-duotone"
                  width={22}
                  className="text-[var(--accent)]"
                />
                <h2
                  className="text-2xl text-[var(--foreground)]"
                  style={{
                    fontFamily: "var(--font-display)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  Вода
                </h2>
              </div>
              {(data?.water ?? 0) === 0 && (
                <HandArrow
                  variant="curve-down"
                  className="absolute right-8 top-14 w-8 h-16 text-[var(--accent)] opacity-60"
                />
              )}
            </div>
            <WaterWidget
              count={data?.water || 0}
              adding={waterAdding}
              onAdd={addWater}
            />
          </div>
        </ScrollReveal>
      </div>

      {/* ============= FOOD TABLE ============= */}
      <ScrollReveal delay={0.12}>
        <div className="card-base p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Icon
                icon="solar:plate-bold-duotone"
                width={22}
                className="text-[var(--accent)]"
              />
              <h2
                className="text-2xl text-[var(--foreground)]"
                style={{
                  fontFamily: "var(--font-display)",
                  letterSpacing: "-0.02em",
                }}
              >
                Что поел
              </h2>
            </div>
            {data?.food_items.length ? (
              <Sticker color="amber" size="sm" rotate={-4} font="appetite">
                {data.food_items.length} {data.food_items.length === 1 ? "блюдо" : "блюд"}
              </Sticker>
            ) : null}
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
                      className="border-t border-dashed border-[var(--border)] hover:bg-[var(--color-sand)]/40 transition-colors"
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
              <div className="flex flex-col md:flex-row items-start md:items-center gap-6 py-4">
                <Scribble
                  variant="empty-plate"
                  className="w-28 h-28 shrink-0 text-[var(--color-latte)]"
                />
                <div className="flex-1">
                  <p
                    className="text-2xl"
                    style={{
                      fontFamily: "var(--font-display)",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    <Highlight color="oklch(72% 0.15 80 / 0.35)">
                      {EMPTY_COPY.food_today.title}
                    </Highlight>
                  </p>
                  <p className="text-sm text-[var(--muted-foreground)] mt-2 max-w-[48ch]">
                    {EMPTY_COPY.food_today.subtitle}
                  </p>
                  <div className="flex flex-wrap gap-3 mt-3">
                    <a
                      href="/food"
                      className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--accent)] hover:text-[var(--accent-hover)]"
                    >
                      <Icon icon="solar:arrow-right-bold-duotone" width={16} />
                      {EMPTY_COPY.food_today.cta}
                    </a>
                    <span className="text-[var(--muted-foreground)]">·</span>
                    <a
                      href="/food?tab=repeat"
                      className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--muted)] hover:text-[var(--foreground)]"
                    >
                      <Icon icon="solar:refresh-circle-bold-duotone" width={16} />
                      Как вчера
                    </a>
                  </div>
                </div>
              </div>
            )}
        </div>
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <a
            href="/weight"
            className="card-base card-hover p-5 flex items-center gap-4 group"
          >
            <div
              className="w-12 h-12 rounded-[var(--radius)] flex items-center justify-center"
              style={{ background: "color-mix(in oklch, var(--accent) 12%, transparent)" }}
            >
              <Icon icon="solar:scale-bold-duotone" width={26} className="text-[var(--accent)]" />
            </div>
            <div className="flex-1 min-w-0">
              <p
                className="text-lg"
                style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
              >
                График веса
              </p>
              <p className="text-xs text-[var(--muted-foreground)]">
                с AI-прогнозом тренда
              </p>
            </div>
            <Icon
              icon="solar:arrow-right-linear"
              width={18}
              className="text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-1 transition"
            />
          </a>

          <a
            href="/digest"
            className="card-base card-hover p-5 flex items-center gap-4 group"
          >
            <div
              className="w-12 h-12 rounded-[var(--radius)] flex items-center justify-center"
              style={{ background: "color-mix(in oklch, var(--color-sage) 18%, transparent)" }}
            >
              <Icon
                icon="solar:letter-opened-bold-duotone"
                width={26}
                className="text-[var(--color-sage)]"
              />
            </div>
            <div className="flex-1 min-w-0">
              <p
                className="text-lg"
                style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
              >
                Дайджест недели
              </p>
              <p className="text-xs text-[var(--muted-foreground)]">
                AI разбирает последние 7 дней
              </p>
            </div>
            <Icon
              icon="solar:arrow-right-linear"
              width={18}
              className="text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-1 transition"
            />
          </a>
        </div>
      </ScrollReveal>
    </div>
  );
}
