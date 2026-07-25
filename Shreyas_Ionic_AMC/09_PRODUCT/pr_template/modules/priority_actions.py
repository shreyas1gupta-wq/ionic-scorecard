# -*- coding: utf-8 -*-
"""priority_actions (Section 04, Recommendations, v8 #29). THE LAST CORE SLIDE.
Numbered action list (sell programme, trim, fund switches, redeploy) with amounts, read from
ctx cost/tax/deployment/totals/equity/funds. Closes on the NDPMS authorisation line."""
from slidekit import NAVY, GOLD, INK, SLATE, NT2, WHITE, SERIF, SANS, ML, UW, RX, HAIR, AMBER, AMBERBG
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SECTION_NO, SECTION = 4, "Recommendations"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


def _rows(reg, n_sell, k):
    if reg == "simple":
        return [
            ("Sell the weak names", f"Sell the {n_sell} weakest-scoring stocks, a little at a time.", "First"),
            ("Trim the big two", "Gently reduce your two largest single stocks.", "Soon"),
            ("Fix the funds", f"Tidy the fund list, move {k} to cheaper or Direct versions, drop the tiny one.", "A few days"),
            ("Reinvest gradually", "Put the freed money to work slowly across three areas.", "Over time"),
        ]
    return [
        ("Sell programme", f"{n_sell} names scored below the gate, staged in slices at <=10% ADV.", "Wave 1"),
        ("Trim concentration", "Two >11% positions eased toward the 8% single-name guideline, into strength.", "This cycle"),
        ("Fund actions", f"{k} switches / redeem-to-Direct / exit, Regular to Direct or passive; exit the sub-scale sleeve.", "T+2–T+3"),
        ("Redeploy net proceeds", "Into a low-vol / value core, a foreign sleeve and gold-silver, cash until deployed.", "Staged"),
    ]


LABELS = {
    "hni": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net to redeploy", "k3s": "after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "std": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net to redeploy", "k3s": "after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "simple": {"eyebrow": "What happens next", "title": "Your action plan, step by step",
               "k1": "Cash freed", "k1s": "from sells + trim", "k2": "Fund changes", "k2s": "switch / move / drop",
               "k3": "To reinvest", "k3s": "after estimated tax",
               "auth": "Nothing happens until you say yes, you approve every step."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    t = ctx["totals"]
    dep, funds, equity = ctx["deployment"], ctx["funds"], ctx["equity"]
    proceeds, net = dep["proceeds_inr"], dep["net_inr"]
    sell_sum = sum(e["value_inr"] for e in equity if e["rec"] == "Sell")
    trim_cash = max(proceeds - sell_sum, 0)
    fund_acts = [f for f in funds if f["action"] not in ("HOLD", "Hold")]
    k = len(fund_acts)
    fund_sum = sum(f["value_inr"] for f in fund_acts)
    n_sell = t["n_sell"]

    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    deck.kpi_strip(s, [
        (_money(proceeds), L["k1"], L["k1s"], INK),
        (str(k), L["k2"], L["k2s"], NT2),
        (_money(net), L["k3"], L["k3s"], NAVY),
    ], y=1.8)

    amounts = [sell_sum, trim_cash, fund_sum, net]
    rows = _rows(reg, n_sell, k)
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
        deck.rule(s, ML, ry + rowh - 0.06, UW, HAIR, 0.006)

    deck.rect(s, ML, 6.1, UW, 0.46, fill=AMBERBG, round_=0.06)
    deck.rect(s, ML, 6.1, 0.06, 0.46, fill=GOLD)
    deck.txt(s, ML + 0.22, 6.1, UW - 0.4, 0.46,
             [("AUTHORISATION   ", SANS, 8.5, AMBER, True, False, 60), (L["auth"], SERIF, 10, INK, False)],
             anchor=MSO_ANCHOR.MIDDLE)
    deck.source(s, f"Amounts illustrative for the AZBY demo · net figures after estimated tax · as of {ctx['client']['as_of']}.")
    return 1
