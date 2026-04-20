"use client";

/**
 * Admin → Social moderation.
 *
 * Table of `social_posts` with filters (visible/hidden/pinned, kind, author)
 * + detail drawer with Hide/Unhide/Pin/Unpin/Delete buttons. Actions hit
 * `/api/admin/social/posts/:id` (PATCH) and DELETE for hard removal.
 *
 * Hidden posts are kept in the database but never surface in the public feed
 * (the feed query joins on `hidden_at IS NULL`). Pinned posts bubble to top
 * of the feed regardless of created_at.
 *
 * The drawer renders the body as preformatted text rather than Markdown on
 * purpose — we want the admin to see exactly what the user typed, including
 * raw URLs, before deciding.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type StatusFilter = "all" | "visible" | "hidden" | "pinned";
type KindFilter = "all" | "form" | "meal" | "workout";

interface PostItem {
  id: number;
  user_id: number;
  author_name: string;
  telegram_username: string | null;
  kind: string;
  title: string | null;
  body: string;
  tags: string[];
  likes_count: number;
  created_at: string;
  hidden_at: string | null;
  hidden_reason: string | null;
  pinned_at: string | null;
}

const PAGE_SIZE = 30;

export function SocialModerationPanel() {
  const { t, lang } = useI18n();
  const [items, setItems] = useState<PostItem[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<PostItem | null>(null);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(id);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status !== "all") params.set("status", status);
      if (kind !== "all") params.set("kind", kind);
      if (debounced) params.set("search", debounced);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String((page - 1) * PAGE_SIZE));
      const data = await api<{ items: PostItem[]; total: number }>(
        `/api/admin/social/posts?${params}`,
      );
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [status, kind, debounced, page]);

  useEffect(() => {
    load();
  }, [load]);

  async function mutate(post: PostItem, action: "hide" | "unhide" | "pin" | "unpin", reason?: string) {
    await api(`/api/admin/social/posts/${post.id}`, {
      method: "PATCH",
      body: JSON.stringify(reason ? { action, reason } : { action }),
    });
    await load();
    // Refresh the selected post from the new list
    setSelected((cur) => (cur ? items.find((i) => i.id === cur.id) ?? null : null));
  }

  async function hardDelete(post: PostItem) {
    if (!window.confirm(t("admin_social_confirm_delete", { id: post.id }))) return;
    await api(`/api/admin/social/posts/${post.id}`, { method: "DELETE" });
    setSelected(null);
    await load();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="grid lg:grid-cols-[1fr_420px] gap-4">
      <div className="space-y-3 min-w-0">
        {/* Filters */}
        <div className="flex flex-wrap gap-1.5">
          {(["all", "visible", "hidden", "pinned"] as StatusFilter[]).map((s) => (
            <FilterPill
              key={s}
              active={status === s}
              onClick={() => {
                setStatus(s);
                setPage(1);
              }}
            >
              {t(`admin_social_filter_${s}`)}
            </FilterPill>
          ))}
          <span className="mx-1 self-center text-[var(--border)]">|</span>
          {(["all", "form", "meal", "workout"] as KindFilter[]).map((k) => (
            <FilterPill
              key={k}
              active={kind === k}
              onClick={() => {
                setKind(k);
                setPage(1);
              }}
            >
              {k === "all" ? t("admin_social_kind_all") : k}
            </FilterPill>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder={t("admin_social_search_placeholder")}
            className="flex-1 px-3 py-2 text-sm bg-[var(--card)] border border-[var(--border)] rounded-full focus:border-[var(--accent)] focus:outline-none"
          />
          <span className="text-xs text-[var(--muted)] self-center px-2 whitespace-nowrap">
            <b>{total}</b>
          </span>
        </div>

        {/* Post cards */}
        <div className="space-y-2">
          {loading && (
            <div className="card-base p-6 text-center text-xs text-[var(--muted)]">
              <Icon icon="svg-spinners:180-ring" width={20} className="inline mr-2" />
              {t("common_loading_dots")}
            </div>
          )}
          {!loading && items.length === 0 && (
            <div className="card-base p-6 text-center text-xs text-[var(--muted)]">
              {t("admin_social_empty")}
            </div>
          )}
          {!loading &&
            items.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelected(p)}
                className={`w-full text-left card-base p-3 transition hover:bg-[var(--color-sand)]/20 ${
                  selected?.id === p.id ? "border-[var(--accent)]" : ""
                } ${p.hidden_at ? "opacity-65" : ""}`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-[var(--color-sand)]">
                      {p.kind}
                    </span>
                    {p.pinned_at && (
                      <Icon
                        icon="solar:pin-bold-duotone"
                        width={14}
                        className="text-[var(--warning)] shrink-0"
                      />
                    )}
                    {p.hidden_at && (
                      <Icon
                        icon="solar:eye-closed-bold-duotone"
                        width={14}
                        className="text-[var(--destructive)] shrink-0"
                      />
                    )}
                    <span className="text-xs font-semibold truncate">
                      {p.title || p.body.slice(0, 60) || "—"}
                    </span>
                  </div>
                  <span className="text-[10px] text-[var(--muted)] shrink-0">
                    {new Date(p.created_at).toLocaleString(lang, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <p className="text-[11px] text-[var(--muted)] line-clamp-2">
                  {p.body.slice(0, 180)}
                </p>
                <div className="flex flex-wrap gap-2 items-center mt-1.5 text-[10px] text-[var(--muted)]">
                  <span>
                    <Icon icon="solar:user-bold-duotone" width={10} className="inline" /> {p.author_name}
                    {p.telegram_username && ` · @${p.telegram_username}`}
                  </span>
                  <span className="ml-auto">
                    <Icon icon="solar:heart-bold" width={10} className="inline" /> {p.likes_count}
                  </span>
                </div>
              </button>
            ))}
        </div>

        <Pager page={page} totalPages={totalPages} onChange={setPage} t={t} />
      </div>

      {/* Desktop drawer */}
      <div className="hidden lg:block">
        <PostDrawer
          post={selected}
          onClose={() => setSelected(null)}
          onMutate={mutate}
          onDelete={hardDelete}
        />
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key="mobile-drawer"
            className="lg:hidden fixed inset-0 z-50 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelected(null)}
          >
            <motion.div
              className="absolute bottom-0 inset-x-0 bg-[var(--background)] rounded-t-3xl max-h-[90vh] overflow-y-auto"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30 }}
              onClick={(e) => e.stopPropagation()}
            >
              <PostDrawer
                post={selected}
                onClose={() => setSelected(null)}
                onMutate={mutate}
                onDelete={hardDelete}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-[11px] px-3 py-1.5 rounded-full transition active:scale-95 ${
        active
          ? "bg-[var(--accent)] text-white"
          : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
      }`}
    >
      {children}
    </button>
  );
}

function Pager({
  page,
  totalPages,
  onChange,
  t,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
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

function PostDrawer({
  post,
  onClose,
  onMutate,
  onDelete,
}: {
  post: PostItem | null;
  onClose: () => void;
  onMutate: (p: PostItem, a: "hide" | "unhide" | "pin" | "unpin", reason?: string) => void | Promise<void>;
  onDelete: (p: PostItem) => void | Promise<void>;
}) {
  const { t, lang } = useI18n();
  const [reason, setReason] = useState("");

  if (!post) {
    return (
      <div className="card-base p-6 text-center text-sm text-[var(--muted)] min-h-[280px] flex items-center justify-center">
        {t("admin_social_pick_left")}
      </div>
    );
  }

  return (
    <div className="card-base p-4 space-y-4 max-h-[85vh] overflow-y-auto">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
            post #{post.id}
          </p>
          <p className="text-sm font-semibold truncate">
            {post.title || `${post.kind} ${post.id}`}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-[var(--muted)] hover:text-[var(--foreground)] shrink-0"
          aria-label="close"
        >
          <Icon icon="solar:close-circle-bold-duotone" width={24} />
        </button>
      </div>

      {/* Status strip */}
      <div className="flex flex-wrap gap-1.5 text-[10px]">
        <span className="px-2 py-0.5 rounded-full bg-[var(--color-sand)] font-bold uppercase">
          {post.kind}
        </span>
        {post.pinned_at && (
          <span className="px-2 py-0.5 rounded-full bg-[var(--warning)]/15 text-[var(--warning)] font-bold uppercase">
            <Icon icon="solar:pin-bold" width={11} className="inline" /> {t("admin_social_status_pinned")}
          </span>
        )}
        {post.hidden_at && (
          <span className="px-2 py-0.5 rounded-full bg-[var(--destructive)]/15 text-[var(--destructive)] font-bold uppercase">
            <Icon icon="solar:eye-closed-bold" width={11} className="inline" /> {t("admin_social_status_hidden")}
          </span>
        )}
        <span className="ml-auto text-[var(--muted)] text-[10px] self-center">
          {new Date(post.created_at).toLocaleString(lang)}
        </span>
      </div>

      {/* Author */}
      <div className="bg-[var(--input-bg)] rounded-lg p-2.5 text-xs">
        <p className="font-semibold">
          {post.author_name} <span className="text-[var(--muted)]">#{post.user_id}</span>
        </p>
        {post.telegram_username && (
          <p className="text-[var(--muted)]">@{post.telegram_username}</p>
        )}
      </div>

      {/* Body */}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
          {t("admin_social_body_label")}
        </p>
        <pre className="text-xs whitespace-pre-wrap bg-[var(--input-bg)] p-3 rounded-lg max-h-[40vh] overflow-auto font-mono">
          {post.body}
        </pre>
      </div>

      {/* Tags */}
      {post.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {post.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)]"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {post.hidden_reason && (
        <div className="text-[11px] p-2 rounded bg-[var(--destructive)]/10 text-[var(--destructive)]">
          <b>{t("admin_social_hidden_reason")}:</b> {post.hidden_reason}
        </div>
      )}

      {/* Actions */}
      <div className="space-y-2 pt-2 border-t border-[var(--border)]">
        {!post.hidden_at ? (
          <div className="space-y-1.5">
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t("admin_social_hide_reason_placeholder")}
              className="w-full px-3 py-1.5 text-xs bg-[var(--input-bg)] border border-[var(--border)] rounded-lg focus:border-[var(--accent)] focus:outline-none"
            />
            <button
              onClick={() => onMutate(post, "hide", reason || undefined)}
              className="w-full py-2 text-xs font-semibold bg-[var(--warning)] text-white rounded-lg active:scale-[0.98] transition"
            >
              <Icon icon="solar:eye-closed-bold-duotone" width={14} className="inline mr-1.5" />
              {t("admin_social_action_hide")}
            </button>
          </div>
        ) : (
          <button
            onClick={() => onMutate(post, "unhide")}
            className="w-full py-2 text-xs font-semibold bg-[var(--color-sage)] text-white rounded-lg active:scale-[0.98] transition"
          >
            <Icon icon="solar:eye-bold-duotone" width={14} className="inline mr-1.5" />
            {t("admin_social_action_unhide")}
          </button>
        )}

        {!post.pinned_at ? (
          <button
            onClick={() => onMutate(post, "pin")}
            className="w-full py-2 text-xs font-semibold bg-[var(--card)] border border-[var(--border)] rounded-lg active:scale-[0.98] transition hover:bg-[var(--color-sand)]/30"
          >
            <Icon icon="solar:pin-bold-duotone" width={14} className="inline mr-1.5" />
            {t("admin_social_action_pin")}
          </button>
        ) : (
          <button
            onClick={() => onMutate(post, "unpin")}
            className="w-full py-2 text-xs font-semibold bg-[var(--card)] border border-[var(--border)] rounded-lg active:scale-[0.98] transition hover:bg-[var(--color-sand)]/30"
          >
            <Icon icon="solar:pin-crossed-bold-duotone" width={14} className="inline mr-1.5" />
            {t("admin_social_action_unpin")}
          </button>
        )}

        <button
          onClick={() => onDelete(post)}
          className="w-full py-2 text-xs font-semibold text-[var(--destructive)] border border-[var(--destructive)]/40 rounded-lg active:scale-[0.98] transition hover:bg-[var(--destructive)]/10"
        >
          <Icon icon="solar:trash-bin-trash-bold-duotone" width={14} className="inline mr-1.5" />
          {t("admin_social_action_delete")}
        </button>
      </div>
    </div>
  );
}
