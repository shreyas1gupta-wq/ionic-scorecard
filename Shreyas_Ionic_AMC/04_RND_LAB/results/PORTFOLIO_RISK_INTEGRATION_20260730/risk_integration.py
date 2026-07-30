"""
PORTFOLIO RISK INTEGRATION -- combined-book risk picture (RP-29..36 methodology)
Owner: Ritika Sharma (Risk). Filed 2026-07-30.

Builds on (does NOT redo):
  - PORTFOLIO_MARGINAL_20260729/DECISION_RULE_AND_VERDICT.md (my own prior verdict this session)
  - PORTFOLIO_MARGINAL_20260729/marginal_framework.py (reused: to_period_series, to_daily_on_calendar,
    ann_sharpe/calmar/max_dd helpers, monthly/quarterly-anchored correlation convention)
  - STACKED_BOOK_20260711/RESULTS.md (max pairwise 0.08 daily -> 0.53 quarterly finding; "only S1-F
    stayed orthogonal in worst months")

Real series used (NEVER synthesized):
  1. STACKED_BOOK_20260711/book_daily_pnl.csv          -- 4-sleeve book, 942 obs, 2022-01-04..2025-12-31
  2. SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv   -- sweep primary (E), 2015-01-09..2026-05-14
     SWEEP_11YR_20260729/trades_D_overnight1_trail40_1lot.csv -- sweep alt (D), same span
     Carry adjustment reproduced EXACTLY per SWEEP_11YR_20260729/carry_adj.py (+0.5%/month, longs pay/
     shorts receive) -- that script printed to stdout only, no CSV was banked; this script re-derives
     the daily net-Rs series so it can be correlated/combined (not re-deriving the METHOD, just banking
     its output).
  3. SWING_DELTA1_20260729/all_trades.csv, cell=D_priorweek_sweep_long__fixed_10 -- 2021-05-24..2025-12-31
  4. A4_COVID_REPLICATION_20260711/a4_cycles.csv -- monthly short-strangle-proxy cycles on REAL 2011-2021
     option settles (used ONLY for the COVID joint-behaviour check; cycle-grain, not daily -- stated).
  5. datasets/etf_gold_silver/niftybees_daily.parquet -- NIFTY spot proxy, context for worst-day dating.

NOT available (stated, not guessed): no long-dated short-vol INCOME sleeve series exists on disk as of
this run (checked results/ tree for "long_dated"/"income"/"leap"/"hedge" dirs -- none found; two other
agents are building the hedge overlay and the long-dated income sleeve per the task brief). Every
place below that would need it says so explicitly instead of inventing a number.
"""
import numpy as np
import pandas as pd
import datetime as dt
import json

R = r"Shreyas_Ionic_AMC/04_RND_LAB/results"
OUT = r"Shreyas_Ionic_AMC/04_RND_LAB/results/PORTFOLIO_RISK_INTEGRATION_20260730"
BOOK_CAPITAL = 1.0e7  # Rs 1cr, RISK_LIMITS D-026

# ===========================================================================
# 0. HELPERS (reused verbatim from PORTFOLIO_MARGINAL_20260729/marginal_framework.py)
# ===========================================================================

def simple_tstat(x):
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    if len(x) < 2 or x.std(ddof=1) == 0: return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

def ann_sharpe(daily_ret, ppy=252):
    x = daily_ret.dropna()
    if x.std(ddof=1) == 0 or len(x) < 5: return np.nan
    return (x.mean() / x.std(ddof=1)) * np.sqrt(ppy)

def calmar(daily_ret, ppy=252):
    x = daily_ret.dropna()
    if len(x) < 5: return np.nan
    n_years = len(x) / ppy
    total = (1 + x).prod() - 1 if (1 + x).min() > 0 else x.sum()
    cagr = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else np.nan
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return cagr / abs(dd) if dd < 0 else np.nan

def max_dd(daily_ret):
    x = daily_ret.dropna()
    eq = (1 + x).cumprod()
    return (eq / eq.cummax() - 1).min()

def hist_var(daily_ret, pct):
    x = daily_ret.dropna()
    if len(x) < 20: return np.nan
    return np.percentile(x, pct)

def hist_es(daily_ret, pct):
    """Expected shortfall = mean of the tail beyond the VaR percentile."""
    x = daily_ret.dropna()
    if len(x) < 20: return np.nan
    v = np.percentile(x, pct)
    tail = x[x <= v]
    return tail.mean() if len(tail) else v

