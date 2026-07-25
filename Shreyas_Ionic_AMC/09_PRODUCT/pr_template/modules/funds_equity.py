# -*- coding: utf-8 -*-
"""funds_equity, equity & index schemes vs their benchmark, with the FIRM's recommendations.
Principal ruling (2026-07-25): no upside/downside-capture graph in the client deck, and the deck
does NOT invent MF methodology; recommendations come from the Ionic MF desk (QFRA 2.0 for
long-term SIP; the 6m capture-ratio overlay for short-term/alpha, see qfra1-rerun skill).
This slide shows 3-5y performance vs benchmark + the desk's call, nothing more."""
import charts as CH
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, SANS, ML, UW, RX

VDISP = {"Redeem-to-Direct": "To-Direct"}

LABELS = {
    "hni":    ("Equity funds vs benchmark", "Three-year record against the index, and the desk's call"),
    "std":    ("Equity funds vs benchmark", "How each fund has compounded against its index"),
    "simple": ("Your equity funds", "How each fund has done against the market, and what we suggest"),
}


def _short(name, n=22):
    name = name.replace(" Fund", "").replace(" (Regular)", "").replace(" (Direct)", "")
    from slidekit import short_name
    return short_name(name, n)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    as_of = ctx["client"]["as_of"]
    efunds = [f for f in ctx["funds"] if f["category"] in ("equity", "passive")]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(3, "Funds", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve · equity & index schemes · Direct-plan NAV vs total-return benchmark · as of {as_of}")

    labs = [_short(f["name"], 13) for f in efunds]
    fv = [f["cagr3y"] for f in efunds]
    bv = [f.get("bench_cagr3y", 13.0) for f in efunds]
    png = CH.paired_bar(labs, fv, bv, "fe_vs_bm", a_label="Fund (3y CAGR)", b_label="Benchmark")
    deck.pic(s, png, ML, 2.0, 6.5, 3.5, valign="top")
    deck.txt(s, ML, 5.66, 6.5, 0.2,
             [("Navy = fund, light = benchmark · 3-year CAGR, % p.a. (demo period)", SERIF, 8, SLATE, False, True)])

    tx = 7.65; tw = RX - tx
    cols = [("Scheme", 0.40, "l"), ("3y CAGR", 0.18, "r"), ("vs BM", 0.16, "r"), ("Desk call", 0.26, "c")]
    rows = []
    for f in efunds:
        d = f["cagr3y"] - f.get("bench_cagr3y", 13.0)
        rows.append([_short(f["name"], 18), f"{f['cagr3y']:.1f}%",
                     ("c", f"{d:+.1f}", HOLD if d >= 0 else SELL, True),
                     ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
    ty = deck.table(s, tx, 2.0, tw, cols, rows, rowh=0.40, fs=9, hfs=7.5)

    body = ("Fund calls follow the Ionic MF desk's own framework: the long-term SIP engine and a "
            "short-horizon overlay, refreshed on the desk's cadence. This review applies those calls "
            "to your holdings; it does not re-score the funds."
            if not simple else
            "These suggestions come from our fund-research desk's standing framework, applied to the "
            "funds you hold.")
    deck.callout(s, tx, min(ty + 0.18, 5.1), tw, 1.35, "Where the calls come from", body, kind="note")

    deck.source(s, "3y CAGR vs total-return benchmark, Direct-plan NAV · fund recommendations per the "
                   "Ionic MF desk (long-term + short-term frameworks) · illustrative synthetic funds.")
    return 1
