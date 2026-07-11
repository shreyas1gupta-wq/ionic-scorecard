"""Comprehensive analysis of Chartlink momentum-breakout scanner signals.
221 signals Nov 2025 - Jul 2026. VCP/Minervini-style breakout + volume + RSI + BB scanner.
Analyzes: forward returns, SL/trail/target optimization, earnings, CANSLIM, position sizing.
"""
import sys, time, warnings, os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SIG_CSV = Path(r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (1).csv")
ANGEL_PQ = ROOT / "datasets" / "angel_daily_n500_2026.parquet"
EARN_PIT = ROOT / "datasets" / "earnings_pit" / "unified_quarterly_pit.parquet"
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "BREAKOUT_SCAN_20260710"
OUT.mkdir(parents=True, exist_ok=True)

GAME = ROOT / "Shreyas_Ionic_AMC" / "09_PRODUCT" / "fno_game" / "server"
HORIZONS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 40]
t0 = time.time()

# =====================================================================
# 1. DATA LOAD & MERGE
# =====================================================================
print("=" * 70)
print("SECTION 1: DATA LOAD & MERGE")
print("=" * 70)

sig = pd.read_csv(SIG_CSV, quotechar='"', skipinitialspace=True)
sig.columns = [c.strip().strip('"') for c in sig.columns]
for c in sig.columns:
    sig[c] = sig[c].astype(str).str.strip().str.strip('"')
sig["date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig["symbol"] = sig["Symbol"]
sig["mcap"] = sig["Marketcapname"]
sig["sector"] = sig["Sector"]
print(f"Signals: {len(sig)}, unique symbols: {sig['symbol'].nunique()}, "
      f"range: {sig['date'].min().date()} -> {sig['date'].max().date()}")

ang = pd.read_parquet(ANGEL_PQ)
ang["date"] = ang["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
ang["date"] = pd.to_datetime(ang["date"])
ang = ang.drop(columns=["timestamp"]).sort_values(["symbol", "date"]).reset_index(drop=True)
print(f"Angel daily: {len(ang)} rows, {ang['symbol'].nunique()} syms, "
      f"{ang['date'].min().date()} -> {ang['date'].max().date()}")

ang_syms = set(ang["symbol"].unique())
sig_syms = set(sig["symbol"].unique())
missing = sorted(sig_syms - ang_syms)
print(f"Overlap: {len(sig_syms & ang_syms)}, missing: {len(missing)}")

# Supplement via yfinance
import truststore; truststore.inject_into_ssl()
import yfinance as yf

yf_rows = []
downloaded = set()
if missing:
    print(f"Downloading {len(missing)} missing symbols via yfinance...")
    for i, sym in enumerate(missing):
        try:
            t = yf.Ticker(sym + ".NS")
            h = t.history(start="2025-10-01", end="2026-07-15", auto_adjust=True)
            if len(h) == 0:
                continue
            for dt, row in h.iterrows():
                dt_val = pd.Timestamp(dt)
                if dt_val.tzinfo:
                    dt_val = dt_val.tz_localize(None)
                yf_rows.append(dict(date=pd.Timestamp(dt_val.date()),
                                    open=row["Open"], high=row["High"],
                                    low=row["Low"], close=row["Close"],
                                    volume=int(row.get("Volume", 0)), symbol=sym))
            downloaded.add(sym)
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(missing)} done, {len(downloaded)} succeeded")
    print(f"  yfinance: {len(downloaded)} symbols, {len(yf_rows)} rows")

if yf_rows:
    yf_df = pd.DataFrame(yf_rows)
    yf_df["date"] = pd.to_datetime(yf_df["date"])
    ang = pd.concat([ang, yf_df], ignore_index=True)
    ang = ang.sort_values(["symbol", "date"]).reset_index(drop=True)

still_missing = sorted(sig_syms - set(ang["symbol"].unique()))
if still_missing:
    print(f"Still missing ({len(still_missing)}): {still_missing[:20]}...")

# 2nd pass: symbols IN angel but signal dates OUTSIDE angel date range
ang_date_range = {}
for sym, g in ang.groupby("symbol"):
    ang_date_range[sym] = (g["date"].min(), g["date"].max())

yf_rows2 = []
gap_syms = set()
for _, row in sig.iterrows():
    sym = row["symbol"]
    if sym not in ang_date_range:
        continue
    amin, amax = ang_date_range[sym]
    sdate = row["date"]
    # need ~30d before signal for lookback and ~45d after for fwd returns
    need_from = sdate - pd.Timedelta(days=30)
    need_to = sdate + pd.Timedelta(days=50)
    if need_from < amin or sdate < amin:
        gap_syms.add(sym)

if gap_syms:
    print(f"2nd pass: {len(gap_syms)} symbols have signal dates outside Angel range, downloading via yfinance...")
    for i, sym in enumerate(sorted(gap_syms)):
        if sym in downloaded:
            continue
        try:
            t = yf.Ticker(sym + ".NS")
            h = t.history(start="2025-09-01", end="2026-07-15", auto_adjust=True)
            if len(h) == 0:
                continue
            for dt2, r2 in h.iterrows():
                dt_val = pd.Timestamp(dt2)
                if dt_val.tzinfo:
                    dt_val = dt_val.tz_localize(None)
                d = pd.Timestamp(dt_val.date())
                if d < ang_date_range[sym][0]:
                    yf_rows2.append(dict(date=d, open=r2["Open"], high=r2["High"],
                                         low=r2["Low"], close=r2["Close"],
                                         volume=int(r2.get("Volume", 0)), symbol=sym))
            downloaded.add(sym)
        except Exception:
            pass
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(gap_syms)} done")
    print(f"  2nd pass: {len(yf_rows2)} rows added for {len(gap_syms)} symbols")
    if yf_rows2:
        yf2 = pd.DataFrame(yf_rows2)
        yf2["date"] = pd.to_datetime(yf2["date"])
        ang = pd.concat([ang, yf2], ignore_index=True)
        ang = ang.sort_values(["symbol", "date"]).reset_index(drop=True)