def to_period_series(event_ret, freq):
    s = event_ret.copy(); s.index = pd.to_datetime(s.index)
    return s.groupby(pd.Grouper(freq=freq)).sum()

def to_daily_on_calendar(event_ret, real_trading_days_index):
    s = event_ret.copy(); s.index = pd.to_datetime(s.index).normalize()
    s = s.groupby(level=0).sum()
    return s.reindex(pd.to_datetime(real_trading_days_index).normalize(), fill_value=0.0)

def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 10: return np.nan
    m = x.mean(); dv = x - m; n = len(x); v = (dv @ dv) / n
    for L in range(1, min(lags, n - 1) + 1):
        v += 2 * (1 - L / (lags + 1)) * ((dv[L:] @ dv[:-L]) / n)
    return m / np.sqrt(v / n) if v > 0 else np.nan

# ===========================================================================
# 1. BOOK (real, 2022-01-04..2025-12-31)
# ===========================================================================
book = pd.read_csv(f"{R}/STACKED_BOOK_20260711/book_daily_pnl.csv", index_col=0, parse_dates=True)
book.index.name = "date"
book_ret = book["total"] / BOOK_CAPITAL
book_ret.name = "book"
s1f_ret = (book["s1f"] / BOOK_CAPITAL).rename("s1f")  # the book's OWN short-vol sleeve (0DTE straddle)
BOOK_START, BOOK_END = book_ret.index.min(), book_ret.index.max()
print(f"[book] {len(book_ret)} obs {BOOK_START.date()}..{BOOK_END.date()} base=Rs{BOOK_CAPITAL/1e7:.0f}cr")

# ===========================================================================
# 2. SWEEP_11YR -- carry-adjusted, full 2015-2026 history (reproduces carry_adj.py's method,
#    banks the daily net-Rs output which that script never wrote to disk)
# ===========================================================================
SW_CAP = 1_000_000.0  # Rs 10L, report.json capital basis
CARRY_MONTHLY = 0.005
LOT = 75
BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019 / 100, 0.18, 0.002 / 100, 10.0
STT_OLD, STT_NEW, SW_DATE = 0.0125 / 100, 0.020 / 100, dt.date(2024, 10, 1)

def rt_cost(e, x, lots, d):
    qty = lots * LOT
    stt = (STT_OLD if d < SW_DATE else STT_NEW) * x * qty
    turn = (e + x) * qty
    brok = BROK * 2
    exch = EXCH * turn
    return brok + exch + stt + GST * (brok + exch) + STAMP * e * qty + SEBI_CR * turn / 1e7

def carry_adjust(cfg):
    tr = pd.read_csv(f"{R}/SWEEP_11YR_20260729/trades_{cfg}_1lot.csv", parse_dates=["t"])
    tr["date"] = pd.to_datetime(tr["date"]).dt.date
    hold_days = np.maximum(tr.hold_min / 375.0, 0.0)
    carry = tr.entry * (CARRY_MONTHLY / 30.0) * np.maximum(hold_days, 0.5)
    d = tr.copy()
    d["eff_pts"] = d.gross_pts - np.sign(d.dir) * carry  # longs pay, shorts receive
    d["gross"] = d.eff_pts * LOT
    d["cost"] = [rt_cost(e, x, 1, dd) for e, x, dd in zip(d.entry, d.exit, d.date)]
    d["net"] = d.gross - d.cost
    daily_net = d.groupby("date")["net"].sum()
    daily_net.index = pd.to_datetime(daily_net.index)
    return daily_net, d

sweepE_daily_rs, sweepE_trades = carry_adjust("E_swing3_trail60")
sweepD_daily_rs, sweepD_trades = carry_adjust("D_overnight1_trail40")
sweepE_ret = (sweepE_daily_rs / SW_CAP).rename("sweep_E")
sweepD_ret = (sweepD_daily_rs / SW_CAP).rename("sweep_D")
print(f"[sweep E carry-adj] {len(sweepE_daily_rs)} trading days, "
      f"{sweepE_daily_rs.index.min().date()}..{sweepE_daily_rs.index.max().date()}, "
      f"total net Rs{sweepE_daily_rs.sum():,.0f}")

