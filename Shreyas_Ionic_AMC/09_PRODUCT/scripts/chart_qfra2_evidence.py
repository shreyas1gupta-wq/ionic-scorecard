# -*- coding: utf-8 -*-
"""Evidence charts for the QFRA-2 committee deck, in the firm's house chart style.

WHY THESE ARE REBUILT RATHER THAN REUSED. The standalone repo already ships six PNGs at
Mf_qfra2-.../QFRA2/assets/ (built by mr_x_framework/src/qfra2_charts_ceo.py). Three of them
could not be carried into this deck as-is:

  * churn_by_category.png  -- its matplotlib SUBTITLE is baked into the pixels and reads
    "Active book ~2.6 changes/yr". That figure is contradicted by the same script's own bar
    data eight lines earlier (7+6+5+5+5+3 = 31 slot changes over 8 years = 3.9/yr) and by
    every reconciled firm doc. NUMBER_AUDIT.md finding #4. A banned number cannot be
    laundered by living inside an image.
  * live_alpha.png         -- bakes "+0.9%/yr" into the pixels, which is the all-8-category
    mean including Focused, a category this deck excludes from the ask. NUMBER_AUDIT.md
    finding #6. Restricted to the six in scope the figure is +0.65%/yr, so this chart is not
    rebuilt at all: the live-proof page carries the per-category table instead, which is
    both honest and more informative.
  * mid_momentum.png       -- the win-rate annotations collide with the x tick labels and
    are illegible. Data fine, rendering not.

Rebuilding the other two (edge, win-rate) as well costs nothing and buys visual coherence:
the repo charts use a teal/emerald palette, while every chart already in this deck
(qfra2_tenure, anchor_pair_evidence, score_distribution) is house NAVY/GOLD.

EVERY NUMBER BELOW IS TRACED. No figure here is computed by this script except the churn
per-year rate, which is a division shown in the caption.

  edge / win-rate  QFRA2_HANDOFF.md section 5, the qfra2_vs_random.py table. All six
                   deployed categories are drawn, including the two whose edge is ~zero or
                   negative -- the original chart omitted Mid, which is the very category
                   the momentum routing exists to fix.
  mid momentum     QFRA2_HANDOFF.md section 4 (+9%/yr full period, win 87% of 3Y and 100%
                   of 5Y windows, +15.1%/yr post-2018) and qfra2_charts_ceo.py:70 for the
                   pre-2018 split (+7.3%/yr). The weaker pre-2018 bar is kept deliberately:
                   dropping it would leave only the flattering half of the split.
  churn            Recomputed from 03_RESEARCH_DESK/qfra2_pac_prep/QFRA2_history_rebuilt.csv
                   rather than copied: the rebuilt, slot-stable history independently
                   reproduces the old chart's per-category counts exactly (7/6/5/5/5/3, 31
                   total), which is what makes 3.9/yr safe to print.

House chart law: no ax.legend(); direct labels only; NAVY is the primary series; no big
title inside the figure, because the slide header carries it.

Usage: python chart_qfra2_evidence.py
Output: 09_PRODUCT/pr_template/out/qfra2_{edge_by_category,winrate,mid_momentum,churn}.png
"""
import os
import csv
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAVY = "#1B27A3"; NAVYD = "#10197A"; NT1 = "#4A57C4"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"
GOLD = "#F2A93C"; INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; WHITE = "#FFFFFF"

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.abspath(os.path.join(HERE, "..", "pr_template", "out"))
HIST = os.path.abspath(os.path.join(HERE, "..", "..", "03_RESEARCH_DESK",
                                    "qfra2_pac_prep", "QFRA2_history_rebuilt.csv"))

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": HAIR,
                     "text.color": INK, "axes.labelcolor": SLATE,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8})

DEPLOYED = ["Large & Mid Cap", "Flexi Cap", "Large Cap", "Small Cap", "Multi Cap", "Mid Cap"]
SHORT = {"Large & Mid Cap": "Large & Mid", "Flexi Cap": "Flexi", "Large Cap": "Large (index core)",
         "Small Cap": "Small", "Multi Cap": "Multi", "Mid Cap": "Mid (momentum sleeve)"}


def bare(ax, keep_bottom=True, keep_left=False):
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    if keep_bottom:
        ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    if keep_left:
        ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)


def panel_title(ax, text, pad=9):
    ax.set_title(text, fontsize=11, color=INK, fontweight="bold", loc="left", pad=pad)


# ---------------------------------------------------------------- 1  EDGE BY CATEGORY
# QFRA2_HANDOFF.md section 5: 3Y / 5Y median-alpha edge of the top-2 over a random pick
# from the same eligible field, %/yr.
EDGE = {"Large & Mid Cap": (+2.86, +2.08), "Flexi Cap": (+1.90, +1.28),
        "Large Cap": (+0.42, +0.86), "Small Cap": (+0.17, -0.28),
        "Multi Cap": (-0.10, +0.74), "Mid Cap": (+0.06, -0.43)}