# Also load pre-downloaded missing data if available
yf_extra_path = OUT / "yf_missing_39.parquet"
if yf_extra_path.exists():
    yf_extra = pd.read_parquet(yf_extra_path)
    yf_extra["date"] = pd.to_datetime(yf_extra["date"])
    # Only add rows not already present
    existing_keys = set(zip(ang["symbol"], ang["date"].dt.date))
    mask = yf_extra.apply(lambda r: (r["symbol"], r["date"].date()) not in existing_keys, axis=1)
    new_rows = yf_extra[mask]
    if len(new_rows) > 0:
        ang = pd.concat([ang, new_rows], ignore_index=True)
        ang = ang.sort_values(["symbol", "date"]).reset_index(drop=True)
        print(f"  Loaded {len(new_rows)} extra rows from yf_missing_39.parquet")

final_coverage = set(ang["symbol"].unique()) & sig_syms
print(f"Final coverage: {len(final_coverage)}/{len(sig_syms)} symbols")

# Load Nifty 50 daily from game server data
sys.path.insert(0, str(GAME))
import data_loader as dl
nifty_1m = dl._spot()
nifty_daily = nifty_1m.groupby("d").agg(
    nifty_open=("open", "first"), nifty_high=("high", "max"),
    nifty_low=("low", "min"), nifty_close=("close", "last")
).reset_index().rename(columns={"d": "date"})
nifty_daily["date"] = pd.to_datetime(nifty_daily["date"])
nifty_daily["nifty_sma20"] = nifty_daily["nifty_close"].rolling(20).mean()
nifty_daily["nifty_sma50"] = nifty_daily["nifty_close"].rolling(50).mean()
nifty_daily["nifty_above_20dma"] = nifty_daily["nifty_close"] > nifty_daily["nifty_sma20"]
print(f"Nifty daily: {len(nifty_daily)} days, {nifty_daily['date'].min().date()} -> {nifty_daily['date'].max().date()}")

# Load earnings PIT
ep = pd.read_parquet(EARN_PIT)
ep["available_date"] = pd.to_datetime(ep["available_date"])
ep["quarter_end"] = pd.to_datetime(ep["quarter_end"])
print(f"Earnings PIT: {len(ep)} rows, {ep['symbol'].nunique()} symbols")

# Build per-symbol daily arrays
sym_daily = {}
for sym, g in ang.groupby("symbol"):
    sym_daily[sym] = g.sort_values("date").reset_index(drop=True)

# =====================================================================
# 2. COMPUTE TRADE FEATURES & FORWARD RETURNS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 2: FORWARD RETURNS & FEATURES")
print("=" * 70)

def get_nifty_context(dt):
    row = nifty_daily[nifty_daily["date"] <= dt]
    if len(row) == 0:
        return {}
    r = row.iloc[-1]
    return {"nifty_close": r["nifty_close"],
            "nifty_above_20dma": bool(r["nifty_above_20dma"]) if pd.notna(r.get("nifty_above_20dma")) else None}

def get_earnings_context(sym, sig_dt):
    sym_ep = ep[ep["symbol"] == sym].sort_values("available_date")
    past = sym_ep[sym_ep["available_date"] <= sig_dt]
    result = {"days_since_earn": np.nan, "q1_sales_yoy_pct": np.nan,
              "q2_sales_yoy_pct": np.nan, "q1_profit_yoy": np.nan,
              "sales_qoq_pct": np.nan, "profit_positive_2q": np.nan}
    if len(past) == 0:
        return result
    last = past.iloc[-1]
    result["days_since_earn"] = (sig_dt - last["available_date"]).days

    if len(past) >= 2:
        q1, q2 = past.iloc[-1], past.iloc[-2]
        if pd.notna(q2["sales"]) and q2["sales"] > 0:
            result["sales_qoq_pct"] = round((q1["sales"] / q2["sales"] - 1) * 100, 1)

    for qi, prefix in [(1, "q1"), (2, "q2")]:
        if len(past) < qi:
            continue
        q = past.iloc[-qi]
        qe = q["quarter_end"]
        yoy_match = past[past["quarter_end"] == qe - pd.DateOffset(years=1)]
        if len(yoy_match) > 0:
            yoy = yoy_match.iloc[-1]
            if pd.notna(yoy["sales"]) and yoy["sales"] > 0:
                result[f"{prefix}_sales_yoy_pct"] = round((q["sales"] / yoy["sales"] - 1) * 100, 1)
            if pd.notna(yoy["net_profit"]):
                result[f"{prefix}_profit_yoy"] = round(q["net_profit"] - yoy["net_profit"], 1)

    if len(past) >= 2:
        p1 = past.iloc[-1].get("net_profit", 0) or 0
        p2 = past.iloc[-2].get("net_profit", 0) or 0
        result["profit_positive_2q"] = 1 if (p1 > 0 and p2 > 0) else 0
    return result

