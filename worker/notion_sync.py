"""Notion同期モジュール

NotionのデータベースからTikTok動画の原稿データ（タイトル・投稿日）を取得し、
postsテーブルに同期する。数値フィールドは上書きしない。

Usage:
    from worker.notion_sync import sync_notion_to_posts
    result = sync_notion_to_posts(supabase, client_id, notion_database_id)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from notion_client import Client as NotionClient

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


def fetch_notion_entries(database_id: str) -> list[dict]:
    """Notionデータベースから全エントリを取得する。

    notion-client v3.0.0 では databases.query が廃止され、
    data_sources.query を使用する。database_id は data_source_id
    または database_id のどちらでも対応する。

    Args:
        database_id: Notion data_source UUID または database UUID

    Returns:
        [{"title": str, "post_date": str, "status": str}, ...]
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
            response = notion.data_sources.query(**kwargs)
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
                        response = notion.data_sources.query(**kwargs)
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

            entries.append({
                "title": title.strip(),
                "post_date": post_date,
                "status": status,
                "notion_page_id": page.get("id"),
            })

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    logger.info("Notionから %d 件のエントリを取得しました", len(entries))
    return entries


def sync_notion_to_posts(
    supabase,
    client_id: str,
    database_id: str,
) -> dict:
    """NotionのDBからpostsテーブルに同期する。

    タイトル・投稿日のみ同期。数値フィールド（views, likes等）は
    上書きしない。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        database_id: Notion database UUID

    Returns:
        {"synced": int, "skipped": int, "total": int}
    """
    entries = fetch_notion_entries(database_id)

    synced = 0
    skipped = 0

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

        # タイトル・投稿日のみでUPSERT（数値フィールドは含めない）
        record = {
            "client_id": client_id,
            "post_date": post_date,
            "caption": title,
        }

        try:
            supabase.table("posts").upsert(
                record,
                on_conflict="client_id,post_date,caption",
            ).execute()
            synced += 1
        except Exception as e:
            logger.warning("同期失敗: %s - %s", title, e)
            skipped += 1

    result = {"synced": synced, "skipped": skipped, "total": len(entries)}
    logger.info(
        "Notion同期完了: %d件同期, %d件スキップ (全%d件)",
        synced, skipped, len(entries),
    )
    return result
