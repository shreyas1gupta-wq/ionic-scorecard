# -*- coding: utf-8 -*-
"""Growth projection (Section 04, Recommendations): an illustrative lognormal cone for the
portfolio value over the mandate horizon, with a goal line (CH.projection_cone). mu/sigma are
derived from THIS book's holdings (weighted EPS growth + fund track record, composition-based
volatility proxy) -- not a fixed 12%/14% assumption (Principal 2026-07-27, permanent) -- pure
Python, no LLM cost, same formula every build."""
import charts as CH
from slidekit import ML, UW, RX

DIVIDEND_YIELD_PROXY = 1.5   # disclosed assumption: typical blended India large/mid dividend yield
EQ_MU_FALLBACK = 12.0        # used only if zero equity names carry a growth_pct (no coverage at all)
FUND_MU_FALLBACK = 9.0       # used only if zero funds carry a cagr3y (no coverage at all)
MU_CAP = 18.0                # Principal 2026-07-28 (permanent): never project above this,
                             # regardless of what the holdings-derived blend computes -- a
                             # forward-growth-heavy book (e.g. concentrated in a few high
                             # expected-growth names) can otherwise produce an implausibly
                             # optimistic headline number on an illustrative chart.


def _weighted_avg(items, value_key, weight_key="weight_pct"):
    pairs = [(it[weight_key], it[value_key]) for it in items if it.get(value_key) is not None]
    w = sum(p[0] for p in pairs)
    return (sum(p[0] * p[1] for p in pairs) / w) if w else None


def _derive_mu_sigma(ctx):
    """Expected return: holdings-weighted equity EPS growth (+ a disclosed dividend-yield proxy)
    blended with the fund sleeve's own real 3y CAGR track record, weighted by eq/mf book share.
    Volatility: no per-holding return-series is in this ctx (fund NAV history caps at 18 monthly
    points firm-wide -- see DATA LANDMINES), so sigma uses a documented composition proxy instead
    of a constant: higher for a smaller-cap-tilted or more concentrated book, lower for a
    diversified large-cap-plus-hybrid one."""
    eq = ctx["equity"]; funds = ctx["funds"]; t = ctx["totals"]
    eq_growth = _weighted_avg(eq, "growth_pct")
    eq_mu = (eq_growth + DIVIDEND_YIELD_PROXY) if eq_growth is not None else EQ_MU_FALLBACK
    fund_mu = _weighted_avg(funds, "cagr3y")
    fund_mu = fund_mu if fund_mu is not None else FUND_MU_FALLBACK
    eq_w = t.get("eq_pct", 0) / 100.0
    mf_w = t.get("mf_pct", 0) / 100.0
    tot_w = (eq_w + mf_w) or 1.0
    mu = round(min(MU_CAP, (eq_mu * eq_w + fund_mu * mf_w) / tot_w), 1)

    eq_wt_sum = sum(e["weight_pct"] for e in eq) or 1.0
    large_share = sum(e["weight_pct"] for e in eq if e.get("mcap_band") == "Large") / eq_wt_sum * 100.0
    top10 = t.get("top10_pct", 50.0)
    eq_vol = 13.0 + (100.0 - large_share) * 0.08 + max(0.0, top10 - 40.0) * 0.06
    sigma = round(min(22.0, max(11.0, eq_vol * eq_w + 7.0 * mf_w)), 1)
    return mu, sigma


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    v0 = ctx["totals"]["grand_inr"]
    years = int(ctx.get("ips", {}).get("horizon_yrs") or 7)
    mu, sigma = _derive_mu_sigma(ctx)
    goal = round(v0 * 2.0)
    goals = [(years, f"Illustrative goal ~ Rs {goal / 1e7:.1f} Cr", goal)]
    png = CH.projection_cone(v0, years, mu, sigma, "annex_cone", goals=goals)

    title = ("An illustrative path for the portfolio over the horizon"
             if reg != "simple" else "Where this could grow over time")
    s = deck.content(4, "Recommendations", "Growth projection", title)
    deck.pic(s, png, ML, 1.85, 8.0, 4.6, valign="top", halign="left")

    rx = ML + 8.15
    rw = RX - rx
    if reg == "simple":
        b1 = (f"Starting from Rs {v0 / 1e7:.2f} Cr, this shows a possible range over {years} years at "
              f"{mu}% a year — worked out from this book's own holdings, not a fixed guess. "
              f"It is an illustration, not a promise.")
        b2 = ("Markets do not move in a straight line, the shaded band shows the good and bad cases "
              "around the middle line.")
    else:
        b1 = (f"Median path from Rs {v0 / 1e7:.2f} Cr at {mu}% p.a. and {sigma}% volatility over "
              f"{years} years — derived from this book's own holdings-weighted growth and fund "
              f"track record, not a fixed assumption. The dashed line is an illustrative wealth goal.")
        b2 = ("Read the band, not the line: the shaded area is the 10th-to-90th-percentile range. "
              "Outcomes compound path-dependently and will differ from any single number.")
    deck.callout(s, rx, 1.95, rw, 2.15, "Assumptions", b1, "note")
    deck.callout(s, rx, 4.25, rw, 2.05, "Read the band", b2, "human")
    deck.source(s, "Illustrative projection on assumed return/volatility; not a forecast, guarantee, or "
                   "indication of future returns. Actual outcomes will differ.")
    return 1
