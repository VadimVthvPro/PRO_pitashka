"use client";

/**
 * Admin → AI logs.
 *
 * Shows paired (user → assistant) chat turns from `chat_history`, joined into
 * a single row each so an operator can scan dialogues without flipping
 * between user/assistant lines. Backed by:
 *   GET    /api/admin/ai/log         — paginated list (server-side LAG-pair)
 *   GET    /api/admin/ai/stats       — KPIs + by-day + top users + by-attach
 *   DELETE /api/admin/ai/message/{id} — moderate-out a bad reply
 *
 * The detail drawer renders the assistant reply through the same Markdown
 * component the chat uses, so what the admin sees is exactly what the user
 * received — fonts, lists, headings and all.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";

import { Markdown } from "@/components/ai/Markdown";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Period = "1d" | "7d" | "30d" | "90d";
type AttachFilter = "all" | "any" | "meal_plan" | "workout_plan";

interface LogItem {
  id: number;
  user_id: number;
  user_name: string | null;
  telegram_username: string | null;
  user_message: string;
  user_message_id: number | null;
  assistant_message: string;
  feedback: -1 | 0 | 1 | null;
  attach_kind: string | null;
  latency_ms: number | null;
  model: string | null;
  created_at: string;
}

interface LogResponse {
  items: LogItem[];
  total: number;
}

interface StatsResponse {
  totals: {
    replies: number;
    questions: number;
    uniq_users: number;
    avg_reply_chars: number;
    avg_latency_ms: number;
    thumbs_up: number;
    thumbs_down: number;
    replies_24h: number;
  };
  by_day: { day: string; replies: number; questions: number }[];
  top_users: {
    user_id: number;
    name: string;
    telegram_username: string | null;
    replies: number;
  }[];
  by_attach: { kind: string; count: number; up: number; down: number }[];
}

const PERIOD_DAYS: Record<Period, number> = { "1d": 1, "7d": 7, "30d": 30, "90d": 90 };
const PAGE_SIZE = 25;

export function AiLogPanel() {
  const { t, lang } = useI18n();
  const [period, setPeriod] = useState<Period>("7d");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [onlyNeg, setOnlyNeg] = useState(false);
  const [attachFilter, setAttachFilter] = useState<AttachFilter>("all");
  const [userFilter, setUserFilter] = useState<number | null>(null);
  const [page, setPage] = useState(0);

  const [items, setItems] = useState<LogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<LogItem | null>(null);

  // Debounce search to avoid hammering the API on every keystroke.
  useEffect(() => {
    const id = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(id);
  }, [search]);

  // Re-load list whenever filters change. Stats only depend on period.
  const loadList = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({
      days: String(PERIOD_DAYS[period]),
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
    });
    if (debounced) params.set("search", debounced);
    if (onlyNeg) params.set("only_negative", "true");
    if (attachFilter !== "all") params.set("has_attach", attachFilter);
    if (userFilter != null) params.set("user_id", String(userFilter));
    api<LogResponse>(`/api/admin/ai/log?${params.toString()}`)
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("admin_err_summary")))
      .finally(() => setLoading(false));
  }, [period, page, debounced, onlyNeg, attachFilter, userFilter, t]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  // Reset to page 0 when filters change so the user doesn't see "no results"
  // simply because the new filter has fewer matches than the old offset.
  useEffect(() => {
    setPage(0);
  }, [debounced, onlyNeg, attachFilter, userFilter, period]);

  useEffect(() => {
    api<StatsResponse>(`/api/admin/ai/stats?days=${PERIOD_DAYS[period]}`)
      .then(setStats)
      .catch(() => setStats(null));
  }, [period]);

  const dateFmt = useMemo(
    () =>
      new Intl.DateTimeFormat(lang || "ru", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }),
    [lang],
  );

  async function deleteMessage(id: number) {
    if (typeof window !== "undefined" && !window.confirm(t("admin_ai_delete_confirm"))) return;
    try {
      await api(`/api/admin/ai/message/${id}`, { method: "DELETE" });
      setItems((cur) => cur.filter((x) => x.id !== id));
      setOpen(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    }
  }

  return (
    <div className="space-y-5">
      {/* KPI strip ------------------------------------------------------- */}
      {stats && (
        <section>
          <div className="flex items-center justify-between mb-2 px-1">
            <h3 className="text-sm font-semibold flex items-center gap-1.5 text-[var(--foreground)]">
              <Icon icon="solar:magic-stick-3-bold-duotone" width={16} className="text-[var(--accent)]" />
              {t("admin_ai_kpi_title")}
            </h3>
            <PeriodSwitch value={period} onChange={setPeriod} />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <Kpi
              icon="solar:chat-round-line-bold-duotone"
              label={t("admin_ai_kpi_replies")}
              value={stats.totals.replies}
              hint={t("admin_ai_kpi_replies_hint", { n: stats.totals.replies_24h })}
            />
            <Kpi
              icon="solar:users-group-rounded-bold-duotone"
              label={t("admin_ai_kpi_users")}
              value={stats.totals.uniq_users}
            />
            <Kpi
              icon="solar:clock-circle-bold-duotone"
              label={t("admin_ai_kpi_latency")}
              value={`${stats.totals.avg_latency_ms} ${t("unit_ms")}`}
            />
            <Kpi
              icon="solar:like-bold-duotone"
              label={t("admin_ai_kpi_feedback")}
              value={
                stats.totals.thumbs_up + stats.totals.thumbs_down > 0
                  ? `${stats.totals.thumbs_up} / ${stats.totals.thumbs_down}`
                  : "—"
              }
              hint={t("admin_ai_kpi_feedback_hint")}
            />
          </div>

          {/* Sparkline + top users */}
          <div className="grid lg:grid-cols-[1fr_280px] gap-3 mt-3">
            <div className="card-base p-4">
              <p className="text-[11px] uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
                {t("admin_ai_chart_title")}
              </p>
              <Sparkline data={stats.by_day.map((d) => d.replies)} />
              <p className="text-[10px] text-[var(--muted-foreground)] mt-1">
                {t("admin_ai_chart_hint", { n: stats.by_day.length })}
              </p>
            </div>
            <div className="card-base p-4">
              <p className="text-[11px] uppercase tracking-wider text-[var(--muted-foreground)] mb-2">
                {t("admin_ai_top_users")}
              </p>
              {stats.top_users.length === 0 ? (
                <p className="text-xs text-[var(--muted-foreground)]">{t("admin_ai_top_empty")}</p>
              ) : (
                <ul className="space-y-1.5">
                  {stats.top_users.map((u) => (
                    <li key={u.user_id} className="flex items-center justify-between gap-2 text-sm">
                      <button
                        type="button"
                        onClick={() => setUserFilter(u.user_id)}
                        className="truncate text-left hover:text-[var(--accent)] transition-colors"
                        title={`@${u.telegram_username ?? u.user_id}`}
                      >
                        {u.name || `#${u.user_id}`}
                      </button>
                      <span className="tabular-nums text-[var(--muted-foreground)] text-xs">
                        {u.replies}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Filters --------------------------------------------------------- */}
      <section className="card-base p-3 sm:p-4 space-y-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex-1 min-w-[200px] flex items-center gap-2 px-3 py-2 rounded-[var(--radius)] bg-[var(--input-bg)] border border-[var(--border)]">
            <Icon icon="solar:magnifer-bold-duotone" width={14} className="text-[var(--muted-foreground)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("admin_ai_search_placeholder")}
              className="flex-1 min-w-0 bg-transparent text-sm focus:outline-none"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                aria-label={t("admin_ai_clear_search")}
              >
                <Icon icon="solar:close-circle-bold" width={14} />
              </button>
            )}
          </div>
          <FilterChip
            active={onlyNeg}
            onClick={() => setOnlyNeg((v) => !v)}
            icon="solar:dislike-bold-duotone"
            label={t("admin_ai_filter_negative")}
          />
          <select
            value={attachFilter}
            onChange={(e) => setAttachFilter(e.target.value as AttachFilter)}
            className="text-xs px-3 py-2 rounded-full border border-[var(--border)] bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
          >
            <option value="all">{t("admin_ai_attach_all")}</option>
            <option value="any">{t("admin_ai_attach_any")}</option>
            <option value="meal_plan">{t("ai_attach_meal_plan")}</option>
            <option value="workout_plan">{t("ai_attach_workout_plan")}</option>
          </select>
          {userFilter != null && (
            <FilterChip
              active
              onClick={() => setUserFilter(null)}
              icon="solar:user-bold-duotone"
              label={t("admin_ai_filter_user", { id: userFilter })}
            />
          )}
        </div>
        <p className="text-[11px] text-[var(--muted-foreground)] px-1">
          {t("admin_ai_total_found", { n: total })}
        </p>
      </section>

      {/* Table ----------------------------------------------------------- */}
      <section>
        {error && (
          <div className="card-base p-4 text-sm text-[var(--destructive)] mb-3">
            <Icon icon="solar:danger-triangle-bold-duotone" width={16} className="inline mr-1" />
            {error}
          </div>
        )}
        {loading ? (
          <div className="card-base p-12 text-center text-sm text-[var(--muted-foreground)]">
            <Icon icon="svg-spinners:180-ring" width={22} className="inline mr-2" />
            {t("admin_loading_summary")}
          </div>
        ) : items.length === 0 ? (
          <div className="card-base p-12 text-center text-sm text-[var(--muted-foreground)]">
            <Icon icon="solar:inbox-bold-duotone" width={28} className="inline mb-2 block mx-auto" />
            {t("admin_ai_empty")}
          </div>
        ) : (
          <ul className="space-y-1.5">
            {items.map((it) => (
              <LogRow
                key={it.id}
                item={it}
                onOpen={() => setOpen(it)}
                onUserFilter={() => setUserFilter(it.user_id)}
                dateFmt={dateFmt}
              />
            ))}
          </ul>
        )}
        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="px-3 py-1.5 rounded-full border border-[var(--border)] text-xs disabled:opacity-40"
            >
              <Icon icon="solar:alt-arrow-left-bold" width={12} className="inline mr-1" />
              {t("prev")}
            </button>
            <span className="text-xs text-[var(--muted-foreground)] tabular-nums">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} / {total}
            </span>
            <button
              type="button"
              disabled={(page + 1) * PAGE_SIZE >= total}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 rounded-full border border-[var(--border)] text-xs disabled:opacity-40"
            >
              {t("next")}
              <Icon icon="solar:alt-arrow-right-bold" width={12} className="inline ml-1" />
            </button>
          </div>
        )}
      </section>

      {/* Drawer ---------------------------------------------------------- */}
      <AnimatePresence>
        {open && (
          <DialogDrawer item={open} onClose={() => setOpen(null)} onDelete={() => deleteMessage(open.id)} />
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pieces
// ---------------------------------------------------------------------------

function PeriodSwitch({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  const opts: Period[] = ["1d", "7d", "30d", "90d"];
  return (
    <div className="inline-flex rounded-full border border-[var(--border)] bg-[var(--card)] p-0.5">
      {opts.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={[
            "text-[11px] px-2.5 py-1 rounded-full transition-colors",
            value === o
              ? "bg-[var(--accent)] text-white"
              : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
          ].join(" ")}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  hint,
}: {
  icon: string;
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <div className="card-base px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
        <Icon icon={icon} width={14} className="text-[var(--accent)]" />
        <span className="text-[10px] uppercase tracking-widest">{label}</span>
      </div>
      <p
        className="text-xl font-bold mt-0.5 tabular-nums text-[var(--foreground)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {value}
      </p>
      {hint && (
        <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5 truncate">{hint}</p>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "inline-flex items-center gap-1.5 text-xs px-3 py-2 rounded-full border transition-colors",
        active
          ? "bg-[var(--accent)] text-white border-[var(--accent)]"
          : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--accent)]/40",
      ].join(" ")}
    >
      <Icon icon={icon} width={13} />
      {label}
    </button>
  );
}

function Sparkline({ data }: { data: number[] }) {
  if (data.length === 0) {
    return <div className="h-12 flex items-center text-xs text-[var(--muted-foreground)]">—</div>;
  }
  const max = Math.max(...data, 1);
  const w = 100;
  const h = 36;
  const step = data.length > 1 ? w / (data.length - 1) : 0;
  const points = data
    .map((v, i) => `${(i * step).toFixed(2)},${(h - (v / max) * h).toFixed(2)}`)
    .join(" ");
  const lastX = (data.length - 1) * step;
  const lastY = h - (data[data.length - 1] / max) * h;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      className="w-full h-12"
      aria-hidden
    >
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastX} cy={lastY} r={2} fill="var(--accent)" />
    </svg>
  );
}

function LogRow({
  item,
  onOpen,
  onUserFilter,
  dateFmt,
}: {
  item: LogItem;
  onOpen: () => void;
  onUserFilter: () => void;
  dateFmt: Intl.DateTimeFormat;
}) {
  const { t } = useI18n();
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="w-full text-left card-base hover:border-[var(--accent)]/40 transition-colors p-3 grid grid-cols-[auto_1fr_auto] gap-3 items-start"
      >
        <span className="shrink-0 mt-0.5 inline-flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-sand)] text-[var(--accent)]">
          <Icon icon="solar:user-rounded-bold-duotone" width={18} />
        </span>
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap text-[11px] text-[var(--muted-foreground)]">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onUserFilter();
              }}
              className="hover:text-[var(--accent)] transition-colors font-medium text-[var(--foreground)]"
            >
              {item.user_name || `#${item.user_id}`}
            </button>
            {item.telegram_username && <span>@{item.telegram_username}</span>}
            <span>·</span>
            <span>{dateFmt.format(new Date(item.created_at))}</span>
            {item.attach_kind && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)]">
                <Icon
                  icon={item.attach_kind === "meal_plan" ? "solar:plate-bold-duotone" : "solar:dumbbell-large-bold-duotone"}
                  width={10}
                />
                {item.attach_kind === "meal_plan" ? t("ai_attach_meal_plan") : t("ai_attach_workout_plan")}
              </span>
            )}
            {item.feedback === 1 && (
              <Icon icon="solar:like-bold" width={12} className="text-[var(--accent)]" />
            )}
            {item.feedback === -1 && (
              <Icon icon="solar:dislike-bold" width={12} className="text-[var(--destructive)]" />
            )}
            {item.latency_ms != null && (
              <span className="ml-auto tabular-nums">{item.latency_ms}{t("unit_ms")}</span>
            )}
          </div>
          <p className="text-sm text-[var(--foreground)] line-clamp-2">
            <Icon icon="solar:user-bold-duotone" width={12} className="inline mr-1 text-[var(--muted-foreground)]" />
            {item.user_message || <em className="text-[var(--muted-foreground)]">{t("admin_ai_no_user_msg")}</em>}
          </p>
          <p className="text-sm text-[var(--muted-foreground)] line-clamp-2">
            <Icon icon="solar:magic-stick-3-bold-duotone" width={12} className="inline mr-1 text-[var(--accent)]" />
            {item.assistant_message}
          </p>
        </div>
        <Icon
          icon="solar:alt-arrow-right-line-duotone"
          width={16}
          className="text-[var(--muted-foreground)] shrink-0 mt-2"
        />
      </button>
    </li>
  );
}

