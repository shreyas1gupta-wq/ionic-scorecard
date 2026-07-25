# -*- coding: utf-8 -*-
"""Annexure A5 - days-to-exit ladder: % of the book exitable in 1d / 2-5d / 6-10d / >10d at
20% of average daily volume, with the honest note on the two big positions."""
import chart_ext_a as CA
from slidekit import ML, UW

BUCKETS = ["1 day", "2-5 days", "6-10 days", "over 10 days"]
BAND_BUCKET = {"Large": 0, "Mid": 1, "Small": 2, "Micro": 3}
# synthetic liquidity tier per name at pooled-mandate size (0=1d, 1=2-5d, 2=6-10d, 3=>10d)
LIQ_TIER = {
    "APLAPOLLO": 1, "PERSISTENT": 1, "NATIONALUM": 1, "MOTHERSON": 1, "VBL": 1,
    "TATATECH": 1, "BOSCHLTD": 1, "POWERINDIA": 1, "IRCTC": 1,
    "DEEPAKNTR": 2, "COCHINSHIP": 2, "ITCHOTELS": 2, "BANDHANBNK": 2,
    "HINDCOPPER": 3, "CMSINFO": 3,
}

LABELS = {
    "hni":    ("How fast this book turns into cash",
               "Share of the book exitable per days-to-exit bucket, at 20% of daily volume"),
    "std":    ("If the book had to be sold, how long would it take?",
               "Share of the portfolio exitable within each time window"),
    "simple": ("How quickly this can become cash",
               "Most of the book can be sold within a week"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    b = [0.0, 0.0, 0.0, 0.0]
    b[0] += ctx["totals"]["cash_pct"]                       # cash: same day
    for e in ctx["equity"]:
        t = LIQ_TIER.get(e["symbol"], BAND_BUCKET.get(e["mcap_band"], 1))
        b[t] += e["weight_pct"]
    for f in ctx["funds"]:
        b[1] += f["weight_pct"]                             # MF redemption settles T+2/T+3
    tot = sum(b)
    b = [x / tot * 100.0 for x in b]

    big = sorted(ctx["equity"], key=lambda e: -e["weight_pct"])[:2]

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Whole book (equity + funds + cash) · exit at 20% of "
                      f"assumed daily volume, pooled-mandate scale · as of {as_of}")

    deck.kpi_strip(s, [(f"{b[0]:.0f}%", "exitable in 1 day"),
                       (f"{b[0] + b[1]:.0f}%", "exitable within a week"),
                       (f"{b[3]:.1f}%", "needs over 10 days")], y=1.9)

    png = CA.liquidity_ladder(BUCKETS, b, "axa_liq")
    deck.pic(s, png, ML, 3.0, UW, 1.8, valign="top")

    n1, n2 = big[0]["symbol"], big[1]["symbol"]
    body1 = (f"The two largest positions, {n1} ({big[0]['weight_pct']:.1f}%) and {n2} "
             f"({big[1]['weight_pct']:.1f}%), sit in the 1-day bucket: their traded volumes are "
             f"deep enough that size alone does not slow the exit. The slow tail is the clutter "
             f"of small positions in thinner names, where the Sell list already concentrates.")
    deck.callout(s, ML, 4.95, 5.62, 1.55, "The two big positions", body1, kind="note")

    body2 = ("Exit math assumes taking at most a fifth of a day's traded volume, slow enough "
             "not to move the price against the book. Use this page before any large redemption "
             "plan: it sets a timetable the market can actually fill.")
    deck.callout(s, ML + 5.77, 4.95, UW - 5.77, 1.55, "Why 20% of daily volume", body2,
                 kind="human")

    deck.source(s, "Days-to-exit at 20% of assumed average daily volume per name; synthetic "
                   "liquidity tiers assessed at pooled-mandate size, not this account alone; "
                   "mutual funds mapped to T+2/T+3 redemption settlement. [ILLUSTRATIVE]")
    return 1
