import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    const res = await fetch(`${workerUrl}/sync-notion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || "Notion同期に失敗しました" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (e) {
    const msg =
      e instanceof DOMException && e.name === "AbortError"
        ? "Worker APIがタイムアウトしました。Railwayの状態を確認してください。"
        : e instanceof Error
          ? `Worker API接続エラー: ${e.message}`
          : "Notion同期に失敗しました";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
