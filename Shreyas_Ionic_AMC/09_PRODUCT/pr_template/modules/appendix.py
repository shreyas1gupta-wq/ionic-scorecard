# -*- coding: utf-8 -*-
"""Annexure, Appendix: methodology notes, data sources and a plain-language glossary (v8 #53-56).
Two slides; returns the count."""
from slidekit import (INK, SLATE, NAVY, GOLD, SERIF, SANS, ML, UW, RX)


_GLOSSARY = [
    ("Ionic Score", "A 0-100 quality/valuation/trend score per stock; a quantitative input, not the final call."),
    ("Sell / Trim / Hold", "The calls used for existing holdings under an NDPMS mandate."),
    ("Fund score", "A 0-100 quality score per fund: net-of-fee alpha, consistency and downside cushioning."),
    ("Grade", "A-D letter grade summarising a fund's standing (A = strongest)."),
    ("Watch-outs", "Red-flag chips a fund can trip: index-hugging, negative alpha, deep drawdown, scale, plan-cost."),
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
        fu_body = ("Funds are scored 0-100 by the firm's fund-quality framework on Direct-plan NAV against "
                   "total-return benchmarks, point-in-time. It rewards net-of-fee alpha, rolling-window "
                   "consistency and downside cushioning, and penalises structural watch-outs. Verdicts: "
                   "Hold / Trim / Switch / Redeem-to-Direct / Exit.")
    # panels hug their text (shared height keeps the pair aligned); data sources become a
    # third, full-width boxed panel so the lower half of the page doesn't sit empty
    h = max(deck.callout_h(colw, eq_body, min_h=1.6), deck.callout_h(colw, fu_body, min_h=1.6))
    deck.callout(s, ML, 1.95, colw, h, "Scoring equities", eq_body, "note")
    deck.callout(s, x2, 1.95, colw, h, "Evaluating funds", fu_body, "note")

    src = ("Scored universe: the firm's stock-scoring engine + per-stock analyst files (point-in-time).  ·  Fund NAVs: "
           "Direct-plan, total-return-benchmark relative.  ·  SEBI market-cap cut-offs and category rules.  ·  "
           "House-view sector / allocation bands.  ·  Official statutory tax rates, updated each Budget.  ·  "
           "Client IPS and holdings as supplied by the advisory desk.")
    sy = 1.95 + h + 0.25
    deck.callout(s, ML, sy, UW, deck.callout_h(UW, src, min_h=1.0), "Data sources", src, "human")
    deck.source(s, "Illustrative synthetic demo (AZBY Family); equity scores real, holdings & funds synthetic.")


def _glossary(deck, ctx, tier):
    s = deck.content(5, "Appendix", "Glossary", "Plain-language definitions of the terms used")
    cols = [("Term", 0.26, "l"), ("What it means", 0.74, "l")]
    rows = [[("b", t), d] for t, d in _GLOSSARY]
    deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.36, fs=9.5, hfs=8)
    deck.source(s, "Definitions are for reader guidance and simplified; they do not modify the disclaimers.")


def render(deck, ctx, tier):
    # glossary page cut from client decks (Principal 2026-07-25); _glossary stays in
    # the library for internal builds
    _methodology(deck, ctx, tier)
    return 1
