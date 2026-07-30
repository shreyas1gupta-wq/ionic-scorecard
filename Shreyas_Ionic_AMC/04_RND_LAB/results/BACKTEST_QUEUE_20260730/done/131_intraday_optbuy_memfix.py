r"""Queued backtest: intraday NIFTY 50 option BUYING re-test at Rs25/lot/side costs.
Self-contained, no arguments. Runs under BACKTEST_QUEUE_20260730/runner.py.

Pre-registration (fixed BEFORE this ran):
  Shreyas_Ionic_AMC/04_RND_LAB/results/INTRADAY_OPTBUY_20260730/PREREG.md
Owner: Arjun Rao (Head of Quant), 2026-07-30.

Outputs -> Shreyas_Ionic_AMC/04_RND_LAB/results/INTRADAY_OPTBUY_20260730/
  results.json          - every pre-registered cell, build+forward+era-split+gates
  run_log.txt           - full stdout
  <cellname>_trades.csv - per-trade rows for the PRIMARY anchor/ATM/DTE2-4 cell + sanity control
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
HARNESS_DIR = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "OPTION_PL_HARNESS_20260729"
SIGBUDGET_DIR = (ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" /
                 "EMA_INTRADAY_BUYING_20260729" / "signal_budget")
STAGE1_DIR = SIGBUDGET_DIR.parent
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "INTRADAY_OPTBUY_20260730"
OUT.mkdir(parents=True, exist_ok=True)

for p in (HARNESS_DIR, SIGBUDGET_DIR, STAGE1_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import opt_pl as H  # noqa: E402
from stage1_signal_test import resample, nw_tstat  # noqa: E402
from measure_signal_budget import sweep_signals, orb_vol_filter, supertrend_flips  # noqa: E402

# ---- COST MODEL CORRECTION per mandate: Rs25/lot/side (harness default was Rs20) ----
H.BROKERAGE_PER_ORDER = 25.0

BUILD_END = dt.date(2025, 12, 31)
PRE_TIGHTEN_END = dt.date(2024, 9, 30)
FWD_END = dt.date(2026, 6, 3)

LOGLINES: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    LOGLINES.append(str(msg))


T0 = time.time()
log(f"[130_intraday_optbuy] start {dt.datetime.now()}")

spot = H.load_spot()
log(f"[spot] {len(spot):,} bars {spot.index[0]} .. {spot.index[-1]}")
bars5 = resample(spot, "5min")
bars15 = resample(spot, "15min")
log(f"[bars] 5min={len(bars5):,} 15min={len(bars15):,}")

# ---------------------------------------------------------------- signals (verbatim reuse)
sweeps = sweep_signals(bars15)
sig_priorday_reclaim = sweeps["priorday_reclaim"].rename(columns={"dir": "direction"})
sig_intraday_continue = sweeps["intraday_continue"].rename(columns={"dir": "direction"})
sig_intraday_reclaim_fade = sweeps["intraday_reclaim"].copy()
sig_intraday_reclaim_fade["dir"] = -sig_intraday_reclaim_fade["dir"]
sig_intraday_reclaim_fade = sig_intraday_reclaim_fade.rename(columns={"dir": "direction"})
sig_volbrk_orb = orb_vol_filter(bars5).rename(columns={"dir": "direction"})
sig_supertrend_15_10_3 = supertrend_flips(bars15, 10, 3).rename(columns={"dir": "direction"})

SIGNAL_SETS = {
    "sweep_priorday_reclaim": sig_priorday_reclaim,
    "sweep_intraday_continue": sig_intraday_continue,
    "volbrk_orb_volfilter": sig_volbrk_orb,
    "supertrend_15min_ATR10x3": sig_supertrend_15_10_3,
    "FADE_sweep_intraday_reclaim": sig_intraday_reclaim_fade,
}
for _name, _df in SIGNAL_SETS.items():
    lo = _df["t"].min() if len(_df) else None
    hi = _df["t"].max() if len(_df) else None
    log(f"[signal] {_name}: n={len(_df)}  {lo} .. {hi}")


def split_build_forward(df: pd.DataFrame):
    if df.empty:
        return df.copy(), df.copy()
    d = pd.to_datetime(df["t"]).dt.date
    b = df[d <= BUILD_END][["t", "direction"]].copy()
    f = df[(d > BUILD_END) & (d <= FWD_END)][["t", "direction"]].copy()
    return b, f


# ---------------------------------------------------------------- config builder
def make_cfg(min_dte: int, max_dte: int, strike_offset: int, exit_name: str) -> H.OptCfg:
    kw = dict(min_dte=min_dte, max_dte=max_dte, strike_offset=strike_offset,
              max_hold_days=0, squareoff_hhmm="15:25", expiry_handling="trade_out",
              lots=1, cost_model="cost_standards")
    if exit_name == "anchor":
        kw.update(trail_pct=0.35, stop_pct=0.50, allow_opposite_signal_exit=True)
    elif exit_name == "trail25":
        kw.update(trail_pct=0.25, stop_pct=0.50, allow_opposite_signal_exit=True)
    elif exit_name == "trail50":
        kw.update(trail_pct=0.50, stop_pct=0.60, allow_opposite_signal_exit=True)
    elif exit_name == "hardstop30":
        kw.update(stop_pct=0.30, allow_opposite_signal_exit=False)
    elif exit_name == "hardstop40":
        kw.update(stop_pct=0.40, allow_opposite_signal_exit=False)
    elif exit_name == "delta1only":
        kw.update(stop_pct=0.60, allow_opposite_signal_exit=True)
    else:
        raise ValueError(exit_name)
    return H.OptCfg(**kw)


# ---------------------------------------------------------------- metrics
def era_stat(sub: pd.DataFrame) -> dict:
    if sub.empty:
        return {"n": 0}
    return {
        "n": int(len(sub)),
        "net_sum": float(sub["net_pnl"].sum()),
        "gross_sum": float(sub["gross"].sum()),
        "mean_net_pct": float(sub["ret_pct_net"].mean()),
        "hit_net": float((sub["net_pnl"] > 0).mean()),
    }


def cell_metrics(cell_name: str, trades: pd.DataFrame, is_build: bool) -> dict:
    n_raw = int(len(trades))
    if n_raw == 0:
        return {"cell": cell_name, "n_raw_signals": 0, "n_filled": 0, "verdict": "NO_SIGNALS"}
    reject_counts = (trades[trades.status == "rejected"]["reject_reason"]
                     .value_counts().to_dict())
    filled = trades[trades.status == "filled"].copy()
    n_filled = int(len(filled))
    out = {"cell": cell_name, "n_raw_signals": n_raw, "n_filled": n_filled,
           "reject_reasons": {str(k): int(v) for k, v in reject_counts.items()}}
    if n_filled == 0:
        out["verdict"] = "NO_FILLS"
        return out
    filled["exit_date"] = pd.to_datetime(filled["exit_t"]).dt.date
    filled["entry_date"] = pd.to_datetime(filled["entry_t"]).dt.date
    gross_sum = float(filled["gross"].sum())
    net_sum = float(filled["net_pnl"].sum())
    ret_net = filled["ret_pct_net"].dropna()
    out.update(
        gross_sum=gross_sum, net_sum=net_sum,
        hit_net=float((filled["net_pnl"] > 0).mean()),
        hit_gross=float((filled["gross"] > 0).mean()),
        mean_ret_net_pct=float(ret_net.mean()) if len(ret_net) else np.nan,
        median_ret_net_pct=float(ret_net.median()) if len(ret_net) else np.nan,
        skew_ret_net=float(ret_net.skew()) if len(ret_net) > 2 else np.nan,
        p95_ret_net_pct=float(ret_net.quantile(0.95)) if len(ret_net) else np.nan,
        max_trade_net_rs=float(filled["net_pnl"].max()),
        min_trade_net_rs=float(filled["net_pnl"].min()),
        largest_trade_share_of_net=(float(filled["net_pnl"].max() / net_sum)
                                    if net_sum > 0 else None),
        avg_allin_cost_pts=float((filled["costs"] / filled["qty"]).mean()),
        avg_hold_min=float(filled["hold_min"].mean()),
        exit_reason_counts={str(k): int(v) for k, v in
                            filled["exit_reason"].value_counts().to_dict().items()},
    )
    # monthly gross/net win rate
    mkey = pd.to_datetime(filled["exit_date"]).astype("datetime64[ns]")
    filled["month"] = mkey.dt.to_period("M").astype(str)
    m_net = filled.groupby("month")["net_pnl"].sum()
    m_gross = filled.groupby("month")["gross"].sum()
    out["monthly_win_net"] = float((m_net > 0).mean())
    out["monthly_win_gross"] = float((m_gross > 0).mean())
    out["n_months"] = int(len(m_net))
    # daily net series + NW t-stat
    daily = filled.groupby("exit_date")["net_pnl"].sum().sort_index()
    out["n_trading_days"] = int(len(daily))
    out["t_nw_daily_net"] = float(nw_tstat(daily.values)) if len(daily) >= 10 else float("nan")
    out["largest_day_share"] = (float(daily.abs().max() / abs(daily.sum()))
                                if daily.sum() else None)
    if is_build:
        d = pd.to_datetime(filled["exit_date"])
        pre = filled[d.dt.date <= PRE_TIGHTEN_END]
        post = filled[d.dt.date > PRE_TIGHTEN_END]
        y2025 = filled[(d.dt.date >= dt.date(2025, 1, 1)) & (d.dt.date <= dt.date(2025, 12, 31))]
        out["era"] = {"pre_2024_10": era_stat(pre), "post_2024_10": era_stat(post),
                      "y2025_only": era_stat(y2025)}
    # leverage-explicit CAGR/maxDD (fixed lots=1; report both an aggressive and a
    # conservative capital assumption, per mandate's explicit-leverage requirement)
    if len(daily) >= 2:
        day_outlay = (filled.groupby("entry_date")
                     .apply(lambda g: float((g["entry_fill"] * g["qty"]).sum()), include_groups=False))
        peak_outlay = float(day_outlay.max()) if len(day_outlay) else float(
            (filled["entry_fill"] * filled["qty"]).max())
        first_d, last_d = daily.index.min(), daily.index.max()
        years = max((last_d - first_d).days / 365.25, 1 / 365.25)
        full_idx = pd.date_range(first_d, last_d, freq="D")
        daily_r = daily.reindex(pd.to_datetime(daily.index)).sort_index()
        daily_full = pd.Series(0.0, index=full_idx)
        daily_full.loc[pd.to_datetime(daily_r.index)] = daily_r.values

        def cagr_maxdd(capital: float) -> dict:
            eq = capital + daily_full.cumsum()
            cummax = eq.cummax()
            dd = (eq - cummax) / cummax
            total_return = float(eq.iloc[-1] / capital - 1)
            cagr = (1 + total_return) ** (1 / years) - 1 if (1 + total_return) > 0 else float("nan")
            return {"capital_rs": capital, "cagr": cagr, "maxdd": float(dd.min()),
                    "total_return": total_return,
                    "worst_day_pct_of_capital": float(daily.min() / capital)}

        cap_aggr = max(peak_outlay, 1.0)
        cap_cons = cap_aggr / 0.15
        out["leverage"] = {
            "peak_day_premium_outlay_rs": peak_outlay,
            "years_spanned": years,
            "aggressive_100pct_worst_day_deployed": cagr_maxdd(cap_aggr),
            "conservative_15pct_worst_day_deployed": cagr_maxdd(cap_cons),
        }
    return out


def gate_k1234(m: dict) -> dict:
    if m.get("n_filled", 0) == 0:
        return {"pass_k1234": False, "reason": "no fills"}
    era = m.get("era", {})
    pre = era.get("pre_2024_10", {})
    post = era.get("post_2024_10", {})
    k1 = (m.get("net_sum", 0) > 0 and pre.get("net_sum", 0) > 0 and post.get("net_sum", 0) > 0)
    k2 = np.isfinite(m.get("t_nw_daily_net", np.nan)) and m["t_nw_daily_net"] >= 2.0
    lts = m.get("largest_trade_share_of_net")
    k3 = (lts is None) or (lts <= 0.30)
    k4 = m.get("n_filled", 0) >= 30
    return {"k1_era_consistent_positive": bool(k1), "k2_t_ge_2": bool(k2),
            "k3_conc_le_30pct": bool(k3), "k4_n_ge_30": bool(k4),
            "pass_k1234": bool(k1 and k2 and k3 and k4)}


# ---------------------------------------------------------------- run all pre-registered cells
RESULTS: dict = {"generated": str(dt.datetime.now()), "cost_model": "cost_standards,BROKERAGE_PER_ORDER=25",
                 "build_window": ["2021-05-24", str(BUILD_END)],
                 "forward_window": [str(BUILD_END + dt.timedelta(days=1)), str(FWD_END)],
                 "cells": {}}

DTE_BANDS = [("0-1", 0, 1), ("2-4", 2, 4), ("5-10", 5, 10)]
STRIKES = [("ITM4", -4), ("ATM", 0), ("OTM4", 4)]

b_primary, f_primary = split_build_forward(sig_priorday_reclaim)
log(f"[primary split] build n={len(b_primary)} forward n={len(f_primary)}")


def run_one(cell_name: str, sig_build: pd.DataFrame, sig_fwd: pd.DataFrame, cfg: H.OptCfg,
           save_trades: bool = False) -> dict:
    t0 = time.time()
    bdf = sig_build.copy(); bdf["tag"] = cell_name
    trb = H.run_signals(bdf, cfg) if len(bdf) else pd.DataFrame(columns=H._TRADE_COLS)
    mb = cell_metrics(cell_name, trb, is_build=True)
    mb["gate"] = gate_k1234(mb)
    fdf = sig_fwd.copy(); fdf["tag"] = cell_name
    trf = H.run_signals(fdf, cfg) if len(fdf) else pd.DataFrame(columns=H._TRADE_COLS)
    mf = cell_metrics(cell_name + "_FORWARD", trf, is_build=False)
    el = time.time() - t0
    log(f"[cell] {cell_name}: build n_filled={mb.get('n_filled')} net={mb.get('net_sum')} "
    # --- MEMORY FIX: chain.load_expiry is @lru_cache(maxsize=64) and each expiry df is
    # --- ~40MB, so the cache alone can reach 2.5GB and segfault the process (rc 0xC0000005,
    # --- which killed the first run of this job). Purge after every cell.
    try:
        chain.load_expiry.cache_clear()
    except Exception:
        pass
    import gc as _gc; _gc.collect()
        f"t_nw={mb.get('t_nw_daily_net')} gate={mb['gate'].get('pass_k1234')} "
        f"| forward n_filled={mf.get('n_filled')} net={mf.get('net_sum')} ({el:.1f}s)")
    if save_trades:
        trb.to_csv(OUT / f"{cell_name}__build_trades.csv", index=False)
        if len(trf):
            trf.to_csv(OUT / f"{cell_name}__forward_trades.csv", index=False)
    return {"build": mb, "forward": mf}


log("\n=== PRIMARY 3x3 CORE GRID (sweep_priorday_reclaim, anchor exit) ===")
for dte_label, mn, mx in DTE_BANDS:
    for strike_label, off in STRIKES:
        name = f"sweep_priorday_reclaim__DTE{dte_label}__{strike_label}__anchor"
        cfg = make_cfg(mn, mx, off, "anchor")
        save = (dte_label == "2-4" and strike_label == "ATM")   # keep the anchor's trades for audit
        RESULTS["cells"][name] = run_one(name, b_primary, f_primary, cfg, save_trades=save)

log("\n=== PRIMARY EXIT-SENSITIVITY SWEEP (anchor DTE2-4/ATM) ===")
for exit_name in ["trail25", "trail50", "hardstop30", "hardstop40", "delta1only"]:
    name = f"sweep_priorday_reclaim__DTE2-4__ATM__{exit_name}"
    cfg = make_cfg(2, 4, 0, exit_name)
    RESULTS["cells"][name] = run_one(name, b_primary, f_primary, cfg)

log("\n=== SECONDARY SIGNALS (1 confirmatory cell each, anchor DTE2-4/ATM) ===")
for sig_name in ["sweep_intraday_continue", "volbrk_orb_volfilter",
                "supertrend_15min_ATR10x3", "FADE_sweep_intraday_reclaim"]:
    b, f = split_build_forward(SIGNAL_SETS[sig_name])
    name = f"{sig_name}__DTE2-4__ATM__anchor"
    cfg = make_cfg(2, 4, 0, "anchor")
    RESULTS["cells"][name] = run_one(name, b, f, cfg)

log("\n=== SANITY-5 RE-CHECK: random-entry control at THIS cost model ===")
rng = np.random.default_rng(20260730)
build_days = sorted({d for d in spot.index.date if d <= BUILD_END})
n_rand = 1600
rows = []
for _ in range(n_rand):
    d = build_days[int(rng.integers(0, len(build_days)))]
    m = int(rng.integers(0, 310))
    rows.append({"t": pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=20 + m),
                "direction": int(rng.choice([1, -1]))})
rand_df = pd.DataFrame(rows)
cfg_anchor = make_cfg(2, 4, 0, "anchor")
name = "SANITY_random_control__DTE2-4__ATM__anchor"
empty_fwd = pd.DataFrame(columns=["t", "direction"])
RESULTS["cells"][name] = run_one(name, rand_df, empty_fwd, cfg_anchor, save_trades=True)
sanity_pass = RESULTS["cells"][name]["build"].get("net_sum", 0) < 0
RESULTS["sanity5_pass"] = bool(sanity_pass)
log(f"[SANITY-5] net_sum={RESULTS['cells'][name]['build'].get('net_sum')} "
    f"-> {'PASS (still loses)' if sanity_pass else 'FAIL -- INVESTIGATE BEFORE TRUSTING ANY CELL'}")

# ---------------------------------------------------------------- overall verdict
any_pass = any(c["build"].get("gate", {}).get("pass_k1234") for c in RESULTS["cells"].values()
              if "gate" in c["build"])
RESULTS["n_total_cells"] = len(RESULTS["cells"])
RESULTS["any_cell_passes_k1234"] = bool(any_pass)
RESULTS["VERDICT"] = ("CANDIDATES_FOUND_needs_DSR_PBO_redteam" if any_pass
                     else "ALL_CELLS_KILLED_per_prereg_kill_criteria")
el_total = time.time() - T0
RESULTS["elapsed_sec"] = el_total
log(f"\n==== VERDICT: {RESULTS['VERDICT']} ({RESULTS['n_total_cells']} cells, {el_total:.1f}s) ====")

(OUT / "results.json").write_text(json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
(OUT / "run_log.txt").write_text("\n".join(LOGLINES), encoding="utf-8")
print("DONE")
