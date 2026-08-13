"""Shared screening library for TV_INDICATORS_20260730 (TradingView-style indicator mining).

Forward-return measurement is in INDEX POINTS (not %), matching the point-based futures cost
model this mandate uses (4.47 pts round trip pre-2024-10-01, 5.97 after, +0.5 slippage --
Shreyas_Ionic_AMC/04_RND_LAB/results/SHARED_CONTEXT_20260729.md).

Entry convention (no lookahead): a signal fires on a COMPLETED bar (bar label = that bar's own
CLOSE time, via resample(..., label="right", closed="right")). Entry fill = the NEXT 1-min
bar's OPEN strictly after that close. Horizons are measured in 1-min-precise minutes from the
entry fill; a horizon is NaN (not fabricated as a truncated partial) if the trading session ends
before that horizon is reached.

Reuses the exact NW t-stat formula and day-reassignment placebo pattern already reviewed in
EMA_INTRADAY_BUYING_20260729/stage1_signal_test.py (consolidate reused code, don't re-derive).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

NIFTY_1MIN = Path(
    r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
    r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
)

HORIZONS = [15, 30, 60, 120]          # minutes
FLAT_TIME = dt.time(15, 25)
BREAK = pd.Timestamp("2024-10-01")    # SEBI F&O tightening + STT rise
HELDOUT = pd.Timestamp("2026-01-01")  # never select on this
FUT_COST_PRE, FUT_COST_POST, SLIP = 4.47, 5.97, 0.5

TOD_START, TOD_END = dt.time(9, 20), dt.time(14, 45)


def fut_cost(day) -> float:
    return (FUT_COST_PRE if pd.Timestamp(day) < BREAK else FUT_COST_POST) + SLIP


def load_spot() -> pd.DataFrame:
    """NIFTY 1-min spot, 2015-01-09..2026-05-14, naive IST, verified clean: no pre-open
    (09:00-09:14) rows, no dup index, no NaN, always 09:15-15:29 (375 bars/day)."""
    df = pd.read_parquet(NIFTY_1MIN)
    df.index.name = "t"
    return df[["open", "high", "low", "close"]].sort_index()


def resample_bars(spot: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Per-day resample so no bar spans a session boundary. Bar label = bar's own CLOSE time
    (label='right', closed='right') -> the label IS the timestamp at which the bar (and any
    indicator computed on it) becomes knowable, which is what entry-lag logic keys off of."""
    parts = []
    for _, day in spot.groupby(spot.index.date):
        r = day.resample(rule, origin=day.index[0], label="right", closed="right").agg(
            o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")
        ).dropna()
        r["d"] = pd.Timestamp(day.index[0].date())
        parts.append(r)
    return pd.concat(parts).sort_index()


def nw_tstat(x, lags: int = 5) -> float:
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


def build_by_day(spot: pd.DataFrame) -> dict:
    """Pre-split the 1-min spot frame by calendar day ONCE, reused across every family/
    timeframe's forward_points() call -- rebuilding this 1M-row groupby 36+ times was the
    dominant cost in an early timing check."""
    return {d: g for d, g in spot.groupby(spot.index.date)}


def forward_points(spot: pd.DataFrame, entries: pd.DataFrame, by_day: dict | None = None
                   ) -> pd.DataFrame:
    """For each entry (t=signal bar close, dir=+-1): entry fill = next 1-min bar's OPEN
    strictly after t, same day. Signed point move at each horizon + to 15:25 (r_eod).
    A horizon not reached before the session ends is NaN, never truncated/fabricated."""
    if entries is None or entries.empty:
        return pd.DataFrame()
    if by_day is None:
        by_day = build_by_day(spot)
    out = []
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
        day_end = day.index[-1]
        for h in HORIZONS:
            target = t0 + pd.Timedelta(minutes=h)
            if target > day_end:
                rec[f"r{h}"] = np.nan
                continue
            w = fwd[fwd.index <= target]
            rec[f"r{h}"] = sgn * (float(w["close"].iloc[-1]) - e) if len(w) else np.nan
        flat = fwd[fwd.index.time <= FLAT_TIME]
        rec["r_eod"] = sgn * (float(flat["close"].iloc[-1]) - e) if len(flat) else np.nan
        out.append(rec)
    f = pd.DataFrame(out)
    if not f.empty:
        f["day"] = pd.to_datetime(f["date"])
    return f


