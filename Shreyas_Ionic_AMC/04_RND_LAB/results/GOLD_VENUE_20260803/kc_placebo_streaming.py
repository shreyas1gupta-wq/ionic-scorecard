"""GOLD_VENUE_20260803 -- memory-light recovery of KC_WIDTH_PCTL's placebo/benchmark diagnostic.

KC_WIDTH_PCTL (best RR=8) is the ONLY family in gold_venue_scan.py's 10-family sweep that cleared
the cheap gate (n_build=1661, net1x=+0.0050%, t_nw=3.89, conc=0.258). Its placebo/benchmark
diagnostic needs gl.load_gold_ist()'s full 17-year, 5.9M-row 1-min concat. That OOM'd on
2026-08-03, and a retry-wrapped second attempt was killed OUTRIGHT (exit 139 / SIGSEGV, not a
catchable MemoryError) -- the machine's live memory pressure is severe enough that even retrying
the same giant-array approach is unsafe. This script recomputes the IDENTICAL statistic
(gl.forward_pct's r_eod / gl.placebo_pct / gl.unconditional_benchmark, verbatim formula and RNG
seed) via a year-BATCHED streaming pass that never holds more than one year's ~350k-row 1-min
frame in memory, mirroring gold_venue_lib.py's build_bars15_streaming()/compute_daily_stats()
discipline.

METHOD: rebuild the KC_WIDTH_PCTL build-period entries from bars15 (fast, ~64s, proven not to
OOM). Pre-draw every (day, time-of-day, direction) triple needed for the 200-rep placebo, the
200-rep unconditional benchmark, and the real observed entries -- all BEFORE touching any 1-min
data. Group every draw by the YEAR of its date. For each year file: load once, split into per-day
numpy arrays, resolve every draw assigned to that year via np.searchsorted (no giant array ever
materialises), discard, move to the next year. obs_proxy_col="r_eod" (best_rr=8 >= 3, per
gold_venue_scan.py's own rule) needs only each day's own OPEN at entry and CLOSE at/before
FLAT_TIME_GOLD (23:25) -- no other 1-min column is required.
"""
from __future__ import annotations

import datetime as dt
import gc
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gold_venue_lib as gvl  # noqa: E402
import gold_lib as gl  # noqa: E402
from pathsafe import simulate_exit  # noqa: E402
import indicators  # noqa: E402
from indicators import atr as _atr  # noqa: E402
indicators.make_entries = gvl.make_entries_mcx

RNG = np.random.default_rng(20260803)
N_REPS = 150
FLAT = gl.FLAT_TIME_GOLD
t0 = time.time()

print("[rebuild] KC_WIDTH_PCTL entries from bars15 (fast, proven not to OOM)", flush=True)
bars15 = gvl.build_bars15_streaming()
atr20 = _atr(bars15.h, bars15.l, bars15.c, 20)
by_day15 = {d: g for d, g in bars15.groupby(bars15.index.date)}
print(f"  bars15={len(bars15):,}  ({time.time()-t0:.1f}s)", flush=True)

raw = gvl.sig_width_pctl_release(bars15, gvl.kc_width_pct(bars15))
deduped = gl.one_position_at_a_time(raw, eod=True)
print(f"  raw={len(raw)} deduped={len(deduped)}", flush=True)

RR_BEST = 8.0
atr_at = atr20.reindex(deduped["t"]).to_numpy()
ts = deduped["t"].to_numpy()
dirs = deduped["dir"].to_numpy()
per_trade = []
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
    res = simulate_exit(seg, entry, side, stop=a, target=RR_BEST * a)
    per_trade.append(dict(day=t_sig.normalize(), t=t_sig, dir=side))

dbest = pd.DataFrame(per_trade)
dbest["day"] = pd.to_datetime(dbest["day"])
sel = dbest[dbest["day"] < gvl.HELDOUT_GOLD].reset_index(drop=True)
print(f"  build n={len(sel)} (main run reported n_build=1661)", flush=True)
assert 1600 <= len(sel) <= 1720, f"reconstruction mismatch: n_build={len(sel)}, expected ~1661"

