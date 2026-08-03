"""task1_a6_isolate.py -- OPEN_ITEMS_20260803, DESK-100.

Isolates how much of INDICATOR_MINE_20260730's A6_vwap_proxy_continue result
(+4.153 index pts, t=2.576, n=9655, placebo p=0.000, largest_day_share=0.087) was the
NEWDIM_LEVELS_20260731-discovered front-week-selection DEFECT (155_indicator_mine_signals.py's
load_feat() did a bare drop_duplicates("bucket") on a table with one row per (bucket, expiry) --
NEWDIM's audit found this picks a non-front expiry in 25.6% of buckets), versus the OTHER
methodology differences NEWDIM introduced alongside the fix (one-trade/day cap, sigma choice,
ATR-scaled exits instead of a fixed to-15:25 horizon).

METHOD: re-run the ORIGINAL 155_indicator_mine_signals.py code UNCHANGED (imported directly
from its actual file in BACKTEST_QUEUE_20260730/done/, not retyped) except for swapping
load_feat()'s dedup for the corrected front-week selector (chain_front.py's min-DTE logic,
also reused verbatim in spirit). Then, ONE AT A TIME, on top of the corrected-selection base,
add: (a) one-trade/day-per-side cap, (b) band multiplier 1.0sigma / 2.0sigma instead of the
original's fixed 1.5sigma, (c) ATR-scaled stop/target exit (pathsafe.simulate_exit, PESSIMISTIC
bound only, per firm convention) instead of the fixed to-15:25-close horizon measurement.

Everything not explicitly varied is held EXACTLY as INDICATOR_MINE_20260730 had it: same spot
loader, same entry rule (next 1-min bar's open after signal bar close, from forward_stats), same
BUILD/FORWARD split (2025-12-31), same placebo mechanism (random-day reassignment) where used.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
AMC = ROOT / "Shreyas_Ionic_AMC"
OUT = AMC / "04_RND_LAB/results/OPEN_ITEMS_20260803"
FEAT_PATH = AMC / "04_RND_LAB/results/INDICATOR_MINE_20260730/chain_features_15min.parquet"
LIB = AMC / "04_RND_LAB/lib"
sys.path.insert(0, str(LIB))
from pathsafe import simulate_exit  # noqa: E402

SEED = 20260730


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


orig155 = load_module(
    AMC / "04_RND_LAB/results/BACKTEST_QUEUE_20260730/done/155_indicator_mine_signals.py",
    "orig155",
)

# SPEED (disclosed deviation, wall-clock reasons -- same tradeoff NEWDIM/PUTCAL_LADDER made this
# week): the original used N_PLACEBO=200 (each draw re-runs forward_stats' python row-loop over
# up to ~9655 build rows -- ~4s/draw observed on this machine, 200 draws/cell x 5 cells = >1hr).
# Cut to 50 draws (resolution 2% instead of 0.5%) via the function's own __defaults__ tuple --
# mine_cell/placebo_pval's SIGNATURES and LOGIC are otherwise byte-identical to the original.
# This affects ONLY the placebo p-value's resolution, not n/mean_pts/t_nw/largest_day_share,
# which are what the isolation is actually being judged on.
orig155.placebo_pval.__defaults__ = (50,)
print(f"[speed] placebo draws reduced 200->50 (disclosed deviation, wall-clock)", flush=True)


def report_cell(res: dict) -> dict:
    b = res.get("build", {})
    best = b.get("best", {})
    return {
        "label": res.get("label"),
        "n_build": res.get("n_signals_build"),
        "n_forward": res.get("n_signals_forward"),
        "best_horizon": b.get("best_horizon"),
        "mean_pts": best.get("mean_pts"),
        "t_nw": best.get("t_nw"),
        "hit": best.get("hit"),
        "largest_day_share": b.get("largest_day_share"),
        "placebo_p": res.get("placebo", {}).get("p_value"),
        "verdict": res.get("verdict"),
    }


def load_feat_corrected():
    """chain_front.py's min-DTE front-week selection, reproduced here (not reused as a module
    import because chain_front.py writes its own output file on import-by-exec; safer to mirror
    its 8 lines than exec a script with disk side effects)."""
    f = pd.read_parquet(FEAT_PATH)
    f["bucket"] = pd.to_datetime(f["bucket"])
    f["expiry_dt"] = pd.to_datetime(f["expiry"])
    f["bucket_date"] = f["bucket"].dt.normalize()
    f["dte"] = (f["expiry_dt"] - f["bucket_date"]).dt.days
    n_before = len(f)
    f = f[f["dte"] >= 0].copy()
    n_after_dte = len(f)
    f = f.sort_values(["bucket", "dte"])
    front = f.drop_duplicates("bucket", keep="first").sort_values("bucket").reset_index(drop=True)
    front["date"] = front["bucket"].dt.date
    front["t_signal"] = front["bucket"] + pd.Timedelta(minutes=15)
    return front, n_before, n_after_dte


def vwap_proxy_continue_param(feat: pd.DataFrame, spot: pd.DataFrame, mult: float,
                               bars15: pd.DataFrame | None = None) -> pd.DataFrame:
    """Verbatim copy of orig155.vwap_proxy_band_signals(..., kind='continue') with the band
    multiplier parameterised (original hardcodes 1.5). Everything else byte-identical."""
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
    if bars15 is None:
        bars15 = orig155.resample(spot, "15min")
    m = pd.merge_asof(
        bars15.reset_index().rename(columns={"t": "t15"}).sort_values("t15"),
        f[["t_signal", "upper_prior", "lower_prior"]].sort_values("t_signal"),
        left_on="t15", right_on="t_signal", direction="backward", tolerance=pd.Timedelta(minutes=20))
    # vectorized (not a behavior change vs the original per-row loop -- same two conditions,
    # same rows selected; done this way here purely for wall-clock speed on this ablation copy)
    valid = m.dropna(subset=["upper_prior", "lower_prior"])
    up = valid[(valid["high"] > valid["upper_prior"]) & (valid["close"] >= valid["upper_prior"])]
    dn = valid[(valid["low"] < valid["lower_prior"]) & (valid["close"] <= valid["lower_prior"])]
    rows = pd.concat([
        pd.DataFrame({"t": up["t15"].values, "dir": 1}),
        pd.DataFrame({"t": dn["t15"].values, "dir": -1}),
    ], ignore_index=True)
    return orig155.clip_entry_window(rows)


def build_daily_atr(spot: pd.DataFrame) -> pd.Series:
    """Daily ATR14, Wilder-smoothed (EWM alpha=1/14), PRIOR day's value (no lookahead) --
    identical construction to NEWDIM_LEVELS_20260731/build_base.py::build_daily_weekly."""
    g = spot.groupby(spot.index.date)
    daily = g.agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    daily.index = pd.to_datetime(daily.index)
    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    return atr.shift(1)  # atr14_prior, indexed by Timestamp(date)


def atr_exit_measure(spot: pd.DataFrame, sig: pd.DataFrame, atr_prior: pd.Series,
                      stop_f: float, target_f: float, label: str) -> dict:
    """Replace the fixed to-15:25-close horizon with an ATR-scaled stop/target, simulated on
    the real 1-min path via pathsafe.simulate_exit. PESSIMISTIC bound only (firm convention:
    quote the pessimistic number). BUILD sample only, matching the original's split."""
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    b = sig[sig["date"] <= orig155.BUILD_END]
    by_day = {d: gr for d, gr in spot.groupby(spot.index.date)}
    pnl, days_list = [], []
    n_no_atr = n_no_fwd = n_too_few_bars = 0
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
            n_too_few_bars += 1
            continue
        stop, target = stop_f * atr, target_f * atr
        res = simulate_exit(exit_bars, entry, sgn, stop=stop, target=target)
        pnl.append(res.pnl_pessimistic)
        days_list.append(d0)
    pnl = np.array(pnl, float)
    if len(pnl) == 0:
        return {"label": label, "n": 0}
    per_day = pd.Series(pnl, index=days_list).groupby(level=0).sum()
    tot = per_day.sum()
    conc = float(per_day.abs().max() / abs(tot)) if tot else None
    return {
        "label": label, "n": int(len(pnl)), "mean_pts": round(float(pnl.mean()), 3),
        "t_nw": round(float(orig155.nw_tstat(pnl)), 3),
        "hit": round(float((pnl > 0).mean()), 4),
        "largest_day_share": round(conc, 4) if conc is not None else None,
        "n_skipped_no_atr": n_no_atr, "n_skipped_no_fwd_bar": n_no_fwd,
        "n_skipped_lt3_exit_bars": n_too_few_bars,
    }


