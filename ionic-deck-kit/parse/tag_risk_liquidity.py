# -*- coding: utf-8 -*-
"""Place every holding on the firm's two risk axes: what can go wrong, and how fast you can get out.

This is NOT the fund score. The score asks whether a manager beat their own category; these two axes
ask what the instrument itself is. A fund can be a Hold on the score and the least liquid thing in
the book, and the review has to show both.

The framework sets a band by SUB-CATEGORY, so the whole job is placing a holding into one, which is
done by evidence and never by guessing:

    a scheme          its SEBI category, which arrives on the score file keyed by ISIN
    a direct share    NSE index membership, from scores/equity_mcap_bands.csv
    anything else     its own Category column on the statement, mapped below one line at a time

A holding this cannot place carries no band and says so. A wrong band puts real money in the wrong
row of a risk grid, so a gap is the better answer. The first version of this defaulted a failed
match to Micro Cap and tagged HDFC Bank at risk 88; defaulting to the riskiest band is the worst
default there is.
"""
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCORES = os.path.join(os.path.dirname(HERE), "scores")

# SEBI category on the score file -> framework sub-category.
SEBI_TO_SUB = {
    "Equity Scheme - Large Cap Fund": "Large Cap Fund",
    "Equity Scheme - Large & Mid Cap Fund": "Large & Mid Cap Fund",
    "Equity Scheme - Flexi Cap Fund": "Flexi Cap Fund",
    "Equity Scheme - Multi Cap Fund": "Flexi Cap Fund",
    "Equity Scheme - Focused Fund": "Focused Fund",
    "Equity Scheme - Mid Cap Fund": "Mid Cap Fund",
    "Equity Scheme - Small Cap Fund": "Small Cap Fund",
    "Equity Scheme - Value Fund": "Flexi Cap Fund",
    "Equity Scheme - Contra Fund": "Flexi Cap Fund",
    "Equity Scheme - Dividend Yield Fund": "Flexi Cap Fund",
    "Equity Scheme - ELSS": "ELSS",
    "Equity Scheme - Sectoral/ Thematic": "Thematic / Sectoral Fund",
    "Other Scheme - FoF Overseas": "International Fund / FoF",
    "Other Scheme - FoF Domestic": "Index Fund / ETF - Broad Market",
    "Other Scheme - Gold ETF": "Gold / Silver ETF or FoF",
    "Hybrid Scheme - Arbitrage Fund": "Arbitrage Fund",
    "Hybrid Scheme - Equity Savings": "Equity Savings Fund",
    "Hybrid Scheme - Aggressive Hybrid Fund": "Balanced Advantage / Dynamic Asset Allocation",
    "Hybrid Scheme - Conservative Hybrid Fund": "Corporate Bond Fund",
    "Hybrid Scheme - Balanced Hybrid Fund": "Balanced Advantage / Dynamic Asset Allocation",
    "Hybrid Scheme - Multi Asset Allocation": "Balanced Advantage / Dynamic Asset Allocation",
    "Hybrid Scheme - Dynamic Asset Allocation or Balanced Advantage":
        "Balanced Advantage / Dynamic Asset Allocation",
    "Solution Oriented Scheme - Retirement Fund": "Flexi Cap Fund",
    "Debt Scheme - Overnight Fund": "Overnight Fund",
    "Debt Scheme - Liquid Fund": "Liquid Fund",
    "Debt Scheme - Money Market Fund": "Money Market / Ultra Short / Low Duration",
    "Debt Scheme - Ultra Short Duration Fund": "Money Market / Ultra Short / Low Duration",
    "Debt Scheme - Low Duration Fund": "Money Market / Ultra Short / Low Duration",
    "Debt Scheme - Floater Fund": "Money Market / Ultra Short / Low Duration",
    "Debt Scheme - Short Duration Fund": "Short Duration / Banking & PSU Debt",
    "Debt Scheme - Banking and PSU Fund": "Short Duration / Banking & PSU Debt",
    "Debt Scheme - Corporate Bond Fund": "Corporate Bond Fund",
    "Debt Scheme - Credit Risk Fund": "Credit Risk Fund",
    "Debt Scheme - Gilt Fund": "Gilt Fund / Constant Maturity Gilt",
    "Debt Scheme - Gilt Fund with 10 year constant duration": "Gilt Fund / Constant Maturity Gilt",
    "Debt Scheme - Dynamic Bond": "Dynamic Bond Fund",
    "Debt Scheme - Medium Duration Fund": "Corporate Bond Fund",
    "Debt Scheme - Medium to Long Duration Fund": "Corporate Bond Fund",
    "Debt Scheme - Long Duration Fund": "G-Sec - Long (residual over 15 years)",
}
# AMFI's legacy label variants. The same inconsistency that once put 126 wrong Sell calls on the
# score file: a category has to be resolved, never pattern-matched loosely.
for _legacy, _sub in (("Income/Debt Oriented Schemes - Liquid Fund", "Liquid Fund"),
                      ("Income/Debt Oriented Schemes - Overnight Fund", "Overnight Fund"),
                      ("Income/Debt Oriented Schemes - Corporate Bond Fund", "Corporate Bond Fund"),
                      ("Income/Debt Oriented Schemes - Banking and PSU Debt Fund",
                       "Short Duration / Banking & PSU Debt"),
                      ("Income/Debt Oriented Schemes - Short Term Fund",
                       "Short Duration / Banking & PSU Debt"),
                      ("Income/Debt Oriented Schemes - Money Market Fund",
                       "Money Market / Ultra Short / Low Duration"),
                      ("Income/Debt Oriented Schemes - Ultra Short Term Fund",
                       "Money Market / Ultra Short / Low Duration"),
                      ("Income", "Corporate Bond Fund"),
                      ("Gilt", "Gilt Fund / Constant Maturity Gilt"),
                      ("ELSS", "ELSS")):
    SEBI_TO_SUB.setdefault(_legacy, _sub)

