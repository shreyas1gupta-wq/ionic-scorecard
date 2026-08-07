# -*- coding: utf-8 -*-
"""snapshot, Section 01 opener. Eq/MF/Cash donut + portfolio KPI strip (AUM, holdings, funds, top-10%)."""
from slidekit import (NAVY, GOLD, INK, SLATE, SELL, WHITE, NT3, SANS, SERIF, ML, UW, RX)
from pptx.enum.text import PP_ALIGN
import charts as CH
from lib import lookthrough as LT

# chart-side colours (matplotlib hex, mirror chart_lib palette)
CNAVY, CGOLD, CNT3 = "#1B27A3", "#F2A93C", "#C9CEF0"

LABELS = {
    "hni":    {"eyebrow": "Portfolio snapshot",
               "title": "Asset mix and the concentration that drives risk",
               "read_title": "THE READ"},
    "std":    {"eyebrow": "Portfolio snapshot",
               "title": "What you own today, equity, funds and cash",
               "read_title": "THE READ"},
    "simple": {"eyebrow": "Your portfolio at a glance",
               "title": "What you own today",
               "read_title": "IN SHORT"},
}


def _alloc_bar(deck, s, x, y, w, h, segs):
    """100%-stacked bar, drawn from primitives (no chart image needed for 3 segments).
    segs = [(label, pct, color), ...]. The legend is ONE text run below the bar, not a label
    positioned per segment -- two adjacent narrow segments (e.g. hybrid/debt and cash both
    sitting near 5-6%) collided when each label claimed its own minimum-width box (found on
    the first visual read of this page, 2026-08-06)."""
    total = sum(v for _, v, _ in segs) or 1.0
    cx = x
    for lab, v, col in segs:
        sw = w * v / total
        deck.rect(s, cx, y, max(sw, 0.02), h, fill=col)
        if sw >= 0.9:
            deck.txt(s, cx, y, sw, h, [(f"{v:.0f}%", SANS, 9, WHITE, True)],
                     align=PP_ALIGN.CENTER)
        cx += sw
    legend = []
    for i, (lab, v, col) in enumerate(segs):
        if i:
            legend.append(("   ·   ", SANS, 7.5, SLATE, False))
        legend.append((f"{lab} {v:.0f}%", SANS, 7.5, SLATE, True, False, 20))
    deck.txt(s, x, y + h + 0.05, w, 0.18, legend)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    t = ctx["totals"]; cl = ctx["client"]; cap = ctx["ips"]["single_name_cap_pct"]
    grand = t["grand_inr"]; eq = t["eq_pct"]; mf = t["mf_pct"]; cash = t["cash_pct"]
    n_st = t["n_stocks"]; n_fd = t["n_funds"]; top10 = t["top10_pct"]

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])

    # ---- KPI band ----
    deck.kpi_strip(s, [
        (f"Rs {grand/1e7:.2f} Cr", "Total portfolio value" if reg == "simple" else "Total AUM"),
        (str(n_st), "Direct equity names"),
        (str(n_fd), "Mutual-fund schemes"),
        (f"{top10:.0f}%", "In the top 10 holdings", None, (SELL if top10 >= 50 else INK)),
    ], y=1.82)
    deck.rule(s, ML, 2.92, UW, h=0.012)

    # ---- donut (left) ----
    dpath = CH.donut([("Direct equity", eq), ("Mutual funds", mf), ("Cash", cash)],
                     "azby_snapshot_donut", colors=[CNAVY, CGOLD, CNT3],
                     center_top=f"Rs {grand/1e7:.1f} Cr", center_bot="Your portfolio" if reg == "simple" else "Total AUM")
    deck.pic(s, dpath, ML, 3.05, 4.35, 3.35, valign="middle", halign="center")

    # ---- read (right) ----
    if reg == "simple":
        body = (f"Most of your money, about {eq:.0f}%, is invested directly in shares. "
                f"About {mf:.0f}% is in mutual funds and {cash:.0f}% is kept as cash. "
                "A lot sits in just a few shares. We look at that next.")
    elif reg == "hni":
        body = (f"The mix itself is healthy: {eq:.0f}% direct equity doing the compounding, "
                f"{mf:.0f}% in funds for breadth, {cash:.0f}% in cash. What deserves attention "
                f"sits inside the equity sleeve: the ten largest names carry {top10:.0f}% of the "
                f"book against an {cap:.0f}% single-name guideline. This review deals with that "
                f"first, then the funds, then the costs.")
    else:
        body = (f"About {eq:.0f}% of the book is in direct equity, {mf:.0f}% in mutual funds and "
                f"{cash:.0f}% in cash. The equity sleeve drives the portfolio, and inside it the ten "
                f"largest names hold {top10:.0f}% of the book. Concentration, not asset mix, is what we address first.")
    cx = ML + 4.85
    cw = RX - cx

    # ---- FM #6, extended by the 2026-08-06 ruling: asset allocation must include EVERYTHING --
    # direct equity + fund look-through equity + debt + cash + others, summing to the whole book,
    # not a partial view. The prior 3-segment strip (Equity/Hybrid-debt/Cash) silently dropped
    # each fund's own "Others" slice (REITs/InvITs/margin/unclassified, per ACE's own column) --
    # real, not hypothetical: every fund in this book carries one. full_lookthrough_mix() is the
    # 4-segment version that reconciles to the whole book; equity is GROSS (2026-08-05 ruling),
    # disclosed by footnote, never a per-row flag.
    true_eq, true_debt, true_cash, true_other = LT.full_lookthrough_mix(ctx)
    alloc_label = ("TRUE MIX, FUNDS LOOKED THROUGH" if reg != "simple" else "WHAT YOU'RE REALLY IN")
    deck.txt(s, cx, 3.15, cw, 0.18, [(alloc_label, SANS, 8, SLATE, True, False, 100)])
    segs = [("Equity", true_eq, NAVY), ("Debt", true_debt, GOLD), ("Cash", true_cash, NT3)]
    if true_other >= 0.05:
        segs.append(("Others", true_other, SLATE))
    _alloc_bar(deck, s, cx, 3.36, cw, 0.22, segs)

    # panel hugs its text — a half-empty tinted box reads as an unfilled template
    callout_y = 3.90
    deck.callout(s, cx, callout_y, cw, deck.callout_h(cw, body, min_h=1.3, max_h=2.68),
                 L["read_title"], body, kind="human")

    demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
    gross_note = LT.gross_equity_footnote(ctx)
    gross_txt = f" {gross_note}" if gross_note else ""
    deck.source(s, f"Source: client custody statement as of {cl['as_of']}; Ionic Wealth Portfolio "
                   "Review. Donut = direct holding, % of AUM. True mix = direct + fund "
                   f"look-through equity/debt/others, % of AUM (FM #8).{gross_txt}{demo_tag}")
    return 1
