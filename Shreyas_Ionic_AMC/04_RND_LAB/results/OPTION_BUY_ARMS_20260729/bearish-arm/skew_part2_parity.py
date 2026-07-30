"""ARM 2 step 3b: correct the skew measurement for the FORWARD BASIS, using put-call parity
on real traded prices. No re-read of the option parquet -- reuses skew_daily.csv.

WHY THIS IS NECESSARY. Part A inverted IV against the SPOT index and found the 1-step-OTM PE
*cheaper* than the equidistant CE by 1.04 vol points (t=-17.5). NIFTY options are priced off
the FORWARD, not spot, and with positive carry F > S. Measuring "equidistant from ATM-spot"
therefore puts the call nearer the money and the put further from it than I assumed, which
biases the comparison toward "puts look cheap". The size of that bias is directly observable:
at the SAME strike, same minute, put-call parity forces IV_CE == IV_PE, so any measured
same-strike differential is PURE forward mis-specification. Part A found -1.62 vol points
there -- larger than the whole "puts are cheap" effect.

FIX (fully empirical, no assumed rate). From the ATM call and put at the SAME strike:
    C - P = DF * (F - K)   with DF = exp(-rT) ~ 1 for a 1-week tenor
    =>  F_implied = K_atm + (C_atm - P_atm)
F_implied is then used as the underlying for both inversions, so the CE and PE are compared at
equal distance from the FORWARD. Two independent corrections are reported:
  (1) re-inverted IVs on F_implied  -- the principled fix;
  (2) parity-neutralised differential (IV_PE_otm - IV_CE_otm) - (IV_PE_atm - IV_CE_atm)
      -- a difference-in-differences that cancels any common forward error.
They should agree in sign; if they disagree, say so and trust neither.

Output: skew_report_parity.json
"""
from __future__ import annotations

import json
from math import log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

HERE = Path(__file__).resolve().parent


def bs(S, K, T, s, otype):
    if T <= 0 or s <= 0:
        return max(S - K, 0.0) if otype == "CE" else max(K - S, 0.0)
    d1 = (log(S / K) + 0.5 * s * s * T) / (s * sqrt(T))
    d2 = d1 - s * sqrt(T)
    if otype == "CE":
        return S * norm.cdf(d1) - K * norm.cdf(d2)
    return K * norm.cdf(-d2) - S * norm.cdf(-d1)


def iv(price, S, K, T, otype):
    if not (np.isfinite(price) and price > 0 and T > 0 and np.isfinite(S) and S > 0):
        return np.nan
    intr = max(S - K, 0.0) if otype == "CE" else max(K - S, 0.0)
    if price <= intr + 1e-9:
        return np.nan
    try:
        return float(brentq(lambda s: bs(S, K, T, s, otype) - price, 1e-4, 6.0,
                            xtol=1e-6, maxiter=200))
    except Exception:
        return np.nan


def tstat(x):
    x = np.asarray(pd.Series(x).dropna(), float)
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan


