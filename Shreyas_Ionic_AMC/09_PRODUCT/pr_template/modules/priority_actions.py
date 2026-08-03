# -*- coding: utf-8 -*-
"""priority_actions (Section 04, Recommendations, v8 #29). THE LAST CORE SLIDE.
Numbered action list (sell programme, trim, fund switches, redeploy) with amounts, read from
ctx cost/tax/deployment/totals/equity/funds. Closes on the NDPMS authorisation line."""
from slidekit import NAVY, GOLD, INK, SLATE, NT2, WHITE, SERIF, SANS, ML, UW, RX, HAIR, AMBER, AMBERBG
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SECTION_NO, SECTION = 4, "Recommendations"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


# canonical action order + per-register nouns (mix text is built from the ACTUAL actions —
# a hardcoded 'switches / redeem-to-Direct / exit' went stale the day the book changed)
_ACT_ORDER = ["SWITCH", "REDEEM", "EXIT", "TRIM"]
_ACT_NOUN = {"SWITCH": ("switch", "switches"), "REDEEM": ("redeem-to-Direct", "redeems-to-Direct"),
             "EXIT": ("exit", "exits"), "TRIM": ("trim", "trims")}


def _mix(act_counts):
    parts = []
    for a in _ACT_ORDER:
        n = act_counts.get(a, 0)
        if n:
            parts.append(f"{n} {_ACT_NOUN[a][0 if n == 1 else 1]}")
    return ", ".join(parts)


def _rows(reg, n_sell, k, act_counts, n_quality_sell, n_liquidity_sell, trim_reason):
    n_exit = act_counts.get("EXIT", 0)
    n_move = k - n_exit
    sell_desc_hni = (f"{n_sell} names sold, {n_quality_sell} score below the gate; "
                      f"{n_liquidity_sell} are directed liquidity exits, not a quality call."
                      if n_liquidity_sell else
                      f"{n_sell} names scored below the gate, staged in slices at <=10% ADV.")
    if reg == "simple":
        # 'cheaper or Direct versions' read as a same-fund plan change (Principal
        # 2026-07-26) — a Switch replaces the FUND; destinations happen to be Direct
        fund_sub = f"Tidy the fund list, replace {n_move} weak funds with stronger, cheaper ones"
        fund_sub += ", drop the tiny one." if n_exit else "."
        sell_sub = (f"Sell the {n_sell} weakest-scoring stocks; {n_liquidity_sell} more are sold just for "
                    "cash, not because they're weak."
                    if n_liquidity_sell else
                    f"Sell the {n_sell} weakest-scoring stocks, a little at a time.")
        return [
            ("Sell the weak names", sell_sub, "First"),
            ("Free up cash", trim_reason, "Soon"),
            ("Fix the funds", fund_sub, "A few days"),
            ("Keep the cash ready", "The freed money sits safely in a liquid fund; where it goes next is decided with you, separately.", "Together"),
        ]
    return [
        ("Sell programme", sell_desc_hni, "Wave 1"),
        ("Trim / liquidity", trim_reason, "This cycle"),
        ("Fund actions", f"{_mix(act_counts)}; every destination is a Direct-plan or passive vehicle.", "T+2–T+3"),
        ("Park net proceeds", "Held in liquid / overnight funds pending your goals and IPS discussion; no redeployment is assumed or recommended here.", "On authorisation"),
    ]