# sanity check vs PROGRESS_OPTION_BUYING_20260729.md headline (CAGR 15.33%/MDD -18.02%/Sharpe 1.84/t=4.35)
_yrs = (sweepE_daily_rs.index.max() - sweepE_daily_rs.index.min()).days / 365.25
_eq = SW_CAP + sweepE_daily_rs.cumsum()
_cagr = (_eq.iloc[-1] / SW_CAP) ** (1 / _yrs) - 1
_mdd = ((_eq - _eq.cummax()) / _eq.cummax()).min()
_sh = (sweepE_ret.mean() / sweepE_ret.std()) * np.sqrt(252)
_t = nw_t(sweepE_daily_rs.values)
print(f"[sweep E sanity-check] CAGR={100*_cagr:.2f}% MDD={100*_mdd:.2f}% Sharpe={_sh:.2f} NW-t={_t:.2f} "
      f"(headline quoted: 15.33% / -18.02% / 1.84 / 4.35)")

# ===========================================================================
# 3. SWING_DELTA1 -- D_priorweek_sweep_long__fixed_10 cell
# ===========================================================================
sd_all = pd.read_csv(f"{R}/SWING_DELTA1_20260729/all_trades.csv", parse_dates=["entry_date", "exit_date"])
sd = sd_all[sd_all["cell"] == "D_priorweek_sweep_long__fixed_10"].copy()
sd_equity_before = sd["equity_after"] - sd["net"]
swing_ret = pd.Series((sd["net"] / sd_equity_before).values, index=sd["exit_date"].values).sort_index()
swing_ret.name = "swing"
swing_daily_rs = pd.Series(sd["net"].values, index=sd["exit_date"].values).sort_index()
print(f"[swing D_fixed10] n={len(sd)} trades, {sd['exit_date'].min().date()}..{sd['exit_date'].max().date()}")

# ===========================================================================
# 4. A4 COVID-era short-vol proxy cycles (monthly grain, real 2011-2021 settles) -- crash context only
# ===========================================================================
a4 = pd.read_csv(f"{R}/A4_COVID_REPLICATION_20260711/a4_cycles.csv", parse_dates=["entry", "expiry"])
a4_covid_cycle = a4[(a4["entry"] >= "2020-02-01") & (a4["entry"] <= "2020-03-01")].iloc[0]
print(f"[A4 COVID cycle] entry={a4_covid_cycle.entry.date()} expiry={a4_covid_cycle.expiry.date()} "
      f"net_pts={a4_covid_cycle.net:.1f} (Rs{a4_covid_cycle.net*LOT:,.0f}/lot)")

# ===========================================================================
# 5. CORRELATION MATRIX -- monthly & quarterly, on the BOOK's own 2022-2025 window
#    (per firm rule: daily correlation among these series is the demonstrated artifact; only
#     monthly/quarterly with sign+magnitude agreement is trusted -- STACKED_BOOK_20260711 addenda)
# ===========================================================================
def corr_matrix(freq):
    series = {
        "book": book_ret,
        "s1f(short-vol,in-book)": s1f_ret,
        "sweep_E": to_daily_on_calendar(sweepE_ret, book_ret.index),
        "sweep_D": to_daily_on_calendar(sweepD_ret, book_ret.index),
        "swing_D10": to_daily_on_calendar(swing_ret, book_ret.index),
    }
    df = pd.DataFrame({k: to_period_series(v, freq) for k, v in series.items()})
    df = df.loc[(df.index >= BOOK_START) & (df.index <= BOOK_END)]
    return df, df.corr()

monthly_df, corr_m = corr_matrix("ME")
quarterly_df, corr_q = corr_matrix("QE")
print("\n=== MONTHLY correlation (n=%d months) ===" % len(monthly_df))
print(corr_m.round(2).to_string())
print("\n=== QUARTERLY correlation (n=%d quarters) ===" % len(quarterly_df))
print(corr_q.round(2).to_string())
corr_m.round(3).to_csv(f"{OUT}/corr_monthly.csv")
corr_q.round(3).to_csv(f"{OUT}/corr_quarterly.csv")
monthly_df.to_csv(f"{OUT}/monthly_pnl_by_sleeve.csv")

# ===========================================================================
# 6. COMBINED-BOOK RISK TABLE -- weight scenarios on the book's real 2022-2025 calendar
# ===========================================================================
sweepE_on_book = to_daily_on_calendar(sweepE_ret, book_ret.index)
sweepD_on_book = to_daily_on_calendar(sweepD_ret, book_ret.index)
swing_on_book = to_daily_on_calendar(swing_ret, book_ret.index)

