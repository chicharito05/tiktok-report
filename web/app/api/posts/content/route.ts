import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";

/**
 * GET: 1件の投稿の原稿本文を取得する
 */
export async function GET(request: NextRequest) {
  const postId = new URL(request.url).searchParams.get("post_id");

  if (!postId) {
    return NextResponse.json({ error: "post_idを指定してください" }, { status: 400 });
  }

  try {
    const supabase = await createServerSupabaseClient();
    const { data, error } = await supabase
      .from("posts")
      .select("id, notion_content")
      .eq("id", postId)
      .single();

    if (error || !data) {
      return NextResponse.json({ error: "投稿が見つかりません" }, { status: 404 });
    }

    return NextResponse.json({ notion_content: data.notion_content });
  } catch {
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}
