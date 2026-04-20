"use client";

/**
 * Horizontal scroll strip of context-aware quick prompts. Generated server-side
 * (`/api/ai/chat/quick-prompts`) from today's snapshot — they are NOT a Gemini
 * call, so they appear instantly and never burn quota. The "accent" chip is
 * the most relevant suggestion (e.g. analyse-the-day if the user already
 * logged kcal today).
 */

import { Icon } from "@iconify/react";

export interface QuickPrompt {
  icon: string;
  label: string;
  prompt: string;
  accent?: boolean;
}

interface QuickPromptsProps {
  prompts: QuickPrompt[];
  onPick: (prompt: string) => void;
  disabled?: boolean;
}

export function QuickPrompts({ prompts, onPick, disabled }: QuickPromptsProps) {
  if (!prompts.length) return null;
  return (
    <div className="-mx-1 px-1 overflow-x-auto no-scrollbar">
      <div className="flex items-center gap-1.5 min-w-max">
        {prompts.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => onPick(p.prompt)}
            disabled={disabled}
            className={[
              "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors disabled:opacity-50",
              p.accent
                ? "bg-[var(--accent)] text-white border-[var(--accent)] hover:bg-[var(--accent-hover)]"
                : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--accent)]/50",
            ].join(" ")}
            title={p.prompt}
          >
            <Icon icon={p.icon} width={14} />
            <span className="whitespace-nowrap">{p.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
