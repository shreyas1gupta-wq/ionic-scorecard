"""IDEA FACTORY screening harness v1 (protocol frozen in PROTOCOL.md).
Runs JSON idea-specs through a standardized daily backtest on the screen window.
Usage: python harness.py <specs.json> [--window screen|validate]
Emits one row per idea to screen_ledger.csv and prints a compact table.
"""
import json
import sys
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
HERE = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/IDEA_FACTORY"
SCREEN = (dt.date(2024, 7, 1), dt.date(2026, 6, 30))
VALIDATE = (dt.date(2015, 1, 1), dt.date(2024, 6, 30))
COST = {"stocks_daily": 0.0050, "index_daily": 0.0008, "crypto_1m": 0.0015, "gold_1m": 0.0012, "fo_daily": 0.0020}

# ---------- data loaders (cached) ----------
_cache = {}

def load_stocks():
    if "stocks" not in _cache:
        px = pd.read_parquet(ROOT / "datasets/nse_bhavcopy_daily/close_all.parquet")
        px["date"] = pd.to_datetime(px["date"])
        uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
        uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
        snaps = {d: set(g["Ticker"].astype(str).str.strip()) for d, g in uni.groupby("snap")}
        ever = set().union(*snaps.values())
        px = px[px.symbol.isin(ever)]
        _cache["stocks"] = ({s: g.set_index("date")["close"].sort_index() for s, g in px.groupby("symbol") if len(g) > 300},
                            sorted(snaps), snaps)
    return _cache["stocks"]

def load_index(name="NIFTY 50"):
    key = f"idx_{name}"
    if key not in _cache:
        frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
        ic = pd.concat(frames, ignore_index=True)
        ic = ic[ic["Index Name"].str.strip().str.upper() == name.strip().upper()]
        s = pd.Series(pd.to_numeric(ic["Closing Index Value"], errors="coerce").values,
                      index=pd.to_datetime(ic["file_date"])).dropna().sort_index()
        _cache[key] = s[~s.index.duplicated()]
    return _cache[key]

def load_vix():
    if "vix" not in _cache:
        _cache["vix"] = load_index("India VIX")
    return _cache["vix"]

def load_crypto(sym="BTCUSDT"):
    key = f"c_{sym}"
    if key not in _cache:
        frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/crypto_1m").glob(f"{sym}_*.parquet"))]
        df = pd.concat(frames).set_index("ts").sort_index()
        _cache[key] = df["close"].resample("1D").last().dropna()
    return _cache[key]

def load_gold():
    if "gold" not in _cache:
        frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/commodities_1m").glob("XAUUSD_1m_*.parquet"))]
        df = pd.concat(frames).set_index("ts").sort_index()
        _cache["gold"] = df["close"].resample("1D").last().dropna()
    return _cache["gold"]

# ---------- signal primitives (each returns boolean Series aligned to close series) ----------
def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def sig_series(c, sig, aux=None):
    t, p = sig["type"], sig.get("params", {})
    if t == "dma_cross":
        f, s = c.rolling(p["fast"]).mean(), c.rolling(p["slow"]).mean()
        return (f > s) & (f.shift(1) <= s.shift(1))
    if t == "dma_above":
        return c > c.rolling(p["n"]).mean()
    if t == "rsi_thresh":
        r = rsi(c, p["n"])
        return r < p["lt"] if "lt" in p else r > p["gt"]
    if t == "nday_breakout":
        return c > c.shift(1).rolling(p["n"]).max()
    if t == "nday_low":
        return c < c.shift(1).rolling(p["n"]).min()
    if t == "gap_pct":
        g = c.pct_change() * 100
        return g < p["lt"] if "lt" in p else g > p["gt"]
    if t == "distance_from_dma":
        d = (c / c.rolling(p["n"]).mean() - 1) * 100
        return d < p["lt"] if "lt" in p else d > p["gt"]
    if t == "consec_days":
        r = np.sign(c.diff())
        k = p["k"]
        s = pd.Series(True, index=c.index)
        for i in range(k):
            s &= (r.shift(i) == (1 if p.get("dir", "up") == "up" else -1))
        return s
    if t == "seasonality_dow":
        return pd.Series(c.index.dayofweek == p["dow"], index=c.index)
    if t == "seasonality_dom":
        return pd.Series(c.index.day <= p.get("first_n", 3), index=c.index) if p.get("turn") else \
               pd.Series(c.index.day >= p.get("after", 25), index=c.index)
    if t == "vol_expansion":
        v = c.pct_change().rolling(p.get("n", 5)).std()
        return v > v.rolling(p.get("base", 60)).mean() * p.get("mult", 1.5)
    if t == "vix_thresh":
        vix = load_vix().reindex(c.index, method="ffill")
        return vix < p["lt"] if "lt" in p else vix > p["gt"]
    if t == "zscore":
        m = c.rolling(p["n"]).mean(); s = c.rolling(p["n"]).std()
        z = (c - m) / s
        return z < p["lt"] if "lt" in p else z > p["gt"]
    raise ValueError(f"unknown signal {t}")

