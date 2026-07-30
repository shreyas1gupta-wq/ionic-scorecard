"""IV term-structure / cheapness candidate builder (test #3 in the brief).
Uses:
  - India VIX (2016-2026, official NSE implied-vol index) for a GENUINE multi-year percentile of
    front-month-ish IV -- avoids re-deriving a percentile from a short option-chain history.
  - fo_bhavcopy_hist daily archive (2011-2026) to build a MONTHLY-expiry ATM straddle term slope
    (front monthly vs next monthly), independent of VIX, for the "term slope flat/inverted" leg.
Entries executed later on 2021-2026 real 1-min option prices (option-data-covered span only).
"""
import sys, gc
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
BHAV_DIR = r"Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
OPT_START = pd.Timestamp("2021-05-24")
OPT_END = pd.Timestamp("2026-06-02")

# ---------------------------------------------------------- 1. India VIX expanding percentile
idxall = pd.read_parquet(r"datasets/index_daily/nse_official_all_indices.parquet")
vix = idxall[idxall.index_name == "India VIX"][["date", "close"]].rename(columns={"close": "vix"})
vix["date"] = pd.to_datetime(vix["date"])
vix = vix.sort_values("date").drop_duplicates("date").set_index("date")
spot = idxall[idxall.index_name.str.strip() == "Nifty 50"][["date", "close"]].rename(columns={"close": "spot"})
spot["date"] = pd.to_datetime(spot["date"])
spot = spot.sort_values("date").drop_duplicates("date").set_index("date")

# expanding percentile: rank of today's VIX among ALL PRIOR days only (shift(1) avoids same-day leak)
def expanding_pct_rank(s, minobs=250):
    out = pd.Series(np.nan, index=s.index)
    vals = s.values
    for i in range(minobs, len(vals)):
        prior = vals[:i]
        out.iloc[i] = (prior < vals[i]).mean()
    return out

print("[vix] computing expanding percentile (this loops but n~2600, fine)...", flush=True)
vix["vix_pct_expanding"] = expanding_pct_rank(vix["vix"])
print(vix.tail(3))

# ---------------------------------------------------------- 2. Monthly ATM straddle term slope, 2021-2026 only
rows = []
for year in range(2021, 2027):
    path = f"{BHAV_DIR}/fo_idx_{year}.parquet"
    print(f"[bhav] {year}", flush=True)
    d = pd.read_parquet(path, columns=["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP",
                                        "CLOSE", "CONTRACTS", "TIMESTAMP"])
    d = d[(d.SYMBOL == "NIFTY") & (d.INSTRUMENT == "OPTIDX") & (d.CONTRACTS > 0)].copy()
    d["EXPIRY_DT"] = pd.to_datetime(d["EXPIRY_DT"], format="mixed", dayfirst=True)
    d["TIMESTAMP"] = pd.to_datetime(d["TIMESTAMP"], format="mixed", dayfirst=True)
    # monthly expiry = the LAST expiry date within each (y,m) of EXPIRY_DT
    d["ym"] = d["EXPIRY_DT"].dt.to_period("M")
    monthly_exp = d.groupby("ym")["EXPIRY_DT"].max()
    d["is_monthly"] = d["EXPIRY_DT"].isin(set(monthly_exp.values))
    dm = d[d["is_monthly"]].copy()
    del d
    days = sorted(dm["TIMESTAMP"].unique())
    monthlies = sorted(dm["EXPIRY_DT"].unique())
    for day in days:
        fut_exp = [e for e in monthlies if (e - day).days >= 1]
        if len(fut_exp) < 2:
            continue
        front_e, next_e = fut_exp[0], fut_exp[1]
        sp = spot["spot"].asof(day)
        if not np.isfinite(sp):
            continue
        for tag, exp in (("front", front_e), ("next", next_e)):
            dte = (exp - day).days
            sub = dm[(dm.TIMESTAMP == day) & (dm.EXPIRY_DT == exp)]
            if len(sub) == 0:
                continue
            strikes = sub["STRIKE_PR"].unique()
            atm = strikes[np.argmin(np.abs(strikes - sp))]
            ce = sub[(sub.STRIKE_PR == atm) & (sub.OPTION_TYP == "CE")]
            pe = sub[(sub.STRIKE_PR == atm) & (sub.OPTION_TYP == "PE")]
            if len(ce) == 0 or len(pe) == 0:
                continue
            straddle = float(ce["CLOSE"].iloc[0]) + float(pe["CLOSE"].iloc[0])
            iv_proxy = straddle / (sp * 0.7978845608 * np.sqrt(dte / 365.0))
            rows.append(dict(date=day, tag=tag, dte=dte, atm=atm, spot=sp, iv_proxy=iv_proxy))
    del dm
    gc.collect()

T = pd.DataFrame(rows)
piv = T.pivot_table(index="date", columns="tag", values="iv_proxy", aggfunc="first")
piv["term_slope"] = piv["next"] - piv["front"]
piv = piv.join(vix[["vix", "vix_pct_expanding"]])
piv = piv[(piv.index >= OPT_START) & (piv.index <= OPT_END)]
print(f"\n[term] {len(piv)} days with front+next monthly IV proxy, option-covered span")
print(piv.describe())

piv.to_parquet(f"{OUT}/iv_term_daily.parquet")
print("wrote iv_term_daily.parquet")

# pre-register gate on BUILD era only (<2024-10-01)
build = piv[piv.index < pd.Timestamp("2024-10-01")]
q_vix_low = build["vix_pct_expanding"].quantile(0.20)
print(f"\n[gate] vix_pct_expanding <= {q_vix_low:.3f} (build-era q20) AND term_slope <= 0 (flat/inverted)")
gate = (piv["vix_pct_expanding"] <= q_vix_low) & (piv["term_slope"] <= 0)
print(f"gate fires on {gate.sum()} of {len(piv)} days ({gate.mean():.1%})")
gdays = piv.index[gate.fillna(False)]
print(gdays[:10], "..." if len(gdays) > 10 else "")

with open(f"{OUT}/iv_gate_threshold.txt", "w") as f:
    f.write(f"q_vix_low_p20_buildera={q_vix_low}\nterm_slope_threshold=0 (flat-or-inverted)\n")
pd.Series(gdays, name="gate_day").to_frame().to_csv(f"{OUT}/iv_gate_days.csv", index=False)
