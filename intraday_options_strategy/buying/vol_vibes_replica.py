"""Faithful 'Volatility Vibes' replica on Indian STOCK options.

Real strategy (per research): SELL earnings vol when it's overpriced. Pre-earnings filter:
  liquidity + IV/RV >= 1.25 + INVERTED term structure (near-month IV > far-month IV).
Express as short front-month straddle OR calendar (short near straddle + long far straddle,
safer). Enter ~2 sessions before earnings, exit ~1 session after -> capture near-month IV crush.
Tests: filtered vs unfiltered, short straddle vs calendar, build/forward.
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
EARN = ROOT / "datasets/nse_earnings_dates/earnings_dates.csv"
R_, Q_ = 0.065, 0.0
SLIP = 0.02
IV_RV_MIN = 1.25
SPLIT = dt.date(2024, 12, 31)


def stock_close():
    df = pq.read_table(DAY, columns=["symbol", "timestamp", "close"]).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    return df.pivot_table("close", "date", "symbol").sort_index()


def load_earn(stocks):
    e = pd.read_csv(EARN)
    e["date"] = pd.to_datetime(e["date"], format="%d-%b-%Y", errors="coerce").dropna()
    e = e[e["purpose"].str.contains("Financial Results", case=False, na=False)]
    e = e[e["symbol"].isin(stocks)]
    return e.groupby("symbol")["date"].apply(lambda s: sorted(set(s.dropna())))


def atm_straddle_iv(df, spot, day, exp):
    """Return (straddle_price, iv) at `day` for ATM strike in expiry df."""
    sub = df[df["trading_day"] == day.isoformat()] if False else df
    strikes = sorted(df["strike"].unique())
    if not strikes:
        return None, None
    k = min(strikes, key=lambda x: abs(x - spot))
    ce = df[(df["strike"] == k) & (df["option_type"] == "CE")].groupby("trading_day")["close"].last()
    pe = df[(df["strike"] == k) & (df["option_type"] == "PE")].groupby("trading_day")["close"].last()
    key = day.isoformat()
    if key not in ce.index or key not in pe.index:
        return None, None
    strad = ce[key] + pe[key]
    T = max((exp - day).days / 365.0, 1e-4)
    ivc = implied_vol(ce[key], spot, k, T, R_, Q_, True)
    ivp = implied_vol(pe[key], spot, k, T, R_, Q_, False)
    ivs = [v for v in (ivc, ivp) if np.isfinite(v)]
    return (strad if strad > 0 else None), (np.mean(ivs) if ivs else None)


def run():
    C = stock_close()
    logret = np.log(C / C.shift(1))
    rv = logret.rolling(42, min_periods=25).std() * np.sqrt(252)
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    earn = load_earn(set(stocks))
    recs = []
    for sym in stocks:
        if sym not in C.columns or sym not in earn.index:
            continue
        cser = C[sym].dropna(); rvser = rv[sym]
        exp_files = {dt.date.fromisoformat(p.stem): p for p in (SOPT / sym).glob("*.parquet")}
        exps = sorted(exp_files)
        for E in earn.loc[sym]:
            Ed = E.date()
            near_cand = [e for e in exps if e >= Ed]
            if len(near_cand) < 2:
                continue
            near_exp, far_exp = near_cand[0], near_cand[1]
            if (near_exp - Ed).days > 45:
                continue
            try:
                ndf = pq.read_table(exp_files[near_exp]).to_pandas(); ndf["trading_day"] = ndf["trading_day"].astype(str)
                fdf = pq.read_table(exp_files[far_exp]).to_pandas(); fdf["trading_day"] = fdf["trading_day"].astype(str)
            except Exception:
                continue
            ntd = sorted(pd.to_datetime(ndf["trading_day"].unique()))
            before = [d for d in ntd if d.date() < Ed]; after = [d for d in ntd if d.date() > Ed]
            if len(before) < 3 or not after:
                continue
            entry = before[-2].date(); ex = after[0].date()          # 2 sessions before -> 1 after
            spot = cser.asof(pd.Timestamp(entry)); rv_e = rvser.asof(pd.Timestamp(entry))
            if not (np.isfinite(spot) and np.isfinite(rv_e) and rv_e > 0):
                continue
            n_strad_e, n_iv = atm_straddle_iv(ndf, spot, entry, near_exp)
            n_strad_x, _ = atm_straddle_iv(ndf, spot, ex, near_exp)
            f_strad_e, f_iv = atm_straddle_iv(fdf, spot, entry, far_exp)
            f_strad_x, _ = atm_straddle_iv(fdf, spot, ex, far_exp)
            if None in (n_strad_e, n_iv, n_strad_x, f_strad_e, f_iv, f_strad_x):
                continue
            iv_rv = n_iv / rv_e
            inverted = n_iv > f_iv               # front-month richer = inverted term structure
            # short front straddle P&L (short: profit if it falls)
            short_strad = (n_strad_e * (1 - SLIP) - n_strad_x * (1 + SLIP)) / n_strad_e
            # calendar: short near + long far; net = near crush gained - far change paid
            cal = ((n_strad_e - n_strad_x) - (f_strad_e - f_strad_x)) / n_strad_e
            recs.append({"sym": sym, "earn": Ed, "iv_rv": iv_rv, "inverted": inverted,
                         "short_strad": np.clip(short_strad, -3, 1),
                         "calendar": np.clip(cal, -3, 1)})
    R = pd.DataFrame(recs)
    print(f"[events] {len(R)} earnings events with near+far expiries")

    def rep(sub, name):
        if len(sub) < 10:
            print(f"  {name:40s}: n={len(sub)} (too few)"); return
        b = sub[sub['earn'] <= SPLIT]; f = sub[sub['earn'] > SPLIT]
        for col in ["short_strad", "calendar"]:
            print(f"  {name:26s} [{col:11s}]: ALL {sub[col].mean():+6.1%} hit {(sub[col]>0).mean():.0%} "
                  f"n={len(sub):3d} p5 {sub[col].quantile(0.05):+.0%} | BUILD {b[col].mean():+6.1%} | FWD {f[col].mean():+6.1%}")

    print("\n=== SHORT earnings vol — filter progression ===")
    rep(R, "ALL events (no filter)")
    rep(R[R["iv_rv"] >= IV_RV_MIN], "IV/RV>=1.25")
    rep(R[R["inverted"]], "inverted term structure")
    rep(R[(R["iv_rv"] >= IV_RV_MIN) & (R["inverted"])], "IV/RV>=1.25 + inverted (FULL)")
    rep(R[(R["iv_rv"] >= 1.4) & (R["inverted"])], "IV/RV>=1.4 + inverted")
    R.to_parquet(ROOT / "intraday_options_strategy/buying/vol_vibes_replica.parquet")
    print("\nsaved -> vol_vibes_replica.parquet")


if __name__ == "__main__":
    run()
