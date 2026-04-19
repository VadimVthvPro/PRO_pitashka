"use client";

import Link from "next/link";
import { Icon } from "@iconify/react";
import { motion } from "motion/react";
import { useState } from "react";
import MobileMenu from "./MobileMenu";

export default function MobileTopBar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <header
        data-mobile-topbar
        className="lg:hidden sticky top-0 z-40 bg-[var(--background)]/85 backdrop-blur-xl border-b border-[var(--border)]/60"
        style={{ paddingTop: "var(--safe-top)" }}
      >
        <div className="flex items-center justify-between px-4 h-14">
          <Link href="/dashboard" className="flex items-baseline gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[var(--muted)]">
              PRO
            </span>
            <span
              className="text-xl font-bold leading-none"
              style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.035em" }}
            >
              pitashka<span className="text-[var(--accent)]">.</span>
            </span>
          </Link>

          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={() => setOpen(true)}
            className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-[var(--color-sand)] transition"
            aria-label="Открыть меню"
          >
            <Icon
              icon="solar:hamburger-menu-bold-duotone"
              width={24}
              className="text-[var(--foreground)]"
            />
          </motion.button>
        </div>
      </header>
      <MobileMenu open={open} onClose={() => setOpen(false)} />
    </>
  );
}
