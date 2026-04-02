"""分析モジュール

指定クライアント・指定期間のデータをSupabaseから取得して分析する。

Usage:
    python worker/analyze.py --client inthegolf [--start-date 2026-03-01 --end-date 2026-03-31]
"""

import argparse
import json
import logging
import sys
from datetime import date, timedelta

from worker.normalize import get_supabase_client, resolve_client_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_default_date_range() -> tuple[str, str]:
    """デフォルトの分析対象期間（前月の1日〜末日）を返す。"""
    today = date.today()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start.isoformat(), last_month_end.isoformat()


def analyze_period(supabase, client_id: str, start_date: str, end_date: str) -> dict:
    """期間指定の分析を実行する。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)

    Returns:
        分析結果の辞書
    """
    # 当期間のdaily_overviewデータ取得
    overview_result = (
        supabase.table("daily_overview")
        .select("*")
        .eq("client_id", client_id)
        .gte("date", start_date)
        .lte("date", end_date)
        .order("date")
        .execute()
    )
    overview_data = overview_result.data

    # 月間合計
    totals = {
        "video_views": sum(r["video_views"] for r in overview_data),
        "profile_views": sum(r["profile_views"] for r in overview_data),
        "likes": sum(r["likes"] for r in overview_data),
        "comments": sum(r["comments"] for r in overview_data),
        "shares": sum(r["shares"] for r in overview_data),
    }

    # エンゲージメント率
    engagement_rate = 0.0
    if totals["video_views"] > 0:
        engagement_rate = (
            (totals["likes"] + totals["comments"] + totals["shares"])
            / totals["video_views"]
        )

    # 前期比（同じ日数分だけ前にずらした期間）
    start_d = date.fromisoformat(start_date)
    end_d = date.fromisoformat(end_date)
    period_days = (end_d - start_d).days + 1
    prev_end_d = start_d - timedelta(days=1)
    prev_start_d = prev_end_d - timedelta(days=period_days - 1)
    prev_start = prev_start_d.isoformat()
    prev_end = prev_end_d.isoformat()

    prev_result = (
        supabase.table("daily_overview")
        .select("*")
        .eq("client_id", client_id)
        .gte("date", prev_start)
        .lte("date", prev_end)
        .execute()
    )
    prev_data = prev_result.data

    prev_totals = {
        "video_views": sum(r["video_views"] for r in prev_data),
        "likes": sum(r["likes"] for r in prev_data),
        "comments": sum(r["comments"] for r in prev_data),
        "shares": sum(r["shares"] for r in prev_data),
    }

    mom_change = {}
    for key in ["video_views", "likes", "comments", "shares"]:
        if prev_totals[key] > 0:
            mom_change[key] = round(
                (totals[key] - prev_totals[key]) / prev_totals[key] * 100, 1
            )
        else:
            mom_change[key] = None

    # 投稿別データ（全件、再生数降順）
    all_posts_result = (
        supabase.table("posts")
        .select("*")
        .eq("client_id", client_id)
        .gte("post_date", start_date)
        .lte("post_date", end_date + "T23:59:59")
        .order("views", desc=True)
        .execute()
    )
    all_posts = [
        {
            "caption": p["caption"],
            "views": p["views"],
            "likes": p["likes"],
            "comments": p["comments"],
            "shares": p.get("shares", 0),
            "post_date": p["post_date"],
            "duration": p.get("duration", ""),
            "visibility": p.get("visibility", ""),
            "watch_through_rate": p.get("watch_through_rate"),
            "two_sec_view_rate": p.get("two_sec_view_rate"),
        }
        for p in all_posts_result.data
    ]
    top_posts = all_posts[:5]

    # ワースト投稿（再生数下位3件、ただし投稿が3件以上ある場合のみ意味がある）
    worst_posts = list(reversed(all_posts))[:3] if len(all_posts) >= 3 else []

    # 日別データ（グラフ・レポート用）
    daily_data = []
    for r in overview_data:
        day_views = r["video_views"]
        day_likes = r["likes"]
        day_comments = r["comments"]
        day_shares = r["shares"]
        day_engagement = 0.0
        if day_views > 0:
            day_engagement = round(
                (day_likes + day_comments + day_shares) / day_views * 100, 2
            )
        daily_data.append({
            "date": r["date"],
            "views": day_views,
            "profile_views": r["profile_views"],
            "likes": day_likes,
            "comments": day_comments,
            "shares": day_shares,
            "engagement_rate": day_engagement,
        })

    # フォロワー数の推移（follower_snapshots テーブルから取得）
    follower_data = []
    follower_growth = None
    try:
        follower_result = (
            supabase.table("follower_snapshots")
            .select("*")
            .eq("client_id", client_id)
            .gte("date", start_date)
            .lte("date", end_date)
            .order("date")
            .execute()
        )
        follower_data = [
            {"date": r["date"], "follower_count": r["follower_count"]}
            for r in follower_result.data
        ]
        if len(follower_data) >= 2:
            first_count = follower_data[0]["follower_count"]
            last_count = follower_data[-1]["follower_count"]
            follower_growth = {
                "start_count": first_count,
                "end_count": last_count,
                "change": last_count - first_count,
                "change_rate": round((last_count - first_count) / first_count * 100, 1) if first_count > 0 else None,
            }
    except Exception as e:
        logger.warning("フォロワーデータ取得に失敗: %s", e)

    result = {
        "start_date": start_date,
        "end_date": end_date,
        "days_with_data": len(overview_data),
        "totals": totals,
        "prev_totals": prev_totals,
        "engagement_rate": round(engagement_rate * 100, 2),
        "month_over_month": mom_change,
        "prev_start_date": prev_start,
        "prev_end_date": prev_end,
        "top_posts": top_posts,
        "worst_posts": worst_posts,
        "all_posts": all_posts,
        "daily_data": daily_data,
        "follower_data": follower_data,
        "follower_growth": follower_growth,
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="指定クライアント・指定期間のTikTokデータを分析する"
    )
    parser.add_argument(
        "--client", required=True,
        help="クライアントslug（例: inthegolf）",
    )
    parser.add_argument(
        "--start-date", default=None,
        help="開始日（YYYY-MM-DD形式）",
    )
    parser.add_argument(
        "--end-date", default=None,
        help="終了日（YYYY-MM-DD形式）",
    )
    args = parser.parse_args()

    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
    else:
        start_date, end_date = get_default_date_range()

    logger.info("分析対象: %s / %s〜%s", args.client, start_date, end_date)

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        result = analyze_period(supabase, client_id, start_date, end_date)
    except Exception:
        logger.exception("分析中にエラーが発生しました")
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    t = result["totals"]
    logger.info("=== %s〜%s サマリー ===", start_date, end_date)
    logger.info("再生数: %s", f"{t['video_views']:,}")
    logger.info("いいね: %s", f"{t['likes']:,}")
    logger.info("コメント: %s", f"{t['comments']:,}")
    logger.info("シェア: %s", f"{t['shares']:,}")
    logger.info("エンゲージメント率: %s%%", result["engagement_rate"])


if __name__ == "__main__":
    main()
