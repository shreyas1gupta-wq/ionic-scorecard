"""POS-2 portfolio-level sim (frozen card @ a379303): 15 slots EW, fill on triggers (55d-break +
stage-2 + growth>=20 + ROCE>=12), exit close<200dma or -25%. Daily NAV -> CAGR/DD/Sharpe/churn.
Placebo x40 full sims: random stage-2 entries at the SAME trigger dates, same exits -> CAGR null.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(107)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/POSITIONAL_20260712"
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
H = d.pivot_table(index="date", columns="symbol", values="high"); H.index = C.index
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
stage2 = (C > ma200) & (ma50 > ma200) & memb

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)

def step(val, frame, symcol):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val]).groupby(symcol):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p

NPG = (step("ttm_np", ev, "symbol") / step("ttm_np_ly", ev, "symbol") - 1) * 100
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step("roce", rat.rename(columns={"ROCE %": "roce"}), "nse_symbol")

brk = C > H.shift(1).rolling(55).max()
fund = (NPG >= 20) & (ROCE >= 12)
sig = (brk & stage2 & fund).loc[W0:W1]
dates = sig.index
NROW = len(C.index)

def portfolio(sig_frame, placebo=False):
    slots = {}
    daily = []
    entries = exits = 0
    for dd in dates[:-1]:
        gi = C.index.get_loc(dd)
        # exits
        for sym in list(slots):
            j = C.columns.get_loc(sym)
            c_ = C.iat[gi, j]
            if np.isfinite(c_) and (c_ <= slots[sym] * 0.75 or c_ < ma200.iat[gi, j]):
                del slots[sym]; exits += 1
        # entries
        todays = sig_frame.loc[dd]
        cands = list(todays.index[todays.fillna(False)])
        if placebo and cands:
            elig = list(stage2.iloc[gi][stage2.iloc[gi]].index)
            cands = list(rng.choice(elig, size=min(len(cands), len(elig)), replace=False)) if elig else []
        for s in cands:
            if len(slots) >= 15:
                break
            if s not in slots:
                e_ = C.iat[gi, C.columns.get_loc(s)]
                if np.isfinite(e_):
                    slots[s] = e_; entries += 1
        # daily ret (next day)
        r = 0.0
        if slots and gi + 1 < NROW:
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in slots]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) * len(slots) / 15 if vals else 0.0
        r -= (entries + exits) * CS / 15
        entries = exits = 0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    eqc = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return ((eqc.iloc[-1]) ** (1 / yrs) - 1, (eqc / eqc.cummax() - 1).min(),
            r.mean() / r.std(ddof=1) * np.sqrt(252), eqc)

cagr, dd_, sh, eqc = portfolio(sig)
print(f"POS-2 PORTFOLIO: CAGR {cagr*100:+.1f}% | maxDD {dd_*100:.1f}% | Sharpe {sh:.2f}", flush=True)
yr = eqc.pct_change().groupby(eqc.index.year).apply(lambda x: (1 + x).prod() - 1)
print(" | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()), flush=True)
null = []
for k in range(40):
    c_, _, _, _ = portfolio(sig, placebo=True)
    null.append(c_)
    if k % 10 == 0:
        print(f"  placebo {k}: {c_*100:.1f}%", flush=True)
null = np.array(null)
p95 = np.percentile(null, 95)
delivered = (cagr >= 0.35) and (dd_ >= -0.25) and (cagr > p95)
lines = [f"POS-2 portfolio: CAGR {cagr*100:+.1f}% maxDD {dd_*100:.1f}% Sharpe {sh:.2f}",
         f"placebo CAGR mean {null.mean()*100:.1f}%, 95th {p95*100:.1f}%",
         f"bars: CAGR>=35 {'P' if cagr>=0.35 else 'F'} | DD<=25 {'P' if dd_>=-0.25 else 'F'} | beat placebo95 {'P' if cagr>p95 else 'F'}",
         f"VERDICT: {'DELIVERED' if delivered else 'NOT DELIVERED (exact numbers above)'}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "POS2_PORTFOLIO.txt").write_text(txt, encoding="utf-8")
eqc.to_frame("equity").to_csv(OUT / "pos2_equity.csv")
