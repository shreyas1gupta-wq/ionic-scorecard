# -*- coding: utf-8 -*-
"""Annexure B, goal mapping. Projection cone with goal lines (education 2031, second home 2034,
retirement 2041 [ILLUSTRATIVE]) plus a funding table: corpus needed, needed today at the assumed
return, and funded-today % on a priority waterfall (nearest goal funded first)."""
import charts as CH
from slidekit import ML, UW, RX, HOLD, AMBER, SELL
from modules.growth_projection import _derive_mu_sigma

LABELS = {
    "hni":    ("Goal mapping", "What the corpus already covers, goal by goal"),
    "std":    ("Goal mapping", "What the corpus already covers, goal by goal"),
    "simple": ("Goal mapping", "Which goals this money already covers"),
}

# (name, target year, years from 2026, corpus needed then, Rs) [ILLUSTRATIVE placeholders
# until the family confirms actual goals]
GOALS = [
    ("Education", 2031, 5, 1.5e7),
    ("Second home", 2034, 8, 3.0e7),
    ("Retirement", 2041, 15, 30.0e7),
]


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    v0 = ctx["totals"]["grand_inr"]
    as_of = ctx["client"]["as_of"]
    # 2026-07-28 fix: reuse the same holdings-derived mu/sigma as growth_projection.py instead
    # of a second, independent flat 12%/14% constant -- two different expected-return
    # assumptions for the same book in the same deck was a cross-panel consistency failure.
    MU, SIGMA = _derive_mu_sigma(ctx)
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Whole portfolio (Rs {v0/1e7:.1f} Cr) vs illustrative goals [ILLUSTRATIVE, "
                      f"to be replaced by the family's confirmed goals] · as of {as_of}")

    # cone shows the first and last goal lines; the near-dated pair sits too close to
    # separate visually at this scale, the table below carries all three
    cone_goals = [(yrs, f"{n} {yr} · Rs {amt/1e7:.1f} Cr", amt)
                  for n, yr, yrs, amt in (GOALS[0], GOALS[-1])]
    png = CH.projection_cone(v0, 15, MU, SIGMA, "annexb_goalcone", goals=cone_goals,
                             figsize=(8.6, 4.6))
    deck.pic(s, png, ML, 1.9, 7.3, 4.0, valign="top", halign="left")

    # --- priority-waterfall funding table (nearest goal funded first) ---
    remaining = float(v0)
    rows = []; tot_pv = 0.0
    for n, yr, yrs, amt in GOALS:
        pv = amt / (1 + MU / 100.0) ** yrs
        tot_pv += pv
        take = min(remaining, pv)
        funded = take / pv * 100
        remaining -= take
        col = HOLD if funded >= 99.5 else (AMBER if funded >= 75 else SELL)
        rows.append([f"{n} ({yr})", f"Rs {amt/1e7:.1f} Cr", f"Rs {pv/1e7:.2f} Cr",
                     ("c", f"{funded:.0f}%", col, True)])
    overall = min(v0 / tot_pv * 100, 100)
    rows.append([("b", "All goals together"), f"Rs {sum(g[3] for g in GOALS)/1e7:.1f} Cr",
                 f"Rs {tot_pv/1e7:.2f} Cr", ("c", f"{overall:.0f}%", HOLD if overall >= 99.5 else AMBER, True)])
    cols = [("Goal", 0.32, "l"), ("Needed then", 0.23, "r"),
            (f"Needed today at {MU:.0f}%", 0.25, "r"), ("Funded today", 0.20, "c")]
    tx = ML + 7.5
    tw = RX - tx
    deck.table(s, tx, 1.95, tw, cols, rows, rowh=0.36, fs=8.5, hfs=6.5)

    # 2026-07-28 fix: describe the near-goals' coverage from the actual computed `funded` %,
    # not an assumed "fully covered" outcome that only held for the original demo corpus size.
    near_funded = [rows[i][3][1] for i in range(len(GOALS) - 1)]  # all goals except the last
    near_covered = all(f == "100%" for f in near_funded)
    near_clause = ("the nearer goals" if near_covered
                   else "the nearer goals are " + ", ".join(near_funded) + " funded respectively,")
    if reg == "simple":
        body = (f"{'The nearer goals are already covered by' if near_covered else near_clause + ' from'} "
                f"today's money. Retirement is ~{rows[len(GOALS)-1][3][1]} of the way there; time and "
                f"ongoing savings close the rest. A shortfall is fixed with contributions or patience, "
                f"never by taking extra risk.")
    else:
        retirement_pct = rows[len(GOALS) - 1][3][1]
        retirement_full = retirement_pct == "100%"
        retirement_clause = (f"retirement is also fully covered by today's corpus."
                              if retirement_full else
                              f"retirement is ~{retirement_pct} funded, a gap that ongoing savings and "
                              f"the {GOALS[-1][2]}-year horizon can close.")
        body = (f"Funded-today discounts each goal at the holdings-derived {MU:.0f}% return and fills "
                f"goals nearest-first. {'Education and the home are fully covered by' if near_covered else near_clause.capitalize()} "
                f"today's corpus; {retirement_clause} A goal short of 100% calls for "
                f"contributions or time, never for stretching the risk profile.")
    deck.callout(s, tx, 4.05, tw, 2.30, "How to read funded-today", body, kind="human")

    deck.source(s, f"Illustrative projection at {MU:.0f}% p.a. return, {SIGMA:.0f}% volatility; goal "
                   f"amounts and dates are placeholders [ILLUSTRATIVE], not advice or a forecast; "
                   f"outcomes will differ.")
    return 1
