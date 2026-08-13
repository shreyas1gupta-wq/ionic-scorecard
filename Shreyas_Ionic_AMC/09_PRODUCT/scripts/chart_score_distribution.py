# -*- coding: utf-8 -*-
"""Score distribution across the 750-stock universe (Principal ask, 2026-08-05).

Buckets 0-10, 10-20 ... 90-100 for both horizons, plus the distribution metrics that actually matter
for a scoring engine: spread, skew, and how much of the universe sits inside the decision bands.

Why the bands matter more than the shape: the engine's calls are set at 40 (quality-sell bar) and 50
(Hold line), so what a committee needs to see is not "is it bell-shaped" but "how many names sit
close enough to a threshold that a small score change flips the call".

Source: 04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored.csv (751 rows).
Output: pr_template/out/score_distribution.png + printed metrics.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NAVY = "#1B27A3"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"; GOLD = "#F2A93C"
INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; SELL = "#E0402F"

HERE = os.path.dirname(os.path.abspath(__file__))
NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = os.path.join(NIFTY, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                   "results", "full750_scored.csv")
OUT = os.path.abspath(os.path.join(HERE, "..", "pr_template", "out", "score_distribution.png"))

SELL_BAR, HOLD_LINE = 40.0, 50.0


def metrics(s, label):
    s = pd.to_numeric(s, errors="coerce").dropna()
    q = s.quantile([.01, .05, .10, .25, .50, .75, .90, .95, .99])
    out = {
        "label": label, "n": len(s), "mean": s.mean(), "median": s.median(),
        "sd": s.std(), "min": s.min(), "max": s.max(),
        "iqr": q[.75] - q[.25], "skew": s.skew(), "kurtosis": s.kurtosis(),
        "p01": q[.01], "p10": q[.10], "p25": q[.25], "p75": q[.75], "p90": q[.90], "p99": q[.99],
        # the decision-relevant cuts
        "below_40": (s < SELL_BAR).mean() * 100,
        "band_40_50": ((s >= SELL_BAR) & (s <= HOLD_LINE)).mean() * 100,
        "above_50": (s > HOLD_LINE).mean() * 100,
        # threshold fragility: how many names are within 2 points of a decision line
        "near_40": (s.sub(SELL_BAR).abs() <= 2).sum(),
        "near_50": (s.sub(HOLD_LINE).abs() <= 2).sum(),
    }
    return out


def main():
    d = pd.read_csv(SRC)
    s3 = pd.to_numeric(d["final_score_3y"], errors="coerce")
    s1 = pd.to_numeric(d["final_score_1y"], errors="coerce")
    m3, m1 = metrics(s3, "3-year"), metrics(s1, "1-year")

    edges = list(range(0, 101, 10))
    lbl = [f"{a}-{b}" for a, b in zip(edges[:-1], edges[1:])]
    h3 = np.histogram(s3.dropna(), bins=edges)[0]
    h1 = np.histogram(s1.dropna(), bins=edges)[0]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.5), dpi=200,
                                  gridspec_kw=dict(width_ratios=[1.62, 1.0], wspace=0.30))
    x = np.arange(len(lbl))
    w = 0.40
    # colour by what the bucket MEANS, not decoratively: below the sell bar is the sell zone
    c3 = [SELL if edges[i + 1] <= SELL_BAR else (NT3 if edges[i] < HOLD_LINE else NAVY)
          for i in range(len(lbl))]
    ax.bar(x - w / 2, h3, w, color=c3, edgecolor="white", linewidth=0.8, zorder=3)
    ax.bar(x + w / 2, h1, w, color=NT2, edgecolor="white", linewidth=0.8, zorder=3)
    for i, (a, b) in enumerate(zip(h3, h1)):
        if a:
            ax.text(i - w / 2, a + 3, str(a), ha="center", fontsize=7.4, color=INK)
        if b:
            ax.text(i + w / 2, b + 3, str(b), ha="center", fontsize=7.4, color=SLATE)
    ax.set_xticks(x); ax.set_xticklabels(lbl, fontsize=8.6, color=SLATE)
    ax.set_ylabel("number of stocks", fontsize=9, color=SLATE)
    ax.set_title("Score distribution across the 750-stock universe",
                 fontsize=12, color=INK, fontweight="bold", loc="left", pad=10)
    ax.set_ylim(0, max(h3.max(), h1.max()) * 1.28)   # headroom so the legend clears the tallest bar
    ax.text(0.02, 0.955, "dark = 3-year horizon      light = 1-year horizon",
            transform=ax.transAxes, fontsize=8, color=SLATE)
    ax.text(0.02, 0.895, "red = below the 40 quality-sell bar", transform=ax.transAxes,
            fontsize=8, color=SELL, fontweight="bold")
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(HAIR)
    ax.grid(axis="y", color=HAIR, lw=0.7, zorder=0); ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=8.4, colors=SLATE)

    # right panel: the decision bands, which is what a committee actually acts on
    bands = ["below 40\n(sell zone)", "40 to 50\n(trim band)", "above 50\n(hold)"]
    v3 = [m3["below_40"], m3["band_40_50"], m3["above_50"]]
    v1 = [m1["below_40"], m1["band_40_50"], m1["above_50"]]
    xb = np.arange(3)
    ax2.bar(xb - w / 2, v3, w, color=[SELL, NT3, NAVY], edgecolor="white", lw=0.8, zorder=3)
    ax2.bar(xb + w / 2, v1, w, color=NT2, edgecolor="white", lw=0.8, zorder=3)
    for i, (a, b) in enumerate(zip(v3, v1)):
        ax2.text(i - w / 2, a + 0.8, f"{a:.0f}%", ha="center", fontsize=8.4, color=INK,
                 fontweight="bold")
        ax2.text(i + w / 2, b + 0.8, f"{b:.0f}%", ha="center", fontsize=8.4, color=SLATE)
    ax2.set_xticks(xb); ax2.set_xticklabels(bands, fontsize=8.4, color=SLATE)
    ax2.set_ylabel("% of universe", fontsize=9, color=SLATE)
    ax2.set_title("Where the calls fall", fontsize=12, color=INK, fontweight="bold",
                  loc="left", pad=10)
    for sp in ("top", "right", "left"):
        ax2.spines[sp].set_visible(False)
    ax2.spines["bottom"].set_color(HAIR)
    ax2.grid(axis="y", color=HAIR, lw=0.7, zorder=0); ax2.set_axisbelow(True)
    ax2.tick_params(length=0, labelsize=8.4, colors=SLATE)

    fig.text(0.005, 0.02,
             f"751 stocks, scored on the frozen methodology. Buckets are left-inclusive. "
             f"{m3['near_40']} names sit within 2 points of the 40 bar on the 3-year score and "
             f"{m3['near_50']} within 2 points of the 50 Hold line, so a small score revision "
             f"flips those calls.", fontsize=7.6, color=SLATE)
    fig.subplots_adjust(left=0.055, right=0.99, top=0.88, bottom=0.155)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print("wrote", OUT)

    print(f"\n{'BUCKET':>9s} {'3Y n':>6s} {'3Y %':>7s} {'1Y n':>6s} {'1Y %':>7s}")
    print("-" * 44)
    for i, L in enumerate(lbl):
        print(f"{L:>9s} {h3[i]:>6d} {h3[i]/len(s3)*100:>6.1f}% "
              f"{h1[i]:>6d} {h1[i]/len(s1)*100:>6.1f}%")
    print("-" * 44)
    print(f"{'TOTAL':>9s} {h3.sum():>6d} {'':>7s} {h1.sum():>6d}")

    print(f"\n{'METRIC':<22s} {'3-YEAR':>10s} {'1-YEAR':>10s}")
    print("-" * 44)
    for k in ("n", "mean", "median", "sd", "iqr", "skew", "kurtosis",
              "min", "p01", "p10", "p25", "p75", "p90", "p99", "max",
              "below_40", "band_40_50", "above_50", "near_40", "near_50"):
        f3, f1 = m3[k], m1[k]
        fmt = "{:>10.0f}" if k in ("n", "near_40", "near_50") else "{:>10.2f}"
        print(f"{k:<22s} " + fmt.format(f3) + " " + fmt.format(f1))


if __name__ == "__main__":
    main()
