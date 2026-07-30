"""Gate-3 measurement: SIGNAL STRENGTH vs COST BUDGET for intraday NIFTY directional
option buying. Measurement only -- no option pricing, no P&L engine.

Pre-registered in PRE_REGISTRATION.md (written before this was run). Reuses load_spot /
resample / nw_tstat from the sibling stage1_signal_test.py (EMA-cross arm already measured
there); this script adds Supertrend, volatility-breakout, liquidity-sweep, weekly/monthly/
round-number S/R, and confluence-stacking triggers, all measured the same way.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
STAGE1_DIR = OUT.parent
sys.path.insert(0, str(STAGE1_DIR))
from stage1_signal_test import load_spot, resample, nw_tstat  # noqa: E402

BUILD_END = dt.date(2025, 12, 31)
ENTRY_START, ENTRY_END = dt.time(9, 20), dt.time(14, 30)
FLAT_H, FLAT_M = 15, 25
HORIZONS = [15, 30, 60, 120]
BREAKEVEN_PCT = 0.0030      # long-option breakeven bar (0.30%)
FUT_COST_PTS = 6.0          # conservative futures round-trip + slippage bar
T_BAR = 2.0
CONC_BAR = 0.30

# ----------------------------------------------------------------------------
# shared plumbing (mirrors stage1_signal_test.py conventions)
# ----------------------------------------------------------------------------

def clip_entry_window(df: pd.DataFrame, tcol: str = "t") -> pd.DataFrame:
    if df.empty:
        return df
    tod = pd.to_datetime(df[tcol]).dt.time
    return df[(tod >= ENTRY_START) & (tod <= ENTRY_END)].sort_values(tcol).reset_index(drop=True)


def forward_stats(spot: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    """Signed forward returns (% and points) + MFE/MAE. Entry fills at the NEXT 1-min
    bar's open after the signal bar closes (no same-bar lookahead)."""
    out = []
    by_day = {d: g for d, g in spot.groupby(spot.index.date)}
    for _, r in entries.iterrows():
        t0, sgn = r["t"], int(r["dir"])
        day = by_day.get(pd.Timestamp(t0).date())
        if day is None:
            continue
        fwd = day[day.index > t0]
        if fwd.empty:
            continue
        e = float(fwd["open"].iloc[0])
        if not np.isfinite(e) or e <= 0:
            continue
        rec = {"t": t0, "dir": sgn, "entry": e, "date": pd.Timestamp(t0).date()}
        for h in HORIZONS:
            w = fwd[fwd.index <= t0 + pd.Timedelta(minutes=h)]
            if len(w):
                px = float(w["close"].iloc[-1])
                rec[f"r{h}_pct"] = sgn * (px / e - 1)
                rec[f"r{h}_pts"] = sgn * (px - e)
            else:
                rec[f"r{h}_pct"] = np.nan
                rec[f"r{h}_pts"] = np.nan
        flat_cut = pd.Timestamp(pd.Timestamp(t0).date()) + pd.Timedelta(hours=FLAT_H, minutes=FLAT_M)
        flat = fwd[fwd.index <= flat_cut]
        if len(flat):
            px = float(flat["close"].iloc[-1])
            rec["reod_pct"] = sgn * (px / e - 1)
            rec["reod_pts"] = sgn * (px - e)
            hi, lo = float(flat["high"].max()), float(flat["low"].min())
            rec["mfe_pct"] = (hi / e - 1) if sgn > 0 else (1 - lo / e)
            rec["mae_pct"] = (lo / e - 1) if sgn > 0 else (1 - hi / e)
        else:
            rec["reod_pct"] = rec["reod_pts"] = rec["mfe_pct"] = rec["mae_pct"] = np.nan
        out.append(rec)
    return pd.DataFrame(out)


HCOLS_PCT = [f"r{h}_pct" for h in HORIZONS] + ["reod_pct"]
HCOLS_PTS = [f"r{h}_pts" for h in HORIZONS] + ["reod_pts"]
HLABELS = [f"+{h}m" for h in HORIZONS] + ["to15:25"]


