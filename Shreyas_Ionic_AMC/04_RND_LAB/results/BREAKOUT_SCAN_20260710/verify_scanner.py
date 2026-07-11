"""
Verify: do my replicated scanner signals match the actual Chartlink signals
from the 9-month CSV in the overlapping window (Nov 2025 - Jul 2026)?
For every Chartlink signal my scanner missed, diagnose WHICH condition failed.
"""
import os, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (1).csv"

# ---------------- Load Chartlink actual signals ----------------
cl = pd.read_csv(SIG_CSV)
cl["Date"] = pd.to_datetime(cl["Date"], format="%d-%m-%Y")
cl = cl.rename(columns={"Date": "date", "Symbol": "symbol"})
print(f"Chartlink signals: {len(cl)} rows, {cl['symbol'].nunique()} symbols, "
      f"{cl['date'].min().date()} -> {cl['date'].max().date()}")

# ---------------- Load my replicated signals ----------------
mine = pd.read_csv(os.path.join(OUT, "backtest_6yr_trades.csv"), parse_dates=["signal_date"])
win_start, win_end = cl["date"].min(), cl["date"].max()
mine_w = mine[(mine["signal_date"] >= win_start) & (mine["signal_date"] <= win_end)]
print(f"My signals in same window: {len(mine_w)} rows, {mine_w['symbol'].nunique()} symbols")

# ---------------- Match on (date, symbol) ----------------
cl_set = set(zip(cl["date"], cl["symbol"]))
my_set = set(zip(mine_w["signal_date"], mine_w["symbol"]))

exact_match = cl_set & my_set
cl_only = cl_set - my_set          # Chartlink flagged, I missed
my_only = my_set - cl_set          # I flagged, Chartlink didn't

print(f"\n=== MATCH RESULTS ===")
print(f"  Exact matches (same date+symbol): {len(exact_match)} / {len(cl_set)} Chartlink signals ({len(exact_match)/len(cl_set)*100:.0f}%)")
print(f"  Chartlink-only (I missed):        {len(cl_only)}")
print(f"  Mine-only (extra signals):        {len(my_only)}")

# +/- 1 day tolerance match
cl_pm1 = set()
for d, s in cl_only:
    for dd in [-1, 1]:
        if (d + pd.Timedelta(days=dd), s) in my_set:
            cl_pm1.add((d, s))
            break
print(f"  Of missed, matched within +/-1 day: {len(cl_pm1)}")

# ---------------- Diagnose every miss ----------------
print(f"\n=== DIAGNOSING {len(cl_only)} MISSED SIGNALS ===")
panel = pd.read_parquet(os.path.join(OUT, "stitched_daily_panel.parquet"))
panel_syms = set(panel["symbol"].unique())

sym_data = {}
for sym, g in panel.groupby("symbol"):
    sym_data[sym] = g.sort_values("date").reset_index(drop=True)

def diagnose(sym, sig_date):
    """Re-run each scanner criterion; return the FIRST reason it fails."""
    if sym not in sym_data:
        return "NO_DATA: symbol not in our panel"
    df = sym_data[sym]
    loc = df[df["date"] == sig_date].index
    if len(loc) == 0:
        return "NO_BAR: no data row on signal date"
    j = loc[0]
    if j < 25:
        return "INSUFFICIENT_HISTORY: <25 prior bars for indicators"

    d = df.iloc[max(0, j-30):j+1].copy()
    row = df.iloc[j]

    # indicators (same as backtest_6yr.py)
    closes = df["close"].iloc[:j+1]
    sma20 = closes.rolling(20).mean().iloc[-1]
    std20 = closes.rolling(20).std().iloc[-1]
    upper_bb = sma20 + 2 * std20
    vol_avg20 = df["volume"].iloc[:j+1].rolling(20).mean().iloc[-1]
    prev_high5 = df["high"].iloc[max(0,j-5):j].max()  # prior 5 days' high

    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    ag = gain.ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
    al = loss.ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
    rsi = 100 - 100 / (1 + ag / al) if al > 0 else 100

    prev_range = (df["high"].iloc[j-1] - df["low"].iloc[j-1]) / df["close"].iloc[j-1]
    rng = ((df["high"] - df["low"]) / df["close"]).iloc[:j]
    avg_range10 = rng.rolling(10).mean().iloc[-1]

    chg = (row["close"] - df["close"].iloc[j-1]) / df["close"].iloc[j-1] * 100

    fails = []
    if row["turnover_cr"] < 25:
        fails.append(f"TURNOVER {row['turnover_cr']:.1f}cr < 25cr")
    if row["close"] <= prev_high5 * 1.01:
        fails.append(f"BREAKOUT close {row['close']:.1f} <= 5d-high*1.01 {prev_high5*1.01:.1f}")
    if rsi <= 60:
        fails.append(f"RSI {rsi:.1f} <= 60")
    if row["volume"] <= 2 * vol_avg20:
        fails.append(f"VOLUME {row['volume']/vol_avg20:.2f}x <= 2x")
    if row["close"] <= upper_bb:
        fails.append(f"BB close {row['close']:.1f} <= upperBB {upper_bb:.1f}")
    if pd.notna(prev_range) and pd.notna(avg_range10) and prev_range > 1.5 * avg_range10:
        fails.append(f"COMPRESSION prev-range {prev_range*100:.1f}% > 1.5x avg {avg_range10*100:.1f}%")
    if chg < 3:
        fails.append(f"CHANGE {chg:.1f}% < 3%")

    return " | ".join(fails) if fails else "ALL PASS (should have matched?!)"

reasons = {}
detail_rows = []
for d, s in sorted(cl_only):
    r = diagnose(s, d)
    key = r.split(":")[0].split(" ")[0]
    reasons[key] = reasons.get(key, 0) + 1
    detail_rows.append({"date": d.date(), "symbol": s, "reason": r})

print(f"\n  Failure reason summary (first-listed reason):")
for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"    {k:<22} {v}")

print(f"\n  Full detail (first 60):")
for r in detail_rows[:60]:
    print(f"    {r['date']} {r['symbol']:<15} {r['reason']}")

pd.DataFrame(detail_rows).to_csv(os.path.join(OUT, "scanner_verify_misses.csv"), index=False)

# ---------------- Also: percent of Chartlink symbols in our panel ----------------
cl_syms = set(cl["symbol"].unique())
in_panel = cl_syms & panel_syms
print(f"\n=== UNIVERSE CHECK ===")
print(f"  Chartlink unique symbols: {len(cl_syms)}")
print(f"  Present in our stitched panel: {len(in_panel)} ({len(in_panel)/len(cl_syms)*100:.0f}%)")
missing_syms = sorted(cl_syms - panel_syms)
print(f"  Missing from panel entirely: {len(missing_syms)}: {missing_syms[:25]}")

# ---------------- Extra signals analysis (mine-only) ----------------
print(f"\n=== MY EXTRA SIGNALS (I flagged, Chartlink didn't) ===")
my_only_df = pd.DataFrame(sorted(my_only), columns=["date", "symbol"])
my_only_df["month"] = pd.to_datetime(my_only_df["date"]).dt.to_period("M")
print(my_only_df.groupby("month").size().to_string())
print(f"\n  Sample extras: {[(str(d.date()), s) for d, s in sorted(my_only)[:15]]}")

print(f"\nSaved: scanner_verify_misses.csv")