# A factor index is not a broad-market index: the factor is itself a concentration, which is why the
# framework prices one at 70 and the other at 50. The name has to be read before the band is set.
FACTOR_RX = re.compile(r"momentum|low\s*vol|value\s*\d|quality|alpha|smart\s*beta|equal\s*weight",
                       re.IGNORECASE)
TARGET_MAT_RX = re.compile(r"\bsdl\b|target\s*matur|g-?sec\s*20\d\d|psu\s*bond", re.IGNORECASE)
LIQUID_RX = re.compile(r"1d\s*rate|liquid\s*bees|liquid\s*rate|overnight", re.IGNORECASE)
GSEC_RX = re.compile(r"g-?sec.*?(20\d\d)", re.IGNORECASE)

# The statement's own Category column, for holdings the score file never sees.
CATEGORY_TO_SUB = {
    "reits": "REIT",
    "invits": "InvIT",
    "ulip": "ULIP",
    "private equity": "Unlisted Equity - Late Stage / Pre-IPO",
    "pms": "PMS - Discretionary Listed Equity",
}
_FORM = re.compile(r"\b(LTD|LIMITED|PVT|PRIVATE|CORPORATION|CORP|COMPANY|CO|THE|INC|INDIA)\b")


def cnorm(s):
    u = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())
    return re.sub(r"\s+", " ", _FORM.sub(" ", u)).strip()


def _load(name):
    p = os.path.join(SCORES, name)
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, comment="#")


def load_bands():
    b = _load("risk_liquidity_bands.csv")
    if b is None:
        return {}, {}
    b["sub_category"] = b["sub_category"].astype(str).str.strip()
    bands = {r["sub_category"]: r for _, r in b.iterrows()}
    m = _load("equity_mcap_bands.csv")
    mcap = {} if m is None else dict(zip(m["company_key"].astype(str), m["mcap_band"].astype(str)))
    return bands, mcap


def sub_for_fund(name, sebi_category):
    """A scheme's sub-category, read off its SEBI category and, where the category is a container
    rather than a mandate (index funds, other ETFs), off what the vehicle actually tracks."""
    nm = str(name or "")
    cat = str(sebi_category or "").strip()
    if LIQUID_RX.search(nm):
        return "Liquid Fund"
    if TARGET_MAT_RX.search(nm):
        return "Target Maturity Index Fund (G-Sec / SDL / PSU)"
    if cat in ("Other Scheme - Index Funds", "Other Scheme - Other  ETFs",
               "Other Scheme - Other ETFs", "Index Funds - Equity Funds",
               "Exchange Traded Funds (ETFs) - Equity ETF") or "index" in nm.lower() \
            or "etf" in nm.lower():
        return "Factor / Smart Beta Fund" if FACTOR_RX.search(nm) else "Index Fund / ETF - Broad Market"
    return SEBI_TO_SUB.get(cat)


