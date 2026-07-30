"""DIRECTION-COMMITTED economic null — removes the best-of-both-sides credit from H4.

THE DEFECT THIS FIXES, IN MY OWN RESULT:
  regime_ml.py labelled a window `tradeable` as `winnable(long) OR winnable(short)`. The economic
  null then paid +1.5k whenever EITHER side would have worked. That silently credits a perfect
  direction choice the model never made. The headline "declining 50% turns -0.0589 into +0.0089"
  is therefore an UPPER BOUND, not a result.
  A real buyer must commit to CE or PE before the window opens.

WHAT THIS RUNS INSTEAD
  Three direction rules, each strictly PIT, each committed BEFORE the forward window:
    DIR_vwap   side = sign(close - session VWAP)          (A6's logic, the best-distributed trigger)
    DIR_trend  side = sign(close - prior close)           (crude momentum)
    DIR_coin   side = deterministic alternation            (a placebo direction: if the gate looks
                                                            good here too, the gate is timing vol,
                                                            not picking winners)
  For each, the payoff is the 1:1.5 harvest on THAT side only, resolved ADVERSELY inside every bar.
  Then the same random-decline null as before: does gating on H4 beat declining the same fraction
  at random? 1000 draws. Held-out slice reported separately.

The ML is NOT refitted. H4's out-of-sample probabilities are joined from oos_predictions.parquet by
timestamp, so nothing here can leak a fitting decision into the test.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
OUT = Path(__file__).parent
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
FWD_MIN, BUCKET, K_ATR = 120, 15, 0.25
ENTRY_LO, ENTRY_HI = "09:30", "13:15"
HELDOUT = pd.Timestamp("2025-07-01")

print("[load] index", flush=True)
px = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
px = px[(px.index.time >= pd.Timestamp("09:15").time()) &
        (px.index.time <= pd.Timestamp("15:30").time())]
px["d"] = px.index.normalize()
dly = px.groupby("d").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr20"] = tr.rolling(20, min_periods=10).mean()
dly["pc"] = dly.c.shift()

lo_t, hi_t = pd.Timestamp(ENTRY_LO).time(), pd.Timestamp(ENTRY_HI).time()
rows = []
flip = 0
for d, g in px.groupby("d"):
    if d not in dly.index or not np.isfinite(dly.at[d, "atr20"]) or dly.at[d, "atr20"] <= 0:
        continue
    atr, pc = float(dly.at[d, "atr20"]), dly.at[d, "pc"]
    c = g["close"].to_numpy(float); h = g["high"].to_numpy(float); lw = g["low"].to_numpy(float)
    ts = g.index; n = len(c)
    if n < 200:
        continue
    tp = (h + lw + c) / 3.0
    vwap = np.cumsum(tp) / np.arange(1, n + 1)
    tgt, stp = 1.5 * K_ATR * atr, 1.0 * K_ATR * atr
    for i in range(n):
        if not (lo_t <= ts[i].time() <= hi_t) or ts[i].minute % BUCKET != 0:
            continue
        j = i + FWD_MIN
        if j >= n:
            continue
        fc, fh, flw = c[i:j + 1], h[i:j + 1], lw[i:j + 1]

        def harvest(sign):
            """1:1.5 outcome on ONE committed side. Adverse-first inside every bar."""
            for k in range(1, len(fc)):
                adv = (flw[k] - fc[0]) if sign > 0 else (fc[0] - fh[k])
                fav = (fh[k] - fc[0]) if sign > 0 else (fc[0] - flw[k])
                if adv <= -stp:
                    return -1.0 * K_ATR
                if fav >= tgt:
                    return 1.5 * K_ATR
            return float(sign * (fc[-1] - fc[0])) / atr      # timeout at the mark

        flip += 1
        rows.append(dict(
            t=ts[i],
            pay_vwap=harvest(1 if c[i] > vwap[i] else -1),
            pay_trend=harvest(1 if (np.isfinite(pc) and c[i] > pc) else -1),
            pay_coin=harvest(1 if flip % 2 == 0 else -1),
            pay_bestof=max(harvest(1), harvest(-1)),
        ))

E = pd.DataFrame(rows).set_index("t").sort_index()
P = pd.read_parquet(OUT / "oos_predictions.parquet")
E = E.join(P[["p_H4_tradeable"]], how="inner").dropna(subset=["p_H4_tradeable"])
print(f"[join] {len(E):,} windows with an out-of-sample H4 probability", flush=True)

ARMS = [("DIR_vwap  (A6 logic)", "pay_vwap"), ("DIR_trend (vs prior close)", "pay_trend"),
        ("DIR_coin  (PLACEBO dir)", "pay_coin"), ("BEST-OF-BOTH (upper bound)", "pay_bestof")]
FRACS = (0.0, 0.3, 0.5, 0.6, 0.7, 0.8)
rep = []
for tag, mask in (("ALL 2015-2026", np.ones(len(E), bool)),
                  (f"HELD OUT from {HELDOUT.date()}", np.asarray(E.index >= HELDOUT))):
    sub = E[mask]
    if len(sub) < 500:
        continue
    print("\n" + "=" * 118)
    print(f"{tag}   n={len(sub):,}   payoff in ATR units, 1:1.5 harvest, adverse-first")
    print("=" * 118)
    print(f"{'arm':<28}{'decline':>9}{'n kept':>9}{'gated':>10}{'random':>10}"
          f"{'rand p95':>10}{'p':>8}{'verdict':>13}", flush=True)
    for name, col in ARMS:
        pay, pp = sub[col], sub.p_H4_tradeable
        for f in FRACS:
            if f == 0:
                print(f"{name:<28}{'all':>9}{len(pay):>9}{pay.mean():>10.4f}"
                      f"{'-':>10}{'-':>10}{'-':>8}{'baseline':>13}", flush=True)
                rep.append(dict(slice=tag, arm=name, decline=0.0, n=len(pay),
                                gated=round(float(pay.mean()), 5), verdict="baseline"))
                continue
            thr = np.quantile(pp, f)
            keep = pp >= thr
            nk = int(keep.sum())
            if nk < 200:
                continue
            gm = float(pay[keep].mean())
            dr = np.array([pay.sample(nk, random_state=int(s), replace=False).mean()
                           for s in range(1000)])
            pv = float((dr >= gm).mean())
            v = "BEATS NULL" if pv < 0.05 else ("weak" if pv < 0.20 else "NO EDGE")
            rep.append(dict(slice=tag, arm=name, decline=f, n=nk, gated=round(gm, 5),
                            random=round(float(dr.mean()), 5), p_value=pv, verdict=v))
            print(f"{'':<28}{f:>9.0%}{nk:>9}{gm:>10.4f}{dr.mean():>10.4f}"
                  f"{np.quantile(dr, .95):>10.4f}{pv:>8.3f}{v:>13}", flush=True)

pd.DataFrame(rep).to_csv(OUT / "direction_committed.csv", index=False)
json.dump(rep, open(OUT / "direction_committed.json", "w"), indent=2, default=str)
print("\nwrote direction_committed.csv/.json", flush=True)
print("\nHOW TO READ THIS: if DIR_coin gains as much as DIR_vwap, the gate is avoiding bad VOLATILITY\n"
      "windows rather than picking winners - still useful, but it is a risk filter, not alpha.\n"
      "And BEST-OF-BOTH minus DIR_vwap is exactly the size of the optimism in my earlier headline.",
      flush=True)
