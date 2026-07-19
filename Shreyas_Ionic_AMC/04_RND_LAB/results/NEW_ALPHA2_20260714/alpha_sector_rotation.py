"""
NEW ALPHA #5: SECTOR ROTATION + STOCK SELECTION (genuinely different 2-stage
mechanic vs anything tested this session - momentum at the SECTOR level,
then pick the strongest STOCKS within the winning sectors).

Monthly: rank all sectors by trailing 1-month equal-weighted return. Take the
top-2 sectors. Within those sectors, rank stocks by trailing 3-month return,
buy the top-N per sector. Hold 1 month, rebalance. Rs.1Cr, no leverage, real
costs, no SL/trail (matching the proven "let it run" law), monthly turnover
naturally gives high trade frequency.
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEW_ALPHA2_20260714"

INIT_CAP = 10_000_000
BUY_COST = 0.00152; SELL_COST = 0.00137; SLIP = 0.0015
MIN_TURNOVER_CR = 3.0; MIN_PRICE = 20.0
TOP_SECTORS = 2; STOCKS_PER_SECTOR = 6

sector_map = pd.read_csv(os.path.join(OUT, "sector_map.csv")).set_index("symbol")["sector"].to_dict()

p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7
p["sector"] = p["symbol"].map(sector_map)
p = p.dropna(subset=["sector"])
p = p[p["sector"] != ""]
print(f"Universe with sector tags: {p['symbol'].nunique()} symbols, {p['sector'].nunique()} sectors")

rows = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 90: continue
    g["ret_21d"] = g["close"].pct_change(21) * 100
    g["ret_63d"] = g["close"].pct_change(63) * 100
    g["turnover_avg20"] = g["turnover_cr"].rolling(20, min_periods=10).mean()
    g["month"] = g["date"].dt.to_period("M")
    rows.append(g[["symbol","sector","date","month","close","open","ret_21d","ret_63d","turnover_avg20"]])
d = pd.concat(rows, ignore_index=True)
d = d.dropna(subset=["ret_21d","ret_63d"])

# month-end snapshot for rebalance decisions (strictly using data up to month-end)
d["is_me"] = d.groupby(["symbol","month"])["date"].transform("max") == d["date"]
me = d[d["is_me"]].copy()

# sector momentum = equal-weighted avg of stock-level trailing 21d returns within sector, at month-end
sector_mom = me.groupby(["month","sector"])["ret_21d"].mean().reset_index()
sector_mom["sector_rank"] = sector_mom.groupby("month")["ret_21d"].rank(ascending=False)
top_sectors_by_month = sector_mom[sector_mom["sector_rank"] <= TOP_SECTORS]

# REGIME GATE: only deploy into equities if NIFTY 50 is above its 200dma at month-end
# (broad market regime filter, replaces the per-sector positive-momentum filter which
# made things worse - v1 result: CAGR 22.14%, MDD -34.5%, 2025 -26.1% i.e. WORSE than baseline)
idx = pd.read_parquet(os.path.join(BASE, "index_daily", "nse_official_all_indices.parquet"))
idx = idx[idx["index_name"] == "Nifty 50"].sort_values("date").reset_index(drop=True)
idx["date"] = pd.to_datetime(idx["date"])
idx["dma200"] = idx["close"].rolling(200, min_periods=150).mean()
idx["month"] = idx["date"].dt.to_period("M")
idx["is_me"] = idx.groupby("month")["date"].transform("max") == idx["date"]
idx_me = idx[idx["is_me"]].copy()
idx_me["regime_ok"] = idx_me["close"] > idx_me["dma200"]
regime_by_month = idx_me.set_index("month")["regime_ok"].to_dict()

months = sorted(me["month"].unique())
sym_bars = {}; sym_dates = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_bars[sym] = dict(zip(pd.DatetimeIndex(g["date"]), zip(g["open"], g["close"])))
    sym_dates[sym] = list(g["date"])
dc = p.groupby("date")["symbol"].nunique()
calendar = sorted([pd.Timestamp(d) for d in p["date"].unique() if dc.get(pd.Timestamp(d), 0) >= 30])

def first_trading_day_of_next_month(month):
    nxt = month + 1
    cands = [d for d in calendar if pd.Period(d, freq="M") == nxt]
    return cands[0] if cands else None

print("Building monthly baskets...")
baskets = {}
for month in months:
    if not regime_by_month.get(month, True): continue
    top_secs = set(top_sectors_by_month[top_sectors_by_month["month"]==month]["sector"])
    if not top_secs: continue
    cand = me[(me["month"]==month) & (me["sector"].isin(top_secs)) &
             (me["turnover_avg20"]>=MIN_TURNOVER_CR) & (me["close"]>=MIN_PRICE)]
    cand = cand.sort_values(["sector","ret_63d"], ascending=[True,False])
    picks = cand.groupby("sector").head(STOCKS_PER_SECTOR)
    entry_day = first_trading_day_of_next_month(month)
    if entry_day is None: continue
    baskets[entry_day] = list(picks["symbol"])

print(f"Months with baskets: {len(baskets)}")

# ---------------- Portfolio sim: monthly rebalance, equal-weight within basket ----------------
cash = float(INIT_CAP); nav_hist = []; ledger = []
sorted_entry_days = sorted(baskets.keys())
positions = {}

def liquidate_all(d):
    global cash
    for s, pos in list(positions.items()):
        bar = sym_bars.get(s, {}).get(d)
        px = bar[1]*(1-SLIP) if bar else pos["last_close"]*(1-SLIP)
        gross = pos["shares"]*px; fees = gross*SELL_COST
        cash += gross - fees
        pnl = (px-pos["entry_px"])*pos["shares"] - fees - pos["bf"]
        ledger.append({"symbol": s, "exit_date": d, "pnl": round(pnl),
                       "ret_pct": round(pnl/(pos["shares"]*pos["entry_px"])*100, 2)})
    positions.clear()

prev_nav = float(INIT_CAP)
for i, d in enumerate(sorted_entry_days):
    liquidate_all(d)
    basket = baskets[d]
    if not basket: continue
    n = len(basket)
    per_stock_budget = cash / n
    for s in basket:
        bar = sym_bars.get(s, {}).get(d)
        if bar is None or bar[0] <= 0: continue
        buy_px = bar[0]*(1+SLIP)
        shares = int(per_stock_budget/(buy_px*(1+BUY_COST)))
        if shares <= 0: continue
        gross = shares*buy_px; fees = gross*BUY_COST
        cash -= gross+fees
        positions[s] = {"shares":shares,"entry_px":buy_px,"bf":fees,"last_close":buy_px}
    # mark-to-market through to next rebalance (approx: just track cash+positions at entry)
    pos_val = sum(pos["shares"]*pos["entry_px"] for pos in positions.values())
    nav_hist.append({"date": d, "nav": cash+pos_val})

# final liquidation at last available date for any open positions
if positions:
    last_d = calendar[-1]
    liquidate_all(last_d)
    nav_hist.append({"date": last_d, "nav": cash})

led = pd.DataFrame(ledger); nd = pd.DataFrame(nav_hist)
final = cash
days = (nd["date"].iloc[-1]-nd["date"].iloc[0]).days
cagr = (final/INIT_CAP)**(365.25/days)-1 if days>0 else 0
v = nd["nav"].values
pk = np.maximum.accumulate(v); mdd = ((v/pk)-1).min()
rr = pd.Series(v).pct_change().dropna()
sharpe = rr.mean()/rr.std()*np.sqrt(12) if rr.std()>0 else 0  # monthly obs -> annualize by sqrt(12)
w = led[led["pnl"]>0]; lz = led[led["pnl"]<=0]
pf = w["pnl"].sum()/abs(lz["pnl"].sum()) if len(lz) else 99
yrs = days/365.25
print(f"\nSECTOR ROTATION (top-{TOP_SECTORS} sectors, top-{STOCKS_PER_SECTOR}/sector, monthly)")
print(f"Final Rs.{final/1e5:.1f}L ({(final/INIT_CAP-1)*100:+.1f}%) | CAGR {cagr*100:.2f}% | MDD {mdd*100:.1f}% | Sharpe {sharpe:.2f}")
print(f"Trades {len(led)} ({len(led)/yrs:.0f}/yr) | win {(led['pnl']>0).mean()*100:.1f}% | PF {pf:.2f}")
nd["year"] = nd["date"].dt.year
for yr, g in nd.groupby("year"):
    print(f"  {yr}: {(g['nav'].iloc[-1]/g['nav'].iloc[0]-1)*100:+.1f}%")
led.to_csv(os.path.join(OUT, "sector_rotation_ledger.csv"), index=False)
nd.to_csv(os.path.join(OUT, "sector_rotation_navcurve.csv"), index=False)
