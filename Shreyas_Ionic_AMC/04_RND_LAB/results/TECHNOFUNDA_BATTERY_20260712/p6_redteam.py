"""P6 SNAPBACK red-team battery (AF-07 template; confirmation @ 0578f2d CONFIRMED).
P1 stock-shuffle x200 (same dates, random member stocks, same exits) - selection value.
L liquidity (median traded value at entry >= Rs 5cr). Y yearly consistency (>=7/10 positive vs
year-placebo not required - raw yearly alpha sign). C 2x-cost stress. CERTIFIED iff all pass.
(Date-shuffle equivalent already passed = the window-matched placebo in confirmation.)
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(83)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TECHNOFUNDA_BATTERY_20260712"
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
H = d.pivot_table(index="date", columns="symbol", values="high"); H.index = C.index
L = d.pivot_table(index="date", columns="symbol", values="low"); L.index = C.index
V = d.pivot_table(index="date", columns="symbol", values="volume"); V.index = C.index
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
NROW = len(C)

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)

def build_step_panel(frame, val_col):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val_col]).groupby("symbol"):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val_col].values, index=pd.to_datetime(g["available_date"])).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p

GROWTH = (build_step_panel(ev, "ttm_np") / build_step_panel(ev, "ttm_np_ly") - 1) * 100

def episode(gi, j, cost_mult=1.0):
    if gi + 1 >= NROW:
        return None
    px = C.iloc[gi:gi + 61, j]
    if not len(px) or not np.isfinite(px.iloc[0]) or px.iloc[0] <= 0:
        return None
    e = px.iloc[0]
    for k in range(1, len(px)):
        row = gi + k; c_ = px.iloc[k]
        if not np.isfinite(c_):
            continue
        if c_ <= e * 0.92:
            return (c_ / e - 1) - 2 * CS * cost_mult
        if c_ < ma50.iat[row, j]:
            return (c_ / e - 1) - 2 * CS * cost_mult
    fin = px.dropna().iloc[-1] if px.notna().any() else np.nan
    return None if not np.isfinite(fin) else (fin / e - 1) - 2 * CS * cost_mult

brk55 = C > H.shift(1).rolling(55).max()
lvl_ff = C.where(brk55).ffill(limit=17)
blow = L.where(brk55).ffill(limit=17)
failed_recent = ((C < blow) & lvl_ff.notna()).rolling(7).max().astype(bool)
sig = (C > lvl_ff) & failed_recent.shift(1) & (GROWTH > 0) & memb & (~brk55)
EV = list(zip(*np.where(sig.values)))
real = np.array([r for r in (episode(i + 1, j) for i, j in EV) if r is not None])
rows_i = [i for i, j in EV if episode(i + 1, j) is not None]
print(f"real: n={len(real)} mean {real.mean()*100:+.2f}%", flush=True)

memb_v = memb.values
null1 = []
for k in range(200):
    rr = []
    for i, j in EV:
        elig = np.where(memb_v[i])[0]
        r = episode(i + 1, int(rng.choice(elig)))
        if r is not None:
            rr.append(r)
    null1.append(np.mean(rr))
    if k % 50 == 0:
        print(f"  P1 {k}", flush=True)
null1 = np.array(null1)
p1_95 = np.percentile(null1, 95)

tv = [V.iat[i, j] * C.iat[i, j] for i, j in EV if np.isfinite(V.iat[i, j] * C.iat[i, j])]
liq_med = np.median(tv) / 1e7
years = pd.Series([C.index[i].year for i, j in EV][:len(real)])
ytab = pd.DataFrame({"y": years, "r": real}).groupby("y").r.mean()
y_pos = int((ytab > 0).sum())
real2x = np.array([r for r in (episode(i + 1, j, 2.0) for i, j in EV) if r is not None])

bars = {"beats_stock_shuffle_95": real.mean() > p1_95, "liquidity_5cr": liq_med >= 5,
        "years>=7of10": y_pos >= 7, "2x_cost_positive": real2x.mean() > 0}
verdict = "CERTIFIED - sleeve candidate #5" if all(bars.values()) else "NOT CERTIFIED"
lines = [f"P6 red-team: real {real.mean()*100:+.2f}% (n={len(real)})",
         f"stock-shuffle null mean {null1.mean()*100:+.2f}%, 95th {p1_95*100:+.2f}%",
         f"liquidity median Rs {liq_med:.1f}cr | years positive {y_pos}/{len(ytab)} | 2x-cost {real2x.mean()*100:+.2f}%",
         f"yearly: " + " ".join(f"{int(y)}:{v*100:+.1f}" for y, v in ytab.items()),
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "P6_REDTEAM.txt").write_text(txt, encoding="utf-8")
