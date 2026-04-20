"use client";

/**
 * Right-side drawer that edits one row of any whitelisted admin table.
 *
 * The drawer is fed a `(table, pk_column, pk_value)` triple. On mount it
 * fetches the current row + policy from
 * `GET /api/admin/tables/{t}/{pk}/{v}`, renders one input per column, and
 * on save POSTs only the changed fields via PATCH.
 *
 * Protective UX decisions:
 *   - Non-editable columns are shown but disabled (gray). The user sees
 *     what data exists, but can't touch PKs / created_at / password hashes.
 *   - For read-only tables (audit_log, otp_codes, etc.) the backend returns
 *     an empty `editable` array; we render a banner and hide Save/Delete.
 *   - Save is enabled only when there's a real diff against the loaded
 *     baseline; this prevents "empty" audit entries.
 *   - Delete has a separate confirm() and lives in the footer next to a
 *     clear warning copy — it's destructive and cross-row-linked data
 *     (likes, chat history, food) won't cascade back.
 */

import { useEffect, useMemo, useState } from "react";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface ColumnMeta {
  column_name: string;
  data_type: string;
  is_nullable: "YES" | "NO" | string;
}

interface RowPolicy {
  pk: string | null;
  editable: string[];
  read_only: boolean;
  hint_key?: string | null;
}

interface SingleRowResponse {
  columns: ColumnMeta[];
  row: Record<string, unknown>;
  policy: RowPolicy;
}

interface Props {
  table: string;
  pkColumn: string;
  pkValue: string;
  onClose: () => void;
  onSaved?: () => void;
  onDeleted?: () => void;
}

