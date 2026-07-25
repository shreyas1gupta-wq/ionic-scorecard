# -*- coding: utf-8 -*-
"""Annexure B, staged deployment illustration. Lumpsum vs 6-month vs 12-month staged entry on a
volatile synthetic path (rally, then a deep dip, then recovery) [ILLUSTRATIVE]. Ties to the
cash-until-deployed discipline in the deployment plan; un-deployed tranches earn a cash yield."""
import numpy as np
import chart_ext_b as CB
from chart_lib import NAVY as C_NAVY, GOLD as C_GOLD, NT1 as C_NT1
from slidekit import ML, UW, RX, SERIF, SLATE

LABELS = {
    "hni":    ("Staged deployment", "Lumpsum vs staged entry on a rough path"),
    "std":    ("Staged deployment", "Why the plan deploys in stages"),
    "simple": ("Staged deployment", "Why we invest the money in steps"),
}

CASH_Y = 6.5  # % p.a. on un-deployed tranches [ILLUSTRATIVE]


def _index(months=24, seed=42):
    """Synthetic volatile path: early rally, mid dip, recovery [ILLUSTRATIVE]."""
    anchors_m = [0, 4, 9, 14, 24]
    anchors_v = [100, 108, 82, 101, 118]
    m = np.arange(months + 1)
    base = np.interp(m, anchors_m, anchors_v)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1.1, months + 1); noise[0] = 0
    return base + noise


def _staged(idx, n_tranches):
    """Value of Rs 100 committed at t0, deployed in equal monthly tranches; cash accrues."""
    r = CASH_Y / 100.0 / 12.0
    units, cash, vals = 0.0, 100.0, []
    per = 100.0 / n_tranches
    for t, level in enumerate(idx):
        if t < n_tranches:
            units += per / level
            cash -= per
        vals.append(units * level + cash)
        cash *= (1 + r)
    return np.array(vals)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    idx = _index()
    m = np.arange(len(idx))
    lump = idx * (100.0 / idx[0])
    s6 = _staged(idx, 6)
    s12 = _staged(idx, 12)
    paths = [("Lumpsum", lump, C_NAVY), ("6-mo staged", s6, C_GOLD), ("12-mo staged", s12, C_NT1)]

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Synthetic 24-month path with a mid-way drawdown [ILLUSTRATIVE] · un-deployed "
                      f"cash at {CASH_Y:.1f}% p.a. · as of {as_of}")

    png = CB.staged_paths(m, paths, "annexb_staged")
    deck.pic(s, png, ML, 1.95, 7.25, 4.45, valign="top", halign="left")

    tx = ML + 7.45
    tw = RX - tx
    if reg == "simple":
        b1 = (f"All three lines start with the same Rs 100. The slowest entry ended highest here "
              f"(Rs {s12[-1]:.0f}) because it kept buying while prices were down; the other two "
              f"ended close together (Rs {lump[-1]:.0f} and Rs {s6[-1]:.0f}).")
        b2 = ("In a market that only goes up, investing everything at once wins. We stage because "
              "nobody knows which path comes next, and a bad first month should never hurt the "
              "whole corpus.")
    else:
        b1 = (f"On this path the 12-month stagger finishes ahead (Rs {s12[-1]:.0f}) because its "
              f"tranches kept buying through the dip; the 6-month stagger (Rs {s6[-1]:.0f}) had "
              f"already deployed most of the corpus before the fall and lands beside lumpsum "
              f"(Rs {lump[-1]:.0f}). On a straight-up path the ordering reverses; staging trades "
              f"some expected return for a smaller worst case.")
        b2 = ("Staging is regret control: it caps the damage of a badly-timed start at a fraction of "
              "the corpus. Hence the deployment plan's discipline: proceeds sit in liquid cash until "
              "each tranche's date, are deployed on settlement, and are never assumed invested.")
    deck.callout(s, tx, 1.95, tw, 2.2, "What the paths show", b1, kind="note")
    deck.callout(s, tx, 4.3, tw, 2.1, "Cash until deployed", b2, kind="human")

    deck.source(s, "Entry-path illustration on a synthetic price series [ILLUSTRATIVE]; not a "
                   "backtest or a forecast. Relative outcomes depend entirely on the path.")
    return 1
