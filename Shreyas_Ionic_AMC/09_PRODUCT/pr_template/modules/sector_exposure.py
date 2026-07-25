# -*- coding: utf-8 -*-
"""sector_exposure (F12), direct-equity sector weights (hbar) + CMP-DATASCOPE tag.
The MF sleeve is NOT looked through here; true sector exposure including funds is higher."""
from slidekit import (NAVY, GOLD, INK, SLATE, SANS, SERIF, ML, UW, RX)
import charts as CH

LABELS = {
    "hni":    {"eyebrow": "Sector exposure",
               "title": "Direct-equity sector weights (sleeve basis)"},
    "std":    {"eyebrow": "Sector exposure",
               "title": "Which sectors your direct equity leans on"},
    "simple": {"eyebrow": "Which industries you own",
               "title": "Where your shares are invested"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; t = ctx["totals"]; as_of = ctx["client"]["as_of"]

    # ---- aggregate sector weights as % of the direct-equity sleeve ----
    agg = {}
    for e in eq:
        sec = (e.get("sector") or "Diversified").strip() or "Diversified"
        agg[sec] = agg.get(sec, 0.0) + e["weight_pct"]
    eq_total = sum(agg.values()) or 1.0
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [(k, 100.0 * v / eq_total) for k, v in ranked]
    if len(ranked) > 8:
        head = ranked[:8]; other = sum(v for _, v in ranked[8:])
        ranked = head + [("Other", other)]

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    # ---- hbar (left) ----
    labels = [k for k, _ in ranked]; values = [v for _, v in ranked]
    hpath = CH.hbar(labels, values, "azby_sector", highlight=0, fmt="{:.1f}%")
    deck.pic(s, hpath, ML, 2.0, 6.75, 4.35, valign="top", halign="left")

    top1, v1 = ranked[0]; top2, v2 = ranked[1] if len(ranked) > 1 else (ranked[0])
    t3 = sum(v for _, v in ranked[:3])

    # ---- scope note (right, top) ----
    cx = ML + 7.05; cw = RX - cx
    scope_body = (f"This chart covers direct equity only ({t['eq_pct']:.0f}% of AUM). The mutual-fund "
                  f"sleeve ({t['mf_pct']:.0f}% of AUM) is not looked through, your true sector "
                  "exposure, funds included, is higher than shown.")
    deck.callout(s, cx, 2.0, cw, 1.95, "SCOPE, MF NOT LOOKED THROUGH", scope_body, kind="warn")

    # ---- read (right, bottom) ----
    if reg == "simple":
        read = (f"Most of your shares are in {top1} and {top2}. Remember, this is only your direct "
                "shares · your mutual funds also hold shares in these areas, so your real exposure is a bit higher.")
    elif reg == "hni":
        read = (f"Sleeve tilts to {top1} ({v1:.0f}%) and {top2} ({v2:.0f}%); top-3 sectors are "
                f"{t3:.0f}% of the direct book. Sector risk compounds with the single-name "
                "concentration flagged earlier · sized together, not in isolation.")
    else:
        read = (f"The direct-equity book leans toward {top1} ({v1:.0f}%) and {top2} ({v2:.0f}%); the "
                f"top three sectors are {t3:.0f}% of the sleeve. Reasonable spread, but sector risk "
                "compounds with the single-name concentration flagged earlier.")
    deck.callout(s, cx, 4.15, cw, 2.0,
                 "THE READ" if reg != "simple" else "IN SHORT", read, kind="human")

    deck.source(s, f"Source: client holdings as of {as_of}. Weights as % of the direct-equity sleeve; "
                   "mutual-fund look-through not included.")
    return 1
