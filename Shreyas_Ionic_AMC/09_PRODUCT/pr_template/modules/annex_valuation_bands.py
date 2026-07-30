# -*- coding: utf-8 -*-
"""Annexure B, valuation bands. Book-level weighted trailing P/E marked against a 10-year
percentile band (p10/p25/median/p75/p90). The band is synthetic [ILLUSTRATIVE] pending a real
index-blend history; the weighted P/E is computed from the actual holdings."""
import chart_ext_b as CB
from slidekit import ML, UW, RX

LABELS = {
    "hni":    ("Valuation check", "The book's P/E against its own 10-year range"),
    "std":    ("Valuation check", "How expensive the book is versus its own history"),
    "simple": ("Valuation check", "Is the book expensive right now"),
}

# 10-year percentile band for the book's sector blend [ILLUSTRATIVE]
P10, P25, P50, P75, P90 = 22.0, 26.0, 31.0, 37.0, 44.0
PE_CAP = 150.0  # exclude broken/extreme trailing multiples from the aggregate


def _weighted_pe(eq):
    pairs = [(e["weight_pct"], e["pe"]) for e in eq if e["pe"] and 0 < e["pe"] < PE_CAP]
    cov = sum(w for w, _ in pairs)
    if cov == 0:
        return None, 0.0  # 2026-07-28: no holding has a usable trailing PE -- honest gap, not a crash
    wpe = sum(w * p for w, p in pairs) / cov
    return round(wpe, 1), round(cov, 1)


def _pctile(v):
    xs = [P10, P25, P50, P75, P90]; ys = [10, 25, 50, 75, 90]
    if v <= xs[0]:
        return 10
    if v >= xs[-1]:
        return 90
    for i in range(len(xs) - 1):
        if xs[i] <= v <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (v - xs[i]) / (xs[i + 1] - xs[i])
    return 50


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    as_of = ctx["client"]["as_of"]
    wpe, cov = _weighted_pe(eq)
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    if wpe is None:
        deck.callout(s, ML, 1.95, UW, 2.0, "Not available",
                     "Book-level P/E isn't available yet — trailing multiples aren't captured "
                     "for this book's holdings.", kind="note")
        deck.source(s, f"Direct equity book · as of {as_of}.")
        return 1
    pct = _pctile(wpe)
    deck.scope_tag(s, f"Direct equity book · weighted trailing P/E on {cov:.0f}% of book weight "
                      f"(usable multiples below {PE_CAP:.0f}x) · as of {as_of} · band [ILLUSTRATIVE]")

    png = CB.percentile_gauge(P10, P25, P50, P75, P90, wpe, "annexb_valband",
                              today_note=f"~{pct:.0f}th percentile")
    deck.pic(s, png, ML, 1.95, 7.15, 4.45, valign="top", halign="left")

    rx = ML + 7.35
    rw = RX - rx
    if pct >= 65:
        zone, impl_simple, impl_detail = "high", "priced for a lot of good news", "sits high"
        b2_body = ("A high percentile is not a timing signal: expensive books can stay expensive for "
                   "years. What it does change is the margin of safety, so the bar for adding rises, "
                   "the case for trimming the weakest scores strengthens, and staged deployment of new "
                   "money matters more.")
    elif pct <= 35:
        zone, impl_simple, impl_detail = "low", "priced modestly relative to history", "sits low"
        b2_body = ("A low percentile does not guarantee high returns, but it does mean the starting "
                   "price gives more room for error. Holdings that score well on quality benefit from "
                   "this cushion; the weakest names still deserve scrutiny on their own standing.")
    else:
        zone, impl_simple, impl_detail = "mid-range", "priced around its historical mid-point", "sits mid-range"
        b2_body = ("A mid-range starting price is neither a tailwind nor a headwind. It says little "
                   "about near-term returns; the individual holdings' scores and business quality "
                   "matter more than the aggregate multiple here.")
    if reg == "simple":
        b1 = (f"The book trades at about {wpe:.0f}x trailing earnings, in the {zone} end of its "
              f"usual 10-year range. That means the holdings are {impl_simple}.")
        b2 = b2_body
    else:
        b1 = (f"The weighted trailing P/E of the direct book is {wpe:.1f}x, around the {pct:.0f}th "
              f"percentile of the illustrative 10-year band for this sector blend. The starting "
              f"multiple is the one return driver already known today, and it {impl_detail}.")
        b2 = b2_body
    deck.callout(s, rx, 1.95, rw, 2.15, "What this says", b1, kind="note")
    deck.callout(s, rx, 4.25, rw, 2.15, "What it does not say", b2, kind="human")

    deck.source(s, f"Weighted trailing P/E over the {cov:.0f}% of book weight with usable multiples "
                   f"(extremes above {PE_CAP:.0f}x excluded); 10-year percentile band is synthetic "
                   f"[ILLUSTRATIVE] pending index-blend history.")
    return 1
