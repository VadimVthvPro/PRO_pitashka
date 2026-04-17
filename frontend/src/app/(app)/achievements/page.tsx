"use client";

import { useEffect, useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { api } from "@/lib/api";
import { type BadgeDTO, type StreakDTO, useLoadStreak, useStreakStore } from "@/lib/streaks";
import { ScrollReveal, Stagger, StaggerItem } from "@/components/motion/ScrollReveal";
import { Sticker } from "@/components/hand/Sticker";
import { Highlight } from "@/components/hand/Highlight";
import { Scribble } from "@/components/hand/Scribble";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";

interface BadgesOverview {
  earned: BadgeDTO[];
  locked: BadgeDTO[];
  total: number;
}

const TIER_BG: Record<BadgeDTO["tier"], string> = {
  bronze: "linear-gradient(135deg, oklch(78% 0.1 55), oklch(62% 0.12 55))",
  silver: "linear-gradient(135deg, oklch(88% 0.02 240), oklch(68% 0.03 240))",
  gold: "linear-gradient(135deg, oklch(85% 0.15 85), oklch(65% 0.16 80))",
  legend: "linear-gradient(135deg, oklch(68% 0.22 320), oklch(45% 0.22 320))",
};

const TIER_LABEL: Record<BadgeDTO["tier"], string> = {
  bronze: "Бронза",
  silver: "Серебро",
  gold: "Золото",
  legend: "Легенда",
};

function BadgeCard({ badge, earned }: { badge: BadgeDTO; earned: boolean }) {
  return (
    <motion.div
      whileHover={earned ? { y: -4, scale: 1.02 } : { y: -1 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="card-base card-hover p-5 h-full relative overflow-hidden"
      style={{
        opacity: earned ? 1 : 0.55,
        filter: earned ? "none" : "grayscale(0.7)",
      }}
    >
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{ background: TIER_BG[badge.tier] }}
        aria-hidden
      />
      <div className="relative flex items-start gap-4">
        <div
          className="shrink-0 w-14 h-14 rounded-full flex items-center justify-center text-white"
          style={{ background: TIER_BG[badge.tier] }}
        >
          <Icon icon={badge.icon} width={30} />
        </div>
        <div className="min-w-0 flex-1">
          <p
            className="text-[9px] uppercase tracking-[0.2em] font-semibold"
            style={{ color: "var(--muted-foreground)" }}
          >
            {TIER_LABEL[badge.tier]}
            {earned && badge.earned_at ? (
              <>
                {" · "}
                {new Date(badge.earned_at).toLocaleDateString("ru-RU", {
                  day: "numeric",
                  month: "short",
                })}
              </>
            ) : null}
          </p>
          <h3
            className="text-lg leading-tight mt-0.5"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.02em",
              fontWeight: 700,
            }}
          >
            {badge.title}
          </h3>
          <p className="text-xs text-[var(--muted)] mt-1.5 line-clamp-2">
            {badge.description}
          </p>
        </div>
      </div>
      {!earned && (
        <div className="absolute top-3 right-3 opacity-60">
          <Icon icon="solar:lock-keyhole-bold-duotone" width={18} className="text-[var(--muted)]" />
        </div>
      )}
    </motion.div>
  );
}

export default function AchievementsPage() {
  useLoadStreak();
  const { streak } = useStreakStore();

  const [data, setData] = useState<BadgesOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api<BadgesOverview>("/api/streaks/badges")
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Не удалось загрузить достижения");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const earnedCount = data?.earned.length ?? 0;
  const total = data?.total ?? 0;
  const percent = total > 0 ? Math.round((earnedCount / total) * 100) : 0;

  return (
    <div className="space-y-10">
      <ScrollReveal>
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              Коллекция
            </p>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(2.5rem, 1.8rem + 3vw, 4rem)",
                letterSpacing: "-0.03em",
                lineHeight: 0.92,
              }}
            >
              Твои{" "}
              <Highlight color="oklch(82% 0.15 85 / 0.5)">
                <span className="px-1">трофеи</span>
              </Highlight>
            </h1>
          </div>
          {streak && streak.current > 0 && <StreakBadgeSummary streak={streak} />}
        </div>
      </ScrollReveal>

      {/* Progress bar */}
      <ScrollReveal delay={0.05}>
        <div className="card-base p-6 relative overflow-hidden">
          <div
            className="pointer-events-none absolute -top-16 -right-16 w-64 h-64 rounded-full blur-3xl opacity-25"
            style={{ background: "var(--accent)" }}
            aria-hidden
          />
          <div className="relative flex items-end justify-between gap-4 flex-wrap mb-4">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
                Собрано
              </p>
              <p
                className="display-number text-6xl leading-none"
                style={{ fontFamily: "var(--font-display)" }}
              >
                <AnimatedNumber value={earnedCount} />
                <span
                  className="text-2xl text-[var(--muted)] font-normal ml-2"
                  style={{ fontFamily: "var(--font-body)" }}
                >
                  из {total}
                </span>
              </p>
            </div>
            <Sticker color="amber" font="appetite" rotate={3}>
              {percent}%
            </Sticker>
          </div>
          <div className="relative h-3 bg-[var(--color-sand)] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${percent}%` }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full"
              style={{
                background:
                  "linear-gradient(90deg, var(--accent), oklch(78% 0.15 85))",
              }}
            />
          </div>
        </div>
      </ScrollReveal>

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-[var(--radius-lg)]" />
          ))}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-6 py-6">
          <Scribble
            variant="circle"
            className="w-20 h-20 text-[var(--destructive)]"
          />
          <p className="text-sm text-[var(--destructive)]">{error}</p>
        </div>
      )}

      {!loading && !error && data && (
        <>
          {data.earned.length > 0 && (
            <ScrollReveal delay={0.1}>
              <h2
                className="text-2xl mb-5"
                style={{
                  fontFamily: "var(--font-display)",
                  letterSpacing: "-0.02em",
                }}
              >
                Уже твои
              </h2>
              <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.earned.map((b) => (
                  <StaggerItem key={b.code}>
                    <BadgeCard badge={b} earned />
                  </StaggerItem>
                ))}
              </Stagger>
            </ScrollReveal>
          )}

          {data.locked.length > 0 && (
            <ScrollReveal delay={0.15}>
              <h2
                className="text-2xl mb-5 mt-4"
                style={{
                  fontFamily: "var(--font-display)",
                  letterSpacing: "-0.02em",
                }}
              >
                Ещё в пути
              </h2>
              <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.locked.map((b) => (
                  <StaggerItem key={b.code}>
                    <BadgeCard badge={b} earned={false} />
                  </StaggerItem>
                ))}
              </Stagger>
            </ScrollReveal>
          )}
        </>
      )}
    </div>
  );
}

function StreakBadgeSummary({ streak }: { streak: StreakDTO }) {
  return (
    <div
      className="relative inline-flex flex-col items-start gap-1 pr-6"
      style={{ transform: "rotate(-1.5deg)" }}
    >
      <Sticker color="cream" font="arkhip" size="sm" rotate={-3}>
        в огне
      </Sticker>
      <div
        className="flex items-baseline gap-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="display-number text-5xl text-[var(--warning)]">
          {streak.current}
        </span>
        <span
          className="text-sm text-[var(--muted)]"
          style={{ fontFamily: "var(--font-body)" }}
        >
          дней подряд
        </span>
      </div>
      <p
        className="text-xs text-[var(--muted-foreground)]"
        style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "13px" }}
      >
        рекорд · {streak.longest}
      </p>
    </div>
  );
}
