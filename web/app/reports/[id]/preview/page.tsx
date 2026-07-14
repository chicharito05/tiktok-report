import { notFound } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import ReportEditor from "./ReportEditor";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Report } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ReportPreviewPage({ params }: PageProps) {
  const { id } = await params;
  const supabase = await createServerSupabaseClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*, clients(name), profiles(display_name, email)")
    .eq("id", id)
    .single<Report>();

  if (!report) {
    notFound();
  }

  // signed URL取得（PPTX）
  let pptxUrl: string | null = null;
  if (report.file_path) {
    const pptxPath = report.file_path.endsWith(".pptx")
      ? report.file_path
      : report.file_path.replace(/\.(html|pdf)$/, ".pptx");

    const { data: pptxData } = await supabase.storage
      .from("reports")
      .createSignedUrl(pptxPath, 3600);
    pptxUrl = pptxData?.signedUrl || null;
  }

  const clientName = report.clients?.name || "不明";
  const periodLabel = report.operation_month || "-";

  return (
    <AuthGuard>
      <ReportEditor
        reportId={report.id}
        clientName={clientName}
        periodLabel={periodLabel}
        pptxUrl={pptxUrl}
      />
    </AuthGuard>
  );
}
