"""
FULL 5-YEAR CHARTLINK BACKTEST — actual screener export (1,536 signals, Jun 2021 - Jul 2026)
Config: 5% position size, SL = entry - 1.5xATR14, trail = close < EMA20 (day 2+), max 30d hold.
Baseline FIX10/no-trail at 5% also run for reference. Realistic engine: daily MTM, full costs,
no leverage, drift trim 20%->15%.
"""
import os, warnings, time
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass

SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (2).csv"
BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
PRICE_CACHE = os.path.join(OUT, "chartlink_prices_full5yr.parquet")

INIT_CAP = 10_000_000
ENTRY_PCT = 0.05
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
MIN_TICKET = 25_000; STALE_LIMIT = 10; MAX_HOLD = 30

# ---------------- 1. Signals ----------------
sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig.sort_values("Date").reset_index(drop=True)
symbols = sorted(sig["Symbol"].unique())
print(f"Signals: {len(sig)}, symbols: {len(symbols)}, {sig['Date'].min().date()} -> {sig['Date'].max().date()}")

# ---------------- 2. Price panel ----------------
if os.path.exists(PRICE_CACHE):
    panel = pd.read_parquet(PRICE_CACHE)
    print(f"Loaded cached panel: {len(panel):,} rows, {panel['symbol'].nunique()} symbols")
else:
    import yfinance as yf
    # reuse the 199-symbol panel where possible (only covers Oct2025+; still need full range) -> just download all fresh
    rows_all = []; failed = []
    for i, s in enumerate(symbols):
        got = False
        for tk in [f"{s}.NS", f"{s}.BO"]:
            for attempt in range(2):
                try:
                    df = yf.download(tk, start="2021-04-01", end="2026-07-12",
                                     progress=False, timeout=25, auto_adjust=False)
                    if len(df) >= 60:
                        df = df.reset_index()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                        sub = pd.DataFrame({
                            "date": pd.to_datetime(df["Date"]).dt.tz_localize(None),
                            "open": df["Open"].astype(float), "high": df["High"].astype(float),
                            "low": df["Low"].astype(float), "close": df["Close"].astype(float),
                            "volume": df["Volume"].fillna(0).astype(np.int64)})
                        sub["symbol"] = s
                        rows_all.append(sub)
                        got = True
                        break
                    break
                except Exception:
                    time.sleep(2)
            if got: break
        if not got: failed.append(s)
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(symbols)} ({len(failed)} failed)")
    print(f"yfinance done: {len(symbols)-len(failed)}/{len(symbols)} OK; failed: {failed}")
    panel = pd.concat(rows_all, ignore_index=True)
    panel = panel[panel["close"] > 0]
    panel = panel.sort_values(["symbol","date"]).drop_duplicates(["symbol","date"]).reset_index(drop=True)
    panel.to_parquet(PRICE_CACHE)
    print(f"Panel cached: {len(panel):,} rows, {panel['symbol'].nunique()} symbols")

# ---------------- 3. Indicators + lookups ----------------
print("Indicators...")
ind = []
for s, g in panel.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    hi, lo, cl = g["high"], g["low"], g["close"]
    pc = cl.shift(1)
    tr = pd.concat([hi-lo, (hi-pc).abs(), (lo-pc).abs()], axis=1).max(axis=1)
    g["atr14"] = tr.ewm(alpha=1/14, min_periods=5).mean()
    g["ema20"] = cl.ewm(span=20, min_periods=5).mean()
    ind.append(g)
panel_i = pd.concat(ind, ignore_index=True)

sym_bars = {}
for s, g in panel_i.groupby("symbol"):
    sym_bars[s] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"], g["atr14"], g["ema20"])))

dc = panel_i.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(panel_i["date"].unique())
            if pd.Timestamp(d) >= pd.Timestamp("2021-06-25") and dc.get(d, 0) >= 50]
cal_set = set(calendar)
print(f"{len(sym_bars)} symbols, {len(calendar)} trading days ({calendar[0].date()} -> {calendar[-1].date()})")

