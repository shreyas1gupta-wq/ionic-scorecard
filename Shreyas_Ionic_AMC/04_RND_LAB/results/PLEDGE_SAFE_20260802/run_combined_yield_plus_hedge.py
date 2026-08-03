"""PLEDGE_SAFE_20260802 -- combined: bond + real-MF + S1-F yield overlay + protective-put insurance,
partly funded by the yield. Reuses ALREADY-COMPUTED trade-level data from both prior scripts
(no re-simulation of option prices) -- final synthesis test.
"""
import numpy as np
import pandas as pd
import datetime as dt

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
TRADES = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\SELLSIDE_20260710\final_three\final_three_trades.csv"
SPOT_1MIN = ROOT + r"\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data\NIFTY 50_minute.csv"
N500 = ROOT + r"\datasets\index_daily\nifty500.parquet"
PROT_PUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\trades_PROT_PUT.csv"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PLEDGE_SAFE_20260802"

BOND0, MF0 = 5_000_000.0, 5_000_000.0
BOND_RATE = 0.08
LOT, MARGIN_RATE, MARGIN_CAP_FRAC = 75, 0.15, 0.40
HEDGE_FRACTION = 0.50   # hedge 50% of current MF notional with the protective put


def load_s1():
    tr = pd.read_csv(TRADES)
    s1 = tr[tr.strat == "S1"].copy()
    s1["date"] = pd.to_datetime(s1.day)
    sp = pd.read_csv(SPOT_1MIN, parse_dates=["date"]).set_index("date").sort_index()
    sp = sp[sp.index.time >= dt.time(9, 15)]
    dcl = sp["close"].groupby(sp.index.date).last()
    dcl.index = pd.to_datetime(dcl.index)
    s1["spot"] = s1["date"].map(dcl)
    s1 = s1.dropna(subset=["spot"]).sort_values("date").reset_index(drop=True)
    d = dcl.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 5, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 5, adjust=False).mean()
    rsi5 = (100 - 100 / (1 + up / dn)).shift(1)
    pret = dcl.pct_change().shift(1) * 100
    s1["veto"] = s1["date"].map(lambda x: bool((rsi5.get(x, 50) >= 80) | (rsi5.get(x, 50) <= 20) | (abs(pret.get(x, 0)) > 1.5)))
    dlogret = np.log(dcl / dcl.shift(1))
    rv3 = dlogret.rolling(3).std() * np.sqrt(252)
    med1y = rv3.rolling(252, min_periods=60).median()
    crash_flag = (rv3.shift(1) > 2 * med1y.shift(1)).fillna(False)
    s1["crash_halve"] = s1["date"].map(lambda x: bool(crash_flag.get(x, False)))
    return s1.set_index("date")


def load_prot_put():
    pp = pd.read_csv(PROT_PUT, parse_dates=["entry_date", "roll_date"])
    return pp.set_index("roll_date").sort_index()   # P&L attributed to roll/exit date, matches S1 convention


def load_mf_ret(start, end):
    n5 = pd.read_parquet(N500)
    n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_localize(None).dt.normalize()
    n5 = n5.set_index("date").sort_index()["close"]
    n5 = n5[(n5.index >= start) & (n5.index <= end)]
    return n5.pct_change().fillna(0.0).to_dict()


def main():
    s1 = load_s1()
    pp = load_prot_put()
    print(f"S1-F events: {len(s1)} | Protective-put rungs: {len(pp)} "
          f"({pp.index.min().date()}..{pp.index.max().date()})")

    start, end = s1.index.min(), s1.index.max()
    mf_ret_lookup = load_mf_ret(start - pd.Timedelta(days=5), end)

    all_dates = pd.date_range(start, end, freq="D")
    bond, mf, cash_pnl = BOND0, MF0, 0.0
    bond_daily_factor = (1 + BOND_RATE) ** (1 / 365.25)
    rows = []
    prev = all_dates[0]
    for d in all_dates:
        if (d - prev).days > 0:
            bond *= bond_daily_factor
            mf *= (1 + mf_ret_lookup.get(d, 0.0))
        prev = d

        lots, net_today = 0, 0.0
        if d in s1.index:
            row = s1.loc[d]
            book_now = bond + mf
            margin_budget = MARGIN_CAP_FRAC * book_now
            margin_per_lot = float(row["spot"]) * LOT * MARGIN_RATE
            if not row["veto"]:
                lots = int(margin_budget / margin_per_lot)
                if row["crash_halve"]:
                    lots = lots // 2
            net_today += lots * float(row["net"]) * LOT

        hedge_lots, hedge_pnl_today = 0, 0.0
        if d in pp.index:
            prow = pp.loc[d]
            hedge_notional = HEDGE_FRACTION * mf
            hedge_lots = round(hedge_notional / (float(prow["spot_entry"]) * LOT))
            hedge_pnl_today = hedge_lots * float(prow["net_pnl_pts"]) * LOT
            net_today += hedge_pnl_today

        cash_pnl += net_today
        total = bond + mf + cash_pnl
        rows.append(dict(date=d, bond=bond, mf=mf, cash_pnl=cash_pnl, total=total,
                          s1_lots=lots, hedge_lots=hedge_lots, hedge_pnl_today=hedge_pnl_today,
                          net_today_rs=net_today, book_now=bond + mf))

    panel = pd.DataFrame(rows).set_index("date")
    panel.to_csv(f"{OUT}/panel_yield_plus_hedge.csv")

    total = panel["total"]
    yrs = (total.index[-1] - total.index[0]).days / 365.25
    cagr = (total.iloc[-1] / total.iloc[0]) ** (1 / yrs) - 1
    dd = (total - total.cummax()) / total.cummax()
    baseline = panel["bond"] + panel["mf"]
    dd_base = (baseline - baseline.cummax()) / baseline.cummax()
    hedge_total_cost = panel["hedge_pnl_today"].sum()
    s1_total = panel["net_today_rs"].sum() - hedge_total_cost

    print(f"\nCOMBINED (yield overlay + {HEDGE_FRACTION:.0%}-notional protective put), REAL MF returns:")
    print(f"  final Rs {total.iloc[-1]:,.0f} | CAGR {cagr:+.2%} | MaxDD {dd.min():+.2%} (worst {dd.idxmin().date()})")
    print(f"  vs bond+MF baseline: CAGR {((baseline.iloc[-1]/baseline.iloc[0])**(1/yrs)-1):+.2%} | "
          f"MaxDD {dd_base.min():+.2%} (worst {dd_base.idxmin().date()})")
    print(f"  S1-F yield total over period: Rs {s1_total:,.0f} | hedge total cost over period: Rs {hedge_total_cost:,.0f} "
          f"(net of hedge, yield alone would have added Rs {s1_total:,.0f})")
    print(f"  hedge P&L during 19Feb-10Apr-2020-equivalent... (out of sample range, this run is 2021-2026 only)")


if __name__ == "__main__":
    main()
