"""
SPREAD/SLIPPAGE CALIBRATION (T5 fill-realism dependency) — MEASUREMENT, no kill threshold.
Pre-registered spec: Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260710_principal_intraday_spec_triage.md
(Data ask #5: "calibrate penalties vs angel_capture_2026 live captures before trusting 0DTE fills")

Part A: NIFTY weekly index options (HF 1-min trade bars, 2021-06 -> 2026-05)
  - effective-spread proxies by DTE bucket x moneyness x time-of-day:
      * volume-weighted within-minute high-low range (upper bound: spread + intraminute drift)
      * Roll (1984) estimator on 1-min traded closes per contract-day (serial-cov based, lower/central)
      * median |1-min close change| (tick-bounce scale)
Part B: Angel live capture, 87 single-stock option front-month files (Jul-2026)
  - same proxies as % of premium; ATM located via put-call-parity argmin|CE-PE| per minute
Compare vs COST_STANDARDS (D-021 APPROVED): index ATM = max(1 tick, 0.25% premium) one-way;
single-stock near-ATM = 0.5-1.5% premium; and the spec's 0.5 / 1 / 2 index-point slippage grid.

Guards: drop_preopen (pre-open auction bug); timestamps in both sources are already IST
(+05:30 tz-aware) -> tz_localize(None) preserves wall time; trade bars only (volume>0);
no fills assumed anywhere - this is pure measurement.
"""
import os, sys, glob, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(BASE, "Shreyas_Ionic_AMC", "04_RND_LAB"))
from lib import guards  # noqa: E402

NIFTY_OPT_DIR = os.path.join(BASE, "intraday_options_strategy", "datasets", "raw",
                             "hf_index_options_1m", "options", "NIFTY")
SPOT_FILE = os.path.join(BASE, "intraday_options_strategy", "datasets", "processed", "nifty_1min.parquet")
ANGEL_MIN = os.path.join(BASE, "intraday_options_strategy", "datasets", "angel_capture_2026", "minute")
OUT = os.path.join(BASE, "Shreyas_Ionic_AMC", "04_RND_LAB", "results",
                   "CHEAPTEST_SPEC_20260710", "spread-calibration")
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(20260710)

def tod_bucket(minutes_of_day):
    # minutes since midnight IST
    b = np.full(len(minutes_of_day), "3_midday(11:30-13:30)", dtype=object)
    m = minutes_of_day
    b[(m >= 9*60+15) & (m < 9*60+30)] = "1_open(09:15-09:30)"
    b[(m >= 9*60+30) & (m < 11*60+30)] = "2_morning(09:30-11:30)"
    b[(m >= 13*60+30) & (m < 15*60)] = "4_afternoon(13:30-15:00)"
    b[(m >= 15*60)] = "5_close(15:00-15:30)"
    return b

def money_bucket(otm_steps):
    # otm_steps: signed distance from ATM in strike steps, +ve = OTM, -ve = ITM
    b = np.full(len(otm_steps), "6_deepOTM(6+)", dtype=object)
    s = otm_steps
    b[s <= -3] = "0_deepITM(3+)"
    b[(s >= -2) & (s <= -1)] = "1_ITM(1-2)"
    b[s == 0] = "2_ATM"
    b[(s >= 1) & (s <= 2)] = "3_OTM(1-2)"
    b[(s >= 3) & (s <= 5)] = "4_OTM(3-5)"
    return b

def roll_estimator(closes):
    """Roll (1984): eff. spread = 2*sqrt(-cov(dP_t, dP_{t-1})). NaN if cov>=0 or too few obs."""
    d = np.diff(closes)
    if len(d) < 20:
        return np.nan
    c = np.cov(d[1:], d[:-1])[0, 1]
    return 2 * np.sqrt(-c) if c < 0 else np.nan

# ---------------------------------------------------------------- Part A
print("Part A: NIFTY weekly options ...", flush=True)
spot = pd.read_parquet(SPOT_FILE)  # index = naive IST datetime, cols open/high/low/close
spot_close = spot["close"]  # Series indexed by minute
spot_max_ts = spot.index.max()

