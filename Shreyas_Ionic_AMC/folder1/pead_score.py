#!/usr/bin/env python3
"""
PEAD (Post-Earnings-Announcement-Drift) fundamental scorer.

Reference implementation of the funda PEAD Score used by the daily Tijori scan
and the "PEAD Scanner & Tracker" web app. This module is the single source of
truth for the scoring math — it mirrors the JavaScript `scoreEP()` in the
tracker HTML byte-for-byte in behaviour.

The score (0-100) grades a quarterly result on how "fly-worthy" the print is:
a big, clean, durable earnings beat that tends to drift, rather than routine
15% growth. It intentionally penalises low-quality beats (profit up on other
income, low absolute base, loss quarters, etc.).

Usage
-----
    # score the built-in sample feed and print a ranked table
    python3 pead_score.py

    # score your own rows from a JSON file (list of row objects)
    python3 pead_score.py rows.json

    # filter to mcap > 500 Cr (the trader's default working set)
    python3 pead_score.py rows.json --min-mcap 500

Row object schema (all numeric fields may be None for blank / "-" cells)
------------------------------------------------------------------------
    name      str    company name
    ticker    str    NSE trading symbol (powers the TradingView link); "" if unknown
    date      str    result date, YYYY-MM-DD
    mcap      float  market cap in Rs Cr   (note: "L Cr" on Tijori = lakh crore = x100000)
    pe        float  price/earnings
    salesYoY  float  Sales YoY growth %
    salesQoQ  float  Sales QoQ growth %
    opYoY     float  Operating Profit YoY growth %
    npYoY     float  Net Profit YoY growth %
    npQoQ     float  Net Profit QoQ growth %
    sMar      float  Sales, latest quarter (Rs Cr)
    sDec      float  Sales, previous quarter
    sPrev     float  Sales, year-ago quarter
    opMar     float  Operating Profit, latest quarter
    opPrev    float  Operating Profit, year-ago quarter
    npMar     float  Net Profit, latest quarter
    npDec     float  Net Profit, previous quarter
    npPrev    float  Net Profit, year-ago quarter
    url       str    Tijori company page URL

(The Mar/Dec/Prev suffixes are historical field names; they map to
latest / previous-qtr / year-ago columns respectively, whatever the calendar.)
"""

