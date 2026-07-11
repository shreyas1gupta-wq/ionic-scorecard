"""ALPHA FORGE engine (campaign frozen @ cb3e776). 10 sleeves -> daily return series on unit capital,
screen (2024-07..2026-06) + validate (2016-01..2024-06) stats -> ledger + per-sleeve series parquet.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/ALPHA_FORGE"
(OUT / "series").mkdir(parents=True, exist_ok=True)
CS, CG, CI = 0.0025, 0.0012, 0.0008  # per-side: stocks, gold, index
S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")
V0, V1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2024-06-30")

print("=== loading data ===", flush=True)
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
print(f"stocks panel {C.shape}", flush=True)

# PIT membership mask (monthly step function on C.index)
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    mask = (C.index.date >= sd) & (C.index.date < end)
    cols = [c for c in C.columns if c in snaps[sd]]
    memb.loc[mask, cols] = True

ma50 = C.rolling(50).mean(); ma150 = C.rolling(150).mean(); ma200 = C.rolling(200).mean()
lo52, hi52 = C.rolling(252).min(), C.rolling(252).max()
stage2 = (C > ma150) & (C > ma200) & (ma200 > ma200.shift(21)) & (ma50 > ma150) & (C >= 1.3 * lo52) & (C >= 0.75 * hi52) & memb
rs126 = (C / C.shift(126) - 1).rank(axis=1, pct=True)

ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.sort_values(["symbol", "quarter_end"])
for col in ("sales", "opm_pct", "net_profit"):
    ev[f"{col}_ly"] = ev.groupby("symbol")[col].shift(4)

gold_frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/commodities_1m").glob("XAUUSD_1m_*.parquet"))]
gold = pd.concat(gold_frames).set_index("ts")["close"].resample("1D").last().dropna()
idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC["Index Name"] = IC["Index Name"].str.strip()
IC["date"] = pd.to_datetime(IC["file_date"])
IC["close"] = pd.to_numeric(IC["Closing Index Value"], errors="coerce")
IC["pe"] = pd.to_numeric(IC["P/E"], errors="coerce") if "P/E" in IC.columns else np.nan
nifty = IC[IC["Index Name"] == "Nifty 50"].set_index("date")["close"].sort_index()
poi = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet")
print("aux data loaded", flush=True)

def trade_sleeve(entries, hold_fn, tag, cost=CS, max_conc=10):
    """entries: list of (entry_date_idx_pos, sym). hold_fn(sym, i_entry) -> (exit_i, ret_gross).
    Returns daily return series on unit capital, equal-split across concurrent (max_conc slots)."""
    dates = C.index
    daily = pd.Series(0.0, index=dates)
    open_pos = []
    entries = sorted(entries)
    ei = 0
    positions = {}
    for i in range(len(dates)):
        # close exits
        for sym in [s for s, x in list(positions.items()) if x[0] == i]:
            positions.pop(sym)
        # new entries
        while ei < len(entries) and entries[ei][0] == i:
            _, sym = entries[ei]; ei += 1
            if sym in positions or len(positions) >= max_conc:
                continue
            res = hold_fn(sym, i)
            if res is None:
                continue
            exit_i, _ = res
            positions[sym] = (exit_i, i)
        if positions:
            w = 1.0 / max_conc
            r = 0.0
            for sym, (xi, en) in positions.items():
                if i > en:
                    v = RET.iat[i, C.columns.get_loc(sym)]
                    if np.isfinite(v):
                        r += w * v
                # entry/exit cost days
                if i == en or i == xi:
                    r -= w * cost
            daily.iloc[i] = r
    daily.name = tag
    return daily

def stat_windows(r):
    out = {}
    for tag, a, b in [("screen", S0, S1), ("validate", V0, V1)]:
        x = r.loc[a:b]
        x = x[x.abs() > 0] if (x.abs() > 0).sum() > 30 else x
        if len(x) < 30 or x.std(ddof=1) == 0:
            out[tag] = (np.nan, np.nan)
            continue
        sh = x.mean() / x.std(ddof=1) * np.sqrt(252)
        ann = (1 + x.reindex(r.loc[a:b].index).fillna(0)).prod() ** (252 / max(len(r.loc[a:b]), 1)) - 1
        out[tag] = (sh, ann)
    return out

date_pos = {dd: i for i, dd in enumerate(C.index)}

def next_pos(day):
    i = np.searchsorted(C.index.values, np.datetime64(day), side="right")
    return i if i < len(C.index) else None

results = {}

# ---------- AF-01 earnings-quality momentum ----------
def af01():
    ent = []
    ok = ev.dropna(subset=["available_date", "sales", "sales_ly", "opm_pct", "opm_pct_ly"])
    ok = ok[(ok.sales_ly > 0) & (ok.sales >= 1.15 * ok.sales_ly) & (ok.opm_pct >= ok.opm_pct_ly + 1.5)]
    for _, r in ok.iterrows():
        i = next_pos(r.available_date)
        sym = str(r.symbol).strip()
        if i is None or sym not in C.columns:
            continue
        if i < len(C.index) and bool(stage2.iat[max(i - 1, 0), C.columns.get_loc(sym)]):
            ent.append((i, sym))
    def hold(sym, i):
        j = C.columns.get_loc(sym)
        px = C.iloc[i:i + 61, j]
        if not len(px) or not np.isfinite(px.iloc[0]):
            return None
        peak = px.cummax()
        trail = px < peak * 0.85
        xi = i + int(np.argmax(trail.values)) if trail.any() else min(i + 60, len(C.index) - 1)
        return (xi, 0.0)
    return trade_sleeve(ent, hold, "AF01", max_conc=10)

# ---------- AF-04 absorption spring ----------
def af04():
    volr = V.rolling(5).mean() / V.rolling(60).mean()
    chg5 = (C / C.shift(5) - 1).abs()
    bdd = 1 - C.rolling(40).min() / C.rolling(40).max(); base = (bdd >= 0.05) & (bdd <= 0.35)
    sig = (volr >= 2.5) & (chg5 <= 0.02) & stage2 & base
    hi10 = H.shift(1).rolling(10).max()
    trig = sig.shift(3).fillna(False) & (C > hi10)  # absorption seen, then break within window
    ent = [(i + 1, C.columns[j]) for i, j in zip(*np.where(trig.values)) if i + 1 < len(C.index)]
    def hold(sym, i):
        j = C.columns.get_loc(sym)
        px = C.iloc[i:i + 41, j]
        if not len(px) or not np.isfinite(px.iloc[0]):
            return None
        stop = px < px.iloc[0] * 0.92
        xi = i + int(np.argmax(stop.values)) if stop.any() else min(i + 40, len(C.index) - 1)
        return (xi, 0.0)
    return trade_sleeve(ent, hold, "AF04", max_conc=10)

# ---------- AF-05 range-compression spring ----------
def af05():
    rng20 = (H.rolling(20).max() - L.rolling(20).min()) / C
    rng_pct = rng20.rolling(252).rank(pct=True)
    dry = V.rolling(10).mean() < 0.8 * V.rolling(50).mean()
    sig = (rng_pct <= 0.10) & dry & (C > ma200) & memb
    atr = (H - L).rolling(14).mean()
    trigger_lvl = H.rolling(20).max() + 0.5 * atr
    trig = sig.shift(1).fillna(False) & (C > trigger_lvl.shift(1))
    ent = [(i + 1, C.columns[j]) for i, j in zip(*np.where(trig.values)) if i + 1 < len(C.index)]
    def hold(sym, i):
        j = C.columns.get_loc(sym)
        px = C.iloc[i:i + 26, j]
        if not len(px) or not np.isfinite(px.iloc[0]):
            return None
        e = px.iloc[0]; a = atr.iat[i - 1, j] if i > 0 else np.nan
        if not np.isfinite(a) or a <= 0:
            return (min(i + 25, len(C.index) - 1), 0.0)
        hit = (px >= e + 2 * a) | (px <= e - a)
        xi = i + int(np.argmax(hit.values)) if hit.any() else min(i + 25, len(C.index) - 1)
        return (xi, 0.0)
    return trade_sleeve(ent, hold, "AF05", max_conc=10)

# ---------- AF-07 stage-1->2 turn ----------
def af07():
    depth = C / hi52
    slope200 = ma200 / ma200.shift(63) - 1
    reclaim = (C > ma50) & (C.shift(1) <= ma50.shift(1))
    sig = (depth >= 0.60) & (depth <= 0.75) & (slope200 > -0.02) & reclaim & (V >= 1.5 * V.rolling(50).mean()) & memb
    ent = [(i + 1, C.columns[j]) for i, j in zip(*np.where(sig.values)) if i + 1 < len(C.index)]
    def hold(sym, i):
        j = C.columns.get_loc(sym)
        px = C.iloc[i:i + 91, j]
        if not len(px) or not np.isfinite(px.iloc[0]):
            return None
        stop = (px < px.iloc[0] * 0.90) | (px < ma200.iloc[i:i + 91, j])
        xi = i + int(np.argmax(stop.values)) if stop.any() else min(i + 90, len(C.index) - 1)
        return (xi, 0.0)
    return trade_sleeve(ent, hold, "AF07", max_conc=10)

# ---------- AF-08 post-earnings quiet drift ----------
def af08():
    ent = []
    ok = ev.dropna(subset=["available_date", "net_profit", "net_profit_ly"])
    ok = ok[(ok.net_profit_ly > 0) & (ok.net_profit >= 1.2 * ok.net_profit_ly)]
    for _, r in ok.iterrows():
        sym = str(r.symbol).strip()
        i = next_pos(r.available_date)
        if i is None or sym not in C.columns or i + 1 >= len(C.index):
            continue
        j = C.columns.get_loc(sym)
        mv = RET.iat[i, j]
        if np.isfinite(mv) and abs(mv) < 0.02 and memb.iat[i, j]:
            ent.append((i + 2, sym))
    def hold(sym, i):
        j = C.columns.get_loc(sym)
        px = C.iloc[i:i + 31, j]
        if not len(px) or not np.isfinite(px.iloc[0]):
            return None
        stop = px < px.iloc[0] * 0.92
        xi = i + int(np.argmax(stop.values)) if stop.any() else min(i + 30, len(C.index) - 1)
        return (xi, 0.0)
    return trade_sleeve(ent, hold, "AF08", max_conc=10)

# ---------- AF-09 quality turn-of-month ----------
def af09():
    dates = C.index
    daily = pd.Series(0.0, index=dates)
    month = pd.Series(dates.month, index=dates)
    is_last = month != month.shift(-1)
    for i in np.where(is_last.values)[0]:
        if i + 4 >= len(dates):
            continue
        elig = stage2.iloc[i] & (rs126.iloc[i] >= 0.75)
        syms = list(elig.index[elig.fillna(False)])[:10]
        if not syms:
            continue
        cols = [C.columns.get_loc(s) for s in syms]
        w = 1 / max(len(syms), 1)
        for k in range(1, 4):
            rr = RET.iloc[i + k, cols]
            daily.iloc[i + k] += float(np.nansum(rr.values) * w)
        daily.iloc[i + 1] -= CS; daily.iloc[i + 3] -= CS
    daily.name = "AF09"
    return daily

# ---------- AF-03 gold-equity regime dance ----------
def af03():
    n500p = C[memb].mean(axis=1)  # equal-weight member proxy
    g = gold.reindex(C.index, method="ffill")
    mg, mn = g / g.shift(63) - 1, n500p / n500p.shift(63) - 1
    gold_ret = g.pct_change().fillna(0)
    eq_ret = n500p.pct_change().fillna(0)
    tilt = (mg > mn).shift(1).fillna(False)
    w = np.where(tilt, 0.7, 0.3)
    r = w * gold_ret + (1 - w) * eq_ret
    # weekly rebal cost approx
    turn = pd.Series(w, index=C.index).diff().abs().fillna(0)
    r = r - turn * (CG + CS) / 2
    r.name = "AF03"
    return pd.Series(r, index=C.index)

# ---------- AF-10 gold range-break asymmetry ----------
def af10():
    g = gold.copy()
    hi10 = g.shift(1).rolling(10).max()
    brk = g > hi10
    days_since = brk.copy() * 0
    cnt = 0
    vals = []
    for b in brk.values:
        cnt = 0 if b else cnt + 1
        vals.append(cnt)
    days_since = pd.Series(vals, index=g.index)
    sig = brk & (days_since.shift(1) >= 15)
    r = pd.Series(0.0, index=g.index)
    gr = g.pct_change().fillna(0)
    i = 0
    idx = list(g.index)
    sigv = sig.values
    while i < len(idx):
        if sigv[i] and i + 1 < len(idx):
            e = g.iloc[i + 1]
            for k in range(i + 1, min(i + 9, len(idx))):
                r.iloc[k] = gr.iloc[k]
                if g.iloc[k] <= e * 0.985:
                    break
            r.iloc[i + 1] -= CG; r.iloc[min(k, len(idx) - 1)] -= CG
            i = k
        i += 1
    r = r.reindex(C.index).fillna(0)
    r.name = "AF10"
    return r

# ---------- AF-06 FII option-positioning tilt ----------
def af06():
    fii = poi[poi["Client Type"] == "FII"].set_index("date").sort_index()
    net_opt = (fii["Option Index Call Long"] - fii["Option Index Call Short"]) \
              - (fii["Option Index Put Long"] - fii["Option Index Put Short"])
    flow = net_opt.diff()
    rank = flow.rolling(252, min_periods=250).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True)
    n500p = C[memb].mean(axis=1).pct_change().fillna(0)
    rk = rank.reindex(C.index, method="ffill").shift(1)
    expo = np.where(rk >= 0.8, 1.25, np.where(rk <= 0.2, 0.25, 0.75))
    r = pd.Series(expo, index=C.index) * n500p
    turn = pd.Series(expo, index=C.index).diff().abs().fillna(0)
    r -= turn * CI
    r.name = "AF06"
    return r

# ---------- AF-02 sector value-momentum rotation ----------
def af02():
    sect = [n for n in IC["Index Name"].unique()
            if n.startswith("Nifty") and any(k in n for k in ["IT", "Pharma", "Bank", "Auto", "FMCG", "Metal", "Energy", "Realty", "Infra", "Media"]) and "50" not in n]
    pe = IC[IC["Index Name"].isin(sect)].pivot_table(index="date", columns="Index Name", values="pe")
    cl = IC[IC["Index Name"].isin(sect)].pivot_table(index="date", columns="Index Name", values="close")
    pe_pct = pe.rolling(504, min_periods=252).rank(pct=True)
    mom = cl / cl.shift(63) - 1
    score = (1 - pe_pct) * 0.5 + mom.rank(axis=1, pct=True) * 0.5
    # map sector -> member stocks via RS within sector unknown; proxy: hold the sector INDEX return (top-2)
    scl = cl.pct_change()
    daily = pd.Series(0.0, index=C.index)
    month_idx = pd.Series(cl.index.month, index=cl.index)
    reb = month_idx != month_idx.shift(1)
    cur = []
    for i, dd in enumerate(cl.index):
        if reb.iloc[i] and i > 0:
            s = score.iloc[i - 1].dropna()
            cur = list(s.sort_values(ascending=False).index[:2])
        if cur and dd in daily.index:
            daily.loc[dd] = float(np.nanmean([scl.iloc[i][c] for c in cur])) if i > 0 else 0.0
    # monthly rebal cost
    daily.loc[daily.index[reb.reindex(daily.index, fill_value=False)]] -= CI
    daily.name = "AF02"
    return daily.fillna(0)

SLEEVES = {"AF01": af01, "AF02": af02, "AF03": af03, "AF04": af04, "AF05": af05,
           "AF06": af06, "AF07": af07, "AF08": af08, "AF09": af09, "AF10": af10}
ledger = []
for tag, fn in SLEEVES.items():
    try:
        r = fn()
        r.to_frame(tag).to_parquet(OUT / "series" / f"{tag}.parquet")
        st = stat_windows(r)
        (ssh, sann), (vsh, vann) = st["screen"], st["validate"]
        passed = (ssh >= 1.2) and (vsh >= 0.8)
        ledger.append(dict(sleeve=tag, screen_sharpe=round(float(ssh), 2) if np.isfinite(ssh) else None,
                           screen_ann=round(float(sann * 100), 1) if np.isfinite(sann) else None,
                           val_sharpe=round(float(vsh), 2) if np.isfinite(vsh) else None,
                           val_ann=round(float(vann * 100), 1) if np.isfinite(vann) else None,
                           PASS=bool(passed)))
        print(f"{tag}: screen Sharpe {ssh:.2f} ({sann*100:+.1f}%) | validate {vsh:.2f} ({vann*100:+.1f}%) "
              f"{'>>> PASS' if passed else ''}", flush=True)
    except Exception as e:
        import traceback
        ledger.append(dict(sleeve=tag, PASS=False, err=str(e)[:80]))
        print(f"{tag}: ERROR {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
pd.DataFrame(ledger).to_csv(OUT / "ledger.csv", index=False)
print("\nledger saved", flush=True)

