"""
build_full750_quant.py — FULL Nifty-750 quant score, v7 TTM amendment (Principal-directed
2026-07-21: "amend score to TTM" so the score reflects just-reported Q1 FY27 quarters).

Method: recompute raw metrics for EVERY name in symbols_750.txt from the refreshed screener_deep
(annual PL/BS/CF) + the NEW screener_quarterly_results.parquet + prices + shareholding, for one
consistent vintage, then run the frozen scoring engine ONCE over the 751-name universe.

TTM AMENDMENT (v7) — the ONLY change vs the frozen annual engine, deliberately minimal + audited:
  * revenue_growth_1y  -> TTM revenue YoY  (sum last 4 quarters / sum prior 4 quarters - 1)
  * pe_current         -> price / TTM EPS  (sum last 4 quarters' EPS)
  TTM-preferred, ANNUAL-FALLBACK: if a name lacks >=8 quarters (recent listing / no quarterly),
  the field falls back to the frozen annual computation, so no name loses its signal.
  Everything else (ROE/ROCE quality, D/E, interest-cov, 3y revenue CAGR, PB, FCF-yield,
  technicals, ownership, all pillar weights/gates/penalty) is UNCHANGED from the frozen engine
  (through-cycle by design). run_engine (pillar ranking) is reused verbatim.

Plus the STALENESS GUARD: any name whose latest annual P&L year < STALE_CUTOFF has fundamentals
nulled (honest Med/Low coverage) rather than scored on stale numbers.

NOTE: this AMENDS a frozen methodology (FROZEN_METHODOLOGY v6.3). Logged as a decision; flag for
quant-head (Arjun) + red-team (Nikhil) validation before it becomes the permanent frozen v7.
It also breaks strict comparability with the V0 annual-scored track record (documented).

Run (AFTER promote_screener_staging.py --promote):
  set PYTHONIOENCODING=utf-8
  <py> build_full750_quant.py
"""
import importlib.util
import os
import re
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SCORECARD = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750")
RESULTS = os.path.join(SCORECARD, "results")
DATASETS = os.path.join(ROOT, "datasets")
UNI = os.path.join(ROOT, "ALPHA_RANKER", "data", "universe", "symbols_750.txt")
ENGINE_PATH = os.path.join(ROOT, "Shreyas_Ionic_AMC", "05_DATA_OFFICE", "scripts", "score_n100_quant.py")
QTR_PATH = os.path.join(DATASETS, "screener_deep", "screener_quarterly_results.parquet")

STALE_CUTOFF = 2025
FUND_COLS = ["roe", "roce", "debt_equity", "interest_coverage", "revenue_cagr_3y",
             "revenue_growth_1y", "pe_current", "pb_current", "fcf_yield",
             "book_value_per_share", "avg_fcf"]
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
PERIOD_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}")

spec = importlib.util.spec_from_file_location("scn100", ENGINE_PATH)
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def _period_key(c):
    mo = c[:3]
    yr = int(re.search(r"\d{4}", c).group(0))
    return (yr, _MONTHS.get(mo, 0))


def latest_fundamental_year(pl, sym):
    mcp = E._mar_cols(pl)
    best = None
    for metric in ("Net Profit+", "Sales+", "Revenue+"):
        s = E._series(pl, sym, metric, mcp)
        nn = s.dropna()
        if len(nn):
            yr = max(int(c.split()[1]) for c in nn.index)
            best = yr if best is None else max(best, yr)
    return best


def ttm_series(qtr, sym, metric_candidates):
    """Return (ttm, prior_ttm, n_quarters, latest_quarter_label) from quarterly data. TTM = sum of
    the last 4 quarters; prior_ttm = the 4 before that. None where not computable."""
    if qtr is None:
        return None, None, 0, None
    q = qtr[qtr["symbol"] == sym]
    if q.empty:
        return None, None, 0, None
    row = None
    for m in metric_candidates:
        r = q[q["metric"] == m]
        if len(r):
            row = r.iloc[0]
            break
    if row is None:
        return None, None, 0, None
    qcols = sorted([c for c in qtr.columns if c not in ("symbol", "metric") and PERIOD_RE.match(str(c))],
                   key=_period_key)
    vals = [(c, E._clean_num(row[c])) for c in qcols]
    vals = [(c, v) for c, v in vals if pd.notna(v)]
    if len(vals) < 4:
        return None, None, len(vals), (vals[-1][0] if vals else None)
    ttm = sum(v for _, v in vals[-4:])
    prior = sum(v for _, v in vals[-8:-4]) if len(vals) >= 8 else None
    return ttm, prior, len(vals), vals[-1][0]


