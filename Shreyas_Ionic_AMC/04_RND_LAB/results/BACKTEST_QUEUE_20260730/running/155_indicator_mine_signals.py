"""155_indicator_mine_signals.py -- Arjun Rao, 2026-07-30. (v3 -- performance fix.)

Stage-1 measurement for the INDICATOR_MINE_20260730 mandate: 15 pre-registered cells (10
option-chain-volume/OI, 3 India-VIX, 2 price-only multi-timeframe extension), measured with
the SAME reviewed machinery as EMA_INTRADAY_BUYING_20260729 (load_spot/resample/nw_tstat from
stage1_signal_test.py; forward_stats/summarize_cell/clip_entry_window from
measure_signal_budget.py -- reused, not re-derived). Adds a placebo p-value (random-day
reassignment, N=200, seed 20260730) as a HARD KILL per this mandate's own binding method.

Depends on 150_indicator_mine_features.py's output (chain_features_15min.parquet) -- already
present on disk (verified 76,239 rows, 0 skipped expiries).

Pre-registered in ../INDICATOR_MINE_20260730/PRE_REGISTRATION.md.

DEVIATIONS from pre-registration (logged, not hidden):
  1. A7-A10 OI-momentum uses TOTAL front-week OI (all strikes, CE+PE), not a strict "within 3%
     of spot" near-ATM filter (150's extraction aggregates OI per (t,type) across the whole
     chain for RAM-safety; far-OTM weekly strikes carry little OI in practice).
  2. A5/A6 VWAP-proxy band operates on 15-min buckets throughout (matches every other Family-A
     cell's native resolution); "rolling 30-min stdev" is implemented as an 8-bucket (~2h)
     rolling stdev for numerical stability at this granularity.
  3. **BUG CAUGHT IN DEV (2026-07-30, before queueing) AND FIXED**: an inclusive rolling
     z-score (window includes the current bar in its own baseline) is self-referential and
     mathematically CANNOT exceed |z|<=sqrt(n-1) (=1.5 for n=4, ddof=1) -- it could never
     reach the pre-registered z>=2 trigger. Fixed by excluding the current bar from its own
     baseline (shift-then-roll). A small floor on the rolling std (5% of the series'
     unconditional std) is also applied as a stability safeguard on the denominator, fixed as
     a constant BEFORE any cell's forward-stats were computed.
  4. sweep_priorday_reclaim@15min reproduces n=1775 EXACTLY against the already-published
     reference (EMA_INTRADAY_BUYING_20260729/signal_budget) -- used as an end-to-end
     correctness check before trusting the 30/45-min extensions.
  5. **PERFORMANCE FIX (v2->v3, caught by timing it live, not by guessing)**: v2 called
     measure_signal_budget.forward_stats() (row-by-row iterrows + a fresh per-day groupby
     dict rebuilt from the full 463,826-row spot frame) inside the N_PLACEBO=200 loop. Timed
     live: still had not finished cell 1 of 15 after 7 minutes -- unacceptable against the
     queue's 3600s hard timeout and unfair to other agents sharing it. Fixed by adding
     fast_horizon_pts(): a pure-numpy searchsorted implementation of the IDENTICAL horizon
     definition (entry = next bar's open strictly after signal; exit = last bar at/before
     t0+horizon, or that day's 15:25 for the "reod" horizon), used ONLY inside the 200x
     placebo loop. The single OBSERVED statistic per cell still goes through the original,
     richer, already-reviewed forward_stats/summarize_cell exactly once -- reuse is preserved
     for the number that is actually reported; only the repeated resampling got vectorized.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EMA_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729"
SB_DIR = EMA_DIR / "signal_budget"
sys.path.insert(0, str(EMA_DIR))
sys.path.insert(0, str(SB_DIR))
from stage1_signal_test import load_spot, resample, nw_tstat  # noqa: E402
from measure_signal_budget import forward_stats, summarize_cell, clip_entry_window  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/INDICATOR_MINE_20260730"
FEAT_PATH = OUT / "chain_features_15min.parquet"
VIX_PATH = ROOT / "intraday_options_strategy/datasets/processed/vix_1min.parquet"

BUILD_END = dt.date(2025, 12, 31)
SEED = 20260730
N_PLACEBO = 200
PLACEBO_P_KILL = 0.10          # hard kill: fails own placebo
CONC_KILL = 0.30               # hard kill: >30% of edge from one day
PROMOTE_EDGE_PTS = 2.0         # stage-2 promotion bar (compute discipline, not a hard kill)
BONFERRONI_M = 481             # 466 firm-cumulative + 15 this mine
T_BONF = 3.8                   # approx two-sided bar at m=481 (SHARED_CONTEXT's own 3.80 @349, stated as approx)


def zscore_intraday(s: pd.Series, dates: pd.Series, window: int) -> pd.Series:
    """z of the CURRENT bar vs the PRIOR `window` bars only (current excluded from its own
    baseline -- an inclusive window is self-referential and caps |z|<=sqrt(window-1),
    verified in dev this could never clear a z>=2 gate at window=4). Std floored at 5% of
    the series' unconditional std to avoid near-zero-denominator blowups."""
    df = pd.DataFrame({"v": s.values, "d": dates.values}, index=s.index)
    floor = 0.05 * float(np.nanstd(s.values))
    shifted = df.groupby("d")["v"].shift(1)
    roll_mean = shifted.groupby(df["d"]).transform(lambda x: x.rolling(window, min_periods=window).mean())
    roll_std = shifted.groupby(df["d"]).transform(lambda x: x.rolling(window, min_periods=window).std())
    roll_std = roll_std.clip(lower=floor)
    z = (df["v"] - roll_mean) / roll_std
    return z.replace([np.inf, -np.inf], np.nan)


