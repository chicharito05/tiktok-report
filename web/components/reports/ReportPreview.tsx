"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Download, Presentation } from "lucide-react";

interface ReportPreviewProps {
  pptxUrl: string | null;
  reportId: string;
}

export default function ReportPreview({
  pptxUrl,
}: ReportPreviewProps) {
  const router = useRouter();

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft size={16} />
          戻る
        </button>

        {pptxUrl && (
          <a
            href={pptxUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 text-sm bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            <Presentation size={16} />
            PPTXダウンロード
          </a>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {pptxUrl ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Presentation size={48} className="text-gray-300 mb-4" />
            <p className="text-sm font-medium">レポートが生成されました</p>
            <p className="text-xs text-gray-400 mt-1">上のボタンからPPTXをダウンロードしてください</p>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            ファイルがStorageにアップロードされていない可能性があります。
          </div>
        )}
      </div>
    </div>
  );
}
