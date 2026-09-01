# -*- coding: utf-8 -*-
"""Build a synthetic holding statement for testing the kit, containing no real client.

DELIBERATELY A DIFFERENT SHAPE from the statements this pipeline was first written against. Those had
a `Holdings` sheet with a fixed column order. This one uses different sheet names, different column
headings, a title block above the header row, and a stray total row at the bottom. If the parser can
read this as well as the original, it is reading ISINs rather than memorising one platform's layout.

The ISINs are real, because the whole point is to exercise the join to the score file. The holder
names, folio numbers and amounts are invented.
"""
import os
import random

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "demo_statement.xlsx")
random.seed(7)

# real ISINs so the score lookup is exercised; everything else is fabricated
SCHEMES = [
    ("INF879O01027", "Parag Parikh Flexi Cap Fund - Direct Plan", "Equity: Flexi Cap", "Direct"),
    ("INF109K015K4", "ICICI Prudential Multi Asset Fund - Direct Plan", "Hybrid: Multi Asset Allocation", "Direct"),
    ("INF200K01T51", "SBI Small Cap Fund - Direct Plan", "Equity: Small Cap", "Direct"),
    ("INF174K01DS9", "Kotak Midcap Fund - Regular Plan", "Equity: Mid Cap", "Regular"),
    ("INF769K01010", "Mirae Asset Large Cap Fund - Regular Plan", "Equity: Large Cap", "Regular"),
    ("INF179KA1RQ7", "HDFC Large and Mid Cap Fund - Direct Plan", "Equity: Large & MidCap", "Direct"),
    ("INF760K01JC6", "Canara Robeco Small Cap Fund - Direct Plan", "Equity: Small Cap", "Direct"),
    ("INF917K01HD4", "HSBC Value Fund - Direct Plan", "Equity: Value Oriented", "Direct"),
    ("INF579M01902", "360 ONE Focused Fund - Direct Plan", "Equity: Focused", "Direct"),
    ("INF109K012B0", "ICICI Prudential Balanced Advantage Fund - Direct Plan",
     "Hybrid: Dynamic Asset Allocation", "Direct"),
    ("INF174K01LC6", "Kotak Arbitrage Fund - Direct Plan", "Hybrid: Arbitrage", "Direct"),
    ("INF277K01PR6", "Tata Money Market Fund - Direct Plan", "Debt: Money Market", "Direct"),
    ("INF179K01VX0", "HDFC Gold ETF Fund of Fund - Direct Plan", "Commodities: Gold", "Direct"),
    ("INF846K01131", "Axis ELSS Tax Saver Fund", "Equity: ELSS", "Regular"),
    ("INF999X01ZZ9", "Some Scheme The Score File Has Never Heard Of", "Equity: Flexi Cap", "Direct"),
]
HOLDERS = ["Demo Holder One", "Demo Holder Two", "Demo Family HUF"]

rows = []
for isin, name, cat, plan in SCHEMES:
    for holder in random.sample(HOLDERS, random.choice([1, 1, 2])):
        inv = round(random.uniform(3, 60) * 1e5, 2)
        cur = round(inv * random.uniform(0.92, 2.9), 2)
        rows.append({
            "Folio No.": f"{random.randint(10**7, 10**8 - 1)}",
            "Investor": holder,
            "Scheme": name,
            "ISIN Code": isin,
            "Asset Category": cat,
            "Plan Type": plan,
            "Units Held": round(cur / random.uniform(40, 900), 3),
            "Amount Invested": inv,
            "Market Value": cur,
        })
df = pd.DataFrame(rows)

with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
    # a title block above the header, which a fixed-row reader would trip on
    pre = pd.DataFrame([["CONSOLIDATED PORTFOLIO STATEMENT"], ["Generated 31-Aug-2026"], [""]])
    pre.to_excel(xl, sheet_name="Portfolio", index=False, header=False, startrow=0)
    df.to_excel(xl, sheet_name="Portfolio", index=False, startrow=3)
    # a total row at the bottom, which a naive reader would treat as a holding
    tot = pd.DataFrame([{"Folio No.": "", "Investor": "", "Scheme": "TOTAL", "ISIN Code": "",
                         "Asset Category": "", "Plan Type": "", "Units Held": "",
                         "Amount Invested": df["Amount Invested"].sum(),
                         "Market Value": df["Market Value"].sum()}])
    tot.to_excel(xl, sheet_name="Portfolio", index=False, header=False, startrow=4 + len(df))
    # a second sheet the parser must ignore
    pd.DataFrame({"Note": ["This sheet carries no holdings.",
                           "It exists so the parser has to decide what to skip."]}
                 ).to_excel(xl, sheet_name="Disclaimer", index=False)

print(f"  wrote {OUT}")
print(f"  {len(df)} holding rows, {df['ISIN Code'].nunique()} schemes, "
      f"{df['Investor'].nunique()} holders, Rs {df['Market Value'].sum():,.0f}")
print(f"  includes 1 ISIN deliberately absent from the score file, a title block, a TOTAL row "
      f"and a second sheet to ignore")
