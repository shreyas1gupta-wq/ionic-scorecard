"""DECEL-TRAP CARD (frozen @ 5b62915): Principal observation - PE>60 + growth decelerating
(prior TTM YoY >= 35% -> current < 20%) falls hard. Forward 3/6/12m vs matched controls.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/DECEL_TRAP_20260712"
OUT.mkdir(parents=True, exist_ok=True)

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
NROW = len(C.index)

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_eps"] = ev.groupby("symbol")["eps"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
ev["g_now"] = (ev.ttm_np / ev.ttm_np_ly - 1).where(ev.ttm_np_ly > 0) * 100
ev["g_prior"] = ev.groupby("symbol")["g_now"].shift(2)  # ~2 quarters earlier growth print

def in_universe(sym, dd):
    prior = [s for s in snap_dates if s <= dd]
    return bool(prior) and sym in snaps[prior[-1]]

def fwd(sym, i, k):
    j = C.columns.get_loc(sym)
    if i + k >= NROW:
        return np.nan
    a, b = C.iat[i, j], C.iat[i + k, j]
    return (b / a - 1) * 100 if np.isfinite(a) and np.isfinite(b) and a > 0 else np.nan

trap, ctrl_stable, ctrl_all = [], [], []
for _, r in ev.dropna(subset=["g_now", "g_prior", "ttm_eps"]).iterrows():
    sym = str(r.symbol).strip()
    if sym not in C.columns:
        continue
    i = np.searchsorted(C.index.values, np.datetime64(r.available_date))
    if i >= NROW - 65 or not in_universe(sym, r.available_date.date()):
        continue
    j = C.columns.get_loc(sym)
    px = C.iat[min(i, NROW - 1), j]
    if not np.isfinite(px) or r.ttm_eps <= 0:
        continue
    pe = px / r.ttm_eps
    row = dict(sym=sym, day=r.available_date.date(), pe=pe, g_now=r.g_now, g_prior=r.g_prior,
               f3=fwd(sym, i, 63), f6=fwd(sym, i, 126), f12=fwd(sym, i, 252))
    if pe > 60 and r.g_prior >= 35 and r.g_now < 20:
        trap.append(row)
    elif pe > 60 and r.g_now >= 25:
        ctrl_stable.append(row)
    ctrl_all.append(row)

T, CSb, A = pd.DataFrame(trap), pd.DataFrame(ctrl_stable), pd.DataFrame(ctrl_all)
T.to_csv(OUT / "trap_events.csv", index=False)

def stat(x):
    x = pd.Series(x).dropna()
    return len(x), x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 3 else np.nan

lines = [f"TRAP events (PE>60, growth {'>='}35% -> <20%): n={len(T)}",
         f"controls: high-PE stable-growth n={len(CSb)} | all-universe events n={len(A)}"]
for k in ("f3", "f6", "f12"):
    nt, mt, tt = stat(T[k]); ns, ms, _ = stat(CSb[k]); na, ma, _ = stat(A[k])
    diff_s, diff_a = mt - ms, mt - ma
    # two-sample t vs stable control
    a1, a2 = T[k].dropna(), CSb[k].dropna()
    t2 = (a1.mean() - a2.mean()) / np.sqrt(a1.var(ddof=1)/len(a1) + a2.var(ddof=1)/len(a2)) if len(a1) > 3 and len(a2) > 3 else np.nan
    lines.append(f"{k}: trap {mt:+.1f}% (n={nt}) | stable-ctrl {ms:+.1f}% | universe {ma:+.1f}% "
                 f"-> underperf vs stable {diff_s:+.1f}% (t={t2:.2f}), vs universe {diff_a:+.1f}%")
n6, m6, _ = stat(T.f6); _, ms6, _ = stat(CSb.f6); _, ma6, _ = stat(A.f6)
a1, a2 = T.f6.dropna(), CSb.f6.dropna()
t6 = (a1.mean() - a2.mean()) / np.sqrt(a1.var(ddof=1)/len(a1) + a2.var(ddof=1)/len(a2))
confirmed = (m6 - ms6 < -5) and (m6 - ma6 < -5) and (t6 <= -2.5)
lines.append(f"BAR (fwd-6m underperf >5% vs BOTH controls, t>=2.5): {'TRAP CONFIRMED -> avoid-filter + short-spec' if confirmed else 'NOT CONFIRMED'}")
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
