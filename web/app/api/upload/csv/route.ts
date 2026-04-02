import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const clientSlug = formData.get("client_slug");
    const year = formData.get("year");
    const file = formData.get("file");
    const csvType = formData.get("csv_type"); // "overview" | "posts" | null

    if (!clientSlug || !year || !file) {
      return NextResponse.json(
        { error: "クライアント、年、CSVファイルを指定してください" },
        { status: 400 }
      );
    }

    // Worker APIにフォワード
    const workerUrl = getWorkerApiUrl();
    const workerForm = new FormData();
    workerForm.append("client_slug", clientSlug as string);
    workerForm.append("year", year as string);
    workerForm.append("file", file as Blob);
    if (csvType) {
      workerForm.append("csv_type", csvType as string);
    }

    const res = await fetch(`${workerUrl}/upload-csv`, {
      method: "POST",
      body: workerForm,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "CSV取り込みに失敗しました" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("CSVアップロードAPIエラー:", error);
    return NextResponse.json(
      { error: "Worker APIに接続できません" },
      { status: 502 }
    );
  }
}
