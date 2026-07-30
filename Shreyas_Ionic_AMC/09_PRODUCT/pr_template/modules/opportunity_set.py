# -*- coding: utf-8 -*-
"""Annexure, Opportunity set: an illustrative efficient frontier from long-run capital-market
assumptions, with the book's Today mix and a Proposed mix marked (v8 #30)."""
import charts as CH
from slidekit import SELL, HOLD, NAVY, ML, UW, RX
from modules.ips_summary import _lookthrough_mix

# matplotlib-safe hex mirrors of the house palette (RGBColor cannot cross into matplotlib)
SELL_HEX = "#E0402F"; NAVY_HEX = "#1B27A3"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    title = ("Long-run risk and return, and where the book can move"
             if reg != "simple" else "How much return, for how much risk")
    s = deck.content(5, "Annexure", "Opportunity set", title)

    assets = ["Indian equity", "Foreign equity", "Debt", "Gold"]
    mu = [13, 11, 7, 8]
    sigma = [16, 15, 4, 14]
    corr = [[1.0, 0.60, 0.10, 0.20],
            [0.60, 1.0, 0.15, 0.25],
            [0.10, 0.15, 1.0, -0.05],
            [0.20, 0.25, -0.05, 1.0]]
    # 2026-07-28: "Today" uses the same real look-through Equity/Hybrid-Debt/Cash split as the
    # IPS page (direct equity + equity-oriented funds, not just direct-equity-only) -- a client
    # with most of their equity exposure inside funds was understated here before. Foreign/gold
    # are not separately tracked yet -- 0, not fabricated.
    true_equity, true_hybrid_debt, true_cash = _lookthrough_mix(ctx)
    tot = (true_equity + true_hybrid_debt + true_cash) or 100.0
    eq_share = true_equity / tot
    today = [round(eq_share, 3), 0.0, round(true_hybrid_debt / tot, 3), round(true_cash / tot, 3)]
    # "Illustrative" is now the client's OWN IPS targets when a bespoke IPS is on file --
    # "based on profile and IPS" (Principal 2026-07-28) -- not a generic constant mix. Falls
    # back to a generic diversification example only when no IPS target exists yet.
    ips = ctx.get("ips", {})
    ab = ips.get("alloc_bands", {})
    if ips.get("on_file") and ab.get("Equity"):
        eq_tgt = ab["Equity"][1] / 100.0
        foreign_tgt = (ips.get("foreign_target_pct") or 0) / 100.0 * eq_tgt
        gold_band = ips.get("gold_band_pct")
        gold_tgt = (gold_band[1] if gold_band else 0) / 100.0
        debt_tgt = max(0.0, 1.0 - eq_tgt - foreign_tgt - gold_tgt)
        illustrative = [round(eq_tgt - foreign_tgt, 3), round(foreign_tgt, 3),
                        round(debt_tgt, 3), round(gold_tgt, 3)]
    else:
        illustrative = [0.60, 0.15, 0.15, 0.10]   # generic diversification example, no IPS to target yet
    # 'Illustrative', never 'Proposed' — no buy recommendation in this deck (Principal 2026-07-25)
    marks = [("Today", today, SELL_HEX), ("Illustrative", illustrative, NAVY_HEX)]
    png = CH.efficient_frontier(assets, mu, sigma, corr, marks, "annex_frontier")
    deck.pic(s, png, ML, 1.85, 7.5, 4.5, valign="top", halign="left")

    rx = ML + 7.75
    rw = RX - rx
    eq_pct_disp = round(eq_share * 100)
    ips_based = ips.get("on_file") and ab.get("Equity")
    illus_basis = "your IPS targets" if ips_based else "a generic diversification example"
    if reg == "simple":
        b1 = ("Each dot is a possible mix of the four assets. Higher up means more return; further "
              "right means more ups and downs. The gold dot is the best-balanced mix.")
        b2 = (f"Your mix today (rust) is about {eq_pct_disp}% equity (shares plus equity-style "
              f"funds), the rest in debt-style funds and cash. The navy dot shows {illus_basis}, "
              f"not something we are asking you to buy.")
    else:
        b1 = ("Each dot is a feasible mix of the four assets; up is more expected return, right is more "
              "risk. The gold dot is the best risk-adjusted (max-Sharpe) mix on these assumptions.")
        b2 = (f"The book today (rust) is ~{eq_pct_disp}% equity look-through (direct shares plus "
              f"equity-style funds); the remainder sits in debt-style funds and cash. The navy "
              f"marker is {illus_basis} · it shows the direction the frontier points, it is not "
              f"a recommendation.")
    deck.callout(s, rx, 1.95, rw, 1.85, "What this shows", b1, "note")
    deck.callout(s, rx, 4.00, rw, 2.05, "Today vs an illustrative mix", b2, "good")
    illus_src = "your IPS targets" if ips_based else "a generic example, no IPS on file yet"
    deck.source(s, "Illustrative long-run CMA (return/risk, % p.a.): Indian eq 13/16 · Foreign "
                   f"eq 11/15 · Debt 7/4 · Gold 8/14 — not a forecast. 'Today' is a real equity/"
                   f"debt look-through split; 'Illustrative' uses {illus_src}.")
    return 1
