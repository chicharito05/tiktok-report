import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const clientSlug = formData.get("client_slug");
    const file = formData.get("file");

    if (!clientSlug || !file) {
      return NextResponse.json(
        { error: "クライアントと画像ファイルを指定してください" },
        { status: 400 }
      );
    }

    // Worker APIにフォワード
    const workerUrl = getWorkerApiUrl();
    const workerForm = new FormData();
    workerForm.append("client_slug", clientSlug as string);
    workerForm.append("file", file as Blob);

    const res = await fetch(`${workerUrl}/upload-screenshot`, {
      method: "POST",
      body: workerForm,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "スクショ解析に失敗しました" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("スクショ解析APIエラー:", error);
    return NextResponse.json(
      { error: "Worker APIに接続できません" },
      { status: 502 }
    );
  }
}

/** 解析済み投稿データをDBに保存する */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { client_slug, posts } = body;

    if (!client_slug || !posts) {
      return NextResponse.json(
        { error: "クライアントと投稿データを指定してください" },
        { status: 400 }
      );
    }

    const workerUrl = getWorkerApiUrl();
    const formData = new FormData();
    formData.append("client_slug", client_slug);
    formData.append("posts_json", JSON.stringify(posts));

    const res = await fetch(`${workerUrl}/save-posts`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "保存に失敗しました" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("投稿保存APIエラー:", error);
    return NextResponse.json(
      { error: "Worker APIに接続できません" },
      { status: 502 }
    );
  }
}
