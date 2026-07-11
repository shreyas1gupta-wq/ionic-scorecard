"""
CHARTLINK-SIGNALS realistic Rs.1Cr portfolio backtest (Nov 2025 - Jul 2026)
===========================================================================
Uses ONLY the actual Chartlink screener output (221 signals) — NOT our
replicated scanner logic. Price data downloaded fresh from yfinance for
all signal symbols (one consistent source, no panel gaps), with Angel
data as fallback.

Simulation rules (as ordered by Principal):
  - Entry: next trading day OPEN after signal date
  - Max 10% of NAV per new entry, cash-constrained, integer shares
  - Drift rule: if a position grows > 20% of NAV -> trim to 15% at close
  - SL checked daily vs intraday low (gap-down: fill at open)
  - Time exit at close after N trading days
  - Daily mark-to-market NAV -> daily P&L
  - Full transaction costs:
      Buy : brokerage 0.03% + STT 0.1% + exch 0.00345% + stamp 0.015% + GST ~ 0.152%
      Sell: brokerage 0.03% + STT 0.1% + exch 0.00345% + GST          ~ 0.137%
      Slippage: 0.15% per side
      Round trip ~ 0.59% all-in
"""
import os, sys, warnings, time
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (1).csv"
BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
PRICE_CACHE = os.path.join(OUT, "chartlink_prices.parquet")

INIT_CAP = 10_000_000
MAX_ENTRY_PCT = 0.10
DRIFT_MAX = 0.20
DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152
SELL_COST = 0.00137
SLIP = 0.0015
MIN_TICKET = 50_000
STALE_LIMIT = 10

CONFIGS = [
    {"name": "SL10_20d", "sl": 0.10, "hold": 20},
    {"name": "SL10_30d", "sl": 0.10, "hold": 30},
    {"name": "SL15_30d", "sl": 0.15, "hold": 30},
]

# ---------------- 1. Load Chartlink signals ----------------
print("=" * 70)
print("STEP 1: Loading Chartlink signals (the actual screener output)")
print("=" * 70)
sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig.sort_values("Date").reset_index(drop=True)
print(f"  {len(sig)} signals, {sig['Symbol'].nunique()} unique symbols")
print(f"  {sig['Date'].min().date()} -> {sig['Date'].max().date()}")

symbols = sorted(sig["Symbol"].unique())

# ---------------- 2. Build price panel (yfinance primary) ----------------
print("\n" + "=" * 70)
print("STEP 2: Building price panel for signal symbols")
print("=" * 70)

DL_START = "2025-10-15"
DL_END = "2026-07-11"

yf_aliases = {
    "NAUKRI": ["NAUKRI.NS", "INFO.NS"],
    "AEGISVOPAK": ["AEGISVOPAK.NS", "AEGISLOG.NS"],
    "TIPSMUSIC": ["TIPSMUSIC.NS", "TIPSINDS.NS"],
    "IKS": ["IKS.NS"],
    "BLSE": ["BLSE.NS"],
}

if os.path.exists(PRICE_CACHE):
    panel = pd.read_parquet(PRICE_CACHE)
    print(f"  Loaded cached panel: {len(panel):,} rows, {panel['symbol'].nunique()} symbols")
