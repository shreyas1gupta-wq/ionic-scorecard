"""AF-07 CERTIFICATION red-team (thesis V2, frozen @ 5e49c26).
Battery (pre-declared): P1 stock-shuffle x200 (random member stocks, same dates+exits) — selection value;
P2 date-shuffle x200 (same stocks, random member dates) — timing value; L liquidity honesty (median
traded value at entry >= Rs 5cr); Y yearly table (>=7/10 positive); C 2x-cost stress.
CERTIFIED iff real > P1-95th AND real > P2-95th AND L AND Y AND C-positive.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(47)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/ALPHA_FORGE"
CS = 0.0025

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
    mask = (C.index.date >= sd) & (C.index.date < end)
    memb.loc[mask, [c for c in C.columns if c in snaps[sd]]] = True

ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
hi52 = C.rolling(252).max()
depth = C / hi52
slope200 = ma200 / ma200.shift(63) - 1
reclaim = (C > ma50) & (C.shift(1) <= ma50.shift(1))
sig = (depth >= 0.60) & (depth <= 0.75) & (slope200 > -0.02) & reclaim & (V >= 1.5 * V.rolling(50).mean()) & memb
sig = sig.loc["2016-01-01":"2026-06-30"]
ent_real = [(i, j) for i, j in zip(*np.where(sig.values))]
print(f"AF-07 real entries: {len(ent_real)}", flush=True)

def episode_ret(i, j, cost_mult=1.0):
    """entry next close after signal row i (in sig frame), col j; AF-07 exits."""
    gi = C.index.get_loc(sig.index[i]) + 1
    if gi + 1 >= len(C):
        return None
    px = C.iloc[gi:gi + 91, j]
    if not len(px) or not np.isfinite(px.iloc[0]) or px.iloc[0] <= 0:
        return None
    m2 = ma200.iloc[gi:gi + 91, j]
    stop = (px < px.iloc[0] * 0.90) | (px < m2)
    xi = int(np.argmax(stop.values)) if stop.any() else min(90, len(px) - 1)
    return (px.iloc[xi] / px.iloc[0] - 1) - 2 * CS * cost_mult

real = [r for r in (episode_ret(i, j) for i, j in ent_real) if r is not None]
real = np.array(real)
real_mean = real.mean()
print(f"real: n={len(real)} mean {real_mean*100:+.2f}%/trade", flush=True)

# liquidity honesty
tv = []
for i, j in ent_real:
    gi = C.index.get_loc(sig.index[i])
    v_ = V.iat[gi, j] * C.iat[gi, j]
    if np.isfinite(v_):
        tv.append(v_)
liq_med = np.median(tv) / 1e7
liq_ok = liq_med >= 5
print(f"liquidity: median traded value Rs {liq_med:.1f}cr {'OK' if liq_ok else 'FAIL'}", flush=True)

# yearly
years = pd.Series([sig.index[i].year for i, j in ent_real])
ydf = pd.DataFrame({"y": years[:len(real)], "r": real})
ytab = ydf.groupby("y").r.mean()
y_pos = (ytab > 0).sum()
print("yearly:", {int(k): f"{v*100:+.1f}%" for k, v in ytab.items()}, flush=True)

# P1 stock shuffle: same signal DATES, random member stock that day
memb_v = memb.loc[sig.index].values
null1 = []
cols_n = C.shape[1]
for k in range(200):
    rets = []
    for i, j in ent_real:
        elig = np.where(memb_v[i])[0]
        if not len(elig):
            continue
        r = episode_ret(i, int(rng.choice(elig)))
        if r is not None:
            rets.append(r)
    null1.append(np.mean(rets))
    if k % 50 == 0:
        print(f"  P1 {k}", flush=True)
null1 = np.array(null1)
p1_95 = np.percentile(null1, 95)

# P2 date shuffle: same stocks, random dates where stock is member
null2 = []
for k in range(200):
    rets = []
    for i, j in ent_real:
        elig = np.where(memb.values[:, j][:len(sig)])[0]
        if not len(elig):
            continue
        r = episode_ret(int(rng.choice(elig)), j)
        if r is not None:
            rets.append(r)
    null2.append(np.mean(rets))
    if k % 50 == 0:
        print(f"  P2 {k}", flush=True)
null2 = np.array(null2)
p2_95 = np.percentile(null2, 95)

# 2x cost stress
real2x = np.array([r for r in (episode_ret(i, j, 2.0) for i, j in ent_real) if r is not None])
c_ok = real2x.mean() > 0

bars = {"beats_P1_stock_shuffle_95": real_mean > p1_95,
        "beats_P2_date_shuffle_95": real_mean > p2_95,
        "liquidity_5cr": bool(liq_ok),
        "years>=7of10_positive": int(y_pos) >= 7,
        "2x_cost_positive": bool(c_ok)}
verdict = "CERTIFIED" if all(bars.values()) else "NOT CERTIFIED"
lines = [f"AF-07 red-team: real {real_mean*100:+.2f}%/trade (n={len(real)})",
         f"P1 stock-shuffle null: mean {null1.mean()*100:+.2f}%, 95th {p1_95*100:+.2f}%",
         f"P2 date-shuffle null: mean {null2.mean()*100:+.2f}%, 95th {p2_95*100:+.2f}%",
         f"liquidity median Rs {liq_med:.1f}cr | years positive {y_pos}/{len(ytab)} | 2x-cost mean {real2x.mean()*100:+.2f}%",
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "AF07_REDTEAM.txt").write_text(txt, encoding="utf-8")