def chart_edge():
    cats = DEPLOYED
    e3 = [EDGE[c][0] for c in cats]; e5 = [EDGE[c][1] for c in cats]
    y = np.arange(len(cats))[::-1]; h = 0.36
    fig, ax = plt.subplots(figsize=(13.0, 3.28), dpi=200)
    ax.barh(y + h / 2, e3, height=h, color=NAVY, zorder=3)
    ax.barh(y - h / 2, e5, height=h, color=GOLD, zorder=3)
    for vals, off in ((e3, +h / 2), (e5, -h / 2)):
        for yi, v in zip(y, vals):
            ax.text(v + (0.055 if v >= 0 else -0.055), yi + off, f"{v:+.2f}",
                    va="center", ha="left" if v >= 0 else "right",
                    fontsize=9.2, color=INK, fontweight="bold")
    # Direct series labels instead of a legend (house law), left-aligned just inside the
    # start of the longest pair of bars. Placed at the bar START, not the end: at the end
    # they crowd the value label, and white on GOLD does not carry.
    ax.text(0.09, y[0] + h / 2, "3-year", va="center", ha="left",
            fontsize=8.4, color=WHITE, fontweight="bold", zorder=5)
    ax.text(0.09, y[0] - h / 2, "5-year", va="center", ha="left",
            fontsize=8.4, color=INK, fontweight="bold", zorder=5)
    ax.axvline(0, color=INK, lw=0.9, zorder=4)
    ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in cats], fontsize=9.6, color=INK)
    ax.set_xlim(-1.15, 3.55); ax.set_xticks([-1, 0, 1, 2, 3])
    ax.set_xlabel("median-alpha edge over a random pick from the same eligible field  (%/yr)",
                  fontsize=8.6, color=SLATE, labelpad=6)
    bare(ax)
    panel_title(ax, "Where the selection edge is, and where it is not")
    ax.text(3.50, y.min() - 0.62, "Active pool, pooled\n+1.65%  (3Y)   +1.55%  (5Y)",
            ha="right", va="bottom", fontsize=8.8, color=NAVY, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.42", fc=WHITE, ec=NT2, lw=0.9))
    fig.subplots_adjust(left=0.152, right=0.995, top=0.865, bottom=0.185)
    p = os.path.join(OUTDIR, "qfra2_edge_by_category.png")
    fig.savefig(p, facecolor=WHITE); plt.close(fig); print("wrote", p)


# ---------------------------------------------------------------- 2  WIN-RATE DUMBBELL
# QFRA2_HANDOFF.md section 5, "win% M/R (3Y)" column: (random, model).
WINRATE = {"Large & Mid Cap": (25.7, 61.8), "Flexi Cap": (35.2, 55.9),
           "Large Cap": (27.1, 41.2), "Small Cap": (64.4, 73.5),
           "Multi Cap": (38.7, 41.2), "Mid Cap": (28.3, 26.5)}


def chart_winrate():
    cats = DEPLOYED
    rand = [WINRATE[c][0] for c in cats]; model = [WINRATE[c][1] for c in cats]
    y = np.arange(len(cats))[::-1]
    fig, ax = plt.subplots(figsize=(13.0, 3.28), dpi=200)
    for yi, rv, mv in zip(y, rand, model):
        ax.plot([rv, mv], [yi, yi], color=NT3, lw=6.5, solid_capstyle="round", zorder=1)
    ax.scatter(rand, y, s=95, color=NT2, zorder=3)
    ax.scatter(model, y, s=115, color=NAVY, zorder=4)
    for yi, rv, mv in zip(y, rand, model):
        # model marker label goes on the far side of whichever end it is
        ax.text(mv + (1.5 if mv >= rv else -1.5), yi, f"{mv:.0f}%", va="center",
                ha="left" if mv >= rv else "right", fontsize=9.4, color=NAVY,
                fontweight="bold")
        ax.text(rv - (1.5 if mv >= rv else -1.5), yi, f"{rv:.0f}%", va="center",
                ha="right" if mv >= rv else "left", fontsize=8.8, color=SLATE)
        d = mv - rv
        ax.text((rv + mv) / 2, yi + 0.24, f"{d:+.0f}pp", ha="center", fontsize=8.4,
                color=NAVY if d > 0 else GOLD, fontweight="bold")
    # Series labels get their own band ABOVE every data row (headroom added via ylim) so they
    # cannot collide with a neighbouring row's value or gap label.
    top = y[0]
    ax.text(rand[0], top + 0.72, "random pick", ha="center", va="center", fontsize=8.4,
            color=SLATE)
    ax.text(model[0], top + 0.72, "QFRA 2.0 top 2", ha="center", va="center", fontsize=8.4,
            color=NAVY, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in cats], fontsize=9.6, color=INK)
    ax.set_ylim(-0.62, top + 1.05)
    ax.set_xlim(17, 84)
    ax.set_xlabel("share of formation dates whose forward 3-year return beat the "
                  "category total-return index  (%)", fontsize=8.6, color=SLATE, labelpad=6)
    bare(ax)
    panel_title(ax, "How often the pick beat the index, against a random pick of the same field")
    fig.subplots_adjust(left=0.152, right=0.995, top=0.865, bottom=0.185)
    p = os.path.join(OUTDIR, "qfra2_winrate.png")
    fig.savefig(p, facecolor=WHITE); plt.close(fig); print("wrote", p)


