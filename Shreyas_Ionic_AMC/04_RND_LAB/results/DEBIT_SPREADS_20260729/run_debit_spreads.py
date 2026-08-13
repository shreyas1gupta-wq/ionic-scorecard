"""ARM: DEBIT SPREADS -- naked long option vs debit call/put spread, matched entries.
Structurer: Aakash Jain. 2026-07-29. Pre-registration: ./PRE_REGISTRATION.md (read first).

Reuses (does not re-implement):
  - intraday_options_strategy/buying/chain.py            (option-chain data access)
  - .../signal_budget/measure_signal_budget.py            (sweep_signals, orb_vol_filter)
  - intraday_options_strategy/buying/engine_swing.py      (entry_days -- daily trend triggers)
  - intraday_options_strategy/buying/engine.py            (STEP=50)

New in this file: the hold-mode grid (intraday_flat / reversal / 5day) x spread-width grid
(0=naked,1,2,4) x strike-offset grid (ATM,1ITM) x DTE-bucket grid, applied uniformly across
6 signal sources, with the Rs25/lot/side cost model + flat-point slippage from SHARED_CONTEXT.

Data note: chain.py reads the HF 1-min OPTIONS parquet (real per-minute traded OHLC+volume
through expiry-day close), NOT the F&O bhavcopy SETTLE_PR column -- so landmine #9 (bhavcopy
expiry settle = underlying level) does not apply here; held-to-expiry exits use the real last
traded 1-min close, which is exactly what we want (no intrinsic-settle hack needed).
"""
from __future__ import annotations

import datetime as dt
import functools
import gc
import json
import pickle
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PYTHON_EXE = sys.executable
EXTRACT_SCRIPT = Path(__file__).parent / "extract_batch.py"

REPO = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BUYING = REPO / "intraday_options_strategy" / "buying"
SIGBUD = REPO / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "EMA_INTRADAY_BUYING_20260729" / "signal_budget"
OUT = Path(__file__).parent

sys.path.insert(0, str(BUYING))
sys.path.insert(0, str(SIGBUD))

import chain                                   # noqa: E402
from engine import STEP                        # noqa: E402  (=50)
import engine_swing as swing                   # noqa: E402
import measure_signal_budget as msb            # noqa: E402  (sweep_signals, orb_vol_filter, load_spot, resample, nw_tstat)

# This machine runs the full multi-agent firm concurrently (psutil showed only 3.3-3.7GB
# free of 16.8GB total, other python.exe processes at ~1GB each). Reading the 261 expiry
# parquet files IN-PROCESS -- even column-pruned, one at a time, with retry-on-
# MemoryError -- still SEGFAULTED under real contention (confirmed twice; a segfault is
# not a catchable Python exception, so no in-process try/except can save it). Fix:
# isolate every extraction in a disposable CHILD process (extract_batch.py). A crash
# there costs at most one small batch, never the long-lived parent -- see preload_legs().
LOT = 75
COST_PER_SIDE_RS = 25.0            # Rs/lot/side, flat (SHARED_CONTEXT)
SLIP_LONG_PT = 0.25                # pt/side, near-the-money leg (low end of firm's 0.25-0.5 band)
SLIP_SHORT_PT = 0.50               # pt/side, further-OTM short leg (high end -- thinner leg)
BUILD_END = dt.date(2025, 12, 31)
SAFETY_CAP_DAYS = 15               # reversal-hold safety cap if no reversal ever fires
CAPITAL = 3_00_000.0               # matches engine_swing.SwingCfg defaults (not fabricated)
RISK_PER_TRADE = 0.03

DTE_BUCKETS = {"0-1": (0, 1), "2-3": (2, 3), "4-7": (4, 7), "8-15": (8, 15)}
OFFSETS = {"ATM": 0, "1ITM": -1}
WIDTHS = [0, 1, 2, 4]               # 0 = naked
HOLDS = ["intraday_flat", "reversal", "5day"]

# ----------------------------------------------------------------------------------
# leg cache: (exp, strike, otype) -> DataFrame[t] open,close,volume  (sorted by t)
# Populated ENTIRELY by preload_legs() before the grid runs. get_leg() is a pure,
# disk-free lookup; a miss returns an empty frame (treated as "no fill" downstream) --
# it never triggers a fresh pyarrow read, by design (that repeated-read pattern is what
# crashed the process, see note above).
# ----------------------------------------------------------------------------------
_LEG_CACHE: dict = {}
_EMPTY_LEG = pd.DataFrame(columns=["open", "close", "volume"])


