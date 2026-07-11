"""
FULL 5-YEAR EXIT-RULE GRID — 49 combos on the complete Chartlink export
(1,536 signals, Jun 2021 - Jul 2026). Rs.1Cr, 5% entries, all costs, no leverage.

SL modes (intraday vs low): FIX5, FIX10, FIX15, ATR1, ATR15, ATR2, SWING(10-bar low -1%)
Trails (close-based, day 2+): NONE, DMA20, KCU15, KCU10, KCMID, KCL10, KCL15
Max hold 30 trading days everywhere.
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (2).csv"
INIT_CAP = 10_000_000; ENTRY_PCT = 0.05
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
MIN_TICKET = 25_000; STALE_LIMIT = 10; MAX_HOLD = 30

sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig.sort_values("Date").reset_index(drop=True)
panel = pd.read_parquet(os.path.join(OUT, "chartlink_prices_full5yr.parquet"))
panel["date"] = pd.to_datetime(panel["date"])
print(f"Panel {len(panel):,} rows / {panel['symbol'].nunique()} syms; signals {len(sig)}")

print("Indicators...")
ind = []
for s, g in panel.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    hi, lo, cl = g["high"], g["low"], g["close"]
    pc = cl.shift(1)
    tr = pd.concat([hi-lo, (hi-pc).abs(), (lo-pc).abs()], axis=1).max(axis=1)
    g["atr14"] = tr.ewm(alpha=1/14, min_periods=5).mean()
    g["sma20"] = cl.rolling(20, min_periods=5).mean()
    g["ema20"] = cl.ewm(span=20, min_periods=5).mean()
    g["swing10"] = lo.rolling(10, min_periods=3).min()
    ind.append(g)
panel_i = pd.concat(ind, ignore_index=True)

sym_bars = {}
for s, g in panel_i.groupby("symbol"):
    sym_bars[s] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"],
            g["atr14"], g["sma20"], g["ema20"], g["swing10"])))

dc = panel_i.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(panel_i["date"].unique())
            if pd.Timestamp(d) >= pd.Timestamp("2021-06-25") and dc.get(d, 0) >= 50]
cal_set = set(calendar)
print(f"{len(calendar)} trading days")

entries_by_day = {}
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    if s not in sym_bars: continue
    d = sd + pd.Timedelta(days=1); later = None
    for _ in range(7):
        if d in cal_set and d in sym_bars[s]:
            later = d; break
        d += pd.Timedelta(days=1)
    if later is None: continue
    entries_by_day.setdefault(later, []).append((s, sym_bars[s].get(pd.Timestamp(sd))))
print(f"Mapped {sum(len(v) for v in entries_by_day.values())}/{len(sig)}")

def initial_sl(mode, entry_px, sig_bar, entry_bar):
    ref = sig_bar if sig_bar is not None and sig_bar[4]==sig_bar[4] else entry_bar
    atr = ref[4]; swing = ref[7]
    if mode == "FIX5":  return entry_px*0.95
    if mode == "FIX10": return entry_px*0.90
    if mode == "FIX15": return entry_px*0.85
    if mode == "ATR1":  return entry_px-1.0*atr if atr==atr else entry_px*0.90
    if mode == "ATR15": return entry_px-1.5*atr if atr==atr else entry_px*0.90
    if mode == "ATR2":  return entry_px-2.0*atr if atr==atr else entry_px*0.90
    if mode == "SWING":
        return swing*0.99 if (swing==swing and swing < entry_px) else entry_px*0.90
    return entry_px*0.90

def trail_level(mode, bar):
    o,h,l,c,atr,sma,ema,sw = bar
    if mode == "NONE": return None
    if mode == "DMA20": return sma if sma==sma else None
    if atr!=atr or ema!=ema: return None
    if mode == "KCU15": return ema+1.5*atr
    if mode == "KCU10": return ema+1.0*atr
    if mode == "KCMID": return ema
    if mode == "KCL10": return ema-1.0*atr
    if mode == "KCL15": return ema-1.5*atr
    return None

def run_sim(sl_mode, trail_mode):
    cash = float(INIT_CAP); positions = {}; nav_hist = []
    wins=losses=0; win_pnl=loss_pnl=0.0; n_entries=0; hold_sum=0
    exits = {"SL":0,"TRAIL":0,"TIME":0,"STALE":0,"FINAL":0}
    yearly_pnl = {}
    def sell(s, px, d, reason):
        nonlocal cash, wins, losses, win_pnl, loss_pnl, hold_sum
        p = positions[s]
        gross = p["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees
        pnl = (px-p["entry_px"])*p["shares"] - fees - p["bf"]
        if pnl>0: wins+=1; win_pnl+=pnl
        else: losses+=1; loss_pnl+=abs(pnl)
        hold_sum += p["days_held"]
        yr = d.year
        yearly_pnl[yr] = yearly_pnl.get(yr, 0) + pnl
        exits[reason]+=1
        del positions[s]
    prev_nav = float(INIT_CAP)
    for d in calendar:
        for s, sig_bar in entries_by_day.get(d, []):
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
            positions[s] = {"shares":shares,"entry_px":buy_px,
                            "sl_px":initial_sl(sl_mode, buy_px, sig_bar, bar),
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees}
            n_entries+=1
        for s in list(positions.keys()):
            p = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"]+=1
                if p["stale"]>STALE_LIMIT: sell(s, p["last_close"]*(1-SLIP), d, "STALE")
                continue
            p["stale"]=0
            o,h,l,c = bar[0],bar[1],bar[2],bar[3]
            if l <= p["sl_px"]:
                sell(s, min(o,p["sl_px"])*(1-SLIP), d, "SL"); continue
            p["last_close"]=c; p["days_held"]+=1
            if p["days_held"]>=2:
                tl_ = trail_level(trail_mode, bar)
                if tl_ is not None and c < tl_:
                    sell(s, c*(1-SLIP), d, "TRAIL"); continue
            if p["days_held"]>=MAX_HOLD:
                sell(s, c*(1-SLIP), d, "TIME")
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash+pos_val
        for s in list(positions.keys()):
            p = positions[s]; val = p["shares"]*p["last_close"]
            if val > DRIFT_MAX*nav:
                excess = int((val-DRIFT_TRIM_TO*nav)/p["last_close"])
                if excess > 0:
                    g2 = excess*p["last_close"]*(1-SLIP)
                    cash += g2*(1-SELL_COST)
                    p["shares"] -= excess
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash+pos_val
        nav_hist.append(nav)
        prev_nav = nav
    for s in list(positions.keys()):
        sell(s, positions[s]["last_close"]*(1-SLIP), calendar[-1], "FINAL")
    nav_arr = np.array(nav_hist+[cash])
    final = cash
    total_ret = final/INIT_CAP-1
    days = (calendar[-1]-calendar[0]).days
    cagr = (final/INIT_CAP)**(365.25/days)-1
    peak = np.maximum.accumulate(nav_arr)
    max_dd = ((nav_arr/peak)-1).min()
    rets = np.diff(nav_arr)/nav_arr[:-1]
    sharpe = rets.mean()/rets.std()*np.sqrt(252) if rets.std()>0 else 0
    n_ex = wins+losses
    return {
        "sl": sl_mode, "trail": trail_mode,
        "ret_pct": round(total_ret*100, 1), "cagr_pct": round(cagr*100, 2),
        "max_dd_pct": round(max_dd*100, 1), "sharpe": round(sharpe, 2),
        "calmar": round(abs(cagr/max_dd), 2) if max_dd<0 else 99,
        "win_pct": round(wins/n_ex*100, 1) if n_ex else 0,
        "pf": round(win_pnl/loss_pnl, 2) if loss_pnl>0 else 99,
        "entries": n_entries,
        "sl_x": exits["SL"], "trail_x": exits["TRAIL"], "time_x": exits["TIME"],
        "avg_hold": round(hold_sum/n_ex, 1) if n_ex else 0,
        "pnl_2023L": round(yearly_pnl.get(2023, 0)/1e5, 1),
        "pnl_2024L": round(yearly_pnl.get(2024, 0)/1e5, 1),
        "pnl_2025L": round(yearly_pnl.get(2025, 0)/1e5, 1),
        "pnl_2026L": round(yearly_pnl.get(2026, 0)/1e5, 1),
    }

SLS = ["FIX5", "FIX10", "FIX15", "ATR1", "ATR15", "ATR2", "SWING"]
TRAILS = ["NONE", "DMA20", "KCU15", "KCU10", "KCMID", "KCL10", "KCL15"]
print(f"\nRunning {len(SLS)*len(TRAILS)} combos on 5yr data...")
rows = []
for tm in TRAILS:
    for sm in SLS:
        r = run_sim(sm, tm)
        rows.append(r)
        print(f"  {sm:<6} x {tm:<6}: ret {r['ret_pct']:>7.1f}%  CAGR {r['cagr_pct']:>6.2f}%  DD {r['max_dd_pct']:>6.1f}%  "
              f"Sharpe {r['sharpe']:>5.2f}  win {r['win_pct']:>5.1f}%  PF {r['pf']:>5.2f}  n {r['entries']:>4}")

grid = pd.DataFrame(rows).sort_values("cagr_pct", ascending=False).reset_index(drop=True)
grid.to_csv(os.path.join(OUT, "full5yr_exit_grid.csv"), index=False)
print("\nTOP 15 BY CAGR")
print(grid.head(15).to_string(index=False))
print("\nBOTTOM 8")
print(grid.tail(8).to_string(index=False))
print("\nNIFTY 50 same window: CAGR 8.84%, MaxDD -17.2%")
print("Saved: full5yr_exit_grid.csv")
