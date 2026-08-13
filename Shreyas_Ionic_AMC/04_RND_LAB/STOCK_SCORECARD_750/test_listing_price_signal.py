# -*- coding: utf-8 -*-
"""Does "price vs listing price" earn the technical pillar for a <1y IPO/demerger?
Principal, 2026-08-07: "we can also give technical points if above listing price or below if it helps
for <1y history ipo/demerger".

The idea is sound in principle -- a 7-month-old listing has no 12m return, but it does have a real,
observable return since it started trading, and refusing to use it throws away the only price evidence
that exists. The question is whether that evidence is GOOD ENOUGH to beat simply scoring the pillar
neutral, because a noisy signal at full pillar weight is worse than an honest 50.

TEST. Take fully-covered names (true score known). For each, pretend it listed N months ago: compute
its return over ONLY the last N months from its own price history, rank that across the sample, and use
it as the technical pillar. Compare against neutral-fill on the same names. Repeat for N = 3, 6, 9, 12
so the answer is a curve, not a single verdict -- the honest question is not "does it work" but "from
how many months of history does it start working".

Two things this deliberately does NOT do:
  * it does not use the IPO offer price. Listing-day close is what the price file has, and offer-to-
    listing pop is an allotment artefact, not a trend.
  * it does not compare a 4-month return against a 12-month return on the same scale. They are ranked
    only against OTHER names measured over the SAME window, which is the only fair comparison.
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
            raise RuntimeError("NIFTY 500 root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand          # keep walking: take the OUTERMOST match, not the first


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
PRICES = os.path.join(ROOT, "ALPHA_RANKER", "data", "prices")
SRC = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(RES, "LISTING_PRICE_TEST.md")

BASE_W = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
              sector_macro_3y_score=11, ownership_3y_score=9, accumulation_3y_score=8)
TILT_CYC = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
                sector_macro_3y_score=3, ownership_3y_score=0, accumulation_3y_score=0)
TILT_NOT = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
                sector_macro_3y_score=-2, ownership_3y_score=0, accumulation_3y_score=0)
# a <1y listing lacks all of these; only quality, value and sector survive
GONE = ["ownership_3y_score", "stage_3y_score", "accumulation_3y_score", "growth_3y_score"]
AS_OF = pd.Timestamp("2026-07-20")          # the engine's own as-of for price-derived fields
TRADING_DAYS_PER_MONTH = 21


def wts(row):
    tilt = TILT_CYC if row.get("cyclicality_tag") == "Cyclical" else TILT_NOT
    return {k: BASE_W[k] + tilt[k] for k in BASE_W}


def sc(vals, w):
    num = sum(w[k] * v for k, v in vals.items() if v is not None and v == v)
    den = sum(w[k] for k, v in vals.items() if v is not None and v == v)
    return num / den if den > 0 else np.nan


def load_since_returns(symbols, months):
    """{sym: return over the last `months` of its own history}, as a fresh listing would see it."""
    out = {}
    need = int(months * TRADING_DAYS_PER_MONTH)
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
        if len(px) < need + 5:
            continue
        window = px.iloc[-need:]
        if window.iloc[0] > 0:
            out[s] = float(window.iloc[-1] / window.iloc[0] - 1.0)
    return out


def main():
    d = pd.read_csv(SRC)
    P = list(BASE_W)
    full = d[d[P].notna().all(axis=1)].copy()
    syms = full["symbol"].astype(str).tolist()

    lines = ["# Listing-price technical proxy for <1y names — does it beat scoring neutral?", "",
             f"Ground truth: {len(full)} fully-covered names. Simulated as if each had listed N months "
             f"ago: technical pillar = return over its last N months, ranked across the sample.",
             "", "| history | names priced | scheme | bias | mean abs err | rank corr | flips |",
             "|---|---|---|---|---|---|---|"]

    for months in (3, 6, 9, 12):
        rets = load_since_returns(syms, months)
        if len(rets) < 50:
            lines.append(f"| {months}m | {len(rets)} | insufficient price files | | | | |")
            continue
        sub = full[full["symbol"].astype(str).isin(rets)].copy()
        r = pd.Series([rets[s] for s in sub["symbol"].astype(str)], index=sub.index)
        # rank ONLY against names measured over the same window
        pct = r.rank(pct=True) * 100

        truth, est_lp, est_nu = [], [], []
        for i, row in sub.iterrows():
            w = wts(row)
            truth.append(sc({k: float(row[k]) for k in P}, w))
            base = {k: (None if k in GONE else float(row[k])) for k in P}
            lp = dict(base); lp["stage_3y_score"] = float(pct.loc[i])
            for k in ("ownership_3y_score", "accumulation_3y_score", "growth_3y_score"):
                lp[k] = 50.0                       # nothing observable -> neutral
            est_lp.append(sc(lp, w))
            nu = {k: (50.0 if v is None else v) for k, v in base.items()}
            est_nu.append(sc(nu, w))
        truth = np.array(truth)
        for nm, est in (("listing-price technical", np.array(est_lp)),
                        ("neutral-fill (baseline)", np.array(est_nu))):
            ok = ~np.isnan(est) & ~np.isnan(truth)
            bias = (est[ok] - truth[ok]).mean()
            mae = np.abs(est[ok] - truth[ok]).mean()
            rho = pd.Series(est[ok]).corr(pd.Series(truth[ok]), method="spearman")
            flips = int(((truth[ok] >= 40) & (est[ok] < 40)).sum()
                        + ((truth[ok] < 40) & (est[ok] >= 40)).sum())
            lines.append(f"| {months}m | {len(rets)} | {nm} | {bias:+.2f} | {mae:.2f} | "
                         f"{rho:.3f} | {flips} |")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