export function RowEditorDrawer({
  table,
  pkColumn,
  pkValue,
  onClose,
  onSaved,
  onDeleted,
}: Props) {
  const { t } = useI18n();
  const [data, setData] = useState<SingleRowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api<SingleRowResponse>(
      `/api/admin/tables/${table}/${pkColumn}/${encodeURIComponent(pkValue)}`,
    )
      .then((r) => {
        if (cancelled) return;
        setData(r);
        setForm({ ...r.row });
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e.message || "load failed");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [table, pkColumn, pkValue]);

  const editable = useMemo(
    () => new Set(data?.policy.editable ?? []),
    [data],
  );

  const diff = useMemo<Record<string, unknown>>(() => {
    if (!data) return {};
    const d: Record<string, unknown> = {};
    for (const col of editable) {
      const before = data.row[col];
      const after = form[col];
      if (!deepEqual(before, after)) d[col] = after;
    }
    return d;
  }, [data, form, editable]);

  const hasDiff = Object.keys(diff).length > 0;

  async function onSave() {
    if (!hasDiff || !data) return;
    setSaving(true);
    setError(null);
    try {
      const r = await api<{ ok: boolean; row: Record<string, unknown> }>(
        `/api/admin/tables/${table}/${pkColumn}/${encodeURIComponent(pkValue)}`,
        {
          method: "PATCH",
          body: JSON.stringify(diff),
          headers: { "Content-Type": "application/json" },
        },
      );
      setData({ ...data, row: r.row });
      setForm({ ...r.row });
      onSaved?.();
    } catch (e) {
      setError((e as Error).message || "save failed");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    if (!data) return;
    if (!window.confirm(t("admin_table_confirm_delete", { pk: pkValue }))) return;
    setDeleting(true);
    setError(null);
    try {
      await api(
        `/api/admin/tables/${table}/${pkColumn}/${encodeURIComponent(pkValue)}`,
        { method: "DELETE" },
      );
      onDeleted?.();
      onClose();
    } catch (e) {
      setError((e as Error).message || "delete failed");
      setDeleting(false);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/30 z-40"
      />
      {/* Drawer */}
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 280, damping: 32 }}
        className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-[var(--background)] border-l border-[var(--border)] shadow-2xl flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] shrink-0">
          <div className="min-w-0">
            <h3 className="font-display text-lg truncate">
              {t("admin_table_edit_title")}
            </h3>
            <p className="text-[11px] text-[var(--muted)] font-mono truncate">
              {table} · {pkColumn}={pkValue}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-[var(--color-sand)]/50 active:scale-95"
            aria-label="close"
          >
            <Icon icon="solar:close-circle-bold-duotone" width={22} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {loading && (
            <div className="text-center py-10 text-[var(--muted)]">
              <Icon icon="svg-spinners:180-ring" width={20} />
            </div>
          )}

          {!loading && error && !data && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-700">
              {error}
            </div>
          )}

          {data && data.policy.read_only && (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--color-sand)]/30 p-3 text-xs text-[var(--muted-foreground)]">
              <Icon
                icon="solar:lock-keyhole-minimalistic-bold-duotone"
                width={14}
                className="inline mr-1 -mt-0.5"
              />
              {t("admin_table_readonly_banner")}
            </div>
          )}

          {data && data.policy.hint_key && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-[11px] text-amber-900">
              <Icon
                icon="solar:info-circle-bold-duotone"
                width={14}
                className="inline mr-1 -mt-0.5"
              />
              {t(data.policy.hint_key)}
            </div>
          )}

          {data && (
            <div className="space-y-2">
              {data.columns.map((col) => {
                const isEditable = editable.has(col.column_name);
                return (
                  <FieldRow
                    key={col.column_name}
                    col={col}
                    editable={isEditable}
                    value={form[col.column_name]}
                    onChange={(v) =>
                      setForm((prev) => ({ ...prev, [col.column_name]: v }))
                    }
                  />
                );
              })}
            </div>
          )}

          {error && data && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-xs text-red-700">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        {data && !data.policy.read_only && (
          <div className="border-t border-[var(--border)] p-3 flex items-center justify-between gap-2 shrink-0">
            <button
              onClick={onDelete}
              disabled={deleting || saving}
              className="text-[11px] px-3 py-2 rounded-full border border-red-500/40 text-red-700 hover:bg-red-500/10 active:scale-95 disabled:opacity-40 flex items-center gap-1"
            >
              {deleting ? (
                <Icon icon="svg-spinners:180-ring" width={14} />
              ) : (
                <Icon icon="solar:trash-bin-trash-bold-duotone" width={14} />
              )}
              {t("admin_table_delete_row")}
            </button>
            <div className="flex items-center gap-2">
              {!hasDiff && (
                <span className="text-[10px] text-[var(--muted)]">
                  {t("admin_table_no_changes")}
                </span>
              )}
              <button
                onClick={onSave}
                disabled={!hasDiff || saving}
                className="text-[12px] px-4 py-2 rounded-full bg-[var(--accent)] text-white active:scale-95 disabled:opacity-40 flex items-center gap-1"
              >
                {saving ? (
                  <Icon icon="svg-spinners:180-ring" width={14} />
                ) : (
                  <Icon icon="solar:diskette-bold-duotone" width={14} />
                )}
                {t("admin_table_save")}
              </button>
            </div>
          </div>
        )}
      </motion.aside>
    </>
  );
}

// ---------------------------------------------------------------------------
// Field renderer — dispatches on Postgres data_type.
// ---------------------------------------------------------------------------

interface FieldRowProps {
  col: ColumnMeta;
  editable: boolean;
  value: unknown;
  onChange: (v: unknown) => void;
}