def blended(w_sweep=0.0, w_swing=0.0, sweep_series=sweepE_on_book):
    w_book = 1 - w_sweep - w_swing
    return w_book * book_ret + w_sweep * sweep_series + w_swing * swing_on_book

scenarios = {
    "Book alone (existing 4 sleeves)": blended(0, 0),
    "Book + Sweep-E @10%": blended(0.10, 0),
    "Book + Sweep-D @10% (tail-conservative alt)": blended(0.0, 0.0, sweep_series=sweepD_on_book) if False else (0.90*book_ret + 0.10*sweepD_on_book),
    "Book + Swing @10%": blended(0, 0.10),
    "Book + Sweep-E @10% + Swing @10%": blended(0.10, 0.10),
    "Book + Sweep-E @15% + Swing @15%": blended(0.15, 0.15),
}

risk_rows = []
for name, s in scenarios.items():
    monthly = to_period_series(s, "ME")
    risk_rows.append(dict(
        scenario=name,
        ann_sharpe=round(ann_sharpe(s), 3),
        calmar=round(calmar(s), 3) if not np.isnan(calmar(s)) else np.nan,
        maxDD_pct=round(100 * max_dd(s), 2),
        VaR95_daily_pct=round(100 * hist_var(s, 5), 3),
        VaR99_daily_pct=round(100 * hist_var(s, 1), 3),
        ES95_daily_pct=round(100 * hist_es(s, 5), 3),
        ES99_daily_pct=round(100 * hist_es(s, 1), 3),
        worst_month_pct=round(100 * monthly.min(), 2),
        best_month_pct=round(100 * monthly.max(), 2),
        n_days=int(s.notna().sum()),
    ))
risk_df = pd.DataFrame(risk_rows)
print("\n=== COMBINED-BOOK RISK TABLE (2022-2025 real overlap window) ===")
print(risk_df.to_string(index=False))
risk_df.to_csv(f"{OUT}/combined_book_risk_table.csv", index=False)

# --- VaR sanity: parametric-normal cross-check on the flagship combo (RP-34 duty) ---
from scipy import stats as _st
flagship = scenarios["Book + Sweep-E @10% + Swing @10%"].dropna()
mu, sigma = flagship.mean(), flagship.std(ddof=1)
var95_hist = hist_var(flagship, 5)
var95_param = mu + sigma * _st.norm.ppf(0.05)
var99_hist = hist_var(flagship, 1)
var99_param = mu + sigma * _st.norm.ppf(0.01)
# simple bootstrap MC (10k resamples of the empirical daily distribution)
rng = np.random.default_rng(42)
mc_draws = rng.choice(flagship.values, size=(10000,), replace=True)
var95_mc = np.percentile(mc_draws, 5)
var99_mc = np.percentile(mc_draws, 1)
print(f"\n=== VaR 3-METHOD SANITY on flagship combo (Book+SweepE10%+Swing10%) ===")
print(f"VaR95: hist={100*var95_hist:.3f}% param-normal={100*var95_param:.3f}% MC-bootstrap={100*var95_mc:.3f}%")
print(f"VaR99: hist={100*var99_hist:.3f}% param-normal={100*var99_param:.3f}% MC-bootstrap={100*var99_mc:.3f}%")
with open(f"{OUT}/var_sanity_flagship.json", "w") as f:
    json.dump(dict(var95_hist=var95_hist, var95_param=var95_param, var95_mc=float(var95_mc),
                    var99_hist=var99_hist, var99_param=var99_param, var99_mc=float(var99_mc),
                    skew=float(_st.skew(flagship.values)), kurtosis=float(_st.kurtosis(flagship.values))), f, indent=2)

# ===========================================================================
# 7. WORST-MONTHS JOINT BEHAVIOUR -- the critical correlation question, real data
# ===========================================================================
book_monthly = to_period_series(book_ret, "ME")
worst5 = book_monthly.nsmallest(5)
print("\n=== BOOK'S 5 WORST MONTHS (2022-2025) -- joint sleeve behaviour ===")
rows = []
for period, book_pct in worst5.items():
    m_s1f = to_period_series(s1f_ret, "ME").get(period, np.nan)
    m_sweepE = to_period_series(sweepE_on_book, "ME").get(period, np.nan)
    m_sweepD = to_period_series(sweepD_on_book, "ME").get(period, np.nan)
    m_swing = to_period_series(swing_on_book, "ME").get(period, np.nan)
    rows.append(dict(month=str(period), book_pct=round(100*book_pct,2),
                      s1f_pct=round(100*m_s1f,2) if pd.notna(m_s1f) else np.nan,
                      sweepE_pct=round(100*m_sweepE,3) if pd.notna(m_sweepE) else np.nan,
                      sweepD_pct=round(100*m_sweepD,3) if pd.notna(m_sweepD) else np.nan,
                      swing_pct=round(100*m_swing,3) if pd.notna(m_swing) else np.nan))