entries_by_day = {}
unmatched = 0
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    if s not in sym_bars:
        unmatched += 1; continue
    sym_dates = sym_bars[s]
    later = None
    d = sd + pd.Timedelta(days=1)
    for _ in range(7):
        if d in cal_set and d in sym_dates:
            later = d; break
        d += pd.Timedelta(days=1)
    if later is None:
        unmatched += 1; continue
    entries_by_day.setdefault(later, []).append((s, sym_bars[s].get(pd.Timestamp(sd))))
print(f"Mapped {len(sig)-unmatched}/{len(sig)} signals ({unmatched} unmatched)")

# ---------------- 4. Sim ----------------
def run(sl_mode, trail, name):
    cash = float(INIT_CAP); positions = {}; nav_hist = []; trade_log = []
    fees_tot = 0.0; skipped = 0
    def sell(s, px, d, reason):
        nonlocal cash, fees_tot
        p = positions[s]
        gross = p["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees; fees_tot += fees
        pnl = (px-p["entry_px"])*p["shares"] - fees - p["bf"]
        trade_log.append({"exit_date": d, "symbol": s, "reason": reason,
                          "pnl": round(pnl), "hold": p["days_held"],
                          "entry_date": p["ed"]})
        del positions[s]
    prev_nav = float(INIT_CAP)
    for d in calendar:
        for s, sig_bar in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or not (bar[0] > 0): continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(ENTRY_PCT*prev_nav, cash)
            if budget < MIN_TICKET:
                skipped += 1; continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0:
                skipped += 1; continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees; fees_tot += fees
            ref = sig_bar if sig_bar is not None and sig_bar[4]==sig_bar[4] else bar
            if sl_mode == "ATR15":
                sl_px = buy_px - 1.5*ref[4] if ref[4]==ref[4] else buy_px*0.90
            else:
                sl_px = buy_px*0.90
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_px,
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees,"ed":d}
        for s in list(positions.keys()):
            p = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"] += 1
                if p["stale"] > STALE_LIMIT:
                    sell(s, p["last_close"]*(1-SLIP), d, "STALE")
                continue
            p["stale"] = 0
            o,h,l,c,atr,ema = bar
            if l <= p["sl_px"]:
                sell(s, min(o,p["sl_px"])*(1-SLIP), d, "SL"); continue
            p["last_close"] = c; p["days_held"] += 1
            if trail == "EMA20" and p["days_held"] >= 2 and ema==ema and c < ema:
                sell(s, c*(1-SLIP), d, "TRAIL"); continue
            if p["days_held"] >= MAX_HOLD:
                sell(s, c*(1-SLIP), d, "TIME")
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash + pos_val
        for s in list(positions.keys()):
            p = positions[s]; val = p["shares"]*p["last_close"]
            if val > DRIFT_MAX*nav:
                excess = int((val - DRIFT_TRIM_TO*nav)/p["last_close"])
                if excess > 0:
                    g2 = excess*p["last_close"]*(1-SLIP); f2 = g2*SELL_COST
                    cash += g2 - f2; fees_tot += f2
                    p["shares"] -= excess
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash + pos_val
        nav_hist.append({"date": d, "nav": round(nav), "cash": round(cash),
                         "n_pos": len(positions), "day_pnl": round(nav-prev_nav)})
        prev_nav = nav
    for s in list(positions.keys()):
        sell(s, positions[s]["last_close"]*(1-SLIP), calendar[-1], "FINAL")

    nav_df = pd.DataFrame(nav_hist)
    tl = pd.DataFrame(trade_log)
    final = cash
    total_ret = final/INIT_CAP - 1
    days = (nav_df["date"].iloc[-1]-nav_df["date"].iloc[0]).days
    cagr = (final/INIT_CAP)**(365.25/days)-1
    peak = nav_df["nav"].cummax()
    dd = (nav_df["nav"]/peak-1)
    max_dd = dd.min()
    rets = nav_df["nav"].pct_change().dropna()
    sharpe = rets.mean()/rets.std()*np.sqrt(252) if rets.std()>0 else 0
    w = tl[tl["pnl"]>0]; lz = tl[tl["pnl"]<=0]
    print(f"\n===== {name} =====")
    print(f"Final NAV : Rs.{final:,.0f} ({total_ret*100:+.1f}%) | CAGR {cagr*100:.2f}%")
    print(f"MaxDD {max_dd*100:.2f}% | Sharpe {sharpe:.2f} | Calmar {abs(cagr/max_dd):.2f}")
    print(f"Trades {len(tl)} | win {len(w)/len(tl)*100:.1f}% | avg win {w['pnl'].mean():,.0f} | "
          f"avg loss {lz['pnl'].mean():,.0f} | PF {w['pnl'].sum()/abs(lz['pnl'].sum()):.2f}")
    print(f"Skipped {skipped} | fees Rs.{fees_tot:,.0f} | avg pos {nav_df['n_pos'].mean():.1f} (max {nav_df['n_pos'].max()})")
    exits = tl.groupby("reason")["pnl"].agg(["count","sum"])
    print(exits.to_string())
    nav_df["year"] = nav_df["date"].dt.year
    print(f"{'Year':<6} {'End NAV(L)':>11} {'Ret%':>7} {'MaxDD%':>7} {'AvgPos':>7}")
    for yr, g in nav_df.groupby("year"):
        st = g["nav"].iloc[0]; en = g["nav"].iloc[-1]
        yp = g["nav"].cummax(); ydd = (g["nav"]/yp-1).min()
        print(f"{yr:<6} {en/1e5:>11.1f} {(en/st-1)*100:>6.1f}% {ydd*100:>6.1f}% {g['n_pos'].mean():>7.1f}")
    nav_df.to_csv(os.path.join(OUT, f"full5yr_nav_{name}.csv"), index=False)
    tl.to_csv(os.path.join(OUT, f"full5yr_trades_{name}.csv"), index=False)
    return nav_df, final, cagr, max_dd

