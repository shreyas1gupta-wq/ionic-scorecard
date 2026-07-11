"""
Comprehensive P&L curves, filter impact analysis, CAGR/XIRR/Sharpe,
and portfolio sizing (1L fixed + 1Cr with 5%/7.5%/10% entry sizes).
"""
import sys, os, warnings, math
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.optimize import brentq

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710")

df = pd.read_csv(OUT / "trades_detail.csv")
df["signal_date"] = pd.to_datetime(df["signal_date"])
df["entry_date"] = pd.to_datetime(df["entry_date"])
df = df.sort_values("entry_date").reset_index(drop=True)
print(f"Loaded {len(df)} trades, {df['entry_date'].min().date()} -> {df['entry_date'].max().date()}")

# =====================================================================
# HELPERS
# =====================================================================

def sim_sl(ret_series, mae_series, sl_pct, hold_days):
    """Simulate SL + time exit. Use MAE to check if SL was hit."""
    if pd.isna(ret_series) or pd.isna(mae_series):
        return np.nan
    if mae_series <= -sl_pct:
        return -sl_pct
    return ret_series

def xirr(cashflows):
    """Compute XIRR from list of (date, amount)."""
    if len(cashflows) < 2:
        return np.nan
    dates = [cf[0] for cf in cashflows]
    amounts = [cf[1] for cf in cashflows]
    d0 = min(dates)
    def npv(r):
        return sum(a / (1 + r) ** ((d - d0).days / 365.25) for d, a in zip(dates, amounts))
    try:
        return brentq(npv, -0.5, 10.0, maxiter=200)
    except:
        return np.nan

def compute_stats(trades_df, capital_per_trade, hold_col="ret_10d", mae_col="mae_10d", sl_pct=10, label=""):
    """Compute comprehensive stats for a trade series."""
    t = trades_df.copy()
    t["trade_ret"] = t.apply(lambda r: sim_sl(r[hold_col], r[mae_col], sl_pct, 10), axis=1)
    t = t.dropna(subset=["trade_ret"])
    if len(t) == 0:
        return None

    t["pnl"] = t["trade_ret"] / 100 * capital_per_trade
    t["cum_pnl"] = t["pnl"].cumsum()

    wins = t[t["pnl"] > 0]
    losses = t[t["pnl"] <= 0]
    total_win = wins["pnl"].sum() if len(wins) > 0 else 0
    total_loss = abs(losses["pnl"].sum()) if len(losses) > 0 else 1

    # Max drawdown
    peak = t["cum_pnl"].cummax()
    dd = t["cum_pnl"] - peak
    max_dd = dd.min()

    # CAGR
    first_date = t["entry_date"].min()
    last_date = t["entry_date"].max()
    days = (last_date - first_date).days
    total_ret = t["cum_pnl"].iloc[-1]
    invested = capital_per_trade  # per trade basis
    # For CAGR: treat as total return on initial capital
    init_cap = capital_per_trade * 10 if capital_per_trade == 100000 else capital_per_trade
    cagr = ((init_cap + total_ret) / init_cap) ** (365.25 / max(days, 1)) - 1 if days > 0 else 0

    # XIRR
    cfs = []
    for _, row in t.iterrows():
        cfs.append((row["entry_date"], -capital_per_trade))
        exit_date = row["entry_date"] + pd.Timedelta(days=10)
        cfs.append((exit_date, capital_per_trade + row["pnl"]))
    xirr_val = xirr(cfs)

    # Sharpe (annualized from per-trade returns)
    mean_r = t["trade_ret"].mean()
    std_r = t["trade_ret"].std()
    trades_per_year = len(t) / max(days / 365.25, 0.01)
    sharpe = (mean_r / std_r * np.sqrt(trades_per_year)) if std_r > 0 else 0

    return {
        "label": label,
        "n": len(t),
        "win_pct": round(len(wins) / len(t) * 100, 1),
        "mean_ret": round(mean_r, 2),
        "median_ret": round(t["trade_ret"].median(), 2),
        "total_pnl": round(total_ret),
        "pf": round(total_win / total_loss, 2) if total_loss > 0 else 99,
        "max_dd": round(max_dd),
        "calmar": round(abs(total_ret / max_dd), 2) if max_dd < 0 else 99,
        "sharpe": round(sharpe, 2),
        "cagr_pct": round(cagr * 100, 1),
        "xirr_pct": round(xirr_val * 100, 1) if not np.isnan(xirr_val) else None,
        "avg_win": round(wins["trade_ret"].mean(), 2) if len(wins) > 0 else 0,
        "avg_loss": round(losses["trade_ret"].mean(), 2) if len(losses) > 0 else 0,
        "cum_pnl_series": t[["entry_date", "cum_pnl", "pnl", "symbol"]].reset_index(drop=True),
    }