def compute_trade(sig_date, symbol, mcap, sector):
    if symbol not in sym_daily:
        return None
    df = sym_daily[symbol]
    sig_idx = df.index[df["date"] == sig_date]
    if len(sig_idx) == 0:
        future = df[df["date"] > sig_date]
        if len(future) == 0:
            return None
        sig_idx = [future.index[0]]
    si = sig_idx[0]
    loc_si = df.index.get_loc(si)

    entry_loc = loc_si + 1
    if entry_loc >= len(df):
        return None
    entry_row = df.iloc[entry_loc]
    entry_price = entry_row["open"]
    if pd.isna(entry_price) or entry_price <= 0:
        return None
    entry_date = entry_row["date"]

    sd = df.iloc[loc_si]
    if loc_si < 1:
        return None
    prev = df.iloc[loc_si - 1]

    pc = prev["close"]
    if pc <= 0 or pd.isna(pc):
        return None

    gap_pct = (sd["open"] - pc) / pc * 100
    body_pct = (sd["close"] - sd["open"]) / sd["open"] * 100 if sd["open"] > 0 else 0
    range_pct = (sd["high"] - sd["low"]) / sd["low"] * 100 if sd["low"] > 0 else 0
    cir = (sd["close"] - sd["low"]) / (sd["high"] - sd["low"] + 1e-9)
    uw_pct = (sd["high"] - sd["close"]) / sd["close"] * 100 if sd["close"] > 0 else 0
    daily_chg = (sd["close"] - pc) / pc * 100
    lb_start = max(0, loc_si - 20)
    vol_20d = df.iloc[lb_start:loc_si]["volume"].mean() if loc_si > 0 else 1
    vol_ratio = sd["volume"] / vol_20d if vol_20d > 0 else 1
    turnover = sd["close"] * sd["volume"]

    # RSI(14) at signal day
    rsi = np.nan
    if loc_si >= 14:
        closes_arr = df.iloc[loc_si - 14:loc_si + 1]["close"].values
        deltas = np.diff(closes_arr)
        avg_g = np.where(deltas > 0, deltas, 0).mean()
        avg_l = np.where(deltas < 0, -deltas, 0).mean()
        rsi = 100 - 100 / (1 + avg_g / (avg_l + 1e-9)) if avg_l > 0 else 100

    # 20DMA / 50DMA for the stock
    above_20dma = np.nan
    above_50dma = np.nan
    if loc_si >= 20:
        sma20 = df.iloc[loc_si - 19:loc_si + 1]["close"].mean()
        above_20dma = sd["close"] > sma20
    if loc_si >= 50:
        sma50 = df.iloc[loc_si - 49:loc_si + 1]["close"].mean()
        above_50dma = sd["close"] > sma50

    # VCP: range contraction over last 5 bars
    vcp_score = np.nan
    if loc_si >= 5:
        ranges = []
        for j in range(loc_si - 4, loc_si + 1):
            r_j = df.iloc[j]
            ranges.append((r_j["high"] - r_j["low"]) / r_j["close"] * 100 if r_j["close"] > 0 else 0)
        if ranges[0] > 0:
            vcp_score = round(ranges[-1] / ranges[0], 2)

    # New high check (proxy for CANSLIM N)
    new_hi = np.nan
    lookback = min(loc_si, 252)
    if lookback >= 50:
        hi_252 = df.iloc[loc_si - lookback:loc_si]["high"].max()
        new_hi = 1 if sd["high"] >= hi_252 * 0.97 else 0

    # Relative strength vs cohort (50d return rank)
    rs_rank = np.nan
    if loc_si >= 50:
        stock_ret50 = (sd["close"] / df.iloc[loc_si - 50]["close"] - 1) * 100
        all_rets = []
        for s2, d2 in sym_daily.items():
            if len(d2) < 51:
                continue
            dt_match = d2[d2["date"] == sd["date"]]
            if len(dt_match) == 0:
                continue
            loc2 = d2.index.get_loc(dt_match.index[0])
            if loc2 >= 50:
                all_rets.append((d2.iloc[loc2]["close"] / d2.iloc[loc2 - 50]["close"] - 1) * 100)
        if all_rets:
            rs_rank = round(np.searchsorted(sorted(all_rets), stock_ret50) / len(all_rets) * 100, 1)

    nifty_ctx = get_nifty_context(sig_date)
    earn_ctx = get_earnings_context(symbol, sig_date)

    result = {
        "signal_date": sig_date, "entry_date": entry_date, "symbol": symbol,
        "mcap": mcap, "sector": sector,
        "entry_price": round(entry_price, 2), "signal_close": round(sd["close"], 2),
        "signal_high": round(sd["high"], 2),
        "gap_pct": round(gap_pct, 2), "body_pct": round(body_pct, 2),
        "range_pct": round(range_pct, 2), "close_in_range": round(cir, 3),
        "upper_wick_pct": round(uw_pct, 2), "daily_chg_pct": round(daily_chg, 2),
        "vol_ratio": round(vol_ratio, 2), "turnover_cr": round(turnover / 1e7, 2),
        "rsi14": round(rsi, 1) if not np.isnan(rsi) else np.nan,
        "above_20dma": above_20dma, "above_50dma": above_50dma,
        "vcp_score": vcp_score, "new_hi": new_hi, "rs_rank": rs_rank,
        "nifty_above_20dma": nifty_ctx.get("nifty_above_20dma"),
    }
    result.update(earn_ctx)

    # Forward returns + MAE/MFE
    fwd_closes, fwd_highs, fwd_lows = [], [], []
    for h in HORIZONS:
        fwd_loc = entry_loc + h
        if fwd_loc >= len(df):
            result[f"ret_{h}d"] = np.nan
            result[f"mae_{h}d"] = np.nan
            result[f"mfe_{h}d"] = np.nan
        else:
            fc = df.iloc[fwd_loc]["close"]
            ret = (fc - entry_price) / entry_price * 100
            lows = df.iloc[entry_loc:fwd_loc + 1]["low"].values
            highs = df.iloc[entry_loc:fwd_loc + 1]["high"].values
            mae = (lows.min() - entry_price) / entry_price * 100
            mfe = (highs.max() - entry_price) / entry_price * 100
            result[f"ret_{h}d"] = round(ret, 2)
            result[f"mae_{h}d"] = round(mae, 2)
            result[f"mfe_{h}d"] = round(mfe, 2)

    max_fwd = min(entry_loc + 61, len(df))
    fwd_closes = df.iloc[entry_loc:max_fwd]["close"].values.astype(float)
    fwd_highs = df.iloc[entry_loc:max_fwd]["high"].values.astype(float)
    fwd_lows = df.iloc[entry_loc:max_fwd]["low"].values.astype(float)

    # "Buy above high" trigger: entry at signal_high + 0.1% next day
    trigger_price = sd["high"] * 1.001
    if entry_row["high"] >= trigger_price:
        result["trigger_entry"] = round(max(trigger_price, entry_row["open"]), 2)
    else:
        result["trigger_entry"] = np.nan

    return result, (fwd_closes, fwd_highs, fwd_lows)

trades = []
fwd_arrays = []
n_skip = 0
for idx, row in sig.iterrows():
    out = compute_trade(row["date"], row["symbol"], row["mcap"], row["sector"])
    if out is None:
        n_skip += 1
        continue
    trade_dict, fwd = out
    trades.append(trade_dict)
    fwd_arrays.append(fwd)

print(f"Computed: {len(trades)} trades, skipped: {n_skip}")
df_t = pd.DataFrame(trades)
df_t.to_csv(OUT / "trades_detail.csv", index=False)

# =====================================================================
# 3. BASE STATISTICS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 3: BASE STATISTICS (buy next-day open, hold N days)")
print("=" * 70)

