# -*- coding: utf-8 -*-
"""SUPERSEDED 2026-08-07 -- decision record only, no longer runnable. Written against the pre-final
five_signals API (worded chips, SCHEMES/BAND_SHARE); the Principal then chose traffic-light dots and
even quartiles, and the lib was rewritten around that choice. Kept because it documents HOW the
banding options were compared; do not fix, do not import.

Four ways to render the five colour-coded signals that replace the one-line holding commentary.
Principal ask, 2026-08-06: "replace fund commentary 1liner into 5 colour coded signals, club what we
were looking like growth value technical etc into 5 broad categories ... thus if we have a high growth
company we will show green below growth ... show me best and 3 or 4 colour coded".

The clubbing and the band floors live in `pr_template/lib/five_signals.py` -- this file only DRAWS
them, so the comparison sheet and the deck page can never disagree about what green means.

Rendered on REAL stocks with REAL scores. Output: pr_template/out/signal_options.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))
sys.path.insert(0, os.path.join(PRT, "lib"))
import five_signals as F                                                   # noqa: E402

NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = os.path.join(NIFTY, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                   "results", "full750_scored.csv")
OUT = os.path.join(PRT, "out", "signal_options.png")

INK, SLATE, HAIR, WHITE = "#16233B", "#6B7280", "#E5E7EB", "#FFFFFF"

# symbol, and the mock's job: cover a Sell, a borderline, and a clear Hold so each option is judged
# on rows that actually differ
WANT = ["TCS", "HDFCBANK", "ITC", "RELIANCE", "DMART", "SBIN", "SUZLON"]


def chip(ax, x, y, w, h, label, fg, bg, fs=7.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.015",
                                facecolor=bg, edgecolor=fg, linewidth=0.9, zorder=3))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fs,
            color=fg, fontweight="bold", zorder=4)


def chip_num(ax, x, y, w, h, label, fg, bg, val):
    """Chip plus the figure, so a 68 and a 97 are both green but not indistinguishable. The number
    sits in a reserved strip OUTSIDE the coloured chip -- the first draft printed it on top of the
    fill, where light backgrounds swallowed it."""
    numw = 0.030
    chip(ax, x, y, w - numw - 0.004, h, label, fg, bg, fs=6.6)
    ax.text(x + w - 0.002, y + h / 2, "-" if val is None else f"{val:.0f}",
            ha="right", va="center", fontsize=6.6, color=SLATE, fontweight="bold", zorder=4)


def bar_num(ax, x, y, w, h, fg, bg, val):
    """Magnitude as a fill, figure in a reserved strip to the right of the track -- never over it."""
    numw = 0.030
    tw = w - numw - 0.006
    ax.add_patch(Rectangle((x, y), tw, h, facecolor=bg, edgecolor="none", zorder=3))
    if val is not None:
        ax.add_patch(Rectangle((x, y), tw * max(val, 0) / 100.0, h, facecolor=fg,
                               edgecolor="none", zorder=4))
    ax.text(x + w - 0.002, y + h / 2, "-" if val is None else f"{val:.0f}",
            ha="right", va="center", fontsize=6.6, color=SLATE, fontweight="bold", zorder=5)


def panel(ax, rows, scheme, style, title, subtitle):
    n = len(rows)
    # Vertical budget, in data units, ~0.34in each. The first draft put the title 0.36 units above the
    # subtitle -- less than an 11pt line's own height -- so they printed on top of each other. Same
    # mistake in the rows: symbol and call were 0.19 units apart. Both now have real clearance, and
    # the symbol/call share one baseline so a row needs only one line.
    ax.set_xlim(0, 1); ax.set_ylim(-1.15, n + 2.00); ax.axis("off")
    ax.text(0, n + 1.62, title, fontsize=11, color=INK, fontweight="bold", va="baseline")
    ax.text(0, n + 1.30, subtitle, fontsize=7.3, color=SLATE, va="top", linespacing=1.35)

    x0, cw = 0.215, 0.157
    for ci, c in enumerate(F.CATS):
        ax.text(x0 + ci * cw + (cw - 0.006) / 2, n + 0.16,
                c.replace(" & ", "\n& "), ha="center", va="bottom", fontsize=6.6,
                color=SLATE, fontweight="bold")

    for ri, (sym, sig, fin) in enumerate(rows):
        y = n - ri - 0.86
        ax.text(0.0, y + 0.10, sym[:11], fontsize=8.0, color=INK, fontweight="bold")
        tag = (("Hold" if fin >= 40 else "Sell") + f" {fin:.0f}") if fin == fin else "not scored"
        ax.text(0.206, y + 0.11, tag, fontsize=6.3, color=SLATE, ha="right")  # clears HDFCBANK
        for ci, (_cat, v) in enumerate(sig):
            lab, fg, bg = F.band(v, scheme)
            x = x0 + ci * cw
            if style == "chip":
                chip(ax, x, y, cw - 0.008, 0.30, lab, fg, bg)
            elif style == "chipnum":
                chip_num(ax, x, y, cw - 0.008, 0.30, lab, fg, bg, v)
            else:
                bar_num(ax, x, y, cw - 0.008, 0.26, fg, bg, v)
        ax.plot([0, 1], [y - 0.14, y - 0.14], color=HAIR, lw=0.5, zorder=1)

    lx = 0.0
    for lo, lab, fg, bg in F.SCHEMES[scheme]:
        chip(ax, lx, -0.62, 0.150, 0.25, lab, fg, bg, fs=6.4)
        ax.text(lx + 0.075, -0.86, f"top {F.BAND_SHARE[scheme][lab]}%" if lo == F.SCHEMES[scheme][0][0]
                else f"{F.BAND_SHARE[scheme][lab]}% of names", ha="center", fontsize=5.7, color=SLATE)
        lx += 0.163
    chip(ax, lx, -0.62, 0.150, 0.25, F.NO_DATA[0], F.NO_DATA[1], F.NO_DATA[2], fs=6.4)
    ax.text(lx + 0.075, -0.86, "pillar has no data", ha="center", fontsize=5.7, color=SLATE)


def main():
    d = pd.read_csv(SRC)
    sc = "symbol" if "symbol" in d.columns else d.columns[0]
    d[sc] = d[sc].astype(str).str.upper().str.strip()
    sub = d[d[sc].isin(WANT)].drop_duplicates(subset=[sc])
    sub = sub.set_index(sc).reindex([w for w in WANT if w in set(sub[sc])]).reset_index()
    rows = [(r[sc], F.signals(dict(r)),
             pd.to_numeric(r.get("final_score_3y"), errors="coerce")) for _, r in sub.iterrows()]

    fig = plt.figure(figsize=(15.0, 9.4), dpi=190)
    fig.text(0.042, 0.965, "Five signals instead of the one-line commentary - four ways to show them",
             fontsize=15, color=INK, fontweight="bold")
    fig.text(0.042, 0.938,
             "Quality, Growth and Value are single pillars. Technical combines trend and "
             "accumulation. Flows & Sector combines institutional ownership change and sector "
             "strength. All seven scorecard pillars are represented; none is dropped.",
             fontsize=8.5, color=SLATE)

    specs = [
        ("A3", "chip", "Option A  ·  three colours",
         "Simplest. Agrees with the Sell/Hold call best of all - but 43% of cells land in\n"
         "the middle band, so nearly half the grid says nothing."),
        ("B4", "chip", "Option B  ·  four colours, even quartiles",
         "The intuitive scheme, and the weakest: half of all cells are below-average by\n"
         "arithmetic, so 28% of HOLD rows show no green at all."),
        ("C4", "chip", "Option C  ·  four colours, tuned floors   [RECOMMENDED]",
         "Same four colours, floors at 67/45/22 instead of 75/50/25. Flattest spread of\n"
         "any scheme tested, and only 11% of Hold rows show no green."),
        ("C4", "chipnum", "Option D  ·  Option C plus the figure",
         "Option C with each pillar's rank printed beside the chip. Distinguishes a 68\n"
         "from a 97, at the cost of five more numbers per row."),
    ]
    for i, (scheme, style, title, sub_t) in enumerate(specs):
        ax = fig.add_axes([0.042 + (i % 2) * 0.492, 0.525 - (i // 2) * 0.455, 0.44, 0.345])
        panel(ax, rows, scheme, style, title, sub_t)

    fig.text(0.042, 0.038,
             "Every figure is a PERCENTILE RANK against the 750-stock universe, so green means "
             "\"better than most of the 750\", not \"good in absolute terms\".",
             fontsize=8.2, color=F.AMBER, fontweight="bold")
    fig.text(0.042, 0.018,
             "In an expensive market the greenest Value cell is still expensive. Whichever option "
             "ships carries that sentence, and each legend chip shows the share of the universe it "
             "covers so the colour cannot overstate.", fontsize=8.0, color=SLATE)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor=WHITE)
    print("wrote", OUT)

    allrows = [dict(r) for _, r in d.iterrows()]
    print("\noccupancy across the 750 universe")
    for s in ("A3", "B4", "C4"):
        occ, n, na = F.occupancy(allrows, s)
        print(f"  {s}: " + " | ".join(f"{l} {p:.0f}%" for l, _k, p in occ)
              + f"    not scored {na / (n + na) * 100:.1f}%")


if __name__ == "__main__":
    main()