else:
    import yfinance as yf
    rows_all = []
    failed = []
    for i, sym in enumerate(symbols):
        tickers = yf_aliases.get(sym, [f"{sym}.NS", f"{sym}.BO"])
        got = False
        for tk in tickers:
            for attempt in range(2):
                try:
                    df = yf.download(tk, start=DL_START, end=DL_END,
                                     progress=False, timeout=20, auto_adjust=False)
                    if len(df) >= 30:
                        df = df.reset_index()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                        sub = pd.DataFrame({
                            "date": pd.to_datetime(df["Date"]).dt.tz_localize(None),
                            "open": df["Open"].astype(float),
                            "high": df["High"].astype(float),
                            "low": df["Low"].astype(float),
                            "close": df["Close"].astype(float),
                            "volume": df["Volume"].fillna(0).astype(np.int64),
                        })
                        sub["symbol"] = sym
                        sub["source"] = "yf"
                        rows_all.append(sub)
                        got = True
                        break
                    break
                except Exception:
                    time.sleep(2)
            if got:
                break
        if not got:
            failed.append(sym)
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(symbols)} downloaded ({len(failed)} failed)")

    print(f"  yfinance: {len(rows_all)} symbols OK, {len(failed)} failed: {failed}")

    # Fallback: Angel daily for failed/missing symbols
    ang = pd.read_parquet(os.path.join(BASE, "angel_daily_n500_2026.parquet"))
    ang["date"] = pd.to_datetime(ang["timestamp"]).dt.tz_localize(None)
    ang_part = ang[ang["symbol"].isin(failed)][["date", "symbol", "open", "high", "low", "close", "volume"]].copy()
    if len(ang_part):
        ang_part["source"] = "angel"
        rows_all.append(ang_part)
        still = set(failed) - set(ang_part["symbol"].unique())
        print(f"  Angel fallback: {ang_part['symbol'].nunique()} symbols; still missing: {sorted(still)}")

    # Fallback 2: yf_missing_39.parquet
    yfm_path = os.path.join(OUT, "yf_missing_39.parquet")
    if os.path.exists(yfm_path):
        yfm = pd.read_parquet(yfm_path)
        yfm["date"] = pd.to_datetime(yfm["date"])
        covered = set(pd.concat(rows_all)["symbol"].unique()) if rows_all else set()
        yfm_part = yfm[~yfm["symbol"].isin(covered)].copy()
        if len(yfm_part):
            yfm_part["source"] = "yfm"
            rows_all.append(yfm_part[["date", "symbol", "open", "high", "low", "close", "volume", "source"]])
            print(f"  yf_missing_39 fallback: {yfm_part['symbol'].nunique()} symbols")

    panel = pd.concat(rows_all, ignore_index=True)
    panel = panel[(panel["close"] > 0)]
    panel = (panel.sort_values(["symbol", "date"])
                  .drop_duplicates(["symbol", "date"], keep="first")
                  .reset_index(drop=True))
    panel.to_parquet(PRICE_CACHE)
    print(f"  Panel cached: {len(panel):,} rows, {panel['symbol'].nunique()} symbols")

# Coverage check per signal
print("\n  Signal coverage check:")
have_syms = set(panel["symbol"].unique())
missing_syms = [s for s in symbols if s not in have_syms]
print(f"  Symbols covered: {len(have_syms & set(symbols))}/{len(symbols)}")
if missing_syms:
    print(f"  MISSING: {missing_syms}")

# ---------------- 3. Bar lookup + calendar ----------------
print("\nSTEP 3: Building bar lookup")
sym_bars = {}
for s, g in panel.groupby("symbol"):
    sym_bars[s] = dict(zip(pd.DatetimeIndex(g["date"]),
                           zip(g["open"], g["high"], g["low"], g["close"])))
cal_start = pd.Timestamp("2025-11-15")
calendar = sorted(d for d in panel["date"].unique() if pd.Timestamp(d) >= cal_start)
calendar = [pd.Timestamp(d) for d in calendar]
# Filter to dates where at least 20 symbols traded (removes odd stragglers)
date_counts = panel.groupby("date")["symbol"].nunique()
calendar = [d for d in calendar if date_counts.get(d, 0) >= 20]
print(f"  {len(sym_bars)} symbols, {len(calendar)} trading days "
      f"({calendar[0].date()} -> {calendar[-1].date()})")

cal_idx = {d: i for i, d in enumerate(calendar)}

# Map each signal to its entry day = next trading day with a bar for that symbol
entries_by_day = {}
unmatched = []
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    if s not in sym_bars:
        unmatched.append((s, sd.date(), "no data"))
        continue
    later = [d for d in calendar if d > sd and d in sym_bars[s]]
    if not later:
        unmatched.append((s, sd.date(), "no bar after signal"))
        continue
    ed = later[0]
    # entry must be within 5 calendar days of signal (else stale signal)
    if (ed - sd).days > 5:
        unmatched.append((s, sd.date(), f"first bar {ed.date()} too late"))
        continue
    entries_by_day.setdefault(ed, []).append(s)

n_entries = sum(len(v) for v in entries_by_day.values())
print(f"  Mapped {n_entries}/{len(sig)} signals to entry days; {len(unmatched)} unmatched")
for u in unmatched[:10]:
    print(f"    unmatched: {u}")

