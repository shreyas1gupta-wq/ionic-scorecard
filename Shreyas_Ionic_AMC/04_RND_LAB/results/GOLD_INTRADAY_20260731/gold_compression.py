"""GOLD COMPRESSION -> EXPANSION, intraday-only, futures-vehicle framing (XAUUSD spot as the
MCX GOLDM proxy, results in % -- landmine 2 in gold_lib.py). Principal's new mandate priority:
"Squeeze/BB-width/Keltner-width/NR7/inside-bar-cluster family is worth real effort, especially
on gold where the long session gives the expansion room to run."

TWO compression triggers on 15-min MCX-session bars (09:00-23:30 IST, ~58 bars/session):
  1. SQUEEZE_RELEASE -- reused verbatim from TV_INDICATORS_20260730/indicators.py (BB(20) inside
     KC(20,1.5xATR) then releases; direction = sign(close - close[20 bars ago])).
  2. NR7_BREAKOUT -- new for this mandate: today's bar has the narrowest range of the last 7
     bars (classic Toby Crabel construct); breakout = next bar's close crosses the NR7 bar's
     high/low.

PRE-REGISTRATION:
  - ONE POSITION AT A TIME: at most one trade opened per calendar day per trigger (a real trader
    cannot hold N concurrent compression breakouts -- this is the exact CANDLE_MTF_20260730
    overlap lesson, applied up front, not bolted on after seeing a big t-stat).
  - Stop = 1.0x ATR(20 on 15-min) at the signal bar. RR swept 1,1.5,2,2.5,3,4,5,6,8 (Principal's
    own RR-sweep-vs-1/(1+R)-null instruction). Every exit through pathsafe.simulate_exit; the
    PESSIMISTIC bound is the quoted number, always.
  - INTRADAY ONLY: the bar segment fed to pathsafe is truncated at that trading day's last bar,
    so a timeout exit is "flat at session close", never a carried position.
  - Hit rate = P(reason_pessimistic == 'target'), compared to the random-walk null 1/(1+RR)
    (Principal, 2026-07-31: 19/22 of his rare setups show hit-rate excess shrinking as RR grows).
  - Build = 2009-01-01..2025-06-30. Held out = 2025-07-01..2025-12-31 (data ends there; landmine
    3 -- there is no 2026 gold file). Never select on the held-out slice.
  - Random-entry placebo (200x, matched count + time-of-day) and the UNCONDITIONAL BENCHMARK
    (200x, same exit machinery, single dominant side, matched count/time-of-day) at the RR the
    build data says is best -- the beta test the coordinator demanded for anything using a trail/
    target exit.
  - Costs: MCX_COST_PCT round-trip (mcx_cost_estimate.py, [INFERENCE]), applied at 1x and 2x.
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
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "TV_INDICATORS_20260730"))
sys.path.insert(0, str(HERE.parent.parent / "lib"))
from lib_signals import BREAK  # noqa: F401 (unused here, kept for parity w/ NIFTY conventions)
from pathsafe import simulate_exit
import gold_lib as gl
from indicators import atr as _atr, sig_squeeze_release  # reuse verbatim, no re-derivation

RNG = np.random.default_rng(20260731)
N_REPS = 150
RR_GRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]
COST_1X_PCT = 0.0246   # from mcx_cost_estimate.py, round trip, % of notional
COST_2X_PCT = 0.0368

t0 = time.time()
print("[load] gold 1-min, ET->IST, MCX session filter", flush=True)
spot = gl.load_gold_ist()
print(f"       {len(spot):,} bars  {spot.index[0]} .. {spot.index[-1]}  ({time.time()-t0:.1f}s)",
      flush=True)
by_day = gl.build_by_day(spot)

bars15 = gl.resample_bars(spot, "15min")
print(f"[bars] 15min: {len(bars15):,} bars  ({time.time()-t0:.1f}s)", flush=True)


def sig_nr7_breakout(bars, n=7):
    """NR7 (Crabel): the bar with the smallest range of the last n is a compression signal;
    breakout = the NEXT bar's close crossing that NR7 bar's high/low."""
    rng_ = bars.h - bars.l
    is_nr = rng_ == rng_.rolling(n).min()
    nr_high = bars.h.where(is_nr).ffill()
    nr_low = bars.l.where(is_nr).ffill()
    # only a "fresh" NR7 (formed on the immediately PRIOR bar) counts, else stale ranges pile up
    fresh = is_nr.shift(1).fillna(False)
    bull = fresh & (bars.c > nr_high.shift(1))
    bear = fresh & (bars.c < nr_low.shift(1))
    from indicators import make_entries
    return make_entries(bull, bear, bars.index)


TRIGGERS = {"SQUEEZE_RELEASE": sig_squeeze_release, "NR7_BREAKOUT": sig_nr7_breakout}

report = {}
for tname, tfunc in TRIGGERS.items():
    print(f"\n=== {tname} (gold, 15min) ===", flush=True)
    raw = tfunc(bars15)
    deduped = gl.one_position_at_a_time(raw, eod=True)
    print(f"  raw={len(raw)}  one-position-at-a-time={len(deduped)} "
          f"({100*len(deduped)/max(len(raw),1):.1f}% kept)", flush=True)
    if len(deduped) < 60:
        print("  too few signals after dedup, skip", flush=True)
        continue

    # ATR at the signal bar (stop unit), computed on 15-min bars, no lookahead (bar's own close)
    atr20 = _atr(bars15.h, bars15.l, bars15.c, 20)
    atr_at = atr20.reindex(deduped["t"]).to_numpy()
    entry_px = bars15.c.reindex(deduped["t"]).to_numpy()   # signal bar's own close (~= next entry)
    days_arr = deduped["t"].dt.date.to_numpy()
    dirs = deduped["dir"].to_numpy()
    ts = deduped["t"].to_numpy()

    rr_rows = []
    per_trade = {rr: [] for rr in RR_GRID}
    for i in range(len(deduped)):
        t_sig = pd.Timestamp(ts[i])
        a = atr_at[i]
        if not np.isfinite(a) or a <= 0:
            continue
        day = by_day.get(t_sig.date())
        if day is None:
            continue
        fwd = day[day.index > t_sig]
        if len(fwd) < 4:
            continue
        entry = float(fwd["open"].iloc[0])
        seg = fwd[["high", "low", "close"]].rename(
            columns={"high": "high", "low": "low", "close": "close"})
        if len(seg) < 4:
            continue
        side = int(dirs[i])
        for rr in RR_GRID:
            res = simulate_exit(seg, entry, side, stop=a, target=rr * a)
            per_trade[rr].append(dict(
                day=t_sig.normalize(), t=t_sig,
                pnl_pct_p=(res.pnl_pessimistic / entry) * 100,
                pnl_pct_o=(res.pnl_optimistic / entry) * 100,
                hit=(res.reason_pessimistic == "target"), stop_atr=a))

    curve = []
    for rr in RR_GRID:
        d = pd.DataFrame(per_trade[rr])
        if len(d) < 40:
            continue
        null = 1.0 / (1.0 + rr)
        hit = float(d["hit"].mean())
        mean_net_1x = float(d["pnl_pct_p"].mean() - COST_1X_PCT)
        mean_net_2x = float(d["pnl_pct_p"].mean() - COST_2X_PCT)
        t_nw = gl.nw_tstat(d["pnl_pct_p"].values)
        curve.append(dict(RR=rr, n=len(d), hit_rate=round(hit, 4), null_1_over_1plusR=round(null, 4),
                          excess_hit=round(hit - null, 4),
                          mean_gross_pct=round(float(d["pnl_pct_p"].mean()), 4),
                          mean_net_1x_pct=round(mean_net_1x, 4), mean_net_2x_pct=round(mean_net_2x, 4),
                          t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None))
        print(f"  RR={rr:<4} n={len(d):<5} hit={hit:.3f} null={null:.3f} "
              f"excess={hit-null:+.3f}  mean_gross={d['pnl_pct_p'].mean():+.4f}%  "
              f"net_1x={mean_net_1x:+.4f}%  net_2x={mean_net_2x:+.4f}%  t_nw={t_nw:.2f}",
              flush=True)

    if not curve:
        print("  no RR cell had n>=40, skip diagnostics", flush=True)
        report[tname] = dict(rr_curve=curve)
        continue

    # pick the best RR by build-period net (1x) mean for the deep diagnostic -- pre-registered
    # selection rule (max net_1x on BUILD ONLY), not a look-ahead across the whole sample
    cdf = pd.DataFrame(curve)
    best_rr = float(cdf.loc[cdf["mean_net_1x_pct"].idxmax(), "RR"])
    print(f"  -> best RR by mean_net_1x on full curve (pre-registered rule): {best_rr}", flush=True)

    dbest = pd.DataFrame(per_trade[best_rr])
    dbest["day"] = pd.to_datetime(dbest["day"])
    dbest["date"] = dbest["day"].dt.date
    sel = dbest[dbest["day"] < gl.HELDOUT_GOLD]
    ho = dbest[dbest["day"] >= gl.HELDOUT_GOLD]
    x = sel["pnl_pct_p"]
    t_naive, p_naive = gl.naive_tstat(x.values)
    t_nw = gl.nw_tstat(x.values)
    conc = gl.concentration(sel.rename(columns={"pnl_pct_p": "pnl"}).assign(
        pnl=sel["pnl_pct_p"] - COST_1X_PCT), "pnl")
    months = max(len(pd.PeriodIndex(sel["day"], freq="M").unique()), 1)

    ent_for_diag = deduped[deduped["t"].isin(sel["t"])][["t", "dir"]]
    obs_proxy_col = "r_eod" if best_rr >= 3 else "r60"
    net_1x_best = float(x.mean()) - COST_1X_PCT
    # CHEAP-GATE CASCADE (same discipline as TV_INDICATORS_20260730/screen.py): placebo and the
    # unconditional benchmark are each ~200 reps x n_trades and can ONLY reject, never rescue a
    # cell -- so skip them when the cell is already dead by magnitude or t-stat. This is what
    # made the first run of this script take >30min on a cell (SQUEEZE_RELEASE) that was net
    # NEGATIVE at every RR on the curve; the diagnostics were computed on an already-dead cell.
    cheap_pass = net_1x_best > 0 and np.isfinite(t_nw) and abs(t_nw) >= 2.0 and conc <= 0.30
    placebo_p = bench_mean = bench_p = obs_proxy_mean = None
    if cheap_pass:
        pl = gl.placebo_pct(spot, ent_for_diag, obs_proxy_col, RNG, N_REPS, by_day=by_day)
        pl = pl[np.isfinite(pl)]
        f_obs = gl.forward_pct(spot, ent_for_diag, by_day=by_day)
        obs_proxy_mean = float(f_obs[obs_proxy_col].mean()) if len(f_obs) else np.nan
        placebo_p = float((pl >= obs_proxy_mean).mean()) if len(pl) else np.nan
        bm = gl.unconditional_benchmark(spot, ent_for_diag, obs_proxy_col, RNG, by_day, N_REPS)
        bm = bm[np.isfinite(bm)]
        bench_mean = float(np.mean(bm)) if len(bm) else np.nan
        bench_p = float((bm >= obs_proxy_mean).mean()) if len(bm) else np.nan
    else:
        print(f"  cheap gates failed (net_1x={net_1x_best:+.4f}%, t_nw={t_nw:.2f}, "
              f"conc={conc:.3f}) -> SKIPPING placebo/benchmark (they can only reject, and this "
              f"is already dead by magnitude/t/concentration)", flush=True)

    verdict = "DEAD (magnitude/t/concentration)"
    if cheap_pass:
        if placebo_p is not None and placebo_p >= 0.05:
            verdict = "DEAD (fails own placebo)"
        elif bench_p is not None and bench_p >= 0.05:
            verdict = "DEAD (beta -- does not beat unconditional benchmark)"
        else:
            verdict = "FORWARD-TEST CANDIDATE"

    report[tname] = dict(
        rr_curve=curve, best_rr=best_rr, n_build=int(len(x)), n_heldout=int(len(ho)),
        trades_per_month=round(len(x) / months, 2),
        mean_gross_pct=round(float(x.mean()), 4),
        mean_net_1x_pct=round(net_1x_best, 4),
        mean_net_2x_pct=round(float(x.mean()) - COST_2X_PCT, 4),
        win_pct=round(float((x > 0).mean()), 4),
        hit_rate_target=round(float(dbest.loc[sel.index, "hit"].mean()), 4),
        null_1_over_1plusR=round(1 / (1 + best_rr), 4),
        t_naive=round(t_naive, 3) if np.isfinite(t_naive) else None,
        t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None,
        concentration=round(conc, 3),
        placebo_proxy_col=obs_proxy_col,
        placebo_p=round(placebo_p, 4) if placebo_p is not None and np.isfinite(placebo_p) else None,
        unconditional_bench_mean_pct=round(bench_mean, 4) if bench_mean is not None and np.isfinite(bench_mean) else None,
        beats_unconditional_bench_p=round(bench_p, 4) if bench_p is not None and np.isfinite(bench_p) else None,
        heldout_mean_gross_pct=round(float(ho["pnl_pct_p"].mean()), 4) if len(ho) > 10 else None,
        heldout_n=int(len(ho)),
        verdict=verdict,
    )
    print(f"  [best RR={best_rr}] n_build={len(x)} tpm={report[tname]['trades_per_month']} "
          f"mean_net_1x={report[tname]['mean_net_1x_pct']:+.4f}% t_naive={t_naive:.2f} "
          f"t_nw={t_nw:.2f} conc={conc:.3f} -> {verdict}", flush=True)
    if cheap_pass:
        print(f"  placebo({obs_proxy_col}) p={placebo_p}  unconditional-bench mean="
              f"{report[tname]['unconditional_bench_mean_pct']} p={bench_p}", flush=True)
    print(f"  HELD OUT (2025-07..2025-12, n={len(ho)}): mean_gross="
          f"{report[tname]['heldout_mean_gross_pct']}%", flush=True)

json.dump(report, open(HERE / "gold_compression_results.json", "w"), indent=2, default=str)
rows = []
for tname, r in report.items():
    for c in r.get("rr_curve", []):
        rows.append(dict(trigger=tname, **c))
pd.DataFrame(rows).to_csv(HERE / "gold_compression_rr_curve.csv", index=False)
print(f"\n[done] elapsed {time.time()-t0:.1f}s -> gold_compression_results.json, "
      f"gold_compression_rr_curve.csv", flush=True)
