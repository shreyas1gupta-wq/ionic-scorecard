# -*- coding: utf-8 -*-
"""mcap_positioning (F12), market-cap bucket bar (Large/Mid/Small/Micro) + scope tag + mid/small view line."""
from slidekit import (NAVY, GOLD, INK, SLATE, SANS, SERIF, ML, UW, RX)
import charts as CH

_BUCKETS = ["Large", "Mid", "Small", "Micro"]

LABELS = {
    "hni":    {"eyebrow": "Market-cap positioning",
               "title": "Direct-equity market-cap distribution vs the house view"},
    "std":    {"eyebrow": "Market-cap positioning",
               "title": "How much sits in large, mid and small caps"},
    "simple": {"eyebrow": "Big vs small companies",
               "title": "How much you own in large and small companies"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; as_of = ctx["client"]["as_of"]
    gap = ctx["house_view"].get("alloc_gap", {})

    # ---- aggregate weights by mcap band, % of the direct-equity sleeve ----
    agg = {b: 0.0 for b in _BUCKETS}
    for e in eq:
        b = e.get("mcap_band") or "Large"
        agg[b] = agg.get(b, 0.0) + e["weight_pct"]
    eq_total = sum(agg.values()) or 1.0
    # a 0.0% bucket is dead ink as a chart row — drop it, note it in the source line
    pairs = [(b, 100.0 * agg[b] / eq_total) for b in _BUCKETS if b in agg]
    dropped = [b for b, v in pairs if v < 0.05]
    pairs = [(b, v) for b, v in pairs if v >= 0.05]
    labels = [b for b, _ in pairs]
    values = [v for _, v in pairs]

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    # ---- bar (left) ----
    hpath = CH.hbar(labels, values, "azby_mcap", highlight=0, fmt="{:.1f}%")
    deck.pic(s, hpath, ML, 2.0, 6.75, 4.35, valign="top", halign="left")

    # ---- SEBI definition note (right, top) ----
    cx = ML + 7.05; cw = RX - cx
    sebi = ("SEBI / AMFI classify by full-market-cap rank: Large-cap = top 100 listed companies, "
            "Mid-cap = 101st–250th, Small-cap = 251st onward. 'Micro' is a sub-bucket we track "
            "below the small-cap line.")
    deck.callout(s, cx, 2.0, cw, 1.95, "SEBI MARKET-CAP CUTOFFS", sebi, kind="note")

    # ---- mid/small VIEW line (right, bottom) ----
    mid = gap.get("Mid"); sml = gap.get("Small")
    if mid is None or sml is None:
        view = ("Mid/small-cap positioning against a target isn't set for this account yet. No "
                "allocation targets on file.")
    elif reg == "simple":
        view = ("Your money is mostly in large, well-known companies, that is steadier. We are not "
                "adding more small companies right now.")
    elif reg == "hni":
        view = (f"House view: mid-caps modestly over-owned ({mid:+.1f} vs target), small-caps a touch "
                f"light ({sml:+.1f}). With momentum on hold we favour low-vol / value over adding "
                "small-cap beta into stretched valuations.")
    else:
        view = (f"House view: mid-caps are modestly over-owned ({mid:+.1f} vs target) and small-caps "
                f"a touch light ({sml:+.1f}). With momentum on hold, we favour low-vol / value over "
                "chasing small-cap exposure here.")
    deck.callout(s, cx, 4.15, cw, 2.0,
                 "MID / SMALL VIEW" if reg != "simple" else "OUR VIEW", view, kind="human")

    drop_note = f" No {'/'.join(dropped).lower()}-cap exposure." if dropped else ""
    deck.source(s, f"Source: client holdings as of {as_of}. Weights as % of the direct-equity sleeve; "
                   f"bands per SEBI/AMFI classification.{drop_note}")
    return 1