worst_df = pd.DataFrame(rows)
print(worst_df.to_string(index=False))
worst_df.to_csv(f"{OUT}/worst_5_months_joint.csv", index=False)

# ===========================================================================
# 8. CRASH-STRESS -- sweep has 11.34yr incl COVID; book/s1f/swing do NOT (crash-blind, stated)
# ===========================================================================
covid_win = sweepE_daily_rs.loc["2020-02-15":"2020-04-15"]
covid_win_pts_lot = (covid_win / LOT).sum()  # back out approx points for readability
full_hist_monthly = to_period_series(sweepE_ret, "ME")
worst_month_full = full_hist_monthly.min()
worst_month_overlap = to_period_series(sweepE_on_book, "ME").min()
worst_day_full = sweepE_ret.min()
print(f"\n=== SWEEP-E FULL-HISTORY CRASH STRESS (2015-2026, incl. COVID) ===")
print(f"COVID window 2020-02-15..2020-04-15: net Rs{covid_win.sum():,.0f} over {len(covid_win)} trading days "
      f"({100*covid_win.sum()/SW_CAP:.2f}% of Rs10L sweep capital)")
print(f"Worst single day (full 11.34yr): {100*worst_day_full:.2f}% | "
      f"Worst month (full 11.34yr): {100*worst_month_full:.2f}% | "
      f"Worst month (2022-2025 book-overlap only): {100*worst_month_overlap:.2f}%")

# Joint check vs the A4 real-settle COVID short-vol crash cycle (2020-02-28..2020-03-26)
a4_win_start, a4_win_end = a4_covid_cycle.entry, a4_covid_cycle.expiry
sweep_during_a4_crash = sweepE_daily_rs.loc[a4_win_start:a4_win_end]
print(f"\n=== JOINT TEST: sweep-E vs the firm's real-settle short-vol COVID crash cycle ===")
print(f"A4 short-vol cycle {a4_win_start.date()}..{a4_win_end.date()}: net {a4_covid_cycle.net:.1f} pts "
      f"= Rs{a4_covid_cycle.net*LOT:,.0f}/lot (a REAL LOSS on the short-vol structure)")
print(f"Sweep-E over the SAME calendar window: net Rs{sweep_during_a4_crash.sum():,.0f} "
      f"over {len(sweep_during_a4_crash)} trading days "
      f"({100*sweep_during_a4_crash.sum()/SW_CAP:.2f}% of Rs10L sweep capital)")
crash_join = dict(a4_window_start=str(a4_win_start.date()), a4_window_end=str(a4_win_end.date()),
                   a4_shortvol_net_pts=float(a4_covid_cycle.net),
                   a4_shortvol_net_rs_per_lot=float(a4_covid_cycle.net*LOT),
                   sweepE_net_rs_same_window=float(sweep_during_a4_crash.sum()),
                   sweepE_pct_of_capital=float(100*sweep_during_a4_crash.sum()/SW_CAP),
                   sweepE_n_trading_days_in_window=int(len(sweep_during_a4_crash)),
                   covid_window_wide_net_rs=float(covid_win.sum()),
                   sweepE_worst_day_full_hist_pct=float(100*worst_day_full),
                   sweepE_worst_month_full_hist_pct=float(100*worst_month_full),
                   sweepE_worst_month_book_overlap_pct=float(100*worst_month_overlap))
with open(f"{OUT}/crash_joint_test.json", "w") as f:
    json.dump(crash_join, f, indent=2)

# sweep_E vs sweep_D vs swing candidate-to-candidate correlation (double-count risk if stacked together)
cc = pd.DataFrame({
    "sweepE_m": to_period_series(sweepE_on_book, "ME"),
    "swing_m": to_period_series(swing_on_book, "ME"),
}).loc[BOOK_START:BOOK_END]
print(f"\n=== Candidate-candidate monthly correlation (sweep-E vs swing) ===")
print(cc.corr().round(3).to_string())

print("\nDone. All outputs written to", OUT)
