"use client";

import Link from "next/link";
import { Eye, Download, Trash2 } from "lucide-react";
import type { Report } from "@/lib/types";
import { formatDate, formatDateRange } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";

interface ReportCardProps {
  report: Report;
  isAdmin: boolean;
  onDelete?: (id: string) => void;
}

export default function ReportCard({
  report,
  isAdmin,
  onDelete,
}: ReportCardProps) {
  const supabase = createClient();

  const handleDownload = async () => {
    if (!report.file_path) return;
    const { data } = await supabase.storage
      .from("reports")
      .createSignedUrl(report.file_path, 60);
    if (data?.signedUrl) {
      window.open(data.signedUrl, "_blank");
    }
  };

  return (
    <tr className="hover:bg-gray-50/60 transition-colors">
      <td className="py-3.5 px-5">
        <span className="font-medium text-gray-800">
          {report.clients?.name || "不明"}
        </span>
      </td>
      <td className="py-3.5 px-4">
        <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-lg">
          {formatDateRange(report.start_date, report.end_date)}
        </span>
      </td>
      <td className="py-3.5 px-4 text-gray-400 text-xs">
        {formatDate(report.generated_at)}
      </td>
      <td className="py-3.5 px-4 text-gray-400 text-xs">
        {report.profiles?.display_name || report.profiles?.email || "-"}
      </td>
      <td className="py-3.5 px-4">
        <div className="flex items-center gap-0.5">
          <Link
            href={`/reports/${report.id}`}
            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors rounded-lg"
            title="プレビュー"
          >
            <Eye size={15} />
          </Link>
          {report.file_path && (
            <button
              onClick={handleDownload}
              className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors rounded-lg"
              title="PDFダウンロード"
            >
              <Download size={15} />
            </button>
          )}
          {isAdmin && onDelete && (
            <button
              onClick={() => onDelete(report.id)}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors rounded-lg"
              title="削除"
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