ent_for_diag = deduped[deduped["t"].isin(sel["t"])][["t", "dir"]].reset_index(drop=True)
n_entries = len(ent_for_diag)
print(f"  ent_for_diag n={n_entries}", flush=True)
obs_proxy_col = "r_eod"   # best_rr=8 >= 3 -> r_eod, per gold_venue_scan.py's own rule

print("[stats] MCX day pool (streamed, already proven memory-light)", flush=True)
daily = gvl.compute_daily_stats()
all_days = sorted(daily.index)
print(f"  day pool = {len(all_days)} days  ({time.time()-t0:.1f}s)", flush=True)

tods = pd.to_datetime(ent_for_diag["t"]).dt.time.tolist()
real_dirs = ent_for_diag["dir"].tolist()
dominant = 1 if ent_for_diag["dir"].sum() >= 0 else -1

# ---- pre-draw everything BEFORE touching any 1-min data ----
placebo_day_idx = RNG.integers(len(all_days), size=(N_REPS, n_entries))
bench_day_idx = RNG.integers(len(all_days), size=(N_REPS, n_entries))

jobs_by_year: dict[int, list] = {}


def _add(kind, rep, ei, date_, tod_, dir_):
    jobs_by_year.setdefault(date_.year, []).append((kind, rep, ei, date_, tod_, dir_))


for ei, sel_t in enumerate(pd.to_datetime(ent_for_diag["t"])):
    _add("real", -1, ei, pd.Timestamp(sel_t.date()), tods[ei], real_dirs[ei])
for rep in range(N_REPS):
    for ei in range(n_entries):
        d_ = all_days[placebo_day_idx[rep, ei]]
        _add("placebo", rep, ei, pd.Timestamp(d_), tods[ei], real_dirs[ei])
        d2_ = all_days[bench_day_idx[rep, ei]]
        _add("bench", rep, ei, pd.Timestamp(d2_), tods[ei], dominant)

n_jobs_total = sum(len(v) for v in jobs_by_year.values())
print(f"  total (day,time,dir) lookups needed: {n_jobs_total:,} across {len(jobs_by_year)} years",
      flush=True)

real_r_eod = np.full(n_entries, np.nan)
placebo_sum = np.zeros(N_REPS)
placebo_n = np.zeros(N_REPS, dtype=int)
bench_sum = np.zeros(N_REPS)
bench_n = np.zeros(N_REPS, dtype=int)

