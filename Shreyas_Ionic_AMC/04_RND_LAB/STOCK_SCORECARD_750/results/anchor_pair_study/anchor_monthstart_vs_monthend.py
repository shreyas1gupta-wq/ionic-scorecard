# -*- coding: utf-8 -*-
"""Month-START vs month-END anchors (Principal ask, 2026-08-04):
"check 1 april vs 30 april start same oct and other months".

The deployed cadence anchors on the month-END close (30-Apr / 31-Oct). This tests the alternative
literally: re-run the identical replay with anchors on the month-START (1-Apr / 1-Oct), for ALL SIX
month pairs, and compare on the pre-registered measures (median + 10% trimmed mean) plus hit rate.

Note on what a month-start anchor MEANS mechanically: the capture window is (t - 6 months, t], so an
anchor of 1-Apr closes its window on the last trading day <= 1-Apr, i.e. it reads essentially the
same data as a 31-Mar anchor. Month-start is therefore not a small tweak to the same window; it is a
~one-month backward SHIFT of the whole window. That is the real question being tested.

Everything else is byte-identical to anchor_pair_study.py so results are comparable. READ-ONLY.
Writes ANCHOR_MS_VS_ME.csv + prints the comparison.
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
LAB = {1: "Jan/Jul", 2: "Feb/Aug", 3: "Mar/Sep", 4: "Apr/Oct", 5: "May/Nov", 6: "Jun/Dec"}


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


def formations(nav, bb, common, br, cut, anchors):
    """One row per (anchor) with the BUY/SELL cohort forward excess. Identical logic to
    anchor_pair_study.py; only the `anchors` sequence differs between conventions."""
    out = []
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
        out.append(dict(anchor=t, month=t.month,
                        win_end=str(f_idx[-1].date()),   # the trading day the window really closes on
                        buy_fwd=buy["fwd"].mean() if len(buy) else np.nan,
                        sell_fwd=sell["fwd"].mean() if len(sell) else np.nan))
    return out


def trim_mean(x, p=0.10):
    x = np.sort(np.asarray(pd.Series(x).dropna()))
    k = int(len(x) * p)
    return np.mean(x[k:len(x) - k]) if len(x) > 2 * k else np.nan


ANCH = {
    "month-END  (30-Apr / 31-Oct)": pd.date_range("2012-01-31", "2024-07-31", freq="ME"),
    "month-START (1-Apr / 1-Oct)": pd.date_range("2012-01-01", "2024-07-01", freq="MS"),
}

rows = []
for cat, (bname, cut) in CATS.items():
    nav = load(cat)
    IDX = load("Indices") if cat == list(CATS)[0] else IDX          # load Indices once
    b = IDX[bname].dropna()
    common = nav.index.intersection(b.index)
    nav_c, bb = nav.loc[common], b.loc[common]
    br = bb.pct_change()
    for conv, anchors in ANCH.items():
        for r in formations(nav_c, bb, common, br, cut, anchors):
            r.update(cat=cat, conv=conv)
            rows.append(r)

R = pd.DataFrame(rows)
print("formations by convention:")
print(R.groupby("conv").size().to_string())

# sanity check the mechanical point: what date does each convention's window actually close on?
print("\nWhat trading day does the window really close on? (Apr anchors, flexi, first 4 years)")
chk = R[(R["cat"] == "flexi") & (R["month"] == 4)][["conv", "anchor", "win_end"]].head(8)
print(chk.to_string(index=False))

out = []
for conv in ANCH:
    S = R[R["conv"] == conv]
    for m in range(1, 7):
        sub = S[S["month"].isin([m, m + 6])]
        buy = sub["buy_fwd"]
        out.append(dict(conv=conv, pair=LAB[m], n=len(sub),
                        med=np.nanmedian(buy) * 100, trim=trim_mean(buy) * 100,
                        mean=np.nanmean(buy) * 100,
                        hit=float((buy > 0).mean()) * 100))
P = pd.DataFrame(out)

for conv in ANCH:
    print("\n" + "=" * 78)
    print(conv.upper())
    print("=" * 78)
    sub = P[P["conv"] == conv].sort_values("trim", ascending=False)
    print(sub[["pair", "n", "med", "trim", "mean", "hit"]].round(2).to_string(index=False))

print("\n" + "=" * 78)
print("HEAD TO HEAD, same pair, both conventions (presented measure = 10% trim)")
print("=" * 78)
piv = P.pivot(index="pair", columns="conv", values=["trim", "med", "hit"])
print(piv.round(2).to_string())

E, S_ = list(ANCH)[0], list(ANCH)[1]
ao_e = P[(P["conv"] == E) & (P["pair"] == "Apr/Oct")].iloc[0]
ao_s = P[(P["conv"] == S_) & (P["pair"] == "Apr/Oct")].iloc[0]
print(f"\nAPR/OCT VERDICT:  month-END trim {ao_e['trim']:+.2f}% (med {ao_e['med']:+.2f}%, "
      f"hit {ao_e['hit']:.1f}%)   vs   month-START trim {ao_s['trim']:+.2f}% "
      f"(med {ao_s['med']:+.2f}%, hit {ao_s['hit']:.1f}%)")
print(f"month-END advantage on the presented measure: {ao_e['trim'] - ao_s['trim']:+.2f}pp")

P.to_csv(os.path.join(HERE, "ANCHOR_MS_VS_ME.csv"), index=False)
print("\nwrote", os.path.join(HERE, "ANCHOR_MS_VS_ME.csv"))
