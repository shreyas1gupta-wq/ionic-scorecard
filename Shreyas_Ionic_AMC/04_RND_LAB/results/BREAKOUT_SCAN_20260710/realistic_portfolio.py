"""
REALISTIC Rs.1Cr Portfolio Backtest — VCP Breakout Scanner (Jan 2020 - Jul 2026)
================================================================================
Fixes every flaw of the earlier simplified sim:
  1. DAILY mark-to-market NAV (not entry-date snapshots)
  2. Full transaction costs: brokerage, STT, exchange charges, stamp duty, slippage
  3. Integer share quantities
  4. SL checked daily against actual intraday lows (gap-down handled: exit at open)
  5. Time exit at close after N trading days
  6. Max 10% of NAV per new entry
  7. Drift rule: position weight > 20% of NAV -> trim to 15% at close
  8. Cash constraint: no trade without cash (no lookahead on future P&L)
  9. Stale/delisted data: force-exit at last known close after 10 missing days

COST MODEL (delivery equity, discount broker, stated explicitly):
  Buy side : brokerage 0.03% + STT 0.1% + exch 0.00345% + stamp 0.015% + GST ~= 0.152%
  Sell side: brokerage 0.03% + STT 0.1% + exch 0.00345% + GST          ~= 0.137%
  Slippage : 0.15% per side (breakout stocks bought at open on strength)
  Round trip ~= 0.59% all-in.
"""
import os, sys, warnings, pickle
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"

# ---------------- Parameters ----------------
INIT_CAP = 10_000_000          # Rs.1 Cr
MAX_ENTRY_PCT = 0.10           # max 10% of NAV per new position
DRIFT_MAX = 0.20               # if position > 20% of NAV...
DRIFT_TRIM_TO = 0.15           # ...trim to 15%
BUY_COST = 0.00152             # brokerage+STT+exch+stamp+GST buy side
SELL_COST = 0.00137            # sell side
SLIP = 0.0015                  # 0.15% slippage per side
MIN_TICKET = 50_000            # skip entries below Rs.50k
STALE_LIMIT = 10               # force-exit after 10 missing bars

CONFIGS = [
    {"name": "SL15pct_30d", "sl": 0.15, "hold": 30, "regime": False},
    {"name": "SL10pct_30d", "sl": 0.10, "hold": 30, "regime": False},
    {"name": "SL15pct_30d_REGIME", "sl": 0.15, "hold": 30, "regime": True},
    {"name": "SL10pct_20d_REGIME", "sl": 0.10, "hold": 20, "regime": True},
]

# ---------------- 1. Load stitched daily panel ----------------
print("=" * 70)
print("STEP 1: Loading stitched daily panel")
print("=" * 70)

panel_path = os.path.join(OUT, "stitched_daily_panel.parquet")
if os.path.exists(panel_path):
    all_data = pd.read_parquet(panel_path)
    print(f"  Loaded cached panel: {len(all_data):,} rows")
