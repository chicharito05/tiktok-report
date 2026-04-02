import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Profile } from "@/lib/types";
import Sidebar from "./Sidebar";
import Header from "./Header";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default async function AuthGuard({
  children,
  requireAdmin = false,
}: AuthGuardProps) {
  const supabase = await createServerSupabaseClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  // プロフィール取得
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single<Profile>();

  const isAdmin = profile?.role === "admin";

  if (requireAdmin && !isAdmin) {
    redirect("/posts");
  }

  return (
    <div className="flex">
      <Sidebar isAdmin={isAdmin} />
      <div className="flex-1 ml-60">
        <Header
          displayName={profile?.display_name || ""}
          email={user.email || ""}
        />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
