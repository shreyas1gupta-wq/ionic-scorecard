# -*- coding: utf-8 -*-
"""DIAGNOSTIC: do thin-history names (recent IPOs, demergers) score HIGHER than fully-covered names?

Principal, 2026-08-07: "recently listed companies with no 3y price history or sometimes earning you are
giving them much higher weights check what error we are doing".

THE SUSPECTED MECHANISM. The composite is a weighted mean over the pillars that EXIST, renormalised by
the weight actually present (that is what `coverage_3y` records). Skipping a missing pillar is not
neutral -- it silently re-allocates that pillar's weight to whichever pillars DO exist. For a company
listed 8 months ago the pillars that exist are precisely the price/technical ones, and a post-IPO run-up
makes those strong. The fundamental pillars that would temper it (3-year growth, ROE history, ownership
trend) are the missing ones. So the score converges on "this thing went up", dressed as a 7-pillar
quantamental composite.

Evidence already on file that this is real, from the run's own validation notes:
  AGL   -- all fundamental fields NaN, coverage 14.29% (1 pillar of 7), final_score_1y 58.8 -> HOLD.
  TATACAP, HYUNDAI -- recent IPOs, no shareholding history, <252/504 trading days, pillars dropped.

This script does not assume the above. It measures:
  1. mean score by coverage bucket -- if thin coverage scores higher, the bias is confirmed and signed
  2. how much weight is being silently re-allocated, per bucket
  3. what those names would score if the missing pillars were treated as NEUTRAL (50) instead of dropped
  4. broken growth inputs (inf / absurd revenue CAGR off a tiny base) that hand a top percentile to a
     first-full-year company
Writes results/THIN_COVERAGE_DIAG.md. Changes nothing.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "THIN_COVERAGE_DIAG.md")

PILLARS_3Y = [("quality_score", 0.20), ("growth_3y_score", 0.20), ("value_score", 0.18),
              ("stage_3y_score", 0.14), ("sector_macro_3y_score", 0.11),
              ("ownership_3y_score", 0.09), ("accumulation_3y_score", 0.08)]
PILLARS_1Y = [("quality_score", 0.16), ("growth_1y_score", 0.16), ("value_score", 0.16),
              ("stage_1y_score", 0.26), ("sector_macro_1y_score", 0.13),
              ("ownership_1y_score", 0.08), ("accumulation_1y_score", 0.05)]


def num(d, c):
    return pd.to_numeric(d[c], errors="coerce") if c in d.columns else pd.Series(np.nan, index=d.index)


def recompute(d, pillars, neutral=None):
    """Weighted composite. neutral=None -> skip missing and renormalise (current behaviour).
    neutral=50 -> treat a missing pillar as mid-universe, so its weight is NOT handed to the survivors."""
    tot = np.zeros(len(d)); wsum = np.zeros(len(d))
    for c, w in pillars:
        v = num(d, c).to_numpy(dtype=float)
        present = ~np.isnan(v)
        if neutral is None:
            tot += np.where(present, v * w, 0.0)
            wsum += np.where(present, w, 0.0)
        else:
            tot += np.where(present, v, neutral) * w
            wsum += w
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(wsum > 0, tot / wsum, np.nan), wsum


def main():
    d = pd.read_csv(SRC)
    n = len(d)
    cov = num(d, "coverage_3y")
    cur = num(d, "final_score_3y")
    lines = ["# Thin-coverage scoring bias — diagnostic", "",
             f"Source: `results/full750_scored.csv`, {n} names. Nothing modified.", ""]

    # ---- 1. score by coverage bucket -------------------------------------------------------------
    buckets = [(0, 30), (30, 60), (60, 80), (80, 99.99), (99.99, 100.01)]
    lines += ["## 1. Score by coverage bucket", "",
              "| coverage of pillar weight | names | mean score | median | share scoring >= 40 (Hold) |",
              "|---|---|---|---|---|"]
    for lo, hi in buckets:
        m = (cov >= lo) & (cov < hi)
        if not m.any():
            continue
        lines.append(f"| {lo:.0f}-{hi:.0f}% | {int(m.sum())} | {cur[m].mean():.1f} | "
                     f"{cur[m].median():.1f} | {(cur[m] >= 40).mean() * 100:.0f}% |")
    full = cov >= 99.99
    thin = cov < 80
    gap = cur[thin].mean() - cur[full].mean()
    lines += ["", f"**Thin (<80% coverage) minus fully-covered: {gap:+.1f} points** "
                  f"(n_thin={int(thin.sum())}, n_full={int(full.sum())}).", ""]

    # ---- 2. which pillars go missing, and how much weight is re-allocated ------------------------
    lines += ["## 2. What is actually missing on thin names", "",
              "| pillar | 3Y weight | missing on all names | missing on thin names |", "|---|---|---|---|"]
    for c, w in PILLARS_3Y:
        v = num(d, c)
        lines.append(f"| `{c}` | {w:.0%} | {v.isna().mean() * 100:.1f}% | "
                     f"{v[thin].isna().mean() * 100:.0f}% |")
    _, wsum = recompute(d, PILLARS_3Y)
    lines += ["", f"Mean weight re-allocated to surviving pillars on thin names: "
                  f"**{(1 - wsum[thin.to_numpy()]).mean() * 100:.0f}%** of the composite.", ""]

    # ---- 3. neutral-fill counterfactual ----------------------------------------------------------
    skip3, _ = recompute(d, PILLARS_3Y)
    neut3, _ = recompute(d, PILLARS_3Y, neutral=50.0)
    delta = skip3 - neut3
    lines += ["## 3. Counterfactual: missing pillar treated as neutral (50) instead of dropped", "",
              "| group | mean score, current (skip) | mean score, neutral-fill | change |",
              "|---|---|---|---|",
              f"| fully covered | {skip3[full.to_numpy()].mean():.1f} | "
              f"{neut3[full.to_numpy()].mean():.1f} | {delta[full.to_numpy()].mean():+.1f} |",
              f"| thin (<80%) | {skip3[thin.to_numpy()].mean():.1f} | "
              f"{neut3[thin.to_numpy()].mean():.1f} | {delta[thin.to_numpy()].mean():+.1f} |", ""]
    flips = int(((skip3 >= 40) & (neut3 < 40) & thin.to_numpy()).sum())
    lines += [f"Thin names currently scoring Hold (>=40) that fall below the Sell bar under "
              f"neutral-fill: **{flips}**.", ""]

    # ---- 4. the worst offenders -------------------------------------------------------------------
    sym = "symbol" if "symbol" in d.columns else d.columns[0]
    w = d.loc[thin, [sym]].copy()
    w["coverage"] = cov[thin].round(1)
    w["score_now"] = np.round(skip3[thin.to_numpy()], 1)
    w["score_neutral"] = np.round(neut3[thin.to_numpy()], 1)
    w["drop"] = (w["score_now"] - w["score_neutral"]).round(1)
    w = w.sort_values("drop", ascending=False).head(15)
    lines += ["## 4. Most inflated names (thin coverage, largest fall under neutral-fill)", "",
              "| symbol | coverage % | score now | score if neutral-filled | inflation |",
              "|---|---|---|---|---|"]
    for _, r in w.iterrows():
        lines.append(f"| {r[sym]} | {r['coverage']:.0f} | {r['score_now']:.1f} | "
                     f"{r['score_neutral']:.1f} | **{r['drop']:+.1f}** |")

    # ---- 5. broken growth inputs -----------------------------------------------------------------
    g = num(d, "revenue_cagr_3y")
    inf_n = int(np.isinf(g).sum())
    absurd = int((g.replace([np.inf, -np.inf], np.nan) > 200).sum())
    lines += ["", "## 5. Broken growth inputs", "",
              f"- `revenue_cagr_3y` infinite: **{inf_n}** names (division by a near-zero base year, "
              f"the classic first-full-year-after-listing artefact).",
              f"- `revenue_cagr_3y` above 200%: **{absurd}** names.",
              f"- `growth_divergence_flag` set: **{int(num(d, 'growth_divergence_flag').sum())}**.",
              f"- `stale_flag` set: **{int(num(d, 'stale_flag').sum())}**, "
              f"`zero_cov_flag` set: **{int(num(d, 'zero_cov_flag').sum())}**.", ""]
    if inf_n:
        bad = d.loc[np.isinf(g), [sym]].head(12)[sym].tolist()
        lines.append(f"  Infinite-CAGR names: {', '.join(map(str, bad))}")

    os.makedirs(RES, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
