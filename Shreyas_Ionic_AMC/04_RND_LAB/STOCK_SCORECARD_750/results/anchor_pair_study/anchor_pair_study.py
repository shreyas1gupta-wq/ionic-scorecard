# -*- coding: utf-8 -*-
"""Anchor-pair study (Principal 2026-07-26): we run the MF model twice a year, 6M apart.
Which month pair (Jan-Jul ... Jun-Dec) yields the best recommendations?
Method: replay QFRA-1's exact decision logic (6M downside capture cutoff -> total-capture
rank -> BUY top-3; SELL = trailing-12M excess<0 & quadrant-4) at EVERY month-end anchor
2012..2024-07 on all 6 category sheets of MF Dashboard.xlsx; measure each cohort's forward
6M excess vs the category benchmark; aggregate by anchor-month pair with MEDIAN and 10%
TRIMMED MEAN. QFRA-2 (3-5y windows) is anchor-insensitive by construction and is not the
discriminator here."""
import os, tempfile
import numpy as np
import pandas as pd

TMP = os.path.join(tempfile.gettempdir(), "mfdash_check.xlsx")   # copied earlier from MF Dashboard.xlsx
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
    anchors = pd.date_range("2012-01-31", "2024-07-31", freq="ME")
    for t in anchors:
        idx6 = common[(common > t - pd.DateOffset(months=6)) & (common <= t)]
        if len(idx6) < 100:
            continue
        dn = br.loc[idx6] < 0
        up = br.loc[idx6] > 0
        bd = (1 + br.loc[idx6][dn]).prod() - 1
        bu = (1 + br.loc[idx6][up]).prod() - 1
        # forward window
        t2 = t + pd.DateOffset(months=6)
        f_idx = common[common <= t]
        fwd_idx = common[common <= t2]
        if not len(fwd_idx) or (t2 - fwd_idx[-1]).days > 15:
            continue
        t0p, t2p = f_idx[-1], fwd_idx[-1]
        bfwd = bb.loc[t2p] / bb.loc[t0p] - 1
        # trailing 12m for CJ
        t12 = t - pd.DateOffset(months=12)
        tr_idx = common[common <= t12]
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
            # trailing 12m excess
            p0i = s.index[s.index <= t12]
            p1i = s.index[s.index <= t]
            if not len(p0i):
                continue
            cj = (s.loc[p1i[-1]] / s.loc[p0i[-1]] - 1) - (bb.loc[p1i[-1]] / bb.loc[p0i[-1]] - 1) \
                if p0i[-1] in bb.index and p1i[-1] in bb.index else np.nan
            pk = 1 if (HC > 1 and FN < 1) else (3 if (HC < 1 and FN > 1) else 4)
            # forward
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
      f"{R['anchor'].min():%Y-%m}..{R['anchor'].max():%Y-%m}")


def trim_mean(x, p=0.10):
    x = np.sort(np.asarray(x.dropna()))
    k = int(len(x) * p)
    return np.mean(x[k:len(x) - k]) if len(x) > 2 * k else np.nan


rows = []
for m in range(1, 7):
    sub = R[R["month"].isin([m, m + 6])]
    buy = sub["buy_fwd"]
    spread = sub["buy_fwd"] - sub["sell_fwd"]
    rows.append(dict(pair=f"{m:02d}/{m+6:02d}", n=len(sub),
                     buy_med=np.nanmedian(buy) * 100, buy_trim=trim_mean(buy) * 100,
                     spr_med=np.nanmedian(spread) * 100, spr_trim=trim_mean(spread) * 100,
                     buy_hit=float((buy > 0).mean()) * 100))
P = pd.DataFrame(rows)
P["score"] = P[["buy_med", "buy_trim", "spr_med", "spr_trim"]].rank().mean(axis=1)
P = P.sort_values("score", ascending=False)
print("\nPAIR RESULTS (fwd 6M vs category benchmark, %, all categories pooled):")
print(P.round(2).to_string(index=False))
print("\nlegend: buy_med/trim = BUY-cohort forward excess (median / 10% trimmed mean); "
      "spr = BUY minus SELL cohort spread; buy_hit = % of formations with positive BUY excess.")