def compute_fundamentals_ttm(sym, pl, bs, cf, qtr, cyclicality_tag, notes):
    """Frozen annual fundamentals, with revenue_growth_1y and latest_eps overridden to TTM where
    the quarterly data supports it (>=8 q for growth, >=4 q for EPS)."""
    fund = E.compute_fundamentals(sym, pl, bs, cf, cyclicality_tag, notes)
    used = {"growth_1y": "annual", "eps": "annual"}
    # TTM revenue YoY
    ttm_rev, prior_rev, nq, latest_q = ttm_series(qtr, sym, ["Sales+", "Revenue+"])
    if ttm_rev is not None and prior_rev not in (None, 0):
        fund["revenue_growth_1y"] = (ttm_rev / prior_rev - 1) * 100
        used["growth_1y"] = f"ttm({latest_q})"
    # TTM EPS
    ttm_eps, _, neps, _ = ttm_series(qtr, sym, ["EPS in Rs"])
    if ttm_eps is not None and neps >= 4:
        fund["latest_eps"] = ttm_eps
        used["eps"] = f"ttm({latest_q})"
    fund["_ttm_used"] = used
    fund["_latest_qtr"] = latest_q
    return fund


def build_raw_ttm(symbols, pl, bs, cf, qtr, sc, sector_map, notes):
    rows = []
    for sym in symbols:
        sm = sector_map[sector_map["symbol"] == sym]
        sector = sm["macro_sector"].iloc[0] if len(sm) else "Unknown"
        sector_norm = str(sector).strip().lower()
        cyc = E.SECTOR_CYCLICALITY.get(sector_norm, "NotCyclical")
        try:
            fund = compute_fundamentals_ttm(sym, pl, bs, cf, qtr, cyc, notes)
        except Exception as e:
            notes.append(f"{sym}: fundamentals error {type(e).__name__}: {str(e)[:80]} — fundamentals NaN.")
            fund = dict(roe=np.nan, roce=np.nan, debt_equity=np.nan, interest_coverage=np.nan,
                        revenue_cagr_3y=np.nan, revenue_growth_1y=np.nan, shares_cr=np.nan,
                        book_value_per_share=np.nan, avg_fcf=np.nan, latest_eps=np.nan,
                        _ttm_used={"growth_1y": "none", "eps": "none"}, _latest_qtr=None)
        try:
            tech = E.compute_technicals(sym, notes)
        except Exception as e:
            notes.append(f"{sym}: NO PRICE DATA ({type(e).__name__}) — technicals NaN.")
            tech = dict(last_close=np.nan, ret_3m=np.nan, ret_6m=np.nan, ret_12m=np.nan, ret_24m=np.nan,
                        above_50sma=np.nan, above_200sma=np.nan, rsi14=np.nan, obv_slope_short=np.nan,
                        obv_slope_long=np.nan, turnover_median_60d=np.nan)
        own = E.compute_ownership(sym, sc, notes)

        shares_cr = fund["shares_cr"]
        last_close = tech["last_close"]
        mcap = last_close * shares_cr if shares_cr and not pd.isna(shares_cr) and not pd.isna(last_close) else np.nan
        eps = fund["latest_eps"]
        pe = last_close / eps if eps and not pd.isna(eps) and eps != 0 and not pd.isna(last_close) else np.nan
        bvps = fund["book_value_per_share"]
        pb = last_close / bvps if bvps and not pd.isna(bvps) and bvps != 0 and not pd.isna(last_close) else np.nan
        fcfy = fund["avg_fcf"] / mcap if mcap and not pd.isna(mcap) and mcap != 0 else np.nan

        rows.append(dict(
            symbol=sym, sector=sector, sector_norm=sector_norm, cyclicality_tag=cyc,
            market_cap_approx=mcap, roe=fund["roe"], roce=fund["roce"],
            debt_equity=fund["debt_equity"], interest_coverage=fund["interest_coverage"],
            revenue_cagr_3y=fund["revenue_cagr_3y"], revenue_growth_1y=fund["revenue_growth_1y"],
            pe_current=pe, pb_current=pb, book_value_per_share=bvps, avg_fcf=fund["avg_fcf"],
            fcf_yield=fcfy, ret_3m=tech["ret_3m"], ret_6m=tech["ret_6m"], ret_12m=tech["ret_12m"],
            ret_24m=tech["ret_24m"], above_50sma=tech["above_50sma"], above_200sma=tech["above_200sma"],
            rsi14=tech["rsi14"], obv_slope_short=tech["obv_slope_short"], obv_slope_long=tech["obv_slope_long"],
            turnover_median_60d=tech["turnover_median_60d"],
            ownership_flow_long=own["ownership_flow_long"], ownership_flow_short=own["ownership_flow_short"],
            ttm_growth=fund["_ttm_used"]["growth_1y"], ttm_eps_src=fund["_ttm_used"]["eps"],
            latest_qtr=fund["_latest_qtr"],
        ))
    return pd.DataFrame(rows)


