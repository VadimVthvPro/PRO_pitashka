import Sidebar from "@/components/layout/Sidebar";
import BottomNav from "@/components/layout/BottomNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 pb-20 lg:pb-0">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-6 lg:py-8">
          {children}
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
