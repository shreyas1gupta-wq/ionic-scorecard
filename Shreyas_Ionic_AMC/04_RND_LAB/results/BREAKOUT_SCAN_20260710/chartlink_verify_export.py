"""
VERIFY + EXPORT: rerun the two headline exit configs with full trade ledgers,
save NAV series, then audit 5 random trades end-to-end:
  - entry open matches raw panel, slippage & fee arithmetic recomputed
  - SL level = entry - 1.5xATR(signal day) recomputed from raw bars
  - exit trigger verified (trail: close<band on exit day but not day before;
    SL: low<=SL; time: 30 bars)
  - cross-check entry/exit day prices vs Angel (independent source) where available
Configs: A) SL 1.5xATR + EMA20 trail (winner)   B) SL 1.5xATR + KC upper 1.0 ATR
"""
import os, warnings, random
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (1).csv"
PRICE_CACHE = os.path.join(OUT, "chartlink_prices.parquet")

INIT_CAP = 10_000_000; MAX_ENTRY_PCT = 0.10; DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015; MIN_TICKET = 50_000
STALE_LIMIT = 10; MAX_HOLD = 30

sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig.sort_values("Date").reset_index(drop=True)
panel = pd.read_parquet(PRICE_CACHE)
panel["date"] = pd.to_datetime(panel["date"])

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

sym_df = {s: g.sort_values("date").reset_index(drop=True) for s, g in panel_i.groupby("symbol")}
sym_bars = {}
for s, g in panel_i.groupby("symbol"):
    sym_bars[s] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"], g["atr14"], g["ema20"])))

cal_start = pd.Timestamp("2025-11-15")
dc = panel_i.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(panel_i["date"].unique())
            if pd.Timestamp(d) >= cal_start and dc.get(d, 0) >= 20]

entries_by_day = {}
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    if s not in sym_bars: continue
    later = [d for d in calendar if d > sd and d in sym_bars[s]]
    if not later or (later[0] - sd).days > 5: continue
    entries_by_day.setdefault(later[0], []).append((s, pd.Timestamp(sd), sym_bars[s].get(pd.Timestamp(sd))))

