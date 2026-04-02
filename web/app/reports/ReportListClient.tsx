"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, ChevronLeft, ChevronRight } from "lucide-react";
import ReportCard from "@/components/reports/ReportCard";
import EmptyState from "@/components/ui/EmptyState";
import type { Report } from "@/lib/types";
import { createClient } from "@/lib/supabase/client";
import { useToast } from "@/components/ui/Toast";

interface ReportListClientProps {
  reports: Report[];
  isAdmin: boolean;
}

export default function ReportListClient({
  reports: initialReports,
  isAdmin,
}: ReportListClientProps) {
  const [reports, setReports] = useState(initialReports);
  const [page, setPage] = useState(0);
  const router = useRouter();
  const supabase = createClient();
  const { showToast } = useToast();
  const perPage = 10;

  const paged = reports.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(reports.length / perPage);

  const handleDelete = async (id: string) => {
    if (!confirm("このレポートを削除しますか？")) return;

    const { error } = await supabase.from("reports").delete().eq("id", id);
    if (!error) {
      setReports((prev) => prev.filter((r) => r.id !== id));
      showToast("success", "レポートを削除しました");
    } else {
      showToast("error", "削除に失敗しました");
    }
  };

  if (reports.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200/80">
        <EmptyState
          icon={FileText}
          title="レポートがありません"
          description="レポート生成ページからレポートを作成できます"
          action={{
            label: "レポート生成へ",
            onClick: () => router.push("/reports/generate"),
          }}
        />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50/80 border-b border-gray-100">
              <th className="text-left py-3 px-5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                クライアント
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                対象期間
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                生成日
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                生成者
              </th>
              <th className="py-3 px-4 w-32"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {paged.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                isAdmin={isAdmin}
                onDelete={handleDelete}
              />
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 p-4 border-t border-gray-100">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="p-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-gray-500 tabular-nums">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="p-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
