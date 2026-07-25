# -*- coding: utf-8 -*-
"""gallery.py, appends a CHART LIBRARY and a STYLE / COMPONENTS reference to a Deck,
so one master file carries every template slide + every graph + the house-style kit."""
import numpy as np
import charts as CH
from chart_lib import (NAVY as HNAVY, NT1 as HNT1, NT2 as HNT2, NT3 as HNT3, GOLD as HGOLD,
                       SELL as HSELL, HOLD as HHOLD)
from slidekit import (NAVY, NT1, NT2, NT3, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL, HAIR, WHITE,
                      SELLBG, HOLDBG, AMBERBG, SERIF, SANS, ML, UW, RX, CW)
from pptx.enum.text import PP_ALIGN

_rng = np.random.default_rng(7)
_nav = list(100 * np.cumprod(1 + _rng.normal(0.0004, 0.012, 950)))


def _chart_specs():
    """(title, when-to-use / module, render_fn -> png path)."""
    return [
        ("Donut, allocation split", "Snapshot · asset mix",
         lambda: CH.donut([("Direct equity", 60.0), ("Mutual funds", 34.0), ("Cash", 6.0)], "g_donut",
                          [HNAVY, HNT2, HNT3], center_top="Rs 6.8 Cr", center_bot="TOTAL")),
        ("Horizontal bars", "Sector exposure · top holdings",
         lambda: CH.hbar(["Financials", "Energy", "Auto", "Metals", "Pharma"], [24, 18, 14, 11, 9], "g_hbar", highlight=0)),
        ("Paired bars, fund vs benchmark", "Three-year test",
         lambda: CH.paired_bar(["Fund A", "Fund B", "Fund C"], [16.2, 13.1, 18.7], [13.0, 12.4, 15.1], "g_paired", alpha_vals=[3.2, 0.7, 3.6])),
        ("Waterfall / bridge", "Deployment · where proceeds go",
         lambda: CH.waterfall([("Proceeds", 60.2e5, "open"), ("Low-vol/value", 27e5, "flow"),
                               ("Foreign eq", 16.8e5, "flow"), ("Gold", 7.2e5, "flow"), ("Cash", 9.2e5, "close")], "g_wf", gold_idx=2)),
        ("Dumbbell, today vs target", "Allocation vs house view",
         lambda: CH.dumbbell(["Equity", "Foreign", "Gold", "Debt"], [79, 3, 1, 12], [72, 15, 5, 8], "g_dumb")),
        ("Radar / spider", "Factor profile · pillar tilt",
         lambda: CH.radar(["Quality", "Growth 3Y", "Value", "Trend", "Growth 1Y", "Macro"], [70, 55, 40, 60, 45, 65], "g_radar",
                          values2=[50, 50, 50, 50, 50, 50], label1="Book", label2="Benchmark")),
        ("Heatmap", "Scheme overlap · rolling returns",
         lambda: CH.heatmap(["Fund A", "Fund B", "Fund C"], ["Fund A", "Fund B", "Fund C"],
                            [[100, 71, 34], [71, 100, 40], [34, 40, 100]], "g_heat")),
        ("Treemap", "Concentration · top-10 weight",
         lambda: CH.treemap(["Reliance", "Titan", "Bajaj Fin", "HDFC Bk", "ICICI", "Rest"],
                            [12.4, 11.3, 5.2, 4.6, 4.1, 62.4], "g_tree",
                            colors=[HSELL, HHOLD, HHOLD, HHOLD, HHOLD, HNT3])),
        ("Histogram, score distribution", "The whole book, scored",
         lambda: CH.histogram(list(_rng.normal(55, 16, 68)), "g_hist", threshold=40)),
        ("Bubble, weight vs score", "Equity book overview",
         lambda: CH.bubble([12.4, 11.3, 3.4, 1.6, 0.9], [27, 78, 26, 38, 32],
                           [26e5, 25e5, 9e5, 4e5, 2e5], [HSELL, HHOLD, HSELL, HSELL, HSELL], "g_bub",
                           labels=["Reliance", "Titan", "Tata Pwr", "Jio Fin", "GAIL"])),
        ("Lollipop", "Ranked metric · any list",
         lambda: CH.lollipop(["Fund A", "Fund B", "Fund C", "Fund D"], [96, 73, 56, 16], "g_loll", highlight=3)),
        ("100% stacked bar", "Before / after mix",
         lambda: CH.stacked100([("Equity", 60, HNAVY), ("Funds", 34, HNT2), ("Cash", 6, HNT3)], "g_stack")),
        ("Small multiples", "Per-holding pillar bars",
         lambda: CH.small_multiples_bars(["Reliance", "Titan", "TCS", "SBIN"],
                                         [[27, 40, 55, 30, 62], [78, 82, 45, 70, 60], [44, 52, 88, 40, 55], [61, 48, 35, 72, 66]],
                                         ["Q", "G", "V", "T", "M"], "g_sm")),
        ("Efficient frontier", "Opportunity set (annexure)",
         lambda: CH.efficient_frontier(["Indian eq", "Foreign eq", "Debt", "Gold"], [13, 11, 7, 8], [16, 15, 4, 14],
                                       [[1, .5, .1, .1], [.5, 1, .1, .2], [.1, .1, 1, -.1], [.1, .2, -.1, 1]],
                                       [("Today", [0.79, 0.03, 0.12, 0.06], HSELL), ("Proposed", [0.60, 0.15, 0.20, 0.05], HHOLD)], "g_ef")),
        ("Value map, quality vs price", "Quality-vs-price (annexure)",
         lambda: CH.value_map([21, 33, 66, 45, 29], [10.6, 32, 21, 24, 14], [26e5, 25e5, 14e5, 9e5, 6e5],
                              [HSELL, HHOLD, HHOLD, HHOLD, HSELL], ["Reliance", "Titan", "Pidilite", "Maruti", "GAIL"], "g_vmap")),
        ("Projection cone", "Growth projection (annexure)",
         lambda: CH.projection_cone(6.8e7, 7, 12, 14, "g_cone", goals=[(7, "Target 15 Cr", 15e7)])),
        ("3D bars", "Headline figures, richer look",
         lambda: CH.bar3d(["FY24", "FY25", "FY26", "FY27e"], [11.2, 13.4, 9.8, 14.0], "g_3d")),
        ("Up / down capture scatter", "Equity funds (F14)",
         lambda: CH.capture_scatter([99, 96, 107, 119], [100, 118, 71, 135], [30e5, 27e5, 45e5, 3e5],
                                    [HSELL, HSELL, HHOLD, HSELL], ["LIC LargeCap", "LIC Flexi", "PPFAS", "Bandhan SC"], "g_cap")),
        ("Drawdown / underwater curve", "Hybrid funds · scorecards (F15)",
         lambda: CH.drawdown_curve(_nav, "g_dd")),
        ("Rolling 1-year return band", "Hybrid funds · worst year (F15)",
         lambda: CH.rolling_return_band(_nav, "g_roll")),
        ("Fee stack (bps)", "Cost slide (F5)",
         lambda: CH.fee_stack([("LIC Large Cap (Reg)", 95, 40, 0), ("ICICI Multi-Asset (Reg)", 62, 40, 0),
                               ("PPFAS Flexi (Dir)", 68, 0, 0), ("PMS wrapper", 0, 0, 120)], "g_fee")),
        ("Tax bridge", "Tax impact (F7)",
         lambda: CH.tax_bridge(60.2e5, 6.6e5, 1.0e5, "g_tax")),
        ("Quality × allocation quadrant", "Fund overlay (F16)",
         lambda: CH.quality_alloc_quadrant([1.8, 3.2, -3.4, -1.0], [26, 96, 12, 59], [30e5, 45e5, 3e5, 20e5],
                                           [HSELL, HHOLD, HSELL, HGOLD], ["LIC LargeCap", "PPFAS", "Bandhan", "LIC Multi"], "g_quad")),
        ("Over / under allocation", "Exec grid · allocation gaps (F16)",
         lambda: CH.over_under_bar(["Large", "Mid", "Small", "Foreign", "Gold", "Debt"], [8.5, 3.0, -1.5, -12.0, -4.0, 6.0], "g_ou")),
    ]


