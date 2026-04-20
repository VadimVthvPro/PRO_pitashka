/**
 * Voice & copy helpers, fully driven by i18n.
 *
 * Each helper accepts a translator (`t`) so the same call site renders the
 * user's currently selected language. Variants ("Доброе утро" / "Поехали" / …)
 * live in locale dictionaries under `copy_*_v1`, `_v2`, … and we pick a
 * stable one per day, per locale. Plain string constants (CTAs, empty
 * states) are exposed as functions that read the dictionary on call.
 */

type TFn = (key: string, vars?: Record<string, string | number>) => string;

function dayHash(): number {
  const d = new Date();
  return d.getFullYear() * 1000 + d.getMonth() * 40 + d.getDate();
}

/** Pick one of the registered variants by day hash. Variants are looked up
 *  as `${baseKey}_v1`, `${baseKey}_v2`, … until a key is missing — that
 *  bound becomes the count. Falls back to baseKey if no variants exist. */
function pickVariant(t: TFn, baseKey: string): string {
  const variants: string[] = [];
  for (let i = 1; i <= 8; i++) {
    const key = `${baseKey}_v${i}`;
    const val = t(key);
    if (val === key) break; // missing
    variants.push(val);
  }
  if (variants.length === 0) return t(baseKey);
  return variants[Math.abs(dayHash()) % variants.length]!;
}

export function greeting(t: TFn): string {
  const h = new Date().getHours();
  if (h < 5) return pickVariant(t, "copy_greet_night");
  if (h < 12) return pickVariant(t, "copy_greet_morning");
  if (h < 18) return pickVariant(t, "copy_greet_day");
  if (h < 23) return pickVariant(t, "copy_greet_evening");
  return pickVariant(t, "copy_greet_night");
}

export function heroSubtitle(
  t: TFn,
  opts: {
    caloriesEaten: number;
    caloriesTarget: number;
    waterGlasses: number;
    workouts: number;
  },
): string {
  const { caloriesEaten, caloriesTarget, waterGlasses, workouts } = opts;
  const left = Math.max(caloriesTarget - caloriesEaten, 0);
  if (caloriesEaten === 0 && workouts === 0 && waterGlasses === 0)
    return t("copy_hero_blank");
  if (workouts >= 1 && caloriesEaten > 0) return t("copy_hero_trained_and_ate");
  if (waterGlasses >= 8) return t("copy_hero_water_king");
  if (left > 0 && left < 400)
    return t("copy_hero_almost_there", { left: Math.round(left) });
  if (left <= 0 && caloriesEaten > 0) return t("copy_hero_norm_eaten");
  return t("copy_hero_default");
}

export function metricLabels(t: TFn) {
  return {
    calories: t("copy_metric_calories"),
    protein: t("copy_metric_protein"),
    fat: t("copy_metric_fat"),
    carbs: t("copy_metric_carbs"),
    water: t("copy_metric_water"),
    workouts: t("copy_metric_workouts"),
    weight: t("copy_metric_weight"),
  };
}

export type EmptyCopyKind =
  | "food_today"
  | "food_day"
  | "workouts_today"
  | "recipes"
  | "plans"
  | "ai_chat";

export function emptyCopy(t: TFn, kind: EmptyCopyKind) {
  return {
    title: t(`copy_empty_${kind}_title`),
    subtitle: t(`copy_empty_${kind}_subtitle`),
    cta: t(`copy_empty_${kind}_cta`),
  };
}

export function cta(t: TFn) {
  return {
    add_water: t("copy_cta_add_water"),
    add_water_done: t("copy_cta_add_water_done"),
    add_water_loading: t("copy_cta_add_water_loading"),
    add_food_photo: t("copy_cta_add_food_photo"),
    add_food_text: t("copy_cta_add_food_text"),
    submit_workout: t("copy_cta_submit_workout"),
    cancel: t("copy_cta_cancel"),
    try_again: t("copy_cta_try_again"),
  };
}

export function streakCompliment(t: TFn, days: number): string {
  if (days >= 30) return t("copy_streak_30");
  if (days >= 14) return t("copy_streak_14");
  if (days >= 7) return t("copy_streak_7");
  if (days >= 3) return t("copy_streak_3");
  return "";
}

export function relativeDay(t: TFn, date: Date): string {
  const now = new Date();
  const diff = Math.floor(
    (date.setHours(0, 0, 0, 0) - new Date(now).setHours(0, 0, 0, 0)) / 86_400_000,
  );
  if (diff === 0) return t("copy_day_today");
  if (diff === -1) return t("copy_day_yesterday");
  if (diff === 1) return t("copy_day_tomorrow");
  if (diff < 0) return t("copy_day_n_ago", { n: -diff });
  return t("copy_day_in_n", { n: diff });
}
