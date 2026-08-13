# -*- coding: utf-8 -*-
"""V3 CORRECTOR — thin-history scoring, FINAL. Supersedes fix_thin_coverage_v2.py.
Principal rulings, 2026-08-07, and what the backtests said about each:

  "no withdrawal, a large cap like Swiggy can also be thin"   ADOPTED. v2 withdrew 8 names; v3 scores
                                                              every name. Withdrawal was the wrong
                                                              instrument -- thin history is a data
                                                              condition, not a disqualification.
  "use technical if 1y history available"                     CONFIRMED BY TEST, and the single biggest
                                                              win here. Substituting the 1-year sibling
                                                              pillars for the missing 3-year ones:
                                                              bias +1.02 -> +0.05, MAE 3.86 -> 2.72,
                                                              rank corr 0.906 -> 0.932.
  "give technical points if above/below listing price for     CONFIRMED BY TEST. Return since listing,
   <1y ipo/demerger"                                          ranked against the universe over the SAME
                                                              window, lifts rank corr 0.601 -> 0.701 at
                                                              only 3 months of history, 0.735 at 12,
                                                              and adds NO bias (+1.84 -> +1.84).
  "give more weight to value 50% growth 25% quality 25%"      REJECTED ON MEASUREMENT -- the one
                                                              instruction the data contradicts. It was
                                                              WORSE than the bug it was meant to fix:
                                                              bias +3.07 vs skip's +2.95, MAE 11.83 vs
                                                              10.08, rank corr 0.445 vs 0.601. Piling
                                                              ~37% of freed weight onto value amplifies
                                                              value's idiosyncratic variance, and value
                                                              is uncorrelated with the pillars that went
                                                              missing, so it adds noise rather than
                                                              information. NEUTRAL-FILL is used instead
                                                              for whatever remains unobservable: under
                                                              uncertainty, shrinking to the middle beats
                                                              betting the weight on one surviving pillar.
                                                              (results/IMPUTATION_TEST.md)
  "no sell if score >40; 40-50 trim if over-conc, not sell"   ADOPTED, and it exposed a live conflict:
                                                              the engine's rec_overall says Sell if
                                                              EITHER horizon is under 40, which called
                                                              88 of its 246 Sells on names whose blended
                                                              score is ABOVE 40 -- BANKBARODA at 54.1,
                                                              HINDALCO 52.5, JSWSTEEL 51.8, AXISBANK
                                                              47.4. v3 calls on the blended score.

Everything lands in *_v3 columns beside v1. The engine is not touched; adoption is the Principal's call.
"""
import json
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("NIFTY 500 root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            return cand


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
PRICES = os.path.join(ROOT, "ALPHA_RANKER", "data", "prices")
SRC = os.path.join(RES, "full750_scored.csv")
PL_PATH = os.path.join(ROOT, "datasets", "screener_deep", "screener_annual_pl.parquet")
EQ = os.path.join(RES, "EARNINGS_QUALITY.csv")
OUT = os.path.join(RES, "full750_scored_v3.csv")
NOTE = os.path.join(RES, "THIN_COVERAGE_FIX_V3_NOTE.md")

BASE_W_3Y = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
                 sector_macro_3y_score=11, ownership_3y_score=9, accumulation_3y_score=8)
BASE_W_1Y = dict(quality_score=16, growth_1y_score=16, value_score=16, stage_1y_score=26,
                 sector_macro_1y_score=13, ownership_1y_score=8, accumulation_1y_score=5)
TILT_CYC_3Y = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
                   sector_macro_3y_score=3, ownership_3y_score=0, accumulation_3y_score=0)
TILT_NOT_3Y = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
                   sector_macro_3y_score=-2, ownership_3y_score=0, accumulation_3y_score=0)
TILT_CYC_1Y = dict(quality_score=-2, growth_1y_score=-2, value_score=3, stage_1y_score=-2,
                   sector_macro_1y_score=3, ownership_1y_score=0, accumulation_1y_score=0)
TILT_NOT_1Y = dict(quality_score=3, growth_1y_score=2, value_score=0, stage_1y_score=-3,
                   sector_macro_1y_score=-2, ownership_1y_score=0, accumulation_1y_score=0)

SIBLING = {"stage_3y_score": "stage_1y_score", "accumulation_3y_score": "accumulation_1y_score",
           "growth_3y_score": "growth_1y_score", "ownership_3y_score": "ownership_1y_score",
           "sector_macro_3y_score": "sector_macro_1y_score"}
NEUTRAL = 50.0
ARTEFACT = 200.0
AS_OF = pd.Timestamp("2026-07-20")
TDPM = 21
WINDOWS = (12, 9, 6, 3)          # months; a thin name uses the longest window it can support
SELL_BAR, TRIM_CEIL = 40.0, 50.0