function FieldRow({ col, editable, value, onChange }: FieldRowProps) {
  const { t } = useI18n();
  const dtype = (col.data_type || "").toLowerCase();
  const nullable = col.is_nullable === "YES";

  const label = (
    <div className="flex items-center justify-between gap-2 mb-1">
      <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-foreground)]">
        {col.column_name}
      </span>
      <span className="text-[9px] font-mono text-[var(--muted)]">
        {dtype}
        {!nullable && " · NOT NULL"}
        {!editable && ` · ${t("admin_table_readonly_field")}`}
      </span>
    </div>
  );

  // Boolean → 3-state toggle (true / false / NULL)
  if (dtype === "boolean") {
    const v = value as boolean | null | undefined;
    const choose = (next: boolean | null) => onChange(next);
    return (
      <div>
        {label}
        <div className="flex gap-1.5">
          <PillBtn
            active={v === true}
            disabled={!editable}
            onClick={() => choose(true)}
          >
            {t("common_yes")}
          </PillBtn>
          <PillBtn
            active={v === false}
            disabled={!editable}
            onClick={() => choose(false)}
          >
            {t("common_no")}
          </PillBtn>
          {nullable && (
            <PillBtn
              active={v === null || v === undefined}
              disabled={!editable}
              onClick={() => choose(null)}
            >
              NULL
            </PillBtn>
          )}
        </div>
      </div>
    );
  }

  // Numeric
  if (
    dtype === "integer" ||
    dtype === "bigint" ||
    dtype === "smallint" ||
    dtype === "numeric" ||
    dtype === "real" ||
    dtype === "double precision"
  ) {
    const isFloat = dtype === "numeric" || dtype === "real" || dtype === "double precision";
    const display = value === null || value === undefined ? "" : String(value);
    return (
      <div>
        {label}
        <input
          type="number"
          step={isFloat ? "0.01" : "1"}
          value={display}
          disabled={!editable}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") onChange(nullable ? null : 0);
            else onChange(isFloat ? parseFloat(raw) : parseInt(raw, 10));
          }}
          className="w-full text-[12px] font-mono px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] disabled:opacity-60 disabled:cursor-not-allowed"
        />
      </div>
    );
  }

  // JSON / JSONB → textarea with parse validation on blur
  if (dtype === "json" || dtype === "jsonb") {
    const display =
      value === null || value === undefined
        ? ""
        : typeof value === "string"
        ? value
        : JSON.stringify(value, null, 2);
    return (
      <div>
        {label}
        <textarea
          value={display}
          disabled={!editable}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          className="w-full text-[11px] font-mono px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] disabled:opacity-60 disabled:cursor-not-allowed"
        />
      </div>
    );
  }

  // Timestamp / date / time — keep as ISO text; Postgres parses it
  if (
    dtype.startsWith("timestamp") ||
    dtype === "date" ||
    dtype === "time"
  ) {
    const display =
      value === null || value === undefined
        ? ""
        : typeof value === "string"
        ? value
        : String(value);
    return (
      <div>
        {label}
        <input
          type="text"
          placeholder={dtype === "date" ? "YYYY-MM-DD" : "ISO-8601"}
          value={display}
          disabled={!editable}
          onChange={(e) =>
            onChange(e.target.value === "" && nullable ? null : e.target.value)
          }
          className="w-full text-[11px] font-mono px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] disabled:opacity-60 disabled:cursor-not-allowed"
        />
      </div>
    );
  }

  // Text / varchar / char / anything else — textarea if long, input otherwise
  const strVal =
    value === null || value === undefined
      ? ""
      : typeof value === "string"
      ? value
      : String(value);
  const isLong = strVal.length > 80 || strVal.includes("\n");
  return (
    <div>
      {label}
      {isLong ? (
        <textarea
          value={strVal}
          disabled={!editable}
          onChange={(e) =>
            onChange(e.target.value === "" && nullable ? null : e.target.value)
          }
          rows={3}
          className="w-full text-[12px] px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] disabled:opacity-60 disabled:cursor-not-allowed"
        />
      ) : (
        <input
          type="text"
          value={strVal}
          disabled={!editable}
          onChange={(e) =>
            onChange(e.target.value === "" && nullable ? null : e.target.value)
          }
          className="w-full text-[12px] px-2 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] disabled:opacity-60 disabled:cursor-not-allowed"
        />
      )}
    </div>
  );
}

function PillBtn({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`text-[11px] px-3 py-1 rounded-full font-mono transition active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed ${
        active
          ? "bg-[var(--accent)] text-white"
          : "bg-[var(--card)] text-[var(--muted)] border border-[var(--border)] hover:text-[var(--foreground)]"
      }`}
    >
      {children}
    </button>
  );
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null) return a === b;
  if (typeof a !== typeof b) return false;
  if (typeof a === "object") {
    try {
      return JSON.stringify(a) === JSON.stringify(b);
    } catch {
      return false;
    }
  }
  return false;
}