# =====================================================================
# 1. FILTER IMPACT ANALYSIS — does each filter HELP or HURT?
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 1: FILTER IMPACT — WHAT HELPS vs HURTS")
print("=" * 70)

CAP = 100000  # Rs.1L per trade
HOLD = "ret_10d"
MAE = "mae_10d"
SL = 10

# Define all filters
filters = {
    "BASELINE (all signals)": df,
    # Market regime
    "Nifty > 20DMA": df[df["nifty_above_20dma"] == True],
    "Nifty < 20DMA": df[df["nifty_above_20dma"] == False],
    # CANSLIM
    "CANSLIM >= 2": df[df.get("ret_10d").notna()],  # placeholder, compute below
    "CANSLIM >= 3": df,
    "CANSLIM >= 4": df,
    # Earnings
    "Earnings > 60d away": df[df["days_since_earn"] > 60],
    "Earnings < 15d": df[df["days_since_earn"] <= 15],
    # Volume
    "Vol ratio 1.5-3x": df[(df["vol_ratio"] >= 1.5) & (df["vol_ratio"] < 3)],
    "Vol ratio > 4x": df[df["vol_ratio"] >= 4],
    # Market cap
    "Largecap only": df[df["mcap"] == "Largecap"],
    "Midcap only": df[df["mcap"] == "Midcap"],
    "Large+Mid (no Small)": df[df["mcap"] != "Smallcap"],
    # Daily change
    "Change > 7%": df[df["daily_chg_pct"] > 7],
    "Change 5-10%": df[(df["daily_chg_pct"] >= 5) & (df["daily_chg_pct"] <= 10)],
    # RSI
    "RSI 55-65": df[(df["rsi14"] >= 55) & (df["rsi14"] <= 65)],
    "RSI > 75": df[df["rsi14"] > 75],
    # Gap
    "Gap down signal": df[df["gap_pct"] < 0],
    "Small gap (0-1%)": df[(df["gap_pct"] >= 0) & (df["gap_pct"] < 1)],
    "Big gap (>2%)": df[df["gap_pct"] > 2],
    # Sector exclusions
    "Exclude Banks": df[df["sector"] != "Bank"],
    "Exclude Banks+Fin": df[~df["sector"].isin(["Bank", "Financials"])],
    "Exclude bottom 5 sectors": df[~df["sector"].isin(["Bank", "Building Materials", "Energy", "Financials", "Textiles"])],
    # Combined
    "Nifty bull + chg>5%": df[(df["nifty_above_20dma"] == True) & (df["daily_chg_pct"] > 5)],
    "Nifty bull + no Banks": df[(df["nifty_above_20dma"] == True) & (df["sector"] != "Bank")],
    "Nifty bull + earn>30d": df[(df["nifty_above_20dma"] == True) & (df["days_since_earn"] > 30)],
    "Nifty bull + Large+Mid": df[(df["nifty_above_20dma"] == True) & (df["mcap"] != "Smallcap")],
    "Nifty bull + vol<3x": df[(df["nifty_above_20dma"] == True) & (df["vol_ratio"] < 3)],
    "BEST COMBO: bull+L/M+earn>30+noBanks": df[(df["nifty_above_20dma"] == True) & (df["mcap"] != "Smallcap") & (df["days_since_earn"] > 30) & (df["sector"] != "Bank")],
}

# Compute CANSLIM score
canslim = pd.Series(0.0, index=df.index)
canslim += (df["q1_sales_yoy_pct"] > 15).astype(float)
canslim += (df["q1_profit_yoy"] > 0).astype(float)
canslim += (df["new_hi"] == True).astype(float) if "new_hi" in df.columns else 0
canslim += np.where(df["mcap"] == "Midcap", 0.5, np.where(df["mcap"] == "Smallcap", 1, 0))
canslim += (df["rs_rank"] > 80).astype(float) if "rs_rank" in df.columns else 0
canslim += (df["nifty_above_20dma"] == True).astype(float)
df["canslim"] = canslim

