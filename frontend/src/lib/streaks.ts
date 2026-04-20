"use client";

import { useEffect, useSyncExternalStore } from "react";

export interface StreakDTO {
  current: number;
  longest: number;
  status: "on_fire" | "at_risk" | "broken" | "none";
  freezes_available: number;
  last_active_date?: string | null;
}

export interface BadgeDTO {
  id: number;
  code: string;
  title: string;
  description: string;
  icon: string;
  tier: "bronze" | "silver" | "gold" | "legend";
  category: string;
  earned_at?: string | null;
}

/**
 * Tiny global store. No external dep.
 */
let state: {
  streak: StreakDTO | null;
  badgeQueue: BadgeDTO[];
} = {
  streak: null,
  badgeQueue: [],
};

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function setStreak(next: StreakDTO | null) {
  state = { ...state, streak: next };
  emit();
}

/** Push newly-earned badges into the queue to be popped by a toast. */
export function enqueueBadges(badges: BadgeDTO[] | undefined | null) {
  if (!badges || badges.length === 0) return;
  state = { ...state, badgeQueue: [...state.badgeQueue, ...badges] };
  emit();
}

export function dequeueBadge(): BadgeDTO | null {
  if (state.badgeQueue.length === 0) return null;
  const [first, ...rest] = state.badgeQueue;
  state = { ...state, badgeQueue: rest };
  emit();
  return first ?? null;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function getSnapshot() {
  return state;
}

function getServerSnapshot() {
  return { streak: null, badgeQueue: [] } as typeof state;
}

export function useStreakStore() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Universal handler for action responses that may contain streak/badges.
 * Call this after any POST whose payload may include `streak` and `newly_earned_badges`.
 */
export function handleActivityResponse(
  payload: {
    streak?: StreakDTO | null;
    newly_earned_badges?: BadgeDTO[] | null;
  } | null | undefined,
) {
  if (!payload) return;
  if (payload.streak) setStreak(payload.streak);
  if (payload.newly_earned_badges?.length) {
    enqueueBadges(payload.newly_earned_badges);
  }
}

/**
 * Auto-fetches the streak on mount.
 * Used by the sidebar flame and any always-visible widget.
 */
export function useLoadStreak() {
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { api } = await import("@/lib/api");
        const s = await api<StreakDTO>("/api/streaks/me");
        if (!cancelled) setStreak(s);
      } catch {
        /* silent — not critical */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
}
