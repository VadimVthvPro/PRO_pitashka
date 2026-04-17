import Sidebar from "@/components/layout/Sidebar";
import BottomNav from "@/components/layout/BottomNav";
import { GrainOverlay } from "@/components/motion/GrainOverlay";
import { PageTransition } from "@/components/motion/PageTransition";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen relative">
      <GrainOverlay />
      <Sidebar />
      <main className="flex-1 pb-24 lg:pb-0 relative z-[2]">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-10 py-6 lg:py-10">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
