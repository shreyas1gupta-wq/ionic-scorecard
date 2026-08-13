# -*- coding: utf-8 -*-
"""EARNINGS QUALITY — decompose profit growth, do not shortcut it.
Principal, 2026-08-07: "PAT +50% while Sales <10% ... this can happen due to margin growth etc etc you
will have to check for the other income no shortcut formula".

He is right and the previous rule was wrong. PAT outgrowing sales is the NORMAL signature of operating
leverage: a company that lifts OPM from 12% to 15% on flat revenue grows profit ~25% with no one-off
whatsoever. Flagging that pattern flags good businesses. The 30 names the old rule caught were mostly
margin stories, not accounting events.

So decompose the profit bridge instead of pattern-matching it. From the screener annual P&L:

    PBT  =  Operating Profit  +  Other Income  -  Interest  -  Depreciation
    Operating Profit = Sales x OPM

and split the year-on-year change into its actual sources:

    volume effect  = (Sales_1 - Sales_0) x OPM_0        revenue genuinely grew
    margin effect  =  Sales_1 x (OPM_1 - OPM_0)         LEGITIMATE operating leverage
    other income   =  OI_1 - OI_0                       NON-OPERATING, the one to watch
    finance/dep    = -(Int_1 - Int_0) - (Dep_1 - Dep_0)

Every rupee of PBT change lands in one of those buckets, and the residual proves the decomposition
closes. The flag is then specific: profit growth mostly bought by NON-OPERATING income, not "profit
grew faster than revenue".

Three flags, all narrow, financials exempt throughout (treasury income IS their operating business):
  oi_driven_growth   >50% of the PBT increase came from Other Income
  oi_level_high      Other Income is >25% of PBT in the latest year (a standing dependence)
  oi_spike           Other Income more than 2x its own prior 3-year median AND >15% of PBT
                     (a one-off event: asset sale, write-back, settlement)

Writes results/EARNINGS_QUALITY.csv (per-name bridge + flags) and results/EARNINGS_QUALITY_NOTE.md.
"""
import os
import re

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
            raise RuntimeError("NIFTY 500 root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand          # keep walking: take the OUTERMOST match, not the first


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
PL = os.path.join(ROOT, "datasets", "screener_deep", "screener_annual_pl.parquet")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "EARNINGS_QUALITY.csv")
NOTE = os.path.join(RES, "EARNINGS_QUALITY_NOTE.md")

FIN_KEYS = ("financial", "bank", "insurance", "nbfc", "capital market", "finance")
OI_GROWTH_SHARE = 0.50
OI_LEVEL = 0.25
OI_SPIKE_MULT = 2.0
OI_SPIKE_MIN_LEVEL = 0.15


