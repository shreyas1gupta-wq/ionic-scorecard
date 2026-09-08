# -*- coding: utf-8 -*-
"""all_holdings, every position in the book on one list: funds, direct shares and everything else.

WHY THIS EXISTS SEPARATELY FROM holdings_detail. That page is the direct-equity annexure and its
columns are Stock Scorecard fields, a sector, an Ionic Score and two horizon scores. A book reviewed
from a holding statement has none of those, so the page rendered a title, a scope tag and nineteen
rows of empty cells under the heading "All holdings, scored". A client page that promises everything
and shows nothing is worse than no page at all.

This one lists what the review actually knows: what the holding is, what it is worth, its share of
the WHOLE book, the desk's call where there is one, and the two risk axes. A holding the desk does
not score still appears, because it is still the client's money. Not reviewed is not not held.
"""
import math

from slidekit import (NAVY, GOLD, INK, SLATE, SELL, HOLD, AMBER, SANS, SERIF, ML, UW, RX,
                      short_name)

PER = 16

LABELS = {
    "hni": {"eyebrow": "Every holding", "title": "The whole book, position by position"},
    "std": {"eyebrow": "Every holding", "title": "Everything you hold, in one list"},
    "simple": {"eyebrow": "Everything you own", "title": "Your complete list of holdings"},
}
CALL_STYLE = {"Sell": SELL, "Trim": AMBER, "Hold (watch)": AMBER, "Hold": HOLD}
_CLASS_ORDER = {"Equity": 0, "Fixed Income": 1, "Alternates": 2, "Other": 3}


def _rows(ctx):
    out = []
    for f in ctx.get("funds") or []:
        out.append(dict(name=f.get("name") or "", kind="Fund",
                        cls=(f.get("asset_class") or "").strip() or "Equity",
                        w=f.get("weight_pct") or 0.0, v=f.get("value_inr") or 0.0,
                        call=f.get("verdict") or "No View",
                        score=f.get("qfra"), rb=f.get("risk_band"), lb=f.get("liq_band")))
    for e in ctx.get("equity") or []:
        out.append(dict(name=e.get("name") or "", kind="Share",
                        cls=(e.get("asset_class") or "").strip() or "Equity",
                        w=e.get("weight_pct") or 0.0, v=e.get("value_inr") or 0.0,
                        call=e.get("rec") or "No View", score=e.get("ionic_score"),
                        rb=e.get("risk_band"), lb=e.get("liq_band")))
    for o in ctx.get("other") or []:
        sub = (o.get("sub_category") or "").strip()
        out.append(dict(name=o.get("name") or "", kind=sub or "Other",
                        cls=(o.get("asset_class") or "").strip() or "Other",
                        w=o.get("weight_pct") or 0.0, v=o.get("value_inr") or 0.0,
                        call=o.get("rec") or "No View", score=None,
                        rb=o.get("risk_band"), lb=o.get("liq_band")))
    # asset class first so the list reads as a portfolio, then size inside each class
    out.sort(key=lambda r: (_CLASS_ORDER.get(r["cls"], 9), -r["w"]))
    return out


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    rows = _rows(ctx)
    if not rows:
        return 0
    asof = ctx["client"]["as_of"]
    grand = float(ctx["totals"].get("grand_inr") or 0) or sum(r["v"] for r in rows)
    # THE PLAIN-LANGUAGE DECK IS A CONVERSATION, NOT A REGISTER. This page lists every position,
    # which on a family book is thirteen consecutive slides of small type in a deck whose whole
    # design target is under twenty pages for a newer investor. The largest are shown, the tail is
    # counted and valued in a line, and the complete list travels with the deck as the holdings
    # workbook, which is the better place to read 227 rows anyway.
    _cap_pages = 2 if reg == "simple" else None
    _all_n, _all_v = len(rows), sum(r["v"] for r in rows)
    if _cap_pages:
        rows = rows[:PER * _cap_pages]
    pages = max(1, math.ceil(len(rows) / PER))

    cols = [("Holding", 0.34, "l"), ("What it is", 0.17, "l"), ("Asset class", 0.12, "l"),
            ("Value", 0.11, "r"), ("Wt %", 0.07, "r"), ("Score", 0.06, "r"),
            ("Risk", 0.06, "c"), ("Liq", 0.06, "c"), ("Call", 0.11, "c")]

    n = 0
    for p in range(pages):
        chunk = rows[p * PER:(p + 1) * PER]
        title = L["title"] + (f"  (page {p + 1} of {pages})" if pages > 1 else "")
        s = deck.content(5, "Annexure", L["eyebrow"], title)
        if p == 0:
            deck.anchor("mod:all_holdings", s, prio=4)
        deck.scope_tag(s, f"{len(rows)} holdings · Rs {grand:,.0f} · as of {asof}")

        body = []
        for r in chunk:
            body.append([
                short_name(r["name"], 40),
                short_name(r["kind"], 20),
                r["cls"],
                f"{r['v']:,.0f}",
                # A held position that rounds to 0.0% shows as under a tenth, not as nothing.
                ("<0.1" if r["w"] < 0.05 and r["v"] > 0 else f"{r['w']:.1f}"),
                "-" if r["score"] is None else f"{float(r['score']):.0f}",
                (r["rb"] or "-")[:1] if r["rb"] else "-",
                (r["lb"] or "-")[:1] if r["lb"] else "-",
                ("pill", r["call"], r["call"]) if r["call"] in CALL_STYLE else r["call"],
            ])
        deck.table(s, ML, 2.02, UW, cols, body, rowh=0.27, fs=7.5, hfs=7)
        _tail_n = _all_n - len(rows)
        if _tail_n and p == pages - 1:
            deck.source(s, "The %d largest of your %d holdings are shown here, Rs %s of Rs %s. "
                           "The remaining %d, Rs %s between them, are listed in full in the "
                           "holdings workbook that comes with this deck; every one of them counts "
                           "in the totals and the weights on these pages."
                           % (len(rows), _all_n, f"{sum(r['v'] for r in rows):,.0f}",
                              f"{_all_v:,.0f}", _tail_n, f"{_all_v - sum(r['v'] for r in rows):,.0f}"))
            deck.score_band(s)
            n += 1
            continue
        deck.source(s, "Weight is a share of the whole portfolio, funds and everything else "
                       "together. Risk and Liq are the two framework bands, H, M or L; a dash "
                       "means the framework does not place that holding. Score is the fund score "
                       "out of 100 where one exists. A holding the desk issues no call on is still "
                       "listed, because it is still held.")
        deck.score_band(s)
        n += 1
    return n