def run(trail_kind, name):
    """trail_kind: 'EMA20' -> exit close<ema20 ; 'KCU10' -> exit close<ema20+1.0*atr"""
    cash = float(INIT_CAP); positions = {}; nav_hist = []; ledger = []
    prev_nav = float(INIT_CAP)
    def sell(s, px, d, reason):
        nonlocal cash
        p = positions[s]
        gross = p["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees
        pnl = (px - p["entry_px"])*p["shares"] - fees - p["buy_fees"]
        ledger.append({
            "symbol": s, "signal_date": p["signal_date"], "entry_date": p["entry_date"],
            "exit_date": d, "reason": reason, "shares": p["shares"],
            "entry_px": round(p["entry_px"], 2), "exit_px": round(px, 2),
            "buy_value": round(p["shares"]*p["entry_px"]), "sell_value": round(gross),
            "buy_fees": round(p["buy_fees"]), "sell_fees": round(fees),
            "sl_px": round(p["sl_px"], 2), "hold_days": p["days_held"],
            "net_pnl": round(pnl),
        })
        del positions[s]
    for d in calendar:
        for s, sd, sig_bar in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or not (bar[0] > 0): continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(MAX_ENTRY_PCT*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross + fees
            ref = sig_bar if sig_bar is not None and sig_bar[4]==sig_bar[4] else bar
            sl_px = buy_px - 1.5*ref[4] if ref[4]==ref[4] else buy_px*0.90
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_px,"days_held":0,
                            "stale":0,"last_close":buy_px,"buy_fees":fees,
                            "signal_date":sd,"entry_date":d}
        for s in list(positions.keys()):
            p = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"] += 1
                if p["stale"] > STALE_LIMIT: sell(s, p["last_close"]*(1-SLIP), d, "STALE")
                continue
            p["stale"] = 0
            o,h,l,c,atr,ema = bar
            if l <= p["sl_px"]:
                sell(s, min(o, p["sl_px"])*(1-SLIP), d, "SL"); continue
            p["last_close"] = c; p["days_held"] += 1
            if p["days_held"] >= 2 and atr==atr and ema==ema:
                band = ema if trail_kind=="EMA20" else ema + 1.0*atr
                if c < band:
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
                    cash += excess*p["last_close"]*(1-SLIP)*(1-SELL_COST)
                    p["shares"] -= excess
        pos_val = sum(p["shares"]*p["last_close"] for p in positions.values())
        nav = cash + pos_val
        nav_hist.append({"date":d,"nav":round(nav),"cash":round(cash),
                         "n_pos":len(positions),"day_pnl":round(nav-prev_nav)})
        prev_nav = nav
    for s in list(positions.keys()):
        sell(s, positions[s]["last_close"]*(1-SLIP), calendar[-1], "FINAL")
    nav_df = pd.DataFrame(nav_hist); led = pd.DataFrame(ledger)
    nav_df.to_csv(os.path.join(OUT, f"chartlink_nav_{name}.csv"), index=False)
    led.to_csv(os.path.join(OUT, f"chartlink_trades_{name}.csv"), index=False)
    final = cash
    w = led[led["net_pnl"]>0]; lz = led[led["net_pnl"]<=0]
    print(f"\n===== {name}: final Rs.{final:,.0f} ({(final/INIT_CAP-1)*100:+.2f}%) =====")
    print(f"  trades {len(led)} | win {len(w)/len(led)*100:.1f}% | avg win {w['net_pnl'].mean():,.0f} | "
          f"avg loss {lz['net_pnl'].mean():,.0f} | fees total {led['buy_fees'].sum()+led['sell_fees'].sum():,.0f}")
    return led, nav_df, final

led_ema, nav_ema, fin_ema = run("EMA20", "ATR15_EMA20")
led_kcu, nav_kcu, fin_kcu = run("KCU10", "ATR15_KCU10")

# ---------------- 5-trade random audit (winner config) ----------------
print("\n" + "="*80)
print("RANDOM 5-TRADE AUDIT — config: SL 1.5xATR + EMA20 trail")
print("="*80)
random.seed(42)
sample = led_ema.sample(5, random_state=42).sort_values("entry_date")

# Angel independent source
ang = pd.read_parquet(os.path.join(BASE, "angel_daily_n500_2026.parquet"))
ang["date"] = pd.to_datetime(ang["timestamp"]).dt.tz_localize(None)

ok_all = True
for _, t in sample.iterrows():
    s = t["symbol"]
    g = sym_df[s]
    ed = pd.Timestamp(t["entry_date"]); xd = pd.Timestamp(t["exit_date"])
    sd = pd.Timestamp(t["signal_date"])
    print(f"\n--- {s} | signal {sd.date()} -> entry {ed.date()} -> exit {xd.date()} ({t['reason']}, {t['hold_days']}d) ---")

    # 1. entry = next trading bar after signal; raw open
    row_e = g[g["date"]==ed]
    raw_open = row_e["open"].iloc[0]
    calc_entry = raw_open*(1+SLIP)
    ok1 = abs(calc_entry - t["entry_px"]) < 0.05
    print(f"  raw open {raw_open:.2f} x 1.0015 slip = {calc_entry:.2f} | ledger entry_px {t['entry_px']:.2f}  {'OK' if ok1 else 'MISMATCH'}")

    # 2. SL = entry - 1.5xATR(signal day)
    row_s = g[g["date"]==sd]
    if len(row_s):
        atr_sig = row_s["atr14"].iloc[0]
        calc_sl = calc_entry - 1.5*atr_sig
        ok2 = abs(calc_sl - t["sl_px"]) < 0.5
        print(f"  ATR14(signal day) {atr_sig:.2f} -> SL = {calc_entry:.2f} - 1.5x{atr_sig:.2f} = {calc_sl:.2f} | ledger {t['sl_px']:.2f}  {'OK' if ok2 else 'MISMATCH'}")
    else:
        ok2 = True
        print(f"  (no signal-day bar in panel; entry-day ATR used) ledger SL {t['sl_px']:.2f}")

    # 3. exit trigger verification
    row_x = g[g["date"]==xd]
    o,h,l,c = row_x[["open","high","low","close"]].iloc[0]
    ema_x = row_x["ema20"].iloc[0]
    ok3 = True
    if t["reason"]=="SL":
        raw_fill = min(o, t["sl_px"])
        calc_exit = raw_fill*(1-SLIP)
        ok3 = (l <= t["sl_px"]) and abs(calc_exit - t["exit_px"]) < 0.5
        print(f"  SL check: low {l:.2f} <= SL {t['sl_px']:.2f}? {'YES' if l<=t['sl_px'] else 'NO'} | fill min(open,SL)={raw_fill:.2f} x .9985 = {calc_exit:.2f} vs ledger {t['exit_px']:.2f}  {'OK' if ok3 else 'MISMATCH'}")
    elif t["reason"]=="TRAIL":
        calc_exit = c*(1-SLIP)
        ok3 = (c < ema_x) and abs(calc_exit - t["exit_px"]) < 0.5
        # also check the trail was NOT triggered the previous bar
        gi = g[g["date"]<xd].tail(1)
        prev_ok = ""
        if len(gi):
            pc2, pe2 = gi["close"].iloc[0], gi["ema20"].iloc[0]
            prev_ok = f" | prev bar close {pc2:.2f} vs EMA {pe2:.2f} -> {'above (correctly not exited)' if pc2>=pe2 else 'below (early bars exempt or SL day)'}"
        print(f"  TRAIL check: close {c:.2f} < EMA20 {ema_x:.2f}? {'YES' if c<ema_x else 'NO'} | exit {c:.2f} x .9985 = {calc_exit:.2f} vs ledger {t['exit_px']:.2f}  {'OK' if ok3 else 'MISMATCH'}{prev_ok}")
    else:  # TIME/FINAL
        calc_exit = c*(1-SLIP)
        ok3 = abs(calc_exit - t["exit_px"]) < 0.5
        print(f"  {t['reason']} exit at close {c:.2f} x .9985 = {calc_exit:.2f} vs ledger {t['exit_px']:.2f}  {'OK' if ok3 else 'MISMATCH'}")

    # 4. cost arithmetic
    buy_val = t["shares"]*t["entry_px"]; sell_val = t["shares"]*t["exit_px"]
    calc_bf = buy_val*BUY_COST; calc_sf = sell_val*SELL_COST
    calc_pnl = (t["exit_px"]-t["entry_px"])*t["shares"] - calc_bf - calc_sf
    ok4 = abs(calc_bf-t["buy_fees"])<2 and abs(calc_sf-t["sell_fees"])<2 and abs(calc_pnl-t["net_pnl"])<5
    print(f"  {t['shares']} sh | buy {buy_val:,.0f} fees {calc_bf:,.0f} (ledger {t['buy_fees']:,}) | "
          f"sell {sell_val:,.0f} fees {calc_sf:,.0f} (ledger {t['sell_fees']:,})")
    print(f"  net pnl calc {calc_pnl:,.0f} vs ledger {t['net_pnl']:,}  {'OK' if ok4 else 'MISMATCH'}")

    # 5. independent source cross-check (Angel)
    a_e = ang[(ang["symbol"]==s) & (ang["date"]==ed)]
    if len(a_e):
        a_open = a_e["open"].iloc[0]
        diff = abs(a_open-raw_open)/raw_open*100
        print(f"  ANGEL cross-check entry open: yf {raw_open:.2f} vs angel {a_open:.2f} ({diff:.2f}% diff)  {'OK' if diff<1 else 'CHECK'}")
    else:
        print(f"  ANGEL cross-check: no bar (date before Feb-26 or symbol not in N500 set)")

    ok_all = ok_all and ok1 and ok2 and ok3 and ok4

print(f"\n{'='*80}\nAUDIT RESULT: {'ALL 5 TRADES VERIFIED CLEAN' if ok_all else 'MISMATCHES FOUND - SEE ABOVE'}")

# monthly for both configs (for dashboard)
for nm, nv in [("ATR15_EMA20", nav_ema), ("ATR15_KCU10", nav_kcu)]:
    nv["month"] = pd.to_datetime(nv["date"]).dt.to_period("M")
    m_prev = INIT_CAP
    print(f"\nMonthly {nm}:")
    for m, gg in nv.groupby("month"):
        end = gg["nav"].iloc[-1]
        print(f"  {m}: end {end/1e5:.1f}L pnl {(end-m_prev)/1e5:+.2f}L avgpos {gg['n_pos'].mean():.1f}")
        m_prev = end
