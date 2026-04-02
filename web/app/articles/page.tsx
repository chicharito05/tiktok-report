import AuthGuard from "@/components/layout/AuthGuard";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Client } from "@/lib/types";
import ArticlesManager from "./ArticlesManager";

export default async function ArticlesPage() {
  const supabase = await createServerSupabaseClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("name")
    .returns<Client[]>();

  return (
    <AuthGuard>
      <ArticlesManager clients={clients || []} />
    </AuthGuard>
  );
}
