"""PROTECTIVE_PUT_20260802 -- fix: the earlier underlying+hedge panels only updated hedge P&L at
ROLL dates (~monthly), leaving the hedge's mark-to-market value STALE in between -- this can hide or
distort the true intra-cycle drawdown if the underlying's worst day falls mid-cycle rather than on
a roll date. This script marks each REAL rung's actual held strikes (near_strike, far_strike, same
expiry, from trades_BACKSPREAD_1x2_10pct.csv) to market EVERY trading day using the real daily CLOSE
price from nifty_optidx_all_traded.parquet, not just at entry/roll. Also runs BOTH 100% and 50%
notional hedge fractions on the SAME daily-marked basis, real 2016-2026 data only (no modeled segment).
"""
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LEVEL = ROOT + r"\results\factor_replication\20260704_perf_table\level_NIFTY50_official.csv"
REAL_TRADES = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\trades_BACKSPREAD_1x2_10pct.csv"
ALL_TRADED = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\nifty_optidx_all_traded.parquet"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

LOT = 75
CAP0 = 1_000_000.0
COST_PER_LEG_RT = 1.77

lvl = pd.read_csv(LEVEL, parse_dates=["date"]).set_index("date").sort_index()["level"]
bs = pd.read_csv(REAL_TRADES, parse_dates=["entry_date", "roll_date", "expiry"]).sort_values("entry_date").reset_index(drop=True)
print(f"REAL backspread rungs: n={len(bs)} | {bs['entry_date'].min().date()} .. {bs['roll_date'].max().date()}")

print("loading option chain for daily marks ...")
tbl = pd.read_parquet(ALL_TRADED).set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()


def pe_close(expiry, K):
    try:
        return tbl.loc[(expiry, K, "PE")]["CLOSE"]
    except KeyError:
        return None


# ---- build a DAILY hedge-P&L series (per 1 lot) covering every trading day of every rung ----
daily_rows = []
for i, r in bs.iterrows():
    near_s = pe_close(r["expiry"], r["near_strike"])
    far_s = pe_close(r["expiry"], r["far_strike"])
    if near_s is None or far_s is None:
        print(f"  WARNING rung {i} ({r['entry_date'].date()}): missing strike series, skipped in daily marks")
        continue
    days = near_s.index[(near_s.index >= r["entry_date"]) & (near_s.index <= r["roll_date"])]
    days = days.intersection(far_s.index)
    if len(days) == 0:
        continue
    near_path = near_s.loc[days]
    far_path = far_s.loc[days]
    # position value each day (1 lot basis): SHORT 1x near + LONG 2x far = -(near) + 2*(far)
    pos_value = -near_path + 2 * far_path
    entry_pos_value = -r["near_entry"] + 2 * r["far_entry"]
    # daily P&L = change in position value from prior day; first day's P&L = change from ENTRY cost basis
    daily_pnl = pos_value.diff()
    daily_pnl.iloc[0] = pos_value.iloc[0] - entry_pos_value
    # costs charged once, on entry day (3 legs round-trip worth, matches the monthly convention)
    daily_pnl.iloc[0] -= 3 * COST_PER_LEG_RT
    for d, pnl in daily_pnl.items():
        daily_rows.append(dict(date=d, rung=i, daily_pnl_pts=pnl, spot_entry=r["spot_entry"]))

daily = pd.DataFrame(daily_rows)
# where rungs are back-to-back (new rung enters same day prior rolls off), sum same-day pnl
daily_agg = daily.groupby("date").agg(daily_pnl_pts=("daily_pnl_pts", "sum"),
                                       spot_entry=("spot_entry", "last")).reset_index()
daily_agg = daily_agg.sort_values("date").set_index("date")

check_sum = daily.groupby("rung")["daily_pnl_pts"].sum()
recon = pd.concat([check_sum.rename("daily_sum"), bs["net_pnl_pts"] + 3 * COST_PER_LEG_RT], axis=1)
print(f"reconciliation check (daily-summed gross P&L vs rung-level gross P&L, should match closely): "
      f"max abs diff = {(recon['daily_sum'] - recon['net_pnl_pts']).abs().max():.2f} pts "
      f"(0 = perfect daily/monthly reconciliation)")

daily_agg.to_csv(f"{OUT}/BACKSPREAD_daily_mtm_pnl.csv")
print(f"saved daily hedge P&L series: {len(daily_agg)} trading days, "
      f"{daily_agg.index.min().date()} .. {daily_agg.index.max().date()}")


def run_hedge(hedge_fraction):
    all_dates = lvl.index
    all_dates = all_dates[(all_dates >= daily_agg.index.min()) & (all_dates <= daily_agg.index.max())]
    underlying_units = CAP0 / lvl.loc[all_dates[0]]
    rows = []
    cash_pnl = 0.0
    for d in all_dates:
        underlying_value = underlying_units * lvl.loc[d]
        hedge_pnl_today = 0.0
        if d in daily_agg.index:
            row = daily_agg.loc[d]
            lots = round(hedge_fraction * underlying_value / (float(row["spot_entry"]) * LOT))
            hedge_pnl_today = lots * float(row["daily_pnl_pts"]) * LOT
            cash_pnl += hedge_pnl_today
        combined = underlying_value + cash_pnl
        rows.append(dict(date=d, underlying_value=underlying_value, cash_pnl=cash_pnl,
                          combined=combined, hedge_pnl_today=hedge_pnl_today))
    return pd.DataFrame(rows).set_index("date")


for frac, label in [(1.00, "100%"), (0.50, "50%")]:
    panel = run_hedge(frac)
    panel.to_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_DAILY_{label.replace('%','pct')}.csv")
    yrs = (panel.index[-1] - panel.index[0]).days / 365.25
    c_u = (panel["underlying_value"].iloc[-1] / panel["underlying_value"].iloc[0]) ** (1 / yrs) - 1
    c_c = (panel["combined"].iloc[-1] / panel["combined"].iloc[0]) ** (1 / yrs) - 1
    dd_u = ((panel["underlying_value"] - panel["underlying_value"].cummax()) / panel["underlying_value"].cummax() * 100)
    dd_c = ((panel["combined"] - panel["combined"].cummax()) / panel["combined"].cummax() * 100)
    print(f"\n=== {label} notional hedge, DAILY mark-to-market, real data only ===")
    print(f"  underlying only:  CAGR {c_u:+.2%} | MaxDD {dd_u.min():+.2f}% ({dd_u.idxmin().date()})")
    print(f"  + hedge ({label}): CAGR {c_c:+.2%} | MaxDD {dd_c.min():+.2f}% ({dd_c.idxmin().date()})")
    print(f"  MaxDD delta: {dd_c.min()-dd_u.min():+.2f}pts | hedge total P&L: Rs {cash_pnl if False else panel['hedge_pnl_today'].sum():,.0f}")
