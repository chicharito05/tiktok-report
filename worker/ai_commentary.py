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

from worker.analyze import analyze_period
from worker.normalize import get_supabase_client, resolve_client_id

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたはTikTokマーケティングの上級コンサルタントです。
クライアント企業へ提出する月次運用レポートの分析コメントを執筆します。

## 執筆ルール
- **必ず具体的な数値を引用**してください（「再生数が伸びた」ではなく「再生数が前月比+12.5%の15万回に到達」）
- データから読み取れる**因果関係・相関**に踏み込んでください
- 「頑張りましょう」のような精神論は禁止。**具体的で再現可能なアクション**を提案してください
- クライアントが社内で即座に共有できる、**経営層にも伝わるプロの文章**で書いてください
- 原稿本文がある場合は、冒頭のフック・構成・CTA（行動喚起）の質も分析してください
- 各セクション**5〜8文程度**でしっかり書いてください（短すぎ厳禁）
"""

USER_PROMPT_TEMPLATE = """\
以下はTikTokアカウントの月次分析データです。

## 数値サマリー
{analysis_json}

## 曜日別パフォーマンス
{dow_section}

## 投稿時間帯別パフォーマンス
{hour_section}

## エンゲージメント構成比
{eng_comp_section}

{article_section}

## 分析の観点
- top_posts = 再生数上位の投稿、worst_posts = 再生数下位の投稿
- 曜日別・時間帯別データから「最適な投稿タイミング」を特定してください
- エンゲージメント構成比（いいね/コメント/シェアの割合）から視聴者の反応パターンを読み取ってください
- 前月比データ（month_over_month）で改善/悪化のトレンドを分析してください
- フォロワー推移データがあれば成長速度と投稿パフォーマンスの相関を見てください
- 原稿本文があれば、バズった投稿とそうでない投稿の「冒頭3秒のフック」「テーマ選定」「構成」の違いを具体的に比較してください

## 出力形式（JSON）
以下の4つのセクションを日本語で出力してください。
各セクション5〜8文程度で、数値を引用しながら具体的に書いてください。

{{
    "best_post_analysis": "【総評・パフォーマンス分析】今月の全体パフォーマンスの評価。トップ投稿がなぜ伸びたか、ワースト投稿がなぜ伸びなかったかを具体的数値と共に比較分析。コンテンツのテーマ・構成・フックの違いにも言及。",
    "improvement_suggestions": "【改善提案】データから導き出される具体的な改善点。投稿時間帯の最適化、コンテンツ構成の改善、エンゲージメント率向上のための施策を、数値的根拠と共に提案。",
    "next_month_plan": "【来月のアクションプラン】具体的なアクションアイテムを5つ程度。各アクションには「何を」「どう変えるか」「期待される効果」を明記。コンテンツテーマの提案、投稿スケジュール案、フォロワー増加施策も含む。",
    "overall_assessment": "【月間総括（1〜2文）】今月を一言で総括する短いコメント。レポートの冒頭に使用する。"
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

    # サマリーデータ（daily_data, all_postsの詳細は除外してトークン節約）
    prompt_data = {
        k: v for k, v in analysis_result.items()
        if k not in ("daily_data", "all_posts", "day_of_week_performance",
                      "hour_performance", "engagement_composition")
    }
    analysis_json = json.dumps(prompt_data, ensure_ascii=False, indent=2)

    # 曜日別パフォーマンス
    dow_data = analysis_result.get("day_of_week_performance", [])
    dow_section = json.dumps(dow_data, ensure_ascii=False) if dow_data else "データなし"

    # 時間帯別パフォーマンス
    hour_data = analysis_result.get("hour_performance", [])
    hour_section = json.dumps(hour_data, ensure_ascii=False) if hour_data else "データなし"

    # エンゲージメント構成比
    eng_comp = analysis_result.get("engagement_composition", {})
    eng_comp_section = json.dumps(eng_comp, ensure_ascii=False) if eng_comp else "データなし"

    # 原稿本文セクション
    article_section = ""
    all_posts = analysis_result.get("all_posts", [])
    articles_with_content = [
        p for p in all_posts if p.get("notion_content")
    ]
    if articles_with_content:
        article_lines = ["## 投稿の原稿本文（コンテンツ分析用）"]
        for p in articles_with_content[:10]:  # 上位10件に絞る
            content = p["notion_content"][:800]
            article_lines.append(
                f"\n【{p['caption']}】(再生数: {p.get('views', 0):,}, "
                f"いいね: {p.get('likes', 0):,}, ENG率: "
                f"{round((p.get('likes',0)+p.get('comments',0)+p.get('shares',0))/max(p.get('views',1),1)*100,1)}%)\n{content}"
            )
        article_section = "\n".join(article_lines)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        analysis_json=analysis_json,
        dow_section=dow_section,
        hour_section=hour_section,
        eng_comp_section=eng_comp_section,
        article_section=article_section,
    )

    logger.info("Claude APIでAI考察コメントを生成中...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
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
        help="クライアントslug（例: bestlife）",
    )
    parser.add_argument(
        "--operation-month", required=True,
        help="運用月ラベル（例: 1ヶ月目）",
    )
    args = parser.parse_args()

    logger.info("AI考察コメント生成: %s / %s", args.client, args.operation_month)

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        analysis = analyze_period(supabase, client_id, args.operation_month)
    except Exception:
        logger.exception("データ取得中にエラーが発生しました")
        sys.exit(1)

    commentary = generate_commentary(analysis)
    print(json.dumps(commentary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
