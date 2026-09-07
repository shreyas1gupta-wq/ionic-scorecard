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

    # WHAT THIS DECK ACTUALLY DID, not what the kit is capable of. This page described a
    # two-horizon stock score, its 40 / 50 thresholds and a per-stock analyst file on a review that
    # scored no stock at all, and described the fund method as net-of-fee alpha against total-return
    # benchmarks when the fund book in front of the reader is scored on the share of each scheme's
    # own SEBI peer group it beat. A methodology appendix that does not describe the method is
    # worse than no appendix: the reader checks the numbers against it.
    _scores_stocks = any(e.get("ionic_score") is not None for e in (ctx.get("equity") or []))
    _pctile = any(f.get("qfra") is not None for f in (ctx.get("funds") or []))
    colw = (UW - 0.4) / 2 if _scores_stocks else UW
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
                   "Hold / Trim / Switch / Exit.")
    if _pctile:
        fu_body = ("A scheme's score is the share of its OWN SEBI category it beat, measured on the "
                   "three-year and five-year records independently, with the peer median as the "
                   "benchmark rather than an index, on Direct-plan NAV. A scheme in the bottom "
                   "third of its category on both horizons is a Sell. A Trim is a judgement on a "
                   "WEIGHT, not on the fund: it is what a holding above the single-name cap gets. "
                   "A scheme the framework does not reach carries No View and is still counted in "
                   "every weight and every concentration test on these pages.")
    # panels hug their text (shared height keeps the pair aligned); data sources become a
    # third, full-width boxed panel so the lower half of the page doesn't sit empty
    if _scores_stocks:
        h = max(deck.callout_h(colw, eq_body, min_h=1.6), deck.callout_h(colw, fu_body, min_h=1.6))
        deck.callout(s, ML, 1.95, colw, h, "Scoring equities", eq_body, "note")
        deck.callout(s, x2, 1.95, colw, h, "Evaluating funds", fu_body, "note")
    else:
        h = deck.callout_h(colw, fu_body, min_h=1.4)
        deck.callout(s, ML, 1.95, colw, h, "Evaluating funds", fu_body, "note")

    _src_bits = ["Holdings and values: the client's own custody statement, as supplied"]
    if _scores_stocks:
        _src_bits.append("Scored universe: the firm's stock-scoring engine + per-stock analyst "
                         "files (point-in-time)")
    _src_bits += ["Fund scores: published centrally by the desk, on Direct-plan NAV against each "
                  "scheme's own SEBI category",
                  "SEBI market-cap cut-offs and category rules",
                  "House-view stance and allocation targets, published on the desk's own cadence"]
    if (ctx.get("tax") or {}).get("gross"):
        _src_bits.append("Official statutory tax rates, updated each Budget")
    _src_bits.append("Mandate bands: the client's risk profile, applied to the desk's own profile "
                     "bands" if (ctx.get("ips") or {}).get("on_file")
                     else "No client mandate on file for this review")
    src = "  ·  ".join(_src_bits) + "."
    sy = 1.95 + h + 0.25
    deck.callout(s, ML, sy, UW, deck.callout_h(UW, src, min_h=1.0), "Data sources", src, "human")
    demo_tag = " Illustrative synthetic demo (AZBY Family); equity scores real, holdings & funds synthetic." \
        if ctx.get("is_demo", False) else ""
    deck.source(s, ("Data sources for this review." + demo_tag).strip())


def _glossary(deck, ctx, tier):
    s = deck.content(5, "Appendix", "Glossary", "Plain-language definitions of the terms used")
    cols = [("Term", 0.26, "l"), ("What it means", 0.74, "l")]
    # "the terms used" was a promise the page did not keep: it defined a letter grade the deck
    # prints nowhere, a reverse-DCF on a book with no stock research, and capture ratios on a
    # review with no NAV series. A definition for a term the reader will not meet is not harmless,
    # it tells them to go looking for it.
    _funds = ctx.get("funds") or []
    _live = {
        "Ionic Score": any(e.get("ionic_score") is not None for e in (ctx.get("equity") or [])),
        "Grade": any(f.get("merit") for f in _funds),
        "Watch-outs": any(f.get("flags") for f in _funds),
        "Up / down capture": any(f.get("down_capture") is not None or f.get("up_capture") is not None
                                 for f in _funds),
        "Closet index": any(f.get("flags") for f in _funds),
        "Sortino / Calmar": any(f.get("mdd") is not None for f in _funds),
        "Max drawdown": any(f.get("mdd") is not None or f.get("worst_1y") is not None
                            for f in _funds),
        "Reverse-DCF": any(e.get("reverse_dcf") for e in (ctx.get("equity") or [])),
        "LTCG / STCG": bool((ctx.get("tax") or {}).get("gross")),
        "Direct vs Regular plan": any(str(f.get("plan") or "").strip() == "Regular" for f in _funds)
                                  or bool((ctx.get("cost") or {}).get("n_regular")),
    }
    rows = [[("b", t), d] for t, d in _GLOSSARY if _live.get(t, True)]
    deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.36, fs=9.5, hfs=8)
    deck.source(s, "Definitions are for reader guidance and simplified; they do not modify the disclaimers.")


def render(deck, ctx, tier):
    # glossary page cut from client decks (Principal 2026-07-25); _glossary stays in
    # the library for internal builds
    _methodology(deck, ctx, tier)
    return 1