base_rows = []
for h in HORIZONS:
    col = f"ret_{h}d"
    v = df_t[col].dropna()
    if len(v) == 0:
        continue
    base_rows.append({
        "horizon": f"{h}d", "n": len(v),
        "mean%": round(v.mean(), 2), "median%": round(v.median(), 2),
        "win%": round((v > 0).mean() * 100, 1),
        "avg_win%": round(v[v > 0].mean(), 2) if (v > 0).any() else 0,
        "avg_loss%": round(v[v < 0].mean(), 2) if (v < 0).any() else 0,
        "pf": round(v[v > 0].sum() / abs(v[v < 0].sum()), 2) if (v < 0).any() else 999,
        "best%": round(v.max(), 2), "worst%": round(v.min(), 2),
    })
bdf = pd.DataFrame(base_rows)
print(bdf.to_string(index=False))
bdf.to_csv(OUT / "base_forward_returns.csv", index=False)

print("\nMAE / MFE summary:")
for h in [5, 10, 20]:
    mae = df_t[f"mae_{h}d"].dropna()
    mfe = df_t[f"mfe_{h}d"].dropna()
    if len(mae) > 0:
        print(f"  {h}d: median MAE={mae.median():.2f}%, p10={mae.quantile(0.1):.2f}%  |  "
              f"median MFE={mfe.median():.2f}%, p90={mfe.quantile(0.9):.2f}%")

# Entry trigger comparison
trig_mask = df_t["trigger_entry"].notna()
if trig_mask.sum() > 10:
    print(f"\nBuy-above-high trigger: {trig_mask.sum()}/{len(df_t)} signals triggered")
    for h in [5, 10, 20]:
        v_open = df_t[f"ret_{h}d"].dropna()
        # Recalc returns for trigger entry
        trig_rets = []
        for i, row in df_t[trig_mask].iterrows():
            tp = row["trigger_entry"]
            # find fwd_arrays index
            arr_idx = df_t.index.get_loc(i)
            fc = fwd_arrays[arr_idx][0]
            if len(fc) > h:
                trig_rets.append((fc[h] - tp) / tp * 100)
        if trig_rets:
            tr = np.array(trig_rets)
            print(f"  {h}d: open-entry mean={v_open.mean():.2f}% vs trigger-entry mean={tr.mean():.2f}% "
                  f"(trigger win%={(tr>0).mean()*100:.0f}%, n={len(tr)})")

# =====================================================================
# 4. ENTRY QUALITY ANALYSIS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 4: ENTRY QUALITY (what predicts 10d fwd return)")
print("=" * 70)

ref_col = "ret_10d"
for feature, bins, labels in [
    ("daily_chg_pct", [0, 3, 5, 7, 10, 100], ["<3%", "3-5%", "5-7%", "7-10%", "10%+"]),
    ("vol_ratio", [0, 1.5, 2.5, 4, 100], ["<1.5x", "1.5-2.5x", "2.5-4x", "4x+"]),
    ("gap_pct", [-100, -0.5, 0.5, 2, 100], ["gap-dn", "flat", "gap-up", "big-gap"]),
    ("close_in_range", [0, 0.7, 0.85, 0.95, 1.01], ["<70%", "70-85%", "85-95%", "95-100%"]),
    ("upper_wick_pct", [-1, 0.3, 0.7, 1.5, 100], ["<0.3%", "0.3-0.7%", "0.7-1.5%", "1.5%+"]),
    ("rsi14", [0, 55, 65, 75, 100], ["<55", "55-65", "65-75", "75+"]),
    ("vcp_score", [0, 0.3, 0.6, 0.9, 10], ["<0.3", "0.3-0.6", "0.6-0.9", "0.9+"]),
]:
    v = df_t[feature].dropna()
    if len(v) < 20:
        continue
    df_t["_b"] = pd.cut(df_t[feature], bins=bins, labels=labels[:len(bins)-1], include_lowest=True)
    print(f"\n{feature}:")
    for bname, g in df_t.dropna(subset=["_b", ref_col]).groupby("_b", observed=True):
        r = g[ref_col]
        if len(r) < 3:
            continue
        print(f"  {bname:>12}: n={len(r):>3}, mean={r.mean():>6.2f}%, "
              f"win={(r>0).mean()*100:>4.0f}%, median={r.median():>6.2f}%")
    df_t.drop(columns=["_b"], inplace=True)

# =====================================================================
# 5. STOP LOSS OPTIMIZATION
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 5: STOP LOSS OPTIMIZATION")
print("=" * 70)

def sim_sl_target(fc, fl, fh, ep, sl_pct, tgt_pct=None, max_days=30):
    n = len(fc)
    if n <= 1:
        return None
    for i in range(1, min(n, max_days + 1)):
        if fl[i] <= ep * (1 - sl_pct / 100):
            return {"days": i, "ret": -sl_pct, "reason": "SL"}
        if tgt_pct and fh[i] >= ep * (1 + tgt_pct / 100):
            return {"days": i, "ret": tgt_pct, "reason": "target"}
    ei = min(n - 1, max_days)
    return {"days": ei, "ret": (fc[ei] - ep) / ep * 100, "reason": "time"}

def sim_trail(fc, fl, ep, trail_pct, init_sl_pct, max_days=30):
    n = len(fc)
    if n <= 1:
        return None
    peak = ep
    for i in range(1, min(n, max_days + 1)):
        if fc[i] > peak:
            peak = fc[i]
        trail_stop = peak * (1 - trail_pct / 100)
        hard_stop = ep * (1 - init_sl_pct / 100)
        stop = max(trail_stop, hard_stop)
        if fl[i] <= stop:
            exit_p = max(stop, fl[i])
            return {"days": i, "ret": (exit_p - ep) / ep * 100,
                    "reason": "trail" if trail_stop >= hard_stop else "SL"}
    ei = min(n - 1, max_days)
    return {"days": ei, "ret": (fc[ei] - ep) / ep * 100, "reason": "time"}

sl_grid = []
for sl in [2, 3, 4, 5, 7, 10, 15]:
    for md in [10, 20, 30]:
        rets = []
        for idx in range(len(df_t)):
            fc, fh, fl = fwd_arrays[idx]
            r = sim_sl_target(fc, fl, fh, df_t.iloc[idx]["entry_price"], sl, max_days=md)
            if r:
                rets.append(r["ret"])
        if not rets:
            continue
        a = np.array(rets)
        sl_grid.append({
            "SL%": sl, "max_d": md, "n": len(a),
            "win%": round((a > 0).mean() * 100, 1),
            "mean%": round(a.mean(), 2),
            "total%": round(a.sum(), 1),
            "pf": round(a[a > 0].sum() / abs(a[a < 0].sum()), 2) if (a < 0).any() else 999,
            "sl_hit%": round(sum(1 for x in rets if isinstance(x, float) or True) and
                             sum(1 for i, r in enumerate(rets) if True) and 0, 1),
        })
        # Fix sl_hit calculation
        sl_grid[-1]["sl_hit%"] = 0  # placeholder

