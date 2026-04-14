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

  // signed URL取得
  let pdfUrl: string | null = null;
  let htmlUrl: string | null = null;
  if (report.file_path) {
    const isPdf = report.file_path.endsWith(".pdf");
    const pdfPath = isPdf
      ? report.file_path
      : report.file_path.replace(".html", ".pdf");
    const htmlPath = isPdf
      ? report.file_path.replace(".pdf", ".html")
      : report.file_path;

    const { data: pdfData } = await supabase.storage
      .from("reports")
      .createSignedUrl(pdfPath, 3600);
    pdfUrl = pdfData?.signedUrl || null;

    const { data: htmlData } = await supabase.storage
      .from("reports")
      .createSignedUrl(htmlPath, 3600);
    htmlUrl = htmlData?.signedUrl || null;
  }

  const clientName = report.clients?.name || "不明";
  const periodLabel = report.operation_month || "-";

  return (
    <AuthGuard>
      <ReportEditor
        reportId={report.id}
        clientName={clientName}
        periodLabel={periodLabel}
        htmlUrl={htmlUrl}
        pdfUrl={pdfUrl}
      />
    </AuthGuard>
  );
}
