"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileText,
  FilePlus,
  Users,
  Film,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isAdmin: boolean;
}

const mainItems = [
  { href: "/posts", label: "動画データ管理", icon: Film },
  { href: "/articles", label: "原稿一覧", icon: BookOpen },
];

const reportItems = [
  { href: "/reports/generate", label: "レポート生成", icon: FilePlus },
  { href: "/reports", label: "レポート一覧", icon: FileText },
];

const adminItems = [
  { href: "/clients", label: "クライアント管理", icon: Users },
];

function NavSection({
  label,
  items,
  pathname,
}: {
  label: string;
  items: { href: string; label: string; icon: typeof Film }[];
  pathname: string;
}) {
  return (
    <div className="mb-2">
      <p className="px-6 py-2 text-[10px] font-semibold uppercase tracking-wider text-white/30">
        {label}
      </p>
      {items.map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/posts" && pathname.startsWith(item.href));
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-6 py-2.5 text-sm transition-all duration-150 mx-2 rounded-lg",
              isActive
                ? "bg-white/15 text-white font-medium shadow-sm"
                : "text-white/60 hover:bg-white/8 hover:text-white/90"
            )}
          >
            <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

export default function Sidebar({ isAdmin }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="w-60 gradient-sidebar min-h-screen flex flex-col fixed left-0 top-0 z-30">
      {/* ロゴ */}
      <div className="p-6 pb-4">
        <Link href="/posts" className="block">
          <span className="text-xl font-bold text-white tracking-tight">
            LEAD <span className="text-accent">ONE</span>
          </span>
          <p className="text-[11px] text-white/40 mt-0.5">TikTok Report Tool</p>
        </Link>
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1 py-2 space-y-1">
        <NavSection label="メイン" items={mainItems} pathname={pathname} />
        <NavSection label="レポート" items={reportItems} pathname={pathname} />
        {isAdmin && (
          <NavSection label="管理" items={adminItems} pathname={pathname} />
        )}
      </nav>

      {/* フッター */}
      <div className="p-4 border-t border-white/5">
        <p className="text-[10px] text-white/20 text-center">v2.0</p>
      </div>
    </aside>
  );
}