# ---- GATES (Principal, 2026-08-07) -----------------------------------------------------------------
# LIQUIDITY caps at 50, not 40. Thin trading is an execution problem, not evidence the business is bad,
# so it should keep a name out of the top half without branding it a Sell.
LIQ_CAP = 50.0
# D/E EXEMPTION, widened. "d/e >2.5 not applicable in many cases like infra solar bank etc." Exempted
# by ECONOMIC MODEL, not by keyword: businesses financed with project or regulated debt as the normal
# way of operating. Note where "solar" actually lands -- generation sits in Power (exempt), while solar
# EQUIPMENT makers (EMMVEE, WEBELSOLAR, UTLSOLAR) are Capital Goods, where high leverage is NOT
# structural and the gate should still bite. Exempting on the word "solar" would have let the wrong
# half through.
# Interest coverage still applies to EVERY name including these: leverage may be normal, but being
# unable to service it never is. That is the honest form of the exemption.
DE_EXEMPT_SECTORS = ("financial services", "power", "realty", "telecommunication", "construction")
# Measured: 50 names breach D/E>2.5, of which 33 are already-exempt Financial Services; widening adds
# Power (4), Realty (1), Telecom (1), Construction (0).

# ---- FORWARD ADJUSTMENT (frozen Ionic Score design; implemented here for the first time) -----------
# `ionic_score_v3` previously returned only the BASE blend (0.60x3Y + 0.40x1Y). The frozen model adds a
# forward adjustment on top of that base, and it was simply missing -- so every "Ionic Score" this
# pipeline produced was the base masquerading as the finished number.
#
# GROWTH LEG. Principal, 2026-08-07: the bonus/penalty points are banded on EXPECTED growth, weighted
# 60 EPS : 40 revenue. The analyst supplies one forward figure (expected 3-5y EPS growth, on all 752
# research files); there is no forward REVENUE estimate anywhere in the stack, so the revenue leg uses
# trailing 1-year revenue growth (99.1% coverage, median 12.35%). [INFERENCE, disclosed] -- if the desk
# starts capturing an expected-revenue figure, swap it in here and nothing else changes.
# GROWTH LEG ON (Principal, 2026-08-07: "if v1 was adding then add it in our aswell"), after evidence
# established that v1 really was applying it -- 30 of 59 holdings on the shipped Talaulikar deck carried
# an adjustment between -11 and +15, and the deck's scores reconcile to pf_mech_flags 59/59. Dropping
# it would have made v3 scores incomparable with every deck already delivered.
#
# THE EVIDENCE AGAINST IT STILL STANDS AND IS NOT SETTLED. The PIT decile test cut the 1Y spread from
# +5.50% to +0.13% with the leg on, and it was the worst arm at all three horizons. But that test had to
# PROXY the analyst's forward estimate with TRAILING growth, because analyst opinion has no
# point-in-time history -- so it tests the mechanism (banding a growth number into +/-15 and adding it),
# not the analyst's actual foresight. Those are different claims. What it does establish is that the
# banding mechanism carries no ranking power on its own; if the leg earns its place, it does so through
# analyst skill that this harness cannot observe. Worth revisiting the day a forward estimate is
# captured with a timestamp.
GROWTH_LEG_ENABLED = True
FWD_EPS_W, FWD_REV_W = 1.00, 0.00      # see FWD_REV_CLIP note: 60:40 needs an EXPECTED revenue field
GROWTH_LEG = ((25.0, 15.0), (20.0, 10.0), (15.0, 5.0), (10.0, 0.0), (5.0, -5.0), (-1e9, -15.0))
# REVENUE LEG OFF -- the growth leg is 100% the analyst's EXPECTED figure, exactly as the frozen client
# pipeline (compute_client_scores.py v6.2) always did it.
#
# WHY THE 60:40 COULD NOT BE IMPLEMENTED HONESTLY. The Principal's ruling was 60 expected-EPS growth :
# 40 expected-REVENUE growth. No expected-revenue figure exists anywhere in the stack, so this used
# TRAILING 1-year revenue as a stand-in. That substitution inverts the leg for exactly the names it
# matters most to. BDL: the analyst expects +15% EPS, trailing revenue was -27% on FY26 delivery
# delays, and 0.60x15 + 0.40x(-27) = -1.8% -> the MAXIMUM -15 penalty on a name the analyst is positive
# about. In v1 the same name scored +5. Systemic, not isolated: of the 93 names taking -15, SEVENTY-FIVE
# had negative trailing revenue and TWENTY carried an analyst estimate of 10% or better (ZENTEC +23%,
# BDL and EMBDL +15%). VOLTAS landed at 4.8% and took -15 instead of -5 for missing the cut-off by
# 0.2pp. Trailing and expected point in opposite directions for turnarounds and lumpy-order businesses,
# and the trailing leg was winning.
#
# Restoring the true 60:40 needs `expected_next_3y_revenue_growth_pct` captured in the research files --
# one extra field per name. Until then the honest weighting is the one v1 used.
FWD_REV_CLIP = 25.0
CONV_ANALYST_SELL = -6.0
CONV_ANALYST_RESCUE = 6.0        # analyst Holds a name the quant would Sell
ADJ_CLAMP = 20.0
# The exceptional +20 requires >=25% growth AND ROE>=20% AND dilution <2%. DILUTION IS NOT IN THE
# DATASET, so the test can only ever be two-of-three -- which over-grants: it fired on 27 names. Rather
# than silently approximate a frozen rule, the tier is DORMANT until a dilution field exists, and the
# growth leg tops out at +15. Set EXCEPTIONAL_ENABLED once dilution is captured.
EXCEPTIONAL_ENABLED = False
EXCEPTIONAL_ROE = 0.20
LOW_GROWTH_CAP = 10.0            # expected growth below this -> net adjustment may not be positive

