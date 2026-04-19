"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "@/lib/api";

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

const KINDS: { id: Kind; label: string; icon: string; color: string }[] = [
  { id: "form", label: "Форма", icon: "solar:user-rounded-bold-duotone", color: "var(--accent)" },
  { id: "meal", label: "Блюдо", icon: "solar:plate-bold-duotone", color: "var(--color-sage)" },
  { id: "workout", label: "Тренировка", icon: "solar:dumbbell-large-bold-duotone", color: "var(--color-amber)" },
];

const SUGGESTED_TAGS = [
  "новичок", "силовая", "кардио", "сушка", "масса", "веган",
  "женщины", "мужчины", "20-30", "30-40", "40+", "домашние",
];

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "только что";
  if (m < 60) return `${m} мин`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ч`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d} дн`;
  return new Date(iso).toLocaleDateString("ru-RU");
}

export default function SocialPage() {
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
    if (!confirm("Удалить пост?")) return;
    try {
      await api(`/api/social/posts/${p.id}`, { method: "DELETE" });
      setPosts((prev) => prev.filter((x) => x.id !== p.id));
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <header className="mb-6 lg:mb-10 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
            community
          </p>
          <h1
            className="text-[var(--foreground)] mt-1"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(2.2rem, 4vw, 3.5rem)",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
            }}
          >
            Соцсеть атлетов
          </h1>
          <p className="mt-2 text-[var(--muted)] text-sm max-w-md">
            Делись формой, блюдами и тренировками. Лайкай чужое — поднимай своё.
          </p>
        </div>
        <button
          onClick={() => setShowCompose(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-[var(--accent)] text-white rounded-[var(--radius)] font-semibold hover:bg-[var(--accent-hover)] transition shadow-[var(--shadow-accent)]"
        >
          <Icon icon="solar:add-circle-bold-duotone" width={20} />
          Поделиться
        </button>
      </header>

      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2 mb-3">
            <FilterChip active={filter === "all"} onClick={() => setFilter("all")}>
              Всё
            </FilterChip>
            {KINDS.map((k) => (
              <FilterChip
                key={k.id}
                active={filter === k.id}
                onClick={() => setFilter(k.id)}
                icon={k.icon}
              >
                {k.label}
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
            <div className="py-12 text-center text-[var(--muted)] text-sm">Загружаем…</div>
          ) : posts.length === 0 ? (
            <div className="py-12 text-center">
              <Icon
                icon="solar:users-group-rounded-bold-duotone"
                width={56}
                className="text-[var(--muted)] mx-auto mb-3 opacity-40"
              />
              <p className="text-[var(--muted)] text-sm">
                Пока пусто. Стань первым, кто поделится!
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
                    onTagClick={(t) => setTag(t)}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          {me && <MyCard me={me} onChanged={loadMe} />}

          <div className="card-base p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
                Топ-10
              </p>
              <select
                value={leaderCat}
                onChange={(e) => setLeaderCat(e.target.value as "overall" | "consistency")}
                className="text-xs bg-transparent border border-[var(--border)] rounded px-2 py-1 outline-none"
              >
                <option value="overall">по очкам</option>
                <option value="consistency">по стрику</option>
              </select>
            </div>
            <ol className="space-y-1.5">
              {leaders.length === 0 && (
                <p className="text-xs text-[var(--muted)]">пока нет участников</p>
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
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition ${
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
}: {
  post: Post;
  isMine: boolean;
  onLike: () => void;
  onDelete: () => void;
  onTagClick: (t: string) => void;
}) {
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
              <span>{kindMeta.label}</span>
              <span>·</span>
              <span>{timeAgo(post.created_at)}</span>
            </p>
          </div>
        </div>
        {isMine && (
          <button
            onClick={onDelete}
            className="text-[var(--muted)] hover:text-[var(--destructive)] transition"
            title="Удалить"
          >
            <Icon icon="solar:trash-bin-2-bold-duotone" width={18} />
          </button>
        )}
      </header>

      {post.title && (
        <h3 className="font-semibold text-base mb-2 leading-snug">{post.title}</h3>
      )}
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
          className={`flex items-center gap-1.5 text-sm transition ${
            post.liked_by_me ? "text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--foreground)]"
          }`}
        >
          <Icon
            icon={post.liked_by_me ? "solar:heart-bold" : "solar:heart-linear"}
            width={20}
          />
          <span className="tabular-nums">{post.likes_count}</span>
        </button>
      </footer>
    </motion.article>
  );
}

function MyCard({ me, onChanged }: { me: MyProfile; onChanged: () => void }) {
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
          <p className="text-[11px] text-[var(--muted)]">очки: {me.social_score}</p>
        </div>
        <button
          onClick={() => setEditing((v) => !v)}
          className="text-[var(--muted)] hover:text-[var(--accent)] transition"
        >
          <Icon icon="solar:pen-2-bold-duotone" width={18} />
        </button>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3 text-center text-xs">
        <Stat label="посты" value={me.posts_count} />
        <Stat label="подписчиков" value={me.followers} />
        <Stat label="подписок" value={me.following} />
      </div>

      {editing && (
        <div className="mt-3 space-y-2 text-sm">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Отображаемое имя"
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm"
          />
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="О себе (до 280 символов)"
            rows={2}
            maxLength={280}
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm resize-none"
          />
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm"
          >
            <option value="">не указан</option>
            <option value="male">мужской</option>
            <option value="female">женский</option>
            <option value="other">другое</option>
          </select>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={pub}
              onChange={(e) => setPub(e.target.checked)}
            />
            Показывать в рейтингах и поиске
          </label>
          <button
            disabled={saving}
            onClick={save}
            className="w-full py-2 bg-[var(--accent)] text-white rounded text-sm font-semibold disabled:opacity-50"
          >
            {saving ? "Сохраняем…" : "Сохранить"}
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
  const [kind, setKind] = useState<Kind>("form");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tagsRaw, setTagsRaw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const tags = useMemo(
    () =>
      tagsRaw
        .split(/[,\s]+/)
        .map((t) => t.trim().replace(/^#/, "").toLowerCase())
        .filter(Boolean)
        .slice(0, 6),
    [tagsRaw],
  );

  async function submit() {
    if (!body.trim()) {
      setError("Напиши что-нибудь");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const res = await api<Post>("/api/social/posts", {
        method: "POST",
        body: JSON.stringify({ kind, title, body, tags }),
      });
      onCreated(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
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
        className="fixed inset-0 z-[80] bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.97 }}
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[90] w-[92vw] max-w-md bg-[var(--card)] rounded-[var(--radius)] shadow-[var(--shadow-3)] border border-[var(--border)] p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-lg">Поделиться</h3>
          <button onClick={onClose} className="text-[var(--muted)]">
            <Icon icon="solar:close-circle-bold-duotone" width={24} />
          </button>
        </div>

        <div className="grid grid-cols-3 gap-1.5 mb-3">
          {KINDS.map((k) => (
            <button
              key={k.id}
              onClick={() => setKind(k.id)}
              className={`py-2 rounded text-xs font-semibold transition flex flex-col items-center gap-1 ${
                kind === k.id
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--input-bg)] text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              <Icon icon={k.icon} width={18} />
              {k.label}
            </button>
          ))}
        </div>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={140}
          placeholder="Заголовок (необязательно)"
          className="w-full px-3 py-2 mb-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={5}
          maxLength={4000}
          placeholder={
            kind === "form"
              ? "Расскажи, как идут дела с формой — вес, ощущения, прогресс…"
              : kind === "meal"
              ? "Опиши блюдо: ингредиенты, КБЖУ, рецепт…"
              : "Опиши тренировку: упражнения, подходы, веса…"
          }
          className="w-full px-3 py-2 mb-2 bg-[var(--input-bg)] border border-[var(--border)] rounded text-sm resize-none"
        />
        <input
          value={tagsRaw}
          onChange={(e) => setTagsRaw(e.target.value)}
          placeholder="теги через запятую: новичок, силовая, женщины"
          className="w-full px-3 py-2 mb-3 bg-[var(--input-bg)] border border-[var(--border)] rounded text-xs"
        />
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {tags.map((t) => (
              <span
                key={t}
                className="text-[11px] px-2 py-0.5 rounded-full bg-[var(--color-sand)] text-[var(--accent)]"
              >
                #{t}
              </span>
            ))}
          </div>
        )}

        {error && <p className="text-xs text-[var(--destructive)] mb-2">{error}</p>}

        <button
          disabled={submitting || !body.trim()}
          onClick={submit}
          className="w-full py-2.5 bg-[var(--accent)] text-white rounded font-semibold disabled:opacity-50"
        >
          {submitting ? "Публикуем…" : "Опубликовать"}
        </button>
      </motion.div>
    </>
  );
}
