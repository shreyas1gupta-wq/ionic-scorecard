"""P6M3-CONFIRMATION (frozen @ 0578f2d): placebo-relative alpha, window-matched pools, params unchanged.
Reuses battery engine layers via exec of its top section would be fragile - reimplements the two setups
verbatim from battery_engine.py (frozen source) with the new measurement only.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(71)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TECHNOFUNDA_BATTERY_20260712"
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
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
swing10 = L.rolling(10).min()
NROW = len(C)

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)

def build_step_panel(frame, sym_col, date_col, val_col):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val_col]).groupby(sym_col):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val_col].values, index=pd.to_datetime(g[date_col])).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p

TTM_NP = build_step_panel(ev, "symbol", "available_date", "ttm_np")
TTM_NP_LY = build_step_panel(ev, "symbol", "available_date", "ttm_np_ly")
GROWTH = (TTM_NP / TTM_NP_LY - 1).where(TTM_NP_LY > 0) * 100

def episode(gi, j, exit_cfg):
    if gi + 1 >= NROW:
        return None
    px = C.iloc[gi:gi + exit_cfg.get("tmax", 90) + 1, j]
    if not len(px) or not np.isfinite(px.iloc[0]) or px.iloc[0] <= 0:
        return None
    e = px.iloc[0]
    for k in range(1, len(px)):
        row = gi + k; c_ = px.iloc[k]
        if not np.isfinite(c_):
            continue
        if "stop" in exit_cfg and c_ <= e * (1 - exit_cfg["stop"]):
            return (c_ / e - 1) - 2 * CS
        if exit_cfg.get("dma") == "50" and c_ < ma50.iat[row, j]:
            return (c_ / e - 1) - 2 * CS
    fin = px.dropna().iloc[-1] if px.notna().any() else np.nan
    return None if not np.isfinite(fin) else (fin / e - 1) - 2 * CS

# P6 events (verbatim battery logic)
brk55 = C > H.shift(1).rolling(55).max()
lvl_ff = C.where(brk55).ffill(limit=17)
blow = L.where(brk55).ffill(limit=17)
failed_recent = ((C < blow) & lvl_ff.notna()).rolling(7).max().astype(bool)
sig_p6 = (C > lvl_ff) & failed_recent.shift(1) & (GROWTH > 0) & memb & (~brk55)
E6 = list(zip(*np.where(sig_p6.values)))
# M3 events
okg = ev[(ev.ttm_np_ly > 0) & (ev.net_profit >= 1.25 * ev.groupby("symbol")["net_profit"].shift(4))]
E3 = []
for _, r in okg.iterrows():
    sym = str(r.symbol).strip()
    if sym not in C.columns:
        continue
    j = C.columns.get_loc(sym)
    i = np.searchsorted(C.index.values, np.datetime64(r.available_date))
    if 1 <= i < NROW - 2 and np.isfinite(RET.iat[i, j]) and RET.iat[i, j] > 0.03 and memb.iat[i, j]:
        E3.append((i, j))

long_pool = (C > ma200) & memb

def confirm(name, events, cfg):
    res = [(i, episode(i + 1, j, cfg)) for i, j in events]
    res = [(i, r) for i, r in res if r is not None]
    real = np.array([r for _, r in res]); dts = C.index[[i for i, _ in res]]
    out = {"name": name}
    for wtag, a, b in [("val", V0, V1), ("scr", S0, S1)]:
        m = (dts >= a) & (dts <= b)
        rm = real[m]
        pr, pc = np.where(long_pool.values & (long_pool.index.to_series().between(a, b).values[:, None]))
        nulls = []
        for k in range(200):
            pick = rng.integers(0, len(pr), size=min(max(len(rm), 30), 250))
            rr = [episode(pr[p_] + 1, pc[p_], cfg) for p_ in pick]
            rr = [x for x in rr if x is not None]
            if rr:
                nulls.append(np.mean(rr))
        nulls = np.array(nulls)
        out[f"{wtag}_n"] = int(len(rm))
        out[f"{wtag}_real"] = round(float(np.mean(rm)) * 100, 2) if len(rm) > 5 else None
        out[f"{wtag}_alpha"] = round(float(np.mean(rm) - np.mean(nulls)) * 100, 2) if len(rm) > 5 else None
        out[f"{wtag}_p95"] = round(float(np.percentile(nulls, 95)) * 100, 2)
        out[f"{wtag}_p50"] = round(float(np.percentile(nulls, 50)) * 100, 2)
    va, sa = out.get("val_alpha"), out.get("scr_alpha")
    conf = (va is not None and va > 0 and out["val_real"] > out["val_p95"]
            and sa is not None and sa > 0 and out["scr_real"] > out["scr_p50"])
    out["verdict"] = "CONFIRMED -> red-team battery" if conf else ("KILL" if (sa is not None and sa < 0) else "PARK")
    print(out, flush=True)
    return out

r1 = confirm("P6_snapback", E6, {"dma": "50", "stop": 0.08, "tmax": 60})
r2 = confirm("M3_confirmed_pead", E3, {"stop": 0.05, "tmax": 20})
pd.DataFrame([r1, r2]).to_csv(OUT / "p6m3_confirmation.csv", index=False)