# ---------------------------------------------------------------- 3  MID MOMENTUM
def chart_mid_momentum():
    labels = ["Full period", "Pre-2018", "Post-2018"]
    prem = [9.0, 7.3, 15.1]
    wins = ["87% of 3Y windows\n100% of 5Y windows", "81% of windows", "100% of windows"]
    cols = [NAVY, NT2, GOLD]
    # Text colour is tied to the BAR it sits on, not to the bar's height: white carries on
    # NAVY and nowhere else here -- white on GOLD is unreadable at print size.
    incol = [WHITE, INK, INK]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(13.0, 2.72), dpi=200)
    ax.bar(x, prem, color=cols, width=0.46, zorder=3)
    for xi, v, w, tc in zip(x, prem, wins, incol):
        ax.text(xi, v + 0.45, f"+{v:.1f}%/yr", ha="center", fontsize=11,
                color=INK, fontweight="bold")
        # win-rate caption sits INSIDE the bar. In the repo's version it was placed below
        # the axis at y=-1.3 and collided with the x tick labels.
        ax.text(xi, 0.55, w, ha="center", va="bottom", fontsize=8.0,
                color=tc, linespacing=1.35)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10, color=INK, fontweight="bold")
    ax.set_ylim(0, 18.2); ax.set_yticks([0, 5, 10, 15])
    ax.set_ylabel("premium over the plain\nmid-cap index (%/yr)", fontsize=8.4, color=SLATE)
    bare(ax)
    panel_title(ax, "BSE Midcap 150 Momentum 30 against the plain mid-cap index")
    fig.subplots_adjust(left=0.105, right=0.995, top=0.845, bottom=0.135)
    p = os.path.join(OUTDIR, "qfra2_mid_momentum.png")
    fig.savefig(p, facecolor=WHITE); plt.close(fig); print("wrote", p)


# ---------------------------------------------------------------- 4  CHURN
def churn_counts():
    """Changed slots per category over the rebuilt 17-period history.

    The first period of each category is the book's start, not a change, so it is excluded.
    This independently reproduces qfra2_charts_ceo.py's own bar data (7/6/5/5/5/3 = 31),
    which is the arithmetic that makes 3.9/yr right and the old caption's 2.6/yr wrong.
    """
    rows = list(csv.DictReader(open(HIST, encoding="utf-8-sig")))
    n = defaultdict(int); periods = defaultdict(set)
    for r in rows:
        periods[r["category"]].add(r["period"])
        if r["note"] == "start":
            continue
        n[r["category"]] += (r["slot1_changed"] == "True") + (r["slot2_changed"] == "True")
    return n, {c: len(p) for c, p in periods.items()}


def chart_churn():
    n, periods = churn_counts()
    order = sorted(DEPLOYED, key=lambda c: -n[c])
    vals = [n[c] for c in order]
    total = sum(vals)
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(13.0, 2.72), dpi=200)
    ax.bar(x, vals, color=NAVY, width=0.5, zorder=3)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.14, str(v), ha="center", fontsize=11, color=INK, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[c].replace(" (index core)", "").replace(" (momentum sleeve)", "")
                        for c in order], fontsize=10, color=INK, fontweight="bold")
    ax.set_ylim(0, 8.6); ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_ylabel("fund slots replaced\nover the 8-year history", fontsize=8.4, color=SLATE)
    bare(ax)
    panel_title(ax, f"Every replacement the churn rule allowed: {total} across the six "
                    f"deployed categories, {total / 8.0:.1f} a year")
    fig.subplots_adjust(left=0.105, right=0.995, top=0.845, bottom=0.145)
    p = os.path.join(OUTDIR, "qfra2_churn.png")
    fig.savefig(p, facecolor=WHITE); plt.close(fig); print("wrote", p)
    # printed so a rebuild re-states the arithmetic behind the 3.9 rather than trusting it
    print(f"  churn: {total} slot changes / 8 years = {total / 8.0:.2f} per year "
          f"({', '.join(f'{c}={n[c]}' for c in order)}); periods per category="
          f"{sorted(set(periods[c] for c in DEPLOYED))}")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    chart_edge(); chart_winrate(); chart_mid_momentum(); chart_churn()


if __name__ == "__main__":
    main()