def main():
    pl = pd.read_parquet(PL)
    # Full-year columns ONLY, matched by strict pattern. Stub periods must be excluded -- comparing a
    # 10-month column against a 12-month year manufactures a collapse that never happened. A token-count
    # test is not enough: this file contains a column literally named "Mar 202315m", where the stub
    # suffix is concatenated with no space, which passes "two tokens" and then explodes on int().
    year_re = re.compile(r"^Mar (\d{4})$")
    years = [c for c in pl.columns if year_re.match(str(c).strip())]
    years = sorted(years, key=lambda c: int(year_re.match(str(c).strip()).group(1)))
    piv = {m: g.set_index("symbol")[years].apply(pd.to_numeric, errors="coerce")
           for m, g in pl.groupby("metric") if m in
           ("Sales+", "Operating Profit", "Other Income+", "Interest", "Depreciation",
            "Profit before tax", "Net Profit+")}

    scored = pd.read_csv(SRC)[["symbol", "sector"]]
    sector = dict(zip(scored["symbol"].astype(str), scored["sector"].astype(str)))

    def last_two(sym, metric):
        t = piv.get(metric)
        if t is None or sym not in t.index:
            return None, None, None
        s = t.loc[sym].dropna()
        if len(s) < 2:
            return None, None, s
        return float(s.iloc[-2]), float(s.iloc[-1]), s

    rows = []
    for sym in scored["symbol"].astype(str):
        is_fin = any(k in sector.get(sym, "").lower() for k in FIN_KEYS)
        s0, s1, _ = last_two(sym, "Sales+")
        op0, op1, _ = last_two(sym, "Operating Profit")
        oi0, oi1, oi_s = last_two(sym, "Other Income+")
        i0, i1, _ = last_two(sym, "Interest")
        d0, d1, _ = last_two(sym, "Depreciation")
        p0, p1, _ = last_two(sym, "Profit before tax")
        if None in (s0, s1, op0, op1, oi0, oi1, p0, p1) or s0 == 0:
            continue
        opm0, opm1 = op0 / s0, op1 / s1 if s1 else np.nan
        volume = (s1 - s0) * opm0
        margin = s1 * (opm1 - opm0)
        d_oi = oi1 - oi0
        d_fin = -((i1 or 0) - (i0 or 0)) - ((d1 or 0) - (d0 or 0))
        d_pbt = p1 - p0
        resid = d_pbt - (volume + margin + d_oi + d_fin)

        oi_share_growth = d_oi / d_pbt if d_pbt > 0 else np.nan
        oi_level = oi1 / p1 if p1 > 0 else np.nan
        prior_med = float(oi_s.iloc[-4:-1].median()) if oi_s is not None and len(oi_s) >= 4 else np.nan

        f_growth = (not is_fin) and pd.notna(oi_share_growth) and oi_share_growth > OI_GROWTH_SHARE
        f_level = (not is_fin) and pd.notna(oi_level) and oi_level > OI_LEVEL
        f_spike = ((not is_fin) and pd.notna(prior_med) and prior_med > 0 and oi1 > OI_SPIKE_MULT * prior_med
                   and pd.notna(oi_level) and oi_level > OI_SPIKE_MIN_LEVEL)
        rows.append(dict(
            symbol=sym, is_financial=is_fin,
            sales_growth_pct=round((s1 / s0 - 1) * 100, 1),
            pat_growth_pct=round((p1 / p0 - 1) * 100, 1) if p0 > 0 else np.nan,
            opm_prev_pct=round(opm0 * 100, 1), opm_latest_pct=round(opm1 * 100, 1),
            d_pbt=round(d_pbt, 1), eff_volume=round(volume, 1), eff_margin=round(margin, 1),
            eff_other_income=round(d_oi, 1), eff_finance_dep=round(d_fin, 1),
            bridge_residual=round(resid, 1),
            oi_share_of_growth=round(oi_share_growth, 3) if pd.notna(oi_share_growth) else np.nan,
            oi_pct_of_pbt=round(oi_level * 100, 1) if pd.notna(oi_level) else np.nan,
            oi_driven_growth="Y" if f_growth else "",
            oi_level_high="Y" if f_level else "",
            oi_spike="Y" if f_spike else "",
        ))

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    # how the OLD rule compares -- the point is that it was catching margin stories
    old = out[(out["pat_growth_pct"] > 50) & (out["sales_growth_pct"] < 10)]
    old_margin_led = old[old["eff_margin"] > old["eff_other_income"]]
    n = len(out)
    lines = [
        "# Earnings quality — profit-bridge decomposition (replaces the PAT-vs-Sales rule)", "",
        f"{n} names with a usable two-year P&L bridge. Bridge closes: median |residual| "
        f"{out['bridge_residual'].abs().median():.2f} cr against a median PBT change of "
        f"{out['d_pbt'].abs().median():.1f} cr.", "",
        "## Why the old rule was wrong", "",
        f"- names the OLD rule flagged (PAT +50% on Sales <10%): **{len(old)}**",
        f"- of those, profit growth actually driven by MARGIN, not other income: "
        f"**{len(old_margin_led)}** ({len(old_margin_led) / max(len(old), 1) * 100:.0f}%)",
        "", "Operating leverage is not an accounting red flag. The old rule was mostly catching "
        "good businesses expanding margin.", "",
        "## New flags", "",
        "| flag | meaning | names |", "|---|---|---|",
        f"| `oi_driven_growth` | >50% of the PBT increase came from Other Income | "
        f"**{int((out['oi_driven_growth'] == 'Y').sum())}** |",
        f"| `oi_level_high` | Other Income >25% of PBT (standing dependence) | "
        f"**{int((out['oi_level_high'] == 'Y').sum())}** |",
        f"| `oi_spike` | Other Income >2x its own 3y median AND >15% of PBT (one-off) | "
        f"**{int((out['oi_spike'] == 'Y').sum())}** |",
        f"| any of the three | | **{int(((out[['oi_driven_growth', 'oi_level_high', 'oi_spike']] == 'Y').any(axis=1)).sum())}** |",
        "", "Financials are exempt throughout: treasury and investment income IS their operating "
        "business, so the same test would flag every bank.", "",
        "## Largest one-off risks (by share of profit growth bought with other income)", "",
        "| symbol | sales grw % | PBT chg | from margin | from other income | OI % of PBT | flags |",
        "|---|---|---|---|---|---|---|",
    ]
    top = out[out["oi_driven_growth"] == "Y"].sort_values("eff_other_income", ascending=False)
    for _, r in top.head(15).iterrows():
        fl = " ".join(f for f, c in (("growth", "oi_driven_growth"), ("level", "oi_level_high"),
                                     ("spike", "oi_spike")) if r[c] == "Y")
        lines.append(f"| {r['symbol']} | {r['sales_growth_pct']:.1f} | {r['d_pbt']:.0f} | "
                     f"{r['eff_margin']:.0f} | {r['eff_other_income']:.0f} | "
                     f"{r['oi_pct_of_pbt']:.0f} | {fl} |")

    with open(NOTE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}\nwrote {NOTE}")


if __name__ == "__main__":
    main()
