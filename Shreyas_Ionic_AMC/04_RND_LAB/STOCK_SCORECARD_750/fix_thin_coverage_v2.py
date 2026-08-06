# -*- coding: utf-8 -*-
"""V2 CORRECTOR — thin-history score inflation + growth artefacts + one-time-income flags.
Principal, 2026-08-07: "recently listed companies with no 3y price history or sometimes earning you
are giving them much higher weights ... we have to fix missing data or scoring problem for such
stocks" and "1 time earning or 1 time effect removal we have to check".

THE DEFECT, precisely. `weighted_mean()` in score_n100_quant.py skips a missing pillar and
renormalises over the pillars that exist -- so a missing pillar's weight is silently handed to the
survivors. For a company listed months ago the survivors are precisely the price pillars, and a
post-IPO run-up makes those strong; the fundamental pillars that would temper it are the missing
ones. Measured (results/THIN_COVERAGE_DIAG.md): 67 names re-allocate a mean 37% of composite weight;
worst inflation +13.3 points (TMCV), +13.2 (SKFINDUS); recent solar IPOs EMMVEE/UTLSOLAR/SAATVIKGL
all in the top-15 inflated list; AGL scored a 58.8 Hold off ONE pillar of seven.

THE FIX, three parts, all mechanical:
  1. NEUTRAL-FILL. A missing pillar contributes 50 (mid-universe) at its full weight instead of
     donating its weight to the survivors. "We don't know" scores as average, not as "whatever the
     price says".
  2. COVERAGE DISCIPLINE. <=3 of 7 pillars -> the score is WITHDRAWN ("No Rec -- insufficient
     history"): a number built on under half the framework is not comparable to the rest of the
     column and should not pretend to be. 4-6 pillars -> scored, but `thin_history_flag=Y`.
  3. GROWTH ARTEFACTS. revenue_cagr_3y that is infinite or >200% is a base-year artefact (first
     full year after listing/demerger), not a growth observation -> the growth pillar becomes
     missing (then neutral-filled). Same for revenue_growth_1y > 200%.

ONE-TIME EARNINGS (flags only -- changing the quality pillar is a frozen-methodology call, not mine):
  `one_time_income_risk`  latest annual Other Income+ > 25% of Profit before tax (financials exempt:
                          treasury income is their core business).
  `pat_sales_divergence`  latest-year PAT growth > 50% while Sales growth < 10% -- profit that
                          revenue cannot explain, the classic one-off signature.

EXACT REPLICATION, no approximation: composite recomputed with the engine's own BASE_W/TILT tables
(cyclicality-aware), the gate re-applied from the file's own bs_flag/liquidity_flag, and the
penalty/boost recovered exactly as residual = final - gate(composite). The script VERIFIES the
replication against the file before touching anything and aborts if it cannot reproduce the
original numbers.

Writes results/full750_scored_v2.csv (all original columns + v2 columns) + THIN_COVERAGE_FIX_NOTE.md.
v1 columns are untouched -- v2 sits beside them for the Principal's adoption call.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def _nifty_root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("NIFTY 500 root not found")
        if tail == "NIFTY 500":
            return os.path.join(p, tail)


ROOT = _nifty_root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "full750_scored_v2.csv")
NOTE = os.path.join(RES, "THIN_COVERAGE_FIX_NOTE.md")
PL = os.path.join(ROOT, "datasets", "screener_deep", "screener_annual_pl.parquet")

# engine's own tables (score_n100_quant.py:99-110) -- restated, not reinvented
BASE_W_3Y = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
                 sector_macro_3y_score=11, ownership_3y_score=9, accumulation_3y_score=8)
BASE_W_1Y = dict(quality_score=16, growth_1y_score=16, value_score=16, stage_1y_score=26,
                 sector_macro_1y_score=13, ownership_1y_score=8, accumulation_1y_score=5)
TILT_CYC_3Y = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
                   sector_macro_3y_score=3, ownership_3y_score=0, accumulation_3y_score=0)
TILT_NOT_3Y = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
                   sector_macro_3y_score=-2, ownership_3y_score=0, accumulation_3y_score=0)
TILT_CYC_1Y = dict(quality_score=-2, growth_1y_score=-2, value_score=3, stage_1y_score=-2,
                   sector_macro_1y_score=3, ownership_1y_score=0, accumulation_1y_score=0)
TILT_NOT_1Y = dict(quality_score=3, growth_1y_score=2, value_score=0, stage_1y_score=-3,
                   sector_macro_1y_score=-2, ownership_1y_score=0, accumulation_1y_score=0)

NEUTRAL = 50.0
GROWTH_ARTEFACT_PCT = 200.0     # a 3y revenue CAGR (or 1y growth) beyond this is a base artefact
WITHDRAW_MAX_PILLARS = 3        # <=3 of 7 pillars -> score withdrawn
OI_PBT_LIMIT = 0.25             # other income > 25% of PBT -> one-time-income risk


def composite(row, base, tilt_c, tilt_n, neutral=None):
    tilt = tilt_c if row.get("cyclicality_tag") == "Cyclical" else tilt_n
    num = den = 0.0
    for k, w in base.items():
        wt = w + tilt[k]
        v = row.get(k)
        if pd.notna(v):
            num += wt * float(v)
            den += wt
        elif neutral is not None:
            num += wt * neutral
            den += wt
    return num / den if den > 0 else np.nan


def gate(row, comp):
    if pd.isna(comp):
        return comp
    if row.get("bs_flag") == "RED" or row.get("liquidity_flag") == "RED":
        return min(comp, 40.0)
    if row.get("bs_flag") == "AMBER":
        return comp * 0.85
    return comp


def one_time_flags(symbols, sectors):
    """(one_time_income_risk, pat_sales_divergence) per symbol from the screener annual P&L."""
    oi_risk, divergence = {}, {}
    if not os.path.exists(PL):
        return oi_risk, divergence
    pl = pd.read_parquet(PL)
    year_cols = [c for c in pl.columns if str(c).startswith("Mar ") and "m" not in str(c).split()[-1]]
    year_cols = sorted(year_cols, key=lambda c: int(str(c).split()[1]))

    def series(sym, metric):
        r = pl[(pl["symbol"] == sym) & (pl["metric"] == metric)]
        if r.empty:
            return None
        s = pd.to_numeric(r.iloc[0][year_cols], errors="coerce").dropna()
        return s if len(s) else None

    fin = {s for s, sec in zip(symbols, sectors)
           if any(k in str(sec).lower() for k in ("financial", "bank", "insurance", "nbfc"))}
    for sym in symbols:
        oi, pbt = series(sym, "Other Income+"), series(sym, "Profit before tax")
        if oi is not None and pbt is not None and sym not in fin:
            common = oi.index.intersection(pbt.index)
            if len(common) and pbt[common[-1]] > 0:
                if oi[common[-1]] / pbt[common[-1]] > OI_PBT_LIMIT:
                    oi_risk[sym] = "Y"
        pat, sales = series(sym, "Net Profit+"), series(sym, "Sales+")
        if pat is not None and sales is not None and len(pat) >= 2 and len(sales) >= 2:
            p0, p1 = pat.iloc[-2], pat.iloc[-1]
            s0, s1 = sales.iloc[-2], sales.iloc[-1]
            if p0 > 0 and s0 > 0:
                pat_g, sales_g = (p1 / p0 - 1) * 100, (s1 / s0 - 1) * 100
                if pat_g > 50 and sales_g < 10:
                    divergence[sym] = "Y"
    return oi_risk, divergence


def main():
    d = pd.read_csv(SRC)
    n = len(d)

    # ---- 3. growth artefacts -> pillar missing ----------------------------------------------------
    g3 = pd.to_numeric(d["revenue_cagr_3y"], errors="coerce")
    g1 = pd.to_numeric(d["revenue_growth_1y"], errors="coerce")
    art3 = np.isinf(g3) | (g3 > GROWTH_ARTEFACT_PCT)
    art1 = np.isinf(g1) | (g1 > GROWTH_ARTEFACT_PCT)
    d["growth_artifact_flag"] = np.where(art3 | art1, "Y", "")
    d2 = d.copy()
    d2.loc[art3, "growth_3y_score"] = np.nan
    d2.loc[art1, "growth_1y_score"] = np.nan

    # ---- replication check BEFORE anything else ----------------------------------------------------
    # Recompute the engine's own skip-renormalised composite on UNTOUCHED rows and demand it matches
    # the file. If it does not, the weights/tilts here have drifted from the engine and every number
    # below would be fiction.
    untouched = ~(art3 | art1)
    chk3 = d[untouched].apply(lambda r: composite(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y), axis=1)
    chk1 = d[untouched].apply(lambda r: composite(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y), axis=1)
    err3 = (chk3 - pd.to_numeric(d.loc[untouched, "composite_3y"])).abs().max()
    err1 = (chk1 - pd.to_numeric(d.loc[untouched, "composite_1y"])).abs().max()
    print(f"replication check: max |diff| composite_3y {err3:.4f}, composite_1y {err1:.4f}")
    assert err3 < 0.05 and err1 < 0.05, "cannot reproduce the engine's composites -- ABORTING"

    # penalty/boost recovered exactly: residual = final - gate(composite)
    res3 = pd.to_numeric(d["final_score_3y"]) - d.apply(
        lambda r: gate(r, composite(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y)), axis=1)
    res1 = pd.to_numeric(d["final_score_1y"]) - d.apply(
        lambda r: gate(r, composite(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y)), axis=1)
    print(f"residual (penalty+boost) range: 3y [{res3.min():.1f},{res3.max():.1f}] "
          f"1y [{res1.min():.1f},{res1.max():.1f}]")

    # ---- 1. neutral-fill composites on sanitised pillars ------------------------------------------
    comp3_v2 = d2.apply(lambda r: composite(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y, NEUTRAL), axis=1)
    comp1_v2 = d2.apply(lambda r: composite(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y, NEUTRAL), axis=1)
    fin3 = (d2.apply(lambda r: gate(r, comp3_v2.loc[r.name]), axis=1) + res3).clip(0, 100)
    fin1 = (d2.apply(lambda r: gate(r, comp1_v2.loc[r.name]), axis=1) + res1).clip(0, 100)

    # ---- 2. coverage discipline (on sanitised pillars) --------------------------------------------
    p3 = list(BASE_W_3Y); p1 = list(BASE_W_1Y)
    cov3_n = d2[p3].notna().sum(axis=1)
    cov1_n = d2[p1].notna().sum(axis=1)
    withdrawn = (cov3_n <= WITHDRAW_MAX_PILLARS) | (cov1_n <= WITHDRAW_MAX_PILLARS)
    thin = ~withdrawn & ((cov3_n < 7) | (cov1_n < 7))
    d["thin_history_flag"] = np.where(withdrawn, "WITHDRAWN", np.where(thin, "Y", ""))

    d["final_score_3y_v2"] = np.where(withdrawn, np.nan, fin3.round(2))
    d["final_score_1y_v2"] = np.where(withdrawn, np.nan, fin1.round(2))
    rec3 = np.where(withdrawn, "No Rec", np.where(fin3 < 40, "Sell", "Hold"))
    rec1 = np.where(withdrawn, "No Rec", np.where(fin1 < 40, "Sell", "Hold"))
    d["recommendation_v2"] = np.where(withdrawn, "No Rec (insufficient history)",
                                      np.where((rec3 == "Sell") | (rec1 == "Sell"), "Sell", "Hold"))

    # ---- one-time earnings flags -------------------------------------------------------------------
    oi_risk, diverg = one_time_flags(d["symbol"].tolist(), d["sector"].tolist())
    d["one_time_income_risk"] = d["symbol"].map(oi_risk).fillna("")
    d["pat_sales_divergence"] = d["symbol"].map(diverg).fillna("")

    d.to_csv(OUT, index=False)

    # ---- fix note -----------------------------------------------------------------------------------
    delta = d["final_score_3y_v2"] - pd.to_numeric(d["final_score_3y"])
    movers = d.assign(delta=delta).dropna(subset=["delta"]).sort_values("delta")
    flips = d[(pd.to_numeric(d["final_score_3y"]) >= 40) & (d["final_score_3y_v2"] < 40)]
    lines = [
        "# Thin-coverage fix — v2 columns beside v1 (nothing overwritten)", "",
        f"Source `full750_scored.csv` ({n} names) -> `full750_scored_v2.csv`. "
        f"Replication verified: max composite diff {max(err3, err1):.4f}.", "",
        f"- growth artefacts neutralised (inf or >{GROWTH_ARTEFACT_PCT:.0f}%): "
        f"**{int((art3 | art1).sum())}** names ({', '.join(d.loc[art3 | art1, 'symbol'].head(8))})",
        f"- scores WITHDRAWN (<= {WITHDRAW_MAX_PILLARS} of 7 pillars): **{int(withdrawn.sum())}** "
        f"({', '.join(d.loc[withdrawn, 'symbol'].head(12))})",
        f"- thin-history flagged (4-6 pillars): **{int(thin.sum())}**",
        f"- Hold -> Sell flips under v2: **{len(flips)}** "
        f"({', '.join(flips['symbol'].head(10))})",
        f"- one-time-income risk (OI > {OI_PBT_LIMIT:.0%} of PBT, non-financials): "
        f"**{int((d['one_time_income_risk'] == 'Y').sum())}**",
        f"- PAT/Sales divergence (PAT +50% on Sales <10%): "
        f"**{int((d['pat_sales_divergence'] == 'Y').sum())}**", "",
        "## Largest corrections (3Y, v2 minus v1)", "",
        "| symbol | coverage | v1 | v2 | change |", "|---|---|---|---|---|",
    ]
    for _, r in movers.head(15).iterrows():
        lines.append(f"| {r['symbol']} | {r['coverage_3y']:.0f}% | "
                     f"{float(r['final_score_3y']):.1f} | {r['final_score_3y_v2']:.1f} | "
                     f"{r['delta']:+.1f} |")
    with open(NOTE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))
    print(f"\nwrote {OUT}\nwrote {NOTE}")


if __name__ == "__main__":
    main()
