# -*- coding: utf-8 -*-
"""Annexure A7 - concentration curve: cumulative weight of the equity book vs number of
holdings (largest first), against an equal-weight diagonal, markers at top-5/10/20."""
import chart_ext_a as CA
from slidekit import ML, RX

LABELS = {
    "hni":    ("How top-heavy is the equity book",
               "Cumulative weight curve vs an equal-weight reference line"),
    "std":    ("How much rides on the first few names",
               "Cumulative share of the equity book, largest holdings first"),
    "simple": ("How much rides on the top names",
               "A few large positions carry most of the equity book"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    weights = sorted((e["weight_pct"] for e in ctx["equity"]), reverse=True)
    n = len(weights)
    if n < 5:
        return 0  # 2026-07-28: a fund-heavy client with <5 direct holdings has no meaningful
                  # concentration curve to show; the old ternary only guarded c20, not c5/c10
    tot = sum(weights)
    cum = []
    run = 0.0
    for w in weights:
        run += w
        cum.append(run / tot * 100.0)
    c5, c10, c20 = cum[4], (cum[9] if n >= 10 else cum[-1]), (cum[19] if n >= 20 else cum[-1])
    cap = ctx["ips"]["single_name_cap_pct"]
    over = sum(1 for e in ctx["equity"] if e["weight_pct"] > cap)

    s = deck.content(5, "Annexure", eyebrow, title)
    # real client weights, not a placeholder -- no [ILLUSTRATIVE] tag needed (unlike the
    # synthetic-proxy annex pages elsewhere in this annexure)
    deck.scope_tag(s, f"Direct-equity sleeve only · {n} holdings · weights as "
                      f"share of the equity book · as of {as_of}")

    png = CA.concentration_curve(weights, "axa_conc")
    deck.pic(s, png, ML, 1.85, 7.0, 4.55, valign="top")

    tx = 8.1; tw = RX - tx
    cols = [("Basket", 0.38, "l"), ("This book", 0.32, "r"), ("Equal weight", 0.30, "r")]
    # only show a basket row that's smaller than the book itself -- "Top 10" of a 7-holding
    # book is a nonsensical >100%-equal-weight row (2026-07-28 fix)
    rows = [["Top 5", ("b", f"{c5:.0f}%"), f"{5 / n * 100:.0f}%"]]
    if n > 10:
        rows.append(["Top 10", ("b", f"{c10:.0f}%"), f"{10 / n * 100:.0f}%"])
    if n > 20:
        rows.append(["Top 20", ("b", f"{c20:.0f}%"), f"{20 / n * 100:.0f}%"])
    deck.table(s, tx, 1.95, tw, cols, rows, rowh=0.36, fs=10, hfs=8)

    body1 = ("The faster the curve climbs, the more the book depends on its first few names. "
             "The dashed diagonal is a book of equal slices; the space between the two lines is "
             "the concentration, made visible.")
    deck.callout(s, tx, 3.6, tw, 1.4, "How to read the curve", body1, kind="note")

    body2 = (f"Use this page alongside the {cap:.0f}% single-name cap in the IPS: {over} name(s) "
             f"sit above the cap today, and the planned trims pull the front of this curve down "
             f"toward the diagonal.")
    deck.callout(s, tx, 5.15, tw, 1.35, "When to use this view", body2, kind="human")

    deck.source(s, f"Cumulative weights of the {n} direct-equity holdings, largest first, as a "
                   f"share of the equity book; equal-weight line = 100/{n} per name.")
    return 1
