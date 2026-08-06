# -*- coding: utf-8 -*-
"""SUPERSEDED 2026-08-07 -- decision record only, no longer runnable. Written against the pre-final
five_signals API (DOT_INK/DOT_SIZE_RAMP/SCHEMES); after the format choice the lib was rewritten and
those symbols no longer exist. Kept because it documents HOW the dot formats were compared; do not
fix, do not import.

Traffic-light DOT formatting -- variants to choose from.
Principal, 2026-08-07: "just colours red yellow light greenish dark green dots like traffic lights,
below their respective columns, in best formatting possible".

The colours are settled (dark green / light green / yellow / red, from lib/five_signals.DOT_INK). What
is NOT settled is the formatting, and it matters more than it sounds: a 0.16in dot centred in a 1.05in
column reads as lost rather than deliberate, because the eye has no reference for where the dot "sits".
Each variant below solves that differently. Rendered on real stocks with real scores.

Output: pr_template/out/dot_formats.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))
sys.path.insert(0, os.path.join(PRT, "lib"))
import five_signals as F                                                   # noqa: E402

NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = os.path.join(NIFTY, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                   "results", "full750_scored.csv")
OUT = os.path.join(PRT, "out", "dot_formats.png")

INK, SLATE, HAIR, WHITE, TRACK = "#16233B", "#6B7280", "#E5E7EB", "#FFFFFF", "#EEEFF7"
WANT = ["TCS", "HDFCBANK", "ITC", "RELIANCE", "DMART", "SBIN", "SUZLON"]

# axes-x of each signal column centre, and the column pitch
X0, PITCH = 0.315, 0.137


DOT_PT = 11.0          # full-size dot diameter in points (~0.15in), matches the deck's 0.15in dot


def dot_at(ax, x, y, fill, r=DOT_PT, size=1.0):
    """A round dot, sized in POINTS.

    Patches.Circle takes its radius in DATA units, and this axes is ~6.6in across 1 x-unit but only
    ~0.32in across 1 y-unit -- so a Circle comes out as a flat 20:1 ellipse. Marker size is in points
    and therefore immune to the data aspect, which is the whole reason to use it here."""
    ax.plot([x], [y], marker="o", markersize=r * size, zorder=5, linestyle="none",
            markerfacecolor=(fill or WHITE), markeredgecolor=(fill or SLATE),
            markeredgewidth=(1.1 if fill is None else 0.0), clip_on=False)


def variant(ax, rows, title, note, mode):
    n = len(rows)
    # 1 y-unit is only ~0.32in here, so a 2-line 7pt note spans ~0.76 units. The first pass put the
    # note 0.76 units above the column headers -- exactly its own height -- and printed through them.
    ax.set_xlim(0, 1); ax.set_ylim(-1.30, n + 2.35); ax.axis("off")
    ax.set_aspect("auto")
    ax.text(0, n + 1.92, title, fontsize=10.5, color=INK, fontweight="bold", va="baseline")
    ax.text(0, n + 1.58, note, fontsize=7.1, color=SLATE, va="top", linespacing=1.35)

    for ci, c in enumerate(F.CATS):
        ax.text(X0 + ci * PITCH, n + 0.20, c.replace(" & ", "\n& "), ha="center", va="bottom",
                fontsize=6.5, color=SLATE, fontweight="bold")

    for ri, (sym, sig, fin) in enumerate(rows):
        y = n - ri - 0.72
        ax.text(0.0, y, sym[:11], fontsize=8.0, color=INK, fontweight="bold", va="center")
        tag = (("Hold" if fin >= 40 else "Sell") + f" {fin:.0f}") if fin == fin else "not scored"
        ax.text(0.262, y, tag, fontsize=6.3, color=SLATE, ha="right", va="center")
        for ci, (_cat, v) in enumerate(sig):
            fill, _lab, rel = F.dot(v)
            x = X0 + ci * PITCH
            if mode == "plain":
                dot_at(ax, x, y, fill)
            elif mode == "track":
                # a faint full-width track behind the dot: gives the eye a frame, so the dot reads as
                # placed rather than floating
                ax.add_patch(FancyBboxPatch((x - PITCH * 0.40, y - 0.145), PITCH * 0.80, 0.29,
                                            boxstyle="round,pad=0.002,rounding_size=0.02",
                                            facecolor=TRACK, edgecolor="none", zorder=2))
                dot_at(ax, x, y, fill)
            elif mode == "num":
                dot_at(ax, x - 0.028, y, fill, r=9.5)
                ax.text(x + 0.006, y, "-" if v is None else f"{v:.0f}", fontsize=6.4,
                        color=SLATE, ha="left", va="center")
            else:                                    # graduated size + colour
                dot_at(ax, x, y, fill, r=12.5, size=rel)
        ax.plot([0, 1], [y - 0.36, y - 0.36], color=HAIR, lw=0.5, zorder=1)

    lx = 0.0
    for _lo, lab, _fg, _bg in F.SCHEMES[F.DEFAULT_SCHEME]:
        fill = F.DOT_INK[lab]
        rel = F.DOT_SIZE_RAMP[lab] if mode == "ramp" else 1.0
        dot_at(ax, lx + 0.014, -0.85, fill, size=rel)
        ax.text(lx + 0.042, -0.85, f"{lab} {F.BAND_SHARE[F.DEFAULT_SCHEME][lab]}%",
                fontsize=6.5, color=INK, va="center")
        lx += 0.205
    dot_at(ax, lx + 0.014, -0.85, None)
    ax.text(lx + 0.042, -0.85, "No data", fontsize=6.5, color=SLATE, va="center")


def main():
    d = pd.read_csv(SRC)
    sc = "symbol" if "symbol" in d.columns else d.columns[0]
    d[sc] = d[sc].astype(str).str.upper().str.strip()
    sub = d[d[sc].isin(WANT)].drop_duplicates(subset=[sc])
    order = [w for w in WANT if w in set(sub[sc])]
    sub = sub.set_index(sc).reindex(order).reset_index()
    rows = [(r[sc], F.signals(dict(r)),
             pd.to_numeric(r.get("final_score_3y"), errors="coerce")) for _, r in sub.iterrows()]

    fig = plt.figure(figsize=(15.0, 9.2), dpi=190)
    fig.text(0.042, 0.966, "Traffic-light dots - four ways to format them",
             fontsize=15, color=INK, fontweight="bold")
    fig.text(0.042, 0.940,
             "Colours are settled: dark green, light green, yellow, red. Same five dimensions, same "
             "band floors (67 / 45 / 22). Only the formatting differs.",
             fontsize=8.5, color=SLATE)

    specs = [
        ("plain", "Format 1  ·  bare dots   [RECOMMENDED]",
         "Cleanest, and the row rules plus column headers turn out to anchor the eye\n"
         "perfectly well on their own. Nothing here is doing nothing."),
        ("track", "Format 2  ·  dots on a faint track",
         "The track was meant to frame each dot. Rendered, it does the opposite: five\n"
         "grey bars per row compete with the dots they were supposed to support."),
        ("num", "Format 3  ·  dot plus the rank",
         "Adds the figure, so a 68 and a 97 are not identical dots. Costs five numbers\n"
         "per row and starts to look like a data table again."),
        ("ramp", "Format 4  ·  graduated size",
         "Survives greyscale printing and red-green colour blindness, the only one that\n"
         "does. Cost: a weak signal is now the SMALLEST dot, so problems recede."),
    ]
    for i, (mode, title, note) in enumerate(specs):
        ax = fig.add_axes([0.042 + (i % 2) * 0.492, 0.520 - (i // 2) * 0.452, 0.44, 0.345])
        variant(ax, rows, title, note, mode)

    fig.text(0.042, 0.040,
             "Worth knowing before you pick: a dot carries no label, so colour is the whole message.",
             fontsize=8.2, color="#92400E", fontweight="bold")
    fig.text(0.042, 0.020,
             "Light green and yellow have almost the same luminance and red is darker than both, so a "
             "mono print or a red-green colour deficiency (about 8% of men) collapses the ramp. "
             "Format 4 is the only one that stays readable in both cases.",
             fontsize=8.0, color=SLATE)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor=WHITE)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
