"""SELL_PLUS_TAIL_20260803 -- step 5/6 support: capital-multiple (k) scan + pessimistic-bound
crash-stress-with-hedge table.

Part 1 (Part C -- efficient frontier of carry given up vs drawdown bought):
cells.csv's "margin basis" (capital = bare 10% margin, k=1x) and "notional basis" (capital =
full notional, k~10x) are the two extremes already computed by combine_book.py. Neither is the
realistic operating point: no real book holds capital = bare margin (one bad day -> margin call
cascade) NOR capital = full notional (that erases the entire point of writing options on margin).
This script finds, PER CELL, the minimum capital multiple k (capital_rs = k * margin_rs, held
fixed in Rs terms per event... actually margin_rs floats with spot per LD_SELL's own convention,
so capital_k_rs = k * margin_rs at each event, same floating-margin convention, just wider) such
that BOTH firm ceilings are met: full-sample MaxDD <= 25% AND combined COVID(Feb-Jun 2020) loss
<= 20% of that capital. Reuses combine_book.py's combined_series()/metrics_from_events() logic
and the SAME cached checkpoints -- no re-extraction.

Part 2 (Part E -- max survivable short-premium notional under a COVID repeat WITH the hedge):
Uses the PESSIMISTIC bound already measured in VALIDATION_DEBTS_20260731/tail_stress.csv (20-day
worst NIFTY move -37.0057% on 2020-03-23, at 0%-OTM/ATM strike distance -- i.e. assume NO cushion
from the short strike's own OTM distance, the conservative bound per the pathsafe standard) netted
against the tail put's intrinsic payoff at the SAME crash magnitude, at hedge ratios x moneyness,
expressed as a multiple of margin at both 10% (unhedged) and 5% (same-expiry-hedged, SPAN relief)
margin rates.
"""
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
LOT = 65
COVID_WIN = (pd.Timestamp("2020-02-01"), pd.Timestamp("2020-06-30"))
RATIOS = [0.0, 0.25, 0.50, 0.75, 1.00]
K_GRID = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 12, 15]

core = pd.read_csv(OUT / "checkpoints" / "core_trades_recost.csv",
                    parse_dates=["entry_day", "exit_day", "expiry"])
core16 = core[core["entry_day"] >= "2016-01-01"].sort_values("exit_day").reset_index(drop=True)
grid = pd.read_csv(OUT / "checkpoints" / "tail_put_grid_summary.csv")


def combined_events(core_df, hedge_df, hedge_ratio):
    ev = []
    for _, r in core_df.iterrows():
        ev.append(dict(date=r["exit_day"], rs=r["pl_rs_net_recost_new"], margin_rs=r["margin_rs"]))
    if hedge_ratio > 0 and hedge_df is not None and len(hedge_df):
        for _, r in hedge_df.iterrows():
            ev.append(dict(date=pd.Timestamp(r["exit_date"]),
                            rs=hedge_ratio * r["net_pnl_new_stt"] * LOT, margin_rs=None))
    ev = pd.DataFrame(ev).sort_values("date").reset_index(drop=True)
    ev["margin_rs"] = ev["margin_rs"].ffill().bfill()
    return ev


def metrics_at_k(ev, k):
    ret = ev["rs"] / (k * ev["margin_rs"])
    nav = (1 + ret).cumprod()
    n_years = (ev["date"].max() - ev["date"].min()).days / 365.25
    cagr = nav.iloc[-1] ** (1 / n_years) - 1
    peak = nav.cummax()
    dd = (nav - peak) / peak
    maxdd = dd.min()
    return 100 * cagr, 100 * maxdd


def covid_pct_at_k(core_covid_rs, hedge_covid_rs, ref_margin_rs, k):
    return 100 * (core_covid_rs + hedge_covid_rs) / (k * ref_margin_rs)


