"use client";

/**
 * Single chat turn — assistant or user. Asymmetric corner radii match the
 * brand's "hand-drawn, off-grid" feel without resorting to literal SVG
 * scribbles inside the bubble (which would clash with prose-rendered Markdown).
 *
 * Hover actions on assistant messages: copy, regenerate, 👍 / 👎. On touch
 * devices they're always visible (revealed by `data-touch=true` set on body
 * by `lib/touch.ts`, falling back to always-visible if unsure).
 */

import { useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import { Markdown } from "@/components/ai/Markdown";
import { useI18n } from "@/lib/i18n";

export type Role = "user" | "assistant";

export interface BubbleMessage {
  id?: number;
  role: Role;
  text: string;
  pending?: boolean;
  feedback?: -1 | 0 | 1 | null;
}

interface MessageBubbleProps {
  message: BubbleMessage;
  /** Set when this is the most recent assistant reply — only it can be regenerated. */
  isLastAssistant?: boolean;
  onCopy?: (text: string) => void;
  onRegenerate?: () => void;
  onFeedback?: (messageId: number, value: 1 | -1 | 0) => void;
}

export function MessageBubble({
  message,
  isLastAssistant,
  onCopy,
  onRegenerate,
  onFeedback,
}: MessageBubbleProps) {
  const { t } = useI18n();
  const isAssistant = message.role === "assistant";
  const [justCopied, setJustCopied] = useState(false);

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={[
        "group flex gap-2.5 items-start",
        isAssistant ? "justify-start" : "justify-end",
      ].join(" ")}
    >
      {isAssistant && <AssistantAvatar />}

      <div
        className={[
          "max-w-[88%] sm:max-w-[78%] flex flex-col gap-1.5",
          isAssistant ? "items-start" : "items-end",
        ].join(" ")}
      >
        <div
          className={[
            "px-4 py-3 text-sm shadow-[var(--shadow-1)]",
            isAssistant
              ? "bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-[22px_22px_22px_4px]"
              : "bg-[var(--accent)] text-white rounded-[22px_22px_4px_22px]",
          ].join(" ")}
        >
          {message.pending ? (
            <TypingDots />
          ) : isAssistant ? (
            <Markdown variant="compact">{message.text}</Markdown>
          ) : (
            <span className="whitespace-pre-wrap break-words leading-relaxed">
              {message.text}
            </span>
          )}
        </div>

        {isAssistant && !message.pending && message.id != null && (
          <div
            className={[
              "flex items-center gap-0.5 transition-opacity",
              "opacity-0 group-hover:opacity-100 focus-within:opacity-100",
              "[body[data-touch='true']_&]:opacity-100",
            ].join(" ")}
          >
            <BubbleAction
              icon={justCopied ? "solar:check-circle-bold" : "solar:copy-bold-duotone"}
              label={justCopied ? t("ai_action_copied") : t("ai_action_copy")}
              onClick={() => {
                onCopy?.(message.text);
                setJustCopied(true);
                setTimeout(() => setJustCopied(false), 1500);
              }}
              tone={justCopied ? "success" : "neutral"}
            />
            {isLastAssistant && (
              <BubbleAction
                icon="solar:refresh-circle-bold-duotone"
                label={t("ai_action_regen")}
                onClick={() => onRegenerate?.()}
              />
            )}
            <BubbleAction
              icon={
                message.feedback === 1
                  ? "solar:like-bold"
                  : "solar:like-bold-duotone"
              }
              label={t("ai_action_thumb_up")}
              onClick={() =>
                onFeedback?.(message.id!, message.feedback === 1 ? 0 : 1)
              }
              tone={message.feedback === 1 ? "good" : "neutral"}
            />
            <BubbleAction
              icon={
                message.feedback === -1
                  ? "solar:dislike-bold"
                  : "solar:dislike-bold-duotone"
              }
              label={t("ai_action_thumb_down")}
              onClick={() =>
                onFeedback?.(message.id!, message.feedback === -1 ? 0 : -1)
              }
              tone={message.feedback === -1 ? "bad" : "neutral"}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}

function AssistantAvatar() {
  return (
    <div
      aria-hidden
      className="shrink-0 w-9 h-9 rounded-full bg-[var(--color-sand)] border border-[var(--border)] text-[var(--accent)] flex items-center justify-center shadow-[var(--shadow-1)] -rotate-3"
    >
      <Icon icon="solar:magic-stick-3-bold-duotone" width={18} />
    </div>
  );
}

function BubbleAction({
  icon,
  label,
  onClick,
  tone = "neutral",
}: {
  icon: string;
  label: string;
  onClick: () => void;
  tone?: "neutral" | "good" | "bad" | "success";
}) {
  const toneClass =
    tone === "good"
      ? "text-[var(--accent)]"
      : tone === "bad"
      ? "text-[var(--destructive)]"
      : tone === "success"
      ? "text-[var(--accent)]"
      : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]";
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "inline-flex items-center justify-center w-7 h-7 rounded-md hover:bg-[var(--card)] transition-colors",
        toneClass,
      ].join(" ")}
      title={label}
      aria-label={label}
    >
      <Icon icon={icon} width={15} />
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