r1 = run("ATR15", "EMA20", "ATR15_EMA20_5pct")
r2 = run("FIX10", "NONE", "FIX10_NONE_5pct")

# NIFTY benchmark
try:
    nifty = pd.read_parquet(os.path.join(BASE, "index_daily", "nifty50.parquet"))
    tcol = "timestamp" if "timestamp" in nifty.columns else "date"
    nifty["date"] = pd.to_datetime(nifty[tcol])
    if nifty["date"].dt.tz is not None:
        nifty["date"] = nifty["date"].dt.tz_localize(None)
    nifty = nifty[(nifty["date"] >= calendar[0]) & (nifty["date"] <= calendar[-1])].sort_values("date")
    ns, ne = nifty["close"].iloc[0], nifty["close"].iloc[-1]
    nd_days = (nifty["date"].iloc[-1]-nifty["date"].iloc[0]).days
    ncagr = (ne/ns)**(365.25/nd_days)-1
    npk = nifty["close"].cummax(); ndd = (nifty["close"]/npk-1).min()
    print(f"\nNIFTY 50: {ns:.0f} -> {ne:.0f} | total {(ne/ns-1)*100:+.1f}% | CAGR {ncagr*100:.2f}% | MaxDD {ndd*100:.1f}%")
except Exception as e:
    print("bench fail", e)

# chart
fig, axes = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios":[3,1]})
for (nd, fin, cg, mdd), col, lbl in [(r1, "#1D5FBF", "ATR1.5+EMA20 5%"), (r2, "#5F6E7C", "FIX10 no-trail 5%")]:
    axes[0].plot(nd["date"], nd["nav"]/1e5, color=col, lw=1.3,
                 label=f"{lbl}: CAGR {cg*100:.1f}%, DD {mdd*100:.1f}%")
    pk = nd["nav"].cummax()
    axes[1].fill_between(nd["date"], (nd["nav"]/pk-1)*100, 0, alpha=0.3, color=col)
axes[0].axhline(100, color="#999", lw=.7, ls="--")
axes[0].set_ylabel("NAV (Rs. L)"); axes[0].legend(); axes[0].grid(alpha=.3)
axes[0].set_title("Full 5-yr Chartlink export (1,536 signals) — Rs.1Cr, 5% entries, all costs")
axes[1].set_ylabel("DD %"); axes[1].grid(alpha=.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "full5yr_nav.png"), dpi=120)
print("\nSaved: full5yr_nav.png, full5yr_nav_*.csv, full5yr_trades_*.csv")
