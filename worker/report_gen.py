"""レポート生成統合スクリプト

全モジュールを統合し、1コマンドでレポート（HTML + PDF）を生成する。

Usage:
    python worker/report_gen.py --client inthegolf [--start-date 2026-03-01 --end-date 2026-03-31]
    python worker/report_gen.py --all
    python worker/report_gen.py --client inthegolf --upload
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from worker.analyze import analyze_period, get_default_date_range
from worker.normalize import get_supabase_client, resolve_client_id

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _format_date_range_japanese(start_date: str, end_date: str) -> str:
    """日付範囲を日本語表記に変換する。

    同一月なら '2026年3月1日〜31日'
    異なる月なら '2026年3月1日〜4月15日'
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if start.year == end.year and start.month == end.month:
        # 月初〜月末の場合は月表記のみ
        import calendar
        last_day = calendar.monthrange(start.year, start.month)[1]
        if start.day == 1 and end.day == last_day:
            return f"{start.year}年{start.month}月"
        return f"{start.year}年{start.month}月{start.day}日〜{end.day}日"
    elif start.year == end.year:
        return f"{start.year}年{start.month}月{start.day}日〜{end.month}月{end.day}日"
    else:
        return f"{start.year}年{start.month}月{start.day}日〜{end.year}年{end.month}月{end.day}日"


def _format_post_date(post_date_str: str) -> str:
    """ISO日時文字列を 'M月D日' 形式に変換する。"""
    if not post_date_str:
        return ""
    try:
        dt = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
        return f"{dt.month}月{dt.day}日"
    except (ValueError, TypeError):
        try:
            parts = post_date_str.split("-")
            return f"{int(parts[1])}月{int(parts[2][:2])}日"
        except (IndexError, ValueError):
            return post_date_str


def _enrich_posts(posts: list[dict]) -> list[SimpleNamespace]:
    """投稿データにテンプレート用の属性を追加する。"""
    enriched = []
    for p in posts:
        views = p.get("views", 0)
        likes = p.get("likes", 0)
        comments = p.get("comments", 0)
        shares = p.get("shares", 0)
        engagement_rate = 0.0
        if views > 0:
            engagement_rate = round((likes + comments + shares) / views * 100, 2)

        enriched.append(SimpleNamespace(
            post_date=p.get("post_date", ""),
            post_date_display=_format_post_date(p.get("post_date", "")),
            caption=p.get("caption", ""),
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            duration=p.get("duration", ""),
            visibility=p.get("visibility", ""),
            engagement_rate=engagement_rate,
            watch_through_rate=p.get("watch_through_rate"),
            two_sec_view_rate=p.get("two_sec_view_rate"),
            notion_content=p.get("notion_content", ""),
        ))
    return enriched


def generate_ai_commentary(analysis: dict) -> dict:
    """AI考察コメントを生成する。失敗時はフォールバックメッセージを返す。"""
    try:
        from worker.ai_commentary import generate_commentary
        return generate_commentary(analysis)
    except Exception as e:
        logger.warning("AI考察コメント生成に失敗しました: %s", e)
        return {
            "best_post_analysis": "分析コメントの生成に失敗しました。",
            "improvement_suggestions": "分析コメントの生成に失敗しました。",
            "next_month_plan": "分析コメントの生成に失敗しました。",
        }