# Recalculate properly
sl_grid = []
for sl in [2, 3, 4, 5, 7, 10, 15]:
    for md in [10, 20, 30]:
        results = []
        for idx in range(len(df_t)):
            fc, fh, fl = fwd_arrays[idx]
            r = sim_sl_target(fc, fl, fh, df_t.iloc[idx]["entry_price"], sl, max_days=md)
            if r:
                results.append(r)
        if not results:
            continue
        rets = np.array([r["ret"] for r in results])
        sl_hits = sum(1 for r in results if r["reason"] == "SL")
        sl_grid.append({
            "SL%": sl, "max_d": md, "n": len(results),
            "win%": round((rets > 0).mean() * 100, 1),
            "mean%": round(rets.mean(), 2),
            "total%": round(rets.sum(), 1),
            "pf": round(rets[rets > 0].sum() / abs(rets[rets < 0].sum()), 2) if (rets < 0).any() else 999,
            "sl_hit%": round(sl_hits / len(results) * 100, 1),
            "avg_days": round(np.mean([r["days"] for r in results]), 1),
        })

sl_df = pd.DataFrame(sl_grid)
print(sl_df.to_string(index=False))
sl_df.to_csv(OUT / "sl_optimization.csv", index=False)

# =====================================================================
# 6. TRAILING STOP OPTIMIZATION
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 6: TRAILING STOP")
print("=" * 70)

trail_grid = []
for tr in [3, 5, 7, 10]:
    for isl in [5, 7, 10]:
        for md in [15, 20, 30]:
            results = []
            for idx in range(len(df_t)):
                fc, fh, fl = fwd_arrays[idx]
                r = sim_trail(fc, fl, df_t.iloc[idx]["entry_price"], tr, isl, md)
                if r:
                    results.append(r)
            if not results:
                continue
            rets = np.array([r["ret"] for r in results])
            trail_grid.append({
                "trail%": tr, "init_SL%": isl, "max_d": md,
                "n": len(results), "win%": round((rets > 0).mean() * 100, 1),
                "mean%": round(rets.mean(), 2), "total%": round(rets.sum(), 1),
                "pf": round(rets[rets > 0].sum() / abs(rets[rets < 0].sum()), 2) if (rets < 0).any() else 999,
                "avg_days": round(np.mean([r["days"] for r in results]), 1),
            })
trl_df = pd.DataFrame(trail_grid)
print(trl_df.sort_values("mean%", ascending=False).head(20).to_string(index=False))
trl_df.to_csv(OUT / "trailing_optimization.csv", index=False)

# =====================================================================
# 7. TARGET + SL COMBOS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 7: TARGET + SL COMBOS")
print("=" * 70)

tgt_grid = []
for sl in [5, 7, 10]:
    for tgt in [5, 8, 10, 15, 20]:
        for md in [20, 30]:
            results = []
            for idx in range(len(df_t)):
                fc, fh, fl = fwd_arrays[idx]
                r = sim_sl_target(fc, fl, fh, df_t.iloc[idx]["entry_price"], sl, tgt, md)
                if r:
                    results.append(r)
            if not results:
                continue
            rets = np.array([r["ret"] for r in results])
            th = sum(1 for r in results if r["reason"] == "target")
            sh = sum(1 for r in results if r["reason"] == "SL")
            tgt_grid.append({
                "SL%": sl, "tgt%": tgt, "max_d": md, "n": len(results),
                "win%": round((rets > 0).mean() * 100, 1),
                "mean%": round(rets.mean(), 2), "total%": round(rets.sum(), 1),
                "pf": round(rets[rets > 0].sum() / abs(rets[rets < 0].sum()), 2) if (rets < 0).any() else 999,
                "tgt_hit%": round(th / len(results) * 100, 1),
                "sl_hit%": round(sh / len(results) * 100, 1),
            })
tdf = pd.DataFrame(tgt_grid)
print(tdf.sort_values("mean%", ascending=False).head(15).to_string(index=False))
tdf.to_csv(OUT / "target_sl_grid.csv", index=False)

# =====================================================================
# 8. PARTIAL PROFIT
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 8: PARTIAL PROFIT")
print("=" * 70)

def sim_partial(fc, fl, fh, ep, sl_pct, t1_pct, trail_pct, max_days=30):
    n = len(fc)
    if n <= 1:
        return None
    peak = ep
    booked = False
    pnl1 = 0
    for i in range(1, min(n, max_days + 1)):
        if not booked:
            if fl[i] <= ep * (1 - sl_pct / 100):
                return {"days": i, "ret": -sl_pct, "reason": "SL_full"}
            if fh[i] >= ep * (1 + t1_pct / 100):
                pnl1 = t1_pct / 2
                booked = True
                peak = fh[i]
                continue
        else:
            if fc[i] > peak:
                peak = fc[i]
            trail_stop = peak * (1 - trail_pct / 100)
            stop = max(trail_stop, ep)
            if fl[i] <= stop:
                exit_p = max(stop, fl[i])
                r2 = (exit_p - ep) / ep * 100 / 2
                return {"days": i, "ret": pnl1 + r2, "reason": "partial+trail"}
    ei = min(n - 1, max_days)
    final = (fc[ei] - ep) / ep * 100
    if booked:
        return {"days": ei, "ret": pnl1 + final / 2, "reason": "time"}
    return {"days": ei, "ret": final, "reason": "time"}

part_grid = []
for sl in [5, 7]:
    for t1 in [5, 8, 10]:
        for tr in [5, 7]:
            results = []
            for idx in range(len(df_t)):
                fc, fh, fl = fwd_arrays[idx]
                r = sim_partial(fc, fl, fh, df_t.iloc[idx]["entry_price"], sl, t1, tr, 30)
                if r:
                    results.append(r)
            if not results:
                continue
            rets = np.array([r["ret"] for r in results])
            part_grid.append({
                "SL%": sl, "T1%": t1, "trail%": tr,
                "n": len(results), "win%": round((rets > 0).mean() * 100, 1),
                "mean%": round(rets.mean(), 2), "total%": round(rets.sum(), 1),
                "pf": round(rets[rets > 0].sum() / abs(rets[rets < 0].sum()), 2) if (rets < 0).any() else 999,
            })
