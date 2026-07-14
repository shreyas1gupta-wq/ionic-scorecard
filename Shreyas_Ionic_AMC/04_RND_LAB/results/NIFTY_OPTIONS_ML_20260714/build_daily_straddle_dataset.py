"""
STEP 1: Build a per-trading-day dataset of REAL short-ATM-straddle payoffs from
genuine NIFTY option chain data (262 expiry files, 1-min bars, 2021-05 -> 2026-06),
plus a strict point-in-time feature set for ML.

For each trading day:
  - Select the CURRENT-WEEK (nearest) expiry contract only (DTE 0-7), to avoid
    double-counting a calendar day across overlapping weekly/monthly contracts.
  - ATM strike = nearest listed strike to spot at entry.
  - Entry = first 1-min bar at/after 09:20. Exit = last bar at/before 15:15.
  - Short straddle payoff_pct = (entry_CE+entry_PE - exit_CE-exit_PE) / spot_entry
    (positive = seller profits, i.e. premium decayed)
  - Also record entry_premium_pct (richness), DTE, day-of-week, expiry date.

Output: daily_straddle_base.csv (~1200-1300 rows, one per trading day)
"""
import os, glob, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"
os.makedirs(OUT, exist_ok=True)

ENTRY_T = pd.to_datetime("09:20:00").time()
EXIT_T = pd.to_datetime("15:15:00").time()

# ---------------- Load spot 1-min (for ATM strike selection + spot entry/exit) ----------------
print("Loading NIFTY spot 1-min...")
spot = pd.read_parquet(os.path.join(BASE, "processed", "nifty_1min.parquet")).reset_index()
spot = spot.rename(columns={spot.columns[0]: "dt"}) if "dt" not in spot.columns else spot
spot["dt"] = pd.to_datetime(spot["dt"])
spot["date"] = spot["dt"].dt.date
spot["time"] = spot["dt"].dt.time
print(f"  {len(spot):,} bars, {spot['date'].nunique()} days")

spot_entry = (spot[spot["time"] >= ENTRY_T].sort_values("dt").groupby("date").first()["close"]).to_dict()
spot_exit = (spot[spot["time"] <= EXIT_T].sort_values("dt").groupby("date").last()["close"]).to_dict()
spot_open = (spot.sort_values("dt").groupby("date").first()["open"]).to_dict()
spot_close = (spot.sort_values("dt").groupby("date").last()["close"]).to_dict()

# daily closes for realized-vol features (strict PIT: only past days used later)
daily_close = pd.Series(spot_close).sort_index()
daily_close.index = pd.to_datetime(daily_close.index)
daily_ret = daily_close.pct_change()

print("Loading VIX 1-min...")
vix = pd.read_parquet(os.path.join(BASE, "processed", "vix_1min.parquet")).reset_index()
vix = vix.rename(columns={vix.columns[0]: "dt"}) if "dt" not in vix.columns else vix
vix["dt"] = pd.to_datetime(vix["dt"])
vix["date"] = vix["dt"].dt.date
vix["time"] = vix["dt"].dt.time
vix_entry = (vix[vix["time"] >= ENTRY_T].sort_values("dt").groupby("date").first()["vix"]).to_dict()
vix_close = (vix.sort_values("dt").groupby("date").last()["vix"]).to_dict()

# ---------------- Process each expiry file: current-week contract only ----------------
files = sorted(glob.glob(os.path.join(BASE, "raw", "hf_index_options_1m", "options", "NIFTY", "*.parquet")))
print(f"\nProcessing {len(files)} NIFTY option expiry files...")

best_dte = {}   # trading_day -> current best (dte, expiry_str)
rows_by_day = {}

