"""
MOMENTUM-TRIGGER CONTINUATION STUDY (daily-bar proxy — see caveat below)
=========================================================================
DATA CONSTRAINT (verified): the project has NO per-stock intraday SPOT data
(only daily bars for 1,039 F&O/N500 stocks, 2021-2026). A true 15-min Opening
Range Breakout needs the stock's own 9:15-9:30 intraday high/low, which does
not exist on disk for individual equities (only the NIFTY INDEX has 1-min
spot history — tested separately as a genuine ORB in nifty_index_orb.py).

So THIS script tests the economic hypothesis behind "ORB after a momentum
trigger" using what we actually have: does a stock that satisfies a trigger
condition continue trending over the NEXT session(s) (open-to-close, and
multi-day), using strictly prior-day/point-in-time information for the
trigger itself. This is a daily-bar continuation/reversal test, not literal
ORB — labeled as such throughout.

Triggers tested (all computed using ONLY data known before today's open):
  T1: prev-day return >= +5%
  T2: prev-day return >= +10%
  T3: trailing 20-trading-day (~28 calendar day) return >= +30%
  T4: today's gap-up at open >= +5% vs prior close (known at 09:15, tradeable)
  T5: yesterday's gap-up was >= +5% (a lagged variant of T4)

Forward outcomes measured (no lookahead):
  - next-day open-to-close return (day after trigger fires)
  - next-day full-day (prior close -> next close) return
  - 5-day and 10-day forward returns from trigger-day close
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"

print("Loading daily stock panel...")
p = pd.read_parquet(os.path.join(BASE, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
print(f"{len(p):,} rows, {p['symbol'].nunique()} symbols, {p['date'].min().date()} -> {p['date'].max().date()}")

rows = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 40:
        continue
    cl = g["close"]; op = g["open"]
    ret1 = cl.pct_change() * 100
    gap = (op / cl.shift(1) - 1) * 100
    ret20 = cl.pct_change(20) * 100   # ~28 calendar days of trading

    g["prev_ret1_pct"] = ret1.shift(1)         # yesterday's return (known before today)
    g["ret20_prior_pct"] = ret20.shift(1)       # trailing 20d return as of yesterday's close
    g["today_gap_pct"] = gap                    # today's own gap (known at open)
    g["prev_gap_pct"] = gap.shift(1)            # yesterday's gap

    # forward outcomes from TODAY (the day the trigger condition is evaluated / tradeable)
    g["fwd_next_day_oc_pct"] = (cl.shift(-2) / op.shift(-1) - 1) * 100   # next day open->close
    g["fwd_next_day_full_pct"] = (cl.shift(-1) / cl - 1) * 100           # today close -> next close
    g["fwd_5d_pct"] = (cl.shift(-5) / cl - 1) * 100
    g["fwd_10d_pct"] = (cl.shift(-10) / cl - 1) * 100
    rows.append(g)

d = pd.concat(rows, ignore_index=True)
d = d.dropna(subset=["fwd_next_day_full_pct"])

def report(mask, label, n_min=30):
    sub = d[mask]
    base = d[~mask]
    if len(sub) < n_min:
        print(f"{label:<28} n={len(sub):>6}  (too few, skipped)")
        return
    for col, cl in [("fwd_next_day_oc_pct", "nextday O->C"), ("fwd_next_day_full_pct", "nextday full"),
                    ("fwd_5d_pct", "fwd 5d"), ("fwd_10d_pct", "fwd 10d")]:
        m_s, m_b = sub[col].mean(), base[col].mean()
        w_s = (sub[col] > 0).mean() * 100
        print(f"{label:<28} [{cl:<13}] n={len(sub):>6} mean {m_s:>6.3f}% (base {m_b:>6.3f}%) win {w_s:>5.1f}%")
    print()

print("\n" + "="*100)
print("TRIGGER CONTINUATION TEST (daily-bar proxy, strictly PIT)")
print("="*100)
report(d["prev_ret1_pct"] >= 5, "T1: prev day >=+5%")
report(d["prev_ret1_pct"] >= 10, "T2: prev day >=+10%")
report(d["ret20_prior_pct"] >= 30, "T3: trailing 20d >=+30%")
report(d["today_gap_pct"] >= 5, "T4: today gap >=+5%")
report(d["prev_gap_pct"] >= 5, "T5: yesterday gap >=+5%")
# combos
report((d["prev_ret1_pct"] >= 5) & (d["today_gap_pct"] >= 2), "T1 + confirming gap today")
report((d["ret20_prior_pct"] >= 30) & (d["prev_ret1_pct"] >= 3), "T3 + fresh trigger day")

d.to_parquet(os.path.join(OUT, "momentum_trigger_daily.parquet"))
print("Saved momentum_trigger_daily.parquet")
