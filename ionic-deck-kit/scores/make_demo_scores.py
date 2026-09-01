# -*- coding: utf-8 -*-
"""Produce a DEMO score file in the shape the central file will take.

The scores here are invented. This file exists so the kit can be tested end to end without shipping
Ionic's real calls, which are the proprietary part and do not belong in a demo or a public repo.

THE REAL FILE is produced centrally, covers the whole AMFI universe, and is the ONLY thing the
advisor's kit needs in order to render a deck. It carries no method, no peer sets, no NAV history and
no computation. A scheme absent from it renders as No View, which is honest by construction.
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
AS_OF = "2026-08-31"

# ISIN, scheme, SEBI category, score, call, rationale
ROWS = [
    ("INF879O01027", "Parag Parikh Flexi Cap Fund", "Equity: Flexi Cap", 63, "Hold",
     "QFRA Framework: clear of the bottom third of its own category on both horizons."),
    ("INF109K015K4", "ICICI Prudential Multi Asset Fund", "Hybrid: Multi Asset Allocation", 58, "Trim",
     "QFRA Framework: three-year return below the category median, and the largest single position, "
     "so the weight comes down rather than the fund being sold."),
    ("INF200K01T51", "SBI Small Cap Fund", "Equity: Small Cap", 13, "Sell",
     "QFRA Framework: bottom third of its own category on both horizons."),
    ("INF174K01DS9", "Kotak Midcap Fund", "Equity: Mid Cap", 61, "Hold",
     "QFRA Framework: clear of the bottom third of its own category on both horizons."),
    ("INF769K01010", "Mirae Asset Large Cap Fund", "Equity: Large Cap", 25, "Sell",
     "QFRA Framework: bottom third of its own category on both horizons."),
    ("INF179KA1RQ7", "HDFC Large and Mid Cap Fund", "Equity: Large & MidCap", 56, "Hold",
     "QFRA Framework: clear of the bottom third of its own category on both horizons."),
    ("INF760K01JC6", "Canara Robeco Small Cap Fund", "Equity: Small Cap", 25, "Sell",
     "QFRA Framework: bottom third of its own category on both horizons."),
    ("INF917K01HD4", "HSBC Value Fund", "Equity: Value Oriented", 90, "Hold",
     "QFRA Framework: top decile of its own category on the three-year record."),
    ("INF579M01902", "360 ONE Focused Fund", "Equity: Focused", 41, "Hold",
     "QFRA Framework: clear of the bottom third of its own category on both horizons."),
    ("INF109K012B0", "ICICI Prudential Balanced Advantage Fund", "Hybrid: Dynamic Asset Allocation",
     79, "Hold", "QFRA Framework: upper quartile of its own category on both horizons."),
    ("INF174K01LC6", "Kotak Arbitrage Fund", "Hybrid: Arbitrage", None, "No View", ""),
    ("INF277K01PR6", "Tata Money Market Fund", "Debt: Money Market", None, "No View", ""),
    ("INF179K01VX0", "HDFC Gold ETF Fund of Fund", "Commodities: Gold", None, "Hold",
     "QFRA Framework: held as a diversifier. The fund tracks its metal, so there is no manager "
     "record to rank."),
    ("INF846K01131", "Axis ELSS Tax Saver Fund", "Equity: ELSS", 17, "Hold",
     "QFRA Framework: below the category median on the five-year record, but a lock-in applies."),
]
df = pd.DataFrame(ROWS, columns=["isin", "scheme", "category", "score", "call", "rationale"])
df["as_of"] = AS_OF
out = os.path.join(HERE, f"ionic_scores_{AS_OF}_DEMO.csv")
df.to_csv(out, index=False)

json.dump({"as_of": AS_OF, "rows": len(df), "kind": "DEMO, invented scores",
           "note": "The production file covers the whole AMFI universe and is distributed privately."},
          open(os.path.join(HERE, "VERSION.json"), "w"), indent=1)

print(f"  wrote {out}")
print(f"  {len(df)} schemes | calls: {dict(df['call'].value_counts())}")
print(f"  as of {AS_OF}")
