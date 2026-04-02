"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Download, FileText } from "lucide-react";

interface ReportPreviewProps {
  pdfUrl: string | null;
  htmlUrl: string | null;
  reportId: string;
}

export default function ReportPreview({
  pdfUrl,
  htmlUrl,
}: ReportPreviewProps) {
  const router = useRouter();
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!htmlUrl) return;
    setLoading(true);
    fetch(htmlUrl)
      .then((res) => res.text())
      .then((text) => setHtmlContent(text))
      .catch(() => setHtmlContent(null))
      .finally(() => setLoading(false));
  }, [htmlUrl]);

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

        {pdfUrl && (
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-3 py-2 text-sm bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            <Download size={16} />
            PDFダウンロード
          </a>
        )}

        {htmlUrl && (
          <a
            href={htmlUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <FileText size={16} />
            HTMLダウンロード
          </a>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-500">
            読み込み中...
          </div>
        ) : htmlContent ? (
          <iframe
            srcDoc={htmlContent}
            className="w-full border-0"
            style={{ height: "80vh" }}
            title="レポートプレビュー"
            sandbox="allow-same-origin allow-scripts"
          />
        ) : pdfUrl ? (
          <iframe
            src={pdfUrl}
            className="w-full border-0"
            style={{ height: "80vh" }}
            title="レポートプレビュー"
          />
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            プレビューを表示できません。ファイルがStorageにアップロードされていない可能性があります。
          </div>
        )}
      </div>
    </div>
  );
}
