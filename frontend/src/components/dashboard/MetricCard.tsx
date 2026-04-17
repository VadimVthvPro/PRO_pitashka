"use client";

interface MetricCardProps {
  label: string;
  value: number;
  target: number;
  unit: string;
  color?: string;
}

export default function MetricCard({ label, value, target, unit, color = "var(--success)" }: MetricCardProps) {
  const percent = target > 0 ? Math.min(Math.round((value / target) * 100), 100) : 0;

  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-1)] hover:shadow-[var(--shadow-2)] hover:-translate-y-0.5 transition-all duration-200">
      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
        {label}
      </p>
      <p className="font-mono text-3xl font-bold text-[var(--foreground)] leading-none mb-1">
        {value.toLocaleString("ru-RU")}
      </p>
      <p className="text-xs text-[var(--muted)] mb-4">
        из {target.toLocaleString("ru-RU")} {unit}
      </p>
      <div className="h-1.5 bg-[var(--color-sand)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-600 ease-out"
          style={{ width: `${percent}%`, background: color }}
        />
      </div>
      <p className="text-xs font-mono mt-1.5" style={{ color }}>
        {percent}%
      </p>
    </div>
  );
}
