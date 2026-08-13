"""PLEDGE_SAFE_20260802 -- actual COVID-era stress rerun (not a proportional guess).
Reuses SELLSIDE_20260710/covid_backcast's STRESS-mode S1 model P&L (Black-Scholes on real 2020
minute spot, pessimistic IV path, validated corr vs real 2021-26 data) + REAL NIFTY 500 index
returns for the MF sleeve over the SAME Jan-2020..May-2021 window (before our real option data
starts) + bond accrual, sized with the SAME 40%-of-book dynamic margin model as the main run.
NOTE: the backcast has no F1/F2 veto applied (sim_day runs every Thursday unconditionally) -- this
makes the rerun somewhat MORE conservative/pessimistic than live rules would be, disclosed not corrected.
"""
import numpy as np
import pandas as pd
import datetime as dt

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
BC = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\SELLSIDE_20260710\covid_backcast\backcast_2020.csv"
SPOT_1MIN = ROOT + r"\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data\NIFTY 50_minute.csv"
N500 = ROOT + r"\datasets\index_daily\nifty500.parquet"

BOND0, MF0 = 5_000_000.0, 5_000_000.0
BOND_RATE = 0.08
LOT, MARGIN_RATE, MARGIN_CAP_FRAC = 75, 0.15, 0.40

bc = pd.read_csv(BC, parse_dates=["day"])
s1 = bc[(bc["mode"] == "STRESS") & (bc["strat"] == "S1")].copy().sort_values("day")

sp = pd.read_csv(SPOT_1MIN, parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dcl = sp["close"].groupby(sp.index.date).last()
dcl.index = pd.to_datetime(dcl.index)
s1["spot"] = s1["day"].map(dcl)
s1 = s1.dropna(subset=["spot"])
print(f"STRESS S1 backcast rows with spot matched: {len(s1)} | {s1['day'].min().date()}..{s1['day'].max().date()}")

n5 = pd.read_parquet(N500)
n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_localize(None).dt.normalize()
n5 = n5.set_index("date").sort_index()["close"]
mf_ret = n5.pct_change().fillna(0.0)
crash_ret = mf_ret[(mf_ret.index >= "2020-02-19") & (mf_ret.index <= "2020-03-23")]
print(f"NIFTY 500 real return, 2020-02-19..2020-03-23 (the actual COVID crash window): "
      f"{(1+crash_ret).prod()-1:+.1%} cumulative")

all_dates = pd.date_range(s1["day"].min(), s1["day"].max(), freq="D")
s1_idx = s1.set_index("day")
bond, mf, cash_pnl = BOND0, MF0, 0.0
bond_daily_factor = (1 + BOND_RATE) ** (1 / 365.25)
mf_ret_lookup = mf_ret.to_dict()
rows = []
prev = all_dates[0]
for d in all_dates:
    ndays = (d - prev).days
    if ndays > 0:
        bond *= bond_daily_factor ** ndays
        mf *= (1 + mf_ret_lookup.get(d, 0.0)) ** ndays if ndays > 1 else (1 + mf_ret_lookup.get(d, 0.0))
    prev = d
    lots, margin_used, net_rs = 0, 0.0, 0.0
    if d in s1_idx.index:
        row = s1_idx.loc[d]
        book_now = bond + mf
        margin_budget = MARGIN_CAP_FRAC * book_now
        margin_per_lot = float(row["spot"]) * LOT * MARGIN_RATE
        lots = int(margin_budget / margin_per_lot)
        margin_used = lots * margin_per_lot
        net_rs = lots * float(row["net"]) * LOT
        cash_pnl += net_rs
    total = bond + mf + cash_pnl
    rows.append(dict(date=d, bond=bond, mf=mf, cash_pnl=cash_pnl, total=total, lots=lots,
                      margin_used=margin_used, book_now=bond + mf, net_today_rs=net_rs))

panel = pd.DataFrame(rows).set_index("date")
panel.to_csv(ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PLEDGE_SAFE_20260802\panel_covid_stress.csv")

total = panel["total"]
dd = (total - total.cummax()) / total.cummax()
baseline = panel["bond"] + panel["mf"]
dd_base = (baseline - baseline.cummax()) / baseline.cummax()
crash_window = panel.loc["2020-02-19":"2020-04-10"]
print(f"\nCOVID-window rerun (Jan-2020..May-2021, STRESS-IV pessimistic options model + REAL NIFTY500 MF):")
print(f"  combined portfolio MaxDD: {dd.min():+.2%}  (worst date {dd.idxmin().date()})")
print(f"  baseline (bond+MF only, no options) MaxDD: {dd_base.min():+.2%}  (worst date {dd_base.idxmin().date()})")
print(f"  options overlay net P&L during 19-Feb..10-Apr-2020 crash window: Rs {crash_window['net_today_rs'].sum():,.0f}")
print(f"  worst single expiry-day options loss (whole rerun window): Rs {panel['net_today_rs'].min():,.0f} "
      f"({(panel['net_today_rs']/panel['book_now']).min():+.3%} of book)")
print(f"  max margin utilization vs 40% cap: {(panel['margin_used']/(0.40*panel['book_now'])).max():.1%} "
      f"(breach count: {(panel['margin_used'] > 0.40*panel['book_now'] + 1e-6).sum()})")
