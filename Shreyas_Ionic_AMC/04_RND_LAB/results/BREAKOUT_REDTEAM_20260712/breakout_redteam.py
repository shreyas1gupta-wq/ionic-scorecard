"""BREAKOUT-PACK RED-TEAM (frozen @ faed362). Battery on the banked 488-trade regime ledger.
Real trades from realistic_trades_SL10pct_20d_REGIME.csv; placebo episodes re-simulated with the
same exit engine (10% SL on close, 20td cap) on the daily OHLCV panel.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(113)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BREAKOUT_REDTEAM_20260712"
OUT.mkdir(parents=True, exist_ok=True)
CS = 0.0025

b = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BREAKOUT_SCAN_20260710/realistic_trades_SL10pct_20d_REGIME.csv",
                parse_dates=["date"])
buys = b[b.action == "BUY"][["date", "symbol", "px"]].reset_index(drop=True)
exits = b[b.action != "BUY"]
per = exits.pnl / (exits.shares * exits.px - exits.pnl).clip(lower=1)
real = per.values
real_mean = np.nanmean(real)
print(f"real ledger: {len(buys)} buys, {len(exits)} exits, mean {real_mean*100:+.2f}%/trade", flush=True)

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
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean(); ma200 = C.rolling(200).mean()
stage2 = (C > ma200) & (ma50 > ma200) & memb
NROW = len(C.index)

def episode(gi, j, cost_mult=1.0):
    if gi + 1 >= NROW:
        return None
    px = C.iloc[gi:gi + 21, j]
    if not len(px) or not np.isfinite(px.iloc[0]) or px.iloc[0] <= 0:
        return None
    e = px.iloc[0]
    for k in range(1, len(px)):
        c_ = px.iloc[k]
        if np.isfinite(c_) and c_ <= e * 0.90:
            return (c_ / e - 1) - 2 * CS * cost_mult
    fin = px.dropna().iloc[-1] if px.notna().any() else np.nan
    return None if not np.isfinite(fin) else (fin / e - 1) - 2 * CS * cost_mult

buy_rows = []
for _, r in buys.iterrows():
    i = np.searchsorted(C.index.values, np.datetime64(r.date))
    if i < NROW:
        buy_rows.append(i)

# P1 stock-shuffle: same dates, random stage-2 stock
s2v = stage2.values
null1 = []
for k in range(200):
    rr = []
    for i in buy_rows:
        elig = np.where(s2v[min(i, NROW - 1)])[0]
        if len(elig):
            r = episode(i, int(rng.choice(elig)))
            if r is not None:
                rr.append(r)
    if rr:
        null1.append(np.mean(rr))
null1 = np.array(null1)
p1_95 = np.percentile(null1, 95)
print(f"stock-shuffle null: mean {null1.mean()*100:+.2f}%, 95th {p1_95*100:+.2f}%", flush=True)

# P2 date-shuffle: random stage-2 (sym,date) pairs, same count
pr, pc = np.where(s2v & (C.index.to_series().between(buys.date.min(), buys.date.max()).values[:, None]))
null2 = []
for k in range(200):
    pick = rng.integers(0, len(pr), size=len(buy_rows))
    rr = [episode(pr[p_], pc[p_]) for p_ in pick]
    rr = [x for x in rr if x is not None]
    if rr:
        null2.append(np.mean(rr))
null2 = np.array(null2)
p2_95 = np.percentile(null2, 95)

# liquidity + 2x cost (approximate 2x cost on ledger mean: subtract extra 2*CS)
tv = []
for _, r in buys.iterrows():
    s = str(r.symbol).strip()
    if s in C.columns:
        i = np.searchsorted(C.index.values, np.datetime64(r.date))
        if i < NROW:
            v_ = V.iat[i, C.columns.get_loc(s)] * C.iat[i, C.columns.get_loc(s)]
            if np.isfinite(v_):
                tv.append(v_)
liq_med = np.median(tv) / 1e7
real_2x = real_mean - 2 * CS

bars = {"beats_stock_shuffle95": real_mean > p1_95, "beats_date_shuffle95": real_mean > p2_95,
        "liquidity_5cr": liq_med >= 5, "2x_cost_positive": real_2x > 0}
verdict = "CERTIFIED" if all(bars.values()) else "NOT CERTIFIED"
lines = [f"BREAKOUT PACK red-team: real {real_mean*100:+.2f}%/trade (n={len(exits)})",
         f"stock-shuffle null95 {p1_95*100:+.2f} | date-shuffle null95 {p2_95*100:+.2f}",
         f"liquidity median Rs {liq_med:.1f}cr | 2x-cost mean {real_2x*100:+.2f}%",
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
