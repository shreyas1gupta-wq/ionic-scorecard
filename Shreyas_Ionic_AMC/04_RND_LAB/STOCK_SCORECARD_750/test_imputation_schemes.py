# -*- coding: utf-8 -*-
"""WHICH missing-pillar scheme is right? Decided by backtest, not by argument.
Principal, 2026-08-07: withdrawal is wrong (a large cap like Swiggy is legitimately thin) -- instead
"use technical if 1y history available and if less than 1 year available give more weight to value 50%
growth 25% quality 25% from the missing. or suggest better options backed with data."

THE TEST. Take names where ALL SEVEN pillars exist, so their true score is known. Delete exactly the
pillars that really-thin names lack (measured from this file, not assumed), impute by each candidate
scheme, and score the schemes on how well they recover the KNOWN answer. Any scheme can be argued for;
only one recovers the truth best, and bias matters more than error here -- a scheme that is wrong
symmetrically is survivable, one that is wrong UPWARDS reproduces the original bug.

The realistic deletion patterns, from the actual missing-rates among thin names:
  <1 YEAR LISTED   ownership, stage_3y, accumulation_3y, growth_3y gone (no history at all to compute
                   any of them); quality, value, sector survive off the latest annual + current price.
  1-2 YEARS LISTED ownership, stage_3y gone (needs 24m return); everything else present.

Candidate schemes:
  A skip        current engine: drop the pillar, renormalise over survivors. THE BUG.
  B neutral50   missing pillar scores 50 at full weight.
  C principal   missing weight redistributed to value 50% / growth 25% / quality 25% (renormalised
                across whichever of the three actually exist).
  D tech1y      Principal's other clause alone: substitute the 1-YEAR technical pillars for the
                missing 3-year ones where 12m history exists; anything still missing -> skip.
  E tech1y+C    D then C on whatever remains missing. (The Principal's full instruction.)
  F tech1y+B    D then neutral-fill.

Writes results/IMPUTATION_TEST.md. Changes nothing.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("NIFTY 500 root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            return cand


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "IMPUTATION_TEST.md")

BASE_W_3Y = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
                 sector_macro_3y_score=11, ownership_3y_score=9, accumulation_3y_score=8)
TILT_CYC = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
                sector_macro_3y_score=3, ownership_3y_score=0, accumulation_3y_score=0)
TILT_NOT = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
                sector_macro_3y_score=-2, ownership_3y_score=0, accumulation_3y_score=0)

# where the redistributed weight goes, per the Principal's instruction
REDIST = {"value_score": 0.50, "growth_3y_score": 0.25, "quality_score": 0.25}
# 3-year pillar -> its 1-year sibling, for the "use technical if 1y history available" clause
SIBLING_1Y = {"stage_3y_score": "stage_1y_score", "accumulation_3y_score": "accumulation_1y_score",
              "growth_3y_score": "growth_1y_score", "ownership_3y_score": "ownership_1y_score",
              "sector_macro_3y_score": "sector_macro_1y_score"}

# Deletion patterns. `kill_1y` matters: for a genuinely sub-1-year listing the 1-YEAR siblings are
# missing too (stage_1y needs a 12m return the company does not have), so the sibling substitution
# CANNOT fire. A first version of this test deleted only the 3-year pillars while the fully-covered
# test names kept their 1-year ones, so the substitution always fired and schemes C and B never
# actually competed -- all three "tech1y" rows came out identical, which was the tell.
PATTERNS = [
    ("<1 year listed (1y siblings also absent)",
     ["ownership_3y_score", "stage_3y_score", "accumulation_3y_score", "growth_3y_score"], True),
    ("1-2 years listed (12m history exists)",
     ["ownership_3y_score", "stage_3y_score"], False),
]


def weights(row):
    tilt = TILT_CYC if row.get("cyclicality_tag") == "Cyclical" else TILT_NOT
    return {k: BASE_W_3Y[k] + tilt[k] for k in BASE_W_3Y}


def score(vals, w):
    num = sum(w[k] * v for k, v in vals.items() if v is not None and v == v)
    den = sum(w[k] for k, v in vals.items() if v is not None and v == v)
    return num / den if den > 0 else np.nan


def impute(row, present, w, scheme, has_12m, blocked=()):
    """present: {pillar: value or None}. `blocked` names pillars whose 1-year sibling is ALSO absent,
    so the substitution must not silently reach for it. Returns values plus an effective weight map."""
    vals = dict(present)
    wt = dict(w)

    if scheme in ("tech1y", "tech1y+C", "tech1y+B") and has_12m:
        # substitute the 1-year sibling where the 3-year pillar is unavailable but 12m history exists.
        # This is the Principal's "use technical if 1y history available": a 14-month-old listing has a
        # real 12-month trend, and refusing to use it discards the one honest observation it has.
        for k in list(vals):
            if vals[k] is None and k in SIBLING_1Y and k not in blocked:
                sib = row.get(SIBLING_1Y[k])
                if pd.notna(sib):
                    vals[k] = float(sib)

    missing = [k for k, v in vals.items() if v is None]
    if not missing:
        return vals, wt

    if scheme in ("neutral50", "tech1y+B"):
        for k in missing:
            vals[k] = 50.0
        return vals, wt

    if scheme in ("principal", "tech1y+C"):
        # hand the missing weight to value/growth/quality in 50/25/25, renormalised across whichever
        # of the three actually exist -- redistributing onto an absent pillar would just re-create the
        # skip bug under a different name.
        free = sum(wt[k] for k in missing)
        targets = {k: s for k, s in REDIST.items() if vals.get(k) is not None}
        if targets:
            tot = sum(targets.values())
            for k, s in targets.items():
                wt[k] += free * s / tot
        for k in missing:
            vals[k] = None
        return vals, wt

    return vals, wt          # "skip": leave missing, score() renormalises


def main():
    d = pd.read_csv(SRC)
    P = list(BASE_W_3Y)
    full = d[d[P].notna().all(axis=1)].copy()

    ret12 = pd.to_numeric(d.get("ret_12m"), errors="coerce")
    ret24 = pd.to_numeric(d.get("ret_24m"), errors="coerce")
    lt1y = int(ret12.isna().sum())
    y1_2 = int((ret12.notna() & ret24.isna()).sum())
    lines = ["# Missing-pillar imputation — backtest on known answers", "",
             f"Fully-covered names available as ground truth: **{len(full)}** of {len(d)}.",
             f"Real history profile of the universe: **{lt1y}** names with <1y price history, "
             f"**{y1_2}** with 1-2y (no 24m return, so `stage_3y` cannot compute).", ""]

    schemes = ["skip", "neutral50", "principal", "tech1y", "tech1y+C", "tech1y+B"]
    for pat_name, pat, kill_1y in PATTERNS:
        lines += [f"## Pattern: {pat_name} — deleted {', '.join(p.replace('_score','') for p in pat)}",
                  "", "| scheme | mean error (bias) | mean abs error | rank corr | Hold->Sell flips |",
                  "|---|---|---|---|---|"]
        truth, res = [], {s: [] for s in schemes}
        blocked = tuple(pat) if kill_1y else ()
        for _, row in full.iterrows():
            w = weights(row)
            t = score({k: float(row[k]) for k in P}, w)
            truth.append(t)
            present = {k: (None if k in pat else float(row[k])) for k in P}
            has12 = pd.notna(row.get("ret_12m")) and not kill_1y
            for s in schemes:
                v, wt = impute(row, present, w, s, has12, blocked)
                res[s].append(score(v, wt))
        truth = np.array(truth)
        for s in schemes:
            est = np.array(res[s], dtype=float)
            ok = ~np.isnan(est) & ~np.isnan(truth)
            bias = (est[ok] - truth[ok]).mean()
            mae = np.abs(est[ok] - truth[ok]).mean()
            rho = pd.Series(est[ok]).corr(pd.Series(truth[ok]), method="spearman")
            flips = int(((truth[ok] >= 40) & (est[ok] < 40)).sum()
                        + ((truth[ok] < 40) & (est[ok] >= 40)).sum())
            star = " **<-**" if s == "tech1y+C" else ""
            lines.append(f"| {s}{star} | {bias:+.2f} | {mae:.2f} | {rho:.3f} | {flips} |")
        lines.append("")

    # how often the 1y-sibling substitution can actually fire
    can = int((pd.to_numeric(d.get("stage_3y_score"), errors="coerce").isna()
               & pd.to_numeric(d.get("stage_1y_score"), errors="coerce").notna()).sum())
    lines += [f"`stage_3y` missing but `stage_1y` available (the substitution can fire): "
              f"**{can}** names.", ""]

    # the rule conflict the Principal restated
    f3 = pd.to_numeric(d["final_score_3y"], errors="coerce")
    f1 = pd.to_numeric(d["final_score_1y"], errors="coerce")
    blend = 0.60 * f3 + 0.40 * f1
    sells = d["recommendation_overall"] == "Sell"
    bad = sells & (blend > 40)
    lines += ["## Sell-rule conflict (separate from imputation)", "",
              "`rec_overall` returns Sell if EITHER horizon is below 40. The client rule is no Sell "
              "above a blended 40.", "",
              f"- names called **Sell** whose blended score is **above 40**: **{int(bad.sum())}** "
              f"of {int(sells.sum())} Sells",
              f"- of those, blended 40-50 (Trim band, not Sell): "
              f"**{int((bad & (blend <= 50)).sum())}**",
              f"- blended above 50 yet called Sell: **{int((bad & (blend > 50)).sum())}**", ""]
    if bad.any():
        ex = d.loc[bad, ["symbol"]].assign(b=blend[bad].round(1), f3=f3[bad].round(1),
                                           f1=f1[bad].round(1)).sort_values("b", ascending=False)
        lines += ["| symbol | blended | 3Y | 1Y |", "|---|---|---|---|"]
        for _, r in ex.head(10).iterrows():
            lines.append(f"| {r['symbol']} | {r['b']:.1f} | {r['f3']:.1f} | {r['f1']:.1f} |")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