pdf = pd.DataFrame(part_grid)
print(pdf.sort_values("mean%", ascending=False).to_string(index=False))
pdf.to_csv(OUT / "partial_profit_grid.csv", index=False)

# =====================================================================
# 9. EARNINGS ANALYSIS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 9: EARNINGS PROXIMITY & MOMENTUM")
print("=" * 70)

print("\nDays since earnings -> 10d fwd return:")
for lo, hi, label in [(0, 5, "0-5d"), (5, 15, "5-15d"), (15, 30, "15-30d"),
                       (30, 60, "30-60d"), (60, 999, "60d+")]:
    mask = (df_t["days_since_earn"] >= lo) & (df_t["days_since_earn"] < hi) & df_t["ret_10d"].notna()
    sub = df_t[mask]["ret_10d"]
    if len(sub) >= 3:
        print(f"  {label:>8}: n={len(sub):>3}, mean={sub.mean():>6.2f}%, win={(sub>0).mean()*100:>4.0f}%")

print("\nLast Q sales YoY growth -> 10d fwd:")
for lo, hi, label in [(-999, 0, "negative"), (0, 15, "0-15%"), (15, 30, "15-30%"), (30, 999, "30%+")]:
    mask = (df_t["q1_sales_yoy_pct"] >= lo) & (df_t["q1_sales_yoy_pct"] < hi) & df_t["ret_10d"].notna()
    sub = df_t[mask]["ret_10d"]
    if len(sub) >= 3:
        print(f"  {label:>12}: n={len(sub):>3}, mean={sub.mean():>6.2f}%, win={(sub>0).mean()*100:>4.0f}%")

print("\nProfit positive last 2Q -> 10d fwd:")
for val, label in [(1, "Yes"), (0, "No")]:
    mask = (df_t["profit_positive_2q"] == val) & df_t["ret_10d"].notna()
    sub = df_t[mask]["ret_10d"]
    if len(sub) >= 3:
        print(f"  {label}: n={len(sub):>3}, mean={sub.mean():>6.2f}%, win={(sub>0).mean()*100:>4.0f}%")

# =====================================================================
# 10. CANSLIM COMPOSITE SCORE
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 10: CANSLIM SCORE")
print("=" * 70)

df_t["canslim"] = 0.0
df_t.loc[df_t["q1_sales_yoy_pct"] > 25, "canslim"] += 1  # C
df_t.loc[df_t["profit_positive_2q"] == 1, "canslim"] += 1  # A (proxy)
df_t.loc[df_t["new_hi"] == 1, "canslim"] += 1  # N
df_t.loc[df_t["mcap"] == "Smallcap", "canslim"] += 1  # S (smaller supply)
df_t.loc[df_t["mcap"] == "Midcap", "canslim"] += 0.5
df_t.loc[df_t["rs_rank"] > 80, "canslim"] += 1  # L
df_t.loc[df_t["nifty_above_20dma"] == True, "canslim"] += 1  # M

print("CANSLIM score -> 10d fwd return:")
for lo, hi, label in [(0, 2, "0-1"), (2, 3, "2"), (3, 4, "3"), (4, 7, "4+")]:
    mask = (df_t["canslim"] >= lo) & (df_t["canslim"] < hi) & df_t["ret_10d"].notna()
    sub = df_t[mask]["ret_10d"]
    if len(sub) >= 3:
        print(f"  Score {label}: n={len(sub):>3}, mean={sub.mean():>6.2f}%, win={(sub>0).mean()*100:>4.0f}%")

# =====================================================================
# 11. SECTOR & CAP BREAKDOWN
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 11: SECTOR & MARKET CAP")
print("=" * 70)

print("\nBy Sector (10d, n>=3):")
sec_rows = []
for sec, g in df_t.dropna(subset=["ret_10d"]).groupby("sector"):
    r = g["ret_10d"]
    if len(r) < 3:
        continue
    sec_rows.append({"sector": sec, "n": len(r), "mean%": round(r.mean(), 2),
                     "win%": round((r > 0).mean() * 100, 1), "median%": round(r.median(), 2)})
sec_df = pd.DataFrame(sec_rows).sort_values("mean%", ascending=False)
print(sec_df.to_string(index=False))

print("\nBy Market Cap:")
for mc, g in df_t.dropna(subset=["ret_10d"]).groupby("mcap"):
    r = g["ret_10d"]
    if len(r) < 3:
        continue
    print(f"  {mc:>10}: n={len(r):>3}, mean={r.mean():>6.2f}%, "
          f"win={(r>0).mean()*100:>4.0f}%, med={r.median():>6.2f}%")

print("\nBy Day of Week (signal day):")
df_t["dow"] = pd.to_datetime(df_t["signal_date"]).dt.dayofweek
dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
for dow, g in df_t.dropna(subset=["ret_10d"]).groupby("dow"):
    r = g["ret_10d"]
    print(f"  {dow_names[int(dow)]}: n={len(r):>3}, mean={r.mean():>6.2f}%, win={(r>0).mean()*100:>4.0f}%")

print("\nBy Month:")
df_t["month"] = pd.to_datetime(df_t["signal_date"]).dt.to_period("M")
for m, g in df_t.dropna(subset=["ret_10d"]).groupby("month"):
    r = g["ret_10d"]
    print(f"  {m}: n={len(r):>3}, mean={r.mean():>6.2f}%, win={(r>0).mean()*100:>4.0f}%")

# =====================================================================
# 12. POSITION SIZING SIMULATION
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 12: POSITION SIZING")
print("=" * 70)

df_sorted = df_t.sort_values("entry_date").reset_index(drop=True)
sort_idx = df_t.sort_values("entry_date").index
fwd_sorted = [fwd_arrays[i] for i in sort_idx]

# Best exit from prior sections: pick SL 7%, trail 7%, max 20d as a reasonable middle ground
BEST_SL = 7; BEST_TRAIL = 7; BEST_MD = 20

