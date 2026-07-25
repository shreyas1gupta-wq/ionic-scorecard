# -*- coding: utf-8 -*-
"""Annexure, Appendix: methodology notes, data sources and a plain-language glossary (v8 #53-56).
Two slides; returns the count."""
from slidekit import (INK, SLATE, NAVY, GOLD, SERIF, SANS, ML, UW, RX)


_GLOSSARY = [
    ("Ionic Score", "A 0-100 quality/valuation/trend score per stock; a quantitative input, not the final call."),
    ("Sell / Trim / Hold", "The calls used for existing holdings under an NDPMS mandate."),
    ("QFRA 2.0", "The firm's frozen fund-ranking engine, scores funds on alpha, consistency and downside."),
    ("MERIT grade", "A-D letter grade summarising a fund's QFRA standing (A = strongest)."),
    ("SENTINEL flags", "Red-flag chips a fund can trip: closet-index, negative alpha, deep drawdown, capacity, plan-cost."),
    ("Up / down capture", "How much of the market's rise / fall a fund captures; ideal is high up, low down."),
    ("Closet index", "An 'active' fund that hugs its benchmark (r² > 0.95) while charging active fees."),
    ("Sortino / Calmar", "Return per unit of downside risk (Sortino) and per unit of max drawdown (Calmar)."),
    ("Max drawdown", "The largest peak-to-trough fall in value over the period shown."),
    ("Reverse-DCF", "Works backward from today's price to the growth it already assumes, a margin-of-safety check."),
    ("LTCG / STCG", "Long- / short-term capital-gains tax; the holding period decides which applies."),
    ("Direct vs Regular plan", "Same fund; Direct has no distributor trail, so it costs less and compounds better."),
]


def _methodology(deck, ctx, tier):
    reg = tier.get("register", "std")
    s = deck.content(5, "Appendix", "Methodology & data sources",
                     "How the numbers on these pages are built")

    colw = (UW - 0.4) / 2
    x2 = ML + colw + 0.4
    if reg == "simple":
        eq_body = ("Every stock gets a 0-100 Ionic Score from two views, a long-term (3-year) view and a "
                   "shorter (1-year) view, combined into one number. A low score flags a sell; a healthy score "
                   "supports holding. The score is an input; the team confirms every call.")
        fu_body = ("Funds are scored on how much they beat their benchmark after fees, how consistent they "
                   "are, and how well they protect on the way down. Weak or high-cost funds are switched, "
                   "redeemed to Direct, or exited.")
    else:
        eq_body = ("Each stock earns a 0-100 Ionic Score from two horizons, a 3-year, fundamentals-tilted "
                   "view and a 1-year, trend-tilted view, combined across pillars (Quality & "
                   "Growth, Value, Trend & Flow). Forensic / balance-sheet gates cap the score at 40. Below "
                   "40 on either horizon = Sell; 40-50 is a watch zone (Trim only with a "
                   "concentration or risk flag); 50+ = Hold.")
        fu_body = ("Funds use the frozen QFRA 2.0 engine on Direct-plan NAV against total-return benchmarks, "
                   "point-in-time. It rewards net-of-fee alpha, rolling-window consistency and downside "
                   "cushioning, and penalises SENTINEL flags. Verdicts: Hold / Trim / Switch / "
                   "Redeem-to-Direct / Exit.")
    deck.callout(s, ML, 1.95, colw, 2.5, "Scoring equities", eq_body, "note")
    deck.callout(s, x2, 1.95, colw, 2.5, "Evaluating funds", fu_body, "note")

    deck.txt(s, ML, 4.75, UW, 0.24, [("DATA SOURCES", SANS, 9, SLATE, True, False, 140)])
    src = ("Scored universe: portfolio_quant.csv + per-stock analyst files (PIT).  ·  Fund NAVs: Direct-plan, "
           "total-return-benchmark relative (QFRA 2.0).  ·  SEBI market-cap cut-offs and category rules.  ·  "
           "House-view sector / allocation bands.  ·  Statutory tax rates (Compliance-signed, Budget-versioned).  ·  "
           "Client IPS and holdings as supplied by the advisory desk.")
    deck.txt(s, ML, 5.0, UW, 1.3, [(src, SERIF, 10.5, INK, False)], ls=1.15)
    deck.source(s, "Illustrative synthetic demo (AZBY Family); equity scores real, holdings & funds synthetic.")


def _glossary(deck, ctx, tier):
    s = deck.content(5, "Appendix", "Glossary", "Plain-language definitions of the terms used")
    cols = [("Term", 0.26, "l"), ("What it means", 0.74, "l")]
    rows = [[("b", t), d] for t, d in _GLOSSARY]
    deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.36, fs=9.5, hfs=8)
    deck.source(s, "Definitions are for reader guidance and simplified; they do not modify the disclaimers.")


def render(deck, ctx, tier):
    _methodology(deck, ctx, tier)
    _glossary(deck, ctx, tier)
    return 2