# ---------------- 4. Daily event-driven simulation ----------------
def run_sim(sl_pct, hold_days, name):
    cash = float(INIT_CAP)
    positions = {}
    nav_hist = []
    trade_log = []
    costs_paid = 0.0
    slip_paid = 0.0
    counters = {"entries": 0, "sl_exits": 0, "time_exits": 0, "trims": 0,
                "stale_exits": 0, "skipped_cash": 0, "skipped_holding": 0}

    def sell_shares(s, shares, px, d, reason):
        nonlocal cash, costs_paid, slip_paid
        p = positions[s]
        gross = shares * px
        fees = gross * SELL_COST
        cash += gross - fees
        costs_paid += fees
        slip_paid += shares * px * SLIP / (1 - SLIP)
        pnl = (px - p["entry_px"]) * shares - fees
        trade_log.append({"date": d, "symbol": s, "action": reason,
                          "shares": shares, "px": round(px, 2),
                          "pnl": round(pnl), "hold_days": p["days_held"]})
        p["shares"] -= shares
        if p["shares"] <= 0:
            del positions[s]

    prev_nav = float(INIT_CAP)

    for d in calendar:
        # 1) ENTRIES at open
        for s in entries_by_day.get(d, []):
            if s in positions:
                counters["skipped_holding"] += 1
                continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                continue
            o = bar[0]
            if not (o > 0):
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
            positions[s] = {"shares": shares, "entry_px": buy_px,
                            "sl_px": buy_px * (1 - sl_pct),
                            "days_held": 0, "stale": 0, "last_close": buy_px,
                            "entry_date": d}
            counters["entries"] += 1
            trade_log.append({"date": d, "symbol": s, "action": "BUY",
                              "shares": shares, "px": round(buy_px, 2),
                              "pnl": 0, "hold_days": 0})

        # 2) SL + time exits
        for s in list(positions.keys()):
            p = positions[s]
            bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"] += 1
                if p["stale"] > STALE_LIMIT:
                    sell_shares(s, p["shares"], p["last_close"] * (1 - SLIP), d, "STALE")
                    counters["stale_exits"] += 1
                continue
            p["stale"] = 0
            o, h, l, c = bar
            if l <= p["sl_px"]:
                fill = min(o, p["sl_px"]) * (1 - SLIP)
                sell_shares(s, p["shares"], fill, d, "SL")
                counters["sl_exits"] += 1
                continue
            p["last_close"] = c
            p["days_held"] += 1
            if p["days_held"] >= hold_days:
                sell_shares(s, p["shares"], c * (1 - SLIP), d, "TIME")
                counters["time_exits"] += 1

        # 3) MTM + drift trim
        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        for s in list(positions.keys()):
            p = positions[s]
            val = p["shares"] * p["last_close"]
            if val > DRIFT_MAX * nav:
                target = DRIFT_TRIM_TO * nav
                excess = int((val - target) / p["last_close"])
                if excess > 0:
                    sell_shares(s, excess, p["last_close"] * (1 - SLIP), d, "TRIM")
                    counters["trims"] += 1

        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        nav_hist.append({"date": d, "nav": round(nav), "cash": round(cash),
                         "invested": round(pos_val), "n_pos": len(positions),
                         "day_pnl": round(nav - prev_nav)})
        prev_nav = nav

    for s in list(positions.keys()):
        p = positions[s]
        sell_shares(s, p["shares"], p["last_close"] * (1 - SLIP), calendar[-1], "FINAL")

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
    sortino = nav_df["ret"].mean() / neg.std() * np.sqrt(252) if len(neg) and neg.std() > 0 else 0

    tl = pd.DataFrame(trade_log)
    sells = tl[tl["action"] != "BUY"]
    wins = sells[sells["pnl"] > 0]
    win_rate = len(wins) / len(sells) * 100 if len(sells) else 0

    print(f"\n===== {name} (SL {sl_pct*100:.0f}%, hold {hold_days}d) =====")
    print(f"  Final NAV   : Rs.{final_nav:,.0f}  ({total_ret*100:+.2f}%)")
    print(f"  CAGR (ann.) : {cagr*100:.1f}%")
    print(f"  Max DD      : {max_dd*100:.2f}%")
    print(f"  Sharpe      : {sharpe:.2f}  Sortino: {sortino:.2f}  Calmar: {abs(cagr/max_dd) if max_dd<0 else 99:.2f}")
    print(f"  Win rate    : {win_rate:.1f}% of {len(sells)} exits")
    print(f"  Friction    : costs Rs.{costs_paid:,.0f} + slippage Rs.{slip_paid:,.0f} "
          f"= Rs.{costs_paid+slip_paid:,.0f} ({(costs_paid+slip_paid)/INIT_CAP*100:.2f}% of capital)")
    print(f"  Trades      : {counters['entries']} entries | {counters['sl_exits']} SL | "
          f"{counters['time_exits']} time | {counters['trims']} trims | {counters['stale_exits']} stale")
    print(f"  Skipped     : {counters['skipped_cash']} no-cash | {counters['skipped_holding']} already-holding")

    # Monthly table
    nav_df["month"] = nav_df["date"].dt.to_period("M")
    print(f"\n  {'Month':<9} {'EndNAV(L)':>10} {'MonthPnL(L)':>12} {'AvgPos':>7}")
    m_prev = INIT_CAP
    for m, g in nav_df.groupby("month"):
        end = g["nav"].iloc[-1]
        print(f"  {str(m):<9} {end/1e5:>10.1f} {(end-m_prev)/1e5:>12.2f} {g['n_pos'].mean():>7.1f}")
        m_prev = end

    nav_df.to_csv(os.path.join(OUT, f"chartlink_nav_{name}.csv"), index=False)
    tl.to_csv(os.path.join(OUT, f"chartlink_trades_{name}.csv"), index=False)

    return {"name": name, "nav_df": nav_df, "final_nav": final_nav, "cagr": cagr,
            "max_dd": max_dd, "sharpe": sharpe, "sortino": sortino, "win_rate": win_rate,
            "costs": costs_paid, "slip": slip_paid, "counters": counters, "trades": tl}

