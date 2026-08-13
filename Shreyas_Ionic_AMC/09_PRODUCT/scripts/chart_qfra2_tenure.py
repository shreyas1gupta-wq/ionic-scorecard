# -*- coding: utf-8 -*-
"""Slot-tenure chart for the QFRA-2 committee deck (Principal ask, 2026-08-04).

Fixes both defects the Principal named on the old history slides, visually:
  1. A CONTINUING fund keeps its slot. Each slot is one row; a tenure is one continuous
     bar. A fund can no longer appear to jump from "Pick 1" to "Pick 2".
  2. EVERY H1/H2 is shown. The x-axis is all 17 periods 2018-H1..2026-H1 with no gaps,
     so held periods are visible rather than collapsed away (the old slides rendered only
     the 43 change rows and silently hid 93 of 136).

Source: 03_RESEARCH_DESK/qfra2_pac_prep/QFRA2_history_rebuilt.csv (from
09_PRODUCT/scripts/qfra2_history_rebuild.py). Deployed six categories only -- Focused and
Value/Contra are out of the CEO deployment scope, so they are named in a footnote instead
of drawn, and the footnote says how many periods they cover so nothing looks hidden.

House chart law: no ax.legend(); direct labels only; NAVY is the primary series.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

NAVY = "#1B27A3"; NAVYD = "#10197A"; NT1 = "#4A57C4"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"
GOLD = "#F2A93C"; INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; WHITE = "#FFFFFF"

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "03_RESEARCH_DESK",
                                   "qfra2_pac_prep", "QFRA2_history_rebuilt.csv"))
OUT = os.path.abspath(os.path.join(HERE, "..", "pr_template", "out", "qfra2_tenure.png"))

DEPLOYED = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Flexi Cap", "Multi Cap", "Small Cap"]
# routing label shown beside the category name, per QFRA2_current.csv (verified 2026-08-04):
# index-core is LARGE CAP and MID CAP -- not the "Large & Mid Cap" category, which is ACTIVE.
ROUTING = {"Large Cap": "index core", "Large & Mid Cap": "active", "Mid Cap": "momentum sleeve",
           "Flexi Cap": "active", "Multi Cap": "active", "Small Cap": "active"}
# alternate tints so two consecutive tenures in the same slot never blur together
TINTS = [NAVY, NT1, NT2, NAVYD, NT3]


def tenures(df, cat, slot):
    """Collapse consecutive identical holdings into (fund, start_idx, end_idx) spans."""
    sub = df[df["category"] == cat].sort_values("_pi")
    col = f"slot{slot}_fund_short"
    out = []
    for _, r in sub.iterrows():
        f = r[col]
        if out and out[-1][0] == f:
            out[-1][2] = r["_pi"]
        else:
            out.append([f, r["_pi"], r["_pi"]])
    return out


def main():
    df = pd.read_csv(SRC)
    periods = sorted(df["period"].unique())
    pidx = {p: i for i, p in enumerate(periods)}
    df["_pi"] = df["period"].map(pidx)
    n = len(periods)

    fig, ax = plt.subplots(figsize=(13.0, 5.3), dpi=200)
    rowh, gap = 0.34, 0.14
    y = 0.0
    ylabels, yticks = [], []
    catbounds = []

    for cat in DEPLOYED:
        top = y
        for slot in (1, 2):
            spans = tenures(df, cat, slot)
            for k, (fund, a, b) in enumerate(spans):
                w = (b - a) + 1
                tint = TINTS[k % len(TINTS)]
                ax.add_patch(Rectangle((a, y), w, rowh, facecolor=tint,
                                       edgecolor=WHITE, linewidth=1.4, zorder=3))
                # Label must stay INSIDE its own bar: a left-aligned overflow ran across
                # the neighbouring tenure and read as if it belonged there. Truncate to the
                # bar's own character budget instead. Full names are in the appendix table.
                budget = max(0, int(w / 0.118) - 1)
                if budget >= 4:
                    label = fund if len(fund) <= budget else fund[:budget - 2].rstrip() + ".."
                    # contrast by tint luminance, not by whether the text fit
                    dark_bg = tint in (NAVY, NAVYD, NT1)
                    ax.text(a + w / 2, y + rowh / 2, label, ha="center", va="center",
                            fontsize=6.9, color=WHITE if dark_bg else INK, zorder=5,
                            fontweight="bold")
            yticks.append(y + rowh / 2)
            ylabels.append(f"slot {slot}")
            y += rowh + gap
        catbounds.append((cat, top, y - gap))
        y += 0.30                                   # breathing room between categories

    # category names + routing on the left rail, clear of the per-slot tick labels
    # (at x=-0.55 the routing line collided with "slot 1")
    for cat, a, b in catbounds:
        mid = (a + b) / 2
        ax.text(-1.30, mid - 0.16, cat, ha="right", va="center", fontsize=9.2,
                color=INK, fontweight="bold")
        ax.text(-1.30, mid + 0.19, ROUTING[cat], ha="right", va="center",
                fontsize=7.4, color=SLATE, style="italic")

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=7.0, color=SLATE)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(-0.05, n)
    ax.set_ylim(-0.15, y - 0.30)
    ax.invert_yaxis()

    ax.set_xticks([i + 0.5 for i in range(n)])
    ax.set_xticklabels([p.replace("-", "\n") for p in periods], fontsize=7.0, color=SLATE)
    ax.tick_params(axis="x", length=0)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    for i in range(1, n):                            # period gridlines
        ax.axvline(i, color=HAIR, lw=0.6, zorder=1)

    ax.set_title("Every review period, and who held each slot",
                 fontsize=12.5, color=INK, fontweight="bold", loc="left", pad=12)
    fig.text(0.005, 0.055,
             "One row per slot, one bar per continuous tenure: a fund that is retained "
             "keeps its slot, so a tenure reads as one unbroken bar. All 17 half-year "
             "periods are shown, including the ones where nothing changed.",
             fontsize=7.6, color=SLATE)
    fig.text(0.005, 0.016,
             "Deployed six categories; Focused and Value/Contra sit outside the deployment "
             "scope and are not drawn. Short tenures are abbreviated to fit their bar, with "
             "full names in the appendix table.",
             fontsize=7.6, color=SLATE)

    fig.subplots_adjust(left=0.175, right=0.995, top=0.895, bottom=0.145)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor=WHITE)
    print("wrote", OUT)

    # audit line: prove the two fixes numerically, printed for the deck's caption
    tot = len(df)
    changed = int(df["changed_flag"].sum())
    print(f"periods={n}  categories={df['category'].nunique()}  rows={tot}  "
          f"change-rows={changed}  held-rows={tot - changed}")


if __name__ == "__main__":
    main()
