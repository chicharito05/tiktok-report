"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Save,
  Loader2,
  RefreshCw,
  Film,
  Eye,
  Heart,
  MessageCircle,
  TrendingUp,
  Play,
  ArrowUpDown,
  SaveAll,
  Search,
  Users,
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import type { Client } from "@/lib/types";
import { useToast } from "@/components/ui/Toast";
import EmptyState from "@/components/ui/EmptyState";

interface Post {
  id: string;
  client_id: string;
  post_date: string;
  caption: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  duration: string;
  watch_through_rate: number | null;
  two_sec_view_rate: number | null;
}

interface PostsManagerProps {
  clients: Client[];
}

type SortKey = "post_date" | "views" | "likes" | "comments" | "shares";
type SortDir = "asc" | "desc";

function formatNum(n: number | null | undefined): string {
  if (n == null || n === 0) return "--";
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  return n.toLocaleString("ja-JP");
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

/** post_date を YYYY-MM-DD のinput[type=date]用に変換 */
function toDateInputValue(d: string): string {
  try {
    const date = new Date(d);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  } catch {
    return d;
  }
}

export default function PostsManager({ clients }: PostsManagerProps) {
  const [selectedClientId, setSelectedClientId] = useState("");
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [editedCells, setEditedCells] = useState<Record<string, Record<string, unknown>>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [savingAll, setSavingAll] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [selectedPostIds, setSelectedPostIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPost, setNewPost] = useState({ caption: "", post_date: new Date().toISOString().slice(0, 10) });
  const [creatingPost, setCreatingPost] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("post_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [searchQuery, setSearchQuery] = useState("");
  // フォロワー数管理
  const [showFollowerPanel, setShowFollowerPanel] = useState(false);
  const [followerSnapshots, setFollowerSnapshots] = useState<{ id?: string; date: string; follower_count: number }[]>([]);
  const [followerLoading, setFollowerLoading] = useState(false);
  const [newFollowerDate, setNewFollowerDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newFollowerCount, setNewFollowerCount] = useState("");
  const [followerSaving, setFollowerSaving] = useState(false);
  const { showToast } = useToast();

  const selectedClient = clients.find((c) => c.id === selectedClientId);
  const editedCount = Object.keys(editedCells).length;
  const hasEdits = editedCount > 0;

  // --- データ取得 ---
  const fetchPosts = useCallback(async () => {
    if (!selectedClient) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ client_slug: selectedClient.name });
      const res = await fetch(`/api/posts?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setPosts(data.posts || []);
      setEditedCells({});
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [selectedClient, showToast]);

  // --- フォロワーデータ取得 ---
  const fetchFollowerSnapshots = useCallback(async () => {
    if (!selectedClientId) return;
    setFollowerLoading(true);
    try {
      const params = new URLSearchParams({ client_id: selectedClientId });
      const res = await fetch(`/api/follower-snapshots?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setFollowerSnapshots(data.snapshots || []);
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "フォロワーデータ取得に失敗");
    } finally {
      setFollowerLoading(false);
    }
  }, [selectedClientId, showToast]);

  const handleAddFollowerSnapshot = async () => {
    if (!selectedClientId || !newFollowerDate || !newFollowerCount) return;
    setFollowerSaving(true);
    try {
      const res = await fetch("/api/follower-snapshots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: selectedClientId,
          date: newFollowerDate,
          follower_count: Number(newFollowerCount),
        }),
      });
      if (!res.ok) throw new Error((await res.json()).error);
      showToast("success", "フォロワー数を保存しました");
      setNewFollowerCount("");
      await fetchFollowerSnapshots();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setFollowerSaving(false);
    }
  };

  useEffect(() => {
    if (selectedClientId) {
      fetchPosts();
      fetchFollowerSnapshots();
    }
  }, [selectedClientId, fetchPosts, fetchFollowerSnapshots]);

  // --- Notion同期 ---
  const handleNotionSync = async () => {
    if (!selectedClient?.notion_database_id) {
      showToast("error", "Notion DB IDが未設定です");
      return;
    }
    setSyncing(true);
    try {
      const res = await fetch("/api/notion/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClient.id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail);
      showToast("success", data.message || `${data.synced}件同期しました`);
      await fetchPosts();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "同期に失敗しました");
    } finally {
      setSyncing(false);
    }
  };

  // --- セル編集 ---
  const handleCellChange = (postId: string, field: string, value: string | number | null) => {
    setEditedCells((prev) => ({
      ...prev,
      [postId]: { ...prev[postId], [field]: value },
    }));
  };

  const handleNumericChange = (postId: string, field: string, raw: string) => {
    handleCellChange(postId, field, raw === "" ? null : Number(raw));
  };

  // --- 保存 ---
  const handleSave = async (postId: string) => {
    const edits = editedCells[postId];
    if (!edits) return;
    setSaving(postId);
    try {
      const res = await fetch("/api/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post_id: postId, ...edits }),
      });
      if (!res.ok) throw new Error();
      setPosts((prev) => prev.map((p) => (p.id === postId ? { ...p, ...edits } as Post : p)));
      setEditedCells((prev) => {
        const n = { ...prev };
        delete n[postId];
        return n;
      });
      showToast("success", "保存しました");
    } catch {
      showToast("error", "保存に失敗しました");
    } finally {
      setSaving(null);
    }
  };

  const handleSaveAll = async () => {
    const entries = Object.entries(editedCells);
    if (entries.length === 0) return;
    setSavingAll(true);
    let ok = 0,
      ng = 0;
    for (const [postId, edits] of entries) {
      try {
        const res = await fetch("/api/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ post_id: postId, ...edits }),
        });
        if (!res.ok) throw new Error();
        setPosts((prev) => prev.map((p) => (p.id === postId ? { ...p, ...edits } as Post : p)));
        setEditedCells((prev) => {
          const n = { ...prev };
          delete n[postId];
          return n;
        });
        ok++;
      } catch {
        ng++;
      }
    }
    showToast(ng > 0 ? "error" : "success", ng > 0 ? `${ng}件失敗` : `${ok}件保存しました`);
    setSavingAll(false);
  };

  // --- 投稿削除 ---
  const handleDeletePost = async (postId: string, caption: string) => {
    if (!confirm(`「${caption || "（タイトルなし）"}」を削除しますか？`)) return;
    setDeleting(postId);
    try {
      const res = await fetch("/api/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", post_id: postId }),
      });
      if (!res.ok) throw new Error((await res.json()).error);
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      setEditedCells((prev) => {
        const n = { ...prev };
        delete n[postId];
        return n;
      });
      showToast("success", "削除しました");
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "削除に失敗しました");
    } finally {
      setDeleting(null);
    }
  };

  // --- 一括削除 ---
  const handleBulkDelete = async () => {
    const ids = Array.from(selectedPostIds);
    if (ids.length === 0) return;
    if (!confirm(`${ids.length}件の動画を削除しますか？この操作は取り消せません。`)) return;
    setBulkDeleting(true);
    let ok = 0, ng = 0;
    for (const postId of ids) {
      try {
        const res = await fetch("/api/posts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "delete", post_id: postId }),
        });
        if (!res.ok) throw new Error();
        ok++;
      } catch {
        ng++;
      }
    }
    setPosts((prev) => prev.filter((p) => !selectedPostIds.has(p.id)));
    setEditedCells((prev) => {
      const n = { ...prev };
      ids.forEach((id) => delete n[id]);
      return n;
    });
    setSelectedPostIds(new Set());
    showToast(ng > 0 ? "error" : "success", ng > 0 ? `${ok}件削除、${ng}件失敗` : `${ok}件削除しました`);
    setBulkDeleting(false);
  };

  const toggleSelectPost = (postId: string) => {
    setSelectedPostIds((prev) => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedPostIds.size === filteredPosts.length) {
      setSelectedPostIds(new Set());
    } else {
      setSelectedPostIds(new Set(filteredPosts.map((p) => p.id)));
    }
  };

  // --- 投稿手動追加 ---
  const handleCreatePost = async () => {
    if (!selectedClientId || !newPost.post_date) return;
    setCreatingPost(true);
    try {
      const res = await fetch("/api/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "create",
          client_id: selectedClientId,
          caption: newPost.caption,
          post_date: newPost.post_date,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      showToast("success", "投稿を追加しました");
      setNewPost({ caption: "", post_date: new Date().toISOString().slice(0, 10) });
      setShowAddForm(false);
      await fetchPosts();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "追加に失敗しました");
    } finally {
      setCreatingPost(false);
    }
  };

  // --- フォロワースナップショット削除 ---
  const handleDeleteFollowerSnapshot = async (snapshotId: string, dateLabel: string) => {
    if (!confirm(`${dateLabel} のフォロワーデータを削除しますか？`)) return;
    try {
      const res = await fetch("/api/follower-snapshots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", snapshot_id: snapshotId }),
      });
      if (!res.ok) throw new Error((await res.json()).error);
      showToast("success", "削除しました");
      await fetchFollowerSnapshots();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "削除に失敗しました");
    }
  };

  // --- ソート ---
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  // --- フィルタ + ソート ---
  const filteredPosts = useMemo(() => {
    let result = [...posts];
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter((p) => p.caption.toLowerCase().includes(q));
    }
    result.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      if (sortDir === "desc") return av > bv ? -1 : av < bv ? 1 : 0;
      return av < bv ? -1 : av > bv ? 1 : 0;
    });
    return result;
  }, [posts, searchQuery, sortKey, sortDir]);

  // --- 統計 ---
  const stats = useMemo(() => {
    if (posts.length === 0) return null;
    const totalViews = posts.reduce((s, p) => s + (p.views || 0), 0);
    const totalLikes = posts.reduce((s, p) => s + (p.likes || 0), 0);
    const totalComments = posts.reduce((s, p) => s + (p.comments || 0), 0);
    const totalShares = posts.reduce((s, p) => s + (p.shares || 0), 0);
    const avgViews = Math.round(totalViews / posts.length);
    const avgEngagement =
      totalViews > 0
        ? (((totalLikes + totalComments + totalShares) / totalViews) * 100).toFixed(2)
        : "0";
    return {
      totalViews,
      totalLikes,
      totalComments,
      totalShares,
      avgViews,
      avgEngagement,
      count: posts.length,
    };
  }, [posts]);

  // ===================== クライアント未選択 =====================
  if (!selectedClientId) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary">動画データ管理</h1>
          <p className="text-sm text-gray-400 mt-1">
            クライアントを選択して動画パフォーマンスを確認・管理
          </p>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {clients.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedClientId(c.id)}
              className="bg-white rounded-xl border border-gray-200/80 p-6 text-left card-hover group transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 gradient-accent rounded-xl flex items-center justify-center shrink-0">
                  <Film size={18} className="text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-primary group-hover:text-accent transition-colors">
                    {c.name}
                  </h3>
                  {c.tiktok_username && (
                    <p className="text-xs text-gray-400">{c.tiktok_username}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {c.notion_database_id && (
                  <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-medium">
                    Notion連携
                  </span>
                )}
                <span className="text-xs text-gray-400 ml-auto group-hover:text-accent transition-colors">
                  データを見る →
                </span>
              </div>
            </button>
          ))}
          {clients.length === 0 && (
            <div className="col-span-3">
              <EmptyState
                icon={Film}
                title="クライアントが未登録です"
                description="クライアント管理画面で追加してください"
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  // ===================== クライアント選択済み =====================
  return (
    <div className="max-w-[1400px] mx-auto">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setSelectedClientId("");
              setPosts([]);
              setEditedCells({});
            }}
            className="text-sm text-gray-400 hover:text-accent transition-colors"
          >
            ← 一覧に戻る
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 gradient-accent rounded-xl flex items-center justify-center">
              <Film size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-primary">
                {selectedClient?.name}
              </h1>
              {selectedClient?.tiktok_username && (
                <p className="text-xs text-gray-400">
                  {selectedClient.tiktok_username}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {selectedClient?.notion_database_id && (
            <button
              onClick={handleNotionSync}
              disabled={syncing}
              className="px-4 py-2.5 gradient-blue text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2 transition-opacity"
            >
              {syncing ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <RefreshCw size={15} />
              )}
              Notion同期
            </button>
          )}
          <Link
            href={`/reports/generate?client=${encodeURIComponent(selectedClient?.name || "")}`}
            className="px-4 py-2.5 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 flex items-center gap-2 transition-opacity"
          >
            <TrendingUp size={15} />
            レポート生成
          </Link>
        </div>
      </div>

      {/* ローディング */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200/80 p-16 text-center">
          <Loader2 size={28} className="animate-spin text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-400">動画データを読み込み中...</p>
        </div>
      ) : posts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200/80">
          <EmptyState
            icon={Film}
            title="動画データがありません"
            description={
              selectedClient?.notion_database_id
                ? "Notion同期を実行してデータを取り込みましょう"
                : "データ取込ページからCSVをアップロードするか、Notion連携を設定してください"
            }
            action={
              selectedClient?.notion_database_id
                ? { label: "Notion同期を実行", onClick: handleNotionSync }
                : undefined
            }
          />
        </div>
      ) : (
        <>
          {/* 統計カード */}
          {stats && (
            <div className="grid grid-cols-6 gap-3 mb-5">
              {[
                { icon: Film, label: "動画数", value: stats.count + "本", color: "text-gray-600", bg: "bg-gray-100" },
                { icon: Eye, label: "合計再生", value: formatNum(stats.totalViews), color: "text-blue-600", bg: "bg-blue-50" },
                { icon: Play, label: "平均再生", value: formatNum(stats.avgViews), color: "text-indigo-600", bg: "bg-indigo-50" },
                { icon: Heart, label: "合計いいね", value: formatNum(stats.totalLikes), color: "text-rose-600", bg: "bg-rose-50" },
                { icon: MessageCircle, label: "合計コメント", value: formatNum(stats.totalComments), color: "text-amber-600", bg: "bg-amber-50" },
                { icon: TrendingUp, label: "エンゲージ率", value: stats.avgEngagement + "%", color: "text-emerald-600", bg: "bg-emerald-50" },
              ].map((s) => (
                <div key={s.label} className="bg-white rounded-xl border border-gray-200/80 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-7 h-7 ${s.bg} rounded-lg flex items-center justify-center`}>
                      <s.icon size={14} className={s.color} />
                    </div>
                    <span className="text-[11px] text-gray-400">{s.label}</span>
                  </div>
                  <p className="text-lg font-bold text-primary tabular-nums">{s.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* フォロワー数管理パネル */}
          <div className="bg-white rounded-xl border border-gray-200/80 mb-5 overflow-hidden">
            <button
              onClick={() => setShowFollowerPanel(!showFollowerPanel)}
              className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Users size={16} className="text-blue-600" />
                <span className="text-sm font-semibold text-gray-800">
                  フォロワー数の推移
                </span>
                {followerSnapshots.length > 0 && (
                  <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-medium">
                    {followerSnapshots.length}件
                  </span>
                )}
              </div>
              {showFollowerPanel ? (
                <ChevronUp size={16} className="text-gray-400" />
              ) : (
                <ChevronDown size={16} className="text-gray-400" />
              )}
            </button>
            {showFollowerPanel && (
              <div className="px-5 pb-5 border-t border-gray-100 pt-4">
                {/* 入力フォーム */}
                <div className="flex items-end gap-3 mb-4">
                  <div>
                    <label className="block text-[11px] font-medium text-gray-500 mb-1">日付</label>
                    <input
                      type="date"
                      value={newFollowerDate}
                      onChange={(e) => setNewFollowerDate(e.target.value)}
                      className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-500 mb-1">フォロワー数</label>
                    <input
                      type="number"
                      value={newFollowerCount}
                      onChange={(e) => setNewFollowerCount(e.target.value)}
                      placeholder="例: 12500"
                      className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 w-40"
                    />
                  </div>
                  <button
                    onClick={handleAddFollowerSnapshot}
                    disabled={followerSaving || !newFollowerCount}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                  >
                    {followerSaving ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Plus size={14} />
                    )}
                    追加
                  </button>
                </div>
                {/* 履歴テーブル */}
                {followerLoading ? (
                  <div className="text-center py-4 text-gray-400 text-sm">
                    <Loader2 size={16} className="animate-spin inline mr-2" />
                    読み込み中...
                  </div>
                ) : followerSnapshots.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">
                    フォロワー数のデータがありません。上のフォームから追加してください。
                  </p>
                ) : (
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-100">
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">日付</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">フォロワー数</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">前回比</th>
                          <th className="px-2 py-2 w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {followerSnapshots.map((snap, idx) => {
                          const prev = followerSnapshots[idx + 1];
                          const diff = prev ? snap.follower_count - prev.follower_count : null;
                          return (
                            <tr key={snap.id || snap.date} className="hover:bg-gray-50/60 group">
                              <td className="px-3 py-2 text-gray-700">{snap.date}</td>
                              <td className="px-3 py-2 text-right font-medium tabular-nums">
                                {snap.follower_count.toLocaleString()}
                              </td>
                              <td className="px-3 py-2 text-right tabular-nums">
                                {diff !== null ? (
                                  <span className={diff >= 0 ? "text-emerald-600" : "text-red-500"}>
                                    {diff >= 0 ? "+" : ""}{diff.toLocaleString()}
                                  </span>
                                ) : (
                                  <span className="text-gray-300">--</span>
                                )}
                              </td>
                              <td className="px-2 py-2 text-center">
                                {snap.id && (
                                  <button
                                    onClick={() => handleDeleteFollowerSnapshot(snap.id!, snap.date)}
                                    className="p-1 text-gray-300 hover:text-red-500 rounded opacity-0 group-hover:opacity-100 transition-all"
                                    title="削除"
                                  >
                                    <Trash2 size={13} />
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 手動追加フォーム */}
          {showAddForm && (
            <div className="bg-white rounded-xl border border-gray-200/80 p-5 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Plus size={16} className="text-accent" />
                <span className="text-sm font-semibold text-gray-800">動画を手動で追加</span>
              </div>
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="block text-[11px] font-medium text-gray-500 mb-1">タイトル</label>
                  <input
                    type="text"
                    value={newPost.caption}
                    onChange={(e) => setNewPost((p) => ({ ...p, caption: e.target.value }))}
                    placeholder="動画のタイトルを入力..."
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-500 mb-1">投稿日</label>
                  <input
                    type="date"
                    value={newPost.post_date}
                    onChange={(e) => setNewPost((p) => ({ ...p, post_date: e.target.value }))}
                    className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                  />
                </div>
                <button
                  onClick={handleCreatePost}
                  disabled={creatingPost || !newPost.post_date}
                  className="px-4 py-2 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 transition-opacity"
                >
                  {creatingPost ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Plus size={14} />
                  )}
                  追加
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 border border-gray-200 text-gray-500 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  キャンセル
                </button>
              </div>
              <p className="text-[10px] text-gray-400 mt-2">
                ※ 再生数・いいね等の数値は追加後にテーブルで入力できます
              </p>
            </div>
          )}

          {/* 一括削除バー */}
          {selectedPostIds.size > 0 && (
            <div className="flex items-center gap-3 mb-4 bg-red-50 border border-red-200 rounded-xl px-5 py-3">
              <input
                type="checkbox"
                checked={selectedPostIds.size === filteredPosts.length}
                onChange={toggleSelectAll}
                className="w-4 h-4 accent-red-500"
              />
              <span className="text-sm font-medium text-red-700">
                {selectedPostIds.size}件選択中
              </span>
              <button
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
              >
                {bulkDeleting ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Trash2 size={13} />
                )}
                {bulkDeleting ? "削除中..." : `${selectedPostIds.size}件を一括削除`}
              </button>
              <button
                onClick={() => setSelectedPostIds(new Set())}
                className="px-3 py-2 text-red-600 text-xs font-medium hover:bg-red-100 rounded-lg transition-colors"
              >
                選択解除
              </button>
            </div>
          )}

          {/* 検索バー + 追加 + 一括保存 */}
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1 max-w-xs">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="タイトルで検索..."
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
            </div>
            <span className="text-xs text-gray-400">
              {filteredPosts.length}件表示 / 全{posts.length}件
            </span>
            <div className="ml-auto flex items-center gap-3">
              {!showAddForm && (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="px-3 py-2 border border-gray-200 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50 flex items-center gap-1.5 transition-colors"
                >
                  <Plus size={13} />
                  手動追加
                </button>
              )}
              {hasEdits && (
                <>
                  <span className="text-xs text-accent font-medium">
                    {editedCount}件の未保存
                  </span>
                  <button
                    onClick={handleSaveAll}
                    disabled={savingAll}
                    className="px-4 py-2 gradient-accent text-white rounded-lg text-xs font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 transition-opacity"
                  >
                    {savingAll ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <SaveAll size={13} />
                    )}
                    すべて保存
                  </button>
                </>
              )}
            </div>
          </div>

          {/* テーブル（横スクロール対応） */}
          <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="text-sm" style={{ minWidth: "1200px", width: "100%" }}>
                <thead>
                  <tr className="bg-gray-50/80 border-b border-gray-100">
                    <th className="pl-4 pr-1 py-3 w-10">
                      <input
                        type="checkbox"
                        checked={selectedPostIds.size > 0 && selectedPostIds.size === filteredPosts.length}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 accent-accent rounded"
                      />
                    </th>
                    <th className="px-5 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "400px" }}>
                      タイトル
                    </th>
                    <th className="px-3 py-3 text-center font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "150px" }}>
                      <SortLabel label="投稿日" sortKey="post_date" current={sortKey} dir={sortDir} onClick={toggleSort} />
                    </th>
                    <th className="px-3 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "130px" }}>
                      <SortLabel label="再生数" sortKey="views" current={sortKey} dir={sortDir} onClick={toggleSort} />
                    </th>
                    <th className="px-3 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "110px" }}>
                      <SortLabel label="いいね" sortKey="likes" current={sortKey} dir={sortDir} onClick={toggleSort} />
                    </th>
                    <th className="px-3 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "110px" }}>
                      <SortLabel label="コメント" sortKey="comments" current={sortKey} dir={sortDir} onClick={toggleSort} />
                    </th>
                    <th className="px-3 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "110px" }}>
                      <SortLabel label="シェア" sortKey="shares" current={sortKey} dir={sortDir} onClick={toggleSort} />
                    </th>
                    <th className="px-3 py-3 text-center font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "110px" }}>
                      視聴完了率
                    </th>
                    <th className="px-3 py-3 text-center font-medium text-gray-500 text-xs uppercase tracking-wider" style={{ minWidth: "110px" }}>
                      2秒視聴率
                    </th>
                    <th className="px-2 py-3 w-20"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredPosts.map((post) => {
                    const edits = editedCells[post.id] || {};
                    const rowEdited = Object.keys(edits).length > 0;
                    return (
                      <tr
                        key={post.id}
                        className={`transition-colors ${
                          selectedPostIds.has(post.id)
                            ? "bg-red-50/50"
                            : rowEdited
                            ? "bg-accent/[0.03]"
                            : "hover:bg-gray-50/60"
                        }`}
                      >
                        {/* チェックボックス */}
                        <td className="pl-4 pr-1 py-2">
                          <input
                            type="checkbox"
                            checked={selectedPostIds.has(post.id)}
                            onChange={() => toggleSelectPost(post.id)}
                            className="w-4 h-4 accent-accent rounded"
                          />
                        </td>
                        {/* タイトル（編集可能） */}
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            defaultValue={post.caption}
                            onChange={(e) =>
                              handleCellChange(post.id, "caption", e.target.value)
                            }
                            className="w-full px-3 py-2 text-sm font-medium text-gray-800 border border-gray-200 rounded-lg cell-input bg-transparent hover:border-gray-300"
                            placeholder="タイトルを入力"
                          />
                        </td>
                        {/* 投稿日（編集可能） */}
                        <td className="px-3 py-2">
                          <input
                            type="date"
                            defaultValue={toDateInputValue(post.post_date)}
                            onChange={(e) =>
                              handleCellChange(post.id, "post_date", e.target.value)
                            }
                            className="w-full px-2 py-2 text-sm text-center border border-gray-200 rounded-lg cell-input bg-transparent hover:border-gray-300"
                          />
                        </td>
                        {/* 数値入力（再生数・いいね・コメント・シェア） */}
                        {(["views", "likes", "comments", "shares"] as const).map(
                          (field) => (
                            <td key={field} className="px-3 py-2">
                              <input
                                type="number"
                                defaultValue={
                                  (post[field] as number) ?? ""
                                }
                                onChange={(e) =>
                                  handleNumericChange(
                                    post.id,
                                    field,
                                    e.target.value
                                  )
                                }
                                className="w-full px-3 py-2 text-right text-sm border border-gray-200 rounded-lg cell-input tabular-nums bg-transparent hover:border-gray-300"
                                placeholder="--"
                              />
                            </td>
                          )
                        )}
                        {/* 率 */}
                        {(
                          ["watch_through_rate", "two_sec_view_rate"] as const
                        ).map((field) => (
                          <td key={field} className="px-3 py-2">
                            <input
                              type="number"
                              step="0.1"
                              defaultValue={
                                (post[field] as number) ?? ""
                              }
                              onChange={(e) =>
                                handleNumericChange(
                                  post.id,
                                  field,
                                  e.target.value
                                )
                              }
                              className="w-full px-3 py-2 text-center text-sm border border-gray-200 rounded-lg cell-input tabular-nums bg-transparent hover:border-gray-300"
                              placeholder="--"
                            />
                          </td>
                        ))}
                        {/* アクション */}
                        <td className="px-2 py-2">
                          <div className="flex items-center justify-center gap-0.5">
                            {rowEdited && (
                              <button
                                onClick={() => handleSave(post.id)}
                                disabled={saving === post.id}
                                className="p-1.5 text-accent hover:bg-accent/10 rounded-lg disabled:opacity-50 transition-colors"
                                title="保存"
                              >
                                {saving === post.id ? (
                                  <Loader2 size={15} className="animate-spin" />
                                ) : (
                                  <Save size={15} />
                                )}
                              </button>
                            )}
                            <button
                              onClick={() => handleDeletePost(post.id, post.caption)}
                              disabled={deleting === post.id}
                              className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg disabled:opacity-50 transition-colors"
                              title="削除"
                            >
                              {deleting === post.id ? (
                                <Loader2 size={15} className="animate-spin" />
                              ) : (
                                <Trash2 size={15} />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/** ソートラベル */
function SortLabel({
  label,
  sortKey: key,
  current,
  dir,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onClick: (key: SortKey) => void;
}) {
  const isActive = current === key;
  return (
    <button
      onClick={() => onClick(key)}
      className={`inline-flex items-center gap-1 select-none transition-colors ${
        isActive ? "text-accent" : "text-gray-500 hover:text-gray-700"
      }`}
    >
      {label}
      {isActive && (
        <ArrowUpDown size={11} className={dir === "asc" ? "rotate-180" : ""} />
      )}
    </button>
  );
}
