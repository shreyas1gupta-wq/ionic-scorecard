"""ARM 2 (BEARISH) step 3: is NIFTY index PUT SKEW real, and how much does a put BUYER pay?

Pre-registered method (PRE_REGISTRATION.md section 8). EMPIRICAL ONLY -- IV is INVERTED OUT
OF REAL TRADED 1-MIN OPTION PRICES. No IV level is ever assumed, and no "required move"
formula is used (Principal's METHOD LAW this session).

Two independent measurements:

  (A) CALENDAR SNAPSHOT -- every trading day at 11:00 IST, nearest weekly expiry with
      2-7 DTE: the 1-step-OTM CE (ATM+50) vs the 1-step-OTM PE (ATM-50). EQUIDISTANT from
      ATM. Real 1-min closes -> Brent-inverted Black-Scholes IV (r=0, q=0, T=cal days/365).
      Reports IV_PE - IV_CE, premium ratio, and the rupee premium gap.

  (B) MATCHED-AT-SIGNAL -- at every bearish signal's actual entry minute, price the PE we
      really buy AND the mirror-offset CE at the same minute/expiry. This is the honest
      decision-relevant number: what the bearish arm pays versus what the bullish arm pays,
      same timestamps, same distance from ATM.

Then the translation the Principal asked for: from the OBSERVED premium gap, how many extra
POINTS of favourable move a put buyer must earn before he is level with a call buyer at the
same moneyness distance. That is arithmetic on measured prices (delta ~ 1 for a long option
past its breakeven), not a heuristic model.

Outputs: skew_daily.csv, skew_at_signals.csv, skew_report.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from math import log, sqrt, exp
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parents[1] / "OPTION_PL_HARNESS_20260729"
sys.path.insert(0, str(HARNESS))
import opt_pl as H                                                    # noqa: E402
sys.path.insert(0, str(HERE.parents[3].parent / "intraday_options_strategy" / "buying"))
import chain                                                          # noqa: E402

STEP = 50
SNAP = dt.time(11, 0)
MIN_DTE, MAX_DTE = 2, 7


def bs(S, K, T, sigma, otype):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0) if otype == "CE" else max(K - S, 0.0)
    d1 = (log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    if otype == "CE":
        return S * norm.cdf(d1) - K * norm.cdf(d2)
    return K * norm.cdf(-d2) - S * norm.cdf(-d1)


def iv(price, S, K, T, otype):
    """Brent inversion on a REAL traded price. None when the price is below intrinsic or
    outside a bracketable range -- never silently clipped to a guess."""
    if not (np.isfinite(price) and price > 0 and T > 0):
        return None
    intr = max(S - K, 0.0) if otype == "CE" else max(K - S, 0.0)
    if price <= intr + 1e-9:
        return None
    try:
        return float(brentq(lambda s: bs(S, K, T, s, otype) - price, 1e-4, 6.0,
                            xtol=1e-6, maxiter=200))
    except Exception:
        return None


def main() -> int:
    spot = H.load_spot()
    _mapping, exps = chain.build_expiry_index()   # (dict, sorted list of expiry dates)
    print(f"[skew] {len(exps)} expiries", flush=True)

    store = H._ExpiryStore(maxsize=2)
    days = sorted({d for d in spot.index.date})
    rows = []
    for d in days:
        cands = [e for e in exps if MIN_DTE <= (e - d).days <= MAX_DTE]
        if not cands:
            continue
        exp = cands[0]
        day = spot[spot.index.date == d]
        snap = day[day.index.time <= SNAP]
        if snap.empty:
            continue
        t = snap.index[-1]
        S = float(snap["close"].iloc[-1])
        atm = int(round(S / STEP) * STEP)
        kce, kpe = atm + STEP, atm - STEP
        try:
            lce = store.leg(exp, kce, "CE")
            lpe = store.leg(exp, kpe, "PE")
            latm_c = store.leg(exp, atm, "CE")
            latm_p = store.leg(exp, atm, "PE")
        except Exception:
            continue
        if lce is None or lpe is None:
            continue

        def px(leg, upto):
            if leg is None:
                return (np.nan, np.nan)
            w = leg[(leg.index <= upto) & (leg.index >= upto - pd.Timedelta(minutes=5))]
            w = w[w["volume"] > 0]
            if w.empty:
                return (np.nan, np.nan)
            return (float(w["close"].iloc[-1]), float(w["volume"].iloc[-1]))

        pce, vce = px(lce, t)
        ppe, vpe = px(lpe, t)
        pac, _ = px(latm_c, t)
        pap, _ = px(latm_p, t)
        if not (np.isfinite(pce) and np.isfinite(ppe)):
            continue
        T = (exp - d).days / 365.0
        ivc = iv(pce, S, kce, T, "CE")
        ivp = iv(ppe, S, kpe, T, "PE")
        iva_c = iv(pac, S, atm, T, "CE") if np.isfinite(pac) else None
        iva_p = iv(pap, S, atm, T, "PE") if np.isfinite(pap) else None
        rows.append(dict(date=d, exp=exp, dte=(exp - d).days, t=t, spot=S, atm=atm,
                         k_ce=kce, k_pe=kpe, px_ce=pce, px_pe=ppe, vol_ce=vce, vol_pe=vpe,
                         iv_ce=ivc, iv_pe=ivp, px_atm_ce=pac, px_atm_pe=pap,
                         iv_atm_ce=iva_c, iv_atm_pe=iva_p))

    dd = pd.DataFrame(rows)
    dd.to_csv(HERE / "skew_daily.csv", index=False)
    print(f"[skew] {len(dd)} daily snapshots", flush=True)

    rep = {"method": "PRE_REGISTRATION.md section 8; IV inverted from real 1-min traded "
                     "closes, r=0 q=0 T=cal_days/365; OTM1 CE (ATM+50) vs OTM1 PE (ATM-50), "
                     "equidistant", "snapshot_time": "11:00 IST", "dte_window": [MIN_DTE, MAX_DTE],
           "n_days": int(len(dd))}
    v = dd.dropna(subset=["iv_ce", "iv_pe"])
    rep["A_otm1_equidistant"] = {
        "n": int(len(v)),
        "iv_ce_mean": round(float(v.iv_ce.mean()), 5),
        "iv_pe_mean": round(float(v.iv_pe.mean()), 5),
        "iv_pe_minus_ce_mean_volpts": round(float((v.iv_pe - v.iv_ce).mean()) * 100, 4),
        "iv_pe_minus_ce_median_volpts": round(float((v.iv_pe - v.iv_ce).median()) * 100, 4),
        "frac_days_pe_richer": round(float((v.iv_pe > v.iv_ce).mean()), 4),
        "t_stat_iv_diff": round(float((v.iv_pe - v.iv_ce).mean() /
                                      (v.iv_pe - v.iv_ce).std() * np.sqrt(len(v))), 3),
        "premium_ratio_pe_over_ce_mean": round(float((v.px_pe / v.px_ce).mean()), 4),
        "premium_ratio_pe_over_ce_median": round(float((v.px_pe / v.px_ce).median()), 4),
        "premium_gap_rs_mean": round(float((v.px_pe - v.px_ce).mean()), 3),
        "premium_gap_pct_of_ce_mean": round(float(((v.px_pe - v.px_ce) / v.px_ce).mean()) * 100, 3),
    }
    va = dd.dropna(subset=["iv_atm_ce", "iv_atm_pe"])
    if len(va):
        rep["A2_atm_same_strike"] = {
            "n": int(len(va)),
            "iv_atm_ce_mean": round(float(va.iv_atm_ce.mean()), 5),
            "iv_atm_pe_mean": round(float(va.iv_atm_pe.mean()), 5),
            "iv_pe_minus_ce_mean_volpts": round(float((va.iv_atm_pe - va.iv_atm_ce).mean()) * 100, 4),
            "note": "same strike, same expiry, same minute -> put-call parity makes this a "
                    "check on the forward/discount rate, NOT a skew measure. Reported for "
                    "transparency only.",
        }
    # by DTE bucket and by year, to see whether skew is a regime artefact
    v2 = v.copy()
    v2["year"] = pd.to_datetime(v2["date"]).dt.year
    rep["A_by_year"] = {int(y): {"n": int(len(g)),
                                 "iv_pe_minus_ce_volpts": round(float((g.iv_pe - g.iv_ce).mean()) * 100, 3),
                                 "frac_pe_richer": round(float((g.iv_pe > g.iv_ce).mean()), 3)}
                        for y, g in v2.groupby("year")}
    rep["A_by_dte"] = {int(k): {"n": int(len(g)),
                                "iv_pe_minus_ce_volpts": round(float((g.iv_pe - g.iv_ce).mean()) * 100, 3)}
                       for k, g in v2.groupby("dte")}

    if "--partA" in sys.argv:
        (HERE / "skew_report_A.json").write_text(json.dumps(rep, indent=2, default=str),
                                                 encoding="utf-8")
        print(json.dumps({k: rep[k] for k in rep if k.startswith(("A_otm1", "A2", "A_by"))},
                         indent=2, default=str), flush=True)
        return 0

    # ---------------------------------------------------------------- (B) matched at signal
    print("[skew] matched-at-signal comparison", flush=True)
    best = None
    for f in sorted(HERE.glob("trades_dte2_3_OTM1_E1*.csv")):
        best = f
    if best is None:
        for f in sorted(HERE.glob("trades_*.csv")):
            best = f
    if best is not None:
        tr = pd.read_csv(best, parse_dates=["signal_t", "entry_t", "exit_t"])
        f = tr[tr.status == "filled"].copy()
        out = []
        for r in f.itertuples(index=False):
            exp = pd.Timestamp(r.exp).date()
            S = float(r.spot_entry)
            atm = int(r.atm)
            kpe = int(r.strike)
            kce = atm + (atm - kpe)                 # mirror distance on the call side
            t = pd.Timestamp(r.entry_t)
            try:
                lce = store.leg(exp, kce, "CE")
            except Exception:
                continue
            if lce is None:
                continue
            w = lce[(lce.index <= t) & (lce.index >= t - pd.Timedelta(minutes=5))]
            w = w[w["volume"] > 0]
            if w.empty:
                continue
            pce = float(w["close"].iloc[-1])
            ppe = float(r.entry_px_raw)
            T = max((exp - t.date()).days, 0) / 365.0
            out.append(dict(entry_t=t, exp=exp, dte=(exp - t.date()).days, spot=S, atm=atm,
                            k_pe=kpe, k_ce=kce, px_pe=ppe, px_ce=pce,
                            iv_pe=iv(ppe, S, kpe, T, "PE"), iv_ce=iv(pce, S, kce, T, "CE"),
                            tag=r.tag))
        sm = pd.DataFrame(out)
        sm.to_csv(HERE / "skew_at_signals.csv", index=False)
        if len(sm):
            q = sm.dropna(subset=["iv_pe", "iv_ce"])
            rep["B_matched_at_signal"] = {
                "source_file": best.name, "n_pairs": int(len(sm)), "n_iv_pairs": int(len(q)),
                "px_pe_mean": round(float(sm.px_pe.mean()), 2),
                "px_ce_mean": round(float(sm.px_ce.mean()), 2),
                "premium_gap_rs_mean": round(float((sm.px_pe - sm.px_ce).mean()), 3),
                "premium_gap_pct_of_ce": round(float(((sm.px_pe - sm.px_ce) / sm.px_ce).mean()) * 100, 3),
                "frac_pe_dearer": round(float((sm.px_pe > sm.px_ce).mean()), 4),
                "iv_pe_minus_ce_volpts": (round(float((q.iv_pe - q.iv_ce).mean()) * 100, 4)
                                          if len(q) else None),
                "extra_points_to_breakeven_vs_call": round(float((sm.px_pe - sm.px_ce).mean()), 3),
                "note": "extra_points_to_breakeven_vs_call = the OBSERVED mean rupee premium "
                        "gap. A long option past its breakeven moves ~1:1 with the index, so "
                        "the put buyer needs that many extra INDEX POINTS of favourable move "
                        "to be level with a call buyer the same distance from ATM. Arithmetic "
                        "on measured prices, not a model.",
            }
    (HERE / "skew_report.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in rep if k.startswith(("A_otm1", "A2", "B_"))},
                     indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
