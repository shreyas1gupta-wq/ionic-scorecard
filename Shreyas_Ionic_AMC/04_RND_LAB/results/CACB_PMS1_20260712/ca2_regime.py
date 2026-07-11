"""CA2-CARD (frozen @ a0d8f33): CA construction + Nifty-200dma defensive gate.
Defensive mode (index < 200dma at monthly review): no new entries; exit holdings below own 200dma.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(131)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CACB_PMS1_20260712"
CS = 0.0025
W0, W1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-06-30")

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
V = d.pivot_table(index="date", columns="symbol", values="volume"); V.index = C.index
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
def rsi_f(cf, n):
    dd_ = cf.diff()
    up = dd_.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dd_.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
rsi14 = rsi_f(C, 14)
mom3 = C / C.shift(63) - 1
upvol = (V.where(RET > 0, 0)).rolling(126).sum() / V.rolling(126).sum()
vwret = (RET * V).rolling(126).sum() / V.rolling(126).sum()

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_sales"] = ev.groupby("symbol")["sales"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
ev["ttm_sales_ly"] = ev.groupby("symbol")["ttm_sales"].shift(4)

def step(frame, symcol, val):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val]).groupby(symcol):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p

NPG = (step(ev, "symbol", "ttm_np") / step(ev, "symbol", "ttm_np_ly") - 1) * 100
SG = (step(ev, "symbol", "ttm_sales") / step(ev, "symbol", "ttm_sales_ly") - 1) * 100
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step(rat.rename(columns={"ROCE %": "roce"}), "nse_symbol", "roce")
ROE = step(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "roe")

idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC = IC[IC["Index Name"].str.strip().str.upper() == "NIFTY 50"]
nifty = pd.Series(pd.to_numeric(IC["Closing Index Value"], errors="coerce").values,
                  index=pd.to_datetime(IC["file_date"])).sort_index()
nifty = nifty[~nifty.index.duplicated()]
n200 = nifty.rolling(200).mean()
risk_on = (nifty >= n200).reindex(C.index, method="ffill").fillna(True)
print("panels ready", flush=True)

def wz(row, cap=3.0):
    m, s = np.nanmean(row), np.nanstd(row)
    if not np.isfinite(s) or s == 0:
        return row * 0
    return np.clip((row - m) / s, -cap, cap)

dates = C.index[(C.index >= W0) & (C.index <= W1)]
month_start = set(dd for i, dd in enumerate(dates) if i == 0 or dates[i - 1].month != dd.month)

def run(placebo=False):
    hold = {}
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in month_start:
            ron = bool(risk_on.iloc[gi])
            if not ron:
                for s in list(hold):
                    j = C.columns.get_loc(s)
                    px = C.iat[gi, j]
                    if not np.isfinite(px) or px < ma200.iat[gi, j]:
                        del hold[s]; turn += 1
            else:
                m100 = mom3.iloc[gi].where(memb.iloc[gi]).dropna().sort_values(ascending=False).index[:100]
                if placebo:
                    tgt = list(rng.choice(list(m100), size=min(20, len(m100)), replace=False))
                    for s in [x for x in hold if x not in tgt]:
                        del hold[s]; turn += 1
                    for s in tgt:
                        if s not in hold and len(hold) < 20:
                            hold[s] = C.iat[gi, C.columns.get_loc(s)]; turn += 1
                else:
                    qa = wz(ROCE.iloc[gi][m100].values); qb = wz(ROE.iloc[gi][m100].values)
                    with np.errstate(all="ignore"):
                        q = pd.Series(np.nanmean(np.vstack([qa, qb]), axis=0), index=m100)
                    q50 = q.dropna().sort_values(ascending=False).index[:50]
                    if len(q50) >= 10:
                        g = pd.Series(wz(NPG.iloc[gi][q50].values) + wz(SG.iloc[gi][q50].values), index=q50)
                        pva = pd.Series(wz(vwret.iloc[gi][q50].values) + wz(upvol.iloc[gi][q50].values), index=q50)
                        pick_g = list(g.dropna().sort_values(ascending=False).index[:10])
                        pick_p = [s for s in pva.dropna().sort_values(ascending=False).index if s not in pick_g][:10]
                        target = pick_g + pick_p
                        for s in list(hold):
                            j = C.columns.get_loc(s)
                            px = C.iat[gi, j]
                            appreciated = np.isfinite(px) and px > hold[s]
                            ob = (rsi14.iat[gi, j] >= 78) or (px >= 1.25 * ma50.iat[gi, j]) or \
                                 (gi >= 10 and px >= 1.35 * C.iat[gi - 10, j])
                            if (s not in target and not appreciated) or ob:
                                del hold[s]; turn += 1
                        for s in target:
                            if s not in hold and len(hold) < 20:
                                e_ = C.iat[gi, C.columns.get_loc(s)]
                                if np.isfinite(e_):
                                    hold[s] = e_; turn += 1
        r = 0.0
        if hold and gi + 1 < len(C.index):
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) * len(hold) / 20 if vals else 0.0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    r = r - (turn / len(daily)) * 2 * CS / 20
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    eqc = (1 + r).cumprod()
    return (eqc.iloc[-1] ** (1 / yrs) - 1, (eqc / eqc.cummax() - 1).min(),
            r.mean() / r.std(ddof=1) * np.sqrt(252), turn / 20 / yrs * 100 / 2, r, eqc)

cagr, dd_, sh, churn, r, eqc = run()
print(f"CA2: CAGR {cagr*100:+.1f}% maxDD {dd_*100:.1f}% Sharpe {sh:.2f} churn {churn:.0f}%", flush=True)
yr = r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1)
print(" | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()), flush=True)
null = []
for k in range(25):
    c_, _, _, _, _, _ = run(placebo=True)
    null.append(c_)
p95 = np.percentile(null, 95)
bars = {"CAGR>=12": cagr >= 0.12, "DD<=25": dd_ >= -0.25, "beat_placebo95": cagr > p95}
verdict = "DELIVERED-CLASS" if all(bars.values()) else ("KILL" if cagr < np.mean(null) else "PARK")
lines = [f"CA2 (regime-gated): CAGR {cagr*100:+.1f}% maxDD {dd_*100:.1f}% Sharpe {sh:.2f} churn {churn:.0f}%",
         f"gated placebo: mean {np.mean(null)*100:.1f}%, 95th {p95*100:.1f}%",
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "CA2_RESULTS.txt").write_text(txt, encoding="utf-8")
eqc.to_frame("equity").to_csv(OUT / "ca2_equity.csv")