def placebo_pts(spot: pd.DataFrame, entries: pd.DataFrame, col: str, rng,
                 n_placebo: int = 200, by_day: dict | None = None) -> np.ndarray:
    """Random-day reassignment placebo, matched on count, time-of-day and direction mix
    (identical discipline to stage1_signal_test.placebo, extended to points/any horizon col)."""
    if by_day is None:
        by_day = build_by_day(spot)
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    dirs = entries["dir"].tolist()
    res = []
    for _ in range(n_placebo):
        rows = []
        for tod, sgn in zip(tods, dirs):
            d = days[rng.integers(len(days))]
            rows.append({"t": pd.Timestamp(d).replace(hour=tod.hour, minute=tod.minute),
                         "dir": sgn})
        f = forward_points(spot, pd.DataFrame(rows), by_day=by_day)
        res.append(f[col].mean() if len(f) and col in f else np.nan)
    return np.array(res, float)


def concentration(f: pd.DataFrame, col: str) -> float:
    """Largest single-day share of total signed edge (SHARED_CONTEXT hard-kill #3, >30%)."""
    per_day = f.groupby("date")[col].sum()
    tot = per_day.sum()
    return float(per_day.abs().max() / abs(tot)) if tot else np.inf


# --------------------------------------------------------------------------- overlap guard
# CANDLE_MTF_20260730 lesson (coordinator, 2026-07-30): a signal that fires often while each
# trade is "held" for a long window means many trades are OPEN AT THE SAME TIME and summing
# them as independent observations inflates the t-stat (measured there: ~10x). Fix: keep only
# the first signal of any overlapping cluster -- exactly what a real trader with ONE position
# could have taken.
def one_position_at_a_time(entries: pd.DataFrame, *, eod: bool, horizon_minutes: int = 0
                           ) -> pd.DataFrame:
    """Drop any entry whose signal time falls before the PRIOR kept entry's position would
    have closed. eod=True -> a position opened on day D is open until that day's 15:25 (so at
    most one entry per calendar day survives). eod=False -> a position is open for
    `horizon_minutes` after the signal."""
    if entries.empty:
        return entries
    e = entries.sort_values("t").reset_index(drop=True)
    keep_idx, open_until = [], None
    for i, t in enumerate(e["t"]):
        if open_until is not None and t < open_until:
            continue
        keep_idx.append(i)
        open_until = (pd.Timestamp(t.date()) + pd.Timedelta(hours=15, minutes=25) if eod
                      else t + pd.Timedelta(minutes=horizon_minutes))
    return e.loc[keep_idx].reset_index(drop=True)


def naive_tstat(x) -> tuple[float, float]:
    """Plain one-sample t-test (IID assumption, no autocorrelation correction) -- reported
    ALONGSIDE nw_tstat per the coordinator's instruction, never in place of it."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return np.nan, np.nan
    from scipy import stats as _st
    t, p = _st.ttest_1samp(x, 0.0)
    return float(t), float(p)


def unconditional_benchmark(spot: pd.DataFrame, entries: pd.DataFrame, col: str, rng,
                            by_day: dict, n_reps: int = 200) -> np.ndarray:
    """THE BETA TEST (coordinator, 2026-07-30): random entries, matched COUNT and TIME-OF-DAY
    distribution, but ALL forced to the cell's own DOMINANT side (not the per-trade dir mix --
    that is what placebo_pts already tests). If a cell cannot beat "just take this one side,
    same exit machinery, at random times" by more than noise, the cell is NIFTY's drift in
    costume, not a timing edge. Same random-day mechanism as placebo_pts for comparability."""
    dominant = 1 if entries["dir"].sum() >= 0 else -1
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    res = []
    for _ in range(n_reps):
        rows = [{"t": pd.Timestamp(days[rng.integers(len(days))]).replace(
            hour=tod.hour, minute=tod.minute), "dir": dominant} for tod in tods]
        f = forward_points(spot, pd.DataFrame(rows), by_day=by_day)
        res.append(f[col].mean() if len(f) and col in f else np.nan)
    return np.array(res, float)
