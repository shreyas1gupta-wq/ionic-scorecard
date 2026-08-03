"""task1_ablation_stage.py -- OPEN_ITEMS_20260803, DESK-100.
Runs ONE ablation stage per process invocation (memory-safe architecture per Principal's explicit
instruction after an OOM/segfault pair on this RAM-starved box). Reuses
NEWDIM_LEVELS_20260731/chain_front_15min.parquet (the already-corrected min-DTE front-week table)
rather than rebuilding it. Avoids list-of-dicts -> DataFrame construction (the exact call that threw
numpy._core._exceptions._ArrayMemoryError trying to allocate 1.18 MiB on attempt 1 today) by
preallocating numpy arrays for forward_stats' per-row outputs, mirroring
measure_signal_budget.py::forward_stats row-for-row (same math, different accumulation only).

Usage: python task1_ablation_stage.py --stage {corrected_only|daily_cap|sigma_1.0|sigma_2.0|atr_tight|atr_wide}
"""
from __future__ import annotations

import argparse
import datetime as dt
import gc
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
AMC = ROOT / "Shreyas_Ionic_AMC"
OUT = AMC / "04_RND_LAB/results/OPEN_ITEMS_20260803"
NEWDIM = AMC / "04_RND_LAB/results/NEWDIM_LEVELS_20260731"
LIB = AMC / "04_RND_LAB/lib"
sys.path.insert(0, str(LIB))
from pathsafe import simulate_exit  # noqa: E402
from chainlock import free_ram_gb  # noqa: E402

SEED = 20260730
N_PLACEBO = 20  # disclosed deviation from the original's 200 (wall-clock AND RAM fragility on
                # this machine, which has thrown ArrayMemoryError on allocations as small as
                # 77KB today; matches NEWDIM's own 200->40 reduction and PUTCAL_LADDER's
                # 500->150 reduction the same week -- same tradeoff, taken further here)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


orig155 = load_module(
    AMC / "04_RND_LAB/results/BACKTEST_QUEUE_20260730/done/155_indicator_mine_signals.py",
    "orig155",
)


def load_feat_corrected_reused() -> pd.DataFrame:
    """REUSE NEWDIM's already-corrected front-week table verbatim (per instruction: do not
    rebuild). Only adds the t_signal column that 155's own load_feat() adds."""
    f = pd.read_parquet(NEWDIM / "chain_front_15min.parquet")
    f["date"] = f["bucket"].dt.date  # match orig155.load_feat()'s python-date convention exactly
    f["t_signal"] = f["bucket"] + pd.Timedelta(minutes=15)
    return f


def vwap_signals_vectorized(feat: pd.DataFrame, spot: pd.DataFrame, mult: float,
                             cap_one_per_day_side: bool = False) -> pd.DataFrame:
    """Same math as orig155.vwap_proxy_band_signals(..., kind='continue') -- band = vwap_proxy +-
    mult*rolling-8-bucket-stdev, PIT-safe shift(1), signal = bar sweeps outside AND closes outside.
    VECTORIZED (boolean masks, no per-row dict list) for memory safety -- verified logically
    identical to the original's per-row loop (same two conditions, same rows selected)."""
    f = feat.copy()
    f["total_vol"] = f["ce_vol"] + f["pe_vol"]
    f["cw"] = f["spot_ref"] * f["total_vol"]
    g = f.groupby("date")
    f["cum_w"] = g["cw"].cumsum()
    f["cum_v"] = g["total_vol"].cumsum()
    f["vwap_proxy"] = f["cum_w"] / f["cum_v"].replace(0, np.nan)
    f["resid"] = f["spot_ref"] - f["vwap_proxy"]
    f["band_std"] = f.groupby("date")["resid"].transform(
        lambda x: x.rolling(8, min_periods=8).std())
    f["upper_prior"] = (f["vwap_proxy"] + mult * f["band_std"]).shift(1)
    f["lower_prior"] = (f["vwap_proxy"] - mult * f["band_std"]).shift(1)
    bars15 = orig155.resample(spot, "15min")
    m = pd.merge_asof(
        bars15.reset_index().rename(columns={"t": "t15"}).sort_values("t15"),
        f[["t_signal", "upper_prior", "lower_prior"]].sort_values("t_signal"),
        left_on="t15", right_on="t_signal", direction="backward", tolerance=pd.Timedelta(minutes=20))
    valid = m.dropna(subset=["upper_prior", "lower_prior"])
    up = valid[(valid["high"] > valid["upper_prior"]) & (valid["close"] >= valid["upper_prior"])]
    dn = valid[(valid["low"] < valid["lower_prior"]) & (valid["close"] <= valid["lower_prior"])]
    rows = pd.concat([
        pd.DataFrame({"t": up["t15"].values, "dir": 1}),
        pd.DataFrame({"t": dn["t15"].values, "dir": -1}),
    ], ignore_index=True)
    sig = orig155.clip_entry_window(rows)
    if cap_one_per_day_side and not sig.empty:
        sig = sig.copy()
        sig["date"] = pd.to_datetime(sig["t"]).dt.date
        sig = (sig.sort_values("t").groupby(["date", "dir"], as_index=False).first()
               [["t", "dir"]].sort_values("t").reset_index(drop=True))
    return sig


