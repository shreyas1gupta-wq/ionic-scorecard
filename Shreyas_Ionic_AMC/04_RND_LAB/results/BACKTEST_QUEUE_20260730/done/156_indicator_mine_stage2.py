"""156_indicator_mine_stage2.py -- Arjun Rao, 2026-07-30.

Stage-2 for INDICATOR_MINE_20260730: full naked-option-buying simulation for whichever
cells 155_indicator_mine_signals.py PROMOTED (../INDICATOR_MINE_20260730/promoted_cells.json).
If that list is empty, this writes a one-line report saying so and exits -- a clean NO is a
valid, complete result, not a reason to invent a trade.

Construction locked in PRE_REGISTRATION.md:
  - strike: BS delta (hand-vectorized numpy+scipy, vollib-anchor-verified: S=K=100 t=.25
    r=5% sigma=20% -> delta 0.5695/-0.4305, matches to 1e-9), sigma=same-day VIX/100, T=DTE/365
    (floored at 1 trading hour), r=0. Nearest to 0.60 within [0.40,0.80]. CE if the cell's
    trade_direction is bullish, PE if bearish (REVERSED cells trade the reversed side).
  - entry: option's own next-1-min-bar OPEN strictly after the spot signal bar's close.
  - exit: hard stop at 35% of entry premium (checked on each bar's LOW -- conservative, no
    favourable resolution), else exact-endpoint at the fixed 60-min mark's CLOSE (or 15:25
    close if 60min spills past session end). No profit target -> no stop-vs-target ambiguity.
  - costs: 1.67 pts round trip (Rs25/lot/side + slippage), lot=65.
  - capital: 1 lot/trade; capital base = 3x the 95th-pctile single-trade premium outlay
    observed on BUILD ([OPINION] convention, stated -- no standing dynamic-margin rule exists
    for naked LONG buying).
  - hard kills: >30% profit concentration one trade/day; maxDD>25%; fills on zero option
    volume at the selected leg.
"""
from __future__ import annotations

import datetime as dt
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

QUEUE_155 = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BACKTEST_QUEUE_20260730/done/155_indicator_mine_signals.py"
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/INDICATOR_MINE_20260730"
COST_RT_PTS = 1.67
STOP_FRAC = 0.35
HOLD_MIN = 60
LOT = 65
BUILD_END = dt.date(2025, 12, 31)
OCT2024 = dt.date(2024, 10, 1)
DELTA_LO, DELTA_HI, DELTA_TARGET = 0.40, 0.80, 0.60
COLS = ["timestamp", "strike", "option_type", "volume", "open", "high", "low", "close"]


def bs_delta(S, K, T, r, sigma, is_call):
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1.0 / 365 / 24)
    sigma = np.maximum(np.asarray(sigma, float), 0.01)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    call_delta = norm.cdf(d1)
    return np.where(is_call, call_delta, call_delta - 1.0)


