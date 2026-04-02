import AuthGuard from "@/components/layout/AuthGuard";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Report, Profile } from "@/lib/types";
import ReportListClient from "./ReportListClient";

export default async function ReportsPage() {
  const supabase = await createServerSupabaseClient();

  const { data: reports } = await supabase
    .from("reports")
    .select("*, clients(name), profiles(display_name, email)")
    .order("generated_at", { ascending: false })
    .returns<Report[]>();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  let isAdmin = false;
  if (user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single<Pick<Profile, "role">>();
    isAdmin = profile?.role === "admin";
  }

  return (
    <AuthGuard>
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-primary mb-6">レポート一覧</h1>
        <ReportListClient reports={reports || []} isAdmin={isAdmin} />
      </div>
    </AuthGuard>
  );
}
