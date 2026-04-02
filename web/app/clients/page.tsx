import AuthGuard from "@/components/layout/AuthGuard";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Client } from "@/lib/types";
import ClientsManager from "./ClientsManager";

export default async function ClientsPage() {
  const supabase = await createServerSupabaseClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("name")
    .returns<Client[]>();

  return (
    <AuthGuard requireAdmin>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-primary mb-6">
          クライアント管理
        </h1>
        <ClientsManager initialClients={clients || []} />
      </div>
    </AuthGuard>
  );
}
