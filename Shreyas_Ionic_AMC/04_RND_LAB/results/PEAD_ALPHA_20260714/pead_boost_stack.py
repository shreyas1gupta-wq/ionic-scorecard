"""
PEAD BOOST STACK: can we push CAGR above 35%?
Levers tested (all on the validated base: Q5, no SL, no trail, 60d hold):
  1. Position sizing: 5% / 7.5% / 10%
  2. Fundamental earnings-surprise MAGNITUDE (actual sales/profit YoY growth,
     not just price reaction) stacked with Q5
  3. 52-week-high proximity stacked with Q5 (the strongest single predictor
     found in the whole session's feature lab)
  4. CONVICTION-WEIGHTED sizing: instead of a hard filter (which we already
     found hurts), size UP quality-confirmed signals and size DOWN others,
     keeping full breadth - the "position size with setup" idea.
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PEAD_ALPHA_20260714"

INIT_CAP = 10_000_000; MIN_TICKET = 25_000
DRIFT_MAX = 0.20; DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
STALE_LIMIT = 10; MAX_HOLD = 60; CA_GAP = -0.25
MIN_TURNOVER_CR = 5.0; MIN_PRICE = 20.0

feat = pd.read_csv(os.path.join(OUT, "pead_enriched_features.csv"), parse_dates=["available_date"])
ep = pd.read_parquet(os.path.join(BASE, "earnings_pit", "unified_quarterly_pit.parquet"),
                     columns=["symbol", "available_date", "quarter_end", "sales", "net_profit"])
ep["available_date"] = pd.to_datetime(ep["available_date"]); ep["quarter_end"] = pd.to_datetime(ep["quarter_end"])
ep = ep.dropna(subset=["available_date"]).sort_values(["symbol", "available_date"])
prev = ep[["symbol", "quarter_end", "sales", "net_profit"]].copy()
prev["quarter_end"] = prev["quarter_end"] + pd.DateOffset(years=1)
prev = prev.rename(columns={"sales": "sales_prev", "net_profit": "np_prev"})
ep = ep.merge(prev, on=["symbol", "quarter_end"], how="left")
ep["sales_yoy"] = (ep["sales"] - ep["sales_prev"]) / ep["sales_prev"].abs() * 100
ep["np_yoy"] = (ep["net_profit"] - ep["np_prev"]) / ep["np_prev"].abs() * 100

feat = feat.merge(ep[["symbol", "available_date", "sales_yoy", "np_yoy"]], on=["symbol", "available_date"], how="left")

p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7
sym_bars = {}; sym_dates = {}; sym_52wh = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    g["hi252"] = g["high"].rolling(252, min_periods=60).max()
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]), zip(g["open"], g["high"], g["low"], g["close"], g["turnover_cr"])))
    sym_dates[sym] = list(g["date"])
    sym_52wh[sym] = g.set_index("date")["hi252"]

dc = p.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(p["date"].unique()) if dc.get(pd.Timestamp(d), 0) >= 50]
cal_set = set(calendar)

# add dist_52wh_pct (as of day before available_date - strictly PIT)
def get_52wh_dist(sym, ad):
    s = sym_52wh.get(sym)
    if s is None: return np.nan
    prior = s.loc[s.index < ad]
    if len(prior) == 0: return np.nan
    hi = prior.iloc[-1]
    return np.nan if hi != hi or hi <= 0 else None  # placeholder, filled below

close_pre_map = {}
for sym, g in p.groupby("symbol"):
    gg = g.sort_values("date").reset_index(drop=True).set_index("date")
    close_pre_map[sym] = gg["close"]

dist52 = []
for _, r in feat.iterrows():
    sym, ad = r["symbol"], r["available_date"]
    s = sym_52wh.get(sym); cp = close_pre_map.get(sym)
    if s is None or cp is None:
        dist52.append(np.nan); continue
    prior_hi = s.loc[s.index < ad]
    prior_cp = cp.loc[cp.index < ad]
    if len(prior_hi) == 0 or len(prior_cp) == 0 or prior_hi.iloc[-1] != prior_hi.iloc[-1] or prior_hi.iloc[-1] <= 0:
        dist52.append(np.nan); continue
    dist52.append((prior_cp.iloc[-1] / prior_hi.iloc[-1] - 1) * 100)
feat["dist_52wh_pct"] = dist52

q5 = feat[feat["decile_rank"] == 4].copy()
print(f"Q5 events: {len(q5)}")
print(f"  with sales_yoy/np_yoy: {q5['np_yoy'].notna().sum()}")
print(f"  with dist_52wh_pct: {q5['dist_52wh_pct'].notna().sum()}")

def entry_day_for(sym, ad):
    dates = sym_dates.get(sym)
    if not dates: return None
    idx = np.searchsorted(dates, ad)
    entry_i = idx + 2
    if entry_i >= len(dates): return None
    d = dates[entry_i]
    return d if d in cal_set else None

def build_entries(subset, weight_col=None, default_w=1.0):
    entries = {}
    for _, r in subset.iterrows():
        ed = entry_day_for(r["symbol"], r["available_date"])
        if ed is None: continue
        bar = sym_bars.get(r["symbol"], {}).get(ed)
        if bar is None or bar[0] <= 0 or bar[4] < MIN_TURNOVER_CR or bar[0] < MIN_PRICE:
            continue
        w = r[weight_col] if weight_col else default_w
        entries.setdefault(ed, []).append((r["symbol"], w))
    return entries

def run(entries_by_day, base_pct, label, max_pos_cap=None):
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
        for s, w in entries_by_day.get(d, []):
            if s in positions: continue
            if max_pos_cap and len(positions) >= max_pos_cap: continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or bar[0] <= 0: continue
            buy_px = bar[0]*(1+SLIP)
            budget = min(base_pct*w*prev_nav, cash)
            if budget < MIN_TICKET: continue
            shares = int(budget/(buy_px*(1+BUY_COST)))
            if shares <= 0: continue
            gross = shares*buy_px; fees = gross*BUY_COST
            cash -= gross+fees
            positions[s] = {"shares":shares,"entry_px":buy_px,"days_held":0,"stale":0,"last_close":buy_px,"bf":fees}
        for s in list(positions.keys()):
            pos = positions[s]; bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                pos["stale"]+=1
                if pos["stale"]>STALE_LIMIT: sell(s, pos["last_close"]*(1-SLIP), d, "STALE")
                continue
            pos["stale"]=0
            o,h,l,c,_ = bar
            if pos["days_held"] > 0 and o > 0 and pos["last_close"] > 0 and (o/pos["last_close"]-1) <= CA_GAP:
                sell(s, pos["last_close"]*(1-SLIP), d, "CA"); continue
            pos["last_close"]=c; pos["days_held"]+=1
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
    print(f"{label:<52} CAGR {cagr*100:>6.2f}% | DD {mdd*100:>6.1f}% | Sharpe {sharpe:>4.2f} | "
          f"win {(led['pnl']>0).mean()*100:>5.1f}% | PF {pf:>4.2f} | n {len(led):>4} | avgpos {nd['n_pos'].mean():>4.1f}")
    return cagr*100, mdd*100, sharpe

print("\n" + "="*105)
print("LEVER 1: position sizing")
print("="*105)
e_base = build_entries(q5)
for pct in [0.05, 0.075, 0.10]:
    run(e_base, pct, f"Q5-only, {pct*100:.1f}% sizing")

print("\n" + "="*105)
print("LEVER 2: stack with fundamental earnings-surprise MAGNITUDE (not just price reaction)")
print("="*105)
q5f = q5.dropna(subset=["np_yoy"])
q5f["quarter"] = q5f["available_date"].dt.to_period("Q")
q5f["np_yoy_rank"] = q5f.groupby("quarter")["np_yoy"].rank(pct=True)
for cut, lbl in [(0.5, "top-50% np_yoy"), (0.67, "top-33% np_yoy")]:
    sub = q5f[q5f["np_yoy_rank"] >= cut]
    e = build_entries(sub)
    run(e, 0.05, f"Q5 + {lbl} (n_events={len(sub)})")

print("\n" + "="*105)
print("LEVER 3: stack with 52-week-high proximity")
print("="*105)
q5h = q5.dropna(subset=["dist_52wh_pct"])
for thresh, lbl in [(-10, "within 10% of 52wh"), (-5, "within 5% of 52wh"), (0, "AT new 52wh")]:
    sub = q5h[q5h["dist_52wh_pct"] >= thresh]
    e = build_entries(sub)
    run(e, 0.05, f"Q5 + {lbl} (n_events={len(sub)})")

print("\n" + "="*105)
print("LEVER 4: CONVICTION-WEIGHTED sizing (not hard filter) - full breadth, tilted capital")
print("="*105)
q5["quarter"] = q5["available_date"].dt.to_period("Q")
q5["rs_ok"] = (q5["rs_vs_n50_63"] > 0).astype(int)
q5["mom_ok"] = (q5["mom_63d_pre"] > q5.groupby("quarter")["mom_63d_pre"].transform("median")).astype(int)
q5["conviction_w"] = 1.0 + 0.5*q5["rs_ok"] + 0.5*q5["mom_ok"]   # 1.0x baseline, up to 2.0x if both confirm
e_conv = build_entries(q5, weight_col="conviction_w")
run(e_conv, 0.05, "Q5 conviction-weighted (1.0-2.0x by RS+momentum)", max_pos_cap=20)

print("\n" + "="*105)
print("LEVER 4b: conviction-weighted AT 7.5% base sizing (combine sizing + conviction)")
print("="*105)
run(e_conv, 0.075, "Q5 conviction-weighted @ 7.5% base", max_pos_cap=20)
