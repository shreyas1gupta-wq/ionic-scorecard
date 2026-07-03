"""User-specified strategy: IV TERM-STRUCTURE DISPERSION (no earnings link).

Signal: compare ATM IV of the CURRENT/near-month expiry (M1) vs the NEXT-month expiry (M2)
for the same stock, at a fixed lead time before M1 expires. If the dispersion (IV_M1 - IV_M2)
crosses a threshold, go LONG BOTH legs:
  - LONG M1 at the deepest OTM strike that is ALSO listed in M2 ("for hedging" = ensures the
    back-month leg exists at the same strike)
  - LONG M2, SAME strike, SAME qty
Exit at M1's expiry (M2 still has ~1 month of life left at that point).
Tests: call-side vs put-side, positive vs negative dispersion, threshold sweep, build/forward.
Also computes what a fixed-fraction "brain-adjusted" Indian threshold should be.
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
R_, Q_ = 0.065, 0.0
SLIP = 0.03            # deep OTM stock options: wide spreads
LEAD_DAYS = 15         # sessions before M1 expiry at which we sample dispersion / enter
SPLIT = dt.date(2024, 12, 31)


def stock_close():
    df = pq.read_table(DAY, columns=["symbol", "timestamp", "close"]).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    return df.pivot_table("close", "date", "symbol").sort_index()


def _series(df, strike, otype):
    s = df[(df["strike"] == strike) & (df["option_type"] == otype)].copy()
    s["t"] = pd.to_datetime(s["timestamp"]).dt.tz_localize(None)
    return s.set_index("t")["close"].sort_index()


def _nearest(ser, day, window):
    """Nearest print to `day` (either direction) within `window` calendar days."""
    if ser.empty:
        return np.nan, None
    d = ser.index.normalize()
    delta = (d - pd.Timestamp(day)).days
    close = np.abs(delta) <= window
    if not close.any():
        return np.nan, None
    sub = ser[close]
    idx = np.argmin(np.abs((sub.index.normalize() - pd.Timestamp(day)).days))
    return sub.iloc[idx], sub.index[idx].date()


def atm_iv_asof(df, spot, day, exp, window=15):
    """ATM IV using the nearest traded print to `day` (handles illiquid/late-listed strikes)."""
    strikes = sorted(df["strike"].unique())
    if not strikes:
        return None
    k = min(strikes, key=lambda x: abs(x - spot))
    ser = _series(df, k, "CE")
    px, used_day = _nearest(ser, day, window)
    if not np.isfinite(px) or used_day is None or used_day >= exp:
        return None
    T = max((exp - used_day).days / 365.0, 1e-4)
    iv = implied_vol(px, spot, k, T, R_, Q_, True)
    return iv if np.isfinite(iv) and 0.03 < iv < 3.0 else None


def price_asof(df, strike, otype, day, max_stale=15):
    ser = _series(df, strike, otype)
    px, _ = _nearest(ser, day, max_stale)
    return px


def common_deep_otm(df1, df2, spot, side):
    """Deepest OTM strike (call: highest > spot; put: lowest < spot) present in BOTH chains."""
    s1 = set(df1["strike"].unique()); s2 = set(df2["strike"].unique())
    common = s1 & s2
    if side == "CE":
        cand = sorted([k for k in common if k > spot])
        return cand[-1] if cand else None      # deepest OTM call = highest common strike
    else:
        cand = sorted([k for k in common if k < spot])
        return cand[0] if cand else None       # deepest OTM put = lowest common strike


def run():
    C = stock_close()
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    recs = []
    for sym in stocks:
        if sym not in C.columns:
            continue
        cser = C[sym].dropna()
        exp_files = {dt.date.fromisoformat(p.stem): p for p in (SOPT / sym).glob("*.parquet")}
        exps = sorted(exp_files)
        for i in range(len(exps) - 1):
            m1_exp, m2_exp = exps[i], exps[i + 1]
            try:
                d1 = pq.read_table(exp_files[m1_exp]).to_pandas(); d1["trading_day"] = d1["trading_day"].astype(str)
                d2 = pq.read_table(exp_files[m2_exp]).to_pandas(); d2["trading_day"] = d2["trading_day"].astype(str)
            except Exception:
                continue
            tdays1 = sorted(pd.to_datetime(d1["trading_day"].unique()))
            tdays2 = sorted(pd.to_datetime(d2["trading_day"].unique()))
            if len(tdays1) <= LEAD_DAYS or not tdays2:
                continue
            target_entry = tdays1[-LEAD_DAYS - 1].date()
            m2_start = tdays2[0].date()
            entry_day = max(target_entry, m2_start)      # M2 must actually be listed
            if entry_day >= m1_exp:
                continue
            spot = cser.asof(pd.Timestamp(entry_day))
            if not np.isfinite(spot):
                continue
            iv_m1 = atm_iv_asof(d1, spot, entry_day, m1_exp)
            iv_m2 = atm_iv_asof(d2, spot, entry_day, m2_exp)
            if iv_m1 is None or iv_m2 is None:
                continue
            disp = iv_m1 - iv_m2
            exp_spot = cser.asof(pd.Timestamp(m1_exp))
            for side in ("CE", "PE"):
                k = common_deep_otm(d1, d2, spot, side)
                if k is None:
                    continue
                p1_e = price_asof(d1, k, side, entry_day)
                p2_e = price_asof(d2, k, side, entry_day)
                if not (np.isfinite(p1_e) and np.isfinite(p2_e) and p1_e > 0 and p2_e > 0):
                    continue
                m1_exit = max(0.0, (exp_spot - k) if side == "CE" else (k - exp_spot))
                m2_x = price_asof(d2, k, side, m1_exp, max_stale=10)
                if not np.isfinite(m2_x):
                    continue
                entry_cost = (p1_e + p2_e) * (1 + SLIP)
                exit_val = (m1_exit + m2_x) * (1 - SLIP)
                ret = exit_val / entry_cost - 1
                recs.append({"sym": sym, "m1_exp": m1_exp, "entry": entry_day,
                             "side": side, "strike": k, "spot": spot,
                             "iv_m1": iv_m1, "iv_m2": iv_m2, "disp": disp,
                             "ret": np.clip(ret, -1.0, 5.0)})
    D = pd.DataFrame(recs)
    if D.empty:
        print("[events] 0 dispersion trades — nothing to report"); return
    D.to_parquet(ROOT / "intraday_options_strategy/buying/dispersion_strategy.parquet")
    print(f"[events] {len(D)} dispersion trades, {D['entry'].min()}..{D['entry'].max()}")
    print(f"[disp]  median IV_M1-IV_M2 = {D['disp'].median():+.3f}  (positive=backwardation/M1 richer)")

    def rep(sub, name):
        if len(sub) < 8:
            print(f"  {name:38s}: n={len(sub)} (too few)"); return
        b = sub[sub["entry"] <= SPLIT]; f = sub[sub["entry"] > SPLIT]
        print(f"  {name:38s}: ALL {sub['ret'].mean():+7.1%} med {sub['ret'].median():+7.1%} "
              f"hit {(sub['ret']>0).mean():.0%} n={len(sub):4d} | BUILD {b['ret'].mean():+7.1%} | FWD {f['ret'].mean():+7.1%}")

    print("\n=== base rates (both sides, no filter) ===")
    rep(D, "ALL (CE+PE, no filter)")
    rep(D[D["side"] == "CE"], "CE only")
    rep(D[D["side"] == "PE"], "PE only")

    print("\n=== by dispersion SIGN ===")
    rep(D[D["disp"] > 0], "disp>0 (M1 richer / backwardation)")
    rep(D[D["disp"] < 0], "disp<0 (M1 cheaper / contango)")

    print("\n=== threshold sweep: |dispersion| >= T, best sign each ===")
    for T in [0.02, 0.04, 0.06, 0.08, 0.10, 0.15]:
        rep(D[D["disp"] >= T], f"disp>=+{T:.2f}")
        rep(D[D["disp"] <= -T], f"disp<=-{T:.2f}")

    print("\n=== decile view: return vs dispersion (find the real shape) ===")
    D["dec"] = pd.qcut(D["disp"], 10, labels=False, duplicates="drop")
    g = D.groupby("dec").agg(disp_lo=("disp", "min"), disp_hi=("disp", "max"),
                             mean=("ret", "mean"), median=("ret", "median"),
                             hit=("ret", lambda x: (x > 0).mean()), n=("ret", "size"))
    print(g.to_string(formatters={"disp_lo": "{:+.3f}".format, "disp_hi": "{:+.3f}".format,
                                  "mean": "{:+.1%}".format, "median": "{:+.1%}".format, "hit": "{:.0%}".format}))


if __name__ == "__main__":
    run()