def summarize_cell(f: pd.DataFrame) -> dict:
    d = {"n": int(len(f))}
    if f.empty:
        return d
    per_h = {}
    for lbl, cp, ct in zip(HLABELS, HCOLS_PCT, HCOLS_PTS):
        x = f[cp].dropna()
        xp = f[ct].dropna()
        if len(x) < 10:
            continue
        per_h[lbl] = {
            "mean_pct": round(100 * x.mean(), 4),
            "mean_pts": round(float(xp.mean()), 3),
            "hit": round(float((x > 0).mean()), 4),
            "t_nw": round(float(nw_tstat(x.values)), 3),
            "n": int(len(x)),
        }
    d["horizons"] = per_h
    if per_h:
        best_lbl = max(per_h, key=lambda k: per_h[k]["mean_pct"])
        d["best_horizon"] = best_lbl
        d["best"] = per_h[best_lbl]
        # concentration on the best horizon's points column (pts, not pct, for $ realism)
        best_pts_col = HCOLS_PTS[HLABELS.index(best_lbl)]
        per_day = f.groupby("date")[best_pts_col].sum()
        tot = per_day.sum()
        d["largest_day_share"] = round(float(per_day.abs().max() / abs(tot)), 4) if tot else None
    if f["mfe_pct"].notna().sum() > 10:
        mfe, mae = f["mfe_pct"].dropna(), f["mae_pct"].dropna()
        d["mfe_pct"] = round(100 * mfe.mean(), 4)
        d["mae_pct"] = round(100 * mae.mean(), 4)
        d["mfe_over_mae"] = round(float(mfe.mean() / abs(mae.mean())), 3) if mae.mean() else None
    return d


def gate(cell: dict) -> dict:
    if "best" not in cell:
        return {"pass": False, "reason": "insufficient n"}
    b = cell["best"]
    g1 = b["mean_pct"] >= 100 * BREAKEVEN_PCT
    g2 = b["mean_pts"] >= FUT_COST_PTS
    g3 = np.isfinite(b["t_nw"]) and b["t_nw"] >= T_BAR
    conc = cell.get("largest_day_share")
    g4 = conc is not None and conc <= CONC_BAR
    return {
        "g1_magnitude_pass": bool(g1), "g2_futcost_pass": bool(g2),
        "g3_tstat_pass": bool(g3), "g4_conc_pass": bool(g4),
        "pass": bool(g1 and g3 and g4),
    }


def run_cell(spot, sig, label):
    if sig.empty:
        return None
    sig = sig.copy()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    b = sig[sig["date"] <= BUILD_END]
    fw = sig[sig["date"] > BUILD_END]
    fb = forward_stats(spot, b)
    ffwd = forward_stats(spot, fw) if len(fw) else pd.DataFrame()
    build = summarize_cell(fb)
    forward = summarize_cell(ffwd) if len(ffwd) else {"n": int(len(fw))}
    g = gate(build)
    print(f"[{label}] build_n={build['n']} forward_n={forward.get('n', 0)} "
          f"best={build.get('best_horizon')} mean={build.get('best', {}).get('mean_pct')}% "
          f"({build.get('best', {}).get('mean_pts')}pts) t={build.get('best', {}).get('t_nw')} "
          f"conc={build.get('largest_day_share')} -> "
          f"{'PASS' if g['pass'] else 'FAIL'}", flush=True)
    return {"label": label, "n_signals_build": int(len(b)), "n_signals_forward": int(len(fw)),
            "build": build, "forward": forward, "gate": g}


# ----------------------------------------------------------------------------
# 1. Supertrend
# ----------------------------------------------------------------------------

