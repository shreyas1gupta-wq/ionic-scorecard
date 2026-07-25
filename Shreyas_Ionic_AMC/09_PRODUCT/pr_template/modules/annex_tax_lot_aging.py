# -*- coding: utf-8 -*-
"""Annexure B, LTCG unlock timeline. % of the book's unrealised taxable gain turning long-term
per quarter over the next 8 quarters (bars) with the cumulative line. Lot schedule is synthetic
[ILLUSTRATIVE]: the real one needs the demat trade file. 'Patience has a tax value' framing."""
import chart_ext_b as CB
from slidekit import ML, UW, RX, HOLD, SERIF, SLATE

LABELS = {
    "hni":    ("Tax-lot aging", "When the gains turn long-term, quarter by quarter"),
    "std":    ("Tax-lot aging", "When the gains turn long-term, quarter by quarter"),
    "simple": ("Tax-lot aging", "Waiting can cut the tax on selling"),
}

QUARTERS = ["Sep 26", "Dec 26", "Mar 27", "Jun 27", "Sep 27", "Dec 27", "Mar 28", "Jun 28"]
START_LT = 34            # % of unrealised gain already long-term today [ILLUSTRATIVE]
ADDS = [9, 12, 10, 8, 7, 6, 4, 3]  # % turning long-term per quarter [ILLUSTRATIVE]
STCG, LTCG = 20.0, 12.5  # equity rates as understood as of Jul-2026; confirm with tax adviser


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    de_gap = ctx.get("tax", {}).get("de_gap_note", "")
    end_lt = START_LT + sum(ADDS)
    save_per_l = round((STCG - LTCG) * 1000)  # Rs saved per Rs 1L of gain that ages to LTCG

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Direct equity unrealised gains · illustrative lot schedule [ILLUSTRATIVE], "
                      f"actuals need the demat trade file · as of {as_of}")

    deck.kpi_strip(s, [
        (f"{START_LT}%", "Long-term today", "of unrealised gain"),
        (f"{end_lt}%", f"By {QUARTERS[-1]}", "if lots simply age"),
        (f"{STCG:.0f}% vs {LTCG:.1f}%", "STCG vs LTCG rate", "as of Jul-2026"),
        (f"Rs {save_per_l:,}", "Saved per Rs 1L of gain", "by waiting for LTCG", HOLD),
    ], y=1.85)

    png = CB.ltcg_unlock(QUARTERS, START_LT, ADDS, "annexb_ltcg")
    deck.pic(s, png, ML, 3.0, 7.3, 3.45, valign="top", halign="left")

    tx = ML + 7.5
    tw = RX - tx
    if reg == "simple":
        body = (f"Gains on shares held over a year are taxed at {LTCG:.1f}% instead of {STCG:.0f}%. "
                f"Some of the book's gains cross that line every quarter, so where a sale can wait a "
                f"few months without adding risk, waiting is often worth it.")
    else:
        body = (f"Patience has a tax value: every Rs 1L of gain that ages past 12 months is taxed at "
                f"{LTCG:.1f}% instead of {STCG:.0f}%, saving about Rs {save_per_l:,}. The sequencing "
                f"rule that follows: conviction Sells execute now, tax is never a reason to hold a "
                f"broken thesis; borderline Trims check the lot calendar first, because a quarter's "
                f"wait can be paid for by the tax saved.")
    deck.callout(s, tx, 3.0, tw, 2.35, "Patience has a tax value", body, kind="good")
    deck.txt(s, tx, 5.55, tw, 0.85,
             [(f"Confirm before acting: {de_gap} Rates and holding-period rules change; verify the "
                f"schedule and character with your tax adviser.", SERIF, 8.5, SLATE, False, True)], ls=1.08)

    deck.source(s, f"Lot-aging schedule is synthetic [ILLUSTRATIVE]; rates ({STCG:.0f}% STCG / "
                   f"{LTCG:.1f}% LTCG on listed equity, over the exemption) as understood as of "
                   f"Jul-2026; confirm with your tax adviser.")
    return 1
