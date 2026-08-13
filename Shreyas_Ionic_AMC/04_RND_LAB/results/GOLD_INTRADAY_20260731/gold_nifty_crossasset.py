"""CROSS-ASSET: gold's OWN overnight move (the window NIFTY is shut but gold keeps trading,
~15:25 IST one NIFTY session to ~09:14 IST the next) -> NIFTY next-session INTRADAY bias.

Principal's priority framing (2026-07-31): the WTI-crude-shock cell was "the best single lead in
the whole book" (+27.60 pts, 59% win, placebo p=0.008, held-out slice LARGER) and gold is the
natural extension. This is a genuinely different information source (a cross-asset overnight
read, not another transform of NIFTY's own price) -- exactly the orthogonality the firm's
breadth protocol asks for.

METHOD:
  - overnight_gold_return = % change in XAUUSD from its last print at/before 15:25 IST on NIFTY
    trading day D-1 to its last print at/before 09:14 IST on NIFTY trading day D (spans
    whatever calendar gap sits between the two NIFTY sessions, weekends included -- the TRUE
    informational gap a NIFTY trader faces at 09:15).
  - TWO directional hypotheses tested and BOTH reported (avoids picking the flattering sign
    after the fact): dir=+sign(overnight_gold_return) ("gold up -> NIFTY up", risk-on
    co-movement) and dir=-sign(overnight_gold_return) ("gold up -> NIFTY down", safe-haven/
    flight-to-gold). Only one of these two can win; disclosing both keeps the trial count honest
    (2 cells, not 1 picked in hindsight).
  - UNCONDITIONAL (every NIFTY day) AND an EXTREME-only filter (|overnight_gold_return| above
    its own TRAILING 252-trading-day 80th percentile -- no lookahead, threshold uses only prior
    data) -- 2 conditioning states x 2 directions = 4 cells.
  - Re-uses lib_signals.forward_points/nw_tstat/placebo_pts/unconditional_benchmark VERBATIM (a
    NIFTY-session entry is still a NIFTY-session entry; only how `dir` is assigned changes).
  - Build = NIFTY day < 2024-10-01 / 2024-10-01..2025-12-31; HELD OUT = 2026 (never selected on).
  - One position at a time is automatic here (at most 1 signal per NIFTY calendar day already).
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
HERE = Path(__file__).parent
TV_DIR = HERE.parent / "TV_INDICATORS_20260730"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TV_DIR))
import gold_lib as gl
from lib_signals import (BREAK, HELDOUT, build_by_day, concentration, forward_points, fut_cost,
                          load_spot, naive_tstat, nw_tstat, placebo_pts, unconditional_benchmark)

RNG = np.random.default_rng(20260731)
N_REPS = 150

t0 = time.time()
print("[load] NIFTY spot + gold (IST)", flush=True)
nifty = load_spot()
gold = gl.load_gold_ist()
print(f"  NIFTY {len(nifty):,} bars {nifty.index[0]}..{nifty.index[-1]}", flush=True)
print(f"  gold  {len(gold):,} bars  {gold.index[0]}..{gold.index[-1]}  ({time.time()-t0:.1f}s)",
      flush=True)
nifty_by_day = build_by_day(nifty)

# gold price nearest-before 15:25 and nearest-before 09:14 IST, per gold calendar date
gold_daily = []
for d, day in gold.groupby(gold.index.date):
    p1525 = day[day.index.time <= pd.Timestamp("15:25").time()]
    p0914 = day[day.index.time <= pd.Timestamp("09:14").time()]
    gold_daily.append(dict(
        date=d, px_1525=float(p1525["close"].iloc[-1]) if len(p1525) else np.nan,
        px_0914=float(p0914["close"].iloc[-1]) if len(p0914) else np.nan))
gdaily = pd.DataFrame(gold_daily).set_index("date").sort_index()
print(f"  gold daily anchor table: {len(gdaily)} calendar days ({time.time()-t0:.1f}s)", flush=True)

nifty_days = sorted(nifty_by_day.keys())
rows = []
for i in range(1, len(nifty_days)):
    d_prev, d_cur = nifty_days[i - 1], nifty_days[i]
    if d_prev not in gdaily.index or d_cur not in gdaily.index:
        continue
    px_prev = gdaily.loc[d_prev, "px_1525"]
    px_cur = gdaily.loc[d_cur, "px_0914"]
    if not (np.isfinite(px_prev) and np.isfinite(px_cur)) or px_prev <= 0:
        continue
    ret = (px_cur / px_prev - 1) * 100
    rows.append(dict(nifty_date=d_cur, overnight_gold_ret_pct=ret))
og = pd.DataFrame(rows).set_index("nifty_date").sort_index()
print(f"  matched NIFTY days with an overnight gold read: {len(og)}", flush=True)

# trailing 252-day 80th-percentile threshold on |overnight return| -- no lookahead (shift(1))
og["abs_ret"] = og["overnight_gold_ret_pct"].abs()
og["thr80"] = og["abs_ret"].shift(1).rolling(252, min_periods=60).quantile(0.80)
og["is_extreme"] = og["abs_ret"] > og["thr80"]

CONDITIONS = {"ALL_DAYS": og.index, "EXTREME_ONLY": og.index[og["is_extreme"].fillna(False)]}

report = {}
for cond_name, idx in CONDITIONS.items():
    sub = og.loc[idx]
    print(f"\n=== {cond_name}  (n_days={len(sub)}) ===", flush=True)
    for hyp_name, sign in [("GOLD_UP_NIFTY_UP", 1), ("GOLD_UP_NIFTY_DOWN", -1)]:
        entries = pd.DataFrame({
            "t": [pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=14) for d in sub.index],
            "dir": [int(sign * np.sign(r)) for r in sub["overnight_gold_ret_pct"]],
        })
        entries = entries[entries["dir"] != 0].reset_index(drop=True)
        if len(entries) < 40:
            print(f"  [{hyp_name}] too few ({len(entries)}), skip", flush=True)
            continue
        f = forward_points(nifty, entries, by_day=nifty_by_day)
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

        cheap_pass = net.mean() > 0 and np.isfinite(t_nw) and abs(t_nw) >= 2.0 and conc <= 0.30
        placebo_p = bench_mean = bench_p = None
        if cheap_pass:
            ent_sub = entries[entries["t"].isin(sel_v["t"])]
            pl = placebo_pts(nifty, ent_sub, pcol, RNG, N_REPS, by_day=nifty_by_day)
            pl = pl[np.isfinite(pl)]
            placebo_p = float((pl >= x.mean()).mean()) if len(pl) else None
            bm = unconditional_benchmark(nifty, ent_sub, pcol, RNG, nifty_by_day, N_REPS)
            bm = bm[np.isfinite(bm)]
            bench_mean = float(np.mean(bm)) if len(bm) else None
            bench_p = float((bm >= x.mean()).mean()) if len(bm) else None

        key = f"{cond_name}|{hyp_name}"
        row = dict(
            n=int(len(x)), trades_per_month=round(len(x) / months, 2),
            mean_gross=round(float(x.mean()), 3), mean_net=round(float(net.mean()), 3),
            win_pct=round(float((x > 0).mean()), 4),
            t_naive=round(t_naive, 3) if np.isfinite(t_naive) else None,
            t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None,
            concentration=round(conc, 3),
            placebo_p=round(placebo_p, 4) if placebo_p is not None else None,
            unconditional_bench_mean=round(bench_mean, 3) if bench_mean is not None else None,
            beats_bench_p=round(bench_p, 4) if bench_p is not None else None,
            era_pre_n=int(len(pre)), era_pre_mean=round(float(pre.mean()), 3) if len(pre) > 10 else None,
            era_post_n=int(len(post)), era_post_mean=round(float(post.mean()), 3) if len(post) > 10 else None,
            ho2026_n=int(len(ho_x)), ho2026_mean=round(float(ho_x.mean()), 3) if len(ho_x) > 5 else None,
        )
        verdict = "DEAD"
        if cheap_pass:
            if placebo_p is not None and placebo_p >= 0.05:
                verdict = "DEAD (fails own placebo)"
            elif bench_p is not None and bench_p >= 0.05:
                verdict = "DEAD (beta -- does not beat unconditional benchmark)"
            else:
                verdict = "FORWARD-TEST CANDIDATE"
        row["verdict"] = verdict
        report[key] = row
        print(f"  [{hyp_name}] n={row['n']} tpm={row['trades_per_month']} "
              f"mean_net={row['mean_net']:+.2f} t_naive={t_naive:.2f} t_nw={t_nw:.2f} "
              f"conc={conc:.2f} placebo_p={placebo_p} bench_p={bench_p} -> {verdict}", flush=True)

json.dump(report, open(HERE / "gold_nifty_crossasset_results.json", "w"), indent=2, default=str)
pd.DataFrame(report).T.to_csv(HERE / "gold_nifty_crossasset_cells.csv")
print(f"\n[done] elapsed {time.time()-t0:.1f}s", flush=True)
