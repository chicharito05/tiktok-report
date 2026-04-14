"use client";

import { useState, useEffect } from "react";
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
  Download,
  RefreshCw,
  Eye,
  EyeOff,
  Presentation,
} from "lucide-react";
import type { Client } from "@/lib/types";
import { useToast } from "@/components/ui/Toast";

function fmtNum(n: number | null | undefined): string {
  if (n == null) return "--";
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  return n.toLocaleString("ja-JP");
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "--";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function fmtDate(d: string): string {
  if (!d) return "";
  try {
    return new Date(d).toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
  } catch {
    return d;
  }
}

interface GenerateFormProps {
  clients: Client[];
  initialClient?: string;
}

type Phase = "input" | "generating" | "review" | "exporting" | "done";

const genSteps = [
  { key: "fetching", label: "データ取得", icon: FileText },
  { key: "charts", label: "グラフ生成", icon: BarChart3 },
  { key: "ai", label: "AI分析", icon: Sparkles },
  { key: "rendering", label: "レポート生成", icon: FileOutput },
] as const;

type GenStep = (typeof genSteps)[number]["key"];

export default function GenerateForm({
  clients,
  initialClient,
}: GenerateFormProps) {
  const { showToast } = useToast();

  // --- Phase ---
  const [phase, setPhase] = useState<Phase>("input");
  const [genStep, setGenStep] = useState<GenStep>("fetching");
  const [errorMsg, setErrorMsg] = useState("");

  // --- Input ---
  const [selectedClient, setSelectedClient] = useState(initialClient || "");
  const [operationMonth, setOperationMonth] = useState("");
  const [availableOperationMonths, setAvailableOperationMonths] = useState<string[]>([]);

  // --- Generated report data ---
  const [reportId, setReportId] = useState<string | null>(null);
  const [htmlUrl, setHtmlUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pptxUrl, setPptxUrl] = useState<string | null>(null);
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [summary, setSummary] = useState<any>(null);

  // --- Editable commentary ---
  const [bestPostAnalysis, setBestPostAnalysis] = useState("");
  const [improvementSuggestions, setImprovementSuggestions] = useState("");
  const [nextMonthPlan, setNextMonthPlan] = useState("");

  // 選択クライアントの運用月リストを取得
  useEffect(() => {
    if (!selectedClient) {
      setAvailableOperationMonths([]);
      return;
    }
    const clientObj = clients.find((c) => c.name === selectedClient);
    if (!clientObj) return;
    fetch(`/api/posts?client_slug=${encodeURIComponent(selectedClient)}`)
      .then((r) => r.json())
      .then((data) => {
        const months = new Set<string>();
        for (const p of data.posts || []) {
          if (p.operation_month) months.add(p.operation_month);
        }
        const sorted = Array.from(months).sort((a, b) => {
          const numA = parseInt(a.replace(/[^0-9]/g, "")) || 0;
          const numB = parseInt(b.replace(/[^0-9]/g, "")) || 0;
          return numA - numB;
        });
        setAvailableOperationMonths(sorted);
      })
      .catch(() => setAvailableOperationMonths([]));
  }, [selectedClient, clients]);

  // Load HTML content and extract commentary when htmlUrl changes
  useEffect(() => {
    if (!htmlUrl) return;
    fetch(htmlUrl)
      .then((res) => res.text())
      .then((text) => {
        setHtmlContent(text);
        extractCommentaryFromHtml(text);
      })
      .catch(() => setHtmlContent(null));
  }, [htmlUrl]);

  /** HTMLからAIコメンタリーテキストを抽出 */
  const extractCommentaryFromHtml = (html: string) => {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const sections = doc.querySelectorAll(".commentary-text");
      if (sections.length >= 3) {
        setBestPostAnalysis(sections[0].textContent?.trim() || "");
        setImprovementSuggestions(sections[1].textContent?.trim() || "");
        setNextMonthPlan(sections[2].textContent?.trim() || "");
      } else {
        const pres = doc.querySelectorAll("pre");
        const texts: string[] = [];
        pres.forEach((pre) => {
          const t = pre.textContent?.trim();
          if (t && t !== "分析コメントの生成に失敗しました。") texts.push(t);
        });
        if (texts.length >= 1) setBestPostAnalysis(texts[0]);
        if (texts.length >= 2) setImprovementSuggestions(texts[1]);
        if (texts.length >= 3) setNextMonthPlan(texts[2]);
      }
    } catch {
      // ignore
    }
  };

  // ============================================================
  // Step 1: レポート作成依頼
  // ============================================================
  const handleGenerate = async () => {
    if (!selectedClient) return;
    if (!operationMonth) {
      setErrorMsg("運用月を選択してください");
      return;
    }
    setPhase("generating");
    setGenStep("fetching");
    setErrorMsg("");
    setReportId(null);

    try {
      await new Promise((r) => setTimeout(r, 400));
      setGenStep("charts");
      await new Promise((r) => setTimeout(r, 400));
      setGenStep("ai");

      const res = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_slug: selectedClient,
          operation_month: operationMonth,
        }),
      });

      setGenStep("rendering");
      await new Promise((r) => setTimeout(r, 300));

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "レポート生成に失敗しました");
      }

      const data = await res.json();
      setReportId(data.report_id);
      if (data.html_url) setHtmlUrl(data.html_url);
      if (data.pptx_url) setPptxUrl(data.pptx_url);
      if (data.summary) setSummary(data.summary);

      // → レビューフェーズへ
      setPhase("review");
    } catch (e) {
      setPhase("input");
      setErrorMsg(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  // ============================================================
  // Step 3: レポート出力（編集反映 → 最終PDF生成）
  // ============================================================
  const handleExport = async () => {
    if (!reportId) {
      showToast("error", "レポートIDが見つかりません。レポートを再作成してください。");
      return;
    }
    setPhase("exporting");

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

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "レポート出力に失敗しました");
      }

      const data = await res.json();
      if (data.html_url) setHtmlUrl(data.html_url);
      if (data.pdf_url) setPdfUrl(data.pdf_url);
      if (data.pptx_url) setPptxUrl(data.pptx_url);

      setPhase("done");
      showToast("success", "レポートを出力しました");
    } catch (e) {
      setPhase("review");
      showToast("error", e instanceof Error ? e.message : "出力に失敗しました");
    }
  };

  const handleReset = () => {
    setPhase("input");
    setReportId(null);
    setHtmlUrl(null);
    setPdfUrl(null);
    setPptxUrl(null);
    setHtmlContent(null);
    setSummary(null);
    setBestPostAnalysis("");
    setImprovementSuggestions("");
    setNextMonthPlan("");
    setOperationMonth("");
    setErrorMsg("");
    setShowPreview(false);
  };

  // ============================================================
  // RENDER
  // ============================================================
  const phaseIndex =
    phase === "input" ? 0
    : phase === "generating" ? 1
    : phase === "review" ? 1
    : 2;

  const genStepIndex = genSteps.findIndex((s) => s.key === genStep);

  return (
    <div className="max-w-5xl">
      {/* ===== ステップインジケーター ===== */}
      <div className="flex items-center gap-3 mb-8">
        {["レポート作成", "チェック・編集", "レポート出力"].map((label, i) => (
          <div key={label} className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  i === phaseIndex
                    ? "gradient-accent text-white"
                    : i < phaseIndex
                    ? "bg-emerald-100 text-emerald-600"
                    : "bg-gray-200 text-gray-400"
                }`}
              >
                {i < phaseIndex ? <CheckCircle size={14} /> : i + 1}
              </div>
              <span
                className={`text-sm font-medium ${
                  i === phaseIndex ? "text-gray-800" : "text-gray-400"
                }`}
              >
                {label}
              </span>
            </div>
            {i < 2 && <ArrowRight size={14} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* ===== Phase: INPUT ===== */}
      {phase === "input" && (
        <div className="bg-white rounded-xl border border-gray-200/80 p-6 space-y-5">
          {errorMsg && (
            <div className="flex items-start gap-3 bg-red-50 p-4 rounded-lg">
              <AlertCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-600">{errorMsg}</p>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              クライアント
            </label>
            <div className="relative">
              <select
                value={selectedClient}
                onChange={(e) => setSelectedClient(e.target.value)}
                className="w-full appearance-none px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent pr-8"
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

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              運用月
            </label>
            <div className="relative">
              <select
                value={operationMonth}
                onChange={(e) => setOperationMonth(e.target.value)}
                disabled={!selectedClient || availableOperationMonths.length === 0}
                className="w-full appearance-none px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent pr-8 disabled:bg-gray-50 disabled:text-gray-400"
              >
                <option value="">
                  {selectedClient
                    ? availableOperationMonths.length === 0
                      ? "運用月タグ付きの投稿がありません"
                      : "選択してください"
                    : "先にクライアントを選択"}
                </option>
                {availableOperationMonths.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={14}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
              />
            </div>
            <p className="text-[11px] text-gray-400 mt-1.5">
              レポート対象期間は Notion 上の「運用月」タグで自動的に決まります。
            </p>
          </div>

          <button
            onClick={handleGenerate}
            disabled={!selectedClient || !operationMonth}
            className="w-full gradient-accent text-white py-3 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Sparkles size={16} />
            レポートを作成
          </button>

          <p className="text-[11px] text-gray-400 text-center">
            AIがデータを分析してレポートを自動生成します。次のステップで内容を確認・編集できます。
          </p>
        </div>
      )}

      {/* ===== Phase: GENERATING ===== */}
      {phase === "generating" && (
        <div className="bg-white rounded-xl border border-gray-200/80 p-8">
          <div className="flex items-center gap-3 mb-6">
            {genSteps.map((s, i) => {
              const isComplete = i < genStepIndex;
              const isCurrent = i === genStepIndex;
              const Icon = s.icon;
              return (
                <div key={s.key} className="flex items-center gap-3 flex-1">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                      isComplete
                        ? "bg-emerald-100 text-emerald-600"
                        : isCurrent
                        ? "bg-accent/10 text-accent progress-pulse"
                        : "bg-gray-100 text-gray-300"
                    }`}
                  >
                    {isComplete ? <CheckCircle size={18} /> : <Icon size={18} />}
                  </div>
                  {i < genSteps.length - 1 && (
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
            {genSteps[genStepIndex]?.label || "処理中"}...
          </p>
          <p className="text-xs text-gray-400 text-center mt-2">
            {selectedClient} / {operationMonth}
          </p>
        </div>
      )}

      {/* ===== Phase: REVIEW (チェック・編集) ===== */}
      {phase === "review" && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-800">
                レポート内容の確認・編集
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                数値データを参照しながら、AIが生成した内容を確認・書き換えてください。
              </p>
            </div>
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {showPreview ? <EyeOff size={14} /> : <Eye size={14} />}
              {showPreview ? "プレビューを閉じる" : "プレビュー表示"}
            </button>
          </div>

          {/* ===== データ参照パネル ===== */}
          {summary && (
            <div className="bg-white rounded-xl border border-gray-200/80 p-5 space-y-4">
              {/* KPIサマリー */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  KPIサマリー
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                  {[
                    { label: "総再生数", value: fmtNum(summary.total_views), mom: summary.mom_views },
                    { label: "いいね", value: fmtNum(summary.total_likes), mom: summary.mom_likes },
                    { label: "コメント", value: fmtNum(summary.total_comments), mom: summary.mom_comments },
                    { label: "シェア", value: fmtNum(summary.total_shares), mom: summary.mom_shares },
                    { label: "投稿数", value: String(summary.post_count ?? "--") },
                    { label: "平均再生数", value: fmtNum(summary.avg_views_per_post) },
                  ].map((kpi) => (
                    <div key={kpi.label} className="bg-gray-50 rounded-lg p-3">
                      <div className="text-[10px] text-gray-400 mb-0.5">{kpi.label}</div>
                      <div className="text-sm font-bold text-gray-800">{kpi.value}</div>
                      {kpi.mom != null && (
                        <div className={`text-[10px] font-medium ${kpi.mom > 0 ? "text-emerald-600" : kpi.mom < 0 ? "text-red-500" : "text-gray-400"}`}>
                          前月比 {fmtPct(kpi.mom)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                {(summary.engagement_rate != null || summary.profile_transition_rate != null) && (
                  <div className="flex gap-3 mt-3">
                    {summary.engagement_rate != null && (
                      <div className="bg-blue-50 rounded-lg p-3 flex-1">
                        <div className="text-[10px] text-blue-400">エンゲージメント率</div>
                        <div className="text-sm font-bold text-blue-700">{summary.engagement_rate.toFixed(2)}%</div>
                      </div>
                    )}
                    {summary.profile_transition_rate != null && (
                      <div className="bg-purple-50 rounded-lg p-3 flex-1">
                        <div className="text-[10px] text-purple-400">プロフィール遷移率</div>
                        <div className="text-sm font-bold text-purple-700">{summary.profile_transition_rate.toFixed(2)}%</div>
                      </div>
                    )}
                    {summary.follower_growth != null && (
                      <div className="bg-emerald-50 rounded-lg p-3 flex-1">
                        <div className="text-[10px] text-emerald-400">フォロワー増減</div>
                        <div className="text-sm font-bold text-emerald-700">
                          {summary.follower_growth > 0 ? "+" : ""}{fmtNum(summary.follower_growth)}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* TOP投稿 */}
              {summary.top_posts?.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    TOP {summary.top_posts.length} 投稿（再生数順）
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-100">
                          <th className="text-left py-1.5 pr-3 font-medium">#</th>
                          <th className="text-left py-1.5 pr-3 font-medium">タイトル</th>
                          <th className="text-left py-1.5 pr-3 font-medium">投稿日</th>
                          <th className="text-right py-1.5 pr-3 font-medium">再生数</th>
                          <th className="text-right py-1.5 pr-3 font-medium">いいね</th>
                          <th className="text-right py-1.5 pr-3 font-medium">コメント</th>
                          <th className="text-right py-1.5 font-medium">シェア</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {summary.top_posts.map((p: any, i: number) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="py-1.5 pr-3 text-gray-400 font-medium">{i + 1}</td>
                            <td className="py-1.5 pr-3 text-gray-700 font-medium max-w-[200px] truncate">{p.caption}</td>
                            <td className="py-1.5 pr-3 text-gray-400 whitespace-nowrap">{fmtDate(p.post_date)}</td>
                            <td className="py-1.5 pr-3 text-right font-bold text-gray-800 tabular-nums">{fmtNum(p.views)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.likes)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.comments)}</td>
                            <td className="py-1.5 text-right text-gray-600 tabular-nums">{fmtNum(p.shares)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* WORST投稿 */}
              {summary.worst_posts?.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    WORST {summary.worst_posts.length} 投稿
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-100">
                          <th className="text-left py-1.5 pr-3 font-medium">タイトル</th>
                          <th className="text-left py-1.5 pr-3 font-medium">投稿日</th>
                          <th className="text-right py-1.5 pr-3 font-medium">再生数</th>
                          <th className="text-right py-1.5 pr-3 font-medium">いいね</th>
                          <th className="text-right py-1.5 pr-3 font-medium">コメント</th>
                          <th className="text-right py-1.5 font-medium">シェア</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {summary.worst_posts.map((p: any, i: number) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="py-1.5 pr-3 text-gray-700 font-medium max-w-[200px] truncate">{p.caption}</td>
                            <td className="py-1.5 pr-3 text-gray-400 whitespace-nowrap">{fmtDate(p.post_date)}</td>
                            <td className="py-1.5 pr-3 text-right font-bold text-gray-800 tabular-nums">{fmtNum(p.views)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.likes)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.comments)}</td>
                            <td className="py-1.5 text-right text-gray-600 tabular-nums">{fmtNum(p.shares)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 全投稿データ */}
              {summary.all_posts?.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    全投稿データ（{summary.all_posts.length}件）
                  </h3>
                  <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-white">
                        <tr className="text-gray-400 border-b border-gray-200">
                          <th className="text-left py-1.5 pr-3 font-medium">#</th>
                          <th className="text-left py-1.5 pr-3 font-medium">タイトル</th>
                          <th className="text-left py-1.5 pr-3 font-medium">投稿日</th>
                          <th className="text-right py-1.5 pr-3 font-medium">再生数</th>
                          <th className="text-right py-1.5 pr-3 font-medium">いいね</th>
                          <th className="text-right py-1.5 pr-3 font-medium">コメント</th>
                          <th className="text-right py-1.5 pr-3 font-medium">シェア</th>
                          <th className="text-right py-1.5 pr-3 font-medium">ENG率</th>
                          <th className="text-right py-1.5 pr-3 font-medium">視聴完了</th>
                          <th className="text-right py-1.5 font-medium">2秒視聴</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {summary.all_posts.map((p: any, i: number) => (
                          <tr key={i} className={`border-b border-gray-50 hover:bg-gray-50/50 ${i < 3 ? "bg-amber-50/30" : ""}`}>
                            <td className="py-1.5 pr-3 text-gray-400 font-medium">{i + 1}</td>
                            <td className="py-1.5 pr-3 text-gray-700 font-medium max-w-[220px] truncate">{p.caption}</td>
                            <td className="py-1.5 pr-3 text-gray-400 whitespace-nowrap">{fmtDate(p.post_date)}</td>
                            <td className="py-1.5 pr-3 text-right font-bold text-gray-800 tabular-nums">{fmtNum(p.views)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.likes)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.comments)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">{fmtNum(p.shares)}</td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">
                              {p.engagement_rate != null ? `${p.engagement_rate.toFixed(1)}%` : "--"}
                            </td>
                            <td className="py-1.5 pr-3 text-right text-gray-600 tabular-nums">
                              {p.watch_through_rate != null ? `${p.watch_through_rate}%` : "--"}
                            </td>
                            <td className="py-1.5 text-right text-gray-600 tabular-nums">
                              {p.two_sec_view_rate != null ? `${p.two_sec_view_rate}%` : "--"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ===== 編集エリア + プレビュー ===== */}
          <div className={`flex gap-5`}>
            {/* 編集パネル */}
            <div className={`${showPreview ? "w-1/2" : "w-full"} space-y-4`}>
              <div className="bg-white rounded-xl border border-gray-200/80 p-5 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-2">
                    総評（ベスト投稿の分析・全体の所感）
                  </label>
                  <textarea
                    value={bestPostAnalysis}
                    onChange={(e) => setBestPostAnalysis(e.target.value)}
                    rows={8}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-y"
                    placeholder="AIが生成した内容がここに表示されます..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-2">
                    改善提案
                  </label>
                  <textarea
                    value={improvementSuggestions}
                    onChange={(e) => setImprovementSuggestions(e.target.value)}
                    rows={8}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-y"
                    placeholder="AIが生成した内容がここに表示されます..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-2">
                    来月のアクションプラン
                  </label>
                  <textarea
                    value={nextMonthPlan}
                    onChange={(e) => setNextMonthPlan(e.target.value)}
                    rows={8}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-y"
                    placeholder="AIが生成した内容がここに表示されます..."
                  />
                </div>
              </div>

              {/* アクション */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleExport}
                  className="flex-1 gradient-accent text-white py-3 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                >
                  <FileOutput size={16} />
                  レポート出力
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-3 border border-gray-200 text-gray-500 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  やり直す
                </button>
              </div>
            </div>

            {/* プレビュー（トグル表示） */}
            {showPreview && (
              <div className="w-1/2">
                <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden sticky top-20">
                  {htmlContent ? (
                    <iframe
                      srcDoc={htmlContent}
                      className="w-full border-0"
                      style={{ height: "80vh" }}
                      title="レポートプレビュー"
                      sandbox="allow-same-origin allow-scripts"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                      <Loader2 size={18} className="animate-spin mr-2" />
                      プレビュー読み込み中...
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== Phase: EXPORTING ===== */}
      {phase === "exporting" && (
        <div className="bg-white rounded-xl border border-gray-200/80 p-8 text-center">
          <Loader2 size={32} className="animate-spin text-accent mx-auto mb-4" />
          <p className="text-sm font-medium text-gray-700">
            編集内容を反映してレポートを出力中...
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Googleスライド用ファイルを生成しています
          </p>
        </div>
      )}

      {/* ===== Phase: DONE ===== */}
      {phase === "done" && (
        <div className="bg-white rounded-xl border border-gray-200/80 p-8 text-center">
          <div className="w-14 h-14 bg-emerald-50 rounded-xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={28} className="text-emerald-500" />
          </div>
          <p className="text-lg font-bold text-gray-800 mb-1">
            レポート出力完了
          </p>
          <p className="text-xs text-gray-400 mb-6">
            {selectedClient} / {operationMonth}
          </p>

          <div className="flex items-center justify-center gap-3 mb-6">
            {pptxUrl && (
              <a
                href={pptxUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-6 py-3 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
              >
                <Presentation size={16} />
                Googleスライド用ダウンロード (.pptx)
              </a>
            )}
            {htmlUrl && (
              <a
                href={htmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-6 py-3 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                <FileText size={16} />
                HTML表示
              </a>
            )}
            {pdfUrl && (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-3 border border-gray-200 text-gray-400 rounded-lg text-xs hover:bg-gray-50 transition-colors"
              >
                <Download size={14} />
                PDF
              </a>
            )}
          </div>

          <button
            onClick={handleReset}
            className="text-sm text-gray-400 hover:text-accent transition-colors flex items-center gap-1.5 mx-auto"
          >
            <RefreshCw size={14} />
            別のレポートを作成
          </button>
        </div>
      )}
    </div>
  );
}
