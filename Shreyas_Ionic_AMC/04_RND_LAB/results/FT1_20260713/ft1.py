"""FT-1 (frozen @ dd60cc4): filing-time existence test, label-permutation placebo within quarter."""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(193)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FT1_20260713"
OUT.mkdir(parents=True, exist_ok=True)
V0, V1 = pd.Timestamp("2019-07-01"), pd.Timestamp("2024-06-30")
S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")
FWD = 20

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
idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC = IC[IC["Index Name"].str.strip().str.upper() == "NIFTY 50"]
nifty = pd.Series(pd.to_numeric(IC["Closing Index Value"], errors="coerce").values,
                  index=pd.to_datetime(IC["file_date"])).sort_index()
nifty = nifty[~nifty.index.duplicated()].reindex(C.index).ffill()
print("panels ready", flush=True)

qr = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/nse_quarterly_results_pit.parquet")
qr = qr[qr.period.astype(str).str.contains("Quarterly", na=False)]
qr["bdt"] = pd.to_datetime(qr.broadCastDate, format="%d-%b-%Y %H:%M:%S", errors="coerce")
qr["qend"] = pd.to_datetime(qr.toDate, format="%d-%b-%Y", errors="coerce")
qr = qr.dropna(subset=["bdt", "qend", "symbol"])
qr["symbol"] = qr.symbol.astype(str).str.strip()
qr = qr.sort_values("bdt").drop_duplicates(subset=["symbol", "qend"], keep="first")  # first announcement per quarter
qr = qr[qr.symbol.isin(C.columns)]
print(f"events after dedupe: {len(qr)}", flush=True)

NDATES = C.index
def fwd_ret(sym, when):
    loc = NDATES.searchsorted(when.normalize() + pd.Timedelta(days=0), side="right")
    # entry at NEXT tradeable close after broadcast: if broadcast after 15:30, next day; else same day close
    if when.hour >= 15 and when.minute >= 30 or when.hour >= 16:
        pass  # loc already points past broadcast date
    else:
        loc = max(loc - 1, 0)  # during/before market: same-day close
    j = C.columns.get_loc(sym)
    if loc + FWD >= len(NDATES):
        return np.nan
    p0, p1 = C.iat[loc, j], C.iat[loc + FWD, j]
    n0, n1 = nifty.iloc[loc], nifty.iloc[loc + FWD]
    if not (np.isfinite(p0) and np.isfinite(p1) and np.isfinite(n0) and np.isfinite(n1)):
        return np.nan
    gi = NDATES[loc]
    if not memb.at[gi, sym]:
        return np.nan
    return (p1 / p0 - 1) - (n1 / n0 - 1)

rows = []
for _, r in qr.iterrows():
    fr = fwd_ret(r.symbol, r.bdt)
    if np.isfinite(fr):
        rows.append(dict(sym=r.symbol, bdt=r.bdt, qend=r.qend, fr=fr,
                         hour=r.bdt.hour + r.bdt.minute / 60, dow=r.bdt.dayofweek,
                         lag=(r.bdt - r.qend).days))
EV = pd.DataFrame(rows)
EV["quarter"] = EV.qend.dt.to_period("Q")
print(f"scored events: {len(EV)}", flush=True)

def spread_test(mask_a, mask_b, tag):
    out = {}
    for wtag, w0, w1 in (("val", V0, V1), ("scr", S0, S1)):
        m = (EV.bdt >= w0) & (EV.bdt <= w1)
        a, b = EV[m & mask_a], EV[m & mask_b]
        sp = a.fr.mean() - b.fr.mean() if len(a) >= 30 and len(b) >= 30 else np.nan
        out[wtag] = (sp, len(a), len(b))
    # permutation within quarter on validate
    m = (EV.bdt >= V0) & (EV.bdt <= V1)
    sub = EV[m & (mask_a | mask_b)].copy()
    lab = (mask_a[m & (mask_a | mask_b)]).values
    perms = []
    for k in range(500):
        pl = lab.copy()
        for q, g in sub.groupby("quarter").groups.items():
            idx = sub.index.get_indexer(g)
            pl[idx] = rng.permutation(pl[idx])
        perms.append(abs(sub.fr.values[pl].mean() - sub.fr.values[~pl].mean()))
    p95 = float(np.percentile(perms, 95)) if perms else np.nan
    spv, na, nb = out["val"]; sps, _, _ = out["scr"]
    ok = (np.isfinite(spv) and abs(spv) > p95 and na >= 300 and nb >= 300
          and np.isfinite(sps) and np.sign(sps) == np.sign(spv))
    res = dict(cell=tag, val_spread=round(spv * 100, 2) if np.isfinite(spv) else None,
               perm95=round(p95 * 100, 2), n_a=na, n_b=nb,
               scr_spread=round(sps * 100, 2) if np.isfinite(sps) else None,
               verdict="CONFIRMED" if ok else "not confirmed")
    print(res, flush=True)
    return res

night = EV.hour >= 20
day = (EV.hour >= 9.25) & (EV.hour <= 15.5)
after_close = EV.hour > 15.5
fri = EV.dow == 4
res = [spread_test(night, day, "C1_night_vs_day"),
       spread_test(fri & after_close, (~fri) & after_close & (EV.dow <= 3), "C2_friAC_vs_weekAC"),
       spread_test(EV.lag > 45, EV.lag < 30, "C3_late_vs_prompt")]
df = pd.DataFrame(res)
nconf = int((df.verdict == "CONFIRMED").sum())
lines = [df.to_string(index=False), f"FAMILY: {'EXISTS' if nconf >= 2 else 'NOT CONFIRMED'} ({nconf}/3)"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "FT1_RESULTS.txt").write_text(txt, encoding="utf-8")
EV.to_parquet(OUT / "ft1_events.parquet", index=False)