_HORIZON_MIN = {"r15_pts": 15, "r30_pts": 30, "r60_pts": 60, "r120_pts": 120, "reod_pts": "reod"}


def fast_horizon_pts(idx_ns: np.ndarray, openp: np.ndarray, closep: np.ndarray,
                      entries_t: np.ndarray, entries_dir: np.ndarray, minutes) -> np.ndarray:
    """Vectorized (searchsorted, no iterrows/no groupby-dict-rebuild) forward move at a FIXED
    horizon -- used only inside the placebo loop. Identical definition to forward_stats:
    entry = next bar's open strictly after t0; exit = last bar at or before t0+horizon (or
    that day's 15:25 for 'reod')."""
    t0 = entries_t.astype("datetime64[ns]")
    entry_pos = np.searchsorted(idx_ns, t0, side="right")
    ok = entry_pos < len(idx_ns)
    entry_pos = entry_pos[ok]
    dirs = entries_dir[ok]
    t0ok = t0[ok]
    if len(entry_pos) == 0:
        return np.array([])
    entry_price = openp[entry_pos]
    if minutes == "reod":
        days = t0ok.astype("datetime64[D]").astype("datetime64[ns]")
        target = days + np.timedelta64(15 * 60 + 25, "m")
    else:
        target = t0ok + np.timedelta64(int(minutes), "m")
    end_pos = np.searchsorted(idx_ns, target, side="right") - 1
    end_pos = np.clip(end_pos, entry_pos, len(idx_ns) - 1)
    exit_price = closep[end_pos]
    valid_px = np.isfinite(entry_price) & (entry_price > 0)
    pts = dirs * (exit_price - entry_price)
    return pts[valid_px]


def placebo_pval(spot: pd.DataFrame, entries: pd.DataFrame, pts_col: str, rng: np.random.Generator,
                  idx_ns: np.ndarray, openp: np.ndarray, closep: np.ndarray,
                  n: int = N_PLACEBO) -> tuple[float, float]:
    """Random-day reassignment placebo (same mechanism as stage1_signal_test.placebo): same
    count/time-of-day/direction mix, random day reassignment. The OBSERVED statistic uses the
    original forward_stats (called once); the 200 placebo draws use fast_horizon_pts."""
    if entries.empty:
        return np.nan, np.nan
    days = sorted({d for d in spot.index.date})
    days_arr = np.array(days, dtype="datetime64[D]")
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    dirs = entries["dir"].to_numpy()
    obs_f = forward_stats(spot, entries)
    if pts_col not in obs_f or obs_f[pts_col].dropna().empty:
        return np.nan, np.nan
    observed = obs_f[pts_col].dropna().mean()
    minutes = _HORIZON_MIN[pts_col]
    tod_minutes = np.array([t.hour * 60 + t.minute for t in tods])
    draws = []
    for _ in range(n):
        rand_days = days_arr[rng.integers(len(days_arr), size=len(tods))]
        t_rand = rand_days.astype("datetime64[ns]") + (tod_minutes * np.timedelta64(1, "m"))
        pts = fast_horizon_pts(idx_ns, openp, closep, t_rand, dirs, minutes)
        draws.append(pts.mean() if len(pts) else np.nan)
    draws = np.array(draws, float)
    valid = draws[np.isfinite(draws)]
    if len(valid) < n * 0.5:
        return np.nan, np.nan
    p = float((np.abs(valid) >= abs(observed)).mean())
    return p, float(np.nanmean(valid))


