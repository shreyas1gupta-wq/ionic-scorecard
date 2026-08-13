"""PART A: full-span (2015-01..2026-05) futures leverage demonstration, NO options.
Answers: what does 10%-margin (10x leverage) NIFTY futures exposure do across COVID-2020 and
the 2015-16 correction, vs an unleveraged buy-and-hold. Weekly-reset margin (fresh 10% posted
each week, consistent with Part B's weekly-cycle option backtest) + explicit shock table.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
NIFTY_1MIN = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
LOT = 75
FUT_COST_PTS_PRE = 4.47 + 0.5
FUT_COST_PTS_POST = 5.97 + 0.5


def futures_cost(day: dt.date) -> float:
    return FUT_COST_PTS_PRE if day < dt.date(2024, 10, 1) else FUT_COST_PTS_POST


def max_drawdown(nav: pd.Series):
    cummax = nav.cummax()
    dd = nav / cummax - 1.0
    trough_idx = dd.idxmin()
    peak_idx = nav.loc[:trough_idx].idxmax()
    return float(dd.min()), peak_idx, trough_idx


def cagr(nav: pd.Series, periods_per_year: float):
    n_periods = len(nav) - 1
    years = n_periods / periods_per_year
    if years <= 0 or nav.iloc[0] <= 0:
        return float("nan")
    total_ret = nav.iloc[-1] / nav.iloc[0]
    if total_ret <= 0:
        return -1.0  # wiped out
    return total_ret ** (1 / years) - 1


def main():
    df = pd.read_parquet(NIFTY_1MIN)
    df = df[df.index.time >= dt.time(9, 15)]
    daily = df.groupby(df.index.date)["close"].last()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    trading_days = [d.date() for d in daily.index]

    # ---- weekly cycles: every trading day that is >=5 trading days after the prior anchor ----
    # simplest robust weekly grid: resample by ISO week, take last trading day's close per week
    weekly = daily.groupby([daily.index.isocalendar().year, daily.index.isocalendar().week]).agg(
        entry_spot=("close", "first"), exit_spot=("close", "last"),
    )
    weekly["entry_day"] = daily.groupby(
        [daily.index.isocalendar().year, daily.index.isocalendar().week]).apply(
        lambda s: s.index[0].date())
    weekly["exit_day"] = daily.groupby(
        [daily.index.isocalendar().year, daily.index.isocalendar().week]).apply(
        lambda s: s.index[-1].date())
    weekly = weekly.reset_index(drop=True)
    weekly["ret_index"] = weekly["exit_spot"] / weekly["entry_spot"] - 1.0

    # long futures @ 10% margin, weekly reset (fresh margin posted each week -> no carry-over
    # of a wipeout into the next week's capital base; this ISOLATES the single-week shock,
    # which is the honest way to show "what does a -10%/-20% week do", not a compounding trap)
    def cost_pts_row(r):
        return futures_cost(r["entry_day"])

    weekly["fut_cost_pts"] = weekly.apply(cost_pts_row, axis=1)
    weekly["pnl_long_rupee"] = ((weekly["exit_spot"] - weekly["entry_spot"])
                                 - weekly["fut_cost_pts"]) * LOT
    weekly["margin_10pct"] = 0.10 * weekly["entry_spot"] * LOT
    weekly["margin_15pct"] = 0.15 * weekly["entry_spot"] * LOT
    weekly["ret_on_margin_10pct"] = weekly["pnl_long_rupee"] / weekly["margin_10pct"]
    weekly["ret_on_margin_15pct"] = weekly["pnl_long_rupee"] / weekly["margin_15pct"]
    # clip at -100% (position force-closed / wiped out, cannot go more negative on THIS week's
    # posted margin in a weekly-reset framing -- the excess-loss-beyond-margin case is reported
    # separately as a count, not silently absorbed)
    weekly["wipeout_10pct"] = weekly["ret_on_margin_10pct"] <= -1.0
    weekly["wipeout_15pct"] = weekly["ret_on_margin_15pct"] <= -1.0
    weekly["ret_on_margin_10pct_clipped"] = weekly["ret_on_margin_10pct"].clip(lower=-1.0)

    # NAV curves (compounded, clipped version -- i.e. if wiped out, re-capitalized next week
    # at the SAME rupee margin base, which is what "weekly reset" structurally means)
    nav_bh = (1 + daily.pct_change().fillna(0)).cumprod()
    nav_bh.iloc[0] = 1.0
    nav_lev10 = (1 + weekly["ret_on_margin_10pct_clipped"]).cumprod()
    nav_lev10 = pd.concat([pd.Series([1.0]), nav_lev10]).reset_index(drop=True)

    bh_cagr = cagr(nav_bh, 252)
    bh_dd, bh_peak, bh_trough = max_drawdown(nav_bh)

    lev_cagr = cagr(nav_lev10, 52)
    lev_dd, lev_peak_i, lev_trough_i = max_drawdown(nav_lev10)

    n_weeks = len(weekly)
    n_wipeouts_10 = int(weekly["wipeout_10pct"].sum())
    n_wipeouts_15 = int(weekly["wipeout_15pct"].sum())
    worst_week = weekly.loc[weekly["ret_index"].idxmin()]
    best_week = weekly.loc[weekly["ret_index"].idxmax()]

    # explicit hypothetical shock table at today-like spot levels (also generic %, margin-relative
    # so it holds at ANY spot level -- that is the point: leverage ratio, not rupee level, is what
    # determines ruin)
    shock_table = []
    for shock_pct in (-0.05, -0.10, -0.15, -0.20, -0.30):
        for margin_pct in (0.10, 0.05):
            ret_on_margin = shock_pct / margin_pct
            shock_table.append(dict(index_move_pct=shock_pct, margin_pct=margin_pct,
                                     ret_on_margin_pct=ret_on_margin,
                                     outcome=("WIPED OUT + margin call" if ret_on_margin <= -1.0
                                              else ("severe" if ret_on_margin <= -0.5 else "material"))))

    # realized worst historical multi-day windows (for grounding, not hypothetical)
    daily_ret = daily.pct_change().dropna()
    roll5 = (1 + daily_ret).rolling(5).apply(np.prod, raw=True) - 1  # ~1 trading week
    roll20 = (1 + daily_ret).rolling(20).apply(np.prod, raw=True) - 1  # ~1 month
    worst_5d = roll5.min()
    worst_5d_end = roll5.idxmin()
    worst_20d = roll20.min()
    worst_20d_end = roll20.idxmin()

    out = dict(
        window=f"{trading_days[0]}..{trading_days[-1]}",
        n_trading_days=len(trading_days),
        n_weekly_cycles=n_weeks,
        buy_and_hold=dict(cagr=bh_cagr, max_dd=bh_dd,
                           calmar=(bh_cagr / abs(bh_dd) if bh_dd else None),
                           dd_peak=str(bh_peak.date()), dd_trough=str(bh_trough.date())),
        naked_long_fut_10pct_margin=dict(
            cagr_on_margin=lev_cagr, max_dd_on_margin=lev_dd,
            calmar=(lev_cagr / abs(lev_dd) if lev_dd else None),
            n_weekly_cycles=n_weeks, n_full_wipeout_weeks_10pct=n_wipeouts_10,
            n_full_wipeout_weeks_15pct_margin=n_wipeouts_15,
            worst_single_week_index_move_pct=float(worst_week["ret_index"]),
            worst_single_week_date=str(worst_week["exit_day"]),
            worst_single_week_ret_on_10pct_margin=float(worst_week["ret_on_margin_10pct"]),
            best_single_week_index_move_pct=float(best_week["ret_index"]),
            best_single_week_date=str(best_week["exit_day"]),
        ),
        realized_worst_windows=dict(
            worst_5trading_day_pct=float(worst_5d), worst_5day_window_ending=str(worst_5d_end.date()),
            worst_5day_ret_on_10pct_margin=float(worst_5d) / 0.10,
            worst_20trading_day_pct=float(worst_20d), worst_20day_window_ending=str(worst_20d_end.date()),
            worst_20day_ret_on_10pct_margin=float(worst_20d) / 0.10,
        ),
        hypothetical_shock_table=shock_table,
    )
    with open(HERE / "LEVERAGE_DEMO.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    weekly.to_csv(HERE / "LEVERAGE_WEEKLY.csv", index=False)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
