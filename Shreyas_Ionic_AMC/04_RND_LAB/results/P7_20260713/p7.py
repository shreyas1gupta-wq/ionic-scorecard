"""P7 (frozen @ 677ed9b): earnings-guided momentum 20-stock, growth-quality-fixed, 3 momentum cells."""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(191)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/P7_20260713"
OUT.mkdir(parents=True, exist_ok=True)
CS = 0.0025
W0, WMID, W1 = pd.Timestamp("2022-07-01"), pd.Timestamp("2024-06-30"), pd.Timestamp("2026-06-30")

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
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
mom3 = C / C.shift(63) - 1
mom6 = C / C.shift(126) - 1
mom12 = C / C.shift(252) - 1

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_sales"] = ev.groupby("symbol")["sales"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
ev["ttm_sales_ly"] = ev.groupby("symbol")["ttm_sales"].shift(4)
up = ev.groupby("symbol")["net_profit"].diff() > 0
ev["qoq2"] = (up & up.groupby(ev["symbol"]).shift(1).fillna(False)).astype(float)
def step(frame, symcol, val):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val]).groupby(symcol):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p
NPG = (step(ev, "symbol", "ttm_np") / step(ev, "symbol", "ttm_np_ly") - 1).where(step(ev, "symbol", "ttm_np_ly") > 0) * 100
SG = (step(ev, "symbol", "ttm_sales") / step(ev, "symbol", "ttm_sales_ly") - 1).where(step(ev, "symbol", "ttm_sales_ly") > 0) * 100
QOQ2 = step(ev, "symbol", "qoq2")
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step(rat.rename(columns={"ROCE %": "roce"}), "nse_symbol", "roce")
ROE = step(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "roe")
print("panels ready", flush=True)

def wz(row, cap=3.0):
    m, s = np.nanmean(row), np.nanstd(row)
    if not np.isfinite(s) or s == 0:
        return row * 0
    return np.clip((row - m) / s, -cap, cap)

dates = C.index[(C.index >= W0) & (C.index <= W1)]
month_start = set(dd for i, dd in enumerate(dates) if i == 0 or dates[i - 1].month != dd.month)

def targets(gi, momcell):
    mrow = memb.iloc[gi]
    g = NPG.iloc[gi].where(mrow)
    band = (g >= 20) & (g <= 60)  # base-effect law: outside band EXCLUDED
    if band.sum() < 25:
        return []
    sg = SG.iloc[gi].where(band).clip(20, 60)
    with np.errstate(all="ignore"):
        q = pd.Series(np.nanmean(np.vstack([wz(ROCE.iloc[gi].where(band).values),
                                            wz(ROE.iloc[gi].where(band).values)]), axis=0), index=C.columns)
    fs = q + pd.Series(wz(g.where(band).values), index=C.columns) + \
         pd.Series(wz(sg.values), index=C.columns) + QOQ2.iloc[gi].fillna(0.0)
    top40 = fs.where(band).dropna().sort_values(ascending=False).index[:40]
    if momcell == "M1":
        mo = (mom3.iloc[gi][top40] + mom6.iloc[gi][top40]) / 2
    elif momcell == "M2":
        mo = (mom6.iloc[gi][top40] + mom12.iloc[gi][top40]) / 2
    else:
        mo = mom3.iloc[gi][top40]
    return list(mo.dropna().sort_values(ascending=False).index[:20])

def run(momcell, placebo=False):
    hold = set()
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in month_start:
            if placebo:
                pool = list(memb.iloc[gi][memb.iloc[gi]].index)
                tgt = set(rng.choice(pool, size=20, replace=False))
            else:
                tgt = set(targets(gi, momcell))
            if tgt:
                turn += len(hold - tgt) + len(tgt - hold)
                hold = tgt
        r = 0.0
        if hold and gi + 1 < len(C.index):
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) * len(hold) / 20 if vals else 0.0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    return r - (turn / len(daily)) * 2 * CS / 20

def perf(r):
    e = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return e.iloc[-1] ** (1 / yrs) - 1, (e / e.cummax() - 1).min(), r.mean() / r.std(ddof=1) * np.sqrt(252)

res = {}
for m in ("M1", "M2", "M3"):
    r = run(m)
    cg, dd_, sh = perf(r)
    a = float((1 + r[r.index <= WMID]).prod() - 1)
    b = float((1 + r[r.index > WMID]).prod() - 1)
    res[m] = dict(cagr=cg, dd=dd_, sh=sh, A=a, B=b, r=r)
    print(f"{m}: CAGR {cg*100:+.1f}% DD {dd_*100:.1f}% Sh {sh:.2f} | A {a*100:+.1f}% B {b*100:+.1f}%", flush=True)

nulls = [perf(run("M1", placebo=True))[0] for _ in range(100)]
p95 = float(np.percentile(nulls, 95)); pmed = float(np.median(nulls))
lines = [f"placebo (random-20 x100): median {pmed*100:+.1f}%, p95 {p95*100:+.1f}%"]
for m in ("M1", "M2", "M3"):
    x = res[m]
    ok = (x["cagr"] > p95) and (x["A"] > 0) and (x["B"] > 0)
    lines.append(f"{m}: CAGR {x['cagr']*100:+.1f}% DD {x['dd']*100:.1f}% Sh {x['sh']:.2f} A {x['A']*100:+.1f}% B {x['B']*100:+.1f}% -> {'PASS' if ok else 'fail'}")
npass = sum(1 for m in res if res[m]["cagr"] > p95 and res[m]["A"] > 0 and res[m]["B"] > 0)
lines.append(f"VERDICT: {'SHORTLIST-FOR-FORWARD' if npass >= 1 else 'NOT SHORTLISTED'} ({npass}/3 cells)")
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "P7_RESULTS.txt").write_text(txt, encoding="utf-8")
pd.DataFrame({m: (1 + res[m]["r"]).cumprod() for m in res}).to_csv(OUT / "p7_equity.csv")
