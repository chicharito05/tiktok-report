import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const clientSlug = searchParams.get("client_slug");
  const startDate = searchParams.get("start_date");
  const endDate = searchParams.get("end_date");

  if (!clientSlug) {
    return NextResponse.json(
      { error: "client_slugを指定してください" },
      { status: 400 }
    );
  }

  try {
    const workerUrl = getWorkerApiUrl();
    const params = new URLSearchParams({ client_slug: clientSlug });
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    const res = await fetch(`${workerUrl}/posts?${params}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: err.detail || "取得に失敗しました" },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json(
      { error: "Worker APIに接続できません" },
      { status: 502 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    // action フィールドでルーティング
    const action = body.action;
    let endpoint = "/update-post";
    if (action === "create") {
      endpoint = "/create-post";
    } else if (action === "delete") {
      endpoint = "/delete-post";
    }

    // action フィールドは Worker に送らない
    const { action: _, ...payload } = body;

    const res = await fetch(`${workerUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: err.detail || "操作に失敗しました" },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json(
      { error: "Worker APIに接続できません" },
      { status: 502 }
    );
  }
}
