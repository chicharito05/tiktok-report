"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Loader2,
  RefreshCw,
  PenLine,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Presentation,
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";

interface ReportEditorProps {
  reportId: string;
  clientName: string;
  periodLabel: string;
  pptxUrl: string | null;
}

export default function ReportEditor({
  reportId,
  clientName,
  periodLabel,
  pptxUrl: initialPptxUrl,
}: ReportEditorProps) {
  const router = useRouter();
  const { showToast } = useToast();

  const [currentPptxUrl, setCurrentPptxUrl] = useState(initialPptxUrl);

  // 総評・改善案の編集
  const [showEditor, setShowEditor] = useState(false);
  const [bestPostAnalysis, setBestPostAnalysis] = useState("");
  const [improvementSuggestions, setImprovementSuggestions] = useState("");
  const [nextMonthPlan, setNextMonthPlan] = useState("");
  const [regenerating, setRegenerating] = useState(false);

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

      if (data.pptx_url) {
        setCurrentPptxUrl(data.pptx_url);
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
            必要に応じて総評・改善案を修正し、PPTXをダウンロードしてください
          </p>
        </div>
        <div className="flex items-center gap-2">
          {currentPptxUrl && (
            <a
              href={currentPptxUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <Presentation size={15} />
              PPTXダウンロード
            </a>
          )}
        </div>
      </div>

      {/* 2カラムレイアウト */}
      <div className="flex gap-5">
        {/* メインエリア */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden">
            {currentPptxUrl ? (
              <div className="flex flex-col items-center justify-center h-[75vh] text-gray-500">
                <Presentation size={64} className="text-gray-300 mb-4" />
                <p className="text-lg font-medium text-gray-700">レポートが生成されました</p>
                <p className="text-sm text-gray-400 mt-2">右上のボタンからPPTXをダウンロードしてください</p>
                <p className="text-xs text-gray-300 mt-1">Google スライドで直接開けます</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                レポートファイルが見つかりません
              </div>
            )}
          </div>
        </div>

        {/* 編集パネル */}
        <div className="w-[380px] shrink-0">
          <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden sticky top-20">
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
                  修正内容でPPTXが再生成されます
                </p>
              </div>
            )}

            {!showEditor && (
              <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-3">
                {currentPptxUrl ? (
                  <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 p-3 rounded-lg">
                    <CheckCircle size={16} />
                    <span className="text-xs font-medium">PPTX生成済み</span>
                  </div>
                ) : (
                  <div className="text-xs text-gray-400 bg-gray-50 p-3 rounded-lg">
                    レポートファイルが見つかりません
                  </div>
                )}
                {currentPptxUrl && (
                  <a
                    href={currentPptxUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                  >
                    <Presentation size={15} />
                    PPTXをダウンロード
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
