"use client";

/**
 * AI assistant — full chat experience, "Пропитошка-собеседник" edition.
 *
 * Layout (lg+):
 *   ┌──────────────┬───────────────────────────────────────┐
 *   │ ContextRail  │  conversation lane                    │
 *   │  • snapshot  │   • day separators in Arkhip          │
 *   │  • plan pins │   • asymmetric bubbles                │
 *   │              │   • hover actions (copy/regen/👍/👎)   │
 *   │              │  ─────────────────────────────────── │
 *   │              │  QuickPrompts → composer → send       │
 *   └──────────────┴───────────────────────────────────────┘
 * On mobile the rail collapses to a horizontal strip above the lane.
 *
 * The page intentionally surfaces *everything the AI sees* before it answers
 * (today's snapshot + which plan is pinned), so the user never has to wonder
 * "почему ты не знаешь сколько я съел". See DESIGN_GUIDE.md §0.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@iconify/react";
import { AnimatePresence, motion } from "motion/react";

import { ContextRail, type ContextSnapshot, type PlanState } from "@/components/ai/ContextRail";
import { MessageBubble, type BubbleMessage } from "@/components/ai/MessageBubble";
import { QuickPrompts, type QuickPrompt } from "@/components/ai/QuickPrompts";
import { DaySeparator } from "@/components/ai/DaySeparator";
import { Highlight } from "@/components/hand/Highlight";
import { Sticker } from "@/components/hand/Sticker";
import { Scribble } from "@/components/hand/Scribble";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Attach = "meal_plan" | "workout_plan" | null;

interface PersistedMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  created_at: string;
  feedback?: -1 | 0 | 1 | null;
  attach_kind?: string | null;
}

interface HistoryResponse {
  messages: PersistedMessage[];
}

interface PlansResponse {
  meal_plan: string | null;
  workout_plan: string | null;
}

interface SnapshotResponse {
  today: ContextSnapshot;
  has_meal_plan?: boolean;
  has_workout_plan?: boolean;
}

interface ChatApiResponse {
  response?: string;
  message_id?: number;
}

interface QuickPromptsResp {
  prompts: QuickPrompt[];
}

type ChatItem =
  | { kind: "day"; key: string; date: Date }
  | { kind: "msg"; key: string; message: BubbleMessage; createdAt: Date };

export default function AiChatPage() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [messages, setMessages] = useState<BubbleMessage[]>([]);
  const [createdAt, setCreatedAt] = useState<Map<number, Date>>(new Map());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attach, setAttach] = useState<Attach>(null);
  const [plans, setPlans] = useState<PlansResponse>({ meal_plan: null, workout_plan: null });
  const [snapshot, setSnapshot] = useState<ContextSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const [quickPrompts, setQuickPrompts] = useState<QuickPrompt[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // ---------------------------------------------------------------- bootstrap
  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    setSnapshotLoading(true);
    Promise.allSettled([
      api<HistoryResponse>("/api/ai/chat/history?limit=200").catch(() => null),
      api<PlansResponse>("/api/ai/plans").catch(() => null),
      api<SnapshotResponse>("/api/ai/snapshot").catch(() => null),
      api<QuickPromptsResp>("/api/ai/chat/quick-prompts").catch(() => null),
    ]).then(([hist, plansRes, snap, qp]) => {
      if (cancelled) return;
      const dateMap = new Map<number, Date>();
      if (hist.status === "fulfilled" && hist.value) {
        const msgs: BubbleMessage[] = hist.value.messages.map((m) => {
          dateMap.set(m.id, new Date(m.created_at));
          return {
            id: m.id,
            role: m.role,
            text: m.text,
            feedback: m.feedback ?? null,
          };
        });
        setMessages(msgs);
        setCreatedAt(dateMap);
      }
      if (plansRes.status === "fulfilled" && plansRes.value) {
        setPlans({
          meal_plan: plansRes.value.meal_plan ?? null,
          workout_plan: plansRes.value.workout_plan ?? null,
        });
      }
      if (snap.status === "fulfilled" && snap.value?.today) {
        setSnapshot(snap.value.today);
      } else {
        setSnapshot({
          calories_in: 0,
          calories_burned: 0,
          water_glasses: 0,
          workout_sessions: 0,
          food_items_logged: 0,
          active_minutes: 0,
        });
      }
      if (qp.status === "fulfilled" && qp.value) {
        setQuickPrompts(qp.value.prompts || []);
      }
      setHistoryLoading(false);
      setSnapshotLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const a = searchParams.get("attach");
    if (a === "meal_plan" || a === "workout_plan") setAttach(a);
  }, [searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  // ------------------------------------------------------------ derived items
  const items: ChatItem[] = useMemo(() => {
    const out: ChatItem[] = [];
    let lastDay: string | null = null;
    messages.forEach((m, i) => {
      const d = (m.id != null && createdAt.get(m.id)) || new Date();
      const dayKey = d.toDateString();
      if (dayKey !== lastDay) {
        lastDay = dayKey;
        out.push({ kind: "day", key: `day-${dayKey}-${i}`, date: d });
      }
      out.push({
        kind: "msg",
        key: m.id != null ? `msg-${m.id}` : `tmp-${i}`,
        message: m,
        createdAt: d,
      });
    });
    return out;
  }, [messages, createdAt]);

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && !messages[i].pending) return messages[i].id;
    }
    return undefined;
  }, [messages]);

  const mealPlanState: PlanState = !plans.meal_plan
    ? "missing"
    : attach === "meal_plan"
    ? "attached"
    : "available";
  const workoutPlanState: PlanState = !plans.workout_plan
    ? "missing"
    : attach === "workout_plan"
    ? "attached"
    : "available";

  // -------------------------------------------------------------- send / regen
  const send = useCallback(
    async (overrideText?: string) => {
      const trimmed = (overrideText ?? input).trim();
      if (!trimmed || loading) return;
      setError(null);
      setInput("");
      setMessages((prev) => [
        ...prev,
        { role: "user", text: trimmed },
        { role: "assistant", text: "", pending: true },
      ]);
      setLoading(true);
      try {
        const data = await api<ChatApiResponse>("/api/ai/chat", {
          method: "POST",
          body: JSON.stringify({ message: trimmed, attach }),
        });
        const reply = data?.response || t("ai_empty_reply");
        const newId = data?.message_id;
        setMessages((prev) => {
          const next = prev.slice(0, -1);
          next.push({
            id: newId,
            role: "assistant",
            text: reply,
            feedback: null,
          });
          return next;
        });
        if (newId != null) {
          setCreatedAt((m) => new Map(m).set(newId, new Date()));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : t("ai_error_request");
        setError(msg);
        setMessages((prev) => {
          const next = prev.slice(0, -1);
          next.push({ role: "assistant", text: t("ai_error_prefix", { message: msg }) });
          return next;
        });
      } finally {
        setLoading(false);
      }
    },
    [input, loading, attach, t],
  );

  const regenerate = useCallback(async () => {
    if (loading) return;
    setError(null);
    setMessages((prev) => {
      const next = [...prev];
      const lastIdx = [...next].reverse().findIndex((m) => m.role === "assistant");
      if (lastIdx === -1) return prev;
      const realIdx = next.length - 1 - lastIdx;
      next.splice(realIdx, 1, { role: "assistant", text: "", pending: true });
      return next;
    });
    setLoading(true);
    try {
      const data = await api<ChatApiResponse>("/api/ai/chat/regenerate", { method: "POST" });
      const reply = data?.response || t("ai_empty_reply");
      const newId = data?.message_id;
      setMessages((prev) => {
        const next = prev.slice(0, -1);
        next.push({ id: newId, role: "assistant", text: reply, feedback: null });
        return next;
      });
      if (newId != null) setCreatedAt((m) => new Map(m).set(newId, new Date()));
    } catch (e) {
      const msg = e instanceof Error ? e.message : t("ai_error_request");
      setError(msg);
      setMessages((prev) => {
        const next = prev.slice(0, -1);
        next.push({ role: "assistant", text: t("ai_error_prefix", { message: msg }) });
        return next;
      });
    } finally {
      setLoading(false);
    }
  }, [loading, t]);

  const handleFeedback = useCallback(
    async (messageId: number, value: 1 | -1 | 0) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, feedback: value } : m)),
      );
      try {
        await api("/api/ai/chat/feedback", {
          method: "POST",
          body: JSON.stringify({ message_id: messageId, value }),
        });
      } catch {
        // Silent revert is more annoying than a stale chip, leave it.
      }
    },
    [],
  );

  const handleCopy = useCallback((text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
  }, []);

  async function clearHistory() {
    if (typeof window === "undefined" || !window.confirm(t("ai_confirm_clear"))) return;
    try {
      await api("/api/ai/chat/history", { method: "DELETE" });
      setMessages([]);
      setCreatedAt(new Map());
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    }
  }

  // Mobile height formula:
  //   - 56px (MobileTopBar h-14) + safe-top (notch)
  //   - 40px (main py-5 top + bottom)
  //   - 72px (BottomNav) + safe-bottom
  // Keeps composer above home-indicator even with iOS URL bar collapse.
  return (
    <div className="flex flex-col gap-3 lg:gap-6 lg:flex-row h-[calc(100dvh-168px-var(--safe-top)-var(--safe-bottom))] lg:h-[min(880px,calc(100vh-7rem))] min-h-[420px] lg:min-h-[560px]">
      {/* Rail — full on desktop, hidden on mobile (compact strip lives inside the lane) */}
      <div className="hidden lg:block lg:w-[280px] xl:w-[320px] shrink-0 lg:overflow-y-auto lg:pr-1">
        <ContextRail
          snapshot={snapshot}
          loading={snapshotLoading}
          mealPlan={mealPlanState}
          workoutPlan={workoutPlanState}
          onToggleMeal={() => setAttach((a) => (a === "meal_plan" ? null : "meal_plan"))}
          onToggleWorkout={() => setAttach((a) => (a === "workout_plan" ? null : "workout_plan"))}
          onCreatePlan={(kind) => router.push(kind === "meal" ? "/plans?focus=meal" : "/plans?focus=workout")}
        />
      </div>

      {/* Conversation lane */}
      <div className="flex-1 min-w-0 flex flex-col gap-2 lg:gap-3">
        {/* Header — compact on mobile */}
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl lg:page-title font-display leading-tight truncate">
              {t("ai_hero_pre")}{" "}
              <span className="relative inline-block">
                <Highlight color="oklch(82% 0.13 80 / 0.55)">
                  <span className="px-1">{t("ai_hero_word")}</span>
                </Highlight>
              </span>
            </h1>
            <p className="page-subtitle mt-1 text-xs sm:text-sm truncate">{t("ai_subtitle")}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="hidden sm:block">
              <Sticker color="sage" font="appetite" rotate={-4} size="sm">
                {t("ai_sticker_knows_you")}
              </Sticker>
            </div>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={clearHistory}
                className="inline-flex items-center justify-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors w-11 h-11 sm:w-auto sm:h-auto sm:px-3 sm:py-2 rounded-md hover:bg-[var(--card)] touch-manipulation"
                title={t("ai_clear")}
                aria-label={t("ai_clear")}
              >
                <Icon icon="solar:eraser-bold-duotone" width={16} />
                <span className="hidden sm:inline">{t("ai_clear")}</span>
              </button>
            )}
          </div>
        </div>

        {/* Mobile-only compact context strip */}
        <MobileContextStrip
          snapshot={snapshot}
          loading={snapshotLoading}
          mealPlan={mealPlanState}
          workoutPlan={workoutPlanState}
          onToggleMeal={() => setAttach((a) => (a === "meal_plan" ? null : "meal_plan"))}
          onToggleWorkout={() => setAttach((a) => (a === "workout_plan" ? null : "workout_plan"))}
          onCreatePlan={(kind) => router.push(kind === "meal" ? "/plans?focus=meal" : "/plans?focus=workout")}
        />

        {error && (
          <div
            className="rounded-[var(--radius)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-3 py-2 text-sm"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* Conversation card */}
        <div className="flex-1 min-h-0 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-1)] overflow-hidden flex flex-col relative">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.04] [background-image:radial-gradient(circle_at_1px_1px,var(--foreground)_1px,transparent_0)] [background-size:18px_18px]"
          />

          <div className="flex-1 overflow-y-auto p-3 sm:p-5 space-y-2.5 relative">
            {historyLoading && (
              <div className="flex justify-center py-12">
                <Icon
                  icon="svg-spinners:180-ring"
                  width={28}
                  className="text-[var(--muted-foreground)]"
                />
              </div>
            )}

            {!historyLoading && messages.length === 0 && (
              <EmptyState onPick={(s) => void send(s)} snapshot={snapshot} prompts={quickPrompts} />
            )}

            <AnimatePresence initial={false}>
              {items.map((it) => {
                if (it.kind === "day") {
                  return <DaySeparator key={it.key} date={it.date} />;
                }
                return (
                  <MessageBubble
                    key={it.key}
                    message={it.message}
                    isLastAssistant={
                      it.message.role === "assistant" && it.message.id === lastAssistantId
                    }
                    onCopy={handleCopy}
                    onRegenerate={regenerate}
                    onFeedback={handleFeedback}
                  />
                );
              })}
            </AnimatePresence>

            <div ref={bottomRef} />
          </div>

          {/* Composer */}
          <div className="border-t border-[var(--border)] bg-[var(--card)] p-3 sm:p-4 relative space-y-2.5">
            {!historyLoading && quickPrompts.length > 0 && messages.length > 0 && (
              <QuickPrompts
                prompts={quickPrompts}
                onPick={(p) => void send(p)}
                disabled={loading}
              />
            )}
            <div className="flex items-end gap-2">
              <motion.div
                layout
                className="flex-1 flex items-center gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-2 focus-within:ring-2 focus-within:ring-[var(--accent)]/30"
              >
                {attach && (
                  <span
                    className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wide text-[var(--accent)] bg-[var(--accent)]/10 px-2 py-1 rounded-full shrink-0"
                    title={t("ai_attach_active", { kind: t(`ai_attach_${attach}`) })}
                  >
                    <Icon
                      icon={attach === "meal_plan" ? "solar:plate-bold-duotone" : "solar:dumbbell-large-bold-duotone"}
                      width={12}
                    />
                    {t(`ai_attach_${attach}`)}
                    <button
                      type="button"
                      onClick={() => setAttach(null)}
                      className="hover:text-[var(--foreground)] inline-flex items-center justify-center w-5 h-5 -m-1 p-1 rounded-full touch-manipulation"
                      aria-label={t("ai_attach_remove")}
                    >
                      <Icon icon="solar:close-circle-bold" width={14} />
                    </button>
                  </span>
                )}
                <textarea
                  ref={taRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                  placeholder={t("ai_placeholder")}
                  rows={1}
                  disabled={loading}
                  className="flex-1 min-w-0 resize-none bg-transparent px-1 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none disabled:opacity-50 max-h-[200px]"
                />
              </motion.div>
              <button
                type="button"
                onClick={() => void send()}
                disabled={loading || !input.trim()}
                className="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-[var(--shadow-1)]"
                aria-label={t("ai_aria_send")}
              >
                {loading ? (
                  <Icon icon="svg-spinners:180-ring" width={20} />
                ) : (
                  <Icon icon="solar:plain-3-bold-duotone" width={22} />
                )}
              </button>
            </div>
            <p className="text-[10px] text-[var(--muted-foreground)] text-center">
              {t("ai_hint_enter")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MobileContextStrip({
  snapshot,
  loading,
  mealPlan,
  workoutPlan,
  onToggleMeal,
  onToggleWorkout,
  onCreatePlan,
}: {
  snapshot: ContextSnapshot | null;
  loading: boolean;
  mealPlan: PlanState;
  workoutPlan: PlanState;
  onToggleMeal: () => void;
  onToggleWorkout: () => void;
  onCreatePlan: (kind: "meal" | "workout") => void;
}) {
  const { t } = useI18n();
  const stats = snapshot
    ? [
        { icon: "solar:plate-bold-duotone", value: snapshot.calories_in, unit: t("unit_kcal_short") },
        { icon: "solar:fire-bold-duotone", value: snapshot.calories_burned, unit: t("unit_kcal_short"), tone: "warm" },
        { icon: "solar:cup-bold-duotone", value: snapshot.water_glasses, unit: t("unit_glass_short") },
        { icon: "solar:dumbbell-large-bold-duotone", value: snapshot.workout_sessions, unit: t("unit_session_short") },
      ]
    : [];

  function PlanChip({ state, icon, onAttach, onCreate }: { state: PlanState; icon: string; onAttach: () => void; onCreate: () => void }) {
    if (state === "missing") {
      return (
        <button
          type="button"
          onClick={onCreate}
          className="shrink-0 inline-flex items-center gap-1 px-3 min-h-9 rounded-full border border-dashed border-[var(--border)] text-xs text-[var(--muted-foreground)] touch-manipulation"
        >
          <Icon icon={icon} width={14} />
          <span>+</span>
        </button>
      );
    }
    const attached = state === "attached";
    return (
      <button
        type="button"
        onClick={onAttach}
        aria-pressed={attached}
        className={[
          "shrink-0 inline-flex items-center gap-1.5 px-3 min-h-9 rounded-full border text-xs transition-colors touch-manipulation",
          attached
            ? "bg-[var(--accent)]/15 border-[var(--accent)] text-[var(--accent)]"
            : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)]",
        ].join(" ")}
      >
        <Icon icon={icon} width={14} />
        <Icon icon={attached ? "solar:check-circle-bold" : "solar:add-circle-line-duotone"} width={12} />
      </button>
    );
  }

  return (
    <div className="lg:hidden -mx-1 px-1 flex items-center gap-2 overflow-x-auto no-scrollbar">
      {loading
        ? Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="shrink-0 h-7 w-20 rounded-full bg-[var(--input-bg)] animate-pulse"
            />
          ))
        : stats.map((s, i) => (
            <div
              key={i}
              className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[var(--card)] border border-[var(--border)] text-[11px]"
            >
              <Icon
                icon={s.icon}
                width={13}
                className={s.tone === "warm" ? "text-[var(--warning)]" : "text-[var(--muted-foreground)]"}
              />
              <span className="font-semibold text-[var(--foreground)]">{s.value}</span>
              <span className="text-[var(--muted-foreground)]">{s.unit}</span>
            </div>
          ))}
      <span className="shrink-0 w-px h-5 bg-[var(--border)] mx-0.5" aria-hidden />
      <PlanChip
        state={mealPlan}
        icon="solar:plate-bold-duotone"
        onAttach={onToggleMeal}
        onCreate={() => onCreatePlan("meal")}
      />
      <PlanChip
        state={workoutPlan}
        icon="solar:dumbbell-large-bold-duotone"
        onAttach={onToggleWorkout}
        onCreate={() => onCreatePlan("workout")}
      />
    </div>
  );
}

