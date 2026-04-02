"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Loader2,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  FileText,
  BarChart3,
  Sparkles,
  FileOutput,
  ArrowRight,
  PenLine,
} from "lucide-react";
import type { Client } from "@/lib/types";
import { getDefaultDateRange } from "@/lib/utils";

interface GenerateFormProps {
  clients: Client[];
  initialClient?: string;
}

type Step =
  | "idle"
  | "fetching"
  | "charts"
  | "ai"
  | "rendering"
  | "done"
  | "error";

const steps = [
  { key: "fetching", label: "データ取得", icon: FileText },
  { key: "charts", label: "グラフ生成", icon: BarChart3 },
  { key: "ai", label: "AI分析", icon: Sparkles },
  { key: "rendering", label: "レポート出力", icon: FileOutput },
] as const;

export default function GenerateForm({
  clients,
  initialClient,
}: GenerateFormProps) {
  const defaultRange = getDefaultDateRange();
  const [selectedClient, setSelectedClient] = useState(initialClient || "");
  const [startDate, setStartDate] = useState(defaultRange.startDate);
  const [endDate, setEndDate] = useState(defaultRange.endDate);
  const [step, setStep] = useState<Step>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [reportId, setReportId] = useState<string | null>(null);
  const router = useRouter();

  // 総評・改善案の入力
  const [bestPostAnalysis, setBestPostAnalysis] = useState("");
  const [improvementSuggestions, setImprovementSuggestions] = useState("");
  const [nextMonthPlan, setNextMonthPlan] = useState("");
  const [useAi, setUseAi] = useState(true); // AI自動生成を使うか

  const handleGenerate = async () => {
    if (!selectedClient) return;
    setStep("fetching");
    setErrorMsg("");
    setReportId(null);

    // ユーザー入力がある場合はそれを送る
    const userCommentary =
      !useAi &&
      (bestPostAnalysis || improvementSuggestions || nextMonthPlan)
        ? {
            best_post_analysis: bestPostAnalysis,
            improvement_suggestions: improvementSuggestions,
            next_month_plan: nextMonthPlan,
          }
        : null;

    try {
      await new Promise((r) => setTimeout(r, 500));
      setStep("charts");
      await new Promise((r) => setTimeout(r, 500));
      setStep("ai");

      const res = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_slug: selectedClient,
          start_date: startDate,
          end_date: endDate,
          user_commentary: userCommentary,
        }),
      });

      setStep("rendering");
      await new Promise((r) => setTimeout(r, 300));

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "レポート生成に失敗しました");
      }

      const data = await res.json();
      setReportId(data.report_id);
      setStep("done");
    } catch (e) {
      setStep("error");
      setErrorMsg(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const isProcessing = !["idle", "done", "error"].includes(step);

  const getStepIndex = () => steps.findIndex((s) => s.key === step);

  return (
    <div className="max-w-2xl">
      {/* ステップインジケーター */}
      <div className="flex items-center gap-3 mb-8">
        {["入力", "生成", "確認・編集"].map((label, i) => (
          <div key={label} className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  step === "idle" && i === 0
                    ? "gradient-accent text-white"
                    : step === "done" && i === 2
                    ? "gradient-accent text-white"
                    : isProcessing && i === 1
                    ? "gradient-accent text-white"
                    : "bg-gray-200 text-gray-400"
                }`}
              >
                {i + 1}
              </div>
              <span
                className={`text-sm font-medium ${
                  (step === "idle" && i === 0) ||
                  (isProcessing && i === 1) ||
                  (step === "done" && i === 2)
                    ? "text-gray-800"
                    : "text-gray-400"
                }`}
              >
                {label}
              </span>
            </div>
            {i < 2 && (
              <ArrowRight size={14} className="text-gray-300" />
            )}
          </div>
        ))}
      </div>

      {/* フォーム */}
      <div className="bg-white rounded-xl border border-gray-200/80 p-6 space-y-5">
        {/* クライアント・日付 */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            クライアント
          </label>
          <div className="relative">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              disabled={isProcessing || step === "done"}
              className="w-full appearance-none px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 disabled:text-gray-400 pr-8"
            >
              <option value="">選択してください</option>
              {clients.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              開始日
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={isProcessing || step === "done"}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              終了日
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={isProcessing || step === "done"}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
        </div>

        {/* 総評・改善案セクション */}
        <div className="border-t border-gray-100 pt-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <PenLine size={15} className="text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                総評・改善案
              </span>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
                disabled={isProcessing || step === "done"}
                className="rounded border-gray-300 text-accent focus:ring-accent/50"
              />
              <span className="text-xs text-gray-500">
                AIで自動生成する
              </span>
            </label>
          </div>

          {!useAi && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  総評（ベスト投稿の分析など）
                </label>
                <textarea
                  value={bestPostAnalysis}
                  onChange={(e) => setBestPostAnalysis(e.target.value)}
                  disabled={isProcessing || step === "done"}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 resize-none"
                  placeholder="例: 今月最も再生されたのは〇〇の動画で..."
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  改善提案
                </label>
                <textarea
                  value={improvementSuggestions}
                  onChange={(e) => setImprovementSuggestions(e.target.value)}
                  disabled={isProcessing || step === "done"}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 resize-none"
                  placeholder="例: 投稿頻度を上げることで..."
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  来月のアクションプラン
                </label>
                <textarea
                  value={nextMonthPlan}
                  onChange={(e) => setNextMonthPlan(e.target.value)}
                  disabled={isProcessing || step === "done"}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:bg-gray-50 resize-none"
                  placeholder="例: 1. 週3回以上の投稿を維持..."
                />
              </div>
              <p className="text-[11px] text-gray-400">
                ※ 空欄の項目はAIが自動生成します。生成後にプレビュー画面で修正も可能です。
              </p>
            </div>
          )}

          {useAi && (
            <p className="text-xs text-gray-400 bg-gray-50 p-3 rounded-lg">
              AIがデータを分析して総評・改善案を自動生成します。生成後にプレビュー画面で内容を確認・修正できます。
            </p>
          )}
        </div>

        {/* 生成ボタン */}
        <button
          onClick={handleGenerate}
          disabled={!selectedClient || isProcessing || step === "done"}
          className="w-full gradient-accent text-white py-3 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isProcessing && <Loader2 size={16} className="animate-spin" />}
          {isProcessing ? "生成中..." : "レポートを生成"}
        </button>
      </div>

      {/* プログレス / 結果 */}
      {step !== "idle" && (
        <div className="mt-5 bg-white rounded-xl border border-gray-200/80 p-6">
          {step === "error" ? (
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center shrink-0">
                <AlertCircle size={20} className="text-red-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-red-600">
                  エラーが発生しました
                </p>
                <p className="text-xs text-red-400 mt-1">{errorMsg}</p>
                <button
                  onClick={() => setStep("idle")}
                  className="text-xs text-gray-500 hover:text-accent mt-2"
                >
                  もう一度試す
                </button>
              </div>
            </div>
          ) : step === "done" ? (
            <div className="text-center py-2">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center mx-auto mb-3">
                <CheckCircle size={24} className="text-emerald-500" />
              </div>
              <p className="text-sm font-semibold text-gray-800 mb-1">
                レポートが生成されました
              </p>
              <p className="text-xs text-gray-400 mb-4">
                プレビュー画面で内容を確認・修正し、PDFとしてダウンロードできます
              </p>
              <button
                onClick={() =>
                  router.push(
                    reportId ? `/reports/${reportId}/preview` : "/reports"
                  )
                }
                className="px-6 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity inline-flex items-center gap-2"
              >
                確認・編集画面へ
                <ArrowRight size={15} />
              </button>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-3 mb-5">
                {steps.map((s, i) => {
                  const currentIdx = getStepIndex();
                  const isComplete = i < currentIdx;
                  const isCurrent = i === currentIdx;
                  const Icon = s.icon;
                  return (
                    <div key={s.key} className="flex items-center gap-3 flex-1">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                          isComplete
                            ? "bg-emerald-100 text-emerald-600"
                            : isCurrent
                            ? "bg-accent/10 text-accent progress-pulse"
                            : "bg-gray-100 text-gray-300"
                        }`}
                      >
                        {isComplete ? <CheckCircle size={16} /> : <Icon size={16} />}
                      </div>
                      {i < steps.length - 1 && (
                        <div
                          className={`flex-1 h-0.5 rounded ${
                            isComplete ? "bg-emerald-200" : "bg-gray-100"
                          }`}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-sm text-gray-600 text-center">
                {steps[getStepIndex()]?.label || "処理中"}...
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
