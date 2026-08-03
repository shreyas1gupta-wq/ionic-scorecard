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


def load_gold_full_ist() -> pd.DataFrame:
    """Same ET->IST fix as gl.load_gold_ist() but WITHOUT the MCX-session filter -- needed to
    measure the true overnight drift across MCX's 23:30-09:00 closed window (gold itself never
    stops trading, so the gap is against wherever XAUUSD actually was)."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"]) for f in files]
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    loc = df["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    df["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.dropna(subset=["t_ist"]).set_index("t_ist").sort_index()
    return df[["open", "high", "low", "close"]]


def session_daily_stats(full: pd.DataFrame) -> pd.DataFrame:
    """Per MCX calendar day: prior_close (last full-frame print strictly before that day's 09:00),
    session_open (first print >= 09:00), session_high/low/close (within 09:00-23:30), and the
    09:00-09:30 / 09:00-10:00 opening-range high/low. All causal -- no same-day lookahead into
    the OR/gap fields (they use only bars up to their own defining window)."""
    tod = full.index.time
    sess_mask = (tod >= MCX_START) & (tod <= MCX_END)
    sess = full[sess_mask]
    rows = []
    days = sorted({d for d in sess.index.date})
    full_idx = full.index
    for d in days:
        day_start = pd.Timestamp(d) + pd.Timedelta(hours=9)
        prior = full.loc[full_idx < day_start]
        if prior.empty:
            continue
        prior_close = float(prior["close"].iloc[-1])
        day = sess[sess.index.date == d]
        if day.empty:
            continue
        session_open = float(day["open"].iloc[0])
        or30 = day[day.index.time <= dt.time(9, 30)]
        or60 = day[day.index.time <= dt.time(10, 0)]
        rows.append(dict(
            date=d, prior_close=prior_close, session_open=session_open,
            session_high=float(day["high"].max()), session_low=float(day["low"].min()),
            session_close=float(day["close"].iloc[-1]),
            or30_high=float(or30["high"].max()) if len(or30) else np.nan,
            or30_low=float(or30["low"].min()) if len(or30) else np.nan,
            or60_high=float(or60["high"].max()) if len(or60) else np.nan,
            or60_low=float(or60["low"].min()) if len(or60) else np.nan,
        ))
    d = pd.DataFrame(rows).set_index("date").sort_index()
    d["gap_pct"] = (d["session_open"] / d["prior_close"] - 1) * 100
    d["day_range_pct"] = (d["session_high"] - d["session_low"]) / d["session_open"] * 100
    # causal 20-session trailing average of the PRIOR days' ranges (today excluded)
    d["typical_range_pct"] = d["day_range_pct"].shift(1).rolling(20, min_periods=10).mean()
    return d


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
    return make_entries(bull, bear, bars.index)


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
    return make_entries(release & (mom > 0), release & (mom < 0), bars.index)


def bb_width_pct(bars, n=20, k=2.0):
    basis = bars.c.rolling(n).mean()
    dev = bars.c.rolling(n).std()
    return (2 * k * dev) / basis.replace(0, np.nan) * 100


def kc_width_pct(bars, n=20, atr_n=20, mult=1.5):
    basis = bars.c.rolling(n).mean()
    a = _atr(bars.h, bars.l, bars.c, atr_n)
    return (2 * mult * a) / basis.replace(0, np.nan) * 100
