"""DEEP-DIVE on the 3 cells that cleared t>=2.87 in the phase-1 screen (screen.py), per the
coordinator's 2026-07-30 instruction, addressing two defects found in the sibling
CANDLE_MTF_20260730 work THAT SAME DAY:
  (a) OVERLAP -- a signal firing often while held a long time means many "trades" are open
      concurrently and summing them as independent inflates t (measured there: ~10x). FIX:
      lib_signals.one_position_at_a_time() keeps only the first signal of any overlapping
      cluster (a real trader has ONE position). Applied here BEFORE any statistic is computed.
  (b) BETA -- an edge that is really just "NIFTY went up a lot over 11 years" dressed as a
      timing signal. FIX: lib_signals.unconditional_benchmark() -- same exit machinery, random
      entries, matched count/time-of-day, but ALL forced to the cell's own dominant side.

For each of VORTEX|60min, AROON|15min, DONCHIAN_BRK|15min (all "trend"-kind -> primary horizon
r_eod, so one_position_at_a_time uses eod=True: at most one trade per calendar day survives):
  1. naive t-test AND Newey-West t (5 lags), on the DEDUPED sample
  2. concentration (must still be <=30%; this was VORTEX|60min's original reason for DEAD)
  3. random-entry placebo (200x, preserving the actual per-trade dir mix + time-of-day)
  4. unconditional benchmark (200x, single dominant side, same exit, matched count/time-of-day)
  5. era split (pre/post 2024-10-01) and 2026 held-out mean, on the deduped sample
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
from lib_signals import (BREAK, HELDOUT, build_by_day, concentration, forward_points, fut_cost,
                          load_spot, naive_tstat, nw_tstat, one_position_at_a_time, placebo_pts,
                          resample_bars, unconditional_benchmark)
from indicators import FAMILIES, sig_aroon, sig_donchian, sig_vortex

OUT = Path(__file__).parent
RNG = np.random.default_rng(20260730)
N_REPS = 200

TARGETS = [
    ("VORTEX", "60min", sig_vortex),
    ("AROON", "15min", sig_aroon),
    ("DONCHIAN_BRK", "15min", sig_donchian),
]

t0 = time.time()
print("[load] 1-min spot", flush=True)
spot = load_spot()
BY_DAY = build_by_day(spot)
BARS = {tf: resample_bars(spot, tf) for tf in ("15min", "60min")}
print(f"       done {time.time()-t0:.1f}s", flush=True)

report = {}
for fname, tf, func in TARGETS:
    print(f"\n=== {fname}|{tf} ===", flush=True)
    bars = BARS[tf]
    raw = func(bars)
    n_raw = len(raw)
    deduped = one_position_at_a_time(raw, eod=True)   # all 3 targets are "trend" kind -> r_eod
    print(f"  raw signals: {n_raw}  ->  one-position-at-a-time: {len(deduped)} "
          f"({100*len(deduped)/n_raw:.1f}% kept)", flush=True)

    f = forward_points(spot, deduped, by_day=BY_DAY)
    sel = f[f["day"] < HELDOUT].copy()
    ho = f[f["day"] >= HELDOUT].copy()
    pcol = "r_eod"
    x = sel[pcol].dropna()
    sel_v = sel.loc[x.index]
    net = np.array([v - fut_cost(d) for v, d in zip(x.values, sel_v["day"])])
    months = max(len(pd.PeriodIndex(sel_v["day"], freq="M").unique()), 1)

    t_naive, p_naive = naive_tstat(x.values)
    t_nw = nw_tstat(x.values)
    conc = concentration(sel_v.assign(**{pcol: net}), pcol)
    pre = sel_v[sel_v["day"] < BREAK][pcol]
    post = sel_v[sel_v["day"] >= BREAK][pcol]
    ho_x = ho[pcol].dropna() if pcol in ho else pd.Series(dtype=float)
    win = float((x > 0).mean())
    avg_win = float(x[x > 0].mean()) if (x > 0).any() else np.nan
    avg_loss = float(x[x <= 0].mean()) if (x <= 0).any() else np.nan
    payoff = avg_win / abs(avg_loss) if np.isfinite(avg_loss) and avg_loss != 0 else np.nan

    entries_for_placebo = deduped[deduped["t"].isin(sel_v["t"])]
    pl = placebo_pts(spot, entries_for_placebo, pcol, RNG, N_REPS, by_day=BY_DAY)
    pl = pl[np.isfinite(pl)]
    placebo_p = float((pl >= x.mean()).mean()) if len(pl) else np.nan

    bm = unconditional_benchmark(spot, entries_for_placebo, pcol, RNG, BY_DAY, N_REPS)
    bm = bm[np.isfinite(bm)]
    bench_mean = float(np.mean(bm)) if len(bm) else np.nan
    bench_p = float((bm >= x.mean()).mean()) if len(bm) else np.nan   # beats the beta bench?
    dominant_side = "LONG" if deduped["dir"].sum() >= 0 else "SHORT"

    row = dict(
        cell=f"{fname}|{tf}", n_raw=n_raw, n_deduped=int(len(x)), dominant_side=dominant_side,
        trades_per_month=round(len(x) / months, 2),
        mean_gross=round(float(x.mean()), 3), mean_net=round(float(net.mean()), 3),
        win_pct=round(win, 4), avg_win=round(avg_win, 2) if np.isfinite(avg_win) else None,
        avg_loss=round(avg_loss, 2) if np.isfinite(avg_loss) else None,
        payoff_ratio=round(payoff, 2) if np.isfinite(payoff) else None,
        t_naive=round(t_naive, 3) if np.isfinite(t_naive) else None,
        t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None,
        concentration=round(conc, 3),
        placebo_mean=round(float(np.mean(pl)), 3) if len(pl) else None,
        placebo_p=round(placebo_p, 4) if np.isfinite(placebo_p) else None,
        unconditional_bench_mean=round(bench_mean, 3) if np.isfinite(bench_mean) else None,
        beats_unconditional_bench_p=round(bench_p, 4) if np.isfinite(bench_p) else None,
        era_pre_n=int(len(pre)), era_pre_mean=round(float(pre.mean()), 3) if len(pre) > 10 else None,
        era_post_n=int(len(post)), era_post_mean=round(float(post.mean()), 3) if len(post) > 10 else None,
        ho2026_n=int(len(ho_x)), ho2026_mean=round(float(ho_x.mean()), 3) if len(ho_x) > 5 else None,
    )
    fails_placebo = np.isfinite(placebo_p) and placebo_p >= 0.05
    fails_bench = np.isfinite(bench_p) and bench_p >= 0.05
    if conc > 0.30:
        verdict = "DEAD (concentration >30%)"
    elif fails_placebo:
        verdict = "DEAD (fails own placebo)"
    elif fails_bench:
        verdict = "DEAD (beta -- does not beat unconditional same-side benchmark)"
    elif net.mean() <= 0:
        verdict = "DEAD (net mean <= 0 after dedup)"
    else:
        verdict = "FORWARD-TEST CANDIDATE (survives overlap fix, placebo, and beta test)"
    row["verdict"] = verdict
    report[row["cell"]] = row
    print(f"  n_raw={n_raw} n_deduped={len(x)} tpm={row['trades_per_month']} "
          f"mean_net={row['mean_net']:+.3f} t_naive={row['t_naive']} t_nw={row['t_nw']} "
          f"conc={conc:.3f}", flush=True)
    print(f"  placebo mean={row['placebo_mean']} p={row['placebo_p']}  |  "
          f"unconditional-{dominant_side}-benchmark mean={row['unconditional_bench_mean']} "
          f"p(bench>=obs)={row['beats_unconditional_bench_p']}", flush=True)
    print(f"  era_pre(n={row['era_pre_n']})={row['era_pre_mean']}  "
          f"era_post(n={row['era_post_n']})={row['era_post_mean']}  "
          f"2026_heldout(n={row['ho2026_n']})={row['ho2026_mean']}", flush=True)
    print(f"  -> {verdict}", flush=True)

json.dump(report, open(OUT / "deep_dive_results.json", "w"), indent=2)
pd.DataFrame(report.values()).to_csv(OUT / "deep_dive_cells.csv", index=False)
print(f"\n[done] deep_dive elapsed {time.time()-t0:.1f}s -> deep_dive_results.json, "
      f"deep_dive_cells.csv", flush=True)
