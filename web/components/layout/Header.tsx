"use client";

import { useRouter } from "next/navigation";
import { LogOut, User } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface HeaderProps {
  displayName: string;
  email: string;
}

export default function Header({ displayName, email }: HeaderProps) {
  const router = useRouter();
  const supabase = createClient();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  };

  return (
    <header className="h-14 bg-white/80 backdrop-blur-md border-b border-gray-200/60 flex items-center justify-end px-6 sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg">
          <div className="w-7 h-7 bg-primary/10 rounded-full flex items-center justify-center">
            <User size={14} className="text-primary" />
          </div>
          <span className="text-sm font-medium text-gray-700">
            {displayName || email}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut size={15} />
          <span className="text-xs">ログアウト</span>
        </button>
      </div>
    </header>
  );
}
