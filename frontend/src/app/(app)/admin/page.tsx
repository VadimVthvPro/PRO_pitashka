"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { ChevronLeft, ChevronRight, Trash2, Database } from "lucide-react";

interface TableRow {
  [key: string]: unknown;
}

interface TableData {
  columns: string[];
  rows: TableRow[];
  total: number;
  page: number;
  per_page: number;
}

export default function AdminPage() {
  const [tables, setTables] = useState<string[]>([]);
  const [activeTable, setActiveTable] = useState("");
  const [data, setData] = useState<TableData | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ tables: string[] }>("/api/admin/tables")
      .then((res) => setTables(res.tables))
      .catch((e) => setError(e.message));
  }, []);

  const loadTable = useCallback(async (table: string, pg: number) => {
    setLoading(true);
    setError("");
    try {
      const res = await api<TableData>(`/api/admin/tables/${table}?page=${pg}&per_page=20`);
      setData(res);
      setActiveTable(table);
      setPage(pg);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  async function deleteRow(pkCol: string, pkValue: unknown) {
    if (!confirm("Удалить запись?")) return;
    try {
      await api(`/api/admin/tables/${activeTable}/${pkCol}/${pkValue}`, { method: "DELETE" });
      loadTable(activeTable, page);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка удаления");
    }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="space-y-6">
      <h1 className="page-title flex items-center gap-3">
        <Database size={32} className="text-[var(--accent)]" />
        Админ-панель
      </h1>

      {error && (
        <div className="px-4 py-3 bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 rounded-[var(--radius)] text-sm text-[var(--destructive)]">
          {error}
        </div>
      )}

      {/* Tables list */}
      <div className="flex flex-wrap gap-2">
        {tables.map((t) => (
          <button
            key={t}
            onClick={() => loadTable(t, 1)}
            className={`px-3 py-1.5 text-sm rounded-full font-mono transition-all ${
              activeTable === t
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--color-sand)] text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Data table */}
      {data && (
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] shadow-[var(--shadow-1)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[var(--color-sand)]/50">
                  {data.columns.map((col) => (
                    <th key={col} className="text-left px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)] whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={data.columns.length + 1} className="px-4 py-8 text-center text-[var(--muted)]">Загрузка...</td></tr>
                ) : data.rows.length === 0 ? (
                  <tr><td colSpan={data.columns.length + 1} className="px-4 py-8 text-center text-[var(--muted)]">Нет данных</td></tr>
                ) : (
                  data.rows.map((row, i) => (
                    <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--color-sand)]/30">
                      {data.columns.map((col) => (
                        <td key={col} className="px-4 py-2.5 font-mono text-xs whitespace-nowrap max-w-[200px] truncate">
                          {String(row[col] ?? "")}
                        </td>
                      ))}
                      <td className="px-2">
                        <button
                          onClick={() => deleteRow(data.columns[0], row[data.columns[0]])}
                          className="p-1.5 rounded text-[var(--destructive)] hover:bg-[var(--destructive)]/10 transition-colors"
                          title="Удалить"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border)]">
              <span className="text-xs text-[var(--muted)]">
                {data.total} записей — страница {page} из {totalPages}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => loadTable(activeTable, page - 1)}
                  disabled={page <= 1}
                  className="p-1.5 rounded border border-[var(--border)] text-[var(--muted)] disabled:opacity-30 hover:bg-[var(--color-sand)] transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => loadTable(activeTable, page + 1)}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded border border-[var(--border)] text-[var(--muted)] disabled:opacity-30 hover:bg-[var(--color-sand)] transition-colors"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
