"""PLEDGE_SAFE_20260802 -- CORRECTED COVID rerun, v2.
Fixes two red-team-confirmed bugs in run_covid_stress_rerun.py:
  1. F1/F2 vetoes were never applied to the covid_backcast STRESS/S1 series (the backcast script
     itself simulates every Thursday unconditionally) -- computed here from the same 1-min spot
     data used by the live spec, D-1 RSI5 >=80/<=20 and |D-1 ret|>1.5%, and applied (lots=0 on veto).
  2. margin_budget used SAME-DAY bond+mf value (mf's daily NAV is not known until EOD, after the
     09:20 entry decision) -- now uses D-1's book_now (the last value actually known before the
     trading day's entry), a real T3-class lookahead fix.
Also reruns the yield+hedge variant with the same two fixes for an apples-to-apples comparison.
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


def log(msg):
    print(msg, flush=True)


# ---- load backcast + spot + compute veto flags (D-1, matching S1F_SPEC.md exactly) ----
bc = pd.read_csv(BC, parse_dates=["day"])
s1 = bc[(bc["mode"] == "STRESS") & (bc["strat"] == "S1")].copy().sort_values("day")

sp = pd.read_csv(SPOT_1MIN, parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dcl = sp["close"].groupby(sp.index.date).last()
dcl.index = pd.to_datetime(dcl.index)

d = dcl.diff()
up = d.clip(lower=0).ewm(alpha=1 / 5, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1 / 5, adjust=False).mean()
rsi5 = (100 - 100 / (1 + up / dn)).shift(1)          # D-1 RSI5
pret = dcl.pct_change().shift(1) * 100                # D-1 return %

s1["spot"] = s1["day"].map(dcl)
s1 = s1.dropna(subset=["spot"])
s1["veto"] = s1["day"].map(lambda x: bool((rsi5.get(x, 50) >= 80) | (rsi5.get(x, 50) <= 20) | (abs(pret.get(x, 0)) > 1.5)))
s1 = s1.set_index("day").sort_index()
log(f"STRESS S1 backcast rows: {len(s1)} | veto rate: {s1['veto'].mean():.1%}")

crash = s1.loc["2020-02-20":"2020-04-10"]
log(f"CRASH WINDOW (20Feb-10Apr 2020): {len(crash)} scheduled days, "
    f"{int(crash['veto'].sum())} would be VETOED under live F1/F2 rules "
    f"({crash['veto'].mean():.0%})")
log(f"  2020-03-19 veto={bool(s1.loc['2020-03-19','veto']) if pd.Timestamp('2020-03-19') in s1.index else 'n/a'} | "
    f"2020-03-26 veto={bool(s1.loc['2020-03-26','veto']) if pd.Timestamp('2020-03-26') in s1.index else 'n/a'}")

pp_all = pd.read_csv(PROT_PUT, parse_dates=["entry_date", "roll_date"]).set_index("roll_date").sort_index()
pp = pp_all[(pp_all.index >= s1.index.min()) & (pp_all.index <= s1.index.max())]

n5 = pd.read_parquet(N500)
n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_localize(None).dt.normalize()
n5 = n5.set_index("date").sort_index()["close"]
mf_ret_lookup = n5.pct_change().fillna(0.0).to_dict()


def run(with_hedge):
    all_dates = pd.date_range(s1.index.min(), s1.index.max(), freq="D")
    bond, mf, cash_pnl = BOND0, MF0, 0.0
    bond_daily_factor = (1 + BOND_RATE) ** (1 / 365.25)
    rows = []
    prev = all_dates[0]
    book_now_prev = bond + mf   # D-1 book value, updated at END of each iteration
    for dte in all_dates:
        if (dte - prev).days > 0:
            bond *= bond_daily_factor
            mf *= (1 + mf_ret_lookup.get(dte, 0.0))
        prev = dte

        net_today = 0.0
        if dte in s1.index:
            row = s1.loc[dte]
            if not row["veto"]:
                margin_budget = MARGIN_CAP_FRAC * book_now_prev     # FIX: D-1 book, not same-day
                margin_per_lot = float(row["spot"]) * LOT * MARGIN_RATE
                lots = int(margin_budget / margin_per_lot)
                net_today += lots * float(row["net"]) * LOT

        if with_hedge and dte in pp.index:
            prow = pp.loc[dte]
            hedge_notional = HEDGE_FRACTION * mf
            hedge_lots = round(hedge_notional / (float(prow["spot_entry"]) * LOT))
            net_today += hedge_lots * float(prow["net_pnl_pts"]) * LOT

        cash_pnl += net_today
        total = bond + mf + cash_pnl
        rows.append(dict(date=dte, bond=bond, mf=mf, cash_pnl=cash_pnl, total=total, net_today_rs=net_today))
        book_now_prev = bond + mf   # becomes "D-1" for the NEXT iteration

    return pd.DataFrame(rows).set_index("date")


for label, with_hedge in [("YIELD_ONLY_corrected", False), ("YIELD_PLUS_HEDGE_corrected", True)]:
    panel = run(with_hedge)
    panel.to_csv(f"{OUT}/panel_covid_{label}.csv")
    total = panel["total"]
    dd = (total - total.cummax()) / total.cummax()
    baseline = panel["bond"] + panel["mf"]
    dd_base = (baseline - baseline.cummax()) / baseline.cummax()
    crash_window = panel.loc["2020-02-19":"2020-04-10"]
    log(f"\n=== {label} ===")
    log(f"  combined MaxDD: {dd.min():+.2%} (worst {dd.idxmin().date()}) | "
        f"baseline (bond+MF only) MaxDD: {dd_base.min():+.2%} (worst {dd_base.idxmin().date()})")
    log(f"  net options(+hedge) P&L during 19Feb-10Apr-2020 crash window: Rs {crash_window['net_today_rs'].sum():,.0f}")
    log(f"  vs RISK_LIMITS.md bar (book survives if drawdown <20%): "
        f"{'PASSES' if dd.min() > -0.20 else 'FAILS'} ({dd.min():+.2%})")
