"""Stage-1 cheap falsification: does an INTRADAY EMA cross on NIFTY 50 predict any
signed forward spot move big enough to clear the long-option breakeven (~0.30-0.50%)?

Index-only, no option pricing. Pre-registered kill criteria in
04_RND_LAB/ideas/20260729_intraday_ema_option_buying.md.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OUT = Path(__file__).parent
NIFTY_INDEX = Path(
    r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
    r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m"
    r"\index\NIFTY.parquet"
)

BUILD_END = dt.date(2025, 12, 31)
ENTRY_START, ENTRY_END = "09:20", "14:30"   # so every trade can be flat by 15:25
FLAT_BY = "15:25"
HORIZONS = [30, 60, 120]                    # minutes
BREAKEVEN = 0.0030                          # pre-registered magnitude bar (0.30%)
N_PLACEBO = 100
SEED = 20260729

GRID = [("5min", 9, 21), ("5min", 20, 50), ("15min", 9, 21)]


def load_spot() -> pd.DataFrame:
    df = pq.read_table(NIFTY_INDEX).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").set_index("t").sort_index()
    # LANDMINE #2: pre-open auction. Real session is 09:15-15:30.
    tod = df.index.time
    df = df[(tod >= dt.time(9, 15)) & (tod <= dt.time(15, 30))]
    return df[["open", "high", "low", "close"]]


def resample(spot: pd.DataFrame, rule: str) -> pd.DataFrame:
    g = spot.groupby(spot.index.date)
    parts = []
    for _, day in g:
        r = day.resample(rule, origin=day.index[0], label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        parts.append(r)
    return pd.concat(parts).sort_index()


def signals(bars: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    """EMA cross events, computed per-day so no EMA state leaks across sessions."""
    rows = []
    for _, day in bars.groupby(bars.index.date):
        if len(day) < slow + 2:
            continue
        c = day["close"]
        ef = c.ewm(span=fast, adjust=False).mean()
        es = c.ewm(span=slow, adjust=False).mean()
        up = (ef > es) & (ef.shift(1) <= es.shift(1))
        dn = (ef < es) & (ef.shift(1) >= es.shift(1))
        for t in day.index[up]:
            rows.append({"t": t, "dir": 1})
        for t in day.index[dn]:
            rows.append({"t": t, "dir": -1})
    s = pd.DataFrame(rows)
    if s.empty:
        return s
    tod = pd.to_datetime(s["t"]).dt.time
    s = s[(tod >= pd.Timestamp(ENTRY_START).time()) & (tod <= pd.Timestamp(ENTRY_END).time())]
    return s.sort_values("t").reset_index(drop=True)


def forward_stats(spot: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    """Signed forward returns + MFE/MAE for each entry. Entry fills at the NEXT 1-min
    bar's open after the signal bar closes (no same-bar lookahead)."""
    idx = spot.index
    out = []
    by_day = {d: g for d, g in spot.groupby(spot.index.date)}
    for _, r in entries.iterrows():
        t0, sgn = r["t"], int(r["dir"])
        day = by_day.get(t0.date())
        if day is None:
            continue
        fwd = day[day.index > t0]
        if fwd.empty:
            continue
        e = float(fwd["open"].iloc[0])
        if not np.isfinite(e) or e <= 0:
            continue
        rec = {"t": t0, "dir": sgn, "entry": e, "date": t0.date()}
        for h in HORIZONS:
            w = fwd[fwd.index <= t0 + pd.Timedelta(minutes=h)]
            rec[f"r{h}"] = sgn * (float(w["close"].iloc[-1]) / e - 1) if len(w) else np.nan
        flat = fwd[fwd.index <= pd.Timestamp(t0.date()) + pd.Timedelta(
            hours=int(FLAT_BY[:2]), minutes=int(FLAT_BY[3:]))]
        rec["r_eod"] = sgn * (float(flat["close"].iloc[-1]) / e - 1) if len(flat) else np.nan
        if len(flat):
            hi, lo = float(flat["high"].max()), float(flat["low"].min())
            rec["mfe"] = (hi / e - 1) if sgn > 0 else (1 - lo / e)
            rec["mae"] = (lo / e - 1) if sgn > 0 else (1 - hi / e)
        out.append(rec)
    return pd.DataFrame(out)


