# -*- coding: utf-8 -*-
"""before_after (Section 04, Recommendations, v8 #28).
Two mini donuts (asset mix before vs after) + a third donut of Sell-count -> proceeds-as-cash.
Freed cash is shown as its OWN line and is never auto-invested (deployment is a separate step)."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, SERIF, SANS, ML, UW, RX
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 5, "Annexure"   # transition plan lives in the annexure (Principal 2026-07-25)
_NAVY, _NT2, _GOLD, _SELL = "#1B27A3", "#8C95DE", "#F2A93C", "#E0402F"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


LABELS = {
    "hni": {"eyebrow": "Before and after", "title": "What the book looks like once the sells and trims settle · cash freed, not redeployed",
            "c1": "Asset mix, today", "c2": "After sells (pre-deploy)", "c3": "Proceeds → cash",
            "ck": "human", "ct": "Freed cash",
            "note": "Fund switches are like-for-like within the fund sleeve, so the mix above moves only with equity sells and the trim. Direct-equity only for the sell/trim step; as of {d}."},
    "std": {"eyebrow": "Before and after", "title": "What the book looks like once the sells and trims settle · cash freed, not redeployed",
            "c1": "Asset mix, today", "c2": "After sells (pre-deploy)", "c3": "Proceeds → cash",
            "ck": "human", "ct": "Freed cash",
            "note": "Fund switches are like-for-like within the fund sleeve, so the mix above moves only with equity sells and the trim. Direct-equity only for the sell/trim step; as of {d}."},
    "simple": {"eyebrow": "Before and after", "title": "How your money is split now, and right after we sell",
               "c1": "Split today", "c2": "After we sell", "c3": "Freed to cash",
               "ck": "human", "ct": "Freed cash sits in cash",
               "note": "Selling frees cash; the fund tidy-up is a like-for-like swap, so only your stock sells change the split. As of {d}."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    t = ctx["totals"]
    grand = t["grand_inr"]
    proceeds = ctx["deployment"]["proceeds_inr"]
    sell_sum = sum(e["value_inr"] for e in ctx["equity"] if e["rec"] == "Sell")
    trim_cash = max(proceeds - sell_sum, 0)
    freed_pct = proceeds / grand * 100
    n_sell = t["n_sell"]

    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    before = [("Equity", t["eq_pct"]), ("Funds", t["mf_pct"]), ("Cash", t["cash_pct"])]
    after = [("Equity", round(t["eq_pct"] - freed_pct, 1)), ("Funds", t["mf_pct"]),
             ("Cash", round(t["cash_pct"] + freed_pct, 1))]
    sell_pct = sell_sum / proceeds * 100 if proceeds else 100
    comp = [("From Sells", round(sell_pct, 1)), ("From trim", round(100 - sell_pct, 1))]

    p1 = CH.donut(before, "azby_ba_before", colors=[_NAVY, _NT2, _GOLD], center_top="Before", center_bot="today")
    p2 = CH.donut(after, "azby_ba_after", colors=[_NAVY, _NT2, _GOLD], center_top="After", center_bot="pre-deploy")
    p3 = CH.donut(comp, "azby_ba_cash", colors=[_SELL, _GOLD], center_top=f"{n_sell} Sells",
                  center_bot=f"{_money(proceeds)} freed")

    boxes = [(ML, L["c1"], p1), (ML + 3.9, L["c2"], p2), (ML + 7.8, L["c3"], p3)]
    for bx, cap, png in boxes:
        deck.txt(s, bx, 1.76, 3.5, 0.24, [(cap.upper(), SANS, 8.5, SLATE, True, False, 80)], align=PP_ALIGN.CENTER)
        deck.pic(s, png, bx, 2.02, 3.5, 2.85, valign="middle")

    body = (f"{_money(proceeds)} is freed to cash after execution and stays in cash until deployment "
            f"is agreed separately, never auto-invested.")
    if reg == "simple":
        body = (f"After we sell, {_money(proceeds)} sits safely in cash. We reinvest it slowly, "
                f"step by step, it is never put to work automatically.")
    deck.callout(s, ML, 5.05, UW, 0.98, L["ct"], body, kind=L["ck"])

    deck.source(s, L["note"].format(d=ctx["client"]["as_of"]))
    return 1