def get_leg(exp: dt.date, strike: int, otype: str) -> pd.DataFrame:
    return _LEG_CACHE.get((exp, strike, otype), _EMPTY_LEG)


SCRATCH = OUT / "leg_cache_files"


def _run_batch(exp_chunk: list, by_exp: dict, tag: str) -> bool:
    """Spawn one child process for this chunk of expiries. Returns True iff the child
    reported BATCH_DONE (a crash / timeout returns False; caller checks which output
    files actually landed either way -- a mid-batch crash still keeps prior files)."""
    spec = {e.isoformat(): [[s, o] for s, o in by_exp[e]] for e in exp_chunk}
    spec_path = SCRATCH / f"_spec_{tag}.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    try:
        r = subprocess.run([PYTHON_EXE, str(EXTRACT_SCRIPT), str(spec_path), str(SCRATCH)],
                            timeout=180, capture_output=True, text=True)
        ok = r.returncode == 0 and "BATCH_DONE" in (r.stdout or "")
        if not ok:
            print(f"  [preload] batch {tag} exit={r.returncode} "
                  f"stderr_tail={(r.stderr or '')[-300:]}", flush=True)
        return ok
    except subprocess.TimeoutExpired:
        print(f"  [preload] batch {tag} TIMEOUT", flush=True)
        return False
    finally:
        spec_path.unlink(missing_ok=True)


def preload_legs(needed: set[tuple], batch_size: int = 6) -> list:
    """needed = set of (exp, strike, otype). Each expiry is extracted by a DISPOSABLE
    child process (extract_batch.py), one pickle per expiry written to SCRATCH. Batched
    (batch_size expiries/process) for speed; any expiry whose output file is still
    missing after the batched pass gets one more try alone (isolates a bad file from its
    batch-mates) before being logged as SKIPPED. Parent process memory never touches the
    raw parquet data at all."""
    SCRATCH.mkdir(exist_ok=True)
    by_exp: dict = {}
    for exp, strike, otype in needed:
        by_exp.setdefault(exp, set()).add((strike, otype))
    exps_sorted = sorted(by_exp)
    t0 = time.time()

    def outfile(e):
        return SCRATCH / f"{e.isoformat()}.pkl"

    todo = [e for e in exps_sorted if not outfile(e).exists()]
    print(f"[preload] {len(exps_sorted)} expiries needed, {len(todo)} not yet cached "
          f"on disk from a prior run", flush=True)
    for size, label in [(batch_size, "batch"), (1, "retry-solo")]:
        if not todo:
            break
        next_todo = []
        n_chunks = (len(todo) + size - 1) // size
        for ci in range(n_chunks):
            chunk = todo[ci * size:(ci + 1) * size]
            if all(outfile(e).exists() for e in chunk):
                continue
            _run_batch(chunk, by_exp, f"{label}{ci}")
            for e in chunk:
                if not outfile(e).exists():
                    next_todo.append(e)
            if ci % 10 == 0:
                print(f"  [preload/{label}] {ci+1}/{n_chunks} chunks "
                      f"({time.time()-t0:.0f}s)", flush=True)
        todo = next_todo

    skipped = todo
    for e in skipped:
        print(f"  [preload] SKIPPED {e} -- failed even solo after batch retry", flush=True)

    n_loaded = 0
    for e in exps_sorted:
        p = outfile(e)
        if not p.exists():
            continue
        with open(p, "rb") as f:
            result = pickle.load(f)
        for (strike, otype), s in result.items():
            _LEG_CACHE[(e, strike, otype)] = s
            n_loaded += 1
        del result
    print(f"[preload] DONE: {len(exps_sorted) - len(skipped)}/{len(exps_sorted)} expiries, "
          f"{n_loaded:,} leg-slices loaded, {len(skipped)} skipped, "
          f"{time.time()-t0:.0f}s", flush=True)
    return skipped


def _atm(x: float) -> int:
    return int(round(x / STEP) * STEP)


# ----------------------------------------------------------------------------------
# day -> expiry cache per DTE bucket
# ----------------------------------------------------------------------------------
_EXP_CACHE: dict = {}