def combo_signal(c, spec):
    sigs = spec["signal"] if isinstance(spec["signal"], list) else [spec["signal"]]
    s = pd.Series(True, index=c.index)
    for sg in sigs:
        s &= sig_series(c, sg).fillna(False)
    return s

# ---------- backtest one series ----------
def run_series(c, spec, w0, w1, cost):
    sig = combo_signal(c, spec)
    ex = spec.get("exit", {"type": "bars", "params": {"n": 5}})
    short = spec.get("direction", "long") == "short"
    rets, dates = [], []
    i_arr = np.arange(len(c))
    sig_idx = i_arr[sig.values & (c.index.date >= w0) & (c.index.date <= w1)]
    last_exit = -1
    d5 = c.rolling(ex["params"].get("dma", 5)).mean() if ex["type"] == "trail_dma" else None
    for i in sig_idx:
        if i + 1 >= len(c) or i <= last_exit:
            continue
        entry = c.iloc[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        j_end = min(i + 1 + ex["params"].get("n", 10), len(c) - 1)
        exit_px, j_exit = c.iloc[j_end], j_end
        if ex["type"] == "trail_dma":
            for j in range(i + 2, j_end + 1):
                if (c.iloc[j] > d5.iloc[j]) if not short else (c.iloc[j] < d5.iloc[j]):
                    exit_px, j_exit = c.iloc[j], j
                    break
        elif ex["type"] == "target_sl":
            tgt, sl = ex["params"]["target"], ex["params"]["sl"]
            for j in range(i + 2, j_end + 1):
                r = (c.iloc[j] / entry - 1) * (-1 if short else 1)
                if r >= tgt or r <= -sl:
                    exit_px, j_exit = c.iloc[j], j
                    break
        r = (exit_px / entry - 1) * (-1 if short else 1) - cost
        rets.append(r); dates.append(c.index[i + 1])
        last_exit = j_exit
    return rets, dates

def run_idea(spec, window="screen"):
    w0, w1 = SCREEN if window == "screen" else VALIDATE
    cost = COST.get(spec.get("asset", "stocks_daily"), 0.005)
    all_rets, all_dates = [], []
    asset = spec.get("asset", "stocks_daily")
    if asset == "stocks_daily":
        series, snap_dates, snaps = load_stocks()
        for sym, c in series.items():
            rr, dd = run_series(c, spec, w0, w1, cost)
            # PIT gate at trade date
            for r, d in zip(rr, dd):
                prior = [s for s in snap_dates if s <= d.date()]
                if prior and sym in snaps[prior[-1]]:
                    all_rets.append(r); all_dates.append(d)
    else:
        c = {"index_daily": lambda: load_index(spec.get("universe", "NIFTY 50")),
             "crypto_1m": lambda: load_crypto(spec.get("universe", "BTCUSDT")),
             "gold_1m": load_gold}[asset]()
        all_rets, all_dates = run_series(c, spec, w0, w1, cost)
    n = len(all_rets)
    if n < 5:
        return dict(n=n, mean=np.nan, t=np.nan, gate=False)
    x = np.array(all_rets)
    t = x.mean() / (x.std(ddof=1) / np.sqrt(n)) if x.std(ddof=1) > 0 else np.nan
    gate = (x.mean() > 2 * cost) and (t >= 1.5) and (n >= 30)
    return dict(n=n, mean=x.mean() * 100, t=t, win=float((x > 0).mean() * 100), gate=bool(gate))

if __name__ == "__main__":
    specs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    window = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--window" else "screen"
    ledger_p = HERE / "screen_ledger.csv"
    rows = []
    for spec in specs:
        try:
            res = run_idea(spec, window)
        except Exception as e:
            res = dict(n=0, mean=np.nan, t=np.nan, gate=False, err=str(e)[:60])
        row = dict(run_ts=dt.datetime.now().isoformat(timespec="seconds"), window=window,
                   id=spec["id"], name=spec.get("name", "")[:60], asset=spec.get("asset", ""),
                   **res)
        rows.append(row)
        print(f"{spec['id']:<28} n={res.get('n',0):>5}  mean={res.get('mean',float('nan')):+7.3f}%  "
              f"t={res.get('t',float('nan')):+5.2f}  {'>>> GATE PASS' if res.get('gate') else ''}"
              f"  {res.get('err','')}", flush=True)
    led = pd.DataFrame(rows)
    if ledger_p.exists():
        led = pd.concat([pd.read_csv(ledger_p), led], ignore_index=True)
    led.to_csv(ledger_p, index=False)
    print(f"\nledger: {ledger_p} ({len(led)} total rows)", flush=True)
