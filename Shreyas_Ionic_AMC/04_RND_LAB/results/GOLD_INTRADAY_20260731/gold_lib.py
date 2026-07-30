"""Gold (XAUUSD spot, MCX-session view) data + cost library for GOLD_INTRADAY_20260731.

DATA: 05_DATA_OFFICE/data/commodities_1m/XAUUSD_1m_{2009..2025}.parquet. Columns ts/open/high/
low/close. ~5.9M 1-min rows.

LANDMINE 1 -- TIMEZONE. `ts` is HistData local time, verified NOT IST: hour-17 has only ~1,199
of a possible ~15,480 bars in 2025 (the daily FX/CFD maintenance break, ~17:00-18:00 local),
which is the signature of US EASTERN TIME stamping, not IST or UTC. Rather than hand-computing
the ET->IST offset (+10:30 in EST / +9:30 in EDT, and the US DST calendar does not line up with
India, which has no DST), this uses `tz_localize("America/New_York")` then
`tz_convert("Asia/Kolkata")` so the IANA tz database resolves every historical DST boundary
correctly. Verified on the 2025 file: 0 ambiguous/nonexistent timestamps, and 2025-01-01 18:00
ET -> 2025-01-02 04:30 IST (+10:30, correct for EST/January).

LANDMINE 2 -- THIS IS XAUUSD SPOT IN USD, NOT MCX GOLD FUTURES IN INR. Percentage/ATR-unit moves
carry over approximately; absolute price levels and rupee P&L do not. Every gold result in this
folder is reported in % or ATR units. [INFERENCE] tag applies to any rupee/point figure derived
from an assumed USDINR rate (see mcx_cost_estimate.py).

LANDMINE 3 -- data ends 2025-12-31. No 2026 file exists despite the dataset name. The held-out
slice for gold is therefore INSIDE 2025 (H2-2025), not 2026.

SESSION: MCX gold trades ~09:00-23:30 IST (coordinator, 2026-07-31). "Intraday only, no
overnight positions" (Principal's new mandate) -- every synthetic gold trade here must open and
close inside that same-day window; FLAT_TIME_GOLD (23:25) is the forced-flat analogue of
NIFTY's 15:25.
"""
from __future__ import annotations

import datetime as dt
import glob
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(
    r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
    r"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\commodities_1m"
)

MCX_START = dt.time(9, 0)
MCX_END = dt.time(23, 30)
FLAT_TIME_GOLD = dt.time(23, 25)
HORIZONS = [15, 30, 60, 120]
HELDOUT_GOLD = pd.Timestamp("2025-07-01")   # H2-2025 held out (data ends 2025-12-31)


def load_gold_ist() -> pd.DataFrame:
    """Concatenate all yearly files, convert ET->IST, filter to the MCX session window.
    Returns a DataFrame indexed by naive IST timestamp with open/high/low/close."""
    files = sorted(glob.glob(str(DATA_DIR / "XAUUSD_1m_*.parquet")))
    parts = []
    for f in files:
        d = pd.read_parquet(f, columns=["ts", "open", "high", "low", "close"])
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    loc = df["ts"].dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    df["t_ist"] = loc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.dropna(subset=["t_ist"])
    df = df.set_index("t_ist").sort_index()
    tod = df.index.time
    df = df[(tod >= MCX_START) & (tod <= MCX_END)]
    return df[["open", "high", "low", "close"]]


def resample_bars(spot: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Per-IST-day resample, bar label = bar's own CLOSE time (same convention as
    lib_signals.resample_bars for NIFTY)."""
    parts = []
    for _, day in spot.groupby(spot.index.date):
        r = day.resample(rule, origin=day.index[0], label="right", closed="right").agg(
            o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")
        ).dropna()
        r["d"] = pd.Timestamp(day.index[0].date())
        parts.append(r)
    return pd.concat(parts).sort_index()


def build_by_day(spot: pd.DataFrame) -> dict:
    return {d: g for d, g in spot.groupby(spot.index.date)}


def forward_pct(spot: pd.DataFrame, entries: pd.DataFrame, by_day: dict | None = None
               ) -> pd.DataFrame:
    """Same discipline as lib_signals.forward_points but in PERCENT (gold is USD spot, not a
    priced INR vehicle -- percent is the currency-invariant unit). Entry fill = next 1-min bar's
    OPEN strictly after the signal bar's close, same MCX session only (no overnight hold)."""
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
            rec[f"r{h}"] = sgn * (float(w["close"].iloc[-1]) / e - 1) * 100 if len(w) else np.nan
        flat = fwd[fwd.index.time <= FLAT_TIME_GOLD]
        rec["r_eod"] = sgn * (float(flat["close"].iloc[-1]) / e - 1) * 100 if len(flat) else np.nan
        out.append(rec)
    f = pd.DataFrame(out)
    if not f.empty:
        f["day"] = pd.to_datetime(f["date"])
    return f


