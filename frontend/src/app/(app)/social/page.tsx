"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "@/lib/api";
import { useI18n, type Lang } from "@/lib/i18n";

type Kind = "form" | "meal" | "workout";

interface Author {
  user_id: number;
  name: string;
  telegram_username: string | null;
  gender: string | null;
  score: number;
}

interface Post {
  id: number;
  kind: Kind;
  title: string | null;
  body: string;
  tags: string[];
  payload: Record<string, unknown>;
  likes_count: number;
  liked_by_me: boolean;
  created_at: string;
  author: Author | null;
}

interface MyProfile {
  user_id: number;
  name: string;
  display_name: string | null;
  bio: string | null;
  gender: string | null;
  public_profile: boolean;
  social_score: number;
  posts_count: number;
  followers: number;
  following: number;
}

interface LeaderRow {
  user_id: number;
  name: string;
  score: number;
}

const KINDS: { id: Kind; labelKey: string; icon: string; color: string }[] = [
  { id: "form", labelKey: "social_kind_form", icon: "solar:user-rounded-bold-duotone", color: "var(--accent)" },
  { id: "meal", labelKey: "social_kind_meal", icon: "solar:plate-bold-duotone", color: "var(--color-sage)" },
  { id: "workout", labelKey: "social_kind_workout", icon: "solar:dumbbell-large-bold-duotone", color: "var(--color-amber)" },
];

// Neutral, goal-oriented tags. The previous list (новичок / женщины /
// 20-30 / 40+ etc.) was reported as judgemental and unwelcoming, so the
// vocabulary now focuses on intent and lifestyle rather than identity.
const SUGGESTED_TAGS = [
  "снижение_веса",
  "поддержание",
  "набор_массы",
  "силовые",
  "кардио",
  "йога",
  "растяжка",
  "бег",
  "ходьба",
  "велосипед",
  "плавание",
  "домашние_тренировки",
  "зал",
  "вегетарианство",
  "правильное_питание",
  "пп_рецепты",
  "мотивация",
  "первый_шаг",
  "прогресс",
  "марафон_30_дней",
];

function timeAgo(
  iso: string,
  t: (key: string, vars?: Record<string, string | number>) => string,
  lang: Lang,
): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return t("social_time_just_now");
  if (m < 60) return t("social_time_min", { n: m });
  const h = Math.floor(m / 60);
  if (h < 24) return t("social_time_h", { n: h });
  const d = Math.floor(h / 24);
  if (d < 7) return t("social_time_d", { n: d });
  return new Date(iso).toLocaleDateString(lang);
}

