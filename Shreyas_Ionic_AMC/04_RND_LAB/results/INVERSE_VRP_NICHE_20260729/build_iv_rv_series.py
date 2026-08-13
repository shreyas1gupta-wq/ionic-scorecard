"""Build the daily ATM-IV (real backout) + trailing realized-vol series for NIFTY.
Per PREREG.md common construction. Resumable-not-needed (fast, single pass, ~1250 days).

Outputs: daily_vol_series.csv with columns
  day, expiry, dte, t_iv, spot_px, atm_strike, ce_px, pe_px, straddle_price, iv,
  logret, rv10, iv_pct, rv_pct
iv_pct / rv_pct are EXPANDING-WINDOW percentiles using ONLY strictly-prior days (no lookahead),
min 60 prior observations before a percentile is emitted (else NaN).
"""
import sys, datetime as dt, bisect
import numpy as np, pandas as pd
from pathlib import Path
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "OPTION_PL_HARNESS_20260729"))
import chain          # noqa: E402
import opt_pl          # noqa: E402

OUT = Path(__file__).parent
R = 0.065  # flat risk-free proxy [INFERENCE], repo-rate level; index, no dividend term needed
IV_TIME = dt.time(15, 25)
IV_LO, IV_HI = 1e-4, 5.0


def bs_straddle(S, K, T, r, sigma):
    if sigma <= 0 or T <= 0:
        return max(S - K, 0.0) + max(K - S, 0.0)
    sqrtT = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return call + put


def backout_iv(S, K, T, price):
    if price <= max(S - K, 0.0) + max(K - S, 0.0) + 1e-6:
        return np.nan  # at/below intrinsic floor -> unsolvable / degenerate
    f_lo = bs_straddle(S, K, T, R, IV_LO) - price
    f_hi = bs_straddle(S, K, T, R, IV_HI) - price
    if f_lo * f_hi > 0:
        return np.nan
    try:
        return brentq(lambda s: bs_straddle(S, K, T, R, s) - price, IV_LO, IV_HI, xtol=1e-6)
    except Exception:
        return np.nan


def main():
    spot = opt_pl.load_spot()  # pre-open filtered, naive IST
    spot_dates = spot.index.date  # computed ONCE (was recomputed per-iteration -> O(n*m), OOM'd)
    spot_by_day = {d: g for d, g in spot.groupby(spot_dates)}
    days = sorted(spot_by_day)
    mapping, exps = chain.build_expiry_index()
    print(f"[build] {len(days)} trading days {days[0]}..{days[-1]}, {len(exps)} expiries")

    rows = []
    for i, d in enumerate(days):
        day_bars = spot_by_day[d]
        pre = day_bars[day_bars.index.time <= IV_TIME]
        bar = pre.iloc[-1] if len(pre) else day_bars.iloc[-1]
        t_iv = pre.index[-1] if len(pre) else day_bars.index[-1]
        spot_px = float(bar["close"])

        exp = chain.nearest_expiry(d, min_dte=1, max_dte=8)
        row = dict(day=str(d), t_iv=t_iv, spot_px=spot_px, expiry=str(exp) if exp else None,
                   dte=(exp - d).days if exp else np.nan)
        if exp is None:
            rows.append(row); continue
        atm = round(spot_px / 50) * 50
        try:
            df = chain.load_expiry(exp)
        except Exception as ex:
            row["err"] = f"load_expiry:{type(ex).__name__}"
            rows.append(row); continue
        dchain = df[(df["trading_day"] == d.isoformat()) & (df["strike"] == atm)
                    & (df["option_type"].isin(["CE", "PE"]))]
        if dchain.empty:
            rows.append(row); continue
        ce = dchain[dchain.option_type == "CE"].set_index("t")["close"].sort_index()
        pe = dchain[dchain.option_type == "PE"].set_index("t")["close"].sort_index()
        ce_b = ce[ce.index <= t_iv]
        pe_b = pe[pe.index <= t_iv]
        if ce_b.empty or pe_b.empty:
            rows.append(row); continue
        ce_px, pe_px = float(ce_b.iloc[-1]), float(pe_b.iloc[-1])
        straddle = ce_px + pe_px
        T = row["dte"] / 365.0
        iv = backout_iv(spot_px, atm, T, straddle)
        row.update(atm_strike=atm, ce_px=ce_px, pe_px=pe_px, straddle_price=straddle, iv=iv)
        rows.append(row)
        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(days)}] {d}", flush=True)

    out = pd.DataFrame(rows)
    out["day"] = pd.to_datetime(out["day"])
    out = out.sort_values("day").reset_index(drop=True)

    # ---- trailing 10-session realized vol (annualized), using ONLY strictly-prior closes
    out["logret"] = np.log(out["spot_px"]).diff()
    out["rv10"] = out["logret"].rolling(10).std() * np.sqrt(252)
    out["rv10"] = out["rv10"].shift(1)  # value available AT start of day t must use t-1..t-10

    # ---- expanding no-lookahead percentiles (strictly-prior history only)
    def expanding_pct_nolookahead(s: pd.Series) -> pd.Series:
        vals = s.values
        hist = []  # sorted list of prior values (non-nan)
        out_pct = np.full(len(vals), np.nan)
        for i, v in enumerate(vals):
            if len(hist) >= 60 and np.isfinite(v):
                lo = bisect.bisect_left(hist, v)
                hi = bisect.bisect_right(hist, v)
                out_pct[i] = 100.0 * (lo + hi) / 2.0 / len(hist)
            if np.isfinite(v):
                bisect.insort(hist, v)
        return pd.Series(out_pct, index=s.index)

    out["iv_pct"] = expanding_pct_nolookahead(out["iv"])
    out["rv_pct"] = expanding_pct_nolookahead(out["rv10"])

    out.to_csv(OUT / "daily_vol_series.csv", index=False)
    n_iv = out["iv"].notna().sum()
    print(f"\nsaved daily_vol_series.csv: {len(out)} days, {n_iv} with valid IV backout "
          f"({100*n_iv/len(out):.1f}%)")
    print(out[["day", "dte", "spot_px", "atm_strike", "straddle_price", "iv", "rv10",
               "iv_pct", "rv_pct"]].describe(include="all").to_string())


if __name__ == "__main__":
    main()
