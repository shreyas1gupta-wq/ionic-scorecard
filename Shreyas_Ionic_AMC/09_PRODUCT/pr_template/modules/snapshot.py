# -*- coding: utf-8 -*-
"""snapshot, Section 01 opener. Eq/MF/Cash donut + portfolio KPI strip (AUM, holdings, funds, top-10%)."""
from slidekit import (NAVY, GOLD, INK, SLATE, SELL, SANS, SERIF, ML, UW, RX)
from pptx.enum.text import PP_ALIGN
import charts as CH

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
    # panel hugs its text — a half-empty tinted box reads as an unfilled template
    deck.callout(s, cx, 3.15, RX - cx, deck.callout_h(RX - cx, body, min_h=1.5, max_h=3.05),
                 L["read_title"], body, kind="human")

    deck.source(s, f"Source: client custody statement as of {cl['as_of']}; Ionic Wealth Portfolio Review. "
                   "Percentages of total AUM.")
    return 1
