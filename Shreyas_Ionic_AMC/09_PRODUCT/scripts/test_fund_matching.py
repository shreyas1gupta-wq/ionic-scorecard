# -*- coding: utf-8 -*-
"""Verification for the no-fuzzy fund matcher in fund_ctx_adapter._canon (2026-08-04).

Removing the 85%-prefix fuzzy matcher only counts as a fix if REAL name variants still match.
MUST_MATCH pairs are (QFRA-source name, holdings-statement name) taken from the actual
QFRA2_current.csv / verified_navs_*.csv and the Talaulikar CAS. MUST_NOT_MATCH are the exact
false positives that fuzzy produced and that caused the original incident.

Run: python test_fund_matching.py    (exit 0 = all pass)
"""
import sys
import fund_ctx_adapter as A

MUST_MATCH = [
    # plan / growth decoration only
    ("Kotak Flexicap Fund(G)", "Kotak Flexicap Fund - Growth (Regular Plan)"),
    ("HDFC Flexi Cap Fund(G)", "HDFC Flexi Cap Fund - Regular Plan - Growth"),
    ("HDFC Flexi Cap Fund(G)", "HDFC Flexi Cap Fund - Direct Plan - Growth Option"),
    ("Nippon India Large Cap Fund(G)", "NIPPON INDIA LARGE CAP FUND - GROWTH"),
    ("Franklin India Flexi Cap Fund(G)", "Franklin India Flexi Cap Fund - Growth"),
    ("Nippon India Multi Cap Fund(G)", "NIPPON INDIA MULTI CAP FUND - GROWTH"),
    # AMC alias
    ("ICICI Pru Large & Mid Cap Fund(G)", "ICICI Prudential Large & Mid Cap Fund - Growth"),
    ("Invesco India Large & Mid Cap Fund(G)",
     "Invesco India Large & Mid Cap Fund - Regular Plan Growth"),
    ("Aditya Birla SL Flexi Cap Fund(G)",
     "Aditya Birla Sun Life Flexi Cap Fund - Growth-Regular Plan"),
    ("Aditya Birla SL Small Cap Fund(G)", "Aditya Birla Sun Life Small Cap Fund - Growth"),
    # "&" vs "and" connector
    ("ICICI Pru Large & Mid Cap Fund(G)", "ICICI Prudential Large and Mid Cap Fund - Growth"),
    # documented scheme renames (these are the two the deck got wrong)
    ("ICICI Pru Bluechip Fund(G)", "ICICI Prudential Large Cap Fund - Growth"),
    ("Kotak Emerging Equity Fund(G)", "Kotak Midcap Fund - Growth (Regular Plan)"),
    ("Bandhan Core Equity Fund", "Bandhan Large & Mid Cap Fund-Regular Plan-Growth"),
    ("DSP Equity Opportunities Fund", "DSP Large & Mid Cap Fund - Regular - Growth"),
    # verified abbreviations
    ("Kotak Equity Opp Fund(G)", "Kotak Equity Opportunities Fund - Growth"),
    ("Franklin India Smaller Cos Fund(G)", "Franklin India Smaller Companies Fund - Growth"),
    # focused funds that were wrongly treated as uncovered
    ("HDFC Focused Fund - Growth Option - Direct Plan",
     "HDFC Focused Fund - Regular Plan - Growth"),
    ("ICICI Prudential Focused Equity Fund",
     "ICICI Prudential Focused Equity Fund - Growth"),
    ("Invesco India Focused Fund", "Invesco India Focused Fund - Regular Plan Growth"),
]

MUST_NOT_MATCH = [
    # the two real false positives fuzzy produced (see mf_mapping.py header)
    ("Kotak Midcap Fund", "Kotak Multicap Fund Regular Plan - Growth"),
    ("ICICI Prudential Liquid Fund - Growth", "ICICI Pru Large & Mid Cap Fund(G)"),
    # same AMC, genuinely different schemes
    ("Franklin India Equity Advantage Fund(G)", "Franklin India Flexi Cap Fund - Growth"),
    ("Sundaram Value Fund", "Sundaram Value Fund Series II"),
    ("HDFC Top 100 Fund(G)", "HDFC Flexi Cap Fund - Regular Plan - Growth"),
    ("Quant Mid Cap Fund(G)", "quant Large Cap Fund - Regular Plan - Growth"),
    ("ICICI Pru Midcap Fund(G)", "ICICI Prudential Multicap Fund - Growth"),
    # cross-AMC lookalikes
    ("Aditya Birla SL Flexi Cap Fund(G)", "Axis Flexi Cap Fund - Growth"),
]

fails = []
print("=== MUST MATCH ===")
for a, b in MUST_MATCH:
    ka, kb = A._canon(a), A._canon(b)
    ok = ka == kb and ka != ""
    print(f"  {'OK  ' if ok else 'FAIL'}  {a[:44]:44s} -> {ka}")
    if not ok:
        print(f"        {b[:44]:44s} -> {kb}")
        fails.append(("MATCH", a, b, ka, kb))

print("\n=== MUST NOT MATCH ===")
for a, b in MUST_NOT_MATCH:
    ka, kb = A._canon(a), A._canon(b)
    ok = ka != kb
    print(f"  {'OK  ' if ok else 'FAIL'}  {a[:40]:40s} vs {b[:40]:40s}")
    if not ok:
        print(f"        both canonicalize to '{ka}'")
        fails.append(("NOMATCH", a, b, ka, kb))

# every published QFRA-2 fund must produce a non-empty, unique canonical key
print("\n=== QFRA2_current.csv key uniqueness ===")
import pandas as pd
df = pd.read_csv(A.QFRA2_CSV)
keys = {}
for _, r in df.iterrows():
    k = A._canon(r["fund"])
    if not k:
        fails.append(("EMPTY", r["fund"], "", "", "")); continue
    keys.setdefault(k, []).append(f'{r["category"]}/{r["fund"]}')
dupes = {k: v for k, v in keys.items() if len(v) > 1}
print(f"  {len(df)} rows -> {len(keys)} distinct canonical keys")
for k, v in dupes.items():
    print(f"  COLLISION '{k}': {v}")
    fails.append(("COLLISION", k, str(v), "", ""))

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURE(S)"))
sys.exit(1 if fails else 0)
