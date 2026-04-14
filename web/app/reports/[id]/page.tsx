import { notFound } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import ReportPreview from "@/components/reports/ReportPreview";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import type { Report } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { PenLine } from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ReportDetailPage({ params }: PageProps) {
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
    const pdfPath = isPdf ? report.file_path : report.file_path.replace(".html", ".pdf");
    const htmlPath = isPdf ? report.file_path.replace(".pdf", ".html") : report.file_path;

    const { data: pdfData } = await supabase.storage
      .from("reports")
      .createSignedUrl(pdfPath, 3600);
    pdfUrl = pdfData?.signedUrl || null;

    const { data: htmlData } = await supabase.storage
      .from("reports")
      .createSignedUrl(htmlPath, 3600);
    htmlUrl = htmlData?.signedUrl || null;
  }

  return (
    <AuthGuard>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-primary">
              {report.clients?.name} - {report.operation_month || "-"}
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              生成日: {formatDate(report.generated_at)} / 生成者:{" "}
              {report.profiles?.display_name ||
                report.profiles?.email ||
                "-"}
            </p>
          </div>
          <Link
            href={`/reports/${report.id}/preview`}
            className="flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors"
          >
            <PenLine size={15} />
            確認・編集
          </Link>
        </div>

        <ReportPreview
          pdfUrl={pdfUrl}
          htmlUrl={htmlUrl}
          reportId={report.id}
        />
      </div>
    </AuthGuard>
  );
}
