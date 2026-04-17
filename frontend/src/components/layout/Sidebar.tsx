"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { StreakFlame } from "@/components/streak/StreakFlame";

interface NavItem {
  href: string;
  icon: string;
  label: string;
}

const navItems: NavItem[] = [
  { href: "/dashboard", icon: "solar:home-2-bold-duotone", label: "Главная" },
  { href: "/food", icon: "solar:plate-bold-duotone", label: "Питание" },
  { href: "/workouts", icon: "solar:dumbbell-large-bold-duotone", label: "Тренировки" },
  { href: "/summary", icon: "solar:graph-new-up-bold-duotone", label: "Прогресс" },
  { href: "/weight", icon: "solar:scale-bold-duotone", label: "Вес" },
  { href: "/digest", icon: "solar:letter-opened-bold-duotone", label: "Дайджест" },
  { href: "/achievements", icon: "solar:medal-ribbon-star-bold-duotone", label: "Достижения" },
  { href: "/ai-chat", icon: "solar:magic-stick-3-bold-duotone", label: "AI-Ассистент" },
  { href: "/plans", icon: "solar:clipboard-check-bold-duotone", label: "Планы" },
  { href: "/recipes", icon: "solar:chef-hat-bold-duotone", label: "Рецепты" },
  { href: "/settings", icon: "solar:settings-bold-duotone", label: "Настройки" },
  { href: "/admin", icon: "solar:shield-user-bold-duotone", label: "Админ" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-[var(--sidebar-width)] h-screen sticky top-0 bg-transparent border-r border-[var(--border)] px-4 py-6 backdrop-blur-[2px]">
      <Link
        href="/dashboard"
        className="block mb-10 px-2 group"
      >
        <span className="block text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
          PRO
        </span>
        <span
          className="block text-[2.1rem] font-bold text-[var(--foreground)] leading-[0.9] transition-transform group-hover:-rotate-[1deg] origin-left"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.035em",
          }}
        >
          pitashka
          <span className="text-[var(--accent)]">.</span>
        </span>
      </Link>

      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative group"
            >
              <motion.div
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                className={`relative flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius)] text-sm font-medium transition-colors duration-200 ${
                  isActive
                    ? "text-[var(--accent)]"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-pill"
                    className="absolute inset-0 bg-[var(--color-sand)] rounded-[var(--radius)] -z-10"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                <Icon
                  icon={item.icon}
                  width={20}
                  height={20}
                  className={isActive ? "text-[var(--accent)]" : ""}
                />
                <span>{item.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 pt-4 border-t border-dashed border-[var(--border)]">
        <StreakFlame />
        <p
          className="mt-3 px-3 text-xs text-[var(--muted-foreground)] leading-snug"
          style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "13px" }}
        >
          «Лучшая диета та,
          <br />
          которую ты не забросил»
        </p>
      </div>
    </aside>
  );
}
