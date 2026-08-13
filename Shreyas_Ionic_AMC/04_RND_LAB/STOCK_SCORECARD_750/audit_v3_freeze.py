# -*- coding: utf-8 -*-
"""FREEZE AUDIT for the v3 scoring model. Every rule the Principal set, checked against the output.

An audit that only checks what I expect to pass is theatre. Each item below is a rule that COULD be
violated by the code as written, phrased so a failure is unambiguous, and the script exits non-zero if
any hard invariant breaks. Soft observations are reported but do not fail the run.
"""
import json
import os
import sys

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


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
OUT = os.path.join(RES, "V3_FREEZE_AUDIT.md")

d = pd.read_csv(os.path.join(RES, "full750_scored_v3.csv"))
ion = pd.to_numeric(d["ionic_score_v3"], errors="coerce")
base = pd.to_numeric(d["base_score_v3"], errors="coerce")
adj = pd.to_numeric(d["forward_adjustment"], errors="coerce")
gp = pd.to_numeric(d["fwd_growth_points"], errors="coerce")
cp = pd.to_numeric(d["conviction_points"], errors="coerce")
rec = d["recommendation_v3"].astype(str)
an = d["analyst_call"].astype(str)
gin = pd.to_numeric(d["fwd_growth_input_pct"], errors="coerce")

HARD, SOFT = [], []


def hard(name, ok, detail=""):
    HARD.append((name, bool(ok), detail))


def soft(name, detail):
    SOFT.append((name, detail))


# ---- the recommendation ladder ---------------------------------------------------------------------
hard("no Sell at or above 40", int(((rec == "Sell") & (ion >= 40)).sum()) == 0,
     f"{int(((rec == 'Sell') & (ion >= 40)).sum())} violations")
hard("no non-Hold above 50", int(((rec != "Hold") & (ion > 50)).sum()) == 0,
     f"{int(((rec != 'Hold') & (ion > 50)).sum())} violations")
hard("every name below 40 is a Sell", int(((ion < 40) & (rec != "Sell")).sum()) == 0,
     f"{int(((ion < 40) & (rec != 'Sell')).sum())} violations")
hard("only two calls exist at universe level", set(rec.unique()) <= {"Sell", "Hold"},
     f"values {sorted(rec.unique())}")
te = d["trim_eligible_v3"].astype(str).fillna("")
hard("no Sell is marked trim-eligible", int(((rec == "Sell") & (te != "")).sum()) == 0)
hard("40-50 band eligibility set exactly on the band",
     int((ion.between(40, 50) & ~te.str.contains("40-50")).sum()) == 0
     and int((~ion.between(40, 50) & te.str.contains("40-50")).sum()) == 0)
hard("analyst-view eligibility implies an analyst Sell",
     int((te.str.contains("analyst") & (an != "Sell")).sum()) == 0)

# ---- score caps -------------------------------------------------------------------------------------
hard("scores within [5,95]", bool(ion.min() >= 5 - 1e-9 and ion.max() <= 95 + 1e-9),
     f"range {ion.min():.2f} to {ion.max():.2f}")
hard("no NaN scores", int(ion.isna().sum()) == 0, f"{int(ion.isna().sum())} NaN")

# ---- the forward adjustment -------------------------------------------------------------------------
hard("adjustment = growth + conviction, clamped 20",
     bool((adj - np.clip(gp + cp, -20, 20).where(
         ~((gin < 10) | (an == "Sell")), np.minimum(np.clip(gp + cp, -20, 20), 0))).abs().max() < 1e-6))
hard("Ionic = base + adjustment (pre-cap)",
     bool(((base + adj).clip(5, 95) - ion).abs().max() < 0.011),
     f"max diff {((base + adj).clip(5, 95) - ion).abs().max():.4f}")
hard("analyst Sell never gets a net uplift", int(((an == "Sell") & (adj > 0)).sum()) == 0)
hard("expected growth <10% never gets a net uplift",
     int(((gin < 10) & (adj > 0)).sum()) == 0)
hard("conviction leg only ever -6/0/+6", set(cp.dropna().unique()) <= {-6.0, 0.0, 6.0},
     f"values {sorted(cp.dropna().unique())}")
hard("growth leg only ever on the frozen bands",
     set(gp.dropna().unique()) <= {-15.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0},
     f"values {sorted(gp.dropna().unique())}")

