"""S-03 FF-calendar pre-IC INCREMENTAL SHUFFLE (D-M2, 2026-07-04).

Question: does FF SELECTION (pick peak-FF, filter FF>=0.25, tier-size) add return
over a random calendar entry in the SAME large-cap universe/period? An edge is what
remains after the regime/universe beta (2026-07-04 IC-1 lesson).

LARGE-CAP GATE first: symbols with a FF candidate before 2024-01-01 (ex-ante liquid).

Return formula: filtered_portfolio.py L59-60 (CE-leg calendar, SLIP=0.015).
Booking: capital-weighted monthly mean on m1_exp (exit-month), tier weights 0.75/1.0/1.25.

Nulls:
  N1 within-month FF shuffle : per expiry-month, permute FF values across that month's
                               trades, re-apply FF>=0.25 + tier weight on shuffled FF.
                               (tests SELECTION+SIZING skill; preserves month set & economics)
  N2 global FF shuffle       : permute FF across ALL trades (break FF<->ret link entirely).
  N3 random-K entry proxy    : ignore FF; take a RANDOM trade per (sym,month) as the entry,
                               equal-weight, no FF filter -> "random calendar entry" baseline.
Pre-registered kill: incremental (actual - null) p>=0.05 one-sided => FF selection adds nothing.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
FF = ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet"
OUT = ROOT / "Shreyas_Ionic_AMC/results/S-03/20260704_shuffle"
SLIP = 0.015
FF_MIN = 0.25
SPLIT = pd.Timestamp(2024, 12, 31)
NSH = 1000
RNG = np.random.default_rng(20260704)


def tierw(f):
    return 0.75 if f < 0.5 else (1.0 if f < 0.75 else 1.25)


def load():
    ff = pd.read_parquet(FF)
    ff["entry"] = pd.to_datetime(ff["entry"]); ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])
    ff["ret"] = (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
                 - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP)) / ff["CE_be"]
    ff["month"] = ff["m1_exp"].dt.to_period("M")
    return ff


def large_cap(ff):
    first = ff.groupby("sym")["entry"].min()
    lc = set(first[first < pd.Timestamp(2024, 1, 1)].index)
    return ff[ff["sym"].isin(lc)].copy(), lc


def tierw_vec(f):
    return np.where(f < 0.5, 0.75, np.where(f < 0.75, 1.0, 1.25))


def ptw_fast(ff_arr, ret_arr):
    """Per-trade tier-weighted mean of ret over FF>=0.25 rows. Pure-numpy, for the shuffle loop."""
    mask = ff_arr >= FF_MIN
    if not mask.any():
        return np.nan
    w = tierw_vec(ff_arr[mask])
    return np.average(ret_arr[mask], weights=w)


def wmean_monthly(df, ffcol, retcol="ret"):
    """FF>=0.25 filter on ffcol, tier-weight on ffcol, capital-weighted monthly mean of ret,
    then equal-weight across months (matches filtered_portfolio booking spirit). Returns
    (per-trade weighted mean, monthly series)."""
    sub = df[df[ffcol] >= FF_MIN].copy()
    if sub.empty:
        return np.nan, pd.Series(dtype=float), 0
    sub["w"] = sub[ffcol].apply(tierw)
    mon = sub.groupby("month").apply(
        lambda g: np.average(g[retcol], weights=g["w"]), include_groups=False)
    # per-trade weighted mean (the honest per-trade figure, not month-averaged)
    ptw = np.average(sub[retcol], weights=sub["w"])
    return ptw, mon, len(sub)


def run():
    log = []
    def P(*a):
        s = " ".join(str(x) for x in a); print(s); log.append(s)

    ff = load()
    lc, lc_syms = large_cap(ff)
    P("=" * 78)
    P("S-03 FF-CALENDAR INCREMENTAL SHUFFLE (D-M2) — LARGE-CAP GATE")
    P("=" * 78)
    P(f"full universe rows {len(ff)} | large-cap (pre-2024 options) symbols {len(lc_syms)} rows {len(lc)}")
    slice_lc = lc[lc["ff"] >= FF_MIN]
    P(f"large-cap FF>=0.25 slice: {len(slice_lc)} trades, {slice_lc['sym'].nunique()} symbols  [DATA]")

    # ---- BASE: actual FF selection ----
    base_ptw, base_mon, base_n = wmean_monthly(lc, "ff")
    P(f"\nBASE (actual FF selection, FF>=0.25, tier-sized):")
    P(f"  per-trade weighted mean ret = {base_ptw:+.4%}  (n={base_n})")
    P(f"  monthly-mean of monthly-wmean = {base_mon.mean():+.4%}  over {len(base_mon)} months")

    # ---- (b) per-year + build/forward ----
    P("\n" + "-" * 78)
    P("(b) PER-YEAR + BUILD/FORWARD  (large-cap FF>=0.25 slice)")
    P("-" * 78)
    s = slice_lc.copy(); s["w"] = s["ff"].apply(tierw); s["yr"] = s["m1_exp"].dt.year
    P(f"  {'year':>6} {'n':>5} {'wmean':>9} {'hit':>6} {'med':>9}")
    for yr, g in s.groupby("yr"):
        wm = np.average(g["ret"], weights=g["w"])
        P(f"  {yr:>6} {len(g):>5} {wm:>+9.3%} {(g['ret']>0).mean():>6.0%} {g['ret'].median():>+9.3%}")
    b = s[s["entry"] <= SPLIT]; f = s[s["entry"] > SPLIT]
    bwm = np.average(b["ret"], weights=b["w"]) if len(b) else np.nan
    fwm = np.average(f["ret"], weights=f["w"]) if len(f) else np.nan
    P(f"  BUILD  (entry<=2024-12-31): n={len(b):>4} wmean {bwm:+.3%} hit {(b['ret']>0).mean():.0%}")
    P(f"  FWD    (entry> 2024-12-31): n={len(f):>4} wmean {fwm:+.3%} hit {(f['ret']>0).mean():.0%}")

    # ---- degenerate: concentration ----
    P("\n" + "-" * 78)
    P("DEGENERATE CHECKS (large-cap FF>=0.25 slice)")
    P("-" * 78)
    sym_pnl = (s["ret"] * s["w"]).groupby(s["sym"]).sum()
    top_sym = sym_pnl.abs().idxmax(); top_frac = sym_pnl.abs().max() / (sym_pnl.abs().sum() + 1e-12)
    P(f"  top symbol {top_sym}: {top_frac:.0%} of |weighted P&L|  {'FLAG >30%' if top_frac>0.30 else 'ok'}")
    contrib = (s["ret"] * s["w"])
    top5 = contrib.nlargest(5).sum(); rest = contrib.sum() - top5
    P(f"  sum contrib {contrib.sum():+.3f} | without top-5 = {rest:+.3f}  {'FLAG neg w/o top5' if rest<0 else 'ok'}")

    # ---- (a) NULLS via shuffle ----
    P("\n" + "-" * 78)
    P("(a) INCREMENTAL SHUFFLE — does FF SELECTION beat random calendar entry?")
    P("-" * 78)

    ff_vals = lc["ff"].to_numpy(float)
    ret_vals = lc["ret"].to_numpy(float)
    # month group index arrays (precompute once)
    month_codes = lc["month"].astype("category").cat.codes.to_numpy()
    month_idx = [np.where(month_codes == m)[0] for m in np.unique(month_codes)]

    # N1: within-month FF permutation (vectorized: permute FF within each month group)
    n1 = np.empty(NSH)
    for i in range(NSH):
        shuf = ff_vals.copy()
        for idx in month_idx:
            if idx.size > 1:
                shuf[idx] = shuf[RNG.permutation(idx)]
        n1[i] = ptw_fast(shuf, ret_vals)
    n1 = n1[np.isfinite(n1)]

    # N2: global FF permutation
    n2 = np.empty(NSH)
    for i in range(NSH):
        n2[i] = ptw_fast(RNG.permutation(ff_vals), ret_vals)
    n2 = n2[np.isfinite(n2)]

    # N3: random calendar entry (ignore FF entirely) — random trade per (sym,month), EW, no filter
    sm_codes = (lc["sym"].astype(str) + "|" + lc["month"].astype(str)).astype("category").cat.codes.to_numpy()
    sm_idx = [np.where(sm_codes == g)[0] for g in np.unique(sm_codes)]
    n3 = np.empty(NSH)
    for i in range(NSH):
        picks = np.array([ret_vals[idx[RNG.integers(idx.size)]] for idx in sm_idx])
        n3[i] = picks.mean()   # equal-weight random entry, no FF filter
    n3 = n3[np.isfinite(n3)]

    def report_null(name, null, base):
        p = (null >= base).mean()   # one-sided: prob null >= actual
        inc = base - null.mean()
        P(f"  {name:32s} null mean {null.mean():+.4%} sd {null.std():.4%} | "
          f"incremental {inc:+.4%} | p(null>=actual)={p:.3f}  {'ADD' if p<0.05 else 'NO-ADD'}")
        return {"name": name, "null_mean": float(null.mean()), "null_sd": float(null.std()),
                "incremental": float(inc), "p_value": float(p), "adds": bool(p < 0.05),
                "n_shuffles": int(len(null))}

    P(f"\n  BASE per-trade weighted mean (actual FF) = {base_ptw:+.4%}")
    res = []
    res.append(report_null("N1 within-month FF shuffle", n1, base_ptw))
    res.append(report_null("N2 global FF shuffle", n2, base_ptw))
    res.append(report_null("N3 random-entry (no FF filter)", n3, base_ptw))

    # ---- verdict logic vs pre-registered kills ----
    P("\n" + "=" * 78)
    P("VERDICT vs PRE-REGISTERED KILLS")
    P("=" * 78)
    k1 = res[0]["adds"]   # within-month selection adds (the key incremental test)
    k2 = not (bwm <= 0 and fwm <= 0)
    k3 = fwm > 0
    k4 = (top_frac <= 0.30) and (rest >= 0)
    P(f"  K1 FF within-month selection adds (p<0.05):     {'PASS' if k1 else 'KILL'}  (p={res[0]['p_value']:.3f})")
    P(f"  K2 base edge not negative both build&fwd:        {'PASS' if k2 else 'KILL'}  (build {bwm:+.3%} fwd {fwm:+.3%})")
    P(f"  K3 forward (2025-26) mean > 0:                   {'PASS' if k3 else 'KILL'}  (fwd {fwm:+.3%})")
    P(f"  K4 no P&L concentration:                         {'PASS' if k4 else 'FLAG'}")

    cfg = {"universe": "large-cap (pre-2024 option data)", "n_symbols": len(lc_syms),
           "slice_rows": int(len(slice_lc)), "ff_min": FF_MIN, "slip": SLIP, "n_shuffles": NSH,
           "base_per_trade_wmean": float(base_ptw), "base_n": int(base_n),
           "build_wmean": float(bwm), "fwd_wmean": float(fwm),
           "top_symbol": str(top_sym), "top_symbol_frac_pnl": float(top_frac),
           "neg_without_top5": bool(rest < 0),
           "nulls": res,
           "kills": {"K1_selection_adds": bool(k1), "K2_not_neg_both": bool(k2),
                     "K3_fwd_positive": bool(k3), "K4_no_concentration": bool(k4)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    (OUT / "shuffle_raw.txt").write_text("\n".join(log), encoding="utf-8")
    np.savez(OUT / "null_distributions.npz", n1=n1, n2=n2, n3=n3, base=base_ptw)
    print("\nsaved config.json, shuffle_raw.txt, null_distributions.npz ->", OUT)
    return cfg


if __name__ == "__main__":
    run()