files = sorted(glob.glob(os.path.join(NIFTY_OPT_DIR, "*.parquet")))
# sample: every 3rd expiry pre-2024, every 2nd in 2024, ALL 2025-2026 (recent era matters most)
sel = []
pre24 = [f for f in files if os.path.basename(f) < "2024-01"]
in24 = [f for f in files if "2024-01" <= os.path.basename(f) < "2025-01"]
post24 = [f for f in files if os.path.basename(f) >= "2025-01"]
sel = pre24[::3] + in24[::2] + post24
print(f"  expiry files sampled: {len(sel)} of {len(files)}", flush=True)

agg_parts, samples, roll_recs = [], [], []
for i, f in enumerate(sel):
    exp = os.path.basename(f).replace(".parquet", "")
    try:
        df = pd.read_parquet(f, columns=["timestamp", "open", "high", "low", "close",
                                         "volume", "trading_day", "strike", "option_type"])
    except Exception as e:
        print(f"  SKIP {exp}: {e}", flush=True)
        continue
    if df.empty:
        continue
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)  # already IST wall time
    df = guards.drop_preopen(df, "timestamp")           # >= 09:15 only
    df = df[df["timestamp"].dt.time <= pd.Timestamp("15:29").time()]
    df = df[df["volume"] > 0]                            # traded bars only
    if df.empty:
        continue
    df = df[df["timestamp"] <= spot_max_ts]
    s = df["timestamp"].map(spot_close)
    df = df[s.notna()].copy()
    if df.empty:
        continue
    df["spot"] = s[s.notna()].values
    atm = (df["spot"] / 50).round() * 50
    steps = ((df["strike"] - atm) / 50).round().astype(int)
    df["otm_steps"] = np.where(df["option_type"] == "CE", steps, -steps)
    df = df[df["otm_steps"].abs() <= 8]
    if df.empty:
        continue
    dte = (pd.to_datetime(exp) - pd.to_datetime(df["trading_day"])).dt.days
    df["dte_b"] = np.select([dte == 0, dte <= 2], ["0DTE", "1-2DTE"], default="3+DTE")
    df["money_b"] = money_bucket(df["otm_steps"].values)
    mod = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df["tod_b"] = tod_bucket(mod.values)
    df["hl"] = df["high"] - df["low"]
    mid = (df["high"] + df["low"]) / 2
    df["hl_pct"] = np.where(mid > 0, df["hl"] / mid, np.nan)
    df["era"] = "2021-22" if exp < "2023" else ("2023-24" if exp < "2025" else "2025-26")

    g = df.groupby(["era", "dte_b", "money_b", "tod_b"], observed=True).agg(
        n_bars=("hl", "size"), vol=("volume", "sum"),
        hl_vw_num=("hl", lambda x: float((x * df.loc[x.index, "volume"]).sum())),
        hlpct_vw_num=("hl_pct", lambda x: float((x * df.loc[x.index, "volume"]).sum())),
        prem_sum=("close", "sum"),
    ).reset_index()
    agg_parts.append(g)

    # sample pool for medians (up to 3000 bars/file)
    k = min(3000, len(df))
    samples.append(df.sample(n=k, random_state=i)[
        ["era", "dte_b", "money_b", "tod_b", "hl", "hl_pct", "close", "volume"]])

    # Roll estimator: 0DTE and 1-2DTE, near-money contracts, per contract-day
    near = df[(df["dte_b"].isin(["0DTE", "1-2DTE"])) & (df["otm_steps"].between(-1, 2))]
    for (td, k2, ot, db, mb), sub in near.groupby(
            ["trading_day", "strike", "option_type", "dte_b", "money_b"], observed=True):
        sub = sub.sort_values("timestamp")
        r = roll_estimator(sub["close"].values)
        med_abs_d = np.median(np.abs(np.diff(sub["close"].values))) if len(sub) > 20 else np.nan
        if not np.isnan(r) or not np.isnan(med_abs_d):
            roll_recs.append({"era": sub["era"].iloc[0], "dte_b": db, "money_b": mb,
                              "expiry": exp, "trading_day": td, "strike": k2, "otype": ot,
                              "roll_spread": r, "med_abs_dclose": med_abs_d,
                              "med_premium": float(sub["close"].median()), "n_min": len(sub)})
    if (i + 1) % 25 == 0:
        print(f"  ... {i+1}/{len(sel)} files", flush=True)

