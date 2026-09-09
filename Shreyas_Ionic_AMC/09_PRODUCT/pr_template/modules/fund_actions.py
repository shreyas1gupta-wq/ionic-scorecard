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
    "hni":    ("Fund actions", "What we would change in the fund book, and exactly why"),
    "std":    ("Fund actions", "What we would change in the fund book, and exactly why"),
    "simple": ("Changes to your funds", "What we would change, and exactly why"),
}


def _short(name, n=30):
    from slidekit import short_name
    return short_name(name, n)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    # This page gives each action a written rationale in the desk's own voice. A client-directed
    # exit has no such rationale to give -- the reason is the client's instruction, stated once on
    # the priority-actions page -- and running nineteen of them through here would have produced
    # nineteen cards each claiming the scheme "sits in the bottom third of its own category".
    acts = [f for f in ctx["funds"]
            if f["action"] not in ("HOLD", "Hold")
            and str(f.get("action") or "").strip().upper() not in ("EXIT (CLIENT)", "RETAIN")]
    # A performance-driven sell is NOT only a sub-40 QFRA-2 score. Fixed 2026-08-19: an MF-only
    # book whose sells were originated by the desk's own long-record category test carried
    # qfra=None on every one of them, n_perf_flag came out 0, and the page then told the client
    # "No fund here is sold on performance alone" -- the exact opposite of the reasoning behind
    # all four sells. Any module that infers intent from one optional field will do this again, so
    # the data layer can now say so directly via perf_flag. Books without it are unaffected.
    n_perf_flag = sum(1 for f in acts
                      if f.get("perf_flag") or (f.get("qfra") is not None and f["qfra"] < 40))
    n_other = len(acts) - n_perf_flag
    # A concentration trim is neither structural nor a liquidity need, and calling it one is the
    # same error in the other direction. Counted separately so the opening can name it.
    n_conc = sum(1 for f in acts if f.get("action_origin") == "concentration")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(2, "The Fund Book", eyebrow, title)
    deck.anchor("mod:fund_actions", s, prio=5)
    if n_perf_flag:
        if n_other == 0:
            # every action is a performance call -- say that plainly rather than implying a
            # structural mix that does not exist in this book
            _cd = ctx.get("client_directive") or {}
            _nce = len(_cd.get("exits") or [])
            opening = (f"All {len(acts)} of these actions are performance calls: each scheme sits in "
                       f"the bottom third of its own category on the long record. Nothing here is being "
                       f"sold for structural or liquidity reasons.")
            if _nce:
                opening += (f" Separately, {_nce} holdings are being exited at your instruction; "
                            f"those are not calls of ours and carry no card here.")
        elif n_conc == n_other:
            opening = (f"{n_perf_flag} of these {len(acts)} actions are performance calls: the scheme "
                       f"sits in the bottom third of its own category on the long record. The other "
                       f"{n_conc} is a position size, not a view on the fund: it is above the "
                       f"single-name cap and is eased back to it."
                       if n_conc == 1 else
                       f"{n_perf_flag} of these {len(acts)} actions are performance calls, the scheme "
                       f"sitting in the bottom third of its own category on the long record. The other "
                       f"{n_conc} are position sizes, not views on the funds: each is above the "
                       f"single-name cap and is eased back to it.")
        else:
            opening = (f"{n_other} of these {len(acts)} actions are structural or a liquidity need, not a "
                       f"quality call. {n_perf_flag} are flagged on performance by our own framework. "
                       "Where a scheme mostly re-buys index names you hold directly, a low-cost index "
                       "sleeve is the cleaner replacement.")
    else:
        # Kept inside the 0.40in band this is laid into. The longer version ran to four lines and
        # clipped by 0.28in on any book with few actions, which the geometry gate caught only once
        # a one-fund book was tested.
        opening = ("No fund here is sold on performance alone. Each action is structural or a "
                   "directed liquidity need. Where a scheme mostly re-buys index names you already "
                   "hold directly, a low-cost index sleeve is the cleaner replacement.")
    deck.txt(s, ML, 1.62, UW, 0.40, [(opening, SERIF, 10, SLATE, False, True)], ls=1.04)

    # 2 or 3 columns of cards, adapting to fund count (2026-07-29 fix: a real client can have
    # more than ~4 non-Hold funds -- e.g. a liquid/debt/arbitrage-to-cash sweep -- and the old
    # fixed-2-column grid shrank card_h toward zero, clipping every card's reason text however
    # short. 3 columns keeps rows (and card_h) bounded once there are more than 6 cards.
    n = len(acts)
    ncols = 4 if n > 12 else (3 if n > 6 else 2)
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
        narrow = ncols >= 4  # a 4-col card is too tight to fit pill + name on one line
        if narrow:
            # tight card: pill, name, reason only — no separate flags line (usually just
            # "structural" anyway, redundant with the reason text) and no exemplar line.
            deck.pill(s, x + 0.18, y + 0.10, verb, w=0.95)
            deck.txt(s, x + 0.18, y + 0.36, col_w - 0.34, 0.20,
                     [(_short(f["name"], 26), "Bahnschrift", 9.5, INK, True)])
            clip_len = 60
            deck.txt(s, x + 0.18, y + 0.58, col_w - 0.34, card_h - 0.62,
                     [(clip_clause(f["structural_reason"], clip_len), SERIF, 8.5, INK, False)], ls=1.0)
            continue
        deck.pill(s, x + 0.18, y + 0.14, verb, w=1.35, kind=f["verdict"])
        deck.txt(s, x + 1.62, y + 0.13, col_w - 1.75, 0.26, [(_short(f["name"], 32), "Bahnschrift", 11, INK, True)])
        # translate raw SENTINEL codes to plain words (2026-07-28: was leaking CLOSET_INDEX/
        # NEG_ALPHA/etc. raw; reuse the same FLAB dict fund_book_scored.py already uses)
        # The default tag used to be the word "structural" on every unflagged card, printed
        # directly above a reason reading "bottom third of its own category on the long record".
        # The tag now says what the data layer says originated the action.
        _ORIGIN_TAG = {"performance": "performance", "concentration": "position size"}
        flags = ("  ·  ".join(FLAB.get(x, x[:9]) for x in f["flags"]) if f["flags"]
                 else _ORIGIN_TAG.get(f.get("action_origin"), "structural"))
        # `or 0`, NOT .get(k, 0). A default only fires when the key is ABSENT, and the sell-gate
        # pass writes holding_years onto every fund -- as None where the statement carries no
        # purchase date. So the default never applied, the comparison raised TypeError, and
        # because this line sits AFTER deck.content() the engine had to remove a half-drawn page:
        # the fund-actions page disappeared from the deck with a one-line [ERR ] in the build log
        # and a zipfile "duplicate slide part" warning as the only other trace.
        if (f.get("holding_years") or 0) >= 5:
            flags += f"  ·  HELD ~{f['holding_years']:.0f}Y, COSTLIER TO SWITCH"
        deck.txt(s, x + 0.18, y + 0.46, col_w - 0.3, 0.2, [(flags, "Bahnschrift", 7.5, vc, True, False, 30)])
        # clipped to the card's real capacity (2026-07-27: a real client's structural_reason
        # ran to ~300 chars and silently overflowed this fixed-height card; 2026-07-29: budget
        # scaled with column count -- but that alone still overflowed once a 5th/6th action
        # fund pushed rows_per_col from 2 to 3, shrinking card_h while clip_len stayed flat,
        # so the exemplar line below collided with wrapped reason text (found 2026-08-06,
        # adding a debt-fund action). Fix: scale clip_len with the card's ACTUAL available
        # text height, not just its column count. Rates below reproduce the original 175/100
        # exactly at the card_h=1.62 this module was tuned against.
        avail_h = max(0.15, card_h - 0.9)
        rate = 243 if ncols == 2 else 139
        clip_len = max(45, int(rate * avail_h))
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