for fi, f in enumerate(files):
    expiry_str = os.path.basename(f).replace(".parquet", "")
    expiry_date = pd.to_datetime(expiry_str).date()
    d = pd.read_parquet(f, columns=["trading_day", "timestamp", "strike", "option_type", "close"])
    d["trading_day"] = pd.to_datetime(d["trading_day"]).dt.date
    d["time"] = pd.to_datetime(d["timestamp"]).dt.time

    for day, g in d.groupby("trading_day"):
        dte = (expiry_date - day).days
        if dte < 0 or dte > 7:
            continue
        prev = best_dte.get(day)
        if prev is not None and prev <= dte:
            continue  # already have an equal-or-nearer expiry for this day
        se = spot_entry.get(day)
        if se is None or np.isnan(se):
            continue
        # ATM strike = nearest available strike in this contract
        strikes = g["strike"].unique()
        if len(strikes) == 0:
            continue
        atm = strikes[np.argmin(np.abs(strikes - se))]
        gs = g[g["strike"] == atm]
        ce = gs[gs["option_type"] == "CE"].sort_values("time")
        pe = gs[gs["option_type"] == "PE"].sort_values("time")
        if len(ce) < 2 or len(pe) < 2:
            continue
        ce_entry_row = ce[ce["time"] >= ENTRY_T]
        pe_entry_row = pe[pe["time"] >= ENTRY_T]
        ce_exit_row = ce[ce["time"] <= EXIT_T]
        pe_exit_row = pe[pe["time"] <= EXIT_T]
        if len(ce_entry_row) == 0 or len(pe_entry_row) == 0 or len(ce_exit_row) == 0 or len(pe_exit_row) == 0:
            continue
        ce_e = ce_entry_row.iloc[0]["close"]; pe_e = pe_entry_row.iloc[0]["close"]
        ce_x = ce_exit_row.iloc[-1]["close"]; pe_x = pe_exit_row.iloc[-1]["close"]

        best_dte[day] = dte
        rows_by_day[day] = {
            "trading_day": day, "expiry": expiry_str, "dte": dte,
            "atm_strike": int(atm), "spot_entry": se, "spot_exit": spot_exit.get(day, np.nan),
            "ce_entry": ce_e, "pe_entry": pe_e, "ce_exit": ce_x, "pe_exit": pe_x,
            "vix_entry": vix_entry.get(day, np.nan), "vix_prevclose": np.nan,  # filled below
        }
    if (fi + 1) % 50 == 0:
        print(f"  {fi+1}/{len(files)} files processed, {len(rows_by_day)} days so far")

print(f"\nTotal unique trading days with a valid current-week ATM straddle: {len(rows_by_day)}")
df = pd.DataFrame(list(rows_by_day.values())).sort_values("trading_day").reset_index(drop=True)
df["trading_day"] = pd.to_datetime(df["trading_day"])

# ---------------- Core payoff + richness ----------------
df["entry_premium"] = df["ce_entry"] + df["pe_entry"]
df["exit_premium"] = df["ce_exit"] + df["pe_exit"]
df["payoff_pct"] = (df["entry_premium"] - df["exit_premium"]) / df["spot_entry"] * 100   # short-straddle, % of spot
df["entry_premium_pct"] = df["entry_premium"] / df["spot_entry"] * 100                    # richness (contemporaneous, non-lookahead vs itself)
df["day_ret_pct"] = (df["spot_exit"] - df["spot_entry"]) / df["spot_entry"] * 100
df["abs_day_ret_pct"] = df["day_ret_pct"].abs()

# vix_prevclose (yesterday's VIX close - strictly PIT)
vc = pd.Series(vix_close)
vc.index = pd.to_datetime(vc.index)
vc = vc.sort_index()
df = df.set_index("trading_day")
df["vix_prevclose"] = vc.shift(1).reindex(df.index)
df["vix_chg"] = df["vix_entry"] - df["vix_prevclose"]

# realized vol features from PAST days only (shift ensures no lookahead)
dr = daily_ret.sort_index()
rv5 = dr.rolling(5).std() * np.sqrt(252) * 100
rv10 = dr.rolling(10).std() * np.sqrt(252) * 100
rv20 = dr.rolling(20).std() * np.sqrt(252) * 100
df["rv5_prior"] = rv5.shift(1).reindex(df.index)
df["rv10_prior"] = rv10.shift(1).reindex(df.index)
df["rv20_prior"] = rv20.shift(1).reindex(df.index)
df["ivrv_proxy"] = df["entry_premium_pct"] / df["rv20_prior"].replace(0, np.nan)  # richness vs realized vol

# gap (today's entry vs yesterday close) - known at entry time, no lookahead
prev_close_s = daily_close.sort_index().shift(1)
df["gap_pct"] = ((df["spot_entry"] - prev_close_s.reindex(df.index)) / prev_close_s.reindex(df.index) * 100)

# prior day's realized straddle payoff (mean-reversion/momentum in vol-selling regime)
df = df.reset_index()
df["prior_payoff_1d"] = df["payoff_pct"].shift(1)
df["prior_payoff_5d_mean"] = df["payoff_pct"].shift(1).rolling(5).mean()

df["dow"] = df["trading_day"].dt.dayofweek
df["is_0dte"] = (df["dte"] == 0).astype(int)
df["month"] = df["trading_day"].dt.month
df["year"] = df["trading_day"].dt.year

df.to_csv(os.path.join(OUT, "daily_straddle_base.csv"), index=False)
print(f"\nSaved daily_straddle_base.csv: {df.shape}")
print(f"Date range: {df['trading_day'].min().date()} -> {df['trading_day'].max().date()}")
print(f"\nUnconditional short-straddle stats (no ML, no costs):")
print(f"  mean payoff {df['payoff_pct'].mean():.3f}% | win rate {(df['payoff_pct']>0).mean()*100:.1f}% | "
      f"Sharpe(raw,daily->ann) {df['payoff_pct'].mean()/df['payoff_pct'].std()*np.sqrt(252):.2f}")
print(f"\nBy year:")
print(df.groupby("year")["payoff_pct"].agg(["count","mean",lambda x: (x>0).mean()*100]).to_string())
