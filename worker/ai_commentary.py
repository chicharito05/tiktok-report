"""AI考察コメント生成モジュール

Claude APIを使い、TikTokの月次データに対する考察・改善提案を自動生成する。

Usage:
    python worker/ai_commentary.py --client inthegolf [--period 2026-03]
"""

import argparse
import json
import logging
import sys

import anthropic
from dotenv import load_dotenv

from worker.analyze import analyze_period, get_default_date_range
from worker.normalize import get_supabase_client, resolve_client_id

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "あなたはTikTokマーケティングの専門家です。"
    "クライアントへの月次レポートに記載する分析コメントを作成してください。"
    "プロフェッショナルだが読みやすいトーンで、具体的な数値を引用しながら書いてください。"
)

USER_PROMPT_TEMPLATE = """\
以下はTikTokアカウントの分析データです。このデータに基づいて、3つのセクションの分析コメントをJSON形式で返してください。

分析データ:
{analysis_json}

※ top_postsは再生数上位の投稿、worst_postsは再生数下位の投稿です。
※ follower_dataがある場合はフォロワー数の推移も考慮してください。

以下のJSON形式で返してください。各セクションは日本語で3〜5文程度で記述してください。
{{
    "best_post_analysis": "ベスト投稿・ワースト投稿の要因分析（なぜバズったか/伸びなかったか、構成・ハッシュタグ・投稿時間の観点から比較）",
    "improvement_suggestions": "改善提案（投稿時間帯、コンテンツの方向性、エンゲージメント向上策、ワースト投稿から学べる改善点）",
    "next_month_plan": "来月の施策提案（具体的なアクションアイテム3〜5個、フォロワー増加施策も含む）"
}}

JSONのみを返してください。"""


def generate_commentary(analysis_result: dict) -> dict:
    """分析結果からAI考察コメントを生成する。

    Args:
        analysis_result: analyze_period()の戻り値

    Returns:
        3セクションのコメント辞書
    """
    client = anthropic.Anthropic()

    # daily_dataはプロンプトが長くなりすぎるので除外
    prompt_data = {
        k: v for k, v in analysis_result.items()
        if k not in ("daily_data", "all_posts")
    }
    analysis_json = json.dumps(prompt_data, ensure_ascii=False, indent=2)
    user_prompt = USER_PROMPT_TEMPLATE.format(analysis_json=analysis_json)

    logger.info("Claude APIでAI考察コメントを生成中...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text.strip()

    # ```json ... ``` で囲まれている場合の処理
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        commentary = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("JSONパース失敗。レスポンス:\n%s", response_text)
        return {
            "best_post_analysis": "分析コメントの生成に失敗しました。",
            "improvement_suggestions": "分析コメントの生成に失敗しました。",
            "next_month_plan": "分析コメントの生成に失敗しました。",
        }

    logger.info("AI考察コメント生成完了")
    return commentary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claude APIでTikTok月次データの考察コメントを生成する"
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
    logger.info("AI考察コメント生成: %s / %s〜%s", args.client, start_date, end_date)

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        analysis = analyze_period(supabase, client_id, start_date, end_date)
    except Exception:
        logger.exception("データ取得中にエラーが発生しました")
        sys.exit(1)

    commentary = generate_commentary(analysis)
    print(json.dumps(commentary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
