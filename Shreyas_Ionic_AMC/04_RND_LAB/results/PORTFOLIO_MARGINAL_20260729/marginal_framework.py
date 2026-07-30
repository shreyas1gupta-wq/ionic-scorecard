"""
PORTFOLIO-MARGINAL EVALUATION FRAMEWORK (RP-17 / /orthogonality methodology, extended)
Owner: Ritika Sharma (Risk). Filed 2026-07-29/30.

Purpose: judge each low-frequency candidate sleeve on its MARGINAL contribution to the
existing book, not on standalone CAGR. Per firm finding (STACKED_BOOK_20260711): daily
sleeve correlation is an ARTIFACT (stacked book corr 0.08 daily -> 0.53 quarterly); the
verdict must be based on MONTHLY/QUARTERLY correlation, never daily alone.

BOOK definition (honest, real series only):
  Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv
  4 real sleeve backtests stacked: s1f (certified live/paper), b1b (Gate-4 PASS +
  red-team SURVIVED, pre-IC), midsmall momentum, breakout equity (stage varies).
  942 daily obs, 2022-01-04..2025-12-31. Base capital = Rs 1,00,00,000 (RISK_LIMITS D-026
  paper-book convention; matches SWING_DELTA1's own BOOK_EQUITY0 assumption).
  NOTE: this is a RESEARCH RECOMBINATION of separately-validated backtests, not the live
  paper ledger (which has exactly ONE closed trade, S1F-001, as of today -- nowhere near
  enough history for a correlation estimate). Stated explicitly per task instructions.

Candidates processed (real per-trade CSVs found on disk as of 2026-07-29 23:5x IST):
  - TREND_CATCHER_MULTIDAY (3 signals, Stage A, ATM/DTE15-22/trail35)
  - SWING_DELTA1 (2 survivor cells of 45 valid / 50 pre-registered: Calmar>0 AND NW-t>=1.0)
  - SWEEP_11YR (6 exit-management variants, kelly-sized futures trend catcher)
  - COVERED_CALL_NIFTY (single unconditional cycle series)
Candidates explicitly PENDING (no finished trade-level output; not guessed):
  DEBIT_SPREADS (crashed, MemoryError mid-run, raw unfiltered grid only), VOL_SELLING_BENCHMARK
  (signal flags only), INVERSE_VRP_NICHE (IV/RV build in progress), CONVEX_STRUCTURES (empty),
  OPTION_SURFACE_SIGNALS (panel build in progress, 800/1236 days), OPTION_BUY_ARMS/bullish-sweep-dte
  (pre-registration only), OPTION_BUY_ARMS bearish-arm & confluence-volbreak (signal timestamps,
  NO P&L attached -- not priced through the option harness yet).
"""
import json
import numpy as np
import pandas as pd

R = r"Shreyas_Ionic_AMC/04_RND_LAB/results"
OUT = r"Shreyas_Ionic_AMC/04_RND_LAB/results/PORTFOLIO_MARGINAL_20260729"
BOOK_CAPITAL = 1.0e7  # Rs 1cr, RISK_LIMITS D-026 / SWING_DELTA1 BOOK_EQUITY0 convention

# ---------------------------------------------------------------------------
# 1. BOOK daily return series (real, on-disk, 2022-01-04..2025-12-31)
# ---------------------------------------------------------------------------
book = pd.read_csv(f"{R}/STACKED_BOOK_20260711/book_daily_pnl.csv", index_col=0, parse_dates=True)
book.index.name = "date"
book_ret = book["total"] / BOOK_CAPITAL
book_ret.name = "book"
BOOK_START, BOOK_END = book_ret.index.min(), book_ret.index.max()
print(f"[book] {len(book_ret)} daily obs, {BOOK_START.date()}..{BOOK_END.date()}, "
      f"base capital Rs{BOOK_CAPITAL/1e7:.1f}cr")