print("\n" + "=" * 70)
print("STEP 4: Running simulations")
print("=" * 70)
results = [run_sim(c["sl"], c["hold"], c["name"]) for c in CONFIGS]

# ---------------- 5. NIFTY benchmark ----------------
print("\n" + "=" * 70)
print("BENCHMARK: NIFTY 50 (same window)")
print("=" * 70)
try:
    nifty = pd.read_parquet(os.path.join(BASE, "index_daily", "nifty50.parquet"))
    tcol = "timestamp" if "timestamp" in nifty.columns else "date"
    nifty["date"] = pd.to_datetime(nifty[tcol])
    if nifty["date"].dt.tz is not None:
        nifty["date"] = nifty["date"].dt.tz_localize(None)
    nifty = nifty[(nifty["date"] >= calendar[0]) & (nifty["date"] <= calendar[-1])].sort_values("date")
    if len(nifty) > 2:
        ns, ne = nifty["close"].iloc[0], nifty["close"].iloc[-1]
        print(f"  NIFTY 50: {ns:.0f} -> {ne:.0f} | total {((ne/ns)-1)*100:+.2f}%")
except Exception as e:
    print(f"  benchmark failed: {e}")

# ---------------- 6. Chart ----------------
fig, axes = plt.subplots(2, 1, figsize=(15, 9), gridspec_kw={"height_ratios": [3, 1]})
colors = ["#2962ff", "#e91e63", "#2e7d32"]
for i, r in enumerate(results):
    nd = r["nav_df"]
    axes[0].plot(nd["date"], nd["nav"] / 1e5,
                 label=f"{r['name']}: {(r['final_nav']/INIT_CAP-1)*100:+.1f}%, DD {r['max_dd']*100:.1f}%",
                 color=colors[i], lw=1.4)
    peak = nd["nav"].cummax()
    axes[1].fill_between(nd["date"], (nd["nav"]/peak - 1) * 100, 0, alpha=0.3, color=colors[i])
axes[0].axhline(INIT_CAP/1e5, color="#787b86", lw=0.8, ls="--")
axes[0].set_ylabel("NAV (Rs. Lakh)")
axes[0].set_title("Chartlink signals — realistic Rs.1Cr portfolio (daily MTM, full costs, 10% entries, 20%->15% trim)")
axes[0].legend(); axes[0].grid(alpha=0.3)
axes[1].set_ylabel("Drawdown %"); axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "chartlink_realistic_nav.png"), dpi=120)
print(f"\nSaved: chartlink_realistic_nav.png, chartlink_nav_*.csv, chartlink_trades_*.csv")
