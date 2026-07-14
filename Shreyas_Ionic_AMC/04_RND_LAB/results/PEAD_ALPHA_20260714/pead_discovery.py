"""
NEW ALPHA FROM SCRATCH: Post-Earnings-Announcement Drift (PEAD)
================================================================
Classic, well-documented anomaly (Ball & Brown 1968, still robust today):
the market UNDER-reacts to earnings surprises on the announcement day, and
price keeps drifting in the same direction for weeks afterward. Completely
independent of any chart pattern / breakout signal used elsewhere in this
project — a genuinely different, fundamentals-event-driven source of edge.

STRICT NO-LOOKAHEAD: uses only earnings_pit.available_date (the date the
result became public knowledge), never quarter_end.

Method:
  1. For each (symbol, available_date) earnings event, find the announcement
     reaction = return from the close BEFORE available_date to the close on
     the first trading day AT/AFTER available_date (captures the market's
     immediate response, whether reported pre/post/during market hours).
  2. Each quarter, rank all events that quarter into quintiles by that
     reaction (a price-based "standardized unexpected earnings" proxy).
  3. Track forward drift from 2 trading days after the reaction (to avoid
     overlapping with the event window itself) out to 20d/60d/120d.
  4. Check monotonicity Q1->Q5 and t-stat significance of the long-short spread.
  5. Convert into an actionable long-only portfolio: quarterly-refreshed
     basket of the top-quintile names, realistic costs, Rs.1Cr, no leverage.
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PEAD_ALPHA_20260714"
os.makedirs(OUT, exist_ok=True)

print("Loading earnings PIT + daily price panel...")
ep = pd.read_parquet(os.path.join(BASE, "earnings_pit", "unified_quarterly_pit.parquet"),
                     columns=["symbol", "available_date", "quarter_end", "sales", "net_profit"])
ep["available_date"] = pd.to_datetime(ep["available_date"])
ep["quarter_end"] = pd.to_datetime(ep["quarter_end"])
ep = ep.dropna(subset=["available_date"]).sort_values(["symbol", "available_date"])

p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
print(f"Earnings PIT: {len(ep):,} rows, {ep['symbol'].nunique()} symbols, "
      f"{ep['available_date'].min().date()} -> {ep['available_date'].max().date()}")
print(f"Price panel: {len(p):,} rows, {p['symbol'].nunique()} symbols, "
      f"{p['date'].min().date()} -> {p['date'].max().date()}")

sym_bars = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_bars[sym] = g

common_syms = set(ep["symbol"].unique()) & set(p["symbol"].unique())
print(f"Common symbols: {len(common_syms)}")

# ---------------- Build event-level dataset ----------------
print("\nBuilding earnings-event dataset (reaction + forward drift)...")
events = []
for sym in common_syms:
    g = sym_bars[sym]
    if len(g) < 60:
        continue
    dates = g["date"].values
    closes = g["close"].values
    date_idx = {d: i for i, d in enumerate(dates)}
    eg = ep[(ep["symbol"] == sym) & (ep["available_date"] >= p["date"].min()) &
            (ep["available_date"] <= p["date"].max())]
    for _, r in eg.iterrows():
        ad = r["available_date"]
        # find first trading day AT/AFTER available_date (the reaction day),
        # and the trading day BEFORE it (pre-announcement close)
        idx_arr = np.searchsorted(dates, np.datetime64(ad))
        if idx_arr <= 0 or idx_arr >= len(dates):
            continue
        react_i = idx_arr if dates[idx_arr] >= np.datetime64(ad) else idx_arr
        pre_i = react_i - 1
        if pre_i < 0 or react_i >= len(dates):
            continue
        pre_close = closes[pre_i]
        react_close = closes[react_i]
        if pre_close <= 0:
            continue
        reaction_pct = (react_close / pre_close - 1) * 100

        # forward drift from 2 trading days after the reaction bar
        base_i = react_i + 2
        out = {"symbol": sym, "available_date": ad, "reaction_pct": reaction_pct,
               "sales": r["sales"], "net_profit": r["net_profit"]}
        for h, label in [(20, "fwd_20d"), (60, "fwd_60d"), (120, "fwd_120d")]:
            if base_i < len(dates) and base_i + h < len(dates):
                out[label] = (closes[base_i + h] / closes[base_i] - 1) * 100
            else:
                out[label] = np.nan
        events.append(out)

ev = pd.DataFrame(events)
print(f"\nTotal earnings events matched to price data: {len(ev)}")
ev = ev.dropna(subset=["reaction_pct"])
print(f"After dropping missing reaction: {len(ev)}")

# ---------------- Quarterly quintile sort ----------------
ev["quarter"] = ev["available_date"].dt.to_period("Q")
ev["decile_rank"] = ev.groupby("quarter")["reaction_pct"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)

print("\n" + "="*100)
print("PEAD QUINTILE TABLE: forward drift by announcement-reaction quintile (Q1=worst reaction, Q5=best)")
print("="*100)
for h in ["fwd_20d", "fwd_60d", "fwd_120d"]:
    d2 = ev.dropna(subset=[h, "decile_rank"])
    print(f"\n--- {h} (n={len(d2)}) ---")
    print(f"{'Quintile':<10} {'n':>6} {'mean%':>8} {'median%':>8} {'win%':>6}")
    means = {}
    for q in range(5):
        sub = d2[d2["decile_rank"] == q]
        if len(sub) < 10:
            continue
        print(f"Q{q+1:<9} {len(sub):>6} {sub[h].mean():>8.2f} {sub[h].median():>8.2f} {(sub[h]>0).mean()*100:>5.1f}%")
        means[q] = sub[h]
    if 4 in means and 0 in means:
        t, pv = stats.ttest_ind(means[4], means[0], equal_var=False)
        spread = means[4].mean() - means[0].mean()
        print(f"  Q5-Q1 spread: {spread:+.2f}%  (t={t:.2f}, p={pv:.4f})")

ev.to_csv(os.path.join(OUT, "pead_events.csv"), index=False)
print(f"\nSaved pead_events.csv ({len(ev)} events)")