filters["CANSLIM >= 2"] = df[df["canslim"] >= 2]
filters["CANSLIM >= 3"] = df[df["canslim"] >= 3]
filters["CANSLIM >= 4"] = df[df["canslim"] >= 4]
filters["CANSLIM < 3 (low score)"] = df[df["canslim"] < 3]

# Compute all filter stats
results = []
for label, fdf in filters.items():
    s = compute_stats(fdf, CAP, HOLD, MAE, SL, label)
    if s:
        results.append(s)

# Print results table
print(f"\n{'Filter':<45} {'n':>4} {'Win%':>6} {'Mean%':>7} {'PF':>5} {'TotalPnL':>10} {'MaxDD':>8} {'Sharpe':>7} {'CAGR%':>7}")
print("-" * 110)
for r in sorted(results, key=lambda x: -x["mean_ret"]):
    print(f"{r['label']:<45} {r['n']:>4} {r['win_pct']:>6.1f} {r['mean_ret']:>7.2f} {r['pf']:>5.2f} {r['total_pnl']:>10,} {r['max_dd']:>8,} {r['sharpe']:>7.2f} {r['cagr_pct']:>7.1f}")

# =====================================================================
# 2. EQUITY CURVES — key scenarios
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 2: EQUITY CURVES")
print("=" * 70)

curve_configs = [
    ("Baseline (all, SL10%, 10d)", df, 10, "ret_10d", "mae_10d"),
    ("Baseline (all, SL10%, 20d)", df, 10, "ret_20d", "mae_20d"),
    ("Baseline (all, SL10%, 30d)", df, 10, "ret_30d", "mae_30d"),
    ("Nifty bull only, SL10%, 10d", df[df["nifty_above_20dma"] == True], 10, "ret_10d", "mae_10d"),
    ("Bull+L/M+earn>30+noBanks, SL10%, 10d", df[(df["nifty_above_20dma"] == True) & (df["mcap"] != "Smallcap") & (df["days_since_earn"] > 30) & (df["sector"] != "Bank")], 10, "ret_10d", "mae_10d"),
    ("Bull+L/M+noBanks, SL10%, 20d", df[(df["nifty_above_20dma"] == True) & (df["mcap"] != "Smallcap") & (df["sector"] != "Bank")], 10, "ret_20d", "mae_20d"),
    ("No filter, SL15%, 30d", df, 15, "ret_30d", "mae_30d"),
]

curves = {}
for label, fdf, sl, ret_col, mae_col in curve_configs:
    s = compute_stats(fdf, CAP, ret_col, mae_col, sl, label)
    if s:
        curves[label] = s
        c = s["cum_pnl_series"]
        print(f"  {label}: n={s['n']}, PnL=Rs.{s['total_pnl']:,}, PF={s['pf']}, Sharpe={s['sharpe']}, MaxDD=Rs.{s['max_dd']:,}, CAGR={s['cagr_pct']}%")

# Plot equity curves
fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]})
colors = ['#2962ff', '#e91e63', '#ff9800', '#4caf50', '#9c27b0', '#00bcd4', '#795548']
for i, (label, s) in enumerate(curves.items()):
    c = s["cum_pnl_series"]
    axes[0].plot(c["entry_date"], c["cum_pnl"] / 1e5, label=f"{label}: Rs.{s['total_pnl']/1e5:.1f}L",
                 color=colors[i % len(colors)], lw=1.5, alpha=0.85)
    # Drawdown
    peak = c["cum_pnl"].cummax()
    dd = (c["cum_pnl"] - peak) / 1e5
    if i < 3:  # only show DD for first 3
        axes[1].fill_between(c["entry_date"], dd, 0, alpha=0.25, color=colors[i % len(colors)], label=label.split(",")[0])

