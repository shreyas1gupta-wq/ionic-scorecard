"""VBT (frozen @ 4d95976): VIX-breadth thrust, 4 cells, same-exit placebo x200 + lag-decay."""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(173)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/VBT_20260713"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0008
V1E = pd.Timestamp("2024-06-30"); S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")

d = pd.read_parquet(ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet")
ts = pd.to_datetime(d.timestamp)
d["date"] = ts.dt.tz_convert("Asia/Kolkata").dt.date
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
snaps = {dd: set(g["Ticker"].astype(str).str.strip()) for dd, g in uni.groupby("snap")}
snap_dates = sorted(snaps)
ever = set().union(*snaps.values())
d = d[d.symbol.isin(ever)]
C = d.pivot_table(index="date", columns="symbol", values="close"); C.index = pd.to_datetime(C.index); C = C.sort_index()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
above20 = (C > C.rolling(20).mean()) & memb
breadth = above20.sum(axis=1) / memb.sum(axis=1).replace(0, np.nan)
print("breadth ready", flush=True)

idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC["nm"] = IC["Index Name"].str.strip().str.upper()
IC["date"] = pd.to_datetime(IC["file_date"])
def iser(nm):
    g = IC[IC.nm == nm].set_index("date").sort_index()
    s = pd.to_numeric(g["Closing Index Value"], errors="coerce")
    return s[~s.index.duplicated()]
nifty = iser("NIFTY 50")
vix = iser("INDIA VIX")
vix_pct = vix.rolling(252).rank(pct=True)
b = breadth.reindex(nifty.index).ffill(limit=3)
vp = vix_pct.reindex(nifty.index)
nret = nifty.pct_change()
N = len(nifty.index)
dates = nifty.index

def events(thresh, vixgate):
    ev = []
    bv = b.values
    for t in range(11, N):
        if not (np.isfinite(bv[t]) and np.isfinite(bv[t - 1])):
            continue
        if bv[t] >= thresh and bv[t - 1] < thresh:
            win = bv[t - 10:t]
            if np.nanmin(win) < 0.40:
                if vixgate:
                    trough = t - 10 + int(np.nanargmin(win))
                    v = vp.iloc[trough]
                    if not (np.isfinite(v) and v >= 0.70):
                        continue
                ev.append(t)
    return ev

def episode(t_entry):
    # enter at close[t_entry]; exit when breadth<0.40 (at that close) or 60td cap
    if t_entry + 1 >= N:
        return None, None
    e = nifty.iloc[t_entry]
    for k in range(t_entry + 1, min(t_entry + 61, N)):
        if np.isfinite(b.values[k]) and b.values[k] < 0.40:
            return (nifty.iloc[k] / e - 1) - 2 * COST, k
    k = min(t_entry + 60, N - 1)
    return (nifty.iloc[k] / e - 1) - 2 * COST, k

CELLS = [("V1_t60", 0.60, False), ("V2_t65", 0.65, False), ("V3_t60vix", 0.60, True), ("V4_t65vix", 0.65, True)]
rows, best_series = [], {}
for tag, th, vg in CELLS:
    ev = events(th, vg)
    res = [(dates[t], *episode(t + 1)) for t in ev if t + 2 < N]
    res = [(d_, r, k) for d_, r, k in res if r is not None]
    dts = pd.DatetimeIndex([x[0] for x in res]); real = np.array([x[1] for x in res])
    mv, ms = dts <= V1E, (dts >= S0) & (dts <= S1)
    n_val = int(mv.sum())
    # lag decay
    lag_means = {}
    for lag in (0, 1, 2, 5):
        rr = [episode(t + 1 + lag)[0] for t in ev if t + 2 + lag < N]
        rr = [x for x in rr if x is not None]
        lag_means[lag] = float(np.mean(rr)) if rr else np.nan
    # same-exit placebo
    nulls_v, nulls_s = [], []
    all_t = np.arange(260, N - 62)
    val_t = all_t[dates[all_t] <= V1E]; scr_t = all_t[(dates[all_t] >= S0) & (dates[all_t] <= S1)]
    for k in range(200):
        if n_val >= 3:
            pick = rng.choice(val_t, size=n_val, replace=False)
            rr = [episode(t + 1)[0] for t in pick]
            rr = [x for x in rr if x is not None]
            if rr: nulls_v.append(np.mean(rr))
        if ms.sum() >= 1 and len(scr_t) > int(ms.sum()):
            pick2 = rng.choice(scr_t, size=int(ms.sum()), replace=False)
            rr2 = [episode(t + 1)[0] for t in pick2]
            rr2 = [x for x in rr2 if x is not None]
            if rr2: nulls_s.append(np.mean(rr2))
    p95 = float(np.percentile(nulls_v, 95)) if len(nulls_v) >= 20 else np.nan
    pms = float(np.mean(nulls_s)) if nulls_s else np.nan
    vm = float(real[mv].mean()) if n_val else np.nan
    sm = float(real[ms].mean()) if ms.sum() else np.nan
    scr_alpha = sm - pms if np.isfinite(sm) and np.isfinite(pms) else np.nan
    lag_ok = np.isfinite(lag_means[5]) and np.isfinite(lag_means[0]) and lag_means[0] > 0 and lag_means[5] < 0.6 * lag_means[0]
    if n_val < 12:
        verdict = "NOT-ADJUDICABLE"
    else:
        verdict = "PASS" if (np.isfinite(vm) and vm > p95 and np.isfinite(scr_alpha) and scr_alpha > 0 and lag_ok) else "FAIL"
    rows.append(dict(cell=tag, n=len(res), n_val=n_val, n_scr=int(ms.sum()),
                     val=round(vm * 100, 2) if np.isfinite(vm) else None,
                     plac95=round(p95 * 100, 2) if np.isfinite(p95) else None,
                     scr_alpha=round(scr_alpha * 100, 2) if np.isfinite(scr_alpha) else None,
                     lag0=round(lag_means[0] * 100, 2), lag5=round(lag_means[5] * 100, 2) if np.isfinite(lag_means[5]) else None,
                     verdict=verdict))
    print(rows[-1], flush=True)
    # daily series for corr (best-cell later): long between entry and exit
    pos = pd.Series(0.0, index=dates)
    for d_, r, kend in res:
        t0 = dates.get_loc(d_) + 1
        pos.iloc[t0 + 1:kend + 1] = 1.0  # returns accrue from day after entry-close
    best_series[tag] = pos * nret

df = pd.DataFrame(rows)
npass = int((df.verdict == "PASS").sum())
book = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv",
                   index_col=0, parse_dates=True)["total"]
passing = df[df.verdict == "PASS"].cell.tolist() or df.sort_values("val", ascending=False).cell.tolist()[:1]
g = best_series[passing[0]]
common = g.index.intersection(book.index)
corr_m = float(pd.concat([g.reindex(common), book.reindex(common) / 1e7], axis=1).resample("ME").sum().corr().iloc[0, 1])
adopt = (npass >= 2) and (corr_m < 0.25)
lines = [df.to_string(index=False),
         f"cells passed: {npass}/4 | monthly corr({passing[0]}, book) = {corr_m:+.2f} (bar < +0.25 signed)",
         f"VERDICT: {'ADOPT-CANDIDATE' if adopt else 'NOT ADOPTED'}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "VBT_RESULTS.txt").write_text(txt, encoding="utf-8")
