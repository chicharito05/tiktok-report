import AuthGuard from "@/components/layout/AuthGuard";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Client } from "@/lib/types";
import PostsManager from "./PostsManager";

export default async function PostsPage() {
  const supabase = await createServerSupabaseClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("name")
    .returns<Client[]>();

  return (
    <AuthGuard>
      <PostsManager clients={clients || []} />
    </AuthGuard>
  );
}
