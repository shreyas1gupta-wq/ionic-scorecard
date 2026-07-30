"""Build the daily NIFTY OPTIDX term-structure series: near-month ATM IV vs next-month ATM IV,
from the 16-year daily F&O bhavcopy archive (fo_idx_{2011..2026}.parquet).

WHY BHAVCOPY NOT THE 1-MIN TREE: each 1-min expiry file holds only the last ~10 days of that
expiry's life -> a next-month leg is simply never priced there. Bhavcopy carries the FULL live
chain (all simultaneously-listed expiries) on every date, which a calendar/diagonal needs.

METHOD (reuses the backout MECHANIC from INVERSE_VRP_NICHE_20260729/build_iv_rv_series.py --
brentq root-find on a closed-form straddle price -- but swaps the pricing model from
Black-Scholes-on-spot to BLACK-76-on-tenor-matched-futures-forward, because:
  (a) NIFTY spot index history only goes back to 2016 (nse_official_all_indices.parquet), while
      this archive runs 2011-2026; futures are in the SAME file for the full period.
  (b) a calendar's near and far legs sit on DIFFERENT forward curves (cost-of-carry differs by
      tenor, materially so in the 8-9% repo years of 2011-2013) -- using one flat "spot" for both
      legs would misprice the ATM strike and bias the IV backout. Tenor-matched forwards avoid
      assuming a term structure of rates rather than measuring one for vol.
  [INFERENCE] Black-76, flat discount r=0.065 (same repo-rate proxy the existing script used) --
  r only discounts the payoff here (forward already embeds carry), so its effect on the IV backout
  is second-order.

HARD GATES (per task + firm landmines):
  - CONTRACTS>0 required on BOTH legs (CE and PE) of a straddle before it is used -- untraded
    model-priced strikes are excluded, never averaged over.
  - Never read SETTLE_PR as an option price (expiry-day settle = underlying level, not the
    option) -- this script reads CLOSE only, everywhere.
  - Date parsing: EXPIRY_DT/TIMESTAMP strings are NOT uniformly formatted across the 16 files --
    2012 mixes 2-digit and 4-digit years (bit two other queued jobs today, 110/113 both died on
    this exact bug). parse_nse_date() below tries 4-digit first, falls back to 2-digit.

OUTPUT: term_structure.csv -- one row per trading day with a valid near+far ATM straddle pair:
  day, near_expiry, near_dte, far_expiry, far_dte, fwd_near, fwd_far, near_strike, far_strike,
  near_straddle, far_straddle, near_iv, far_iv, iv_spread(=near-far), iv_ratio(=near/far),
  near_iv_pct (expanding, no-lookahead, min 60 prior obs -- same convention as build_iv_rv_series.py)
"""
import bisect
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DATA = ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "fo_bhavcopy_hist"
OUT = Path(__file__).parent
YEARS = list(range(2011, 2027))

R = 0.065           # flat discount proxy [INFERENCE], same as build_iv_rv_series.py
IV_LO, IV_HI = 1e-4, 5.0
NEAR_MIN_DTE = 2     # numerically stable floor for the backout; NOT the trading exit rule
COLS = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "CLOSE", "CONTRACTS", "TIMESTAMP"]


