# -*- coding: utf-8 -*-
"""Annexure B, look-through revenue geography of the equity book. India/US/Europe/Other stacked
bars for the largest holdings plus the book total, with the natural-FX-hedge vs foreign-equity-gap
note. Splits are sector-keyed [ILLUSTRATIVE] pending annual-report segment data."""
import chart_ext_b as CB
from slidekit import ML, UW, RX, SERIF, SLATE

LABELS = {
    "hni":    ("Revenue geography", "Where the book actually earns its money"),
    "std":    ("Revenue geography", "Where the book actually earns its money"),
    "simple": ("Revenue geography", "How much of the book earns abroad"),
}

# sector -> (India, US, Europe, Other) revenue split, % [ILLUSTRATIVE]
GEO = {
    "Information Technology": (30, 48, 15, 7),
    "Healthcare": (45, 32, 13, 10),
    "Chemicals": (55, 15, 18, 12),
    "Metals & Mining": (72, 6, 9, 13),
    "Automobile And Auto Components": (72, 9, 13, 6),
    "Oil Gas & Consumable Fuels": (82, 4, 6, 8),
    "Capital Goods": (78, 8, 9, 5),
    "Telecommunication": (88, 2, 3, 7),
}
GEO_DEFAULT = (94, 2, 2, 2)


def _split(e):
    return GEO.get(e["sector"], GEO_DEFAULT)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    as_of = ctx["client"]["as_of"]
    gap = ctx.get("house_view", {}).get("alloc_gap", {}).get("Foreign")
    foreign_tgt = ctx.get("ips", {}).get("foreign_target_pct", 15)

    wsum = sum(e["weight_pct"] for e in eq)
    book = [round(sum(e["weight_pct"] * _split(e)[i] for e in eq) / wsum, 1) for i in range(4)]
    abroad = round(100 - book[0], 1)

    # rows: the 4 largest positions + the 4 most-global names (the hedge providers)
    top = sorted(eq, key=lambda e: -e["weight_pct"])[:4]
    globals_ = sorted([e for e in eq if e not in top and e["weight_pct"] >= 0.4],
                      key=lambda e: _split(e)[0])[:4]
    rows = [(f"{e['symbol']}  ({e['weight_pct']:.1f}%)", list(_split(e))) for e in top + globals_]
    rows.append(("EQUITY BOOK (look-through)", book))

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Direct equity book · look-through revenue by geography, sector-keyed splits "
                      f"[ILLUSTRATIVE] · as of {as_of}")

    png = CB.geo_stack(rows, "annexb_geo")
    deck.pic(s, png, ML, 2.0, 7.2, 4.4, valign="top", halign="left")

    rx = ML + 7.4
    rw = RX - rx
    if reg == "simple":
        b1 = (f"About {abroad:.0f}% of the money these companies earn comes from outside India, mostly "
              f"from the IT, pharma and auto-parts names. That gives some protection if the rupee weakens.")
        b2 = (f"It is still not the same as owning foreign companies. The plan keeps the {foreign_tgt:.0f}% "
              f"foreign target, funded from the sale proceeds.")
    else:
        b1 = (f"Roughly {abroad:.0f}% of the book's underlying revenue is earned outside India, led by "
              f"IT, healthcare and auto-component exporters. That is a real, if partial, currency hedge: "
              f"a weaker rupee lifts those earnings without any action from us.")
        b2 = (f"Export revenue does not close the foreign-equity gap ({gap:+.0f} pts vs the "
              f"{foreign_tgt:.0f}% IPS target). These shares still trade at India-market multiples and "
              f"fall with the India market; owning foreign assets diversifies the market itself, which "
              f"revenue geography cannot. The deployment plan funds the first foreign sleeve.")
    deck.callout(s, rx, 2.0, rw, 2.05, "The natural FX hedge", b1, kind="good")
    deck.callout(s, rx, 4.2, rw, 2.25, "Why the foreign target still stands", b2, kind="note")

    deck.source(s, "Revenue splits are sector-keyed illustrative estimates [ILLUSTRATIVE], pending "
                   "company segment disclosures; book row is the weight-averaged look-through.")
    return 1
