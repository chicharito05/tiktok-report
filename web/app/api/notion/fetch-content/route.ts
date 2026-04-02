import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export const maxDuration = 300; // Vercel Pro: 最大5分

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    const controller = new AbortController();
    // 原稿本文取得はレート制限対応で時間がかかる（最大5分）
    const timeout = setTimeout(() => controller.abort(), 300000);

    const res = await fetch(`${workerUrl}/fetch-notion-content`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || "原稿本文の取得に失敗しました" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (e) {
    const msg =
      e instanceof DOMException && e.name === "AbortError"
        ? "原稿取得がタイムアウトしました。再度お試しください（差分取得のため、途中まで取得済みの分は保持されます）。"
        : e instanceof Error
          ? `Worker API接続エラー: ${e.message}`
          : "原稿本文の取得に失敗しました";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
