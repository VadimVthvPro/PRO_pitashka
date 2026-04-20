"use client";

/**
 * Inline editor embedded into the Users drawer.
 *
 * Renders a compact form for the admin-editable subset of `user_main`
 * columns (EDITABLE_USER_FIELDS on the backend). The form is optimistic:
 * every change updates local state immediately; the Save button sends the
 * full delta in one PATCH request and surfaces server errors inline.
 *
 * Tier is rendered as 4 pills ("free · pro · elite · admin") rather than a
 * select — it's a short, exhaustive list and pills make the current choice
 * obvious at a glance.
 *
 * Ban/unban is intentionally a separate button pair with its own confirm
 * flow — it's a scarier action than toggling `ai_disabled`, and mixing it
 * into the generic "Save" button would be easy to trigger by accident.
 */

import { useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Tier = "free" | "pro" | "elite" | "admin";

export interface EditableUser {
  user_id: number;
  user_name: string | null;
  display_name?: string | null;
  bio?: string | null;
  user_sex?: string | null;
  gender?: string | null;
  public_profile?: boolean;
  tier?: Tier;
  ai_disabled?: boolean;
  social_disabled?: boolean;
  is_premium?: boolean;
  social_score?: number;
  banned_at?: string | null;
  ban_reason?: string | null;
}

const TIERS: Tier[] = ["free", "pro", "elite", "admin"];

export function UserEditor({
  user,
  onSaved,
}: {
  user: EditableUser;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState<EditableUser>(user);
  const [banReason, setBanReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setDraft(user);
    setError(null);
    setSuccess(false);
  }, [user]);

  const dirtyFields = useMemo(() => {
    const out: Record<string, unknown> = {};
    (Object.keys(draft) as (keyof EditableUser)[]).forEach((k) => {
      if (k === "user_id" || k === "banned_at" || k === "ban_reason") return;
      const v = draft[k];
      const orig = user[k];
      if (v !== orig && v !== undefined) {
        out[k] = v;
      }
    });
    return out;
  }, [draft, user]);

  const isDirty = Object.keys(dirtyFields).length > 0;
  const isBanned = Boolean(user.banned_at);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api(`/api/admin/users/${user.user_id}`, {
        method: "PATCH",
        body: JSON.stringify(dirtyFields),
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setSaving(false);
    }
  }

  async function ban() {
    if (!window.confirm(t("admin_user_confirm_ban", { id: user.user_id }))) return;
    setSaving(true);
    setError(null);
    try {
      await api(`/api/admin/users/${user.user_id}/ban`, {
        method: "POST",
        body: JSON.stringify({ reason: banReason || null }),
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setSaving(false);
    }
  }

  async function unban() {
    setSaving(true);
    setError(null);
    try {
      await api(`/api/admin/users/${user.user_id}/unban`, { method: "POST" });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-sm flex items-center gap-1.5">
          <Icon icon="solar:pen-2-bold-duotone" width={14} />
          {t("admin_user_edit_title")}
        </h4>
        {isBanned && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--destructive)]/15 text-[var(--destructive)] font-bold uppercase">
            <Icon icon="solar:shield-cross-bold" width={11} className="inline" /> {t("admin_user_banned")}
          </span>
        )}
      </div>

      {/* Tier */}
      <div>
        <label className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
          {t("admin_user_tier")}
        </label>
        <div className="flex gap-1 mt-1 flex-wrap">
          {TIERS.map((tier) => {
            const active = (draft.tier ?? "free") === tier;
            return (
              <button
                key={tier}
                onClick={() => setDraft({ ...draft, tier })}
                className={`text-[11px] px-3 py-1 rounded-full font-semibold transition ${
                  active
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
                }`}
              >
                {tier}
              </button>
            );
          })}
        </div>
      </div>

      {/* String fields */}
      <EditField
        label={t("admin_user_field_name")}
        value={draft.user_name ?? ""}
        onChange={(v) => setDraft({ ...draft, user_name: v })}
      />
      <EditField
        label={t("admin_user_field_display_name")}
        value={draft.display_name ?? ""}
        onChange={(v) => setDraft({ ...draft, display_name: v })}
        maxLength={64}
      />
      <EditField
        label={t("admin_user_field_bio")}
        value={draft.bio ?? ""}
        onChange={(v) => setDraft({ ...draft, bio: v })}
        maxLength={280}
        textarea
      />

      {/* Toggles */}
      <ToggleField
        label={t("admin_user_field_public")}
        value={Boolean(draft.public_profile)}
        onChange={(v) => setDraft({ ...draft, public_profile: v })}
      />
      <ToggleField
        label={t("admin_user_field_is_premium")}
        value={Boolean(draft.is_premium)}
        onChange={(v) => setDraft({ ...draft, is_premium: v })}
      />
      <ToggleField
        label={t("admin_user_field_ai_disabled")}
        value={Boolean(draft.ai_disabled)}
        onChange={(v) => setDraft({ ...draft, ai_disabled: v })}
        tone="warn"
      />
      <ToggleField
        label={t("admin_user_field_social_disabled")}
        value={Boolean(draft.social_disabled)}
        onChange={(v) => setDraft({ ...draft, social_disabled: v })}
        tone="warn"
      />

      {error && (
        <div className="text-xs text-[var(--destructive)] p-2 rounded bg-[var(--destructive)]/10 border border-[var(--destructive)]/30">
          <Icon icon="solar:danger-triangle-bold-duotone" width={14} className="inline mr-1" />
          {error}
        </div>
      )}

      {/* Save */}
      <button
        disabled={!isDirty || saving}
        onClick={save}
        className={`w-full py-2 text-xs font-semibold rounded-lg active:scale-[0.98] transition ${
          success
            ? "bg-[var(--color-sage)] text-white"
            : "bg-[var(--accent)] text-white disabled:opacity-30 disabled:cursor-not-allowed"
        }`}
      >
        {saving ? (
          <Icon icon="svg-spinners:180-ring" width={14} className="inline" />
        ) : success ? (
          <>
            <Icon icon="solar:check-circle-bold" width={14} className="inline mr-1" />
            {t("admin_user_saved")}
          </>
        ) : (
          t("admin_user_save")
        )}
      </button>

      {/* Ban/unban */}
      <div className="pt-3 border-t border-[var(--border)] space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
          {t("admin_user_moderation")}
        </p>
        {!isBanned ? (
          <>
            <input
              value={banReason}
              onChange={(e) => setBanReason(e.target.value)}
              placeholder={t("admin_user_ban_reason_placeholder")}
              maxLength={280}
              className="w-full px-3 py-1.5 text-xs bg-[var(--input-bg)] border border-[var(--border)] rounded-lg focus:border-[var(--destructive)] focus:outline-none"
            />
            <button
              disabled={saving}
              onClick={ban}
              className="w-full py-2 text-xs font-semibold text-[var(--destructive)] border border-[var(--destructive)]/40 rounded-lg active:scale-[0.98] transition hover:bg-[var(--destructive)]/10"
            >
              <Icon icon="solar:shield-cross-bold-duotone" width={14} className="inline mr-1.5" />
              {t("admin_user_btn_ban")}
            </button>
          </>
        ) : (
          <>
            {user.ban_reason && (
              <p className="text-[11px] text-[var(--muted)] p-2 rounded bg-[var(--input-bg)]">
                <b>{t("admin_user_ban_reason")}:</b> {user.ban_reason}
              </p>
            )}
            <button
              disabled={saving}
              onClick={unban}
              className="w-full py-2 text-xs font-semibold bg-[var(--color-sage)] text-white rounded-lg active:scale-[0.98] transition"
            >
              <Icon icon="solar:shield-check-bold-duotone" width={14} className="inline mr-1.5" />
              {t("admin_user_btn_unban")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function EditField({
  label,
  value,
  onChange,
  maxLength,
  textarea,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  maxLength?: number;
  textarea?: boolean;
}) {
  return (
    <div>
      <label className="text-[10px] uppercase tracking-widest text-[var(--muted-foreground)]">
        {label}
      </label>
      {textarea ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={maxLength}
          rows={3}
          className="w-full mt-1 px-3 py-1.5 text-xs bg-[var(--input-bg)] border border-[var(--border)] rounded-lg focus:border-[var(--accent)] focus:outline-none resize-none"
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={maxLength}
          className="w-full mt-1 px-3 py-1.5 text-xs bg-[var(--input-bg)] border border-[var(--border)] rounded-lg focus:border-[var(--accent)] focus:outline-none"
        />
      )}
    </div>
  );
}

function ToggleField({
  label,
  value,
  onChange,
  tone,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  tone?: "warn";
}) {
  const activeColor = tone === "warn" ? "var(--warning)" : "var(--color-sage)";
  return (
    <label className="flex items-center justify-between cursor-pointer py-1">
      <span className="text-xs">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`relative w-10 h-6 rounded-full transition`}
        style={{
          background: value ? activeColor : "var(--input-bg)",
          border: value ? "none" : "1px solid var(--border)",
        }}
      >
        <span
          className={`absolute top-0.5 bg-white shadow rounded-full w-5 h-5 transition-all ${
            value ? "left-[18px]" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}
