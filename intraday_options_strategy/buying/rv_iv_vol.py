"""RV-vs-IV volatility strategy on Indian STOCK options ('Volatility Vibes' style).

Signal: compare trailing REALIZED vol (RV) vs the option's IMPLIED vol (IV) on the ~2-month
expiry. Trade the ATM straddle, HOLD ~1 month (exit with ~1 month left -> dodge terminal theta).
Test the 4 cases: {LONG vol, SHORT vol} x {IV cheap vs RV, IV rich vs RV}.
Hypothesis: LONG vol when IV is CHEAP (IV/RV low) is the 1-of-4 winner (long gamma when the
stock realizes more than implied).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from options.bs_pricing import implied_vol  # noqa: E402

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ROOT / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
DAY = ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet"
R, Q = 0.065, 0.0
ENTRY_DTE = 55          # ~2 months to expiry at entry (sessions ~ calendar days here)
HOLD_D = 30             # hold ~1 month (calendar), exit with ~1 month left
SLIP = 0.02
SPLIT = dt.date(2024, 12, 31)


def stock_close():
    df = pq.read_table(DAY, columns=["symbol", "timestamp", "close"]).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    return df.pivot_table("close", "date", "symbol").sort_index()


def eod_leg(df, k, otype):
    s = df[(df["strike"] == k) & (df["option_type"] == otype)].groupby("trading_day")["close"].last()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def run():
    C = stock_close()
    logret = np.log(C / C.shift(1))
    rv = logret.rolling(42, min_periods=25).std() * np.sqrt(252)   # trailing realized vol
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    recs = []
    for sym in stocks:
        if sym not in C.columns:
            continue
        cser = C[sym].dropna(); rvser = rv[sym]
        for p in sorted((SOPT / sym).glob("*.parquet")):
            exp = dt.date.fromisoformat(p.stem)
            try:
                df = pq.read_table(p).to_pandas()
            except Exception:
                continue
            df["trading_day"] = df["trading_day"].astype(str)
            tdays = sorted(pd.to_datetime(df["trading_day"].unique()))
            # entry: first day with ~ENTRY_DTE calendar days to expiry
            entry_day = None
            for d in tdays:
                if (exp - d.date()).days <= ENTRY_DTE:
                    entry_day = d; break
            if entry_day is None:
                continue
            # exit ~HOLD_D calendar days later (still within option life)
            later = [d for d in tdays if (d - entry_day).days >= HOLD_D]
            if not later:
                continue
            exit_day = later[0]
            spot = cser.asof(entry_day)
            rv_e = rvser.asof(entry_day)
            if not (np.isfinite(spot) and np.isfinite(rv_e) and rv_e > 0):
                continue
            strikes = sorted(df["strike"].unique())
            k = min(strikes, key=lambda x: abs(x - spot))
            ce = eod_leg(df, k, "CE"); pe = eod_leg(df, k, "PE")
            if entry_day not in ce.index or entry_day not in pe.index:
                continue
            if exit_day not in ce.index or exit_day not in pe.index:
                continue
            T = max((exp - entry_day.date()).days / 365.0, 1e-4)
            iv_c = implied_vol(ce[entry_day], spot, k, T, R, Q, True)
            iv_p = implied_vol(pe[entry_day], spot, k, T, R, Q, False)
            ivs = [v for v in (iv_c, iv_p) if np.isfinite(v)]
            if not ivs:
                continue
            iv = np.mean(ivs)
            if not (0.05 < iv < 1.0):        # IV sanity cap: drop solver blow-ups / bad prints (e.g. INFY 133%)
                continue
            strad_e = ce[entry_day] + pe[entry_day]
            strad_x = ce[exit_day] + pe[exit_day]
            if strad_e <= 0 or strad_x <= 0:
                continue
            long_ret = (strad_x * (1 - SLIP)) / (strad_e * (1 + SLIP)) - 1
            recs.append({"sym": sym, "exp": exp, "entry": entry_day.date(), "exit": exit_day.date(),
                         "iv": iv, "rv": rv_e, "iv_rv": iv / rv_e,
                         "long_ret": np.clip(long_ret, -1.0, 3.0),
                         "short_ret": np.clip(-long_ret, -3.0, 1.0)})
    R_ = pd.DataFrame(recs)
    print(f"[events] {len(R_)} vol trades, {R_['entry'].min()}..{R_['entry'].max()}")
    print(f"[iv/rv] median {R_['iv_rv'].median():.2f}  (IV vs realized; <1 = IV cheap)")

    med = R_["iv_rv"].median()
    R_["bucket"] = np.where(R_["iv_rv"] < med, "IV_cheap(<med)", "IV_rich(>med)")
    print("\n=== 4 CASES: {LONG, SHORT} vol x {IV cheap, IV rich} — mean 1-month straddle return ===")
    for bucket in ["IV_cheap(<med)", "IV_rich(>med)"]:
        g = R_[R_["bucket"] == bucket]
        gb = g[pd.to_datetime(g["entry"]).dt.date <= SPLIT]
        gf = g[pd.to_datetime(g["entry"]).dt.date > SPLIT]
        for side in ["long_ret", "short_ret"]:
            lbl = ("LONG vol " if side == "long_ret" else "SHORT vol") + " | " + bucket
            print(f"  {lbl:30s}: ALL {g[side].mean():+6.1%} hit {(g[side]>0).mean():.0%} n={len(g)} "
                  f"| BUILD {gb[side].mean():+6.1%} | FWD {gf[side].mean():+6.1%}")

    # finer: by IV/RV quartile, LONG vol
    print("\n=== LONG vol return by IV/RV quartile (is cheapest-IV the winner?) ===")
    R_["q"] = pd.qcut(R_["iv_rv"], 4, labels=["Q1 cheapest", "Q2", "Q3", "Q4 richest"])
    gg = R_.groupby("q", observed=True)["long_ret"].agg(["mean", "median", "count",
                                                         lambda x: (x > 0).mean()])
    gg.columns = ["mean", "median", "n", "hit"]
    print(gg.to_string(formatters={"mean": "{:+.1%}".format, "median": "{:+.1%}".format, "hit": "{:.0%}".format}))
    R_.to_parquet(ROOT / "intraday_options_strategy/buying/rv_iv_vol.parquet")
    print(f"\nsaved -> rv_iv_vol.parquet")


if __name__ == "__main__":
    run()
