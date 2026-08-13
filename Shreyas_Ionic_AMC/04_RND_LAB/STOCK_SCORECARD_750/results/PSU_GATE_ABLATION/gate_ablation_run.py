# -*- coding: utf-8 -*-
"""gate_ablation_run.py - TEST 2: gate-layer ablation, one mechanism at a time.
Nikhil Bose, red team, 2026-08-06.

Uses abl_scorer.py (a verified byte-identical COPY of bt_pit_quant.score_asof when all gates are
ON -- checked separately: max abs diff 0.0 on final AND composite_3y for a real formation date).
Never imports or edits the live bt_pit_quant.py's gate code; only abl_scorer's GATE_CFG changes.

SAME 35 formations as bt_decile_rolling.py (2022-08-31 .. 2025-06-30, 12m hold, same
MIN_HIST_SESSIONS=260 rule) so V0-V3 are apples-to-apples with the Principal's banked headline.

Variants:
  V0  full model (control)                          red_cap=T amber_mult=T penalty=T boost=T
  V1  penalty and boost OFF                         red_cap=T amber_mult=T penalty=F boost=F
  V2  amber multiplier OFF                           red_cap=T amber_mult=F penalty=T boost=T
  V3  red cap OFF                                    red_cap=F amber_mult=T penalty=T boost=T

Banks per (variant, formation) as it goes -- a long run that dies mid-way loses nothing; reruns
skip already-banked rows.
"""
import os
import sys
import time
import json

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SC750 = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, SC750)
import abl_scorer as ABL                                              # noqa: E402

OUT = HERE
NDEC = 10
HOLD_MONTHS = 12
MIN_HIST_SESSIONS = 260

VARIANTS = {
    "V0_full_model":       dict(red_cap=True,  amber_mult=True,  penalty=True,  boost=True),
    "V1_no_penalty_boost": dict(red_cap=True,  amber_mult=True,  penalty=False, boost=False),
    "V2_no_amber":         dict(red_cap=True,  amber_mult=False, penalty=True,  boost=True),
    "V3_no_red_cap":       dict(red_cap=False, amber_mult=True,  penalty=True,  boost=True),
}


