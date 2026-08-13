"""SELL_PLUS_TAIL_20260803 -- step 4: combine core (short-premium) + tail-put overlay.

Merges the recost LD_SELL core (2016-2026 subset, matching the hedge data's availability window)
with each of the 12 tail-put configs (tenor x moneyness), at 5 hedge ratios (0/25/50/75/100% of the
core's LOT=65 notional), into one chronological return series per cell, compounded on a common
capital base = the core's own margin_rs (10% naked, dynamic with spot) at the time of each event.
This expresses the hedge cost/payoff AS A DRAG/OFFSET AGAINST THE SAME BOOK CAPITAL the core uses --
i.e. "how much does the hedge cost the SAME account that's writing the strangle."

Output: cells.csv (60 rows: 12 structures x 5 ratios) with CAGR/MaxDD/Sharpe/Calmar/ann.carry/
COVID-window combined outcome, plus the net-hedge-positive test (full-sample and crash-only).
"""
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
LOT = 65
COVID_WIN = (pd.Timestamp("2020-02-01"), pd.Timestamp("2020-06-30"))
RATIOS = [0.0, 0.25, 0.50, 0.75, 1.00]

core = pd.read_csv(OUT / "checkpoints" / "core_trades_recost.csv",
                    parse_dates=["entry_day", "exit_day", "expiry"])
core16 = core[core["entry_day"] >= "2016-01-01"].sort_values("exit_day").reset_index(drop=True)
print(f"core (2016-2026 subset): n={len(core16)}, "
      f"{core16['entry_day'].min().date()}..{core16['exit_day'].max().date()}")

grid = pd.read_csv(OUT / "checkpoints" / "tail_put_grid_summary.csv")


def combined_series(core_df, hedge_df, hedge_ratio):
    """Chronological merged return series. Computes returns on TWO capital bases so a capital-
    structure artifact doesn't get mistaken for a hedge result (see PROGRESS.md note):
      - margin basis:   rs / margin_rs   (margin_rs = 10% x notional -- the FIRM's own existing
        convention for LD_SELL's quoted CAGR/MaxDD; 10x levered)
      - notional basis: rs / notional    (notional = spot x LOT -- fully-collateralized, unlevered;
        the realistic base for a hedge whose premium is an outright cash outlay, not a margin draw)
    A first pass using margin_rs for BOTH core and hedge produced MaxDD that got WORSE as hedge_ratio
    rose (e.g. 1M/3pct: -69.8% at 0% hedge -> -98.4% at 100%) purely from compounding a 100%-notional
    put's real carry cost against a capital base that is only 10% of notional -- a 10x leverage
    artifact of the accounting convention, not a property of the hedge itself. Reporting notional-
    basis as the headline avoids that artifact; margin-basis is kept for cross-checking against the
    firm's already-published core-alone numbers (verified: reproduces -69.71% MaxDD / 16.25% CAGR
    for the core alone, see checkpoints/core_summary.csv)."""
    ev = []
    for _, r in core_df.iterrows():
        notional = r["spot_entry"] * LOT
        ev.append(dict(date=r["exit_day"], rs=r["pl_rs_net_recost_new"], margin_rs=r["margin_rs"],
                        notional=notional, kind="core"))
    if hedge_ratio > 0 and hedge_df is not None and len(hedge_df):
        for _, r in hedge_df.iterrows():
            ev.append(dict(date=pd.Timestamp(r["exit_date"]),
                            rs=hedge_ratio * r["net_pnl_new_stt"] * LOT, margin_rs=None,
                            notional=None, kind="hedge"))
    ev = pd.DataFrame(ev).sort_values("date").reset_index(drop=True)
    # forward/back-fill a capital-base reference for hedge events from the nearest core event
    ev["margin_rs"] = ev["margin_rs"].ffill().bfill()
    ev["notional"] = ev["notional"].ffill().bfill()
    ev["ret_margin"] = ev["rs"] / ev["margin_rs"]
    ev["ret_notional"] = ev["rs"] / ev["notional"]
    return ev


def metrics_from_events(ev, retcol):
    if len(ev) < 2:
        return None
    nav = (1 + ev[retcol]).cumprod()
    n_years = (ev["date"].max() - ev["date"].min()).days / 365.25
    if n_years <= 0:
        return None
    cagr = nav.iloc[-1] ** (1 / n_years) - 1
    peak = nav.cummax()
    dd = (nav - peak) / peak
    maxdd = dd.min()
    maxdd_date = ev["date"].iloc[dd.values.argmin()]
    tpy = len(ev) / n_years
    mu, sd = ev[retcol].mean(), ev[retcol].std()
    sharpe = (mu / sd) * np.sqrt(tpy) if sd > 0 else np.nan
    calmar = cagr / abs(maxdd) if maxdd < 0 else np.nan
    return dict(cagr_pct=100 * cagr, maxdd_pct=100 * maxdd, maxdd_date=str(maxdd_date.date()),
                sharpe=sharpe, calmar=calmar, n_events=len(ev), span_yr=n_years)


