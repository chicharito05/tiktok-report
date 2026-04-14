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
クライアント企業へ提出する月次運用レポートの**分析・考察コメント**を執筆します。

## 最重要ルール：「分析」と「考察」を書く
- **事実の羅列は禁止**です。「再生数は○○回でした」「いいねは○○件でした」のような数値の列挙はレポートの他ページで既に表示されています。
- 数値は必ず引用しますが、それを**「なぜそうなったか」「何を意味するか」「次にどう活かすか」**という考察とセットで書いてください。
- 例（NG）：「トップ投稿は○○で再生数8.4万回、いいね579件でした」
- 例（OK）：「トップ投稿『○○』が8.4万回再生を記録した要因は、国試直後というタイムリーな話題選定と、"難しすぎなかった…？"という共感を誘うフレーズにあると考えられます。同様の時事ネタ×感情フック構成は再現性が高く、来月も活用すべきです」

## 執筆ルール
- 数値を引用する際は必ず**「だからどうなのか（So What?）」**を添えてください
- データから読み取れる**因果関係・相関・パターン**に踏み込んでください
- トップ投稿とワースト投稿を**比較分析**し、伸びた/伸びなかった**構造的な理由**を特定してください
- 「頑張りましょう」のような精神論は禁止。**具体的で再現可能なアクション**を提案してください
- クライアントが社内で即座に共有できる、**経営層にも伝わるプロの文章**で書いてください
- 原稿本文がある場合は、冒頭のフック・構成・CTA（行動喚起）の質も分析してください
- 各セクション**5〜8文程度**でしっかり書いてください（短すぎ厳禁）
- 「今月は好調でした」「引き続き良い傾向です」のような**曖昧な総括は禁止**。必ず具体的な根拠と示唆を述べてください
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
各セクション5〜8文程度で書いてください。

**重要: 事実の羅列ではなく、「なぜそうなったか」「何を意味するか」「次にどう活かすか」を中心に書いてください。**

{{
    "best_post_analysis": "【総評・パフォーマンス分析】今月のパフォーマンスの構造的な分析。トップ投稿が伸びた要因（テーマ選定・フック・タイミング等）とワースト投稿が伸びなかった原因を比較し、再現可能なパターンを抽出する。単なる数値の列挙ではなく、数値の背景にある「なぜ」を考察すること。",
    "improvement_suggestions": "【改善提案】データから導き出される具体的な改善点。なぜその改善が有効かの根拠（数値やパターン）と共に、投稿時間帯・コンテンツ構成・エンゲージメント率向上の施策を提案。抽象的な提案ではなく、すぐに実行できる具体策を書くこと。",
    "next_month_plan": "【来月のアクションプラン】今月のデータ分析から導き出された、具体的なアクションアイテムを5つ程度。各アクションには「何を」「どう変えるか」「なぜそれが効くと考えるか（今月のデータ根拠）」「期待される効果」を明記。",
    "overall_assessment": "【月間総括（1〜2文）】今月の最大の成果と最大の課題を端的にまとめた、示唆に富む一文。レポートの冒頭に使用する。"
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
