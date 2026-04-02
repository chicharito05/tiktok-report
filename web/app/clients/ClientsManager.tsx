"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, X, Check, Loader2, Users } from "lucide-react";
import type { Client } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { useToast } from "@/components/ui/Toast";
import EmptyState from "@/components/ui/EmptyState";

interface ClientsManagerProps {
  initialClients: Client[];
}

export default function ClientsManager({
  initialClients,
}: ClientsManagerProps) {
  const [clients, setClients] = useState(initialClients);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newNotionDbId, setNewNotionDbId] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editUsername, setEditUsername] = useState("");
  const [editNotionDbId, setEditNotionDbId] = useState("");
  const [loading, setLoading] = useState(false);
  const supabase = createClient();
  const { showToast } = useToast();

  const handleAdd = async () => {
    if (!newName.trim()) return;
    setLoading(true);

    try {
      const { data, error } = await supabase
        .from("clients")
        .insert({
          name: newName.trim(),
          tiktok_username: newUsername.trim() || null,
          notion_database_id: newNotionDbId.trim() || null,
        })
        .select()
        .single<Client>();

      if (error) throw error;
      if (data) {
        setClients((prev) =>
          [...prev, data].sort((a, b) => a.name.localeCompare(b.name))
        );
      }
      setNewName("");
      setNewUsername("");
      setNewNotionDbId("");
      setShowAdd(false);
      showToast("success", "クライアントを追加しました");
    } catch {
      showToast("error", "追加に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (id: string) => {
    setLoading(true);
    try {
      const { error } = await supabase
        .from("clients")
        .update({
          name: editName.trim(),
          tiktok_username: editUsername.trim() || null,
          notion_database_id: editNotionDbId.trim() || null,
        })
        .eq("id", id);

      if (error) throw error;
      setClients((prev) =>
        prev.map((c) =>
          c.id === id
            ? {
                ...c,
                name: editName.trim(),
                tiktok_username: editUsername.trim() || null,
                notion_database_id: editNotionDbId.trim() || null,
              }
            : c
        )
      );
      setEditingId(null);
      showToast("success", "更新しました");
    } catch {
      showToast("error", "更新に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (
      !confirm(
        "このクライアントを削除しますか？関連するデータもすべて削除されます。"
      )
    )
      return;

    try {
      const { error } = await supabase.from("clients").delete().eq("id", id);
      if (error) throw error;
      setClients((prev) => prev.filter((c) => c.id !== id));
      showToast("success", "クライアントを削除しました");
    } catch {
      showToast("error", "削除に失敗しました");
    }
  };

  const startEdit = (client: Client) => {
    setEditingId(client.id);
    setEditName(client.name);
    setEditUsername(client.tiktok_username || "");
    setEditNotionDbId(client.notion_database_id || "");
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200/80 overflow-hidden">
      {/* ヘッダー */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={16} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-600">
            {clients.length}件のクライアント
          </span>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Plus size={15} />
          新規追加
        </button>
      </div>

      {/* 追加フォーム */}
      {showAdd && (
        <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/50">
          <p className="text-xs font-medium text-gray-500 mb-3">
            新しいクライアントを追加
          </p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                クライアント名 *
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="例: クライアント名"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                TikTokアカウント
              </label>
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder="例: @tiktok_account"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 flex items-center gap-1">
                Notion DB ID
                <span className="relative group">
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-gray-300 text-[10px] text-gray-400 cursor-help">?</span>
                  <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-64 bg-gray-800 text-white text-[11px] leading-relaxed rounded-lg px-3 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none shadow-lg">
                    NotionでDBを開き、URLの末尾にある32文字のIDをコピーしてください。<br />
                    例: notion.so/.../<span className="text-accent font-mono">1d5b2cec5aaf...</span>
                  </span>
                </span>
              </label>
              <input
                type="text"
                value={newNotionDbId}
                onChange={(e) => setNewNotionDbId(e.target.value)}
                placeholder="例: 1d5b2cec-5aaf-81d9-..."
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent font-mono text-xs"
              />
            </div>
          </div>
          <div className="flex items-center gap-2 mt-3 justify-end">
            <button
              onClick={() => setShowAdd(false)}
              className="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
            >
              キャンセル
            </button>
            <button
              onClick={handleAdd}
              disabled={!newName.trim() || loading}
              className="px-4 py-2 gradient-accent text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 transition-opacity"
            >
              {loading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Check size={14} />
              )}
              追加
            </button>
          </div>
        </div>
      )}

      {/* テーブル */}
      {clients.length > 0 ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50/50 border-b border-gray-100">
              <th className="text-left py-3 px-5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                クライアント名
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                TikTokアカウント
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Notion DB ID
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">
                登録日
              </th>
              <th className="py-3 px-4 w-24"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {clients.map((client) => (
              <tr
                key={client.id}
                className="hover:bg-gray-50/60 transition-colors"
              >
                {editingId === client.id ? (
                  <>
                    <td className="py-2 px-5">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
                      />
                    </td>
                    <td className="py-2 px-4">
                      <input
                        type="text"
                        value={editUsername}
                        onChange={(e) => setEditUsername(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
                      />
                    </td>
                    <td className="py-2 px-4">
                      <input
                        type="text"
                        value={editNotionDbId}
                        onChange={(e) => setEditNotionDbId(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 font-mono text-xs"
                      />
                    </td>
                    <td className="py-2 px-4 text-gray-400 text-xs">
                      {formatDate(client.created_at)}
                    </td>
                    <td className="py-2 px-4">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleEdit(client.id)}
                          disabled={loading}
                          className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                        >
                          <Check size={15} />
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                          <X size={15} />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="py-3.5 px-5">
                      <span className="font-medium text-gray-800">
                        {client.name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-gray-500">
                      {client.tiktok_username || (
                        <span className="text-gray-300">--</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {client.notion_database_id ? (
                        <span
                          className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded cursor-help"
                          title={client.notion_database_id}
                        >
                          {client.notion_database_id.substring(0, 16)}...
                        </span>
                      ) : (
                        <span className="text-gray-300 text-xs">未設定</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-gray-400 text-xs">
                      {formatDate(client.created_at)}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-0.5">
                        <button
                          onClick={() => startEdit(client)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="編集"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(client.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="削除"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <EmptyState
          icon={Users}
          title="クライアントが未登録です"
          description="「新規追加」ボタンからクライアントを登録してください"
          action={{ label: "新規追加", onClick: () => setShowAdd(true) }}
        />
      )}
    </div>
  );
}
