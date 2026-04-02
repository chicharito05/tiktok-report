"use client";

import { useState, useRef } from "react";
import { Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import type { Client } from "@/lib/types";

interface CsvUploaderProps {
  clients: Client[];
  csvType?: "overview" | "posts";
}

export default function CsvUploader({ clients, csvType }: CsvUploaderProps) {
  const [selectedClient, setSelectedClient] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".csv")) {
      setFile(f);
    }
  };

  const handleSubmit = async () => {
    if (!selectedClient || !file) return;
    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("client_slug", selectedClient);
      formData.append("year", String(year));
      formData.append("file", file);
      if (csvType) {
        formData.append("csv_type", csvType);
      }

      const res = await fetch("/api/upload/csv", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "取り込みに失敗しました");

      setResult({
        type: "success",
        message: data.message || `${data.rows_imported}件のデータを取り込みました`,
      });
      setFile(null);
    } catch (e) {
      setResult({
        type: "error",
        message: e instanceof Error ? e.message : "エラーが発生しました",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            クライアント
          </label>
          <select
            value={selectedClient}
            onChange={(e) => setSelectedClient(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
          >
            <option value="">選択してください</option>
            {clients.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            年
          </label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
          />
        </div>
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-accent/50 transition-colors"
      >
        <Upload size={32} className="mx-auto text-gray-400 mb-2" />
        {file ? (
          <p className="text-sm font-medium text-primary">{file.name}</p>
        ) : (
          <>
            <p className="text-sm text-gray-500">
              CSVファイルをドラッグ＆ドロップ
            </p>
            <p className="text-xs text-gray-400 mt-1">
              またはクリックして選択
            </p>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="hidden"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={!selectedClient || !file || loading}
        className="w-full bg-accent text-white py-2.5 rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading && <Loader2 size={16} className="animate-spin" />}
        取り込み
      </button>

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