axes[0].axhline(0, color='#787b86', lw=0.5)
axes[0].set_ylabel("Cumulative P&L (Rs. Lakh)")
axes[0].set_title("Breakout Scanner: Equity Curves (Rs.1L/trade, SL+time exit)")
axes[0].legend(fontsize=8, loc="upper left")
axes[0].grid(alpha=0.3)
axes[1].set_ylabel("Drawdown (Rs. L)")
axes[1].set_xlabel("Date")
axes[1].legend(fontsize=8)
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "equity_curves_v2.png", dpi=120)
print(f"  -> equity_curves_v2.png saved")

# =====================================================================
# 3. PORTFOLIO SIMULATION: 1Cr with 5%, 7.5%, 10% position sizes
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 3: PORTFOLIO SIZING (1Cr capital)")
print("=" * 70)

def simulate_portfolio(trades, initial_capital, pct_per_trade, sl_pct, hold_days, ret_col, mae_col, label=""):
    """Simulate a portfolio with capital allocation, max positions, and reinvestment."""
    t = trades.sort_values("entry_date").copy()
    t["trade_ret_pct"] = t.apply(lambda r: sim_sl(r[ret_col], r[mae_col], sl_pct, hold_days), axis=1)
    t = t.dropna(subset=["trade_ret_pct"]).reset_index(drop=True)

    capital = initial_capital
    position_size_fixed = initial_capital * pct_per_trade / 100
    max_positions = int(100 / pct_per_trade)

    # Track open positions
    open_positions = []  # list of (entry_date, exit_date, pnl)
    daily_nav = []
    trades_taken = []
    trades_skipped = 0

    for _, row in t.iterrows():
        entry_d = row["entry_date"]
        exit_d = entry_d + pd.Timedelta(days=hold_days)

        # Close expired positions
        closed = [p for p in open_positions if p[1] <= entry_d]
        for p in closed:
            capital += p[2] + position_size_fixed  # return capital + pnl
        open_positions = [p for p in open_positions if p[1] > entry_d]

        # Check if we can take this trade
        if len(open_positions) >= max_positions:
            trades_skipped += 1
            continue
        if capital < position_size_fixed:
            trades_skipped += 1
            continue

        # Take trade
        pnl = row["trade_ret_pct"] / 100 * position_size_fixed
        capital -= position_size_fixed  # allocate
        open_positions.append((entry_d, exit_d, pnl))

        # NAV = free cash + sum of (position_size + unrealized pnl) for open positions
        # Simplified: at entry, we know the final pnl but track as if it's realized at exit
        nav = capital + sum(position_size_fixed + p[2] for p in open_positions)
        daily_nav.append({"date": entry_d, "nav": nav, "pnl": pnl, "symbol": row["symbol"]})
        trades_taken.append(row)

    # Close remaining
    for p in open_positions:
        capital += p[2] + position_size_fixed

    nav_df = pd.DataFrame(daily_nav)
    if len(nav_df) == 0:
        return None

    total_pnl = capital - initial_capital
    trades_df = pd.DataFrame(trades_taken)
    wins = trades_df[trades_df["trade_ret_pct"] > 0]
    losses = trades_df[trades_df["trade_ret_pct"] <= 0]
    total_win_rs = (wins["trade_ret_pct"] / 100 * position_size_fixed).sum() if len(wins) > 0 else 0
    total_loss_rs = abs((losses["trade_ret_pct"] / 100 * position_size_fixed).sum()) if len(losses) > 0 else 1

    # Max DD
    peak = nav_df["nav"].cummax()
    dd = nav_df["nav"] - peak
    max_dd = dd.min()
    max_dd_pct = (max_dd / peak[dd.idxmin()]) * 100 if dd.min() < 0 else 0

    # CAGR
    days = (nav_df["date"].max() - nav_df["date"].min()).days
    cagr = ((initial_capital + total_pnl) / initial_capital) ** (365.25 / max(days, 1)) - 1 if days > 0 else 0

    # Sharpe
    mean_r = trades_df["trade_ret_pct"].mean()
    std_r = trades_df["trade_ret_pct"].std()
    tpy = len(trades_df) / max(days / 365.25, 0.01)
    sharpe = (mean_r / std_r * np.sqrt(tpy)) if std_r > 0 else 0

    # XIRR
    cfs = [(nav_df["date"].min(), -initial_capital)]
    cfs.append((nav_df["date"].max(), initial_capital + total_pnl))
    xirr_val = xirr(cfs)

    return {
        "label": label,
        "initial_cap": initial_capital,
        "pct_per_trade": pct_per_trade,
        "max_positions": max_positions,
        "n_trades": len(trades_df),
        "n_skipped": trades_skipped,
        "win_pct": round(len(wins) / len(trades_df) * 100, 1) if len(trades_df) > 0 else 0,
        "total_pnl": round(total_pnl),
        "total_ret_pct": round(total_pnl / initial_capital * 100, 2),
        "pf": round(total_win_rs / total_loss_rs, 2) if total_loss_rs > 0 else 99,
        "max_dd": round(max_dd),
        "max_dd_pct": round(max_dd_pct, 1),
        "sharpe": round(sharpe, 2),
        "cagr_pct": round(cagr * 100, 1),
        "xirr_pct": round(xirr_val * 100, 1) if xirr_val and not np.isnan(xirr_val) else None,
        "calmar": round(abs(total_pnl / max_dd), 2) if max_dd < 0 else 99,
        "nav_series": nav_df,
    }

