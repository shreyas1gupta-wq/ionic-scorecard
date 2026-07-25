# -*- coding: utf-8 -*-
"""Annexure B, beta ladder. Holding-level beta lollipops (stems from market = 1.0), high-beta
tail flagged. Betas are sector-keyed synthetic estimates [ILLUSTRATIVE] with a deterministic
per-name offset, pending a real regression on price history."""
import hashlib
import chart_ext_b as CB
from slidekit import ML, UW, RX, SELL, SERIF, SLATE

LABELS = {
    "hni":    ("Volatility ladder", "Which holdings amplify the market, and by how much"),
    "std":    ("Volatility ladder", "Which holdings move more than the market"),
    "simple": ("Volatility ladder", "The jumpier stocks in the book"),
}

# sector -> illustrative beta anchor
BETA = {
    "Metals & Mining": 1.35, "Construction": 1.22, "Capital Goods": 1.18,
    "Financial Services": 1.10, "Automobile And Auto Components": 1.05,
    "Consumer Services": 1.05, "Chemicals": 1.05, "Construction Materials": 1.05,
    "Oil Gas & Consumable Fuels": 1.00, "Power": 0.98, "Information Technology": 0.95,
    "Consumer Durables": 0.92, "Services": 0.90, "Telecommunication": 0.85,
    "Healthcare": 0.82, "Fast Moving Consumer Goods": 0.72,
}
FLAG = 1.2


def _beta(e):
    base = BETA.get(e["sector"], 1.0)
    j = (int(hashlib.md5(e["symbol"].encode()).hexdigest(), 16) % 17 - 8) / 100.0
    return round(base + j, 2)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    as_of = ctx["client"]["as_of"]
    betas = {e["symbol"]: _beta(e) for e in eq}
    wsum = sum(e["weight_pct"] for e in eq)
    book_beta = round(sum(e["weight_pct"] * betas[e["symbol"]] for e in eq) / wsum, 2)
    hi_tail = sorted([e for e in eq if betas[e["symbol"]] >= FLAG],
                     key=lambda e: -betas[e["symbol"]])
    tail_wt = sum(e["weight_pct"] for e in hi_tail)

    # ladder: top 13 by weight, plus every flagged name, sorted by beta
    ladder = sorted(eq, key=lambda e: -e["weight_pct"])[:13]
    for e in hi_tail:
        if e not in ladder:
            ladder.append(e)
    ladder = sorted(ladder, key=lambda e: -betas[e["symbol"]])[:17]

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Direct equity book · sector-keyed betas [ILLUSTRATIVE] pending regression "
                      f"on price history · as of {as_of}")

    png = CB.beta_ladder([e["symbol"] for e in ladder], [betas[e["symbol"]] for e in ladder],
                         "annexb_beta", flag=FLAG, book_beta=book_beta)
    deck.pic(s, png, ML, 1.95, 6.9, 4.5, valign="top", halign="left")

    tx = ML + 7.1
    tw = RX - tx
    cols = [("High-beta name", 0.42, "l"), ("Beta", 0.18, "r"), ("Weight", 0.20, "r"), ("Call", 0.20, "c")]
    rows = [[e["symbol"], ("c", f"{betas[e['symbol']]:.2f}", SELL, True),
             f"{e['weight_pct']:.1f}%", ("pill", e["rec"], e["rec"])] for e in hi_tail[:6]]
    deck.txt(s, tx, 1.86, tw, 0.22, [(f"THE HIGH-BETA TAIL · {tail_wt:.1f}% OF BOOK",
                                      "Bahnschrift", 9, SELL, True, False, 60)])
    deck.table(s, tx, 2.14, tw, cols, rows, rowh=0.30, fs=8.5, hfs=7)

    if reg == "simple":
        body = (f"Beta says how much a stock moves when the market moves. The book overall sits near "
                f"{book_beta:.1f}, close to the market. A small tail of names moves harder in both "
                f"directions; in a fall they will drop more than the index.")
    else:
        body = (f"Book-weighted beta is {book_beta:.2f}, close to the market, so the base is sensible. "
                f"The tail above {FLAG:.1f} ({tail_wt:.1f}% of the book, concentrated in metals and "
                f"capital goods) is where a market drawdown bites hardest: these names tend to fall "
                f"further than the index and recover on their own cycle, not the market's. Position "
                f"sizes there should earn their volatility.")
    deck.callout(s, tx, 4.25, tw, 2.25, "How to read the ladder", body, kind="note")

    deck.source(s, "Betas are sector-keyed illustrative estimates with a fixed per-name offset "
                   "[ILLUSTRATIVE], not regression output; ladder shows the largest positions plus "
                   "every flagged name.")
    return 1
