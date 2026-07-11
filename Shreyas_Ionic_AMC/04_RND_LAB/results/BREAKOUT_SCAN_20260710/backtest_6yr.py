"""
6-Year Backtest: Chartlink VCP/Minervini Breakout Scanner
=========================================================
Replicate the scanner logic on all available daily OHLCV data from Jan 2020.
Test top 3 configs: SL15%/30d, SL10%/30d, SL15%/20d.
Also test with the best filter (Exclude bottom 5 sectors).

Data sources stitched:
  1. nifty_stock_daily/1_bhavcopy.csv (Jan-Jul 2020, full OHLCV, all NSE)
  2. stocks_data_cache.pkl -> price (Jun 2020 - Jan 2026, 435 symbols OHLCV)
  3. angel_daily_n500_2026.parquet (Feb-Jul 2026, 500 symbols OHLCV)
"""
import os, sys, warnings, pickle, math
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.optimize import brentq

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"

# =====================================================================
# 1. LOAD AND STITCH ALL DATA SOURCES
# =====================================================================
print("=" * 70)
print("STEP 1: Loading and stitching data sources")
print("=" * 70)

frames = []

# Source A: bhavcopy 2020 (Jan-Jul 2020 with full OHLCV)
print("  Loading bhavcopy 2020...")
bhav = pd.read_csv(os.path.join(BASE, "nifty_stock_daily", "1_bhavcopy.csv"),
                   parse_dates=["date"])