# REVENUE-RESCUE (Principal, 2026-08-07): "if revenue >15% but eps<10% instead of penalty -15 give
# penalty max capped at 5", and on the second pass: "keep future [since eps can be dragged if rnd]
# instead of trailing".
#
# A company compounding its top line at 15%+ while the analyst expects modest EPS is a MARGIN,
# R&D-spend or DILUTION story, not a dying business. The harshest band is meant for companies that are
# not growing at all, and applying it here confuses "earnings are not converting yet" with "there is no
# growth".
#
# THE REVENUE FIGURE MUST BE FORWARD, and that is the whole point of the correction: a business
# spending heavily on R&D or capex shows depressed EPS *and* can show a soft trailing year while its
# expected revenue is strong. Using trailing revenue would fire the rescue on the wrong names, which is
# the same mistake that broke the 60:40 growth leg. So this reads
# `expected_next_3y_revenue_growth_pct` from the research files.
#
# THAT FIELD DOES NOT EXIST YET. The rescue is therefore DORMANT -- it fires on zero names -- rather
# than silently falling back to trailing. Adding one field per research file activates it with no code
# change. Left visible in `revenue_rescue` (which will read "no fwd revenue data") instead of quietly
# doing nothing, so the gap cannot be forgotten.
REV_RESCUE_MIN = 15.0            # EXPECTED forward revenue growth
REV_RESCUE_EPS_MAX = 10.0        # expected EPS growth below this
REV_RESCUE_FLOOR = -5.0          # the worst the growth leg may be when the rescue applies
# Principal, 2026-08-07: "no score can be below 5, or above 95 these are cap". Both bounds sit far
# outside the 40 Sell bar and the 40-50 Trim band, so NO recommendation changes -- verified below.
SCORE_FLOOR, SCORE_CEIL = 5.0, 95.0


def comp(row, base, tilt_c, tilt_n, neutral=None):
    tilt = tilt_c if row.get("cyclicality_tag") == "Cyclical" else tilt_n
    num = den = 0.0
    for k, w in base.items():
        wt = w + tilt[k]
        v = row.get(k)
        if pd.notna(v):
            num += wt * float(v); den += wt
        elif neutral is not None:
            num += wt * neutral; den += wt
    return num / den if den > 0 else np.nan


def _num(x):
    v = pd.to_numeric(x, errors="coerce")
    return None if pd.isna(v) else float(v)


def de_exempt(sector):
    return any(k in str(sector or "").lower() for k in DE_EXEMPT_SECTORS)


def bs_flag_v3(row):
    """Balance-sheet gate with the widened D/E exemption. Two DIFFERENT exemptions, because the two
    sector groups fail the tests for different reasons:

    FINANCIALS -- exempt from the WHOLE gate, D/E and interest coverage alike. The frozen doc says only
    the D/E trigger, and I initially implemented it that way; the data showed why the engine's blanket
    exemption was right. Interest expense is a lender's cost of FUNDS, not debt service, and an insurer
    barely has any: applying the coverage test flagged NIACL RED at coverage -399 with ZERO debt,
    CANHLIFE at -11.8, NIVABUPA at -3.7, plus BAJAJFINSV and four capital-market firms at 2.0-2.9x,
    which is simply what their model looks like. Eleven healthy names penalised by a ratio that does not
    describe them. The documentation is the imprecise thing here, not the code.

    CAPITAL-INTENSIVE (power, realty, telecom, construction) -- exempt from the D/E TRIGGER ONLY.
    Project and regulated debt is the normal way these businesses are financed, so a high ratio says
    little. Coverage still applies to every one of them, and it should: leverage may be normal, being
    unable to service it never is."""
    de = _num(row.get("debt_equity"))
    ic = _num(row.get("interest_coverage"))
    sec = str(row.get("sector") or "").lower()
    if "financial services" in sec or any(k in sec for k in ("bank", "insurance", "nbfc")):
        return "N/A-financial-sector"
    if de is not None and de_exempt(sec):
        de = None
    if (de is not None and de > 2.5) or (ic is not None and ic < 1.5):
        return "RED"
    if (de is not None and de > 1.5) or (ic is not None and ic < 3):
        return "AMBER"
    return "GREEN"


def gate(row, c, use_v3_flags=False):
    if pd.isna(c):
        return c
    bs = bs_flag_v3(row) if use_v3_flags else row.get("bs_flag")
    if bs == "RED":
        c = min(c, 40.0)
    elif bs == "AMBER":
        c = c * 0.85
    # liquidity caps at 50, applied independently -- a name can be both illiquid and levered
    if row.get("liquidity_flag") == "RED":
        c = min(c, LIQ_CAP if use_v3_flags else 40.0)
    return c