def rec_overall(r3, r1):
    if r3 == "No Recommendation" and r1 == "No Recommendation":
        return "No Recommendation"
    if r3 == "Sell" or r1 == "Sell":
        return "Sell"
    return "Hold"


def main():
    notes = []
    uni = list(dict.fromkeys(l.strip() for l in open(UNI, encoding="utf-8") if l.strip()))
    print(f"universe: {len(uni)} names")

    print("Loading data sources...")
    sector_map = pd.read_parquet(E.SECTOR_MAP_PATH)
    pl, bs, cf = E.load_screener()
    qtr = pd.read_parquet(QTR_PATH) if os.path.exists(QTR_PATH) else None
    sc = pd.read_parquet(os.path.join(DATASETS, "derived", "shareholding_changes.parquet"))
    scr = set(pl["symbol"].astype(str))
    qsyms = set(qtr["symbol"].astype(str)) if qtr is not None else set()
    print(f"  screener annual: {len(scr & set(uni))}/{len(uni)} present | quarterly: {len(qsyms & set(uni))}/{len(uni)} present")

    print("Computing raw metrics (TTM growth/EPS where quarterly supports it)...")
    raw = build_raw_ttm(uni, pl, bs, cf, qtr, sc, sector_map, notes)
    print(f"  raw computed for {raw.shape[0]} names")
    print(f"  growth_1y source: {raw['ttm_growth'].apply(lambda s: s.split('(')[0]).value_counts().to_dict()}")
    print(f"  pe EPS source   : {raw['ttm_eps_src'].apply(lambda s: s.split('(')[0]).value_counts().to_dict()}")

    stale, zero = [], []
    for i, row in raw.iterrows():
        sym = row["symbol"]
        yr = latest_fundamental_year(pl, sym)
        if yr is None:
            zero.append(sym)
            notes.append(f"{sym}: ZERO screener fundamental coverage — fundamentals NaN.")
        elif yr < STALE_CUTOFF:
            stale.append((sym, yr))
            for c in FUND_COLS:
                if c in raw.columns:
                    raw.at[i, c] = np.nan
            notes.append(f"{sym}: STALE (latest FY Mar-{yr} < {STALE_CUTOFF}) — fundamentals nulled.")

    ref_cols = ["symbol", "sector", "sector_norm", "cyclicality_tag", "market_cap_approx",
                "roe", "roce", "debt_equity", "interest_coverage", "revenue_cagr_3y",
                "revenue_growth_1y", "pe_current", "pb_current", "fcf_yield",
                "ret_3m", "ret_6m", "ret_12m", "ret_24m", "above_50sma", "above_200sma",
                "rsi14", "obv_slope_short", "obv_slope_long", "turnover_median_60d",
                "ownership_flow_long", "ownership_flow_short"]
    union = raw[ref_cols].copy()
    union["is_new"] = True
    assert union["symbol"].is_unique, "dup symbols!"
    print(f"Running scoring engine over {union.shape[0]} names...")
    scored = E.run_engine(union)

    scored = scored.merge(raw[["symbol", "ttm_growth", "ttm_eps_src", "latest_qtr"]], on="symbol", how="left")
    out_cols = list(dict.fromkeys(E.SCHEMA_54 + ["coverage_flag_3y", "coverage_flag_1y",
                                                 "ttm_growth", "ttm_eps_src", "latest_qtr"]))
    for c in out_cols:
        if c not in scored.columns:
            scored[c] = np.nan
    sub = scored.copy()
    sub["stale_flag"] = sub["symbol"].isin([s for s, _ in stale])
    sub["zero_cov_flag"] = sub["symbol"].isin(zero)
    sub["recommendation_overall"] = sub.apply(lambda r: rec_overall(r["recommendation_3y"], r["recommendation_1y"]), axis=1)
    sub = sub[out_cols + ["stale_flag", "zero_cov_flag", "recommendation_overall"]].sort_values(
        "final_score_3y", ascending=False).reset_index(drop=True)

    OUT = os.path.join(RESULTS, "full750_scored.csv")
    sub.to_csv(OUT, index=False)
    print(f"\nSaved {sub.shape[0]} x {sub.shape[1]} -> {OUT}")
    print("\nOverall recommendation split:\n" + sub["recommendation_overall"].value_counts().to_string())
    print("\nCoverage flag (3y):\n" + sub["coverage_flag_3y"].value_counts().to_string())
    print(f"\nNames using TTM growth: {(sub['ttm_growth'].str.startswith('ttm')).sum()} | TTM EPS: {(sub['ttm_eps_src'].str.startswith('ttm')).sum()}")
    print(f"Stale (nulled): {len(stale)} | Zero-coverage: {len(zero)}")
    if zero:
        print("  zero:", zero)
    with open(os.path.join(RESULTS, "full750_quant_build_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes))
    print(f"Saved {len(notes)} notes.")


if __name__ == "__main__":
    main()
