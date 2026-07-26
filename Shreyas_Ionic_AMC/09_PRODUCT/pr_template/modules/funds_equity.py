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
    deck.scope_tag(s, f"MF sleeve · equity & index schemes · Direct-plan NAV, each scheme vs its own "
                      f"SEBI category benchmark (TRI) · as of {as_of}")

    # two charts, one per framework (Principal 2026-07-25): the long-term record and the
    # short-horizon framework's own decision variable — nothing invented, nothing contradictory
    labs = [_short(f["name"], 13) for f in efunds]
    fv = [f["cagr3y"] for f in efunds]
    bv = [f.get("bench_cagr3y", 13.0) for f in efunds]
    png = CH.paired_bar(labs, fv, bv, "fe_vs_bm", a_label="Fund (3y CAGR)", b_label="Its category benchmark",
                        figsize=(7.6, 3.0))
    deck.txt(s, ML, 1.98, 6.5, 0.2, [("THE LONG-TERM TEST · 3-YEAR RECORD VS OWN CATEGORY BENCHMARK", SANS, 8, NAVY, True, False, 80)])
    deck.pic(s, png, ML, 2.2, 6.5, 1.95, valign="top")

    # short-horizon framework: how much of the index's falls each active fund takes,
    # against the framework's own category cutoff (its literal pass/fail line)
    CUT = {"Large": 90.0, "Multi": 90.0, "Mid": 80.0}
    act = [f for f in efunds if f["category"] != "passive"]
    labs2 = [_short(f["name"], 13) for f in act]
    dcap = [f["down_capture"] for f in act]
    cuts = [next((v for k, v in CUT.items() if k in f["name"]), 100.0) for f in act]
    png2 = CH.paired_bar(labs2, dcap, cuts, "fe_dcap", a_label="Share of benchmark falls taken (6m, %)",
                         b_label="Framework cutoff", figsize=(7.6, 3.0))
    deck.txt(s, ML, 4.38, 6.5, 0.2, [("THE SHORT-HORIZON TEST · PARTICIPATION IN FALLS VS THE CUTOFF",
                                      SANS, 8, NAVY, True, False, 80)])
    deck.pic(s, png2, ML, 4.6, 6.5, 1.85, valign="top")
    deck.txt(s, ML, 6.42, 6.5, 0.18,
             [("Navy = fund, light = the framework's line · below the line passes", SERIF, 8, SLATE, False, True)])

    tx = 7.65; tw = RX - tx
    cols = [("Scheme", 0.40, "l"), ("3y CAGR", 0.18, "r"), ("vs BM", 0.16, "r"), ("Desk call", 0.26, "c")]
    rows = []
    for f in efunds:
        d = f["cagr3y"] - f.get("bench_cagr3y", 13.0)
        rows.append([_short(f["name"], 18), f"{f['cagr3y']:.1f}%",
                     ("c", f"{d:+.1f}", HOLD if d >= 0 else SELL, True),
                     ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
    ty = deck.table(s, tx, 2.0, tw, cols, rows, rowh=0.40, fs=9, hfs=7.5)

    body = ("Fund calls follow our fund-quality frameworks, a long-term view and a short-horizon "
            "overlay, refreshed regularly. This review applies those calls "
            "to your holdings; it does not re-score the funds."
            if not simple else
            "These suggestions come from our fund-research desk's standing framework, applied to the "
            "funds you hold.")
    deck.callout(s, tx, min(ty + 0.18, 5.1), tw, 1.35, "Where the calls come from", body, kind="note")

    deck.source(s, "3y CAGR and down-capture vs each scheme's own SEBI category benchmark (TRI), "
                   "Direct-plan NAV, common 3y window · fund recommendations per the "
                   "Ionic MF desk (long-term + short-term frameworks) · illustrative synthetic funds.")
    return 1
