"""PLEDGE_SAFE_20260802 -- COVID-era combined: bond + real-MF + S1-F STRESS backcast + REAL
protective-put rungs (trades_PROT_PUT.csv already covers 2016-2026, incl. real 2020 option prices).
Does the hedge actually fix the -23.34% combined MaxDD found in the yield-only COVID rerun?
"""
import numpy as np
import pandas as pd
import datetime as dt

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
BC = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\SELLSIDE_20260710\covid_backcast\backcast_2020.csv"
SPOT_1MIN = ROOT + r"\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data\NIFTY 50_minute.csv"
N500 = ROOT + r"\datasets\index_daily\nifty500.parquet"
PROT_PUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\trades_PROT_PUT.csv"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PLEDGE_SAFE_20260802"

BOND0, MF0 = 5_000_000.0, 5_000_000.0
BOND_RATE = 0.08
LOT, MARGIN_RATE, MARGIN_CAP_FRAC = 75, 0.15, 0.40
HEDGE_FRACTION = 0.50

bc = pd.read_csv(BC, parse_dates=["day"])
s1 = bc[(bc["mode"] == "STRESS") & (bc["strat"] == "S1")].copy().sort_values("day")
sp = pd.read_csv(SPOT_1MIN, parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dcl = sp["close"].groupby(sp.index.date).last()
dcl.index = pd.to_datetime(dcl.index)
s1["spot"] = s1["day"].map(dcl)
s1 = s1.dropna(subset=["spot"]).set_index("day").sort_index()
print(f"STRESS S1 backcast rows: {len(s1)} | {s1.index.min().date()}..{s1.index.max().date()}")

pp_all = pd.read_csv(PROT_PUT, parse_dates=["entry_date", "roll_date"]).set_index("roll_date").sort_index()
pp = pp_all[(pp_all.index >= s1.index.min()) & (pp_all.index <= s1.index.max())]
print(f"Real protective-put rungs falling in this window: {len(pp)} -> dates: {list(pp.index.date)}")

n5 = pd.read_parquet(N500)
n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_localize(None).dt.normalize()
n5 = n5.set_index("date").sort_index()["close"]
mf_ret_lookup = n5.pct_change().fillna(0.0).to_dict()

all_dates = pd.date_range(s1.index.min(), s1.index.max(), freq="D")
bond, mf, cash_pnl = BOND0, MF0, 0.0
bond_daily_factor = (1 + BOND_RATE) ** (1 / 365.25)
rows = []
prev = all_dates[0]
for d in all_dates:
    if (d - prev).days > 0:
        bond *= bond_daily_factor
        mf *= (1 + mf_ret_lookup.get(d, 0.0))
    prev = d
    net_today = 0.0
    if d in s1.index:
        row = s1.loc[d]
        book_now = bond + mf
        margin_budget = MARGIN_CAP_FRAC * book_now
        margin_per_lot = float(row["spot"]) * LOT * MARGIN_RATE
        lots = int(margin_budget / margin_per_lot)
        net_today += lots * float(row["net"]) * LOT
    hedge_pnl_today = 0.0
    if d in pp.index:
        prow = pp.loc[d]
        hedge_notional = HEDGE_FRACTION * mf
        hedge_lots = round(hedge_notional / (float(prow["spot_entry"]) * LOT))
        hedge_pnl_today = hedge_lots * float(prow["net_pnl_pts"]) * LOT
        net_today += hedge_pnl_today
    cash_pnl += net_today
    total = bond + mf + cash_pnl
    rows.append(dict(date=d, bond=bond, mf=mf, cash_pnl=cash_pnl, total=total,
                      hedge_pnl_today=hedge_pnl_today, net_today_rs=net_today, book_now=bond + mf))

panel = pd.DataFrame(rows).set_index("date")
panel.to_csv(f"{OUT}/panel_covid_yield_plus_hedge.csv")

total = panel["total"]
dd = (total - total.cummax()) / total.cummax()
baseline = panel["bond"] + panel["mf"]
dd_base = (baseline - baseline.cummax()) / baseline.cummax()
crash_window = panel.loc["2020-02-19":"2020-04-10"]

print(f"\nCOVID-window rerun WITH {HEDGE_FRACTION:.0%}-notional protective put added to the yield overlay:")
print(f"  combined portfolio MaxDD: {dd.min():+.2%}  (worst date {dd.idxmin().date()})")
print(f"  bond+MF-only baseline MaxDD: {dd_base.min():+.2%}  (worst date {dd_base.idxmin().date()})")
print(f"  hedge P&L during 19Feb..10Apr-2020 crash window: Rs {crash_window['hedge_pnl_today'].sum():,.0f}")
print(f"  total net P&L (options+hedge combined) during crash window: Rs {crash_window['net_today_rs'].sum():,.0f}")
print(f"  [for comparison, yield-ONLY rerun (no hedge) showed: combined MaxDD -23.34%, "
      f"options P&L in crash window -Rs 744,700]")