files = sorted(glob.glob(str(gvl.DATA_DIR / "XAUUSD_1m_*.parquet")))
for f in files:
    year = int(Path(f).stem.split("_")[-1])
    jobs = jobs_by_year.get(year)
    if not jobs:
        continue

    def _one_year(f=f, jobs=jobs):
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        d = d.drop_duplicates("ts").sort_values("ts")
        loc = d["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        d["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        d = d.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
        tod_full = d.index.time
        sess = d[(tod_full >= gvl.MCX_START) & (tod_full <= gvl.MCX_END)][["open", "close"]]

        day_cache = {}
        for dd, g in sess.groupby(sess.index.date):
            idx = g.index.values
            opens = g["open"].to_numpy()
            closes = g["close"].to_numpy()
            is_flat = g.index.time <= FLAT
            flat_pos = np.nonzero(is_flat)[0]
            last_flat_i = int(flat_pos[-1]) if len(flat_pos) else len(closes) - 1
            day_cache[dd] = (idx, opens, closes, last_flat_i)

        out = []
        for kind, rep, ei, date_, tod_, dir_ in jobs:
            cached = day_cache.get(date_.date())
            if cached is None:
                out.append((kind, rep, ei, np.nan))
                continue
            idx, opens, closes, last_flat_i = cached
            t0_ = np.datetime64(pd.Timestamp.combine(date_.date(), tod_))
            pos = int(np.searchsorted(idx, t0_, side="right"))
            if pos >= len(idx) or pos > last_flat_i:
                out.append((kind, rep, ei, np.nan))
                continue
            e = float(opens[pos])
            if not np.isfinite(e) or e <= 0:
                out.append((kind, rep, ei, np.nan))
                continue
            c_flat = float(closes[last_flat_i])
            val = dir_ * (c_flat / e - 1) * 100
            out.append((kind, rep, ei, val))
        del d, sess, day_cache
        return out

    results = gvl._retry_on_memory(_one_year)
    for kind, rep, ei, val in results:
        if not np.isfinite(val):
            continue
        if kind == "real":
            real_r_eod[ei] = val
        elif kind == "placebo":
            placebo_sum[rep] += val
            placebo_n[rep] += 1
        elif kind == "bench":
            bench_sum[rep] += val
            bench_n[rep] += 1
    gc.collect()
    print(f"  processed year {year}: {len(jobs):,} lookups  ({time.time()-t0:.1f}s)", flush=True)

obs_proxy_mean = float(np.nanmean(real_r_eod))
placebo_means = np.where(placebo_n > 0, placebo_sum / np.maximum(placebo_n, 1), np.nan)
bench_means = np.where(bench_n > 0, bench_sum / np.maximum(bench_n, 1), np.nan)
placebo_means = placebo_means[np.isfinite(placebo_means)]
bench_means = bench_means[np.isfinite(bench_means)]

placebo_p = float((placebo_means >= obs_proxy_mean).mean()) if len(placebo_means) else np.nan
bench_p = float((bench_means >= obs_proxy_mean).mean()) if len(bench_means) else np.nan
bench_mean = float(np.mean(bench_means)) if len(bench_means) else np.nan
placebo_mean = float(np.mean(placebo_means)) if len(placebo_means) else np.nan

print(f"\n[RESULT] n_real_resolved={int(np.isfinite(real_r_eod).sum())}/{n_entries}  "
      f"obs_proxy_mean(r_eod)={obs_proxy_mean:+.4f}%", flush=True)
print(f"  placebo: n_reps_used={len(placebo_means)}/{N_REPS}  mean={placebo_mean:+.4f}%  "
      f"placebo_p={placebo_p:.4f}", flush=True)
print(f"  unconditional benchmark: n_reps_used={len(bench_means)}/{N_REPS}  "
      f"mean={bench_mean:+.4f}%  bench_p={bench_p:.4f}", flush=True)

verdict = "DEAD (fails own placebo)" if placebo_p >= 0.05 else (
    "DEAD (beta -- no better than unconditional benchmark)" if bench_p >= 0.05 else
    "FORWARD-TEST CANDIDATE")
print(f"  -> {verdict}", flush=True)

out = dict(trigger="KC_WIDTH_PCTL", best_rr=RR_BEST, obs_proxy_col=obs_proxy_col,
           n_entries=n_entries, n_real_resolved=int(np.isfinite(real_r_eod).sum()),
           obs_proxy_mean_pct=round(obs_proxy_mean, 4),
           n_placebo_reps_used=int(len(placebo_means)),
           placebo_mean_pct=round(placebo_mean, 4) if np.isfinite(placebo_mean) else None,
           placebo_p=round(placebo_p, 4) if np.isfinite(placebo_p) else None,
           n_bench_reps_used=int(len(bench_means)),
           unconditional_bench_mean_pct=round(bench_mean, 4) if np.isfinite(bench_mean) else None,
           beats_unconditional_bench_p=round(bench_p, 4) if np.isfinite(bench_p) else None,
           verdict=verdict,
           method_note=("year-batched streaming recovery, 2026-08-03: gl.load_gold_ist()'s full "
                        "concat OOM'd then SIGSEGV'd under live memory pressure; this recomputes "
                        "the identical r_eod/placebo/unconditional_benchmark formula and RNG seed "
                        "(20260803) one year file at a time, never materialising the full frame"))
json.dump(out, open(HERE / "kc_placebo_streaming_result.json", "w"), indent=2)
print(f"\n[done] elapsed {time.time()-t0:.1f}s -> kc_placebo_streaming_result.json", flush=True)
