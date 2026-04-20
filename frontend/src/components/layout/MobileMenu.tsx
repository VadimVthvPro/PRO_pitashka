"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@iconify/react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { useI18n } from "@/lib/i18n";

interface NavItem {
  href: string;
  icon: string;
  /** i18n key resolved at render time */
  labelKey: string;
}

const groups: { titleKey: string; items: NavItem[] }[] = [
  {
    titleKey: "menu_section_daily",
    items: [
      { href: "/dashboard", icon: "solar:home-2-bold-duotone", labelKey: "nav_dashboard" },
      { href: "/food", icon: "solar:plate-bold-duotone", labelKey: "nav_food" },
      { href: "/workouts", icon: "solar:dumbbell-large-bold-duotone", labelKey: "nav_workouts" },
    ],
  },
  {
    titleKey: "menu_section_progress",
    items: [
      { href: "/summary", icon: "solar:graph-new-up-bold-duotone", labelKey: "nav_summary" },
      { href: "/weight", icon: "solar:scale-bold-duotone", labelKey: "nav_weight" },
      { href: "/digest", icon: "solar:letter-opened-bold-duotone", labelKey: "nav_digest" },
      { href: "/achievements", icon: "solar:medal-ribbon-star-bold-duotone", labelKey: "nav_achievements" },
    ],
  },
  {
    titleKey: "menu_section_assistant",
    items: [
      { href: "/ai-chat", icon: "solar:magic-stick-3-bold-duotone", labelKey: "nav_ai" },
      { href: "/plans", icon: "solar:clipboard-check-bold-duotone", labelKey: "nav_plans" },
      { href: "/social", icon: "solar:users-group-rounded-bold-duotone", labelKey: "nav_social" },
    ],
  },
  {
    titleKey: "menu_section_account",
    items: [
      { href: "/settings", icon: "solar:settings-bold-duotone", labelKey: "nav_settings" },
      { href: "/admin", icon: "solar:shield-user-bold-duotone", labelKey: "nav_admin" },
    ],
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function MobileMenu({ open, onClose }: Props) {
  const pathname = usePathname();
  const { t } = useI18n();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="lg:hidden fixed inset-0 z-[60] bg-black/40 backdrop-blur-[2px]"
            aria-hidden
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
            className="lg:hidden fixed top-0 right-0 bottom-0 z-[70] w-[88vw] max-w-[360px] bg-[var(--card)] shadow-[var(--shadow-3)] border-l border-[var(--border)] flex flex-col"
            style={{ paddingTop: "var(--safe-top)" }}
            role="dialog"
            aria-modal="true"
            aria-label={t("layout_aria_main_menu")}
          >
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <div>
                <span className="block text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
                  PRO
                </span>
                <span
                  className="block text-2xl font-bold leading-[0.9]"
                  style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.035em" }}
                >
                  pitashka<span className="text-[var(--accent)]">.</span>
                </span>
              </div>
              <button
                onClick={onClose}
                className="w-11 h-11 rounded-full flex items-center justify-center hover:bg-[var(--color-sand)] transition touch-manipulation"
                aria-label={t("layout_aria_close_menu")}
              >
                <Icon icon="solar:close-circle-bold-duotone" width={26} className="text-[var(--muted)]" />
              </button>
            </div>

            <div
              className="flex-1 overflow-y-auto px-3"
              style={{ paddingBottom: "max(1.5rem, var(--safe-bottom))" }}
            >
              {groups.map((group) => (
                <div key={group.titleKey} className="mb-5">
                  <p
                    className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]"
                  >
                    {t(group.titleKey)}
                  </p>
                  <div className="flex flex-col gap-1">
                    {group.items.map((item) => {
                      const isActive =
                        pathname === item.href || pathname.startsWith(item.href + "/");
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={onClose}
                          className={`flex items-center gap-3 px-3 py-3 rounded-[var(--radius)] text-[15px] font-medium transition-colors ${
                            isActive
                              ? "bg-[var(--color-sand)] text-[var(--accent)]"
                              : "text-[var(--foreground)] hover:bg-[var(--color-sand)]/60"
                          }`}
                        >
                          <Icon
                            icon={item.icon}
                            width={22}
                            className={isActive ? "text-[var(--accent)]" : "text-[var(--muted)]"}
                          />
                          <span className="flex-1">{t(item.labelKey)}</span>
                          {isActive && (
                            <Icon
                              icon="solar:arrow-right-linear"
                              width={16}
                              className="text-[var(--accent)]"
                            />
                          )}
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div className="px-5 py-4 border-t border-dashed border-[var(--border)]">
              <p
                className="text-xs text-[var(--muted-foreground)] leading-snug"
                style={{ fontFamily: "var(--font-arkhip-stack)", fontSize: "13px" }}
              >
                {t("menu_quote")}
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
