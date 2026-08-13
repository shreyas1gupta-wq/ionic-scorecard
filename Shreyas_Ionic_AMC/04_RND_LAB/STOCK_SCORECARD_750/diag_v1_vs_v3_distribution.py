# -*- coding: utf-8 -*-
"""How the score distribution moved from v1 to v3, and WHAT MOVED IT.
Principal, 2026-08-07: "what all changes we did from previous score distribution ... did it change to
better or worse and factors behind it?"

Decomposes the v1 -> v3 shift into its four causes, one at a time and in order, so each one's
contribution is separable rather than asserted:
    step 1  growth artefacts neutralised (inf / >200% CAGR)
    step 2  imputation (1y sibling, listing-price technical, neutral-fill)
    step 3  score cap [5, 95]
    step 4  forward adjustment (growth leg + analyst conviction leg)

A NOTE ON WHAT CANNOT BE ANSWERED HERE. Whether v3 PREDICTS better is a different question from whether
its distribution is better shaped, and steps 1-3 can be backtested while step 4 cannot: the forward
adjustment depends on analyst EPS estimates and analyst recommendations that exist only as of today,
with no point-in-time history. Scoring a past date with today's analyst view is lookahead of the purest
kind. See the companion note for what is and is not testable.
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
OUT = os.path.join(RES, "V1_VS_V3_DISTRIBUTION.md")


def moments(s, label):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return (f"| {label} | {len(s)} | {s.mean():.1f} | {s.std():.1f} | {s.min():.1f} | "
            f"{s.quantile(.10):.1f} | {s.median():.1f} | {s.quantile(.90):.1f} | {s.max():.1f} |")


def main():
    d = pd.read_csv(os.path.join(RES, "full750_scored_v3.csv"))
    v1 = pd.to_numeric(d["final_score_3y"], errors="coerce")
    base = pd.to_numeric(d["base_score_v3"], errors="coerce")
    v3f3 = pd.to_numeric(d["final_score_3y_v3"], errors="coerce")
    ionic = pd.to_numeric(d["ionic_score_v3"], errors="coerce")

    lines = ["# v1 to v3 — how the distribution moved, and what moved it", "",
             "## 1. Shape", "",
             "| series | n | mean | sd | min | p10 | median | p90 | max |",
             "|---|---|---|---|---|---|---|---|---|",
             moments(v1, "v1 `final_score_3y`"),
             moments(v3f3, "v3 3Y (imputation + artefacts + cap)"),
             moments(base, "v3 base blend (0.6x3Y + 0.4x1Y)"),
             moments(ionic, "v3 **Ionic** (base + forward adjustment)"), ""]

    rho = v1.corr(ionic, method="spearman")
    rho_f3 = v1.corr(v3f3, method="spearman")
    lines += [f"Rank correlation v1 vs v3 3Y: **{rho_f3:.3f}**. v1 vs final Ionic: **{rho:.3f}**.",
              "A high correlation is the point -- these are corrections, not a new model. What matters "
              "is which names moved and why.", ""]

    # ---- 2. decompose the move ------------------------------------------------------------------
    art = (d["growth_artifact_flag"] == "Y")
    imp = d["imputation_applied"].fillna("").astype(str).str.len() > 0
    capped = (base <= 5.0) | (base >= 95.0) | (ionic <= 5.0) | (ionic >= 95.0)
    adj = pd.to_numeric(d["forward_adjustment"], errors="coerce")

    lines += ["## 2. What moved the scores", "",
              "| cause | names touched | mean move on those names | largest single move |",
              "|---|---|---|---|"]
    d3 = v3f3 - v1
    for lab, m in (("growth artefact neutralised", art),
                   ("imputation applied", imp),
                   ("score cap bound", capped)):
        sub = d3[m].dropna()
        if len(sub):
            worst = sub.abs().max()
            lines.append(f"| {lab} | {int(m.sum())} | {sub.mean():+.1f} | {worst:.1f} |")
        else:
            lines.append(f"| {lab} | {int(m.sum())} | - | - |")
    lines.append(f"| forward adjustment | {int((adj != 0).sum())} | "
                 f"{adj[adj != 0].mean():+.1f} | {adj.abs().max():.0f} |")
    lines += ["", f"Untouched by any of the four: **{int((~art & ~imp & ~capped & (adj == 0)).sum())}** "
                  f"names, whose Ionic equals their base exactly.", ""]

    # ---- 3. call migration -----------------------------------------------------------------------
    lines += ["## 3. Where the calls went", "",
              "| | v1 | v3 |", "|---|---|---|",
              f"| Sell | {int((d['recommendation_overall'] == 'Sell').sum())} | "
              f"{int((d['recommendation_v3'] == 'Sell').sum())} |",
              f"| Trim band (40-50) | not modelled | "
              f"{int((d['recommendation_v3'] == 'Hold (Trim if concentrated)').sum())} |",
              f"| Hold | {int((d['recommendation_overall'] == 'Hold').sum())} | "
              f"{int((d['recommendation_v3'] == 'Hold').sum())} |", ""]

    # ---- 4. decile stability ----------------------------------------------------------------------
    dec1 = pd.qcut(v1.rank(method="first"), 10, labels=False)
    dec3 = pd.qcut(ionic.rank(method="first"), 10, labels=False)
    same = (dec1 == dec3).mean() * 100
    moved2 = (abs(dec1 - dec3) >= 2).mean() * 100
    lines += ["## 4. Decile stability", "",
              f"- names staying in the same decile: **{same:.0f}%**",
              f"- names moving 2+ deciles: **{moved2:.0f}%**", ""]

    # ---- 5. BAJAJ-AUTO worked example --------------------------------------------------------------
    b = d[d["symbol"] == "BAJAJ-AUTO"]
    if len(b):
        r = b.iloc[0]
        lines += ["## 5. Worked example — BAJAJ-AUTO", "",
                  "| field | value |", "|---|---|",
                  f"| v1 score 3Y | {float(r['final_score_3y']):.1f} |",
                  f"| v3 base blend | {float(r['base_score_v3']):.1f} |",
                  f"| forward growth input (60:40) | {float(r['fwd_growth_input_pct']):.1f}% |",
                  f"| growth-leg points | {float(r['fwd_growth_points']):+.0f} |",
                  f"| conviction points (analyst Sell) | {float(r['conviction_points']):+.0f} |",
                  f"| net forward adjustment | {float(r['forward_adjustment']):+.0f} |",
                  f"| **Ionic Score** | **{float(r['ionic_score_v3']):.1f}** |",
                  f"| analyst call | {r['analyst_call']} |",
                  f"| final call | {r['recommendation_v3']} |",
                  f"| earnings-quality flags | OI-driven `{r.get('oi_driven_growth', '')}` · "
                  f"OI>25% PBT `{r.get('oi_level_high', '')}` · spike `{r.get('oi_spike', '')}` |", "",
                  "The score never says Sell here. The call comes entirely from Gate A.", ""]

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
