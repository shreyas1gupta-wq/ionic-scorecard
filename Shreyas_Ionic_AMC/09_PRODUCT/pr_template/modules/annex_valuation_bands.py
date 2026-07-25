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
    pct = _pctile(wpe)
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Direct equity book · weighted trailing P/E on {cov:.0f}% of book weight "
                      f"(usable multiples below {PE_CAP:.0f}x) · as of {as_of} · band [ILLUSTRATIVE]")

    png = CB.percentile_gauge(P10, P25, P50, P75, P90, wpe, "annexb_valband",
                              today_note=f"~{pct:.0f}th percentile")
    deck.pic(s, png, ML, 1.95, 7.15, 4.45, valign="top", halign="left")

    rx = ML + 7.35
    rw = RX - rx
    if reg == "simple":
        b1 = (f"The book trades at about {wpe:.0f}x trailing earnings, near the top of its usual "
              f"10-year range. That means the holdings are priced for a lot of good news.")
        b2 = ("A high price is not a signal to sell everything. It does mean new money should go in "
              "carefully, and the weakest names should not get the benefit of the doubt.")
    else:
        b1 = (f"The weighted trailing P/E of the direct book is {wpe:.1f}x, around the {pct:.0f}th "
              f"percentile of the illustrative 10-year band for this sector blend. The starting "
              f"multiple is the one return driver already known today, and it sits high.")
        b2 = ("A high percentile is not a timing signal: expensive books can stay expensive for "
              "years. What it does change is the margin of safety, so the bar for adding rises, "
              "the case for trimming the weakest scores strengthens, and staged deployment of new "
              "money matters more.")
    deck.callout(s, rx, 1.95, rw, 2.15, "What this says", b1, kind="note")
    deck.callout(s, rx, 4.25, rw, 2.15, "What it does not say", b2, kind="human")

    deck.source(s, f"Weighted trailing P/E over the {cov:.0f}% of book weight with usable multiples "
                   f"(extremes above {PE_CAP:.0f}x excluded); 10-year percentile band is synthetic "
                   f"[ILLUSTRATIVE] pending index-blend history.")
    return 1
