"""Data-access layer for the FnO Replay Game.

EVERY market-data read goes through this module. It is the single choke point
that enforces the two dataset landmines (ROADMAP section 3):
  #1 timezone: dates taken only AFTER tz-convert to Asia/Kolkata
  #2 pre-open auction: bars before 09:15 IST are dropped at the boundary

No other module may open the parquet files directly.
"""
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SPOT_PQ = ROOT / r"intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet"
OPT_DIR = ROOT / r"intraday_options_strategy\datasets\raw\hf_index_options_1m\options\NIFTY"
VIX_1M = ROOT / r"intraday_options_strategy\datasets\processed\vix_1min.parquet"

OPEN_HM = 9 * 60 + 15     # 09:15
CLOSE_HM = 15 * 60 + 30   # 15:30 (settlement basis window ends 15:29)


def _ist(ts: pd.Series) -> pd.Series:
    ts = pd.to_datetime(ts)
    return ts.dt.tz_convert("Asia/Kolkata") if ts.dt.tz is not None else ts.dt.tz_localize("Asia/Kolkata")


def _session_filter(df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
    """Landmine enforcement: IST tz + regular session bars only."""
    ts = _ist(df[ts_col])
    hm = ts.dt.hour * 60 + ts.dt.minute
    out = df.loc[(hm >= OPEN_HM) & (hm <= CLOSE_HM)].copy()
    out["ts"] = ts[out.index]
    out["d"] = out["ts"].dt.date
    out["hm"] = hm[out.index]
    return out


@lru_cache(maxsize=1)
def _spot() -> pd.DataFrame:
    df = pq.read_table(SPOT_PQ, columns=["timestamp", "open", "high", "low", "close", "volume"]).to_pandas()
    return _session_filter(df, "timestamp").sort_values("ts").reset_index(drop=True)


@lru_cache(maxsize=1)
def trading_days() -> tuple:
    return tuple(sorted(_spot()["d"].unique()))


def load_spot_day(d: date) -> pd.DataFrame:
    """1-min spot bars for day d, 09:15..15:30 IST, sorted."""
    s = _spot()
    return s[s["d"] == d].reset_index(drop=True)


def prev_trading_day(d: date) -> date | None:
    days = trading_days()
    prior = [x for x in days if x < d]
    return prior[-1] if prior else None


def day_levels(d: date) -> dict:
    """PDH/PDL/PWH/PWL for day d plus the D-1 bar frame (for the prev-day chart)."""
    days = trading_days()
    prior = [x for x in days if x < d]
    if len(prior) < 5:
        raise ValueError(f"{d}: fewer than 5 prior sessions on file")
    d1 = prior[-1]
    week = prior[-5:]
    s = _spot()
    d1_bars = s[s["d"] == d1].reset_index(drop=True)
    wk = s[s["d"].isin(week)]
    return {
        "prev_day": d1,
        "prev_day_bars": d1_bars,
        "pdh": float(d1_bars["high"].max()),
        "pdl": float(d1_bars["low"].min()),
        "pwh": float(wk["high"].max()),
        "pwl": float(wk["low"].min()),
    }


@lru_cache(maxsize=1)
def expiries() -> tuple:
    out = []
    for p in sorted(OPT_DIR.glob("*.parquet")):
        try:
            out.append(date.fromisoformat(p.stem[:10]))
        except ValueError:
            continue
    return tuple(sorted(out))


def expiry_path(e: date) -> Path:
    return OPT_DIR / f"{e.isoformat()}.parquet"


def front_expiries(d: date, n: int = 2) -> list:
    """The n nearest expiries >= d. Calendar = the file list, never weekday rules."""
    return [e for e in expiries() if e >= d][:n]


def load_option_day(expiry: date, d: date) -> dict:
    """One expiry's option bars for trading day d, pivoted for O(1) minute access.

    Returns {
      'minute_index': {hm: {(strike, 'CE'|'PE'): {o,h,l,c,v,oi}}},
      'strikes': sorted list of strikes present,
      'expiry': date, 'day': date,
    }
    """
    cols = ["timestamp", "open", "high", "low", "close", "volume",
            "open_interest", "strike", "option_type", "expiry", "trading_day"]
    df = pq.read_table(expiry_path(expiry), columns=cols).to_pandas()
    # calendar truth check: expiry column inside the file must match the filename
    file_exp = pd.to_datetime(df["expiry"].iloc[0]).date()
    if file_exp != expiry:
        raise ValueError(f"expiry file {expiry} contains expiry column {file_exp}")
    td = pd.to_datetime(df["trading_day"]).dt.date
    df = df[td == d]
    if df.empty:
        raise ValueError(f"no option rows for trading_day {d} in expiry {expiry}")
    df = _session_filter(df, "timestamp")
    minute_index: dict = {}
    for row in df.itertuples(index=False):
        key = (int(row.strike), str(row.option_type))
        minute_index.setdefault(int(row.hm), {})[key] = {
            "o": float(row.open), "h": float(row.high), "l": float(row.low),
            "c": float(row.close), "v": int(row.volume), "oi": int(row.open_interest),
        }
    return {
        "minute_index": minute_index,
        "strikes": sorted({int(s) for s in df["strike"].unique()}),
        "expiry": expiry,
        "day": d,
    }


def load_vix_day(d: date) -> pd.DataFrame:
    """1-min VIX for day d (may be empty -> caller falls back to daily value)."""
    df = pq.read_table(VIX_1M).to_pandas().reset_index()  # 'dt' is the pandas index, tz-naive IST
    df = _session_filter(df.rename(columns={"dt": "timestamp"}), "timestamp")
    return df[df["d"] == d].reset_index(drop=True)


if __name__ == "__main__":
    # P0 smoke test on a mid-sample day
    days = trading_days()
    d = days[len(days) // 2]
    spot = load_spot_day(d)
    lv = day_levels(d)
    fx = front_expiries(d)
    od = load_option_day(fx[0], d)
    hms = sorted(od["minute_index"])
    n_at_open = len(od["minute_index"].get(OPEN_HM, {}))
    print(f"sample day {d}: {len(spot)} spot bars {spot['hm'].min()}..{spot['hm'].max()}")
    print(f"levels: PDH {lv['pdh']:.1f} PDL {lv['pdl']:.1f} PWH {lv['pwh']:.1f} PWL {lv['pwl']:.1f} (D-1 {lv['prev_day']})")
    print(f"front expiries {fx}, dte {(fx[0] - d).days}")
    print(f"chain: {len(od['strikes'])} strikes, minutes {hms[0]}..{hms[-1]}, contracts@0915 {n_at_open}")
    vix = load_vix_day(d)
    print(f"vix bars: {len(vix)}")
    assert spot["hm"].min() >= OPEN_HM, "auction bar leaked through filter"
    assert hms[0] >= OPEN_HM, "auction bar leaked into options"
    print("SMOKE TEST PASS")
