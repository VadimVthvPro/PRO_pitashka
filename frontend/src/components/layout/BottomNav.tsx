"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Apple, Dumbbell, CalendarDays, Bot } from "lucide-react";

const items = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Главная" },
  { href: "/food", icon: Apple, label: "Еда" },
  { href: "/workouts", icon: Dumbbell, label: "Трен." },
  { href: "/summary", icon: CalendarDays, label: "Сводка" },
  { href: "/ai-chat", icon: Bot, label: "AI" },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-[var(--card)] border-t border-[var(--border)] shadow-[var(--shadow-3)]">
      <div className="flex justify-around items-center h-16 px-2">
        {items.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 min-w-[44px] min-h-[44px] justify-center rounded-[var(--radius)] transition-colors ${
                isActive ? "text-[var(--accent)]" : "text-[var(--muted-foreground)]"
              }`}
            >
              <Icon size={20} strokeWidth={1.8} />
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
