"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  FileText,
  Loader2,
  RefreshCw,
  PenLine,
  ChevronDown,
  ChevronUp,
  CheckCircle,
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";

interface ReportEditorProps {
  reportId: string;
  clientName: string;
  periodLabel: string;
  htmlUrl: string | null;
  pdfUrl: string | null;
}

export default function ReportEditor({
  reportId,
  clientName,
  periodLabel,
  htmlUrl: initialHtmlUrl,
  pdfUrl: initialPdfUrl,
}: ReportEditorProps) {
  const router = useRouter();
  const { showToast } = useToast();

  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentPdfUrl, setCurrentPdfUrl] = useState(initialPdfUrl);
  const [currentHtmlUrl, setCurrentHtmlUrl] = useState(initialHtmlUrl);

  // 総評・改善案の編集
  const [showEditor, setShowEditor] = useState(false);
  const [bestPostAnalysis, setBestPostAnalysis] = useState("");
  const [improvementSuggestions, setImprovementSuggestions] = useState("");
  const [nextMonthPlan, setNextMonthPlan] = useState("");
  const [regenerating, setRegenerating] = useState(false);

  // HTML読み込み
  useEffect(() => {
    if (!currentHtmlUrl) return;
    setLoading(true);
    fetch(currentHtmlUrl)
      .then((res) => res.text())
      .then((text) => {
        setHtmlContent(text);
        // HTMLから現在の総評テキストを抽出して初期値にセット
        extractCommentaryFromHtml(text);
      })
      .catch(() => setHtmlContent(null))
      .finally(() => setLoading(false));
  }, [currentHtmlUrl]);

  /** HTMLから現在のAIコメンタリーテキストを抽出 */
  const extractCommentaryFromHtml = (html: string) => {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // テンプレートのP5スライド内のテキストを抽出
      const sections = doc.querySelectorAll(".commentary-text");
      if (sections.length >= 3) {
        setBestPostAnalysis(sections[0].textContent?.trim() || "");
        setImprovementSuggestions(sections[1].textContent?.trim() || "");
        setNextMonthPlan(sections[2].textContent?.trim() || "");
      } else {
        // fallback: pre要素から取得
        const pres = doc.querySelectorAll("pre");
        const texts: string[] = [];
        pres.forEach((pre) => {
          const t = pre.textContent?.trim();
          if (t && t !== "分析コメントの生成に失敗しました。") {
            texts.push(t);
          }
        });
        if (texts.length >= 1) setBestPostAnalysis(texts[0]);
        if (texts.length >= 2) setImprovementSuggestions(texts[1]);
        if (texts.length >= 3) setNextMonthPlan(texts[2]);
      }
    } catch {
      // 抽出失敗は無視
    }
  };

  /** 総評・改善案を修正してレポート再生成 */
  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const res = await fetch("/api/reports/regenerate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_id: reportId,
          best_post_analysis: bestPostAnalysis,
          improvement_suggestions: improvementSuggestions,
          next_month_plan: nextMonthPlan,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "再生成に失敗しました");

      showToast("success", "レポートを更新しました");

      // 新しいURLでプレビューを更新
      if (data.html_url) {
        setCurrentHtmlUrl(data.html_url);
      }
      if (data.pdf_url) {
        setCurrentPdfUrl(data.pdf_url);
      }

      setShowEditor(false);
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "再生成に失敗しました");
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <button
              onClick={() => router.push("/reports")}
              className="text-sm text-gray-400 hover:text-accent transition-colors"
            >
              ← レポート一覧
            </button>
          </div>
          <h1 className="text-xl font-bold text-primary">
            {clientName} - {periodLabel}
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            プレビューを確認し、必要に応じて総評・改善案を修正してください
          </p>
        </div>
        <div className="flex items-center gap-2">
          {currentPdfUrl && (
            <a
              href={currentPdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <Download size={15} />
              PDFダウンロード
            </a>
          )}
          {currentHtmlUrl && (
            <a
              href={currentHtmlUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors"
            >
              <FileText size={15} />
              HTML
            </a>
          )}
        </div>
      </div>

      {/* 2カラムレイアウト：プレビュー + 編集パネル */}
      <div className="flex gap-5">
        {/* プレビュー */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-[75vh] text-gray-400">
                <Loader2 size={24} className="animate-spin mr-2" />
                読み込み中...
              </div>
            ) : htmlContent ? (
              <iframe
                srcDoc={htmlContent}
                className="w-full border-0"
                style={{ height: "75vh" }}
                title="レポートプレビュー"
                sandbox="allow-same-origin allow-scripts"
              />
            ) : currentPdfUrl ? (
              <iframe
                src={currentPdfUrl}
                className="w-full border-0"
                style={{ height: "75vh" }}
                title="レポートプレビュー"
              />
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                プレビューを表示できません
              </div>
            )}
          </div>
        </div>

        {/* 編集パネル */}
        <div className="w-[380px] shrink-0">
          <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden sticky top-20">
            {/* パネルヘッダー */}
            <button
              onClick={() => setShowEditor(!showEditor)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <PenLine size={16} className="text-accent" />
                <span className="text-sm font-semibold text-gray-800">
                  総評・改善案を編集
                </span>
              </div>
              {showEditor ? (
                <ChevronUp size={16} className="text-gray-400" />
              ) : (
                <ChevronDown size={16} className="text-gray-400" />
              )}
            </button>

            {showEditor && (
              <div className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    総評
                  </label>
                  <textarea
                    value={bestPostAnalysis}
                    onChange={(e) => setBestPostAnalysis(e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none"
                    placeholder="ベスト投稿の分析、全体的な所感など..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    改善提案
                  </label>
                  <textarea
                    value={improvementSuggestions}
                    onChange={(e) => setImprovementSuggestions(e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none"
                    placeholder="改善すべきポイントや提案..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    来月のアクションプラン
                  </label>
                  <textarea
                    value={nextMonthPlan}
                    onChange={(e) => setNextMonthPlan(e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-none"
                    placeholder="来月の具体的なアクションプラン..."
                  />
                </div>

                <button
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  className="w-full gradient-accent text-white py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {regenerating ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <RefreshCw size={15} />
                  )}
                  {regenerating ? "再生成中..." : "修正を反映してレポート更新"}
                </button>

                <p className="text-[10px] text-gray-400 text-center">
                  修正内容でHTML/PDFが再生成されます
                </p>
              </div>
            )}

            {/* PDF化セクション */}
            {!showEditor && (
              <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-3">
                {currentPdfUrl ? (
                  <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 p-3 rounded-lg">
                    <CheckCircle size={16} />
                    <span className="text-xs font-medium">PDF生成済み</span>
                  </div>
                ) : (
                  <div className="text-xs text-gray-400 bg-gray-50 p-3 rounded-lg">
                    PDFは総評を編集して「レポート更新」を実行すると生成されます
                  </div>
                )}
                {currentPdfUrl && (
                  <a
                    href={currentPdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                  >
                    <Download size={15} />
                    PDFをダウンロード
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
