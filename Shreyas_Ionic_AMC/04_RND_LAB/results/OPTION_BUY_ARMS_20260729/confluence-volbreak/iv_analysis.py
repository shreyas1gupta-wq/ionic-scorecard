"""ARM 3 step 3 (Q3, the honest mechanism question): when you enter on a volatility
EXPANSION, are you buying already-elevated IV?

METHOD LAW (Principal, this session): no heuristic required-move formula is used to decide
whether a trade pays. Payoff is the harness's REAL option P&L. IV enters ONLY as a
conditioning variable, and it is DERIVED FROM REAL 1-MIN OPTION PRICES -- never assumed.

Per entry:
  * read the REAL ATM CE and ATM PE 1-min closes at/just before the entry minute
  * straddle = CE + PE            (an observed price, not a model output)
  * sig_straddle = (straddle/spot) / sqrt(DTE_cal/365)   -- normalisation of that price
  * bs_iv       = Black-Scholes IV bisected from the REAL ATM CE price
                  (r=0, q=0, spot-not-forward => monotone approximation, adequate for a
                   PERCENTILE, NOT a quotable vol level. Declared in PRE_REGISTRATION s6.)
  * PIT expanding percentile of sig_straddle (rank vs that cell's own history only)
  * subsequent REALIZED spot move to 15:25 (signed and absolute), measured directly

Then the pre-registered tercile split (<=33.3 vs >66.7 PIT percentile) is applied to the
ALREADY-COMPUTED C1 trades. Because every signal is sized and evaluated independently
(no_overlap=False, lots=1), partitioning the C1 trade set by an entry-time variable is
ARITHMETICALLY IDENTICAL to re-running the harness on the filtered signal list -- so this
is the same test at a fraction of the compute, not an approximation.

Outputs: iv_per_trade.csv, iv_analysis.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
TRDIR = OUT / "trades"
RESULTS = OUT.parent.parent
sys.path.insert(0, str(RESULTS / "OPTION_PL_HARNESS_20260729"))
import opt_pl as H                                     # noqa: E402

CELLS = ["volbrk_orb_volfilter", "volbrk_atr_expansion"]   # PRE_REGISTRATION s8 item 2
CFG = "C1_ATM_hold1525"
LO_CUT, HI_CUT = 33.3, 66.7                                # fixed in advance


# ------------------------------------------------------------------ BS IV
def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call(S: float, K: float, T: float, sig: float) -> float:
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    v = sig * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / v
    return S * _ncdf(d1) - K * _ncdf(d1 - v)


def call_iv(price: float, S: float, K: float, T: float) -> float:
    """Bisection. Returns NaN when the price is outside the no-arbitrage band."""
    if not (np.isfinite(price) and price > 0 and T > 0 and S > 0 and K > 0):
        return np.nan
    if price <= max(S - K, 0.0) + 1e-9 or price >= S:
        return np.nan
    lo, hi = 1e-4, 5.0
    if bs_call(S, K, T, hi) < price:
        return np.nan
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if bs_call(S, K, T, mid) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------------ chain reads
def px_at(store, exp, strike, otype, t) -> tuple[float, float]:
    """Real 1-min close at or before t for that exact listed strike. (price, lag_min)."""
    leg = store.leg(exp, int(strike), otype)
    if leg is None or leg.empty:
        return np.nan, np.nan
    w = leg[leg.index <= t]
    if w.empty:
        return np.nan, np.nan
    row = w.iloc[-1]
    return float(row["close"]), (t - w.index[-1]).total_seconds() / 60.0


def build_iv_table(cell: str, spot: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for spl in ("build", "forward"):
        p = TRDIR / f"{cell}__{CFG}__{spl}.csv"
        if not p.exists():
            print(f"   [skip] missing {p.name}", flush=True)
            continue
        d = pd.read_csv(p, parse_dates=["signal_t", "entry_t", "exit_t"])
        d["split"] = spl
        frames.append(d)
    if not frames:
        return pd.DataFrame()
    tr = pd.concat(frames, ignore_index=True)
    tr = tr[tr["status"] == "filled"].sort_values("entry_t").reset_index(drop=True)

    store = H._ExpiryStore(maxsize=2)
    by_day = {d: g for d, g in spot.groupby(spot.index.date)}
    rows = []
    for i, r in tr.iterrows():
        exp = pd.Timestamp(r["exp"]).date()
        t, S, K_atm = r["entry_t"], float(r["spot_entry"]), int(r["atm"])
        dte = int(r["dte_entry"])
        T = max(dte, 0.5) / 365.0          # 0DTE floored at half a day (declared)
        ce, ce_lag = px_at(store, exp, K_atm, "CE", t)
        pe, pe_lag = px_at(store, exp, K_atm, "PE", t)
        strad = ce + pe if (np.isfinite(ce) and np.isfinite(pe)) else np.nan
        sig_str = (strad / S) / math.sqrt(T) if np.isfinite(strad) and S > 0 else np.nan
        iv = call_iv(ce, S, K_atm, T)
        # realized subsequent spot move to 15:25 -- measured, no formula
        day = by_day.get(pd.Timestamp(t).date())
        rm_signed = rm_abs = np.nan
        if day is not None:
            cut = pd.Timestamp(pd.Timestamp(t).date()) + pd.Timedelta(hours=15, minutes=25)
            w = day[(day.index >= t) & (day.index <= cut)]
            if len(w) > 1:
                e = float(w["close"].iloc[0]); x = float(w["close"].iloc[-1])
                rm_signed = int(r["direction"]) * (x / e - 1.0)
                rm_abs = abs(x / e - 1.0)
        rows.append(dict(
            cell=cell, split=r["split"], signal_t=r["signal_t"], entry_t=t,
            direction=int(r["direction"]), spot=S, atm=K_atm, dte=dte,
            atm_ce=ce, atm_pe=pe, straddle=strad, ce_lag_min=ce_lag, pe_lag_min=pe_lag,
            sig_straddle=sig_str, bs_iv=iv,
            realized_signed=rm_signed, realized_abs=rm_abs,
            gross=float(r["gross"]), net_pnl=float(r["net_pnl"]),
            ret_pct_net=float(r["ret_pct_net"]), entry_fill=float(r["entry_fill"]),
        ))
        if i and i % 500 == 0:
            print(f"   {cell}: {i}/{len(tr)}", flush=True)
    d = pd.DataFrame(rows)

    # ---- PIT expanding percentile: rank vs that cell's OWN PRIOR history only
    d = d.sort_values("entry_t").reset_index(drop=True)
    for src, dst in (("sig_straddle", "pit_pct_straddle"), ("bs_iv", "pit_pct_bsiv")):
        v = d[src].values
        pit = np.full(len(v), np.nan)
        for j in range(len(v)):
            hist = v[:j][np.isfinite(v[:j])]
            if len(hist) >= 60 and np.isfinite(v[j]):     # need a history to rank against
                pit[j] = 100.0 * (hist < v[j]).mean()
        d[dst] = pit
    # full-sample percentile = DESCRIPTIVE ONLY (not knowable at entry time)
    d["full_pct_straddle"] = d["sig_straddle"].rank(pct=True) * 100.0
    return d


# ------------------------------------------------------------------ reporting
def bucket_stats(d: pd.DataFrame) -> dict:
    if d.empty:
        return {"n": 0}
    n = d["net_pnl"]
    g = d["gross"]
    wins, loss = n[n > 0], n[n <= 0]
    return {
        "n": int(len(d)),
        "mean_bs_iv": round(float(d["bs_iv"].mean()), 4) if d["bs_iv"].notna().any() else None,
        "mean_sig_straddle": round(float(d["sig_straddle"].mean()), 4),
        "mean_realized_abs_pct": round(100 * float(d["realized_abs"].mean()), 4),
        "mean_realized_signed_pct": round(100 * float(d["realized_signed"].mean()), 4),
        "gross_total": round(float(g.sum()), 0), "net_total": round(float(n.sum()), 0),
        "mean_ret_pct_net": round(float(d["ret_pct_net"].mean()), 5),
        "t_ret_pct_net": round(float(d["ret_pct_net"].mean() / d["ret_pct_net"].std()
                                     * math.sqrt(len(d))), 3) if d["ret_pct_net"].std() > 0 else None,
        "wr_net": round(float((n > 0).mean()), 4),
        "pf_net": round(float(wins.sum() / abs(loss.sum())), 3) if loss.sum() != 0 else None,
        "mean_entry_premium": round(float(d["entry_fill"].mean()), 2),
    }


def main():
    spot = H.load_spot()
    report = {"pre_registration": "PRE_REGISTRATION.md",
              "method": "IV derived from REAL ATM CE/PE 1-min prices; r=0,q=0,spot-not-forward "
                        "=> monotone approximation, used for PERCENTILE only",
              "tercile_cuts": [LO_CUT, HI_CUT], "config": CFG, "cells": {}}
    all_tabs = []
    for cell in CELLS:
        print(f"\n=== IV table: {cell} ===", flush=True)
        d = build_iv_table(cell, spot)
        if d.empty:
            report["cells"][cell] = {"error": "no trades found"}
            continue
        all_tabs.append(d)
        cov = {"rows": int(len(d)),
               "straddle_available_frac": round(float(d["straddle"].notna().mean()), 4),
               "bs_iv_available_frac": round(float(d["bs_iv"].notna().mean()), 4),
               "pit_rankable_frac": round(float(d["pit_pct_straddle"].notna().mean()), 4),
               "median_ce_lag_min": round(float(d["ce_lag_min"].median()), 2),
               "median_pe_lag_min": round(float(d["pe_lag_min"].median()), 2)}
        rec = {"coverage": cov, "by_split": {}, "terciles_PIT": {}, "quintiles_PIT": {},
               "correlations": {}}
        for spl, gg in d.groupby("split"):
            rec["by_split"][spl] = bucket_stats(gg)
        # --- the pre-registered tercile test, BUILD set (PIT percentile)
        for spl in ("build", "forward"):
            s = d[(d["split"] == spl) & d["pit_pct_straddle"].notna()]
            lo = s[s["pit_pct_straddle"] <= LO_CUT]
            mid = s[(s["pit_pct_straddle"] > LO_CUT) & (s["pit_pct_straddle"] <= HI_CUT)]
            hi = s[s["pit_pct_straddle"] > HI_CUT]
            rec["terciles_PIT"][spl] = {"IV_LOW": bucket_stats(lo), "IV_MID": bucket_stats(mid),
                                        "IV_HIGH": bucket_stats(hi)}
        # --- quintile view (descriptive, build only)
        s = d[(d["split"] == "build") & d["pit_pct_straddle"].notna()].copy()
        if len(s) >= 50:
            s["q"] = pd.qcut(s["pit_pct_straddle"], 5, labels=False, duplicates="drop")
            rec["quintiles_PIT"]["build"] = {f"Q{int(q)+1}": bucket_stats(gg)
                                             for q, gg in s.groupby("q")}
        # --- does high implied vol actually come with a bigger realized move?
        c = d.dropna(subset=["sig_straddle", "realized_abs"])
        if len(c) > 30:
            rec["correlations"] = {
                "n": int(len(c)),
                "corr_sig_straddle_vs_realized_abs": round(float(
                    np.corrcoef(c["sig_straddle"], c["realized_abs"])[0, 1]), 4),
                "corr_sig_straddle_vs_ret_pct_net": round(float(
                    np.corrcoef(c["sig_straddle"], c["ret_pct_net"])[0, 1]), 4),
                "corr_pitpct_vs_ret_pct_net": round(float(np.corrcoef(
                    d.dropna(subset=["pit_pct_straddle", "ret_pct_net"])["pit_pct_straddle"],
                    d.dropna(subset=["pit_pct_straddle", "ret_pct_net"])["ret_pct_net"])[0, 1]), 4),
            }
        report["cells"][cell] = rec
        print(f"   coverage {cov}", flush=True)
        for spl in ("build", "forward"):
            t3 = rec["terciles_PIT"][spl]
            for k in ("IV_LOW", "IV_MID", "IV_HIGH"):
                b = t3[k]
                if b.get("n"):
                    print(f"   {spl:7s} {k:8s} n={b['n']:5d} iv={b['mean_bs_iv']} "
                          f"realized|move|={b['mean_realized_abs_pct']}% "
                          f"net={b['net_total']:,.0f} ret/tr={b['mean_ret_pct_net']:+.4f} "
                          f"t={b['t_ret_pct_net']}", flush=True)

    if all_tabs:
        pd.concat(all_tabs, ignore_index=True).to_csv(OUT / "iv_per_trade.csv", index=False)
    (OUT / "iv_analysis.json").write_text(json.dumps(report, indent=2, default=str),
                                          encoding="utf-8")
    print("\n[done] iv_analysis.json + iv_per_trade.csv", flush=True)


if __name__ == "__main__":
    sys.exit(main())