else:
    frames = []
    bhav = pd.read_csv(os.path.join(BASE, "nifty_stock_daily", "1_bhavcopy.csv"), parse_dates=["date"])
    bhav["turnover_cr"] = bhav["turnover_lacs"] / 100
    b = bhav[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr"]].copy()
    b["source"] = "bhavcopy"; frames.append(b)

    with open(os.path.join(os.path.dirname(BASE), "stocks_data_cache.pkl"), "rb") as fh:
        cache = pickle.load(fh)
    price_wide = cache["price"]
    rows = []
    for sym_ns in sorted(set(c[0] for c in price_wide.columns)):
        sym = sym_ns.replace(".NS", "")
        sub = price_wide[sym_ns].dropna(subset=["Close"])
        if len(sub) < 30: continue
        sub = sub.reset_index()
        sub.columns = ["date", "open", "high", "low", "close", "volume"]
        sub["symbol"] = sym
        sub["turnover_cr"] = sub["close"] * sub["volume"] / 1e7
        sub["source"] = "cache"
        sub["date"] = pd.to_datetime(sub["date"])
        rows.append(sub[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr", "source"]])
    frames.append(pd.concat(rows, ignore_index=True))

    ang = pd.read_parquet(os.path.join(BASE, "angel_daily_n500_2026.parquet"))
    ang["date"] = pd.to_datetime(ang["timestamp"]).dt.tz_localize(None)
    ang["turnover_cr"] = ang["close"] * ang["volume"] / 1e7
    ang["source"] = "angel"
    frames.append(ang[["date", "symbol", "open", "high", "low", "close", "volume", "turnover_cr", "source"]])

    all_data = pd.concat(frames, ignore_index=True)
    prio = {"angel": 0, "cache": 1, "bhavcopy": 2}
    all_data["p"] = all_data["source"].map(prio)
    all_data = (all_data.sort_values(["symbol", "date", "p"])
                        .drop_duplicates(["symbol", "date"], keep="first")
                        .drop(columns=["p"]))
    all_data = all_data[(all_data["close"] > 0) & (all_data["volume"] > 0) & (all_data["date"] >= "2020-01-01")]
    all_data = all_data.sort_values(["symbol", "date"]).reset_index(drop=True)
    all_data.to_parquet(panel_path)
    print(f"  Built & cached panel: {len(all_data):,} rows")

# ---------------- 2. Bar lookup + calendar ----------------
print("STEP 2: Building bar lookup")
sym_bars = {}
for sym, g in all_data.groupby("symbol"):
    dts = g["date"].values
    sym_bars[sym] = dict(zip(
        pd.DatetimeIndex(dts),
        zip(g["open"].values, g["high"].values, g["low"].values, g["close"].values)
    ))
calendar = sorted(all_data["date"].unique())
calendar = [pd.Timestamp(d) for d in calendar]
print(f"  {len(sym_bars)} symbols, {len(calendar)} trading days")

# ---------------- 3. Load signals ----------------
print("STEP 3: Loading signals")
sig = pd.read_csv(os.path.join(OUT, "backtest_6yr_trades.csv"),
                  parse_dates=["signal_date", "entry_date"])
sig = sig.sort_values(["entry_date", "turnover_cr"], ascending=[True, False])
entries_by_day = {}
for d, g in sig.groupby("entry_date"):
    entries_by_day[pd.Timestamp(d)] = list(zip(g["symbol"], g["turnover_cr"]))
print(f"  {len(sig)} signals across {len(entries_by_day)} entry days")

# NIFTY regime: signal-day NIFTY close > its 20DMA
nifty_r = pd.read_parquet(os.path.join(BASE, "index_daily", "nifty50.parquet"))
tcol_r = "timestamp" if "timestamp" in nifty_r.columns else "date"
nifty_r["date"] = pd.to_datetime(nifty_r[tcol_r])
if nifty_r["date"].dt.tz is not None:
    nifty_r["date"] = nifty_r["date"].dt.tz_localize(None)
nifty_r = nifty_r.sort_values("date")
nifty_r["dma20"] = nifty_r["close"].rolling(20).mean()
regime_ok = dict(zip(nifty_r["date"], nifty_r["close"] > nifty_r["dma20"]))

sig_regime = sig.merge(nifty_r[["date", "close", "dma20"]], left_on="signal_date", right_on="date", how="left")
sig["bull"] = (sig_regime["close"] > sig_regime["dma20"]).fillna(True).values
entries_by_day_bull = {}
for d, g in sig[sig["bull"]].groupby("entry_date"):
    entries_by_day_bull[pd.Timestamp(d)] = list(zip(g["symbol"], g["turnover_cr"]))
print(f"  Regime-filtered: {int(sig['bull'].sum())} bull-only signals")

# ---------------- 4. Daily event-driven simulation ----------------
def run_sim(sl_pct, hold_days, name, use_regime=False):
    entry_map = entries_by_day_bull if use_regime else entries_by_day
    cash = float(INIT_CAP)
    positions = {}   # sym -> dict
    nav_hist = []    # (date, nav, cash, n_pos, invested)
    trade_log = []
    costs_paid = 0.0
    slip_paid = 0.0
    counters = {"entries": 0, "sl_exits": 0, "time_exits": 0, "trims": 0,
                "stale_exits": 0, "skipped_cash": 0, "skipped_holding": 0}

    def sell_shares(sym, shares, px, d, reason):
        nonlocal cash, costs_paid, slip_paid
        p = positions[sym]
        gross = shares * px
        fees = gross * SELL_COST
        slip_amt = shares * px * SLIP / (1 - SLIP)   # slippage already inside px
        cash += gross - fees
        costs_paid += fees
        slip_paid += slip_amt
        pnl = (px - p["entry_px"]) * shares - fees
        trade_log.append({"date": d, "symbol": sym, "action": reason,
                          "shares": shares, "px": round(px, 2),
                          "pnl": round(pnl), "hold_days": p["days_held"]})
        p["shares"] -= shares
        if p["shares"] <= 0:
            del positions[sym]

    prev_nav = float(INIT_CAP)

    for d in calendar:
        # ---- 1. ENTRIES at today's open ----
        for sym, _turn in entry_map.get(d, []):
            if sym in positions:
                counters["skipped_holding"] += 1
                continue
            bar = sym_bars.get(sym, {}).get(d)
            if bar is None:
                continue
            o = bar[0]
            if o <= 0 or np.isnan(o):
                continue
            buy_px = o * (1 + SLIP)
            budget = min(MAX_ENTRY_PCT * prev_nav, cash)
            if budget < MIN_TICKET:
                counters["skipped_cash"] += 1
                continue
            shares = int(budget / (buy_px * (1 + BUY_COST)))
            if shares <= 0:
                counters["skipped_cash"] += 1
                continue
            gross = shares * buy_px
            fees = gross * BUY_COST
            cash -= gross + fees
            costs_paid += fees
            slip_paid += shares * o * SLIP
            positions[sym] = {
                "shares": shares, "entry_px": buy_px,
                "sl_px": buy_px * (1 - sl_pct),
                "days_held": 0, "stale": 0, "last_close": buy_px,
            }
            counters["entries"] += 1
            trade_log.append({"date": d, "symbol": sym, "action": "BUY",
                              "shares": shares, "px": round(buy_px, 2), "pnl": 0, "hold_days": 0})

        # ---- 2. SL (intraday) + time exits ----
        for sym in list(positions.keys()):
            p = positions[sym]
            bar = sym_bars.get(sym, {}).get(d)
            if bar is None:
                p["stale"] += 1
                if p["stale"] > STALE_LIMIT:
                    sell_shares(sym, p["shares"], p["last_close"] * (1 - SLIP), d, "STALE")
                    counters["stale_exits"] += 1
                continue
            p["stale"] = 0
            o, h, l, c = bar
            # SL check (gap-down: fill at open, else at SL price)
            if l <= p["sl_px"]:
                fill = min(o, p["sl_px"]) * (1 - SLIP)
                sell_shares(sym, p["shares"], fill, d, "SL")
                counters["sl_exits"] += 1
                continue
            p["last_close"] = c
            p["days_held"] += 1
            # time exit at close
            if p["days_held"] >= hold_days:
                sell_shares(sym, p["shares"], c * (1 - SLIP), d, "TIME")
                counters["time_exits"] += 1

        # ---- 3. MTM + drift trims at close ----
        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        for sym in list(positions.keys()):
            p = positions[sym]
            val = p["shares"] * p["last_close"]
            if val > DRIFT_MAX * nav:
                target_val = DRIFT_TRIM_TO * nav
                excess_shares = int((val - target_val) / p["last_close"])
                if excess_shares > 0:
                    sell_shares(sym, excess_shares, p["last_close"] * (1 - SLIP), d, "TRIM")
                    counters["trims"] += 1

        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        nav_hist.append({"date": d, "nav": nav, "cash": cash,
                         "n_pos": len(positions), "invested": pos_val})
        prev_nav = nav

    # liquidate remaining at last close
    for sym in list(positions.keys()):
        p = positions[sym]
        sell_shares(sym, p["shares"], p["last_close"] * (1 - SLIP), calendar[-1], "FINAL")

    nav_df = pd.DataFrame(nav_hist)
    nav_df["ret"] = nav_df["nav"].pct_change()

    final_nav = cash
    total_ret = final_nav / INIT_CAP - 1
    days_span = (nav_df["date"].iloc[-1] - nav_df["date"].iloc[0]).days
    cagr = (final_nav / INIT_CAP) ** (365.25 / days_span) - 1
    peak = nav_df["nav"].cummax()
    dd = nav_df["nav"] / peak - 1
    max_dd = dd.min()
    sharpe = nav_df["ret"].mean() / nav_df["ret"].std() * np.sqrt(252) if nav_df["ret"].std() > 0 else 0
    neg = nav_df["ret"][nav_df["ret"] < 0]
    sortino = nav_df["ret"].mean() / neg.std() * np.sqrt(252) if len(neg) > 0 and neg.std() > 0 else 0

    print(f"\n===== {name} (SL {sl_pct*100:.0f}%, hold {hold_days}d) =====")
    print(f"  Final NAV     : Rs.{final_nav:,.0f}  ({total_ret*100:+.1f}%)")
    print(f"  CAGR          : {cagr*100:.2f}%")
    print(f"  Max Drawdown  : {max_dd*100:.2f}%")
    print(f"  Sharpe (daily): {sharpe:.2f}   Sortino: {sortino:.2f}")
    print(f"  Calmar        : {abs(cagr/max_dd):.2f}")
    print(f"  Costs paid    : Rs.{costs_paid:,.0f} | Slippage: Rs.{slip_paid:,.0f} "
          f"| Total friction: Rs.{costs_paid+slip_paid:,.0f} ({(costs_paid+slip_paid)/INIT_CAP*100:.1f}% of initial capital)")
    print(f"  Trades: {counters['entries']} entries | {counters['sl_exits']} SL | "
          f"{counters['time_exits']} time | {counters['trims']} trims | {counters['stale_exits']} stale")
    print(f"  Skipped: {counters['skipped_cash']} no-cash | {counters['skipped_holding']} already-holding")

    # yearly returns from daily NAV
    nav_df["year"] = nav_df["date"].dt.year
    print(f"\n  {'Year':<6} {'StartNAV':>12} {'EndNAV':>12} {'Return%':>8} {'MaxDD%':>7} {'AvgPos':>7}")
    yearly_rows = []
    for yr, g in nav_df.groupby("year"):
        start = g["nav"].iloc[0]; end = g["nav"].iloc[-1]
        ypeak = g["nav"].cummax(); ydd = (g["nav"] / ypeak - 1).min()
        yret = end / start - 1
        print(f"  {yr:<6} {start:>12,.0f} {end:>12,.0f} {yret*100:>7.1f}% {ydd*100:>6.1f}% {g['n_pos'].mean():>7.1f}")
        yearly_rows.append({"year": yr, "ret_pct": round(yret*100, 1), "maxdd_pct": round(ydd*100, 1),
                            "avg_pos": round(g["n_pos"].mean(), 1), "end_nav": round(end)})

    # monthly NAV snapshots (for charting)
    monthly = nav_df.groupby(nav_df["date"].dt.to_period("M")).last()[["nav"]]
    print(f"\n  Monthly NAV snapshots (Rs. L):")
    print("  " + ", ".join(f"{str(m)}:{v/1e5:.0f}" for m, v in monthly["nav"].items()))

    nav_df.to_csv(os.path.join(OUT, f"realistic_nav_{name}.csv"), index=False)
    pd.DataFrame(trade_log).to_csv(os.path.join(OUT, f"realistic_trades_{name}.csv"), index=False)

    return {"name": name, "nav_df": nav_df, "final_nav": final_nav, "cagr": cagr,
            "max_dd": max_dd, "sharpe": sharpe, "sortino": sortino,
            "costs": costs_paid, "slip": slip_paid, "counters": counters,
            "yearly": yearly_rows, "monthly": monthly}

results = []
for cfg in CONFIGS:
    results.append(run_sim(cfg["sl"], cfg["hold"], cfg["name"], cfg["regime"]))

# ---------------- 5. NIFTY benchmark ----------------
print("\n" + "=" * 70)
print("BENCHMARK: NIFTY 50 buy & hold (same window)")
print("=" * 70)
nifty = pd.read_parquet(os.path.join(BASE, "index_daily", "nifty50.parquet"))
tcol = "timestamp" if "timestamp" in nifty.columns else "date"
nifty["date"] = pd.to_datetime(nifty[tcol])
if nifty["date"].dt.tz is not None:
    nifty["date"] = nifty["date"].dt.tz_localize(None)
nifty = nifty[(nifty["date"] >= calendar[0]) & (nifty["date"] <= calendar[-1])].sort_values("date")
n_start, n_end = nifty["close"].iloc[0], nifty["close"].iloc[-1]
n_days = (nifty["date"].iloc[-1] - nifty["date"].iloc[0]).days
n_cagr = (n_end / n_start) ** (365.25 / n_days) - 1
n_peak = nifty["close"].cummax()
n_dd = (nifty["close"] / n_peak - 1).min()
print(f"  NIFTY 50: {n_start:.0f} -> {n_end:.0f}  | total {((n_end/n_start)-1)*100:+.1f}% | CAGR {n_cagr*100:.2f}% | MaxDD {n_dd*100:.1f}%")

# ---------------- 6. Chart ----------------
fig, axes = plt.subplots(2, 1, figsize=(15, 9), gridspec_kw={"height_ratios": [3, 1]})
colors = ["#2962ff", "#e91e63", "#2e7d32", "#ff9800"]
for i, r in enumerate(results):
    nd = r["nav_df"]
    axes[0].plot(nd["date"], nd["nav"] / 1e7, label=f"{r['name']}: CAGR {r['cagr']*100:.1f}%, DD {r['max_dd']*100:.1f}%",
                 color=colors[i], lw=1.3)
    peak = nd["nav"].cummax()
    axes[1].fill_between(nd["date"], (nd["nav"]/peak - 1) * 100, 0, alpha=0.3, color=colors[i])
# nifty scaled to 1Cr
axes[0].plot(nifty["date"], nifty["close"] / n_start, label=f"NIFTY 50: CAGR {n_cagr*100:.1f}%",
             color="#787b86", lw=1.2, ls="--")
axes[0].set_ylabel("NAV (Rs. Cr)")
axes[0].set_title("Realistic Rs.1Cr Portfolio — daily MTM, full costs, 10% entries, 20%->15% drift trim")
axes[0].legend(); axes[0].grid(alpha=0.3)
axes[1].set_ylabel("Drawdown %"); axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "realistic_portfolio_nav.png"), dpi=120)
print(f"\nSaved: realistic_portfolio_nav.png, realistic_nav_*.csv, realistic_trades_*.csv")
