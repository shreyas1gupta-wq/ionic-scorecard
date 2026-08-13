# -*- coding: utf-8 -*-
"""PART A -- validate/refute the 2.5x safety factor, on long-history benchmark indices.

Pre-registered before computing (Sameer Bhat, 2026-08-06):
  CALM window   = last 3 complete years of index history ending at the latest month-end
                  on file (2023-08-01 .. 2026-07-31). Verified below to not overlap any
                  named crisis window.
  CRISIS windows (named by the Principal, 2026-08-05):
    covid    2020-01-01 .. 2020-06-30
    y2018_19 2018-01-01 .. 2019-12-31   (Jan-2018 smallcap top + Sep-2018 IL&FS)
    y2022    2021-10-01 .. 2022-06-30
  ES90 computed on rolling 1-MONTH returns from month-end closes (same granularity the
  fund-level method will actually use).
  MDD computed twice per crisis: once from the SAME month-end series (apples-to-apples
  with ES90), and once from DAILY closes (the true peak-to-trough) -- the gap between the
  two is itself a finding about monthly-granularity understatement.
  multiple = |MDD_crisis| / |ES90_calm|.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\C--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500--claude-worktrees-sweet-austin-283067\60624b2b-b530-4e53-8e92-dc9dc2087600\scratchpad")
from tail_lib import es_90, mdd_from_returns, mdd_from_levels  # noqa: E402

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
FIRM = BASE + r"\.claude\worktrees\sweet-austin-283067\Shreyas_Ionic_AMC"
RESULTS = FIRM + r"\04_RND_LAB\results\MF_TAIL_TEST_20260806"

BENCH = {
    "Nifty 50": "Large Cap Fund",
    "Nifty Midcap 150": "Mid Cap Fund",
    "Nifty Smallcap 250": "Small cap Fund",
    "Nifty 500": "Flexi/Multi Cap Fund (broad proxy)",
}

CALM_START, CALM_END = "2023-08-01", "2026-07-31"
CRISES = {
    "covid_2020": ("2020-01-01", "2020-06-30"),
    "y2018_19_ilfs": ("2018-01-01", "2019-12-31"),
    "y2022_selloff": ("2021-10-01", "2022-06-30"),
}

# sanity: calm window must not overlap any crisis window
cs, ce = pd.Timestamp(CALM_START), pd.Timestamp(CALM_END)
for name, (s, e) in CRISES.items():
    s, e = pd.Timestamp(s), pd.Timestamp(e)
    overlap = max(cs, s) <= min(ce, e)
    assert not overlap, f"CALM window overlaps {name} -- fix before computing"
print("Calm-window/crisis-window overlap check: PASS (no overlap)")

idx = pd.read_parquet(BASE + r"\datasets\index_daily\nse_official_all_indices.parquet")
idx["date"] = pd.to_datetime(idx["date"])

rows = []
for iname, cat in BENCH.items():
    d = idx[idx["index_name"] == iname].sort_values("date").set_index("date")["close"]
    d = d[~d.index.duplicated(keep="last")]
    print(f"\n{iname}: {d.index.min().date()} -> {d.index.max().date()}, n_daily={len(d)}")

    # month-end series (last available daily close in each calendar month)
    me = d.resample("ME").last().dropna()
    me_ret = me.pct_change().dropna()

    calm_ret = me_ret[(me_ret.index >= CALM_START) & (me_ret.index <= CALM_END)]
    es90_calm = es_90(calm_ret)
    print(f"  calm window {CALM_START}..{CALM_END}: n_monthly_returns={len(calm_ret)}  ES90={es90_calm:.4%}")

    for cname, (s, e) in CRISES.items():
        # monthly-granularity MDD (same series ES90 was computed on)
        crisis_me_ret = me_ret[(me_ret.index >= s) & (me_ret.index <= e)]
        mdd_monthly = mdd_from_returns(crisis_me_ret) if len(crisis_me_ret) else np.nan

        # true daily MDD, using a short pre-buffer so the peak just before the window is captured
        buf_start = pd.Timestamp(s) - pd.Timedelta(days=45)
        crisis_daily = d[(d.index >= buf_start) & (d.index <= e)]
        mdd_daily = mdd_from_levels(crisis_daily) if len(crisis_daily) else np.nan

        mult_monthly = abs(mdd_monthly) / abs(es90_calm) if pd.notna(mdd_monthly) and es90_calm != 0 else np.nan
        mult_daily = abs(mdd_daily) / abs(es90_calm) if pd.notna(mdd_daily) and es90_calm != 0 else np.nan

        rows.append({
            "index": iname, "category_proxy": cat, "es90_calm": es90_calm,
            "n_calm_monthly_obs": len(calm_ret),
            "crisis": cname, "crisis_window": f"{s}..{e}",
            "mdd_monthly_granularity": mdd_monthly, "mdd_daily_granularity": mdd_daily,
            "multiple_monthly_basis": mult_monthly, "multiple_daily_basis": mult_daily,
        })
        print(f"    {cname:16s} MDD(monthly)={mdd_monthly:8.2%}  MDD(daily)={mdd_daily:8.2%}  "
              f"multiple(monthly)={mult_monthly:5.2f}x  multiple(daily)={mult_daily:5.2f}x")

out = pd.DataFrame(rows)
out.to_csv(RESULTS + r"\partA_safety_factor_by_index.csv", index=False)
print("\nsaved:", RESULTS + r"\partA_safety_factor_by_index.csv")

print("\n=== SUMMARY: multiple (daily-basis, the honest one) ===")
print(out.groupby("index")["multiple_daily_basis"].agg(["min", "median", "max"]))
print("\noverall median multiple (daily basis), all index x crisis cells:",
      round(out["multiple_daily_basis"].median(), 2))
print("overall mean multiple (daily basis):", round(out["multiple_daily_basis"].mean(), 2))
print("\n=== SUMMARY: multiple (monthly-basis, apples-to-apples with the deployed method) ===")
print(out.groupby("index")["multiple_monthly_basis"].agg(["min", "median", "max"]))
print("overall median multiple (monthly basis):", round(out["multiple_monthly_basis"].median(), 2))
