"""Report layer for gated_buying.py. Reads trades.parquet — the 36,061 simulated legs — and scores
the cells. Split out because pathsafe.summarize() correctly REFUSED a duck-typed stand-in for
ExitResult, which is the guard behaving as designed; real ExitResult objects are rebuilt here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathsafe import ExitResult, summarize      # noqa: E402

OUT = Path(__file__).parent
HELDOUT = pd.Timestamp("2026-01-01")
STRIKES = ["delta0.60", "itm100", "itm50"]
STOPS = [10, 15, 20, 25]

T = pd.read_parquet(OUT / "trades.parquet")
T["day"] = pd.to_datetime(T["day"])
print(f"[load] {len(T):,} legs  {T.day.min().date()} .. {T.day.max().date()}")
print(f"       triggers {T.trig.value_counts().to_dict()}")
print(f"       measured delta by rule:")
print(T.groupby("strike_rule").delta.describe()[["count", "mean", "50%", "min", "max"]]
      .round(3).to_string())

# IV/RV state, trailing expanding tercile, PIT (shift(1) so the day itself never sets its own bucket)
iv = T.groupby("day").ivrv.first().sort_index().to_frame()
iv["lo"] = iv.ivrv.expanding(120).quantile(1 / 3).shift(1)
iv["hi"] = iv.ivrv.expanding(120).quantile(2 / 3).shift(1)
T = T.merge(iv[["lo", "hi"]], left_on="day", right_index=True, how="left")
T["ivstate"] = np.where(T.ivrv <= T.lo, "CHEAP", np.where(T.ivrv >= T.hi, "RICH", "MID"))
T.loc[T.lo.isna(), "ivstate"] = "n/a"
print(f"       iv-state {T.ivstate.value_counts().to_dict()}")

rep = []


def block(sub, lbl):
    if len(sub) < 40:
        return
    s = summarize([ExitResult(float(a), float(b), "", "", 0, 1)
                   for a, b in zip(sub.pnl_p, sub.pnl_o)], verbose=False)
    hit = float((sub.why == "target").mean())
    wins, loss = sub[sub.pnl_p > 0].pnl_p, sub[sub.pnl_p <= 0].pnl_p
    pf = float(wins.sum() / abs(loss.sum())) if loss.sum() else np.nan
    dd = sub.groupby("ds").pnl_p.sum()
    eq = dd.cumsum()
    mdd = float((eq - eq.cummax()).min())
    yrs = max((sub.day.max() - sub.day.min()).days / 365.25, .05)
    ppy = sub.pnl_p.sum() / yrs
    tst = float(dd.mean() / dd.std() * np.sqrt(len(dd))) if dd.std() > 0 else np.nan
    rep.append(dict(cell=lbl, n=len(sub), hit_target=round(hit, 4),
                    mean_pess=round(float(sub.pnl_p.mean()), 3),
                    median_pess=round(float(sub.pnl_p.median()), 3),
                    mean_opt=round(float(sub.pnl_o.mean()), 3),
                    spread_frac=round(s.spread_frac, 3), reliable=bool(s.reliable),
                    win_rate=round(float((sub.pnl_p > 0).mean()), 4),
                    PF=round(pf, 3) if np.isfinite(pf) else None,
                    pts_per_yr=round(ppy, 1), maxDD=round(mdd, 1),
                    Calmar=round(ppy / abs(mdd), 3) if mdd else None, t_day=round(tst, 2)))
    print(f"{lbl:<42}{len(sub):>6}{hit:>8.1%}{sub.pnl_p.mean():>9.2f}{sub.pnl_p.median():>8.2f}"
          f"{float((sub.pnl_p > 0).mean()):>8.1%}{(pf if np.isfinite(pf) else 0):>7.2f}"
          f"{ppy:>9.1f}{mdd:>9.1f}{(ppy / abs(mdd) if mdd else 0):>8.3f}{tst:>7.2f}"
          f"{'  OK' if s.reliable else '  *AMBIG*'}")


hdr = (f"{'cell':<42}{'n':>6}{'hit%':>8}{'mean':>9}{'med':>8}{'win%':>8}{'PF':>7}"
       f"{'pts/yr':>9}{'maxDD':>9}{'Calmar':>8}{'t':>7}")
for tag, D in (("IS", T[T.day < HELDOUT]), ("HO", T[T.day >= HELDOUT])):
    ttl = "IN-SAMPLE 2021-2025" if tag == "IS" else "HELD-OUT 2026"
    print("\n" + "=" * 130)
    print(f"{ttl}   RR fixed 1:1.5 (target = 1.5 x stop).   BREAKEVEN HIT RATE = 40.0%   "
          f"cost {0.385 * 2 + 0.5 * 2:.2f} prem pts rt")
    print("=" * 130); print(hdr); print("-" * 130)
    for trig in ("A6", "C1", "C2"):
        for sr in STRIKES:
            for st in STOPS:
                block(D[(D.trig == trig) & (D.strike_rule == sr) & (D.stop == st)],
                      f"{tag} {trig} {sr} stop{st}")
    print("-" * 130)
    print("  IV-STATE SPLIT (the B2 gate). RICH is the CONTROL: if RICH ~ CHEAP, B2 added nothing.")
    print("-" * 130)
    for st_ in ("CHEAP", "MID", "RICH"):
        for sr in STRIKES:
            block(D[(D.ivstate == st_) & (D.strike_rule == sr) & (D.stop == 15)],
                  f"{tag} IV={st_} {sr} stop15 allTrig")

R = pd.DataFrame(rep)
R.to_csv(OUT / "cells.csv", index=False)
print(f"\n[cells] {len(R)} scored -> cells.csv")
pos = R[(R.mean_pess > 0) & (R.n >= 100)]
print(f"[cells] with POSITIVE pessimistic mean and n>=100: {len(pos)} of {len(R)}")
if len(pos):
    print(pos.sort_values("mean_pess", ascending=False)
          [["cell", "n", "hit_target", "mean_pess", "win_rate", "PF", "Calmar", "t_day"]]
          .to_string(index=False))
best_hit = R[R.n >= 200].sort_values("hit_target", ascending=False).head(8)
print("\n[hit rate] best 8 cells with n>=200 (40.0% is breakeven at RR 1:1.5):")
print(best_hit[["cell", "n", "hit_target", "mean_pess", "PF"]].to_string(index=False))
print(f"\n[ambiguity] cells flagged unreliable by pathsafe: "
      f"{int((~R.reliable).sum())} of {len(R)}")
