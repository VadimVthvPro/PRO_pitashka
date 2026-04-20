"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "@/lib/api";
import { useI18n, type Lang } from "@/lib/i18n";
import { AiLogPanel } from "@/components/admin/AiLogPanel";

type Tab = "overview" | "audit" | "users" | "ai" | "tables";

interface SessionInfo {
  authorized: boolean;
  configured: boolean;
}

export default function AdminPage() {
  const { t } = useI18n();
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");

  const refreshSession = useCallback(async () => {
    try {
      const s = await api<SessionInfo>("/api/admin/session");
      setSession(s);
    } catch {
      setSession({ authorized: false, configured: false });
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  async function login() {
    setLoading(true);
    setError("");
    try {
      await api("/api/admin/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setPassword("");
      await refreshSession();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    await api("/api/admin/logout", { method: "POST" });
    refreshSession();
  }

  if (!session) {
    return (
      <div className="py-24 text-center text-[var(--muted)]">
        <Icon icon="svg-spinners:180-ring" width={28} className="mx-auto" />
      </div>
    );
  }

  if (!session.authorized) {
    return (
      <div className="max-w-sm mx-auto py-12 sm:py-20 px-2">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-base p-6 sm:p-7"
        >
          <div className="w-14 h-14 rounded-full bg-[var(--accent)]/10 flex items-center justify-center mb-4">
            <Icon
              icon="solar:shield-keyhole-bold-duotone"
              width={32}
              className="text-[var(--accent)]"
            />
          </div>
          <h1
            className="text-2xl mb-1"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.02em",
            }}
          >
            {t("admin_login_title")}
          </h1>
          <p className="text-sm text-[var(--muted)] mb-5">
            {session.configured ? t("admin_password_hint_env") : t("admin_password_hint_missing")}
          </p>
          {session.configured && (
            <>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && login()}
                placeholder={t("admin_placeholder_password")}
                autoFocus
                autoComplete="current-password"
                className="w-full px-4 py-3 mb-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-sm focus:border-[var(--accent)] focus:outline-none"
              />
              <button
                disabled={loading || !password}
                onClick={login}
                className="w-full py-3 bg-[var(--accent)] text-white rounded-[var(--radius)] font-semibold disabled:opacity-50 active:scale-[0.98] transition-transform"
              >
                {loading ? t("admin_btn_checking") : t("admin_btn_login")}
              </button>
              {error && (
                <p className="mt-3 text-xs text-[var(--destructive)] flex items-center gap-1">
                  <Icon icon="solar:danger-circle-bold-duotone" width={14} />
                  {error}
                </p>
              )}
            </>
          )}
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-1 sm:px-2 lg:px-4 py-2 lg:py-6">
      <header className="flex items-start sm:items-center justify-between gap-3 mb-4 px-2 sm:px-0">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
            admin
          </p>
          <h1
            className="mt-1"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(1.6rem, 3.5vw, 2.4rem)",
              letterSpacing: "-0.025em",
              lineHeight: 1,
            }}
          >
            {t("admin_panel_title")}
          </h1>
        </div>
        <button
          onClick={logout}
          className="text-xs text-[var(--muted)] hover:text-[var(--destructive)] inline-flex items-center gap-1 px-3 py-2 rounded-full border border-[var(--border)]"
        >
          <Icon icon="solar:logout-3-linear" width={14} />
          {t("admin_logout")}
        </button>
      </header>

      <nav className="flex gap-1.5 mb-4 overflow-x-auto -mx-1 px-2 sm:px-0 sticky top-0 z-10 bg-[var(--background)] py-2 backdrop-blur-md">
        <TabBtn icon="solar:chart-square-bold-duotone" active={tab === "overview"} onClick={() => setTab("overview")}>
          {t("admin_tab_summary")}
        </TabBtn>
        <TabBtn icon="solar:document-text-bold-duotone" active={tab === "audit"} onClick={() => setTab("audit")}>
          {t("admin_tab_logs")}
        </TabBtn>
        <TabBtn icon="solar:users-group-rounded-bold-duotone" active={tab === "users"} onClick={() => setTab("users")}>
          {t("admin_tab_users")}
        </TabBtn>
        <TabBtn icon="solar:magic-stick-3-bold-duotone" active={tab === "ai"} onClick={() => setTab("ai")}>
          {t("admin_tab_ai")}
        </TabBtn>
        <TabBtn icon="solar:database-bold-duotone" active={tab === "tables"} onClick={() => setTab("tables")}>
          {t("admin_tab_tables")}
        </TabBtn>
      </nav>

      <div className="px-2 sm:px-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            {tab === "overview" && <OverviewPanel />}
            {tab === "audit" && <AuditPanel />}
            {tab === "users" && <UsersPanel />}
            {tab === "ai" && <AiLogPanel />}
            {tab === "tables" && <TablesPanel />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function TabBtn({
  icon,
  active,
  onClick,
  children,
}: {
  icon: string;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold transition active:scale-95 ${
        active
          ? "bg-[var(--accent)] text-white shadow-[var(--shadow-1)]"
          : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
      }`}
    >
      <Icon icon={icon} width={14} />
      {children}
    </button>
  );
}

// ============== OVERVIEW ==============

interface OverviewData {
  users: {
    total: number;
    new_today: number;
    new_week: number;
    active_24h: number;
    active_7d: number;
  };
  today: {
    food_entries: number;
    food_calories: number;
    water_glasses: number;
    training_entries: number;
    training_calories: number;
  };
  ai_7d: { category: string; count: number; errors: number }[];
  social: { posts: number; posts_week: number; likes: number };
  top_users: {
    user_id: number;
    name: string | null;
    telegram_username: string | null;
    actions: number;
  }[];
  recent_errors: {
    id: number;
    user_id: number | null;
    method: string;
    path: string;
    status_code: number;
    created_at: string;
  }[];
}

function OverviewPanel() {
  const { t, lang } = useI18n();
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<OverviewData>("/api/admin/overview")
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : t("admin_err_summary")),
      );
  }, [t]);

  if (error) {
    return (
      <div className="card-base p-5 text-sm text-[var(--destructive)]">
        <Icon icon="solar:danger-triangle-bold-duotone" width={18} className="inline mr-1" />
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card-base p-8 text-center text-sm text-[var(--muted)]">
        <Icon icon="svg-spinners:180-ring" width={22} className="inline mr-2" />
        {t("admin_loading_summary")}
      </div>
    );
  }

  const aiTotal = data.ai_7d.reduce((s, x) => s + x.count, 0);
  const aiErrors = data.ai_7d.reduce((s, x) => s + x.errors, 0);

  return (
    <div className="space-y-5">
      {/* Users */}
      <section>
        <SectionTitle icon="solar:users-group-rounded-bold-duotone" title={t("admin_section_users")} />
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <StatCard label={t("admin_stat_total")} value={data.users.total} />
          <StatCard label={t("admin_stat_new_today")} value={data.users.new_today} />
          <StatCard label={t("admin_stat_new_week")} value={data.users.new_week} />
          <StatCard label={t("admin_stat_active_24h")} value={data.users.active_24h} />
          <StatCard label={t("admin_stat_active_7d")} value={data.users.active_7d} />
        </div>
      </section>

      {/* Today's logs */}
      <section>
        <SectionTitle icon="solar:calendar-bold-duotone" title={t("admin_section_today")} />
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <StatCard label={t("admin_stat_meals")} value={data.today.food_entries} />
          <StatCard label={t("admin_stat_kcal_in")} value={data.today.food_calories} />
          <StatCard label={t("admin_stat_water_glasses")} value={data.today.water_glasses} />
          <StatCard label={t("admin_stat_workouts")} value={data.today.training_entries} />
          <StatCard label={t("admin_stat_kcal_burned")} value={data.today.training_calories} />
        </div>
      </section>

      {/* AI usage */}
      <section>
        <SectionTitle
          icon="solar:magic-stick-3-bold-duotone"
          title={t("admin_section_ai_7d")}
          right={
            <span className="text-[11px] text-[var(--muted)]">
              {t("admin_ai_total_label")} <b>{aiTotal}</b>
              {aiErrors > 0 && (
                <>
                  {" · "}
                  <span className="text-[var(--destructive)]">
                    {t("admin_ai_errors_label")} {aiErrors}
                  </span>
                </>
              )}
            </span>
          }
        />
        {data.ai_7d.length === 0 ? (
          <p className="card-base p-4 text-xs text-[var(--muted)]">
            {t("admin_ai_empty_7d")}
          </p>
        ) : (
          <div className="card-base p-3 space-y-1.5">
            {data.ai_7d.map((row) => {
              const pct = aiTotal > 0 ? Math.round((row.count / aiTotal) * 100) : 0;
              return (
                <div key={row.category} className="text-xs">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className="font-mono">{row.category}</span>
                    <span className="text-[var(--muted)] tabular-nums">
                      {row.count}
                      {row.errors > 0 && (
                        <span className="text-[var(--destructive)] ml-1">
                          (·{row.errors})
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="h-1.5 bg-[var(--input-bg)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--accent)]"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Social */}
      <section>
        <SectionTitle icon="solar:chat-round-bold-duotone" title={t("admin_section_social")} />
        <div className="grid grid-cols-3 gap-2">
          <StatCard label={t("admin_stat_posts_total")} value={data.social.posts} />
          <StatCard label={t("admin_stat_posts_week")} value={data.social.posts_week} />
          <StatCard label={t("admin_stat_likes")} value={data.social.likes} />
        </div>
      </section>

      {/* Top users */}
      <section>
        <SectionTitle icon="solar:cup-star-bold-duotone" title={t("admin_section_top_active")} />
        {data.top_users.length === 0 ? (
          <p className="card-base p-4 text-xs text-[var(--muted)]">{t("common_empty")}</p>
        ) : (
          <div className="card-base divide-y divide-[var(--border)]">
            {data.top_users.map((u, idx) => (
              <div
                key={u.user_id}
                className="flex items-center gap-3 px-3 py-2 text-sm"
              >
                <span className="w-6 text-center text-[var(--muted)] tabular-nums text-xs">
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm">
                    {u.name || u.telegram_username || `user #${u.user_id}`}
                  </p>
                  <p className="text-[10px] text-[var(--muted)]">
                    #{u.user_id}
                    {u.telegram_username && ` · @${u.telegram_username}`}
                  </p>
                </div>
                <span className="text-xs tabular-nums">
                  <b>{u.actions}</b>
                  <span className="text-[var(--muted)]"> {t("admin_top_actions_abbr")}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent errors */}
      <section>
        <SectionTitle
          icon="solar:bug-bold-duotone"
          title={t("admin_section_errors_5xx")}
        />
        {data.recent_errors.length === 0 ? (
          <p className="card-base p-4 text-xs text-[var(--color-sage)]">
            {t("admin_errors_clean")}
          </p>
        ) : (
          <div className="card-base divide-y divide-[var(--border)]">
            {data.recent_errors.map((e) => (
              <div key={e.id} className="px-3 py-2 text-xs">
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="flex items-center gap-2">
                    <span className="font-mono font-bold">{e.method}</span>
                    <span className={statusBadgeClass(e.status_code)}>
                      {e.status_code}
                    </span>
                  </span>
                  <span className="text-[var(--muted)] text-[10px]">
                    {new Date(e.created_at).toLocaleString(lang, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {e.user_id && ` · user ${e.user_id}`}
                  </span>
                </div>
                <p className="font-mono text-[11px] break-all text-[var(--muted-foreground)]">
                  {e.path}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SectionTitle({
  icon,
  title,
  right,
}: {
  icon: string;
  title: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-2 px-1">
      <h3 className="text-sm font-semibold flex items-center gap-1.5 text-[var(--foreground)]">
        <Icon icon={icon} width={16} className="text-[var(--accent)]" />
        {title}
      </h3>
      {right}
    </div>
  );
}

// ============== AUDIT ==============

interface AuditItem {
  id: number;
  user_id: number | null;
  method: string;
  path: string;
  category: string;
  status_code: number;
  duration_ms: number;
  ip: string | null;
  created_at: string;
}

interface AuditStats {
  totals: {
    total: number;
    uniq_users: number;
    avg_ms: number;
    errors_5xx: number;
    errors_4xx: number;
  };
  by_category: { category: string; count: number }[];
}

function AuditPanel() {
  const { t, lang } = useI18n();
  const [items, setItems] = useState<AuditItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const perPage = 30;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (search) params.set("search", search);
      params.set("limit", String(perPage));
      params.set("offset", String((page - 1) * perPage));
      const data = await api<{
        items: AuditItem[];
        total: number;
        categories: string[];
      }>(`/api/admin/audit?${params}`);
      setItems(data.items);
      setTotal(data.total);
      setCategories(data.categories);
    } finally {
      setLoading(false);
    }
  }, [category, search, page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api<AuditStats>("/api/admin/audit/stats?days=7")
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div className="space-y-4">
      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <StatCard label={t("admin_logs_stat_total_week")} value={stats.totals.total} />
          <StatCard label={t("admin_logs_stat_uniq")} value={stats.totals.uniq_users} />
          <StatCard
            label={t("admin_logs_stat_avg_ms")}
            value={`${stats.totals.avg_ms} ${t("common_ms")}`}
          />
          <StatCard
            label="4xx"
            value={stats.totals.errors_4xx}
            tone={stats.totals.errors_4xx > 0 ? "warn" : undefined}
          />
          <StatCard
            label="5xx"
            value={stats.totals.errors_5xx}
            tone={stats.totals.errors_5xx > 0 ? "danger" : undefined}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={category}
          onChange={(e) => {
            setPage(1);
            setCategory(e.target.value);
          }}
          className="px-3 py-1.5 text-xs bg-[var(--card)] border border-[var(--border)] rounded-full"
        >
          <option value="">{t("admin_logs_filter_all_cats")}</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (setPage(1), load())}
          placeholder={t("admin_logs_search_placeholder")}
          className="px-3 py-1.5 text-xs bg-[var(--card)] border border-[var(--border)] rounded-full flex-1 min-w-[140px] focus:border-[var(--accent)] focus:outline-none"
        />
        <span className="text-xs text-[var(--muted)] self-center px-2">
          {t("admin_logs_total_label")} <b>{total}</b>
        </span>
      </div>

      {/* Mobile: card list. Desktop: table. */}
      <div className="hidden sm:block card-base overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-[var(--color-sand)]/40">
              <tr className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                <th className="px-3 py-2 text-left">{t("admin_logs_col_time")}</th>
                <th className="px-2 py-2 text-left">User</th>
                <th className="px-2 py-2 text-left">{t("admin_logs_col_method")}</th>
                <th className="px-2 py-2 text-left">{t("admin_logs_col_category")}</th>
                <th className="px-2 py-2 text-left">Path</th>
                <th className="px-2 py-2 text-right">Status</th>
                <th className="px-2 py-2 text-right">ms</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-[var(--muted)]">
                    <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
                    {t("common_loading_dots")}
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-[var(--muted)]">
                    {t("admin_logs_empty_filter")}
                  </td>
                </tr>
              )}
              {!loading &&
                items.map((it) => (
                  <tr
                    key={it.id}
                    className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/20"
                  >
                    <td className="px-3 py-1.5 whitespace-nowrap text-[var(--muted)]">
                      {new Date(it.created_at).toLocaleString(lang, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="px-2 py-1.5 font-mono">{it.user_id ?? "—"}</td>
                    <td className="px-2 py-1.5 font-mono font-bold">{it.method}</td>
                    <td className="px-2 py-1.5">
                      <span className="px-1.5 py-0.5 rounded bg-[var(--color-sand)] text-[10px]">
                        {it.category}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 font-mono truncate max-w-[300px]">
                      {it.path}
                    </td>
                    <td className={statusClass(it.status_code)}>{it.status_code}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums text-[var(--muted)]">
                      {it.duration_ms}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile cards */}
      <div className="sm:hidden space-y-2">
        {loading && (
          <div className="card-base p-4 text-center text-xs text-[var(--muted)]">
            <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
            {t("common_loading_dots")}
          </div>
        )}
        {!loading && items.length === 0 && (
          <div className="card-base p-4 text-center text-xs text-[var(--muted)]">
            {t("admin_logs_empty")}
          </div>
        )}
        {!loading &&
          items.map((it) => (
            <div key={it.id} className="card-base p-3 text-xs space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono font-bold">{it.method}</span>
                <span className={statusBadgeClass(it.status_code)}>{it.status_code}</span>
              </div>
              <div className="font-mono text-[11px] text-[var(--foreground)] break-all">
                {it.path}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[var(--muted)] text-[10px]">
                <span className="px-1.5 py-0.5 rounded bg-[var(--color-sand)]">
                  {it.category}
                </span>
                <span>user {it.user_id ?? "—"}</span>
                <span className="tabular-nums">
                  {it.duration_ms} {t("common_ms")}
                </span>
                <span className="ml-auto">
                  {new Date(it.created_at).toLocaleString(lang, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
      </div>

      <Pager page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  );
}

function statusClass(s: number): string {
  const base = "px-2 py-1.5 text-right tabular-nums font-bold ";
  if (s >= 500) return base + "text-[var(--destructive)]";
  if (s >= 400) return base + "text-[var(--warning)]";
  return base + "text-[var(--color-sage)]";
}

function statusBadgeClass(s: number): string {
  const base = "inline-block px-2 py-0.5 rounded font-bold tabular-nums text-[10px] ";
  if (s >= 500) return base + "bg-[var(--destructive)]/15 text-[var(--destructive)]";
  if (s >= 400) return base + "bg-[var(--warning)]/15 text-[var(--warning)]";
  return base + "bg-[var(--color-sage)]/15 text-[var(--color-sage)]";
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: "warn" | "danger";
}) {
  const color =
    tone === "danger"
      ? "text-[var(--destructive)]"
      : tone === "warn"
      ? "text-[var(--warning)]"
      : "text-[var(--foreground)]";
  return (
    <div className="card-base px-3 py-2.5">
      <p className="text-[9px] uppercase tracking-widest text-[var(--muted-foreground)]">
        {label}
      </p>
      <p
        className={`text-xl font-bold mt-0.5 tabular-nums ${color}`}
        style={{ fontFamily: "var(--font-display)" }}
      >
        {value}
      </p>
    </div>
  );
}

function Pager({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-between text-xs px-1">
      <span className="text-[var(--muted)]">
        {t("common_page_of", { page, total: totalPages })}
      </span>
      <div className="flex gap-1">
        <button
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="px-3 py-1.5 rounded-full border border-[var(--border)] disabled:opacity-30 active:scale-95 transition"
        >
          ←
        </button>
        <button
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="px-3 py-1.5 rounded-full border border-[var(--border)] disabled:opacity-30 active:scale-95 transition"
        >
          →
        </button>
      </div>
    </div>
  );
}

// ============== USERS ==============

interface UserRow {
  user_id: number;
  name: string | null;
  telegram_username: string | null;
  google_email: string | null;
  created_at: string;
  social_score: number;
}

function UsersPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const perPage = 25;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      params.set("limit", String(perPage));
      params.set("offset", String((page - 1) * perPage));
      const data = await api<{ items: UserRow[]; total: number }>(
        `/api/admin/users?${params}`,
      );
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div className="grid lg:grid-cols-[1fr_400px] gap-4">
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (setPage(1), load())}
            placeholder={t("admin_users_search_placeholder")}
            className="flex-1 px-3 py-2 text-sm bg-[var(--card)] border border-[var(--border)] rounded-full focus:border-[var(--accent)] focus:outline-none"
          />
          <span className="text-xs text-[var(--muted)] self-center px-2">
            <b>{total}</b>
          </span>
        </div>

        {/* Mobile cards */}
        <div className="lg:hidden space-y-2">
          {loading && (
            <div className="card-base p-4 text-center text-xs text-[var(--muted)]">
              {t("common_loading_dots")}
            </div>
          )}
          {!loading &&
            items.map((u) => (
              <button
                key={u.user_id}
                onClick={() => setSelected(u.user_id)}
                className={`w-full text-left card-base p-3 transition ${
                  selected === u.user_id ? "border-[var(--accent)]" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="font-semibold truncate text-sm">
                    {u.name || "—"}
                  </span>
                  <span className="text-xs text-[var(--muted)] font-mono">
                    #{u.user_id}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 text-[11px] text-[var(--muted)]">
                  {u.telegram_username && (
                    <span>@{u.telegram_username}</span>
                  )}
                  {u.google_email && <span className="truncate">{u.google_email}</span>}
                  <span className="ml-auto">
                    score <b className="text-[var(--accent)]">{u.social_score}</b>
                  </span>
                </div>
              </button>
            ))}
        </div>

        {/* Desktop table */}
        <div className="hidden lg:block card-base overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-[var(--color-sand)]/40">
              <tr className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                <th className="px-3 py-2 text-left">ID</th>
                <th className="px-2 py-2 text-left">{t("admin_users_col_name")}</th>
                <th className="px-2 py-2 text-left">@TG</th>
                <th className="px-2 py-2 text-left">Email</th>
                <th className="px-2 py-2 text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="text-center px-3 py-6 text-[var(--muted)]">
                    {t("common_loading_dots")}
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center px-3 py-10 text-[var(--muted)]">
                    {t("admin_users_empty")}
                  </td>
                </tr>
              )}
              {!loading &&
                items.map((u) => (
                  <tr
                    key={u.user_id}
                    onClick={() => setSelected(u.user_id)}
                    className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--color-sand)]/30 ${
                      selected === u.user_id ? "bg-[var(--color-sand)]/40" : ""
                    }`}
                  >
                    <td className="px-3 py-1.5 font-mono">{u.user_id}</td>
                    <td className="px-2 py-1.5 truncate max-w-[140px]">
                      {u.name || "—"}
                    </td>
                    <td className="px-2 py-1.5 truncate max-w-[120px]">
                      {u.telegram_username ? `@${u.telegram_username}` : "—"}
                    </td>
                    <td className="px-2 py-1.5 truncate max-w-[160px]">
                      {u.google_email || "—"}
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {u.social_score}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <Pager page={page} totalPages={totalPages} onChange={setPage} />
      </div>

      <UserDetail userId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

interface UserDetailData {
  user: Record<string, unknown>;
  health: Array<Record<string, unknown>>;
  recent_actions: Array<{
    method: string;
    path: string;
    category?: string;
    status_code: number;
    created_at: string;
  }>;
}

const PROFILE_FIELDS: { key: string; labelKey: string }[] = [
  { key: "user_id", labelKey: "field_id" },
  { key: "name", labelKey: "field_name" },
  { key: "telegram_username", labelKey: "field_telegram" },
  { key: "google_email", labelKey: "field_google_email" },
  { key: "user_sex", labelKey: "field_sex" },
  { key: "aim", labelKey: "field_aim" },
  { key: "daily_cal", labelKey: "field_daily_kcal" },
  { key: "social_score", labelKey: "field_social_score" },
  { key: "created_at", labelKey: "field_registered" },
  { key: "google_linked_at", labelKey: "field_google_linked" },
];

function UserDetail({
  userId,
  onClose,
}: {
  userId: number | null;
  onClose: () => void;
}) {
  const { t, lang } = useI18n();
  const [data, setData] = useState<UserDetailData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) {
      setData(null);
      return;
    }
    setLoading(true);
    api(`/api/admin/users/${userId}`)
      .then((d) => setData(d as UserDetailData))
      .finally(() => setLoading(false));
  }, [userId]);

  if (!userId) {
    return (
      <div className="hidden lg:flex card-base p-5 text-sm text-[var(--muted)] text-center items-center justify-center min-h-[300px]">
        {t("admin_pick_user_left")}
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="card-base p-5 text-sm text-[var(--muted)] text-center">
        <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
        {t("common_loading_dots")}
      </div>
    );
  }

  return (
    <div className="card-base p-4 sm:p-5 space-y-4 text-xs max-h-[80vh] overflow-y-auto">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-base">User #{userId}</h3>
        <button
          onClick={onClose}
          className="lg:hidden text-[var(--muted)] hover:text-[var(--foreground)]"
          aria-label={t("admin_aria_close")}
        >
          <Icon icon="solar:close-circle-bold-duotone" width={22} />
        </button>
      </div>

      {/* Selected profile fields */}
      <div className="grid grid-cols-2 gap-2">
        {PROFILE_FIELDS.map(({ key, labelKey }) => {
          const v = data.user[key];
          if (v === null || v === undefined || v === "") return null;
          return (
            <div
              key={key}
              className="bg-[var(--input-bg)] rounded p-2 min-w-0"
            >
              <p className="text-[9px] uppercase tracking-widest text-[var(--muted-foreground)]">
                {t(labelKey)}
              </p>
              <p className="text-[12px] font-mono truncate">{formatVal(v, t, lang)}</p>
            </div>
          );
        })}
      </div>

      {/* Health log */}
      {data.health.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2 flex items-center gap-1">
            <Icon icon="solar:heart-pulse-bold-duotone" width={14} />
            {t("admin_health_section")} ({data.health.length})
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead className="text-[9px] uppercase text-[var(--muted-foreground)]">
                <tr>
                  <th className="text-left pb-1">{t("weight_th_date")}</th>
                  <th className="text-right pb-1">{t("weight_th_weight")}</th>
                  <th className="text-right pb-1">{t("field_height_cm")}</th>
                  <th className="text-right pb-1">{t("field_bmi")}</th>
                </tr>
              </thead>
              <tbody>
                {data.health.slice(0, 8).map((h, i) => (
                  <tr key={i} className="border-t border-dashed border-[var(--border)]">
                    <td className="py-1">{formatVal(h.date, t, lang)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.weight, t, lang)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.height, t, lang)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.imt, t, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent actions */}
      <div>
        <h4 className="font-semibold mb-2 flex items-center gap-1">
          <Icon icon="solar:document-text-bold-duotone" width={14} />
          {t("admin_actions_section")} ({data.recent_actions.length})
        </h4>
        {data.recent_actions.length === 0 ? (
          <p className="text-[var(--muted)] text-[11px]">{t("admin_none")}</p>
        ) : (
          <ul className="space-y-1">
            {data.recent_actions.slice(0, 25).map((a, i) => (
              <li
                key={i}
                className="flex items-center gap-2 text-[11px] border-b border-dashed border-[var(--border)] pb-1"
              >
                <span className="font-mono font-bold w-12 shrink-0">{a.method}</span>
                <span className="font-mono flex-1 truncate">{a.path}</span>
                <span className={statusBadgeClass(a.status_code)}>{a.status_code}</span>
                <span className="text-[var(--muted)] text-[10px] shrink-0">
                  {new Date(a.created_at).toLocaleString(lang, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function formatVal(
  v: unknown,
  t: (key: string, vars?: Record<string, string | number>) => string,
  lang: Lang,
): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") {
    // ISO-ish date — render shorter
    if (/^\d{4}-\d{2}-\d{2}T/.test(v)) {
      return new Date(v).toLocaleString(lang, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
      return v;
    }
    return v;
  }
  if (typeof v === "boolean") return v ? t("common_yes") : t("common_no");
  return JSON.stringify(v);
}

// ============== TABLES ==============

interface TableData {
  columns: { column_name: string }[] | string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  per_page: number;
}

function TablesPanel() {
  const { t, lang } = useI18n();
  const [tables, setTables] = useState<string[]>([]);
  const [active, setActive] = useState("");
  const [data, setData] = useState<TableData | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<{ tables: string[] }>("/api/admin/tables").then((r) =>
      setTables(r.tables),
    );
  }, []);

  const load = useCallback(async (tableName: string, p: number) => {
    setLoading(true);
    try {
      const r = await api<TableData>(
        `/api/admin/tables/${tableName}?page=${p}&per_page=20`,
      );
      setData(r);
      setActive(tableName);
      setPage(p);
    } finally {
      setLoading(false);
    }
  }, []);

  const cols = useMemo<string[]>(() => {
    if (!data) return [];
    return data.columns.map((c) =>
      typeof c === "string" ? c : c.column_name,
    );
  }, [data]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {tables.map((tableName) => (
          <button
            key={tableName}
            onClick={() => load(tableName, 1)}
            className={`text-[11px] px-3 py-1.5 rounded-full font-mono transition active:scale-95 ${
              active === tableName
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
            }`}
          >
            {tableName}
          </button>
        ))}
      </div>
      {loading && (
        <div className="card-base p-6 text-center text-xs text-[var(--muted)]">
          <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
          {t("admin_table_loading_named", { table: active })}
        </div>
      )}
      {!loading && data && (
        <div className="card-base overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead className="bg-[var(--color-sand)]/40 sticky top-0">
              <tr>
                {cols.map((c) => (
                  <th
                    key={c}
                    className="px-2 py-1.5 text-left text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] whitespace-nowrap"
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 && (
                <tr>
                  <td
                    colSpan={cols.length}
                    className="text-center px-3 py-8 text-[var(--muted)]"
                  >
                    {t("admin_table_empty")}
                  </td>
                </tr>
              )}
              {data.rows.map((r, i) => (
                <tr
                  key={i}
                  className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/20"
                >
                  {cols.map((c) => (
                    <td
                      key={c}
                      className="px-2 py-1 font-mono whitespace-nowrap max-w-[260px] truncate"
                      title={String(r[c] ?? "")}
                    >
                      {formatVal(r[c], t, lang)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {data.total > data.per_page && (
            <div className="flex items-center justify-between p-3 text-xs border-t border-[var(--border)]">
              <span className="text-[var(--muted)]">
                {t("admin_table_records_count", { total: data.total, page })}
              </span>
              <div className="flex gap-1">
                <button
                  disabled={page <= 1}
                  onClick={() => load(active, page - 1)}
                  className="px-3 py-1 border border-[var(--border)] rounded-full disabled:opacity-30 active:scale-95"
                >
                  ←
                </button>
                <button
                  disabled={page * data.per_page >= data.total}
                  onClick={() => load(active, page + 1)}
                  className="px-3 py-1 border border-[var(--border)] rounded-full disabled:opacity-30 active:scale-95"
                >
                  →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {!loading && !data && (
        <div className="card-base p-6 text-center text-xs text-[var(--muted)]">
          {t("admin_table_pick_above")}
        </div>
      )}
    </div>
  );
}
