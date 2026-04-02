import AuthGuard from "@/components/layout/AuthGuard";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Client } from "@/lib/types";
import UploadTabs from "./UploadTabs";

export default async function UploadPage() {
  const supabase = await createServerSupabaseClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("name")
    .returns<Client[]>();

  return (
    <AuthGuard>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-primary mb-6">データ取込</h1>
        <UploadTabs clients={clients || []} />
      </div>
    </AuthGuard>
  );
}