# ---------- Part 1: capital-multiple (k) scan, all 60 cells ----------
rows = []
for _, g in grid.iterrows():
    cfg = f"{g['tenor']}_{g['moneyness']}"
    hedge_df = pd.read_csv(OUT / "checkpoints" / f"tail_trades_{cfg}.csv",
                            parse_dates=["entry_date", "expiry", "exit_date"])
    hedge16 = hedge_df[hedge_df["entry_date"] >= "2016-01-01"]
    covid_payoff_100 = g["covid_payoff_new_stt_pts"]

    core_covid = core16[(core16["exit_day"] >= COVID_WIN[0]) & (core16["entry_day"] <= COVID_WIN[1])]
    core_covid_rs = core_covid["pl_rs_net_recost_new"].sum()
    ref_row = core16.iloc[(core16["entry_day"] - pd.Timestamp("2020-03-01")).abs().argsort()[:1]]
    ref_margin_rs = float(ref_row["margin_rs"].iloc[0])

    for ratio in RATIOS:
        ev = combined_events(core16, hedge16, ratio)
        hedge_covid_rs = ratio * covid_payoff_100 * LOT
        min_k = None
        chosen = None
        for k in K_GRID:
            cagr_k, maxdd_k = metrics_at_k(ev, k)
            covid_k = covid_pct_at_k(core_covid_rs, hedge_covid_rs, ref_margin_rs, k)
            if maxdd_k >= -25.0 and covid_k >= -20.0:
                min_k = k
                chosen = (cagr_k, maxdd_k, covid_k)
                break
        if min_k is None:
            # not satisfied even at largest k tested
            cagr_k, maxdd_k = metrics_at_k(ev, K_GRID[-1])
            covid_k = covid_pct_at_k(core_covid_rs, hedge_covid_rs, ref_margin_rs, K_GRID[-1])
            rows.append(dict(tenor=g["tenor"], moneyness=g["moneyness"], hedge_ratio=ratio,
                              min_k_for_compliance=f">{K_GRID[-1]}", cagr_at_k=cagr_k,
                              maxdd_at_k=maxdd_k, covid_at_k=covid_k))
        else:
            rows.append(dict(tenor=g["tenor"], moneyness=g["moneyness"], hedge_ratio=ratio,
                              min_k_for_compliance=min_k, cagr_at_k=chosen[0],
                              maxdd_at_k=chosen[1], covid_at_k=chosen[2]))

K = pd.DataFrame(rows)
K.to_csv(OUT / "checkpoints" / "capital_multiple_scan.csv", index=False)
print("=== min capital multiple k (capital = k x bare 10pct margin) for BOTH ceilings ===")
print("(25pct full-sample MaxDD ceiling AND 20pct COVID-window bar; margin_rs floats with spot,")
print(" same convention as LD_SELL's own registered numbers)")
print(K.sort_values(["tenor", "moneyness", "hedge_ratio"]).to_string(index=False))

best = K[K["min_k_for_compliance"].apply(lambda x: isinstance(x, (int, float)))].copy()
best = best.sort_values(["min_k_for_compliance", "cagr_at_k"], ascending=[True, False])
print("\n=== TOP 10 cells by LOWEST capital multiple needed (cheapest compliance route) ===")
print(best.head(10).to_string(index=False))

# ---------- Part 2: pessimistic-bound crash stress WITH hedge, at 10% vs 5% margin ----------
WORST_20D = 0.3700567  # measured, VALIDATION_DEBTS tail_stress.csv, 2020-03-23, 20-day NIFTY move
S1_RATIO = 1 - WORST_20D
MONEY = {"3pct": 0.97, "5pct": 0.95, "7pct": 0.93, "10pct": 0.90}

print("\n\n=== PART E: pessimistic-bound (0%-OTM short strike, 20-day -37.01% measured) ===")
print("=== crash stress WITH hedge, loss as multiple of margin, 10pct unhedged vs 5pct hedged ===")
stress_rows = []
for mname, ofrac in MONEY.items():
    payoff_pct = max(ofrac - S1_RATIO, 0.0)  # intrinsic payoff, % of notional, GROSS
    for r in RATIOS:
        loss_pct_notional = WORST_20D - r * payoff_pct  # combined short+hedge loss, % notional
        mult_10 = loss_pct_notional / 0.10
        mult_5 = loss_pct_notional / 0.05
        stress_rows.append(dict(moneyness=mname, hedge_ratio=r, payoff_pct_notional=100 * payoff_pct,
                                 combined_loss_pct_notional=100 * loss_pct_notional,
                                 loss_as_multiple_10pct_margin=mult_10,
                                 loss_as_multiple_5pct_margin=mult_5))
ST = pd.DataFrame(stress_rows)
ST.to_csv(OUT / "checkpoints" / "pessimistic_stress_with_hedge.csv", index=False)
print(ST.to_string(index=False))
print("\nreference: unhedged (r=0) at 10pct margin = 3.70x margin wiped out (matches VALIDATION_DEBTS)")
