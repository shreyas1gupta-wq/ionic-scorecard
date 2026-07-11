"""ADX-ATR BATTERY (frozen @ de0cc36). 8 cells, episode-level, same-exit placebos.
Indices/gold use daily closes (indices_close has no OHLC for all -> ATR proxied by |close diff| Wilder-style
where H/L unavailable; NIFTY/BANK/MIDCAP have OHLC in ind_close_all: Open/High/Low columns exist).
Stocks use full OHLCV panel.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(137)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/ADX_ATR_20260712"
OUT.mkdir(parents=True, exist_ok=True)
V0, V1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2024-06-30")
S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")

def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()

def adx_frames(H, L, C, n=14):
    up = H.diff(); dn = -L.diff()
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1) \
        if isinstance(C, pd.Series) else None
    if isinstance(C, pd.Series):
        atr = wilder(tr, n)
        pdi = 100 * wilder(plus_dm, n) / atr
        mdi = 100 * wilder(minus_dm, n) / atr
        dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
        return wilder(dx, n), pdi, mdi, atr
    raise ValueError

# ---------- index/gold loaders with OHLC ----------
idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC["Index Name"] = IC["Index Name"].str.strip()
IC["date"] = pd.to_datetime(IC["file_date"])
for c, col in [("open", "Open Index Value"), ("high", "High Index Value"), ("low", "Low Index Value"), ("close", "Closing Index Value")]:
    IC[c] = pd.to_numeric(IC[col], errors="coerce")

def load_idx(name):
    g = IC[IC["Index Name"].str.upper() == name.upper()].set_index("date").sort_index()
    g = g[~g.index.duplicated()]
    return g["high"], g["low"], g["close"]

gold_frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/commodities_1m").glob("XAUUSD_1m_*.parquet"))]
gm = pd.concat(gold_frames).set_index("ts").sort_index()
gH = gm["high"].resample("1D").max().dropna()
gL = gm["low"].resample("1D").min().dropna()
gC = gm["close"].resample("1D").last().dropna()

def run_series_cell(tag, H, L, C, mode, cost, short=False):
    adx, pdi, mdi, atr = adx_frames(H, L, C)
    if mode == "rider":
        raw = (adx > 25) & ((mdi > pdi) if short else (pdi > mdi))
        sig = raw & ~raw.shift(1).fillna(False)
    elif mode == "squeeze":
        lowadx = (adx < 20).rolling(10).sum() >= 10
        sig = lowadx.shift(1) & (C > C.shift(1).rolling(20).max())
    else:  # compression
        sig = (atr / wilder(pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1), 100) < 0.75) \
              & (C > C.shift(1).rolling(20).max())
    dates = C.index
    def episode(i0):
        e = C.iloc[i0]
        if not np.isfinite(e):
            return None
        hh = e; ll = e
        for k in range(i0 + 1, min(i0 + 260, len(C))):
            c_ = C.iloc[k]; a_ = atr.iloc[k]
            if not np.isfinite(c_) or not np.isfinite(a_):
                continue
            hh = max(hh, H.iloc[k]); ll = min(ll, L.iloc[k])
            if mode == "rider":
                if short:
                    if c_ > ll + 3 * a_ or (pdi.iloc[k] > mdi.iloc[k]):
                        return -( (c_ / e - 1)) - 2 * cost
                else:
                    if c_ < hh - 3 * a_ or (mdi.iloc[k] > pdi.iloc[k]):
                        return (c_ / e - 1) - 2 * cost
            else:
                if c_ < e + (max(hh, c_) - e) - 2.5 * a_ if False else c_ < hh - 2.5 * a_:
                    return (c_ / e - 1) - 2 * cost
        c_ = C.iloc[min(i0 + 259, len(C) - 1)]
        r = (c_ / e - 1)
        return (-(r) if short else r) - 2 * cost
    sig_idx = [i for i, v in enumerate(sig.values) if v and i + 2 < len(C)]
    res = [(dates[i], episode(i + 1)) for i in sig_idx]
    res = [(d_, r) for d_, r in res if r is not None]
    real = np.array([r for _, r in res]); dts = pd.DatetimeIndex([d_ for d_, _ in res])
    if len(real) < 15:
        out = dict(cell=tag, n=int(len(real)), verdict="INSUFFICIENT")
        print(out, flush=True); return out
    mv, ms = (dts >= V0) & (dts <= V1), (dts >= S0) & (dts <= S1)
    # placebo: random dates, same episode engine
    nulls_v, nulls_s = [], []
    all_i = np.arange(30, len(C) - 261)
    for k in range(200):
        pick = rng.choice(all_i, size=max(int(mv.sum()), 10), replace=False)
        rr = [episode(i + 1) for i in pick if V0 <= dates[i] <= V1]
        rr = [x for x in rr if x is not None]
        if rr: nulls_v.append(np.mean(rr))
        pick2 = rng.choice(all_i, size=max(int(ms.sum()), 5), replace=False)
        rr2 = [episode(i + 1) for i in pick2 if S0 <= dates[i] <= S1]
        rr2 = [x for x in rr2 if x is not None]
        if rr2: nulls_s.append(np.mean(rr2))
    p95v = np.percentile(nulls_v, 95) if len(nulls_v) > 20 else np.nan
    pms = np.mean(nulls_s) if nulls_s else np.nan
    vm = real[mv].mean() if mv.sum() >= 5 else np.nan
    sm = real[ms].mean() if ms.sum() >= 3 else np.nan
    passed = (np.isfinite(vm) and vm > p95v) and (np.isfinite(sm) and np.isfinite(pms) and (sm - pms) > 0) and mv.sum() >= 60
    out = dict(cell=tag, n=int(len(real)), n_val=int(mv.sum()),
               val_mean=round(float(vm) * 100, 2) if np.isfinite(vm) else None,
               val_p95=round(float(p95v) * 100, 2) if np.isfinite(p95v) else None,
               scr_alpha=round(float(sm - pms) * 100, 2) if np.isfinite(sm) and np.isfinite(pms) else None,
               verdict="PASS" if passed else "FAIL")
    print(out, flush=True)
    return out

results = []
for tag, name in [("X1_nifty", "Nifty 50"), ("X2_bank", "Nifty Bank"), ("X3_midcap", "Nifty Midcap 100")]:
    Hh, Ll, Cc = load_idx(name)
    results.append(run_series_cell(tag, Hh, Ll, Cc, "rider", 0.0008))
results.append(run_series_cell("X4_gold", gH, gL, gC, "rider", 0.0012))
Hh, Ll, Cc = load_idx("Nifty 50")
results.append(run_series_cell("X5_nifty_short", Hh, Ll, Cc, "rider", 0.0008, short=True))
results.append(run_series_cell("X6_squeeze", Hh, Ll, Cc, "squeeze", 0.0008))
results.append(run_series_cell("X7_compress", Hh, Ll, Cc, "compression", 0.0008))
pd.DataFrame([r for r in results if r]).to_csv(OUT / "adx_atr_results.csv", index=False)
print("index/gold cells done; X8 stocks cell in part 2", flush=True)
