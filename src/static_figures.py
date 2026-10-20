"""Static Matplotlib figures (PNG) for the written report."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import analysis
from .common import (
    BASELINE_YEARS, BLUE, DIVERGING, FIGURE_DIR, GRAY, LOCKDOWN_YEAR, ORANGE,
    POLLUTANT_NAMES, WINDOWS, WINDOW_LABELS,
)

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2de"
BASE_LABEL = f"{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]} average"


def _setup():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })


def fig_baseline(df, city, pollutant, out: Path):
    c = analysis.daily_curve(df, city, pollutant)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    if "base_min" in c:
        ax.fill_between(c["Date"], c["base_min"], c["base_max"], color=BLUE, alpha=0.15,
                        linewidth=0, label=f"{BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]} range")
        ax.plot(c["Date"], c["base_mean"], color=BLUE, lw=2, label=BASE_LABEL)
    ax.plot(c["Date"], c["y2020"], color=ORANGE, lw=2, label=str(LOCKDOWN_YEAR))
    s, e = WINDOWS["lockdown"]
    x0, x1 = pd.Timestamp(f"{LOCKDOWN_YEAR}-{s}"), pd.Timestamp(f"{LOCKDOWN_YEAR}-{e}")
    ax.axvspan(x0, x1, color=GRAY, alpha=0.14, lw=0)
    ax.text(x0, ax.get_ylim()[1], " Lockdown", va="top", color=GRAY)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_ylabel(POLLUTANT_NAMES.get(pollutant, pollutant))
    ax.set_title(f"{city}: {pollutant} in 2020 vs normal years")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_dumbbell(summary, pollutant, out: Path):
    s = summary[(summary["Pollutant"] == pollutant) & (summary["window"] == "lockdown")]
    s = s.sort_values("pct_change", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.38 * len(s) + 1.6)))
    y = np.arange(len(s))
    ax.hlines(y, s["y2020"], s["baseline"], color=GRAY, lw=2, zorder=1)
    ax.scatter(s["baseline"], y, color=BLUE, s=70, zorder=2, edgecolor=SURFACE, lw=1.5, label=BASE_LABEL)
    ax.scatter(s["y2020"], y, color=ORANGE, s=70, zorder=3, edgecolor=SURFACE, lw=1.5, label=str(LOCKDOWN_YEAR))
    ax.set_yticks(y, s["City"]); ax.grid(axis="y", visible=False)
    ax.set_xlabel(POLLUTANT_NAMES.get(pollutant, pollutant))
    ax.set_title(f"{pollutant}: lockdown vs normal years (25 Mar - 31 May)")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_pause_or_fix(pf, pollutant, out: Path):
    pf = pf.sort_values("pct_lockdown", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, max(3.8, 0.5 * len(pf) + 1.6)))
    y = np.arange(len(pf)); h = 0.36
    ax.barh(y - h / 2, pf["pct_lockdown"], height=h - 0.04, color=BLUE, label=WINDOW_LABELS["lockdown"])
    ax.barh(y + h / 2, pf["pct_june"], height=h - 0.04, color=ORANGE, label=WINDOW_LABELS["june"])
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(y, pf["City"]); ax.grid(axis="y", visible=False)
    ax.set_xlabel("% change vs 2017-2019 on the same dates")
    ax.set_title(f"{pollutant}: did the improvement last into June?")
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_correlation(corr, out: Path):
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap=cmap, vmin=-1, vmax=1, ax=ax,
                linewidths=2, linecolor=SURFACE, cbar_kws={"label": "correlation (r)"})
    ax.grid(False); ax.set_title("How pollutants move together")
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def make_all(df, summary, kept, pollutant="AQI", out_dir: Path = FIGURE_DIR) -> list[Path]:
    _setup()
    out_dir.mkdir(parents=True, exist_ok=True)
    city = "Delhi" if "Delhi" in kept else kept[0]
    pf = analysis.pause_or_fix(summary, pollutant)
    files = [
        out_dir / f"fig1_baseline_vs_2020_{city}.png",
        out_dir / "fig2_lockdown_dumbbell.png",
        out_dir / "fig3_pause_or_fix.png",
        out_dir / "fig4_correlation.png",
    ]
    fig_baseline(df, city, pollutant, files[0])
    fig_dumbbell(summary, pollutant, files[1])
    fig_pause_or_fix(pf, pollutant, files[2])
    fig_correlation(analysis.correlation(df, kept), files[3])
    return files
