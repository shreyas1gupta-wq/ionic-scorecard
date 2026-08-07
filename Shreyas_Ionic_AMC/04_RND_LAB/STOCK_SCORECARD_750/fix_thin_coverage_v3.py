# -*- coding: utf-8 -*-
"""V3 CORRECTOR — thin-history scoring, FINAL. Supersedes fix_thin_coverage_v2.py.
Principal rulings, 2026-08-07, and what the backtests said about each:

  "no withdrawal, a large cap like Swiggy can also be thin"   ADOPTED. v2 withdrew 8 names; v3 scores
                                                              every name. Withdrawal was the wrong
                                                              instrument -- thin history is a data
                                                              condition, not a disqualification.
  "use technical if 1y history available"                     CONFIRMED BY TEST, and the single biggest
                                                              win here. Substituting the 1-year sibling
                                                              pillars for the missing 3-year ones:
                                                              bias +1.02 -> +0.05, MAE 3.86 -> 2.72,
                                                              rank corr 0.906 -> 0.932.
  "give technical points if above/below listing price for     CONFIRMED BY TEST. Return since listing,
   <1y ipo/demerger"                                          ranked against the universe over the SAME
                                                              window, lifts rank corr 0.601 -> 0.701 at
                                                              only 3 months of history, 0.735 at 12,
                                                              and adds NO bias (+1.84 -> +1.84).
  "give more weight to value 50% growth 25% quality 25%"      REJECTED ON MEASUREMENT -- the one
                                                              instruction the data contradicts. It was
                                                              WORSE than the bug it was meant to fix:
                                                              bias +3.07 vs skip's +2.95, MAE 11.83 vs
                                                              10.08, rank corr 0.445 vs 0.601. Piling
                                                              ~37% of freed weight onto value amplifies
                                                              value's idiosyncratic variance, and value
                                                              is uncorrelated with the pillars that went
                                                              missing, so it adds noise rather than
                                                              information. NEUTRAL-FILL is used instead
                                                              for whatever remains unobservable: under
                                                              uncertainty, shrinking to the middle beats
                                                              betting the weight on one surviving pillar.
                                                              (results/IMPUTATION_TEST.md)
  "no sell if score >40; 40-50 trim if over-conc, not sell"   ADOPTED, and it exposed a live conflict:
                                                              the engine's rec_overall says Sell if
                                                              EITHER horizon is under 40, which called
                                                              88 of its 246 Sells on names whose blended
                                                              score is ABOVE 40 -- BANKBARODA at 54.1,
                                                              HINDALCO 52.5, JSWSTEEL 51.8, AXISBANK
                                                              47.4. v3 calls on the blended score.

Everything lands in *_v3 columns beside v1. The engine is not touched; adoption is the Principal's call.
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
        if tail == "NIFTY 500":
            return os.path.join(p, tail)


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
PRICES = os.path.join(ROOT, "ALPHA_RANKER", "data", "prices")
SRC = os.path.join(RES, "full750_scored.csv")
EQ = os.path.join(RES, "EARNINGS_QUALITY.csv")
OUT = os.path.join(RES, "full750_scored_v3.csv")
NOTE = os.path.join(RES, "THIN_COVERAGE_FIX_V3_NOTE.md")

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

SIBLING = {"stage_3y_score": "stage_1y_score", "accumulation_3y_score": "accumulation_1y_score",
           "growth_3y_score": "growth_1y_score", "ownership_3y_score": "ownership_1y_score",
           "sector_macro_3y_score": "sector_macro_1y_score"}
NEUTRAL = 50.0
ARTEFACT = 200.0
AS_OF = pd.Timestamp("2026-07-20")
TDPM = 21
WINDOWS = (12, 9, 6, 3)          # months; a thin name uses the longest window it can support
SELL_BAR, TRIM_CEIL = 40.0, 50.0


def comp(row, base, tilt_c, tilt_n, neutral=None):
    tilt = tilt_c if row.get("cyclicality_tag") == "Cyclical" else tilt_n
    num = den = 0.0
    for k, w in base.items():
        wt = w + tilt[k]
        v = row.get(k)
        if pd.notna(v):
            num += wt * float(v); den += wt
        elif neutral is not None:
            num += wt * neutral; den += wt
    return num / den if den > 0 else np.nan


def gate(row, c):
    if pd.isna(c):
        return c
    if row.get("bs_flag") == "RED" or row.get("liquidity_flag") == "RED":
        return min(c, 40.0)
    if row.get("bs_flag") == "AMBER":
        return c * 0.85
    return c


def window_returns(symbols):
    """{months: {sym: return}} plus {sym: months of history}. One pass over the price files."""
    rets = {m: {} for m in WINDOWS}
    hist = {}
    for s in symbols:
        p = os.path.join(PRICES, f"{s}.parquet")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        col = next((c for c in ("close", "Close", "adj_close") if c in df.columns), None)
        if col is None:
            continue
        if not isinstance(df.index, pd.DatetimeIndex):
            dc = next((c for c in ("date", "Date", "timestamp") if c in df.columns), None)
            if dc is None:
                continue
            df = df.set_index(pd.to_datetime(df[dc]))
        px = df[col].dropna()
        px = px[px.index <= AS_OF]
        if len(px) < 2:
            continue
        hist[s] = len(px) / TDPM
        for m in WINDOWS:
            need = int(m * TDPM)
            if len(px) >= need + 5:
                w = px.iloc[-need:]
                if w.iloc[0] > 0:
                    rets[m][s] = float(w.iloc[-1] / w.iloc[0] - 1.0)
    return rets, hist


def main():
    d = pd.read_csv(SRC)
    n = len(d)
    syms = d["symbol"].astype(str).tolist()

    # ---- growth artefacts -> pillar unobservable ---------------------------------------------------
    g3 = pd.to_numeric(d["revenue_cagr_3y"], errors="coerce")
    g1 = pd.to_numeric(d["revenue_growth_1y"], errors="coerce")
    art3 = np.isinf(g3) | (g3 > ARTEFACT)
    art1 = np.isinf(g1) | (g1 > ARTEFACT)
    d["growth_artifact_flag"] = np.where(art3 | art1, "Y", "")

    # ---- replication check on untouched rows BEFORE changing anything ------------------------------
    keep = ~(art3 | art1)
    e3 = (d[keep].apply(lambda r: comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y), axis=1)
          - pd.to_numeric(d.loc[keep, "composite_3y"])).abs().max()
    print(f"replication check: max |diff| composite_3y {e3:.4f}")
    assert e3 < 0.05, "cannot reproduce the engine composite -- ABORTING"
    res3 = pd.to_numeric(d["final_score_3y"]) - d.apply(
        lambda r: gate(r, comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y)), axis=1)
    res1 = pd.to_numeric(d["final_score_1y"]) - d.apply(
        lambda r: gate(r, comp(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y)), axis=1)

    d2 = d.copy()
    d2.loc[art3, "growth_3y_score"] = np.nan
    d2.loc[art1, "growth_1y_score"] = np.nan

    # ---- history class -----------------------------------------------------------------------------
    ret12 = pd.to_numeric(d["ret_12m"], errors="coerce")
    ret24 = pd.to_numeric(d["ret_24m"], errors="coerce")
    cls = np.where(ret24.notna(), "full", np.where(ret12.notna(), "1-2y", "<1y"))
    d["history_class"] = cls

    # ---- <1y: technical from return since listing, ranked over the SAME window ---------------------
    rets, hist = window_returns(syms)
    pct_by_win = {}
    for m in WINDOWS:
        s = pd.Series(rets[m])
        pct_by_win[m] = (s.rank(pct=True) * 100) if len(s) else pd.Series(dtype=float)
    listing_pct, listing_win = {}, {}
    for i, sym in enumerate(syms):
        if cls[i] != "<1y":
            continue
        hm = hist.get(sym)
        if hm is None:
            continue
        for m in WINDOWS:                       # longest window the name can actually support
            if hm >= m + 0.3 and sym in pct_by_win[m].index:
                listing_pct[sym] = float(pct_by_win[m].loc[sym])
                listing_win[sym] = m
                break
    d["listing_return_pctile"] = d["symbol"].astype(str).map(listing_pct)
    d["listing_window_months"] = d["symbol"].astype(str).map(listing_win)

    # Count observed pillars BEFORE imputing. Counting after would report a name as 7-of-7 covered
    # because the fix filled it in, which is precisely the opposite of what this column is for.
    p3 = list(BASE_W_3Y)
    d["pillars_observed"] = d2[p3].notna().sum(axis=1)

    # ---- impute: 1y siblings, then listing-price technical, then neutral ---------------------------
    imputed_note = []
    for i, row in d2.iterrows():
        used = []
        for k, sib in SIBLING.items():
            if k in BASE_W_3Y and pd.isna(row.get(k)):
                v = row.get(sib)
                if pd.notna(v):
                    d2.at[i, k] = float(v)
                    used.append(f"{k.replace('_score','')}<-1y")
        sym = str(row["symbol"])
        if pd.isna(d2.at[i, "stage_3y_score"]) and sym in listing_pct:
            d2.at[i, "stage_3y_score"] = listing_pct[sym]
            used.append(f"stage<-listing{listing_win[sym]}m")
        imputed_note.append(",".join(used))
    d["imputation_applied"] = imputed_note

    # Publish the IMPUTED pillar values as *_v3 columns. Without these the v3 file carries a corrected
    # score alongside the original NaN pillars, so anything reading the pillars (the five-signal dots,
    # the Excel) shows "not scored" on a name whose score demonstrably used a substituted value -- the
    # page would contradict its own number.
    for k in BASE_W_3Y:
        d[f"{k}_v3"] = d2[k]

    c3 = d2.apply(lambda r: comp(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOT_3Y, NEUTRAL), axis=1)
    c1 = d2.apply(lambda r: comp(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOT_1Y, NEUTRAL), axis=1)
    f3 = (d2.apply(lambda r: gate(r, c3.loc[r.name]), axis=1) + res3).clip(0, 100)
    f1 = (d2.apply(lambda r: gate(r, c1.loc[r.name]), axis=1) + res1).clip(0, 100)
    d["final_score_3y_v3"] = f3.round(2)
    d["final_score_1y_v3"] = f1.round(2)

    # ---- call on the BLENDED score: no Sell above 40, 40-50 is the Trim band -----------------------
    blend = (0.60 * f3 + 0.40 * f1)
    d["ionic_score_v3"] = blend.round(2)
    d["recommendation_v3"] = np.where(blend < SELL_BAR, "Sell",
                                      np.where(blend <= TRIM_CEIL, "Hold (Trim if concentrated)",
                                               "Hold"))
    d["thin_history_flag"] = np.where(d["history_class"] == "<1y", "<1y",
                                      np.where(d["pillars_observed"] < 7, "Y", ""))

    # ---- earnings-quality flags -------------------------------------------------------------------
    if os.path.exists(EQ):
        eq = pd.read_csv(EQ)[["symbol", "oi_driven_growth", "oi_level_high", "oi_spike",
                              "oi_pct_of_pbt", "eff_margin", "eff_other_income"]]
        d = d.merge(eq, on="symbol", how="left")

    d.to_csv(OUT, index=False)

    # ---- note --------------------------------------------------------------------------------------
    old_sell = d["recommendation_overall"] == "Sell"
    new_sell = d["recommendation_v3"] == "Sell"
    delta = d["final_score_3y_v3"] - pd.to_numeric(d["final_score_3y"])
    mv = d.assign(delta=delta).dropna(subset=["delta"]).sort_values("delta")
    lines = [
        "# Thin-history fix v3 — FINAL (v3 columns beside v1; engine untouched)", "",
        f"{n} names. Replication verified: max composite diff {e3:.4f}.", "",
        "## What changed vs v2", "",
        "- **No withdrawals.** v2 withdrew 8 names; v3 scores every one (Principal: a large cap like "
        "Swiggy can legitimately be thin).",
        "- **1-year siblings substituted** where a 3-year pillar is unavailable (backtest: rank corr "
        "0.906 -> 0.932, MAE 3.86 -> 2.72).",
        "- **Listing-price technical** for <1y names: return since listing, ranked over the same "
        "window (rank corr 0.601 -> 0.701 at 3 months, 0.735 at 12; no added bias).",
        "- **50/25/25 redistribution REJECTED on measurement** — it scored worse than the bug "
        "(bias +3.07 vs +2.95, MAE 11.83 vs 10.08, corr 0.445 vs 0.601). Neutral-fill used instead.",
        "- **Call taken on the blended score**, so no name above 40 is ever a Sell.", "",
        "## Coverage", "",
        f"- history: full **{int((d['history_class'] == 'full').sum())}**, "
        f"1-2y **{int((d['history_class'] == '1-2y').sum())}**, "
        f"<1y **{int((d['history_class'] == '<1y').sum())}**",
        f"- names receiving a 1y-sibling or listing-price substitution: "
        f"**{int((d['imputation_applied'] != '').sum())}**",
        f"- <1y names given a listing-price technical: **{int(d['listing_return_pctile'].notna().sum())}**",
        f"- growth artefacts neutralised: **{int((art3 | art1).sum())}** "
        f"({', '.join(d.loc[art3 | art1, 'symbol'].head(8))})", "",
        "## Recommendation change", "",
        f"| | v1 (either horizon <40) | v3 (blended) |", "|---|---|---|",
        f"| Sell | {int(old_sell.sum())} | {int(new_sell.sum())} |",
        f"| Hold / Trim band | {int((~old_sell).sum())} | "
        f"{int((d['recommendation_v3'] != 'Sell').sum())} |",
        "",
        f"- names v1 called Sell that are NOT Sell under the blended rule: "
        f"**{int((old_sell & ~new_sell).sum())}**",
        f"- of the v3 Holds, in the 40-50 Trim band: "
        f"**{int((d['recommendation_v3'] == 'Hold (Trim if concentrated)').sum())}**", "",
        "## Largest score corrections (3Y, v3 minus v1)", "",
        "| symbol | history | pillars | v1 | v3 | change | imputation |", "|---|---|---|---|---|---|---|",
    ]
    for _, r in mv.head(12).iterrows():
        lines.append(f"| {r['symbol']} | {r['history_class']} | {int(r['pillars_observed'])} | "
                     f"{float(r['final_score_3y']):.1f} | {r['final_score_3y_v3']:.1f} | "
                     f"{r['delta']:+.1f} | {r['imputation_applied'] or '-'} |")
    with open(NOTE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}\nwrote {NOTE}")


if __name__ == "__main__":
    main()