function DialogDrawer({
  item,
  onClose,
  onDelete,
}: {
  item: LogItem;
  onClose: () => void;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  return (
    <>
      <motion.button
        type="button"
        aria-label={t("admin_ai_close_drawer")}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
      />
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed right-0 top-0 bottom-0 z-50 w-full sm:w-[520px] bg-[var(--background)] border-l border-[var(--border)] shadow-2xl flex flex-col"
      >
        <header className="px-5 py-4 border-b border-[var(--border)] flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-widest text-[var(--muted-foreground)]">
              {t("admin_ai_drawer_title")}
            </p>
            <p className="text-base font-semibold truncate">
              {item.user_name || `#${item.user_id}`}
              {item.telegram_username && (
                <span className="ml-1.5 text-xs text-[var(--muted-foreground)] font-normal">
                  @{item.telegram_username}
                </span>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-[var(--card)] transition-colors"
            aria-label={t("admin_ai_close_drawer")}
          >
            <Icon icon="solar:close-circle-bold-duotone" width={22} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <DrawerMeta item={item} />
          <section>
            <p className="text-[11px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1.5">
              {t("admin_ai_drawer_question")}
            </p>
            <div className="card-base p-3 text-sm whitespace-pre-wrap break-words">
              {item.user_message || <em className="text-[var(--muted-foreground)]">{t("admin_ai_no_user_msg")}</em>}
            </div>
          </section>
          <section>
            <p className="text-[11px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1.5">
              {t("admin_ai_drawer_answer")}
            </p>
            <div className="card-base p-4">
              <Markdown variant="comfortable">{item.assistant_message}</Markdown>
            </div>
          </section>
        </div>

        <footer className="px-5 py-3 border-t border-[var(--border)] flex items-center justify-between">
          <button
            type="button"
            onClick={onDelete}
            className="inline-flex items-center gap-1.5 text-xs text-[var(--destructive)] px-3 py-2 rounded-full border border-[var(--destructive)]/30 hover:bg-[var(--destructive)]/10 transition-colors"
          >
            <Icon icon="solar:trash-bin-trash-bold-duotone" width={14} />
            {t("admin_ai_delete_message")}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-3 py-2"
          >
            {t("close")}
          </button>
        </footer>
      </motion.aside>
    </>
  );
}

function DrawerMeta({ item }: { item: LogItem }) {
  const { t, lang } = useI18n();
  const dt = new Intl.DateTimeFormat(lang || "ru", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(item.created_at));
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <Meta dt={t("admin_ai_meta_when")} dd={dt} />
      <Meta
        dt={t("admin_ai_meta_latency")}
        dd={item.latency_ms != null ? `${item.latency_ms} ${t("unit_ms")}` : "—"}
      />
      <Meta dt={t("admin_ai_meta_model")} dd={item.model || "—"} />
      <Meta
        dt={t("admin_ai_meta_attach")}
        dd={
          item.attach_kind === "meal_plan"
            ? t("ai_attach_meal_plan")
            : item.attach_kind === "workout_plan"
            ? t("ai_attach_workout_plan")
            : "—"
        }
      />
      <Meta
        dt={t("admin_ai_meta_feedback")}
        dd={
          item.feedback === 1
            ? "👍"
            : item.feedback === -1
            ? "👎"
            : "—"
        }
      />
      <Meta dt={t("admin_ai_meta_chars")} dd={String(item.assistant_message.length)} />
    </dl>
  );
}

function Meta({ dt, dd }: { dt: string; dd: string }) {
  return (
    <div className="flex justify-between gap-2 py-0.5 border-b border-dashed border-[var(--border)]/50 last:border-0">
      <dt className="text-[var(--muted-foreground)]">{dt}</dt>
      <dd className="font-medium text-[var(--foreground)] truncate">{dd}</dd>
    </div>
  );
}
