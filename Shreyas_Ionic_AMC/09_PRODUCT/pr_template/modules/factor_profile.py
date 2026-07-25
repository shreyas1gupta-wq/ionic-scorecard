# -*- coding: utf-8 -*-
"""Annexure, Factor profile: the book's average factor tilt (approximated from the scored book)
plotted against a neutral benchmark (v8 #32, CH.radar)."""
import charts as CH
from pptx.enum.text import MSO_ANCHOR
from slidekit import INK, SLATE, NAVY, NT2, GOLD, SERIF, SANS, ML, UW, RX


def _num(v, d):
    try:
        return float(v)
    except Exception:
        return d


def _clip(x):
    return max(6.0, min(97.0, x))


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    asof = ctx["client"]["as_of"]
    W = sum(e["weight_pct"] for e in eq) or 1.0

    def wa(key, dflt):
        return sum(_num(e.get(key), dflt) * e["weight_pct"] for e in eq) / W

    avg3 = wa("score_3y", 50.0)
    avg1 = wa("score_1y", 50.0)
    avg_g = wa("growth_pct", 10.0)
    pes = [(e["pe"], e["weight_pct"]) for e in eq if e.get("pe")]
    avg_pe = (sum(p * w for p, w in pes) / sum(w for _, w in pes)) if pes else 25.0
    large_share = sum(e["weight_pct"] for e in eq if e.get("mcap_band") == "Large") / W * 100.0

    # approximate 0-100 factor tilts; 50 = neutral (benchmark)
    cats = ["Quality", "Growth", "Value", "Trend /\nmomentum", "Low\nvolatility", "Small-cap\ntilt", "Yield"]
    quality = _clip(avg3)
    growth = _clip(45 + avg_g * 1.1)
    value = _clip(95 - avg_pe * 1.4)
    trend = _clip(avg1)
    lowvol = _clip(42 + (large_share - 50) * 0.35)
    smalltilt = _clip(100 - large_share)
    yld = 48.0
    values = [quality, growth, value, trend, lowvol, smalltilt, yld]
    values2 = [50.0] * len(cats)
    png = CH.radar(cats, values, "annex_radar", values2=values2, label1="This book", label2="Neutral")

    title = ("What the book is tilted toward, versus a neutral benchmark"
             if reg != "simple" else "What kind of shares you own")
    s = deck.content(5, "Annexure", "Factor profile", title)
    deck.scope_tag(s, f"Direct equity only · as of {asof}")
    deck.pic(s, png, ML, 1.95, 4.7, 4.5, valign="top", halign="left")

    # legend
    lx = ML + 0.1
    deck.oval(s, lx, 6.28, 0.15, NAVY)
    deck.txt(s, lx + 0.24, 6.25, 2.0, 0.2, [("This book", SANS, 9, INK, False)], anchor=MSO_ANCHOR.MIDDLE)
    deck.oval(s, lx + 1.7, 6.28, 0.15, NT2)
    deck.txt(s, lx + 1.94, 6.25, 2.3, 0.2, [("Neutral (50)", SANS, 9, SLATE, False)], anchor=MSO_ANCHOR.MIDDLE)

    flat = [("Quality", quality), ("Growth", growth), ("Value", value), ("Trend / momentum", trend),
            ("Low volatility", lowvol), ("Small-cap tilt", smalltilt), ("Yield", yld)]
    overs = [c for c in sorted(flat, key=lambda x: -x[1]) if c[1] >= 55][:3]
    unders = [c for c in sorted(flat, key=lambda x: x[1]) if c[1] <= 45][:3]

    rx = ML + 5.1
    rw = RX - rx
    ov_txt = ("; ".join(f"{n} ({v:.0f})" for n, v in overs) or "broadly balanced") + "."
    un_txt = ("; ".join(f"{n} ({v:.0f})" for n, v in unders) or "no material gaps") + "."
    deck.callout(s, rx, 2.05, rw, 1.9, "What the book leans into", ov_txt +
                 ("  A quality-and-trend tilt, as you'd expect from a large-cap core." if reg != "simple" else ""),
                 "good")
    deck.callout(s, rx, 4.05, rw, 1.9, "Where it is light", un_txt +
                 ("  These are the diversifiers the proposed changes lean toward." if reg != "simple" else ""),
                 "note")
    deck.source(s, "Illustrative factor tilts approximated from the book's weighted 3Y/1Y scores, "
                   "growth, valuation and market-cap mix; 50 = neutral benchmark.")
    return 1