rows = []
for _, g in grid.iterrows():
    cfg = f"{g['tenor']}_{g['moneyness']}"
    hedge_df = pd.read_csv(OUT / "checkpoints" / f"tail_trades_{cfg}.csv",
                            parse_dates=["entry_date", "expiry", "exit_date"])
    hedge16 = hedge_df[hedge_df["entry_date"] >= "2016-01-01"]
    ann_carry_full_pts = g["ann_cost_new_stt_pts"]  # pts/yr at 100% hedge ratio
    covid_payoff_pts_100 = g["covid_payoff_new_stt_pts"]

    # core-alone COVID combined loss reference (recost, new STT), Feb-Jun 2020 window
    core_covid = core16[(core16["exit_day"] >= COVID_WIN[0]) & (core16["entry_day"] <= COVID_WIN[1])]
    core_covid_rs = core_covid["pl_rs_net_recost_new"].sum()
    # representative margin (capital "at risk" going into the crash): the core position's own
    # margin_rs for the trade active right before/at the crash trough (2020-03-23)
    ref_row = core16.iloc[(core16["entry_day"] - pd.Timestamp("2020-03-01")).abs().argsort()[:1]]
    ref_margin_rs = float(ref_row["margin_rs"].iloc[0])
    ref_notional = float(ref_row["spot_entry"].iloc[0]) * LOT

    for ratio in RATIOS:
        ev = combined_series(core16, hedge16, ratio)
        m_marg = metrics_from_events(ev, "ret_margin")
        m_not = metrics_from_events(ev, "ret_notional")
        if m_marg is None or m_not is None:
            continue
        hedge_covid_rs = ratio * covid_payoff_pts_100 * LOT
        combined_covid_rs = core_covid_rs + hedge_covid_rs
        combined_covid_pct_margin = 100 * combined_covid_rs / ref_margin_rs
        combined_covid_pct_notional = 100 * combined_covid_rs / ref_notional
        core_covid_pct_margin = 100 * core_covid_rs / ref_margin_rs
        core_covid_pct_notional = 100 * core_covid_rs / ref_notional
        ann_carry_pts = ratio * ann_carry_full_pts
        ann_carry_rs = ann_carry_pts * LOT
        # full-sample net-hedge-positive test: does the hedge's OWN full-sample net P&L (all
        # hedge cycles 2016-2026, ratio-scaled) exceed zero -- i.e. does it pay for itself outright
        hedge_full_sample_rs = ratio * hedge16["net_pnl_new_stt"].sum() * LOT if ratio > 0 else 0.0
        # crash-only net-hedge-positive test: does the hedge's COVID-window payoff alone exceed the
        # hedge's OWN full-sample cost (i.e. did the crash payoff repay the carry spent to hold it)
        crash_pays_for_carry = hedge_covid_rs > 0 and hedge_covid_rs >= abs(hedge_full_sample_rs)

        rows.append(dict(
            tenor=g["tenor"], moneyness=g["moneyness"], hedge_ratio=ratio,
            # HEADLINE (notional/fully-collateralized basis -- realistic hedge funding)
            cagr_pct=m_not["cagr_pct"], maxdd_pct=m_not["maxdd_pct"], maxdd_date=m_not["maxdd_date"],
            sharpe=m_not["sharpe"], calmar=m_not["calmar"],
            # cross-check (margin/10x-levered basis -- firm's existing LD_SELL convention)
            cagr_pct_marginbasis=m_marg["cagr_pct"], maxdd_pct_marginbasis=m_marg["maxdd_pct"],
            calmar_marginbasis=m_marg["calmar"],
            ann_carry_pts_yr=ann_carry_pts, ann_carry_rs_yr=ann_carry_rs,
            hedge_full_sample_net_rs=hedge_full_sample_rs,
            hedge_pays_for_itself_full_sample=hedge_full_sample_rs > 0,
            core_covid_pct_margin=core_covid_pct_margin, core_covid_pct_notional=core_covid_pct_notional,
            combined_covid_rs=combined_covid_rs,
            combined_covid_pct_margin=combined_covid_pct_margin,
            combined_covid_pct_notional=combined_covid_pct_notional,
            hedge_covid_contribution_rs=hedge_covid_rs,
            crash_pays_for_own_carry=crash_pays_for_carry,
            n_events=m_not["n_events"], span_yr=m_not["span_yr"],
        ))

C = pd.DataFrame(rows)
C.to_csv(OUT / "cells.csv", index=False)
print(f"wrote cells.csv, {len(C)} rows ({C['tenor'].nunique()} tenors x "
      f"{C['moneyness'].nunique()} moneyness x {C['hedge_ratio'].nunique()} ratios)")
print(C[["tenor", "moneyness", "hedge_ratio", "cagr_pct", "maxdd_pct", "calmar",
          "maxdd_pct_marginbasis", "combined_covid_pct_notional",
          "combined_covid_pct_margin"]].to_string(index=False))