def trimmed_mean(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    if len(a) == 0:
        return np.nan
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def fwd(pxm, sym, e0, e1):
    if sym not in pxm.columns:
        return np.nan
    a, b = pxm[sym].asof(e0), pxm[sym].asof(e1)
    if pd.isna(a) or pd.isna(b) or a <= 0:
        return np.nan
    return b / a - 1


def formations(pxm):
    first_ok = pxm.index[MIN_HIST_SESSIONS - 1]
    last_ok = pxm.index.max() - pd.DateOffset(months=HOLD_MONTHS)
    me = pd.date_range(first_ok, last_ok, freq="ME")
    return [d for d in me if d >= first_ok and d <= last_ok]


def run_variant(vname, cfg, fund, mem, sh, sect, pxm, vol):
    ABL.GATE_CFG.clear()
    ABL.GATE_CFG.update(cfg)
    obs_path = os.path.join(OUT, f"observations_{vname}.csv")
    fdates = formations(pxm)

    done = set()
    if os.path.exists(obs_path):
        prev = pd.read_csv(obs_path)
        done = set(prev["formation"].unique())
        print(f"  [{vname}] resuming: {len(done)}/{len(fdates)} formations already banked")

    t0 = time.time()
    for i, t in enumerate(fdates):
        key = str(t.date())
        if key in done:
            continue
        sc = ABL.score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or sc.empty:
            print(f"  [{vname}] {key}: scorer returned nothing, skipped")
            continue
        e0 = ABL.next_session(pxm, t)
        end = t + pd.DateOffset(months=HOLD_MONTHS)
        e1 = pxm.index[pxm.index <= end].max()
        if e0 is None or pd.isna(e1) or e1 <= e0:
            continue
        sc = sc.copy()
        sc["fwd"] = [fwd(pxm, s, e0, e1) for s in sc["sym"]]
        sc = sc.dropna(subset=["fwd"])
        if len(sc) < 100:
            print(f"  [{vname}] {key}: only {len(sc)} scored+priced names, skipped")
            continue
        sc["formation"] = key
        sc["dec_final"] = pd.qcut(sc["final"].rank(method="first"), NDEC,
                                   labels=range(1, NDEC + 1)).astype(int)
        keep = ["formation", "sym", "final", "composite_3y", "fwd", "dec_final",
                "red_flag", "amber_flag", "n_penalty_flags"]
        sc[keep].to_csv(obs_path, mode="a", header=not os.path.exists(obs_path), index=False)
        if (i + 1) % 10 == 0 or i == len(fdates) - 1:
            print(f"  [{vname}] {key} ({i+1}/{len(fdates)})  n={len(sc)}  "
                  f"elapsed={time.time()-t0:.0f}s")

    obs = pd.read_csv(obs_path)
    g = obs.groupby("dec_final", observed=True)["fwd"]
    tab = pd.DataFrame({"n": g.size(), "trim5": (g.apply(lambda x: trimmed_mean(x, 0.05)) * 100).round(2)})
    per = []
    for f, sub in obs.groupby("formation"):
        a = sub[sub["dec_final"] == 1]["fwd"]; b = sub[sub["dec_final"] == NDEC]["fwd"]
        if len(a) and len(b):
            per.append(dict(formation=f, spread=(trimmed_mean(b) - trimmed_mean(a)) * 100))
    per = pd.DataFrame(per)
    ic = obs[["final", "fwd"]].corr(method="spearman").iloc[0, 1]
    summary = dict(
        variant=vname, cfg=cfg, pooled_n=int(len(obs)), formations=int(obs["formation"].nunique()),
        d1_trim5=float(tab.loc[1, "trim5"]), d10_trim5=float(tab.loc[NDEC, "trim5"]),
        spread_trim5_pp=round(float(tab.loc[NDEC, "trim5"] - tab.loc[1, "trim5"]), 2),
        spearman_ic=round(float(ic), 4),
        formations_d10_beat_d1=int((per["spread"] > 0).sum()), formations_total=int(len(per)),
        hit_rate_pct=round(float((per["spread"] > 0).mean() * 100), 1),
        median_formation_spread_pp=round(float(per["spread"].median()), 2),
        worst_formation_spread_pp=round(float(per["spread"].min()), 2),
        pct_red_flagged=round(float(obs["red_flag"].mean() * 100), 2),
        pct_amber_flagged=round(float(obs["amber_flag"].mean() * 100), 2),
    )
    per.to_csv(os.path.join(OUT, f"per_formation_{vname}.csv"), index=False)
    print(f"\n[{vname}] D10-D1(trim5)={summary['spread_trim5_pp']:+.2f}pp  IC={summary['spearman_ic']:+.4f}  "
          f"hit={summary['hit_rate_pct']}%  worst={summary['worst_formation_spread_pp']:+.2f}pp  "
          f"red%={summary['pct_red_flagged']}  amber%={summary['pct_amber_flagged']}")
    return summary


def main():
    print("loading PIT panels and prices (shared across all 4 variants, ~6 min) ...")
    t0 = time.time()
    fund, mem, sh, sect, pxm, vol, idx = ABL.load()
    print(f"  loaded in {time.time()-t0:.0f}s  prices: {pxm.shape[1]} symbols, "
          f"{pxm.index.min().date()} to {pxm.index.max().date()}")
    fd = formations(pxm)
    print(f"  formations: {len(fd)}  ({fd[0].date()} .. {fd[-1].date()})")

    summaries = []
    for vname, cfg in VARIANTS.items():
        print(f"\n{'='*80}\nrunning {vname}  cfg={cfg}")
        summaries.append(run_variant(vname, cfg, fund, mem, sh, sect, pxm, vol))
        with open(os.path.join(OUT, "ablation_summary.json"), "w") as f:
            json.dump(summaries, f, indent=2)   # checkpoint after EVERY variant

    print(f"\n\n{'='*80}\n=== FINAL: all 4 variants, same 35 formations ===")
    df = pd.DataFrame(summaries)
    cols = ["variant", "d1_trim5", "d10_trim5", "spread_trim5_pp", "spearman_ic",
            "hit_rate_pct", "worst_formation_spread_pp", "pct_red_flagged", "pct_amber_flagged"]
    print(df[cols].to_string(index=False))
    df[cols].to_csv(os.path.join(OUT, "ablation_summary.csv"), index=False)
    print("\nwrote", os.path.join(OUT, "ablation_summary.csv"))


if __name__ == "__main__":
    main()