def nw_tstat(x: np.ndarray, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    m = x.mean()
    d = x - m
    g0 = (d @ d) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        gL = (d[L:] @ d[:-L]) / n
        var += 2 * (1 - L / (lags + 1)) * gL
    if var <= 0:
        return np.nan
    return m / np.sqrt(var / n)


def placebo(spot: pd.DataFrame, entries: pd.DataFrame, rng) -> np.ndarray:
    """Randomized controls: same count, same time-of-day mix, same direction mix,
    but random days. Tests whether the EMA cross beats an arbitrary nearby entry."""
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    dirs = entries["dir"].tolist()
    best_col = "r_eod"
    res = []
    for _ in range(N_PLACEBO):
        rows = []
        for tod, sgn in zip(tods, dirs):
            d = days[rng.integers(len(days))]
            rows.append({"t": pd.Timestamp(d).replace(
                hour=tod.hour, minute=tod.minute), "dir": sgn})
        f = forward_stats(spot, pd.DataFrame(rows))
        res.append(f[best_col].mean() if len(f) else np.nan)
    return np.array(res, float)


def summarize(f: pd.DataFrame, label: str) -> dict:
    cols = [f"r{h}" for h in HORIZONS] + ["r_eod"]
    d = {"label": label, "n": int(len(f))}
    for c in cols:
        if c not in f:
            continue
        x = f[c].dropna()
        if len(x) < 10:
            continue
        d[c] = {"mean_pct": round(100 * x.mean(), 4),
                "median_pct": round(100 * x.median(), 4),
                "hit": round(float((x > 0).mean()), 4),
                "t_nw": round(float(nw_tstat(x.values)), 3),
                "n": int(len(x))}
    if "mfe" in f and f["mfe"].notna().sum() > 10:
        mfe, mae = f["mfe"].dropna(), f["mae"].dropna()
        d["mfe_pct"] = round(100 * mfe.mean(), 4)
        d["mae_pct"] = round(100 * mae.mean(), 4)
        d["mfe_over_mae"] = round(float(mfe.mean() / abs(mae.mean())), 3) if mae.mean() else None
    return d


def main():
    spot = load_spot()
    print(f"[spot] {len(spot):,} 1-min bars  {spot.index[0]} .. {spot.index[-1]}", flush=True)
    rng = np.random.default_rng(SEED)
    report = {"breakeven_bar_pct": 100 * BREAKEVEN, "cells": []}

    for rule, fast, slow in GRID:
        name = f"{rule}_EMA{fast}_{slow}"
        print(f"\n=== {name} ===", flush=True)
        bars = resample(spot, rule)
        sig = signals(bars, fast, slow)
        if sig.empty:
            print("  no signals"); continue
        sig["date"] = pd.to_datetime(sig["t"]).dt.date
        b = sig[sig["date"] <= BUILD_END]
        fw = sig[sig["date"] > BUILD_END]
        print(f"  signals: build {len(b)}  forward {len(fw)}", flush=True)

        fb = forward_stats(spot, b)
        ff = forward_stats(spot, fw) if len(fw) else pd.DataFrame()
        cell = {"cell": name, "build": summarize(fb, "build"),
                "forward": summarize(ff, "forward_2026H1") if len(ff) else None}

        # pre-registered gates on the BUILD set
        horizons = [c for c in [f"r{h}" for h in HORIZONS] + ["r_eod"] if c in cell["build"]]
        best = max(horizons, key=lambda c: cell["build"][c]["mean_pct"]) if horizons else None
        if best:
            bm = cell["build"][best]
            x = fb[best].dropna()
            # concentration: largest single-day share of total signed edge
            per_day = fb.groupby("date")[best].sum()
            tot = per_day.sum()
            conc = float(per_day.abs().max() / abs(tot)) if tot else np.inf
            gates = {
                "best_horizon": best,
                "g1_magnitude": {"value_pct": bm["mean_pct"], "bar_pct": 100 * BREAKEVEN,
                                 "pass": bool(bm["mean_pct"] >= 100 * BREAKEVEN)},
                "g2_tstat": {"value": bm["t_nw"], "bar": 2.0,
                             "pass": bool(np.isfinite(bm["t_nw"]) and bm["t_nw"] >= 2.0)},
                "g4_concentration": {"max_day_share": round(conc, 4), "bar": 0.30,
                                     "pass": bool(conc <= 0.30)},
            }
            # The placebo (g3) is EXPENSIVE and can only ever REJECT a cell, never rescue one.
            # So run it only where the cheap gates already pass. Skipping it on an
            # already-failed cell cannot flatter the verdict.
            cheap_pass = all(gates[k]["pass"] for k in
                             ["g1_magnitude", "g2_tstat", "g4_concentration"])
            if cheap_pass:
                pl = placebo(spot, b, rng)
                pct = float((bm["mean_pct"] / 100 > pl).mean() * 100)
                gates["g3_placebo_pctile"] = {
                    "value": round(pct, 1), "bar": 90.0, "pass": bool(pct >= 90.0),
                    "placebo_mean_pct": round(100 * float(np.nanmean(pl)), 4)}
            else:
                gates["g3_placebo_pctile"] = {
                    "skipped": "cheap gates already failed; placebo cannot rescue", "pass": False}
            gates["ALL_PASS"] = cheap_pass and gates["g3_placebo_pctile"]["pass"]
            cell["gates"] = gates
            failed = [k for k in ["g1_magnitude", "g2_tstat", "g4_concentration"]
                      if not gates[k]["pass"]]
            print(f"  best={best} mean={bm['mean_pct']:+.4f}% (bar {100*BREAKEVEN:.2f}%) "
                  f"t={bm['t_nw']} hit={bm['hit']:.1%} conc={conc:.2f} "
                  f"-> {'PASS' if gates['ALL_PASS'] else 'FAIL ' + ','.join(failed)}", flush=True)
            if "mfe_over_mae" in cell["build"]:
                print(f"  MFE {cell['build']['mfe_pct']:+.3f}% / MAE "
                      f"{cell['build']['mae_pct']:+.3f}% -> ratio "
                      f"{cell['build']['mfe_over_mae']}", flush=True)
        report["cells"].append(cell)
        fb.to_csv(OUT / f"stage1_{name}_build.csv", index=False)
        if len(ff):
            ff.to_csv(OUT / f"stage1_{name}_forward.csv", index=False)

    any_pass = any(c.get("gates", {}).get("ALL_PASS") for c in report["cells"])
    report["VERDICT"] = ("STAGE1_PASSED_proceed_to_option_layer" if any_pass
                         else "STAGE1_FAILED_kill_no_option_layer")
    (OUT / "stage1_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n==== VERDICT: {report['VERDICT']} ====", flush=True)


if __name__ == "__main__":
    sys.exit(main())
