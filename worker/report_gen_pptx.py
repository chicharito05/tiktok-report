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
PRIMARY = RGBColor(0x0F, 0x17, 0x2A)
ACCENT = RGBColor(0xE9, 0x45, 0x60)
SUB = RGBColor(0x1E, 0x3A, 0x5F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF4, 0xF5, 0xF7)
GRAY_100 = RGBColor(0xF1, 0xF3, 0xF5)
GRAY_200 = RGBColor(0xE2, 0xE5, 0xE9)
GRAY_400 = RGBColor(0x9C, 0xA3, 0xAF)
GRAY_600 = RGBColor(0x4B, 0x55, 0x63)
GRAY_800 = RGBColor(0x1F, 0x2A, 0x37)
GREEN = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xDC, 0x26, 0x26)
BLUE = RGBColor(0x25, 0x63, 0xEB)
AMBER = RGBColor(0xD9, 0x77, 0x06)

SLIDE_WIDTH = Inches(13.333)  # ワイドスクリーン 16:9
SLIDE_HEIGHT = Inches(7.5)


def _fmt(n) -> str:
    if n is None:
        return "--"
    if isinstance(n, float) and n == int(n):
        n = int(n)
    if isinstance(n, int):
        if n >= 10000:
            return f"{n / 10000:.1f}万"
        return f"{n:,}"
    return str(n)


def _pct(n) -> str:
    if n is None:
        return "--"
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def _set_cell(cell, text: str, size: int = 10, bold: bool = False,
              color: RGBColor = GRAY_800, align=PP_ALIGN.LEFT, bg: RGBColor | None = None):
    """テーブルセルのテキスト+スタイルを設定"""
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.alignment = align
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Arial"
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = Emu(54864)
    cell.margin_right = Emu(54864)
    cell.margin_top = Emu(27432)
    cell.margin_bottom = Emu(27432)
    if bg:
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg


def _add_header(slide, client_name: str, period: str):
    """スライドヘッダー"""
    # ブランド名
    txBox = slide.shapes.add_textbox(Inches(0.6), Inches(0.25), Inches(2.5), Inches(0.4))
    tf = txBox.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "LEAD ONE"
    run.font.size = Pt(12)
    run.font.color.rgb = ACCENT
    run.font.bold = True
    run.font.name = "Arial"

    # クライアント + 期間
    txBox2 = slide.shapes.add_textbox(Inches(5), Inches(0.25), Inches(7.8), Inches(0.4))
    tf2 = txBox2.text_frame
    tf2.word_wrap = False
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    run2 = p2.add_run()
    run2.text = f"{client_name}　|　{period}"
    run2.font.size = Pt(10)
    run2.font.color.rgb = GRAY_400
    run2.font.name = "Arial"

    # 区切り線
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(0.7), Inches(12.1), Pt(1.5),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = GRAY_200
    line.line.fill.background()


def _add_title(slide, title: str, top: float = 0.9):
    """スライドタイトル（左アクセントバー付き）"""
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(top), Pt(5), Inches(0.4),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    txBox = slide.shapes.add_textbox(Inches(0.9), Inches(top - 0.02), Inches(10), Inches(0.45))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = PRIMARY
    run.font.name = "Arial"


def _add_subtitle(slide, text: str, left: float, top: float, width: float = 3.0):
    """小見出し"""
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.3))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = GRAY_400
    run.font.name = "Arial"


def _add_kpi_card(slide, left: float, top: float, width: float, height: float,
                  label: str, value: str, sub: str = "", color: RGBColor = GRAY_800):
    """KPIカード"""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height),
    )
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = GRAY_200
    card.line.width = Pt(0.75)

    # ラベル
    lb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.1), Inches(width - 0.3), Inches(0.2))
    ltf = lb.text_frame
    lp = ltf.paragraphs[0]
    lr = lp.add_run()
    lr.text = label
    lr.font.size = Pt(8)
    lr.font.color.rgb = GRAY_400
    lr.font.name = "Arial"

    # 値
    vb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.32), Inches(width - 0.3), Inches(0.35))
    vtf = vb.text_frame
    vp = vtf.paragraphs[0]
    vr = vp.add_run()
    vr.text = value
    vr.font.size = Pt(18)
    vr.font.bold = True
    vr.font.color.rgb = color
    vr.font.name = "Arial"

    # サブテキスト
    if sub:
        sb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.65), Inches(width - 0.3), Inches(0.2))
        stf = sb.text_frame
        sp = stf.paragraphs[0]
        sr = sp.add_run()
        sr.text = sub
        sr.font.size = Pt(8)
        sr.font.bold = True
        sr.font.color.rgb = GREEN if sub.startswith("+") else RED if sub.startswith("-") else GRAY_400
        sr.font.name = "Arial"


