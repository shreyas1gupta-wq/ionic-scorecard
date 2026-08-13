"""ADV extraction for NIFTY futures (SWEEP vehicle) and NIFTY 0DTE ATM options (S1-F vehicle).
Source: Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2025,2026}.parquet
        (NSE official F&O bhavcopy, CONTRACTS col = lots traded that day; verified row counts logged).
Output: adv_futures_daily.csv, adv_options_expiry_daily.csv, adv_summary.json
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DATA = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CAPACITY_20260803"

fut_parts, opt_parts = [], []
for yr in (2025, 2026):
    p = DATA / f"fo_idx_{yr}.parquet"
    d = pd.read_parquet(p, columns=["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR",
                                     "OPTION_TYP", "CLOSE", "CONTRACTS", "TIMESTAMP"])
    d["TIMESTAMP"] = pd.to_datetime(d["TIMESTAMP"], format="%d-%b-%Y", errors="coerce")
    print(f"[loaded] {p.name}: {len(d):,} rows, {d['TIMESTAMP'].min().date()}..{d['TIMESTAMP'].max().date()}")
    fut_parts.append(d[(d.INSTRUMENT == "FUTIDX") & (d.SYMBOL == "NIFTY")].copy())
    opt_parts.append(d[(d.INSTRUMENT == "OPTIDX") & (d.SYMBOL == "NIFTY")].copy())
    del d

# ---------------------------------------------------------------- FUTURES (SWEEP vehicle)
fut = pd.concat(fut_parts, ignore_index=True)
del fut_parts
fut["EXPIRY_DT"] = pd.to_datetime(fut["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce")

# all-contracts (all expiries, near+far month) market volume per day -- true total ADV
fut_all_day = fut.groupby("TIMESTAMP")["CONTRACTS"].sum().sort_index()
# near-month only: the contract with nearest (>= day) expiry each day -- what an intraday sleeve
# actually trades (far-month NIFTY futures are thin; near-month carries almost all volume)
fut_sorted = fut.sort_values(["TIMESTAMP", "EXPIRY_DT"])
near = fut_sorted[fut_sorted.EXPIRY_DT >= fut_sorted.TIMESTAMP].groupby("TIMESTAMP").first()
near_vol = near["CONTRACTS"].sort_index()
near_close = near["CLOSE"].sort_index()

fut_daily = pd.DataFrame({"all_contracts_vol": fut_all_day, "near_month_vol": near_vol,
                           "near_month_close": near_close}).dropna()
fut_daily["adv20_all"] = fut_daily["all_contracts_vol"].rolling(20, min_periods=10).mean()
fut_daily["adv20_near"] = fut_daily["near_month_vol"].rolling(20, min_periods=10).mean()
fut_daily.to_csv(OUT / "adv_futures_daily.csv")
print(f"[futures] {len(fut_daily)} days written; last 5:")
print(fut_daily.tail(5).to_string())

recent = fut_daily.loc["2026-01-01":]
print(f"\n[futures 2026 YTD] all-contracts ADV20 median={recent['adv20_all'].median():,.0f} lots, "
      f"near-month ADV20 median={recent['adv20_near'].median():,.0f} lots, "
      f"spot median={recent['near_month_close'].median():,.0f}")

# ---------------------------------------------------------------- OPTIONS (S1-F vehicle, 0DTE ATM)
opt = pd.concat(opt_parts, ignore_index=True)
del opt_parts
opt["EXPIRY_DT"] = pd.to_datetime(opt["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce")
# 0DTE rows: the trading day IS the expiry day
zdte = opt[opt.TIMESTAMP == opt.EXPIRY_DT].copy()
print(f"\n[options 0DTE] {len(zdte):,} rows across {zdte['TIMESTAMP'].nunique()} expiry days")

rows = []
for (day, exp), g in zdte.groupby(["TIMESTAMP", "EXPIRY_DT"]):
    # proxy spot for that day = near-month futures close (already computed above)
    if day not in fut_daily.index:
        continue
    spot = fut_daily.loc[day, "near_month_close"]
    g = g.copy()
    g["dist"] = (g["STRIKE_PR"] - spot).abs()
    atm_strike = g.loc[g["dist"].idxmin(), "STRIKE_PR"]
    atm_rows = g[g["STRIKE_PR"] == atm_strike]
    ce_vol = atm_rows.loc[atm_rows.OPTION_TYP == "CE", "CONTRACTS"].sum()
    pe_vol = atm_rows.loc[atm_rows.OPTION_TYP == "PE", "CONTRACTS"].sum()
    ce_prem = atm_rows.loc[atm_rows.OPTION_TYP == "CE", "CLOSE"]
    pe_prem = atm_rows.loc[atm_rows.OPTION_TYP == "PE", "CLOSE"]
    rows.append(dict(day=day, expiry=exp, spot=spot, atm_strike=atm_strike,
                      atm_ce_vol=ce_vol, atm_pe_vol=pe_vol,
                      atm_straddle_vol_min=min(ce_vol, pe_vol),  # the tighter leg gates the whole straddle
                      atm_straddle_vol_sum=ce_vol + pe_vol,
                      ce_premium=ce_prem.iloc[0] if len(ce_prem) else np.nan,
                      pe_premium=pe_prem.iloc[0] if len(pe_prem) else np.nan))
O = pd.DataFrame(rows).sort_values("day")
O.to_csv(OUT / "adv_options_expiry_daily.csv", index=False)
print(f"[options] {len(O)} 0DTE-expiry days written")
print(O.tail(10).to_string())

o26 = O[O.day >= "2026-01-01"]
summary = dict(
    futures_window="2025-01..latest 2026 (bhavcopy)",
    fut_2026ytd_adv20_all_median=float(recent["adv20_all"].median()),
    fut_2026ytd_adv20_near_median=float(recent["adv20_near"].median()),
    fut_2026ytd_spot_median=float(recent["near_month_close"].median()),
    n_expiry_days_2026ytd=int(len(o26)),
    opt_atm_straddle_vol_median_2026ytd=float(o26["atm_straddle_vol_sum"].median()),
    opt_atm_ce_vol_median_2026ytd=float(o26["atm_ce_vol"].median()),
    opt_atm_pe_vol_median_2026ytd=float(o26["atm_pe_vol"].median()),
    opt_atm_straddle_vol_p10_2026ytd=float(o26["atm_straddle_vol_sum"].quantile(0.10)),
    opt_atm_premium_median_2026ytd=float((o26["ce_premium"] + o26["pe_premium"]).median()),
)
json.dump(summary, open(OUT / "adv_summary.json", "w"), indent=2, default=str)
print("\n[summary]")
print(json.dumps(summary, indent=2))
