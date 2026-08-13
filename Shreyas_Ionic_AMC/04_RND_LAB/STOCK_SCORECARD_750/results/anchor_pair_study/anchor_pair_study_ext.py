# -*- coding: utf-8 -*-
"""Anchor-pair study, EXTENDED (Principal asks, 2026-08-04).

Adds to `anchor_pair_study.py` (identical formation logic, so the 906-formation count and the
median / 10%-trimmed-mean columns must reconcile exactly with the 2026-07-26 run):

  1. PLAIN UNTRIMMED MEAN for the BUY cohort, the SELL cohort and the BUY-SELL spread.
     ("what are the results without trimming?")
  2. The SELL cohort reported in full, per pair — this is the backtest credibility of QFRA-1's
     SELL, which the Principal wants leaned on.
  3. SMALLCAP-ONLY breakout, all pairs, trimmed and untrimmed side by side, with Apr/Oct called
     out. ("for april/oct show only smallcap results trimmed no trimmed separately")

The anchor is the month-END close (pd.date_range(..., freq='ME')): "Apr/Oct" means data through
30-Apr and 31-Oct.

Writes ANCHOR_PAIR_EXT.csv + prints the tables. READ-ONLY on the workbook.
"""
import os
import tempfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(tempfile.gettempdir(), "mfdash_check.xlsx")
CATS = {"small": ("NIFTY SMALLCAP 250", 1.0), "flexi": ("NIFTY 500", 1.0),
        "large": ("NIFTY 100", 0.9), "largemid": ("NIFTY 250", 1.0),
        "mid": ("NIFTY MIDCAP 150", 0.8), "multi": ("NIFTY MULTICAP 50:25:25", 0.9)}


def load(sheet):
    raw = pd.read_excel(TMP, sheet_name=sheet, header=1)
    raw = raw.rename(columns={raw.columns[0]: "date"})
    raw = raw[raw["date"].apply(lambda v: not isinstance(v, str))]
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw.dropna(subset=["date"]).set_index("date").sort_index()
    cols = []
    for c in raw.columns:
        if str(c).startswith("Unnamed"):
            break
        cols.append(c)
    return raw[cols].apply(pd.to_numeric, errors="coerce")


IDX = load("Indices")
results = []
for cat, (bname, cut) in CATS.items():
    nav = load(cat)
    b = IDX[bname].dropna()
    common = nav.index.intersection(b.index)
    nav, bb = nav.loc[common], b.loc[common]
    br = bb.pct_change()
    anchors = pd.date_range("2012-01-31", "2024-07-31", freq="ME")   # month-END anchors
    for t in anchors:
        idx6 = common[(common > t - pd.DateOffset(months=6)) & (common <= t)]
        if len(idx6) < 100:
            continue
        dn = br.loc[idx6] < 0
        up = br.loc[idx6] > 0
        bd = (1 + br.loc[idx6][dn]).prod() - 1
        bu = (1 + br.loc[idx6][up]).prod() - 1
        t2 = t + pd.DateOffset(months=6)
        f_idx = common[common <= t]
        fwd_idx = common[common <= t2]
        if not len(fwd_idx) or (t2 - fwd_idx[-1]).days > 15:
            continue
        t0p, t2p = f_idx[-1], fwd_idx[-1]
        bfwd = bb.loc[t2p] / bb.loc[t0p] - 1
        t12 = t - pd.DateOffset(months=12)
        recs = []
        for c in nav.columns:
            s = nav[c].dropna()
            si = s.index.intersection(idx6)
            if len(si) < 100 or s.index[-1] < t or s.index[0] > t12:
                continue
            fr = s.pct_change().loc[si]
            fd = (1 + fr[dn.reindex(si).fillna(False)]).prod() - 1
            fu = (1 + fr[up.reindex(si).fillna(False)]).prod() - 1
            if bd == 0 or bu == 0:
                continue
            FN = fd / bd
            UC = fu / bu
            if FN == 0:
                continue
            HC = UC / FN
            p0i = s.index[s.index <= t12]
            p1i = s.index[s.index <= t]
            if not len(p0i):
                continue
            cj = (s.loc[p1i[-1]] / s.loc[p0i[-1]] - 1) - (bb.loc[p1i[-1]] / bb.loc[p0i[-1]] - 1) \
                if p0i[-1] in bb.index and p1i[-1] in bb.index else np.nan
            pk = 1 if (HC > 1 and FN < 1) else (3 if (HC < 1 and FN > 1) else 4)
            f1i = s.index[s.index <= t2]
            if not len(f1i) or (t2 - f1i[-1]).days > 15:
                continue
            fwd = (s.loc[f1i[-1]] / s.loc[p1i[-1]] - 1) - bfwd
            recs.append((c, FN, HC, cj, pk, fwd))
        if len(recs) < 5:
            continue
        df = pd.DataFrame(recs, columns=["fund", "FN", "HC", "cj", "pk", "fwd"])
        df["rank"] = df["HC"].rank(ascending=False, method="min")
        buy = df[(df["rank"] < 4) & (df["FN"] <= cut)]
        sell = df[(df["cj"] < 0) & (df["pk"] == 4)]
        results.append(dict(cat=cat, anchor=t, month=t.month,
                            buy_fwd=buy["fwd"].mean() if len(buy) else np.nan,
                            sell_fwd=sell["fwd"].mean() if len(sell) else np.nan,
                            n_buy=len(buy), n_sell=len(sell)))