# A: Fixed 1L per trade
CAP_PER = 100_000
sim_a = []
for idx in range(len(df_sorted)):
    fc, fh, fl = fwd_sorted[idx]
    ep = df_sorted.iloc[idx]["entry_price"]
    r = sim_trail(fc, fl, ep, BEST_TRAIL, BEST_SL, BEST_MD)
    if r:
        pnl = CAP_PER * r["ret"] / 100
        sim_a.append({"date": df_sorted.iloc[idx]["entry_date"], "pnl": pnl,
                      "ret": r["ret"], "days": r["days"]})

# B: 1Cr portfolio, max 10 positions
CAP_TOTAL = 10_000_000; MAX_POS = 10
sim_b = []
open_pos = []
for idx in range(len(df_sorted)):
    edt = df_sorted.iloc[idx]["entry_date"]
    # Close expired positions
    open_pos = [p for p in open_pos if (edt - p["entry_date"]).days <= BEST_MD]
    if len(open_pos) >= MAX_POS:
        continue
    ep = df_sorted.iloc[idx]["entry_price"]
    alloc = CAP_TOTAL / MAX_POS
    shares = int(alloc / ep)
    if shares <= 0:
        continue
    fc, fh, fl = fwd_sorted[idx]
    r = sim_trail(fc, fl, ep, BEST_TRAIL, BEST_SL, BEST_MD)
    if r:
        pnl = shares * ep * r["ret"] / 100
        sim_b.append({"date": edt, "symbol": df_sorted.iloc[idx]["symbol"],
                      "pnl": pnl, "ret": r["ret"], "days": r["days"]})
        open_pos.append({"entry_date": edt, "days": r["days"]})

# C: 1L per trade, simple buy-hold 10d
sim_c = []
for idx in range(len(df_sorted)):
    ret = df_sorted.iloc[idx].get("ret_10d")
    if pd.notna(ret):
        sim_c.append({"date": df_sorted.iloc[idx]["entry_date"],
                      "pnl": CAP_PER * ret / 100, "ret": ret})

for label, sim_data in [("A) 1L/trade, SL7% trail7% 20d", sim_a),
                         ("B) 1Cr portfolio, max10, SL7% trail7% 20d", sim_b),
                         ("C) 1L/trade, buy-hold 10d", sim_c)]:
    if not sim_data:
        continue
    sd = pd.DataFrame(sim_data)
    cum = sd["pnl"].cumsum()
    peak = cum.cummax(); dd = cum - peak
    rets = sd["ret"].values
    n_yr = len(sd) / max(1, (sd["date"].max() - sd["date"].min()).days / 365.25)
    print(f"\n{label}:")
    print(f"  Trades: {len(sd)}, Win%: {(rets > 0).mean()*100:.1f}%")
    print(f"  Total P&L: Rs.{cum.iloc[-1]:,.0f}, Avg/trade: Rs.{sd['pnl'].mean():,.0f}")
    print(f"  Mean ret/trade: {rets.mean():.2f}%, PF: "
          f"{rets[rets>0].sum()/abs(rets[rets<0].sum()):.2f}" if (rets < 0).any() else "inf")
    print(f"  Max DD: Rs.{dd.min():,.0f}")
    if "days" in sd.columns:
        print(f"  Avg hold: {sd['days'].mean():.1f}d")

# =====================================================================
# 13. FILTER SEARCH
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 13: COMBINED FILTER SEARCH")
print("=" * 70)

filter_results = []
def test_filter(name, mask, horizon="ret_10d"):
    sub = df_t[mask & df_t[horizon].notna()][horizon]
    if len(sub) < 5:
        return
    filter_results.append({"filter": name, "n": len(sub),
                           "mean%": round(sub.mean(), 2),
                           "win%": round((sub > 0).mean() * 100, 1),
                           "median%": round(sub.median(), 2)})

test_filter("BASELINE", pd.Series(True, index=df_t.index))
test_filter("vol > 2.5x", df_t["vol_ratio"] > 2.5)
test_filter("vol > 3x", df_t["vol_ratio"] > 3)
test_filter("chg 3-7%", (df_t["daily_chg_pct"] >= 3) & (df_t["daily_chg_pct"] <= 7))
test_filter("chg > 5%", df_t["daily_chg_pct"] > 5)
test_filter("close_in_range > 0.9", df_t["close_in_range"] > 0.9)
test_filter("wick < 0.3%", df_t["upper_wick_pct"] < 0.3)
test_filter("rsi 60-75", (df_t["rsi14"] >= 60) & (df_t["rsi14"] <= 75))
test_filter("turnover > 10cr", df_t["turnover_cr"] > 10)
test_filter("Largecap", df_t["mcap"] == "Largecap")
test_filter("Midcap", df_t["mcap"] == "Midcap")
test_filter("above_20dma", df_t["above_20dma"] == True)
test_filter("nifty > 20dma", df_t["nifty_above_20dma"] == True)
test_filter("new_high", df_t["new_hi"] == 1)
test_filter("RS rank > 80", df_t["rs_rank"] > 80)
test_filter("sales_yoy > 15%", df_t["q1_sales_yoy_pct"] > 15)
test_filter("profit_pos_2q", df_t["profit_positive_2q"] == 1)
test_filter("CANSLIM >= 3", df_t["canslim"] >= 3)
test_filter("CANSLIM >= 4", df_t["canslim"] >= 4)
test_filter("vcp < 0.6", df_t["vcp_score"] < 0.6)
test_filter("gap < 1%", df_t["gap_pct"] < 1)
# Combos
test_filter("vol>2.5 & chg 3-7% & wick<0.5",
            (df_t["vol_ratio"] > 2.5) & (df_t["daily_chg_pct"].between(3, 7)) & (df_t["upper_wick_pct"] < 0.5))
test_filter("Largecap & vol>2.5",
            (df_t["mcap"] == "Largecap") & (df_t["vol_ratio"] > 2.5))
test_filter("new_hi & RS>80",
            (df_t["new_hi"] == 1) & (df_t["rs_rank"] > 80))
test_filter("sales>15% & vol>2.5",
            (df_t["q1_sales_yoy_pct"] > 15) & (df_t["vol_ratio"] > 2.5))
test_filter("CANSLIM>=3 & vol>2.5",
            (df_t["canslim"] >= 3) & (df_t["vol_ratio"] > 2.5))
test_filter("nifty_bull & chg 3-7% & gap<1%",
            (df_t["nifty_above_20dma"] == True) & (df_t["daily_chg_pct"].between(3, 7)) & (df_t["gap_pct"] < 1))