def one_position_at_a_time(entries: pd.DataFrame, *, eod: bool, horizon_minutes: int = 0
                           ) -> pd.DataFrame:
    if entries.empty:
        return entries
    e = entries.sort_values("t").reset_index(drop=True)
    keep_idx, open_until = [], None
    for i, t in enumerate(e["t"]):
        if open_until is not None and t < open_until:
            continue
        keep_idx.append(i)
        open_until = (pd.Timestamp(t.date()) + pd.Timedelta(hours=23, minutes=25) if eod
                      else t + pd.Timedelta(minutes=horizon_minutes))
    return e.loc[keep_idx].reset_index(drop=True)


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


def naive_tstat(x) -> tuple[float, float]:
    from scipy import stats as _st
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return np.nan, np.nan
    t, p = _st.ttest_1samp(x, 0.0)
    return float(t), float(p)


def placebo_pct(spot: pd.DataFrame, entries: pd.DataFrame, col: str, rng, n_placebo: int = 200,
                by_day: dict | None = None) -> np.ndarray:
    if by_day is None:
        by_day = build_by_day(spot)
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    dirs = entries["dir"].tolist()
    res = []
    for _ in range(n_placebo):
        rows = [{"t": pd.Timestamp(days[rng.integers(len(days))]).replace(
            hour=tod.hour, minute=tod.minute), "dir": sgn} for tod, sgn in zip(tods, dirs)]
        f = forward_pct(spot, pd.DataFrame(rows), by_day=by_day)
        res.append(f[col].mean() if len(f) and col in f else np.nan)
    return np.array(res, float)


def unconditional_benchmark(spot: pd.DataFrame, entries: pd.DataFrame, col: str, rng,
                            by_day: dict, n_reps: int = 200) -> np.ndarray:
    dominant = 1 if entries["dir"].sum() >= 0 else -1
    days = sorted({d for d in spot.index.date})
    tods = pd.to_datetime(entries["t"]).dt.time.tolist()
    res = []
    for _ in range(n_reps):
        rows = [{"t": pd.Timestamp(days[rng.integers(len(days))]).replace(
            hour=tod.hour, minute=tod.minute), "dir": dominant} for tod in tods]
        f = forward_pct(spot, pd.DataFrame(rows), by_day=by_day)
        res.append(f[col].mean() if len(f) and col in f else np.nan)
    return np.array(res, float)


def concentration(f: pd.DataFrame, col: str) -> float:
    per_day = f.groupby("date")[col].sum()
    tot = per_day.sum()
    return float(per_day.abs().max() / abs(tot)) if tot else np.inf


# --------------------------------------------------------------------------- MCX cost model
# [INFERENCE -- not a firm standard; needs CEO+CIO approval under D-025 before any adoption].
# COST_STANDARDS.md (D-021, APPROVED) is NSE-only and has no MCX row. Rates below sourced from
# MCX/CTT public circulars checked 2026-07-31 (CTT 0.01% sell-side confirmed via mcxindia.com /
# mcxccl.com; exchange transaction charge ~Rs 2.1-2.6/lakh turnover per the Oct-2024 SEBI-driven
# fixed-fee revision; stamp duty 0.002% buy-side is the uniform post-2020 stamp-duty-reform rate
# for commodity futures). Brokerage assumed flat Rs 20/lot/side (discount-broker convention,
# matching this firm's own Rs25/lot/side NSE-options assumption in spirit, not identical).
def mcx_goldm_cost_breakdown(spot_usd: float, usdinr: float = 87.0) -> dict:
    """Round-trip cost for ONE GOLDM (100g) lot, itemised. Returns rupee figures AND the
    currency-invariant % of notional (= % price move needed to break even), which is what the
    gold backtest actually uses."""
    oz_to_g = 31.1035
    price_per_g_inr = spot_usd * usdinr / oz_to_g
    notional = price_per_g_inr * 100          # GOLDM = 100g
    brokerage_rt = 20.0 * 2                   # Rs20/lot/side, round trip
    exch_txn_rt = notional * 0.000021 * 2     # ~Rs2.1/lakh/side (0.0021%), both sides
    ctt = notional * 0.0001                   # 0.01% SELL side only, once per round trip
    stamp = notional * 0.00002                # 0.002% BUY side only, once per round trip
    sebi_fee_rt = notional / 1e7 * 20 * 2     # Rs20/crore/side, round trip (negligible)
    gst_base = brokerage_rt + exch_txn_rt + sebi_fee_rt
    gst = gst_base * 0.18
    slippage_rt = 20.0 * 2                    # ~2 ticks/side conservative, Rs10/tick/lot
    total_rt_inr = (brokerage_rt + exch_txn_rt + ctt + stamp + sebi_fee_rt + gst + slippage_rt)
    pct_of_notional = total_rt_inr / notional * 100
    return dict(spot_usd=spot_usd, usdinr=usdinr, price_per_g_inr=round(price_per_g_inr, 2),
                notional_inr=round(notional, 0), brokerage_rt=round(brokerage_rt, 2),
                exch_txn_rt=round(exch_txn_rt, 2), ctt=round(ctt, 2), stamp=round(stamp, 2),
                sebi_fee_rt=round(sebi_fee_rt, 2), gst=round(gst, 2),
                slippage_rt=round(slippage_rt, 2), total_rt_inr=round(total_rt_inr, 2),
                pct_of_notional=round(pct_of_notional, 4))