def expiry_for(day: dt.date, dte_label: str):
    key = (day, dte_label)
    if key in _EXP_CACHE:
        return _EXP_CACHE[key]
    mn, mx = DTE_BUCKETS[dte_label]
    e = chain.nearest_expiry(day, mn, mx)
    _EXP_CACHE[key] = e
    return e


# ----------------------------------------------------------------------------------
# 1. Signal sources -> entries DataFrame [t, dir] + reversal_t precomputed
# ----------------------------------------------------------------------------------

def _reversal_times_mixed(entries: pd.DataFrame) -> pd.Series:
    """For a mixed-direction signal table (sorted by t), find for each row the first
    STRICTLY LATER timestamp with the opposite dir (searchsorted on the two direction
    sub-series). NaT if none within SAFETY_CAP_DAYS."""
    entries = entries.sort_values("t").reset_index(drop=True)
    pos_t = entries.loc[entries["dir"] == 1, "t"].values
    neg_t = entries.loc[entries["dir"] == -1, "t"].values
    out = np.empty(len(entries), dtype="datetime64[ns]")
    out[:] = np.datetime64("NaT")
    tvals = entries["t"].values
    dvals = entries["dir"].values
    for i in range(len(entries)):
        t0 = tvals[i]
        cap = t0 + np.timedelta64(SAFETY_CAP_DAYS, "D")
        target = neg_t if dvals[i] == 1 else pos_t
        j = np.searchsorted(target, t0, side="right")
        if j < len(target) and target[j] <= cap:
            out[i] = target[j]
    entries["reversal_t"] = out
    return entries


def load_intraday_signals(spot: pd.DataFrame, bars5: pd.DataFrame, bars15: pd.DataFrame) -> dict:
    sweeps = msb.sweep_signals(bars15)
    orb = msb.orb_vol_filter(bars5)
    out = {
        "sweep_priorday_reclaim": sweeps["priorday_reclaim"],
        "sweep_intraday_continue": sweeps["intraday_continue"],
        "volbrk_orb_volfilter": orb,
    }
    return {k: _reversal_times_mixed(v.copy()) for k, v in out.items() if not v.empty}


def load_trend_signals(spot: pd.DataFrame) -> dict:
    """engine_swing.entry_days() per trigger, dir always +1, entry at cfg.entry_hhmm.
    Reversal = first later day the MIRRORED (bearish) condition of the same trigger fires."""
    d = swing._daily(spot)
    c = d["close"]
    out = {}
    for trig in ("ema_cross", "breakout20", "bigday"):
        cfg = swing.SwingCfg(trigger=trig)
        edays = swing.entry_days(spot, cfg)
        if not edays:
            continue
        ef = c.ewm(span=cfg.ema_fast, adjust=False).mean()
        es = c.ewm(span=cfg.ema_slow, adjust=False).mean()
        ret1 = c.pct_change()
        ll = d["low"].rolling(cfg.breakout_n).min()
        if trig == "ema_cross":
            mirror = (ef < es)
        elif trig == "breakout20":
            mirror = c < ll.shift(1)
        else:
            mirror = ret1 < -cfg.bigday_ret
        mirror_days = np.array(sorted([dd for dd, v in mirror.items() if bool(v)]))
        h, m = int(cfg.entry_hhmm[:2]), int(cfg.entry_hhmm[3:])
        rows = []
        for dd in edays:
            t0 = pd.Timestamp(dd) + pd.Timedelta(hours=h, minutes=m)
            cap = np.datetime64(dd) + np.timedelta64(SAFETY_CAP_DAYS, "D")
            j = np.searchsorted(mirror_days, np.datetime64(dd), side="right")
            rev_t = pd.NaT
            if j < len(mirror_days) and mirror_days[j] <= cap:
                rev_day = mirror_days[j]
                rev_t = pd.Timestamp(rev_day) + pd.Timedelta(hours=15, minutes=15)
            rows.append({"t": t0, "dir": 1, "reversal_t": rev_t})
        out[f"trend_{trig}"] = pd.DataFrame(rows)
    return out


# ----------------------------------------------------------------------------------
# 2. Core: base entry info per (signal, offset, dte_bucket) -- reused across width/hold
# ----------------------------------------------------------------------------------

