"""PPTX（Googleスライド互換）レポート生成モジュール

analyze_periodの結果とAIコメンタリーからPowerPointプレゼンテーションを生成する。
Googleスライドで直接開ける.pptx形式で出力する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

logger = logging.getLogger(__name__)

# ブランドカラー
PRIMARY = RGBColor(0x1A, 0x1A, 0x2E)
ACCENT = RGBColor(0xE9, 0x45, 0x60)
SUB = RGBColor(0x0F, 0x34, 0x60)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY_50 = RGBColor(0xF8, 0xF9, 0xFA)
GRAY_200 = RGBColor(0xE5, 0xE7, 0xEB)
GRAY_400 = RGBColor(0x9C, 0xA3, 0xAF)
GRAY_600 = RGBColor(0x4B, 0x55, 0x63)
GRAY_800 = RGBColor(0x1F, 0x2A, 0x37)
GREEN = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xDC, 0x26, 0x26)

SLIDE_WIDTH = Inches(10)
SLIDE_HEIGHT = Inches(5.625)


def _fmt_num(n) -> str:
    if n is None:
        return "--"
    n = int(n) if isinstance(n, float) and n == int(n) else n
    if isinstance(n, int):
        if n >= 10000:
            return f"{n / 10000:.1f}万"
        return f"{n:,}"
    return str(n)


def _fmt_pct(n) -> str:
    if n is None:
        return "--"
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def _add_header(slide, client_name: str, period: str):
    """各スライドにヘッダーを追加"""
    # ブランド名
    left = Inches(0.5)
    top = Inches(0.2)
    txBox = slide.shapes.add_textbox(left, top, Inches(2), Inches(0.35))
    tf = txBox.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "LEAD ONE"
    run.font.size = Pt(10)
    run.font.color.rgb = ACCENT
    run.font.bold = True

    # クライアント名 + 期間
    txBox2 = slide.shapes.add_textbox(Inches(3), top, Inches(6.5), Inches(0.35))
    tf2 = txBox2.text_frame
    tf2.word_wrap = False
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    run2 = p2.add_run()
    run2.text = f"{client_name}　{period}"
    run2.font.size = Pt(9)
    run2.font.color.rgb = GRAY_400

    # 区切り線
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(0.55), Inches(9), Pt(1.5),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = GRAY_200
    line.line.fill.background()


def _add_slide_title(slide, title: str, top: float = 0.7):
    """スライドタイトルを左ボーダー付きで追加"""
    # 左ボーダー
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(top), Pt(4), Inches(0.35),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    # タイトルテキスト
    txBox = slide.shapes.add_textbox(Inches(0.75), Inches(top), Inches(8), Inches(0.35))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = PRIMARY


def _set_cell_text(cell, text: str, size: int = 9, bold: bool = False,
                   color: RGBColor = GRAY_800, align=PP_ALIGN.LEFT):
    """テーブルセルのテキストを設定"""
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    # マージン縮小
    cell.margin_left = Emu(45720)
    cell.margin_right = Emu(45720)
    cell.margin_top = Emu(18288)
    cell.margin_bottom = Emu(18288)


def generate_pptx(context: dict, output_path: Path) -> Path:
    """レポートのPPTXを生成する。

    Args:
        context: report_gen.pyのテンプレートコンテキストと同じ辞書
        output_path: 出力先パス

    Returns:
        生成されたPPTXファイルのパス
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]  # Blank

    client_name = context.get("client_name", "")
    period = context.get("period", "")

    # ============================
    # P1: 表紙
    # ============================
    slide1 = prs.slides.add_slide(blank_layout)

    # 背景色
    bg = slide1.background.fill
    bg.solid()
    bg.fore_color.rgb = PRIMARY

    # アクセントライン
    accent_bar = slide1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(2.3), Inches(10), Pt(4),
    )
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = ACCENT
    accent_bar.line.fill.background()

    # ブランド名
    txBox = slide1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(8), Inches(0.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "LEAD ONE"
    run.font.size = Pt(14)
    run.font.color.rgb = ACCENT
    run.font.bold = True

    # タイトル
    txBox2 = slide1.shapes.add_textbox(Inches(0.8), Inches(2.7), Inches(8), Inches(0.8))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    run2 = p2.add_run()
    run2.text = f"{client_name} TikTok運用レポート"
    run2.font.size = Pt(28)
    run2.font.color.rgb = WHITE
    run2.font.bold = True

    # 期間
    txBox3 = slide1.shapes.add_textbox(Inches(0.8), Inches(3.5), Inches(8), Inches(0.5))
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    run3 = p3.add_run()
    run3.text = period
    run3.font.size = Pt(16)
    run3.font.color.rgb = GRAY_400

    # ============================
    # P2: KPI数値報告
    # ============================
    slide2 = prs.slides.add_slide(blank_layout)
    _add_header(slide2, client_name, period)
    _add_slide_title(slide2, "数値報告")

    # KPIテーブル
    kpi_rows = [
        ("総再生数", context.get("total_views"), context.get("mom_views")),
        ("いいね", context.get("total_likes"), context.get("mom_likes")),
        ("コメント", context.get("total_comments"), context.get("mom_comments")),
        ("シェア", context.get("total_shares"), context.get("mom_shares")),
        ("プロフィール閲覧", context.get("total_profile_views"), None),
        ("エンゲージメント率", f"{context.get('engagement_rate', 0):.2f}%", None),
        ("投稿数", context.get("post_count"), None),
        ("平均再生数/投稿", context.get("avg_views_per_post"), None),
    ]

    tbl = slide2.shapes.add_table(
        len(kpi_rows) + 1, 3,
        Inches(0.5), Inches(1.2), Inches(9), Inches(3.8),
    ).table

    # ヘッダー
    for ci, header in enumerate(["指標", "今月実績", "前月比"]):
        cell = tbl.cell(0, ci)
        _set_cell_text(cell, header, size=9, bold=True, color=WHITE,
                       align=PP_ALIGN.CENTER if ci > 0 else PP_ALIGN.LEFT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = SUB

    # データ行
    for ri, (label, value, mom) in enumerate(kpi_rows, start=1):
        _set_cell_text(tbl.cell(ri, 0), label, size=9, bold=True, color=GRAY_800)
        val_str = _fmt_num(value) if not isinstance(value, str) else value
        _set_cell_text(tbl.cell(ri, 1), val_str, size=10, bold=True,
                       color=GRAY_800, align=PP_ALIGN.CENTER)
        mom_str = _fmt_pct(mom) if mom is not None else "--"
        mom_color = GREEN if mom and mom > 0 else RED if mom and mom < 0 else GRAY_400
        _set_cell_text(tbl.cell(ri, 2), mom_str, size=9, bold=True,
                       color=mom_color, align=PP_ALIGN.CENTER)
        # 行背景
        if ri % 2 == 0:
            for ci in range(3):
                tbl.cell(ri, ci).fill.solid()
                tbl.cell(ri, ci).fill.fore_color.rgb = GRAY_50

    # ============================
    # P3: 動画毎レポート
    # ============================
    posts = context.get("posts", [])
    if posts:
        # 1スライド最大15行
        chunk_size = 15
        for chunk_idx in range(0, len(posts), chunk_size):
            chunk = posts[chunk_idx:chunk_idx + chunk_size]
            slide3 = prs.slides.add_slide(blank_layout)
            _add_header(slide3, client_name, period)
            suffix = f" ({chunk_idx + 1}〜{chunk_idx + len(chunk)}件)" if len(posts) > chunk_size else ""
            _add_slide_title(slide3, f"動画毎レポート{suffix}")

            cols = ["タイトル", "投稿日", "再生数", "いいね", "コメント", "シェア", "ENG率"]
            col_widths = [Inches(3.2), Inches(0.9), Inches(0.9), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.7)]

            tbl = slide3.shapes.add_table(
                len(chunk) + 1, len(cols),
                Inches(0.4), Inches(1.2), Inches(9.2), Inches(4.0),
            ).table

            for ci, (header, w) in enumerate(zip(cols, col_widths)):
                tbl.columns[ci].width = w
                cell = tbl.cell(0, ci)
                _set_cell_text(cell, header, size=7, bold=True, color=WHITE,
                               align=PP_ALIGN.CENTER if ci > 0 else PP_ALIGN.LEFT)
                cell.fill.solid()
                cell.fill.fore_color.rgb = SUB

            for ri, post in enumerate(chunk, start=1):
                p = post if isinstance(post, SimpleNamespace) else SimpleNamespace(**post)
                caption = p.caption if len(p.caption) <= 25 else p.caption[:24] + "…"
                _set_cell_text(tbl.cell(ri, 0), caption, size=7, color=GRAY_800)
                _set_cell_text(tbl.cell(ri, 1), getattr(p, "post_date_display", ""),
                               size=7, color=GRAY_600, align=PP_ALIGN.CENTER)
                _set_cell_text(tbl.cell(ri, 2), _fmt_num(p.views),
                               size=7, bold=True, color=GRAY_800, align=PP_ALIGN.RIGHT)
                _set_cell_text(tbl.cell(ri, 3), _fmt_num(p.likes),
                               size=7, color=GRAY_600, align=PP_ALIGN.RIGHT)
                _set_cell_text(tbl.cell(ri, 4), _fmt_num(p.comments),
                               size=7, color=GRAY_600, align=PP_ALIGN.RIGHT)
                _set_cell_text(tbl.cell(ri, 5), _fmt_num(p.shares),
                               size=7, color=GRAY_600, align=PP_ALIGN.RIGHT)
                eng = getattr(p, "engagement_rate", 0) or 0
                _set_cell_text(tbl.cell(ri, 6), f"{eng:.1f}%",
                               size=7, color=GRAY_600, align=PP_ALIGN.CENTER)
                if ri % 2 == 0:
                    for ci in range(len(cols)):
                        tbl.cell(ri, ci).fill.solid()
                        tbl.cell(ri, ci).fill.fore_color.rgb = GRAY_50

    # ============================
    # P4: トップ投稿ハイライト
    # ============================
    top_posts = context.get("top_posts", [])
    if top_posts:
        slide4 = prs.slides.add_slide(blank_layout)
        _add_header(slide4, client_name, period)
        _add_slide_title(slide4, f"トップ{min(len(top_posts), 5)}投稿")

        for i, post in enumerate(top_posts[:5]):
            p = post if isinstance(post, SimpleNamespace) else SimpleNamespace(**post)
            col = i % 3
            row = i // 3
            left = Inches(0.5 + col * 3.1)
            top = Inches(1.2 + row * 2.1)

            # カード背景
            card = slide4.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                left, top, Inches(2.8), Inches(1.9),
            )
            card.fill.solid()
            card.fill.fore_color.rgb = WHITE
            card.line.color.rgb = GRAY_200
            card.line.width = Pt(1)

            # ランクバッジ
            badge = slide4.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                left + Inches(0.1), top + Inches(0.1), Inches(0.5), Inches(0.3),
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = ACCENT
            badge.line.fill.background()
            badge_tf = badge.text_frame
            badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            badge_run = badge_tf.paragraphs[0].add_run()
            badge_run.text = f"#{i + 1}"
            badge_run.font.size = Pt(9)
            badge_run.font.color.rgb = WHITE
            badge_run.font.bold = True

            # 再生数
            views_box = slide4.shapes.add_textbox(
                left + Inches(0.7), top + Inches(0.08), Inches(1.8), Inches(0.35),
            )
            vtf = views_box.text_frame
            vtf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            vrun = vtf.paragraphs[0].add_run()
            vrun.text = f"{_fmt_num(p.views)} 再生"
            vrun.font.size = Pt(11)
            vrun.font.bold = True
            vrun.font.color.rgb = PRIMARY

            # タイトル
            caption = p.caption if len(p.caption) <= 30 else p.caption[:29] + "…"
            title_box = slide4.shapes.add_textbox(
                left + Inches(0.15), top + Inches(0.5), Inches(2.5), Inches(0.5),
            )
            ttf = title_box.text_frame
            ttf.word_wrap = True
            trun = ttf.paragraphs[0].add_run()
            trun.text = caption
            trun.font.size = Pt(8)
            trun.font.color.rgb = GRAY_800

            # メトリクス
            metrics = f"♡ {_fmt_num(p.likes)}　💬 {_fmt_num(p.comments)}　↗ {_fmt_num(p.shares)}"
            metrics_box = slide4.shapes.add_textbox(
                left + Inches(0.15), top + Inches(1.15), Inches(2.5), Inches(0.3),
            )
            mtf = metrics_box.text_frame
            mrun = mtf.paragraphs[0].add_run()
            mrun.text = metrics
            mrun.font.size = Pt(7)
            mrun.font.color.rgb = GRAY_600

            # 日付
            date_box = slide4.shapes.add_textbox(
                left + Inches(0.15), top + Inches(1.45), Inches(2.5), Inches(0.3),
            )
            dtf = date_box.text_frame
            drun = dtf.paragraphs[0].add_run()
            drun.text = getattr(p, "post_date_display", "")
            drun.font.size = Pt(7)
            drun.font.color.rgb = GRAY_400

    # ============================
    # P5: 総評・改善案
    # ============================
    ai = context.get("ai_commentary", {})
    slide5 = prs.slides.add_slide(blank_layout)
    _add_header(slide5, client_name, period)
    _add_slide_title(slide5, "総評・改善案")

    sections = [
        ("総評", ai.get("best_post_analysis", ""), Inches(0.5), Inches(1.2), Inches(4.2), Inches(1.8)),
        ("改善提案", ai.get("improvement_suggestions", ""), Inches(5.0), Inches(1.2), Inches(4.5), Inches(1.8)),
        ("来月のアクションプラン", ai.get("next_month_plan", ""), Inches(0.5), Inches(3.2), Inches(9.0), Inches(2.0)),
    ]

    for title, body, left, top, width, height in sections:
        # カード背景
        card = slide5.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left, top, width, height,
        )
        card.fill.solid()
        card.fill.fore_color.rgb = GRAY_50
        card.line.color.rgb = GRAY_200
        card.line.width = Pt(0.5)

        # セクションタイトル
        title_box = slide5.shapes.add_textbox(
            left + Inches(0.15), top + Inches(0.08), width - Inches(0.3), Inches(0.25),
        )
        ttf = title_box.text_frame
        trun = ttf.paragraphs[0].add_run()
        trun.text = title
        trun.font.size = Pt(9)
        trun.font.bold = True
        trun.font.color.rgb = SUB

        # 本文
        body_box = slide5.shapes.add_textbox(
            left + Inches(0.15), top + Inches(0.35),
            width - Inches(0.3), height - Inches(0.45),
        )
        btf = body_box.text_frame
        btf.word_wrap = True
        # 長すぎる場合は切り詰め
        max_chars = int(width.inches * height.inches * 80)
        body_text = body if len(body) <= max_chars else body[:max_chars] + "…"
        brun = btf.paragraphs[0].add_run()
        brun.text = body_text
        brun.font.size = Pt(7)
        brun.font.color.rgb = GRAY_800

    # ============================
    # 保存
    # ============================
    prs.save(str(output_path))
    logger.info("PPTX生成完了: %s", output_path)
    return output_path