def load_mine155():
    """Import the Stage-1 module (from done/, where the runner moves finished jobs) for its
    signal-generator functions -- reused so Stage-2 tests EXACTLY the same trigger definition
    that was measured, never a re-derivation."""
    import importlib.util
    path = QUEUE_155 if QUEUE_155.exists() else (
        ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BACKTEST_QUEUE_20260730/queue/155_indicator_mine_signals.py")
    spec = importlib.util.spec_from_file_location("mine155", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GEN = None  # filled in main() once mine155 is loaded


def signal_for_label(label: str, m, spot, feat, vix) -> pd.DataFrame:
    fns = {
        "A1_imbalance_call_heavy": lambda: m.imbalance_signals(feat, "call_heavy"),
        "A2_imbalance_put_heavy": lambda: m.imbalance_signals(feat, "put_heavy"),
        "A3_otm_call_concentration": lambda: m.concentration_signals(feat, "call"),
        "A4_otm_put_concentration": lambda: m.concentration_signals(feat, "put"),
        "A5_vwap_proxy_reclaim": lambda: m.vwap_proxy_band_signals(feat, spot, "reclaim"),
        "A6_vwap_proxy_continue": lambda: m.vwap_proxy_band_signals(feat, spot, "continue"),
        "A7_oi_long_buildup": lambda: m.oi_quadrant_signals(feat, "long_buildup"),
        "A8_oi_short_covering": lambda: m.oi_quadrant_signals(feat, "short_covering"),
        "A9_oi_short_buildup": lambda: m.oi_quadrant_signals(feat, "short_buildup"),
        "A10_oi_long_unwind": lambda: m.oi_quadrant_signals(feat, "long_unwind"),
        "B1_vix_rv_divergence_high": lambda: m.vix_rv_divergence_signals(spot, vix, "high"),
        "B2_vix_rv_divergence_low": lambda: m.vix_rv_divergence_signals(spot, vix, "low"),
        "B3_vix_roc_spike": lambda: m.vix_roc_spike_signals(spot, vix),
        "C1_sweep_priorday_reclaim_30min": lambda: m.sweep_priorday_reclaim(spot, "30min"),
        "C2_sweep_priorday_reclaim_45min": lambda: m.sweep_priorday_reclaim(spot, "45min"),
    }
    return fns[label]()


class ChainCache:
    """size-1 cache: only ever holds the CURRENTLY needed expiry's lean frame. Explicit
    clear+gc every time we move to a new expiry (RAM discipline, this box has crashed 3x
    today on unbounded option-chain loads)."""
    def __init__(self):
        self.exp = None
        self.df = None

    def get(self, exp):
        if exp != self.exp:
            del self.df
            gc.collect()
            mapping, _ = chain.build_expiry_index()
            tbl = pq.read_table(mapping[exp], columns=COLS)
            df = tbl.to_pandas()
            df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            self.df = df.drop(columns=["timestamp"])
            self.exp = exp
        return self.df


def simulate_one(cache: ChainCache, sig_t: pd.Timestamp, direction: int, spot_price: float,
                  vix_level: float) -> dict | None:
    day = sig_t.date()
    exp = chain.nearest_expiry(day, min_dte=0, max_dte=7)
    if exp is None:
        return {"skip": "no_expiry"}
    dte = max((exp - day).days, 0)
    T = dte / 365.0
    df = cache.get(exp)
    day_df = df[df["t"].dt.date == day]
    if day_df.empty:
        return {"skip": "no_chain_data_this_day"}
    is_call = direction > 0
    otype = "CE" if is_call else "PE"
    side_df = day_df[day_df["option_type"] == otype]
    strikes = np.sort(side_df["strike"].unique())
    if len(strikes) == 0:
        return {"skip": "no_strikes"}
    sigma = max(vix_level, 5.0) / 100.0 if np.isfinite(vix_level) else 0.15
    deltas = bs_delta(spot_price, strikes, T, 0.0, sigma, is_call)
    absd = np.abs(deltas)
    band = (absd >= DELTA_LO) & (absd <= DELTA_HI)
    if not band.any():
        return {"skip": "no_strike_in_delta_band"}
    cand_strikes = strikes[band]
    cand_deltas = absd[band]
    k = cand_strikes[np.argmin(np.abs(cand_deltas - DELTA_TARGET))]
    leg = side_df[side_df["strike"] == k].set_index("t").sort_index()
    after = leg[leg.index > sig_t]
    if after.empty:
        return {"skip": "no_bar_after_signal"}
    entry_row = after.iloc[0]
    entry_t = after.index[0]
    entry_px = entry_row["open"]
    entry_vol = entry_row["volume"]
    if not np.isfinite(entry_px) or entry_px <= 0:
        return {"skip": "bad_entry_price"}
    if entry_vol <= 0:
        return {"skip": "zero_volume_entry", "hard_kill": True}
    stop_level = entry_px * (1 - STOP_FRAC)
    flat_cutoff = pd.Timestamp(day) + pd.Timedelta(hours=15, minutes=25)
    hold_cutoff = min(entry_t + pd.Timedelta(minutes=HOLD_MIN), flat_cutoff)
    path = leg[(leg.index > entry_t) & (leg.index <= flat_cutoff)]
    exit_px, exit_t, reason = None, None, None
    for t, row in path.iterrows():
        if row["low"] <= stop_level:
            exit_px, exit_t, reason = stop_level, t, "stop"
            break
        if t >= hold_cutoff:
            exit_px, exit_t, reason = row["close"], t, "time"
            break
    if exit_px is None:
        if path.empty:
            return {"skip": "no_bars_after_entry"}
        exit_px, exit_t, reason = path.iloc[-1]["close"], path.index[-1], "eod_fallback"
    exit_vol = path.loc[exit_t, "volume"] if exit_t in path.index else np.nan
    gross_pts = exit_px - entry_px
    net_pts = gross_pts - COST_RT_PTS
    return {
        "date": day, "expiry": str(exp), "dte": dte, "strike": int(k), "type": otype,
        "delta_at_entry": float(cand_deltas[np.argmin(np.abs(cand_deltas - DELTA_TARGET))]),
        "entry_t": entry_t, "entry_px": float(entry_px), "entry_vol": int(entry_vol),
        "exit_t": exit_t, "exit_px": float(exit_px), "exit_reason": reason,
        "exit_vol": float(exit_vol) if pd.notna(exit_vol) else None,
        "gross_pts": float(gross_pts), "net_pts": float(net_pts),
    }


def run_stage2_for_cell(label: str, direction_sign: int, m, spot, feat, vix, cache: ChainCache) -> dict:
    sig = signal_for_label(label, m, spot, feat, vix)
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    sig["eff_dir"] = sig["dir"] * direction_sign   # apply REVERSED flag if any
    build = sig[sig["date"] <= BUILD_END]
    trades = []
    skips = {}
    vix_by_day = vix.groupby(vix.index.date).mean()
    for _, r in build.iterrows():
        sig_t = pd.Timestamp(r["t"])
        vix_lvl = vix_by_day.get(sig_t.date(), np.nan)
        # spot price at signal time (last close at/before t)
        pos = spot.index.searchsorted(sig_t, side="right") - 1
        if pos < 0:
            continue
        spot_price = float(spot["close"].iloc[pos])
        res = simulate_one(cache, sig_t, int(r["eff_dir"]), spot_price, vix_lvl)
        if res is None or "skip" in res:
            reason = res.get("skip", "unknown") if res else "none"
            skips[reason] = skips.get(reason, 0) + 1
            continue
        trades.append(res)
    tdf = pd.DataFrame(trades)
    out = {"label": label, "n_signals_build": int(len(build)), "n_trades": int(len(tdf)),
           "skips": skips}
    if tdf.empty:
        out["verdict"] = "DEAD"; out["reason"] = "no executable trades (see skips)"
        return out
    tdf["date"] = pd.to_datetime(tdf["date"])
    tdf["era"] = np.where(tdf["date"].dt.date >= OCT2024, "post_oct2024", "pre_oct2024")
    net = tdf["net_pts"]
    out["median_net_pts"] = float(net.median())
    wins, losses = net[net > 0], net[net <= 0]
    out["rr"] = float(wins.mean() / abs(losses.mean())) if len(losses) and losses.mean() != 0 else None
    out["win_rate"] = float((net > 0).mean())
    by_day = tdf.groupby(tdf["date"].dt.date)["net_pts"].sum()
    out["largest_day_share"] = float(by_day.abs().max() / abs(by_day.sum())) if by_day.sum() else None
    out["hard_kill_concentration"] = out["largest_day_share"] is not None and out["largest_day_share"] > 0.30
    out["entry_vol_min"] = int(tdf["entry_vol"].min())
    out["entry_vol_median"] = float(tdf["entry_vol"].median())
    out["pre_oct2024_mean_net"] = float(tdf.loc[tdf["era"] == "pre_oct2024", "net_pts"].mean()) if (tdf["era"] == "pre_oct2024").any() else None
    out["post_oct2024_mean_net"] = float(tdf.loc[tdf["era"] == "post_oct2024", "net_pts"].mean()) if (tdf["era"] == "post_oct2024").any() else None

    # capital / CAGR convention (locked in PRE_REGISTRATION.md)
    outlay = tdf["entry_px"] * LOT
    capital = 3 * float(outlay.quantile(0.95))
    tdf_sorted = tdf.sort_values("date")
    equity = capital + (tdf_sorted["net_pts"] * LOT).cumsum()
    peak = equity.cummax()
    dd = (equity - peak) / peak
    out["capital_base_rs"] = round(capital, 0)
    out["maxDD_pct"] = float(dd.min())
    out["hard_kill_maxDD"] = out["maxDD_pct"] < -0.25
    yrs = max((tdf_sorted["date"].max() - tdf_sorted["date"].min()).days / 365.25, 0.05)
    final_eq = float(equity.iloc[-1])
    out["CAGR_pct"] = (final_eq / capital) ** (1 / yrs) - 1 if final_eq > 0 and capital > 0 else None
    out["years_span"] = round(yrs, 2)

    if out["hard_kill_concentration"]:
        out["verdict"] = "DEAD"; out["reason"] = "profit concentration >30% one day"
    elif out["hard_kill_maxDD"]:
        out["verdict"] = "DEAD"; out["reason"] = f"maxDD {out['maxDD_pct']:.1%} > 25% cap"
    elif out["entry_vol_min"] <= 0:
        out["verdict"] = "DEAD"; out["reason"] = "zero-volume fill present"
    else:
        median_pass = out["median_net_pts"] > 5.0
        rr_pass = (out["rr"] or 0) >= 1.5
        out["verdict"] = "FORWARD-TEST CANDIDATE" if (median_pass and rr_pass) else "UNDERPOWERED-UNRESOLVED"
        out["meets_principal_bar_median>5_AND_RR>=1.5"] = bool(median_pass and rr_pass)
    tdf.to_csv(OUT / f"stage2_trades_{label}.csv", index=False)
    return out


def main():
    promoted_path = OUT / "promoted_cells.json"
    if not promoted_path.exists():
        (OUT / "stage2_report.json").write_text(json.dumps(
            {"verdict": "NOT_RUN", "reason": "promoted_cells.json missing -- 155 has not finished"}, indent=2))
        print("[stage2] promoted_cells.json missing, nothing to do", flush=True)
        return
    promoted = json.loads(promoted_path.read_text())
    if not promoted:
        report = {"verdict": "CLEAN_NO", "reason": "zero cells promoted from Stage-1 -- no option "
                  "simulation to run. A clean NO is a complete, valid result.", "cells": {}}
        (OUT / "stage2_report.json").write_text(json.dumps(report, indent=2))
        print("[stage2] 0 cells promoted -- writing CLEAN_NO and exiting", flush=True)
        return

    m = load_mine155()
    stage1 = json.loads((OUT / "stage1_report.json").read_text())
    spot = m.load_spot()
    feat = m.load_feat()
    vix = m.load_vix()
    cache = ChainCache()

    out = {}
    for label in promoted:
        cell1 = stage1["cells"][label]
        direction_sign = -1 if "REVERSED" in cell1.get("trade_direction", "") else 1
        t0 = time.time()
        res = run_stage2_for_cell(label, direction_sign, m, spot, feat, vix, cache)
        res["elapsed_s"] = round(time.time() - t0, 1)
        out[label] = res
        print(f"[stage2] {label}: n_trades={res.get('n_trades')} verdict={res.get('verdict')} "
              f"median={res.get('median_net_pts')} rr={res.get('rr')} "
              f"CAGR={res.get('CAGR_pct')} maxDD={res.get('maxDD_pct')} [{res['elapsed_s']}s]", flush=True)

    (OUT / "stage2_report.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("[stage2] DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
