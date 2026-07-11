"""X8 (frozen card @ de0cc36): stocks long-hold ADX rider — stage-2 + ADX>25 + DI+>DI- + 20d-high
break -> chandelier 3xATR22 exit. Episode-level, PIT universe, same-exit placebo x100.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(139)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/ADX_ATR_20260712"
CS = 0.0025
V0, V1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2024-06-30")
S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")

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
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
stage2 = (C > ma200) & (ma50 > ma200) & memb

def wilder(df, n):
    return df.ewm(alpha=1 / n, adjust=False).mean()

up = H.diff(); dn = -L.diff()
plus_dm = up.where((up > dn) & (up > 0), 0.0)
minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max()
atr = wilder(tr, 14)
pdi = 100 * wilder(plus_dm, 14) / atr
mdi = 100 * wilder(minus_dm, 14) / atr
dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
adx = wilder(dx, 14)
atr22 = wilder(tr, 22)
print("indicators ready", flush=True)

raw = (adx > 25) & (pdi > mdi) & stage2 & (C > H.shift(1).rolling(20).max())
sig = raw & ~raw.shift(1).fillna(False)
sig = sig.loc["2016-01-01":"2026-06-30"]
NROW = len(C.index)

def episode(gi, j):
    e = C.iat[gi, j]
    if not np.isfinite(e):
        return None
    hh = e
    for k in range(gi + 1, min(gi + 260, NROW)):
        c_ = C.iat[k, j]; a_ = atr22.iat[k, j]; h_ = H.iat[k, j]
        if not np.isfinite(c_) or not np.isfinite(a_):
            continue
        if np.isfinite(h_):
            hh = max(hh, h_)
        if c_ < hh - 3 * a_:
            return ((c_ / e - 1) - 2 * CS, k - gi)
    c_ = C.iat[min(gi + 259, NROW - 1), j]
    return (((c_ / e - 1) - 2 * CS) if np.isfinite(c_) else None, 259)

events = []
for i, j in zip(*np.where(sig.values)):
    gi = C.index.get_loc(sig.index[i]) + 1
    if gi + 2 < NROW:
        events.append((gi, j, sig.index[i]))
res = []
for gi, j, dd in events:
    r = episode(gi, j)
    if r and r[0] is not None:
        res.append((dd, r[0], r[1]))
real = np.array([x[1] for x in res]); dts = pd.DatetimeIndex([x[0] for x in res])
held = np.array([x[2] for x in res])
print(f"X8: n={len(real)}, mean {real.mean()*100:+.2f}%, avg hold {held.mean():.0f}td", flush=True)

mv, ms = (dts >= V0) & (dts <= V1), (dts >= S0) & (dts <= S1)
pool_r, pool_c = np.where(stage2.values & (stage2.index.to_series().between(V0, V1).values[:, None]))
pool_r2, pool_c2 = np.where(stage2.values & (stage2.index.to_series().between(S0, S1).values[:, None]))
nulls_v, nulls_s = [], []
for k in range(100):
    pick = rng.integers(0, len(pool_r), size=min(int(mv.sum()), 200))
    rr = [episode(pool_r[p] + 1, pool_c[p]) for p in pick]
    rr = [x[0] for x in rr if x and x[0] is not None]
    if rr: nulls_v.append(np.mean(rr))
    pick2 = rng.integers(0, len(pool_r2), size=min(max(int(ms.sum()), 10), 200))
    rr2 = [episode(pool_r2[p] + 1, pool_c2[p]) for p in pick2]
    rr2 = [x[0] for x in rr2 if x and x[0] is not None]
    if rr2: nulls_s.append(np.mean(rr2))
p95v = np.percentile(nulls_v, 95)
vm, sm, pms = real[mv].mean(), real[ms].mean() if ms.sum() > 3 else np.nan, np.mean(nulls_s)
passed = (vm > p95v) and np.isfinite(sm) and (sm - pms > 0) and mv.sum() >= 60
lines = [f"X8 stocks long-hold rider: n={len(real)} (val {int(mv.sum())}), mean {real.mean()*100:+.2f}%, hold {held.mean():.0f}td",
         f"validate {vm*100:+.2f}% vs placebo95 {p95v*100:+.2f}% | screen alpha {(sm-pms)*100 if np.isfinite(sm) else float('nan'):+.2f}%",
         f"VERDICT: {'PASS' if passed else 'FAIL'}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "X8_RESULTS.txt").write_text(txt, encoding="utf-8")
