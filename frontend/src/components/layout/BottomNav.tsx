"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { useState } from "react";
import MobileMenu from "./MobileMenu";
import { useI18n } from "@/lib/i18n";

const items = [
  { href: "/dashboard", icon: "solar:home-2-bold-duotone", labelKey: "nav_dashboard" },
  { href: "/food", icon: "solar:plate-bold-duotone", labelKey: "nav_food" },
  { href: "/workouts", icon: "solar:dumbbell-large-bold-duotone", labelKey: "nav_workouts" },
  { href: "/ai-chat", icon: "solar:magic-stick-3-bold-duotone", labelKey: "nav_ai" },
];

export default function BottomNav() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { t } = useI18n();

  return (
    <>
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-[var(--card)]/95 backdrop-blur-xl border-t border-[var(--border)] shadow-[var(--shadow-3)] pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around items-center h-16 px-2">
          {items.map((item) => {
            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className="relative flex flex-col items-center gap-0.5 min-w-[56px] min-h-[48px] justify-center rounded-[var(--radius)]"
              >
                {isActive && (
                  <motion.span
                    layoutId="bottomnav-active-pill"
                    className="absolute inset-x-2 inset-y-1 bg-[var(--color-sand)] rounded-[var(--radius)] -z-10"
                    transition={{ type: "spring", stiffness: 350, damping: 28 }}
                  />
                )}
                <motion.div
                  animate={{ scale: isActive ? 1.1 : 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 22 }}
                >
                  <Icon
                    icon={item.icon}
                    width={22}
                    height={22}
                    className={
                      isActive
                        ? "text-[var(--accent)]"
                        : "text-[var(--muted-foreground)]"
                    }
                  />
                </motion.div>
                <span
                  className={`text-[10px] font-medium ${
                    isActive
                      ? "text-[var(--accent)]"
                      : "text-[var(--muted-foreground)]"
                  }`}
                >
                  {t(item.labelKey)}
                </span>
              </Link>
            );
          })}

          <button
            onClick={() => setMenuOpen(true)}
            className="relative flex flex-col items-center gap-0.5 min-w-[56px] min-h-[48px] justify-center rounded-[var(--radius)]"
            aria-label="Открыть меню"
          >
            <motion.div whileTap={{ scale: 0.92 }}>
              <Icon
                icon="solar:hamburger-menu-bold-duotone"
                width={22}
                height={22}
                className="text-[var(--muted-foreground)]"
              />
            </motion.div>
            <span className="text-[10px] font-medium text-[var(--muted-foreground)]">
              {t("nav_more")}
            </span>
          </button>
        </div>
      </nav>

      <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </>
  );
}