def sub_for_other(name, category, asset_class, mcap):
    """A holding the score file never sees: a share, a bond, an AIF, a REIT, a ULIP."""
    nm = str(name or "").strip()
    cat = str(category or "").strip().lower()
    if cat in ("direct equity", "direct equities"):
        band = mcap.get(cnorm(nm))
        if band is None:
            return None            # not in the top 750 by market cap, or a name we cannot resolve
        return "Direct Equity - " + band
    if cat in CATEGORY_TO_SUB:
        return CATEGORY_TO_SUB[cat]
    if cat == "direct units":
        return "REIT" if "reit" in nm.lower() else "InvIT" if "invit" in nm.lower() else None
    if cat == "direct fixed income":
        m = GSEC_RX.search(nm)
        if m:
            yrs = int(m.group(1)) - pd.Timestamp.utcnow().year
            return ("G-Sec - Long (residual over 15 years)" if yrs > 15 else
                    "G-Sec - Medium (residual 5 to 15 years)" if yrs >= 5 else
                    "G-Sec - Short (residual under 5 years)")
        if re.search(r"\bbank\b", nm, re.IGNORECASE):
            return "Fixed Deposit - small finance bank / NBFC / corporate"
        if re.search(r"national highway|railway finance|infrastructure finance|\bnhai\b|\birfc\b",
                     nm, re.IGNORECASE):
            return "Bonds - AAA PSU / sovereign-owned"
        if re.search(r"\bncd\b|debenture", nm, re.IGNORECASE):
            return "NCD - AA and below / unrated / market-linked"
        return None
    if cat == "aif":
        low = nm.lower()
        if re.search(r"credit|debt|sstif|mezzan|structur", low):
            return "AIF Cat II - Structured / Mezzanine / Venture Debt"
        if re.search(r"\bpe\b|private equity|growth fund|capital", low):
            return "AIF Cat II - Private Equity Fund"
        if re.search(r"venture|vc\b", low):
            return "AIF Cat I - Venture Capital Fund"
        if re.search(r"real estate|realty", low):
            return "AIF Cat II - Real Estate - Yield / Lease"
        if str(asset_class or "").strip().lower() == "alternates":
            return "AIF Cat III - Long / Short / Absolute Return"
        return "AIF Cat III - Long Only Listed Equity"
    if cat == "funds" and re.search(r"life insurance|ulip|wealth", nm, re.IGNORECASE):
        return "ULIP"
    return None


def attach(rows, bands, mcap, kind):
    """Attach a band to every row in place. Returns (placed, unplaced_value)."""
    placed, gap = 0, 0.0
    for r in rows:
        sub = (sub_for_fund(r.get("name"), r.get("sebi_category")) if kind == "fund"
               else sub_for_other(r.get("name"), r.get("sub_category"), r.get("asset_class"), mcap))
        b = bands.get(sub) if sub else None
        if b is None:
            r["risk_sub"] = None
            r["risk_band"] = r["liq_band"] = None
            r["risk_score"] = r["days_to_cash"] = r["liq_priority"] = None
            gap += float(r.get("value_inr") or 0)
            continue
        r["risk_sub"] = sub
        r["risk_band"] = str(b["risk_band"]).strip()
        r["liq_band"] = str(b["liq_band"]).strip()
        r["risk_score"] = float(b["risk_score"])
        r["days_to_cash"] = float(b["days_to_cash"])
        p = b.get("liq_priority")
        r["liq_priority"] = None if pd.isna(p) else int(p)
        placed += 1
    return placed, gap


# The slide engine buckets a fund by a COARSE category string, and lib/lookthrough.py sorts those
# into equity, hybrid and debt. The kit used to hand every fund the literal string "equity", which
# is itself a member of _EQUITY_FUND_CATS, so every gilt, liquid and corporate-bond fund in a book
# counted as equity in the look-through. On this book that was Rs 36.9 crore, and it is why the
# equity share appeared as 82% on one page against a true 75.9% on another.
ENGINE_CATEGORY = {
    "Large Cap Fund": "large",
    "Large & Mid Cap Fund": "largemid",
    "Flexi Cap Fund": "flexi",
    "Focused Fund": "focused",
    "Mid Cap Fund": "mid",
    "Small Cap Fund": "small",
    "Thematic / Sectoral Fund": "thematic_mnc",
    "Factor / Smart Beta Fund": "passive",
    "Index Fund / ETF - Broad Market": "passive",
    "International Fund / FoF": "passive",
    "ELSS": "elss",
    "Arbitrage Fund": "hybrid",
    "Equity Savings Fund": "hybrid",
    "Balanced Advantage / Dynamic Asset Allocation": "hybrid",
    "Gold / Silver ETF or FoF": "passive",
    "Overnight Fund": "overnight",
    "Liquid Fund": "overnight",
    "Money Market / Ultra Short / Low Duration": "debt_short",
    "Short Duration / Banking & PSU Debt": "debt_short",
    "Corporate Bond Fund": "debt_short",
    "Credit Risk Fund": "debt",
    "Target Maturity Index Fund (G-Sec / SDL / PSU)": "debt_short",
    "Gilt Fund / Constant Maturity Gilt": "gilt",
    "Dynamic Bond Fund": "debt",
}


def engine_category(sub, asset_class=""):
    """The coarse category the slide engine buckets on, from the framework sub-category."""
    if sub in ENGINE_CATEGORY:
        return ENGINE_CATEGORY[sub]
    # Unknown scheme: fall back to the asset class the statement gave, never to "equity".
    c = (asset_class or "").strip().lower()
    return "debt" if c == "fixed income" else "hybrid" if c == "alternates" else "flexi"
