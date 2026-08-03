"""GOLD_VENUE_20260803 -- re-opening the gold intraday question now that the STT hike (Budget
2026, futures 0.02%->0.05% of notional, MCX untouched) makes MCX GOLDM 2.45x CHEAPER than NIFTY
futures (STT_RECOST_20260803/FINDINGS.md). The 2026-07-31 pass (GOLD_INTRADAY_20260731) tested
exactly 2 triggers (SQUEEZE_RELEASE, NR7_BREAKOUT) plus a dead cross-asset arm and found gold's
best gross edge (0.0149%, RR=5 SQUEEZE_RELEASE) below its own 0.0246% cost. This pass asks: is
there ANY gold intraday structure -- esp. time-of-day / session-structural ones with no NIFTY
analogue -- that clears the cost bar now that gold is the cheap venue.

PRE-REGISTRATION (written before any cell was run):
  10 signal families, each ONE trial for Bonferroni purposes (the RR sweep within a family is an
  exploration curve with a pre-registered selection rule -- max build-period net_1x -- not 9
  separate hypothesis tests; same convention as gold_compression.py 2026-07-31):
    2 REUSED verbatim  : SQUEEZE_RELEASE, NR7_BREAKOUT (indicators.py / gold_compression.py)
    4 NEW compression  : BB_WIDTH_PCTL, KC_WIDTH_PCTL, INSIDE_BAR_CLUSTER(k=3), ATR_CONSUMPTION_BRK
    2 NEW session-struct: ORB30, ORB60 (MCX-session-specific opening range, not a generic Donchian)
    2 NEW gap          : GAP_CONTINUATION, GAP_FADE (both directions disclosed, avoids picking the
                          flattering sign after the fact -- same discipline as the crossasset arm)
  KILL CRITERIA (pre-registered, same as firm standard): fails own placebo: DEAD. profit
  concentration >30%: FRAGILE/DEAD. Net edge <=0 at 1x cost after the pre-registered RR pick: DEAD
  by magnitude (skip the expensive placebo/benchmark diagnostics -- they can only reject a cell
  that already failed on magnitude/t/concentration, so skip to save runtime, exact cheap-gate
  cascade as gold_compression.py).
  Build = 2009-01-01..2025-06-30. HELD OUT = 2025-07-01..2025-12-31 (gl.HELDOUT_GOLD; data ends
  2025-12-31, no 2026 file -- landmine 3). Never selected on.
  ONE POSITION AT A TIME (gl.one_position_at_a_time, eod=True, intraday-only per the mandate).
  Costs: COST_1X_PCT=0.0246%, COST_2X_PCT=0.0492% (LITERAL 2x, per instruction -- harsher than
  the original mcx_cost_estimate.py's own partial-doubling of 0.0368%).
  Every stop/target through pathsafe.simulate_exit; PESSIMISTIC bound quoted always.
  Random-entry placebo (200 reps, matched count+time-of-day) for anything clearing the cheap gate.
  TIME-OF-DAY: every family's build-period trades at its pre-registered best RR are broken down by
  the 6 MCX session buckets (gold_venue_lib.BUCKET_EDGES), ALL buckets reported (not just the
  profitable ones) -- this is the mandate's centrepiece ask.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gold_venue_lib as gvl  # noqa: E402
import gold_lib as gl  # noqa: E402
from pathsafe import simulate_exit  # noqa: E402
import indicators  # noqa: E402
from indicators import atr as _atr, sig_squeeze_release  # noqa: E402

# BUG FOUND 2026-08-03 (before any cell ran): indicators.make_entries hard-filters entries to
# lib_signals.TOD_START..TOD_END = 09:20-14:45 (NIFTY's own window). Gold's MCX session is
# 09:00-23:30; reusing the NIFTY filter verbatim would have silently zeroed every SQUEEZE_RELEASE
# / NR7_BREAKOUT / BB_WIDTH_PCTL / KC_WIDTH_PCTL / INSIDE_BAR_CLUSTER entry after 14:45 -- exactly
# the London-open/NY-open/late-session buckets this scan exists to test (mandate priority #1).
# Patch BOTH the indicators module's own global (so sig_squeeze_release's internal call picks it
# up) and this module's local name (so _nr7 below picks it up) to gold_venue_lib's MCX-aware
# version. gold_venue_lib.py's own sig_inside_bar_cluster/sig_width_pctl_release were fixed at
# their source instead (they call gvl.make_entries_mcx directly now).
indicators.make_entries = gvl.make_entries_mcx
make_entries = gvl.make_entries_mcx

RNG = np.random.default_rng(20260803)
N_REPS = 150
RR_GRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]
COST_1X, COST_2X = gvl.COST_1X_PCT, gvl.COST_2X_PCT
BUCKET_NAMES = [b[0] for b in gvl.BUCKET_EDGES]

# MEMORY NOTE (2026-08-03): this box was under severe system-wide virtual-memory pressure today
# (other processes had committed 62-63 of 64.7GB pagefile) -- even `gl.load_gold_ist()`'s own
# all-years concat of the full 1-min frame (~3.7M rows) OOM'd at a 5.6MiB allocation. Everything
# below is built from `gvl.build_bars15_streaming()` / `gvl.compute_daily_stats()`, which process
# ONE YEAR FILE AT A TIME and never hold more than ~350k raw 1-min rows in memory. The full 1-min
# `spot` frame is loaded LAZILY (see get_spot_by_day() below) and ONLY if a cell actually clears
# the cheap-gate cascade and needs its placebo/benchmark diagnostic -- on the 2026-07-31 prior
# pass NEITHER trigger cleared that gate, so this path is expected to be rarely/never exercised.
t0 = time.time()
print("[load] MCX 15-min bars, streamed one year at a time (memory-light)", flush=True)
bars15 = gvl.build_bars15_streaming()
print(f"       {len(bars15):,} bars  {bars15.index[0]} .. {bars15.index[-1]}  "
      f"({time.time()-t0:.1f}s)", flush=True)
by_day15 = {d: g for d, g in bars15.groupby(bars15.index.date)}
atr20 = _atr(bars15.h, bars15.l, bars15.c, 20)

print("[stats] per-day gap/OR/typical-range table (streamed one year at a time)", flush=True)
daily = gvl.compute_daily_stats()
print(f"       {len(daily):,} MCX days  ({time.time()-t0:.1f}s)", flush=True)

_spot_cache: dict = {}


def get_spot_by_day():
    """Lazy, cached, memory-guarded load of the full 1-min session-filtered spot (needed only by
    gl.placebo_pct/gl.forward_pct/gl.unconditional_benchmark for cells that clear the cheap gate).
    Returns (None, None) if the load fails so callers can degrade gracefully instead of crashing
    the whole run."""
    if "spot" not in _spot_cache:
        print("  [lazy-load] a cell cleared the cheap gate -- loading full 1-min spot for its "
              "placebo/benchmark diagnostic (this is the allocation that OOM'd earlier today)",
              flush=True)
        try:
            sp = gl.load_gold_ist()
            _spot_cache["spot"] = sp
            _spot_cache["by_day"] = gl.build_by_day(sp)
        except MemoryError as e:
            print(f"  [lazy-load FAILED] {e!r} -- diagnostic skipped, cell reported UNVERIFIED",
                  flush=True)
            _spot_cache["spot"] = None
            _spot_cache["by_day"] = None
    return _spot_cache["spot"], _spot_cache["by_day"]


# ------------------------------------------------------------------ day-keyed signal generators
def sig_gap(dir_sign: int) -> pd.DataFrame:
    rows = []
    for d, g in daily.iterrows():
        if not np.isfinite(g["gap_pct"]) or g["gap_pct"] == 0:
            continue
        db = by_day15.get(d)
        if db is None or len(db) < 2:
            continue
        rows.append(dict(t=db.index[0], dir=int(dir_sign * np.sign(g["gap_pct"]))))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["t", "dir"])


def _scan_breakout(db: pd.DataFrame, hi: float, lo: float, cutoff):
    after = db[db.index.time > cutoff]
    for t, row in after.iterrows():
        if row["c"] > hi:
            return t, 1
        if row["c"] < lo:
            return t, -1
    return None, None


def sig_orb(minutes: int) -> pd.DataFrame:
    cutoff = (pd.Timestamp("2000-01-01 09:00") + pd.Timedelta(minutes=minutes)).time()
    hi_col, lo_col = (f"or30_high", "or30_low") if minutes == 30 else (f"or60_high", "or60_low")
    rows = []
    for d, g in daily.iterrows():
        hi, lo = g[hi_col], g[lo_col]
        if not (np.isfinite(hi) and np.isfinite(lo)):
            continue
        db = by_day15.get(d)
        if db is None:
            continue
        t_brk, sgn = _scan_breakout(db, hi, lo, cutoff)
        if t_brk is not None:
            rows.append(dict(t=t_brk, dir=sgn))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["t", "dir"])


def sig_atr_consumption(thresh=0.40, cutoff_hour=13) -> pd.DataFrame:
    cutoff = pd.Timestamp(f"2000-01-01 {cutoff_hour}:00").time()
    rows = []
    for d, g in daily.iterrows():
        typical = g["typical_range_pct"]
        if not np.isfinite(typical) or typical <= 0:
            continue
        db = by_day15.get(d)
        if db is None:
            continue
        morn = db[db.index.time <= cutoff]
        if len(morn) < 4:
            continue
        session_open = db["o"].iloc[0]
        range_so_far_pct = (morn["h"].max() - morn["l"].min()) / session_open * 100
        if range_so_far_pct / typical >= thresh:
            continue  # not compressed -> no signal today
        t_brk, sgn = _scan_breakout(db, morn["h"].max(), morn["l"].min(), cutoff)
        if t_brk is not None:
            rows.append(dict(t=t_brk, dir=sgn))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["t", "dir"])


TRIGGERS = {
    "SQUEEZE_RELEASE":    lambda: sig_squeeze_release(bars15),
    "NR7_BREAKOUT":       lambda: _nr7(bars15),
    "BB_WIDTH_PCTL":      lambda: gvl.sig_width_pctl_release(bars15, gvl.bb_width_pct(bars15)),
    "KC_WIDTH_PCTL":      lambda: gvl.sig_width_pctl_release(bars15, gvl.kc_width_pct(bars15)),
    "INSIDE_BAR_CLUSTER": lambda: gvl.sig_inside_bar_cluster(bars15, k=3),
    "ATR_CONSUMPTION_BRK": lambda: sig_atr_consumption(),
    "ORB30":              lambda: sig_orb(30),
    "ORB60":              lambda: sig_orb(60),
    "GAP_CONTINUATION":   lambda: sig_gap(+1),
    "GAP_FADE":           lambda: sig_gap(-1),
}


def _nr7(bars, n=7):
    rng_ = bars.h - bars.l
    is_nr = rng_ == rng_.rolling(n).min()
    nr_high = bars.h.where(is_nr).ffill()
    nr_low = bars.l.where(is_nr).ffill()
    fresh = is_nr.shift(1).fillna(False)
    bull = fresh & (bars.c > nr_high.shift(1))
    bear = fresh & (bars.c < nr_low.shift(1))
    return make_entries(bull, bear, bars.index)


def _checkpoint():
    """Incremental checkpoint (2026-08-03: jobs in this fleet have died mid-run repeatedly today).
    Called after EVERY family below so a crash loses at most one family's diagnostics, never the
    whole run. Overwrites the same 3 files each time -- cheap at 10 families."""
    pd.DataFrame(all_curve_rows).to_csv(HERE / "cells.csv", index=False)
    pd.DataFrame(all_bucket_rows).to_csv(HERE / "timebuckets.csv", index=False)
    json.dump(report, open(HERE / "gold_venue_results.json", "w"), indent=2, default=str)


# ------------------------------------------------------------------------------ the family loop
report = {}
all_curve_rows = []
all_bucket_rows = []
for tname, tfunc in TRIGGERS.items():
    print(f"\n=== {tname} ===", flush=True)
    raw = tfunc()
    if raw is None or raw.empty:
        print("  no raw signals, skip", flush=True)
        continue
    deduped = gl.one_position_at_a_time(raw, eod=True)
    print(f"  raw={len(raw)}  one-position-at-a-time={len(deduped)} "
          f"({100*len(deduped)/max(len(raw),1):.1f}% kept)", flush=True)
    if len(deduped) < 60:
        print("  too few signals after dedup, skip", flush=True)
        continue

    atr_at = atr20.reindex(deduped["t"]).to_numpy()
    ts = deduped["t"].to_numpy()
    dirs = deduped["dir"].to_numpy()

    per_trade = {rr: [] for rr in RR_GRID}
    for i in range(len(deduped)):
        t_sig = pd.Timestamp(ts[i])
        a = atr_at[i]
        if not np.isfinite(a) or a <= 0:
            continue
        day = by_day15.get(t_sig.date())
        if day is None:
            continue
        fwd = day[day.index > t_sig]
        if len(fwd) < 4:
            continue
        entry = float(fwd["o"].iloc[0])
        seg = fwd[["h", "l", "c"]].rename(columns={"h": "high", "l": "low", "c": "close"})
        side = int(dirs[i])
        entry_bucket = gvl.time_bucket(pd.Series([fwd.index[0]])).iloc[0]
        for rr in RR_GRID:
            res = simulate_exit(seg, entry, side, stop=a, target=rr * a)
            per_trade[rr].append(dict(
                day=t_sig.normalize(), t=t_sig, entry_t=fwd.index[0], bucket=entry_bucket,
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
        mean_gross = float(d["pnl_pct_p"].mean())
        t_nw = gl.nw_tstat(d["pnl_pct_p"].values)
        curve.append(dict(trigger=tname, RR=rr, n=len(d), hit_rate=round(hit, 4),
                          null_1_over_1plusR=round(null, 4), excess_hit=round(hit - null, 4),
                          mean_gross_pct=round(mean_gross, 4),
                          mean_net_1x_pct=round(mean_gross - COST_1X, 4),
                          mean_net_2x_pct=round(mean_gross - COST_2X, 4),
                          t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None))
        print(f"  RR={rr:<4} n={len(d):<5} hit={hit:.3f} null={null:.3f} "
              f"excess={hit-null:+.3f}  gross={mean_gross:+.4f}%  "
              f"net1x={mean_gross-COST_1X:+.4f}%  net2x={mean_gross-COST_2X:+.4f}%  "
              f"t_nw={t_nw:.2f}", flush=True)
    all_curve_rows.extend(curve)
    if not curve:
        print("  no RR cell had n>=40, skip", flush=True)
        report[tname] = dict(rr_curve=curve, verdict="INSUFFICIENT_N")
        _checkpoint()
        continue

    cdf = pd.DataFrame(curve)
    best_rr = float(cdf.loc[cdf["mean_net_1x_pct"].idxmax(), "RR"])
    print(f"  -> best RR (pre-registered: max build net_1x): {best_rr}", flush=True)

    dbest = pd.DataFrame(per_trade[best_rr])
    dbest["day"] = pd.to_datetime(dbest["day"])
    sel = dbest[dbest["day"] < gvl.HELDOUT_GOLD]
    ho = dbest[dbest["day"] >= gvl.HELDOUT_GOLD]
    x = sel["pnl_pct_p"]
    t_naive, p_naive = gl.naive_tstat(x.values)
    t_nw = gl.nw_tstat(x.values)
    conc = gl.concentration(sel.rename(columns={"pnl_pct_p": "pnl"}).assign(
        pnl=sel["pnl_pct_p"] - COST_1X).assign(date=sel["day"].dt.date), "pnl")
    months = max(len(pd.PeriodIndex(sel["day"], freq="M").unique()), 1)
    net_1x_best = float(x.mean()) - COST_1X

    cheap_pass = net_1x_best > 0 and np.isfinite(t_nw) and abs(t_nw) >= 2.0 and conc <= 0.30
    placebo_p = bench_mean = bench_p = None
    diag_unavailable = False
    if cheap_pass:
        spot, by_day = get_spot_by_day()
        if spot is None:
            diag_unavailable = True
        else:
            ent_for_diag = deduped[deduped["t"].isin(sel["t"])][["t", "dir"]]
            obs_proxy_col = "r_eod" if best_rr >= 3 else "r60"
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
        print(f"  cheap gates failed (net1x={net_1x_best:+.4f}%, t_nw={t_nw:.2f}, "
              f"conc={conc:.3f}) -> skip placebo/benchmark", flush=True)

    verdict = "DEAD (magnitude/t/concentration)"
    if cheap_pass:
        if diag_unavailable:
            verdict = "CLEARS CHEAP GATE -- PLACEBO UNVERIFIED (memory constrained)"
        elif placebo_p is not None and placebo_p >= 0.05:
            verdict = "DEAD (fails own placebo)"
        elif bench_p is not None and bench_p >= 0.05:
            verdict = "DEAD (beta -- no better than unconditional benchmark)"
        else:
            verdict = "FORWARD-TEST CANDIDATE"

    # -------------------------------------------------------------- time-of-day decomposition
    bucket_rows = []
    for b in BUCKET_NAMES:
        bd = sel[sel["bucket"] == b]
        if len(bd) == 0:
            bucket_rows.append(dict(trigger=tname, bucket=b, n=0, mean_gross_pct=None,
                                    mean_net_1x_pct=None, win_pct=None, hit_rate=None))
            continue
        gm = float(bd["pnl_pct_p"].mean())
        bucket_rows.append(dict(
            trigger=tname, bucket=b, n=int(len(bd)), mean_gross_pct=round(gm, 4),
            mean_net_1x_pct=round(gm - COST_1X, 4), win_pct=round(float((bd["pnl_pct_p"] > 0).mean()), 4),
            hit_rate=round(float(bd["hit"].mean()), 4)))
    all_bucket_rows.extend(bucket_rows)
    print("  time-of-day (build, best RR):", flush=True)
    for r in bucket_rows:
        print(f"    {r['bucket']:<12} n={r['n']:<5} gross={r['mean_gross_pct']}  "
              f"net1x={r['mean_net_1x_pct']}  win%={r['win_pct']}  hit={r['hit_rate']}", flush=True)

    report[tname] = dict(
        rr_curve=curve, best_rr=best_rr, n_build=int(len(x)), n_heldout=int(len(ho)),
        trades_per_month=round(len(x) / months, 2),
        mean_gross_pct=round(float(x.mean()), 4),
        mean_net_1x_pct=round(net_1x_best, 4),
        mean_net_2x_pct=round(float(x.mean()) - COST_2X, 4),
        win_pct=round(float((x > 0).mean()), 4),
        hit_rate_target=round(float(sel["hit"].mean()), 4),
        null_1_over_1plusR=round(1 / (1 + best_rr), 4),
        t_naive=round(t_naive, 3) if np.isfinite(t_naive) else None,
        t_nw=round(t_nw, 3) if np.isfinite(t_nw) else None,
        concentration=round(conc, 3),
        placebo_p=round(placebo_p, 4) if placebo_p is not None and np.isfinite(placebo_p) else None,
        unconditional_bench_mean_pct=round(bench_mean, 4) if bench_mean is not None and np.isfinite(bench_mean) else None,
        beats_unconditional_bench_p=round(bench_p, 4) if bench_p is not None and np.isfinite(bench_p) else None,
        heldout_mean_gross_pct=round(float(ho["pnl_pct_p"].mean()), 4) if len(ho) > 10 else None,
        heldout_n=int(len(ho)),
        heldout_mean_net_1x_pct=round(float(ho["pnl_pct_p"].mean()) - COST_1X, 4) if len(ho) > 10 else None,
        time_of_day=bucket_rows,
        verdict=verdict,
    )
    print(f"  [best RR={best_rr}] n_build={len(x)} tpm={report[tname]['trades_per_month']} "
          f"net1x={net_1x_best:+.4f}% t_naive={t_naive:.2f} t_nw={t_nw:.2f} conc={conc:.3f} "
          f"-> {verdict}", flush=True)
    print(f"  HELD OUT n={len(ho)}: gross={report[tname]['heldout_mean_gross_pct']}% "
          f"net1x={report[tname]['heldout_mean_net_1x_pct']}%", flush=True)
    _checkpoint()

print(f"\n[done family loop] elapsed {time.time()-t0:.1f}s", flush=True)

# ------------------------------------------------------------------- descriptive session profile
# BUG FOUND 2026-08-03 (before any cell ran): this section originally referenced a bare `spot`
# global that is ONLY assigned inside the family loop's lazy cheap-gate branch (line ~284) -- if
# NO family cleared the cheap gate (as happened on the entire 2026-07-31 prior pass), `spot` was
# never assigned and this section would NameError, losing every result computed above it. Rebuilt
# as a memory-light streaming pass (one year file at a time) so it is now BOTH crash-proof and
# immune to the full-frame OOM that hit gl.load_gold_ist() earlier today.
print("\n=== SESSION PROFILE (descriptive, unconditional) ===", flush=True)
print("  (memory-light streaming pass, one year file at a time)", flush=True)
prof_df = gvl.compute_session_profile_streaming()
for _, r in prof_df.iterrows():
    print(f"  {r['bucket']:<12} n_days={r['n_days']:<5} mean_1min_ret_bps={r['mean_1min_logret_bps']:+.4f} "
          f"std_1min_bps={r['std_1min_logret_bps']:.4f} "
          f"mean_range_pct={r['mean_bucket_range_pct']:.4f}", flush=True)
prof_df.to_csv(HERE / "session_profile.csv", index=False)

# --------------------------------------------------------------------------------- RR-curve verdict
print("\n=== RR-CURVE VERDICT (excess-hit slope across families) ===", flush=True)
cdf_all = pd.DataFrame(all_curve_rows)
slope_rows = []
for tname, g in cdf_all.groupby("trigger"):
    g = g.sort_values("RR")
    if len(g) < 3:
        continue
    rho, _ = stats.spearmanr(g["RR"], g["excess_hit"])
    slope_rows.append(dict(trigger=tname, n_rr_pts=len(g), spearman_RR_vs_excesshit=round(rho, 3),
                           negative=bool(rho < 0)))
    print(f"  {tname:<22} spearman(RR, excess_hit)={rho:+.3f} {'NEGATIVE' if rho < 0 else 'positive'}",
          flush=True)
neg_n = sum(r["negative"] for r in slope_rows)
print(f"  -> {neg_n}/{len(slope_rows)} families show excess-hit DECLINING as RR rises", flush=True)
pd.DataFrame(slope_rows).to_csv(HERE / "rr_slope_verdict.csv", index=False)

print(f"\n[ALL DONE] elapsed {time.time()-t0:.1f}s", flush=True)
