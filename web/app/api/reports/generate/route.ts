import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { client_slug, start_date, end_date, user_commentary } = body;

    if (!client_slug) {
      return NextResponse.json(
        { error: "クライアントを指定してください" },
        { status: 400 }
      );
    }

    const workerUrl = getWorkerApiUrl();
    const res = await fetch(`${workerUrl}/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_slug, start_date, end_date, user_commentary }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "レポート生成に失敗しました" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("レポート生成APIエラー:", error);
    return NextResponse.json(
      {
        error:
          "Worker APIに接続できません。Mac miniのWorkerサーバーが起動しているか確認してください。",
      },
      { status: 502 }
    );
  }
}