# also keep sleeve-level series for context (these are PART of the book, not candidates)
sleeve_ret = book[["midsmall", "breakout", "s1f", "b1b"]] / BOOK_CAPITAL

# ---------------------------------------------------------------------------
# 2. Candidate loaders -> each returns a DataFrame indexed by event date with
#    column 'ret' = net P&L / candidate's own pre-registered capital base
#    (so that reallocating w-fraction of BOOK_CAPITAL to the candidate and
#    applying its own historical per-rupee edge is a like-for-like operation).
# ---------------------------------------------------------------------------
candidates = {}  # name -> (pd.Series of 'ret' indexed by date, dict of meta)


def add(name, s, meta):
    s = s.sort_index()
    s.name = name
    candidates[name] = (s, meta)


# --- TREND_CATCHER_MULTIDAY: capital Rs 3,00,000, ret = net_pnl / capital ---
TC_CAP = 300_000.0
for sig, fname in [
    ("breakout20", "stageA_breakout20_b2_ATM_trail35.csv"),
    ("ema_cross", "stageA_ema_cross_b2_ATM_trail35.csv"),
    ("sweep_priorweek_reclaim", "stageA_sweep_priorweek_reclaim_b2_ATM_trail35.csv"),
]:
    df = pd.read_csv(f"{R}/TREND_CATCHER_MULTIDAY_20260729/trades/{fname}", parse_dates=["exit_date"])
    s = df.set_index("exit_date")["net_pnl"] / TC_CAP
    add(f"TC_{sig}", s, dict(family="TREND_CATCHER_MULTIDAY", n=len(df), capital=TC_CAP,
                              build_window="2021-08-17..2025-12-31", instrument="long CE/PE, ATM, DTE15-22, trail35"))

# --- SWING_DELTA1: BOOK_EQUITY0 = Rs 1cr, ret = net / equity_before (compounding-consistent) ---
sd_all = pd.read_csv(f"{R}/SWING_DELTA1_20260729/all_trades.csv", parse_dates=["entry_date", "exit_date"])
for cell in ["D_priorweek_sweep_long__fixed_5", "D_priorweek_sweep_long__fixed_10"]:
    df = sd_all[sd_all["cell"] == cell].copy()
    equity_before = df["equity_after"] - df["net"]
    s = pd.Series((df["net"] / equity_before).values, index=df["exit_date"].values)
    add(f"SD_{cell}", s, dict(family="SWING_DELTA1", n=len(df), capital=BOOK_CAPITAL,
                               build_window="2021-05-24..2025-12-31", instrument="NIFTY futures, daily signal, multi-day hold"))

# --- SWEEP_11YR: capital Rs 10,00,000 (report.json), ret = net / (equity - net); bucket by ENTRY date
#     (no exit-date column on disk; holds are short (intraday/overnight/swing<=3d) so entry-date
#     bucketing is a stated approximation, immaterial at monthly/quarterly grain -- [INFERENCE]) ---
SW_CAP = 1_000_000.0
for cfg in ["A_intraday_stop30", "B_intraday_trail25", "C_intraday_trail40",
            "D_overnight1_trail40", "E_swing3_trail60", "F_intraday_tgt200"]:
    df = pd.read_csv(f"{R}/SWEEP_11YR_20260729/trades_{cfg}_kelly01.csv", parse_dates=["date"])
    equity_before = df["equity"] - df["net"]
    s = pd.Series((df["net"] / equity_before).values, index=df["date"].values)
    add(f"SW11_{cfg}", s, dict(family="SWEEP_11YR", n=len(df), capital=SW_CAP,
                                 build_window="2015-01-09..2026-05-14 (full; book overlap 2022-2025 only)",
                                 instrument="NIFTY futures, kelly-sized, exit-mgmt variant"))

