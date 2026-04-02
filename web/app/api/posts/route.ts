import { NextRequest, NextResponse } from "next/server";
import { getWorkerApiUrl } from "@/lib/utils";
import { createServerSupabaseClient } from "@/lib/supabase/server";

/**
 * GET: 投稿一覧取得 — Supabase直接アクセス（高速）
 *
 * notion_content はフルテキストを返さず、存在有無のフラグだけ返す。
 * フルテキストが必要な場合は ?include_content=true を指定する。
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const clientSlug = searchParams.get("client_slug");
  const startDate = searchParams.get("start_date");
  const endDate = searchParams.get("end_date");
  const includeContent = searchParams.get("include_content") === "true";

  if (!clientSlug) {
    return NextResponse.json(
      { error: "client_slugを指定してください" },
      { status: 400 }
    );
  }

  try {
    const supabase = await createServerSupabaseClient();

    // クライアントID解決
    const { data: client, error: clientError } = await supabase
      .from("clients")
      .select("id")
      .eq("name", clientSlug)
      .single();

    if (clientError || !client) {
      return NextResponse.json(
        { error: "クライアントが見つかりません" },
        { status: 404 }
      );
    }

    // 投稿データ取得
    let query = supabase
      .from("posts")
      .select("*")
      .eq("client_id", client.id)
      .order("post_date", { ascending: false });

    if (startDate) query = query.gte("post_date", startDate);
    if (endDate) query = query.lte("post_date", endDate + "T23:59:59");

    const { data: posts, error: postsError } = await query;

    if (postsError) {
      return NextResponse.json(
        { error: postsError.message },
        { status: 500 }
      );
    }

    // notion_content をフラグに変換してレスポンスサイズを削減
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const processedPosts = (posts || []).map((p: any) => {
      const hasContent = !!p.notion_content;
      return {
        ...p,
        has_notion_content: hasContent,
        notion_content: includeContent ? p.notion_content : null,
      };
    });

    return NextResponse.json({ posts: processedPosts });
  } catch (e) {
    console.error("Posts GET error:", e);
    return NextResponse.json(
      { error: "データの取得に失敗しました" },
      { status: 500 }
    );
  }
}

/**
 * POST: 投稿の作成・更新・削除 — Worker API経由
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const workerUrl = getWorkerApiUrl();

    const action = body.action;
    let endpoint = "/update-post";
    if (action === "create") {
      endpoint = "/create-post";
    } else if (action === "delete") {
      endpoint = "/delete-post";
    }

    const { action: _, ...payload } = body;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const res = await fetch(`${workerUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: err.detail || "操作に失敗しました" },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch {
    // Worker APIが落ちている場合のフォールバック: Supabase直接操作
    try {
      const body = await request.clone().json();
      const action = body.action;
      const supabase = await createServerSupabaseClient();

      if (action === "delete" && body.post_id) {
        const { error } = await supabase
          .from("posts")
          .delete()
          .eq("id", body.post_id);
        if (error) throw error;
        return NextResponse.json({ message: "削除しました" });
      }

      if (action === "create") {
        const { error } = await supabase.from("posts").insert({
          client_id: body.client_id,
          caption: body.caption || "",
          post_date: body.post_date,
        });
        if (error) throw error;
        return NextResponse.json({ message: "作成しました" });
      }

      // update
      if (body.post_id) {
        const { post_id, ...updates } = body;
        delete updates.action;
        const { error } = await supabase
          .from("posts")
          .update(updates)
          .eq("id", post_id);
        if (error) throw error;
        return NextResponse.json({ message: "更新しました" });
      }

      return NextResponse.json(
        { error: "Worker APIに接続できません" },
        { status: 502 }
      );
    } catch (fallbackError) {
      console.error("Fallback error:", fallbackError);
      return NextResponse.json(
        { error: "操作に失敗しました" },
        { status: 500 }
      );
    }
  }
}
