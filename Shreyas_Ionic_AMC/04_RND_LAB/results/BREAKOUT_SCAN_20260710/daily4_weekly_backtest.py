"""
NEW EXPORTS BACKTEST
 A) Daily D_2026_4 (2,111 signals): champion spec — next-day-open entry,
    SL = 10-bar swing low -1% (hard/intraday, gap-down at open), no trail,
    30-trading-day close exit, 5% of NAV, Rs.1Cr, all costs. Oct-2022 start.
 B) Weekly W_2026_2 (901 signals, week-start dated): screened over Mon-Fri,
    tradeable only NEXT week -> entry = first trading day of the following week
    at OPEN. SL = 10-bar swing low -1% as of the Friday before entry. No trail.
    Hold variants: 30d and 60d. 5% sizing.
Panel: extends cached 5yr panel with 262 new symbols via yfinance.
"""
import os, warnings, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
D_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_4.csv"
W_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest w_2026_2.csv"
PANEL_V1 = os.path.join(OUT, "chartlink_prices_full5yr.parquet")
PANEL_V2 = os.path.join(OUT, "chartlink_prices_full5yr_v2.parquet")

INIT_CAP = 10_000_000; ENTRY_PCT = 0.05; MIN_TICKET = 25_000
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
STALE_LIMIT = 10
START = pd.Timestamp("2022-10-01")

d4 = pd.read_csv(D_CSV); d4["Date"] = pd.to_datetime(d4["Date"], format="%d-%m-%Y")
w2 = pd.read_csv(W_CSV); w2["Date"] = pd.to_datetime(w2["Date"], format="%d-%m-%Y")

# ---------------- 1. Panel v2 ----------------
if os.path.exists(PANEL_V2):
    panel = pd.read_parquet(PANEL_V2)
    print(f"Loaded panel v2: {len(panel):,} rows, {panel['symbol'].nunique()} syms")
else:
    panel = pd.read_parquet(PANEL_V1)
    have = set(panel["symbol"].unique())
    need = sorted((set(d4["Symbol"]) | set(w2["Symbol"])) - have)
    print(f"Downloading {len(need)} new symbols...")
    import yfinance as yf
    rows_all = []; failed = []
    for i, s in enumerate(need):
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
                        rows_all.append(sub); got = True
                        break
                    break
                except Exception:
                    time.sleep(2)
            if got: break
        if not got: failed.append(s)
        if (i+1) % 50 == 0: print(f"  {i+1}/{len(need)} ({len(failed)} failed)")
    print(f"downloaded {len(need)-len(failed)}/{len(need)}; failed: {failed}")
    if rows_all:
        newp = pd.concat(rows_all, ignore_index=True)
        newp = newp[newp["close"] > 0]
        panel = pd.concat([panel, newp], ignore_index=True)
        panel = panel.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    panel.to_parquet(PANEL_V2)
    print(f"panel v2 cached: {len(panel):,} rows, {panel['symbol'].nunique()} syms")

ind = []
for s, g in panel.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    g["swing10"] = g["low"].rolling(10, min_periods=3).min()
    ind.append(g)
panel_i = pd.concat(ind, ignore_index=True)
sym_bars = {}
for s, g in panel_i.groupby("symbol"):
    sym_bars[s] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"], g["swing10"])))
sym_dates = {s: sorted(d.keys()) for s, d in sym_bars.items()}
dc = panel_i.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(panel_i["date"].unique())
            if pd.Timestamp(d) >= START and dc.get(d, 0) >= 50]
cal_set = set(calendar)
print(f"{len(sym_bars)} symbols, {len(calendar)} trading days")

def build_entries_daily(sig):
    out = {}
    n = 0
    for _, r in sig.iterrows():
        s, sd = r["Symbol"], r["Date"]
        if s not in sym_bars: continue
        d = sd + pd.Timedelta(days=1); later = None
        for _ in range(7):
            if d in cal_set and d in sym_bars[s]:
                later = d; break
            d += pd.Timedelta(days=1)
        if later is None: continue
        # swing/SL reference = signal-day bar
        out.setdefault(later, []).append((s, sym_bars[s].get(pd.Timestamp(sd))))
        n += 1
    return out, n

def build_entries_weekly(sig):
    """Entry = first trading day of the FOLLOWING week (>= week_monday+7).
    SL reference bar = last bar strictly before entry day (the prior Friday)."""
    out = {}
    n = 0
    for _, r in sig.iterrows():
        s, sd = r["Symbol"], r["Date"]
        if s not in sym_bars: continue
        wk_mon = sd - pd.Timedelta(days=int(sd.weekday()))
        target = wk_mon + pd.Timedelta(days=7)
        later = None
        d = target
        for _ in range(6):
            if d in cal_set and d in sym_bars[s]:
                later = d; break
            d += pd.Timedelta(days=1)
        if later is None: continue
        prior = [x for x in sym_dates[s] if x < later]
        ref = sym_bars[s][prior[-1]] if prior else None
        out.setdefault(later, []).append((s, ref))
        n += 1
    return out, n

