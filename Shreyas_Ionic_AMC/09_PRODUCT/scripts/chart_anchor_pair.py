# -*- coding: utf-8 -*-
"""Anchor-pair evidence chart for the PAC/CEO deck: why the fund model runs Apr-end / Oct-end.

Data source: 04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md
(906 formations, 2012-01..2024-07, all 6 category sheets, QFRA-1's live decision logic replayed,
forward 6M excess vs category benchmark). Numbers are quoted, not recomputed here.

House chart law: no ax.legend() -- direct labels only. NAVY = the chosen pair, tinted for the rest.
Writes a paired panel: BUY median (left) and hit rate (right), both sorted by BUY median.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAVY = "#1B27A3"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"
GOLD = "#F2A93C"; INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"

# (label, BUY median %, BUY plain-mean %, BUY 10%-trim-mean %, hit rate %, n)
#
# PRESENTED MEASURE = the 10% TRIMMED MEAN (Principal ruling 2026-08-04). This is not a measure
# chosen after seeing the results: the Principal's original question on 2026-07-26 specified
# "judge on median + trimmed mean" BEFORE the study ran, so it is pre-registered. On both
# pre-registered measures Apr/Oct ranks 1st and Jan/Jul ranks last.
# The plain untrimmed mean is the ONE measure that disagrees (Jun/Dec 2.65 vs Apr/Oct 2.62). It is
# still drawn, as a gold tick, so the disagreement is disclosed rather than hidden -- never ship a
# version of this chart that shows only the favourable measure.
ROWS = [
    ("Apr / Oct", 2.59, 2.62, 2.59, 66.0, 150),
    ("Jun / Dec", 2.22, 2.65, 2.34, 66.0, 150),
    ("Mar / Sep", 1.82, 2.08, 2.10, 54.7, 150),
    ("Feb / Aug", 2.34, 1.99, 2.04, 58.0, 150),
    ("May / Nov", 1.94, 1.94, 1.98, 58.0, 150),
    ("Jan / Jul", 1.31, 2.20, 1.77, 57.7, 156),
]
CHOSEN, PRIOR = "Apr / Oct", "Jun / Dec"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "pr_template", "out", "anchor_pair_evidence.png")


def _bar_color(lab):
    if lab == CHOSEN:
        return NAVY
    return NT2 if lab == PRIOR else NT3


def main():
    labs = [r[0] for r in ROWS]
    y = list(range(len(ROWS)))[::-1]          # best at top
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 3.9), dpi=200,
                                   gridspec_kw=dict(width_ratios=[1.55, 1.0], wspace=0.42))

    # ---- left: BUY forward 6M excess. Bar = 10% TRIMMED MEAN (the pre-registered,
    # presented measure). Gold tick = plain untrimmed mean, drawn so the one measure that
    # disagrees stays visible.
    for (lab, _med, _mean, trim, _hit, _n), yy in zip(ROWS, y):
        axL.barh(yy, trim, height=0.62, color=_bar_color(lab),
                 edgecolor="none", zorder=3)
        axL.text(trim + 0.08, yy, f"{trim:+.2f}%", va="center", ha="left",
                 fontsize=9.5, color=INK,
                 fontweight="bold" if lab == CHOSEN else "normal", zorder=4)
    axL.set_yticks(y)
    axL.set_yticklabels(labs, fontsize=10, color=INK)
    for t, lab in zip(axL.get_yticklabels(), labs):
        if lab == CHOSEN:
            t.set_fontweight("bold")
    axL.set_xlim(0, 3.25)
    axL.set_xlabel("Forward 6-month excess return of BUY calls, vs category benchmark",
                   fontsize=8.6, color=SLATE, labelpad=6)
    axL.set_title("Every month-pair tested, ranked", fontsize=11, color=INK,
                  fontweight="bold", loc="left", pad=9)
    # direct label, not a legend (house chart law)
    axL.text(1.55, y[0] + 0.60, "bar = 10% trimmed mean", fontsize=8.0, color=SLATE)
    for s in ("top", "right", "left"):
        axL.spines[s].set_visible(False)
    axL.spines["bottom"].set_color(HAIR)
    axL.tick_params(axis="x", labelsize=8.4, colors=SLATE, length=0)
    axL.tick_params(axis="y", length=0)
    axL.grid(axis="x", color=HAIR, lw=0.7, zorder=0)
    axL.set_axisbelow(True)

    # ---- right: hit rate (the measure trimming cannot move) ----------------
    for (lab, _med, _mean, _tm, hit, _n), yy in zip(ROWS, y):
        axR.barh(yy, hit, height=0.62, color=_bar_color(lab), edgecolor="none", zorder=3)
        axR.text(hit - 1.6, yy, f"{hit:.0f}%", va="center", ha="right", fontsize=9.5,
                 color="white", fontweight="bold" if lab == CHOSEN else "normal", zorder=4)
    axR.set_yticks(y); axR.set_yticklabels([])
    axR.set_xlim(0, 72)
    axR.set_xlabel("Share of BUY calls that beat the benchmark", fontsize=8.6,
                   color=SLATE, labelpad=6)
    axR.set_title("Hit rate", fontsize=11, color=INK, fontweight="bold", loc="left", pad=9)
    for s in ("top", "right", "left"):
        axR.spines[s].set_visible(False)
    axR.spines["bottom"].set_color(HAIR)
    axR.tick_params(axis="x", labelsize=8.4, colors=SLATE, length=0)
    axR.tick_params(axis="y", length=0)
    axR.grid(axis="x", color=HAIR, lw=0.7, zorder=0)
    axR.set_axisbelow(True)
    # the two-good-anchors story: 66% for the top pair, ~55-58% for the rest
    axR.axvline(66, color=GOLD, lw=1.1, ls=(0, (3, 2)), zorder=2)

    # look the rows up by LABEL — these annotations were hardcoded to y[0]/y[2] and silently
    # landed on the wrong bar the moment the sort order changed to the trimmed mean
    _yof = {lab: yy for (lab, *_r), yy in zip(ROWS, y)}
    axL.annotate("chosen", xy=(0.10, _yof[CHOSEN]), fontsize=8.2, color="white",
                 fontweight="bold", ha="left", va="center")
    axL.annotate("prior cadence", xy=(0.10, _yof[PRIOR]), fontsize=8.2, color="white",
                 ha="left", va="center")

    fig.text(0.008, 0.062,
             "906 formations, Jan-2012 to Jul-2024, all six category sheets. The short-term "
             "framework's live decision logic replayed at every month-END anchor: data through "
             "30-April and 31-October.",
             fontsize=7.4, color=SLATE)
    fig.text(0.008, 0.018,
             "Measure is the 10% trimmed mean, specified before the study ran. Apr/Oct ranks "
             "first on the median too (+2.59%), and Jan/Jul last on both (+1.31% median).",
             fontsize=7.4, color=SLATE)
    fig.subplots_adjust(left=0.098, right=0.985, top=0.845, bottom=0.255)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