HORIZONS = [15, 30, 60, 120]


def forward_stats_safe(spot: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    """Row-for-row IDENTICAL logic to measure_signal_budget.py::forward_stats. Only the
    accumulation strategy differs: preallocated numpy arrays instead of a list of per-row dicts
    fed to pd.DataFrame() (that list-of-dicts -> object-array conversion is what threw
    ArrayMemoryError on attempt 1 today, even for a 1.18 MiB allocation -- this machine has been
    at ~2-3GB free all day with several concurrent agents)."""
    n = len(entries)
    if n == 0:
        return pd.DataFrame()
    by_day = {d: gr for d, gr in spot.groupby(spot.index.date)}
    t_arr = pd.to_datetime(entries["t"]).values
    dir_arr = entries["dir"].to_numpy()

    keep = np.zeros(n, dtype=bool)
    entry_px = np.full(n, np.nan)
    dates_out = np.empty(n, dtype=object)
    hpct = {h: np.full(n, np.nan) for h in HORIZONS}
    hpts = {h: np.full(n, np.nan) for h in HORIZONS}
    reod_pct = np.full(n, np.nan)
    reod_pts = np.full(n, np.nan)
    mfe_pct = np.full(n, np.nan)
    mae_pct = np.full(n, np.nan)

    for i in range(n):
        t0 = pd.Timestamp(t_arr[i])
        sgn = int(dir_arr[i])
        day = by_day.get(t0.date())
        if day is None:
            continue
        fwd = day[day.index > t0]
        if fwd.empty:
            continue
        e = float(fwd["open"].iloc[0])
        if not np.isfinite(e) or e <= 0:
            continue
        keep[i] = True
        entry_px[i] = e
        dates_out[i] = t0.date()
        for h in HORIZONS:
            w = fwd[fwd.index <= t0 + pd.Timedelta(minutes=h)]
            if len(w):
                px = float(w["close"].iloc[-1])
                hpct[h][i] = sgn * (px / e - 1)
                hpts[h][i] = sgn * (px - e)
        flat_cut = pd.Timestamp(t0.date()) + pd.Timedelta(hours=15, minutes=25)
        flat = fwd[fwd.index <= flat_cut]
        if len(flat):
            px = float(flat["close"].iloc[-1])
            reod_pct[i] = sgn * (px / e - 1)
            reod_pts[i] = sgn * (px - e)
            hi, lo = float(flat["high"].max()), float(flat["low"].min())
            mfe_pct[i] = (hi / e - 1) if sgn > 0 else (1 - lo / e)
            mae_pct[i] = (lo / e - 1) if sgn > 0 else (1 - hi / e)

    out = {"t": t_arr[keep], "dir": dir_arr[keep], "entry": entry_px[keep], "date": dates_out[keep]}
    for h in HORIZONS:
        out[f"r{h}_pct"] = hpct[h][keep]
        out[f"r{h}_pts"] = hpts[h][keep]
    out["reod_pct"] = reod_pct[keep]
    out["reod_pts"] = reod_pts[keep]
    out["mfe_pct"] = mfe_pct[keep]
    out["mae_pct"] = mae_pct[keep]
    return pd.DataFrame(out)


def placebo_pval_safe(spot, entries, pts_col, rng, n=N_PLACEBO):
    """Same random-day-reassignment placebo as orig155.placebo_pval, with per-draw
    MemoryError resilience: this machine has been at ~2-3GB free all day with several agents
    running and has thrown ArrayMemoryError on allocations as small as 77KB -- a single failed
    draw must not kill the whole process. Matches the 150_indicator_mine_features.py convention
    already in this codebase: retry once after gc.collect(), then skip-and-log (never silently
    drop -- skipped draws reduce the effective n, reported)."""
    if entries.empty:
        return np.nan, np.nan, 0
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    dirs = entries["dir"].tolist()
    obs_f = forward_stats_safe(spot, entries)
    if pts_col not in obs_f or obs_f[pts_col].dropna().empty:
        return np.nan, np.nan, 0
    observed = obs_f[pts_col].dropna().mean()
    del obs_f
    draws = np.full(n, np.nan)
    n_failed = 0
    for k in range(n):
        rows_t, rows_dir = [], []
        for tod, sgn in zip(tods, dirs):
            d = days[rng.integers(len(days))]
            rows_t.append(pd.Timestamp(d).replace(hour=tod.hour, minute=tod.minute))
            rows_dir.append(sgn)
        entries_k = pd.DataFrame({"t": rows_t, "dir": rows_dir})
        for attempt in (1, 2):
            try:
                f = forward_stats_safe(spot, entries_k)
                x = f[pts_col].dropna() if (not f.empty and pts_col in f) else pd.Series(dtype=float)
                draws[k] = x.mean() if len(x) else np.nan
                del f, x
                break
            except MemoryError as e:
                print(f"  [placebo draw {k} attempt {attempt}] MemoryError ({e}); "
                      f"gc.collect() and retry" if attempt == 1 else
                      f"  [placebo draw {k}] failed again, skipping this draw", flush=True)
                gc.collect()
                if attempt == 2:
                    n_failed += 1
        del entries_k
        if k % 10 == 0:
            gc.collect()
    valid = draws[np.isfinite(draws)]
    if len(valid) < max(5, n * 0.3):
        return np.nan, np.nan, n_failed
    p = float((np.abs(valid) >= abs(observed)).mean())
    return p, float(np.nanmean(valid)), n_failed


def forward_stats_retry(spot, entries, tries=3):
    for attempt in range(1, tries + 1):
        try:
            return forward_stats_safe(spot, entries)
        except MemoryError as e:
            print(f"  [forward_stats attempt {attempt}/{tries}] MemoryError ({e}); "
                  f"gc.collect()+retry", flush=True)
            gc.collect()
            time.sleep(1)
    raise MemoryError(f"forward_stats_safe failed after {tries} attempts (n={len(entries)})")


def mine_cell_safe(spot, sig, label, hypothesis, rng):
    if sig.empty:
        return {"label": label, "hypothesis": hypothesis, "n": 0, "verdict": "DEAD",
                "reason": "no signal instances"}
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    b = sig[sig["date"] <= orig155.BUILD_END]
    fw = sig[sig["date"] > orig155.BUILD_END]
    fb = forward_stats_retry(spot, b)
    ffwd = forward_stats_retry(spot, fw) if len(fw) else pd.DataFrame()
    build = orig155.summarize_cell(fb)
    forward = orig155.summarize_cell(ffwd) if len(ffwd) else {"n": int(len(fw))}
    cell = {"label": label, "hypothesis": hypothesis, "n_signals_build": int(len(b)),
            "n_signals_forward": int(len(fw)), "build": build, "forward": forward}
    if "best" not in build:
        cell["verdict"] = "UNDERPOWERED-UNRESOLVED" if build["n"] > 0 else "DEAD"
        cell["reason"] = "insufficient n for any horizon (<10 obs)"
        return cell
    best_lbl = build["best_horizon"]
    horizons = ["+15m", "+30m", "+60m", "+120m", "to15:25"]
    pts_cols = ["r15_pts", "r30_pts", "r60_pts", "r120_pts", "reod_pts"]
    pts_col = pts_cols[horizons.index(best_lbl)]
    conc = build.get("largest_day_share")
    p_val, placebo_mean, n_failed_draws = placebo_pval_safe(spot, b, pts_col, rng)
    cell["placebo"] = {"p_value": p_val, "placebo_mean_pts": placebo_mean, "n_draws": N_PLACEBO,
                       "n_failed_draws": n_failed_draws}
    n = build["n"]
    mean_pts = build["best"]["mean_pts"]
    t_nw = build["best"]["t_nw"]
    if not np.isfinite(p_val) or p_val >= orig155.PLACEBO_P_KILL:
        cell["verdict"] = "DEAD"; cell["reason"] = f"fails own placebo (p={p_val})"
    elif conc is not None and conc > orig155.CONC_KILL:
        cell["verdict"] = "DEAD"; cell["reason"] = f"profit concentration {conc:.0%} > 30%"
    elif n < 30:
        cell["verdict"] = "UNDERPOWERED-UNRESOLVED"; cell["reason"] = f"n={n} < 30/parameter floor"
    elif abs(mean_pts) < orig155.PROMOTE_EDGE_PTS:
        cell["verdict"] = "DEAD"
        cell["reason"] = f"edge {mean_pts}pts below 2pt economic floor despite passing placebo"
    else:
        cell["verdict"] = "FORWARD-TEST CANDIDATE"
        cell["clears_bonferroni_m481"] = bool(np.isfinite(t_nw) and abs(t_nw) >= orig155.T_BONF)
        cell["trade_direction"] = "as-hypothesized" if mean_pts > 0 else "REVERSED"
        cell["promote_to_stage2"] = True
    cell.setdefault("promote_to_stage2", False)
    return cell


def report_cell(res: dict) -> dict:
    b = res.get("build", {})
    best = b.get("best", {})
    return {
        "label": res.get("label"), "n_build": res.get("n_signals_build"),
        "n_forward": res.get("n_signals_forward"), "best_horizon": b.get("best_horizon"),
        "mean_pts": best.get("mean_pts"), "t_nw": best.get("t_nw"), "hit": best.get("hit"),
        "largest_day_share": b.get("largest_day_share"),
        "placebo_p": res.get("placebo", {}).get("p_value"), "verdict": res.get("verdict"),
    }


def build_daily_atr(spot: pd.DataFrame) -> pd.Series:
    g = spot.groupby(spot.index.date)
    daily = g.agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    daily.index = pd.to_datetime(daily.index)
    prev_close = daily["close"].shift(1)
    tr = pd.concat([daily["high"] - daily["low"], (daily["high"] - prev_close).abs(),
                    (daily["low"] - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    return atr.shift(1)


def atr_exit_measure(spot, sig, atr_prior, stop_f, target_f, label):
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    b = sig[sig["date"] <= orig155.BUILD_END]
    by_day = {d: gr for d, gr in spot.groupby(spot.index.date)}
    pnl_list, days_list = [], []
    n_no_atr = n_no_fwd = n_too_few = 0
    for _, r in b.iterrows():
        t0, sgn, d0 = r["t"], int(r["dir"]), r["date"]
        atr = atr_prior.get(pd.Timestamp(d0))
        if atr is None or not np.isfinite(atr) or atr <= 0:
            n_no_atr += 1
            continue
        day = by_day.get(d0)
        if day is None:
            continue
        fwd = day[day.index > t0]
        if fwd.empty:
            n_no_fwd += 1
            continue
        entry = float(fwd["open"].iloc[0])
        exit_bars = fwd.iloc[1:][["high", "low", "close"]]
        if len(exit_bars) < 3:
            n_too_few += 1
            continue
        stop, target = stop_f * atr, target_f * atr
        res = simulate_exit(exit_bars, entry, sgn, stop=stop, target=target)
        pnl_list.append(res.pnl_pessimistic)
        days_list.append(d0)
    pnl = np.array(pnl_list, float)
    if len(pnl) == 0:
        return {"label": label, "n": 0}
    per_day = pd.Series(pnl, index=days_list).groupby(level=0).sum()
    tot = per_day.sum()
    conc = float(per_day.abs().max() / abs(tot)) if tot else None
    return {
        "label": label, "n_build": int(len(pnl)), "mean_pts": round(float(pnl.mean()), 3),
        "t_nw": round(float(orig155.nw_tstat(pnl)), 3),
        "hit": round(float((pnl > 0).mean()), 4),
        "largest_day_share": round(conc, 4) if conc is not None else None,
        "placebo_p": None,
        "n_skipped_no_atr": n_no_atr, "n_skipped_no_fwd_bar": n_no_fwd,
        "n_skipped_lt3_exit_bars": n_too_few,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["corrected_only", "daily_cap", "sigma_1.0", "sigma_2.0",
                             "atr_tight", "atr_wide"])
    args = ap.parse_args()

    fr = free_ram_gb()
    print(f"[ram] free={fr:.2f}GB before stage {args.stage}", flush=True)
    if fr < 1.0:
        print(f"[ram] under 1.0GB free -- exiting cleanly WITHOUT running (per RAM discipline), "
              f"retry this stage later", flush=True)
        sys.exit(3)

    OUT.mkdir(parents=True, exist_ok=True)
    OUTFILE = OUT / "task1_a6_isolation.json"
    results = json.loads(OUTFILE.read_text(encoding="utf-8")) if OUTFILE.exists() else {}
    results.setdefault("ablations", {})

    spot = orig155.load_spot()
    print(f"[spot] {len(spot):,} bars", flush=True)
    feat_corr = load_feat_corrected_reused()
    print(f"[feat] reused NEWDIM chain_front_15min.parquet: {len(feat_corr):,} rows", flush=True)

    rng = np.random.default_rng(SEED + hash(args.stage) % 10000)

    if args.stage == "corrected_only":
        sig = vwap_signals_vectorized(feat_corr, spot, mult=1.5, cap_one_per_day_side=False)
        res = mine_cell_safe(spot, sig, "A6_CORRECTED_SELECTION_ONLY", "continuation", rng)
        key = "corrected_selection_only"
        results[key] = report_cell(res)
        sig.to_parquet(OUT / "_sig_corr_cache.parquet")
        print(f"[{key}]", results[key], flush=True)
    elif args.stage == "daily_cap":
        sig = vwap_signals_vectorized(feat_corr, spot, mult=1.5, cap_one_per_day_side=True)
        res = mine_cell_safe(spot, sig, "A6_corrected_PLUS_dailycap", "continuation", rng)
        results["ablations"]["plus_daily_cap"] = report_cell(res)
        print("[plus_daily_cap]", results["ablations"]["plus_daily_cap"], flush=True)
    elif args.stage in ("sigma_1.0", "sigma_2.0"):
        mult = float(args.stage.split("_")[1])
        sig = vwap_signals_vectorized(feat_corr, spot, mult=mult, cap_one_per_day_side=False)
        res = mine_cell_safe(spot, sig, f"A6_corrected_sigma{mult}", "continuation", rng)
        results["ablations"][args.stage] = report_cell(res)
        print(f"[{args.stage}]", results["ablations"][args.stage], flush=True)
    elif args.stage in ("atr_tight", "atr_wide"):
        sig = vwap_signals_vectorized(feat_corr, spot, mult=1.5, cap_one_per_day_side=False)
        atr_prior = build_daily_atr(spot)
        stop_f, target_f = (0.30, 0.45) if args.stage == "atr_tight" else (0.50, 0.85)
        r = atr_exit_measure(spot, sig, atr_prior, stop_f, target_f, args.stage)
        results["ablations"][args.stage] = r
        print(f"[{args.stage}]", r, flush=True)

    OUTFILE.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[checkpoint] wrote {OUTFILE}", flush=True)
    gc.collect()
    print(f"[ram] free={free_ram_gb():.2f}GB after stage {args.stage}", flush=True)
    print("[STAGE_DONE]", flush=True)


if __name__ == "__main__":
    sys.exit(main())