def supertrend_flips(bars: pd.DataFrame, period: int, mult: float) -> pd.DataFrame:
    rows = []
    for _, day in bars.groupby(bars.index.date):
        n = len(day)
        if n < period + 2:
            continue
        high, low, close = day["high"].values, day["low"].values, day["close"].values
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]
        tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
        atr = pd.Series(tr).rolling(period, min_periods=period).mean().values
        hl2 = (high + low) / 2.0
        ub_basic = hl2 + mult * atr
        lb_basic = hl2 - mult * atr
        ub = ub_basic.copy()
        lb = lb_basic.copy()
        trend = np.full(n, np.nan)
        first_valid = period - 1
        if np.isnan(atr[first_valid]):
            continue
        trend[first_valid] = 1.0 if close[first_valid] > ub[first_valid] else -1.0
        for i in range(first_valid + 1, n):
            if np.isnan(atr[i]):
                continue
            if ub_basic[i] < ub[i - 1] or close[i - 1] > ub[i - 1]:
                ub[i] = ub_basic[i]
            else:
                ub[i] = ub[i - 1]
            if lb_basic[i] > lb[i - 1] or close[i - 1] < lb[i - 1]:
                lb[i] = lb_basic[i]
            else:
                lb[i] = lb[i - 1]
            prev_t = trend[i - 1]
            if np.isnan(prev_t):
                trend[i] = 1.0 if close[i] > ub[i] else -1.0
            elif prev_t == 1.0:
                trend[i] = -1.0 if close[i] < lb[i] else 1.0
            else:
                trend[i] = 1.0 if close[i] > ub[i] else -1.0
        idx = day.index
        for i in range(first_valid + 1, n):
            if np.isnan(trend[i]) or np.isnan(trend[i - 1]):
                continue
            if trend[i] == 1.0 and trend[i - 1] == -1.0:
                rows.append({"t": idx[i], "dir": 1})
            elif trend[i] == -1.0 and trend[i - 1] == 1.0:
                rows.append({"t": idx[i], "dir": -1})
    return clip_entry_window(pd.DataFrame(rows))


# ----------------------------------------------------------------------------
# 2. Volatility breakout (5-min bars)
# ----------------------------------------------------------------------------