test_filter("BEST: new_hi & RS>80 & vol>2x & nifty_bull",
            (df_t["new_hi"] == 1) & (df_t["rs_rank"] > 80) & (df_t["vol_ratio"] > 2) &
            (df_t["nifty_above_20dma"] == True))
test_filter("BEST2: CANSLIM>=3 & wick<0.5 & chg<8%",
            (df_t["canslim"] >= 3) & (df_t["upper_wick_pct"] < 0.5) & (df_t["daily_chg_pct"] < 8))

filt_df = pd.DataFrame(filter_results).sort_values("mean%", ascending=False)
print(filt_df.to_string(index=False))
filt_df.to_csv(OUT / "filter_search.csv", index=False)

# =====================================================================
# 14. CHARTS
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 14: CHARTS")
print("=" * 70)

# Chart 1: Forward return distributions
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
for i, h in enumerate([1, 3, 5, 10, 20, 30]):
    ax = axes[i // 3][i % 3]
    v = df_t[f"ret_{h}d"].dropna()
    if len(v) > 0:
        color = '#26a69a' if v.mean() > 0 else '#ef5350'
        ax.hist(v, bins=30, color=color, alpha=0.7, edgecolor='white')
        ax.axvline(0, color='#787b86', ls='--', lw=1)
        ax.axvline(v.mean(), color='#2962ff', lw=1.5, label=f'mean={v.mean():.1f}%')
        ax.set_title(f'{h}d (n={len(v)}, win={((v>0).mean()*100):.0f}%)')
        ax.set_xlabel('Return %'); ax.legend(fontsize=8)
plt.suptitle('Chartlink Breakout: Forward Return Distributions', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(OUT / "fwd_return_dist.png", dpi=110, bbox_inches='tight')
print("  fwd_return_dist.png saved")

# Chart 2: MAE vs MFE scatter
fig, ax = plt.subplots(figsize=(10, 8))
mae = df_t["mae_10d"].dropna(); mfe = df_t["mfe_10d"].dropna()
ci = mae.index.intersection(mfe.index)
if len(ci) > 5:
    winners = df_t.loc[ci, "ret_10d"] > 0
    ax.scatter(mae[ci][winners], mfe[ci][winners], alpha=0.5, c='#26a69a', s=30, label='Winners')
    ax.scatter(mae[ci][~winners], mfe[ci][~winners], alpha=0.5, c='#ef5350', s=30, label='Losers')
    for sl in [3, 5, 7, 10]:
        ax.axvline(-sl, color='#ff9800', ls=':', alpha=0.6)
        ax.text(-sl - 0.3, mfe[ci].max() * 0.95, f'SL {sl}%', fontsize=7, color='#ff9800')
    ax.set_xlabel('MAE % (max drawdown from entry)'); ax.set_ylabel('MFE % (max gain from entry)')
    ax.set_title(f'MAE vs MFE, 10d horizon (n={len(ci)})'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "mae_mfe_10d.png", dpi=110)
print("  mae_mfe_10d.png saved")

# Chart 3: Equity curves
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [3, 1]})
curves = []
if sim_a:
    eq = np.concatenate(([0], np.cumsum([r["pnl"] for r in sim_a])))
    curves.append(("SL7%+Trail7%+20d", eq, '#26a69a'))
if sim_c:
    eq = np.concatenate(([0], np.cumsum([r["pnl"] for r in sim_c])))
    curves.append(("Buy-hold 10d", eq, '#787b86'))

for label, eq, color in curves:
    ax1.plot(eq, label=f'{label}: Rs.{eq[-1]:,.0f}', color=color, lw=1.5)
    pk = np.maximum.accumulate(eq); dd = eq - pk
    ax2.fill_between(range(len(dd)), dd, 0, color=color, alpha=0.2)

ax1.axhline(0, color='#787b86', ls='--', lw=0.5)
ax1.set_ylabel('Cumulative P&L (Rs.)')
ax1.set_title('Breakout Scanner: Rs.1L per trade equity curves')
ax1.legend(fontsize=9); ax1.grid(alpha=0.3)
ax2.set_ylabel('DD (Rs.)'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "equity_curves.png", dpi=110)
print("  equity_curves.png saved")

# Chart 4: SL optimization heatmap
if len(sl_df) > 0:
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot = sl_df.pivot_table(values="mean%", index="SL%", columns="max_d")
    im = ax.imshow(pivot.values, aspect='auto', cmap='RdYlGn')
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels(pivot.index)
    ax.set_xlabel('Max Hold Days'); ax.set_ylabel('SL %')
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            ax.text(j, i, f'{pivot.values[i,j]:.1f}', ha='center', va='center', fontsize=9)
    ax.set_title('Mean Return % by SL and Max Hold Period')
    plt.colorbar(im); plt.tight_layout()
    plt.savefig(OUT / "sl_heatmap.png", dpi=110)
    print("  sl_heatmap.png saved")

# Chart 5: Sector breakdown bar
if len(sec_df) > 0:
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['#26a69a' if x > 0 else '#ef5350' for x in sec_df["mean%"]]
    ax.barh(sec_df["sector"], sec_df["mean%"], color=colors)
    for i, row in sec_df.iterrows():
        ax.text(row["mean%"] + 0.1, i, f'n={row["n"]}, win={row["win%"]:.0f}%', va='center', fontsize=8)
    ax.axvline(0, color='#787b86', ls='--'); ax.set_xlabel('Mean 10d Return %')
    ax.set_title('10d Forward Return by Sector'); ax.grid(alpha=0.3, axis='x')
    plt.tight_layout(); plt.savefig(OUT / "sector_breakdown.png", dpi=110)
    print("  sector_breakdown.png saved")

# =====================================================================
# FINAL SUMMARY
# =====================================================================
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
v10 = df_t["ret_10d"].dropna()
print(f"Total signals analyzed: {len(df_t)}")
print(f"10d base: mean={v10.mean():.2f}%, win={(v10>0).mean()*100:.0f}%, median={v10.median():.2f}%")
print(f"Best SL grid: see sl_optimization.csv")
print(f"Best trailing: see trailing_optimization.csv")
print(f"Best filters: see filter_search.csv")
print(f"All outputs in: {OUT}")
print(f"Runtime: {time.time()-t0:.0f}s")