# Test configurations
INIT_CAP = 10000000  # Rs.1Cr
portfolio_configs = []

# Baseline (all signals) with different sizing
for pct in [5, 7.5, 10]:
    for hold, ret_c, mae_c in [(10, "ret_10d", "mae_10d"), (20, "ret_20d", "mae_20d"), (30, "ret_30d", "mae_30d")]:
        label = f"ALL SL10% {hold}d hold, {pct}% size"
        r = simulate_portfolio(df, INIT_CAP, pct, 10, hold, ret_c, mae_c, label)
        if r:
            portfolio_configs.append(r)

# Filtered (Nifty bull + no small + no banks) with different sizing
filt_df = df[(df["nifty_above_20dma"] == True) & (df["mcap"] != "Smallcap") & (df["sector"] != "Bank")]
for pct in [5, 7.5, 10]:
    for hold, ret_c, mae_c in [(10, "ret_10d", "mae_10d"), (20, "ret_20d", "mae_20d")]:
        label = f"FILTERED SL10% {hold}d, {pct}% size"
        r = simulate_portfolio(filt_df, INIT_CAP, pct, 10, hold, ret_c, mae_c, label)
        if r:
            portfolio_configs.append(r)

# SL15% variants
for pct in [5, 7.5, 10]:
    label = f"ALL SL15% 30d, {pct}% size"
    r = simulate_portfolio(df, INIT_CAP, pct, 15, 30, "ret_30d", "mae_30d", label)
    if r:
        portfolio_configs.append(r)

# Print portfolio results
print(f"\n{'Config':<40} {'Trades':>6} {'Skip':>5} {'MaxPos':>6} {'Win%':>6} {'PnL':>12} {'Ret%':>7} {'PF':>5} {'MaxDD':>10} {'DD%':>6} {'Sharpe':>7} {'CAGR%':>7} {'Calmar':>7}")
print("-" * 145)
for r in sorted(portfolio_configs, key=lambda x: -x["total_pnl"]):
    print(f"{r['label']:<40} {r['n_trades']:>6} {r['n_skipped']:>5} {r['max_positions']:>6} {r['win_pct']:>6.1f} {r['total_pnl']:>12,} {r['total_ret_pct']:>7.2f} {r['pf']:>5.2f} {r['max_dd']:>10,} {r['max_dd_pct']:>6.1f} {r['sharpe']:>7.2f} {r['cagr_pct']:>7.1f} {r['calmar']:>7.2f}")

# =====================================================================
# 4. Rs.1L FIXED PER TRADE — comprehensive stats
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 4: Rs.1L FIXED PER TRADE — FULL STATS")
print("=" * 70)

fixed_configs = []
for hold, ret_c, mae_c in [(5, "ret_5d", "mae_5d"), (10, "ret_10d", "mae_10d"), (15, "ret_15d", "mae_15d"), (20, "ret_20d", "mae_20d"), (30, "ret_30d", "mae_30d")]:
    for sl in [7, 10, 15]:
        label = f"1L/trade SL{sl}% {hold}d"
        s = compute_stats(df, CAP, ret_c, mae_c, sl, label)
        if s:
            fixed_configs.append(s)