def _add_text_card(slide, left: float, top: float, width: float, height: float,
                   title: str, body: str, title_color: RGBColor = SUB):
    """テキストカード（総評・改善案用）"""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height),
    )
    card.fill.solid()
    card.fill.fore_color.rgb = LIGHT_BG
    card.line.color.rgb = GRAY_200
    card.line.width = Pt(0.5)

    # タイトルバー
    title_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(0.35),
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = title_color
    title_bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.05), Inches(width - 0.4), Inches(0.25))
    ttf = tb.text_frame
    tr = ttf.paragraphs[0].add_run()
    tr.text = title
    tr.font.size = Pt(10)
    tr.font.bold = True
    tr.font.color.rgb = WHITE
    tr.font.name = "Arial"

    # 本文
    bb = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.45), Inches(width - 0.4), Inches(height - 0.55),
    )
    btf = bb.text_frame
    btf.word_wrap = True
    br = btf.paragraphs[0].add_run()
    max_chars = int(width * height * 55)
    br.text = body if len(body) <= max_chars else body[:max_chars] + "…"
    br.font.size = Pt(9)
    br.font.color.rgb = GRAY_800
    br.font.name = "Arial"


def generate_pptx(context: dict, output_path: Path) -> Path:
    """レポートのPPTXを生成する"""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank = prs.slide_layouts[6]

    cn = context.get("client_name", "")
    period = context.get("period", "")
    ai = context.get("ai_commentary", {})

    # ================================================================
    # P1: 表紙
    # ================================================================
    s1 = prs.slides.add_slide(blank)
    bg = s1.background.fill
    bg.solid()
    bg.fore_color.rgb = PRIMARY

    # 左アクセントバー
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.15), SLIDE_HEIGHT)
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    # ブランド
    b1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.5), Inches(5), Inches(0.5))
    r1 = b1.text_frame.paragraphs[0].add_run()
    r1.text = "LEAD ONE"
    r1.font.size = Pt(16)
    r1.font.color.rgb = ACCENT
    r1.font.bold = True
    r1.font.name = "Arial"

    # 水平線
    hl = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(2.8), Inches(6), Pt(3))
    hl.fill.solid()
    hl.fill.fore_color.rgb = ACCENT
    hl.line.fill.background()

    # タイトル
    t1 = s1.shapes.add_textbox(Inches(1.2), Inches(3.1), Inches(10), Inches(1.0))
    tr1 = t1.text_frame.paragraphs[0].add_run()
    tr1.text = f"{cn}\nTikTok Monthly Report"
    tr1.font.size = Pt(32)
    tr1.font.color.rgb = WHITE
    tr1.font.bold = True
    tr1.font.name = "Arial"

    # 期間
    p1 = s1.shapes.add_textbox(Inches(1.2), Inches(4.5), Inches(8), Inches(0.5))
    pr1 = p1.text_frame.paragraphs[0].add_run()
    pr1.text = period
    pr1.font.size = Pt(18)
    pr1.font.color.rgb = GRAY_400
    pr1.font.name = "Arial"

    # 月間総括（AIの一言コメント）
    overall = ai.get("overall_assessment", "")
    if overall:
        o1 = s1.shapes.add_textbox(Inches(1.2), Inches(5.5), Inches(10), Inches(0.8))
        otf = o1.text_frame
        otf.word_wrap = True
        orun = otf.paragraphs[0].add_run()
        orun.text = overall
        orun.font.size = Pt(11)
        orun.font.color.rgb = RGBColor(0xA0, 0xA8, 0xB8)
        orun.font.italic = True
        orun.font.name = "Arial"

    # ================================================================
    # P2: KPIダッシュボード
    # ================================================================
    s2 = prs.slides.add_slide(blank)
    _add_header(s2, cn, period)
    _add_title(s2, "KPIダッシュボード")

    mom_views = context.get("mom_views")
    mom_likes = context.get("mom_likes")
    mom_comments = context.get("mom_comments")
    mom_shares = context.get("mom_shares")

    kpis = [
        ("総再生数", _fmt(context.get("total_views")), _pct(mom_views) if mom_views is not None else "", BLUE),
        ("いいね", _fmt(context.get("total_likes")), _pct(mom_likes) if mom_likes is not None else "", ACCENT),
        ("コメント", _fmt(context.get("total_comments")), _pct(mom_comments) if mom_comments is not None else "", AMBER),
        ("シェア", _fmt(context.get("total_shares")), _pct(mom_shares) if mom_shares is not None else "", GREEN),
        ("投稿数", str(context.get("post_count", 0)) + "本", "", GRAY_800),
        ("平均再生/投稿", _fmt(context.get("avg_views_per_post")), "", GRAY_800),
    ]

    for i, (label, value, sub, color) in enumerate(kpis):
        col = i % 6
        _add_kpi_card(s2, 0.6 + col * 2.05, 1.55, 1.85, 0.95, label, value, sub, color)

    # 下段: エンゲージメント率 + プロフィール遷移率 + フォロワー増減
    eng_rate = context.get("engagement_rate", 0)
    prof_rate = context.get("profile_transition_rate")
    fg = context.get("follower_growth")

    row2_items = [
        ("エンゲージメント率", f"{eng_rate:.2f}%", "", BLUE),
    ]
    if prof_rate is not None:
        row2_items.append(("プロフィール遷移率", f"{prof_rate:.2f}%", "", SUB))
    if fg:
        change = fg.get("change", 0)
        row2_items.append((
            "フォロワー増減",
            f"{'+'if change>0 else ''}{_fmt(change)}",
            f"{fg['start_count']:,} → {fg['end_count']:,}",
            GREEN if change > 0 else RED,
        ))

    card_w = 12.1 / max(len(row2_items), 1)
    for i, (label, value, sub, color) in enumerate(row2_items):
        _add_kpi_card(s2, 0.6 + i * (card_w + 0.1), 2.75, card_w - 0.1, 0.95, label, value, sub, color)

    # KPIテーブル（詳細）
    _add_subtitle(s2, "詳細数値", 0.6, 3.95)
    kpi_detail = [
        ("指標", "今月実績", "前月比"),
        ("総再生数", _fmt(context.get("total_views")), _pct(mom_views)),
        ("いいね", _fmt(context.get("total_likes")), _pct(mom_likes)),
        ("コメント", _fmt(context.get("total_comments")), _pct(mom_comments)),
        ("シェア", _fmt(context.get("total_shares")), _pct(mom_shares)),
        ("プロフィール閲覧", _fmt(context.get("total_profile_views")), "--"),
        ("エンゲージメント率", f"{eng_rate:.2f}%", "--"),
        ("投稿数", str(context.get("post_count", 0)), "--"),
        ("平均再生数/投稿", _fmt(context.get("avg_views_per_post")), "--"),
    ]

    tbl = s2.shapes.add_table(len(kpi_detail), 3, Inches(0.6), Inches(4.2), Inches(12.1), Inches(3.0)).table
    tbl.columns[0].width = Inches(4.0)
    tbl.columns[1].width = Inches(4.0)
    tbl.columns[2].width = Inches(4.1)

    for ri, row in enumerate(kpi_detail):
        for ci, val in enumerate(row):
            is_header = ri == 0
            mom_val = row[2] if ci == 2 and not is_header else None
            color = WHITE if is_header else GRAY_800
            bg_color = SUB if is_header else (GRAY_100 if ri % 2 == 0 else None)

            if ci == 2 and not is_header and val not in ("--", None):
                try:
                    num = float(val.replace("+", "").replace("%", ""))
                    color = GREEN if num > 0 else RED if num < 0 else GRAY_400
                except (ValueError, AttributeError):
                    pass

            _set_cell(tbl.cell(ri, ci), val or "--", size=10, bold=is_header or ci == 1,
                      color=color, align=PP_ALIGN.CENTER if ci > 0 else PP_ALIGN.LEFT,
                      bg=bg_color)

    # ================================================================
    # P3: 動画毎レポート（ページ分割）
    # ================================================================
    posts = context.get("posts", [])
    if posts:
        chunk_size = 12
        for ci_idx in range(0, len(posts), chunk_size):
            chunk = posts[ci_idx:ci_idx + chunk_size]
            s3 = prs.slides.add_slide(blank)
            _add_header(s3, cn, period)
            suffix = f"（{ci_idx + 1}〜{ci_idx + len(chunk)}件 / 全{len(posts)}件）" if len(posts) > chunk_size else f"（全{len(posts)}件）"
            _add_title(s3, f"動画毎レポート{suffix}")

            cols = ["#", "タイトル", "投稿日", "再生数", "いいね", "コメント", "シェア", "ENG率", "完了率", "2秒率"]
            col_w = [Inches(0.4), Inches(4.0), Inches(1.1), Inches(1.1), Inches(1.0), Inches(1.0), Inches(1.0), Inches(0.9), Inches(0.8), Inches(0.8)]

            tbl = s3.shapes.add_table(len(chunk) + 1, len(cols),
                                      Inches(0.6), Inches(1.5), Inches(12.1), Inches(5.5)).table

            for ci, (header, w) in enumerate(zip(cols, col_w)):
                tbl.columns[ci].width = w
                _set_cell(tbl.cell(0, ci), header, size=9, bold=True, color=WHITE,
                          align=PP_ALIGN.CENTER if ci > 1 else PP_ALIGN.LEFT, bg=SUB)

            for ri, post in enumerate(chunk, start=1):
                p = post if isinstance(post, SimpleNamespace) else SimpleNamespace(**post)
                rank = ci_idx + ri
                caption = p.caption if len(p.caption) <= 28 else p.caption[:27] + "…"
                is_top3 = rank <= 3
                row_bg = RGBColor(0xFE, 0xF3, 0xC7) if is_top3 else (GRAY_100 if ri % 2 == 0 else None)

                _set_cell(tbl.cell(ri, 0), str(rank), size=9, bold=is_top3,
                          color=ACCENT if is_top3 else GRAY_400, align=PP_ALIGN.CENTER, bg=row_bg)
                _set_cell(tbl.cell(ri, 1), caption, size=9, bold=is_top3,
                          color=GRAY_800, bg=row_bg)
                _set_cell(tbl.cell(ri, 2), getattr(p, "post_date_display", ""),
                          size=9, color=GRAY_600, align=PP_ALIGN.CENTER, bg=row_bg)
                _set_cell(tbl.cell(ri, 3), _fmt(p.views), size=9, bold=True,
                          color=GRAY_800, align=PP_ALIGN.RIGHT, bg=row_bg)
                _set_cell(tbl.cell(ri, 4), _fmt(p.likes), size=9,
                          color=GRAY_600, align=PP_ALIGN.RIGHT, bg=row_bg)
                _set_cell(tbl.cell(ri, 5), _fmt(p.comments), size=9,
                          color=GRAY_600, align=PP_ALIGN.RIGHT, bg=row_bg)
                _set_cell(tbl.cell(ri, 6), _fmt(p.shares), size=9,
                          color=GRAY_600, align=PP_ALIGN.RIGHT, bg=row_bg)
                eng = getattr(p, "engagement_rate", 0) or 0
                _set_cell(tbl.cell(ri, 7), f"{eng:.1f}%", size=9,
                          color=GRAY_600, align=PP_ALIGN.CENTER, bg=row_bg)
                wtr = getattr(p, "watch_through_rate", None)
                _set_cell(tbl.cell(ri, 8), f"{wtr}%" if wtr else "--", size=9,
                          color=GRAY_600, align=PP_ALIGN.CENTER, bg=row_bg)
                svr = getattr(p, "two_sec_view_rate", None)
                _set_cell(tbl.cell(ri, 9), f"{svr}%" if svr else "--", size=9,
                          color=GRAY_600, align=PP_ALIGN.CENTER, bg=row_bg)

    # ================================================================
    # P4: トップ投稿ハイライト
    # ================================================================
    top_posts = context.get("top_posts", [])
    if top_posts:
        s4 = prs.slides.add_slide(blank)
        _add_header(s4, cn, period)
        _add_title(s4, f"トップ{min(len(top_posts), 5)}投稿ハイライト")

        for i, post in enumerate(top_posts[:5]):
            p = post if isinstance(post, SimpleNamespace) else SimpleNamespace(**post)
            col = i % 3
            row = i // 3
            left = 0.6 + col * 4.1
            top = 1.5 + row * 2.8

            # カード
            card = s4.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(left), Inches(top), Inches(3.8), Inches(2.5),
            )
            card.fill.solid()
            card.fill.fore_color.rgb = WHITE
            card.line.color.rgb = GRAY_200
            card.line.width = Pt(1)

            # ランクバッジ
            badge = s4.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(left + 0.15), Inches(top + 0.15), Inches(0.55), Inches(0.35),
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = ACCENT
            badge.line.fill.background()
            btf = badge.text_frame
            btf.paragraphs[0].alignment = PP_ALIGN.CENTER
            brun = btf.paragraphs[0].add_run()
            brun.text = f"#{i + 1}"
            brun.font.size = Pt(11)
            brun.font.color.rgb = WHITE
            brun.font.bold = True

            # 再生数（大きく）
            vb = s4.shapes.add_textbox(Inches(left + 0.85), Inches(top + 0.12), Inches(2.7), Inches(0.4))
            vtf = vb.text_frame
            vtf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            vr = vtf.paragraphs[0].add_run()
            vr.text = f"{_fmt(p.views)} 再生"
            vr.font.size = Pt(14)
            vr.font.bold = True
            vr.font.color.rgb = PRIMARY

            # タイトル
            caption = p.caption if len(p.caption) <= 40 else p.caption[:39] + "…"
            tb = s4.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.6), Inches(3.4), Inches(0.7))
            ttf = tb.text_frame
            ttf.word_wrap = True
            tr = ttf.paragraphs[0].add_run()
            tr.text = caption
            tr.font.size = Pt(10)
            tr.font.color.rgb = GRAY_800

            # メトリクス行
            metrics_items = [
                (f"♡ {_fmt(p.likes)}", ACCENT),
                (f"💬 {_fmt(p.comments)}", AMBER),
                (f"↗ {_fmt(p.shares)}", GREEN),
            ]
            for mi, (mtxt, mclr) in enumerate(metrics_items):
                mb = s4.shapes.add_textbox(
                    Inches(left + 0.2 + mi * 1.2), Inches(top + 1.5), Inches(1.1), Inches(0.25),
                )
                mr = mb.text_frame.paragraphs[0].add_run()
                mr.text = mtxt
                mr.font.size = Pt(9)
                mr.font.color.rgb = mclr
                mr.font.bold = True

            # ENG率 + 日付
            eng = getattr(p, "engagement_rate", 0) or 0
            info = s4.shapes.add_textbox(Inches(left + 0.2), Inches(top + 1.9), Inches(3.4), Inches(0.3))
            inf = info.text_frame.paragraphs[0].add_run()
            inf.text = f"ENG率 {eng:.1f}%　|　{getattr(p, 'post_date_display', '')}"
            inf.font.size = Pt(8)
            inf.font.color.rgb = GRAY_400

    # ================================================================
    # P4b: ワースト投稿分析
    # ================================================================
    worst_posts = context.get("worst_posts", [])
    if worst_posts:
        s4b = prs.slides.add_slide(blank)
        _add_header(s4b, cn, period)
        _add_title(s4b, "ワースト投稿分析")

        _add_subtitle(s4b, "再生数下位の投稿 — 改善ポイントの発見に活用", 0.6, 1.45)

        cols = ["タイトル", "投稿日", "再生数", "いいね", "コメント", "シェア", "ENG率"]
        tbl = s4b.shapes.add_table(len(worst_posts) + 1, len(cols),
                                    Inches(0.6), Inches(1.85), Inches(12.1), Inches(2.0)).table
        col_w = [Inches(4.5), Inches(1.2), Inches(1.3), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.5)]
        for ci, (h, w) in enumerate(zip(cols, col_w)):
            tbl.columns[ci].width = w
            _set_cell(tbl.cell(0, ci), h, size=9, bold=True, color=WHITE,
                      align=PP_ALIGN.CENTER if ci > 0 else PP_ALIGN.LEFT, bg=SUB)

        for ri, post in enumerate(worst_posts, start=1):
            p = post if isinstance(post, SimpleNamespace) else SimpleNamespace(**post)
            _set_cell(tbl.cell(ri, 0), p.caption[:35] + ("…" if len(p.caption) > 35 else ""),
                      size=9, color=GRAY_800, bg=GRAY_100 if ri % 2 == 0 else None)
            _set_cell(tbl.cell(ri, 1), getattr(p, "post_date_display", ""),
                      size=9, color=GRAY_600, align=PP_ALIGN.CENTER, bg=GRAY_100 if ri % 2 == 0 else None)
            _set_cell(tbl.cell(ri, 2), _fmt(p.views), size=9, bold=True,
                      color=RED, align=PP_ALIGN.RIGHT, bg=GRAY_100 if ri % 2 == 0 else None)
            _set_cell(tbl.cell(ri, 3), _fmt(p.likes), size=9,
                      color=GRAY_600, align=PP_ALIGN.RIGHT, bg=GRAY_100 if ri % 2 == 0 else None)
            _set_cell(tbl.cell(ri, 4), _fmt(p.comments), size=9,
                      color=GRAY_600, align=PP_ALIGN.RIGHT, bg=GRAY_100 if ri % 2 == 0 else None)
            _set_cell(tbl.cell(ri, 5), _fmt(p.shares), size=9,
                      color=GRAY_600, align=PP_ALIGN.RIGHT, bg=GRAY_100 if ri % 2 == 0 else None)
            eng = getattr(p, "engagement_rate", 0) or 0
            _set_cell(tbl.cell(ri, 6), f"{eng:.1f}%", size=9,
                      color=GRAY_600, align=PP_ALIGN.CENTER, bg=GRAY_100 if ri % 2 == 0 else None)

    # ================================================================
    # P5: 曜日別・時間帯別パフォーマンス + エンゲージメント構成
    # ================================================================
    dow = context.get("day_of_week_performance", [])
    hour = context.get("hour_performance", [])
    eng_comp = context.get("engagement_composition", {})

    if dow or hour or eng_comp:
        s5 = prs.slides.add_slide(blank)
        _add_header(s5, cn, period)
        _add_title(s5, "投稿パフォーマンス分析")

        # 曜日別テーブル
        if dow:
            _add_subtitle(s5, "曜日別 平均再生数", 0.6, 1.5)
            tbl_dow = s5.shapes.add_table(2, 7, Inches(0.6), Inches(1.8), Inches(7.0), Inches(1.0)).table
            for ci, d in enumerate(dow):
                tbl_dow.columns[ci].width = Inches(1.0)
                _set_cell(tbl_dow.cell(0, ci), d["day"], size=10, bold=True,
                          color=WHITE, align=PP_ALIGN.CENTER, bg=SUB)
                val = _fmt(d["avg_views"]) if d["count"] > 0 else "--"
                best_day = max(dow, key=lambda x: x["avg_views"]) if dow else None
                is_best = best_day and d["day"] == best_day["day"] and d["avg_views"] > 0
                _set_cell(tbl_dow.cell(1, ci), f"{val}\n({d['count']}本)", size=10, bold=is_best,
                          color=ACCENT if is_best else GRAY_800, align=PP_ALIGN.CENTER,
                          bg=RGBColor(0xFE, 0xF3, 0xC7) if is_best else LIGHT_BG)

        # 時間帯テーブル
        if hour:
            _add_subtitle(s5, "投稿時間帯別 平均再生数", 0.6, 3.1)
            n_hours = min(len(hour), 12)
            tbl_hr = s5.shapes.add_table(2, n_hours, Inches(0.6), Inches(3.4), Inches(12.1), Inches(0.9)).table
            best_hr = max(hour, key=lambda x: x["avg_views"]) if hour else None
            for ci, h in enumerate(hour[:n_hours]):
                tbl_hr.columns[ci].width = Inches(12.1 / n_hours)
                _set_cell(tbl_hr.cell(0, ci), f"{h['hour']}時", size=9, bold=True,
                          color=WHITE, align=PP_ALIGN.CENTER, bg=SUB)
                is_best = best_hr and h["hour"] == best_hr["hour"]
                _set_cell(tbl_hr.cell(1, ci), f"{_fmt(h['avg_views'])}\n({h['count']}本)",
                          size=9, bold=is_best, color=ACCENT if is_best else GRAY_800,
                          align=PP_ALIGN.CENTER,
                          bg=RGBColor(0xFE, 0xF3, 0xC7) if is_best else LIGHT_BG)

        # エンゲージメント構成比
        if eng_comp:
            _add_subtitle(s5, "エンゲージメント構成比", 0.6, 4.6)
            items = [
                ("♡ いいね", eng_comp.get("likes", 0), ACCENT),
                ("💬 コメント", eng_comp.get("comments", 0), AMBER),
                ("↗ シェア", eng_comp.get("shares", 0), GREEN),
            ]
            for i, (label, pct_val, color) in enumerate(items):
                left = 0.6 + i * 4.1
                card = s5.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    Inches(left), Inches(4.9), Inches(3.8), Inches(0.8),
                )
                card.fill.solid()
                card.fill.fore_color.rgb = WHITE
                card.line.color.rgb = GRAY_200
                card.line.width = Pt(0.5)

                lb = s5.shapes.add_textbox(Inches(left + 0.2), Inches(4.95), Inches(2.0), Inches(0.25))
                lr = lb.text_frame.paragraphs[0].add_run()
                lr.text = label
                lr.font.size = Pt(9)
                lr.font.color.rgb = GRAY_600

                vb = s5.shapes.add_textbox(Inches(left + 2.2), Inches(4.95), Inches(1.4), Inches(0.6))
                vtf = vb.text_frame
                vtf.paragraphs[0].alignment = PP_ALIGN.RIGHT
                vr = vtf.paragraphs[0].add_run()
                vr.text = f"{pct_val:.1f}%"
                vr.font.size = Pt(18)
                vr.font.bold = True
                vr.font.color.rgb = color

    # ================================================================
    # P6: 総評・分析
    # ================================================================
    s6 = prs.slides.add_slide(blank)
    _add_header(s6, cn, period)
    _add_title(s6, "総評・パフォーマンス分析")

    _add_text_card(s6, 0.6, 1.5, 12.1, 5.5,
                   "総評・パフォーマンス分析",
                   ai.get("best_post_analysis", ""),
                   title_color=SUB)

    # ================================================================
    # P7: 改善提案
    # ================================================================
    s7 = prs.slides.add_slide(blank)
    _add_header(s7, cn, period)
    _add_title(s7, "改善提案")

    _add_text_card(s7, 0.6, 1.5, 12.1, 5.5,
                   "データに基づく改善提案",
                   ai.get("improvement_suggestions", ""),
                   title_color=BLUE)

    # ================================================================
    # P8: 来月のアクションプラン
    # ================================================================
    s8 = prs.slides.add_slide(blank)
    _add_header(s8, cn, period)
    _add_title(s8, "来月のアクションプラン")

    _add_text_card(s8, 0.6, 1.5, 12.1, 5.5,
                   "来月の施策・アクションアイテム",
                   ai.get("next_month_plan", ""),
                   title_color=GREEN)

    # ================================================================
    # 保存
    # ================================================================
    prs.save(str(output_path))
    logger.info("PPTX生成完了: %s", output_path)
    return output_path
