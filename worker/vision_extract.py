"""Vision解析スクリプト

TikTok Studioのスクリーンショットから投稿データを
Claude API (Vision) で抽出する。

Usage:
    python worker/vision_extract.py --client inthegolf --image screenshot.png
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from worker.normalize import (
    PostRow,
    get_supabase_client,
    parse_int_safe,
    resolve_client_id,
    upsert_posts,
)

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
この画像はTikTok Studioのコンテンツ一覧画面のスクリーンショットです。

画像に表示されている各投稿について、以下の情報を抽出してJSON配列で返してください：

- post_date: 投稿日時（YYYY-MM-DD HH:MM 形式、年が不明な場合は2026年と仮定）
- caption: キャプション（テキスト）
- views: 再生数（整数）
- likes: いいね数（整数）
- comments: コメント数（整数）
- duration: 動画の長さ（MM:SS形式、不明なら空文字）
- visibility: 公開設定（不明なら空文字）

K表記は数値に変換してください（例: 141K → 141000, 1.5M → 1500000）。

JSONのみを返してください。説明文は不要です。
例:
[
  {"post_date": "2026-03-15 18:00", "caption": "ゴルフ練習動画", "views": 141000, "likes": 3200, "comments": 45, "duration": "00:22", "visibility": "誰でも"}
]
"""


def extract_posts_from_image(image_path: str) -> list[PostRow]:
    """スクリーンショットからClaude Visionで投稿データを抽出する。

    Args:
        image_path: 画像ファイルパス

    Returns:
        PostRowのリスト
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"画像が見つかりません: {image_path}")

    # 画像をbase64エンコード
    image_data = path.read_bytes()
    base64_image = base64.standard_b64encode(image_data).decode("utf-8")

    # 拡張子からmedia_typeを判定
    suffix = path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/png")

    # Claude API呼び出し
    client = anthropic.Anthropic()
    logger.info("Claude Vision APIで画像を解析中...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    # レスポンスからJSONを抽出
    response_text = message.content[0].text
    logger.info("Vision APIレスポンス受信")

    # JSONブロックを抽出（```json ... ``` で囲まれている場合にも対応）
    json_text = response_text.strip()
    if json_text.startswith("```"):
        lines = json_text.split("\n")
        # 最初と最後の ``` 行を除去
        lines = [l for l in lines if not l.strip().startswith("```")]
        json_text = "\n".join(lines)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        logger.error("JSONパース失敗。レスポンス:\n%s", response_text)
        return []

    # PostRowに変換
    posts: list[PostRow] = []
    for item in data:
        post = PostRow(
            post_date=item.get("post_date", ""),
            caption=item.get("caption", ""),
            views=parse_int_safe(str(item.get("views", 0))),
            likes=parse_int_safe(str(item.get("likes", 0))),
            comments=parse_int_safe(str(item.get("comments", 0))),
            duration=item.get("duration", ""),
            visibility=item.get("visibility", ""),
        )
        posts.append(post)

    logger.info("画像から %d 件の投稿を抽出しました", len(posts))
    return posts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="スクリーンショットからClaude Visionで投稿データを抽出する"
    )
    parser.add_argument(
        "--client", required=True,
        help="クライアントslug（例: inthegolf）",
    )
    parser.add_argument(
        "--image", required=True,
        help="スクリーンショット画像パス",
    )
    args = parser.parse_args()

    try:
        posts = extract_posts_from_image(args.image)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    if not posts:
        logger.warning("抽出した投稿データがありません")
        sys.exit(0)

    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, args.client)
        count = upsert_posts(supabase, client_id, posts)
        logger.info("完了: %d 件の投稿を保存しました", count)
    except Exception:
        logger.exception("Supabase保存中にエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
