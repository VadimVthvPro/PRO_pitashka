"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { StreakFlame } from "@/components/streak/StreakFlame";
import { useI18n } from "@/lib/i18n";
import { BrandWordmark } from "@/components/brand/BrandWordmark";

interface NavItem {
  href: string;
  icon: string;
  /** i18n key resolved at render time */
  labelKey: string;
}

const navItems: NavItem[] = [
  { href: "/dashboard", icon: "solar:home-2-bold-duotone", labelKey: "nav_dashboard" },
  { href: "/food", icon: "solar:plate-bold-duotone", labelKey: "nav_food" },
  { href: "/workouts", icon: "solar:dumbbell-large-bold-duotone", labelKey: "nav_workouts" },
  { href: "/summary", icon: "solar:graph-new-up-bold-duotone", labelKey: "nav_summary" },
  { href: "/weight", icon: "solar:scale-bold-duotone", labelKey: "nav_weight" },
  { href: "/digest", icon: "solar:letter-opened-bold-duotone", labelKey: "nav_digest" },
  { href: "/achievements", icon: "solar:medal-ribbon-star-bold-duotone", labelKey: "nav_achievements" },
  { href: "/ai-chat", icon: "solar:magic-stick-3-bold-duotone", labelKey: "nav_ai" },
  { href: "/plans", icon: "solar:clipboard-check-bold-duotone", labelKey: "nav_plans" },
  { href: "/social", icon: "solar:users-group-rounded-bold-duotone", labelKey: "nav_social" },
  { href: "/settings", icon: "solar:settings-bold-duotone", labelKey: "nav_settings" },
  { href: "/admin", icon: "solar:shield-user-bold-duotone", labelKey: "nav_admin" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <aside className="hidden lg:flex flex-col w-[var(--sidebar-width)] h-screen sticky top-0 bg-transparent border-r border-[var(--border)] px-4 py-6 backdrop-blur-[2px]">
      <Link
        href="/dashboard"
        className="block mb-10 px-2 group text-[var(--foreground)]"
      >
        <BrandWordmark
          size="lg"
          orientation="stacked"
          className="transition-transform group-hover:-rotate-[1deg] origin-left"
        />
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
                <span>{t(item.labelKey)}</span>
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
          {t("menu_quote")}
        </p>
      </div>
    </aside>
  );
}
