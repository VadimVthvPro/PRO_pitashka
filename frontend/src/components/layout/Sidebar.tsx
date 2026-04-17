"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Apple, Dumbbell,
  CalendarDays, Bot, ClipboardList, CookingPot,
  Settings, ShieldCheck,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, labelKey: "nav_dashboard" },
  { href: "/food", icon: Apple, labelKey: "nav_food" },
  { href: "/workouts", icon: Dumbbell, labelKey: "nav_workouts" },
  { href: "/summary", icon: CalendarDays, labelKey: "nav_summary" },
  { href: "/ai-chat", icon: Bot, labelKey: "nav_ai" },
  { href: "/plans", icon: ClipboardList, labelKey: "nav_plans" },
  { href: "/recipes", icon: CookingPot, labelKey: "nav_recipes" },
  { href: "/settings", icon: Settings, labelKey: "nav_settings" },
  { href: "/admin", icon: ShieldCheck, labelKey: "nav_admin" },
];

const labels: Record<string, string> = {
  nav_dashboard: "Главная",
  nav_food: "Питание",
  nav_workouts: "Тренировки",
  nav_summary: "Сводка",
  nav_ai: "AI-Ассистент",
  nav_plans: "Планы",
  nav_recipes: "Рецепты",
  nav_settings: "Настройки",
  nav_admin: "Админ",
};

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-[var(--sidebar-width)] h-screen sticky top-0 bg-[var(--background)] border-r border-[var(--border)] px-4 py-6">
      <Link href="/dashboard" className="flex items-center gap-2 mb-8 px-2">
        <span className="font-display text-xl font-bold text-[var(--foreground)]">
          PROpitashka
        </span>
      </Link>

      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius)] text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-[var(--color-sand)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:bg-[var(--color-sand)] hover:text-[var(--foreground)]"
              }`}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{labels[item.labelKey]}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
