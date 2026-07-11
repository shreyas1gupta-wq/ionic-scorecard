"""POSITIONAL engine (frozen @ a379303). POS-1 quarterly formula portfolio (3 momentum cells)
+ POS-2 trigger/stage-exit. Portfolio-level, PIT fundamentals, quarterly placebos.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(101)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/POSITIONAL_20260712"
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
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
stage2 = (C > ma200) & (ma50 > ma200) & memb
H = d.pivot_table(index="date", columns="symbol", values="high"); H.index = C.index

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_sales"] = ev.groupby("symbol")["sales"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
ev["ttm_sales_ly"] = ev.groupby("symbol")["ttm_sales"].shift(4)
ev["qup"] = ev.groupby("symbol")["net_profit"].diff() > 0
ev["qup2"] = (ev["qup"] & ev.groupby("symbol")["qup"].shift(1).fillna(False)).astype(float)

def step(val):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in ev.dropna(subset=[val]).groupby("symbol"):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p

NPG = (step("ttm_np") / step("ttm_np_ly") - 1).where(step("ttm_np_ly") > 0) * 100
SG = (step("ttm_sales") / step("ttm_sales_ly") - 1).where(step("ttm_sales_ly") > 0) * 100
QUP2 = step("qup2")
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
rocp = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
for sym, g in rat.rename(columns={"ROCE %": "roce"}).dropna(subset=["roce"]).groupby("nse_symbol"):
    s = str(sym).strip()
    if s not in C.columns:
        continue
    ser = pd.Series(g["roce"].values, index=g["available_date"]).sort_index()
    rocp[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
print("PIT panels ready", flush=True)

def zrow(row):
    m, s = np.nanmean(row), np.nanstd(row)
    return (row - m) / s if s > 0 else row * 0

def run_pos1(mom_mode, tag):
    dates = C.index[(C.index >= W0) & (C.index <= W1)]
    reb = [dd for i, dd in enumerate(dates) if dd.month in (1, 4, 7, 10) and (i == 0 or dates[i - 1].month != dd.month)]
    hold, eq, rets, turn_total = [], 1.0, [], 0.0
    daily = []
    prev = set()
    for i, dd in enumerate(dates[:-1]):
        if dd in reb:
            gi = C.index.get_loc(dd)
            if mom_mode == "3m":
                mom = C.iloc[gi] / C.iloc[max(gi - 63, 0)] - 1
            elif mom_mode == "6m":
                mom = C.iloc[gi] / C.iloc[max(gi - 126, 0)] - 1
            else:
                mom = (C.iloc[gi] / C.iloc[max(gi - 126, 0)] - 1) + (C.iloc[gi] / C.iloc[max(gi - 252, 0)] - 1)
            elig = stage2.iloc[gi]
            score = (zrow(rocp.iloc[gi].values) + zrow(NPG.iloc[gi].values) + zrow(SG.iloc[gi].values)
                     + np.nan_to_num(QUP2.iloc[gi].values) + zrow(mom.values))
            score = pd.Series(score, index=C.columns).where(elig)
            new = set(score.dropna().sort_values(ascending=False).index[:20])
            churn_names = len(new - prev)
            turn_total += churn_names / 20  # one-way fraction of book
            cost_hit = (churn_names / 20) * 2 * CS
            prev = new
            hold = list(new)
            daily.append(-cost_hit)
        else:
            daily.append(0.0)
        if hold:
            gi2 = C.index.get_loc(dd)
            rr = RET.iloc[gi2 + 1][hold] if gi2 + 1 < len(C.index) else None
            daily[-1] += float(np.nanmean(rr.values)) if rr is not None else 0.0
    r = pd.Series(daily, index=dates[:len(daily)])
    eqc = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eqc.iloc[-1] ** (1 / yrs) - 1
    dd_ = (eqc / eqc.cummax() - 1).min()
    sh = r.mean() / r.std(ddof=1) * np.sqrt(252)
    churn = turn_total / yrs * 100
    e1 = (1 + r[r.index < "2021-01-01"]).prod() ** (1 / 5) - 1
    e2 = (1 + r[r.index >= "2021-01-01"]).prod() ** (1 / 5.5) - 1
    out = dict(tag=tag, cagr=round(cagr * 100, 1), maxdd=round(dd_ * 100, 1), sharpe=round(sh, 2),
               churn_pct_yr=round(churn, 0), era1=round(e1 * 100, 1), era2=round(e2 * 100, 1))
    print(out, flush=True)
    return r, out

results = []
series = {}
for mode, tag in [("3m", "POS1_3m"), ("6m", "POS1_6m"), ("6m12m", "POS1_6m12m")]:
    r, out = run_pos1(mode, tag)
    results.append(out); series[tag] = r

# placebo x200 (random-20 stage-2, quarterly, same costs approx) — compute distribution of CAGR
print("placebo...", flush=True)
def placebo_once():
    dates = C.index[(C.index >= W0) & (C.index <= W1)]
    reb = [dd for i, dd in enumerate(dates) if dd.month in (1, 4, 7, 10) and (i == 0 or dates[i - 1].month != dd.month)]
    hold, daily = [], []
    for i, dd in enumerate(dates[:-1]):
        if dd in reb:
            gi = C.index.get_loc(dd)
            elig = list(stage2.iloc[gi][stage2.iloc[gi]].index)
            hold = list(rng.choice(elig, size=min(20, len(elig)), replace=False)) if elig else []
            daily.append(-0.7 * 2 * CS)
        else:
            daily.append(0.0)
        if hold:
            gi2 = C.index.get_loc(dd)
            if gi2 + 1 < len(C.index):
                daily[-1] += float(np.nanmean(RET.iloc[gi2 + 1][hold].values))
    r = pd.Series(daily, index=dates[:len(daily)])
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (1 + r).prod() ** (1 / yrs) - 1

null = np.array([placebo_once() for _ in range(60)])  # 60 full-decade portfolio sims (heavy) -> boot to 200
boot = rng.choice(null, size=(200, 30)).mean(axis=1)
p95 = np.percentile(null, 95) * 100
print(f"placebo CAGR: mean {null.mean()*100:.1f}%, 95th {p95:.1f}%", flush=True)

# POS-2 trigger/stage-exit
brk = C > H.shift(1).rolling(55).max()
fund = (NPG >= 20) & (rocp >= 12)
sig = brk & stage2 & fund
sig = sig.loc[W0:W1]
NROW = len(C.index)
def pos2_episode(gi, j):
    px = C.iloc[gi:gi + 500, j]
    if not len(px) or not np.isfinite(px.iloc[0]):
        return None
    e = px.iloc[0]
    for k in range(1, len(px)):
        row = gi + k; c_ = px.iloc[k]
        if not np.isfinite(c_):
            continue
        if c_ <= e * 0.75 or c_ < ma200.iat[row, j]:
            return ((c_ / e - 1) - 2 * CS, k)
    fin = px.dropna().iloc[-1]
    return ((fin / e - 1) - 2 * CS, len(px))
eps = []
for i, j in zip(*np.where(sig.values)):
    gi = C.index.get_loc(sig.index[i]) + 1
    if gi < NROW - 5:
        r = pos2_episode(gi, j)
        if r:
            eps.append((sig.index[i], r[0], r[1]))
ep = pd.DataFrame(eps, columns=["day", "ret", "held"])
avg_hold = ep.held.mean()
churn2 = 252 / avg_hold * 100  # full-book one-way churn %/yr at steady state
out2 = dict(tag="POS2_trigger", n=len(ep), mean_ret=round(ep.ret.mean() * 100, 2),
            avg_hold_td=round(avg_hold, 0), churn_pct_yr=round(churn2, 0),
            ann_per_slot=round(((1 + ep.ret.mean()) ** (252 / avg_hold) - 1) * 100, 1))
print(out2, flush=True)
results.append(out2)

pd.DataFrame(results).to_csv(OUT / "positional_results.csv", index=False)
(OUT / "RESULTS_RAW.txt").write_text(
    "\n".join(str(x) for x in results) + f"\nplacebo CAGR 95th: {p95:.1f}%", encoding="utf-8")
print("DONE", flush=True)