def discover_keys(entries: pd.DataFrame, spot_close: pd.Series, spot_idx: np.ndarray,
                   offset_val: int, dte_label: str, needed: set) -> None:
    """Dry run of build_base_entries' day/exp/strike arithmetic ONLY (no leg data
    touched) -- registers every (exp,strike,otype) the real pass will need, long AND
    every short-leg candidate strike for width in {1,2,4}, into the shared `needed` set."""
    for row in entries.itertuples(index=False):
        t0, d0 = row.t, row.dir
        day = pd.Timestamp(t0).date()
        exp = expiry_for(day, dte_label)
        if exp is None or exp <= day:
            continue
        pos = np.searchsorted(spot_idx, np.datetime64(t0), side="right") - 1
        if pos < 0:
            continue
        s0 = spot_close.iloc[pos]
        if not np.isfinite(s0):
            continue
        k = _atm(s0) - offset_val * STEP * d0
        otype = "CE" if d0 == 1 else "PE"
        needed.add((exp, k, otype))
        for width in (1, 2, 4):
            sk = k + width * STEP * d0
            needed.add((exp, sk, otype))


def build_base_entries(entries: pd.DataFrame, spot_close: pd.Series, spot_idx: np.ndarray,
                        offset_val: int, dte_label: str) -> list[dict]:
    out = []
    for row in entries.itertuples(index=False):
        t0, d0, rev_t = row.t, row.dir, row.reversal_t
        day = pd.Timestamp(t0).date()
        exp = expiry_for(day, dte_label)
        if exp is None or exp <= day:
            continue
        # spot at/just before signal time
        pos = np.searchsorted(spot_idx, np.datetime64(t0), side="right") - 1
        if pos < 0:
            continue
        s0 = spot_close.iloc[pos]
        if not np.isfinite(s0):
            continue
        k = _atm(s0) - offset_val * STEP * d0
        otype = "CE" if d0 == 1 else "PE"
        long_df = get_leg(exp, k, otype)
        if long_df.empty:
            continue
        idx = long_df.index.values
        j = np.searchsorted(idx, np.datetime64(t0), side="right")
        if j >= len(idx):
            continue
        entry_bar = long_df.index[j]
        long_open = long_df["open"].iloc[j]
        if not np.isfinite(long_open) or long_open <= 0:
            continue
        out.append({
            "t0": t0, "dir": d0, "reversal_t": rev_t, "day": day, "exp": exp, "k": k,
            "otype": otype, "entry_bar": entry_bar, "long_open": long_open,
            "long_df": long_df,
        })
    return out


# ----------------------------------------------------------------------------------
# 3. Exit-time resolution per hold mode
# ----------------------------------------------------------------------------------

def _last_bar_at_or_before(idx: np.ndarray, cutoff: np.datetime64):
    j = np.searchsorted(idx, cutoff, side="right") - 1
    return j if j >= 0 else None


def resolve_exit(hold_mode: str, entry_bar: pd.Timestamp, exp: dt.date,
                  reversal_t, long_idx: np.ndarray) -> tuple:
    """Return (exit_j_index_into_long_idx, reason). Bounded by data end (== expiry's
    last traded bar for that strike, real 1-min close -- no intrinsic-settle hack needed,
    see module docstring)."""
    last_j = len(long_idx) - 1
    if hold_mode == "intraday_flat":
        day = pd.Timestamp(entry_bar).date()
        cutoff = np.datetime64(pd.Timestamp(day) + pd.Timedelta(hours=15, minutes=25))
        j = _last_bar_at_or_before(long_idx, cutoff)
        if j is None or j <= 0:
            return last_j, "data_end"
        j = max(j, np.searchsorted(long_idx, np.datetime64(entry_bar), side="right"))
        j = min(j, last_j)
        if long_idx[j] <= np.datetime64(entry_bar):
            return last_j, "data_end"
        return j, ("timebox" if long_idx[j] <= cutoff else "data_end")
    if hold_mode == "5day":
        target_day = pd.Timestamp(entry_bar).date() + dt.timedelta(days=5)
        cutoff = np.datetime64(pd.Timestamp(target_day) + pd.Timedelta(hours=15, minutes=15))
        j = _last_bar_at_or_before(long_idx, cutoff)
        if j is None or j <= 0:
            j = last_j
        reason = "timebox" if long_idx[min(j, last_j)] < np.datetime64(exp) else "expiry"
        return min(j, last_j), reason
    if hold_mode == "reversal":
        if pd.isna(reversal_t):
            # safety cap: SAFETY_CAP_DAYS after entry, else data end (== expiry)
            cutoff = np.datetime64(entry_bar) + np.timedelta64(SAFETY_CAP_DAYS, "D")
            j = _last_bar_at_or_before(long_idx, cutoff)
            j = last_j if j is None else min(j, last_j)
            return j, "safety_cap_no_reversal"
        j = np.searchsorted(long_idx, np.datetime64(reversal_t), side="left")
        j = min(j, last_j)
        return j, "reversal"
    raise ValueError(hold_mode)