def wilder_atr(day: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = day["high"], day["low"], day["close"]
    prev_close = close.shift(1).fillna(close.iloc[0])
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def keltner_squeeze_release(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, day in bars.groupby(bars.index.date):
        if len(day) < 22:
            continue
        c = day["close"]
        sma20 = c.rolling(20, min_periods=20).mean()
        std20 = c.rolling(20, min_periods=20).std()
        bb_u, bb_l = sma20 + 2 * std20, sma20 - 2 * std20
        ema20 = c.ewm(span=20, adjust=False).mean()
        atr10 = wilder_atr(day, 10)
        kc_u, kc_l = ema20 + 1.5 * atr10, ema20 - 1.5 * atr10
        squeeze = (bb_l > kc_l) & (bb_u < kc_u)
        release = squeeze.shift(1).fillna(False) & (~squeeze.fillna(False))
        for t in day.index[release]:
            sgn = 1 if c.loc[t] >= ema20.loc[t] else -1
            rows.append({"t": t, "dir": sgn})
    return clip_entry_window(pd.DataFrame(rows))


def atr_expansion(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, day in bars.groupby(bars.index.date):
        if len(day) < 16:
            continue
        high, low, close, openp = day["high"], day["low"], day["close"], day["open"]
        prev_close = close.shift(1).fillna(close.iloc[0])
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        prior_atr = tr.shift(1).rolling(14, min_periods=14).mean()
        bar_range = high - low
        expand = bar_range > 1.5 * prior_atr
        for t in day.index[expand.fillna(False)]:
            sgn = 1 if close.loc[t] >= openp.loc[t] else -1
            rows.append({"t": t, "dir": sgn})
    return clip_entry_window(pd.DataFrame(rows))


def orb_vol_filter(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, day in bars.groupby(bars.index.date):
        if len(day) < 16:
            continue
        tod = day.index.time
        orr = day[(tod >= dt.time(9, 15)) & (tod < dt.time(9, 45))]
        if orr.empty:
            continue
        or_hi, or_lo = orr["high"].max(), orr["low"].min()
        high, low, close = day["high"], day["low"], day["close"]
        prev_close = close.shift(1).fillna(close.iloc[0])
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean()
        rest = day[tod >= dt.time(9, 45)]
        done_up = done_dn = False
        # vol filter = ATR now vs ATR 14 bars ago (expanding), first breakout each side/day
        atr_prior14 = atr.shift(14)
        for t in rest.index:
            if done_up and done_dn:
                break
            expanding = bool(atr.loc[t] > atr_prior14.loc[t]) if pd.notna(atr_prior14.loc[t]) else False
            if not done_up and close.loc[t] > or_hi and expanding:
                rows.append({"t": t, "dir": 1}); done_up = True
            if not done_dn and close.loc[t] < or_lo and expanding:
                rows.append({"t": t, "dir": -1}); done_dn = True
    return clip_entry_window(pd.DataFrame(rows))


# ----------------------------------------------------------------------------
# 3. Liquidity sweep (15-min bars)
# ----------------------------------------------------------------------------

def sweep_signals(bars15: pd.DataFrame) -> dict[str, pd.DataFrame]:
    daily_hi = bars15.groupby(bars15.index.date)["high"].max()
    daily_lo = bars15.groupby(bars15.index.date)["low"].min()
    days_sorted = sorted(daily_hi.index)
    prior_hi = {d: daily_hi[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}
    prior_lo = {d: daily_lo[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}

    out = {"priorday_reclaim": [], "priorday_continue": [], "intraday_reclaim": [], "intraday_continue": []}
    for d, day in bars15.groupby(bars15.index.date):
        if d not in prior_hi:
            continue
        ph, pl = prior_hi[d], prior_lo[d]
        # PIT-safe "intraday swing so far": running day high/low established >=2 bars ago
        day_hi_so_far = day["high"].cummax().shift(2)
        day_lo_so_far = day["low"].cummin().shift(2)
        for t, row in day.iterrows():
            hi, lo, close = row["high"], row["low"], row["close"]
            # prior-day high sweep
            if hi > ph:
                if close < ph:
                    out["priorday_reclaim"].append({"t": t, "dir": -1})
                else:
                    out["priorday_continue"].append({"t": t, "dir": 1})
            if lo < pl:
                if close > pl:
                    out["priorday_reclaim"].append({"t": t, "dir": 1})
                else:
                    out["priorday_continue"].append({"t": t, "dir": -1})
            # intraday swing sweep (needs 2-bar-old reference)
            ihi, ilo = day_hi_so_far.loc[t], day_lo_so_far.loc[t]
            if pd.notna(ihi) and hi > ihi:
                if close < ihi:
                    out["intraday_reclaim"].append({"t": t, "dir": -1})
                else:
                    out["intraday_continue"].append({"t": t, "dir": 1})
            if pd.notna(ilo) and lo < ilo:
                if close > ilo:
                    out["intraday_reclaim"].append({"t": t, "dir": 1})
                else:
                    out["intraday_continue"].append({"t": t, "dir": -1})
    return {k: clip_entry_window(pd.DataFrame(v)) for k, v in out.items()}


# ----------------------------------------------------------------------------
# 4. Weekly / monthly S/R + round numbers (15-min bars)
# ----------------------------------------------------------------------------

def daily_bars(spot: pd.DataFrame) -> pd.DataFrame:
    g = spot.groupby(spot.index.date)
    d = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    d.index = pd.to_datetime(d.index)
    return d


def week_month_levels(daily: pd.DataFrame) -> tuple[dict, dict]:
    wk = daily.copy()
    wk["period"] = wk.index.to_period("W-FRI")
    wk_agg = wk.groupby("period").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    wk_periods = sorted(wk_agg.index)
    wk_prior = {p: wk_agg.loc[wk_periods[i - 1]] for i, p in enumerate(wk_periods) if i > 0}
    day_to_wk_levels = {}
    for d in daily.index:
        p = pd.Timestamp(d).to_period("W-FRI")
        if p in wk_prior:
            day_to_wk_levels[d.date()] = wk_prior[p]

    mo = daily.copy()
    mo["period"] = mo.index.to_period("M")
    mo_agg = mo.groupby("period").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    mo_periods = sorted(mo_agg.index)
    mo_prior = {p: mo_agg.loc[mo_periods[i - 1]] for i, p in enumerate(mo_periods) if i > 0}
    day_to_mo_levels = {}
    for d in daily.index:
        p = pd.Timestamp(d).to_period("M")
        if p in mo_prior:
            day_to_mo_levels[d.date()] = mo_prior[p]
    return day_to_wk_levels, day_to_mo_levels


def _dedup(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(["t", "dir"]) if not df.empty else df


def level_breakout_reject(bars15: pd.DataFrame, day_to_levels: dict, level_cols=("high", "low", "close")) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each day, test breakout-through and rejection-from vs each of the day's
    prior-period high/low/close levels. Touch/away tolerance = 0.05% of level."""
    brk, rej = [], []
    for d, day in bars15.groupby(bars15.index.date):
        lv = day_to_levels.get(d)
        if lv is None:
            continue
        levels = [float(lv[c]) for c in level_cols]
        prev_close = day["close"].shift(1)
        for t, row in day.iterrows():
            pc = prev_close.loc[t]
            if pd.isna(pc):
                continue
            hi, lo, close = row["high"], row["low"], row["close"]
            for lvl in levels:
                tol = 0.0005 * lvl
                # breakout-through: prev close one side, this close other side
                if pc < lvl <= close:
                    brk.append({"t": t, "dir": 1})
                elif pc > lvl >= close:
                    brk.append({"t": t, "dir": -1})
                # rejection-from: touches within tol, closes back away by >=tol
                if hi >= lvl - tol and close <= lvl - tol:
                    rej.append({"t": t, "dir": -1})
                if lo <= lvl + tol and close >= lvl + tol:
                    rej.append({"t": t, "dir": 1})
    return clip_entry_window(_dedup(pd.DataFrame(brk))), clip_entry_window(_dedup(pd.DataFrame(rej)))


def round_number_levels(bars15: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    brk, rej = [], []
    for d, day in bars15.groupby(bars15.index.date):
        prev_close = day["close"].shift(1)
        for t, row in day.iterrows():
            pc = prev_close.loc[t]
            if pd.isna(pc):
                continue
            hi, lo, close = row["high"], row["low"], row["close"]
            for lvl in (np.floor(pc / 100.0) * 100.0, np.ceil(pc / 100.0) * 100.0):
                tol = 0.0005 * lvl
                if pc < lvl <= close:
                    brk.append({"t": t, "dir": 1})
                elif pc > lvl >= close:
                    brk.append({"t": t, "dir": -1})
                if hi >= lvl - tol and close <= lvl - tol:
                    rej.append({"t": t, "dir": -1})
                if lo <= lvl + tol and close >= lvl + tol:
                    rej.append({"t": t, "dir": 1})
    return clip_entry_window(pd.DataFrame(brk).drop_duplicates(["t", "dir"])), \
        clip_entry_window(pd.DataFrame(rej).drop_duplicates(["t", "dir"]))


# ----------------------------------------------------------------------------
# 5. Confluence stacking (15-min bars)
# ----------------------------------------------------------------------------

def confluence_buckets(spot, bars15, st_flips, atr_exp_15, sweeps, sr_levels) -> dict:
    """Union all condition signals into one long table, dedupe within a bar+dir to a
    stack_count, then bucket. Uses the 15-min versions of each condition family."""
    frames = []
    for name, df in [("supertrend", st_flips), ("atr_expand", atr_exp_15),
                      ("sweep", pd.concat(list(sweeps.values()), ignore_index=True) if sweeps else pd.DataFrame()),
                      ("sr", pd.concat(sr_levels, ignore_index=True) if sr_levels else pd.DataFrame())]:
        if df is None or df.empty:
            continue
        d = df[["t", "dir"]].drop_duplicates()
        d["cond"] = name
        frames.append(d)
    if not frames:
        return {}
    long = pd.concat(frames, ignore_index=True).sort_values("t")
    # snap each signal's timestamp to its 15-min bar boundary (backward asof) so conditions
    # on different native timeframes can be compared at the same bar
    bar_index = pd.DataFrame({"t15": bars15.index}).sort_values("t15")
    long = pd.merge_asof(long, bar_index, left_on="t", right_on="t15", direction="backward")
    long = long.dropna(subset=["t15"])
    grp = long.groupby(["t15", "dir"])["cond"].nunique().reset_index(name="stack_count")
    grp = grp.rename(columns={"t15": "t"})
    buckets = {}
    for k in sorted(grp["stack_count"].unique()):
        sub = grp[grp["stack_count"] == k][["t", "dir"]]
        buckets[int(k)] = clip_entry_window(sub)
    return buckets


# ----------------------------------------------------------------------------
def main():
    spot = load_spot()
    print(f"[spot] {len(spot):,} 1-min bars  {spot.index[0]} .. {spot.index[-1]}", flush=True)
    bars5 = resample(spot, "5min")
    bars15 = resample(spot, "15min")
    daily = daily_bars(spot)
    wk_lv, mo_lv = week_month_levels(daily)

    report = {"pre_registration": "PRE_REGISTRATION.md", "breakeven_pct": 100 * BREAKEVEN_PCT,
              "fut_cost_pts_bar": FUT_COST_PTS, "cells": {}}

    print("\n=== 1. SUPERTREND ===", flush=True)
    st_cache = {}
    for tf_name, bars in [("5min", bars5), ("15min", bars15)]:
        for period, mult in [(10, 3), (7, 2), (14, 3)]:
            sig = supertrend_flips(bars, period, mult)
            label = f"supertrend_{tf_name}_ATR{period}_x{mult}"
            st_cache[(tf_name, period, mult)] = sig
            report["cells"][label] = run_cell(spot, sig, label)

    print("\n=== 2. VOLATILITY BREAKOUT (5min) ===", flush=True)
    kc_sig = keltner_squeeze_release(bars5)
    report["cells"]["volbrk_keltner_squeeze_release"] = run_cell(spot, kc_sig, "volbrk_keltner_squeeze_release")
    atrexp5_sig = atr_expansion(bars5)
    report["cells"]["volbrk_atr_expansion"] = run_cell(spot, atrexp5_sig, "volbrk_atr_expansion")
    orb_sig = orb_vol_filter(bars5)
    report["cells"]["volbrk_orb_volfilter"] = run_cell(spot, orb_sig, "volbrk_orb_volfilter")

    print("\n=== 3. LIQUIDITY SWEEP (15min) ===", flush=True)
    sweeps = sweep_signals(bars15)
    for name, sig in sweeps.items():
        label = f"sweep_{name}"
        report["cells"][label] = run_cell(spot, sig, label)

    print("\n=== 4. WEEKLY/MONTHLY/ROUND S-R (15min) ===", flush=True)
    wk_brk, wk_rej = level_breakout_reject(bars15, wk_lv)
    mo_brk, mo_rej = level_breakout_reject(bars15, mo_lv)
    rn_brk, rn_rej = round_number_levels(bars15)
    sr_cells = {"sr_week_breakout": wk_brk, "sr_week_reject": wk_rej,
                "sr_month_breakout": mo_brk, "sr_month_reject": mo_rej,
                "sr_round_breakout": rn_brk, "sr_round_reject": rn_rej}
    for label, sig in sr_cells.items():
        report["cells"][label] = run_cell(spot, sig, label)

    print("\n=== 5. CONFLUENCE STACKING (15min) ===", flush=True)
    atrexp15_sig = atr_expansion(bars15)
    st_15 = st_cache[("15min", 10, 3)]
    sr_frames = [wk_brk, wk_rej, mo_brk, mo_rej, rn_brk, rn_rej]
    buckets = confluence_buckets(spot, bars15, st_15, atrexp15_sig, sweeps, sr_frames)
    confluence_report = {}
    for k, sig in sorted(buckets.items()):
        label = f"confluence_stack{k}"
        confluence_report[label] = run_cell(spot, sig, label)
    report["cells"].update(confluence_report)
    report["confluence_stack_labels"] = sorted(confluence_report.keys())

    any_pass = any(c and c.get("gate", {}).get("pass") for c in report["cells"].values())
    report["VERDICT"] = "SUSPECT_PASS_needs_forward_validation" if any_pass else "ALL_FAIL_signal_magnitude_below_option_budget"
    (OUT / "signal_budget_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n==== VERDICT: {report['VERDICT']} ====", flush=True)


if __name__ == "__main__":
    sys.exit(main())