def run(entries_by_day, max_hold, name):
    cash = float(INIT_CAP); positions = {}; nav_hist = []; ledger = []
    prev_nav = float(INIT_CAP)
    def sell(s, px, d, reason):
        nonlocal cash
        p = positions[s]
        gross = p["shares"]*px; fees = gross*SELL_COST
        cash += gross-fees
        pnl = (px-p["entry_px"])*p["shares"] - fees - p["bf"]
        ledger.append({"symbol": s, "entry_date": p["ed"], "exit_date": d, "reason": reason,
                       "hold": p["days_held"], "pnl": round(pnl),
                       "ret_pct": round(pnl/(p["shares"]*p["entry_px"])*100, 2)})
        del positions[s]
    for d in calendar:
        for s, ref in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or not (bar[0] > 0): continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(ENTRY_PCT*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees
            sw = ref[4] if ref is not None and ref[4]==ref[4] else np.nan
            sl_px = sw*0.99 if (sw==sw and sw<buy_px) else buy_px*0.90
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_px,
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees,"ed":d}
        for s in list(positions.keys()):
            p = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"]+=1
                if p["stale"]>STALE_LIMIT: sell(s, p["last_close"]*(1-SLIP), d, "STALE")
                continue
            p["stale"]=0
            o,h,l,c,sw = bar
            if l <= p["sl_px"]:
                sell(s, min(o,p["sl_px"])*(1-SLIP), d, "SL"); continue
            p["last_close"]=c; p["days_held"]+=1
            if p["days_held"]>=max_hold:
                sell(s, c*(1-SLIP), d, "TIME")
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash+pos_val
        for s in list(positions.keys()):
            p = positions[s]; val = p["shares"]*p["last_close"]
            if val > DRIFT_MAX*nav:
                excess = int((val-DRIFT_TRIM_TO*nav)/p["last_close"])
                if excess>0:
                    cash += excess*p["last_close"]*(1-SLIP)*(1-SELL_COST)
                    p["shares"] -= excess
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash+pos_val
        nav_hist.append({"date": d, "nav": round(nav), "n_pos": len(positions)})
        prev_nav = nav
    for s in list(positions.keys()):
        p = positions[s]
        px = p["last_close"]*(1-SLIP)
        cash += p["shares"]*px*(1-SELL_COST)
        pnl = (px-p["entry_px"])*p["shares"] - p["bf"]
        ledger.append({"symbol": s, "entry_date": p["ed"], "exit_date": calendar[-1],
                       "reason": "OPEN", "hold": p["days_held"], "pnl": round(pnl),
                       "ret_pct": round(pnl/(p["shares"]*p["entry_px"])*100, 2)})
        del positions[s]
    led = pd.DataFrame(ledger)
    nd = pd.DataFrame(nav_hist)
    final = cash
    days = (calendar[-1]-calendar[0]).days
    cagr = (final/INIT_CAP)**(365.25/days)-1
    v = nd["nav"].values
    pk = np.maximum.accumulate(v); mdd = ((v/pk)-1).min()
    rr = pd.Series(v).pct_change().dropna()
    sharpe = rr.mean()/rr.std()*np.sqrt(252)
    r = led["ret_pct"]
    w = led[led["pnl"]>0]; lz = led[led["pnl"]<=0]
    pf = w["pnl"].sum()/abs(lz["pnl"].sum()) if len(lz) else 99
    print(f"\n===== {name} =====")
    print(f"Final Rs.{final/1e5:.1f}L ({(final/INIT_CAP-1)*100:+.1f}%) | CAGR {cagr*100:.2f}% | "
          f"DD {mdd*100:.1f}% | Sharpe {sharpe:.2f}")
    print(f"Trades {len(led)} | win {(led['pnl']>0).mean()*100:.1f}% | PF {pf:.2f} | "
          f"avg hold {led['hold'].mean():.1f}d | avg pos {nd['n_pos'].mean():.1f} (max {nd['n_pos'].max()})")
    print(f">+10%: {(r>10).mean()*100:.1f}% | >+25%: {(r>25).mean()*100:.1f}% | <-10%: {(r<-10).mean()*100:.1f}%")
    nd["year"] = nd["date"].dt.year
    yl = []
    for yr, g in nd.groupby("year"):
        st, en = g["nav"].iloc[0], g["nav"].iloc[-1]
        yl.append(f"{yr}: {(en/st-1)*100:+.1f}%")
    print("Yearly NAV: " + " | ".join(yl))
    led.to_csv(os.path.join(OUT, f"ledger_{name}.csv"), index=False)
    nd.to_csv(os.path.join(OUT, f"nav_{name}.csv"), index=False)
    return final, cagr, mdd

# ---------------- A) Daily D4 ----------------
d4s = d4[d4["Date"] >= START]
ed_d, n_d = build_entries_daily(d4s)
print(f"\nDaily D_2026_4: mapped {n_d}/{len(d4s)} signals from {START.date()}")
run(ed_d, 30, "D4_champion")

# ---------------- B) Weekly ----------------
w2s = w2[w2["Date"] >= START]
ew, n_w = build_entries_weekly(w2s)
print(f"\nWeekly W_2026_2: mapped {n_w}/{len(w2s)} signals (entry = next-week first trading day)")
run(ew, 30, "W2_30d")
run(ew, 60, "W2_60d")
