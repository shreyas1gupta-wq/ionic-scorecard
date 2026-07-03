"""Earnings-vol QUADRANT backtest on Indian STOCK options (tests 'long IV, 1 of 4').

For each earnings event on an F&O stock, take the ATM straddle in the expiry that spans
the event and test the 4 canonical cases:
  Case1 LONG_pre  : BUY straddle ~ENTRY_D sessions before earnings, SELL 1 session BEFORE
                    the announcement  -> harvests the pre-earnings IV RAMP, dodges IV crush ('long IV')
  Case2 LONG_thru : BUY ~ENTRY_D before, HOLD THROUGH, sell 1 session AFTER  -> ramp+move-crush
  Case3 SHORT_pre : SELL before, buy back 1 session before earnings -> shorts the ramp
  Case4 SHORT_thru: SELL 1 session before earnings, buy back 1 after -> classic IV-CRUSH harvest
Reports mean return / hit / build+forward per case. EOD straddle prices; slippage applied.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ROOT / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
DAY = ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet"
EARN = ROOT / "datasets/nse_earnings_dates/earnings_dates.csv"
ENTRY_D = 10          # sessions before earnings to buy (IV-ramp window)
SLIP = 0.02           # 2% per side (stock options spreads are wide)
SPLIT = dt.date(2024, 12, 31)


def stock_close():
    df = pq.read_table(DAY, columns=["symbol", "timestamp", "close"]).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    return df.pivot_table("close", "date", "symbol").sort_index()


def load_earnings(stocks):
    e = pd.read_csv(EARN)
    e["date"] = pd.to_datetime(e["date"], format="%d-%b-%Y", errors="coerce")
    e = e.dropna(subset=["date"])
    e = e[e["purpose"].str.contains("Financial Results", case=False, na=False)]
    e = e[e["symbol"].isin(stocks)]
    return e.groupby("symbol")["date"].apply(lambda s: sorted(set(s)))


def eod_straddle(df, k):
    """EOD (last bar/day) ATM straddle close series indexed by trading_day (date)."""
    sub = df[df["strike"] == k]
    ce = sub[sub["option_type"] == "CE"].groupby("trading_day")["close"].last()
    pe = sub[sub["option_type"] == "PE"].groupby("trading_day")["close"].last()
    s = (ce + pe).dropna()
    s.index = pd.to_datetime(s.index)
    return s


def run():
    C = stock_close()
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    earn = load_earnings(set(stocks))
    print(f"[data] {len(stocks)} option stocks, earnings for {len(earn)} of them")

    recs = []
    for sym in stocks:
        if sym not in earn.index or sym not in C.columns:
            continue
        exp_files = {dt.date.fromisoformat(p.stem): p for p in (SOPT / sym).glob("*.parquet")}
        exps = sorted(exp_files)
        if not exps:
            continue
        cser = C[sym].dropna()
        for E in earn.loc[sym]:
            Ed = E.date()
            # expiry that spans the event: nearest expiry >= earnings date
            cand = [e for e in exps if e >= Ed]
            if not cand:
                continue
            exp = cand[0]
            if (exp - Ed).days > 45:      # event must be reasonably close to that expiry
                continue
            try:
                df = pq.read_table(exp_files[exp]).to_pandas()
            except Exception:
                continue
            df["trading_day"] = df["trading_day"].astype(str)
            tdays = sorted(pd.to_datetime(df["trading_day"].unique()))
            # sessions relative to earnings
            before = [d for d in tdays if d.date() < Ed]
            after = [d for d in tdays if d.date() > Ed]
            if len(before) < ENTRY_D + 1 or len(after) < 1:
                continue
            entry_day = before[-(ENTRY_D)]            # ENTRY_D sessions before earnings
            pre_day = before[-1]                      # 1 session before earnings
            post_day = after[0]                       # 1 session after earnings
            # ATM strike from spot near entry
            spot = cser.asof(entry_day)
            if not np.isfinite(spot):
                continue
            strikes = sorted(df["strike"].unique())
            k = min(strikes, key=lambda x: abs(x - spot))
            strad = eod_straddle(df, k)
            if entry_day not in strad.index or pre_day not in strad.index or post_day not in strad.index:
                continue
            s_entry, s_pre, s_post = strad[entry_day], strad[pre_day], strad[post_day]
            if not (s_entry > 0 and s_pre > 0 and s_post > 0):
                continue
            # net returns with slippage (buy pay +slip, sell get -slip)
            def long_ret(buy, sell):
                return (sell * (1 - SLIP)) / (buy * (1 + SLIP)) - 1
            recs.append({
                "sym": sym, "earn": Ed, "exp": exp, "spot": spot, "k": k,
                "s_entry": s_entry, "s_pre": s_pre, "s_post": s_post,
                "c1_long_pre": long_ret(s_entry, s_pre),          # long IV, exit before
                "c2_long_thru": long_ret(s_entry, s_post),        # long, hold through
                "c3_short_pre": -long_ret(s_entry, s_pre),        # short the ramp
                "c4_short_thru": (s_pre * (1 - SLIP)) / (s_post * (1 + SLIP)) - 1,  # short thru = sell pre buy post
            })
    R = pd.DataFrame(recs)
    print(f"[events] {len(R)} earnings straddle events {R['earn'].min()}..{R['earn'].max()}\n")

    cases = {"c1_long_pre": "LONG IV, exit BEFORE (ramp)",
             "c2_long_thru": "LONG, hold THROUGH",
             "c3_short_pre": "SHORT the ramp (exit before)",
             "c4_short_thru": "SHORT hold THROUGH (IV crush)"}
    for c, name in cases.items():
        b = R[R["earn"] <= SPLIT]; f = R[R["earn"] > SPLIT]
        print(f"  {name:32s}: ALL mean {R[c].mean():+6.1%} hit {(R[c]>0).mean():.0%} n={len(R)} "
              f"| BUILD {b[c].mean():+6.1%} ({(b[c]>0).mean():.0%}) | FWD {f[c].mean():+6.1%} ({(f[c]>0).mean():.0%})")
    R.to_parquet(ROOT / "intraday_options_strategy/buying/stock_earnings_vol.parquet")
    print(f"\nsaved {len(R)} events -> stock_earnings_vol.parquet")
    # quick per-year for the winning case
    R["yr"] = pd.to_datetime(R["earn"]).dt.year
    print("\nc1_long_pre by year:")
    print(R.groupby("yr")["c1_long_pre"].agg(["mean", "count"]).to_string())


if __name__ == "__main__":
    run()
