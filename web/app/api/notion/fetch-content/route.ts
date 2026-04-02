import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    const controller = new AbortController();
    // 原稿本文取得はレート制限対応で時間がかかるため、10分のタイムアウト
    const timeout = setTimeout(() => controller.abort(), 600000);

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
    return NextResponse.json(
      {
        error:
          e instanceof Error ? e.message : "原稿本文の取得に失敗しました",
      },
      { status: 500 }
    );
  }
}
