"""CA/CB/PMS1 engine (frozen @ a752ec3). Three portfolio constructions, shared loaders.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(127)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CACB_PMS1_20260712"
OUT.mkdir(parents=True, exist_ok=True)
CS = 0.0025
W0, W1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-06-30")

print("loading...", flush=True)
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
L = d.pivot_table(index="date", columns="symbol", values="low"); L.index = C.index
V = d.pivot_table(index="date", columns="symbol", values="volume"); V.index = C.index
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma20 = C.rolling(20).mean(); ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
hi52 = C.rolling(252).max()
atr14 = (H - L).rolling(14).mean()
def rsi_f(cf, n):
    dd_ = cf.diff()
    up = dd_.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dd_.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
rsi14 = rsi_f(C, 14)
mom3 = C / C.shift(63) - 1
rs126 = (C / C.shift(126) - 1).rank(axis=1, pct=True)
upvol = (V.where(RET > 0, 0)).rolling(126).sum() / V.rolling(126).sum()
vwret = (RET * V).rolling(126).sum() / V.rolling(126).sum()

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_sales"] = ev.groupby("symbol")["sales"].rolling(4).sum().values
ev["ttm_eps"] = ev.groupby("symbol")["eps"].rolling(4).sum().values
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
TTM_EPS = step(ev, "symbol", "ttm_eps")
PE = (C / TTM_EPS).where(TTM_EPS > 0)
PE_PCT3 = PE.rolling(756, min_periods=400).rank(pct=True)
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step(rat.rename(columns={"ROCE %": "roce"}), "nse_symbol", "roce")
ROE = step(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "roe")
meta = pd.read_csv(ROOT / "datasets/india_stock_metadata/india.csv")
sector = {str(r.ticker).strip(): str(r.sector) for _, r in meta.iterrows()}
sec_of = pd.Series({c: sector.get(c, "UNK") for c in C.columns})
print("panels ready", flush=True)

def wz(row, cap=3.0):
    m, s = np.nanmean(row), np.nanstd(row)
    if not np.isfinite(s) or s == 0:
        return row * 0
    return np.clip((row - m) / s, -cap, cap)

def perf(r):
    eqc = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (eqc.iloc[-1] ** (1 / yrs) - 1, (eqc / eqc.cummax() - 1).min(),
            r.mean() / r.std(ddof=1) * np.sqrt(252), eqc)

dates = C.index[(C.index >= W0) & (C.index <= W1)]
month_start = [dd for i, dd in enumerate(dates) if i == 0 or dates[i - 1].month != dd.month]
q_start = [dd for dd in month_start if dd.month in (1, 4, 7, 10)]

# ================= CA =================
def run_ca(placebo=False):
    hold = {}
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in month_start:
            m100 = mom3.iloc[gi].where(memb.iloc[gi]).dropna().sort_values(ascending=False).index[:100]
            if placebo:
                new20 = list(rng.choice(list(m100), size=min(20, len(m100)), replace=False))
                sells = [s for s in hold if s not in new20]
                for s in sells:
                    del hold[s]; turn += 1
                for s in new20:
                    if s not in hold and len(hold) < 20:
                        hold[s] = C.iat[gi, C.columns.get_loc(s)]; turn += 1
            else:
                qa = wz(ROCE.iloc[gi][m100].values); qb = wz(ROE.iloc[gi][m100].values)
                with np.errstate(all="ignore"):
                    q = pd.Series(np.nanmean(np.vstack([qa, qb]), axis=0), index=m100)  # nan-aware (ROE covers ~56 syms only)
                q50 = q.dropna().sort_values(ascending=False).index[:50]
                if len(q50) >= 10:
                    g = pd.Series(wz(NPG.iloc[gi][q50].values) + wz(SG.iloc[gi][q50].values), index=q50)
                    pva = pd.Series(wz(vwret.iloc[gi][q50].values) + wz(upvol.iloc[gi][q50].values), index=q50)
                    pick_g = list(g.dropna().sort_values(ascending=False).index[:10])
                    pick_p = [s for s in pva.dropna().sort_values(ascending=False).index if s not in pick_g][:10]
                    target = pick_g + pick_p
                    # asymmetric review: keep appreciated non-overbought holds
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
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    churn = turn / 20 / yrs * 100 / 2
    r = r - 0.0  # costs via churn note; apply approximate drag:
    r = r - (turn / len(daily)) * 2 * CS / 20
    return r, churn

ca_r, ca_churn = run_ca()
cagr, dd_, sh, eqc = perf(ca_r)
print(f"CA: CAGR {cagr*100:+.1f}% maxDD {dd_*100:.1f}% Sharpe {sh:.2f} churn {ca_churn:.0f}%/yr", flush=True)
null_ca = []
for k in range(25):
    pr_, _ = run_ca(placebo=True)
    null_ca.append(perf(pr_)[0])
print(f"CA placebo CAGR mean {np.mean(null_ca)*100:.1f}%, 95th {np.percentile(null_ca,95)*100:.1f}%", flush=True)

# ================= CB =================
def run_cb(cell, placebo=False):
    hold = []
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in q_start:
            elig = memb.iloc[gi]
            pe_row = PE.iloc[gi].where(elig)
            secmed = pe_row.groupby(sec_of).transform("median")
            with np.errstate(all='ignore'):
                val = pd.Series(np.nanmean(np.vstack([wz(-pe_row.values), wz(-(pe_row / secmed).values),
                                wz(-(PE_PCT3.iloc[gi].where(elig)).values)]), axis=0), index=C.columns)  # nan-aware law
            top50 = val.dropna().sort_values(ascending=False).index[:50]
            if len(top50) >= 10:
                if placebo:
                    pick = list(rng.choice(list(top50), size=10, replace=False))
                else:
                    if cell == "atr":
                        wash = ((ma200.iloc[gi] - C.iloc[gi]) / atr14.iloc[gi])[top50]
                    elif cell == "pct200":
                        wash = (ma200.iloc[gi] / C.iloc[gi] - 1)[top50]
                    elif cell == "rsi":
                        wash = (-rsi14.iloc[gi])[top50]
                    else:
                        wash = (1 - C.iloc[gi] / hi52.iloc[gi])[top50]
                    pick = list(wash.dropna().sort_values(ascending=False).index[:10])
                turn += len(set(pick) ^ set(hold))
                hold = pick
        r = 0.0
        if hold and gi + 1 < len(C.index):
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) if vals else 0.0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    r = r - (turn / len(daily)) * 2 * CS / 10
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return r, turn / 10 / yrs * 100 / 2

cb_out = []
for cell in ("atr", "pct200", "rsi", "hi52"):
    r_, ch_ = run_cb(cell)
    cg, dd2, sh2, _ = perf(r_)
    cb_out.append((cell, cg, dd2, sh2, ch_))
    print(f"CB[{cell}]: CAGR {cg*100:+.1f}% maxDD {dd2*100:.1f}% Sharpe {sh2:.2f} churn {ch_:.0f}%", flush=True)
null_cb = []
for k in range(25):
    r_, _ = run_cb("atr", placebo=True)
    null_cb.append(perf(r_)[0])
print(f"CB placebo (random-10-of-top50): mean {np.mean(null_cb)*100:.1f}%, 95th {np.percentile(null_cb,95)*100:.1f}%", flush=True)

# ================= PMS1 =================
def run_pms1(arm):
    hold = {}
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in month_start:
            elig = (C.iloc[gi] > ma200.iloc[gi]) & (ma50.iloc[gi] > ma200.iloc[gi]) & memb.iloc[gi] \
                   & (ROCE.iloc[gi] >= 15) & (NPG.iloc[gi] >= 20)
            ranked = rs126.iloc[gi].where(elig).dropna().sort_values(ascending=False).index[:20]
            for s in ranked:
                if s not in hold and len(hold) < 20:
                    e_ = C.iat[gi, C.columns.get_loc(s)]
                    if np.isfinite(e_):
                        hold[s] = e_; turn += 1
        # exits daily
        for s in list(hold):
            j = C.columns.get_loc(s)
            px = C.iat[gi, j]
            if not np.isfinite(px):
                continue
            exit_ = px < ma200.iat[gi, j]
            if arm == "A":
                exit_ = exit_ or (np.isfinite(NPG.iat[gi, j]) and NPG.iat[gi, j] < 15) \
                        or (np.isfinite(PE_PCT3.iat[gi, j]) and PE_PCT3.iat[gi, j] > 0.90
                            and np.isfinite(NPG.iat[gi, j]) and NPG.iat[gi, j] < 25)
            if exit_:
                del hold[s]; turn += 1
        r = 0.0
        if hold and gi + 1 < len(C.index):
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) * len(hold) / 20 if vals else 0.0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    r = r - (turn / len(daily)) * 2 * CS / 20
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return r, turn / 20 / yrs * 100 / 2

resA, chA = run_pms1("A"); cgA, ddA, shA, _ = perf(resA)
resB, chB = run_pms1("B"); cgB, ddB, shB, _ = perf(resB)
print(f"PMS1 ARM-A (decel exit): CAGR {cgA*100:+.1f}% maxDD {ddA*100:.1f}% Sharpe {shA:.2f} churn {chA:.0f}%", flush=True)
print(f"PMS1 ARM-B (200dma only): CAGR {cgB*100:+.1f}% maxDD {ddB*100:.1f}% Sharpe {shB:.2f} churn {chB:.0f}%", flush=True)
verdict = "A BEATS B (decel exit = alpha)" if (cgA - cgB >= 0.03 and ddA > ddB) else "A does NOT beat B by bars"
lines = [f"CA: CAGR {cagr*100:+.1f}% DD {dd_*100:.1f}% Sharpe {sh:.2f} churn {ca_churn:.0f}% | placebo95 {np.percentile(null_ca,95)*100:.1f}%",
         "CB cells: " + " | ".join(f"{c}: {cg*100:+.1f}%/{d2*100:.1f}%/{s2:.2f}" for c, cg, d2, s2, _ in cb_out)
         + f" | placebo95 {np.percentile(null_cb,95)*100:.1f}%",
         f"PMS1: A {cgA*100:+.1f}%/{ddA*100:.1f}% vs B {cgB*100:+.1f}%/{ddB*100:.1f}% -> {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

