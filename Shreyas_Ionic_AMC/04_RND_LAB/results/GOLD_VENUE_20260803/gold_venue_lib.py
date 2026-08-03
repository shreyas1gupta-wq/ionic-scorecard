"""GOLD_VENUE_20260803 -- shared library. Re-opens the gold-intraday question under the new
cost regime (STT hike makes MCX gold 2.45x CHEAPER than NIFTY futures from 1 April 2026, see
STT_RECOST_20260803/FINDINGS.md). Reuses GOLD_INTRADAY_20260731/gold_lib.py VERBATIM for the
data load / tz-fix / cost model (consolidate reused code -- do not re-derive) and adds:
  - a continuous (NOT session-filtered) loader, needed for the MCX-session GAP test (the gap is
    defined against the price wherever XAUUSD was trading during MCX's 23:30-09:00 closed hours)
  - MCX session time-of-day buckets (6, covering 09:00-23:30 with no overlap)
  - a handful of NEW compression/session signal generators not covered by the 2026-07-31 pass
    (which only ran SQUEEZE_RELEASE and NR7_BREAKOUT)

LANDMINES (all verified in gold_lib.py / GOLD_INTRADAY_20260731, reused not re-derived):
  1. `ts` is HistData US-EASTERN LOCAL TIME, not IST. Converted via
     tz_localize("America/New_York") -> tz_convert("Asia/Kolkata") so the IANA tz db resolves
     every DST boundary. MCX session = 09:00-23:30 IST.
  2. XAUUSD SPOT USD, not MCX GOLDM INR. All results in % or ATR units, never rupees.
  3. Data ends 2025-12-31 -- no 2026 file. Held-out slice = 2025-07-01..2025-12-31 (gl.HELDOUT_GOLD).

SESSION BUCKETS (this file's own addition, [INFERENCE] on the exact London/NY anchor times --
the brief gave "roughly 13:30" and "roughly 18:30" IST and those are used as-is; "post-NY-close
stretch" is read as the LAST hours of the MCX session, i.e. after US cash-equity hours have
substantially wound down, since the literal NYSE 16:00 ET close falls at ~01:30-02:30 IST, past
MCX's own 23:30 cutoff and therefore not reachable within the same session):
  OPEN_ASIA    09:00-11:00  pre-London, thin Asia/India hours
  MID_ASIA     11:00-13:00  Asia midday lull
  LONDON_OPEN  13:00-15:00  centered on the ~13:30 IST London open
  LONDON_MID   15:00-18:00  London midday, pre-NY
  NY_OPEN      18:00-20:00  centered on the ~18:30 IST NY/COMEX open
  NY_LATE      20:00-23:30  US afternoon into the post-NY-close thinning stretch, MCX close
"""
from __future__ import annotations

import datetime as dt
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
OLD_GOLD_DIR = HERE.parent / "GOLD_INTRADAY_20260731"
TV_DIR = HERE.parent / "TV_INDICATORS_20260730"
LIB_DIR = HERE.parent.parent / "lib"
for p in (OLD_GOLD_DIR, TV_DIR, LIB_DIR):
    sys.path.insert(0, str(p))

import gold_lib as gl  # noqa: E402  (reused verbatim -- DATA_DIR, MCX_START/END, cost model, stats)
from indicators import atr as _atr, true_range, make_entries  # noqa: E402

DATA_DIR = gl.DATA_DIR
MCX_START, MCX_END = gl.MCX_START, gl.MCX_END
FLAT_TIME_GOLD = gl.FLAT_TIME_GOLD
HELDOUT_GOLD = gl.HELDOUT_GOLD
COST_1X_PCT = 0.0246   # mcx_cost_estimate.json, round trip, % of notional
COST_2X_PCT = 0.0492   # LITERAL 2x per Principal's instruction (the lib's own file only doubled
                       # judgement-call lines to 0.0368%; this run uses the harsher, explicitly
                       # requested "2x that cost" reading as the sensitivity bound)

