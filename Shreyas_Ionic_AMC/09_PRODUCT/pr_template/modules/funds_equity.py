# -*- coding: utf-8 -*-
"""funds_equity, equity & index schemes vs their benchmark, with the FIRM's recommendations.
Principal ruling (2026-07-25): no upside/downside-capture graph in the client deck, and the deck
does NOT invent MF methodology; recommendations come from the Ionic MF desk (QFRA 2.0 for
long-term SIP; the 6m capture-ratio overlay for short-term/alpha, see qfra1-rerun skill).
This slide shows 3-5y performance vs benchmark + the desk's call, nothing more."""
import charts as CH
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, SANS, ML, UW, RX

VDISP = {"Redeem-to-Direct": "Switch"}  # display label only (Principal 2026-07-27); internal verdict code unchanged

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
    s = deck.content(2, "The Fund Book", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve · equity & index schemes · Direct-plan NAV, each scheme vs its own "
                      f"SEBI category benchmark (TRI) · as of {as_of}")

    # two charts, one per framework (Principal 2026-07-25): the long-term record and the
    # short-horizon framework's own decision variable — nothing invented, nothing contradictory
    # a fund that's a portfolio-construction call (consolidate index/passive exposure) rather
    # than a performance call has no independently-benchmarked cagr3y -- never chart it as 0%
    # A paired bar chart stops being readable past a handful of bars. ctx["chart_top_n"] caps BOTH
    # charts on this page to the largest N holdings by weight (Principal 2026-08-19: "too cluttered,
    # add only 6 on one graph ... only take top funds by wt"). The TABLE still lists every scheme, so
    # nothing is hidden -- the cap is a legibility choice, and the chart captions say so. Unset =
    # previous behaviour, so existing books are unchanged.
    TOPN = ctx.get("chart_top_n")

    def _cap(seq):
        if not TOPN or len(seq) <= TOPN:
            return seq, False
        return sorted(seq, key=lambda f: -f.get("weight_pct", 0))[:TOPN], True

    bfunds = [f for f in efunds if f.get("cagr3y") is not None]
    bfunds, b_capped = _cap(bfunds)
    labs = [_short(f["name"], 13) for f in bfunds]
    fv = [f["cagr3y"] for f in bfunds]
    bv = [f.get("bench_cagr3y") if f.get("bench_cagr3y") is not None else 13.0 for f in bfunds]
    _cap_note = f" · LARGEST {TOPN} HOLDINGS BY WEIGHT" if b_capped else ""
    deck.txt(s, ML, 1.98, 6.5, 0.2, [("THE LONG-TERM TEST · 3-YEAR RECORD VS OWN CATEGORY BENCHMARK"
                                      + _cap_note, SANS, 8, NAVY, True, False, 80)])
    if bfunds:
        png = CH.paired_bar(labs, fv, bv, "fe_vs_bm", a_label="Fund (3y CAGR)", b_label="Its category benchmark",
                            figsize=(7.6, 3.0))
        deck.pic(s, png, ML, 2.2, 6.5, 1.95, valign="top")
    else:
        deck.callout(s, ML, 2.2, 6.5, 1.95, "No funds scored yet",
                     "No equity or index-style funds are scored under this category yet.", kind="note")

    # short-horizon framework: how much of the index's falls each active fund takes,
    # against the framework's own category cutoff (its literal pass/fail line)
    CUT = {"Large": 90.0, "Multi": 90.0, "Mid": 80.0}
    # 2026-07-28: down_capture is frequently None for real clients (thin fund NAV history
    # firm-wide, per root CLAUDE.md DATA LANDMINES) -- filter before charting, don't pass None
    # into a numeric bar chart.
    act = [f for f in efunds if f["category"] != "passive" and f.get("down_capture") is not None]
    act, a_capped = _cap(act)
    _cap_note2 = f" · LARGEST {TOPN} BY WEIGHT" if a_capped else ""
    deck.txt(s, ML, 4.38, 6.5, 0.2, [("THE SHORT-HORIZON TEST · PARTICIPATION IN FALLS VS THE CUTOFF"
                                      + _cap_note2, SANS, 8, NAVY, True, False, 80)])
    if act:
        labs2 = [_short(f["name"], 13) for f in act]
        dcap = [f["down_capture"] for f in act]
        cuts = [next((v for k, v in CUT.items() if k in f["name"]), 100.0) for f in act]
        png2 = CH.paired_bar(labs2, dcap, cuts, "fe_dcap", a_label="Share of benchmark falls taken (6m, %)",
                             b_label="Framework cutoff", figsize=(7.6, 3.0))
        deck.pic(s, png2, ML, 4.6, 6.5, 1.85, valign="top")
        deck.txt(s, ML, 6.42, 6.5, 0.18,
                 [("Navy = fund, light = the framework's line · below the line passes", SERIF, 8, SLATE, False, True)])
    else:
        deck.callout(s, ML, 4.6, 6.5, 1.85, "No actively-managed funds to test",
                     "No actively-managed equity-style funds are scored under this category yet.", kind="note")

    tx = 7.65; tw = RX - tx
    cols = [("Scheme", 0.40, "l"), ("3y CAGR", 0.18, "r"), ("vs BM", 0.16, "r"), ("Desk call", 0.26, "c")]
    rows = []
    for f in efunds:
        if f.get("cagr3y") is None:
            rows.append([_short(f["name"], 18), "n/a",
                         ("c", "n/a", SLATE, False),
                         ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
            continue
        d = f["cagr3y"] - (f.get("bench_cagr3y") if f.get("bench_cagr3y") is not None else 13.0)
        rows.append([_short(f["name"], 18), f"{f['cagr3y']:.1f}%",
                     ("c", f"{d:+.1f}", HOLD if d >= 0 else SELL, True),
                     ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
    # PAGINATION (added 2026-08-19). This table was unpaginated and always returned 1 slide, so a
    # book with many equity schemes ran straight off the page: a 43-holding MF-only book put 28 rows
    # here, reaching 12.33in on a 7.5in slide -- 75 shapes below the trim, invisible in the deck and
    # silently lost. Same defect class as the flags valve fixed in data_notes on 2026-08-02.
    # Backwards-compatible: at or under _ROWS_P1 rows nothing changes -- one slide, chart + table.
    # 6 on page 1: the "where the calls come from" callout is pinned at y=5.1, so the table must
    # end above it (2.0 + 0.33 header + 6*0.40 = 4.73). 10 on continuation pages, which have no
    # callout but must still clear the source line and footer (2.0 + 0.33 + 10*0.40 = 6.33).
    _ROWS_P1, _ROWS_PN = 6, 10
    extra_pages = []
    if len(rows) > _ROWS_P1:
        extra_pages = [rows[i:i + _ROWS_PN] for i in range(_ROWS_P1, len(rows), _ROWS_PN)]
        rows = rows[:_ROWS_P1]
    ty = deck.table(s, tx, 2.0, tw, cols, rows, rowh=0.40, fs=9, hfs=7.5)

    body = ("Fund calls follow our fund-quality frameworks, a long-term view and a short-horizon "
            "overlay, refreshed regularly. This review applies those calls "
            "to your holdings; it does not re-score the funds."
            if not simple else
            "These suggestions come from our fund-research desk's standing framework, applied to the "
            "funds you hold.")
    deck.callout(s, tx, min(ty + 0.18, 5.1), tw, 1.35, "Where the calls come from", body, kind="note")

    demo_tag = " · illustrative synthetic funds." if ctx.get("is_demo", False) else "."
    src = ("3y CAGR and down-capture vs each scheme's own SEBI category benchmark (TRI), "
           "Direct-plan NAV, common 3y window · fund recommendations per the "
           "Ionic MF desk (long-term + short-term frameworks)" + demo_tag)
    deck.source(s, src)

    # continuation pages: table only, full width, header repeated. No chart -- the charts describe
    # the whole set once and repeating them would imply a different sample per page.
    n = 1
    for pg, chunk in enumerate(extra_pages, 2):
        s2 = deck.content(2, "The Fund Book", eyebrow,
                          f"{title}  ({pg} of {len(extra_pages) + 1})")
        deck.scope_tag(s2, f"MF sleeve · equity & index schemes, continued · as of {as_of}")
        deck.table(s2, ML, 2.0, UW, cols, chunk, rowh=0.40, fs=9, hfs=7.5)
        deck.source(s2, src)
        deck.score_band(s2)
        n += 1
    return n
