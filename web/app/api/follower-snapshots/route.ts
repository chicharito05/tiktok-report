import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const clientId = searchParams.get("client_id");
  const startDate = searchParams.get("start_date");
  const endDate = searchParams.get("end_date");

  if (!clientId) {
    return NextResponse.json(
      { error: "client_idを指定してください" },
      { status: 400 }
    );
  }

  try {
    const workerUrl = getWorkerApiUrl();
    const params = new URLSearchParams({ client_id: clientId });
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    const res = await fetch(`${workerUrl}/follower-snapshots?${params}`);
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

    // action で分岐
    if (body.action === "delete") {
      const res = await fetch(`${workerUrl}/delete-follower-snapshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot_id: body.snapshot_id }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return NextResponse.json(
          { error: err.detail || "削除に失敗しました" },
          { status: res.status }
        );
      }
      return NextResponse.json(await res.json());
    }

    // bulkかsingleか判定
    const endpoint = body.snapshots
      ? "/follower-snapshots/bulk"
      : "/follower-snapshots";

    const res = await fetch(`${workerUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: err.detail || "保存に失敗しました" },
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
