"""
PEAD Q5 — SL/trail grid + PRACTICAL ENTRY-DAY GAP CHECK.
Same portfolio engine as pead_portfolio.py, now with:
  - SL variants: NONE (pure 60d time exit, the baseline already tested),
    FIX10, FIX15, SWING (10-bar low -1%)
  - Trail variants: NONE, EMA20 (close<EMA20 from day2), E20_3D (3 consecutive
    closes below EMA20)
  - Entry-day gap check: what does the actual open look like on the day we
    enter (t+2 after the reaction)? If it's already gapping up hard, we'd be
    chasing an extended move (proven bad in the earlier gap-chase study).
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PEAD_ALPHA_20260714"

INIT_CAP = 10_000_000; ENTRY_PCT = 0.05; MIN_TICKET = 25_000
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
STALE_LIMIT = 10; MAX_HOLD = 60
CA_GAP = -0.25
MIN_TURNOVER_CR = 5.0; MIN_PRICE = 20.0

ev = pd.read_csv(os.path.join(OUT, "pead_events.csv"), parse_dates=["available_date"])
p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7

sym_bars = {}; sym_dates = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    g["ema20"] = g["close"].ewm(span=20, min_periods=5).mean()
    g["swing10"] = g["low"].rolling(10, min_periods=3).min()
    g["prev_close"] = g["close"].shift(1)
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"], g["turnover_cr"], g["ema20"], g["swing10"], g["prev_close"])))
    sym_dates[sym] = list(g["date"])

dc = p.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(p["date"].unique()) if dc.get(pd.Timestamp(d), 0) >= 50]
cal_set = set(calendar)

ev["quarter"] = ev["available_date"].dt.to_period("Q")
ev["decile_rank"] = ev.groupby("quarter")["reaction_pct"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)
q5 = ev[ev["decile_rank"] == 4]

def entry_day_for(sym, ad):
    dates = sym_dates.get(sym)
    if not dates: return None
    idx = np.searchsorted(dates, ad)
    entry_i = idx + 2
    if entry_i >= len(dates): return None
    d = dates[entry_i]
    return d if d in cal_set else None

entries_by_day = {}
entry_gaps = []
for _, r in q5.iterrows():
    ed = entry_day_for(r["symbol"], r["available_date"])
    if ed is None: continue
    bar = sym_bars.get(r["symbol"], {}).get(ed)
    if bar is None or bar[0] <= 0 or bar[4] < MIN_TURNOVER_CR or bar[0] < MIN_PRICE:
        continue
    entry_gap_pct = (bar[0]/bar[7]-1)*100 if bar[7] and bar[7] > 0 else np.nan
    entry_gaps.append(entry_gap_pct)
    entries_by_day.setdefault(ed, []).append((r["symbol"], ed))

eg = pd.Series(entry_gaps).dropna()
print("="*100)
print("PRACTICAL ENTRY-DAY GAP CHECK (the day we actually buy, t+2 after the reaction)")
print("="*100)
print(f"n={len(eg)} | mean gap {eg.mean():.2f}% | median {eg.median():.2f}%")
print(f"  gap >= +3%: {(eg>=3).mean()*100:.1f}% of entries | >= +5%: {(eg>=5).mean()*100:.1f}% | "
      f">= +8%: {(eg>=8).mean()*100:.1f}%")
print(f"  gap <= -3%: {(eg<=-3).mean()*100:.1f}% of entries (buying into a pullback)")
print("  -> if a meaningful share gap >=5% AGAIN at entry, we may be chasing an already-extended move\n")

def sl_price(mode, buy_px, sym, entry_date):
    if mode == "NONE": return -1  # never triggers
    if mode == "FIX10": return buy_px*0.90
    if mode == "FIX15": return buy_px*0.85
    if mode == "SWING":
        bar = sym_bars.get(sym, {}).get(entry_date)
        sw = bar[6] if bar is not None else np.nan
        return sw*0.99 if (sw==sw and sw<buy_px) else buy_px*0.90
    return -1

def run(sl_mode, trail_mode, label):
    cash = float(INIT_CAP); positions = {}; ledger = []; nav_hist = []
    prev_nav = float(INIT_CAP)
    def sell(s, px, d, reason):
        nonlocal cash
        pos = positions[s]
        gross = pos["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees
        pnl = (px-pos["entry_px"])*pos["shares"] - fees - pos["bf"]
        ledger.append({"symbol": s, "exit_date": d, "reason": reason, "hold": pos["days_held"],
                       "pnl": round(pnl), "ret_pct": round(pnl/(pos["shares"]*pos["entry_px"])*100, 2)})
        del positions[s]
    for d in calendar:
        for s, ed in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or bar[0] <= 0: continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(ENTRY_PCT*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_price(sl_mode, buy_px, s, d),
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees,"b20":0}
        for s in list(positions.keys()):
            pos = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                pos["stale"]+=1
                if pos["stale"]>STALE_LIMIT: sell(s, pos["last_close"]*(1-SLIP), d, "STALE")
                continue
            pos["stale"]=0
            o,h,l,c,_,ema,sw,_ = bar
            if pos["days_held"] > 0 and o > 0 and pos["last_close"] > 0 and (o/pos["last_close"]-1) <= CA_GAP:
                sell(s, pos["last_close"]*(1-SLIP), d, "CA"); continue
            if pos["days_held"] > 0 and l <= pos["sl_px"]:
                sell(s, min(o,pos["sl_px"])*(1-SLIP), d, "SL"); continue
            pos["last_close"]=c; pos["days_held"]+=1
            pos["b20"] = pos["b20"]+1 if (ema==ema and c<ema) else 0
            if pos["days_held"] >= 2:
                if trail_mode=="EMA20" and ema==ema and c<ema:
                    sell(s, c*(1-SLIP), d, "TRAIL"); continue
                if trail_mode=="E20_3D" and pos["b20"]>=3:
                    sell(s, c*(1-SLIP), d, "TRAIL"); continue
            if pos["days_held"]>=MAX_HOLD:
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
        ledger.append({"symbol": s, "exit_date": calendar[-1], "reason": "OPEN", "hold": pos["days_held"],
                       "pnl": round(pnl), "ret_pct": round(pnl/(pos["shares"]*pos["entry_px"])*100, 2)})
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
    exits = led["reason"].value_counts().to_dict()
    print(f"{label:<22} final {final/1e5:>6.1f}L | CAGR {cagr*100:>6.2f}% | DD {mdd*100:>6.1f}% | "
          f"Sharpe {sharpe:>4.2f} | win {(led['pnl']>0).mean()*100:>5.1f}% | PF {pf:>4.2f} | n {len(led):>3} | "
          f"exits {exits}")
    return {"sl": sl_mode, "trail": trail_mode, "cagr": cagr*100, "dd": mdd*100, "sharpe": sharpe}

print("="*100)
print("SL x TRAIL GRID (PEAD Q5, 60d max hold, 5% sizing)")
print("="*100)
results = []
for sl_mode in ["NONE", "FIX10", "FIX15", "SWING"]:
    for trail_mode in ["NONE", "EMA20", "E20_3D"]:
        r = run(sl_mode, trail_mode, f"{sl_mode}/{trail_mode}")
        results.append(r)
rdf = pd.DataFrame(results).sort_values("sharpe", ascending=False)
print("\nTOP BY SHARPE:")
print(rdf.head(6).to_string(index=False))
rdf.to_csv(os.path.join(OUT, "pead_sl_trail_grid.csv"), index=False)
print("\nSaved pead_sl_trail_grid.csv")