def generate_report(
    client_slug: str,
    start_date: str,
    end_date: str,
    upload: bool = False,
    user_commentary: dict | None = None,
    operation_month: str | None = None,
) -> tuple[Path, Path | None]:
    """指定クライアント・期間のレポートを生成する。

    Args:
        client_slug: クライアントslug
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        upload: Supabase Storageにアップロードするか

    Returns:
        (HTMLファイルパス, PDFファイルパス or None)
    """
    supabase = get_supabase_client()
    client_id = resolve_client_id(supabase, client_slug)

    # クライアント名をDBから取得
    client_result = (
        supabase.table("clients")
        .select("name")
        .eq("id", client_id)
        .single()
        .execute()
    )
    client_name = client_result.data["name"] if client_result.data else client_slug

    # 1. データ分析
    logger.info("データ分析中: %s / %s〜%s (運用月: %s)", client_slug, start_date, end_date, operation_month or "全て")
    analysis = analyze_period(supabase, client_id, start_date, end_date, operation_month=operation_month)

    # データがない場合でも投稿データがあればレポート生成を許可
    has_posts = len(analysis.get("all_posts", [])) > 0
    if analysis["days_with_data"] == 0 and not has_posts:
        raise RuntimeError(
            f"データがありません。先にデータを取り込んでください。"
            f"(client={client_slug}, period={start_date}〜{end_date})"
        )

    # 2. AI考察コメント（ユーザー入力があればそちらを優先）
    if user_commentary and any(user_commentary.values()):
        logger.info("ユーザー入力の総評・改善案を使用")
        ai_commentary = {
            "best_post_analysis": user_commentary.get("best_post_analysis", ""),
            "improvement_suggestions": user_commentary.get("improvement_suggestions", ""),
            "next_month_plan": user_commentary.get("next_month_plan", ""),
        }
        # 空欄の項目のみAI生成で補完
        if not any(ai_commentary.values()):
            logger.info("AI考察コメント生成中...")
            ai_commentary = generate_ai_commentary(analysis)
    else:
        logger.info("AI考察コメント生成中...")
        ai_commentary = generate_ai_commentary(analysis)

    # 4. テンプレートコンテキスト組み立て
    mom = analysis["month_over_month"]
    all_posts = _enrich_posts(analysis.get("all_posts", []))
    top_posts = _enrich_posts(analysis.get("top_posts", []))
    worst_posts = _enrich_posts(analysis.get("worst_posts", []))

    totals = analysis["totals"]
    total_views = totals["video_views"]
    total_profile_views = totals.get("profile_views", 0)

    # プロフィール遷移率
    profile_transition_rate = None
    if total_views > 0 and total_profile_views > 0:
        profile_transition_rate = round(total_profile_views / total_views * 100, 2)

    # 投稿数・平均再生数
    post_count = len(all_posts)
    avg_views_per_post = round(total_views / post_count) if post_count > 0 else None

    period_display = _format_date_range_japanese(start_date, end_date)

    context = {
        "client_name": client_name,
        "period": period_display,
        "generated_date": date.today().isoformat(),
        # KPIサマリー
        "total_views": total_views,
        "total_likes": totals["likes"],
        "total_comments": totals["comments"],
        "total_shares": totals["shares"],
        "total_profile_views": total_profile_views,
        "engagement_rate": analysis.get("engagement_rate", 0),
        "profile_transition_rate": profile_transition_rate,
        "post_count": post_count,
        "avg_views_per_post": avg_views_per_post,
        # 前期比
        "mom_views": mom.get("video_views"),
        "mom_likes": mom.get("likes"),
        "mom_comments": mom.get("comments"),
        "mom_shares": mom.get("shares"),
        # 投稿データ
        "posts": all_posts,
        "top_posts": top_posts,
        "worst_posts": worst_posts,
        # フォロワー推移
        "follower_data": analysis.get("follower_data", []),
        "follower_growth": analysis.get("follower_growth"),
        # AI分析（総評・改善案）
        "ai_commentary": ai_commentary,
    }

    # 5. HTML生成
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report_template.html")
    html_content = template.render(**context)

    # 出力ディレクトリ
    output_dir = OUTPUT_DIR / client_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    file_prefix = f"{start_date}_{end_date}_{client_slug}"
    html_path = output_dir / f"{file_prefix}_report.html"
    html_path.write_text(html_content, encoding="utf-8")
    logger.info("HTML生成完了: %s", html_path)

    # 6. PDF変換
    pdf_path = None
    try:
        from weasyprint import HTML
        pdf_path = output_dir / f"{file_prefix}_report.pdf"
        HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(pdf_path))
        logger.info("PDF生成完了: %s", pdf_path)
    except ImportError:
        logger.warning(
            "WeasyPrintがインストールされていません。HTMLのみ出力しました。"
        )
    except Exception as e:
        logger.warning("PDF生成に失敗しました: %s HTMLのみ出力しました。", e)

    # 7. Supabase Storageアップロード & reportsテーブル記録
    if upload:
        safe_prefix = f"reports/{client_id}"
        storage_path = None

        # 既存ファイルを削除してから再アップロード（上書き対応）
        try:
            supabase.storage.from_("reports").remove([
                f"{safe_prefix}/{start_date}_{end_date}_report.pdf",
                f"{safe_prefix}/{start_date}_{end_date}_report.html",
            ])
        except Exception:
            pass  # 削除失敗は無視（ファイルが存在しない場合など）

        if pdf_path and pdf_path.exists():
            try:
                storage_path = f"{safe_prefix}/{start_date}_{end_date}_report.pdf"
                with open(pdf_path, "rb") as f:
                    supabase.storage.from_("reports").upload(
                        storage_path, f.read(),
                        {"content-type": "application/pdf"},
                    )
                logger.info("Supabase Storageにアップロード: %s", storage_path)
            except Exception as e:
                logger.warning("Storageアップロードに失敗: %s", e)
                storage_path = None

        html_storage_path = f"{safe_prefix}/{start_date}_{end_date}_report.html"
        try:
            supabase.storage.from_("reports").upload(
                html_storage_path, html_content.encode("utf-8"),
                {"content-type": "text/html; charset=utf-8"},
            )
            logger.info("HTML Storageアップロード: %s", html_storage_path)
        except Exception as e:
            logger.warning("HTML Storageアップロードに失敗: %s", e)

        # reportsテーブルに記録
        try:
            supabase.table("reports").insert({
                "client_id": client_id,
                "start_date": start_date,
                "end_date": end_date,
                "file_path": storage_path or html_storage_path,
            }).execute()
            logger.info("reportsテーブルに記録しました")
        except Exception as e:
            logger.warning("reportsテーブル記録に失敗: %s", e)

    # フロントエンド向けのサマリーデータを返す
    summary = {
        "client_name": client_name,
        "period": period_display,
        "total_views": total_views,
        "total_likes": totals["likes"],
        "total_comments": totals["comments"],
        "total_shares": totals["shares"],
        "total_profile_views": total_profile_views,
        "engagement_rate": analysis.get("engagement_rate", 0),
        "profile_transition_rate": profile_transition_rate,
        "post_count": post_count,
        "avg_views_per_post": avg_views_per_post,
        "mom_views": mom.get("video_views"),
        "mom_likes": mom.get("likes"),
        "mom_comments": mom.get("comments"),
        "mom_shares": mom.get("shares"),
        "top_posts": [
            {
                "caption": getattr(p, "caption", ""),
                "post_date": getattr(p, "post_date", ""),
                "views": getattr(p, "views", 0),
                "likes": getattr(p, "likes", 0),
                "comments": getattr(p, "comments", 0),
                "shares": getattr(p, "shares", 0),
                "engagement_rate": getattr(p, "engagement_rate", None),
            }
            for p in top_posts[:5]
        ],
        "worst_posts": [
            {
                "caption": getattr(p, "caption", ""),
                "post_date": getattr(p, "post_date", ""),
                "views": getattr(p, "views", 0),
                "likes": getattr(p, "likes", 0),
                "comments": getattr(p, "comments", 0),
                "shares": getattr(p, "shares", 0),
            }
            for p in worst_posts[:3]
        ],
        "follower_growth": analysis.get("follower_growth"),
    }

    return html_path, pdf_path, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TikTokレポートを生成する"
    )
    parser.add_argument(
        "--client",
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
    parser.add_argument(
        "--all", action="store_true",
        help="全クライアントのレポートを一括生成",
    )
    parser.add_argument(
        "--upload", action="store_true",
        help="Supabase Storageにもアップロードする",
    )
    args = parser.parse_args()

    if not args.client and not args.all:
        parser.error("--client または --all を指定してください")

    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
    else:
        start_date, end_date = get_default_date_range()

    if args.all:
        config_path = PROJECT_ROOT / "config" / "clients.yaml"
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        slugs = [c["slug"] for c in config["clients"]]
    else:
        slugs = [args.client]

    success_count = 0
    for slug in slugs:
        try:
            logger.info("=== レポート生成開始: %s / %s〜%s ===", slug, start_date, end_date)
            html_path, pdf_path, _summary = generate_report(slug, start_date, end_date, args.upload)
            logger.info("=== レポート生成完了: %s ===", slug)
            logger.info("  HTML: %s", html_path)
            if pdf_path:
                logger.info("  PDF:  %s", pdf_path)
            success_count += 1
        except RuntimeError as e:
            logger.error("スキップ: %s - %s", slug, e)
        except Exception:
            logger.exception("エラー: %s のレポート生成に失敗しました", slug)

    logger.info("完了: %d / %d クライアントのレポートを生成しました", success_count, len(slugs))


if __name__ == "__main__":
    main()
