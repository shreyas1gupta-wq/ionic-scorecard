"""NICHE 4 bonus — Union Budget day, zero-new-data check (n small, NON-DECISIVE, per PREREG.md).
Main scheduled-event test (RBI MPC / FOMC) is SKIPPED: no D-009-verified PIT macro-event
calendar exists on disk (checked DATA_CATALOG.md, 05_DATA_OFFICE/, repo-wide search for
rbi/mpc/fomc calendar files -- none found). Budget day (always Feb 1 since 2017, a fixed public
calendar fact, no dataset needed) is the only zero-new-data event we can test. We VERIFY each
candidate date against our OWN spot data rather than assume it was a trading day (e.g. weekend).
Uses the SAME per-day straddle snapshot already computed in daily_vol_series.csv -- no new data
pull, no new option-chain reads.
"""
import pandas as pd
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent
CANDIDATES = ["2022-02-01", "2023-02-01", "2024-02-01", "2024-07-23", "2025-02-01", "2026-02-01"]

df = pd.read_csv(OUT / "daily_vol_series.csv", parse_dates=["day"])
df = df.set_index("day").sort_index()
days = df.index

rows = []
for cd in CANDIDATES:
    cd_ts = pd.Timestamp(cd)
    if cd_ts not in days:
        rows.append(dict(budget_day=cd, status="NOT_A_TRADING_DAY_IN_OUR_DATA"))
        continue
    loc = days.get_loc(cd_ts)
    if loc == 0:
        rows.append(dict(budget_day=cd, status="no_prior_day")); continue
    prev_ts = days[loc - 1]
    d0, dm1 = df.loc[cd_ts], df.loc[prev_ts]
    if pd.isna(dm1["straddle_price"]) or pd.isna(d0["straddle_price"]):
        rows.append(dict(budget_day=cd, status="missing_straddle_price")); continue
    strike_match = dm1["atm_strike"] == d0["atm_strike"]
    ratio = d0["straddle_price"] / dm1["straddle_price"]
    rows.append(dict(
        budget_day=cd, status="ok", prior_day=str(prev_ts.date()),
        prior_iv=dm1["iv"], prior_iv_pct=dm1["iv_pct"],
        prior_straddle=dm1["straddle_price"], event_day_straddle=d0["straddle_price"],
        strike_match=bool(strike_match), strike_prior=dm1["atm_strike"], strike_event=d0["atm_strike"],
        gap_ratio=ratio, gross_pts_1x=(d0["straddle_price"] - dm1["straddle_price"]),
        spot_move_pct=100 * (d0["spot_px"] / dm1["spot_px"] - 1),
    ))

out = pd.DataFrame(rows)
out.to_csv(OUT / "niche4_budget_bonus.csv", index=False)
print("=== NICHE 4 bonus: Union Budget day, straddle premium day-over-day (n small, NON-DECISIVE) ===")
print(out.to_string(index=False))
ok = out[out.status == "ok"]
if len(ok):
    print(f"\nn={len(ok)} usable Budget days | mean gap_ratio {ok['gap_ratio'].mean():.3f}x | "
          f"mean gross pts(1 lot=1x) {ok['gross_pts_1x'].mean():.2f} | "
          f"prior-day IV percentile mean {ok['prior_iv_pct'].mean():.1f} "
          f"(was IV cheap ahead of Budget, on average? >50=rich, <50=cheap)")
print("\nsaved ->", OUT / "niche4_budget_bonus.csv")
