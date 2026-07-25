# -*- coding: utf-8 -*-
"""fund_actions (F4), rationale cards. One card per non-Hold fund. No fund is sold on performance:
every card cites a STRUCTURAL reason (mandate rigidity / plan-cost / capacity / closet-index / down-capture)
and the firing SENTINEL flags, measured against the category exemplar it failed. SEBI-safe verbs only."""
from slidekit import (NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, ML, UW, RX, PANEL,
                      SELLBG, AMBERBG)

VERB = {"SWITCH": ("Switch", AMBER, AMBERBG), "EXIT": ("Exit", SELL, SELLBG),
        "REDEEM": ("Redeem to Direct", AMBER, AMBERBG), "TRIM": ("Trim", AMBER, AMBERBG)}

LABELS = {
    "hni":    ("Fund actions", "Every action is structural, never a performance sale"),
    "std":    ("Fund actions", "What we would change in the fund book, and exactly why"),
    "simple": ("Changes to your funds", "A few structural fixes, none is about last year's return"),
}


def _short(name, n=30):
    return name if len(name) <= n else name[:n - 1] + "…"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    acts = [f for f in ctx["funds"] if f["action"] not in ("HOLD", "Hold")]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(3, "Funds", eyebrow, title)
    deck.anchor("mod:fund_actions", s, prio=5)
    deck.txt(s, ML, 1.62, UW, 0.40,
             [("No fund here is sold on performance alone. Each action is structural: mandate, cost, "
               "scale or consistency, measured against the fund that does the job better.", SERIF, 10, SLATE, False, True)])

    # two columns of cards
    n = len(acts)
    col_w = (UW - 0.3) / 2
    rows_per_col = (n + 1) // 2
    card_h = min(1.62, (6.4 - 2.1) / max(rows_per_col, 1) - 0.12)
    x0 = [ML, ML + col_w + 0.3]
    for i, f in enumerate(acts):
        col = i // rows_per_col
        row = i % rows_per_col
        x = x0[col]; y = 2.1 + row * (card_h + 0.12)
        verb, vc, vbg = VERB.get(f["action"], (f["verdict"], AMBER, AMBERBG))
        deck.rect(s, x, y, col_w, card_h, fill=PANEL, line=vc, lw=1.0, round_=0.05)
        deck.rect(s, x, y, 0.06, card_h, fill=vc)
        deck.pill(s, x + 0.18, y + 0.14, verb, w=1.35, kind=f["verdict"])
        deck.txt(s, x + 1.62, y + 0.13, col_w - 1.75, 0.26, [(_short(f["name"], 32), "Bahnschrift", 11, INK, True)])
        flags = "  ·  ".join(f["flags"]) if f["flags"] else "structural"
        if f.get("holding_years", 0) >= 5:
            flags += f"  ·  HELD ~{f['holding_years']:.0f}Y (LTCG BAR RAISED)"
        deck.txt(s, x + 0.18, y + 0.46, col_w - 0.3, 0.2, [(flags, "Bahnschrift", 7.5, vc, True, False, 30)])
        deck.txt(s, x + 0.18, y + 0.68, col_w - 0.34, card_h - 0.9,
                 [(f["structural_reason"], SERIF, 9.5, INK, False)], ls=1.04)
        if f.get("exemplar") and f["exemplar"] != "-":
            deck.txt(s, x + 0.18, y + card_h - 0.24, col_w - 0.34, 0.2,
                     [("Measured against ", SERIF, 8.5, SLATE, False, True),
                      (f["exemplar"], SERIF, 8.5, NAVY, False, True)])

    deck.source(s, "Category exemplar = the QFRA final-2 benchmark the held fund is measured against, not a "
                   "recommendation to buy it. Whether a replacement is named is a compliance decision. Synthetic demo funds.")
    return 1
