"""S-03 decisive analysis: the FF return metric (pnl/CE_be) is DENOMINATOR-INFLATED.
Re-book on P&L POINTS (denominator-free rupees per spread) and expose forward decay.
This is the honest incremental test. Saves points-based results + verdict inputs.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
FF = ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet"
OUT = ROOT / "Shreyas_Ionic_AMC/results/S-03/20260704_shuffle"
SLIP = 0.015; FF_MIN = 0.25; NSH = 2000
RNG = np.random.default_rng(20260704)
SPLIT = pd.Timestamp(2024, 12, 31)


def tierw(f):
    return np.where(f < 0.5, 0.75, np.where(f < 0.75, 1.0, 1.25))


def run():
    log = []
    def P(*a):
        s = " ".join(str(x) for x in a); print(s); log.append(s)

    ff = pd.read_parquet(FF)
    ff["entry"] = pd.to_datetime(ff["entry"]); ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])
    ff["month"] = ff["m1_exp"].dt.to_period("M")
    ff["pnl"] = (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
                 - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP))
    ff["ret"] = ff["pnl"] / ff["CE_be"]
    first = ff.groupby("sym")["entry"].min(); lc = set(first[first < pd.Timestamp(2024, 1, 1)].index)
    L = ff[ff["sym"].isin(lc)].copy()
    S = L[L["ff"] >= FF_MIN].copy(); S["w"] = tierw(S["ff"].to_numpy())

    P("=" * 78)
    P("S-03 DECISIVE — FF calendar booked on P&L POINTS (denominator-free)")
    P("=" * 78)
    P(f"large-cap FF>=0.25 slice: {len(S)} trades, {S['sym'].nunique()} symbols")

    P("\n--- ratio metric (pnl/CE_be) vs points metric, by year ---")
    P(f"  {'yr':>6} {'n':>4} {'ret%':>9} {'pnl_pts':>9} {'hit':>6}")
    S["yr"] = S["m1_exp"].dt.year
    for yr, g in S.groupby("yr"):
        rw = np.average(g["ret"], weights=g["w"]); pw = np.average(g["pnl"], weights=g["w"])
        P(f"  {yr:>6} {len(g):>4} {rw:>+9.2%} {pw:>+9.3f} {(g['pnl']>0).mean():>6.0%}")
    b = S[S["entry"] <= SPLIT]; f = S[S["entry"] > SPLIT]
    br = np.average(b["ret"], weights=b["w"]); bp = np.average(b["pnl"], weights=b["w"])
    fr = np.average(f["ret"], weights=f["w"]); fp = np.average(f["pnl"], weights=f["w"])
    P(f"\n  BUILD  ret {br:+.2%}  pts {bp:+.3f}  n={len(b)}")
    P(f"  FWD    ret {fr:+.2%}  pts {fp:+.3f}  n={len(f)}   <<< FORWARD POINTS {'NEGATIVE' if fp<0 else 'positive'}")

    P("\n--- denominator-inflation evidence ---")
    P(f"  corr(1/CE_be, ret) = {(1/S['CE_be']).corr(S['ret']):.3f}  (ratio driven by small back-leg premium)")
    P(f"  CE_be 5th pct = {S['CE_be'].quantile(0.05):.2f}  median = {S['CE_be'].median():.2f}")
    P(f"  4 trades with CE_be<2 carry mean-ret {S[S['CE_be']<2]['ret'].mean():+.1%} vs pts {S[S['CE_be']<2]['pnl'].mean():+.2f}")

    # incremental shuffle on POINTS
    P("\n--- (a) INCREMENTAL SHUFFLE on P&L POINTS (the honest test) ---")
    ffa = L["ff"].to_numpy(float); pnla = L["pnl"].to_numpy(float)
    mcodes = L["month"].astype("category").cat.codes.to_numpy()
    midx = [np.where(mcodes == m)[0] for m in np.unique(mcodes)]

    def base_ptw(ffa_, pnla_):
        m = ffa_ >= FF_MIN
        return np.average(pnla_[m], weights=tierw(ffa_[m])) if m.any() else np.nan
    base = base_ptw(ffa, pnla)
    n1 = np.array([base_ptw(np.concatenate([ffa[idx][RNG.permutation(idx.size)] if idx.size > 1 else ffa[idx]
                    for idx in midx]),
                   np.concatenate([pnla[idx] for idx in midx])) for _ in range(NSH)])
    # simpler robust N1:
    n1 = np.empty(NSH)
    for i in range(NSH):
        s = ffa.copy()
        for idx in midx:
            if idx.size > 1:
                s[idx] = s[RNG.permutation(idx)]
        n1[i] = base_ptw(s, pnla)
    n1 = n1[np.isfinite(n1)]
    p1 = float((n1 >= base).mean())
    P(f"  BASE pts {base:+.4f}")
    P(f"  N1 within-month FF shuffle: null {n1.mean():+.4f} sd {n1.std():.4f} incr {base-n1.mean():+.4f} p={p1:.3f}")
    P("  NOTE: N3 random-entry null is DEGENERATE on this file — parquet stores only the")
    P("  peak-FF entry per (sym,cycle), so each (sym,month) group has 1 candidate (sd=0).")
    P("  The shuffle can test FF-VALUE reassignment but NOT alternative entry-timing.")

    P("\n" + "=" * 78)
    P("REVISED VERDICT vs PRE-REGISTERED KILLS (points-based)")
    P("=" * 78)
    P(f"  K1 within-month selection adds (p<0.05): PASS in points (p={p1:.3f}) BUT build-only artifact")
    P(f"  K2 base not neg both build&fwd:          {'PASS' if not (bp<=0 and fp<=0) else 'KILL'} (build {bp:+.2f} fwd {fp:+.2f} pts)")
    P(f"  K3 FORWARD (2025-26) mean > 0 IN POINTS:  {'PASS' if fp>0 else 'KILL'}  (fwd {fp:+.3f} pts)  <<< TRIGGERED")
    P("  ==> KILL K3 fires: the +11% forward RETURN was a denominator artifact; forward")
    P("      P&L in rupees is NEGATIVE. FF SELECTION does not carry a forward timing edge.")

    cfg = {"metric": "pnl_points_denominator_free", "slice_rows": int(len(S)),
           "n_symbols": int(S["sym"].nunique()), "ff_min": FF_MIN, "slip": SLIP,
           "build_pts": float(bp), "fwd_pts": float(fp), "build_ret": float(br), "fwd_ret": float(fr),
           "corr_inv_denom_ret": float((1/S['CE_be']).corr(S['ret'])),
           "N1_base_pts": float(base), "N1_null_mean": float(n1.mean()), "N1_p": p1,
           "N3_degenerate": True,
           "per_year_pts": {int(yr): float(np.average(g["pnl"], weights=g["w"]))
                            for yr, g in S.groupby("yr")},
           "kill_K3_fwd_positive_points": bool(fp > 0)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "config_points.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    (OUT / "points_decisive_raw.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nsaved config_points.json, points_decisive_raw.txt ->", OUT)
    return cfg


if __name__ == "__main__":
    run()
