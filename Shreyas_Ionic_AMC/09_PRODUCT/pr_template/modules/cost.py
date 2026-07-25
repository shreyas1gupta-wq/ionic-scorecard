# -*- coding: utf-8 -*-
"""cost (Section 04, Recommendations, F5).
Scheme-level cost of ownership ONLY: what each fund charges (current-plan TER, bps), a blended
book average, and the fee in rupees a year. Principal 2026-07-25: the NDPMS deck does NOT show
'extra you pay' overlays (Regular-plan drag bars, PMS/advisory fee) — plan hygiene is handled as
a fund ACTION (Redeem-to-Direct), not as a cost exhibit. CoPilot hook retained."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, NT2, SERIF, SANS, ML, UW, RX, AMBER
from pptx.enum.text import MSO_ANCHOR

SECTION_NO, SECTION = 4, "Recommendations"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


LABELS = {
    "hni": {"eyebrow": "What you're paying today", "title": "Fund-level cost of ownership · what each scheme charges",
            "t1": "Fund fees, a year", "t2": "Blended fund TER", "t3": "Cost spread",
            "s2": "value-weighted, current plan", "s3": "cheapest to priciest holding",
            "copilot": "Want a full fee-optimisation run across alternatives? Ask CoPilot."},
    "std": {"eyebrow": "What you're paying today", "title": "Fund-level cost of ownership · what each scheme charges",
            "t1": "Fund fees, a year", "t2": "Blended fund TER", "t3": "Cost spread",
            "s2": "value-weighted, current plan", "s3": "cheapest to priciest holding",
            "copilot": "Want a full fee-optimisation run across alternatives? Ask CoPilot."},
    "simple": {"eyebrow": "What your funds cost", "title": "What each fund charges you, every year",
               "t1": "Fund fees a year", "t2": "Average charge", "t3": "Lowest and highest",
               "s2": "across all your funds", "s3": "your cheapest and priciest fund",
               "copilot": "Want us to run the numbers across cheaper options? Ask CoPilot."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    def _short(name, n=26):
        from slidekit import short_name
        return short_name(name.split("(")[0].strip(), n)   # plan markers don't matter here

    # current-plan TER per scheme (direct TER + plan drag = what the holder pays today)
    cur = [(_short(name), ter + drag) for (name, plan, ter, drag) in ctx["cost"]["rows"]]
    vals = {_short(f["name"]): f["value_inr"] for f in ctx["funds"]}
    tot_val = sum(vals.get(n, 0) for n, _ in cur) or 1
    blended = sum(b * vals.get(n, 0) for n, b in cur) / tot_val
    fee_inr = sum(b / 1e4 * vals.get(n, 0) for n, b in cur)
    lo = min(cur, key=lambda r: r[1]); hi = max(cur, key=lambda r: r[1])

    deck.kpi_strip(s, [
        (_money(fee_inr), L["t1"], f"{blended:.0f} bps blended", INK),
        (f"{blended:.0f} bps", L["t2"], L["s2"], NAVY),
        (f"{lo[1]:.0f}–{hi[1]:.0f} bps", L["t3"], L["s3"], NT2),
    ], y=1.82)

    png = CH.ter_bars(sorted(cur, key=lambda r: -r[1]), "azby_ter_bars", avg_bps=blended)
    deck.pic(s, png, ML, 2.92, UW, 3.18, valign="top")

    # single soft CoPilot hook line (compliance-gated), rendered subtly
    cy = 6.16
    deck.rect(s, ML, cy, 0.10, 0.24, fill=GOLD, round_=0.4)
    deck.txt(s, ML + 0.22, cy - 0.02, UW - 0.22, 0.28,
             [("COPILOT   ", SANS, 8, AMBER, True, False, 60), (L["copilot"], SERIF, 10, SLATE, False, True)],
             anchor=MSO_ANCHOR.MIDDLE)

    deck.source(s, "Basis: scheme Total Expense Ratio (current plan) from scheme documents, "
                   "weighted by holding value. Illustrative for the AZBY demo.")
    return 1
