"""
PEAD PORTFOLIO: convert the Q5-reaction signal into a real, tradeable strategy.
Buy top-quintile (biggest positive earnings-day reaction) names, entry = the
trading day 2 days after the reaction (avoids paying up into the event-day
spike itself), hold 60 trading days, no leverage, real costs, Rs.1Cr.
Compares: Q5-only vs ALL events (unconditional) vs NIFTY50/Smallcap100.
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
p["turnover_cr"] = p["close"] * p["volume"] / 1e7

sym_bars = {}
sym_dates = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]), zip(g["open"], g["high"], g["low"], g["close"],
                                                              g["turnover_cr"])))
    sym_dates[sym] = list(g["date"])

dc = p.groupby("date")["symbol"].nunique()
calendar = [pd.Timestamp(d) for d in sorted(p["date"].unique()) if dc.get(pd.Timestamp(d), 0) >= 50]
cal_set = set(calendar)

def entry_day_for(sym, ad):
    """2 trading days after the reaction bar (matching pead_discovery's base_i)."""
    dates = sym_dates.get(sym)
    if not dates: return None
    idx = np.searchsorted(dates, ad)
    react_i = idx
    entry_i = react_i + 2
    if entry_i >= len(dates): return None
    d = dates[entry_i]
    return d if d in cal_set else None

ev["quarter"] = ev["available_date"].dt.to_period("Q")
ev["decile_rank"] = ev.groupby("quarter")["reaction_pct"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)

def build_entries(subset):
    entries = {}
    for _, r in subset.iterrows():
        ed = entry_day_for(r["symbol"], r["available_date"])
        if ed is None: continue
        bar = sym_bars.get(r["symbol"], {}).get(ed)
        if bar is None or bar[0] <= 0 or bar[4] < MIN_TURNOVER_CR or bar[0] < MIN_PRICE:
            continue
        entries.setdefault(ed, []).append(r["symbol"])
    return entries

def run(entries_by_day, label):
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
        for s in entries_by_day.get(d, []):
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
            positions[s] = {"shares":shares,"entry_px":buy_px,"days_held":0,"stale":0,
                            "last_close":buy_px,"bf":fees}
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
    print(f"\n===== {label} =====")
    print(f"Final Rs.{final/1e5:.1f}L ({(final/INIT_CAP-1)*100:+.1f}%) | CAGR {cagr*100:.2f}% | "
          f"MaxDD {mdd*100:.1f}% | Sharpe {sharpe:.2f}")
    print(f"Trades {len(led)} | win {(led['pnl']>0).mean()*100:.1f}% | PF {pf:.2f} | avg hold {led['hold'].mean():.1f}d | "
          f"avg pos {nd['n_pos'].mean():.1f} (max {nd['n_pos'].max()})")
    nd["year"] = nd["date"].dt.year
    yl = [f"{yr}:{(g['nav'].iloc[-1]/g['nav'].iloc[0]-1)*100:+.1f}%" for yr, g in nd.groupby("year")]
    print("Yearly: " + " | ".join(yl))

print("Building entries for Q5-only vs ALL events...")
q5 = ev.dropna(subset=["decile_rank"])
q5_top = q5[q5["decile_rank"] == 4]
entries_q5 = build_entries(q5_top)
entries_all = build_entries(ev)
print(f"Q5-only tradeable entries: {sum(len(v) for v in entries_q5.values())}")
print(f"ALL events tradeable entries: {sum(len(v) for v in entries_all.values())}")

run(entries_q5, "PEAD Q5-only, 60d hold, 5%")
run(entries_all, "ALL earnings events (unconditional), 60d hold, 5%")

print("\n" + "="*100)
print("BENCHMARKS")
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
