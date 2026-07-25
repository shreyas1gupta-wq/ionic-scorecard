# -*- coding: utf-8 -*-
"""fund_category_rules (F14), Category & Structure preference rules.
Rule 1: Flexi-Cap > Multi-Cap (SEBI 25/25/25 floor kills agility at the same fee).
Rule 2: Factor / Passive > Active Large-Cap (thin net-of-fee alpha, closet-indexing).
Each rule = RULE -> WHY -> which held scheme violates -> action; plus an AMC-concentration strip.
Violators are read from ctx (flags / category), never hardcoded."""
from collections import Counter
from slidekit import (NAVY, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL, HAIR, SERIF, SANS,
                      ML, UW, RX)
from pptx.enum.text import PP_ALIGN


def _short(name, n=30):
    return name if len(name) <= n else name[:n - 1] + "…"


def _rule_card(deck, s, x, y, w, h, num, rule, why, violators, action_text, action_kind, simple):
    deck.rect(s, x, y, w, h, fill=PANEL, round_=0.03)
    deck.rect(s, x, y, 0.06, h, fill=GOLD)
    ix = x + 0.24
    iw = w - 0.44
    deck.txt(s, ix, y + 0.16, iw, 0.2, [(f"RULE {num}", SANS, 9, GOLD, True, False, 120)])
    deck.txt(s, ix, y + 0.40, iw, 0.5, [(rule, SANS, 12.5, NAVY, True)], ls=1.0)
    deck.rule(s, ix, y + 0.94, iw, HAIR, 0.012)
    deck.txt(s, ix, y + 1.04, iw, 0.2, [("WHY", SANS, 8, SLATE, True, False, 120)])
    deck.txt(s, ix, y + 1.26, iw, 1.0, [(why, SERIF, 10, INK, False)], ls=1.08)
    vy = y + h - 1.02
    deck.txt(s, ix, vy, iw, 0.2, [("IN THIS BOOK", SANS, 8, SLATE, True, False, 120)])
    if violators:
        vt = "  ·  ".join(_short(v["name"], 26) for v in violators)
        deck.txt(s, ix, vy + 0.21, iw, 0.4, [(vt, SANS, 9.5, SELL, True)], ls=1.0)
    else:
        deck.txt(s, ix, vy + 0.21, iw, 0.3, [("No scheme violates this rule.", SERIF, 9.5, HOLD, False, True)])
    deck.pill(s, ix, y + h - 0.42, action_text, w=min(iw, 2.5), kind=action_kind)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    funds = ctx["funds"]

    # violators from ctx — Rule 2 fires on active large-caps that trail their index
    # (closet-indexing ALSO fires it, but no held scheme trips that test in this book)
    multi = [f for f in funds if "MANDATE_RIGIDITY" in f["flags"] or "Multi Cap" in f["name"]]
    weak_lc = [f for f in funds if "Large Cap" in f["name"] and f["category"] == "equity"
               and ("NEG_ALPHA" in f["flags"] or "CLOSET_INDEX" in f["flags"])]

    if simple:
        eyebrow, title = "How we pick the fund type", "Two simple rules about the kind of fund, before returns"
    else:
        eyebrow, title = "Category & structure · preference rules", "Two rules that decide the vehicle, before performance"
    s = deck.content(3, "Funds", eyebrow, title)

    if simple:
        why1 = ("A multi-cap fund is forced by rule to hold at least 25% each in large, mid and small "
                "companies. A flexi-cap manager can move freely. Same fee, less freedom · so we prefer flexi.")
        why2 = ("Most large-company funds struggle to beat the index once fees are taken out; yours has "
                "trailed it for years. A low-cost index or factor fund does the same job for much less.")
    else:
        why1 = ("Multi-Cap carries a SEBI 25/25/25 floor, a hard minimum in large, mid and small caps, "
                "so it can't shift with the cycle. A Flexi-Cap runs the same brief with full cap freedom at "
                "a similar fee. We'd rather size mid/small ourselves than pay for a locked mandate.")
        why2 = ("Net-of-fee alpha in active Large-Cap is thin and inconsistent, and the held scheme has "
                "trailed its index over both 3 and 5 years. A low-cost passive or factor Large-Cap secures "
                "the same beta and frees the fee budget for categories where active management can pay.")

    gap = 0.30
    cw = (UW - gap) / 2
    _rule_card(deck, s, ML, 1.95, cw, 3.5, 1, "Flexi-Cap  >  Multi-Cap", why1, multi,
               "Switch to Flexi", "Switch", simple)
    _rule_card(deck, s, ML + cw + gap, 1.95, cw, 3.5, 2, "Factor / Passive  >  Active Large-Cap", why2,
               weak_lc, "Switch to Passive/Factor", "Switch", simple)

    # AMC concentration strip
    ct = Counter(f["amc"] for f in funds)
    wt = {}
    for f in funds:
        wt[f["amc"]] = wt.get(f["amc"], 0) + f["weight_pct"]
    top = max(ct, key=lambda a: (ct[a], wt[a]))
    amc_body = (f"{ct[top]} of your {len(funds)} schemes (~{wt[top]:.1f}% of the book) sit with a single "
                f"AMC, {top}. That concentrates house-style and single-manager risk; diversifying the "
                f"switch targets across fund houses is part of the fix.")
    if simple:
        amc_body = (f"{ct[top]} of your {len(funds)} funds are from the same company, {top} "
                    f"(~{wt[top]:.1f}% of the money). Spreading across fund houses lowers the risk.")
    deck.callout(s, ML, 5.72, UW, 0.85, "AMC concentration", amc_body, kind="warn")

    deck.source(s, "SEBI category framework (25/25/25 multi-cap floor) · net-of-fee alpha and r² measured "
                   "vs total-return benchmark. Rules applied to the held schemes. Illustrative synthetic funds.")
    return 1