def mine_cell(spot: pd.DataFrame, sig: pd.DataFrame, label: str, hypothesis: str, rng,
              idx_ns: np.ndarray, openp: np.ndarray, closep: np.ndarray) -> dict:
    if sig.empty:
        return {"label": label, "hypothesis": hypothesis, "n": 0, "verdict": "DEAD",
                "reason": "no signal instances", "promote_to_stage2": False}
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    b = sig[sig["date"] <= BUILD_END]
    fw = sig[sig["date"] > BUILD_END]
    fb = forward_stats(spot, b)
    ffwd = forward_stats(spot, fw) if len(fw) else pd.DataFrame()
    build = summarize_cell(fb)
    forward = summarize_cell(ffwd) if len(ffwd) else {"n": int(len(fw))}
    cell = {"label": label, "hypothesis": hypothesis, "n_signals_build": int(len(b)),
            "n_signals_forward": int(len(fw)), "build": build, "forward": forward}
    if "best" not in build:
        cell["verdict"] = "UNDERPOWERED-UNRESOLVED" if build["n"] > 0 else "DEAD"
        cell["reason"] = "insufficient n for any horizon (<10 obs)"
        cell["promote_to_stage2"] = False
        return cell
    best_lbl = build["best_horizon"]
    horizons = ["+15m", "+30m", "+60m", "+120m", "to15:25"]
    pts_cols = ["r15_pts", "r30_pts", "r60_pts", "r120_pts", "reod_pts"]
    pts_col = pts_cols[horizons.index(best_lbl)]
    conc = build.get("largest_day_share")
    p_val, placebo_mean = placebo_pval(spot, b, pts_col, rng, idx_ns, openp, closep)
    cell["placebo"] = {"p_value": p_val, "placebo_mean_pts": placebo_mean, "n_draws": N_PLACEBO}
    n = build["n"]
    mean_pts = build["best"]["mean_pts"]
    t_nw = build["best"]["t_nw"]
    if not np.isfinite(p_val) or p_val >= PLACEBO_P_KILL:
        cell["verdict"] = "DEAD"; cell["reason"] = f"fails own placebo (p={p_val})"
    elif conc is not None and conc > CONC_KILL:
        cell["verdict"] = "DEAD"; cell["reason"] = f"profit concentration {conc:.0%} > 30%"
    elif n < 30:
        cell["verdict"] = "UNDERPOWERED-UNRESOLVED"; cell["reason"] = f"n={n} < 30/parameter floor"
    elif abs(mean_pts) < PROMOTE_EDGE_PTS:
        cell["verdict"] = "DEAD"; cell["reason"] = f"edge {mean_pts}pts below 2pt economic floor despite passing placebo"
    else:
        cell["verdict"] = "FORWARD-TEST CANDIDATE"
        cell["clears_bonferroni_m481"] = bool(np.isfinite(t_nw) and abs(t_nw) >= T_BONF)
        cell["trade_direction"] = "as-hypothesized" if mean_pts > 0 else "REVERSED (opposite of hypothesis)"
    cell.setdefault("promote_to_stage2", cell.get("verdict") == "FORWARD-TEST CANDIDATE")
    return cell


