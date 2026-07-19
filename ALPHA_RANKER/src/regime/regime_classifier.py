"""
ALPHA_RANKER Phase 2 — Market/Factor Regime Classifier.

Reads <ROOT>\\factor_navs (1).xlsx (Sheet1) and produces a daily regime
timeline covering five independent lenses (see 02_SCORING_ENGINE.md Step 4):
  1. TREND       : NIFTY 500 vs 200-DMA + 50/200-DMA slope -> {bull, bear, sideways}
  2. VOLATILITY  : 21d realized vol of NIFTY 500 returns, expanding tertile -> {low, normal, high}
  3. BREADTH     : Midcap150 & Smallcap250 relative strength vs Nifty100 (3m/6m) -> {broad, narrow/large-cap-led}
  4. RISK        : High Beta 50 vs Low Vol 30 RS, and Gold vs Nifty 500 RS -> {risk-on, risk-off}
  5. FACTOR LEAD : trailing 3m/6m returns of Momentum/Value/Quality/LowVol/Alpha -> leading factor(s)

HARD RULES enforced:
  - NO LOOKAHEAD: every metric at date T uses only rows <= T. Vol tertile cuts use an
    EXPANDING (not full-sample) quantile, so the cut itself only reflects history to date T.
  - NO FABRICATION: some factor-index columns stop updating ~38 trading days before the
    NIFTY 500 / Low Vol 30 / Momentum 30 / Midcap Momentum 50 columns (data-vendor lag, not a
    signal event). Rows/lenses with a stale or missing input are left NaN / labelled
    "insufficient_data" rather than forward-filled or guessed. The current-regime snapshot
    reports a PER-LENS as_of date for exactly this reason.

Outputs:
  <PROJECT>/results/regime_timeline.parquet   (daily labels + underlying metrics)
  <PROJECT>/results/current_regime.json       (latest snapshot per lens, with justifying metrics)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
PROJECT = ROOT / "ALPHA_RANKER"
INPUT_XLSX = ROOT / "factor_navs (1).xlsx"
OUT_PARQUET = PROJECT / "results" / "regime_timeline.parquet"
OUT_JSON = PROJECT / "results" / "current_regime.json"

# trailing windows (trading days)
W3M, W6M = 63, 126
MA_FAST, MA_SLOW = 50, 200
SLOPE_LOOKBACK = 20          # ~1 month, for "is the DMA rising/falling"
RV_WINDOW = 21               # realized-vol window
VOL_TERTILE_MIN_PERIODS = 252  # need >= 1y of history before a tertile cut means anything

COL_NIFTY500 = "NIFTY 500"
COL_NIFTY100 = "NIFTY 100"
COL_MIDCAP150 = "NIFTY MIDCAP 150"
COL_SMALLCAP250 = "NIFTY SMALLCAP 250"
COL_HIGHBETA50 = "NIFTY HIGH BETA 50"
COL_LOWVOL30 = "NIFTY 100 Low Vol 30"
COL_GOLD = "GOLDBEES"

FACTOR_COLS = {
    "Momentum": "NIFTY 200 Momentum 30",
    "Value": "NIFTY 200 Value 30",
    "Quality": "NIFTY 200 Quality 30",
    "LowVol": "NIFTY 100 Low Vol 30",
    "Alpha": "NIFTY 200 Alpha 30",
}


def load_navs() -> pd.DataFrame:
    df = pd.read_excel(INPUT_XLSX)
    df["NAV Date"] = pd.to_datetime(df["NAV Date"])
    df = df.sort_values("NAV Date").reset_index(drop=True)
    assert df["NAV Date"].is_monotonic_increasing and not df["NAV Date"].duplicated().any(), \
        "NAV Date must be sorted, unique"
    return df


def last_valid_date(df: pd.DataFrame, cols: list[str]) -> pd.Timestamp:
    """Last date where ALL of `cols` are non-null (honest 'as of' for a multi-input lens)."""
    mask = df[cols].notna().all(axis=1)
    return df.loc[mask, "NAV Date"].iloc[-1]


def compute_trend(df: pd.DataFrame) -> pd.DataFrame:
    s = df[COL_NIFTY500]
    ma_fast = s.rolling(MA_FAST, min_periods=MA_FAST).mean()
    ma_slow = s.rolling(MA_SLOW, min_periods=MA_SLOW).mean()
    fast_up = ma_fast.diff(SLOPE_LOOKBACK) > 0
    slow_up = ma_slow.diff(SLOPE_LOOKBACK) > 0
    above_slow = s > ma_slow

    have_data = ma_slow.notna() & ma_fast.diff(SLOPE_LOOKBACK).notna()
    trend = pd.Series(np.nan, index=df.index, dtype=object)
    trend[have_data] = "sideways"
    trend[have_data & above_slow & fast_up & slow_up] = "bull"
    trend[have_data & (~above_slow) & (~fast_up) & (~slow_up)] = "bear"

    out = pd.DataFrame({
        "nifty500": s,
        "ma50": ma_fast,
        "ma200": ma_slow,
        "ma50_slope_up": fast_up,
        "ma200_slope_up": slow_up,
        "price_above_ma200": above_slow,
        "trend_regime": trend,
    })
    return out


def compute_volatility(df: pd.DataFrame) -> pd.DataFrame:
    ret = df[COL_NIFTY500].pct_change()
    rv21 = ret.rolling(RV_WINDOW, min_periods=RV_WINDOW).std() * np.sqrt(252)
    # expanding (causal) tertile cuts: quantile at row t uses only rv21[0..t]
    q33 = rv21.expanding(min_periods=VOL_TERTILE_MIN_PERIODS).quantile(0.33)
    q67 = rv21.expanding(min_periods=VOL_TERTILE_MIN_PERIODS).quantile(0.67)

    have_data = rv21.notna() & q33.notna()
    vol_regime = pd.Series(np.nan, index=df.index, dtype=object)
    vol_regime[have_data] = "normal"
    vol_regime[have_data & (rv21 < q33)] = "low"
    vol_regime[have_data & (rv21 > q67)] = "high"

    return pd.DataFrame({
        "ret1d": ret,
        "rv21_ann": rv21,
        "vol_tertile_q33_expanding": q33,
        "vol_tertile_q67_expanding": q67,
        "vol_regime": vol_regime,
    })


def compute_breadth(df: pd.DataFrame) -> pd.DataFrame:
    def rs(window):
        r_mid = df[COL_MIDCAP150].pct_change(window)
        r_small = df[COL_SMALLCAP250].pct_change(window)
        r_100 = df[COL_NIFTY100].pct_change(window)
        return ((r_mid + r_small) / 2.0) - r_100, r_mid, r_small, r_100

    rs3m, mid3m, small3m, n100_3m = rs(W3M)
    rs6m, mid6m, small6m, n100_6m = rs(W6M)

    have_data = rs3m.notna() & rs6m.notna()
    avg_rs = (rs3m + rs6m) / 2.0
    breadth = pd.Series(np.nan, index=df.index, dtype=object)
    breadth[have_data] = "narrow/large-cap-led"
    breadth[have_data & (avg_rs > 0)] = "broad"
    conflict = have_data & (np.sign(rs3m) != np.sign(rs6m)) & (rs3m != 0) & (rs6m != 0)

    return pd.DataFrame({
        "midcap150_ret3m": mid3m, "smallcap250_ret3m": small3m, "nifty100_ret3m": n100_3m,
        "midcap150_ret6m": mid6m, "smallcap250_ret6m": small6m, "nifty100_ret6m": n100_6m,
        "breadth_rs_3m": rs3m, "breadth_rs_6m": rs6m, "breadth_rs_avg": avg_rs,
        "breadth_conflict_3m_vs_6m": conflict,
        "breadth_regime": breadth,
    })


def compute_risk_appetite(df: pd.DataFrame) -> pd.DataFrame:
    beta_ret3m = df[COL_HIGHBETA50].pct_change(W3M)
    lowvol_ret3m = df[COL_LOWVOL30].pct_change(W3M)
    gold_ret3m = df[COL_GOLD].pct_change(W3M)
    n500_ret3m = df[COL_NIFTY500].pct_change(W3M)

    vote_beta = beta_ret3m - lowvol_ret3m          # >0 => high-beta leading => risk-on
    vote_gold = n500_ret3m - gold_ret3m            # >0 => equities beating gold => risk-on
    score = vote_beta + vote_gold

    have_data = vote_beta.notna() & vote_gold.notna()
    risk = pd.Series(np.nan, index=df.index, dtype=object)
    risk[have_data] = "risk-off"
    risk[have_data & (score > 0)] = "risk-on"

    return pd.DataFrame({
        "highbeta50_ret3m": beta_ret3m, "lowvol30_ret3m": lowvol_ret3m,
        "gold_ret3m": gold_ret3m, "nifty500_ret3m": n500_ret3m,
        "risk_vote_beta_vs_lowvol": vote_beta, "risk_vote_equity_vs_gold": vote_gold,
        "risk_score": score, "risk_regime": risk,
    })


def compute_factor_leadership(df: pd.DataFrame) -> pd.DataFrame:
    out = {}
    scores = {}
    for name, col in FACTOR_COLS.items():
        r3 = df[col].pct_change(W3M)
        r6 = df[col].pct_change(W6M)
        sc = 0.5 * r3 + 0.5 * r6
        out[f"{name.lower()}_ret3m"] = r3
        out[f"{name.lower()}_ret6m"] = r6
        out[f"{name.lower()}_score"] = sc
        scores[name] = sc

    score_df = pd.DataFrame(scores)
    have_data = score_df.notna().all(axis=1)

    def leader_row(row):
        if row.isna().any():
            return np.nan
        return row.idxmax()

    def leader2_row(row):
        if row.isna().any():
            return np.nan
        ranked = row.sort_values(ascending=False)
        top, second = ranked.index[0], ranked.index[1]
        # "leading factor(s)" plural if #2 is within 20% (relative) of #1's score magnitude
        if abs(ranked.iloc[0]) > 1e-9 and abs(ranked.iloc[1] - ranked.iloc[0]) <= 0.2 * abs(ranked.iloc[0]):
            return f"{top}+{second}"
        return top

    leading = score_df.apply(leader_row, axis=1)
    leading_multi = score_df.apply(leader2_row, axis=1)

    out["leading_factor"] = leading
    out["leading_factor(s)"] = leading_multi
    return pd.DataFrame(out)


def build_timeline(df: pd.DataFrame) -> pd.DataFrame:
    parts = [
        df[["NAV Date"]].rename(columns={"NAV Date": "date"}),
        compute_trend(df),
        compute_volatility(df),
        compute_breadth(df),
        compute_risk_appetite(df),
        compute_factor_leadership(df),
    ]
    timeline = pd.concat(parts, axis=1)
    return timeline


def snapshot_current(df: pd.DataFrame, timeline: pd.DataFrame) -> dict:
    global_last_date = df["NAV Date"].iloc[-1]

    def last_row_for(cols):
        d = last_valid_date(df, cols)
        idx = df.index[df["NAV Date"] == d][0]
        return d, idx

    snap = {
        "generated_note": (
            "[DATA] Input columns update at two different cadences: NIFTY 500, NIFTY 100 Low Vol 30, "
            "NIFTY 200 Momentum 30 and Nifty Midcap Momentum 50 run through the file's last date; the "
            "other 16 factor/breadth columns (Value/Quality/Alpha indices, High Beta 50, GOLDBEES, "
            "Midcap150/Smallcap250/Nifty100/Smallcap100/Multicap/Liquid Fund) stop ~38 trading days earlier "
            "(vendor lag, verified: gap is a clean trailing NaN block with zero internal gaps, not a data error). "
            "Each lens below reports its OWN as_of date rather than silently using stale or forward-filled inputs."
        ),
        "file_last_date": str(global_last_date.date()),
    }

    # TREND (needs NIFTY 500 only)
    d, idx = last_row_for([COL_NIFTY500])
    trow = timeline.loc[idx]
    snap["trend"] = {
        "as_of": str(d.date()),
        "label": trow["trend_regime"],
        "nifty500": float(trow["nifty500"]),
        "ma50": round(float(trow["ma50"]), 2),
        "ma200": round(float(trow["ma200"]), 2),
        "price_above_ma200": bool(trow["price_above_ma200"]),
        "ma50_slope_up_20d": bool(trow["ma50_slope_up"]),
        "ma200_slope_up_20d": bool(trow["ma200_slope_up"]),
    }

    # VOLATILITY (needs NIFTY 500 only)
    d, idx = last_row_for([COL_NIFTY500])
    vrow = timeline.loc[idx]
    snap["volatility"] = {
        "as_of": str(d.date()),
        "label": vrow["vol_regime"],
        "rv21_annualized": round(float(vrow["rv21_ann"]), 4) if pd.notna(vrow["rv21_ann"]) else None,
        "expanding_tertile_q33": round(float(vrow["vol_tertile_q33_expanding"]), 4) if pd.notna(vrow["vol_tertile_q33_expanding"]) else None,
        "expanding_tertile_q67": round(float(vrow["vol_tertile_q67_expanding"]), 4) if pd.notna(vrow["vol_tertile_q67_expanding"]) else None,
    }

    # BREADTH (needs Midcap150, Smallcap250, Nifty100)
    d, idx = last_row_for([COL_MIDCAP150, COL_SMALLCAP250, COL_NIFTY100])
    brow = timeline.loc[idx]
    snap["breadth"] = {
        "as_of": str(d.date()),
        "label": brow["breadth_regime"],
        "rs_3m_vs_nifty100": round(float(brow["breadth_rs_3m"]), 4),
        "rs_6m_vs_nifty100": round(float(brow["breadth_rs_6m"]), 4),
        "conflict_3m_vs_6m": bool(brow["breadth_conflict_3m_vs_6m"]),
    }

    # RISK APPETITE (needs HighBeta50, LowVol30, Gold, Nifty500)
    d, idx = last_row_for([COL_HIGHBETA50, COL_LOWVOL30, COL_GOLD, COL_NIFTY500])
    rrow = timeline.loc[idx]
    snap["risk_appetite"] = {
        "as_of": str(d.date()),
        "label": rrow["risk_regime"],
        "vote_beta_vs_lowvol_3m": round(float(rrow["risk_vote_beta_vs_lowvol"]), 4),
        "vote_equity_vs_gold_3m": round(float(rrow["risk_vote_equity_vs_gold"]), 4),
    }

    # FACTOR LEADERSHIP (needs all 5 factor cols)
    d, idx = last_row_for(list(FACTOR_COLS.values()))
    frow = timeline.loc[idx]
    factor_scores = {name: round(float(frow[f"{name.lower()}_score"]), 4) for name in FACTOR_COLS}
    snap["factor_leadership"] = {
        "as_of": str(d.date()),
        "leading_factor": frow["leading_factor"],
        "leading_factor(s)": frow["leading_factor(s)"],
        "scores_3m6m_blend": dict(sorted(factor_scores.items(), key=lambda kv: -kv[1])),
    }

    return snap


def main():
    df = load_navs()
    timeline = build_timeline(df)

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    timeline.to_parquet(OUT_PARQUET, index=False)

    snap = snapshot_current(df, timeline)
    OUT_JSON.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")

    print("rows:", len(timeline))
    print("wrote:", OUT_PARQUET)
    print("wrote:", OUT_JSON)
    print(json.dumps(snap, indent=2, default=str))


if __name__ == "__main__":
    main()
