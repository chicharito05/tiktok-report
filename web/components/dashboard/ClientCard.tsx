"use client";

import Link from "next/link";
import { FileText, ExternalLink, Film } from "lucide-react";
import type { Client, Report } from "@/lib/types";

interface ClientCardProps {
  client: Client;
  latestReport: Report | null;
  postCount?: number;
}

export default function ClientCard({ client, latestReport, postCount }: ClientCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200/80 p-5 card-hover group">
      {/* ヘッダー */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-bold text-primary text-base">{client.name}</h3>
          {client.tiktok_username && (
            <p className="text-xs text-gray-400 mt-0.5">
              {client.tiktok_username}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          {client.notion_database_id && (
            <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-medium">
              Notion
            </span>
          )}
        </div>
      </div>

      {/* ステータス */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 flex items-center gap-1.5">
            <FileText size={14} />
            最新レポート
          </span>
          {latestReport ? (
            <span className="text-emerald-600 font-medium text-xs bg-emerald-50 px-2 py-0.5 rounded-full">
              {latestReport.operation_month || "-"}
            </span>
          ) : (
            <span className="text-gray-400 text-xs">未生成</span>
          )}
        </div>
        {typeof postCount === "number" && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 flex items-center gap-1.5">
              <Film size={14} />
              動画データ
            </span>
            <span className="text-gray-700 font-medium text-xs">
              {postCount}件
            </span>
          </div>
        )}
      </div>

      {/* アクション */}
      <div className="flex gap-2">
        <Link
          href={`/reports/generate?client=${encodeURIComponent(client.name)}`}
          className="flex-1 text-center gradient-accent text-white py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
        >
          レポート生成
        </Link>
        <Link
          href={`/posts?client=${encodeURIComponent(client.name)}`}
          className="px-3 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors flex items-center"
          title="動画データ管理"
        >
          <ExternalLink size={14} />
        </Link>
      </div>
    </div>
  );
}
