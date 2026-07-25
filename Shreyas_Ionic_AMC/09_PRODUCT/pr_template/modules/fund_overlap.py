# -*- coding: utf-8 -*-
"""fund_overlap (F17), 'Where you're duplicating exposure'. Renamed from the ambiguous v8 'fund overlap'.
Panel A: funds duplicating each other. Panel B: stocks held BOTH directly AND via funds (double-paying
an active fee to re-buy what you already own). Headline: X% of AUM re-buys direct holdings at Y bps."""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, ML, UW, RX, PANEL

LABELS = {
    "hni":    ("Where you're duplicating exposure", "Two schemes, one bet, and stocks you already own directly"),
    "std":    ("Where you're duplicating exposure", "Funds that overlap, and stocks you pay a fund to re-buy"),
    "simple": ("Are you paying twice?", "Some funds may buy the same shares you already own"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    ov = ctx["overlap"]
    fd = ov["fund_direct"]                       # (stock, direct_pct, via_funds_pct, n_funds)
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(3, "Funds", eyebrow, title)

    # headline stat band
    deck.kpi_strip(s, [
        (f"{ov['headline_pct']:.1f}%", "of AUM re-bought via funds", "stocks already held directly", SELL),
        (f"~{ov['headline_bps']} bps", "avg active fee on that slice", "paid to duplicate", AMBER),
        (f"{len(fd)}", "double-paid names", "direct + fund overlap", NAVY),
    ], y=1.85)

    # Panel B — fund-vs-direct double-pay table (the decision-relevant one, stays core)
    deck.txt(s, ML, 3.15, UW, 0.3, [("STOCKS HELD BOTH DIRECTLY AND INSIDE YOUR FUNDS", "Bahnschrift", 10, NAVY, True, False, 40)])
    cols = [("Stock", 0.34, "l"), ("Held directly", 0.18, "r"), ("Via funds (look-through)", 0.26, "r"),
            ("In # funds", 0.14, "c"), ("Combined", 0.14, "r")]
    rows = []
    for (stock, direct, via, nf) in fd:
        combined = direct + via
        rows.append([stock, f"{direct:.1f}%", f"{via:.1f}%", str(nf),
                     ("c", f"{combined:.1f}%", SELL if combined > 10 else INK, True)])
    deck.table(s, ML, 3.55, UW, cols, rows, rowh=0.36, fs=10, hfs=8)

    yb = 3.55 + 0.33 + 0.36 * len(rows) + 0.2
    body = ("Every rupee a fund holds in a stock you already own directly pays an active management fee to "
            "buy exposure you have for free. It also quietly concentrates the book: the look-through weight "
            "in these names is higher than the direct line suggests. The fix isn't necessarily to sell the "
            "funds · it's to count this exposure when we size the direct positions and the fund switches.")
    deck.callout(s, ML, min(yb, 5.35), UW, 1.15, "Two schemes, one bet, two fees", body, kind="note")
    deck.source(s, "Fund-vs-direct look-through from latest scheme portfolio disclosures (illustrative for the "
                   "demo). Full pairwise scheme-overlap heatmap in the annexure.")
    return 1