import json
import sys


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def score_row(c):
    """Return a dict: total, grade, four pillar sub-scores, flags, and OPM figures.

    Scoring logic (must stay identical to the tracker's JS scoreEP):

    Growth magnitude (max 30)
        +clamp((npYoY-25)/75, 0, 1) * 14     # PAT growth, scaled 25% -> 100%
        +clamp((salesYoY-8)/22, 0, 1) * 8    # sales growth, scaled 8% -> 30%
        +clamp((opYoY-15)/45, 0, 1) * 8      # OP growth, scaled 15% -> 60%

    Acceleration (max 20)
        +5 if salesQoQ > 0                   # sequential top-line momentum
        +5 if npQoQ  > 0                     # sequential bottom-line momentum
        +5 if npMar > npDec                  # PAT above previous quarter (level)
        +5 if npMar > npPrev                 # PAT above year-ago quarter (level)

    Margin / operating leverage (max 25)
        if opMar,sMar,opPrev,sPrev all > 0:
            +clamp((OPM_latest - OPM_yearago)/4, 0, 1) * 13   # margin expansion
        if opYoY > salesYoY:
            +clamp((opYoY - salesYoY)/30, 0, 1) * 12          # positive op-leverage

    Quality of beat (start 25, subtract; floor 0)
        -12 flag "NP up OP down"  if opYoY <= 0 and npYoY > 0
        else -8 flag "NP>>OP"     if npYoY > opYoY + 40
        -8  flag "sales down"     if salesYoY < 0 and npYoY > 0
        -10 flag "low base"       if abs(npMar) < 5
        -15 flag "loss qtr"       if npMar < 0

    total = round(sum of the four pillars)
    grade: >=75 A, >=60 B, >=45 C, else D
    """
    flags = []
    npY, sY, opY = c.get("npYoY"), c.get("salesYoY"), c.get("opYoY")
    npMar, npDec, npPrev = c.get("npMar"), c.get("npDec"), c.get("npPrev")
    sMar, sPrev = c.get("sMar"), c.get("sPrev")
    opMar, opPrev = c.get("opMar"), c.get("opPrev")

    # --- Pillar 1: growth magnitude (max 30) ---
    g = 0.0
    if npY is not None:
        g += clamp((npY - 25) / 75, 0, 1) * 14
    if sY is not None:
        g += clamp((sY - 8) / 22, 0, 1) * 8
    if opY is not None:
        g += clamp((opY - 15) / 45, 0, 1) * 8
    g = clamp(g, 0, 30)

    # --- Pillar 2: acceleration (max 20) ---
    a = 0.0
    if c.get("salesQoQ") is not None and c["salesQoQ"] > 0:
        a += 5
    if c.get("npQoQ") is not None and c["npQoQ"] > 0:
        a += 5
    if npMar is not None and npDec is not None and npMar > npDec:
        a += 5
    if npMar is not None and npPrev is not None and npMar > npPrev:
        a += 5
    a = clamp(a, 0, 20)

    # --- Pillar 3: margin / operating leverage (max 25) ---
    m = 0.0
    omN = omP = None
    if (opMar is not None and sMar is not None and sMar > 0
            and opPrev is not None and sPrev is not None and sPrev > 0):
        omN = opMar / sMar * 100
        omP = opPrev / sPrev * 100
        m += clamp((omN - omP) / 4, 0, 1) * 13
    if opY is not None and sY is not None and opY > sY:
        m += clamp((opY - sY) / 30, 0, 1) * 12
    m = clamp(m, 0, 25)

    # --- Pillar 4: quality of beat (start 25, subtract) ---
    q = 25.0
    if npY is not None and opY is not None:
        if opY <= 0 and npY > 0:
            q -= 12
            flags.append("NP up OP down")
        elif npY > opY + 40:
            q -= 8
            flags.append("NP>>OP")
    if sY is not None and sY < 0 and npY is not None and npY > 0:
        q -= 8
        flags.append("sales down")
    if npMar is not None and abs(npMar) < 5:
        q -= 10
        flags.append("low base")
    if npMar is not None and npMar < 0:
        q -= 15
        flags.append("loss qtr")
    q = clamp(q, 0, 25)

    total = round(g + a + m + q)
    grade = "A" if total >= 75 else "B" if total >= 60 else "C" if total >= 45 else "D"
    return {
        "total": total,
        "grade": grade,
        "growth": round(g),
        "acceleration": round(a),
        "margin": round(m),
        "quality": round(q),
        "flags": flags,
        "opm_latest": omN,
        "opm_yearago": omP,
    }


# NOTE: Banks / NBFCs report an unusual "operating profit", so their margin and
# quality pillars can mislead. Treat A/B grades on financials with extra caution.

