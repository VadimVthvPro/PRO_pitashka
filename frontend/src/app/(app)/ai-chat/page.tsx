"use client";

/**
 * AI assistant — full chat experience.
 *
 * Features in this revision:
 *  - Persisted history loaded from `/api/ai/chat/history` on mount, so the
 *    user sees their conversation across devices and reloads.
 *  - "Discuss my plan" attachments: the user can pin their active meal /
 *    workout plan to the conversation; the backend then injects it into
 *    Gemini's context block (`attach: 'meal_plan' | 'workout_plan'`) and
 *    the model answers from the actual plan instead of inventing one.
 *  - Markdown rendering of assistant replies (bold/italic, lists,
 *    headings, rules) via `<Markdown />` so the answers look like the
 *    rest of the app instead of raw `**asterisks**`.
 *  - Suggestion chips, sticky composer, soft animations, and consistent
 *    use of `--accent`, `--card`, `--border`, `--shadow` tokens from
 *    DESIGN_GUIDE.md.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Markdown } from "@/components/ai/Markdown";

type Role = "user" | "assistant";
type Attach = "meal_plan" | "workout_plan" | null;

interface ChatMessage {
  id?: number;
  role: Role;
  text: string;
  pending?: boolean;
}

interface HistoryResponse {
  messages: { id: number; role: Role; text: string; created_at: string }[];
}

interface PlansResponse {
  meal_plan: string | null;
  workout_plan: string | null;
}

interface ChatApiResponse {
  response?: string;
  message_id?: number;
}

export default function AiChatPage() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attach, setAttach] = useState<Attach>(null);
  const [plans, setPlans] = useState<PlansResponse>({ meal_plan: null, workout_plan: null });
  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // ---- bootstrap: history + plans ----
  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api<HistoryResponse>("/api/ai/chat/history?limit=200").catch(() => null),
      api<PlansResponse>("/api/ai/plans").catch(() => null),
    ]).then(([h, p]) => {
      if (cancelled) return;
      if (h.status === "fulfilled" && h.value) {
        setMessages(
          h.value.messages.map((m) => ({ id: m.id, role: m.role, text: m.text })),
        );
      }
      if (p.status === "fulfilled" && p.value) {
        setPlans({
          meal_plan: p.value.meal_plan ?? null,
          workout_plan: p.value.workout_plan ?? null,
        });
      }
      setHistoryLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Honour ?attach=meal_plan|workout_plan from /plans "Discuss with AI"
  useEffect(() => {
    const a = searchParams.get("attach");
    if (a === "meal_plan" || a === "workout_plan") setAttach(a);
  }, [searchParams]);

  // ---- autoscroll on new content ----
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  // ---- autoresize textarea ----
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const suggestions = useMemo(
    () => [
      t("ai_sugg_meal_plan"),
      t("ai_sugg_workout_plan"),
      t("ai_sugg_recipe"),
      t("ai_sugg_progress"),
    ],
    [t],
  );

  const send = useCallback(
    async (overrideText?: string) => {
      const trimmed = (overrideText ?? input).trim();
      if (!trimmed || loading) return;

      setError(null);
      setInput("");
      const userMsg: ChatMessage = { role: "user", text: trimmed };
      setMessages((prev) => [...prev, userMsg, { role: "assistant", text: "", pending: true }]);
      setLoading(true);

      try {
        const data = await api<ChatApiResponse>("/api/ai/chat", {
          method: "POST",
          body: JSON.stringify({ message: trimmed, attach }),
        });
        const reply = data?.response ?? "";
        setMessages((prev) => {
          const next = prev.slice(0, -1);
          next.push({
            id: data?.message_id ?? undefined,
            role: "assistant",
            text: reply || t("ai_empty_reply"),
          });
          return next;
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : t("ai_error_request");
        setError(msg);
        setMessages((prev) => {
          const next = prev.slice(0, -1);
          next.push({
            role: "assistant",
            text: t("ai_error_prefix", { message: msg }),
          });
          return next;
        });
      } finally {
        setLoading(false);
      }
    },
    [input, loading, attach, t],
  );

  async function clearHistory() {
    if (!confirm(t("ai_confirm_clear"))) return;
    try {
      await api("/api/ai/chat/history", { method: "DELETE" });
      setMessages([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    }
  }

  return (
    <div className="flex flex-col h-[min(820px,calc(100vh-7rem))] gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <span
              className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] text-white shadow-[var(--shadow-1)]"
              aria-hidden
            >
              <Icon icon="ph:sparkle-fill" width={18} />
            </span>
            {t("nav_ai")}
          </h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">{t("ai_subtitle")}</p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={clearHistory}
            className="hidden sm:inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors px-2 py-1 rounded-md hover:bg-[var(--card)]"
            title={t("ai_clear")}
          >
            <Icon icon="ph:broom" width={14} />
            {t("ai_clear")}
          </button>
        )}
      </div>

      {/* Plan attach pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
          {t("ai_context_label")}:
        </span>
        <AttachPill
          icon="ph:fork-knife"
          label={t("ai_attach_meal_plan")}
          active={attach === "meal_plan"}
          available={!!plans.meal_plan}
          onClick={() =>
            setAttach((a) => (a === "meal_plan" ? null : "meal_plan"))
          }
        />
        <AttachPill
          icon="ph:barbell"
          label={t("ai_attach_workout_plan")}
          active={attach === "workout_plan"}
          available={!!plans.workout_plan}
          onClick={() =>
            setAttach((a) => (a === "workout_plan" ? null : "workout_plan"))
          }
        />
        {attach && !plans[attach] && (
          <span className="text-xs text-[var(--warning)]">{t("ai_attach_need_plan")}</span>
        )}
      </div>

      {/* Inline error */}
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
        {/* Soft texture overlay */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.04] [background-image:radial-gradient(circle_at_1px_1px,var(--foreground)_1px,transparent_0)] [background-size:18px_18px]"
        />

        <div className="flex-1 overflow-y-auto p-3 sm:p-5 space-y-3 relative">
          {historyLoading && (
            <div className="flex justify-center py-12">
              <Icon
                icon="ph:circle-notch"
                width={28}
                className="animate-spin text-[var(--muted-foreground)]"
              />
            </div>
          )}

          {!historyLoading && messages.length === 0 && (
            <EmptyState onPick={(s) => void send(s)} suggestions={suggestions} />
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={m.id ?? `msg-${i}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div
                    aria-hidden
                    className="shrink-0 mr-2 mt-1 w-7 h-7 rounded-full bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] text-white flex items-center justify-center shadow-[var(--shadow-1)]"
                  >
                    <Icon icon="ph:sparkle-fill" width={14} />
                  </div>
                )}
                <div
                  className={[
                    "max-w-[88%] sm:max-w-[78%] px-3.5 py-2.5 text-sm shadow-[var(--shadow-1)]",
                    m.role === "user"
                      ? "bg-[var(--accent)] text-white rounded-2xl rounded-br-sm"
                      : "bg-[var(--input-bg)] text-[var(--foreground)] border border-[var(--border)] rounded-2xl rounded-bl-sm",
                  ].join(" ")}
                >
                  {m.pending ? (
                    <TypingDots />
                  ) : m.role === "assistant" ? (
                    <Markdown variant="compact">{m.text}</Markdown>
                  ) : (
                    <span className="whitespace-pre-wrap break-words">{m.text}</span>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-[var(--border)] bg-[var(--card)] p-3 sm:p-4 relative">
          <div className="flex items-end gap-2">
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
              className="flex-1 resize-none rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 disabled:opacity-50 max-h-[200px]"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              className="shrink-0 flex items-center justify-center w-11 h-11 rounded-[var(--radius)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-40 transition-colors shadow-[var(--shadow-1)]"
              aria-label={t("ai_aria_send")}
            >
              {loading ? (
                <Icon icon="ph:circle-notch" width={20} className="animate-spin" />
              ) : (
                <Icon icon="ph:paper-plane-tilt-fill" width={20} />
              )}
            </button>
          </div>
          <p className="mt-1.5 text-[10px] text-[var(--muted-foreground)] text-center">
            {t("ai_hint_enter")}
          </p>
        </div>
      </div>
    </div>
  );
}

function AttachPill({
  icon,
  label,
  active,
  available,
  onClick,
}: {
  icon: string;
  label: string;
  active: boolean;
  available: boolean;
  onClick: () => void;
}) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full border transition-colors",
        active
          ? "bg-[var(--accent)] text-white border-[var(--accent)] shadow-[var(--shadow-1)]"
          : "bg-[var(--input-bg)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--accent)]/40",
        !available && !active ? "opacity-60" : "",
      ].join(" ")}
      title={available ? label : t("ai_attach_unavailable", { label })}
    >
      <Icon icon={icon} width={14} />
      {label}
      {active && <Icon icon="ph:check-bold" width={12} />}
    </button>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--muted-foreground)] animate-bounce [animation-delay:-0.3s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--muted-foreground)] animate-bounce [animation-delay:-0.15s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--muted-foreground)] animate-bounce" />
    </span>
  );
}

function EmptyState({
  onPick,
  suggestions,
}: {
  onPick: (s: string) => void;
  suggestions: string[];
}) {
  const { t } = useI18n();
  return (
    <div className="text-center py-8 sm:py-12 max-w-md mx-auto space-y-5">
      <div
        aria-hidden
        className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-[var(--accent)]/15 to-[var(--accent)]/5 flex items-center justify-center"
      >
        <Icon icon="ph:sparkle-fill" width={28} className="text-[var(--accent)]" />
      </div>
      <div>
        <p className="text-base font-semibold text-[var(--foreground)]">{t("ai_empty_title")}</p>
        <p className="text-sm text-[var(--muted-foreground)] mt-1.5 leading-relaxed">
          {t("ai_empty_p1")}
        </p>
        <p className="text-sm text-[var(--muted-foreground)] mt-1.5 leading-relaxed">
          {t("ai_empty_p2")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="text-xs px-3 py-1.5 rounded-full border border-[var(--border)] bg-[var(--input-bg)] hover:border-[var(--accent)]/40 hover:bg-[var(--card)] transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
