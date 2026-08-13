# -*- coding: utf-8 -*-
"""Is substituting growth_1y for a missing growth_3y right when the cause is a SCHEMA GAP, not thin
history?

Why this needs its own test. The v3 sibling substitution was justified by a backtest of THIN-HISTORY
names, where the 3-year pillar is missing because the company has not existed for 3 years. But it also
fires on banks, where growth_3y is missing for an entirely different reason: the screener P&L carries
'Financing Profit' instead of 'Sales+', so no revenue line exists to compute a 3-year CAGR from. Those
are long-listed, fully-covered companies. Applying a rule validated on one cause to a different cause
is exactly the kind of transfer that quietly breaks things -- and it moves real money here: UNIONBANK
-13.7, J&KBANK -11.0, CANBK -10.5, KTKBANK -12.8 in the v3 run.

TEST. Take fully-covered names, delete ONLY growth_3y (the schema-gap pattern, price history intact),
and compare: skip (engine today), neutral-fill, sibling substitution.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    found = None
    while True:
        p, tail = os.path.split(p)
        if not tail:
            if found:
                return found
            raise RuntimeError("root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand          # keep walking: take the OUTERMOST match, not the first


RES = os.path.join(_root(HERE), "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "GROWTH_SCHEMA_GAP_TEST.md")

BASE = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
            sector_macro_3y_score=11, ownership_3y_score=9, accumulation_3y_score=8)
TC = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
          sector_macro_3y_score=3, ownership_3y_score=0, accumulation_3y_score=0)
TN = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
          sector_macro_3y_score=-2, ownership_3y_score=0, accumulation_3y_score=0)


def w_of(r):
    t = TC if r.get("cyclicality_tag") == "Cyclical" else TN
    return {k: BASE[k] + t[k] for k in BASE}


def sc(v, w):
    num = sum(w[k] * x for k, x in v.items() if x is not None and x == x)
    den = sum(w[k] for k, x in v.items() if x is not None and x == x)
    return num / den if den > 0 else np.nan


d = pd.read_csv(SRC)
P = list(BASE)
full = d[d[P].notna().all(axis=1) & d["growth_1y_score"].notna()].copy()

truth, sk, nu, sib = [], [], [], []
for _, r in full.iterrows():
    w = w_of(r)
    truth.append(sc({k: float(r[k]) for k in P}, w))
    base = {k: float(r[k]) for k in P}; base["growth_3y_score"] = None
    sk.append(sc(base, w))
    b2 = dict(base); b2["growth_3y_score"] = 50.0
    nu.append(sc(b2, w))
    b3 = dict(base); b3["growth_3y_score"] = float(r["growth_1y_score"])
    sib.append(sc(b3, w))

truth = np.array(truth)
lines = ["# growth_3y missing via SCHEMA GAP (not thin history) — which fill is right?", "",
         f"Ground truth: {len(full)} fully-covered names with a usable growth_1y. Only growth_3y "
         f"deleted; all price history intact.", "",
         "| scheme | bias | mean abs err | rank corr | call flips |", "|---|---|---|---|---|"]
for nm, est in (("skip (engine today)", np.array(sk)), ("neutral-fill 50", np.array(nu)),
                ("substitute growth_1y", np.array(sib))):
    ok = ~np.isnan(est) & ~np.isnan(truth)
    bias = (est[ok] - truth[ok]).mean()
    mae = np.abs(est[ok] - truth[ok]).mean()
    rho = pd.Series(est[ok]).corr(pd.Series(truth[ok]), method="spearman")
    fl = int(((truth[ok] >= 40) & (est[ok] < 40)).sum() + ((truth[ok] < 40) & (est[ok] >= 40)).sum())
    lines.append(f"| {nm} | {bias:+.2f} | {mae:.2f} | {rho:.3f} | {fl} |")

# how correlated are the two growth pillars in the first place -- the substitution only makes sense
# if 1-year growth actually carries information about the 3-year rank
c = full[["growth_3y_score", "growth_1y_score"]].corr(method="spearman").iloc[0, 1]
n_banks = int(d["growth_3y_score"].isna().sum())
lines += ["", f"Spearman correlation between `growth_3y_score` and `growth_1y_score` across the "
              f"universe: **{c:.3f}**.",
          f"Names in the file with `growth_3y_score` missing (the population this decides): "
          f"**{n_banks}**.", ""]
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
print("wrote", OUT)
