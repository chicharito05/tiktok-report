"""正規化モジュール

CSV, Playwright, Visionの3系統からのデータを
統一フォーマットに変換してSupabaseに保存する共通モジュール。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import yaml
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(override=True)
logger = logging.getLogger(__name__)


@dataclass
class DailyOverviewRow:
    """日別Overviewデータの統一フォーマット"""
    date: str  # YYYY-MM-DD
    video_views: int = 0
    profile_views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


@dataclass
class PostRow:
    """投稿データの統一フォーマット"""
    post_date: str  # ISO 8601
    caption: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    duration: str = ""
    visibility: str = ""
    watch_through_rate: Optional[float] = None
    two_sec_view_rate: Optional[float] = None


def get_supabase_client() -> Client:
    """Supabaseクライアントを取得する。"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL と SUPABASE_KEY を .env に設定してください"
        )
    return create_client(url, key)


def resolve_client_id(supabase: Client, slug: str) -> str:
    """クライアント名またはIDからSupabase上のclient_idを取得する。

    Args:
        supabase: Supabaseクライアント
        slug: クライアント名またはUUID

    Returns:
        client_id (UUID文字列)

    Raises:
        ValueError: クライアントが見つからない場合
    """
    # UUIDの場合はそのまま返す
    if len(slug) == 36 and slug.count("-") == 4:
        return slug

    # nameで検索
    result = (
        supabase.table("clients")
        .select("id")
        .eq("name", slug)
        .execute()
    )
    if result.data:
        return result.data[0]["id"]

    # tiktok_usernameで検索
    result = (
        supabase.table("clients")
        .select("id")
        .eq("tiktok_username", slug)
        .execute()
    )
    if result.data:
        return result.data[0]["id"]

    raise ValueError(f"クライアント '{slug}' がDBに見つかりません。先にクライアント管理画面で登録してください。")


def upsert_daily_overview(
    supabase: Client,
    client_id: str,
    rows: list[DailyOverviewRow],
) -> int:
    """日別OverviewデータをSupabaseにUPSERTする。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        rows: DailyOverviewRowのリスト

    Returns:
        UPSERTした行数
    """
    if not rows:
        return 0

    records = []
    for row in rows:
        record = asdict(row)
        record["client_id"] = client_id
        records.append(record)

    result = (
        supabase.table("daily_overview")
        .upsert(records, on_conflict="client_id,date")
        .execute()
    )
    count = len(result.data)
    logger.info("daily_overview: %d 行をUPSERTしました", count)
    return count


def upsert_posts(
    supabase: Client,
    client_id: str,
    rows: list[PostRow],
) -> int:
    """投稿データをSupabaseにUPSERTする。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        rows: PostRowのリスト

    Returns:
        UPSERTした行数
    """
    if not rows:
        return 0

    records = []
    for row in rows:
        record = asdict(row)
        record["client_id"] = client_id
        # None値を除外（DBのデフォルト値を使う / 既存値を上書きしない）
        record = {k: v for k, v in record.items() if v is not None}
        records.append(record)

    result = (
        supabase.table("posts")
        .upsert(records, on_conflict="client_id,post_date,caption")
        .execute()
    )
    count = len(result.data)
    logger.info("posts: %d 行をUPSERTしました", count)
    return count


def parse_int_safe(value: str) -> int:
    """カンマ区切りやK表記を含む数値文字列をintに変換する。

    Args:
        value: 数値文字列（例: "1,234", "141K", "-1"）

    Returns:
        変換後の整数値。負の値は0にクランプ。
    """
    if not value or value.strip() == "":
        return 0

    s = value.strip().replace(",", "").replace("\"", "")

    # K表記対応 (例: 141K → 141000)
    if s.upper().endswith("K"):
        try:
            return max(0, int(float(s[:-1]) * 1000))
        except ValueError:
            return 0

    # M表記対応 (例: 1.5M → 1500000)
    if s.upper().endswith("M"):
        try:
            return max(0, int(float(s[:-1]) * 1_000_000))
        except ValueError:
            return 0

    try:
        n = int(float(s))
        return max(0, n)  # -1 → 0
    except ValueError:
        logger.warning("数値変換失敗: '%s' → 0として処理", value)
        return 0


def parse_float_safe(value: str) -> Optional[float]:
    """パーセント表記を含む数値文字列をfloatに変換する。空なら None。"""
    if not value or value.strip() in ("", "-", "—"):
        return None
    s = value.strip().replace("%", "").replace(",", "").replace('"', "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None
