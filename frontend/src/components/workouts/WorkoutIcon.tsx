"use client";

import { Icon } from "@iconify/react";

/**
 * Workout icon with two rendering modes:
 *
 *   1. If an ``emoji`` is passed (or is present in the fallback table),
 *      we render it as a styled span. This is the single source of truth
 *      — the ``training_types.emoji`` column in the DB is what the admin
 *      sees and edits.
 *
 *   2. If we have no emoji at all (e.g. a freshly inserted training type
 *      that the admin forgot to emoji-tag), we fall back to a Solar icon
 *      matched by id. The fallback map mirrors the actual DB seed order
 *      — don't re-order it without updating the DB first.
 */

// DB seed (see migration + `training_types` table):
//   1 Бег · 2 Ходьба · 3 Велосипед · 4 Плавание · 5 Силовая
//   6 Йога · 7 Пилатес · 8 HIIT · 9 Кроссфит · 10 Бокс
//   11 Танцы · 12 Лыжи · 13 Сноуборд · 14 Скакалка · 15 Гребля
//   16 Эллипсоид · 17 Футбол · 18 Баскетбол · 19 Теннис · 20 Растяжка
const EMOJI_FALLBACK: Record<number, string> = {
  1: "🏃",
  2: "🚶",
  3: "🚴",
  4: "🏊",
  5: "🏋️",
  6: "🧘",
  7: "🤸",
  8: "🔥",
  9: "🤾",
  10: "🥊",
  11: "💃",
  12: "🎿",
  13: "🏂",
  14: "🪢",
  15: "🚣",
  16: "⚙️",
  17: "⚽",
  18: "🏀",
  19: "🎾",
  20: "🤲",
};

// Solar icon fallback if even the emoji lookup misses. Matched to the
// same DB order as above so ids line up with real training names.
const ICON_FALLBACK: Record<number, string> = {
  1: "solar:running-2-bold-duotone",        // Бег
  2: "solar:walking-bold-duotone",          // Ходьба
  3: "solar:scooter-bold-duotone",          // Велосипед
  4: "solar:swimming-bold-duotone",         // Плавание
  5: "solar:dumbbell-large-bold-duotone",   // Силовая тренировка
  6: "solar:meditation-bold-duotone",       // Йога
  7: "solar:stretching-bold-duotone",       // Пилатес
  8: "solar:bolt-bold-duotone",             // HIIT
  9: "solar:dumbbell-bold-duotone",         // Кроссфит
  10: "solar:bolt-circle-bold-duotone",     // Бокс
  11: "solar:music-note-bold-duotone",      // Танцы
  12: "solar:snowflake-bold-duotone",       // Лыжи
  13: "solar:snowflake-bold-duotone",       // Сноуборд
  14: "solar:bolt-bold-duotone",            // Скакалка
  15: "solar:running-2-bold-duotone",       // Гребля
  16: "solar:refresh-circle-bold-duotone",  // Эллипсоид
  17: "solar:football-bold-duotone",        // Футбол
  18: "solar:basketball-bold-duotone",      // Баскетбол
  19: "solar:tennis-2-bold-duotone",        // Теннис
  20: "solar:stretching-bold-duotone",      // Растяжка
};

const DEFAULT_ICON = "solar:running-2-bold-duotone";

interface WorkoutIconProps {
  id: number;
  /** Emoji straight from ``training_types.emoji``. Preferred when present. */
  emoji?: string | null;
  size?: number;
  className?: string;
}

export function WorkoutIcon({ id, emoji, size = 32, className }: WorkoutIconProps) {
  const finalEmoji = emoji?.trim() || EMOJI_FALLBACK[id];
  if (finalEmoji) {
    return (
      <span
        className={className}
        style={{
          fontSize: size,
          lineHeight: 1,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily:
            '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif',
        }}
        aria-hidden="true"
      >
        {finalEmoji}
      </span>
    );
  }
  const icon = ICON_FALLBACK[id] ?? DEFAULT_ICON;
  return (
    <Icon
      icon={icon}
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
    />
  );
}
