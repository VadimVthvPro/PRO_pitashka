"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "@/lib/api";

type Tab = "audit" | "users" | "tables";

interface SessionInfo {
  authorized: boolean;
  configured: boolean;
}

export default function AdminPage() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("audit");

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
      setError(e instanceof Error ? e.message : "Ошибка");
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
            Админ-панель
          </h1>
          <p className="text-sm text-[var(--muted)] mb-5">
            {session.configured
              ? "Введите пароль из переменной ADMIN_PASSWORD."
              : "ADMIN_PASSWORD не задан в .env. Установите его и перезапустите сервер."}
          </p>
          {session.configured && (
            <>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && login()}
                placeholder="Пароль"
                autoFocus
                autoComplete="current-password"
                className="w-full px-4 py-3 mb-3 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-sm focus:border-[var(--accent)] focus:outline-none"
              />
              <button
                disabled={loading || !password}
                onClick={login}
                className="w-full py-3 bg-[var(--accent)] text-white rounded-[var(--radius)] font-semibold disabled:opacity-50 active:scale-[0.98] transition-transform"
              >
                {loading ? "Проверяем…" : "Войти"}
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
            Панель управления
          </h1>
        </div>
        <button
          onClick={logout}
          className="text-xs text-[var(--muted)] hover:text-[var(--destructive)] inline-flex items-center gap-1 px-3 py-2 rounded-full border border-[var(--border)]"
        >
          <Icon icon="solar:logout-3-linear" width={14} />
          Выйти
        </button>
      </header>

      <nav className="flex gap-1.5 mb-4 overflow-x-auto -mx-1 px-2 sm:px-0 sticky top-0 z-10 bg-[var(--background)] py-2 backdrop-blur-md">
        <TabBtn icon="solar:document-text-bold-duotone" active={tab === "audit"} onClick={() => setTab("audit")}>
          Логи
        </TabBtn>
        <TabBtn icon="solar:users-group-rounded-bold-duotone" active={tab === "users"} onClick={() => setTab("users")}>
          Пользователи
        </TabBtn>
        <TabBtn icon="solar:database-bold-duotone" active={tab === "tables"} onClick={() => setTab("tables")}>
          Таблицы
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
            {tab === "audit" && <AuditPanel />}
            {tab === "users" && <UsersPanel />}
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
          <StatCard label="всего за 7д" value={stats.totals.total} />
          <StatCard label="уникальных" value={stats.totals.uniq_users} />
          <StatCard label="ср. latency" value={`${stats.totals.avg_ms} мс`} />
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
          <option value="">все категории</option>
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
          placeholder="поиск по path…"
          className="px-3 py-1.5 text-xs bg-[var(--card)] border border-[var(--border)] rounded-full flex-1 min-w-[140px] focus:border-[var(--accent)] focus:outline-none"
        />
        <span className="text-xs text-[var(--muted)] self-center px-2">
          всего: <b>{total}</b>
        </span>
      </div>

      {/* Mobile: card list. Desktop: table. */}
      <div className="hidden sm:block card-base overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-[var(--color-sand)]/40">
              <tr className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                <th className="px-3 py-2 text-left">Время</th>
                <th className="px-2 py-2 text-left">User</th>
                <th className="px-2 py-2 text-left">Метод</th>
                <th className="px-2 py-2 text-left">Категория</th>
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
                    загружаем…
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-[var(--muted)]">
                    Нет записей под этот фильтр
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
                      {new Date(it.created_at).toLocaleString("ru-RU", {
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
            загружаем…
          </div>
        )}
        {!loading && items.length === 0 && (
          <div className="card-base p-4 text-center text-xs text-[var(--muted)]">
            Нет записей
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
                <span className="tabular-nums">{it.duration_ms} мс</span>
                <span className="ml-auto">
                  {new Date(it.created_at).toLocaleString("ru-RU", {
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
  return (
    <div className="flex items-center justify-between text-xs px-1">
      <span className="text-[var(--muted)]">
        стр <b>{page}</b> из {totalPages}
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
            placeholder="имя · @username · email"
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
              загружаем…
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
                <th className="px-2 py-2 text-left">Имя</th>
                <th className="px-2 py-2 text-left">@TG</th>
                <th className="px-2 py-2 text-left">Email</th>
                <th className="px-2 py-2 text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="text-center px-3 py-6 text-[var(--muted)]">
                    загружаем…
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center px-3 py-10 text-[var(--muted)]">
                    Нет пользователей
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

const PROFILE_FIELDS: { key: string; label: string }[] = [
  { key: "user_id", label: "ID" },
  { key: "name", label: "Имя" },
  { key: "telegram_username", label: "Telegram" },
  { key: "google_email", label: "Google email" },
  { key: "user_sex", label: "Пол" },
  { key: "aim", label: "Цель" },
  { key: "daily_cal", label: "Норма ккал" },
  { key: "social_score", label: "Соц. рейтинг" },
  { key: "created_at", label: "Регистрация" },
  { key: "google_linked_at", label: "Привязан Google" },
];

function UserDetail({
  userId,
  onClose,
}: {
  userId: number | null;
  onClose: () => void;
}) {
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
        Выберите пользователя слева
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="card-base p-5 text-sm text-[var(--muted)] text-center">
        <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
        загружаем…
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
          aria-label="Закрыть"
        >
          <Icon icon="solar:close-circle-bold-duotone" width={22} />
        </button>
      </div>

      {/* Selected profile fields */}
      <div className="grid grid-cols-2 gap-2">
        {PROFILE_FIELDS.map(({ key, label }) => {
          const v = data.user[key];
          if (v === null || v === undefined || v === "") return null;
          return (
            <div
              key={key}
              className="bg-[var(--input-bg)] rounded p-2 min-w-0"
            >
              <p className="text-[9px] uppercase tracking-widest text-[var(--muted-foreground)]">
                {label}
              </p>
              <p className="text-[12px] font-mono truncate">{formatVal(v)}</p>
            </div>
          );
        })}
      </div>

      {/* Health log */}
      {data.health.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2 flex items-center gap-1">
            <Icon icon="solar:heart-pulse-bold-duotone" width={14} />
            Здоровье ({data.health.length})
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead className="text-[9px] uppercase text-[var(--muted-foreground)]">
                <tr>
                  <th className="text-left pb-1">Дата</th>
                  <th className="text-right pb-1">Вес</th>
                  <th className="text-right pb-1">Рост</th>
                  <th className="text-right pb-1">ИМТ</th>
                </tr>
              </thead>
              <tbody>
                {data.health.slice(0, 8).map((h, i) => (
                  <tr key={i} className="border-t border-dashed border-[var(--border)]">
                    <td className="py-1">{formatVal(h.date)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.weight)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.height)}</td>
                    <td className="py-1 text-right tabular-nums">{formatVal(h.imt)}</td>
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
          Последние действия ({data.recent_actions.length})
        </h4>
        {data.recent_actions.length === 0 ? (
          <p className="text-[var(--muted)] text-[11px]">нет</p>
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
                  {new Date(a.created_at).toLocaleString("ru-RU", {
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

function formatVal(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") {
    // ISO-ish date — render shorter
    if (/^\d{4}-\d{2}-\d{2}T/.test(v)) {
      return new Date(v).toLocaleString("ru-RU", {
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
  if (typeof v === "boolean") return v ? "да" : "нет";
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

  const load = useCallback(async (t: string, p: number) => {
    setLoading(true);
    try {
      const r = await api<TableData>(
        `/api/admin/tables/${t}?page=${p}&per_page=20`,
      );
      setData(r);
      setActive(t);
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
        {tables.map((t) => (
          <button
            key={t}
            onClick={() => load(t, 1)}
            className={`text-[11px] px-3 py-1.5 rounded-full font-mono transition active:scale-95 ${
              active === t
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      {loading && (
        <div className="card-base p-6 text-center text-xs text-[var(--muted)]">
          <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
          загружаем {active}…
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
                    Таблица пуста
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
                      {formatVal(r[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {data.total > data.per_page && (
            <div className="flex items-center justify-between p-3 text-xs border-t border-[var(--border)]">
              <span className="text-[var(--muted)]">
                {data.total} записей · стр {page}
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
          Выберите таблицу выше
        </div>
      )}
    </div>
  );
}