BUCKET_EDGES = [
    ("OPEN_ASIA",   dt.time(9, 0),  dt.time(11, 0)),
    ("MID_ASIA",    dt.time(11, 0), dt.time(13, 0)),
    ("LONDON_OPEN", dt.time(13, 0), dt.time(15, 0)),
    ("LONDON_MID",  dt.time(15, 0), dt.time(18, 0)),
    ("NY_OPEN",     dt.time(18, 0), dt.time(20, 0)),
    ("NY_LATE",     dt.time(20, 0), dt.time(23, 30)),
]


def time_bucket(ts: pd.Series) -> pd.Series:
    """Assign each timestamp's time-of-day to one of the 6 MCX session buckets."""
    t = ts.dt.time if hasattr(ts, "dt") else pd.Series(ts).dt.time
    out = pd.Series("NONE", index=ts.index if hasattr(ts, "index") else None, dtype=object)
    for name, lo, hi in BUCKET_EDGES:
        m = (t >= lo) & (t < hi if hi != dt.time(23, 30) else t <= hi)
        out = out.mask(m, name)
    return out


def make_entries_mcx(bull_mask: pd.Series, bear_mask: pd.Series, index) -> pd.DataFrame:
    """MCX-session-aware replacement for `indicators.make_entries`.

    BUG FOUND 2026-08-03 (before any cell ran): `indicators.make_entries` hard-filters entries to
    `lib_signals.TOD_START..TOD_END` = 09:20-14:45, NIFTY's own window (chosen there so a trade has
    room to reach NIFTY's 15:25 flat time). Gold's session runs 09:00-23:30. Reusing the NIFTY
    function verbatim for SQUEEZE_RELEASE / NR7_BREAKOUT / BB_WIDTH_PCTL / KC_WIDTH_PCTL /
    INSIDE_BAR_CLUSTER would have silently zeroed every entry after 14:45 -- exactly the
    London-open/NY-open/late-session buckets this whole scan exists to test (priority #1 of the
    mandate). This mirrors indicators.make_entries's construction exactly, gated to
    MCX_START..FLAT_TIME_GOLD (09:00-23:25) instead."""
    t = index.time
    ok = (t >= MCX_START) & (t <= FLAT_TIME_GOLD)
    bm = bull_mask.fillna(False).to_numpy() & ok
    sm = bear_mask.fillna(False).to_numpy() & ok
    rows = [{"t": t_, "dir": 1} for t_ in index[bm]] + [{"t": t_, "dir": -1} for t_ in index[sm]]
    if not rows:
        return pd.DataFrame(columns=["t", "dir"])
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)