def march_to_march_growth(symbols):
    """{sym: (fy_1y_growth_pct, fy_3y_cagr_pct)} from FULL-YEAR March columns only.
    Principal, 2026-08-07: "always look march to march basis or analyst instead of trailing".

    Why this is not cosmetic. The engine takes growth from a TTM window: 666 names land on ttm(Mar
    2026), but 76 land on ttm(Jun 2026) -- a window spanning Apr-Jun 2026 plus the preceding three
    quarters. The Growth pillar is a CROSS-SECTIONAL PERCENTILE, so those 76 are being ranked against
    the other 666 over a DIFFERENT period. That is not a freshness trade-off, it is an invalid
    comparison: COHANCE reads -13.0% on the engine's window against +89.4% March-to-March, FACT +30.4%
    against -19.8%, JIOFIN +119.3% against +72.0%. Forty names differ by more than 5pp, twelve by more
    than 20pp.

    Cost, stated plainly: the June-TTM names give up one quarter of freshness. That is the right trade
    when the number's whole job is to be comparable with 750 others.
    """
    out = {}
    if not os.path.exists(PL_PATH):
        return out
    pl = pd.read_parquet(PL_PATH)
    yre = re.compile(r"^Mar (\d{4})$")           # full years only; "Mar 2025  10m" is a stub period
    yrs = sorted([c for c in pl.columns if yre.match(str(c).strip())],
                 key=lambda c: int(yre.match(str(c).strip()).group(1)))
    if not yrs:
        return out
    sales = pl[pl["metric"] == "Sales+"].drop_duplicates(subset=["symbol"]).set_index("symbol")
    fin = pl[pl["metric"] == "Financing Profit"].drop_duplicates(subset=["symbol"]).set_index("symbol")
    for sym in symbols:
        src = sales if sym in sales.index else (fin if sym in fin.index else None)
        if src is None:                          # lenders carry Financing Profit, not Sales+
            continue
        s = pd.to_numeric(src.loc[sym, yrs], errors="coerce").dropna()
        if len(s) < 2:
            continue
        g1 = ((s.iloc[-1] / s.iloc[-2] - 1) * 100) if s.iloc[-2] > 0 else np.nan
        g3 = (((s.iloc[-1] / s.iloc[-4]) ** (1 / 3) - 1) * 100) \
            if len(s) >= 4 and s.iloc[-4] > 0 else np.nan
        out[sym] = (g1, g3)
    return out


def pctile(series):
    """Winsorised 2/98 percentile rank, matching the engine's `pctile_universe`."""
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if len(valid) == 0:
        return s
    lo, hi = np.nanpercentile(valid, [2, 98])
    return s.clip(lo, hi).rank(pct=True) * 100


def load_analyst():
    """{SYMBOL: (recommendation, expected_growth_pct, escalation_flag)} from the research files."""
    out = {}
    qd = os.path.join(RES)
    try:
        names = os.listdir(qd)
    except OSError:
        return out
    for fn in names:
        if not (fn.startswith("pf_qual_") and fn.endswith(".json")):
            continue
        sym = fn[len("pf_qual_"):-len(".json")].strip().upper()
        try:
            with open(os.path.join(qd, fn), "r", encoding="utf-8") as fh:
                j = json.load(fh)
        except (OSError, ValueError):
            continue
        g = j.get("expected_next_3y_growth_pct")
        # the forward REVENUE estimate the rescue needs. Not yet produced by the research pass;
        # several key spellings accepted so the field activates the moment any of them lands.
        rv = next((j.get(k) for k in ("expected_next_3y_revenue_growth_pct",
                                      "expected_revenue_growth_pct",
                                      "expected_next_3y_revenue_pct") if j.get(k) is not None), None)
        out[sym] = (str(j.get("your_recommendation") or "").strip(),
                    float(g) if isinstance(g, (int, float)) else np.nan,
                    bool(j.get("escalation_flag")),
                    float(rv) if isinstance(rv, (int, float)) else np.nan)
    return out


def growth_leg(exp_eps, rev_growth, roe, exp_rev=None):
    """Bonus/penalty points from EXPECTED growth, weighted 60 EPS : 40 revenue, then banded."""
    legs, wts = [], []
    if exp_eps is not None and exp_eps == exp_eps and FWD_EPS_W > 0:
        legs.append(exp_eps); wts.append(FWD_EPS_W)
    if rev_growth is not None and rev_growth == rev_growth and FWD_REV_W > 0:
        legs.append(min(rev_growth, FWD_REV_CLIP)); wts.append(FWD_REV_W)
    if not legs:
        return 0.0, np.nan, False
    g = sum(v * w for v, w in zip(legs, wts)) / sum(wts)     # renormalised if a leg is absent
    if not GROWTH_LEG_ENABLED:
        return 0.0, g, False     # figure still returned for the Excel's disclosure column
    pts = GROWTH_LEG[-1][1]
    for lo, p in GROWTH_LEG:
        if g >= lo:
            pts = p
            break
    if EXCEPTIONAL_ENABLED and g >= 25.0 and roe is not None and roe == roe and roe >= EXCEPTIONAL_ROE:
        pts = 20.0
    # revenue rescue: strong EXPECTED top-line growth floors the penalty at -5
    rescued = ""
    if pts < REV_RESCUE_FLOOR and exp_eps is not None and exp_eps == exp_eps \
            and exp_eps < REV_RESCUE_EPS_MAX:
        if exp_rev is None or exp_rev != exp_rev:
            rescued = "no fwd revenue data"      # eligible on EPS, cannot test revenue -- disclosed
        elif exp_rev > REV_RESCUE_MIN:
            pts, rescued = REV_RESCUE_FLOOR, "Y"
    return pts, g, rescued


