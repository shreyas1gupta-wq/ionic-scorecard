# -*- coding: utf-8 -*-
"""Four word sets for the traffic-light legend -- options to choose from.
Principal, 2026-08-07: "footnote keep simple Strong, Okay, Weak, Bad or some other 4 better words along
with colour show me options to choose from".

The dots and the bands are settled (even quartiles, floors 75/50/25). Only the four WORDS differ, and
they carry more weight than they look like they do, because the explanatory footnote is being removed:
whatever these words say is now the only thing telling the reader what a colour means.

Output: pr_template/out/signal_words.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))
sys.path.insert(0, os.path.join(PRT, "lib"))
import five_signals as F                                                   # noqa: E402

NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = os.path.join(NIFTY, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                   "results", "full750_scored.csv")
OUT = os.path.join(PRT, "out", "signal_words.png")

INK, SLATE, HAIR, WHITE = "#16233B", "#6B7280", "#E5E7EB", "#FFFFFF"
WANT = ["TCS", "HDFCBANK", "ITC", "RELIANCE", "DMART", "SBIN"]
X0, PITCH, DOT_PT = 0.315, 0.137, 11.0

SETS = [
    ("relative", "Set A  ·  Top 25% / Upper / Lower / Bottom 25%   [RECOMMENDED]",
     "The only set that survives losing the footnote. A dot is a rank against the 750, and\n"
     "these words say so, so the colour cannot be heard as an absolute grade."),
    ("plain", "Set B  ·  Strong / Fair / Weak / Poor",
     "Plainest ranked words, and unambiguous in order. Risk: \"Strong\" quality sounds like\n"
     "good quality, when it only means top-quartile among the 750."),
    ("blunt", "Set C  ·  Strong / Okay / Weak / Bad   (your suggestion)",
     "Most direct. \"Okay\" is informal for a client deck and \"Bad\" is a verdict on the\n"
     "company rather than a description of where it ranks."),
    ("level", "Set D  ·  High / Medium / Low / Very low",
     "No praise or blame in it, so it never over-claims. Reads a little clinical, and does\n"
     "not say high WHAT -- high quality, or high rank?"),
]


def dot_at(ax, x, y, fill, size=1.0):
    ax.plot([x], [y], marker="o", markersize=DOT_PT * size, zorder=5, linestyle="none",
            markerfacecolor=(fill or WHITE), markeredgecolor=(fill or SLATE),
            markeredgewidth=(1.1 if fill is None else 0.0), clip_on=False)


def panel(ax, rows, wordset, title, note):
    n = len(rows)
    ax.set_xlim(0, 1); ax.set_ylim(-1.55, n + 2.30); ax.axis("off")
    ax.text(0, n + 1.88, title, fontsize=10.5, color=INK, fontweight="bold", va="baseline")
    ax.text(0, n + 1.54, note, fontsize=7.1, color=SLATE, va="top", linespacing=1.35)
    for ci, c in enumerate(F.CATS):
        ax.text(X0 + ci * PITCH, n + 0.20, c.replace(" & ", "\n& "), ha="center", va="bottom",
                fontsize=6.5, color=SLATE, fontweight="bold")
    for ri, (sym, sig, fin) in enumerate(rows):
        y = n - ri - 0.72
        ax.text(0.0, y, sym[:11], fontsize=8.0, color=INK, fontweight="bold", va="center")
        tag = (("Hold" if fin >= 40 else "Sell") + f" {fin:.0f}") if fin == fin else "not scored"
        ax.text(0.262, y, tag, fontsize=6.3, color=SLATE, ha="right", va="center")
        for ci, (_cat, v) in enumerate(sig):
            dot_at(ax, X0 + ci * PITCH, y, F.dot(v))
        ax.plot([0, 1], [y - 0.36, y - 0.36], color=HAIR, lw=0.5, zorder=1)
    # the legend exactly as it will print: four dots, four words, plus the not-scored ring
    lx = 0.0
    for lab, fill in F.legend(words=wordset):
        dot_at(ax, lx + 0.014, -0.95, fill)
        ax.text(lx + 0.044, -0.95, lab, fontsize=7.2, color=INK, va="center")
        lx += 0.196
    dot_at(ax, lx + 0.014, -0.95, None)
    ax.text(lx + 0.044, -0.95, F.NO_DATA_WORD, fontsize=7.2, color=SLATE, va="center")


def main():
    d = pd.read_csv(SRC)
    sc = "symbol" if "symbol" in d.columns else d.columns[0]
    d[sc] = d[sc].astype(str).str.upper().str.strip()
    sub = d[d[sc].isin(WANT)].drop_duplicates(subset=[sc])
    sub = sub.set_index(sc).reindex([w for w in WANT if w in set(sub[sc])]).reset_index()
    rows = [(r[sc], F.signals(dict(r)),
             pd.to_numeric(r.get("final_score_3y"), errors="coerce")) for _, r in sub.iterrows()]

    fig = plt.figure(figsize=(15.0, 9.0), dpi=190)
    fig.text(0.042, 0.966, "Four words for the legend - which set to use",
             fontsize=15, color=INK, fontweight="bold")
    fig.text(0.042, 0.940,
             "Dots and bands are settled: even quartiles, a quarter of the universe in each colour. "
             "Only the four words differ.", fontsize=8.5, color=SLATE)
    for i, (ws, title, note) in enumerate(SETS):
        ax = fig.add_axes([0.042 + (i % 2) * 0.492, 0.520 - (i // 2) * 0.452, 0.44, 0.345])
        panel(ax, rows, ws, title, note)
    fig.text(0.042, 0.030,
             "With the footnote gone, these four words are the entire explanation of what a colour "
             "means - which is why Set A is the recommendation.",
             fontsize=8.2, color="#92400E", fontweight="bold")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor=WHITE)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