bhav = bhav.rename(columns={"turnover_lacs": "turnover_lacs_raw"})
bhav["turnover_cr"] = bhav["turnover_lacs_raw"] / 100
bhav_clean = bhav[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr"]].copy()
bhav_clean["source"] = "bhavcopy"
frames.append(bhav_clean)
print(f"    bhavcopy: {len(bhav_clean):,} rows, {bhav_clean['symbol'].nunique()} symbols, "
      f"{bhav_clean['date'].min().date()} -> {bhav_clean['date'].max().date()}")

# Source B: stocks_data_cache.pkl (Jun 2020 - Jan 2026)
print("  Loading stocks_data_cache.pkl...")
with open(os.path.join(os.path.dirname(BASE), "stocks_data_cache.pkl"), "rb") as fh:
    cache = pickle.load(fh)
price_wide = cache["price"]
sectors = cache.get("sectors", {})

# Melt MultiIndex to long format
cache_rows = []
symbols_in_cache = set()
for col_pair in price_wide.columns:
    sym_ns, field = col_pair  # e.g., ('HAL.NS', 'Open')
    sym = sym_ns.replace(".NS", "")
    symbols_in_cache.add(sym)

# More efficient: pivot by symbol
syms_done = set()
for sym_ns in sorted(set(c[0] for c in price_wide.columns)):
    sym = sym_ns.replace(".NS", "")
    if sym in syms_done:
        continue
    syms_done.add(sym)
    try:
        sub = price_wide[sym_ns].copy()
        sub = sub.dropna(subset=["Close"])
        if len(sub) < 30:
            continue
        sub = sub.reset_index()
        sub.columns = ["date", "open", "high", "low", "close", "volume"]
        sub["symbol"] = sym
        sub["turnover_cr"] = sub["close"] * sub["volume"] / 1e7  # approx
        sub["source"] = "cache"
        sub["date"] = pd.to_datetime(sub["date"])
        cache_rows.append(sub[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr", "source"]])
    except Exception:
        pass

cache_df = pd.concat(cache_rows, ignore_index=True)
print(f"    cache: {len(cache_df):,} rows, {cache_df['symbol'].nunique()} symbols, "
      f"{cache_df['date'].min().date()} -> {cache_df['date'].max().date()}")
frames.append(cache_df)

# Source C: angel daily 2026 (Feb-Jul 2026)
print("  Loading angel_daily_n500_2026.parquet...")
ang = pd.read_parquet(os.path.join(BASE, "angel_daily_n500_2026.parquet"))
ang_col = "timestamp" if "timestamp" in ang.columns else "date"
ang["date"] = pd.to_datetime(ang[ang_col]).dt.tz_localize(None)
ang["turnover_cr"] = ang["close"] * ang["volume"] / 1e7
ang["source"] = "angel"
ang_clean = ang[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr", "source"]].copy()
frames.append(ang_clean)
print(f"    angel: {len(ang_clean):,} rows, {ang_clean['symbol'].nunique()} symbols, "
      f"{ang_clean['date'].min().date()} -> {ang_clean['date'].max().date()}")

# Combine all, deduplicate (prefer cache > angel > bhavcopy for overlapping dates)
print("  Stitching and deduplicating...")
all_data = pd.concat(frames, ignore_index=True)
# Priority: angel > cache > bhavcopy
source_priority = {"angel": 0, "cache": 1, "bhavcopy": 2}
all_data["priority"] = all_data["source"].map(source_priority)
all_data = all_data.sort_values(["symbol", "date", "priority"])
all_data = all_data.drop_duplicates(subset=["symbol", "date"], keep="first")
all_data = all_data.drop(columns=["priority"])
all_data = all_data.sort_values(["symbol", "date"]).reset_index(drop=True)

# Filter valid data
all_data = all_data[(all_data["close"] > 0) & (all_data["volume"] > 0)]
all_data = all_data[all_data["date"] >= "2020-01-01"]

print(f"\n  FINAL DATASET:")
print(f"    Rows: {len(all_data):,}")
print(f"    Symbols: {all_data['symbol'].nunique()}")
print(f"    Date range: {all_data['date'].min().date()} -> {all_data['date'].max().date()}")
print(f"    Trading days: {all_data['date'].nunique()}")

# Year distribution
for yr, g in all_data.groupby(all_data["date"].dt.year):
    print(f"    {yr}: {len(g):,} rows, {g['symbol'].nunique()} symbols, {g['date'].nunique()} dates")

# =====================================================================
# 2. LOAD NIFTY 50 INDEX FOR REGIME FILTER
# =====================================================================
print("\n" + "=" * 70)
print("STEP 2: Loading NIFTY 50 index for regime filter")
print("=" * 70)

nifty_path = os.path.join(BASE, "index_daily", "nifty50.parquet")
if os.path.exists(nifty_path):
    nifty = pd.read_parquet(nifty_path)
    tcol = "timestamp" if "timestamp" in nifty.columns else "date"
    nifty["date"] = pd.to_datetime(nifty[tcol])
    if nifty["date"].dt.tz is not None:
        nifty["date"] = nifty["date"].dt.tz_localize(None)
    nifty = nifty.sort_values("date")
    nifty["nifty_20dma"] = nifty["close"].rolling(20).mean()
    nifty["nifty_above_20dma"] = nifty["close"] > nifty["nifty_20dma"]
    nifty_regime = nifty[["date", "nifty_above_20dma"]].copy()
    print(f"  NIFTY 50: {len(nifty)} rows, {nifty['date'].min().date()} -> {nifty['date'].max().date()}")
else:
    print("  WARNING: nifty50.parquet not found, will skip regime filter")
    nifty_regime = None

# =====================================================================
# 3. BUILD SECTOR MAP
# =====================================================================
print("\n" + "=" * 70)
print("STEP 3: Building sector map")
print("=" * 70)

sector_map = {}
for sym, sec in sectors.items():
    clean_sym = sym.replace(".NS", "") if ".NS" in sym else sym
    if isinstance(sec, str):
        sector_map[clean_sym] = sec
    elif isinstance(sec, dict) and "sector" in sec:
        sector_map[clean_sym] = sec["sector"]

# Also try to load from bhavcopy meta
meta_path = os.path.join(BASE, "nifty_stock_daily", "1_meta.csv")
if os.path.exists(meta_path):
    meta = pd.read_csv(meta_path)
    if "industry" in [c.lower() for c in meta.columns]:
        ind_col = [c for c in meta.columns if c.lower() == "industry"][0]
        sym_col = [c for c in meta.columns if c.lower() == "symbol"][0]
        for _, row in meta.iterrows():
            if row[sym_col] not in sector_map and pd.notna(row[ind_col]):
                sector_map[row[sym_col]] = row[ind_col]

print(f"  Sector map: {len(sector_map)} symbols mapped")

# Bottom 5 sectors to exclude (from our analysis)
BAD_SECTORS = {"Bank", "Financials", "Energy", "Building Materials", "Textiles",
               "Financial Services", "Banking", "Oil & Gas"}

# =====================================================================
# 4. GENERATE SCANNER SIGNALS
# =====================================================================
print("\n" + "=" * 70)
print("STEP 4: Generating VCP breakout signals (replicating Chartlink scanner)")
print("=" * 70)

signals = []
symbol_groups = all_data.groupby("symbol")
total_syms = len(symbol_groups)

for i, (sym, df_sym) in enumerate(symbol_groups):
    if (i + 1) % 200 == 0:
        print(f"  Processing {i+1}/{total_syms} symbols... ({len(signals)} signals so far)")

    df_sym = df_sym.sort_values("date").reset_index(drop=True)
    if len(df_sym) < 30:
        continue

    # Compute indicators
    df_sym["sma20"] = df_sym["close"].rolling(20).mean()
    df_sym["std20"] = df_sym["close"].rolling(20).std()
    df_sym["upper_bb"] = df_sym["sma20"] + 2 * df_sym["std20"]
    df_sym["vol_avg20"] = df_sym["volume"].rolling(20).mean()
    df_sym["high5"] = df_sym["high"].rolling(5).max()

    # RSI(14)
    delta = df_sym["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df_sym["rsi14"] = 100 - (100 / (1 + rs))

    # Previous day range ratio (compression check)
    df_sym["prev_range"] = (df_sym["high"].shift(1) - df_sym["low"].shift(1)) / df_sym["close"].shift(1)
    df_sym["avg_range_10"] = df_sym["prev_range"].rolling(10).mean()

    # Daily change
    df_sym["daily_chg"] = (df_sym["close"] - df_sym["close"].shift(1)) / df_sym["close"].shift(1) * 100

    for j in range(25, len(df_sym)):
        row = df_sym.iloc[j]

        # Skip if NaN
        if pd.isna(row["rsi14"]) or pd.isna(row["vol_avg20"]) or pd.isna(row["upper_bb"]):
            continue

        # SCANNER CRITERIA:
        # 1. Turnover > 25cr (liquidity gate)
        if row["turnover_cr"] < 25:
            continue

        # 2. Close > 5-day high * 1.01 (breakout)
        prev_high5 = df_sym.iloc[j-1]["high5"] if j > 0 else np.nan
        if pd.isna(prev_high5) or row["close"] <= prev_high5 * 1.01:
            continue

        # 3. RSI(14) > 60
        if row["rsi14"] <= 60:
            continue

        # 4. Volume > 2x 20-day average
        if row["vol_avg20"] <= 0 or row["volume"] <= 2 * row["vol_avg20"]:
            continue

        # 5. Upper Bollinger Band breakout
        if row["close"] <= row["upper_bb"]:
            continue

        # 6. Range compression: prior day not extended (range < 1.5x avg range)
        if pd.notna(row["prev_range"]) and pd.notna(row["avg_range_10"]):
            if row["prev_range"] > 1.5 * row["avg_range_10"]:
                continue
        else:
            continue

        # 7. Daily change > 3% (meaningful breakout)
        if row["daily_chg"] < 3:
            continue

        # Signal passes! Record it.
        vol_ratio = row["volume"] / row["vol_avg20"] if row["vol_avg20"] > 0 else 0
        gap_pct = (row["open"] - df_sym.iloc[j-1]["close"]) / df_sym.iloc[j-1]["close"] * 100 if j > 0 else 0

        signals.append({
            "signal_date": row["date"],
            "symbol": sym,
            "close": row["close"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "volume": row["volume"],
            "turnover_cr": row["turnover_cr"],
            "rsi14": row["rsi14"],
            "vol_ratio": vol_ratio,
            "daily_chg_pct": row["daily_chg"],
            "gap_pct": gap_pct,
            "sector": sector_map.get(sym, "Unknown"),
        })

print(f"\n  TOTAL SIGNALS GENERATED: {len(signals)}")
sig_df = pd.DataFrame(signals)
sig_df = sig_df.sort_values("signal_date").reset_index(drop=True)
print(f"  Date range: {sig_df['signal_date'].min().date()} -> {sig_df['signal_date'].max().date()}")

# Year distribution
for yr, g in sig_df.groupby(sig_df["signal_date"].dt.year):
    print(f"    {yr}: {len(g)} signals, {g['symbol'].nunique()} symbols")

# =====================================================================
# 5. COMPUTE FORWARD RETURNS FOR EACH SIGNAL
# =====================================================================
print("\n" + "=" * 70)
print("STEP 5: Computing forward returns (entry = next-day open)")
print("=" * 70)

# Pre-index data for fast lookup
sym_data = {}
for sym, g in all_data.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_data[sym] = g

trades = []
skipped = 0

for idx, sig in sig_df.iterrows():
    sym = sig["symbol"]
    sig_date = sig["signal_date"]

    if sym not in sym_data:
        skipped += 1
        continue

    df_s = sym_data[sym]
    # Find signal date index
    loc = df_s[df_s["date"] == sig_date].index
    if len(loc) == 0:
        skipped += 1
        continue
    loc_i = loc[0]

    # Entry = next trading day open
    if loc_i + 1 >= len(df_s):
        skipped += 1
        continue
    entry_row = df_s.iloc[loc_i + 1]
    entry_price = entry_row["open"]
    entry_date = entry_row["date"]

    if entry_price <= 0 or pd.isna(entry_price):
        skipped += 1
        continue

    trade = {
        "signal_date": sig_date,
        "entry_date": entry_date,
        "symbol": sym,
        "entry_price": entry_price,
        "signal_close": sig["close"],
        "rsi14": sig["rsi14"],
        "vol_ratio": sig["vol_ratio"],
        "daily_chg_pct": sig["daily_chg_pct"],
        "gap_pct": sig["gap_pct"],
        "turnover_cr": sig["turnover_cr"],
        "sector": sig["sector"],
    }

    # Forward returns at multiple horizons
    for days, label in [(5, "5d"), (10, "10d"), (15, "15d"), (20, "20d"), (30, "30d"), (40, "40d")]:
        if loc_i + 1 + days < len(df_s):
            future = df_s.iloc[loc_i + 2 : loc_i + 1 + days + 1]  # days after entry
            if len(future) > 0:
                exit_price = future.iloc[-1]["close"]
                ret = (exit_price - entry_price) / entry_price * 100

                # MAE (max adverse excursion)
                min_low = future["low"].min()
                mae = (min_low - entry_price) / entry_price * 100

                # MFE (max favorable excursion)
                max_high = future["high"].max()
                mfe = (max_high - entry_price) / entry_price * 100

                trade[f"ret_{label}"] = ret
                trade[f"mae_{label}"] = mae
                trade[f"mfe_{label}"] = mfe
            else:
                trade[f"ret_{label}"] = np.nan
                trade[f"mae_{label}"] = np.nan
                trade[f"mfe_{label}"] = np.nan
        else:
            trade[f"ret_{label}"] = np.nan
            trade[f"mae_{label}"] = np.nan
            trade[f"mfe_{label}"] = np.nan

    trades.append(trade)

    if (idx + 1) % 500 == 0:
        print(f"  Processed {idx+1}/{len(sig_df)} signals...")

trade_df = pd.DataFrame(trades)
trade_df = trade_df.sort_values("entry_date").reset_index(drop=True)

# Add regime filter
if nifty_regime is not None:
    trade_df = trade_df.merge(nifty_regime, left_on="signal_date", right_on="date", how="left")
    trade_df = trade_df.drop(columns=["date"], errors="ignore")
    trade_df["nifty_above_20dma"] = trade_df["nifty_above_20dma"].fillna(True)
else:
    trade_df["nifty_above_20dma"] = True

print(f"\n  TRADES COMPUTED: {len(trade_df)} (skipped {skipped})")
print(f"  Date range: {trade_df['entry_date'].min().date()} -> {trade_df['entry_date'].max().date()}")

# Save trades
trade_df.to_csv(os.path.join(OUT, "backtest_6yr_trades.csv"), index=False)
print(f"  Saved to backtest_6yr_trades.csv")

# =====================================================================
# 6. SIMULATE TOP 3 CONFIGS
# =====================================================================
print("\n" + "=" * 70)
print("STEP 6: Simulating top 3 configs")
print("=" * 70)

def sim_sl(ret, mae, sl_pct):
    if pd.isna(ret) or pd.isna(mae):
        return np.nan
    if mae <= -sl_pct:
        return -sl_pct
    return ret

def compute_yearly_stats(df, ret_col, mae_col, sl_pct, label):
    """Compute per-year and overall stats."""
    t = df.copy()
    t["trade_ret"] = t.apply(lambda r: sim_sl(r[ret_col], r[mae_col], sl_pct), axis=1)
    t = t.dropna(subset=["trade_ret"])

    if len(t) == 0:
        return None

    t["pnl_1L"] = t["trade_ret"] / 100 * 100000
    t["cum_pnl"] = t["pnl_1L"].cumsum()

    # Overall stats
    wins = t[t["pnl_1L"] > 0]
    losses = t[t["pnl_1L"] <= 0]
    total_win = wins["pnl_1L"].sum() if len(wins) > 0 else 0
    total_loss = abs(losses["pnl_1L"].sum()) if len(losses) > 0 else 1
    pf = total_win / total_loss if total_loss > 0 else 99

    peak = t["cum_pnl"].cummax()
    dd = t["cum_pnl"] - peak
    max_dd = dd.min()

    # Sharpe
    mean_r = t["trade_ret"].mean()
    std_r = t["trade_ret"].std()
    days = (t["entry_date"].max() - t["entry_date"].min()).days
    tpy = len(t) / max(days / 365.25, 0.01)
    sharpe = (mean_r / std_r * np.sqrt(tpy)) if std_r > 0 else 0

    # CAGR
    total_invested = 100000 * 10  # assume 10L base
    cagr = ((total_invested + t["cum_pnl"].iloc[-1]) / total_invested) ** (365.25 / max(days, 1)) - 1 if days > 0 else 0

    overall = {
        "label": label,
        "n": len(t),
        "win_pct": round(len(wins) / len(t) * 100, 1),
        "mean_ret": round(mean_r, 2),
        "median_ret": round(t["trade_ret"].median(), 2),
        "total_pnl": round(t["cum_pnl"].iloc[-1]),
        "pf": round(pf, 2),
        "max_dd": round(max_dd),
        "sharpe": round(sharpe, 2),
        "cagr_pct": round(cagr * 100, 1),
        "avg_win": round(wins["trade_ret"].mean(), 2) if len(wins) > 0 else 0,
        "avg_loss": round(losses["trade_ret"].mean(), 2) if len(losses) > 0 else 0,
    }

    # Per-year stats
    t["year"] = t["entry_date"].dt.year
    yearly = []
    for yr, yg in t.groupby("year"):
        yw = yg[yg["pnl_1L"] > 0]
        yl = yg[yg["pnl_1L"] <= 0]
        tw = yw["pnl_1L"].sum() if len(yw) > 0 else 0
        tl = abs(yl["pnl_1L"].sum()) if len(yl) > 0 else 1
        ypeak = yg["pnl_1L"].cumsum().cummax()
        ydd = (yg["pnl_1L"].cumsum() - ypeak).min()
        yearly.append({
            "year": yr,
            "n": len(yg),
            "win_pct": round(len(yw) / len(yg) * 100, 1) if len(yg) > 0 else 0,
            "mean_ret": round(yg["trade_ret"].mean(), 2),
            "total_pnl": round(yg["pnl_1L"].sum()),
            "pf": round(tw / tl, 2) if tl > 0 else 99,
            "max_dd": round(ydd),
        })

    return overall, yearly, t[["entry_date", "cum_pnl", "trade_ret", "pnl_1L", "symbol", "sector"]].copy()

# Top 3 configs
configs = [
    ("SL15% 30d (Rank 1)", "ret_30d", "mae_30d", 15),
    ("SL10% 30d (Rank 2)", "ret_30d", "mae_30d", 10),
    ("SL15% 20d (Rank 3)", "ret_20d", "mae_20d", 15),
]

all_results = {}
for label, ret_col, mae_col, sl_pct in configs:
    # Unfiltered
    result = compute_yearly_stats(trade_df, ret_col, mae_col, sl_pct, f"ALL: {label}")
    if result:
        overall, yearly, curve = result
        all_results[f"ALL: {label}"] = (overall, yearly, curve)
        print(f"\n  {overall['label']}")
        print(f"    Overall: n={overall['n']}, win={overall['win_pct']}%, mean={overall['mean_ret']}%, "
              f"PF={overall['pf']}, PnL=Rs.{overall['total_pnl']:,}, MaxDD=Rs.{overall['max_dd']:,}, "
              f"Sharpe={overall['sharpe']}, CAGR={overall['cagr_pct']}%")
        for y in yearly:
            print(f"    {y['year']}: n={y['n']:>4}, win={y['win_pct']:>5.1f}%, "
                  f"mean={y['mean_ret']:>6.2f}%, PnL=Rs.{y['total_pnl']:>10,}, PF={y['pf']:>5.2f}, MaxDD=Rs.{y['max_dd']:>8,}")

    # Filtered: exclude bad sectors
    filt = trade_df[~trade_df["sector"].isin(BAD_SECTORS)]
    result_f = compute_yearly_stats(filt, ret_col, mae_col, sl_pct, f"FILT: {label}")
    if result_f:
        overall_f, yearly_f, curve_f = result_f
        all_results[f"FILT: {label}"] = (overall_f, yearly_f, curve_f)
        print(f"\n  {overall_f['label']}")
        print(f"    Overall: n={overall_f['n']}, win={overall_f['win_pct']}%, mean={overall_f['mean_ret']}%, "
              f"PF={overall_f['pf']}, PnL=Rs.{overall_f['total_pnl']:,}, MaxDD=Rs.{overall_f['max_dd']:,}, "
              f"Sharpe={overall_f['sharpe']}, CAGR={overall_f['cagr_pct']}%")
        for y in yearly_f:
            print(f"    {y['year']}: n={y['n']:>4}, win={y['win_pct']:>5.1f}%, "
                  f"mean={y['mean_ret']:>6.2f}%, PnL=Rs.{y['total_pnl']:>10,}, PF={y['pf']:>5.2f}, MaxDD=Rs.{y['max_dd']:>8,}")

    # Nifty bull only
    bull = trade_df[trade_df["nifty_above_20dma"] == True]
    result_b = compute_yearly_stats(bull, ret_col, mae_col, sl_pct, f"BULL: {label}")
    if result_b:
        overall_b, yearly_b, curve_b = result_b
        all_results[f"BULL: {label}"] = (overall_b, yearly_b, curve_b)
        print(f"\n  {overall_b['label']}")
        print(f"    Overall: n={overall_b['n']}, win={overall_b['win_pct']}%, mean={overall_b['mean_ret']}%, "
              f"PF={overall_b['pf']}, PnL=Rs.{overall_b['total_pnl']:,}, MaxDD=Rs.{overall_b['max_dd']:,}")

# =====================================================================
# 7. PORTFOLIO SIMULATION (1Cr, 7.5% per trade)
# =====================================================================
print("\n" + "=" * 70)
print("STEP 7: Portfolio simulation (Rs.1Cr, 7.5% per trade)")
print("=" * 70)

def simulate_portfolio(trades, initial_capital, pct_per_trade, sl_pct, hold_days, ret_col, mae_col, label=""):
    t = trades.sort_values("entry_date").copy()
    t["trade_ret_pct"] = t.apply(lambda r: sim_sl(r[ret_col], r[mae_col], sl_pct), axis=1)
    t = t.dropna(subset=["trade_ret_pct"]).reset_index(drop=True)

    capital = initial_capital
    position_size = initial_capital * pct_per_trade / 100
    max_positions = int(100 / pct_per_trade)

    open_positions = []
    nav_history = []
    trades_taken = 0
    trades_skipped = 0

    for _, row in t.iterrows():
        entry_d = row["entry_date"]
        exit_d = entry_d + pd.Timedelta(days=hold_days)

        closed = [p for p in open_positions if p[1] <= entry_d]
        for p in closed:
            capital += p[2] + position_size
        open_positions = [p for p in open_positions if p[1] > entry_d]

        if len(open_positions) >= max_positions or capital < position_size:
            trades_skipped += 1
            continue

        pnl = row["trade_ret_pct"] / 100 * position_size
        capital -= position_size
        open_positions.append((entry_d, exit_d, pnl))
        trades_taken += 1

        nav = capital + sum(position_size + p[2] for p in open_positions)
        nav_history.append({"date": entry_d, "nav": nav, "year": entry_d.year})

    for p in open_positions:
        capital += p[2] + position_size

    total_pnl = capital - initial_capital
    nav_df = pd.DataFrame(nav_history)

    if len(nav_df) == 0:
        return None

    peak = nav_df["nav"].cummax()
    dd = nav_df["nav"] - peak
    max_dd_pct = (dd.min() / peak[dd.idxmin()] * 100) if dd.min() < 0 else 0

    days_span = (nav_df["date"].max() - nav_df["date"].min()).days
    cagr = ((initial_capital + total_pnl) / initial_capital) ** (365.25 / max(days_span, 1)) - 1 if days_span > 0 else 0

    print(f"  {label}")
    print(f"    Trades: {trades_taken} taken, {trades_skipped} skipped")
    print(f"    Total PnL: Rs.{total_pnl:,.0f} ({total_pnl/initial_capital*100:.1f}%)")
    print(f"    MaxDD: {max_dd_pct:.1f}%, CAGR: {cagr*100:.1f}%")

    # Yearly breakdown
    for yr, yg in nav_df.groupby("year"):
        yr_pnl = yg["nav"].iloc[-1] - (yg["nav"].iloc[0] if len(yg) > 0 else initial_capital)
        print(f"    {yr}: {len(yg)} trades in this year")

    return {"label": label, "total_pnl": total_pnl, "ret_pct": total_pnl/initial_capital*100,
            "max_dd_pct": max_dd_pct, "cagr": cagr*100, "n_trades": trades_taken,
            "nav_series": nav_df}

port_results = []
for label, ret_col, mae_col, sl_pct in configs:
    # ALL signals
    r = simulate_portfolio(trade_df, 10000000, 7.5, sl_pct,
                           30 if "30d" in label else 20,
                           ret_col, mae_col, f"Portfolio ALL: {label}")
    if r:
        port_results.append(r)

    # Filtered
    filt = trade_df[~trade_df["sector"].isin(BAD_SECTORS)]
    r_f = simulate_portfolio(filt, 10000000, 7.5, sl_pct,
                             30 if "30d" in label else 20,
                             ret_col, mae_col, f"Portfolio FILT: {label}")
    if r_f:
        port_results.append(r_f)

# =====================================================================
# 8. EQUITY CURVES CHART
# =====================================================================
print("\n" + "=" * 70)
print("STEP 8: Plotting equity curves")
print("=" * 70)

fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={"height_ratios": [3, 1]})
colors = ['#2962ff', '#e91e63', '#ff9800', '#4caf50', '#9c27b0', '#00bcd4',
          '#795548', '#607d8b', '#f44336']

plot_keys = list(all_results.keys())[:6]  # top 6 curves
for i, key in enumerate(plot_keys):
    overall, yearly, curve = all_results[key]
    c = colors[i % len(colors)]
    lbl = f"{key}: Rs.{overall['total_pnl']/1e5:.1f}L, PF={overall['pf']}"
    axes[0].plot(curve["entry_date"], curve["cum_pnl"] / 1e5, label=lbl, color=c, lw=1.5, alpha=0.85)

    # Drawdown for first 3
    if i < 3:
        peak = curve["cum_pnl"].cummax()
        dd = (curve["cum_pnl"] - peak) / 1e5
        axes[1].fill_between(curve["entry_date"], dd, 0, alpha=0.2, color=c, label=key.split(":")[0])

axes[0].axhline(0, color='#787b86', lw=0.5)
axes[0].set_ylabel("Cumulative P&L (Rs. Lakh)", fontsize=12)
axes[0].set_title("6-Year Backtest: Chartlink VCP Breakout Scanner (Jan 2020 - Jul 2026)", fontsize=14)
axes[0].legend(fontsize=8, loc="upper left")
axes[0].grid(alpha=0.3)
axes[1].set_ylabel("Drawdown (Rs. L)")
axes[1].set_xlabel("Date")
axes[1].legend(fontsize=8)
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "backtest_6yr_equity.png"), dpi=120)
print("  -> backtest_6yr_equity.png saved")

# =====================================================================
# 9. MONTHLY P&L HEATMAP DATA
# =====================================================================
print("\n" + "=" * 70)
print("STEP 9: Monthly breakdown (best config: SL10%/30d)")
print("=" * 70)

best_key = "ALL: SL10% 30d (Rank 2)"
if best_key in all_results:
    overall, yearly, curve = all_results[best_key]
    curve["month"] = curve["entry_date"].dt.to_period("M")
    print(f"\n  Monthly P&L for {best_key}:")
    print(f"  {'Month':<10} {'N':>4} {'Win%':>6} {'Mean%':>7} {'P&L(L)':>8}")
    print(f"  {'-'*40}")
    for m, mg in curve.groupby("month"):
        w = (mg["trade_ret"] > 0).mean() * 100
        pnl_l = mg["pnl_1L"].sum() / 1e5
        print(f"  {str(m):<10} {len(mg):>4} {w:>6.1f} {mg['trade_ret'].mean():>7.2f} {pnl_l:>8.2f}")

# =====================================================================
# 10. SECTOR BREAKDOWN
# =====================================================================
print("\n" + "=" * 70)
print("STEP 10: Sector breakdown (SL10%/30d, all signals)")
print("=" * 70)

if best_key in all_results:
    overall, yearly, curve = all_results[best_key]
    print(f"\n  {'Sector':<30} {'N':>4} {'Win%':>6} {'Mean%':>7} {'P&L(L)':>8}")
    print(f"  {'-'*60}")
    for sec, sg in curve.groupby("sector"):
        if len(sg) >= 3:
            w = (sg["trade_ret"] > 0).mean() * 100
            pnl_l = sg["pnl_1L"].sum() / 1e5
            print(f"  {sec:<30} {len(sg):>4} {w:>6.1f} {sg['trade_ret'].mean():>7.2f} {pnl_l:>8.2f}")

# =====================================================================
# SUMMARY
# =====================================================================
print("\n" + "=" * 70)
print("SUMMARY — 6-Year Backtest Results")
print("=" * 70)

print(f"\n{'Config':<40} {'N':>5} {'Win%':>6} {'Mean%':>7} {'PF':>5} {'PnL(L)':>8} {'MaxDD(L)':>9} {'Sharpe':>7} {'CAGR%':>7}")
print("-" * 100)
for key, (overall, yearly, curve) in sorted(all_results.items(), key=lambda x: -x[1][0]["total_pnl"]):
    o = overall
    print(f"{o['label']:<40} {o['n']:>5} {o['win_pct']:>6.1f} {o['mean_ret']:>7.2f} {o['pf']:>5.2f} "
          f"{o['total_pnl']/1e5:>8.1f} {o['max_dd']/1e5:>9.1f} {o['sharpe']:>7.2f} {o['cagr_pct']:>7.1f}")

print(f"\nAll outputs in: {OUT}")
print("Files: backtest_6yr_trades.csv, backtest_6yr_equity.png")
