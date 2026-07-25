# -*- coding: utf-8 -*-
"""Annexure A6 - estimated annual dividend income by holding (hbar, Rs lakhs) with a total
yield strip. Income as a byproduct of a growth book, made visible."""
import chart_ext_a as CA
from slidekit import ML, RX

# assumed dividend yield % per name (synthetic, patterned on typical payout levels)
YLD = {
    "ITC": 3.4, "GAIL": 4.6, "SBIN": 2.0, "TATASTEEL": 2.2, "HINDALCO": 1.3,
    "NATIONALUM": 2.8, "BHEL": 1.0, "RELIANCE": 0.8, "HDFCBANK": 1.1, "ICICIBANK": 0.8,
    "LT": 1.5, "MARUTI": 1.0, "M&M": 1.0, "BAJFINANCE": 0.5, "TITAN": 0.3,
    "SUNPHARMA": 0.9, "CIPLA": 0.9, "BHARTIARTL": 0.5, "TATAPOWER": 0.9, "SIEMENS": 0.4,
    "ABB": 0.4, "PIDILITIND": 0.5, "BOSCHLTD": 1.1, "ULTRACEMCO": 0.4, "POWERINDIA": 0.4,
    "PERSISTENT": 0.6, "VBL": 0.2, "MOTHERSON": 0.8, "JIOFIN": 0.2, "DEEPAKNTR": 0.7,
}

LABELS = {
    "hni":    ("What the book pays while it compounds",
               "Estimated annual dividend income by holding · Rs lakhs"),
    "std":    ("The income this portfolio throws off",
               "Estimated yearly dividends from the direct-equity holdings"),
    "simple": ("The cash the shares pay out",
               "A growth portfolio pays small dividends, on purpose"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    eq = ctx["equity"]
    inc = [(e, e["value_inr"] * YLD.get(e["symbol"], 0.7) / 100.0) for e in eq]
    total = sum(v for _, v in inc)
    eq_val = sum(e["value_inr"] for e in eq)
    blend = total / eq_val * 100.0
    top = sorted(inc, key=lambda t: -t[1])[:8]
    labels = [t[0]["symbol"] for t in top]
    vals = [t[1] / 1e5 for t in top]
    top_share = sum(v for _, v in top[:2]) / total * 100.0

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Direct-equity sleeve · position value x assumed dividend "
                      f"yield per name · as of {as_of}")

    png = CA.income_hbar(labels, vals, "axa_income")
    deck.pic(s, png, ML, 1.85, 6.9, 4.5, valign="top")

    tx = 7.95; tw = RX - tx
    deck.kpi_strip(s, [(f"₹{total / 1e5:.1f} L", "est. annual dividends"),
                       (f"{blend:.1f}%", "blended equity yield")], y=1.95, x=tx, w=tw)

    body1 = (f"{labels[0]} and {labels[1]} pay about {top_share:.0f}% of the book's cash income; "
             f"the growth names pay almost nothing by design. At {blend:.1f}% on the equity "
             f"sleeve, dividends here are a byproduct of stock selection, never its purpose.")
    deck.callout(s, tx, 3.2, tw, 1.6, "Where the income sits", body1, kind="note")

    body2 = ("Bring this page out when regular cash flow enters the conversation. If income "
             "becomes a goal, it is funded through planned withdrawals or a dedicated income "
             "sleeve agreed in the IPS, rather than by tilting this growth book toward "
             "high-dividend names.")
    deck.callout(s, tx, 4.95, tw, 1.55, "When to use this view", body2, kind="human")

    deck.source(s, "Estimated dividends: position value times an assumed per-name dividend yield "
                   "(synthetic, patterned on typical payout levels); no forecast of actual "
                   "distributions. [ILLUSTRATIVE]")
    return 1