# ----------------------------------------------------------------------------------
# 4. Trade builder for one (base_entry, width, hold_mode)
# ----------------------------------------------------------------------------------

def make_trade(be: dict, width: int, hold_mode: str, offset_label: str, dte_label: str,
                signal_name: str) -> dict | None:
    long_df = be["long_df"]
    long_idx = long_df.index.values
    d0 = be["dir"]
    has_short = width > 0
    short_open = 0.0
    short_entry_vol = np.nan
    short_df = None
    if has_short:
        sk = be["k"] + width * STEP * d0
        short_df = get_leg(be["exp"], sk, be["otype"])
        sidx = short_df.index.values
        j = np.searchsorted(sidx, np.datetime64(be["entry_bar"]), side="left")
        if j >= len(sidx) or short_df.index[j] != be["entry_bar"]:
            # try next bar at/after entry_bar (align to long's entry bar or later)
            j2 = np.searchsorted(sidx, np.datetime64(be["entry_bar"]), side="left")
            if j2 >= len(sidx):
                return {"_no_fill": True, "signal": signal_name, "offset": offset_label,
                        "dte": dte_label, "width": width, "hold": hold_mode}
            j = j2
        short_open = short_df["open"].iloc[j]
        short_entry_vol = short_df["volume"].iloc[j]
        if not np.isfinite(short_open) or short_open <= 0:
            return {"_no_fill": True, "signal": signal_name, "offset": offset_label,
                    "dte": dte_label, "width": width, "hold": hold_mode}

    entry_debit_raw = be["long_open"] - short_open
    if entry_debit_raw <= 0:
        return None
    fill_debit = (be["long_open"] + SLIP_LONG_PT) - (short_open - SLIP_SHORT_PT if has_short else 0.0)

    exit_j, reason = resolve_exit(hold_mode, be["entry_bar"], be["exp"], be["reversal_t"], long_idx)
    if long_idx[exit_j] <= np.datetime64(be["entry_bar"]):
        exit_j = min(exit_j + 1, len(long_idx) - 1)
        if long_idx[exit_j] <= np.datetime64(be["entry_bar"]):
            return None
    exit_t = long_df.index[exit_j]
    long_exit_close = long_df["close"].iloc[exit_j]
    short_exit_close = 0.0
    short_exit_vol = np.nan
    if has_short:
        sj = np.searchsorted(short_df.index.values, np.datetime64(exit_t), side="right") - 1
        if sj < 0:
            sj = 0
        short_exit_close = short_df["close"].iloc[sj]
        short_exit_vol = short_df["volume"].iloc[sj]

    exit_val = long_exit_close - short_exit_close
    fill_exit = (long_exit_close - SLIP_LONG_PT) - (short_exit_close + SLIP_SHORT_PT if has_short else 0.0)

    n_sides = 4 if has_short else 2
    cost_pts = n_sides * COST_PER_SIDE_RS / LOT
    gross_pts = exit_val - entry_debit_raw
    net_pts = (fill_exit - fill_debit) - cost_pts

    outlay_per_lot = fill_debit * LOT
    lots = max(1, int((RISK_PER_TRADE * CAPITAL) // max(outlay_per_lot, 1)))
    qty = lots * LOT

    degenerate = (hold_mode == "5day" and DTE_BUCKETS[dte_label][1] < 5)
    return {
        "signal": signal_name, "offset": offset_label, "dte": dte_label,
        "hold": hold_mode, "width": width, "structure": "naked" if width == 0 else f"spread_w{width}",
        "entry_t": be["t0"], "entry_bar": be["entry_bar"], "exit_t": exit_t, "exp": be["exp"],
        "strike": be["k"],   # ATM-rounded spot proxy at entry -- notional = strike*LOT
        "dte0": (be["exp"] - be["day"]).days, "reason": reason, "dir": d0,
        "entry_debit_raw": entry_debit_raw, "fill_debit": fill_debit,
        "exit_val": exit_val, "fill_exit": fill_exit,
        "gross_pts": gross_pts, "net_pts": net_pts, "cost_pts": cost_pts,
        "lots": lots, "qty": qty, "gross_rs": gross_pts * qty, "net_rs": net_pts * qty,
        "short_entry_vol": short_entry_vol, "short_exit_vol": short_exit_vol,
        "is_forward": be["day"] > BUILD_END, "degenerate": degenerate,
        "hold_days": (exit_t.date() - be["entry_bar"].date()).days,
    }


# ----------------------------------------------------------------------------------
# 5. Grid runner
# ----------------------------------------------------------------------------------

def run_signal(signal_name: str, entries: pd.DataFrame, spot_close: pd.Series,
                spot_idx: np.ndarray) -> list[dict]:
    trades = []
    no_fill = 0
    for offset_label, offset_val in OFFSETS.items():
        for dte_label in DTE_BUCKETS:
            base = build_base_entries(entries, spot_close, spot_idx, offset_val, dte_label)
            for be in base:
                for width in WIDTHS:
                    for hold_mode in HOLDS:
                        tr = make_trade(be, width, hold_mode, offset_label, dte_label, signal_name)
                        if tr is None:
                            continue
                        if tr.get("_no_fill"):
                            no_fill += 1
                            continue
                        trades.append(tr)
            print(f"  [{signal_name}] offset={offset_label} dte={dte_label} "
                  f"base_entries={len(base)} trades_so_far={len(trades)}", flush=True)
    print(f"[{signal_name}] DONE: {len(trades)} trades, {no_fill} short-leg no-fill skips", flush=True)
    return trades


def main():
    t_start = time.time()
    spot = chain.load_index()
    spot_close = spot["close"]
    spot_idx = spot.index.values
    bars5 = msb.resample(spot, "5min")
    bars15 = msb.resample(spot, "15min")
    print(f"[spot] {len(spot):,} bars {spot.index[0]}..{spot.index[-1]}", flush=True)

    intraday = load_intraday_signals(spot, bars5, bars15)
    trend = load_trend_signals(spot)
    all_signals = {**intraday, **trend}
    print(f"[signals] {list(all_signals.keys())}", flush=True)
    for k, v in all_signals.items():
        print(f"  {k}: n={len(v)}", flush=True)

    print("\n[phase 1/2] discovering every (exp,strike,otype) the grid will need "
          "(no disk I/O yet)...", flush=True)
    needed: set = set()
    for name, ent in all_signals.items():
        for offset_val in OFFSETS.values():
            for dte_label in DTE_BUCKETS:
                discover_keys(ent, spot_close, spot_idx, offset_val, dte_label, needed)
    n_exps = len({k[0] for k in needed})
    print(f"[phase 1/2] {len(needed):,} unique (exp,strike,otype) legs across "
          f"{n_exps} expiries -- {time.time()-t_start:.0f}s elapsed", flush=True)

    print("\n[phase 2/2] preloading -- each expiry file read exactly once...", flush=True)
    skipped = preload_legs(needed)
    print(f"[phase 2/2] done -- {time.time()-t_start:.0f}s elapsed total, "
          f"{len(skipped)} expiries skipped (memory contention)", flush=True)
    if skipped:
        (OUT / "skipped_expiries.json").write_text(
            json.dumps([str(e) for e in skipped], indent=2), encoding="utf-8")

    all_trades = []
    for name, ent in all_signals.items():
        trs = run_signal(name, ent, spot_close, spot_idx)
        all_trades.extend(trs)
        df_partial = pd.DataFrame(all_trades)
        df_partial.to_csv(OUT / "trades_ALL_partial.csv", index=False)
        print(f"--- checkpoint saved after {name}: {len(all_trades)} total trades "
              f"({time.time()-t_start:.0f}s elapsed) ---", flush=True)

    df = pd.DataFrame(all_trades)
    df.to_csv(OUT / "trades_ALL.csv", index=False)
    print(f"\nTOTAL TRADES: {len(df)}  elapsed {time.time()-t_start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
