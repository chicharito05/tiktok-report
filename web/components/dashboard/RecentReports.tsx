import Link from "next/link";
import { FileText, ArrowRight, Clock } from "lucide-react";
import type { Report } from "@/lib/types";
import { formatDate, formatDateRange } from "@/lib/utils";

interface RecentReportsProps {
  reports: Report[];
}

export default function RecentReports({ reports }: RecentReportsProps) {
  if (reports.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200/80 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={18} className="text-gray-400" />
          <h2 className="text-base font-bold text-primary">最近のレポート</h2>
        </div>
        <div className="text-center py-8">
          <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
            <FileText size={24} className="text-gray-300" />
          </div>
          <p className="text-sm text-gray-400">レポートがまだありません</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200/80 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock size={18} className="text-gray-400" />
          <h2 className="text-base font-bold text-primary">最近のレポート</h2>
        </div>
        <Link
          href="/reports"
          className="text-xs text-gray-400 hover:text-accent transition-colors flex items-center gap-1"
        >
          すべて表示
          <ArrowRight size={12} />
        </Link>
      </div>

      <div className="space-y-1">
        {reports.map((report) => (
          <Link
            key={report.id}
            href={`/reports/${report.id}`}
            className="flex items-center gap-4 px-3 py-3 -mx-1 rounded-lg hover:bg-gray-50 transition-colors group"
          >
            <div className="w-9 h-9 bg-accent/8 rounded-lg flex items-center justify-center shrink-0">
              <FileText size={16} className="text-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">
                {report.clients?.name || "不明"}
              </p>
              <p className="text-xs text-gray-400">
                {formatDateRange(report.start_date, report.end_date)}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs text-gray-400">
                {formatDate(report.generated_at)}
              </p>
              <p className="text-[11px] text-gray-300">
                {report.profiles?.display_name || report.profiles?.email || ""}
              </p>
            </div>
            <ArrowRight
              size={14}
              className="text-gray-300 group-hover:text-accent transition-colors shrink-0"
            />
          </Link>
        ))}
      </div>
    </div>
  );
}