function EmptyState({
  onPick,
  snapshot,
  prompts,
}: {
  onPick: (s: string) => void;
  snapshot: ContextSnapshot | null;
  prompts: QuickPrompt[];
}) {
  const { t } = useI18n();
  const knows =
    snapshot && (snapshot.calories_in > 0 || snapshot.water_glasses > 0)
      ? t("ai_empty_knows", {
          kcal: snapshot.calories_in,
          water: snapshot.water_glasses,
        })
      : t("ai_empty_neutral");

  return (
    <div className="text-center py-6 sm:py-10 max-w-xl mx-auto space-y-5 px-2">
      <div className="flex items-end justify-center gap-3">
        <Scribble variant="squiggle" className="w-20 h-20 text-[var(--color-latte)] -rotate-6" />
        <div className="text-left max-w-[24ch]">
          <p className="font-display text-2xl text-[var(--foreground)] leading-tight">
            {t("ai_empty_title")}
          </p>
          <p className="text-sm text-[var(--muted-foreground)] mt-2 leading-relaxed">{knows}</p>
        </div>
      </div>

      {prompts.length > 0 && (
        <div className="flex flex-wrap gap-2 justify-center pt-2">
          {prompts.slice(0, 6).map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => onPick(p.prompt)}
              className={[
                "inline-flex items-center gap-1.5 text-xs px-3.5 min-h-11 rounded-full border transition-colors touch-manipulation",
                p.accent
                  ? "bg-[var(--accent)] text-white border-[var(--accent)] hover:bg-[var(--accent-hover)]"
                  : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--accent)]/50",
              ].join(" ")}
            >
              <Icon icon={p.icon} width={14} />
              {p.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
