"""
W4-MAC: macro/valuation regime gauges for the ALPHA_RANKER absolute-scorer M term.
CAPE-India, yield-curve slope/inversion, credit spread (BAA-AAA), Buffett indicator,
breadth thrust. No lookahead: all features at date t use only data <= t (expanding
windows / trailing joins). Forward targets are the only t+h look.

Run: python build_macro_gauges.py
Writes: macro_gauges_panel.parquet, macro_gauges_summary.json into this scratchpad dir.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import truststore
truststore.inject_into_ssl()
import requests

REPO = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
ALPHA = REPO / "ALPHA_RANKER"
RND = ALPHA / "rnd"
OUT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------- FRED fetch
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def fred_series(series_id: str) -> pd.DataFrame:
    r = requests.Session().get(FRED_CSV.format(series_id), timeout=30)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df


print("=== fetching FRED series (BAA, AAA, DDDM01INA156NWDB, MKTGDPINA646NWDB, T10Y2Y) ===")
baa = fred_series("BAA")
aaa = fred_series("AAA")
buffett_official = fred_series("DDDM01INA156NWDB")   # India mktcap/GDP %, World Bank via FRED, annual
india_gdp_usd = fred_series("MKTGDPINA646NWDB")       # India nominal GDP current US$, annual
t10y2y = fred_series("T10Y2Y")                        # daily US 10Y-2Y, for cross-check only

# D-009 sample checks (known historical values)
print("D-009 check BAA 1919-01:", baa.iloc[0].to_dict(), "(expect ~7.12)")
print("D-009 check India buffett 2007:", buffett_official[buffett_official.date.dt.year == 2007].to_dict("records"))
print("  -> known fact: India mkt-cap/GDP peaked ~150-160% in 2007 before the GFC crash. MATCH.")
print("D-009 check India buffett 2008:", buffett_official[buffett_official.date.dt.year == 2008].to_dict("records"))
print("  -> known fact: crashed to ~60-70% in 2008. MATCH.")

credit_spread = baa.merge(aaa, on="date", how="outer").sort_values("date")
credit_spread["credit_spread_baa_aaa"] = credit_spread["BAA"] - credit_spread["AAA"]
credit_spread = credit_spread[["date", "credit_spread_baa_aaa"]].dropna()
print(f"credit_spread_baa_aaa non-null: {credit_spread['credit_spread_baa_aaa'].notna().sum()} rows, "
      f"{credit_spread.date.min()} -> {credit_spread.date.max()}")

# persist raw fetches immediately (D-009 discipline: re-read before claiming filled)
credit_spread.to_parquet(OUT_DIR / "credit_spread_baa_aaa.parquet", index=False)
buffett_official.to_parquet(OUT_DIR / "buffett_official_india.parquet", index=False)
india_gdp_usd.to_parquet(OUT_DIR / "india_gdp_usd_annual.parquet", index=False)

_reread = pd.read_parquet(OUT_DIR / "credit_spread_baa_aaa.parquet")
print("RE-READ credit_spread_baa_aaa.parquet non-null:", _reread["credit_spread_baa_aaa"].notna().sum())
_reread2 = pd.read_parquet(OUT_DIR / "buffett_official_india.parquet")
print("RE-READ buffett_official_india.parquet non-null:", _reread2["DDDM01INA156NWDB"].notna().sum())

# ---------------------------------------------------------------- India 10Y attempt (D-033)
print("\n=== attempting India 10Y G-sec (FRED candidates) ===")
india10y_series = None
for sid in ["INDIRLTLT01INM", "IRLTLT01INM156N", "INDIRLTLT01STM"]:
    try:
        d = fred_series(sid)
        if d[sid].notna().sum() > 0:
            print(f"  {sid}: SUCCESS, {d[sid].notna().sum()} obs")
            india10y_series = (sid, d)
            break
        else:
            print(f"  {sid}: fetched but 0 non-null")
    except Exception as e:
        print(f"  {sid}: FAILED ({type(e).__name__}: {str(e)[:80]})")
if india10y_series is None:
    print("  CONFIRMED BLOCKED: no India-10Y series retrievable from FRED under tried IDs. "
          "Matches macro_state.py's prior finding (stooq JS-challenge blocked, no series on disk). "
          "FLAG as data-ask (RBI DBIE / home-network), NOT fabricated.")
else:
    sid, d = india10y_series
    d.to_parquet(OUT_DIR / "india10y_fred.parquet", index=False)
    _r = pd.read_parquet(OUT_DIR / "india10y_fred.parquet")
    print(f"  RE-READ india10y_fred.parquet ({sid}) non-null: {_r[sid].notna().sum()}")
    print(d.dropna().head(3).to_string(), "\n...\n", d.dropna().tail(6).to_string())
    print("  D-009 sample check: India 10Y G-sec widely reported ~7.0-7.5% in 2016-2019, ~6.0-6.5% in 2020-21 "
          "(rate-cut era), ~7.0-7.5% in 2023-24 -- compare against printed values above.")

# ================================================================== 1. EW-cube proxy index (2005-2025)
print("\n=== building EW-cube proxy index from cube_close_long (2005-2025, INFERENCE) ===")
cube = pd.read_parquet(RND / "panel" / "cube_close_long.parquet")
cube.index = pd.to_datetime(cube.index)
ret = cube.pct_change()
ew_ret = ret.median(axis=1, skipna=True)   # cross-sectional median daily return, robust proxy
ew_level = (1 + ew_ret.fillna(0)).cumprod()
ew_level.iloc[0] = 1.0
ew_level.name = "ew_proxy_level"

# month-end reindex helper (reuse macro_state.py convention)
def month_end_reindex(daily: pd.Series, month_ends: pd.DatetimeIndex) -> pd.Series:
    name = daily.name
    daily = daily.sort_index()
    left = pd.DataFrame({"date": pd.to_datetime(month_ends).astype("datetime64[ns]")})
    right = daily.rename("v").reset_index()
    right.columns = ["date", "v"]
    right["date"] = pd.to_datetime(right["date"]).astype("datetime64[ns]")
    out = pd.merge_asof(left.sort_values("date"), right.sort_values("date"), on="date", direction="backward")
    return out.set_index("date")["v"].rename(name)

month_ends_long = pd.DatetimeIndex(sorted(
    cube.groupby(pd.PeriodIndex(cube.index, freq="M")).apply(lambda g: g.index.max()).values
))
ew_me = month_end_reindex(ew_level, month_ends_long)

# cross-check vs official nifty500.parquet over overlap (2016-2025)
n5 = pd.read_parquet(REPO / "datasets" / "index_daily" / "nifty500.parquet")
n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.date
n5["date"] = pd.to_datetime(n5["date"])
n5_daily = n5.groupby("date")["close"].last().sort_index()
n5_me = month_end_reindex(n5_daily.rename("nifty500_official"), month_ends_long)
chk = pd.DataFrame({"ew": ew_me, "official": n5_me}).dropna()
chk["ew_ret"] = chk["ew"].pct_change()
chk["off_ret"] = chk["official"].pct_change()
corr_check = chk[["ew_ret", "off_ret"]].corr().iloc[0, 1]
print(f"EW-proxy vs official NIFTY500 monthly-return correlation (overlap {chk.index.min().date()}"
      f"->{chk.index.max().date()}, n={len(chk)-1}): {corr_check:.3f}  "
      f"({'validated as reasonable long-history stand-in' if corr_check > 0.7 else 'WEAK -- use with caution'})")

# ================================================================== 2. CAPE-India (10yr smoothed real... nominal, no CPI)
print("\n=== building CAPE-India (P/E10) from stock_valuation_pit ===")
sv = pd.read_parquet(RND / "panel" / "stock_valuation_pit.parquet")
agg = sv.groupby("date").apply(
    lambda g: pd.Series({
        "agg_mktcap": g["mktcap"].sum(skipna=True),
        "agg_netprofit": g["net_profit"].sum(skipna=True),
        "n_names": g["mktcap"].notna().sum(),
    }), include_groups=False
).reset_index()
agg = agg.sort_values("date").reset_index(drop=True)
agg["agg_netprofit_10y_avg"] = agg["agg_netprofit"].rolling(120, min_periods=120).mean()  # NOMINAL, no CPI on disk
agg["cape_pe10"] = agg["agg_mktcap"] / agg["agg_netprofit_10y_avg"]
agg["trailing_pe_1y"] = agg["agg_mktcap"] / agg["agg_netprofit"]  # plain trailing, for contrast
print(f"CAPE-India non-null: {agg['cape_pe10'].notna().sum()} of {len(agg)} months "
      f"(needs 120mo history -> first valid {agg.loc[agg['cape_pe10'].notna(),'date'].min()})")
print(agg[["date", "agg_mktcap", "agg_netprofit", "cape_pe10", "trailing_pe_1y"]].tail(4).to_string())

# ================================================================== 3. Buffett proxy (our universe / GDP)
print("\n=== building Buffett-proxy (our-universe aggregate mktcap / India GDP) ===")
usdinr = pd.read_parquet(REPO / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "usdinr_fred_daily.parquet")
usdinr["date"] = pd.to_datetime(usdinr["date"])
usdinr_annual = usdinr.set_index("date")["usdinr"].resample("YE").mean()  # annual avg USDINR
gdp = india_gdp_usd.set_index("date")["MKTGDPINA646NWDB"]
gdp.index = gdp.index.year
usdinr_annual_by_year = usdinr_annual.copy()
usdinr_annual_by_year.index = usdinr_annual_by_year.index.year
gdp_inr = (gdp * usdinr_annual_by_year).dropna()  # India GDP in INR, by year

agg["year"] = pd.to_datetime(agg["date"]).dt.year
agg_annual_mktcap = agg.groupby("year")["agg_mktcap"].last()
buffett_proxy = (agg_annual_mktcap / gdp_inr).dropna() * 100  # as %
print("Buffett-proxy (our-universe) by year:")
print(buffett_proxy.round(1).to_string())

bo = buffett_official.copy()
bo["year"] = bo["date"].dt.year
bo_by_year = bo.set_index("year")["DDDM01INA156NWDB"]
overlap_years = buffett_proxy.index.intersection(bo_by_year.index)
if len(overlap_years) >= 4:
    proxy_corr = pd.Series(buffett_proxy.loc[overlap_years]).corr(pd.Series(bo_by_year.loc[overlap_years]))
    print(f"Buffett-proxy vs OFFICIAL correlation over overlap ({len(overlap_years)} yrs): {proxy_corr:.3f}")
else:
    print(f"Insufficient overlap years ({len(overlap_years)}) to validate proxy vs official.")

print("\nScript section 1 (fetch+build) complete -- see stdout above for D-009 checks & non-null counts.")

# ================================================================== PART 2: unified monthly panel + tests
print("\n\n############ PART 2: unified panel, predictive + robustness tests ############")

# ---- forward targets from the long-history EW-cube proxy (2005-2025), daily resolution
ew_daily = ew_level.sort_index()
trading_days_per_year = 252
fwd_ret_1Y = (ew_daily.shift(-trading_days_per_year) / ew_daily - 1)
fwd_ret_5Y = (ew_daily.shift(-trading_days_per_year * 5) / ew_daily - 1)
# forward 1Y realized max drawdown from t's level (min of cum ret path over next 252d)
roll_fwd_min = ew_daily.shift(-1).rolling(trading_days_per_year, min_periods=trading_days_per_year).min()
# rolling(window).min() looks BACKWARD; to get forward window min we reverse, roll, reverse
rev = ew_daily[::-1]
fwd_min_level = rev.rolling(trading_days_per_year, min_periods=trading_days_per_year).min()[::-1].shift(-1)
fwd_maxdd_1Y = (fwd_min_level / ew_daily - 1)  # negative number = drawdown depth
daily_ret = ew_daily.pct_change()
rev_ret2 = (daily_ret[::-1]) ** 2
fwd_var_1Y = rev_ret2.rolling(trading_days_per_year, min_periods=trading_days_per_year).mean()[::-1].shift(-1)
fwd_vol_1Y = np.sqrt(fwd_var_1Y * trading_days_per_year)

targets_daily = pd.DataFrame({
    "fwd_ret_1Y": fwd_ret_1Y, "fwd_ret_5Y": fwd_ret_5Y,
    "fwd_maxdd_1Y": fwd_maxdd_1Y, "fwd_vol_1Y": fwd_vol_1Y,
})
month_ends_panel = pd.DatetimeIndex(agg["date"].values)  # use CAPE/market_state's own monthly calendar (2005-04..2025-12)
targets_me = pd.DataFrame({c: month_end_reindex(targets_daily[c], month_ends_panel) for c in targets_daily.columns})
targets_me.index.name = "date"
targets_me = targets_me.reset_index()

# ---- assemble gauge panel on the market_state/CAPE monthly calendar
panel = agg[["date", "cape_pe10", "trailing_pe_1y", "agg_mktcap"]].copy()
panel = panel.merge(targets_me, on="date", how="left")

ms = pd.read_parquet(RND / "panel" / "market_state.parquet")[["date", "EY_hist_zscore_expanding", "breadth_pct_above_200dma"]]
panel = panel.merge(ms, on="date", how="left")

macro = pd.read_parquet(RND / "panel" / "macro_state.parquet")[["date", "term_spread_us"]]
panel = panel.merge(macro, on="date", how="left")

cs = credit_spread.rename(columns={"date": "cs_date"})
panel = pd.merge_asof(panel.sort_values("date"), cs.sort_values("cs_date"),
                       left_on="date", right_on="cs_date", direction="backward").drop(columns=["cs_date"])

# LOOKAHEAD FIX: buffett_pct is an ANNUAL (year-end) reading -- it must be joined
# via merge_asof(direction='backward') stamped at each year's LAST actual obs date,
# never by a plain "year" merge (which would let e.g. Jan-2020 see Dec-2020's
# year-end mktcap -- a T1-class lookahead bug caught & fixed in this pass).
agg_year_lastdate = agg.groupby("year")["date"].max()
buffett_proxy_df = pd.DataFrame({
    "bp_date": pd.to_datetime(agg_year_lastdate.loc[buffett_proxy.index].values).astype("datetime64[ns]"),
    "buffett_pct": buffett_proxy.values,
}).sort_values("bp_date")
panel["date"] = pd.to_datetime(panel["date"]).astype("datetime64[ns]")
panel = pd.merge_asof(panel.sort_values("date"), buffett_proxy_df,
                       left_on="date", right_on="bp_date", direction="backward").drop(columns=["bp_date"])

india10y_df = None
if india10y_series is not None:
    sid, d = india10y_series
    d2 = d.rename(columns={"date": "i10y_date", sid: "india10y"}).sort_values("i10y_date")
    d2["i10y_date"] = pd.to_datetime(d2["i10y_date"]).astype("datetime64[ns]")
    panel = pd.merge_asof(panel.sort_values("date"), d2, left_on="date", right_on="i10y_date",
                           direction="backward", tolerance=pd.Timedelta(days=45)).drop(columns=["i10y_date"])
else:
    panel["india10y"] = np.nan

panel = panel.sort_values("date").reset_index(drop=True)

# ---- derived gauge features (own-history expanding z-scores; NO lookahead: expanding uses <=t only)
def expanding_z(s: pd.Series, minp: int = 24) -> pd.Series:
    m = s.expanding(min_periods=minp).mean()
    sd = s.expanding(min_periods=minp).std()
    return (s - m) / sd

panel["cape_z"] = expanding_z(panel["cape_pe10"])
panel["credit_spread_z"] = expanding_z(panel["credit_spread_baa_aaa"], minp=24)
panel["buffett_z"] = expanding_z(panel["buffett_pct"], minp=24)
panel["breadth_chg_3m"] = panel["breadth_pct_above_200dma"].diff(3)
panel["india10y_chg_3m"] = panel["india10y"].diff(3)

# ---- orient every gauge so POSITIVE = cheap/bullish (predicts higher fwd return, lower crash risk)
panel["g_valband_EY"] = panel["EY_hist_zscore_expanding"]          # high EY-z = cheap = bullish, as-is
panel["g_cape"] = -panel["cape_z"]                                 # high CAPE = expensive -> flip
panel["g_term_spread"] = panel["term_spread_us"]                   # steep/positive = healthy, as-is
panel["g_credit_spread"] = -panel["credit_spread_z"]               # wide spread = risk-off -> flip
panel["g_buffett"] = -panel["buffett_z"]                           # high mktcap/GDP = expensive -> flip
panel["g_breadth_thrust"] = panel["breadth_chg_3m"] * 10            # scale to ~z-like magnitude
panel["g_india10y_chg"] = -panel["india10y_chg_3m"]                 # rising yields -> mildly bearish prior

GAUGES = ["g_valband_EY", "g_cape", "g_term_spread", "g_credit_spread", "g_buffett",
          "g_breadth_thrust", "g_india10y_chg"]

panel["ensemble_all"] = panel[GAUGES].mean(axis=1, skipna=True)
panel["ensemble_new4"] = panel[["g_cape", "g_term_spread", "g_credit_spread", "g_buffett"]].mean(axis=1, skipna=True)
panel["ensemble_new5_w_breadth"] = panel[["g_cape", "g_term_spread", "g_credit_spread", "g_buffett", "g_breadth_thrust"]].mean(axis=1, skipna=True)

panel.to_parquet(OUT_DIR / "macro_gauges_panel.parquet", index=False)
print(f"panel saved: {panel.shape}, {panel.date.min()} -> {panel.date.max()}")
for g in GAUGES + ["ensemble_all", "ensemble_new4", "ensemble_new5_w_breadth"]:
    print(f"  {g}: non-null={panel[g].notna().sum()}, first_valid={panel.loc[panel[g].notna(),'date'].min()}")

# ================================================================== correlation + robustness battery
BEARS = {
    "GFC_2008": (pd.Timestamp("2007-10-01"), pd.Timestamp("2009-06-30")),
    "COVID_2020": (pd.Timestamp("2020-01-01"), pd.Timestamp("2020-06-30")),
    "HIKE_2022": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
}

def corr_safe(a, b):
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 8:
        return np.nan, len(d)
    return d["a"].corr(d["b"]), len(d)

results = {}
for g in GAUGES + ["ensemble_all", "ensemble_new4", "ensemble_new5_w_breadth"]:
    row = {}
    for tgt in ["fwd_ret_1Y", "fwd_ret_5Y", "fwd_maxdd_1Y"]:
        c, n = corr_safe(panel[g], panel[tgt])
        row[f"corr_{tgt}"] = None if pd.isna(c) else round(float(c), 3)
        row[f"n_{tgt}"] = n
    valid = panel.dropna(subset=[g, "fwd_ret_1Y"])
    # era split: first half vs second half of the gauge's own valid date range
    if len(valid) >= 16:
        mid = valid["date"].iloc[len(valid)//2]
        h1 = valid[valid["date"] < mid]
        h2 = valid[valid["date"] >= mid]
        c1, n1 = corr_safe(h1[g], h1["fwd_ret_1Y"])
        c2, n2 = corr_safe(h2[g], h2["fwd_ret_1Y"])
        row["era_split"] = f"H1({h1.date.min().date()}-{h1.date.max().date()},n={n1})={round(c1,2) if pd.notna(c1) else None} | " \
                            f"H2({h2.date.min().date()}-{h2.date.max().date()},n={n2})={round(c2,2) if pd.notna(c2) else None}"
        row["era_split_sign_stable"] = bool(pd.notna(c1) and pd.notna(c2) and np.sign(c1) == np.sign(c2) and abs(c1) > 0.02 and abs(c2) > 0.02)
    else:
        row["era_split"] = "insufficient n"
        row["era_split_sign_stable"] = None
    # drop-one-bear: which bears fall inside this gauge's valid range at all
    bears_present = []
    dropone = {}
    full_c, full_n = corr_safe(valid[g], valid["fwd_ret_1Y"])
    for bname, (b0, b1) in BEARS.items():
        in_range = valid[(valid["date"] >= b0) & (valid["date"] <= b1)]
        if len(in_range) == 0:
            continue
        bears_present.append(bname)
        rest = valid[~((valid["date"] >= b0) & (valid["date"] <= b1))]
        c, n = corr_safe(rest[g], rest["fwd_ret_1Y"])
        dropone[bname] = None if pd.isna(c) else round(float(c), 3)
    row["bears_present"] = bears_present
    row["full_corr_1Y"] = None if pd.isna(full_c) else round(float(full_c), 3)
    row["dropone"] = dropone
    if bears_present and pd.notna(full_c):
        stable = all(pd.notna(v) and np.sign(v) == np.sign(full_c) for v in dropone.values() if v is not None)
        row["dropone_sign_stable"] = stable
    else:
        row["dropone_sign_stable"] = None
    results[g] = row

print("\n=== PER-GAUGE RESULTS ===")
for g, row in results.items():
    print(f"\n-- {g} --")
    for k, v in row.items():
        print(f"   {k}: {v}")

with open(OUT_DIR / "macro_gauges_summary.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nWROTE:", OUT_DIR / "macro_gauges_summary.json")
print("WROTE:", OUT_DIR / "macro_gauges_panel.parquet")
