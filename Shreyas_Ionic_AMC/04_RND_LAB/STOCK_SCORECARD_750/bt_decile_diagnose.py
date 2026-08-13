# -*- coding: utf-8 -*-
"""bt_decile_diagnose.py - WHY is the decile curve U-shaped? (Principal question, 2026-08-05)

The rolling study (35 formations, 14,943 observations) confirmed the shape is not an outlier
artefact: deciles 2-3 and 8-10 earn well, deciles 4-7 earn least apart from decile 1. His two
hypotheses, to be tested rather than assumed:

  H1  deciles 2-3 do well because the bad news is already in the price and they mean-revert
      upward - cheap, beaten-down names bouncing.
  H2  deciles 5-6 do badly because they are overvalued.

A third hypothesis has to be on the list because the composite is an AVERAGE of seven pillars, and
an average can reach the middle two completely different ways:

  H3  the middle is "mediocre on everything" while the flanks are "extreme on something". A stock
      scoring 48 by being uniformly average is a different animal from one scoring 48 by being
      cheap-and-broken or expensive-and-surging. If so, the middle deciles have no ACTIVE bet in
      them, and low dispersion across pillars is the signature.

  H4  the window was a small-cap and low-quality melt-up: equal-weight universe +69.8% against
      Nifty 500 +40.6% over Mar-2023 to Mar-2026. If deciles 2-3 are simply smaller and higher-beta,
      the "mean reversion" story is really a size-and-beta story.

WHAT IS MEASURED PER DECILE
  value / quality / growth / stage pillar means   -> tests H1 (cheap+beaten) and H2 (expensive)
  within-stock pillar dispersion (max - min)      -> tests H3 (mediocre-on-everything)
  median 60-day turnover                          -> size proxy, tests H4
  forward-return dispersion                       -> beta/risk proxy, tests H4
  gate drag (final - composite_3y)                -> how much the gate layer moved each decile
  sector mix                                      -> whether a flank is one crowded trade

Several formations are pooled so the answer is not one window's accident.
Outputs -> results/DECILE_DIAG_20260805/
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt_pit_quant as B                                              # noqa: E402

OUT = os.path.join(HERE, "results", "DECILE_DIAG_20260805")
os.makedirs(OUT, exist_ok=True)

NDEC = 10
PILL = ["quality", "growth", "value", "stage"]
# spread across the window so the answer is not one regime; each gets a 12m forward leg
FORMATIONS = ["2023-03-31", "2023-09-30", "2024-03-31", "2024-09-30", "2025-03-31"]


def fwd(pxm, sym, e0, e1):
    if sym not in pxm.columns:
        return np.nan
    a, b = pxm[sym].asof(e0), pxm[sym].asof(e1)
    if pd.isna(a) or pd.isna(b) or a <= 0:
        return np.nan
    return b / a - 1


def main():
    print("loading ...")
    fund, mem, sh, sect, pxm, vol, idx = B.load()

    frames = []
    for t_str in FORMATIONS:
        t = pd.Timestamp(t_str)
        sc = B.score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or sc.empty:
            print(f"  {t_str}: no scores"); continue
        e0 = B.next_session(pxm, t)
        e1 = pxm.index[pxm.index <= t + pd.DateOffset(months=12)].max()
        if e0 is None or pd.isna(e1):
            continue
        sc = sc.copy()
        sc["fwd"] = [fwd(pxm, s, e0, e1) for s in sc["sym"]]
        # size proxy: median 60-day traded value at formation
        tv = []
        for s in sc["sym"]:
            v = vol.get(s)
            tv.append(float(v.loc[:t].tail(60).median()) if v is not None else np.nan)
        sc["turnover"] = tv
        sc = sc.dropna(subset=["fwd"])
        sc["formation"] = t_str
        sc["dec"] = pd.qcut(sc["final"].rank(method="first"), NDEC,
                            labels=range(1, NDEC + 1)).astype(int)
        # within-stock pillar dispersion: high = an extreme bet, low = uniformly average
        sc["pill_spread"] = sc[PILL].max(axis=1) - sc[PILL].min(axis=1)
        sc["gate_drag"] = sc["final"] - sc["composite_3y"]
        frames.append(sc)
        print(f"  {t_str}: n={len(sc)}")

    d = pd.concat(frames, ignore_index=True)
    d.to_csv(os.path.join(OUT, "diag_detail.csv"), index=False)
    print(f"\npooled: {len(d)} observations across {d['formation'].nunique()} formations")

    g = d.groupby("dec", observed=True)
    tab = pd.DataFrame({
        "n": g.size(),
        "fwd_trim5": g["fwd"].apply(lambda x: _trim(x) * 100).round(1),
        "value": g["value"].mean().round(1),
        "quality": g["quality"].mean().round(1),
        "growth": g["growth"].mean().round(1),
        "stage": g["stage"].mean().round(1),
        "pill_spread": g["pill_spread"].mean().round(1),
        "gate_drag": g["gate_drag"].mean().round(2),
        "turnover_cr": (g["turnover"].median() / 1e7).round(1),
        "fwd_sd": (g["fwd"].std() * 100).round(1),
    })
    print("\n=== DECILE DECOMPOSITION (pooled) ===")
    print(tab.to_string())
    tab.to_csv(os.path.join(OUT, "decomposition.csv"))

    print("\n=== hypothesis read-out ===")
    lo, mid, hi = tab.loc[2:3], tab.loc[4:7], tab.loc[8:10]
    print(f"H1  D2-3 cheap and beaten?    value {lo['value'].mean():.1f} vs mid "
          f"{mid['value'].mean():.1f} vs D8-10 {hi['value'].mean():.1f}   |   "
          f"stage {lo['stage'].mean():.1f} vs {mid['stage'].mean():.1f} vs {hi['stage'].mean():.1f}")
    print(f"H2  D5-6 overvalued?          value D5-6 {tab.loc[5:6,'value'].mean():.1f} "
          f"(universe mean {d['value'].mean():.1f})")
    print(f"H3  middle mediocre?          pillar spread D4-7 {mid['pill_spread'].mean():.1f} vs "
          f"D2-3 {lo['pill_spread'].mean():.1f} vs D8-10 {hi['pill_spread'].mean():.1f}")
    print(f"H4  size/beta?                turnover D2-3 {lo['turnover_cr'].mean():.1f}cr vs mid "
          f"{mid['turnover_cr'].mean():.1f}cr vs D8-10 {hi['turnover_cr'].mean():.1f}cr   |   "
          f"fwd SD {lo['fwd_sd'].mean():.0f} vs {mid['fwd_sd'].mean():.0f} vs {hi['fwd_sd'].mean():.0f}")
    print(f"    gate drag: D2-3 {lo['gate_drag'].mean():+.2f}  D4-7 {mid['gate_drag'].mean():+.2f}  "
          f"D8-10 {hi['gate_drag'].mean():+.2f}")

    print("\n=== top 3 sectors per decile band ===")
    for name, sl in (("D2-3", (2, 3)), ("D4-7", (4, 7)), ("D8-10", (8, 10))):
        sub = d[(d["dec"] >= sl[0]) & (d["dec"] <= sl[1])]
        vc = (sub["sector"].value_counts(normalize=True) * 100).head(3)
        print(f"  {name}: " + ", ".join(f"{k} {v:.0f}%" for k, v in vc.items()))


def _trim(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


if __name__ == "__main__":
    main()