R = pd.DataFrame(results)
print(f"formations: {len(R)} across {R['cat'].nunique()} categories, "
      f"{R['anchor'].min():%Y-%m}..{R['anchor'].max():%Y-%m}   "
      f"(must reconcile with the 2026-07-26 run: 906)")


def trim_mean(x, p=0.10):
    x = np.sort(np.asarray(pd.Series(x).dropna()))
    k = int(len(x) * p)
    return np.mean(x[k:len(x) - k]) if len(x) > 2 * k else np.nan


def block(sub, tag):
    """Median / PLAIN MEAN / 10% trimmed mean for buy, sell and spread + hit rates."""
    buy, sell = sub["buy_fwd"], sub["sell_fwd"]
    spread = sub["buy_fwd"] - sub["sell_fwd"]
    return dict(
        pair=tag, n=len(sub),
        buy_med=np.nanmedian(buy) * 100, buy_mean=np.nanmean(buy) * 100,
        buy_trim=trim_mean(buy) * 100, buy_hit=float((buy > 0).mean()) * 100,
        sell_med=np.nanmedian(sell) * 100, sell_mean=np.nanmean(sell) * 100,
        sell_trim=trim_mean(sell) * 100,
        # a SELL "works" when the sold cohort went on to underperform its benchmark
        sell_hit=float((sell < 0).mean()) * 100,
        spr_med=np.nanmedian(spread) * 100, spr_mean=np.nanmean(spread) * 100,
        spr_trim=trim_mean(spread) * 100)


LAB = {1: "Jan/Jul", 2: "Feb/Aug", 3: "Mar/Sep", 4: "Apr/Oct", 5: "May/Nov", 6: "Jun/Dec"}

# ---- 1. all categories pooled, every pair, trimmed AND untrimmed ---------------
allp = pd.DataFrame([block(R[R["month"].isin([m, m + 6])], LAB[m]) for m in range(1, 7)])
allp = allp.sort_values("buy_med", ascending=False)
print("\n" + "=" * 108)
print("ALL CATEGORIES POOLED - fwd 6M excess vs category benchmark (%)")
print("=" * 108)
print(allp[["pair", "n", "buy_med", "buy_mean", "buy_trim", "buy_hit",
            "sell_med", "sell_mean", "sell_trim", "sell_hit"]].round(2).to_string(index=False))
print("\nspread (BUY minus SELL cohort):")
print(allp[["pair", "spr_med", "spr_mean", "spr_trim"]].round(2).to_string(index=False))

# ---- 2. SMALLCAP ONLY, every pair, trimmed AND untrimmed ----------------------
S = R[R["cat"] == "small"]
smp = pd.DataFrame([block(S[S["month"].isin([m, m + 6])], LAB[m]) for m in range(1, 7)])
smp = smp.sort_values("buy_med", ascending=False)
print("\n" + "=" * 108)
print("SMALLCAP ONLY - fwd 6M excess vs NIFTY SMALLCAP 250 (%)")
print("=" * 108)
print(smp[["pair", "n", "buy_med", "buy_mean", "buy_trim", "buy_hit",
           "sell_med", "sell_mean", "sell_trim", "sell_hit"]].round(2).to_string(index=False))

# ---- 3. Apr/Oct called out, smallcap vs pooled, trimmed vs untrimmed ---------
print("\n" + "=" * 108)
print("APR/OCT ISOLATED  (anchor = month-END close: 30-Apr / 31-Oct)")
print("=" * 108)
ao_all = block(R[R["month"].isin([4, 10])], "Apr/Oct  ALL CATS")
ao_sml = block(S[S["month"].isin([4, 10])], "Apr/Oct  SMALLCAP")
jd_sml = block(S[S["month"].isin([6, 12])], "Jun/Dec  SMALLCAP")
out = pd.DataFrame([ao_all, ao_sml, jd_sml])
print(out[["pair", "n", "buy_med", "buy_mean", "buy_trim", "buy_hit",
           "sell_med", "sell_mean", "sell_trim", "sell_hit"]].round(2).to_string(index=False))

# per-category BUY for Apr/Oct, untrimmed vs trimmed
print("\nApr/Oct BUY cohort by category (untrimmed mean vs trimmed vs median):")
rows = []
for cat in CATS:
    sub = R[(R["cat"] == cat) & (R["month"].isin([4, 10]))]
    if not len(sub):
        continue
    rows.append(dict(cat=cat, n=len(sub),
                     med=np.nanmedian(sub["buy_fwd"]) * 100,
                     mean=np.nanmean(sub["buy_fwd"]) * 100,
                     trim=trim_mean(sub["buy_fwd"]) * 100,
                     hit=float((sub["buy_fwd"] > 0).mean()) * 100))
print(pd.DataFrame(rows).round(2).to_string(index=False))

allp.assign(scope="pooled").to_csv(os.path.join(HERE, "ANCHOR_PAIR_EXT.csv"), index=False)
smp.assign(scope="smallcap").to_csv(os.path.join(HERE, "ANCHOR_PAIR_EXT.csv"),
                                    index=False, mode="a", header=False)
print("\nwrote", os.path.join(HERE, "ANCHOR_PAIR_EXT.csv"))
print("\nlegend: med/mean/trim = median / PLAIN UNTRIMMED mean / 10% trimmed mean of each "
      "formation's cohort-average forward 6M excess. buy_hit = % of formations with positive "
      "BUY excess. sell_hit = % of formations where the SELL cohort went on to UNDERPERFORM "
      "(higher = the sell call worked more often).")
