"""
charts.py — Matplotlib visualisations for the expense tracker.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from rich.console import Console
from database import get_monthly_summary, get_spending_by_category

console = Console()


# ── Shared style ────────────────────────────────────────────────────────────

PALETTE = [
    "#6C63FF", "#FF6584", "#43D9AD", "#FFD166", "#EF8C8C",
    "#56CFE1", "#FF9F1C", "#A8DADC", "#E63946", "#2EC4B6",
]

def _apply_dark_theme(fig, ax):
    """Apply a consistent dark background theme."""
    fig.patch.set_facecolor("#1E1E2E")
    ax.set_facecolor("#2A2A3E")
    ax.tick_params(colors="#CDD6F4")
    ax.xaxis.label.set_color("#CDD6F4")
    ax.yaxis.label.set_color("#CDD6F4")
    ax.title.set_color("#CDD6F4")
    for spine in ax.spines.values():
        spine.set_edgecolor("#45475A")


# ── Bar chart — Monthly spending ─────────────────────────────────────────────

def plot_monthly_bar():
    summary = get_monthly_summary()
    if not summary:
        console.print("[yellow]No data available for the monthly chart.[/]")
        return

    months = [s["month"] for s in summary]
    totals = [s["total"] for s in summary]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(months, totals, color=PALETTE[:len(months)], width=0.55, zorder=3)
    ax.set_title("Monthly Spending", fontsize=16, fontweight="bold", pad=14)
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Amount (₹)", fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x:,.2f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, val in zip(bars, totals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(totals) * 0.01,
            f"₹{val:,.2f}",
            ha="center", va="bottom", fontsize=9, color="#CDD6F4",
        )

    _apply_dark_theme(fig, ax)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.show()


# ── Pie chart — Spending by category ────────────────────────────────────────

def plot_category_pie():
    breakdown = get_spending_by_category()
    if not breakdown:
        console.print("[yellow]No data available for the category chart.[/]")
        return

    cats   = [b["category"] for b in breakdown]
    totals = [b["total"]    for b in breakdown]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        totals,
        labels=cats,
        autopct="%1.1f%%",
        colors=PALETTE[:len(cats)],
        startangle=140,
        pctdistance=0.82,
        wedgeprops=dict(edgecolor="#1E1E2E", linewidth=2),
    )
    for t in texts:
        t.set_color("#CDD6F4")
    for at in autotexts:
        at.set_color("#1E1E2E")
        at.set_fontweight("bold")

    ax.set_title("Spending by Category", fontsize=16, fontweight="bold", pad=14, color="#CDD6F4")
    fig.patch.set_facecolor("#1E1E2E")
    plt.tight_layout()
    plt.show()


# ── Combined — show both ─────────────────────────────────────────────────────

def show_graphs():
    """Render both charts side-by-side in separate windows."""
    plot_monthly_bar()
    plot_category_pie()