# Filtered variants
for hold, ret_c, mae_c in [(10, "ret_10d", "mae_10d"), (20, "ret_20d", "mae_20d")]:
    for sl in [10, 15]:
        label = f"1L FILT SL{sl}% {hold}d"
        s = compute_stats(filt_df, CAP, ret_c, mae_c, sl, label)
        if s:
            fixed_configs.append(s)

print(f"\n{'Config':<30} {'n':>4} {'Win%':>6} {'Mean%':>7} {'Med%':>6} {'PnL':>10} {'PF':>5} {'MaxDD':>8} {'Sharpe':>7} {'CAGR%':>7} {'AvgW':>6} {'AvgL':>6}")
print("-" * 115)
for r in sorted(fixed_configs, key=lambda x: -x["total_pnl"]):
    print(f"{r['label']:<30} {r['n']:>4} {r['win_pct']:>6.1f} {r['mean_ret']:>7.2f} {r['median_ret']:>6.2f} {r['total_pnl']:>10,} {r['pf']:>5.2f} {r['max_dd']:>8,} {r['sharpe']:>7.2f} {r['cagr_pct']:>7.1f} {r['avg_win']:>6.2f} {r['avg_loss']:>6.2f}")

# =====================================================================
# 5. PORTFOLIO NAV CURVES CHART
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 5: PORTFOLIO NAV CURVES")
print("=" * 70)

# Select best configs for charting
chart_configs = [
    ("ALL 10d 5%", "ALL SL10% 10d hold, 5% size"),
    ("ALL 10d 10%", "ALL SL10% 10d hold, 10% size"),
    ("ALL 20d 10%", "ALL SL10% 20d hold, 10% size"),
    ("ALL 30d 10%", "ALL SL10% 30d hold, 10% size"),
    ("FILT 10d 10%", "FILTERED SL10% 10d, 10% size"),
    ("FILT 20d 10%", "FILTERED SL10% 20d, 10% size"),
    ("ALL SL15 30d 10%", "ALL SL15% 30d, 10% size"),
]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]})
for i, (short, full) in enumerate(chart_configs):
    match = [r for r in portfolio_configs if r["label"] == full]
    if match:
        r = match[0]
        nav = r["nav_series"]
        ret_pct = (nav["nav"] - INIT_CAP) / INIT_CAP * 100
        ax1.plot(nav["date"], ret_pct, label=f"{short}: {r['total_ret_pct']}%",
                 color=colors[i % len(colors)], lw=1.5)
        # DD
        peak = nav["nav"].cummax()
        dd_pct = (nav["nav"] - peak) / peak * 100
        if i < 4:
            ax2.fill_between(nav["date"], dd_pct, 0, alpha=0.2, color=colors[i % len(colors)])

ax1.axhline(0, color='#787b86', lw=0.5)
ax1.set_ylabel("Portfolio Return %")
ax1.set_title("Rs.1Cr Portfolio: NAV Curves by Position Size & Hold Period")
ax1.legend(fontsize=8, loc="upper left")
ax1.grid(alpha=0.3)
ax2.set_ylabel("Drawdown %")
ax2.set_xlabel("Date")
ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "portfolio_nav_curves.png", dpi=120)
print(f"  -> portfolio_nav_curves.png saved")

# =====================================================================
# 6. MONTHLY BREAKDOWN
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 6: MONTHLY P&L BREAKDOWN")
print("=" * 70)

df["month"] = df["entry_date"].dt.to_period("M")
for hold, ret_c, mae_c in [(10, "ret_10d", "mae_10d"), (20, "ret_20d", "mae_20d")]:
    print(f"\n  {hold}d hold, SL10%:")
    for m, g in df.groupby("month"):
        g2 = g.copy()
        g2["tr"] = g2.apply(lambda r: sim_sl(r[ret_c], r[mae_c], 10, hold), axis=1)
        g2 = g2.dropna(subset=["tr"])
        if len(g2) == 0:
            continue
        pnl = (g2["tr"] / 100 * CAP).sum()
        win = (g2["tr"] > 0).mean() * 100
        print(f"    {m}: n={len(g2):>3}, win={win:>5.1f}%, mean={g2['tr'].mean():>6.2f}%, PnL=Rs.{pnl/1e5:>6.2f}L")

# =====================================================================
# 7. INDIVIDUAL SIGNAL REMOVAL TEST — which signals hurt most?
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 7: WORST SIGNALS — IMPACT IF REMOVED")
print("=" * 70)

