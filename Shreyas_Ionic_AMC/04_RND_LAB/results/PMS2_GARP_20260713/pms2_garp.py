"""PMS2-GARP (frozen @ d4f257a): consensus GARP entry, E1 decel-exit vs E2 hold-forever vs E3 regime gate."""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(181)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/PMS2_GARP_20260713"
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

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_eps"] = ev.groupby("symbol")["eps"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
def step(frame, symcol, val):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val]).groupby(symcol):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p
GROWTH = (step(ev, "symbol", "ttm_np") / step(ev, "symbol", "ttm_np_ly") - 1).where(step(ev, "symbol", "ttm_np_ly") > 0) * 100
PE = (C / step(ev, "symbol", "ttm_eps")).where(step(ev, "symbol", "ttm_eps") > 0)
PEG = (PE / GROWTH).where(GROWTH > 0)
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step(rat.rename(columns={"ROCE %": "roce"}), "nse_symbol", "roce")
ROE = step(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "roe")
QUAL = (ROCE >= 20) | (ROE >= 20)
idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC = IC[IC["Index Name"].str.strip().str.upper() == "NIFTY 50"]
nifty = pd.Series(pd.to_numeric(IC["Closing Index Value"], errors="coerce").values,
                  index=pd.to_datetime(IC["file_date"])).sort_index()
nifty = nifty[~nifty.index.duplicated()]
risk_on = (nifty >= nifty.rolling(200).mean()).reindex(C.index, method="ffill").fillna(True)
print("panels ready", flush=True)

dates = C.index[(C.index >= W0) & (C.index <= W1)]
month_start = set(dd for i, dd in enumerate(dates) if i == 0 or dates[i - 1].month != dd.month)

def entry_screen(gi):
    ok = QUAL.iloc[gi] & (GROWTH.iloc[gi] >= 20) & (PEG.iloc[gi] < 1.5) & memb.iloc[gi]
    cand = GROWTH.iloc[gi].where(ok).dropna().sort_values(ascending=False)
    return list(cand.index)

def run(mode, placebo=False):
    hold, fails = {}, {}
    daily, turn = [], 0
    for i, dd in enumerate(dates[:-1]):
        gi = C.index.get_loc(dd)
        if dd in month_start:
            cands = entry_screen(gi)
            if placebo:
                pool = list(memb.iloc[gi][memb.iloc[gi]].index)
                cands = list(rng.choice(pool, size=min(60, len(pool)), replace=False))
            # exits
            for s in list(hold):
                j = C.columns.get_loc(s)
                g_ = GROWTH.iat[gi, j]; pg = PEG.iat[gi, j]
                if mode == "E2":
                    in_screen = s in cands[:60] if placebo else (np.isfinite(g_) and g_ >= 20 and QUAL.iat[gi, j]
                                                                 and np.isfinite(pg) and pg < 1.5)
                    fails[s] = fails.get(s, 0) + (0 if in_screen else 1)
                    if fails[s] >= 2:
                        del hold[s]; fails.pop(s, None); turn += 1
                else:  # E1/E3 decel exit
                    if (np.isfinite(g_) and g_ < 12) or (np.isfinite(pg) and pg > 2.5):
                        del hold[s]; turn += 1
            # entries
            gate = True if mode != "E3" else bool(risk_on.iloc[gi])
            if gate:
                for s in cands:
                    if len(hold) >= 18:
                        break
                    if s not in hold:
                        e_ = C.iat[gi, C.columns.get_loc(s)]
                        if np.isfinite(e_):
                            hold[s] = e_; fails[s] = 0; turn += 1
        r = 0.0
        if hold and gi + 1 < len(C.index):
            vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
            vals = [v for v in vals if np.isfinite(v)]
            r = np.mean(vals) * len(hold) / 18 if vals else 0.0
        daily.append(r)
    r = pd.Series(daily, index=dates[:len(daily)])
    r = r - (turn / len(daily)) * 2 * CS / 18
    return r

def perf(r):
    e = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return e.iloc[-1] ** (1 / yrs) - 1, (e / e.cummax() - 1).min(), r.mean() / r.std(ddof=1) * np.sqrt(252)

res = {}
for mode in ("E1", "E2", "E3"):
    r = run(mode)
    cg, dd_, sh = perf(r)
    a = float((1 + r[r.index <= WMID]).prod() - 1)
    b = float((1 + r[r.index > WMID]).prod() - 1)
    res[mode] = dict(cagr=cg, dd=dd_, sh=sh, subA=a, subB=b, r=r)
    print(f"{mode}: CAGR {cg*100:+.1f}% DD {dd_*100:.1f}% Sh {sh:.2f} | A {a*100:+.1f}% B {b*100:+.1f}%", flush=True)

nulls = []
for k in range(100):
    rp = run("E1", placebo=True)
    nulls.append(perf(rp)[0])
p95 = float(np.percentile(nulls, 95))
lines = []
for mode in ("E1", "E2", "E3"):
    x = res[mode]
    ok = (x["cagr"] > p95) and (x["subA"] > 0) and (x["subB"] > 0)
    lines.append(f"{mode}: CAGR {x['cagr']*100:+.1f}% DD {x['dd']*100:.1f}% Sh {x['sh']:.2f} A {x['subA']*100:+.1f}% B {x['subB']*100:+.1f}% -> {'PASS' if ok else 'fail'}")
thesis = res["E1"]["cagr"] - res["E2"]["cagr"]
lines.append(f"placebo95 CAGR {p95*100:+.1f}% (n=100 random-18 baskets)")
lines.append(f"STUDY THESIS (E1-E2): {thesis*100:+.1f}pts (bar +3) -> {'CONFIRMED' if thesis >= 0.03 else 'NOT CONFIRMED'}")
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "PMS2_GARP_RESULTS.txt").write_text(txt, encoding="utf-8")
pd.DataFrame({m: (1 + res[m]["r"]).cumprod() for m in res}).to_csv(OUT / "pms2_equity.csv")
