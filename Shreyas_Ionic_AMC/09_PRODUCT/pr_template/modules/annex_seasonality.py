# -*- coding: utf-8 -*-
"""Annexure A8 - monthly-returns calendar heatmap (synthetic 5y x 12m) with the
'seasonality is noise, discipline is signal' caption."""
import numpy as np
import chart_ext_a as CA
from slidekit import ML, UW

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
YEARS = ["2021", "2022", "2023", "2024", "2025"]

LABELS = {
    "hni":    ("Months do not have memory",
               "Five years of monthly returns · the seasonality check"),
    "std":    ("Is there a best month to invest?",
               "Five years of monthly returns say no"),
    "simple": ("Is there a best month?",
               "Green and red months land everywhere"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    rng = np.random.default_rng(20260725)
    M = np.round(rng.normal(1.0, 4.2, (5, 12)), 1)
    avg = np.round(M.mean(axis=0), 1)
    grid = np.vstack([M, avg])
    rows = YEARS + ["5-yr avg"]
    best_j = int(np.argmax(avg)); worst_j = int(np.argmin(avg))

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, "[ILLUSTRATIVE] Synthetic monthly returns, 5 years x 12 months · built "
                      "to show typical dispersion, not any index's record")

    png = CA.seasonality_heat(rows, MONTHS, grid, "axa_season")
    deck.pic(s, png, ML, 1.85, UW, 3.35, valign="top")

    body = (f"No month is dependable: the strongest average month ({MONTHS[best_j]}, "
            f"{avg[best_j]:+.1f}%) and the weakest ({MONTHS[worst_j]}, {avg[worst_j]:+.1f}%) are "
            f"both small next to the swing within any single month across years. Use this page "
            f"when a calendar-timing idea comes up; entry discipline and rebalancing bands do "
            f"the timing here, the calendar does not.")
    deck.callout(s, ML, 5.35, UW, 1.15, "Seasonality is noise, discipline is signal", body,
                 kind="human")

    deck.source(s, "Synthetic monthly returns (random draws, mean ~1%, sd ~4%) sized to typical "
                   "equity dispersion; any real calendar pattern of this size would still be "
                   "dominated by noise. [ILLUSTRATIVE]")
    return 1