agg = pd.concat(agg_parts, ignore_index=True)
agg = agg.groupby(["era", "dte_b", "money_b", "tod_b"], observed=True).sum(numeric_only=True).reset_index()
agg["hl_vw"] = agg["hl_vw_num"] / agg["vol"]
agg["hlpct_vw"] = agg["hlpct_vw_num"] / agg["vol"]
agg["prem_mean"] = agg["prem_sum"] / agg["n_bars"]
samp = pd.concat(samples, ignore_index=True)
med = samp.groupby(["era", "dte_b", "money_b", "tod_b"], observed=True).agg(
    hl_med=("hl", "median"), hl_p75=("hl", lambda x: x.quantile(0.75)),
    hlpct_med=("hl_pct", "median"), prem_med=("close", "median")).reset_index()
nifty_tab = agg.merge(med, on=["era", "dte_b", "money_b", "tod_b"], how="left")
nifty_tab = nifty_tab[["era", "dte_b", "money_b", "tod_b", "n_bars", "vol", "prem_med",
                       "hl_vw", "hl_med", "hl_p75", "hlpct_vw", "hlpct_med"]]
nifty_tab.to_csv(os.path.join(OUT, "nifty_spread_by_era_dte_money_tod.csv"), index=False)

roll_df = pd.DataFrame(roll_recs)
roll_df.to_csv(os.path.join(OUT, "nifty_roll_contract_day.csv"), index=False)
roll_sum = roll_df.groupby(["era", "dte_b", "money_b"], observed=True).agg(
    n_contract_days=("roll_spread", "size"),
    roll_med=("roll_spread", "median"), roll_p75=("roll_spread", lambda x: x.quantile(0.75)),
    roll_valid_frac=("roll_spread", lambda x: x.notna().mean()),
    med_abs_dclose=("med_abs_dclose", "median"),
    prem_med=("med_premium", "median")).reset_index()
roll_sum.to_csv(os.path.join(OUT, "nifty_roll_summary.csv"), index=False)
print("Part A done.", flush=True)
print(roll_sum.to_string(index=False), flush=True)