def load_gold_full_ist() -> pd.DataFrame:
    """Same ET->IST fix as gl.load_gold_ist() but WITHOUT the MCX-session filter.
    **MEMORY WARNING -- do not call this on this machine.** Concatenating all 17 years'
    full-resolution frames (~5.9M rows) OOM'd on 2026-08-03 at a 179MiB allocation: the box's
    pagefile commit was at 63.4/64.7GB system-wide (other processes, not this job) so even a
    routine-sized concat had nowhere to go. Kept only for reference; `compute_daily_stats()`
    below gets the same information (prior-close/gap/OR) via a streamed, one-year-at-a-time pass
    that never holds more than ~350k rows (one year) in memory."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"]) for f in files]
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    loc = df["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    df["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
    return df[["open", "high", "low", "close"]]


def build_bars15_streaming() -> pd.DataFrame:
    """The SAME 15-min-bar series `gl.resample_bars(gl.load_gold_ist(), '15min')` would produce,
    built WITHOUT ever materialising the full multi-year 1-min frame that OOM'd both
    `load_gold_full_ist()` and even `gl.load_gold_ist()` itself on this machine on 2026-08-03 (the
    box's system-wide virtual-memory commit was at 62-63/64.7GB -- other processes, not this job --
    so even `gl.load_gold_ist()`'s own all-years concat failed at a 5.6MiB allocation). Processes
    one year file at a time: load -> tz-fix -> session-filter -> resample THAT YEAR's ~250 days to
    15-min bars -> discard the year's raw 1-min data. Final concat is of 17 small 15-min-bar
    frames (~250k rows total), not 17 large 1-min frames (~5.9M rows total)."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    parts = []
    for f in files:
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        d = d.drop_duplicates("ts").sort_values("ts")
        loc = d["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        d["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        d = d.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
        tod = d.index.time
        sess = d[(tod >= MCX_START) & (tod <= MCX_END)][["open", "high", "low", "close"]]
        if sess.empty:
            del d
            continue
        r15 = gl.resample_bars(sess, "15min")
        parts.append(r15)
        del d, sess
    bars15 = pd.concat(parts).sort_index()
    return bars15


def compute_daily_stats() -> pd.DataFrame:
    """Per MCX calendar day: prior_close (last print strictly before that day's 09:00, from
    WHEREVER XAUUSD was trading -- gold never stops), session_open/high/low/close, and the
    09:00-09:30 / 09:00-10:00 opening-range high/low. All causal.

    MEMORY-LIGHT BY CONSTRUCTION (2026-08-03 fix): processes ONE YEAR FILE AT A TIME (~350k rows,
    ~11MB for 4 float64 cols) and immediately reduces it to the ~250-row daily summary before
    moving to the next year -- never materialises the 5.9M-row full-resolution frame that OOM'd
    `load_gold_full_ist()` above. Carries only a single scalar (previous year's last close) across
    the year boundary for the first day of each year's prior-close lookup. Within a year,
    prior-close uses np.searchsorted on that year's sorted index (O(log n), vectorised over all of
    that year's days at once) -- not the O(n_bars x n_days) per-day scan the first draft of this
    function used, which silently would have taken hours."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    daily_parts = []
    carry_close = None
    for f in files:
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        d = d.drop_duplicates("ts").sort_values("ts")
        loc = d["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        d["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        d = d.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()[["open", "high", "low", "close"]]
        if d.empty:
            continue

        tod = d.index.time
        sess_mask = (tod >= MCX_START) & (tod <= MCX_END)
        sess = d[sess_mask]
        if sess.empty:
            carry_close = float(d["close"].iloc[-1])
            continue
        dates = sess.index.date
        g = sess.groupby(dates)
        yr = pd.DataFrame({
            "session_open": g["open"].first(), "session_high": g["high"].max(),
            "session_low": g["low"].min(), "session_close": g["close"].last(),
        })
        or30_mask = sess.index.time <= dt.time(9, 30)
        or60_mask = sess.index.time <= dt.time(10, 0)
        g30 = sess[or30_mask].groupby(dates[or30_mask])
        g60 = sess[or60_mask].groupby(dates[or60_mask])
        yr = (yr.join(g30["high"].max().rename("or30_high"))
                 .join(g30["low"].min().rename("or30_low"))
                 .join(g60["high"].max().rename("or60_high"))
                 .join(g60["low"].min().rename("or60_low")))
        yr.index.name = "date"
        yr = yr.sort_index()

        day_starts = (pd.to_datetime(pd.Series(yr.index)) + pd.Timedelta(hours=9)).values
        idx_vals = d.index.values
        close_vals = d["close"].to_numpy()
        pos = np.searchsorted(idx_vals, day_starts, side="left")
        first_day_prior = carry_close if carry_close is not None else np.nan
        prior_close = np.where(pos > 0, close_vals[np.clip(pos - 1, 0, None)], first_day_prior)
        yr["prior_close"] = prior_close
        daily_parts.append(yr)
        carry_close = float(d["close"].iloc[-1])
        del d, sess, g, g30, g60

    daily = pd.concat(daily_parts).sort_index()
    daily.index.name = "date"
    daily["gap_pct"] = (daily["session_open"] / daily["prior_close"] - 1) * 100
    daily["day_range_pct"] = (daily["session_high"] - daily["session_low"]) / daily["session_open"] * 100
    daily["typical_range_pct"] = daily["day_range_pct"].shift(1).rolling(20, min_periods=10).mean()
    return daily


def compute_volstate_features_streaming() -> pd.DataFrame:
    """Per-MCX-day trailing/afternoon window features for gold_volstate.py: trailing_rv_2h
    (11:00-13:00), trailing_rv_4h (09:00-13:00), morning/OR60/afternoon hi-lo. Exact same
    construction gold_volstate.py's original draft computed off the full 1-min `spot` frame from
    `gl.load_gold_ist()` -- rebuilt streaming ONE YEAR FILE AT A TIME (same discipline as
    compute_daily_stats()/build_bars15_streaming() above) so it never needs the full-frame concat
    that OOM'd on 2026-08-03. Returns a DataFrame indexed by date with columns trailing_rv_2h,
    trailing_rv_4h, m_hi, m_lo, o60_hi, o60_lo, a_hi, a_lo."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    parts = []
    for f in files:
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        d = d.drop_duplicates("ts").sort_values("ts")
        loc = d["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        d["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        d = d.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
        tod_full = d.index.time
        sess = d[(tod_full >= MCX_START) & (tod_full <= MCX_END)][["open", "high", "low", "close"]]
        if sess.empty:
            del d
            continue
        sess = sess.copy()
        sess["logret"] = np.log(sess["close"]).diff()
        sess["date"] = sess.index.date
        t_tod = sess.index.time
        m2h = (t_tod > dt.time(11, 0)) & (t_tod <= dt.time(13, 0))
        m4h = (t_tod > dt.time(9, 0)) & (t_tod <= dt.time(13, 0))
        maft = t_tod > dt.time(13, 0)
        o60m = (t_tod > dt.time(9, 0)) & (t_tod <= dt.time(10, 0))
        rv2h = sess[m2h].groupby("date")["logret"].std().rename("trailing_rv_2h")
        rv4h = sess[m4h].groupby("date")["logret"].std().rename("trailing_rv_4h")
        morn = sess[m4h].groupby("date").agg(m_hi=("high", "max"), m_lo=("low", "min"))
        or60 = sess[o60m].groupby("date").agg(o60_hi=("high", "max"), o60_lo=("low", "min"))
        aft = sess[maft].groupby("date").agg(a_hi=("high", "max"), a_lo=("low", "min"))
        yr = rv2h.to_frame().join(rv4h).join(morn).join(or60).join(aft)
        parts.append(yr)
        del d, sess
    out = pd.concat(parts).sort_index()
    out.index.name = "date"
    return out


def compute_session_profile_streaming() -> pd.DataFrame:
    """SESSION PROFILE (descriptive, unconditional): per MCX bucket, n unique days, n 1-min bars,
    mean/std of 1-min log returns (bps), and mean bucket-range as % of that bucket's own opening
    price on the day (same normalisation gold_venue_scan.py's original draft used). Computed
    streaming ONE YEAR FILE AT A TIME so it never needs the full 17-year 1-min frame that OOM'd on
    2026-08-03 -- replaces that draft's dependence on the bare `spot` global (which was also only
    conditionally defined, a second latent bug: if no family cleared the cheap gate, `spot` was
    never assigned and the SESSION PROFILE section would NameError)."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    sums = {b: {"days": set(), "n_bars": 0, "sum_lr": 0.0, "sumsq_lr": 0.0, "n_lr": 0,
                "rng_pct_sum": 0.0, "rng_pct_n": 0} for b, _, _ in BUCKET_EDGES}
    for f in files:
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        d = d.drop_duplicates("ts").sort_values("ts")
        loc = d["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        d["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        d = d.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
        tod_full = d.index.time
        sess = d[(tod_full >= MCX_START) & (tod_full <= MCX_END)][["open", "high", "low", "close"]]
        if sess.empty:
            del d
            continue
        sess = sess.copy()
        sess["logret"] = np.log(sess["close"]).diff()
        sess["bucket"] = time_bucket(pd.Series(sess.index, index=sess.index))
        for bname, _, _ in BUCKET_EDGES:
            bm = sess[sess["bucket"] == bname]
            if bm.empty:
                continue
            dates_b = bm.index.date
            s = sums[bname]
            s["days"] |= set(dates_b)
            s["n_bars"] += len(bm)
            lr = bm["logret"].dropna()
            s["sum_lr"] += float(lr.sum())
            s["sumsq_lr"] += float((lr ** 2).sum())
            s["n_lr"] += len(lr)
            hi = bm.groupby(dates_b)["high"].max()
            lo = bm.groupby(dates_b)["low"].min()
            ob = bm.groupby(dates_b)["open"].first().replace(0, np.nan)
            rng_pct = (hi - lo) / ob * 100
            s["rng_pct_sum"] += float(rng_pct.sum(skipna=True))
            s["rng_pct_n"] += int(rng_pct.notna().sum())
        del d, sess
    rows = []
    for bname, _, _ in BUCKET_EDGES:
        s = sums[bname]
        mean_lr = s["sum_lr"] / s["n_lr"] if s["n_lr"] else np.nan
        if s["n_lr"] > 1:
            var_pop = s["sumsq_lr"] / s["n_lr"] - mean_lr ** 2
            var_lr = max(var_pop, 0.0) * s["n_lr"] / (s["n_lr"] - 1)   # ddof=1, matches pandas .std()
        else:
            var_lr = np.nan
        std_lr = float(np.sqrt(var_lr)) if np.isfinite(var_lr) else np.nan
        mean_rng = s["rng_pct_sum"] / s["rng_pct_n"] if s["rng_pct_n"] else np.nan
        rows.append(dict(
            bucket=bname, n_days=len(s["days"]), n_1min_bars=s["n_bars"],
            mean_1min_logret_bps=round(mean_lr * 1e4, 4) if np.isfinite(mean_lr) else None,
            std_1min_logret_bps=round(std_lr * 1e4, 4) if np.isfinite(std_lr) else None,
            mean_bucket_range_pct=round(mean_rng, 4) if np.isfinite(mean_rng) else None))
    return pd.DataFrame(rows)


def sig_inside_bar_cluster(bars, k=3):
    """k consecutive inside bars (each h<=prior h, l>=prior l) = a contraction; the mother bar
    (k+1 bars back from the confirming bar) bounds the whole cluster's high/low, since each
    subsequent inside bar's range nests inside the one before it. Breakout = the IMMEDIATE next
    bar's close crossing the cluster high/low (same 'immediate next bar only' convention as
    NR7_BREAKOUT in gold_compression.py -- stale clusters do not keep re-signalling)."""
    h, l = bars.h, bars.l
    is_inside = (h <= h.shift(1)) & (l >= l.shift(1))
    confirmed = is_inside.copy()
    for i in range(1, k):
        confirmed &= is_inside.shift(i)
    mother_h = h.shift(k)
    mother_l = l.shift(k)
    fresh = confirmed.shift(1).fillna(False)
    bull = fresh & (bars.c > mother_h.shift(1))
    bear = fresh & (bars.c < mother_l.shift(1))
    return make_entries_mcx(bull, bear, bars.index)


def sig_width_pctl_release(bars, width: pd.Series, pctl_lookback=1160, thresh=0.10, mom_lb=20):
    """Generic percentile-rank compression->release signal: `width` is any width-of-band series
    aligned to `bars.index` (BB width or Keltner width, both in % of basis so comparable). A
    squeeze is 'on' when width's OWN trailing rolling rank falls below `thresh` (bottom decile,
    ~20 sessions of 15-min bars at the default lookback); release = the first bar the rank climbs
    back above `thresh`. Direction = sign(close - close[mom_lb bars ago]), same momentum proxy as
    indicators.sig_squeeze_release so the two constructions are comparable apples-to-apples."""
    pctl = width.rolling(pctl_lookback, min_periods=pctl_lookback // 4).rank(pct=True)
    squeeze_on = pctl < thresh
    release = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    mom = bars.c - bars.c.shift(mom_lb)
    return make_entries_mcx(release & (mom > 0), release & (mom < 0), bars.index)


def bb_width_pct(bars, n=20, k=2.0):
    basis = bars.c.rolling(n).mean()
    dev = bars.c.rolling(n).std()
    return (2 * k * dev) / basis.replace(0, np.nan) * 100


def kc_width_pct(bars, n=20, atr_n=20, mult=1.5):
    basis = bars.c.rolling(n).mean()
    a = _atr(bars.h, bars.l, bars.c, atr_n)
    return (2 * mult * a) / basis.replace(0, np.nan) * 100
