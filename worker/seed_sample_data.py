"""サンプルデータ投入スクリプト

InTheGolfの2026年2月分のdaily_overviewデータと投稿データを投入する。

Usage:
    python worker/seed_sample_data.py
"""

import logging
import sys

from dotenv import load_dotenv

from worker.normalize import (
    DailyOverviewRow,
    PostRow,
    get_supabase_client,
    resolve_client_id,
    upsert_daily_overview,
    upsert_posts,
)

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 2026年2月のdaily_overviewデータ（InTheGolf実データ）
DAILY_DATA = [
    ("2026-02-01", 5010, 14, 29, 0, 1),
    ("2026-02-02", 8515, 61, 48, 3, 1),
    ("2026-02-03", 6781, 16, 34, 0, 2),
    ("2026-02-04", 4753, 11, 32, 0, 2),
    ("2026-02-05", 4334, 16, 27, 0, 1),
    ("2026-02-06", 5658, 12, 32, 0, 0),
    ("2026-02-07", 4069, 12, 29, 1, 1),
    ("2026-02-08", 9062, 20, 56, 1, 5),
    ("2026-02-09", 8392, 21, 38, 0, 0),
    ("2026-02-10", 4540, 7, 28, 0, 1),
    ("2026-02-11", 7038, 10, 44, 0, 3),
    ("2026-02-12", 15720, 38, 83, 8, 6),
    ("2026-02-13", 19603, 30, 113, 3, 17),
    ("2026-02-14", 17021, 39, 135, 7, 15),
    ("2026-02-15", 18585, 38, 146, 2, 13),
    ("2026-02-16", 26983, 62, 237, 2, 17),
    ("2026-02-17", 34054, 47, 217, 12, 21),
    ("2026-02-18", 26142, 53, 140, 4, 15),
    ("2026-02-19", 26970, 42, 170, 0, 11),
    ("2026-02-20", 31149, 62, 196, 3, 15),
    ("2026-02-21", 27042, 54, 162, 2, 17),
    ("2026-02-22", 30533, 64, 224, 5, 9),
    ("2026-02-23", 28694, 58, 180, 0, 7),
    ("2026-02-24", 20714, 37, 112, 0, 12),
    ("2026-02-25", 17611, 32, 106, 4, 22),
    ("2026-02-26", 16472, 23, 95, 3, 12),
    ("2026-02-27", 11986, 24, 52, 2, 7),
    ("2026-02-28", 7609, 14, 36, 0, 3),
]

# サンプル投稿データ（InTheGolf）
POSTS_DATA = [
    (
        "2026-01-25T18:00:00",
        "転写熱で永遠にインクが不要なのはありがたい！#整理整頓 #プリンター",
        141000, 445, 11, "00:29", "誰でも",
    ),
    (
        "2026-02-10T19:00:00",
        "充電式でカバンに入るプリンターって凄すぎ #ガジェット紹介 #プリンター",
        277000, 1783, 34, "00:31", "誰でも",
    ),
    (
        "2025-12-26T18:30:00",
        "チョコを食べたくて震えた時に最適 #チロルチョコ #tiktokshop",
        205000, 1167, 46, "00:25", "誰でも",
    ),
    (
        "2026-02-16T20:00:00",
        "バキュームフライ #訳あり #お得",
        42000, 202, 6, "00:30", "誰でも",
    ),
    (
        "2026-03-22T19:30:00",
        "これだけで鞄の中がすっきりした #充電器 #アップルウォッチ",
        49000, 131, 1, "00:20", "誰でも",
    ),
]


def main() -> None:
    logger.info("サンプルデータ投入を開始します")

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, "inthegolf")
    except Exception:
        logger.exception("Supabase接続に失敗しました")
        sys.exit(1)

    # daily_overview
    overview_rows = [
        DailyOverviewRow(
            date=d[0],
            video_views=d[1],
            profile_views=d[2],
            likes=d[3],
            comments=d[4],
            shares=d[5],
        )
        for d in DAILY_DATA
    ]
    count = upsert_daily_overview(supabase, client_id, overview_rows)
    logger.info("daily_overview: %d 行投入完了", count)

    # posts
    post_rows = [
        PostRow(
            post_date=p[0],
            caption=p[1],
            views=p[2],
            likes=p[3],
            comments=p[4],
            duration=p[5],
            visibility=p[6],
        )
        for p in POSTS_DATA
    ]
    count = upsert_posts(supabase, client_id, post_rows)
    logger.info("posts: %d 行投入完了", count)

    logger.info("サンプルデータ投入が完了しました")


if __name__ == "__main__":
    main()