# ---------------------------------------------------------------- Part B
print("\nPart B: Angel live stock-option captures ...", flush=True)
recs, brecs = [], []
syms = sorted(os.listdir(ANGEL_MIN))
for sym in syms:
    fs = sorted(glob.glob(os.path.join(ANGEL_MIN, sym, "*.parquet")))
    if not fs:
        continue
    df = pd.read_parquet(fs[0])  # front expiry
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = guards.drop_preopen(df, "timestamp")
    df = df[df["timestamp"].dt.time <= pd.Timestamp("15:29").time()]
    if df.empty:
        continue
    # strike step
    ks = np.sort(df["strike"].unique())
    step = float(np.median(np.diff(ks))) if len(ks) > 1 else np.nan
    if not step or np.isnan(step) or step <= 0:
        continue
    # ATM per minute via put-call parity (argmin |CE-PE| on ffilled closes)
    pv = df.pivot_table(index="timestamp", columns=["option_type", "strike"],
                        values="close", aggfunc="last").ffill()
    if "CE" not in pv.columns.get_level_values(0) or "PE" not in pv.columns.get_level_values(0):
        continue
    ce, pe = pv["CE"], pv["PE"]
    common = ce.columns.intersection(pe.columns)
    if len(common) < 3:
        continue
    diff = (ce[common] - pe[common]).abs()
    diff = diff.dropna(how="all")  # minutes before first trade in any strike
    if diff.empty:
        continue
    atm_strike = diff.idxmin(axis=1)  # Series: timestamp -> strike
    df["atm"] = df["timestamp"].map(atm_strike)
    df = df[df["atm"].notna() & (df["volume"] > 0)].copy()
    if df.empty:
        continue
    steps = ((df["strike"] - df["atm"]) / step).round().astype(int)
    df["otm_steps"] = np.where(df["option_type"] == "CE", steps, -steps)
    df = df[df["otm_steps"].abs() <= 6]
    df["money_b"] = money_bucket(df["otm_steps"].values)
    mod = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df["tod_b"] = tod_bucket(mod.values)
    df["hl_pct"] = np.where(df["close"] > 0, (df["high"] - df["low"]) / df["close"], np.nan)
    df = df[df["close"] >= 0.5]  # drop sub-tick premiums (pct meaningless)
    for (mb, tb), sub in df.groupby(["money_b", "tod_b"], observed=True):
        brecs.append({"symbol": sym, "money_b": mb, "tod_b": tb, "n_bars": len(sub),
                      "vol": int(sub["volume"].sum()),
                      "hlpct_vw": float((sub["hl_pct"] * sub["volume"]).sum() / sub["volume"].sum()),
                      "hlpct_med": float(sub["hl_pct"].median()),
                      "prem_med": float(sub["close"].median())})
    # Roll per contract-day, near-money
    near = df[df["otm_steps"].between(-1, 2)]
    for (td, k2, ot), sub in near.groupby(["trading_day", "strike", "option_type"], observed=True):
        sub = sub.sort_values("timestamp")
        r = roll_estimator(sub["close"].values)
        if not np.isnan(r):
            p = float(sub["close"].median())
            recs.append({"symbol": sym, "roll_spread": r, "roll_pct": r / p if p > 0 else np.nan,
                         "prem_med": p, "n_min": len(sub)})

stock_tab = pd.DataFrame(brecs)
stock_agg = stock_tab.groupby(["money_b", "tod_b"], observed=True).apply(
    lambda g: pd.Series({
        "n_bars": g["n_bars"].sum(), "vol": g["vol"].sum(),
        "hlpct_vw": (g["hlpct_vw"] * g["vol"]).sum() / g["vol"].sum(),
        "hlpct_med": g["hlpct_med"].median(), "prem_med": g["prem_med"].median(),
        "n_symbols": g["symbol"].nunique()})).reset_index()
stock_agg.to_csv(os.path.join(OUT, "stock_angel_spread_by_money_tod.csv"), index=False)
stock_roll = pd.DataFrame(recs)
stock_roll.to_csv(os.path.join(OUT, "stock_angel_roll_contract_day.csv"), index=False)
print(stock_agg.to_string(index=False), flush=True)
if len(stock_roll):
    print("\nstock Roll pct-of-premium: median %.4f p75 %.4f (n=%d contract-days)" % (
        stock_roll["roll_pct"].median(), stock_roll["roll_pct"].quantile(0.75), len(stock_roll)), flush=True)

# ---------------------------------------------------------------- Calibration vs standards
print("\n--- CALIBRATION vs COST_STANDARDS + 0.5/1/2-pt grid (NIFTY ATM/OTM1-2, 2025-26) ---", flush=True)
cal = roll_sum[(roll_sum["era"] == "2025-26")]
print(cal.to_string(index=False), flush=True)
hl_recent = nifty_tab[(nifty_tab["era"] == "2025-26") & (nifty_tab["money_b"].isin(["2_ATM", "3_OTM(1-2)"]))]
hl_recent.to_csv(os.path.join(OUT, "nifty_recent_atm_hl_table.csv"), index=False)
print(hl_recent.to_string(index=False), flush=True)
print("\nDONE. Outputs in", OUT, flush=True)