# ============================================================================
# Family C -- price-only multi-timeframe extension of sweep_priorday_reclaim
# ============================================================================
def sweep_priorday_reclaim(spot: pd.DataFrame, rule: str) -> pd.DataFrame:
    bars = resample(spot, rule)
    daily_hi = bars.groupby(bars.index.date)["high"].max()
    daily_lo = bars.groupby(bars.index.date)["low"].min()
    days_sorted = sorted(daily_hi.index)
    prior_hi = {d: daily_hi[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}
    prior_lo = {d: daily_lo[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}
    rows = []
    for d, day in bars.groupby(bars.index.date):
        if d not in prior_hi:
            continue
        ph, pl = prior_hi[d], prior_lo[d]
        for t, row in day.iterrows():
            hi, lo, close = row["high"], row["low"], row["close"]
            if hi > ph and close < ph:
                rows.append({"t": t, "dir": -1})
            if lo < pl and close > pl:
                rows.append({"t": t, "dir": 1})
    return clip_entry_window(pd.DataFrame(rows))


# ============================================================================
# Family A -- option-chain volume/OI (built from chain_features_15min.parquet)
# ============================================================================
def load_feat() -> pd.DataFrame:
    if not FEAT_PATH.exists():
        raise FileNotFoundError(f"{FEAT_PATH} missing -- 150_indicator_mine_features.py must run first")
    f = pd.read_parquet(FEAT_PATH)
    f["bucket"] = pd.to_datetime(f["bucket"])
    f = f.drop_duplicates("bucket").sort_values("bucket").reset_index(drop=True)
    f["date"] = f["bucket"].dt.date
    f["t_signal"] = f["bucket"] + pd.Timedelta(minutes=15)   # decision fires at bucket close
    return f


def imbalance_signals(feat: pd.DataFrame, side: str) -> pd.DataFrame:
    feat = feat.copy()
    feat["imb"] = (feat["ce_vol"] - feat["pe_vol"]) / (feat["ce_vol"] + feat["pe_vol"]).replace(0, np.nan)
    feat["z"] = zscore_intraday(feat["imb"], feat["date"], window=4)
    if side == "call_heavy":
        trig = feat[feat["z"] >= 2]; d = 1
    else:
        trig = feat[feat["z"] <= -2]; d = -1
    return clip_entry_window(pd.DataFrame({"t": trig["t_signal"], "dir": d}))


def concentration_signals(feat: pd.DataFrame, side: str) -> pd.DataFrame:
    col = "conc_ce" if side == "call" else "conc_pe"
    trig = feat[feat[col] >= 0.40]
    d = 1 if side == "call" else -1
    return clip_entry_window(pd.DataFrame({"t": trig["t_signal"], "dir": d}))


def vwap_proxy_band_signals(feat: pd.DataFrame, spot: pd.DataFrame, kind: str) -> pd.DataFrame:
    f = feat.copy()
    f["total_vol"] = f["ce_vol"] + f["pe_vol"]
    f["cw"] = f["spot_ref"] * f["total_vol"]
    g = f.groupby("date")
    f["cum_w"] = g["cw"].cumsum()
    f["cum_v"] = g["total_vol"].cumsum()
    f["vwap_proxy"] = f["cum_w"] / f["cum_v"].replace(0, np.nan)
    f["resid"] = f["spot_ref"] - f["vwap_proxy"]
    f["band_std"] = f.groupby("date")["resid"].transform(lambda x: x.rolling(8, min_periods=8).std())
    f["upper_prior"] = (f["vwap_proxy"] + 1.5 * f["band_std"]).shift(1)
    f["lower_prior"] = (f["vwap_proxy"] - 1.5 * f["band_std"]).shift(1)
    bars15 = resample(spot, "15min")
    m = pd.merge_asof(bars15.reset_index().rename(columns={"t": "t15"}).sort_values("t15"),
                       f[["t_signal", "upper_prior", "lower_prior"]].sort_values("t_signal"),
                       left_on="t15", right_on="t_signal", direction="backward", tolerance=pd.Timedelta(minutes=20))
    rows = []
    for _, row in m.iterrows():
        if pd.isna(row["upper_prior"]) or pd.isna(row["lower_prior"]):
            continue
        hi, lo, close = row["high"], row["low"], row["close"]
        if hi > row["upper_prior"]:
            if kind == "reclaim" and close < row["upper_prior"]:
                rows.append({"t": row["t15"], "dir": -1})
            elif kind == "continue" and close >= row["upper_prior"]:
                rows.append({"t": row["t15"], "dir": 1})
        if lo < row["lower_prior"]:
            if kind == "reclaim" and close > row["lower_prior"]:
                rows.append({"t": row["t15"], "dir": 1})
            elif kind == "continue" and close <= row["lower_prior"]:
                rows.append({"t": row["t15"], "dir": -1})
    return clip_entry_window(pd.DataFrame(rows))


def oi_quadrant_signals(feat: pd.DataFrame, quadrant: str) -> pd.DataFrame:
    f = feat.copy()
    f["oi_tot"] = f["ce_oi"] + f["pe_oi"]
    f["d_oi"] = f.groupby("date")["oi_tot"].diff()
    f["d_px"] = f.groupby("date")["spot_ref"].diff()
    if quadrant == "long_buildup":
        trig = f[(f["d_px"] > 0) & (f["d_oi"] > 0)]; d = 1
    elif quadrant == "short_covering":
        trig = f[(f["d_px"] > 0) & (f["d_oi"] < 0)]; d = 1
    elif quadrant == "short_buildup":
        trig = f[(f["d_px"] < 0) & (f["d_oi"] > 0)]; d = -1
    else:
        trig = f[(f["d_px"] < 0) & (f["d_oi"] < 0)]; d = -1
    return clip_entry_window(pd.DataFrame({"t": trig["t_signal"], "dir": d}))


# ============================================================================
# Family B -- India VIX
# ============================================================================
def load_vix() -> pd.Series:
    v = pd.read_parquet(VIX_PATH)
    return v["vix"].sort_index()


def vix_rv_divergence_signals(spot: pd.DataFrame, vix: pd.Series, side: str) -> pd.DataFrame:
    ret = spot["close"].pct_change()
    rv = ret.groupby(spot.index.date).transform(
        lambda x: x.rolling(30, min_periods=20).std() * np.sqrt(252 * 375) * 100)
    vix_aligned = vix.reindex(spot.index, method="ffill")
    div = vix_aligned - rv
    dates = pd.Series(spot.index.date, index=spot.index)
    z = zscore_intraday(div, dates, window=60)
    if side == "high":
        trig_idx = z[z >= 2].index
        return clip_entry_window(pd.DataFrame({"t": trig_idx, "dir": 1}))
    trig_idx = z[z <= -2].index
    mom = spot["close"].pct_change(30)
    d = np.sign(mom.reindex(trig_idx)).fillna(0)
    sig = pd.DataFrame({"t": trig_idx, "dir": d.values})
    return clip_entry_window(sig[sig["dir"] != 0])


def vix_roc_spike_signals(spot: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    vix_aligned = vix.reindex(spot.index, method="ffill")
    roc = vix_aligned.diff(15)
    hi_thr, lo_thr = roc.quantile(0.90), roc.quantile(0.10)
    up = roc[roc >= hi_thr].index
    dn = roc[roc <= lo_thr].index
    rows = [{"t": t, "dir": 1} for t in up] + [{"t": t, "dir": -1} for t in dn]
    return clip_entry_window(pd.DataFrame(rows))


# ============================================================================
def main():
    t_start = time.time()
    rng = np.random.default_rng(SEED)
    spot = load_spot()
    print(f"[spot] {len(spot):,} bars {spot.index[0]} .. {spot.index[-1]}", flush=True)
    idx_ns = spot.index.values.astype("datetime64[ns]")
    openp = spot["open"].to_numpy(dtype=float)
    closep = spot["close"].to_numpy(dtype=float)
    feat = load_feat()
    print(f"[feat] {len(feat):,} 15-min buckets {feat['bucket'].min()} .. {feat['bucket'].max()}", flush=True)
    vix = load_vix()
    print(f"[vix] {len(vix):,} bars {vix.index.min()} .. {vix.index.max()}", flush=True)

    check = sweep_priorday_reclaim(spot, "15min")
    check_b = check[pd.to_datetime(check["t"]).dt.date <= BUILD_END]
    print(f"[check] sweep_priorday_reclaim@15min build n={len(check_b)} (published ref: 1775) "
          f"{'OK' if len(check_b) == 1775 else 'MISMATCH -- STOP AND INVESTIGATE'}", flush=True)
    assert len(check_b) == 1775, "reused sweep machinery does not reproduce the published reference"

    results = {}
    print("\n=== FAMILY A: option-chain volume/OI (10 cells) ===", flush=True)
    a_defs = [
        ("A1_imbalance_call_heavy", "bullish (call-volume pressure precedes upside)", lambda: imbalance_signals(feat, "call_heavy")),
        ("A2_imbalance_put_heavy", "bearish (put-volume pressure precedes downside)", lambda: imbalance_signals(feat, "put_heavy")),
        ("A3_otm_call_concentration", "bullish (unusual OTM-call strike volume)", lambda: concentration_signals(feat, "call")),
        ("A4_otm_put_concentration", "bearish (unusual OTM-put strike volume)", lambda: concentration_signals(feat, "put")),
        ("A5_vwap_proxy_reclaim", "reversal (mirrors proven sweep_priorday_reclaim structure)", lambda: vwap_proxy_band_signals(feat, spot, "reclaim")),
        ("A6_vwap_proxy_continue", "continuation", lambda: vwap_proxy_band_signals(feat, spot, "continue")),
        ("A7_oi_long_buildup", "bullish continuation (price up + OI up)", lambda: oi_quadrant_signals(feat, "long_buildup")),
        ("A8_oi_short_covering", "bullish (price up + OI down)", lambda: oi_quadrant_signals(feat, "short_covering")),
        ("A9_oi_short_buildup", "bearish continuation (price down + OI up)", lambda: oi_quadrant_signals(feat, "short_buildup")),
        ("A10_oi_long_unwind", "bearish (price down + OI down)", lambda: oi_quadrant_signals(feat, "long_unwind")),
    ]
    for label, hyp, fn in a_defs:
        t0 = time.time()
        sig = fn()
        res = mine_cell(spot, sig, label, hyp, rng, idx_ns, openp, closep)
        results[label] = res
        print(f"  [{label}] n={res.get('n_signals_build', res.get('n'))} -> {res['verdict']} "
              f"({res.get('reason', '')}) [{time.time()-t0:.1f}s]", flush=True)

    print("\n=== FAMILY B: India VIX dynamics (3 cells) ===", flush=True)
    b_defs = [
        ("B1_vix_rv_divergence_high", "contrarian bounce (VIX richer than realized)", lambda: vix_rv_divergence_signals(spot, vix, "high")),
        ("B2_vix_rv_divergence_low", "continuation of recent realized move", lambda: vix_rv_divergence_signals(spot, vix, "low")),
        ("B3_vix_roc_spike", "fear-spike bounce / complacency-drop fade", lambda: vix_roc_spike_signals(spot, vix)),
    ]
    for label, hyp, fn in b_defs:
        t0 = time.time()
        sig = fn()
        res = mine_cell(spot, sig, label, hyp, rng, idx_ns, openp, closep)
        results[label] = res
        print(f"  [{label}] n={res.get('n_signals_build', res.get('n'))} -> {res['verdict']} "
              f"({res.get('reason', '')}) [{time.time()-t0:.1f}s]", flush=True)

    print("\n=== FAMILY C: multi-timeframe sweep_priorday_reclaim extension (2 cells) ===", flush=True)
    c_defs = [
        ("C1_sweep_priorday_reclaim_30min", "reversal (identical def to today's t=3.10 winner, 30min bars)", lambda: sweep_priorday_reclaim(spot, "30min")),
        ("C2_sweep_priorday_reclaim_45min", "reversal (identical def, 45min bars)", lambda: sweep_priorday_reclaim(spot, "45min")),
    ]
    for label, hyp, fn in c_defs:
        t0 = time.time()
        sig = fn()
        res = mine_cell(spot, sig, label, hyp, rng, idx_ns, openp, closep)
        results[label] = res
        print(f"  [{label}] n={res.get('n_signals_build', res.get('n'))} -> {res['verdict']} "
              f"({res.get('reason', '')}) [{time.time()-t0:.1f}s]", flush=True)

    promoted = [k for k, v in results.items() if v.get("promote_to_stage2")]
    n_dead = sum(1 for v in results.values() if v.get("verdict") == "DEAD")
    n_under = sum(1 for v in results.values() if v.get("verdict") == "UNDERPOWERED-UNRESOLVED")
    n_cand = sum(1 for v in results.values() if v.get("verdict") == "FORWARD-TEST CANDIDATE")
    report = {
        "n_cells": len(results), "n_dead": n_dead, "n_underpowered": n_under,
        "n_forward_test_candidate": n_cand, "promoted_to_stage2": promoted,
        "bonferroni_m": BONFERRONI_M, "t_bar_approx": T_BONF,
        "elapsed_s": round(time.time() - t_start, 1),
        "cells": results,
    }
    (OUT / "stage1_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (OUT / "promoted_cells.json").write_text(json.dumps(promoted, indent=2), encoding="utf-8")
    print(f"\n[DONE] {n_dead} DEAD, {n_under} UNDERPOWERED, {n_cand} FORWARD-TEST CANDIDATE. "
          f"Promoted to stage2: {promoted}. Total elapsed {report['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
