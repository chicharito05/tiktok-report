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

# カラー定義（PPTX パレットと統一）
COLOR_ACCENT = "#374BF5"
COLOR_ACCENT_LIGHT = "#8B9AFF"
COLOR_SUB = "#1A1A2E"
COLOR_GRID = "#E5E7EB"
COLOR_BG = "#F9FAFB"
COLOR_TEXT_PRIMARY = "#1A1A2E"
COLOR_TEXT_MUTED = "#9CA3AF"

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


def generate_dow_chart(dow_data: list[dict]) -> io.BytesIO:
    """曜日別パフォーマンスの棒グラフを PNG BytesIO で返す。

    Args:
        dow_data: [{"day_of_week": "月", "avg_views": 1234, "post_count": 3, ...}, ...]
    """
    if not dow_data:
        return _empty_chart_buf("曜日別データなし")

    day_order = ["月", "火", "水", "木", "金", "土", "日"]
    data_map = {d["day_of_week"]: d for d in dow_data}
    days = [d for d in day_order if d in data_map]
    if not days:
        days = [d["day_of_week"] for d in dow_data]

    avg_views = [data_map.get(d, {}).get("avg_views", 0) for d in days]
    post_counts = [data_map.get(d, {}).get("post_count", 0) for d in days]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(days, avg_views, color=COLOR_ACCENT, alpha=0.85, width=0.5, zorder=3)

    max_v = max(avg_views) if avg_views else 1
    for bar, count in zip(bars, post_counts):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + max_v * 0.02,
                f"{int(h):,}", ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=COLOR_TEXT_PRIMARY)
        ax.text(bar.get_x() + bar.get_width() / 2, h + max_v * 0.08,
                f"({count}本)", ha="center", va="bottom",
                fontsize=8, color=COLOR_TEXT_MUTED)

    ax.set_ylabel("平均再生数", fontsize=11, color=COLOR_TEXT_PRIMARY)
    ax.tick_params(axis="x", labelsize=12, colors=COLOR_TEXT_PRIMARY)
    ax.tick_params(axis="y", labelsize=10, colors=COLOR_TEXT_MUTED)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.grid(axis="y", alpha=0.3, color=COLOR_GRID)
    ax.set_axisbelow(True)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_hour_chart(hour_data: list[dict]) -> io.BytesIO:
    """時間帯別パフォーマンスの棒グラフを PNG BytesIO で返す。

    Args:
        hour_data: [{"hour": 9, "avg_views": 1234, "post_count": 2, ...}, ...]
    """
    if not hour_data:
        return _empty_chart_buf("時間帯別データなし")

    sorted_data = sorted(hour_data, key=lambda x: x.get("hour", 0))
    hours = [f"{d['hour']}時" for d in sorted_data]
    avg_views = [d.get("avg_views", 0) for d in sorted_data]

    max_val = max(avg_views) if avg_views else 1
    colors = [COLOR_ACCENT if v >= max_val * 0.8 else COLOR_ACCENT_LIGHT for v in avg_views]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(hours, avg_views, color=colors, alpha=0.85, width=0.6, zorder=3)

    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + max_val * 0.02,
                    f"{int(h):,}", ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=COLOR_TEXT_PRIMARY)

    ax.set_ylabel("平均再生数", fontsize=11, color=COLOR_TEXT_PRIMARY)
    ax.tick_params(axis="x", labelsize=9, colors=COLOR_TEXT_PRIMARY, rotation=45)
    ax.tick_params(axis="y", labelsize=10, colors=COLOR_TEXT_MUTED)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.grid(axis="y", alpha=0.3, color=COLOR_GRID)
    ax.set_axisbelow(True)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _empty_chart_buf(message: str) -> io.BytesIO:
    """データがない場合のプレースホルダー画像を BytesIO で返す。"""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=14, color=COLOR_TEXT_MUTED)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