def parse_nse_date(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    out = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    bad = out.isna()
    if bad.any():
        out.loc[bad] = pd.to_datetime(s[bad], format="%d-%b-%y", errors="coerce")
    still_bad = out.isna()
    if still_bad.any():
        out.loc[still_bad] = pd.to_datetime(s[still_bad], format="mixed", dayfirst=True, errors="coerce")
    return out


def bs76_straddle(F, K, T, r, sigma):
    """Black-76: underlying = forward F, discounted at flat r. Straddle = call+put."""
    if sigma <= 0 or T <= 0:
        return max(F - K, 0.0) + max(K - F, 0.0)
    sqrtT = np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    disc = np.exp(-r * T)
    call = disc * (F * norm.cdf(d1) - K * norm.cdf(d2))
    put = disc * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
    return call + put


def backout_iv76(F, K, T, price):
    floor = max(F - K, 0.0) + max(K - F, 0.0)
    if price <= floor * np.exp(-R * T) + 1e-6:
        return np.nan
    f_lo = bs76_straddle(F, K, T, R, IV_LO) - price
    f_hi = bs76_straddle(F, K, T, R, IV_HI) - price
    if f_lo * f_hi > 0:
        return np.nan
    try:
        return brentq(lambda s: bs76_straddle(F, K, T, R, s) - price, IV_LO, IV_HI, xtol=1e-6)
    except Exception:
        return np.nan


def load_year(y: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"fo_idx_{y}.parquet", columns=COLS)
    df = df[df["SYMBOL"] == "NIFTY"].copy()
    df["EXPIRY_DT"] = parse_nse_date(df["EXPIRY_DT"])
    df["TIMESTAMP"] = parse_nse_date(df["TIMESTAMP"])
    return df


def main():
    t0 = time.time()
    print(f"[{time.time()-t0:6.1f}s] pass 1: collecting global monthly-expiry calendar ...", flush=True)

    # ---- pass 1: cheap, EXPIRY_DT-only, to build the global monthly-expiry list (spans year files)
    all_expiries = set()
    for y in YEARS:
        df = pd.read_parquet(DATA / f"fo_idx_{y}.parquet", columns=["SYMBOL", "EXPIRY_DT"])
        df = df[df["SYMBOL"] == "NIFTY"]
        all_expiries.update(parse_nse_date(df["EXPIRY_DT"]).dropna().unique())
    all_expiries = pd.Series(sorted(all_expiries))
    ym = all_expiries.dt.year * 100 + all_expiries.dt.month
    monthly_mask = all_expiries.groupby(ym).transform("max") == all_expiries
    monthly_expiries = sorted(all_expiries[monthly_mask].tolist())
    print(f"  {len(all_expiries)} distinct expiries total -> {len(monthly_expiries)} monthly", flush=True)

    rows = []
    for y in YEARS:
        print(f"[{time.time()-t0:6.1f}s] year {y}: loading ...", flush=True)
        df = load_year(y)
        fut = df[(df["INSTRUMENT"] == "FUTIDX")]
        opt = df[(df["INSTRUMENT"] == "OPTIDX") & (df["CONTRACTS"] > 0)
                 & (df["OPTION_TYP"].isin(["CE", "PE"]))]
        days = sorted(df["TIMESTAMP"].dropna().unique())
        # [DATA] the 2024-25 backfill/extend pass (CLAUDE.md landmine #4) introduces duplicate
        # (TIMESTAMP,EXPIRY_DT[,STRIKE,TYP]) rows in some years -> collapse with mean before indexing,
        # else a plain .loc lookup returns a Series and blows up float().
        fut_idx = fut.groupby(["TIMESTAMP", "EXPIRY_DT"])["CLOSE"].mean()
        opt_dedup = opt.groupby(["TIMESTAMP", "EXPIRY_DT", "OPTION_TYP", "STRIKE_PR"])["CLOSE"].mean().reset_index()
        opt_g = opt_dedup.groupby(["TIMESTAMP", "EXPIRY_DT"])

        for d in days:
            d_ts = pd.Timestamp(d)
            # locate near/far monthly expiries relative to this date
            future_monthlies = [e for e in monthly_expiries if (e - d_ts).days >= NEAR_MIN_DTE]
            if len(future_monthlies) < 2:
                continue
            near_exp, far_exp = future_monthlies[0], future_monthlies[1]
            near_dte, far_dte = (near_exp - d_ts).days, (far_exp - d_ts).days

            try:
                fwd_near = float(fut_idx.loc[(d_ts, near_exp)])
            except KeyError:
                continue
            try:
                fwd_far = float(fut_idx.loc[(d_ts, far_exp)])
            except KeyError:
                fwd_far = fwd_near  # [INFERENCE] fallback: far future not separately listed yet

            def atm_straddle(exp, F):
                try:
                    g = opt_g.get_group((d_ts, exp))
                except KeyError:
                    return None, None, None
                ce = g[g["OPTION_TYP"] == "CE"].set_index("STRIKE_PR")["CLOSE"]
                pe = g[g["OPTION_TYP"] == "PE"].set_index("STRIKE_PR")["CLOSE"]
                common = ce.index.intersection(pe.index)
                if len(common) == 0:
                    return None, None, None
                strike = min(common, key=lambda k: abs(k - F))
                return strike, float(ce.loc[strike]), float(pe.loc[strike])

            k_near, ce_n, pe_n = atm_straddle(near_exp, fwd_near)
            k_far, ce_f, pe_f = atm_straddle(far_exp, fwd_far)
            if k_near is None or k_far is None:
                continue

            straddle_near, straddle_far = ce_n + pe_n, ce_f + pe_f
            T_near, T_far = near_dte / 365.0, far_dte / 365.0
            iv_near = backout_iv76(fwd_near, k_near, T_near, straddle_near)
            iv_far = backout_iv76(fwd_far, k_far, T_far, straddle_far)

            rows.append(dict(
                day=d_ts, near_expiry=near_exp, near_dte=near_dte, far_expiry=far_exp, far_dte=far_dte,
                fwd_near=fwd_near, fwd_far=fwd_far, near_strike=k_near, far_strike=k_far,
                near_straddle=straddle_near, far_straddle=straddle_far, iv_near=iv_near, iv_far=iv_far,
            ))
        print(f"[{time.time()-t0:6.1f}s] year {y}: {sum(1 for r in rows if r['day'].year==y)} rows w/ both legs", flush=True)

    out = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    out["iv_spread"] = out["iv_near"] - out["iv_far"]
    out["iv_ratio"] = out["iv_near"] / out["iv_far"]

    # expanding no-lookahead percentile of near-month IV (same convention as build_iv_rv_series.py)
    def expanding_pct_nolookahead(s: pd.Series) -> pd.Series:
        vals = s.values
        hist = []
        out_pct = np.full(len(vals), np.nan)
        for i, v in enumerate(vals):
            if len(hist) >= 60 and np.isfinite(v):
                lo = bisect.bisect_left(hist, v)
                hi = bisect.bisect_right(hist, v)
                out_pct[i] = 100.0 * (lo + hi) / 2.0 / len(hist)
            if np.isfinite(v):
                bisect.insort(hist, v)
        return pd.Series(out_pct, index=s.index)

    out["near_iv_pct"] = expanding_pct_nolookahead(out["iv_near"])
    out["spread_pct"] = expanding_pct_nolookahead(out["iv_spread"])

    out.to_csv(OUT / "term_structure.csv", index=False)
    n_valid = out["iv_spread"].notna().sum()
    print(f"\n[{time.time()-t0:6.1f}s] saved term_structure.csv: {len(out)} days, "
          f"{n_valid} with valid iv_spread ({100*n_valid/max(len(out),1):.1f}%)")
    print(out[["day", "near_dte", "far_dte", "iv_near", "iv_far", "iv_spread", "iv_ratio", "near_iv_pct"]]
          .describe(include="all").to_string())


if __name__ == "__main__":
    main()
