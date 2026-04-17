"use client";

import { Icon } from "@iconify/react";

/**
 * Maps training_type.id → curated Solar Icons (bold-duotone style).
 * Falls back to generic "running" for unmapped ids so the UI never shows nothing.
 */
const WORKOUT_ICON_MAP: Record<number, string> = {
  1: "solar:running-2-bold-duotone",        // Бег
  2: "solar:running-2-bold-duotone",        // Быстрый бег
  3: "solar:walking-bold-duotone",          // Ходьба
  4: "solar:walking-bold-duotone",          // Быстрая ходьба
  5: "solar:scooter-bold-duotone",          // Велосипед
  6: "solar:swimming-bold-duotone",         // Плавание
  7: "solar:dumbbell-large-bold-duotone",   // Тренажерный зал
  8: "solar:dumbbell-bold-duotone",         // Кроссфит
  9: "solar:running-2-bold-duotone",        // Упр. с весом тела
  10: "solar:bolt-bold-duotone",            // Аэробика
  11: "solar:music-note-bold-duotone",      // Зумба
  12: "solar:meditation-bold-duotone",      // Йога
  13: "solar:meditation-bold-duotone",      // Пилатес
  14: "solar:football-bold-duotone",        // Футбол
  15: "solar:basketball-bold-duotone",      // Баскетбол
  16: "solar:tennis-2-bold-duotone",        // Теннис
  17: "solar:music-note-bold-duotone",      // Танцы
  18: "solar:bolt-circle-bold-duotone",     // Бокс
  19: "solar:bolt-circle-bold-duotone",     // Единоборства
  20: "solar:stretching-bold-duotone",      // Растяжка
};

const DEFAULT_ICON = "solar:running-2-bold-duotone";

interface WorkoutIconProps {
  id: number;
  size?: number;
  className?: string;
}

export function WorkoutIcon({ id, size = 32, className }: WorkoutIconProps) {
  const icon = WORKOUT_ICON_MAP[id] ?? DEFAULT_ICON;
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
