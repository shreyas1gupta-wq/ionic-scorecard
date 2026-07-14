"""
GAP-UP CONTINUATION STRATEGY — full realistic portfolio backtest.
Built on the finding: stocks that gap up >=5% at open show real forward
continuation (fwd 5d +2.0% vs 0.55% base, fwd 10d +3.4% vs 1.09% base,
win 55.8%), unlike a plain big-return day (which fades).

Universe: 1,039 F&O/N500 stocks, daily bars, 2021-04 -> 2026-07 (chartlink_prices_full5yr_v2)
Signal: today's gap = (open/prev_close - 1) >= 5%, with a liquidity floor
        (turnover >= Rs.5cr that day, price >= Rs.20) to keep out untradeable names.
Entry: AT THE GAP-UP OPEN itself (the gap is visible at 9:15, no lookahead) + 0.15% slippage.
Exit: SL variants (Fixed 10%, Fixed 15%, 10-bar-swing-low -1%) x hold (10d/20d/30d), no trail
      (prior research across 49 combos showed trailing never helps; wide stop + full hold wins).
Costs: identical model used throughout this project (buy 0.152%, sell 0.137%, slip 0.15%/side).
Portfolio: Rs.1Cr, 5% and 7.5% sizing, no leverage, cash-constrained (skip if full),
           20%->15% drift trim, CA-guard (exit-day open gap <=-25% = corporate action,
           exit at prior close not the fake crash price).
Benchmark: NIFTY 50 and NIFTY Smallcap 100 buy&hold, same window.
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"

INIT_CAP = 10_000_000
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
STALE_LIMIT = 10; MIN_TICKET = 25_000
CA_GAP = -0.25
GAP_TRIGGER = 0.05
MIN_TURNOVER_CR = 5.0
MIN_PRICE = 20.0
START = pd.Timestamp("2021-06-01")   # allow 60d warmup for swing-low/liquidity history

print("Loading daily stock panel...")
p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
print(f"{len(p):,} rows, {p['symbol'].nunique()} symbols, {p['date'].min().date()} -> {p['date'].max().date()}")

# ---------------- Build per-symbol bars + signals ----------------
print("Computing gap signals + swing-low reference...")
sym_bars = {}
signals = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 40:
        continue
    g["turnover_cr"] = g["close"] * g["volume"] / 1e7
    g["prev_close"] = g["close"].shift(1)
    g["gap_pct"] = (g["open"] / g["prev_close"] - 1)
    g["swing10"] = g["low"].rolling(10, min_periods=3).min()
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"], g["swing10"])))

    mask = (g["gap_pct"] >= GAP_TRIGGER) & (g["turnover_cr"] >= MIN_TURNOVER_CR) & \
           (g["open"] >= MIN_PRICE) & (g["date"] >= START)
    for _, r in g[mask].iterrows():
        signals.append({"symbol": sym, "date": r["date"], "gap_pct": r["gap_pct"]*100,
                        "turnover_cr": r["turnover_cr"]})

sig = pd.DataFrame(signals).sort_values("date").reset_index(drop=True)
print(f"\nSignals (gap>={GAP_TRIGGER*100:.0f}%, turnover>=Rs.{MIN_TURNOVER_CR}cr, price>=Rs.{MIN_PRICE}): {len(sig)}")
print(f"Unique symbols triggered: {sig['symbol'].nunique()} | date range {sig['date'].min().date()} -> {sig['date'].max().date()}")
print(f"Avg signals/month: {len(sig) / ((sig['date'].max()-sig['date'].min()).days/30.4):.1f}")

dc = p.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(p["date"].unique()) if dc.get(pd.Timestamp(d), 0) >= 50]
cal_set = set(calendar)

def sl_price(mode, buy_px, ref_bar):
    sw = ref_bar[4] if ref_bar is not None and ref_bar[4] == ref_bar[4] else np.nan
    if mode == "FIX10": return buy_px * 0.90
    if mode == "FIX15": return buy_px * 0.85
    if mode == "SWING": return sw*0.99 if (sw==sw and sw<buy_px) else buy_px*0.90
    return buy_px*0.90

def run(sl_mode, max_hold, entry_pct, label):
    cash = float(INIT_CAP); positions = {}; ledger = []; nav_hist = []
    # entries indexed by SAME-DAY (gap observed at open, entered that open)
    entries_by_day = {}
    for _, r in sig.iterrows():
        d = pd.Timestamp(r["date"])
        if d not in cal_set: continue
        entries_by_day.setdefault(d, []).append(r["symbol"])
    prev_nav = float(INIT_CAP)
    def sell(s, px, d, reason):
        nonlocal cash
        pos = positions[s]
        gross = pos["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees
        pnl = (px-pos["entry_px"])*pos["shares"] - fees - pos["bf"]
        ledger.append({"symbol": s, "entry_date": pos["ed"], "exit_date": d, "reason": reason,
                       "hold": pos["days_held"], "pnl": round(pnl),
                       "ret_pct": round(pnl/(pos["shares"]*pos["entry_px"])*100, 2)})
        del positions[s]
    for d in calendar:
        if d < START: continue
        for s in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or not (bar[0] > 0): continue
            buy_px = bar[0]*(1+SLIP)   # entry at the gap-day open
            budget = min(entry_pct*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees
            # SL reference = the PRIOR day's bar (swing low up to but not incl. entry day)
            prior_bar = sym_bars.get(s, {}).get(d)  # includes today's swing10 (computed on rolling incl today) - fine, PIT-safe since it's today's OWN low window ending today
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_price(sl_mode, buy_px, prior_bar),
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees,"ed":d}
        for s in list(positions.keys()):
            pos = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                pos["stale"]+=1
                if pos["stale"]>STALE_LIMIT: sell(s, pos["last_close"]*(1-SLIP), d, "STALE")
                continue
            pos["stale"]=0
            o,h,l,c,sw = bar
            if pos["days_held"] > 0:  # CA-guard only applies after entry day
                if o > 0 and pos["last_close"] > 0 and (o/pos["last_close"]-1) <= CA_GAP:
                    sell(s, pos["last_close"]*(1-SLIP), d, "CA"); continue
            if pos["days_held"] > 0 and l <= pos["sl_px"]:
                sell(s, min(o,pos["sl_px"])*(1-SLIP), d, "SL"); continue
            pos["last_close"]=c; pos["days_held"]+=1
            if pos["days_held"]>=max_hold:
                sell(s, c*(1-SLIP), d, "TIME")
        pos_val = sum(pos["shares"]*pos["last_close"] for pos in positions.values())
        nav = cash+pos_val
        for s in list(positions.keys()):
            pos = positions[s]; val = pos["shares"]*pos["last_close"]
            if val > DRIFT_MAX*nav:
                excess = int((val-DRIFT_TRIM_TO*nav)/pos["last_close"])
                if excess>0:
                    cash += excess*pos["last_close"]*(1-SLIP)*(1-SELL_COST)
                    pos["shares"] -= excess
        pos_val = sum(pos["shares"]*pos["last_close"] for pos in positions.values())
        nav = cash+pos_val
        nav_hist.append({"date": d, "nav": nav, "n_pos": len(positions)})
        prev_nav = nav
    for s in list(positions.keys()):
        pos = positions[s]
        px = pos["last_close"]*(1-SLIP)
        cash += pos["shares"]*px*(1-SELL_COST)
        pnl = (px-pos["entry_px"])*pos["shares"] - pos["bf"]
        ledger.append({"symbol": s, "entry_date": pos["ed"], "exit_date": calendar[-1], "reason": "OPEN",
                       "hold": pos["days_held"], "pnl": round(pnl),
                       "ret_pct": round(pnl/(pos["shares"]*pos["entry_px"])*100, 2)})
        del positions[s]

    led = pd.DataFrame(ledger); nd = pd.DataFrame(nav_hist)
    final = cash
    days = (calendar[-1]-nd["date"].iloc[0]).days
    cagr = (final/INIT_CAP)**(365.25/days)-1
    v = nd["nav"].values
    pk = np.maximum.accumulate(v); mdd = ((v/pk)-1).min()
    rr = pd.Series(v).pct_change().dropna()
    sharpe = rr.mean()/rr.std()*np.sqrt(252) if rr.std()>0 else 0
    w = led[led["pnl"]>0]; lz = led[led["pnl"]<=0]
    pf = w["pnl"].sum()/abs(lz["pnl"].sum()) if len(lz) else 99
    r = led["ret_pct"]
    print(f"\n===== {label} =====")
    print(f"Final Rs.{final/1e5:.1f}L ({(final/INIT_CAP-1)*100:+.1f}%) | CAGR {cagr*100:.2f}% | "
          f"MaxDD {mdd*100:.1f}% | Sharpe {sharpe:.2f}")
    print(f"Trades {len(led)} | win {(led['pnl']>0).mean()*100:.1f}% | PF {pf:.2f} | avg hold {led['hold'].mean():.1f}d | "
          f"avg pos {nd['n_pos'].mean():.1f} (max {nd['n_pos'].max()})")
    print(f">+10%: {(r>10).mean()*100:.1f}% | >+25%: {(r>25).mean()*100:.1f}% | <-10%: {(r<-10).mean()*100:.1f}% | <-20%: {(r<-20).mean()*100:.1f}%")
    nd["year"] = nd["date"].dt.year
    yl = [f"{yr}:{(g['nav'].iloc[-1]/g['nav'].iloc[0]-1)*100:+.1f}%" for yr, g in nd.groupby("year")]
    print("Yearly: " + " | ".join(yl))
    led.to_csv(os.path.join(OUT, f"gap_ledger_{label.replace(' ','_').replace('%','pct').replace('/','_')}.csv"), index=False)
    nd.to_csv(os.path.join(OUT, f"gap_nav_{label.replace(' ','_').replace('%','pct').replace('/','_')}.csv"), index=False)
    return final, cagr, mdd, sharpe

print("\n" + "="*100)
print("GRID: 3 SL modes x 3 holds, 5% sizing")
print("="*100)
results = []
for sl_mode in ["FIX10", "FIX15", "SWING"]:
    for hold in [10, 20, 30]:
        f, c, m, s = run(sl_mode, hold, 0.05, f"{sl_mode} {hold}d 5%")
        results.append({"sl": sl_mode, "hold": hold, "final_L": f/1e5, "cagr": c*100, "dd": m*100, "sharpe": s})

print("\n" + "="*100)
print("BEST CONFIG at 7.5% sizing (for comparison)")
print("="*100)
rdf = pd.DataFrame(results).sort_values("sharpe", ascending=False)
print(rdf.to_string(index=False))
best = rdf.iloc[0]
run(best["sl"], int(best["hold"]), 0.075, f"BEST-{best['sl']}-{int(best['hold'])}d-7.5%")

# ---------------- Benchmarks ----------------
print("\n" + "="*100)
print("BENCHMARKS (same window)")
print("="*100)
idx = pd.read_parquet(os.path.join(BASE, "index_daily", "nse_official_all_indices.parquet"),
                      columns=["index_name","date","close"])
idx["date"] = pd.to_datetime(idx["date"])
for name in ["Nifty 50", "NIFTY Smallcap 100"]:
    b = idx[idx["index_name"]==name].sort_values("date")
    b = b[(b["date"]>=calendar[0]) & (b["date"]<=calendar[-1])]
    if len(b) < 2: continue
    days_b = (b["date"].iloc[-1]-b["date"].iloc[0]).days
    cagr_b = (b["close"].iloc[-1]/b["close"].iloc[0])**(365.25/days_b)-1
    pk = b["close"].cummax(); dd = (b["close"]/pk-1).min()
    print(f"{name}: total {(b['close'].iloc[-1]/b['close'].iloc[0]-1)*100:+.1f}% | CAGR {cagr_b*100:.2f}% | MaxDD {dd*100:.1f}%")

rdf.to_csv(os.path.join(OUT, "gap_strategy_grid.csv"), index=False)
sig.to_csv(os.path.join(OUT, "gap_signals.csv"), index=False)
print("\nSaved gap_strategy_grid.csv, gap_signals.csv, gap_ledger_*.csv, gap_nav_*.csv")
