"""PHASE 1 SCREEN -- TradingView-style indicator families on NIFTY 50 UNDERLYING (index points,
no option/futures vehicle yet -- method rule 1: measure the signal on the underlying first).

PRE-REGISTRATION (fixed BEFORE looking at any result; do not tune after seeing output):
  - 18 families (indicators.py FAMILIES) x 2 timeframes (15min, 60min) = 36 cells.
  - Primary horizon per family is fixed by ECONOMIC KIND, not picked post-hoc from the best of
    5: "trend"-kind families -> r_eod (let a breakout/turn run to the day's close); "reversion"
    -kind families -> 2 bars of the signal's OWN timeframe (15min->r30, 60min->r120). All 5
    horizons (r15/r30/r60/r120/r_eod) are still written to cells_all_horizons.csv for full
    transparency (SHARED_CONTEXT SS2: "report ALL buckets, not just the profitable one").
  - Selection set = all signals with date < 2026-01-01. 2026 (2026-01-01..2026-05-14, the full
    span this data file has) is HELD OUT: reported, never used to pick a cell.
  - Era split at 2024-10-01 (SEBI F&O tightening + STT rise), reported for every cell.
  - Cheap gates on the selection set: net mean pts > 0 (net of era-correct futures cost) AND
    |NW t-stat| >= 2.0 AND single-day profit concentration <= 30%. Placebo (200x random-day
    reassignment, matched on count/time-of-day/direction) is EXPENSIVE and can only reject, so
    it is run only on cells that already clear the cheap gates (same discipline as
    stage1_signal_test.py). A cell failing its own placebo is DEAD regardless of its t-stat
    (SHARED_CONTEXT hard-kill #1).
  - Concentration > 30% of signed edge from a single day is a HARD KILL (hard-kill #3),
    independent of t-stat.
  - Bonferroni bar computed from THIS session's own m=36 (house convention: candle_mtf.py and
    155_indicator_mine_signals.py both state their own trial count's bar, not the firm's
    ever-growing cumulative ledger, though that cumulative context is reported too for honesty).
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
from lib_signals import (BREAK, HELDOUT, build_by_day, concentration, forward_points, fut_cost,
                          load_spot, nw_tstat, placebo_pts, resample_bars)
from indicators import FAMILIES

OUT = Path(__file__).parent
RNG = np.random.default_rng(20260730)
N_PLACEBO = 200
T_GATE, CONC_GATE = 2.0, 0.30

t0 = time.time()
print("[load] 1-min spot", flush=True)
spot = load_spot()
print(f"       {len(spot):,} bars  {spot.index[0]} .. {spot.index[-1]}", flush=True)
print("[prep] pre-splitting spot by calendar day (reused across all 36 cells)", flush=True)
BY_DAY = build_by_day(spot)

BARS = {}
for tf in ("15min", "60min"):
    b = resample_bars(spot, tf)
    BARS[tf] = b
    print(f"[bars] {tf}: {len(b):,} bars  {b.index[0]} .. {b.index[-1]}", flush=True)

HORIZ_COLS = ["r15", "r30", "r60", "r120", "r_eod"]


def primary_col(kind: str, tf: str) -> str:
    if kind == "trend":
        return "r_eod"
    return "r30" if tf == "15min" else "r120"


rows_primary = []
rows_all = []
n_cells_done = 0
for fname, (func, kind) in FAMILIES.items():
    for tf in ("15min", "60min"):
        bars = BARS[tf]
        try:
            entries = func(bars)
        except Exception as e:
            print(f"  [{fname}|{tf}] ERROR building signal: {e}", flush=True)
            continue
        if entries.empty or len(entries) < 40:
            print(f"  [{fname}|{tf}] too few signals (n={len(entries)}), skip", flush=True)
            continue
        f = forward_points(spot, entries, by_day=BY_DAY)
        if f.empty:
            print(f"  [{fname}|{tf}] forward_points empty, skip", flush=True)
            continue
        pcol = primary_col(kind, tf)
        sel = f[f["day"] < HELDOUT].copy()
        ho = f[f["day"] >= HELDOUT].copy()
        if len(sel) < 40 or pcol not in sel or sel[pcol].notna().sum() < 40:
            print(f"  [{fname}|{tf}] insufficient primary-horizon n on selection set, skip",
                  flush=True)
            continue
        x = sel[pcol].dropna()
        sel_valid = sel.loc[x.index]
        net = np.array([v - fut_cost(d) for v, d in zip(x.values, sel_valid["day"])])
        months = max(len(pd.PeriodIndex(sel_valid["day"], freq="M").unique()), 1)
        t_nw = nw_tstat(x.values)
        conc = concentration(sel_valid.assign(**{pcol: net}), pcol)
        pre = sel_valid[sel_valid["day"] < BREAK][pcol]
        post = sel_valid[(sel_valid["day"] >= BREAK)][pcol]
        ho_x = ho[pcol].dropna() if pcol in ho else pd.Series(dtype=float)

        cheap_pass = (net.mean() > 0) and np.isfinite(t_nw) and (abs(t_nw) >= T_GATE) and (
            conc <= CONC_GATE)
        placebo_p = None
        if cheap_pass:
            pl = placebo_pts(spot, entries[entries["t"].isin(sel_valid["t"])], pcol, RNG,
                              N_PLACEBO, by_day=BY_DAY)
            pl = pl[np.isfinite(pl)]
            if len(pl):
                placebo_p = float((pl >= x.mean()).mean())

        verdict = "DEAD"
        if not cheap_pass:
            if net.mean() > 0 and conc <= CONC_GATE:
                verdict = "UNDERPOWERED-UNRESOLVED"
            else:
                verdict = "DEAD"
        else:
            if placebo_p is not None and placebo_p >= 0.05:
                verdict = "DEAD (fails own placebo)"
            elif conc > CONC_GATE:
                verdict = "DEAD (concentration)"
            else:
                verdict = "FORWARD-TEST CANDIDATE"

        r = dict(
            cell=f"{fname}|{tf}", family=fname, tf=tf, kind=kind, primary_horizon=pcol,
            n=int(len(x)), trades_per_month=round(len(x) / months, 1),
            mean_gross=round(float(x.mean()), 3), mean_net=round(float(net.mean()), 3),
            median_gross=round(float(x.median()), 3),
            win_pct=round(float((x > 0).mean()), 4),
            avg_win=round(float(x[x > 0].mean()), 2) if (x > 0).any() else None,
            avg_loss=round(float(x[x <= 0].mean()), 2) if (x <= 0).any() else None,
            payoff_ratio=(round(float(x[x > 0].mean() / abs(x[x <= 0].mean())), 2)
                         if (x > 0).any() and (x <= 0).any() and x[x <= 0].mean() != 0 else None),
            t_nw=round(float(t_nw), 3) if np.isfinite(t_nw) else None,
            concentration=round(conc, 3),
            placebo_p=round(placebo_p, 4) if placebo_p is not None else None,
            era_pre_n=int(len(pre)), era_pre_mean=round(float(pre.mean()), 3) if len(pre) > 10 else None,
            era_post_n=int(len(post)), era_post_mean=round(float(post.mean()), 3) if len(post) > 10 else None,
            ho2026_n=int(len(ho_x)), ho2026_mean=round(float(ho_x.mean()), 3) if len(ho_x) > 5 else None,
            verdict=verdict,
        )
        rows_primary.append(r)
        for c in HORIZ_COLS:
            if c in sel.columns and sel[c].notna().sum() >= 20:
                xx = sel[c].dropna()
                rows_all.append(dict(cell=f"{fname}|{tf}", horizon=c, n=int(len(xx)),
                                     mean=round(float(xx.mean()), 3),
                                     t_nw=round(float(nw_tstat(xx.values)), 3)
                                     if np.isfinite(nw_tstat(xx.values)) else None,
                                     win_pct=round(float((xx > 0).mean()), 4)))
        n_cells_done += 1
        print(f"  [{fname}|{tf}] n={len(x)} tpm={r['trades_per_month']} "
              f"mean_net={r['mean_net']:+.2f} t={r['t_nw']} conc={conc:.2f} "
              f"placebo_p={placebo_p} -> {verdict}", flush=True)

R = pd.DataFrame(rows_primary)
Rall = pd.DataFrame(rows_all)
R.to_csv(OUT / "cells.csv", index=False)
Rall.to_csv(OUT / "cells_all_horizons.csv", index=False)

m = len(R)
bar_own = float(stats.norm.ppf(1 - 0.025 / m)) if m > 0 else float("nan")
cumulative_prior = 466 + 480 + 15   # ledger row + CANDLE_MTF_20260730 + INDICATOR_MINE_20260730
m_cum = cumulative_prior + m
bar_cum = float(stats.norm.ppf(1 - 0.025 / m_cum))

json.dump(dict(n_cells=m, bonferroni_bar_own_m=round(bar_own, 3), own_m=m,
               cumulative_firm_m=m_cum, bonferroni_bar_cumulative=round(bar_cum, 3),
               heldout_from="2026-01-01", break_date="2024-10-01",
               families=list(FAMILIES), timeframes=["15min", "60min"],
               n_placebo=N_PLACEBO, t_gate=T_GATE, conc_gate=CONC_GATE),
          open(OUT / "meta.json", "w"), indent=2)

print(f"\n[done] {m} cells scored -> cells.csv, cells_all_horizons.csv, meta.json", flush=True)
print(f"       Bonferroni bar @ own m={m}: t>={bar_own:.2f}", flush=True)
print(f"       Bonferroni bar @ cumulative firm m={m_cum}: t>={bar_cum:.2f}", flush=True)
print(f"       elapsed {time.time()-t0:.1f}s", flush=True)