base = compute_stats(df, CAP, "ret_10d", "mae_10d", 10, "base")
base_pnl = base["total_pnl"]

# Find worst individual trades
df_copy = df.copy()
df_copy["trade_ret"] = df_copy.apply(lambda r: sim_sl(r["ret_10d"], r["mae_10d"], 10, 10), axis=1)
df_copy["pnl_1L"] = df_copy["trade_ret"] / 100 * CAP
worst = df_copy.nlargest(10, "pnl_1L")  # best
worst_trades = df_copy.nsmallest(15, "pnl_1L")  # worst

print("\n  WORST 15 trades (biggest losses, SL10% 10d hold):")
print(f"  {'Date':<12} {'Symbol':<15} {'MCap':<10} {'Sector':<25} {'Ret%':>7} {'PnL':>10} {'Gap%':>6} {'Chg%':>6} {'Vol':>5} {'RSI':>5}")
for _, r in worst_trades.iterrows():
    print(f"  {r['signal_date'].date()} {r['symbol']:<15} {r['mcap']:<10} {r['sector']:<25} {r['trade_ret']:>7.2f} {r['pnl_1L']:>10,.0f} {r['gap_pct']:>6.2f} {r['daily_chg_pct']:>6.1f} {r['vol_ratio']:>5.1f} {r['rsi14']:>5.1f}")

print(f"\n  BEST 10 trades:")
for _, r in worst.iterrows():
    print(f"  {r['signal_date'].date()} {r['symbol']:<15} {r['mcap']:<10} {r['sector']:<25} {r['trade_ret']:>7.2f} {r['pnl_1L']:>10,.0f}")

# =====================================================================
# 8. STRATEGY NOTES SUMMARY
# =====================================================================
print("\n" + "=" * 70)
print("SECTION 8: STRATEGY NOTES")
print("=" * 70)

print("""
CHARTLINK VCP BREAKOUT SCANNER — STRATEGY NOTES
================================================

SCANNER FORMULA (Minervini/VCP-style):
  - Market cap > Rs.1000cr, Turnover > Rs.25cr
  - Close > 5-day high * 1.01 (new breakout)
  - RSI(14) > 60
  - Volume > 2x 20-day average
  - Upper Bollinger Band breakout
  - Prior day NOT extended (range compression → expansion)

ENTRY: Next-day OPEN (signal fires at EOD, buy at next morning's open)
  - Outperforms buy-above-high at ALL horizons (3.87% vs 3.60% at 10d)

STOP LOSS: 10-15% (WIDE)
  - 2% SL kills 73% of trades. Breakout stocks retrace 3-5% before running.
  - 10% SL, 30d hold: 62.1% win, 7.10% mean, PF 3.50
  - 15% SL, 30d hold: 65.0% win, 7.37% mean, PF 3.54

EXIT: Time-based (10-30 days). NO trailing stops, NO targets, NO partial profits.
  - All exit sophistication reduces expectancy.
  - Simple hold beats every trail/target/partial variant tested.

FILTERS THAT HELP:
  + Nifty > 20DMA (market regime filter is ESSENTIAL)
  + Volume ratio 1.5-3x (moderate surge > monster volume)
  + RSI 55-65 (not yet overbought)
  + Earnings > 30-60 days away
  + Exclude Banks, Building Materials sectors
  + Exclude Smallcap

FILTERS THAT HURT:
  - CANSLIM >= 4 (over-screening kills returns)
  - Very tight filters (reduce sample too much)
  - Complex multi-factor combos (marginal improvement, large sample loss)

MARKET REGIME DEPENDENCY:
  - Nov 2025 - Feb 2026: NET NEGATIVE (-2.1% mean, 31% win)
  - Apr 2026: +13.22% mean, 91% win (India-Pak rally anomaly)
  - Strategy needs BULL market to work. Regime filter is mandatory.

POSITION SIZING:
  - 1L fixed per trade: simplest, best PF, ~Rs.7-8L total
  - 1Cr portfolio, 10% per trade (max 10 positions): higher absolute returns
  - 7.5% sizing = balance between diversification and concentration
""")

print(f"\nAll outputs saved to: {OUT}")
print("Files: equity_curves_v2.png, portfolio_nav_curves.png, trades_detail.csv")