def main() -> int:
    d = pd.read_csv(HERE / "skew_daily.csv", parse_dates=["date", "t"])
    d = d.dropna(subset=["px_ce", "px_pe", "px_atm_ce", "px_atm_pe"]).copy()
    d["T"] = d["dte"] / 365.0

    # ---- forward implied by put-call parity on the ATM pair (real traded prices) --------
    d["F_implied"] = d["atm"] + (d["px_atm_ce"] - d["px_atm_pe"])
    d["basis_pts"] = d["F_implied"] - d["spot"]
    d["basis_pct"] = d["basis_pts"] / d["spot"]

    # ---- (1) re-invert BOTH wings on the implied forward --------------------------------
    d["ivF_ce"] = [iv(p, F, K, T, "CE") for p, F, K, T in
                   zip(d.px_ce, d.F_implied, d.k_ce, d.T)]
    d["ivF_pe"] = [iv(p, F, K, T, "PE") for p, F, K, T in
                   zip(d.px_pe, d.F_implied, d.k_pe, d.T)]
    d["ivF_atm_ce"] = [iv(p, F, K, T, "CE") for p, F, K, T in
                       zip(d.px_atm_ce, d.F_implied, d.atm, d.T)]
    d["ivF_atm_pe"] = [iv(p, F, K, T, "PE") for p, F, K, T in
                       zip(d.px_atm_pe, d.F_implied, d.atm, d.T)]

    # ALSO compare at equal distance from the FORWARD, not from ATM-spot: the honest
    # apples-to-apples wing pair. Uses the strikes we have (ATM+-50) but reports how far
    # each really is from F, so the reader can see any residual asymmetry.
    d["dist_ce_from_F"] = d["k_ce"] - d["F_implied"]
    d["dist_pe_from_F"] = d["F_implied"] - d["k_pe"]

    # ---- (2) parity-neutralised difference-in-differences ------------------------------
    d["skew_raw"] = d["iv_pe"] - d["iv_ce"]                       # spot-based (part A)
    d["parity_bias"] = d["iv_atm_pe"] - d["iv_atm_ce"]            # must be 0 in truth
    d["skew_did"] = d["skew_raw"] - d["parity_bias"]
    d["skew_fwd"] = d["ivF_pe"] - d["ivF_ce"]                     # forward-based
    d["parity_bias_fwd"] = d["ivF_atm_pe"] - d["ivF_atm_ce"]      # residual check

    d.to_csv(HERE / "skew_daily_parity.csv", index=False)

    def blk(col, sub=None):
        s = (d if sub is None else sub)[col].dropna()
        return {"n": int(len(s)), "mean_volpts": round(float(s.mean()) * 100, 4),
                "median_volpts": round(float(s.median()) * 100, 4),
                "t": round(tstat(s), 3),
                "frac_positive": round(float((s > 0).mean()), 4)}

    rep = {
        "why": "Part A's spot-based inversion is contaminated by the forward basis; the "
               "same-strike differential measures that contamination exactly (parity forces "
               "it to zero in truth). Both corrections below are computed from real traded "
               "prices only; no interest rate is assumed.",
        "n_days": int(len(d)),
        "forward_basis": {
            "F_minus_S_pts_mean": round(float(d.basis_pts.mean()), 3),
            "F_minus_S_pts_median": round(float(d.basis_pts.median()), 3),
            "F_minus_S_pct_mean": round(float(d.basis_pct.mean()) * 100, 4),
            "annualised_carry_pct_mean": round(float((d.basis_pct / d["T"]).replace(
                [np.inf, -np.inf], np.nan).dropna().mean()) * 100, 3),
            "note": "F_implied = K_atm + (C_atm - P_atm), r-discount ~1 at 1-week tenor. A "
                    "positive basis is exactly why a spot-anchored 'equidistant' comparison "
                    "makes puts look cheap.",
        },
        "spot_based_raw_partA": blk("skew_raw"),
        "same_strike_parity_bias": blk("parity_bias"),
        "CORRECTED_1_forward_reinverted": blk("skew_fwd"),
        "CORRECTED_2_parity_neutralised_DiD": blk("skew_did"),
        "residual_parity_check_on_forward": blk("parity_bias_fwd"),
        "distance_from_forward_pts": {
            "ce_wing_mean": round(float(d.dist_ce_from_F.mean()), 2),
            "pe_wing_mean": round(float(d.dist_pe_from_F.mean()), 2),
            "note": "if these differ, the ATM+-50 pair is NOT equidistant from the forward; "
                    "that residual asymmetry is why correction (2) is the safer read.",
        },
    }
    d["year"] = d["date"].dt.year
    rep["corrected_by_year"] = {int(y): {"n": int(len(g)),
                                         "skew_fwd_volpts": round(float(g.skew_fwd.mean()) * 100, 3),
                                         "skew_did_volpts": round(float(g.skew_did.mean()) * 100, 3)}
                                for y, g in d.groupby("year")}
    s1 = d.skew_fwd.dropna().mean()
    s2 = d.skew_did.dropna().mean()
    rep["VERDICT"] = ("AGREE_puts_richer" if (s1 > 0 and s2 > 0) else
                      "AGREE_puts_cheaper" if (s1 < 0 and s2 < 0) else
                      "DISAGREE_do_not_trust_either")
    (HERE / "skew_report_parity.json").write_text(json.dumps(rep, indent=2, default=str),
                                                  encoding="utf-8")
    print(json.dumps(rep, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
