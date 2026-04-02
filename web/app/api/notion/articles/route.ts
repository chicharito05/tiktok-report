import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const clientId = searchParams.get("client_id");
    const startDate = searchParams.get("start_date");
    const endDate = searchParams.get("end_date");

    if (!clientId) {
      return NextResponse.json(
        { error: "client_id は必須です" },
        { status: 400 }
      );
    }

    const workerUrl = getWorkerApiUrl();
    const params = new URLSearchParams({ client_id: clientId });
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);

    const res = await fetch(`${workerUrl}/notion-articles?${params}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || "原稿一覧の取得に失敗しました" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      {
        error:
          e instanceof Error ? e.message : "原稿一覧の取得に失敗しました",
      },
      { status: 500 }
    );
  }
}
