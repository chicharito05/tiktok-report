import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    const res = await fetch(`${workerUrl}/sync-notion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || "Notion同期に失敗しました" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      {
        error: e instanceof Error ? e.message : "Notion同期に失敗しました",
      },
      { status: 500 }
    );
  }
}
