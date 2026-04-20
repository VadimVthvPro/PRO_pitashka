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
import { useI18n } from "@/lib/i18n";

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
  source?: "ai" | "fallback" | null;
  ai_error?: "ai_misconfigured" | "ai_quota_exceeded" | "ai_unavailable";
  message?: string;
}

export default function DigestPage() {
  const { t } = useI18n();
  const [data, setData] = useState<DigestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const res = await api<DigestResponse>(
        `/api/digest/weekly${refresh ? "?refresh=true" : ""}`,
      );
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("digest_err_load"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-8">
      <ScrollReveal>
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              {t("digest_title")}
            </p>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(2.5rem, 1.8rem + 3vw, 4rem)",
                letterSpacing: "-0.03em",
                lineHeight: 0.92,
              }}
            >
              {t("digest_your_word")}{" "}
              <Highlight color="oklch(75% 0.13 150 / 0.45)">
                <span className="px-1">{t("digest_word_digest")}</span>
              </Highlight>
            </h1>
            <p
              className="text-sm text-[var(--muted-foreground)] mt-3"
              style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "15px" }}
            >
              {t("digest_tagline")}
            </p>
          </div>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => void load(true)}
            disabled={loading || refreshing}
            className="px-4 min-h-11 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)] inline-flex items-center gap-2 text-sm disabled:opacity-50 touch-manipulation"
          >
            <Icon
              icon="solar:refresh-bold-duotone"
              width={18}
              className={refreshing ? "animate-spin text-[var(--accent)]" : "text-[var(--accent)]"}
            />
            {refreshing ? t("digest_refresh_dots") : t("digest_regenerate")}
          </motion.button>
        </div>
      </ScrollReveal>

      {data?.source === "fallback" && (
        <ScrollReveal>
          <div
            className="card-base p-4 flex items-start gap-3 border-2 border-dashed"
            style={{ borderColor: "var(--warning)" }}
          >
            <Icon
              icon="solar:info-circle-bold-duotone"
              width={22}
              className="text-[var(--warning)] shrink-0 mt-0.5"
            />
            <div className="text-sm">
              <p className="font-semibold mb-1">{t("digest_fallback_banner")}</p>
              <p className="text-[var(--muted-foreground)] leading-snug">
                {data.ai_error === "ai_misconfigured"
                  ? t("digest_fallback_body_no_key")
                  : data.ai_error === "ai_quota_exceeded"
                    ? t("digest_fallback_body_quota")
                    : t("digest_fallback_body_unavailable")}
              </p>
            </div>
          </div>
        </ScrollReveal>
      )}

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
                {t("digest_empty_title")}
              </p>
              <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[52ch]">
                {data.message ?? t("digest_empty_hint")}
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
                    {t("digest_sticker_wins")}
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
                      {t("digest_wins_empty_alt")}
                    </li>
                  )}
                </ul>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={0.15}>
              <div className="card-base p-6 h-full">
                <div className="flex items-center gap-2 mb-3">
                  <Sticker color="amber" font="arkhip" size="sm" rotate={1.5}>
                    {t("digest_sticker_growth")}
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
                      {t("digest_focus_empty_alt")}
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
                      {t("digest_tip_section_title")}
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
                label={t("digest_stat_food_entries")}
                value={data.stats.food.entries}
                hint={t("digest_stat_food_hint_days", { logged: data.stats.food.days_logged })}
              />
              <StatBlock
                icon="solar:glass-water-bold-duotone"
                label={t("digest_stat_water")}
                value={data.stats.water.glasses_total}
                hint={t("digest_stat_water_hint", { avg: data.stats.water.avg_daily })}
              />
              <StatBlock
                icon="solar:dumbbell-large-bold-duotone"
                label={t("digest_stat_workouts")}
                value={data.stats.workouts.sessions}
                hint={t("digest_stat_workouts_hint_min", { m: data.stats.workouts.minutes })}
              />
              <StatBlock
                icon="solar:fire-bold-duotone"
                label={t("digest_stat_burned")}
                value={data.stats.workouts.cal_burned}
                hint={t("digest_hint_kcal")}
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
