"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "motion/react";
import { Icon } from "@iconify/react";
import { api } from "@/lib/api";
import { ScrollReveal } from "@/components/motion/ScrollReveal";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { Sticker } from "@/components/hand/Sticker";
import { Highlight } from "@/components/hand/Highlight";
import { Scribble } from "@/components/hand/Scribble";

interface DigestResponse {
  stats: {
    period: { from: string; to: string };
    goal: string | null;
    daily_cal_target: number | null;
    food: {
      total_cal: number;
      avg_daily_cal: number;
      days_logged: number;
      entries: number;
      protein_g: number;
      fat_g: number;
      carbs_g: number;
    };
    water: {
      glasses_total: number;
      days_logged: number;
      avg_daily: number;
    };
    workouts: {
      sessions: number;
      minutes: number;
      cal_burned: number;
    };
    weight_recent: { date: string; weight: number }[];
  };
  digest: {
    summary: string;
    wins: string[];
    focus: string[];
    tip: string;
  } | null;
  message?: string;
}

export default function DigestPage() {
  const [data, setData] = useState<DigestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api<DigestResponse>("/api/digest/weekly");
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-8">
      <ScrollReveal>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
            Итог недели
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
            <Highlight color="oklch(75% 0.13 150 / 0.45)">
              <span className="px-1">дайджест</span>
            </Highlight>
          </h1>
          <p
            className="text-sm text-[var(--muted-foreground)] mt-3"
            style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "15px" }}
          >
            — смотрю на цифры последних 7 дней и говорю, что круто, а куда тянуть
          </p>
        </div>
      </ScrollReveal>

      {loading && (
        <div className="card-base p-6">
          <div className="skeleton h-48 w-full rounded-[var(--radius)]" />
        </div>
      )}

      {error && <p className="text-sm text-[var(--destructive)]">{error}</p>}

      {!loading && data && !data.digest && (
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
                Пока данных мало
              </p>
              <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[52ch]">
                {data.message ?? "Добавь еду, воду или тренировку — и я соберу дайджест"}
              </p>
            </div>
          </div>
        </ScrollReveal>
      )}

      {!loading && data?.digest && (
        <>
          <ScrollReveal delay={0.05}>
            <div className="card-base p-6 sm:p-8 relative overflow-hidden">
              <div
                className="pointer-events-none absolute -top-20 -right-20 w-72 h-72 rounded-full blur-3xl opacity-15"
                style={{ background: "var(--accent)" }}
                aria-hidden
              />
              <div className="flex items-start gap-3 mb-4">
                <Icon
                  icon="solar:letter-opened-bold-duotone"
                  width={32}
                  className="text-[var(--accent)] shrink-0 mt-1"
                />
                <p
                  className="text-xl sm:text-2xl leading-relaxed text-[var(--foreground)]"
                  style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.01em" }}
                >
                  {data.digest.summary}
                </p>
              </div>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ScrollReveal delay={0.1}>
              <div className="card-base p-6 h-full">
                <div className="flex items-center gap-2 mb-3">
                  <Sticker color="sage" font="arkhip" size="sm" rotate={-1.5}>
                    ты молодец
                  </Sticker>
                </div>
                <ul className="space-y-3 mt-4">
                  {data.digest.wins.map((w, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 + i * 0.08 }}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Icon
                        icon="solar:check-circle-bold-duotone"
                        width={20}
                        className="text-[var(--color-sage)] shrink-0 mt-0.5"
                      />
                      <span>{w}</span>
                    </motion.li>
                  ))}
                  {data.digest.wins.length === 0 && (
                    <li className="text-sm text-[var(--muted-foreground)] italic">
                      — пока без очевидных побед. Следующую неделю закроем
                    </li>
                  )}
                </ul>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={0.15}>
              <div className="card-base p-6 h-full">
                <div className="flex items-center gap-2 mb-3">
                  <Sticker color="amber" font="arkhip" size="sm" rotate={1.5}>
                    точки роста
                  </Sticker>
                </div>
                <ul className="space-y-3 mt-4">
                  {data.digest.focus.map((f, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.15 + i * 0.08 }}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Icon
                        icon="solar:target-bold-duotone"
                        width={20}
                        className="text-[var(--warning)] shrink-0 mt-0.5"
                      />
                      <span>{f}</span>
                    </motion.li>
                  ))}
                  {data.digest.focus.length === 0 && (
                    <li className="text-sm text-[var(--muted-foreground)] italic">
                      — всё в порядке, держи темп
                    </li>
                  )}
                </ul>
              </div>
            </ScrollReveal>
          </div>

          {data.digest.tip && (
            <ScrollReveal delay={0.2}>
              <div
                className="card-base p-5 border-2 border-dashed"
                style={{
                  borderColor: "var(--accent)",
                  background: "color-mix(in oklch, var(--accent) 6%, var(--card))",
                }}
              >
                <div className="flex items-start gap-3">
                  <Icon
                    icon="solar:lightbulb-bolt-bold-duotone"
                    width={28}
                    className="text-[var(--accent)] shrink-0"
                  />
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
                      совет на неделю
                    </p>
                    <p
                      className="text-base"
                      style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "17px" }}
                    >
                      {data.digest.tip}
                    </p>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          )}

          {/* Raw numbers */}
          <ScrollReveal delay={0.25}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatBlock
                icon="solar:plate-bold-duotone"
                label="Записей еды"
                value={data.stats.food.entries}
                hint={`${data.stats.food.days_logged} из 7 дней`}
              />
              <StatBlock
                icon="solar:glass-water-bold-duotone"
                label="Стаканов воды"
                value={data.stats.water.glasses_total}
                hint={`≈ ${data.stats.water.avg_daily}/день`}
              />
              <StatBlock
                icon="solar:dumbbell-large-bold-duotone"
                label="Тренировок"
                value={data.stats.workouts.sessions}
                hint={`${data.stats.workouts.minutes} минут`}
              />
              <StatBlock
                icon="solar:fire-bold-duotone"
                label="Сжёг на тренировках"
                value={data.stats.workouts.cal_burned}
                hint="ккал"
              />
            </div>
          </ScrollReveal>
        </>
      )}
    </div>
  );
}

function StatBlock({
  icon,
  label,
  value,
  hint,
}: {
  icon: string;
  label: string;
  value: number;
  hint: string;
}) {
  return (
    <div className="card-base p-4">
      <div className="flex items-center gap-2">
        <Icon icon={icon} width={22} className="text-[var(--accent)]" />
        <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
          {label}
        </p>
      </div>
      <p
        className="display-number text-3xl mt-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <AnimatedNumber value={value} />
      </p>
      <p className="text-xs text-[var(--muted)] mt-0.5">{hint}</p>
    </div>
  );
}
