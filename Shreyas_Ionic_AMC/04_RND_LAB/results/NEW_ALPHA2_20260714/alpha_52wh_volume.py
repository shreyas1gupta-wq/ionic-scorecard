"""52wh + VOLUME CONFIRMATION refinement (does adding just one filter salvage it,
vs the full Chartlink compound screen?)"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEW_ALPHA2_20260714"

INIT_CAP = 10_000_000; MIN_TICKET = 25_000
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
STALE_LIMIT = 10; CA_GAP = -0.25
MIN_TURNOVER_CR = 5.0; MIN_PRICE = 20.0
START = pd.Timestamp("2021-06-01")

p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7

sym_bars = {}
signals = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 260: continue
    g["hi252"] = g["high"].rolling(252, min_periods=200).max()
    g["prior_hi252"] = g["hi252"].shift(1)
    g["swing10"] = g["low"].rolling(10, min_periods=3).min()
    g["turnover_avg20"] = g["turnover_cr"].rolling(20, min_periods=10).mean()
    g["vol_avg20"] = g["volume"].rolling(20, min_periods=10).mean()
    g["vol_ratio"] = g["volume"] / g["vol_avg20"]
    g["chg_pct"] = g["close"].pct_change()*100
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]), zip(g["open"], g["high"], g["low"], g["close"],
                                                              g["turnover_cr"], g["swing10"])))
    mask = (g["close"] >= g["prior_hi252"]) & (g["turnover_avg20"] >= MIN_TURNOVER_CR) & \
           (g["close"] >= MIN_PRICE) & (g["date"] >= START) & (g["vol_ratio"] >= 1.5) & (g["chg_pct"] >= 2)
    for _, r in g[mask].iterrows():
        signals.append({"symbol": sym, "date": r["date"]})

sig = pd.DataFrame(signals).sort_values("date").reset_index(drop=True)
print(f"52wh+volume(1.5x)+chg(2%) signals: {len(sig)}, {len(sig)/((sig['date'].max()-sig['date'].min()).days/365.25):.0f}/yr")

dc = p.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(p["date"].unique()) if dc.get(pd.Timestamp(d), 0) >= 50]
cal_set = set(calendar)
entries_by_day = {}
for _, r in sig.iterrows():
    s, sd = r["symbol"], r["date"]
    d = sd + pd.Timedelta(days=1); later = None
    for _ in range(7):
        if d in cal_set and d in sym_bars[s]:
            later = d; break
        d += pd.Timedelta(days=1)
    if later is None: continue
    entries_by_day.setdefault(later, []).append((s, sym_bars[s].get(pd.Timestamp(sd))))

def run(sl_mode, max_hold, entry_pct, label):
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
        if d < START: continue
        for s, ref in entries_by_day.get(d, []):
            if s in positions: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or bar[0] <= 0: continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(entry_pct*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees
            sw = ref[5] if ref is not None and ref[5]==ref[5] else np.nan
            sl_px = -1 if sl_mode=="NONE" else (sw*0.99 if (sl_mode=="SWING" and sw==sw and sw<buy_px) else buy_px*0.85)
            positions[s] = {"shares":shares,"entry_px":buy_px,"sl_px":sl_px,
                            "days_held":0,"stale":0,"last_close":buy_px,"bf":fees}
        for s in list(positions.keys()):
            pos = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                pos["stale"]+=1
                if pos["stale"]>STALE_LIMIT: sell(s, pos["last_close"]*(1-SLIP), d, "STALE")
                continue
            pos["stale"]=0
            o,h,l,c,_,_ = bar
            if pos["days_held"] > 0 and o > 0 and pos["last_close"] > 0 and (o/pos["last_close"]-1) <= CA_GAP:
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
    yrs = (calendar[-1]-nd["date"].iloc[0]).days/365.25
    print(f"{label:<24} CAGR {cagr*100:>6.2f}% | MDD {mdd*100:>6.1f}% | Sharpe {sharpe:>4.2f} | "
          f"win {(led['pnl']>0).mean()*100:>5.1f}% | PF {pf:>4.2f} | n {len(led):>4} ({len(led)/yrs:>4.0f}/yr) | avgpos {nd['n_pos'].mean():>4.1f}")

for sl_mode in ["NONE", "SWING"]:
    for hold in [30, 60]:
        for pct in [0.05, 0.075]:
            run(sl_mode, hold, pct, f"{sl_mode} {hold}d {pct*100:.1f}%")
