# -*- coding: utf-8 -*-
"""cost (Section 04, Recommendations, NEW split from v8 #26, F5).
3 KPI tiles (total fee load bps & Rs | Regular-plan drag avoidable | PMS fee) + CH.fee_stack
(fund TER direct + Regular-plan drag + PMS) + a single soft CoPilot line + basis footnote.
PMS/advisory fee shown SEPARATELY from fund TER."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, SELL, NT2, SERIF, SANS, ML, UW, RX, AMBERBG, AMBER, PANEL, HAIR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SECTION_NO, SECTION = 4, "Recommendations"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


LABELS = {
    "hni": {"eyebrow": "What you're paying today", "title": "The full fee stack · fund TER, avoidable Regular-plan drag, and PMS fee, separated",
            "t1": "Total fee load", "t2": "Regular-plan drag", "t3": "PMS / advisory fee",
            "s2": "avoidable, Direct plan removes it", "s3": "on the whole book, separate from fund TER",
            "copilot": "Want a full fee-optimisation run across alternatives? Ask CoPilot."},
    "std": {"eyebrow": "What you're paying today", "title": "The full fee stack · fund TER, avoidable Regular-plan drag, and PMS fee, separated",
            "t1": "Total fee load", "t2": "Regular-plan drag", "t3": "PMS / advisory fee",
            "s2": "avoidable, Direct plan removes it", "s3": "on the whole book, separate from fund TER",
            "copilot": "Want a full fee-optimisation run across alternatives? Ask CoPilot."},
    "simple": {"eyebrow": "What your fees cost you", "title": "Your yearly fees · and the part you can simply avoid",
               "t1": "Total fees a year", "t2": "Avoidable extra", "t3": "PMS fee",
               "s2": "the Direct plan removes this", "s3": "charged on the whole portfolio",
               "copilot": "Want us to run the numbers across cheaper options? Ask CoPilot."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    cost = ctx["cost"]
    grand = ctx["totals"]["grand_inr"]
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    reg_drag_bps = round(cost["reg_drag_inr"] / grand * 10000)
    stats = [
        (f"{cost['total_bps']} bps", L["t1"], _money(cost["total_inr"]) + " / yr", INK),
        (_money(cost["reg_drag_inr"]), L["t2"], f"~{reg_drag_bps} bps · {L['s2']}", SELL),
        (f"{cost['pms_bps']} bps", L["t3"], L["s3"], NT2),
    ]
    deck.kpi_strip(s, stats, y=1.82)

    # fee stack: fund TER (direct) + Regular-plan drag (avoidable) + PMS row (whole book), worst-to-best
    frows = sorted(cost["rows"], key=lambda r: (r[2] + r[3]), reverse=True)
    fee_rows = [(name[:26], ter, drag, 0) for (name, plan, ter, drag) in frows]
    fee_rows.append(("PMS / advisory (whole book)", 0, 0, cost["pms_bps"]))
    png = CH.fee_stack(fee_rows, "azby_fee_stack")
    deck.pic(s, png, ML, 2.92, UW, 3.18, valign="top")

    # single soft CoPilot hook line (compliance-gated), rendered subtly
    cy = 6.16
    deck.rect(s, ML, cy, 0.10, 0.24, fill=GOLD, round_=0.4)
    deck.txt(s, ML + 0.22, cy - 0.02, UW - 0.22, 0.28,
             [("COPILOT   ", SANS, 8, AMBER, True, False, 60), (L["copilot"], SERIF, 10, SLATE, False, True)],
             anchor=MSO_ANCHOR.MIDDLE)

    deck.source(s, "Basis: fund TER from scheme documents (Direct vs Regular); Regular-plan drag = Regular minus Direct expense; "
                   "PMS / advisory fee per the signed IMA, charged separately. Illustrative for the AZBY demo.")
    return 1
