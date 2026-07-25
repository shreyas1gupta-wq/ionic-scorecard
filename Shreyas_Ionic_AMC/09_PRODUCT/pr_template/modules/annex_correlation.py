# -*- coding: utf-8 -*-
"""Annexure A2 - correlation grid of the top-8 direct-equity holdings (synthetic but plausible
pairwise correlations) with a 'diversification actually held' read."""
import chart_ext_a as CA
from slidekit import ML, RX

GROUP = {"BAJFINANCE": "fin", "HDFCBANK": "fin", "ICICIBANK": "fin", "SBIN": "fin",
         "JIOFIN": "fin", "BANDHANBNK": "fin",
         "SUNPHARMA": "def", "CIPLA": "def", "ITC": "def"}

LABELS = {
    "hni":    ("What the top eight actually share",
               "Pairwise correlation of the largest direct-equity holdings"),
    "std":    ("Do the big holdings move together?",
               "Pairwise correlation of the top-8 direct-equity positions"),
    "simple": ("Do the big holdings move together?",
               "Dark squares move together, green squares balance each other"),
}


def _pair(si, sj, i, j):
    gi, gj = GROUP.get(si), GROUP.get(sj)
    if gi == "fin" and gj == "fin":
        base = 0.74
    elif gi == "def" or gj == "def":
        base = 0.28
    else:
        base = 0.44
    jit = (((i * 7 + j * 13) % 9) - 4) * 0.012
    return max(0.15, min(0.90, base + jit))


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    top8 = sorted(ctx["equity"], key=lambda e: -e["weight_pct"])[:8]
    syms = [e["symbol"] for e in top8]
    n = len(syms)
    M = [[1.0 if i == j else _pair(syms[i], syms[j], i, j) for j in range(n)] for i in range(n)]

    # stats for the read
    pairs = [(M[i][j], syms[i], syms[j]) for i in range(n) for j in range(i)]
    avg = sum(p[0] for p in pairs) / len(pairs)
    mxv, mxa, mxb = max(pairs); mnv, mna, mnb = min(pairs)
    nfin = sum(1 for x in syms if GROUP.get(x) == "fin")

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Top-8 direct-equity holdings by weight · synthetic "
                      f"pairwise correlations · as of {as_of}")

    png = CA.corr_heat(syms, M, "axa_corr")
    deck.pic(s, png, ML, 1.85, 6.5, 4.7, valign="top")

    tx = 7.57; tw = RX - tx
    body1 = (f"The {nfin} financial names move as a block: {mxa} and {mxb} top the grid at "
             f"{mxv:.2f}. {mna} against {mnb} is the most independent pair at {mnv:.2f}. Average "
             f"pairwise correlation is {avg:.2f}, so these eight tickers diversify like a "
             f"smaller handful.")
    deck.callout(s, tx, 1.95, tw, 1.95, "Diversification actually held", body1, kind="note")

    body2 = ("Bring this page out when the number of holdings is offered as diversification. "
             "Portfolio risk is set by how much the names respond to the same forces (rates, "
             "credit, the consumer); a ninth name from the same cluster adds little.")
    deck.callout(s, tx, 4.10, tw, 1.85, "When to use this view", body2, kind="human")

    deck.source(s, "Synthetic correlation estimates for illustration, patterned on typical "
                   "3-year weekly-return relationships; not measured from market data. "
                   "[ILLUSTRATIVE]")
    return 1
