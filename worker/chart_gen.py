"""グラフ生成モジュール

matplotlibで日別再生数・エンゲージメント率のグラフをPNG画像として生成し、
base64エンコードされたdata URIを返す。
"""

from __future__ import annotations

import base64
import io
import logging

import matplotlib
matplotlib.use("Agg")  # GUIバックエンドを使わない
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

# カラー定義
COLOR_ACCENT = "#E94560"
COLOR_SUB = "#0F3460"
COLOR_GRID = "#E0E0E0"
COLOR_BG = "#FFFFFF"

# Noto Sans JP がシステムにあれば使用、なければデフォルト
_FONT_FAMILY = "sans-serif"
for font in fm.findSystemFonts():
    if "NotoSansJP" in font or "NotoSansCJKjp" in font:
        _font_prop = fm.FontProperties(fname=font)
        _FONT_FAMILY = _font_prop.get_name()
        break

plt.rcParams.update({
    "font.family": _FONT_FAMILY,
    "axes.facecolor": COLOR_BG,
    "figure.facecolor": COLOR_BG,
    "axes.grid": True,
    "grid.color": COLOR_GRID,
    "grid.linewidth": 0.5,
})


def _fig_to_base64(fig: plt.Figure) -> str:
    """matplotlibのFigureをbase64 data URIに変換する。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.standard_b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _format_date_label(date_str: str) -> str:
    """YYYY-MM-DD を M/D 形式に変換する。"""
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}/{int(parts[2])}"
    return date_str


def generate_views_chart(daily_data: list[dict]) -> str:
    """日別再生数グラフを生成し、base64エンコードされたdata URIを返す。

    Args:
        daily_data: 日別データのリスト。各要素に "date" と "views" キーが必要。

    Returns:
        base64エンコードされたPNG画像のdata URI
    """
    if not daily_data:
        logger.warning("グラフ生成: データがありません")
        return ""

    dates = [_format_date_label(d["date"]) for d in daily_data]
    views = [d["views"] for d in daily_data]

    fig, ax = plt.subplots(figsize=(7.09, 2.76))  # 約180mm x 70mm
    ax.plot(dates, views, color=COLOR_ACCENT, linewidth=2, marker="o", markersize=3)
    ax.fill_between(range(len(dates)), views, alpha=0.1, color=COLOR_ACCENT)
    ax.set_ylabel("再生数", fontsize=10)
    ax.set_title("日別再生数", fontsize=12, fontweight="bold", pad=10)

    # X軸ラベルの間引き（多すぎる場合）
    if len(dates) > 15:
        step = len(dates) // 10
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], fontsize=8)
    else:
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, fontsize=8, rotation=45, ha="right")

    # Y軸のフォーマット（千単位）
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x / 1000:.0f}K" if x >= 1000 else f"{x:.0f}")
    )

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_engagement_chart(daily_data: list[dict]) -> str:
    """エンゲージメント率推移グラフを生成し、base64エンコードされたdata URIを返す。

    Args:
        daily_data: 日別データのリスト。各要素に "date" と "engagement_rate" キーが必要。

    Returns:
        base64エンコードされたPNG画像のdata URI
    """
    if not daily_data:
        logger.warning("グラフ生成: データがありません")
        return ""

    dates = [_format_date_label(d["date"]) for d in daily_data]
    rates = [d["engagement_rate"] for d in daily_data]

    fig, ax = plt.subplots(figsize=(7.09, 2.76))
    ax.plot(dates, rates, color=COLOR_SUB, linewidth=2, marker="o", markersize=3)
    ax.fill_between(range(len(dates)), rates, alpha=0.1, color=COLOR_SUB)
    ax.set_ylabel("エンゲージメント率 (%)", fontsize=10)
    ax.set_title("エンゲージメント率推移", fontsize=12, fontweight="bold", pad=10)

    if len(dates) > 15:
        step = len(dates) // 10
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], fontsize=8)
    else:
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, fontsize=8, rotation=45, ha="right")

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

    fig.tight_layout()
    return _fig_to_base64(fig)
