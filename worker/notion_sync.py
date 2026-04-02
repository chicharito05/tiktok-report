"""Notion同期モジュール

NotionのデータベースからTikTok動画の原稿データ（タイトル・投稿日・本文）を取得し、
postsテーブルに同期する。数値フィールドは上書きしない。

Usage:
    from worker.notion_sync import sync_notion_to_posts
    result = sync_notion_to_posts(supabase, client_id, notion_database_id)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


def get_notion_client() -> NotionClient:
    """Notion APIクライアントを取得する。"""
    token = os.getenv("NOTION_API_KEY")
    if not token:
        raise RuntimeError(
            "NOTION_API_KEY を .env に設定してください。"
            "Notion Integration Token が必要です。"
        )
    return NotionClient(auth=token)


def _extract_title(page: dict, prop_names: list[str]) -> Optional[str]:
    """ページからtitleプロパティの値を取得する。"""
    props = page.get("properties", {})
    for name in prop_names:
        prop = props.get(name)
        if not prop:
            continue
        if prop["type"] == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return "".join(t.get("plain_text", "") for t in title_arr)
    return None


def _extract_date(page: dict, prop_names: list[str]) -> Optional[str]:
    """ページからdateプロパティのstart値を取得する。"""
    props = page.get("properties", {})
    for name in prop_names:
        prop = props.get(name)
        if not prop:
            continue
        if prop["type"] == "date":
            date_obj = prop.get("date")
            if date_obj and date_obj.get("start"):
                return date_obj["start"]
    return None


def _extract_status(page: dict, prop_names: list[str]) -> Optional[str]:
    """ページからstatusプロパティの値を取得する。"""
    props = page.get("properties", {})
    for name in prop_names:
        prop = props.get(name)
        if not prop:
            continue
        if prop["type"] == "status":
            status_obj = prop.get("status")
            if status_obj:
                return status_obj.get("name")
    return None


def _extract_block_text(block: dict) -> str:
    """1つのブロックからテキストを抽出する。"""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    # rich_text を持つブロックタイプ
    rich_text_types = [
        "paragraph", "heading_1", "heading_2", "heading_3",
        "bulleted_list_item", "numbered_list_item", "to_do",
        "toggle", "quote", "callout",
    ]

    if block_type in rich_text_types:
        rich_text = block_data.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich_text)
        if block_type.startswith("heading_"):
            return f"\n{text}\n"
        if block_type in ("bulleted_list_item", "numbered_list_item"):
            return f"・{text}"
        if block_type == "to_do":
            checked = "✓" if block_data.get("checked") else "□"
            return f"{checked} {text}"
        return text

    if block_type == "code":
        rich_text = block_data.get("rich_text", [])
        return "".join(rt.get("plain_text", "") for rt in rich_text)

    if block_type == "divider":
        return "---"

    return ""


def _notion_request_with_retry(func, *args, max_retries: int = 3, **kwargs):
    """Notion APIリクエストをレート制限対応のリトライ付きで実行する。"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except APIResponseError as e:
            if e.status == 429 and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # 2, 4, 8秒
                logger.info("レート制限: %d秒待機後にリトライ (%d/%d)", wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
                continue
            raise
        except Exception:
            raise


def fetch_page_content(page_id: str) -> str:
    """Notionページの本文テキストを取得する。

    ブロックAPIを使用してページ内の全テキストブロックを取得し、
    プレーンテキストとして結合する。

    Args:
        page_id: NotionページのUUID

    Returns:
        ページ本文のプレーンテキスト
    """
    notion = get_notion_client()
    texts = []
    has_more = True
    start_cursor = None

    while has_more:
        kwargs = {"block_id": page_id, "page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        try:
            # レート制限対応: リクエスト間に0.35秒待機（約3req/s）
            time.sleep(0.35)
            response = _notion_request_with_retry(
                notion.blocks.children.list, **kwargs
            )
        except Exception as e:
            logger.warning("ページ本文の取得に失敗: %s - %s", page_id, e)
            return ""

        for block in response.get("results", []):
            text = _extract_block_text(block)
            if text:
                texts.append(text)

            # 子ブロックがある場合は再帰的に取得
            if block.get("has_children"):
                child_text = fetch_page_content(block["id"])
                if child_text:
                    texts.append(child_text)

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    return "\n".join(texts)


def fetch_notion_entries(database_id: str, include_content: bool = False) -> list[dict]:
    """Notionデータベースから全エントリを取得する。

    notion-client v3.0.0 では databases.query が廃止され、
    data_sources.query を使用する。database_id は data_source_id
    または database_id のどちらでも対応する。

    Args:
        database_id: Notion data_source UUID または database UUID
        include_content: Trueの場合、各ページの本文も取得する

    Returns:
        [{"title": str, "post_date": str, "status": str, "notion_page_id": str, "content": str}, ...]
    """
    notion = get_notion_client()

    entries = []
    has_more = True
    start_cursor = None

    # data_source_id を特定する
    # まず data_sources.query を試し、失敗したら databases.retrieve で
    # data_source_id を取得する
    data_source_id = database_id

    while has_more:
        kwargs = {"data_source_id": data_source_id, "page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        try:
            time.sleep(0.35)  # レート制限対策
            response = _notion_request_with_retry(
                notion.data_sources.query, **kwargs
            )
        except Exception as e:
            # data_source_idではなくdatabase_idが渡された場合、
            # databases.retrieveでdata_source_idを取得して再試行
            if start_cursor is None:
                logger.info("data_sources.query失敗、database_idからdata_source_idを取得: %s", e)
                try:
                    db = notion.databases.retrieve(database_id=database_id)
                    ds_list = db.get("data_sources", [])
                    if ds_list:
                        data_source_id = ds_list[0]["id"]
                        kwargs["data_source_id"] = data_source_id
                        time.sleep(0.35)
                        response = _notion_request_with_retry(
                            notion.data_sources.query, **kwargs
                        )
                    else:
                        raise RuntimeError(f"Database {database_id} にdata_sourceが見つかりません")
                except Exception as e2:
                    raise RuntimeError(f"Notionデータベースのクエリに失敗: {e2}") from e
            else:
                raise

        results = response.get("results", [])

        for page in results:
            title = _extract_title(page, ["タイトル", "名前", "Name", "title"])
            post_date = _extract_date(page, ["公開予定", "投稿日", "公開日", "日付"])
            status = _extract_status(page, ["ステータス", "Status"])

            if not title:
                logger.debug("タイトルなしのエントリをスキップ: %s", page.get("id"))
                continue

            entry = {
                "title": title.strip(),
                "post_date": post_date,
                "status": status,
                "notion_page_id": page.get("id"),
                "content": "",
            }

            # 本文取得
            if include_content and page.get("id"):
                entry["content"] = fetch_page_content(page["id"])

            entries.append(entry)

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    logger.info("Notionから %d 件のエントリを取得しました", len(entries))
    return entries


def sync_notion_to_posts(
    supabase,
    client_id: str,
    database_id: str,
    include_content: bool = True,
) -> dict:
    """NotionのDBからpostsテーブルに同期する。

    タイトル・投稿日・原稿本文を同期。数値フィールド（views, likes等）は
    上書きしない。include_content=True の場合、DBに既にnotion_contentが
    ある投稿はスキップし、未取得の投稿のみNotionから本文を取得する。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        database_id: Notion database UUID
        include_content: 原稿本文も取得・同期するか

    Returns:
        {"synced": int, "skipped": int, "total": int, "content_fetched": int}
    """
    # まずタイトル・投稿日のみ取得（高速）
    entries = fetch_notion_entries(database_id, include_content=False)

    # 既にnotion_contentがある投稿のcaptionセットを取得（差分取得用）
    existing_content_captions: set[str] = set()
    if include_content:
        try:
            existing = (
                supabase.table("posts")
                .select("caption")
                .eq("client_id", client_id)
                .not_.is_("notion_content", "null")
                .neq("notion_content", "")
                .execute()
            )
            existing_content_captions = {
                r["caption"] for r in (existing.data or [])
            }
            logger.info(
                "既にnotion_content取得済み: %d件",
                len(existing_content_captions),
            )
        except Exception as e:
            logger.warning("既存notion_content確認失敗: %s", e)

    skipped = 0
    content_fetched = 0
    records = []

    for entry in entries:
        title = entry["title"]
        post_date = entry.get("post_date")

        if not post_date:
            logger.debug("投稿日なし、スキップ: %s", title)
            skipped += 1
            continue

        # post_dateがdate-onlyの場合、タイムゾーン付きのISO形式に変換
        if len(post_date) == 10:  # YYYY-MM-DD
            post_date = post_date + "T00:00:00+09:00"

        record = {
            "client_id": client_id,
            "post_date": post_date,
            "caption": title,
        }

        # 原稿本文取得（差分のみ）
        if include_content and title not in existing_content_captions:
            page_id = entry.get("notion_page_id")
            if page_id:
                content = fetch_page_content(page_id)
                if content:
                    record["notion_content"] = content
                    content_fetched += 1
                    logger.debug("本文取得: %s (%d文字)", title[:30], len(content))

        records.append(record)

    # バッチUPSERT（50件ずつ）
    synced = 0
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            supabase.table("posts").upsert(
                batch,
                on_conflict="client_id,post_date,caption",
            ).execute()
            synced += len(batch)
        except Exception as e:
            logger.warning("バッチ同期失敗 (件数=%d): %s", len(batch), e)
            skipped += len(batch)

    result = {
        "synced": synced,
        "skipped": skipped,
        "total": len(entries),
        "content_fetched": content_fetched,
    }
    logger.info(
        "Notion同期完了: %d件同期, %d件スキップ, 本文%d件取得 (全%d件)",
        synced, skipped, content_fetched, len(entries),
    )
    return result


def fetch_notion_articles(
    supabase,
    client_id: str,
    database_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Notionから原稿一覧（本文付き）を取得する。

    DBに保存済みのnotion_contentがあればそれを返し、
    なければNotionから直接取得する。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        database_id: Notion database UUID
        start_date: 絞り込み開始日 (YYYY-MM-DD)
        end_date: 絞り込み終了日 (YYYY-MM-DD)

    Returns:
        [{"caption": str, "post_date": str, "notion_content": str}, ...]
    """
    # まずDBから取得を試みる
    query = (
        supabase.table("posts")
        .select("caption, post_date, notion_content")
        .eq("client_id", client_id)
        .order("post_date", desc=True)
    )
    if start_date:
        query = query.gte("post_date", start_date)
    if end_date:
        query = query.lte("post_date", end_date + "T23:59:59")

    result = query.execute()
    posts = result.data or []

    # notion_contentが空の投稿があれば、Notionから本文を取得して更新
    empty_content_posts = [p for p in posts if not p.get("notion_content")]
    if empty_content_posts and database_id:
        logger.info("notion_content未取得の投稿が %d 件あります。Notionから取得中...", len(empty_content_posts))
        entries = fetch_notion_entries(database_id, include_content=True)

        # caption(タイトル)でマッチさせて更新
        entry_map = {e["title"]: e.get("content", "") for e in entries}
        for post in empty_content_posts:
            content = entry_map.get(post["caption"], "")
            if content:
                post["notion_content"] = content
                # DBも更新
                try:
                    supabase.table("posts").update(
                        {"notion_content": content}
                    ).eq("client_id", client_id).eq("caption", post["caption"]).execute()
                except Exception as e:
                    logger.warning("notion_content更新失敗: %s - %s", post["caption"], e)

    return posts