# --- Built-in sample feed (Tijori Q1 FY27 batch, page 1) for a quick self-test ---
SAMPLE_FEED = [
    {"name": "Bhansali Engg. Poly.", "ticker": "BEPL", "date": "2026-07-18", "mcap": 2803, "pe": 14.02, "salesYoY": 53.34, "salesQoQ": 38.22, "opYoY": 57.16, "npYoY": 42.84, "npQoQ": 26.06, "sMar": 472, "sDec": 341, "sPrev": 307, "opMar": 82.59, "opPrev": 52.55, "npMar": 65.14, "npDec": 51.67, "npPrev": 45.6},
    {"name": "Sangam (India)", "ticker": "SANGAMIND", "date": "2026-07-18", "mcap": 3189, "pe": 26.25, "salesYoY": 8.94, "salesQoQ": -2.67, "opYoY": 82.84, "npYoY": 1825, "npQoQ": 24.76, "sMar": 860, "sDec": 883, "sPrev": 789, "opMar": 105, "opPrev": 57.63, "npMar": 41.02, "npDec": 32.88, "npPrev": 2.13},
    {"name": "India Cements", "ticker": "INDIACEM", "date": "2026-07-18", "mcap": 12715, "pe": 137.48, "salesYoY": -0.52, "salesQoQ": -17.03, "opYoY": 87.19, "npYoY": 120, "npQoQ": -54.87, "sMar": 1019, "sDec": 1228, "sPrev": 1024, "opMar": 155, "opPrev": 83.19, "npMar": 26.85, "npDec": 59.5, "npPrev": -131},
    {"name": "Premier Polyfilm", "ticker": "PREMIERPOL", "date": "2026-07-18", "mcap": 775, "pe": 22.17, "salesYoY": 34.25, "salesQoQ": 8.93, "opYoY": 40.1, "npYoY": 51.33, "npQoQ": 5.83, "sMar": 100, "sDec": 92.4, "sPrev": 74.97, "opMar": 13.52, "opPrev": 9.65, "npMar": 9.08, "npDec": 8.58, "npPrev": 6.0},
    {"name": "Yes Bank", "ticker": "YESBANK", "date": "2026-07-18", "mcap": 74168, "pe": 19.65, "salesYoY": 5.92, "salesQoQ": 5.12, "opYoY": 24.61, "npYoY": 32.54, "npQoQ": -0.96, "sMar": 8054, "sDec": 7662, "sPrev": 7604, "opMar": 1705, "opPrev": 1368, "npMar": 1071, "npDec": 1082, "npPrev": 808},
    {"name": "Kotak Mahindra Bank", "ticker": "KOTAKBANK", "date": "2026-07-18", "mcap": 388000, "pe": 19.11, "salesYoY": 6.41, "salesQoQ": 2.96, "opYoY": 12.19, "npYoY": 22.55, "npQoQ": 1.06, "sMar": 18354, "sDec": 17827, "sPrev": 17248, "opMar": 8273, "opPrev": 7374, "npMar": 5487, "npDec": 5401, "npPrev": 4429},
    {"name": "PNB", "ticker": "PNB", "date": "2026-07-18", "mcap": 122000, "pe": 5.51, "salesYoY": 3.12, "salesQoQ": 2.41, "opYoY": 4.7, "npYoY": 174, "npQoQ": 3.99, "sMar": 33589, "sDec": 32797, "sPrev": 32572, "opMar": 7662, "opPrev": 7318, "npMar": 5339, "npDec": 5225, "npPrev": 1832},
]


def run(rows, min_mcap=None):
    scored = [(score_row(r), r) for r in rows]
    scored.sort(key=lambda x: -x[0]["total"])
    print(f"{'Score':>5} {'Gr':>2}  {'Company':24s} {'Mcap(Cr)':>10}  {'S/OP/NP YoY':>18}  Flags")
    print("-" * 92)
    for s, r in scored:
        if min_mcap is not None and (r.get("mcap") or 0) < min_mcap:
            continue
        yoy = f"{r.get('salesYoY')}/{r.get('opYoY')}/{r.get('npYoY')}"
        flags = ", ".join(s["flags"]) if s["flags"] else "clean"
        print(f"{s['total']:>5} {s['grade']:>2}  {r['name'][:24]:24s} {r.get('mcap',0):>10}  {yoy:>18}  {flags}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    min_mcap = None
    if "--min-mcap" in args:
        i = args.index("--min-mcap")
        min_mcap = float(args[i + 1])
        del args[i:i + 2]
    if args:
        with open(args[0]) as f:
            rows = json.load(f)
    else:
        print("(no input file given — scoring the built-in sample feed)\n")
        rows = SAMPLE_FEED
    run(rows, min_mcap=min_mcap)
