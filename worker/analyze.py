"""分析モジュール

指定クライアントの指定運用月（Nヶ月目）のデータをSupabaseから取得して分析する。

本ツールは Notion 連携を前提とし、投稿の `operation_month`（例: "1ヶ月目"）
ラベルでレポート対象を切り出す。日付範囲は該当運用月に属する投稿の
`post_date` から自動導出される。

Usage:
    python worker/analyze.py --client inthegolf --operation-month "1ヶ月目"
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime as dt_cls
from typing import Optional

from worker.normalize import get_supabase_client, resolve_client_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _extract_month_num(operation_month: Optional[str]) -> Optional[int]:
    """'1ヶ月目' → 1 を取り出す。数字が見つからなければ None。"""
    if not operation_month:
        return None
    m = re.search(r"(\d+)", operation_month)
    return int(m.group(1)) if m else None


def _fetch_posts_for_operation_month(
    supabase, client_id: str, operation_month: str
) -> list[dict]:
    """指定運用月に属する投稿を再生数降順で取得する。"""
    result = (
        supabase.table("posts")
        .select("*")
        .eq("client_id", client_id)
        .eq("operation_month", operation_month)
        .order("views", desc=True)
        .execute()
    )
    return [
        {
            "caption": p.get("caption", ""),
            "views": p.get("views", 0) or 0,
            "likes": p.get("likes", 0) or 0,
            "comments": p.get("comments", 0) or 0,
            "shares": p.get("shares", 0) or 0,
            "post_date": p.get("post_date"),
            "duration": p.get("duration", ""),
            "visibility": p.get("visibility", ""),
            "watch_through_rate": p.get("watch_through_rate"),
            "two_sec_view_rate": p.get("two_sec_view_rate"),
            "notion_content": p.get("notion_content", ""),
            "operation_month": p.get("operation_month"),
        }
        for p in (result.data or [])
    ]


def _derive_date_range_from_posts(
    posts: list[dict],
) -> tuple[Optional[str], Optional[str]]:
    """投稿リストの post_date から最小〜最大の日付を JST ベースで返す。"""
    post_dates: list[date] = []
    for p in posts:
        pd_str = p.get("post_date")
        if not pd_str:
            continue
        try:
            parsed = dt_cls.fromisoformat(str(pd_str).replace("Z", "+00:00"))
            post_dates.append(parsed.date())
        except (ValueError, TypeError):
            continue
    if not post_dates:
        return None, None
    return min(post_dates).isoformat(), max(post_dates).isoformat()


def _sum_daily_overview(
    supabase, client_id: str, start_date: str, end_date: str
) -> tuple[list[dict], dict]:
    """daily_overview を指定期間で合計して返す。"""
    result = (
        supabase.table("daily_overview")
        .select("*")
        .eq("client_id", client_id)
        .gte("date", start_date)
        .lte("date", end_date)
        .order("date")
        .execute()
    )
    data = result.data or []
    totals = {
        "video_views": sum(r.get("video_views", 0) or 0 for r in data),
        "profile_views": sum(r.get("profile_views", 0) or 0 for r in data),
        "likes": sum(r.get("likes", 0) or 0 for r in data),
        "comments": sum(r.get("comments", 0) or 0 for r in data),
        "shares": sum(r.get("shares", 0) or 0 for r in data),
    }
    return data, totals


def _calc_monthly_transition(supabase, client_id: str) -> list[dict]:
    """運用月別の累計・月間パフォーマンスを集計する（P5: 月別推移テーブル用）。

    Returns:
        [{"month_num": 1, "month_label": "1ヶ月目",
          "monthly_views": ..., "cumulative_views": ...}, ...]
    """
    posts_result = (
        supabase.table("posts")
        .select("operation_month, views, likes, comments, shares")
        .eq("client_id", client_id)
        .not_.is_("operation_month", "null")
        .execute()
    )

    month_data: dict[int, dict] = {}
    for p in (posts_result.data or []):
        num = _extract_month_num(p.get("operation_month"))
        if num is None:
            continue
        if num not in month_data:
            month_data[num] = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        month_data[num]["views"] += p.get("views", 0) or 0
        month_data[num]["likes"] += p.get("likes", 0) or 0
        month_data[num]["comments"] += p.get("comments", 0) or 0
        month_data[num]["shares"] += p.get("shares", 0) or 0

    if not month_data:
        return []

    max_month = max(month_data.keys())
    result = []
    cum_views = 0
    for num in range(1, max_month + 1):
        md = month_data.get(num, {"views": 0, "likes": 0, "comments": 0, "shares": 0})
        cum_views += md["views"]
        result.append({
            "month_num": num,
            "month_label": f"{num}ヶ月目",
            "monthly_views": md["views"],
            "monthly_likes": md["likes"],
            "monthly_comments": md["comments"],
            "monthly_shares": md["shares"],
            "cumulative_views": cum_views,
        })
    return result


def analyze_period(
    supabase,
    client_id: str,
    operation_month: str,
) -> dict:
    """指定クライアント・運用月の分析を実行する。

    Args:
        supabase: Supabaseクライアント
        client_id: クライアントUUID
        operation_month: 運用月ラベル（例: "1ヶ月目"）。必須。

    Returns:
        分析結果の辞書
    """
    if not operation_month:
        raise ValueError("operation_month は必須です")

    # --- 当月投稿を取得し、実 post_date から有効期間を導出 ---
    all_posts = _fetch_posts_for_operation_month(supabase, client_id, operation_month)
    effective_start_date, effective_end_date = _derive_date_range_from_posts(all_posts)

    top_posts = all_posts[:5]
    worst_posts = list(reversed(all_posts))[:3] if len(all_posts) >= 3 else []

    if effective_start_date and effective_end_date:
        logger.info(
            "operation_month=%s の実データ期間: %s〜%s (%d件の投稿)",
            operation_month, effective_start_date, effective_end_date, len(all_posts),
        )
    else:
        logger.warning(
            "operation_month=%s に紐づく投稿が見つかりません (client_id=%s)",
            operation_month, client_id,
        )

    # --- KPI (daily_overview を有効期間で集計) ---
    overview_data: list[dict] = []
    totals = {"video_views": 0, "profile_views": 0, "likes": 0, "comments": 0, "shares": 0}
    if effective_start_date and effective_end_date:
        overview_data, totals = _sum_daily_overview(
            supabase, client_id, effective_start_date, effective_end_date,
        )

    engagement_rate = 0.0
    if totals["video_views"] > 0:
        engagement_rate = (
            (totals["likes"] + totals["comments"] + totals["shares"])
            / totals["video_views"]
        )

    # --- 前月比 = (N-1)ヶ月目 との比較 ---
    month_num = _extract_month_num(operation_month)
    prev_operation_month: Optional[str] = None
    prev_start_date: Optional[str] = None
    prev_end_date: Optional[str] = None
    prev_totals = {"video_views": 0, "likes": 0, "comments": 0, "shares": 0}
    if month_num and month_num >= 2:
        prev_operation_month = f"{month_num - 1}ヶ月目"
        prev_posts = _fetch_posts_for_operation_month(
            supabase, client_id, prev_operation_month,
        )
        prev_start_date, prev_end_date = _derive_date_range_from_posts(prev_posts)
        if prev_start_date and prev_end_date:
            _, prev_totals = _sum_daily_overview(
                supabase, client_id, prev_start_date, prev_end_date,
            )

    mom_change: dict[str, Optional[float]] = {}
    for key in ["video_views", "likes", "comments", "shares"]:
        if prev_totals[key] > 0:
            mom_change[key] = round(
                (totals[key] - prev_totals[key]) / prev_totals[key] * 100, 1
            )
        else:
            mom_change[key] = None

    # --- 日別データ（グラフ・HTMLレポート用） ---
    daily_data = []
    for r in overview_data:
        day_views = r.get("video_views", 0) or 0
        day_likes = r.get("likes", 0) or 0
        day_comments = r.get("comments", 0) or 0
        day_shares = r.get("shares", 0) or 0
        day_engagement = 0.0
        if day_views > 0:
            day_engagement = round(
                (day_likes + day_comments + day_shares) / day_views * 100, 2
            )
        daily_data.append({
            "date": r.get("date"),
            "views": day_views,
            "profile_views": r.get("profile_views", 0) or 0,
            "likes": day_likes,
            "comments": day_comments,
            "shares": day_shares,
            "engagement_rate": day_engagement,
        })

    # --- フォロワー数の推移 ---
    follower_data: list[dict] = []
    follower_growth: Optional[dict] = None
    if effective_start_date and effective_end_date:
        try:
            follower_result = (
                supabase.table("follower_snapshots")
                .select("*")
                .eq("client_id", client_id)
                .gte("date", effective_start_date)
                .lte("date", effective_end_date)
                .order("date")
                .execute()
            )
            follower_data = [
                {"date": r["date"], "follower_count": r["follower_count"]}
                for r in (follower_result.data or [])
            ]
            if len(follower_data) >= 2:
                first_count = follower_data[0]["follower_count"]
                last_count = follower_data[-1]["follower_count"]
                follower_growth = {
                    "start_count": first_count,
                    "end_count": last_count,
                    "change": last_count - first_count,
                    "change_rate": round(
                        (last_count - first_count) / first_count * 100, 1
                    ) if first_count > 0 else None,
                }
        except Exception as e:
            logger.warning("フォロワーデータ取得に失敗: %s", e)

    # --- 投稿の曜日別・時間帯別パフォーマンス ---
    day_of_week_stats: dict[str, dict] = {}
    hour_stats: dict[int, dict] = {}
    engagement_breakdown = {"likes": 0, "comments": 0, "shares": 0}

    for p in all_posts:
        try:
            pd_str = p["post_date"]
            parsed = dt_cls.fromisoformat(str(pd_str).replace("Z", "+00:00"))
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            wd = weekday_names[parsed.weekday()]
            hr = parsed.hour

            if wd not in day_of_week_stats:
                day_of_week_stats[wd] = {"count": 0, "total_views": 0, "total_eng": 0}
            day_of_week_stats[wd]["count"] += 1
            day_of_week_stats[wd]["total_views"] += p.get("views", 0) or 0
            day_of_week_stats[wd]["total_eng"] += (
                (p.get("likes", 0) or 0)
                + (p.get("comments", 0) or 0)
                + (p.get("shares", 0) or 0)
            )

            if hr not in hour_stats:
                hour_stats[hr] = {"count": 0, "total_views": 0}
            hour_stats[hr]["count"] += 1
            hour_stats[hr]["total_views"] += p.get("views", 0) or 0
        except (ValueError, TypeError):
            pass

        engagement_breakdown["likes"] += p.get("likes", 0) or 0
        engagement_breakdown["comments"] += p.get("comments", 0) or 0
        engagement_breakdown["shares"] += p.get("shares", 0) or 0

    day_of_week_perf = []
    for wd in ["月", "火", "水", "木", "金", "土", "日"]:
        s = day_of_week_stats.get(wd, {"count": 0, "total_views": 0, "total_eng": 0})
        avg_views = round(s["total_views"] / s["count"]) if s["count"] > 0 else 0
        day_of_week_perf.append({"day": wd, "count": s["count"], "avg_views": avg_views})

    hour_perf = []
    for hr in sorted(hour_stats.keys()):
        s = hour_stats[hr]
        avg_views = round(s["total_views"] / s["count"]) if s["count"] > 0 else 0
        hour_perf.append({"hour": hr, "count": s["count"], "avg_views": avg_views})

    total_eng = sum(engagement_breakdown.values())
    engagement_composition = {
        k: round(v / total_eng * 100, 1) if total_eng > 0 else 0
        for k, v in engagement_breakdown.items()
    }

    # --- 月別推移（P5: 1ヶ月目〜現在までの全月） ---
    monthly_transition = _calc_monthly_transition(supabase, client_id)

    return {
        "operation_month": operation_month,
        "effective_start_date": effective_start_date,
        "effective_end_date": effective_end_date,
        "days_with_data": len(overview_data),
        "totals": totals,
        "prev_totals": prev_totals,
        "prev_operation_month": prev_operation_month,
        "prev_start_date": prev_start_date,
        "prev_end_date": prev_end_date,
        "engagement_rate": round(engagement_rate * 100, 2),
        "month_over_month": mom_change,
        "top_posts": top_posts,
        "worst_posts": worst_posts,
        "all_posts": all_posts,
        "daily_data": daily_data,
        "follower_data": follower_data,
        "follower_growth": follower_growth,
        "day_of_week_performance": day_of_week_perf,
        "hour_performance": hour_perf,
        "engagement_composition": engagement_composition,
        "monthly_transition": monthly_transition,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="指定クライアント・運用月の TikTok データを分析する"
    )
    parser.add_argument(
        "--client", required=True,
        help="クライアントslug または UUID（例: bestlife）",
    )
    parser.add_argument(
        "--operation-month", required=True,
        help='運用月ラベル（例: "1ヶ月目"）',
    )
    args = parser.parse_args()

    logger.info("分析対象: %s / %s", args.client, args.operation_month)

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        result = analyze_period(supabase, client_id, args.operation_month)
    except Exception:
        logger.exception("分析中にエラーが発生しました")
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    t = result["totals"]
    eff_s = result.get("effective_start_date") or "--"
    eff_e = result.get("effective_end_date") or "--"
    logger.info("=== %s (%s〜%s) サマリー ===", args.operation_month, eff_s, eff_e)
    logger.info("再生数: %s", f"{t['video_views']:,}")
    logger.info("いいね: %s", f"{t['likes']:,}")
    logger.info("コメント: %s", f"{t['comments']:,}")
    logger.info("シェア: %s", f"{t['shares']:,}")
    logger.info("エンゲージメント率: %s%%", result["engagement_rate"])


if __name__ == "__main__":
    main()
