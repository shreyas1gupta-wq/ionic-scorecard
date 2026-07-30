"""Q1 answered properly: is the signed move actually INCREASING in the number of stacked
conditions k, or is the k-curve noise on a collapsing sample?

Three tests on the BUILD set (spot only, no option pricing needed):
  1. per-k mean / sd / standard error / t   (does any k differ from zero?)
  2. OLS regression of per-signal signed move on k  -> slope + its t
     ("does magnitude increase with the number of conditions" as ONE number)
  3. Welch two-sample test of the top bucket vs the rest, + a bootstrap CI on the top
     bucket, because n=35 is exactly where a big-looking mean means nothing.

Outputs: kcurve_stats.json, kcurve_per_signal.csv
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
SIGDIR = OUT / "signals"
RESULTS = OUT.parent.parent
SB = RESULTS / "EMA_INTRADAY_BUYING_20260729" / "signal_budget"
sys.path.insert(0, str(SB)); sys.path.insert(0, str(SB.parent))
import measure_signal_budget as M                       # noqa: E402

BUILD_END = dt.date(2025, 12, 31)
FAMS = {"stackA": [1, 2, 3, 4], "stackB": [1, 2, 3, 4]}


def welch(a: np.ndarray, b: np.ndarray) -> dict:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return {"t": None, "df": None, "note": "n too small"}
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / na + vb / nb)
    if se == 0:
        return {"t": None, "df": None, "note": "zero variance"}
    t = (a.mean() - b.mean()) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return {"t": round(float(t), 3), "df": round(float(df), 1),
            "mean_a": round(float(a.mean()), 4), "mean_b": round(float(b.mean()), 4)}


def boot_ci(x: np.ndarray, n_boot: int = 10000, seed: int = 7) -> list:
    rng = np.random.default_rng(seed)
    if len(x) < 2:
        return [None, None]
    bs = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]


def main():
    spot = M.load_spot()
    report = {"metric": "signed spot move to 15:25, POINTS, entry = next 1-min bar open "
                        "after the signal bar (no same-bar lookahead)",
              "split": f"BUILD only (<= {BUILD_END})", "families": {}}
    keep = []

    for fam, ks in FAMS.items():
        per_k, pooled = {}, []
        for k in ks:
            p = SIGDIR / f"{fam}_exact{k}.csv"
            if not p.exists():
                continue
            s = pd.read_csv(p, parse_dates=["t"])
            s["date"] = s["t"].dt.date
            s = s[s["date"] <= BUILD_END]
            if s.empty:
                continue
            f = M.forward_stats(spot, s.rename(columns={"direction": "dir"}))
            x = f["reod_pts"].dropna().values
            xp = f["reod_pct"].dropna().values
            per_k[k] = {
                "n": int(len(x)),
                "mean_pts": round(float(x.mean()), 3),
                "sd_pts": round(float(x.std(ddof=1)), 2),
                "se_pts": round(float(x.std(ddof=1) / math.sqrt(len(x))), 3),
                "t_iid": round(float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))), 3),
                "t_nw": round(float(M.nw_tstat(xp)), 3),
                "mean_pct": round(100 * float(xp.mean()), 4),
                "hit": round(float((x > 0).mean()), 4),
                "boot95_mean_pts": boot_ci(x),
            }
            pooled.append(pd.DataFrame({"k": k, "pts": x}))
            d = f[["t", "dir", "reod_pts", "reod_pct"]].copy()
            d["family"], d["k"] = fam, k
            keep.append(d)

        rec = {"per_k": per_k}
        if len(pooled) >= 2:
            allk = pd.concat(pooled, ignore_index=True)
            # --- TEST 2: does magnitude increase with k? OLS slope on the raw signals
            kk, yy = allk["k"].values.astype(float), allk["pts"].values
            kc = kk - kk.mean()
            slope = float((kc * (yy - yy.mean())).sum() / (kc ** 2).sum())
            resid = yy - (yy.mean() + slope * kc)
            s_err = math.sqrt((resid ** 2).sum() / (len(yy) - 2))
            se_slope = s_err / math.sqrt((kc ** 2).sum())
            rec["regression_move_on_k"] = {
                "n": int(len(yy)), "slope_pts_per_condition": round(slope, 3),
                "se": round(se_slope, 3), "t": round(slope / se_slope, 3),
                "interpretation": "t on the slope is THE answer to 'does stacking buy magnitude'",
            }
            top = max(per_k)
            a = allk.loc[allk.k == top, "pts"].values
            b = allk.loc[allk.k != top, "pts"].values
            rec["top_bucket_vs_rest"] = {"top_k": int(top), **welch(a, b)}
            # n-collapse vs magnitude-gain accounting
            k_lo = min(per_k)
            rec["n_collapse_accounting"] = {
                "from_k": int(k_lo), "to_k": int(top),
                "n_shrink_factor": round(per_k[k_lo]["n"] / per_k[top]["n"], 1),
                "magnitude_gain_factor": (round(per_k[top]["mean_pts"] / per_k[k_lo]["mean_pts"], 1)
                                          if per_k[k_lo]["mean_pts"] else None),
                "t_at_lowest_k": per_k[k_lo]["t_iid"], "t_at_highest_k": per_k[top]["t_iid"],
                "max_t_across_k": max(v["t_iid"] for v in per_k.values()),
            }
        report["families"][fam] = rec

    if keep:
        pd.concat(keep, ignore_index=True).to_csv(OUT / "kcurve_per_signal.csv", index=False)
    (OUT / "kcurve_stats.json").write_text(json.dumps(report, indent=2, default=str),
                                           encoding="utf-8")
    for fam, rec in report["families"].items():
        print(f"\n=== {fam} (BUILD, signed pts to 15:25) ===")
        for k, v in rec["per_k"].items():
            print(f"  k={k}  n={v['n']:6d}  mean={v['mean_pts']:+8.2f} pts  se={v['se_pts']:6.2f}"
                  f"  t={v['t_iid']:+6.2f}  t_NW={v['t_nw']:+6.2f}  hit={v['hit']:.3f}"
                  f"  boot95={v['boot95_mean_pts']}")
        r = rec.get("regression_move_on_k")
        if r:
            print(f"  REGRESSION move ~ k : slope {r['slope_pts_per_condition']:+.3f} pts per "
                  f"condition, se {r['se']:.3f}, t={r['t']:+.2f}  (n={r['n']})")
            tv = rec["top_bucket_vs_rest"]
            print(f"  top bucket k={tv['top_k']} vs rest: Welch t={tv['t']} (df={tv['df']})")
            a = rec["n_collapse_accounting"]
            print(f"  n shrinks {a['n_shrink_factor']}x from k={a['from_k']} to k={a['to_k']}; "
                  f"magnitude gain {a['magnitude_gain_factor']}x; max |t| across k = "
                  f"{a['max_t_across_k']}")
    print("\n[done] kcurve_stats.json")


if __name__ == "__main__":
    sys.exit(main())
