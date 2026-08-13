"""TECHNOFUNDA BATTERY engine (frozen @ 9da01a6). Episode-level, PIT fundamentals.
P1a/b/c, P2, P3, P4, P5a/b, P6, M1-M4 event setups. Per-setup same-exit placebo x200.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(61)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TECHNOFUNDA_BATTERY_20260712"
OUT.mkdir(parents=True, exist_ok=True)
CS = 0.0025
V0, V1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2024-06-30")
S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")

print("loading panels...", flush=True)
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
rs126 = (C / C.shift(126) - 1).rank(axis=1, pct=True)
swing10 = L.rolling(10).min(); swing20 = L.rolling(20).min()
NROW, NCOL = C.shape
print(f"panel {C.shape}", flush=True)

# ---- PIT fundamentals ----
ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
for c in ("net_profit", "sales", "eps"):
    ev[f"ttm_{c}"] = ev.groupby("symbol")[c].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_net_profit"].shift(4)
ev["ttm_sales_ly"] = ev.groupby("symbol")["ttm_sales"].shift(4)
ev["np_qoq_up"] = ev.groupby("symbol")["net_profit"].diff() > 0
ev["np_qoq_up2"] = ev["np_qoq_up"] & ev.groupby("symbol")["np_qoq_up"].shift(1).fillna(False)
ev["np_qoq_up3"] = ev["np_qoq_up2"] & ev.groupby("symbol")["np_qoq_up"].shift(2).fillna(False)

def build_step_panel(frame, sym_col, date_col, val_col):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    f = frame.dropna(subset=[val_col])
    for sym, g in f.groupby(sym_col):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val_col].values, index=pd.to_datetime(g[date_col])).sort_index()
        ser = ser[~ser.index.duplicated(keep="last")]
        p[s] = ser.reindex(C.index, method="ffill")
    return p

print("building PIT panels...", flush=True)
TTM_EPS = build_step_panel(ev, "symbol", "available_date", "ttm_eps")
TTM_NP = build_step_panel(ev, "symbol", "available_date", "ttm_net_profit")
TTM_NP_LY = build_step_panel(ev, "symbol", "available_date", "ttm_np_ly")
QUP3 = build_step_panel(ev.assign(q3=ev.np_qoq_up3.astype(float)), "symbol", "available_date", "q3")
GROWTH = (TTM_NP / TTM_NP_LY - 1).where(TTM_NP_LY > 0) * 100
GROWTH_PRIOR = GROWTH.shift(63)
PE = (C / TTM_EPS).where(TTM_EPS > 0)
PEG = (PE / GROWTH).where(GROWTH > 0)
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROE = build_step_panel(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "available_date", "roe")
ed = pd.read_csv(ROOT / "datasets/nse_earnings_dates/earnings_dates.csv")
edc = [c for c in ed.columns if "date" in c.lower()][0]
eds = [c for c in ed.columns if "symbol" in c.lower() or "ticker" in c.lower()][0]
ed[edc] = pd.to_datetime(ed[edc], errors="coerce")
ed = ed.dropna(subset=[edc])
sched = {s: sorted(g[edc].values) for s, g in ed.groupby(ed[eds].astype(str).str.strip())}
print("PIT panels ready", flush=True)

def episode(gi, j, exit_cfg):
    """entry at row gi close (already next-close), exits per cfg. Returns net episode return."""
    if gi + 1 >= NROW:
        return None
    n_max = exit_cfg.get("tmax", 90)
    px = C.iloc[gi:gi + n_max + 1, j]
    if not len(px) or not np.isfinite(px.iloc[0]) or px.iloc[0] <= 0:
        return None
    e = px.iloc[0]
    for k in range(1, len(px)):
        row = gi + k
        c_ = px.iloc[k]
        if not np.isfinite(c_):
            continue
        if "stop" in exit_cfg and c_ <= e * (1 - exit_cfg["stop"]):
            return (c_ / e - 1) - 2 * CS
        if "target" in exit_cfg and c_ >= e * (1 + exit_cfg["target"]):
            return (c_ / e - 1) - 2 * CS
        if exit_cfg.get("trail") == "swing10" and c_ < swing10.iat[row - 1, j] * 0.99:
            return (c_ / e - 1) - 2 * CS
        if exit_cfg.get("trail") == "swing20" and c_ < swing20.iat[row - 1, j] * 0.99:
            return (c_ / e - 1) - 2 * CS
        if exit_cfg.get("dma") and c_ < {"20": ma20, "50": ma50, "200": ma200}[exit_cfg["dma"]].iat[row, j]:
            return (c_ / e - 1) - 2 * CS
        if exit_cfg.get("recapture20") and c_ > H.iloc[max(row - 20, 0):row, j].max():
            return (c_ / e - 1) - 2 * CS
        if "exit_row" in exit_cfg and row >= exit_cfg["exit_row"]:
            return (c_ / e - 1) - 2 * CS
    fin = px.iloc[-1]
    if not np.isfinite(fin):
        fin = px.dropna().iloc[-1] if px.notna().any() else np.nan
    if not np.isfinite(fin):
        return None
    return (fin / e - 1) - 2 * CS

def run_setup(name, events, exit_cfg, pool_mask, short=False):
    """events: list of (signal_row, col) -> entry row+1. pool_mask: eligibility for placebo draws."""
    res = []
    for i, j in events:
        r = episode(i + 1, j, exit_cfg)
        if r is not None:
            res.append((i, r if not short else -r - 4 * CS * 0))  # short: negate price return, costs already in
    if short:
        res = [(i, -(r + 2 * CS) - 2 * 0.0015) for i, r in
               [(i, episode(i + 1, j, exit_cfg)) for i, j in events] if r is not None]
    real = np.array([r for _, r in res])
    if len(real) < 20:
        out = dict(name=name, n=int(len(real)), verdict='INSUFFICIENT')
        print(out, flush=True)
        return out
    rows_idx = np.array([i for i, _ in res])
    dts = C.index[rows_idx]
    mv = (dts >= V0) & (dts <= V1)
    ms = (dts >= S0) & (dts <= S1)
    v_mean = real[mv].mean() if mv.sum() >= 20 else np.nan
    s_mean = real[ms].mean() if ms.sum() >= 10 else np.nan
    # placebo x200: same n_v draws from pool within validate window, same exits
    pool_rows, pool_cols = np.where(pool_mask.values & (pool_mask.index.to_series().between(V0, V1).values[:, None]))
    nulls = []
    n_draw = min(int(mv.sum()), 250)
    for k in range(200):
        pick = rng.integers(0, len(pool_rows), size=n_draw)
        rr = []
        for p_ in pick:
            r = episode(pool_rows[p_] + 1, pool_cols[p_], exit_cfg)
            if r is not None:
                rr.append(-r - 4 * CS * 0 if short else r)
        if rr:
            nulls.append(np.nanmean(rr))
    nulls = np.array([x for x in nulls if np.isfinite(x)])
    p95 = np.percentile(nulls, 95) if len(nulls) >= 20 else np.nan
    ok = (np.isfinite(v_mean) and v_mean > p95) and (np.isfinite(s_mean) and np.sign(s_mean) == np.sign(v_mean) and s_mean > 0)
    verdict = "PASS" if ok else "FAIL"
    out = dict(name=name, n=int(len(real)), n_val=int(mv.sum()), n_scr=int(ms.sum()),
               val_mean=round(float(v_mean * 100), 2) if np.isfinite(v_mean) else None,
               scr_mean=round(float(s_mean * 100), 2) if np.isfinite(s_mean) else None,
               placebo95=round(float(p95 * 100), 2), verdict=verdict)
    print(out, flush=True)
    return out

results = []
long_pool = (C > ma200) & memb  # stage-matched placebo pool for long setups

# --- P1: technofunda base breakout ---
runup = (C.shift(20) / C.shift(20).rolling(126).min() - 1) >= 0.25
base_rng = (H.rolling(20).max() - L.rolling(20).min()) / C <= 0.15
fund1 = (ROE >= 15) & (GROWTH >= 20) & (PE < 30)
brk1 = C > H.shift(1).rolling(20).max()
sig1 = runup & base_rng.shift(1) & fund1 & brk1 & memb
e1 = list(zip(*np.where(sig1.values)))
for tag, cfg in [("P1a_swing10", {"trail": "swing10", "tmax": 120}),
                 ("P1b_swing20", {"trail": "swing20", "tmax": 120}),
                 ("P1c_50dma", {"dma": "50", "tmax": 120})]:
    results.append(run_setup(tag, e1, cfg, long_pool))

# --- P2 cheap-growth momentum ---
sig2 = (PEG < 1) & (GROWTH > GROWTH_PRIOR) & (rs126 >= 0.70) & (C > H.shift(1).rolling(20).max()) & memb
results.append(run_setup("P2_peg_mom", list(zip(*np.where(sig2.values))), {"dma": "50", "tmax": 120}, long_pool))

# --- P3 pre-earnings rich-decel short (futures proxy, top-liquidity names) ---
tv = (C * V).rolling(60).mean()
top150 = tv.rank(axis=1, ascending=False) <= 150
short_events = []
for sym, dts_ in sched.items():
    if sym not in C.columns:
        continue
    j = C.columns.get_loc(sym)
    for dd in dts_:
        di = np.searchsorted(C.index.values, np.datetime64(dd))
        i = di - 4  # signal 4 rows before -> entry (i+1) = 3td before announcement
        if i < 260 or i >= NROW:
            continue
        if (np.isfinite(PE.iat[i, j]) and PE.iat[i, j] > 75 and np.isfinite(GROWTH.iat[i, j])
                and np.isfinite(GROWTH_PRIOR.iat[i, j]) and GROWTH.iat[i, j] < GROWTH_PRIOR.iat[i, j]
                and top150.iat[i, j] and memb.iat[i, j]):
            short_events.append((i, j, min(di + 2, NROW - 1)))
res3 = []
for i, j, xr in short_events:
    r = episode(i + 1, j, {"exit_row": xr, "tmax": 12})
    if r is not None:
        res3.append((i, -(r) - 4 * 0.0015))  # negate + futures RT cost both legs
real3 = np.array([r for _, r in res3])
if len(real3) >= 20:
    dts3 = C.index[[i for i, _ in res3]]
    mv3, ms3 = (dts3 >= V0) & (dts3 <= V1), (dts3 >= S0) & (dts3 <= S1)
    out3 = dict(name="P3_preearn_short", n=len(real3),
                val_mean=round(float(real3[mv3].mean() * 100), 2) if mv3.sum() > 10 else None,
                scr_mean=round(float(real3[ms3].mean() * 100), 2) if ms3.sum() > 5 else None,
                placebo95=None, verdict="REPORT-ONLY (placebo=abs zero line)")
else:
    out3 = dict(name="P3_preearn_short", n=int(len(real3)), verdict="INSUFFICIENT")
print(out3, flush=True)
results.append(out3)

# --- P4 deep pullback in strong trend ---
strong = (C / ma200).rolling(60).mean() > 1.2
def rsi(cf, n):
    dd_ = cf.diff()
    up = dd_.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dd_.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
rsi14 = rsi(C, 14)
pull = (C / hi52 - 1 <= -0.12) & ((C.shift(15) / hi52.shift(15) - 1) > -0.05)
sig4 = strong & pull & (rsi14 < 40) & memb
results.append(run_setup("P4_deep_pullback", list(zip(*np.where(sig4.values))),
                         {"recapture20": True, "stop": 0.08, "tmax": 30}, long_pool))

# --- P5 shakeout reclaim ---
for tag, MA in [("P5a_50dma", ma50), ("P5b_20dma", ma20)]:
    slope_ok = (MA / MA.shift(63) - 1) > 0.025
    below = C < MA
    below5 = below.rolling(5).sum()
    reclaim = (C > MA) & below.shift(1) & (below5.shift(1) <= 5) & (below5.shift(1) >= 1)
    sig5 = slope_ok & reclaim & memb & (rs126 >= 0.6)
    results.append(run_setup(tag, list(zip(*np.where(sig5.values))),
                             {"trail": "swing10", "tmax": 60}, long_pool))

# --- P6 failed-breakout snapback ---
brk55 = C > H.shift(1).rolling(55).max()
lvl = C.where(brk55)  # breakout close level
lvl_ff = lvl.ffill(limit=17)
blow = L.where(brk55).ffill(limit=17)  # breakout-day low
failed = (C < blow) & lvl_ff.notna()
failed_recent = failed.rolling(7).max().astype(bool)
snap = (C > lvl_ff) & failed_recent.shift(1) & (GROWTH > 0) & memb
sig6 = snap & (~brk55)
results.append(run_setup("P6_snapback", list(zip(*np.where(sig6.values))),
                         {"dma": "50", "stop": 0.08, "tmax": 60}, long_pool))

# --- M1 PE-compression turn ---
eps_g = TTM_EPS / TTM_EPS.shift(252) - 1
px_g = C / C.shift(126) - 1
reclaim50 = (C > ma50) & (C.shift(1) <= ma50.shift(1))
sigm1 = (eps_g >= 0.25) & (px_g <= 0) & reclaim50 & memb
results.append(run_setup("M1_pe_compression", list(zip(*np.where(sigm1.values))),
                         {"dma": "50", "tmax": 90}, long_pool))

# --- M2 acceleration chain (entry at 3rd rising QoQ availability) ---
m2_events = []
ok2 = ev[ev.np_qoq_up3 == True]
for _, r in ok2.iterrows():
    sym = str(r.symbol).strip()
    if sym not in C.columns:
        continue
    j = C.columns.get_loc(sym)
    i = np.searchsorted(C.index.values, np.datetime64(r.available_date))
    if i >= NROW - 5 or not memb.iat[min(i, NROW - 1), j]:
        continue
    nxt = [x for x in sched.get(sym, []) if x > np.datetime64(r.available_date)]
    xr = np.searchsorted(C.index.values, nxt[0]) - 2 if nxt else min(i + 70, NROW - 1)
    m2_events.append((i, j, min(max(xr, i + 5), NROW - 1)))
res_m2 = []
for i, j, xr in m2_events:
    r = episode(i + 1, j, {"exit_row": xr, "stop": 0.10, "tmax": 90})
    if r is not None:
        res_m2.append((i, r))
realm2 = np.array([r for _, r in res_m2])
dtm2 = C.index[[i for i, _ in res_m2]]
if len(realm2) >= 40:
    mv2, ms2 = (dtm2 >= V0) & (dtm2 <= V1), (dtm2 >= S0) & (dtm2 <= S1)
    # placebo: same exit horizon random long-pool
    nulls = []
    pr, pc = np.where(long_pool.values)
    for k in range(200):
        pick = rng.integers(0, len(pr), size=min(int(mv2.sum()), 250))
        rr = [episode(pr[p_] + 1, pc[p_], {"exit_row": pr[p_] + 45, "stop": 0.10, "tmax": 90}) for p_ in pick]
        rr = [x for x in rr if x is not None]
        if rr:
            nulls.append(np.mean(rr))
    p95m2 = np.percentile(nulls, 95)
    vm2 = realm2[mv2].mean(); sm2 = realm2[ms2].mean() if ms2.sum() > 5 else np.nan
    outm2 = dict(name="M2_accel_chain", n=len(realm2), val_mean=round(vm2 * 100, 2),
                 scr_mean=round(float(sm2 * 100), 2) if np.isfinite(sm2) else None,
                 placebo95=round(p95m2 * 100, 2),
                 verdict="PASS" if (vm2 > p95m2 and np.isfinite(sm2) and sm2 > 0) else "FAIL")
else:
    outm2 = dict(name="M2_accel_chain", n=int(len(realm2)), verdict="INSUFFICIENT")
print(outm2, flush=True)
results.append(outm2)

# --- M3 confirmed-PEAD gap ---
m3 = []
okg = ev[(ev.ttm_np_ly > 0) & (ev.net_profit >= 1.25 * ev.groupby("symbol")["net_profit"].shift(4))]
for _, r in okg.iterrows():
    sym = str(r.symbol).strip()
    if sym not in C.columns:
        continue
    j = C.columns.get_loc(sym)
    i = np.searchsorted(C.index.values, np.datetime64(r.available_date))
    if i >= NROW - 2 or i < 1:
        continue
    if np.isfinite(RET.iat[i, j]) and RET.iat[i, j] > 0.03 and memb.iat[i, j]:
        m3.append((i, j))
results.append(run_setup("M3_confirmed_pead", m3, {"stop": 0.05, "tmax": 20}, long_pool))

# --- M4 leadership emergence ---
topdec = rs126 >= 0.90
was_top = topdec.shift(1).rolling(252).max().astype(bool)
sigm4 = topdec & (~was_top) & (GROWTH > 0) & memb
results.append(run_setup("M4_leadership", list(zip(*np.where(sigm4.values))),
                         {"dma": "50", "tmax": 60}, long_pool))

pd.DataFrame(results).to_csv(OUT / "battery_results.csv", index=False)
print("\nBATTERY DONE", flush=True)