def add_chart_gallery(deck):
    deck.section_divider(6, "Chart Library", "Every graph in the template, with sample data")
    for title, usage, fn in _chart_specs():
        try:
            png = fn()
        except Exception as e:
            deck.folio += 1; s = deck.slide()
            deck.txt(s, ML, 1.0, UW, 0.4, [(f"{title}, render error: {e}", SANS, 12, SELL, True)]); continue
        s = deck.content(6, "Chart Library", title, f"Used in: {usage}")
        deck.pic(s, png, ML, 1.95, UW, 4.5, valign="top", halign="center")
        deck.txt(s, ML, 6.55, UW, 0.2, [(f"chart_lib function for this graphic · sample data · Ionic house palette", SERIF, 8.5, SLATE, False, True)])
    return len(_chart_specs()) + 1


def add_style_reference(deck):
    deck.section_divider(7, "Style & Components", "Palette, pills, callouts, tables, the building blocks")
    s = deck.content(7, "Style & Components", "House style", "Palette, recommendation pills and score bar")
    # palette swatches
    deck.txt(s, ML, 1.85, UW, 0.24, [("PALETTE", SANS, 9, SLATE, True, False, 120)])
    swatches = [("Navy", NAVY, "#1B27A3"), ("NT1", NT1, "#4A57C4"), ("NT2", NT2, "#8C95DE"), ("NT3", NT3, "#C9CEF0"),
                ("Gold", GOLD, "#F2A93C"), ("Sell", SELL, "#E0402F"), ("Hold", HOLD, "#1E9E6A"), ("Amber", AMBER, "#92400E"),
                ("Ink", INK, "#16233B"), ("Slate", SLATE, "#6B7280")]
    for i, (nm, col, hx) in enumerate(swatches):
        x = ML + i * (UW / len(swatches))
        deck.rect(s, x, 2.15, UW / len(swatches) - 0.12, 0.5, fill=col, round_=0.08)
        deck.txt(s, x, 2.70, UW / len(swatches) - 0.12, 0.2, [(nm, SANS, 8.5, INK, True)])
        deck.txt(s, x, 2.88, UW / len(swatches) - 0.12, 0.2, [(hx, SANS, 7, SLATE, False)])
    # pills
    deck.txt(s, ML, 3.35, UW, 0.24, [("RECOMMENDATION PILLS", SANS, 9, SLATE, True, False, 120)])
    for i, k in enumerate(["Sell", "Trim", "Hold", "Switch", "Exit", "Redeem-to-Direct", "Watch"]):
        deck.pill(s, ML + i * 1.55, 3.65, k if k != "Redeem-to-Direct" else "To-Direct", w=1.35, kind=k)
    # score bars
    deck.txt(s, ML, 4.25, UW, 0.24, [("IONIC SCORE BAR  (Sell < 40 · Trim 40-50 · Hold >= 50)", SANS, 9, SLATE, True, False, 120)])
    for i, sc in enumerate([27, 45, 72]):
        deck.score_bar(s, ML + i * 3.4, 4.72, sc, w=2.4)
    # callouts
    deck.txt(s, ML, 5.15, UW, 0.24, [("CALLOUT STYLES", SANS, 9, SLATE, True, False, 120)])
    kinds = [("note", "Note", "Neutral context or method."), ("good", "Good", "A strength worth holding."),
             ("warn", "Warning", "A risk or a Sell trigger."), ("human", "Human read", "Score is the input, not the verdict.")]
    for i, (k, tt, bd) in enumerate(kinds):
        deck.callout(s, ML + i * (UW / 4), 5.45, UW / 4 - 0.15, 1.0, tt, bd, kind=k)
    deck.source(s, "All colours, fonts (Bahnschrift head / Georgia body), pills, bars and callouts come from slidekit.py, modules never hardcode style.")

    # component table sample
    s2 = deck.content(7, "Style & Components", "Table & KPI band", "The register table and the KPI strip used across the deck")
    deck.kpi_strip(s2, [("Rs 6.8 Cr", "total reviewed", "AUM"), ("38 / 9", "stocks / schemes", None),
                        ("42%", "top-10 weight", "concentration", GOLD), ("8", "rated Sell", "of 38", SELL),
                        ("6", "fund actions", "structural", NAVY)], y=1.95)
    cols = [("Name", 0.30, "l"), ("Wt", 0.10, "r"), ("Score", 0.18, "l"), ("Rec", 0.16, "c"), ("Read", 0.26, "l")]
    rows = [["Reliance Industries", "12.4%", ("bar", 27), ("pill", "Sell", "Sell"), "Rich vs SOTP; Jio-IPO hinge"],
            ["Titan Company", "11.3%", ("bar", 78), ("pill", "Hold", "Hold"), "Gold-led growth, watch margin"],
            ["Tata Power", "3.4%", ("bar", 26), ("pill", "Sell", "Sell"), "Leverage + arbitration overhang"],
            ["HDFC Bank", "4.6%", ("bar", 55), ("pill", "Hold", "Hold"), "LDR normalising; core intact"]]
    deck.table(s2, ML, 3.35, UW, cols, rows, rowh=0.5, fs=11, hfs=9)
    deck.source(s2, "deck.kpi_strip(...) and deck.table(...), cells accept text, ('bar',score), ('pill',text,kind), ('flags',[...]).")
    return 3
