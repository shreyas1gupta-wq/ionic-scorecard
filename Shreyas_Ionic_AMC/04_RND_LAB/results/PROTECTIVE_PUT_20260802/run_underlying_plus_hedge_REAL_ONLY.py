"""PROTECTIVE_PUT_20260802 -- Principal flagged the 21y result as not seeming right. Re-running
restricted to ONLY the REAL 2016-2026 backspread trades (trades_BACKSPREAD_1x2_10pct.csv) -- no
modeled 2005-2016 segment at all, so any artifact from the Black-Scholes reconstruction (flat-vol,
no skew, bias-corrected but still a model) cannot be driving the result. If "hedge makes MaxDD worse"
still shows up on pure real data, it's a real finding, not a modeling artifact.
"""
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LEVEL = ROOT + r"\results\factor_replication\20260704_perf_table\level_NIFTY50_official.csv"
REAL_TRADES = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\trades_BACKSPREAD_1x2_10pct.csv"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

LOT = 75
CAP0 = 1_000_000.0
HEDGE_FRACTION = 1.00

lvl = pd.read_csv(LEVEL, parse_dates=["date"]).set_index("date").sort_index()["level"]
bs = pd.read_csv(REAL_TRADES, parse_dates=["entry_date", "roll_date", "expiry"]).sort_values("roll_date")
print(f"REAL backspread trades: n={len(bs)} | {bs['entry_date'].min().date()} .. {bs['roll_date'].max().date()}")
bs = bs.set_index("roll_date")

all_dates = lvl.index
all_dates = all_dates[(all_dates >= bs.index.min()) & (all_dates <= bs.index.max())]
print(f"NIFTY 50 level rows in this window: {len(all_dates)} ({all_dates.min().date()} .. {all_dates.max().date()})")

underlying_units = CAP0 / lvl.loc[all_dates[0]]
rows = []
cash_pnl = 0.0
for d in all_dates:
    underlying_value = underlying_units * lvl.loc[d]
    hedge_pnl_today = 0.0
    if d in bs.index:
        row = bs.loc[d]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        lots = round(HEDGE_FRACTION * underlying_value / (float(row["spot_entry"]) * LOT))
        hedge_pnl_today = lots * float(row["net_pnl_pts"]) * LOT
        cash_pnl += hedge_pnl_today
    combined = underlying_value + cash_pnl
    rows.append(dict(date=d, underlying_value=underlying_value, cash_pnl=cash_pnl,
                      combined=combined, hedge_pnl_today=hedge_pnl_today))

panel = pd.DataFrame(rows).set_index("date")
panel.to_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_REAL_ONLY.csv")

yrs = (panel.index[-1] - panel.index[0]).days / 365.25


def cagr_mdd(s):
    c = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    dd = (s - s.cummax()) / s.cummax() * 100
    return c, dd.min(), dd.idxmin()


c_u, dd_u, dd_u_date = cagr_mdd(panel["underlying_value"])
c_c, dd_c, dd_c_date = cagr_mdd(panel["combined"])

print(f"\nWindow: {panel.index[0].date()} .. {panel.index[-1].date()} ({yrs:.1f}y) -- REAL OPTION DATA ONLY")
print(f"\nUNDERLYING ONLY (Rs {CAP0/1e5:.0f}L in NIFTY 50):")
print(f"  final Rs {panel['underlying_value'].iloc[-1]:,.0f} | CAGR {c_u:+.2%} | MaxDD {dd_u:+.2f}% ({dd_u_date.date()})")
print(f"\nUNDERLYING + BACKSPREAD HEDGE ({HEDGE_FRACTION:.0%} notional):")
print(f"  final Rs {panel['combined'].iloc[-1]:,.0f} | CAGR {c_c:+.2%} | MaxDD {dd_c:+.2f}% ({dd_c_date.date()})")
print(f"\nHedge total P&L over {yrs:.1f}y: Rs {cash_pnl:,.0f}")
print(f"MaxDD improvement: {dd_c - dd_u:+.2f}pts | CAGR cost/benefit: {c_c - c_u:+.2%}pts")

# every calendar year, so we can see WHERE (if anywhere) the hedge helps vs hurts, real data only
print("\nYear-by-year (worst intra-year drawdown, underlying-only vs combined):")
for yr in range(panel.index[0].year, panel.index[-1].year + 1):
    w = panel.loc[f"{yr}-01-01":f"{yr}-12-31"]
    if len(w) < 5:
        continue
    u_dd = ((w["underlying_value"] - w["underlying_value"].cummax()) / w["underlying_value"].cummax() * 100).min()
    c_dd = ((w["combined"] - w["combined"].cummax()) / w["combined"].cummax() * 100).min()
    hedge_yr_pnl = w["hedge_pnl_today"].sum()
    flag = "  <-- hedge WORSE" if c_dd < u_dd - 0.5 else ("  <-- hedge BETTER" if c_dd > u_dd + 0.5 else "")
    print(f"  {yr}: underlying {u_dd:+6.1f}%  vs combined {c_dd:+6.1f}%  | hedge P&L Rs {hedge_yr_pnl:+11,.0f}{flag}")
