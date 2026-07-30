# -*- coding: utf-8 -*-
"""fund_actions (F4), rationale cards. One card per non-Hold fund. No fund is sold on performance:
every card cites a STRUCTURAL reason (mandate rigidity / plan-cost / capacity / closet-index / down-capture)
and the firing SENTINEL flags, measured against the category exemplar it failed. SEBI-safe verbs only."""
from slidekit import (NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, ML, UW, RX, PANEL,
                      SELLBG, AMBERBG, clip_clause)
from modules.fund_book_scored import FLAB

VERB = {"SWITCH": ("Switch", AMBER, AMBERBG), "EXIT": ("Exit", SELL, SELLBG),
        "REDEEM": ("Switch", AMBER, AMBERBG), "TRIM": ("Trim", AMBER, AMBERBG)}

LABELS = {
    "hni":    ("Fund actions", "Every action is structural, never a performance sale"),
    "std":    ("Fund actions", "What we would change in the fund book, and exactly why"),
    "simple": ("Changes to your funds", "A few structural fixes, none is about last year's return"),
}


def _short(name, n=30):
    from slidekit import short_name
    return short_name(name, n)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    acts = [f for f in ctx["funds"] if f["action"] not in ("HOLD", "Hold")]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(3, "Funds", eyebrow, title)
    deck.anchor("mod:fund_actions", s, prio=5)
    deck.txt(s, ML, 1.62, UW, 0.40,
             [("No fund here is sold on performance alone. Each action is structural: mandate, cost, scale "
               "or consistency. Where a scheme mostly re-buys index names you already hold directly, the "
               "cleaner replacement is a low-cost index sleeve (Nifty 50 / Nifty 500 class) rather than "
               "paying an active fee twice.", SERIF, 10, SLATE, False, True)], ls=1.04)

    # 2 or 3 columns of cards, adapting to fund count (2026-07-29 fix: a real client can have
    # more than ~4 non-Hold funds -- e.g. a liquid/debt/arbitrage-to-cash sweep -- and the old
    # fixed-2-column grid shrank card_h toward zero, clipping every card's reason text however
    # short. 3 columns keeps rows (and card_h) bounded once there are more than 6 cards.
    n = len(acts)
    ncols = 3 if n > 6 else 2
    col_w = (UW - 0.3 * (ncols - 1)) / ncols
    rows_per_col = -(-n // ncols)  # ceil division
    card_h = min(1.62, (6.4 - 2.1) / max(rows_per_col, 1) - 0.12)
    x0 = [ML + i * (col_w + 0.3) for i in range(ncols)]
    for i, f in enumerate(acts):
        col = i // rows_per_col
        row = i % rows_per_col
        x = x0[col]; y = 2.1 + row * (card_h + 0.12)
        verb, vc, vbg = VERB.get(f["action"], (f["verdict"], AMBER, AMBERBG))
        deck.rect(s, x, y, col_w, card_h, fill=PANEL, line=vc, lw=1.0, round_=0.05)
        deck.rect(s, x, y, 0.06, card_h, fill=vc)
        deck.pill(s, x + 0.18, y + 0.14, verb, w=1.35, kind=f["verdict"])
        deck.txt(s, x + 1.62, y + 0.13, col_w - 1.75, 0.26, [(_short(f["name"], 32), "Bahnschrift", 11, INK, True)])
        # translate raw SENTINEL codes to plain words (2026-07-28: was leaking CLOSET_INDEX/
        # NEG_ALPHA/etc. raw; reuse the same FLAB dict fund_book_scored.py already uses)
        flags = "  ·  ".join(FLAB.get(x, x[:9]) for x in f["flags"]) if f["flags"] else "structural"
        if f.get("holding_years", 0) >= 5:
            flags += f"  ·  HELD ~{f['holding_years']:.0f}Y, COSTLIER TO SWITCH"
        deck.txt(s, x + 0.18, y + 0.46, col_w - 0.3, 0.2, [(flags, "Bahnschrift", 7.5, vc, True, False, 30)])
        # clipped to the card's real capacity (2026-07-27: a real client's structural_reason
        # ran to ~300 chars and silently overflowed this fixed-height card; 2026-07-29: budget
        # now scales with column count -- a narrower 3-column card fits far fewer characters
        # per line than a 2-column one, so a flat 175-char clip still overflowed at 3 columns)
        clip_len = 175 if ncols == 2 else 100
        deck.txt(s, x + 0.18, y + 0.68, col_w - 0.34, card_h - 0.9,
                 [(clip_clause(f["structural_reason"], clip_len), SERIF, 9.5, INK, False)], ls=1.04)
        if f.get("exemplar") and f["exemplar"] != "-":
            deck.txt(s, x + 0.18, y + card_h - 0.24, col_w - 0.34, 0.2,
                     [("Measured against ", SERIF, 8.5, SLATE, False, True),
                      (f["exemplar"], SERIF, 8.5, NAVY, False, True)])

    demo_tag = " Synthetic demo funds." if ctx.get("is_demo", False) else ""
    deck.source(s, "Category exemplar = the fund our quality framework ranks best in the category, used as the "
                   "measuring stick, not a recommendation to buy it. Whether a replacement is named is a "
                   f"compliance decision.{demo_tag}")
    return 1
