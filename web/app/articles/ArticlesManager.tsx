"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  RefreshCw,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Search,
  FileText,
} from "lucide-react";
import Link from "next/link";
import type { Client } from "@/lib/types";
import { useToast } from "@/components/ui/Toast";
import EmptyState from "@/components/ui/EmptyState";

interface Article {
  caption: string;
  post_date: string;
  notion_content: string | null;
}

interface ArticlesManagerProps {
  clients: Client[];
}

function formatPostDate(d: string): string {
  try {
    const date = new Date(d);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return d;
  }
}

export default function ArticlesManager({ clients }: ArticlesManagerProps) {
  const [selectedClientId, setSelectedClientId] = useState("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const { showToast } = useToast();

  const fetchArticles = useCallback(async () => {
    if (!selectedClientId) return;
    setLoading(true);
    try {
      const res = await fetch(
        `/api/notion/articles?client_id=${selectedClientId}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setArticles(data.articles || []);
    } catch (e) {
      showToast(
        "error",
        e instanceof Error ? e.message : "原稿の取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, [selectedClientId, showToast]);

  useEffect(() => {
    if (selectedClientId) {
      fetchArticles();
    } else {
      setArticles([]);
    }
  }, [selectedClientId, fetchArticles]);

  const handleSync = async () => {
    if (!selectedClientId) return;
    setSyncing(true);
    try {
      const res = await fetch("/api/notion/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClientId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      showToast("success", data.message || "同期完了");
      await fetchArticles();
    } catch (e) {
      showToast(
        "error",
        e instanceof Error ? e.message : "同期に失敗しました"
      );
    } finally {
      setSyncing(false);
    }
  };

  const filteredArticles = articles.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.caption.toLowerCase().includes(q) ||
      (a.notion_content || "").toLowerCase().includes(q)
    );
  });

  const articlesWithContent = filteredArticles.filter(
    (a) => a.notion_content
  );
  const articlesWithoutContent = filteredArticles.filter(
    (a) => !a.notion_content
  );

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen size={24} />
          原稿一覧
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Notionから取得した原稿の本文を確認できます。レポート生成時にAI分析に活用されます。
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedClientId}
            onChange={(e) => {
              setSelectedClientId(e.target.value);
              setExpandedIndex(null);
            }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-accent/20 focus:border-accent"
          >
            <option value="">クライアントを選択</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {selectedClientId && (
            <>
              <div className="relative flex-1 max-w-xs">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                />
                <input
                  type="text"
                  placeholder="タイトル・本文で検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-accent/20 focus:border-accent"
                />
              </div>

              <button
                onClick={handleSync}
                disabled={syncing}
                className="ml-auto flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                {syncing ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <RefreshCw size={16} />
                )}
                Notion同期（本文取得）
              </button>
            </>
          )}
        </div>

        {selectedClientId && articles.length > 0 && (
          <div className="flex gap-4 mt-3 text-xs text-gray-500">
            <span>全 {filteredArticles.length} 件</span>
            <span>本文あり: {articlesWithContent.length} 件</span>
            <span>本文なし: {articlesWithoutContent.length} 件</span>
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-accent" />
          <span className="ml-2 text-sm text-gray-500">読み込み中...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && selectedClientId && articles.length === 0 && (
        <EmptyState
          icon={BookOpen}
          title="原稿データがありません"
          description="Notion同期を実行して原稿データを取得してください。"
          action={{ label: "Notion同期", onClick: handleSync }}
        />
      )}

      {/* No client selected */}
      {!selectedClientId && (
        <EmptyState
          icon={FileText}
          title="クライアントを選択してください"
          description="上のプルダウンからクライアントを選択すると、原稿一覧が表示されます。"
        />
      )}

      {/* Articles list */}
      {!loading && filteredArticles.length > 0 && (
        <div className="space-y-3">
          {filteredArticles.map((article, idx) => {
            const isExpanded = expandedIndex === idx;
            const hasContent = !!article.notion_content;

            return (
              <div
                key={`${article.caption}-${article.post_date}`}
                className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden"
              >
                {/* Article header */}
                <button
                  onClick={() =>
                    setExpandedIndex(isExpanded ? null : idx)
                  }
                  className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
                >
                  <div
                    className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      hasContent ? "bg-green-400" : "bg-gray-300"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {article.caption || "(無題)"}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {article.post_date
                        ? formatPostDate(article.post_date)
                        : "日付なし"}
                      {hasContent && (
                        <span className="ml-2 text-green-600">
                          本文あり
                        </span>
                      )}
                      {!hasContent && (
                        <span className="ml-2 text-gray-400">
                          本文未取得
                        </span>
                      )}
                    </p>
                  </div>
                  {isExpanded ? (
                    <ChevronUp size={18} className="text-gray-400" />
                  ) : (
                    <ChevronDown size={18} className="text-gray-400" />
                  )}
                </button>

                {/* Article content */}
                {isExpanded && (
                  <div className="px-5 pb-4 border-t border-gray-100">
                    {hasContent ? (
                      <pre className="mt-3 text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                        {article.notion_content}
                      </pre>
                    ) : (
                      <p className="mt-3 text-sm text-gray-400 italic">
                        本文が取得されていません。「Notion同期（本文取得）」ボタンを押して取得してください。
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
