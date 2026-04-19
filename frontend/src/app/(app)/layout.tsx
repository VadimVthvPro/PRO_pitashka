import Sidebar from "@/components/layout/Sidebar";
import BottomNav from "@/components/layout/BottomNav";
import MobileTopBar from "@/components/layout/MobileTopBar";
import { GrainOverlay } from "@/components/motion/GrainOverlay";
import { PageTransition } from "@/components/motion/PageTransition";
import { BadgeToast } from "@/components/streak/BadgeToast";
import { SettingsHydrator } from "@/components/settings/SettingsHydrator";

// Authenticated layout MUST be rendered fresh on every request so the
// middleware-applied `Cache-Control: no-store` header takes effect and we
// never serve a previously cached prerendered shell to a logged-out user.
export const dynamic = "force-dynamic";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen relative">
      <GrainOverlay />
      <BadgeToast />
      <SettingsHydrator />
      <Sidebar />
      <main className="flex-1 pb-24 lg:pb-0 relative z-[2]">
        <MobileTopBar />
        <div className="max-w-[1200px] mx-auto px-4 lg:px-10 py-5 lg:py-10">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