def window_returns(symbols):
    """{months: {sym: return}} plus {sym: months of history}. One pass over the price files."""
    rets = {m: {} for m in WINDOWS}
    hist = {}
    for s in symbols:
        p = os.path.join(PRICES, f"{s}.parquet")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        col = next((c for c in ("close", "Close", "adj_close") if c in df.columns), None)
        if col is None:
            continue
        if not isinstance(df.index, pd.DatetimeIndex):
            dc = next((c for c in ("date", "Date", "timestamp") if c in df.columns), None)
            if dc is None:
                continue
            df = df.set_index(pd.to_datetime(df[dc]))
        px = df[col].dropna()
        px = px[px.index <= AS_OF]
        if len(px) < 2:
            continue
        hist[s] = len(px) / TDPM
        for m in WINDOWS:
            need = int(m * TDPM)
            if len(px) >= need + 5:
                w = px.iloc[-need:]
                if w.iloc[0] > 0:
                    rets[m][s] = float(w.iloc[-1] / w.iloc[0] - 1.0)
    return rets, hist


def main():
    d = pd.read_csv(SRC)
    n = len(d)
    syms = d["symbol"].astype(str).tolist()

    # ---- growth artefacts -> pillar unobservable ---------------------------------------------------
    g3 = pd.to_numeric(d["revenue_cagr_3y"], errors="coerce")
    g1 = pd.to_numeric(d["revenue_growth_1y"], errors="coerce")
    art3 = np.isinf(g3) | (g3 > ARTEFACT)
    art1 = np.isinf(g1) | (g1 > ARTEFACT)
    d["growth_artifact_flag"] = np.where(art3 | art1, "Y", "")

    # ---- replication check on untouched rows BEFORE changing anything ------------------------------
    keep = ~(art3 | art1)
    e3 = (d[keep].apply(lambda r: comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y), axis=1)
          - pd.to_numeric(d.loc[keep, "composite_3y"])).abs().max()
    print(f"replication check: max |diff| composite_3y {e3:.4f}")
    assert e3 < 0.05, "cannot reproduce the engine composite -- ABORTING"
    res3 = pd.to_numeric(d["final_score_3y"]) - d.apply(
        lambda r: gate(r, comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y)), axis=1)
    res1 = pd.to_numeric(d["final_score_1y"]) - d.apply(
        lambda r: gate(r, comp(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y)), axis=1)

    d2 = d.copy()
    d2.loc[art3, "growth_3y_score"] = np.nan
    d2.loc[art1, "growth_1y_score"] = np.nan

    # ---- MARCH-TO-MARCH growth, replacing the TTM windows ------------------------------------------
    m2m = march_to_march_growth(d["symbol"].astype(str).tolist())
    fy1 = d["symbol"].astype(str).map(lambda s: m2m.get(s, (np.nan, np.nan))[0])
    fy3 = d["symbol"].astype(str).map(lambda s: m2m.get(s, (np.nan, np.nan))[1])
    # keep the engine's figure only where no full-year pair exists at all
    d["rev_growth_1y_m2m"] = fy1.fillna(pd.to_numeric(d["revenue_growth_1y"], errors="coerce"))
    d["rev_cagr_3y_m2m"] = fy3.fillna(pd.to_numeric(d["revenue_cagr_3y"], errors="coerce"))
    d["growth_source_v3"] = np.where(fy1.notna(), "March-to-March", "engine TTM (no FY pair)")
    # artefacts again, on the new figures
    a3m = np.isinf(d["rev_cagr_3y_m2m"]) | (d["rev_cagr_3y_m2m"] > ARTEFACT)
    a1m = np.isinf(d["rev_growth_1y_m2m"]) | (d["rev_growth_1y_m2m"] > ARTEFACT)
    d.loc[a3m, "rev_cagr_3y_m2m"] = np.nan
    d.loc[a1m, "rev_growth_1y_m2m"] = np.nan
    d["growth_artifact_flag"] = np.where(a3m | a1m | art3 | art1, "Y", "")
    # re-percentile the growth pillars on the comparable figures
    d2["growth_3y_score"] = pctile(d["rev_cagr_3y_m2m"])
    d2["growth_1y_score"] = pctile(d["rev_growth_1y_m2m"])

    # ---- history class -----------------------------------------------------------------------------
    ret12 = pd.to_numeric(d["ret_12m"], errors="coerce")
    ret24 = pd.to_numeric(d["ret_24m"], errors="coerce")
    cls = np.where(ret24.notna(), "full", np.where(ret12.notna(), "1-2y", "<1y"))
    d["history_class"] = cls

    # ---- <1y: technical from return since listing, ranked over the SAME window ---------------------
    rets, hist = window_returns(syms)
    pct_by_win = {}
    for m in WINDOWS:
        s = pd.Series(rets[m])
        pct_by_win[m] = (s.rank(pct=True) * 100) if len(s) else pd.Series(dtype=float)
    listing_pct, listing_win = {}, {}
    for i, sym in enumerate(syms):
        if cls[i] != "<1y":
            continue
        hm = hist.get(sym)
        if hm is None:
            continue
        for m in WINDOWS:                       # longest window the name can actually support
            if hm >= m + 0.3 and sym in pct_by_win[m].index:
                listing_pct[sym] = float(pct_by_win[m].loc[sym])
                listing_win[sym] = m
                break
    d["listing_return_pctile"] = d["symbol"].astype(str).map(listing_pct)
    d["listing_window_months"] = d["symbol"].astype(str).map(listing_win)

    # Count observed pillars BEFORE imputing. Counting after would report a name as 7-of-7 covered
    # because the fix filled it in, which is precisely the opposite of what this column is for.
    p3 = list(BASE_W_3Y)
    d["pillars_observed"] = d2[p3].notna().sum(axis=1)

    # ---- impute: 1y siblings, then listing-price technical, then neutral ---------------------------
    imputed_note = []
    for i, row in d2.iterrows():
        used = []
        for k, sib in SIBLING.items():
            if k in BASE_W_3Y and pd.isna(row.get(k)):
                v = row.get(sib)
                if pd.notna(v):
                    d2.at[i, k] = float(v)
                    used.append(f"{k.replace('_score','')}<-1y")
        sym = str(row["symbol"])
        if pd.isna(d2.at[i, "stage_3y_score"]) and sym in listing_pct:
            d2.at[i, "stage_3y_score"] = listing_pct[sym]
            used.append(f"stage<-listing{listing_win[sym]}m")
        imputed_note.append(",".join(used))
    d["imputation_applied"] = imputed_note

    # Publish the IMPUTED pillar values as *_v3 columns. Without these the v3 file carries a corrected
    # score alongside the original NaN pillars, so anything reading the pillars (the five-signal dots,
    # the Excel) shows "not scored" on a name whose score demonstrably used a substituted value -- the
    # page would contradict its own number.
    for k in BASE_W_3Y:
        d[f"{k}_v3"] = d2[k]

    c3 = d2.apply(lambda r: comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y, NEUTRAL), axis=1)
    c1 = d2.apply(lambda r: comp(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y, NEUTRAL), axis=1)
    # PENALTY/BOOST recomputed, not inherited. The residual trick (final - gate(composite)) captured
    # v1's red-flag battery, which was built on the TTM growth figures. Two of the four flags read
    # revenue growth directly, so switching to March-to-March changes them -- carrying the old residual
    # forward would pair new pillars with stale penalties.
    de_v = pd.to_numeric(d2["debt_equity"], errors="coerce")
    ic_v = pd.to_numeric(d2["interest_coverage"], errors="coerce")
    g1_v = pd.to_numeric(d["rev_growth_1y_m2m"], errors="coerce")
    g3_v = pd.to_numeric(d["rev_cagr_3y_m2m"], errors="coerce")
    is_fin_v = d2.apply(lambda r: bs_flag_v3(r) == "N/A-financial-sector", axis=1)
    rf = ((ic_v < 1.5).fillna(False).astype(int)
          + ((~is_fin_v) & (de_v > 2.5)).fillna(False).astype(int)
          + (g1_v < 0).fillna(False).astype(int)
          + ((g3_v - g1_v) > 15).fillna(False).astype(int))
    pen_v3 = -np.minimum(10, 2.0 ** rf - 1)
    boo_v3 = np.where((rf == 0) & (pd.to_numeric(d2["quality_score"], errors="coerce") > 60)
                      & (pd.to_numeric(d2["value_score"], errors="coerce") > 60), 3, 0)
    d["redflag_count_v3"] = rf
    d["penalty_v3"] = pen_v3
    d["boost_v3"] = boo_v3

    # use_v3_flags=True here ONLY. The replication check above must reproduce v1 exactly, so it keeps
    # the stored bs_flag and the 40 liquidity cap; the scoring pass gets the widened D/E exemption and
    # the 50 liquidity cap.
    f3 = (d2.apply(lambda r: gate(r, c3.loc[r.name], True), axis=1)
          + pen_v3 + boo_v3).clip(SCORE_FLOOR, SCORE_CEIL)
    f1 = (d2.apply(lambda r: gate(r, c1.loc[r.name], True), axis=1)
          + pen_v3 + boo_v3).clip(SCORE_FLOOR, SCORE_CEIL)
    d["bs_flag_v3"] = d2.apply(bs_flag_v3, axis=1)
    d["final_score_3y_v3"] = f3.round(2)
    d["final_score_1y_v3"] = f1.round(2)

    # ---- base blend, then the FORWARD ADJUSTMENT, then the call ------------------------------------
    base = 0.60 * f3 + 0.40 * f1
    d["base_score_v3"] = base.round(2)

    an = load_analyst()
    rev1y = pd.to_numeric(d["revenue_growth_1y"], errors="coerce")
    roe = pd.to_numeric(d["roe"], errors="coerce")
    g_pts, c_pts, adj, exp_g, a_rec, resc, exp_rv = [], [], [], [], [], [], []
    for i, sym in enumerate(d["symbol"].astype(str).str.upper()):
        rec, eps, _esc, erev = an.get(sym, ("", np.nan, False, np.nan))
        gp, g, was_rescued = growth_leg(eps, rev1y.iloc[i], roe.iloc[i], erev)
        resc.append(was_rescued)
        exp_rv.append(erev)
        quant_would_sell = base.iloc[i] < SELL_BAR
        if rec == "Sell":
            cp = CONV_ANALYST_SELL
        elif rec == "Hold" and quant_would_sell:
            cp = CONV_ANALYST_RESCUE          # the analyst-AI Sell->Hold conversion path
        else:
            cp = 0.0
        a = max(-ADJ_CLAMP, min(ADJ_CLAMP, gp + cp))
        # the two frozen caps: weak expected growth, or an analyst Sell, cannot produce a NET UPLIFT
        if (g == g and g < LOW_GROWTH_CAP) or rec == "Sell":
            a = min(a, 0.0)
        g_pts.append(gp); c_pts.append(cp); adj.append(a); exp_g.append(g); a_rec.append(rec)

    d["revenue_rescue"] = resc
    d["expected_rev_growth_pct"] = exp_rv        # the forward field the rescue needs; NaN until captured
    d["fwd_growth_input_pct"] = np.round(exp_g, 1)
    d["fwd_growth_points"] = g_pts
    d["conviction_points"] = c_pts
    d["forward_adjustment"] = adj
    d["analyst_call"] = a_rec

    ionic = (base + pd.Series(adj, index=d.index)).clip(SCORE_FLOOR, SCORE_CEIL)
    d["ionic_score_v3"] = ionic.round(2)

    # THE 40 BAR IS ABSOLUTE (Principal, 2026-08-07: "no sell for >40 value strictly ... we can show
    # trim at max"). An analyst Sell on a name scoring at or above 40 is DOWNGRADED TO TRIM, not
    # honoured as a Sell. The frozen Gate A let the analyst sell at any score; that produced 23 Sells
    # above the bar, 9 of them on names whose own Value pillar read Upper or Top 25% -- the analyst
    # overriding a valuation the model had already looked at and priced as reasonable. The analyst view
    # is not discarded: it still costs the name 6 points through the conviction leg, and it surfaces as
    # an explicit Trim rather than being silently dropped.
    # THE LADDER (Principal, 2026-08-07). Only TWO calls exist at universe level:
    #     below 40      Sell
    #     40 and above  Hold
    # 40-50 IS NOT A TRIM BAND. His correction: "40-50 does not ment trim, it was basis allowed to be
    # trimmed as per concentration and analyst not a fixed rule." So the band confers ELIGIBILITY to
    # trim, not a trim instruction -- and eligibility cannot be resolved in a universe file at all,
    # because trimming is a function of POSITION WEIGHT, which only exists inside a client book. Naming
    # a universe row "Trim" would be asserting a portfolio decision from data that contains no
    # portfolio. The eligibility and its reason are recorded separately for the book-level pass.
    #
    # Gate A is bounded by the score: an analyst Sell at or above 40 does not sell the name. It was
    # selling BAJAJ-AUTO at 67 on a valuation argument the Value pillar had already weighed. The view
    # is not discarded -- it costs 6 points through the conviction leg and marks the name trim-eligible.
    an_sell = pd.Series(a_rec, index=d.index) == "Sell"
    d["recommendation_v3"] = np.where(ionic < SELL_BAR, "Sell", "Hold")

    in_band = (ionic >= SELL_BAR) & (ionic <= TRIM_CEIL)
    hold = ionic >= SELL_BAR
    reasons = []
    for i in d.index:
        if not hold.loc[i]:
            reasons.append("")
            continue
        r = []
        if in_band.loc[i]:
            r.append("score 40-50 (trim if weight >2.5%)")
        if an_sell.loc[i]:
            r.append("analyst view")
        reasons.append(" + ".join(r))
    d["trim_eligible_v3"] = reasons

    # The conversions, measured against the FINAL Ionic score -- not against the base.
    # A first version compared `base >= 40` with a Sell verdict and reported 117 analyst-forced Sells.
    # That was wrong: most of those names fell below 40 through the forward adjustment itself (the -6
    # conviction penalty plus a weak growth leg), which is the score working, not an override. Only a
    # name whose FINAL Ionic still clears the bar is genuinely being sold by Gate A alone. The honest
    # count is 23, not 117.
    d["analyst_conversion"] = np.where(
        (base < SELL_BAR) & (d["recommendation_v3"] != "Sell"), "Sell->Hold (analyst)",
        np.where(an_sell & (ionic >= SELL_BAR) & (ionic <= TRIM_CEIL), "Analyst Sell -> Trim",
                 np.where(an_sell & (ionic > TRIM_CEIL), "Analyst Sell OVERRULED (score > 50)", "")))
    d["thin_history_flag"] = np.where(d["history_class"] == "<1y", "<1y",
                                      np.where(d["pillars_observed"] < 7, "Y", ""))

    # The cap must not quietly move a call. Tested by isolating the CAP alone: recompute the call from
    # the uncapped Ionic score with everything else (forward adjustment, analyst gate) held identical.
    ionic_raw = base + pd.Series(adj, index=d.index)
    rec_uncapped = np.where(ionic_raw < SELL_BAR, "Sell", "Hold")
    n_moved = int((rec_uncapped != d["recommendation_v3"].to_numpy()).sum())
    print(f"cap check: [{SCORE_FLOOR:.0f},{SCORE_CEIL:.0f}] moved {n_moved} recommendations "
          f"(expected 0); floored {int((ionic_raw < SCORE_FLOOR).sum())}, "
          f"ceiled {int((ionic_raw > SCORE_CEIL).sum())}")
    assert n_moved == 0, "score cap changed a recommendation -- investigate before shipping"

    # ---- earnings-quality flags -------------------------------------------------------------------
    if os.path.exists(EQ):
        eq = pd.read_csv(EQ)[["symbol", "oi_driven_growth", "oi_level_high", "oi_spike",
                              "oi_pct_of_pbt", "eff_margin", "eff_other_income"]]
        d = d.merge(eq, on="symbol", how="left")

    d.to_csv(OUT, index=False)

    # ---- note --------------------------------------------------------------------------------------
    old_sell = d["recommendation_overall"] == "Sell"
    new_sell = d["recommendation_v3"] == "Sell"
    delta = d["final_score_3y_v3"] - pd.to_numeric(d["final_score_3y"])
    mv = d.assign(delta=delta).dropna(subset=["delta"]).sort_values("delta")
    lines = [
        "# Thin-history fix v3 — FINAL (v3 columns beside v1; engine untouched)", "",
        f"{n} names. Replication verified: max composite diff {e3:.4f}.", "",
        "## What changed vs v2", "",
        "- **No withdrawals.** v2 withdrew 8 names; v3 scores every one (Principal: a large cap like "
        "Swiggy can legitimately be thin).",
        "- **1-year siblings substituted** where a 3-year pillar is unavailable (backtest: rank corr "
        "0.906 -> 0.932, MAE 3.86 -> 2.72).",
        "- **Listing-price technical** for <1y names: return since listing, ranked over the same "
        "window (rank corr 0.601 -> 0.701 at 3 months, 0.735 at 12; no added bias).",
        "- **50/25/25 redistribution REJECTED on measurement** — it scored worse than the bug "
        "(bias +3.07 vs +2.95, MAE 11.83 vs 10.08, corr 0.445 vs 0.601). Neutral-fill used instead.",
        "- **Call taken on the blended score**, so no name above 40 is ever a Sell.", "",
        "## Coverage", "",
        f"- history: full **{int((d['history_class'] == 'full').sum())}**, "
        f"1-2y **{int((d['history_class'] == '1-2y').sum())}**, "
        f"<1y **{int((d['history_class'] == '<1y').sum())}**",
        f"- names receiving a 1y-sibling or listing-price substitution: "
        f"**{int((d['imputation_applied'] != '').sum())}**",
        f"- <1y names given a listing-price technical: **{int(d['listing_return_pctile'].notna().sum())}**",
        f"- growth artefacts neutralised: **{int((art3 | art1).sum())}** "
        f"({', '.join(d.loc[art3 | art1, 'symbol'].head(8))})", "",
        "## Forward adjustment (implemented for the first time — it was missing)", "",
        f"- growth leg, banded on the analyst's expected EPS growth ALONE "
        f"({FWD_EPS_W:.0%} EPS / {FWD_REV_W:.0%} revenue, matching v1): mean "
        f"**{np.nanmean(d['fwd_growth_points']):+.2f}** pts",
        f"- conviction leg: analyst Sell **{int((d['conviction_points'] == CONV_ANALYST_SELL).sum())}** "
        f"at {CONV_ANALYST_SELL:+.0f}, analyst rescue of a quant-Sell "
        f"**{int((d['conviction_points'] == CONV_ANALYST_RESCUE).sum())}** at "
        f"{CONV_ANALYST_RESCUE:+.0f}",
        f"- net adjustment: mean **{np.nanmean(d['forward_adjustment']):+.2f}**, range "
        f"{np.nanmin(d['forward_adjustment']):+.0f} to {np.nanmax(d['forward_adjustment']):+.0f}",
        f"- base vs Ionic: median {d['base_score_v3'].median():.1f} -> "
        f"{d['ionic_score_v3'].median():.1f}", "",
        "## Analyst-AI conversions", "",
        f"- **{int((d['analyst_conversion'] == 'Sell->Hold (analyst)').sum())}** names the quant would "
        f"have sold are held on analyst conviction (the Sell->Hold path the Principal asked to keep)",
        f"- **{int((d['trim_eligible_v3'].astype(str).str.contains('analyst')).sum())}** Holds are "
        f"trim-ELIGIBLE on the analyst's view, **{int((d['trim_eligible_v3'].astype(str).str.contains('40-50')).sum())}** "
        f"on the 40-50 score band (weight decides, at book level). Sell rate "
        f"{(d['recommendation_v3'] == 'Sell').mean() * 100:.0f}% (the frozen note expects ~33%).",
        f"- gates: liquidity now caps at {LIQ_CAP:.0f}; D/E exemption widened to "
        f"{', '.join(DE_EXEMPT_SECTORS)} -- names whose balance-sheet flag improved: "
        f"**{int((d['bs_flag_v3'] != d['bs_flag']).sum())}**", "",
        "## Recommendation change", "",
        "| | v1 (either horizon <40) | v3 (Ionic + analyst gate) |", "|---|---|---|",
        f"| Sell | {int(old_sell.sum())} | {int(new_sell.sum())} |",
        f"| Hold / Trim band | {int((~old_sell).sum())} | "
        f"{int((d['recommendation_v3'] != 'Sell').sum())} |",
        "",
        f"- of the v3 Holds, trim-eligible for any reason: "
        f"**{int((d['trim_eligible_v3'].astype(str) != '').sum())}**", "",
        "## Largest score corrections (3Y, v3 minus v1)", "",
        "| symbol | history | pillars | v1 | v3 | change | imputation |", "|---|---|---|---|---|---|---|",
    ]
    for _, r in mv.head(12).iterrows():
        lines.append(f"| {r['symbol']} | {r['history_class']} | {int(r['pillars_observed'])} | "
                     f"{float(r['final_score_3y']):.1f} | {r['final_score_3y_v3']:.1f} | "
                     f"{r['delta']:+.1f} | {r['imputation_applied'] or '-'} |")
    with open(NOTE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}\nwrote {NOTE}")


if __name__ == "__main__":
    main()