export default function SocialPage() {
  const { t, lang } = useI18n();
  const [posts, setPosts] = useState<Post[]>([]);
  const [filter, setFilter] = useState<Kind | "all">("all");
  const [tag, setTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<MyProfile | null>(null);
  const [leaders, setLeaders] = useState<LeaderRow[]>([]);
  const [leaderCat, setLeaderCat] = useState<"overall" | "consistency">("overall");
  const [showCompose, setShowCompose] = useState(false);

  const loadFeed = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== "all") params.set("kind", filter);
      if (tag) params.set("tag", tag);
      params.set("limit", "30");
      const data = await api<{ items: Post[] }>(`/api/social/feed?${params}`);
      setPosts(data.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter, tag]);

  const loadMe = useCallback(async () => {
    try {
      setMe(await api<MyProfile>("/api/social/me"));
    } catch (e) {
      console.error(e);
    }
  }, []);

  const loadLeaders = useCallback(async () => {
    try {
      const data = await api<{ items: LeaderRow[] }>(
        `/api/social/leaderboard?category=${leaderCat}&limit=10`,
      );
      setLeaders(data.items);
    } catch (e) {
      console.error(e);
    }
  }, [leaderCat]);

  useEffect(() => { loadFeed(); }, [loadFeed]);
  useEffect(() => { loadMe(); }, [loadMe]);
  useEffect(() => { loadLeaders(); }, [loadLeaders]);

  async function toggleLike(p: Post) {
    setPosts((prev) =>
      prev.map((x) =>
        x.id === p.id
          ? {
              ...x,
              liked_by_me: !x.liked_by_me,
              likes_count: x.likes_count + (x.liked_by_me ? -1 : 1),
            }
          : x,
      ),
    );
    try {
      await api(`/api/social/posts/${p.id}/like`, { method: "POST" });
    } catch {
      loadFeed();
    }
  }

  async function deletePost(p: Post) {
    if (!confirm(t("social_confirm_delete_post"))) return;
    try {
      await api(`/api/social/posts/${p.id}`, { method: "DELETE" });
      setPosts((prev) => prev.filter((x) => x.id !== p.id));
    } catch (e) {
      console.error(e);
    }
  }

  return (
    // Layout already provides max-width, padding and safe-area. Don't double up.
    <div>
      <header className="mb-6 lg:mb-10 flex items-end justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
            community
          </p>
          <h1
            className="text-[var(--foreground)] mt-1"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(2rem, 7vw, 3.5rem)",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
            }}
          >
            {t("social_hero_title")}
          </h1>
          <p className="mt-2 text-[var(--muted)] text-sm max-w-md">
            {t("social_hero_subtitle")}
          </p>
        </div>
        <button
          onClick={() => setShowCompose(true)}
          className="inline-flex items-center gap-2 px-4 min-h-11 bg-[var(--accent)] text-white rounded-[var(--radius)] font-semibold hover:bg-[var(--accent-hover)] transition shadow-[var(--shadow-accent)] touch-manipulation"
        >
          <Icon icon="solar:add-circle-bold-duotone" width={20} />
          {t("social_btn_share")}
        </button>
      </header>

      {/* На мобиле сначала показываем профиль и лидерборд (aside получает
          order-first), затем ленту. Так пользователь видит «это я и мой
          рейтинг» выше первого экрана — без бесконечного скролла вниз. */}
      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="min-w-0 order-last lg:order-first">
          <div className="flex flex-wrap gap-2 mb-3">
            <FilterChip active={filter === "all"} onClick={() => setFilter("all")}>
              {t("social_filter_all")}
            </FilterChip>
            {KINDS.map((k) => (
              <FilterChip
                key={k.id}
                active={filter === k.id}
                onClick={() => setFilter(k.id)}
                icon={k.icon}
              >
                {t(k.labelKey)}
              </FilterChip>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 mb-5">
            {tag && (
              <button
                onClick={() => setTag(null)}
                className="text-xs px-2.5 py-1 rounded-full bg-[var(--accent)] text-white inline-flex items-center gap-1"
              >
                #{tag}
                <Icon icon="solar:close-circle-bold" width={14} />
              </button>
            )}
            {!tag &&
              SUGGESTED_TAGS.slice(0, 8).map((t) => (
                <button
                  key={t}
                  onClick={() => setTag(t)}
                  className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] text-[var(--muted)] hover:text-[var(--accent)] hover:border-[var(--accent)] transition"
                >
                  #{t}
                </button>
              ))}
          </div>

          {loading ? (
            <div className="py-12 text-center text-[var(--muted)] text-sm">{t("social_feed_loading")}</div>
          ) : posts.length === 0 ? (
            <div className="py-12 text-center">
              <Icon
                icon="solar:users-group-rounded-bold-duotone"
                width={56}
                className="text-[var(--muted)] mx-auto mb-3 opacity-40"
              />
              <p className="text-[var(--muted)] text-sm">
                {t("social_feed_empty")}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <AnimatePresence>
                {posts.map((p) => (
                  <PostCard
                    key={p.id}
                    post={p}
                    isMine={me?.user_id === p.author?.user_id}
                    onLike={() => toggleLike(p)}
                    onDelete={() => deletePost(p)}
                    onTagClick={(tagId) => setTag(tagId)}
                    timeLabel={timeAgo(p.created_at, t, lang)}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        <aside className="space-y-4 order-first lg:order-last">
          {me && <MyCard me={me} onChanged={loadMe} />}

          <div className="card-base p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                {t("social_leaderboard_title")}
              </p>
              <select
                value={leaderCat}
                onChange={(e) => setLeaderCat(e.target.value as "overall" | "consistency")}
                className="text-xs bg-transparent border border-[var(--border)] rounded px-2 py-1 outline-none"
              >
                <option value="overall">{t("social_sort_points")}</option>
                <option value="consistency">{t("social_sort_streak")}</option>
              </select>
            </div>
            <ol className="space-y-1.5">
              {leaders.length === 0 && (
                <p className="text-xs text-[var(--muted)]">{t("social_leaderboard_empty")}</p>
              )}
              {leaders.map((l, i) => (
                <li
                  key={l.user_id}
                  className={`flex items-center justify-between text-sm py-1.5 px-2 rounded ${
                    me?.user_id === l.user_id ? "bg-[var(--color-sand)]" : ""
                  }`}
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <span
                      className={`w-6 text-xs font-mono ${
                        i === 0
                          ? "text-[var(--color-amber)]"
                          : i < 3
                          ? "text-[var(--accent)]"
                          : "text-[var(--muted)]"
                      }`}
                    >
                      {i + 1}.
                    </span>
                    <span className="truncate">{l.name}</span>
                  </span>
                  <span className="text-[var(--muted)] text-xs tabular-nums">{l.score}</span>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>

      <AnimatePresence>
        {showCompose && (
          <ComposeModal
            onClose={() => setShowCompose(false)}
            onCreated={(p) => {
              setPosts((prev) => [p, ...prev]);
              setShowCompose(false);
              loadMe();
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 min-h-10 rounded-full text-xs font-semibold transition touch-manipulation ${
        active
          ? "bg-[var(--accent)] text-white"
          : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
      }`}
    >
      {icon && <Icon icon={icon} width={14} />}
      {children}
    </button>
  );
}

function PostCard({
  post,
  isMine,
  onLike,
  onDelete,
  onTagClick,
  timeLabel,
}: {
  post: Post;
  isMine: boolean;
  onLike: () => void;
  onDelete: () => void;
  onTagClick: (tagId: string) => void;
  timeLabel: string;
}) {
  const { t } = useI18n();
  const kindMeta = KINDS.find((k) => k.id === post.kind)!;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="card-base p-4"
    >
      <header className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0"
            style={{ background: kindMeta.color }}
          >
            <Icon icon={kindMeta.icon} width={20} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">{post.author?.name ?? "user"}</p>
            <p className="text-[11px] text-[var(--muted)] flex items-center gap-1.5">
              <span>{t(kindMeta.labelKey)}</span>
              <span>·</span>
              <span>{timeLabel}</span>
            </p>
          </div>
        </div>
        {isMine && (
          <button
            onClick={onDelete}
            className="w-11 h-11 -mr-2 flex items-center justify-center text-[var(--muted)] hover:text-[var(--destructive)] transition rounded-full touch-manipulation"
            title={t("social_post_delete")}
            aria-label={t("social_post_delete")}
          >
            <Icon icon="solar:trash-bin-2-bold-duotone" width={20} />
          </button>
        )}
      </header>

      {post.title && (
        <h3 className="font-semibold text-base mb-2 leading-snug">{post.title}</h3>
      )}

      {typeof post.payload?.photo_url === "string" && post.payload.photo_url ? (
        <a
          href={post.payload.photo_url as string}
          target="_blank"
          rel="noopener noreferrer"
          className="block mb-3 -mx-1 sm:-mx-2 overflow-hidden rounded-[var(--radius)] border border-[var(--border)] bg-[var(--input-bg)]"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={post.payload.photo_url as string}
            alt={post.title || t("social_post_photo_alt")}
            loading="lazy"
            className="w-full max-h-[520px] object-cover"
          />
        </a>
      ) : null}

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--foreground)]">
        {post.body}
      </p>

      {post.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {post.tags.map((t) => (
            <button
              key={t}
              onClick={() => onTagClick(t)}
              className="text-[11px] px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted)] hover:text-[var(--accent)] hover:border-[var(--accent)] transition"
            >
              #{t}
            </button>
          ))}
        </div>
      )}

      <footer className="mt-4 pt-3 border-t border-dashed border-[var(--border)] flex items-center gap-4">
        <button
          onClick={onLike}
          className={`inline-flex items-center gap-1.5 text-sm transition min-h-11 px-2 -ml-2 rounded-full touch-manipulation ${
            post.liked_by_me ? "text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--foreground)]"
          }`}
        >
          <Icon
            icon={post.liked_by_me ? "solar:heart-bold" : "solar:heart-linear"}
            width={22}
          />
          <span className="tabular-nums">{post.likes_count}</span>
        </button>
      </footer>
    </motion.article>
  );
}

function MyCard({ me, onChanged }: { me: MyProfile; onChanged: () => void }) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(me.display_name ?? "");
  const [bio, setBio] = useState(me.bio ?? "");
  const [gender, setGender] = useState(me.gender ?? "");
  const [pub, setPub] = useState(me.public_profile);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api("/api/social/me", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: name,
          bio,
          gender: gender || null,
          public_profile: pub,
        }),
      });
      setEditing(false);
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card-base p-4">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-[var(--accent)] text-white flex items-center justify-center font-bold text-lg">
          {(me.display_name ?? me.name).slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold truncate">{me.display_name ?? me.name}</p>
          <p className="text-[11px] text-[var(--muted)]">
            {t("social_profile_points")} {me.social_score}
          </p>
        </div>
        <button
          onClick={() => setEditing((v) => !v)}
          className="w-11 h-11 -mr-2 flex items-center justify-center text-[var(--muted)] hover:text-[var(--accent)] transition rounded-full touch-manipulation"
          aria-label={t("common_edit")}
        >
          <Icon icon="solar:pen-2-bold-duotone" width={20} />
        </button>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3 text-center text-xs">
        <Stat label={t("social_stat_posts")} value={me.posts_count} />
        <Stat label={t("social_stat_followers")} value={me.followers} />
        <Stat label={t("social_stat_following")} value={me.following} />
      </div>

      {editing && (
        <div className="mt-3 space-y-2 text-sm">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("social_placeholder_display_name")}
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm"
          />
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder={t("social_placeholder_bio")}
            rows={2}
            maxLength={280}
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm resize-none"
          />
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm"
          >
            <option value="">{t("social_sex_unspecified")}</option>
            <option value="male">{t("social_sex_male")}</option>
            <option value="female">{t("social_sex_female")}</option>
            <option value="other">{t("social_sex_other")}</option>
          </select>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={pub}
              onChange={(e) => setPub(e.target.checked)}
            />
            {t("social_show_in_rankings")}
          </label>
          <button
            disabled={saving}
            onClick={save}
            className="w-full py-2 bg-[var(--accent)] text-white rounded text-sm font-semibold disabled:opacity-50"
          >
            {saving ? t("common_saving_dots") : t("save")}
          </button>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="font-bold tabular-nums text-base">{value}</p>
      <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{label}</p>
    </div>
  );
}

function ComposeModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (p: Post) => void;
}) {
  const { t } = useI18n();
  const [kind, setKind] = useState<Kind>("form");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tagsRaw, setTagsRaw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoUploading, setPhotoUploading] = useState(false);

  const tags = useMemo(
    () =>
      tagsRaw
        .split(/[,\s]+/)
        .map((t) => t.trim().replace(/^#/, "").toLowerCase())
        .filter(Boolean)
        .slice(0, 6),
    [tagsRaw],
  );

  function pickPhoto(file: File | null) {
    if (!file) {
      setPhotoFile(null);
      if (photoPreview) URL.revokeObjectURL(photoPreview);
      setPhotoPreview(null);
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError(t("social_err_image_type"));
      return;
    }
    if (file.size > 6 * 1024 * 1024) {
      setError(t("social_err_image_size"));
      return;
    }
    setError("");
    setPhotoFile(file);
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function uploadPhoto(): Promise<string | null> {
    if (!photoFile) return null;
    setPhotoUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", photoFile);
      const res = await fetch("/api/social/posts/photo", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t("social_err_upload_status", { status: res.status }));
      }
      const json: { url: string } = await res.json();
      return json.url;
    } finally {
      setPhotoUploading(false);
    }
  }

  async function submit() {
    if (!body.trim() && !photoFile) {
      setError(t("social_err_need_content"));
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const photoUrl = await uploadPhoto();
      const payload: Record<string, unknown> = {};
      if (photoUrl) payload.photo_url = photoUrl;

      const res = await api<Post>("/api/social/posts", {
        method: "POST",
        body: JSON.stringify({
          kind,
          title,
          body:
            body.trim() ||
            (kind === "meal"
              ? t("social_default_body_meal")
              : kind === "workout"
                ? t("social_default_body_workout")
                : t("social_default_body_form")),
          tags,
          payload,
        }),
      });
      onCreated(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-[80] bg-black/55 backdrop-blur-sm"
      />
      {/* Bottom-sheet on mobile, centered dialog on sm+.
          Using dvh + safe-bottom so the sheet never clips the keyboard or home indicator. */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        transition={{ type: "spring", stiffness: 320, damping: 32 }}
        className="fixed inset-x-0 bottom-0 sm:left-1/2 sm:top-1/2 sm:inset-auto sm:-translate-x-1/2 sm:-translate-y-1/2 z-[90] w-full sm:w-[94vw] sm:max-w-lg max-h-[95dvh] sm:max-h-[90vh] overflow-y-auto bg-[var(--card)] rounded-t-[var(--radius-lg)] sm:rounded-[var(--radius-lg)] shadow-[var(--shadow-3)] border border-[var(--border)]"
        style={{ paddingBottom: "var(--safe-bottom)" }}
      >
        {/* Grab bar (mobile only) */}
        <div className="sm:hidden pt-2 pb-1 flex justify-center">
          <span className="block w-10 h-1 rounded-full bg-[var(--border)]" aria-hidden />
        </div>

        {/* Header */}
        <div className="sticky top-0 z-10 bg-[var(--card)] flex items-center justify-between px-5 py-3 sm:py-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-2 min-w-0">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-[var(--accent)] text-white shadow-[var(--shadow-1)] shrink-0"
            >
              <Icon icon="ph:share-network-fill" width={18} />
            </span>
            <h3 className="font-display text-lg font-semibold truncate">{t("social_compose_title")}</h3>
          </div>
          <button
            onClick={onClose}
            aria-label={t("common_close")}
            className="w-11 h-11 flex items-center justify-center rounded-full text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--color-sand)]/50 transition touch-manipulation shrink-0"
          >
            <Icon icon="ph:x-bold" width={20} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Kind picker */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-2">
              {t("social_compose_topic")}
            </p>
            <div className="grid grid-cols-3 gap-2">
              {KINDS.map((k) => (
                <button
                  key={k.id}
                  type="button"
                  onClick={() => setKind(k.id)}
                  className={`py-3 rounded-[var(--radius)] text-xs font-semibold transition flex flex-col items-center gap-1.5 border ${
                    kind === k.id
                      ? "bg-[var(--accent)] text-white border-[var(--accent)] shadow-[var(--shadow-1)]"
                      : "bg-[var(--input-bg)] text-[var(--muted-foreground)] border-[var(--border)] hover:text-[var(--foreground)] hover:border-[var(--accent)]/40"
                  }`}
                >
                  <Icon icon={k.icon} width={22} />
                  {t(k.labelKey)}
                </button>
              ))}
            </div>
          </div>

          {/* Photo dropzone */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-2">
              {t("social_compose_photo_optional")}
            </p>
            {photoPreview ? (
              <div className="relative rounded-[var(--radius)] overflow-hidden border border-[var(--border)] group">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photoPreview}
                  alt={t("social_photo_preview_alt")}
                  className="w-full max-h-72 object-cover"
                />
                <button
                  type="button"
                  onClick={() => pickPhoto(null)}
                  className="absolute top-2 right-2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/60 text-white hover:bg-black/80 transition touch-manipulation"
                  aria-label={t("social_photo_remove_aria")}
                >
                  <Icon icon="ph:x-bold" width={18} />
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center gap-2 py-6 border-2 border-dashed border-[var(--border)] rounded-[var(--radius)] bg-[var(--input-bg)]/50 hover:border-[var(--accent)]/40 hover:bg-[var(--input-bg)] cursor-pointer transition">
                <Icon icon="ph:image-square" width={28} className="text-[var(--muted-foreground)]" />
                <span className="text-sm text-[var(--muted-foreground)]">
                  {t("social_dropzone_hint")}
                </span>
                <span className="text-[10px] text-[var(--muted-foreground)]">
                  {t("social_dropzone_formats")}
                </span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => pickPhoto(e.target.files?.[0] ?? null)}
                />
              </label>
            )}
          </div>

          {/* Title */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
              {t("social_field_title")}
            </p>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={140}
              placeholder={t("social_placeholder_title_example")}
              className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-sm focus:border-[var(--accent)] focus:outline-none"
            />
          </div>

          {/* Body */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
              {t("social_field_body")}
            </p>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              maxLength={4000}
              placeholder={
                kind === "form"
                  ? t("social_placeholder_body_form")
                  : kind === "meal"
                    ? t("social_placeholder_body_meal")
                    : t("social_placeholder_body_workout")
              }
              className="w-full px-3 py-2.5 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-sm resize-none focus:border-[var(--accent)] focus:outline-none"
            />
            <p className="text-[10px] text-[var(--muted-foreground)] text-right mt-1 tabular-nums">
              {body.length} / 4000
            </p>
          </div>

          {/* Tags */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)] mb-1">
              {t("social_field_tags")}
            </p>
            <input
              value={tagsRaw}
              onChange={(e) => setTagsRaw(e.target.value)}
              placeholder={t("social_placeholder_tags")}
              className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded-[var(--radius)] text-sm focus:border-[var(--accent)] focus:outline-none"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {(tags.length > 0 ? tags : SUGGESTED_TAGS.slice(0, 6)).map((t) => {
                const active = tags.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      if (active) {
                        setTagsRaw(tags.filter((x) => x !== t).join(" "));
                      } else if (tags.length < 6) {
                        setTagsRaw([...tags, t].join(" "));
                      }
                    }}
                    className={`text-[11px] px-2 py-0.5 rounded-full border transition ${
                      active
                        ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                        : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--accent)] hover:border-[var(--accent)]/40"
                    }`}
                  >
                    #{t}
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div
              className="rounded-[var(--radius)] border border-[var(--warning)] bg-[var(--color-sand)]/80 px-3 py-2 text-xs"
              role="alert"
            >
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-[var(--card)] border-t border-[var(--border)] px-5 py-3 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 min-h-11 text-sm rounded-[var(--radius)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] touch-manipulation"
          >
            {t("cancel")}
          </button>
          <button
            disabled={submitting || photoUploading || (!body.trim() && !photoFile)}
            onClick={submit}
            className="px-5 min-h-11 bg-[var(--accent)] text-white rounded-[var(--radius)] text-sm font-semibold disabled:opacity-50 inline-flex items-center gap-2 shadow-[var(--shadow-1)] touch-manipulation"
          >
            {submitting || photoUploading ? (
              <>
                <Icon icon="ph:circle-notch" width={16} className="animate-spin" />
                {photoUploading ? t("social_publish_uploading") : t("social_publish_posting")}
              </>
            ) : (
              <>
                <Icon icon="ph:paper-plane-tilt-fill" width={16} />
                {t("social_publish")}
              </>
            )}
          </button>
        </div>
      </motion.div>
    </>
  );
}
