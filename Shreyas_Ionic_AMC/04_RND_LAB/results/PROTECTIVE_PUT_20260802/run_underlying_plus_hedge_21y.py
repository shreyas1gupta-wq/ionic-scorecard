"""PROTECTIVE_PUT_20260802 -- CORRECTION: Principal meant UNDERLYING+HEDGE vs UNDERLYING alone,
not hedge-P&L vs underlying. Rebuilds the 21y comparison as:
  Portfolio A: Rs 10L in NIFTY 50 (price index, no dividends), held throughout, unhedged.
  Portfolio B: same NIFTY 50 holding PLUS the backspread (sell 1x 2.5% OTM PE / buy 2x 10% OTM PE,
    30D, roll T-5) sized to hedge 100% of the CURRENT underlying notional at each roll date
    (lots = underlying_value / (spot_at_entry x 75), recomputed every rung as the underlying moves).
Uses the already-built 21y backspread series (BACKSPREAD_21Y_full_series.csv: 116 real 2016-2026
rungs + 128 calibrated-and-bias-corrected modeled 2005-2016 rungs) verbatim -- no re-simulation.
"""
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LEVEL = ROOT + r"\results\factor_replication\20260704_perf_table\level_NIFTY50_official.csv"
BACKSPREAD = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\BACKSPREAD_21Y_full_series.csv"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

LOT = 75
CAP0 = 1_000_000.0
HEDGE_FRACTION = 1.00   # [ASSUMPTION] 100% of underlying notional hedged; not specified by Principal

lvl = pd.read_csv(LEVEL, parse_dates=["date"]).set_index("date").sort_index()["level"]
bs = pd.read_csv(BACKSPREAD, parse_dates=["entry_date", "roll_date", "expiry"]).sort_values("roll_date")
bs = bs.set_index("roll_date")

all_dates = lvl.index
all_dates = all_dates[(all_dates >= bs.index.min()) & (all_dates <= min(bs.index.max(), all_dates.max()))]

underlying_units = CAP0 / lvl.loc[all_dates[0]]   # bought once, held throughout, no rebalancing
rows = []
cash_pnl = 0.0
for d in all_dates:
    underlying_value = underlying_units * lvl.loc[d]
    hedge_pnl_today = 0.0
    if d in bs.index:
        row = bs.loc[d]
        if isinstance(row, pd.DataFrame):   # guard against same-day duplicate rolls
            row = row.iloc[0]
        lots = round(HEDGE_FRACTION * underlying_value / (float(row["spot_entry"]) * LOT))
        hedge_pnl_today = lots * float(row["net_pnl_pts"]) * LOT
        cash_pnl += hedge_pnl_today
    combined = underlying_value + cash_pnl
    rows.append(dict(date=d, underlying_value=underlying_value, cash_pnl=cash_pnl,
                      combined=combined, hedge_pnl_today=hedge_pnl_today))

panel = pd.DataFrame(rows).set_index("date")
panel.to_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_21y.csv")

yrs = (panel.index[-1] - panel.index[0]).days / 365.25


def cagr_mdd(s):
    c = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    dd = (s - s.cummax()) / s.cummax() * 100
    return c, dd.min(), dd.idxmin()


c_u, dd_u, dd_u_date = cagr_mdd(panel["underlying_value"])
c_c, dd_c, dd_c_date = cagr_mdd(panel["combined"])

print(f"Window: {panel.index[0].date()} .. {panel.index[-1].date()} ({yrs:.1f}y)")
print(f"\nUNDERLYING ONLY (Rs {CAP0/1e5:.0f}L in NIFTY 50, price index, unhedged):")
print(f"  final Rs {panel['underlying_value'].iloc[-1]:,.0f} | CAGR {c_u:+.2%} | MaxDD {dd_u:+.2f}% ({dd_u_date.date()})")
print(f"\nUNDERLYING + BACKSPREAD HEDGE ({HEDGE_FRACTION:.0%} notional, 30D roll T-5):")
print(f"  final Rs {panel['combined'].iloc[-1]:,.0f} | CAGR {c_c:+.2%} | MaxDD {dd_c:+.2f}% ({dd_c_date.date()})")
print(f"\nHedge total P&L over {yrs:.1f}y: Rs {cash_pnl:,.0f}")
print(f"MaxDD improvement: {dd_c - dd_u:+.2f}pts | CAGR cost/benefit: {c_c - c_u:+.2%}pts")

# 2008 GFC and 2020 COVID window drilldowns specifically
for name, start, end in [("2008 GFC (Jan-Dec 2008)", "2008-01-01", "2008-12-31"),
                          ("2020 COVID (Jan-Jun 2020)", "2020-01-01", "2020-06-30"),
                          ("2025 correction (Jan-Apr 2025)", "2025-01-01", "2025-04-30")]:
    w = panel.loc[start:end]
    if len(w) < 2:
        continue
    u_dd = ((w["underlying_value"] - w["underlying_value"].cummax()) / w["underlying_value"].cummax() * 100).min()
    c_dd = ((w["combined"] - w["combined"].cummax()) / w["combined"].cummax() * 100).min()
    print(f"  [{name}] underlying-only worst intra-window DD {u_dd:+.1f}% vs combined {c_dd:+.1f}% "
          f"(hedge P&L in window: Rs {w['hedge_pnl_today'].sum():,.0f})")