LABELS = {
    "hni": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net proceeds", "k3s": "to cash, after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "std": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net proceeds", "k3s": "to cash, after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "simple": {"eyebrow": "What happens next", "title": "Your action plan, step by step",
               "k1": "Cash freed", "k1s": "from sells + trim", "k2": "Fund changes", "k2s": "switch / move / drop",
               "k3": "Cash in hand", "k3s": "after estimated tax",
               "auth": "Nothing happens without your approval; every step is yours to confirm."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    t = ctx["totals"]
    dep, funds, equity = ctx["deployment"], ctx["funds"], ctx["equity"]
    proceeds, net = dep["proceeds_inr"], dep["net_inr"]
    sell_sum = sum(e["value_inr"] for e in equity if e["rec"] == "Sell")
    # real trim cash = money actually coming off over-cap Hold names, reduced toward the
    # single-name cap -- NOT "whatever proceeds are left over once sells are subtracted"
    # (that residual silently included fund-exit money whenever a book has zero Trim-rec
    # equities, e.g. Anand Reddy 2026-07-27: showed fund-exit cash against a stock-trim
    # action label, wrongly implying HDFCBANK/TCS trims were worth the fund-exit amount)
    cap = ctx["ips"]["single_name_cap_pct"]
    grand = t["grand_inr"]
    trim_cash = round(sum((e["weight_pct"] - cap) / 100 * grand
                          for e in equity if e["rec"] != "Sell" and e["weight_pct"] > cap))
    fund_acts = [f for f in funds if f["action"] not in ("HOLD", "Hold")]
    k = len(fund_acts)
    act_counts = {}
    for f in fund_acts:
        a = f["action"].upper()
        act_counts[a] = act_counts.get(a, 0) + 1
    # KPI sub-label mirrors the actions actually present, register-appropriate nouns
    _sub_noun = ({"SWITCH": "switch", "REDEEM": "move", "EXIT": "drop", "TRIM": "trim"}
                 if reg == "simple" else
                 {"SWITCH": "switch", "REDEEM": "redeem", "EXIT": "exit", "TRIM": "trim"})
    L = dict(L)
    L["k2s"] = " / ".join(_sub_noun[a] for a in _ACT_ORDER if act_counts.get(a))
    # displayed as the sum of the ROUNDED per-fund amounts so it matches the tax-slide
    # total digit-for-digit (independent rounding printed 82.1 here vs 82.2 there)
    fund_sum = round(sum(round(f["value_inr"] / 1e5, 1) for f in fund_acts), 1) * 1e5
    n_sell = t["n_sell"]
    n_liquidity_sell = sum(1 for e in equity if e["rec"] == "Sell" and e.get("sell_reason_type") == "liquidity")
    n_quality_sell = n_sell - n_liquidity_sell
    trim_names = [e for e in equity if e["rec"] == "Trim"]
    if trim_names and any((e["weight_pct"] or 0) > cap for e in trim_names):
        trim_reason = "Positions above the 8% single-name guideline eased toward the cap, into strength."
    elif trim_names:
        trim_reason = (f"{trim_names[0]['name'].title()} trimmed for a directed cash need, not a "
                        "concentration or quality concern — no position in this book is above the 8% cap.")
    else:
        trim_reason = "No position in this book exceeds the 8% single-name guideline; nothing to trim."

    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    deck.kpi_strip(s, [
        (_money(proceeds), L["k1"], L["k1s"], INK),
        (str(k), L["k2"], L["k2s"], NT2),
        (_money(net), L["k3"], L["k3s"], NAVY),
    ], y=1.8)

    amounts = [sell_sum, trim_cash, fund_sum, net]
    rows = _rows(reg, n_sell, k, act_counts, n_quality_sell, n_liquidity_sell, trim_reason)
    # v7 device (p.29): every action row carries a REF back to the page that justifies it
    refs = ["tbl:sell_list", "mod:concentration", "mod:fund_actions", "mod:tax_impact"]
    ry0, rowh = 2.98, 0.78
    for i, ((title, sub, when), amt) in enumerate(zip(rows, amounts)):
        ry = ry0 + i * rowh
        deck.oval(s, ML, ry + 0.04, 0.42, NAVY)
        deck.txt(s, ML, ry + 0.04, 0.42, 0.42, [(str(i + 1), SANS, 14, WHITE, True)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, ML + 0.62, ry, 8.0, 0.3, [(title, SANS, 13, INK, True)])
        deck.txt(s, ML + 0.62, ry + 0.31, 8.0, 0.34, [(sub, SERIF, 9.5, SLATE, False, True)], ls=1.02)
        deck.txt(s, RX - 2.55, ry + 0.02, 2.55, 0.3, [(_money(amt), SANS, 15, GOLD, True)],
                 align=PP_ALIGN.RIGHT)
        deck.txt(s, RX - 2.55, ry + 0.42, 2.55, 0.22, [(when.upper(), SANS, 7.5, SLATE, True, False, 60)],
                 align=PP_ALIGN.RIGHT)
        if reg != "simple":
            deck.pageref(s, ML - 0.04, ry + 0.50, refs[i], w=0.62, align=PP_ALIGN.CENTER)
        deck.rule(s, ML, ry + rowh - 0.06, UW, HAIR, 0.006)

    # authorisation band, with the signature blank beside it (v7 p.29: the deck gets signed)
    bw = UW - 3.95
    deck.rect(s, ML, 6.1, bw, 0.46, fill=AMBERBG, round_=0.06)
    deck.rect(s, ML, 6.1, 0.06, 0.46, fill=GOLD)
    deck.txt(s, ML + 0.22, 6.1, bw - 0.4, 0.46,
             [("AUTHORISATION   ", SANS, 8.5, AMBER, True, False, 60), (L["auth"], SERIF, 9.5, INK, False)],
             anchor=MSO_ANCHOR.MIDDLE, ls=1.0)
    deck.txt(s, RX - 3.75, 6.1, 3.75, 0.46,
             [("Reviewed with client on  ____________________", SANS, 8, SLATE, False)],
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    demo_tag = "Amounts illustrative for the AZBY demo · " if ctx.get("is_demo", False) else ""
    deck.source(s, f"{demo_tag}Net figures after estimated tax · as of {ctx['client']['as_of']}.")
    return 1
