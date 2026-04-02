import AuthGuard from "@/components/layout/AuthGuard";
import GenerateForm from "@/components/reports/GenerateForm";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Client } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{ client?: string }>;
}

export default async function GeneratePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const supabase = await createServerSupabaseClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("name")
    .returns<Client[]>();

  return (
    <AuthGuard>
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-primary mb-6">レポート生成</h1>
        <GenerateForm
          clients={clients || []}
          initialClient={params.client}
        />
      </div>
    </AuthGuard>
  );
}
