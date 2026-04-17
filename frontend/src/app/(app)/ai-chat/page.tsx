"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Send, Loader2 } from "lucide-react";

type Role = "user" | "assistant";

interface ChatMessage {
  role: Role;
  text: string;
}

interface ChatApiResponse {
  response?: string;
  reply?: string;
}

export default function AiChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setLoading(true);

    try {
      const data = await api<ChatApiResponse>("/api/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: trimmed }),
      });
      const reply = data?.response ?? data?.reply ?? "";
      setMessages((prev) => [...prev, { role: "assistant", text: reply || "(пустой ответ)" }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Ошибка запроса";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Не удалось получить ответ: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[min(720px,calc(100vh-8rem))] gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold text-[var(--foreground)]">AI-чат</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Спросите про питание, тренировки или здоровье
        </p>
      </div>

      {error && (
        <div
          className="rounded-[var(--radius-lg)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-4 py-2 text-sm"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="flex-1 min-h-0 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--input-bg)] shadow-[var(--shadow-1)] overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !loading && (
            <p className="text-sm text-[var(--muted-foreground)] text-center py-12">
              Напишите сообщение — ассистент ответит с учётом вашего контекста.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-[var(--radius-lg)] px-4 py-3 text-sm shadow-[var(--shadow-1)] whitespace-pre-wrap break-words ${
                  m.role === "user"
                    ? "bg-[var(--accent)] text-white rounded-br-sm"
                    : "bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-bl-sm"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm text-[var(--muted-foreground)]">
                <Loader2 className="animate-spin shrink-0" size={18} aria-hidden />
                <span>Думаем…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="p-3 border-t border-[var(--border)] bg-[var(--card)]">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              placeholder="Сообщение…"
              rows={2}
              disabled={loading}
              className="flex-1 resize-none rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              className="self-end shrink-0 flex items-center justify-center w-12 h-12 rounded-[var(--radius)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] active:bg-[var(--accent-active)] disabled:opacity-40 transition-colors"
              aria-label="Отправить"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