# --- COVERED_CALL_NIFTY: ret = net_pnl_rs / (spot_entry*75) notional then-deployed; bucket by exit_day ---
cc = pd.read_csv(f"{R}/COVERED_CALL_NIFTY_20260729/cc_bhav_cycles.csv", parse_dates=["exit_day"])
cc = cc.dropna(subset=["net_pnl_rs"])
s = pd.Series((cc["net_pnl_rs"] / (cc["spot_entry"] * 75)).values, index=cc["exit_day"].values)
add("CC_unconditional", s, dict(family="COVERED_CALL_NIFTY", n=len(cc), capital="notional (spot*75, ~Rs18-24L)",
                                  build_window="2016-04-01..2026-07-03", instrument="NIFTYBEES + short monthly ATM call, unconditional"))

print(f"\n[candidates loaded] {len(candidates)}: {list(candidates.keys())}")

# ---------------------------------------------------------------------------
# 3. Per-candidate standalone stats (t-stat on per-trade returns, simple; annualized
#    Sharpe/Calmar on the OVERLAP window with the book, since that's the only window
#    we can judge marginal contribution over)
# ---------------------------------------------------------------------------


def simple_tstat(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def ann_sharpe(daily_ret, periods_per_year=252):
    x = daily_ret.dropna()
    if x.std(ddof=1) == 0 or len(x) < 5:
        return np.nan
    return (x.mean() / x.std(ddof=1)) * np.sqrt(periods_per_year)


def calmar(daily_ret, periods_per_year=252):
    x = daily_ret.dropna()
    if len(x) < 5:
        return np.nan
    n_years = len(x) / periods_per_year
    total = (1 + x).prod() - 1 if (1 + x).min() > 0 else x.sum()
    cagr = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else np.nan
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return cagr / abs(dd) if dd < 0 else np.nan


def max_dd(daily_ret):
    x = daily_ret.dropna()
    eq = (1 + x).cumprod()
    return (eq / eq.cummax() - 1).min()


def hist_var95(daily_ret):
    x = daily_ret.dropna()
    if len(x) < 20:
        return np.nan
    return np.percentile(x, 5)


def to_period_series(event_ret, freq):
    """Sum per-trade returns into calendar buckets (month/quarter). NOT used for
    daily -- pd.Grouper('D') would manufacture a full calendar incl. weekends/
    holidays, creating synchronized (0,0) phantom-day pairs between any two
    thinly-traded series and biasing daily correlation. Monthly/quarterly are
    safe: summing real trading-day observations into a month/quarter bucket is
    unaffected by whether non-trading calendar days exist inside that bucket."""
    s = event_ret.copy()
    s.index = pd.to_datetime(s.index)
    return s.groupby(pd.Grouper(freq=freq)).sum()


def to_daily_on_calendar(event_ret, real_trading_days_index):
    """Collapse same-day duplicate events, then reindex onto an EXACT set of
    real trading dates (fill 0 where flat) -- no phantom weekend/holiday days."""
    s = event_ret.copy()
    s.index = pd.to_datetime(s.index).normalize()
    s = s.groupby(level=0).sum()
    return s.reindex(pd.to_datetime(real_trading_days_index).normalize(), fill_value=0.0)


overlap_start, overlap_end = BOOK_START, BOOK_END
book_daily_full = book_ret.reindex(pd.date_range(overlap_start, overlap_end, freq="D")).fillna(0.0)
# restrict to actual book trading days for Sharpe/Calmar (book_ret already only has trading days)
book_daily_trading = book_ret

rows = []
corr_rows = []
weight_sweep_rows = []

WEIGHTS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

for name, (s, meta) in candidates.items():
    n = meta["n"]
    t_simple = simple_tstat(s.values)
    # --- period aggregation ---
    daily = to_daily_on_calendar(s, book_ret.index)  # exact book trading days only
    monthly = to_period_series(s, "ME")
    quarterly = to_period_series(s, "QE")

    b_daily = book_ret  # already real trading days only
    b_monthly = to_period_series(book_ret, "ME")
    b_quarterly = to_period_series(book_ret, "QE")

    def corr_on_overlap(a, b, min_n=4):
        j = pd.concat([a, b], axis=1, join="inner").dropna()
        if len(j) < min_n:
            return np.nan, len(j)
        return j.iloc[:, 0].corr(j.iloc[:, 1]), len(j)

    # daily: inner-join is exact (both already on book's trading-day index) --
    # this correctly keeps the many zero-return days for a low-frequency
    # candidate as real (uncorrelated) observations, without weekend padding.
    c_d, nd = corr_on_overlap(daily, b_daily)
    c_m, nm = corr_on_overlap(monthly, b_monthly)
    c_q, nq = corr_on_overlap(quarterly, b_quarterly)

    corr_rows.append(dict(candidate=name, family=meta["family"], n_trades=n,
                           corr_daily=c_d, n_daily_obs=nd,
                           corr_monthly=c_m, n_monthly_obs=nm,
                           corr_quarterly=c_q, n_quarterly_obs=nq))

    # --- standalone stats on the candidate's own full history ---
    cagr_full = ((1 + daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D")).fillna(0)).prod()) ** (
        365.25 / (daily.index.max() - daily.index.min()).days) - 1 if len(daily) > 1 else np.nan

    rows.append(dict(
        candidate=name, family=meta["family"], n=n, t_stat=t_simple,
        mean_ret_per_trade_pct=100 * np.nanmean(s.values),
        win_rate=float((s.values > 0).mean()),
        build_window=meta["build_window"], instrument=meta["instrument"],
        corr_book_daily=c_d, corr_book_monthly=c_m, corr_book_quarterly=c_q,
    ))

    # --- marginal weight sweep, ONLY on the book's own date range (2022-2025 overlap),
    #     using the candidate's daily-bucketed return series reindexed to book's calendar
    #     (candidate return = 0 on days it has no trade -> idle capital assumption) ---
    cand_daily_on_book_dates = daily  # already exact-reindexed onto book_ret.index, 0-filled
    has_overlap = cand_daily_on_book_dates.abs().sum() > 0
    if has_overlap:
        for w in WEIGHTS:
            blend = (1 - w) * book_ret + w * cand_daily_on_book_dates
            weight_sweep_rows.append(dict(
                candidate=name, weight=w,
                sharpe=ann_sharpe(blend), calmar=calmar(blend),
                maxDD_pct=100 * max_dd(blend), var95_daily_pct=100 * hist_var95(blend),
                worst_month_pct=100 * to_period_series(blend, "ME").min(),
            ))

stats_df = pd.DataFrame(rows).sort_values(["family", "candidate"])
corr_df = pd.DataFrame(corr_rows).sort_values(["family", "candidate"])
weight_df = pd.DataFrame(weight_sweep_rows)

stats_df.to_csv(f"{OUT}/candidate_standalone_stats.csv", index=False)
corr_df.to_csv(f"{OUT}/correlation_daily_monthly_quarterly.csv", index=False)
weight_df.to_csv(f"{OUT}/marginal_weight_sweep.csv", index=False)

print("\n" + "=" * 100)
print("CANDIDATE STANDALONE STATS")
print(stats_df.to_string(index=False))

print("\n" + "=" * 100)
print("CORRELATION TO BOOK -- DAILY vs MONTHLY vs QUARTERLY")
print(corr_df.to_string(index=False))

print("\n" + "=" * 100)
print("MARGINAL WEIGHT-SWEEP (book alone at w=0 for reference)")
book_alone = dict(sharpe=ann_sharpe(book_ret), calmar=calmar(book_ret),
                   maxDD_pct=100 * max_dd(book_ret), var95_daily_pct=100 * hist_var95(book_ret),
                   worst_month_pct=100 * to_period_series(book_ret, "ME").min())
print("BOOK ALONE:", book_alone)
print(weight_df.to_string(index=False))

print("\nDone. Files written to", OUT)