def main():
    import gc
    OUT.mkdir(parents=True, exist_ok=True)
    OUTFILE = OUT / "task1_a6_isolation.json"

    results = {}
    if OUTFILE.exists():
        try:
            results = json.loads(OUTFILE.read_text(encoding="utf-8"))
            print(f"[resume] loaded existing checkpoint with keys: {list(results.keys())}",
                  flush=True)
        except Exception as e:
            print(f"[resume] could not parse existing checkpoint ({e}); starting fresh",
                  flush=True)
    results.setdefault("ablations", {})

    def checkpoint():
        OUTFILE.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"[checkpoint] wrote {OUTFILE} (top keys: {list(results.keys())}, "
              f"ablations: {list(results['ablations'].keys())})", flush=True)

    spot = orig155.load_spot()
    print(f"[spot] {len(spot):,} bars {spot.index[0]} .. {spot.index[-1]}", flush=True)

    # --- 0. SANITY: reproduce the original (buggy) result byte-for-byte ---
    if "sanity_original_repro" not in results:
        feat_buggy = orig155.load_feat()
        sig_buggy = orig155.vwap_proxy_band_signals(feat_buggy, spot, "continue")
        res_buggy = orig155.mine_cell(spot, sig_buggy, "A6_ORIGINAL_BUGGY_REPRO", "continuation",
                                       np.random.default_rng(SEED))
        print("SANITY (target: n=9655 mean_pts=4.153 t_nw=2.576 largest_day_share=0.087):",
              report_cell(res_buggy), flush=True)
        results["sanity_original_repro"] = report_cell(res_buggy)
        del feat_buggy, sig_buggy, res_buggy
        gc.collect()
        checkpoint()
    else:
        print("[resume] skipping sanity_original_repro (already on disk)", flush=True)

    # --- 1. DEFECT-ONLY FIX: corrected front-week selection, everything else identical ---
    if "corrected_selection_only" not in results:
        feat_corr, n_before_dte, n_after_dte = load_feat_corrected()
        feat_buggy_for_audit = orig155.load_feat()
        naive_idx = feat_buggy_for_audit.set_index("bucket")
        corr_idx = feat_corr.set_index("bucket")
        common = naive_idx.index.intersection(corr_idx.index)
        mismatch = float((naive_idx.loc[common, "expiry"].astype(str).values !=
                          corr_idx.loc[common, "expiry"].astype(str).values).mean())
        print(f"[audit] naive-vs-corrected expiry mismatch on {len(common):,} common buckets: "
              f"{mismatch:.3f} (NEWDIM reported 0.256)", flush=True)
        results["expiry_mismatch_frac"] = mismatch
        results["n_buckets_dte_negative_dropped"] = n_before_dte - n_after_dte
        del feat_buggy_for_audit, naive_idx, corr_idx, common
        gc.collect()
        checkpoint()

        sig_corr = orig155.vwap_proxy_band_signals(feat_corr, spot, "continue")
        sig_corr.to_parquet(OUT / "_sig_corr_cache.parquet")  # for resume across process restarts
        res_corr = orig155.mine_cell(spot, sig_corr, "A6_CORRECTED_SELECTION_ONLY", "continuation",
                                      np.random.default_rng(SEED + 1))
        print("DEFECT-ONLY CORRECTED (the headline number):", report_cell(res_corr), flush=True)
        results["corrected_selection_only"] = report_cell(res_corr)
        checkpoint()
        del res_corr
        gc.collect()
    else:
        print("[resume] skipping corrected_selection_only (already on disk)", flush=True)
        feat_corr, _, _ = load_feat_corrected()
        sig_corr = pd.read_parquet(OUT / "_sig_corr_cache.parquet")

    # --- 2a. + one-trade/day-per-side cap ---
    if "plus_daily_cap" not in results["ablations"]:
        sig_capped = sig_corr.copy()
        sig_capped["date"] = pd.to_datetime(sig_capped["t"]).dt.date
        sig_capped = (sig_capped.sort_values("t")
                      .groupby(["date", "dir"], as_index=False).first()[["t", "dir"]]
                      .sort_values("t").reset_index(drop=True))
        res_capped = orig155.mine_cell(spot, sig_capped, "A6_corrected_PLUS_dailycap",
                                        "continuation", np.random.default_rng(SEED + 2))
        print("ABLATION +daily cap:", report_cell(res_capped), flush=True)
        results["ablations"]["plus_daily_cap"] = report_cell(res_capped)
        del sig_capped, res_capped
        gc.collect()
        checkpoint()
    else:
        print("[resume] skipping plus_daily_cap", flush=True)

    # --- 2b. sigma variation (band multiplier 1.0 / 2.0 instead of the original's 1.5) ---
    for mult in (1.0, 2.0):
        key = f"sigma_{mult}"
        if key in results["ablations"]:
            print(f"[resume] skipping {key}", flush=True)
            continue
        sig_m = vwap_proxy_continue_param(feat_corr, spot, mult)
        res_m = orig155.mine_cell(spot, sig_m, f"A6_corrected_sigma{mult}", "continuation",
                                   np.random.default_rng(SEED + 3))
        print(f"ABLATION sigma={mult}:", report_cell(res_m), flush=True)
        results["ablations"][key] = report_cell(res_m)
        del sig_m, res_m
        gc.collect()
        checkpoint()

    # --- 2c. ATR-scaled stop/target exit instead of the fixed to-15:25 horizon ---
    atr_prior = build_daily_atr(spot)
    for cfg_name, stop_f, target_f in (("tight_atr", 0.30, 0.45), ("wide_atr", 0.50, 0.85)):
        if cfg_name in results["ablations"]:
            print(f"[resume] skipping {cfg_name}", flush=True)
            continue
        r = atr_exit_measure(spot, sig_corr, atr_prior, stop_f, target_f, cfg_name)
        print(f"ABLATION {cfg_name} (stop={stop_f}xATR target={target_f}xATR, PESSIMISTIC):",
              r, flush=True)
        results["ablations"][cfg_name] = r
        gc.collect()
        checkpoint()

    print(f"\n[DONE] wrote {OUTFILE}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
