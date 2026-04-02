"""Playwrightスクレイパー

TikTok Studioのコンテンツ一覧ページからデータを取得する。
ログイン済みChromeプロファイルを使ってpersistent contextで起動する。

Usage:
    python worker/scraper.py --client inthegolf --chrome-profile /path/to/profile
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from playwright.async_api import async_playwright

from worker.normalize import (
    PostRow,
    get_supabase_client,
    resolve_client_id,
    upsert_posts,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TIKTOK_STUDIO_URL = "https://www.tiktok.com/tiktokstudio/content"


async def scrape_posts(chrome_profile_path: str) -> list[PostRow]:
    """TikTok Studioから投稿データをスクレイピングする。

    Args:
        chrome_profile_path: Chromeプロファイルのパス

    Returns:
        PostRowのリスト
    """
    posts: list[PostRow] = []

    async with async_playwright() as p:
        # ログイン済みChromeプロファイルでブラウザ起動
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_profile_path,
            headless=False,
            channel="chrome",
        )

        page = context.pages[0] if context.pages else await context.new_page()
        logger.info("TikTok Studio にアクセス中...")
        await page.goto(TIKTOK_STUDIO_URL, wait_until="networkidle")
        logger.info("ページ読み込み完了")

        # スクロールして全投稿を表示
        prev_height = 0
        for _ in range(50):  # 最大50回スクロール
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
            current_height = await page.evaluate("document.body.scrollHeight")
            if current_height == prev_height:
                break
            prev_height = current_height

        logger.info("スクロール完了")

        # TODO: ここでDOM解析を実装
        # セレクタ調査後に以下のような処理を追加：
        # - 投稿一覧の各行を取得
        # - 各行からキャプション、再生数、いいね数、コメント数、投稿日時、動画長さを抽出
        # - PostRowオブジェクトに変換してpostsリストに追加
        #
        # 例:
        # rows = await page.query_selector_all("セレクタ")
        # for row in rows:
        #     caption = await row.query_selector("...")
        #     ...
        #     posts.append(PostRow(...))

        logger.warning(
            "DOM解析は未実装です。セレクタ調査後に実装してください。"
        )

        await context.close()

    return posts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TikTok Studioから投稿データをスクレイピングする"
    )
    parser.add_argument(
        "--client", required=True,
        help="クライアントslug（例: inthegolf）",
    )
    parser.add_argument(
        "--chrome-profile", required=True,
        help="Chromeプロファイルのパス",
    )
    args = parser.parse_args()

    posts = asyncio.run(scrape_posts(args.chrome_profile))

    if not posts:
        logger.warning("取得した投稿データがありません")
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
