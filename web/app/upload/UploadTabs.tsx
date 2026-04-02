"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import CsvUploader from "@/components/upload/CsvUploader";
import ScreenshotUploader from "@/components/upload/ScreenshotUploader";
import type { Client } from "@/lib/types";

interface UploadTabsProps {
  clients: Client[];
}

type Tab = "overview" | "posts" | "screenshot";

export default function UploadTabs({ clients }: UploadTabsProps) {
  const [tab, setTab] = useState<Tab>("overview");

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "概要データ（CSV）" },
    { key: "posts", label: "動画データ（CSV）" },
    { key: "screenshot", label: "スクリーンショット" },
  ];

  return (
    <div>
      <div className="flex border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {tab === "overview" && (
          <>
            <p className="text-xs text-gray-500 mb-4">
              TikTok Studioの概要画面からエクスポートしたCSV（Date, Video Views, Profile Views, Likes, Comments, Shares）
            </p>
            <CsvUploader clients={clients} csvType="overview" />
          </>
        )}
        {tab === "posts" && (
          <>
            <p className="text-xs text-gray-500 mb-4">
              動画毎のデータCSV。ヘッダー例: タイトル, 投稿日, 再生回数, いいね数, コメント数, シェア数, 視聴完了率, 2秒視聴率
            </p>
            <CsvUploader clients={clients} csvType="posts" />
          </>
        )}
        {tab === "screenshot" && (
          <ScreenshotUploader clients={clients} />
        )}
      </div>
    </div>
  );
}
