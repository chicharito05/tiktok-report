"use client";

import { useState, useRef } from "react";
import {
  ImageIcon,
  CheckCircle,
  AlertCircle,
  Loader2,
  Save,
} from "lucide-react";
import type { Client, ScreenshotPost } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface ScreenshotUploaderProps {
  clients: Client[];
}

export default function ScreenshotUploader({
  clients,
}: ScreenshotUploaderProps) {
  const [selectedClient, setSelectedClient] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [posts, setPosts] = useState<ScreenshotPost[]>([]);
  const [result, setResult] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const newFiles = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleAnalyze = async () => {
    if (!selectedClient || files.length === 0) return;
    setLoading(true);
    setResult(null);
    setPosts([]);

    try {
      const allPosts: ScreenshotPost[] = [];

      for (const file of files) {
        const formData = new FormData();
        formData.append("client_slug", selectedClient);
        formData.append("file", file);

        const res = await fetch("/api/upload/screenshot", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "解析に失敗しました");
        allPosts.push(...data.posts);
      }

      setPosts(allPosts);
      setResult({
        type: "success",
        message: `${allPosts.length}件の投稿を検出しました`,
      });
    } catch (e) {
      setResult({
        type: "error",
        message: e instanceof Error ? e.message : "エラーが発生しました",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedClient || posts.length === 0) return;
    setSaving(true);

    try {
      const res = await fetch("/api/upload/screenshot", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_slug: selectedClient,
          posts,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "保存に失敗しました");

      setResult({
        type: "success",
        message: data.message || `${posts.length}件の投稿を保存しました`,
      });
      setPosts([]);
      setFiles([]);
    } catch (e) {
      setResult({
        type: "error",
        message: e instanceof Error ? e.message : "保存に失敗しました",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          クライアント
        </label>
        <select
          value={selectedClient}
          onChange={(e) => setSelectedClient(e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
        >
          <option value="">選択してください</option>
          {clients.map((c) => (
            <option key={c.id} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-accent/50 transition-colors"
      >
        <ImageIcon size={32} className="mx-auto text-gray-400 mb-2" />
        {files.length > 0 ? (
          <p className="text-sm font-medium text-primary">
            {files.length}枚の画像を選択中
          </p>
        ) : (
          <>
            <p className="text-sm text-gray-500">
              スクリーンショットをドラッグ＆ドロップ
            </p>
            <p className="text-xs text-gray-400 mt-1">
              複数枚対応（PNG, JPG）
            </p>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) =>
            setFiles(Array.from(e.target.files || []))
          }
          className="hidden"
        />
      </div>

      <button
        onClick={handleAnalyze}
        disabled={!selectedClient || files.length === 0 || loading}
        className="w-full bg-accent text-white py-2.5 rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading && <Loader2 size={16} className="animate-spin" />}
        {loading ? "解析中..." : "解析・取込"}
      </button>

      {/* 解析結果プレビュー */}
      {posts.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="p-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              解析結果（{posts.length}件）
            </span>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1 px-3 py-1.5 bg-sub text-white rounded-lg text-sm hover:bg-sub/90 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Save size={14} />
              )}
              確定して保存
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">
                    投稿日
                  </th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">
                    キャプション
                  </th>
                  <th className="text-right py-2 px-3 text-gray-500 font-medium">
                    再生数
                  </th>
                  <th className="text-right py-2 px-3 text-gray-500 font-medium">
                    いいね
                  </th>
                  <th className="text-right py-2 px-3 text-gray-500 font-medium">
                    コメント
                  </th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post, i) => (
                  <tr key={i} className="border-b border-gray-50">
                    <td className="py-2 px-3">{post.post_date}</td>
                    <td className="py-2 px-3 max-w-[200px] truncate">
                      {post.caption}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {formatNumber(post.views)}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {formatNumber(post.likes)}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {formatNumber(post.comments)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            result.type === "success"
              ? "bg-green-50 text-green-700"
              : "bg-red-50 text-red-600"
          }`}
        >
          {result.type === "success" ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          {result.message}
        </div>
      )}
    </div>
  );
}