# ---- the revenue rescue -------------------------------------------------------------------------------
rescol = d.get("revenue_rescue", pd.Series([""] * len(d))).astype(str)
resc = rescol == "Y"
erev = pd.to_numeric(d.get("expected_rev_growth_pct", pd.Series([np.nan] * len(d))), errors="coerce")
hard("rescued names never below -5 on the growth leg", int((resc & (gp < -5)).sum()) == 0)
hard("rescue only fires on FORWARD revenue >15% and expected EPS <10%",
     int((resc & ~((erev > 15) & (gin < 10))).sum()) == 0)
hard("rescue never fires on trailing revenue",
     int((resc & erev.isna()).sum()) == 0,
     "the whole point of the forward-only correction")
soft_dormant = int((rescol == "no fwd revenue data").sum())

# ---- gates ---------------------------------------------------------------------------------------------
FIN = d["sector"].astype(str).str.lower().str.contains("financial|bank|insurance|nbfc")
hard("all financials exempt from the balance-sheet gate",
     int((FIN & (d["bs_flag_v3"] != "N/A-financial-sector")).sum()) == 0)
de = pd.to_numeric(d["debt_equity"], errors="coerce")
EXEMPT = d["sector"].astype(str).str.lower().str.contains(
    "financial services|power|realty|telecommunication|construction")
hard("no exempt-sector name flagged RED on D/E alone",
     int((EXEMPT & (d["bs_flag_v3"] == "RED")
          & (de > 2.5) & (pd.to_numeric(d["interest_coverage"], errors="coerce") >= 1.5)).sum()) == 0)

# ---- growth source ---------------------------------------------------------------------------------------
m2m_share = (d["growth_source_v3"] == "March-to-March").mean() * 100
hard("most names on March-to-March", m2m_share > 90, f"{m2m_share:.0f}%")

# ---- soft observations ------------------------------------------------------------------------------------
soft("Sell rate", f"{(rec == 'Sell').mean()*100:.0f}% (frozen note expects ~33%)")
soft("double-count risk", f"growth-leg and conviction-leg correlation "
                          f"{gp.corr(cp, method='spearman'):+.2f}; "
                          f"{int(((gp <= -5) & (cp == -6)).sum())} names charged by both")
soft("revenue rescue", f"{int(resc.sum())} applied; {soft_dormant} names eligible on EPS but "
                       f"DORMANT — expected_next_3y_revenue_growth_pct not yet in the research files")
soft("trim-eligible Holds", f"{int((te != '').sum())} "
                            f"({int(te.str.contains('40-50').sum())} on the score band, "
                            f"{int(te.str.contains('analyst').sum())} on the analyst view)")
soft("analyst rescues suppressed", f"{int(((cp > 0) & (adj <= 0)).sum())} of {int((cp > 0).sum())} "
                                   f"blocked by the low-growth cap")
soft("names at the -20 clamp", f"{int((adj <= -20).sum())}")
soft("bottom band", f"{int((ion < 20).sum())} names under 20")
soft("thin history", f"{int((d['history_class'] != 'full').sum())} names, "
                     f"{int(d['listing_return_pctile'].notna().sum())} given a listing-price technical")
soft("earnings-quality flags", f"OI-driven {int((d.get('oi_driven_growth','') == 'Y').sum())}, "
                               f"level {int((d.get('oi_level_high','') == 'Y').sum())}, "
                               f"spike {int((d.get('oi_spike','') == 'Y').sum())}")

# ---- report ------------------------------------------------------------------------------------------------
npass = sum(1 for _n, ok, _dd in HARD if ok)
lines = ["# v3 freeze audit", "",
         f"**{npass} of {len(HARD)} hard invariants pass.**", "",
         "| # | invariant | result | detail |", "|---|---|---|---|"]
for i, (n, ok, dd) in enumerate(HARD, 1):
    lines.append(f"| {i} | {n} | {'PASS' if ok else '**FAIL**'} | {dd} |")
lines += ["", "## Observations (not failures)", "", "| item | value |", "|---|---|"]
for n, dd in SOFT:
    lines.append(f"| {n} | {dd} |")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\nwrote", OUT)
sys.exit(0 if npass == len(HARD) else 1)
