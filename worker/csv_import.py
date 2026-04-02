"""CSV取り込みスクリプト

TikTok StudioからエクスポートされるOverview CSVをパースし、
Supabaseのdaily_overviewテーブルにUPSERTする。

Usage:
    python worker/csv_import.py --client inthegolf --file data/Overview.csv --year 2026
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from datetime import date

from worker.normalize import (
    DailyOverviewRow,
    PostRow,
    get_supabase_client,
    parse_float_safe,
    parse_int_safe,
    resolve_client_id,
    upsert_daily_overview,
    upsert_posts,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 日本語月名 → 月番号
MONTH_MAP = {
    "1月": 1, "2月": 2, "3月": 3, "4月": 4,
    "5月": 5, "6月": 6, "7月": 7, "8月": 8,
    "9月": 9, "10月": 10, "11月": 11, "12月": 12,
}


def parse_japanese_date(date_str: str, year: int) -> str:
    """「2月1日」形式の日付をYYYY-MM-DD形式に変換する。

    Args:
        date_str: 日本語日付文字列（例: "2月1日"）
        year: 年

    Returns:
        YYYY-MM-DD形式の文字列

    Raises:
        ValueError: パースできない場合
    """
    match = re.match(r"(\d{1,2})月(\d{1,2})日", date_str.strip())
    if not match:
        raise ValueError(f"日付をパースできません: '{date_str}'")

    month = int(match.group(1))
    day = int(match.group(2))
    return date(year, month, day).isoformat()


def parse_csv(file_path: str, year: int) -> list[DailyOverviewRow]:
    """TikTok Studio Overview CSVをパースする。

    Args:
        file_path: CSVファイルパス
        year: 日付の年

    Returns:
        DailyOverviewRowのリスト
    """
    rows: list[DailyOverviewRow] = []

    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for line_num, record in enumerate(reader, start=2):
            try:
                date_str = record.get("Date", "").strip().strip('"')
                parsed_date = parse_japanese_date(date_str, year)

                row = DailyOverviewRow(
                    date=parsed_date,
                    video_views=parse_int_safe(record.get("Video Views", "0")),
                    profile_views=parse_int_safe(record.get("Profile Views", "0")),
                    likes=parse_int_safe(record.get("Likes", "0")),
                    comments=parse_int_safe(record.get("Comments", "0")),
                    shares=parse_int_safe(record.get("Shares", "0")),
                )
                rows.append(row)
            except ValueError as e:
                logger.warning("行 %d をスキップ: %s", line_num, e)
                continue

    logger.info("CSV: %d 行を読み込みました（%s）", len(rows), file_path)
    return rows


def detect_csv_type(file_path: str) -> str:
    """CSVのヘッダーからタイプを自動判別する。

    Returns:
        "overview" or "posts"
    """
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    header_lower = [h.strip().lower() for h in header]
    # 動画データCSVの判別: タイトル/キャプション列がある
    if any(k in header_lower for k in ("caption", "title", "タイトル", "キャプション")):
        return "posts"
    return "overview"


def parse_posts_csv(file_path: str, year: int) -> list[PostRow]:
    """動画毎データCSVをパースする。

    ヘッダー例（日本語 or 英語対応）:
        タイトル,投稿日,再生回数,いいね数,コメント数,シェア数,視聴完了率,2秒視聴率
        Title,Post Date,Views,Likes,Comments,Shares,Watch Through Rate,2s View Rate
    """
    rows: list[PostRow] = []

    # ヘッダー名のマッピング（日本語/英語両対応）
    COL_MAP = {
        "caption": ("caption", "title", "タイトル", "キャプション"),
        "post_date": ("post date", "post_date", "投稿日", "date"),
        "views": ("views", "再生回数", "再生数"),
        "likes": ("likes", "いいね数", "いいね"),
        "comments": ("comments", "コメント数", "コメント"),
        "shares": ("shares", "シェア数", "シェア"),
        "duration": ("duration", "動画長", "動画時間", "長さ"),
        "watch_through_rate": ("watch through rate", "watch_through_rate", "視聴完了率"),
        "two_sec_view_rate": ("2s view rate", "two_sec_view_rate", "2秒視聴率", "2秒視聴"),
    }

    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # ヘッダーを正規化してマッピング
        field_map = {}
        for field_name in (reader.fieldnames or []):
            normalized = field_name.strip().lower()
            for key, aliases in COL_MAP.items():
                if normalized in aliases:
                    field_map[key] = field_name
                    break

        if "caption" not in field_map:
            raise ValueError("CSVにタイトル列が見つかりません。ヘッダーに「タイトル」または「Caption」を含めてください。")

        for line_num, record in enumerate(reader, start=2):
            try:
                # 投稿日のパース
                date_raw = record.get(field_map.get("post_date", ""), "").strip()
                if not date_raw:
                    logger.warning("行 %d: 投稿日が空のためスキップ", line_num)
                    continue

                # YYYY-MM-DD or YYYY/MM/DD 形式を試す
                parsed_date = None
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
                    try:
                        parsed_date = date.fromisoformat(
                            date_raw.replace("/", "-")[:10]
                        ).isoformat()
                        break
                    except ValueError:
                        continue

                # 日本語形式を試す
                if not parsed_date:
                    try:
                        parsed_date = parse_japanese_date(date_raw, year)
                    except ValueError:
                        logger.warning("行 %d: 日付パース失敗 '%s'", line_num, date_raw)
                        continue

                caption = record.get(field_map.get("caption", ""), "").strip()
                if not caption:
                    logger.warning("行 %d: タイトルが空のためスキップ", line_num)
                    continue

                row = PostRow(
                    post_date=parsed_date,
                    caption=caption,
                    views=parse_int_safe(record.get(field_map.get("views", ""), "0")),
                    likes=parse_int_safe(record.get(field_map.get("likes", ""), "0")),
                    comments=parse_int_safe(record.get(field_map.get("comments", ""), "0")),
                    shares=parse_int_safe(record.get(field_map.get("shares", ""), "0")),
                    duration=record.get(field_map.get("duration", ""), "").strip(),
                    watch_through_rate=parse_float_safe(
                        record.get(field_map.get("watch_through_rate", ""), "")
                    ),
                    two_sec_view_rate=parse_float_safe(
                        record.get(field_map.get("two_sec_view_rate", ""), "")
                    ),
                )
                rows.append(row)
            except Exception as e:
                logger.warning("行 %d をスキップ: %s", line_num, e)
                continue

    logger.info("動画CSV: %d 行を読み込みました（%s）", len(rows), file_path)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TikTok Studio Overview CSVをSupabaseに取り込む"
    )
    parser.add_argument(
        "--client", required=True,
        help="クライアントslug（例: inthegolf）",
    )
    parser.add_argument(
        "--file", required=True,
        help="CSVファイルパス",
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="日付の年（省略時は現在年）",
    )
    args = parser.parse_args()

    year = args.year or date.today().year

    # CSV読み込み
    try:
        rows = parse_csv(args.file, year)
    except FileNotFoundError:
        logger.error("ファイルが見つかりません: %s", args.file)
        sys.exit(1)

    if not rows:
        logger.warning("取り込みデータがありません")
        sys.exit(0)

    # Supabaseに保存
    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        count = upsert_daily_overview(supabase, client_id, rows)
        logger.info("完了: %d 行を取り込みました", count)
    except Exception:
        logger.exception("Supabase保存中にエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
