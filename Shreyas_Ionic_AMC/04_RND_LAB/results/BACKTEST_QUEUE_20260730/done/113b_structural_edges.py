"""113b_structural_edges.py -- Arjun Rao (Quant), 2026-07-30. RUN 3 (fixed weekly-cadence logic bug).
Structural/calendar/positioning edges in NIFTY options. Self-contained, no args.
Implements PREREG.md exactly:
  Shreyas_Ionic_AMC/04_RND_LAB/results/STRUCTURAL_EDGES_20260730/PREREG.md
Writes all outputs to that same results dir. Queued because it loops the full 16yr
option chain (fo_bhavcopy_hist) and the 1.05M-bar 1-min NIFTY spot file.

RUN 1 FAILED (rc=1, 7s): fo_idx_2012.parquet has 1,467 rows (0.4%) with a 2-digit-year
EXPIRY_DT/TIMESTAMP string ("31-May-12" vs the normal "31-May-2012") -- isolated data-quality
landmine in that one file. Fixed with a length-dispatch parser (verified against an independent
format='mixed',dayfirst=True re-parse across ALL 16 years/7,670,250 rows: 0 NaT either way, 0
disagreements between the two methods -- both are correct and equivalent here).

RUN 2 SUCCEEDED (rc=0, 43s) but effect1 (expiry weekday history) was WRONG: the naive
"gap between consecutive unique EXPIRY_DT <= 8 days" test for weekly cadence let a single
ISOLATED holiday-shift pair (26-Feb-2014 Wed / 27-Feb-2014 Thu -- both genuine MONTHLY expiries,
one day apart because that month's expiry got moved by a holiday) get flagged as "weekly", and
the segment-builder then let that 2-point anchor silently span a fake "weekly regime" all the
way from 2014 to 2025 with no density check in between. Verified directly against the raw expiry
list (2013-2015) before trusting anything. FIX: require a connected run of >=15 consecutive
close-gap dates before calling a stretch genuine weekly cadence (real weekly cadence has ~300+
such dates post-2019; a holiday-shift blip has exactly 2).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

t_script_start = time.time()

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
FO_DIR = ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "fo_bhavcopy_hist"
SPOT_PATH = ROOT / "intraday_options_strategy" / "datasets" / "processed" / "nifty_1min.parquet"
CAL_PATH = ROOT / "intraday_options_strategy" / "datasets" / "processed" / "trading_calendar.csv"
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "STRUCTURAL_EDGES_20260730"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import guards as G  # noqa: E402

SEED = 42
BUILD_END = pd.Timestamp("2024-12-31")
HOLDOUT_START = pd.Timestamp("2025-01-01")
OCT2024 = pd.Timestamp("2024-10-01")
MIN_WEEKLY_RUN = 15  # min consecutive close-gap dates to call a stretch genuine weekly cadence

LOG = []


def log(msg: str) -> None:
    line = f"[{time.time()-t_script_start:7.1f}s] {msg}"
    print(line, flush=True)
    LOG.append(line)


def parse_dmy_mixed(s: pd.Series) -> pd.Series:
    """DD-Mon-YYYY is standard; fo_idx_2012.parquet has a DD-Mon-YY (2-digit year) minority.
    Dispatch by string length rather than trusting a single format string. Verified against an
    independent format='mixed',dayfirst=True reparse across all 16 years: identical, 0 NaT."""
    s = s.astype(str)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    len4 = s.str.len() == 11
    len2 = s.str.len() == 9
    if len4.any():
        out.loc[len4] = pd.to_datetime(s[len4], format="%d-%b-%Y")
    if len2.any():
        out.loc[len2] = pd.to_datetime(s[len2], format="%d-%b-%y")
    other = ~(len4 | len2)
    n_other = int(other.sum())
    if n_other:
        out.loc[other] = pd.to_datetime(s[other], format="mixed", dayfirst=True, errors="coerce")
    return out


def welch_t(a: np.ndarray, b: np.ndarray):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan, np.nan, np.nan, na, nb
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    t = (a.mean() - b.mean()) / se if se > 0 else np.nan
    return t, a.mean(), b.mean(), na, nb


def placebo_relabel_null(values: np.ndarray, n_true: int, draws: int = 500, seed: int = SEED):
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = np.arange(n)
    ts = np.empty(draws)
    for i in range(draws):
        sel = rng.choice(idx, size=n_true, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[sel] = True
        t, *_ = welch_t(values[mask], values[~mask])
        ts[i] = t
    return ts


def ols_beta_t(x: np.ndarray, y: np.ndarray):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 10:
        return np.nan, np.nan, n
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if sxx <= 0:
        return np.nan, np.nan, n
    sxy = ((x - xm) * (y - ym)).sum()
    beta = sxy / sxx
    resid = y - (ym + beta * (x - xm))
    dof = n - 2
    if dof <= 0:
        return beta, np.nan, n
    s2 = (resid ** 2).sum() / dof
    se_beta = np.sqrt(s2 / sxx) if s2 > 0 and sxx > 0 else np.nan
    t = beta / se_beta if se_beta and se_beta > 0 else np.nan
    return beta, t, n


def ks_stat(a: np.ndarray, b: np.ndarray):
    """Two-sample KS D-stat + asymptotic-approx p-value (no scipy dependency)."""
    a = np.sort(np.asarray(a, dtype=float))
    b = np.sort(np.asarray(b, dtype=float))
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return np.nan, np.nan
    allv = np.concatenate([a, b])
    allv.sort()
    cdf_a = np.searchsorted(a, allv, side="right") / na
    cdf_b = np.searchsorted(b, allv, side="right") / nb
    d = np.max(np.abs(cdf_a - cdf_b))
    n_eff = na * nb / (na + nb)
    p_approx = 2 * np.exp(-2 * n_eff * d ** 2)
    p_approx = min(1.0, p_approx)
    return d, p_approx


effects_rows = []  # effect | measurement | n | t | vs_placebo | verdict

# =====================================================================================
# LOAD OPTION CHAIN (column subset, per-year loop, NIFTY only) — the full-chain scan
# =====================================================================================
log("Loading fo_idx_*.parquet 2011-2026, NIFTY subset, column subset ...")
COLS = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP",
        "CONTRACTS", "OPEN_INT", "CHG_IN_OI", "TIMESTAMP"]
frames = []
year_rowcounts = {}
for yr in range(2011, 2027):
    fp = FO_DIR / f"fo_idx_{yr}.parquet"
    if not fp.exists():
        continue
    d = pd.read_parquet(fp, columns=COLS)
    d = d[d["SYMBOL"] == "NIFTY"].copy()
    year_rowcounts[yr] = len(d)
    frames.append(d)
chain = pd.concat(frames, ignore_index=True)
del frames
chain["EXPIRY_DT"] = parse_dmy_mixed(chain["EXPIRY_DT"])
chain["TIMESTAMP"] = parse_dmy_mixed(chain["TIMESTAMP"])
n_bad_ts = int(chain["TIMESTAMP"].isna().sum())
n_bad_ex = int(chain["EXPIRY_DT"].isna().sum())
assert n_bad_ts == 0, f"L-date: {n_bad_ts} unparseable TIMESTAMP strings -- do not silently proceed"
assert n_bad_ex == 0, f"L-date: {n_bad_ex} unparseable EXPIRY_DT strings -- do not silently proceed"
log(f"chain loaded: {len(chain):,} NIFTY rows, 0 NaT in EXPIRY_DT/TIMESTAMP (asserted). "
    f"per-year counts: {year_rowcounts}")

opt = chain[chain["INSTRUMENT"] == "OPTIDX"].copy()
log(f"OPTIDX subset: {len(opt):,} rows, {opt['EXPIRY_DT'].nunique()} distinct expiries, "
    f"date range {chain['TIMESTAMP'].min().date()}..{chain['TIMESTAMP'].max().date()}")

# =====================================================================================
# EFFECT 1 -- expiry weekday history + switch dates (descriptive)
# =====================================================================================
log("Effect 1: expiry weekday history ...")
all_expiries = pd.Series(sorted(opt["EXPIRY_DT"].unique()))
gaps = all_expiries.diff().dt.days
is_close = (gaps <= 8).fillna(False).to_numpy()
N = len(all_expiries)
comp = np.zeros(N, dtype=int)
for i in range(1, N):
    comp[i] = comp[i - 1] if is_close[i] else comp[i - 1] + 1
comp_sizes = np.bincount(comp)
genuine_weekly_mask = comp_sizes[comp] >= MIN_WEEKLY_RUN
n_rejected_blips = int(((comp_sizes >= 2) & (comp_sizes < MIN_WEEKLY_RUN)).sum())
log(f"Weekly-cadence connected components: {len(comp_sizes)} total, "
    f"{(comp_sizes >= MIN_WEEKLY_RUN).sum()} genuine (size>={MIN_WEEKLY_RUN}), "
    f"{n_rejected_blips} rejected as holiday-shift blips (2<=size<{MIN_WEEKLY_RUN})")
weeklies = all_expiries[genuine_weekly_mask].reset_index(drop=True)
WD_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
wd = weeklies.dt.weekday

def rolling_mode(s: pd.Series, w: int = 9) -> pd.Series:
    return s.rolling(w, min_periods=1, center=True).apply(lambda x: pd.Series(x).mode().iloc[0], raw=False)

mode_wd = rolling_mode(wd, 9) if len(wd) > 0 else pd.Series(dtype=float)

segments = []
if len(mode_wd) > 0:
    cur_wd = mode_wd.iloc[0]
    start_idx = 0
    i = 1
    while i < len(mode_wd):
        if mode_wd.iloc[i] != cur_wd:
            lookahead = mode_wd.iloc[i:i + 9]
            if len(lookahead) > 0 and (lookahead == mode_wd.iloc[i]).mean() >= 0.8:
                segments.append((weeklies.iloc[start_idx], weeklies.iloc[i - 1], int(cur_wd)))
                start_idx = i
                cur_wd = mode_wd.iloc[i]
        i += 1
    segments.append((weeklies.iloc[start_idx], weeklies.iloc[len(mode_wd) - 1], int(cur_wd)))

seg_df = pd.DataFrame(segments, columns=["regime_start", "regime_end", "weekday_num"])
if len(seg_df) > 0:
    seg_df["weekday_name"] = seg_df["weekday_num"].map(lambda x: WD_NAMES[x])
seg_df.to_csv(OUT / "effect1_expiry_weekday_regimes.csv", index=False)
log(f"Effect 1: {len(seg_df)} weekly-expiry weekday regimes found:\n{seg_df.to_string()}")

# Sanity check requested explicitly: weekday distribution WITHIN each regime should be
# concentrated (one dominant weekday), not smeared across all 5 -- else suspect the logic/parse.
for _, row in seg_df.iterrows():
    sub = wd[(weeklies >= row["regime_start"]) & (weeklies <= row["regime_end"])]
    vc = sub.value_counts(normalize=True).sort_values(ascending=False)
    top_share = vc.iloc[0] if len(vc) else np.nan
    concentrated = "CONCENTRATED" if top_share >= 0.8 else "SMEARED -- suspect logic/parse"
    log(f"  regime {row['regime_start'].date()}..{row['regime_end'].date()} "
        f"({row['weekday_name']}): top-weekday share={top_share:.2%} n={len(sub)} -> {concentrated}")

# Monthly expiry weekday (background context; monthly = last listed expiry per (year,month))
opt_ym = opt.assign(ym=opt["EXPIRY_DT"].dt.to_period("M"))
monthly_expiries = opt_ym.groupby("ym")["EXPIRY_DT"].max().sort_values().reset_index(drop=True)
monthly_wd = monthly_expiries.dt.weekday
monthly_wd_by_year = pd.DataFrame({"expiry": monthly_expiries, "weekday": monthly_wd.map(lambda x: WD_NAMES[x])})
monthly_wd_by_year["year"] = monthly_wd_by_year["expiry"].dt.year
monthly_summary = monthly_wd_by_year.groupby("year")["weekday"].agg(lambda s: s.mode().iloc[0])
monthly_summary.to_csv(OUT / "effect1_monthly_expiry_weekday_by_year.csv")
log(f"Monthly expiry modal weekday by year:\n{monthly_summary.to_string()}")

weekly_set = set(pd.to_datetime(weeklies).dt.normalize())
monthly_set = set(pd.to_datetime(monthly_expiries).dt.normalize())
expiry_set = set(pd.to_datetime(all_expiries).dt.normalize())

# =====================================================================================
# LOAD SPOT (cash NIFTY, full 1-min file -- also used later for Effect 9)
# =====================================================================================
log("Loading nifty_1min.parquet (full file, 1.05M bars) ...")
spot = pd.read_parquet(SPOT_PATH)
spot = spot.reset_index()
ts_col = "dt" if "dt" in spot.columns else spot.columns[0]
spot = spot.rename(columns={ts_col: "ts"})
n0_spot = len(spot)
spot = G.drop_preopen(spot, ts_col="ts")  # L2 guard: strip any pre-open-auction prints if present
if len(spot) != n0_spot:
    log(f"L2 guard dropped {n0_spot - len(spot)} pre-09:15 bars from nifty_1min.parquet")
spot["date"] = pd.to_datetime(spot["ts"].dt.date)
log(f"spot loaded: {len(spot):,} bars, {spot['date'].min().date()}..{spot['date'].max().date()}")

daily = spot.groupby("date").agg(close=("close", "last"), open=("open", "first")).reset_index()
daily = daily.sort_values("date").reset_index(drop=True)
daily["ret"] = daily["close"].pct_change()
daily["is_expiry"] = daily["date"].isin(expiry_set)
daily["is_weekly_expiry"] = daily["date"].isin(weekly_set)
daily["is_monthly_expiry"] = daily["date"].isin(monthly_set)
daily["absret"] = daily["ret"].abs()

# =====================================================================================
# EFFECT 2 -- expiry-day realized |return| vs non-expiry days
# =====================================================================================
log("Effect 2: expiry-day realized vol vs non-expiry ...")
valid = daily.dropna(subset=["ret"]).reset_index(drop=True)
absret = valid["absret"].values
is_exp = valid["is_expiry"].values
t_real, m_exp, m_non, n_exp, n_non = welch_t(absret[is_exp], absret[~is_exp])
null = placebo_relabel_null(absret, n_true=int(is_exp.sum()), draws=500, seed=SEED)
bar95 = np.percentile(np.abs(null), 95)
verdict2 = "REAL (clears placebo)" if abs(t_real) > bar95 else "NO CONTENT (placebo-indistinguishable)"
log(f"Effect2 expiry-vs-non: t={t_real:.3f} mean|ret| exp={m_exp:.5f} non={m_non:.5f} "
    f"n_exp={n_exp} n_non={n_non} placebo95={bar95:.3f} -> {verdict2}")
effects_rows.append(["expiry_day_vol_vs_nonexpiry", "Welch t, mean|ret|, exp vs non-exp days",
                     f"{n_exp}/{n_non}", round(t_real, 3), round(bar95, 3), verdict2])

idx_map = {d: i for i, d in enumerate(daily["date"])}
offsets = {-1: [], 0: [], 1: []}
for e in sorted(weekly_set):
    if e in idx_map:
        i = idx_map[e]
        for off in (-1, 0, 1):
            j = i + off
            if 0 <= j < len(daily):
                r = daily["absret"].iloc[j]
                if not np.isnan(r):
                    offsets[off].append(r)
tminus1_of_plus1 = {k: (np.mean(v) if v else np.nan, len(v)) for k, v in offsets.items()}
log(f"Effect2 T-1/T/T+1 mean|ret| around WEEKLY expiry: {tminus1_of_plus1}")
pd.DataFrame({"offset": list(tminus1_of_plus1.keys()),
              "mean_absret": [v[0] for v in tminus1_of_plus1.values()],
              "n": [v[1] for v in tminus1_of_plus1.values()]}
             ).to_csv(OUT / "effect2_t-1_t_t+1_weekly.csv", index=False)

# =====================================================================================
# EFFECT 3 -- weekly-only vs monthly expiry-day vol
# =====================================================================================
log("Effect 3: weekly-only vs monthly-expiry vol ...")
weekly_only_mask = valid["is_weekly_expiry"].values & ~valid["is_monthly_expiry"].values
monthly_mask = valid["is_monthly_expiry"].values
t3, m_wonly, m_month, n_wonly, n_month = welch_t(absret[weekly_only_mask], absret[monthly_mask])
log(f"Effect3: t={t3:.3f} mean|ret| weekly-only={m_wonly:.5f} (n={n_wonly}) "
    f"monthly={m_month:.5f} (n={n_month})")
effects_rows.append(["weekly_only_vs_monthly_expiry_vol", "Welch t, mean|ret|",
                     f"{n_wonly}/{n_month}", round(t3, 3), "n/a (descriptive)",
                     "monthly higher" if m_month > m_wonly else "weekly-only higher"])

# =====================================================================================
# EFFECT 4 -- PCR (OI & volume) as forward return/vol predictor
# =====================================================================================
log("Effect 4: building daily PCR (OI + volume) from full chain ...")
oi_by_type = opt.groupby(["TIMESTAMP", "OPTION_TYP"])["OPEN_INT"].sum().unstack("OPTION_TYP")
vol_by_type = opt.groupby(["TIMESTAMP", "OPTION_TYP"])["CONTRACTS"].sum().unstack("OPTION_TYP")
pcr = pd.DataFrame(index=oi_by_type.index)
pcr["PCR_OI"] = oi_by_type.get("PE") / oi_by_type.get("CE")
pcr["PCR_VOL"] = vol_by_type.get("PE") / vol_by_type.get("CE").replace(0, np.nan)
pcr = pcr.reset_index().rename(columns={"TIMESTAMP": "date"}).sort_values("date").reset_index(drop=True)
assert pcr["date"].is_unique, "L4: PCR frame has duplicate dates -- would fan out on merge"

merged = daily.merge(pcr, on="date", how="inner").sort_values("date").reset_index(drop=True)
for col in ("PCR_OI", "PCR_VOL"):
    roll_mean = merged[col].rolling(252, min_periods=60).mean()
    roll_std = merged[col].rolling(252, min_periods=60).std()
    merged[col + "_z"] = (merged[col] - roll_mean) / roll_std

ret_arr = merged["ret"].values
n_days = len(ret_arr)
HORIZONS = (1, 3, 5, 10)
fwd_ret = {h: np.full(n_days, np.nan) for h in HORIZONS}
fwd_vol = {h: np.full(n_days, np.nan) for h in HORIZONS}
close_arr = merged["close"].values
for h in HORIZONS:
    for i in range(n_days - h):
        fwd_ret[h][i] = close_arr[i + h] / close_arr[i] - 1.0
        window = ret_arr[i + 1:i + 1 + h]
        fwd_vol[h][i] = abs(window[0]) if h == 1 else np.std(window, ddof=0)
for h in HORIZONS:
    merged[f"fwd_ret_{h}"] = fwd_ret[h]
    merged[f"fwd_vol_{h}"] = fwd_vol[h]

build_mask = (merged["date"] <= BUILD_END).values
hold_mask = (merged["date"] >= HOLDOUT_START).values
log(f"Effect4 sample: build n={build_mask.sum()} holdout n={hold_mask.sum()}")

effect4_rows = []
rng4 = np.random.default_rng(SEED)
for sig_name, sig_col in (("PCR_OI", "PCR_OI_z"), ("PCR_VOL", "PCR_VOL_z")):
    x_build_full = merged.loc[build_mask, sig_col].values
    for dep_kind in ("ret", "vol"):
        for h in HORIZONS:
            y_build = merged.loc[build_mask, f"fwd_{dep_kind}_{h}"].values
            x_build = x_build_full.copy()
            beta_b, t_b, n_b = ols_beta_t(x_build, y_build)
            mask_ok = ~(np.isnan(x_build) | np.isnan(y_build))
            xv, yv = x_build[mask_ok], y_build[mask_ok]
            x_shuf = rng4.permutation(xv)
            _, t_pa, _ = ols_beta_t(x_shuf, yv)
            x_roll = np.roll(xv, 126)
            _, t_pb, _ = ols_beta_t(x_roll, yv)
            bar = max(abs(t_pa) if not np.isnan(t_pa) else 0, abs(t_pb) if not np.isnan(t_pb) else 0)
            cleared = (not np.isnan(t_b)) and (abs(t_b) > bar)
            x_hold = merged.loc[hold_mask, sig_col].values
            y_hold = merged.loc[hold_mask, f"fwd_{dep_kind}_{h}"].values
            beta_h, t_h, n_h = ols_beta_t(x_hold, y_hold)
            sign_match = (not np.isnan(beta_h)) and (not np.isnan(beta_b)) and (np.sign(beta_h) == np.sign(beta_b))
            if cleared and sign_match:
                verdict = "LEAD (clears placebo + holdout sign match)"
            elif cleared:
                verdict = "CLEARS PLACEBO but holdout sign flips -> not a lead"
            else:
                verdict = "NO CONTENT (placebo-indistinguishable)"
            effect4_rows.append({
                "signal": sig_name, "dep": dep_kind, "horizon": h,
                "n_build": int(n_b), "t_build": round(t_b, 3) if not np.isnan(t_b) else None,
                "beta_build": beta_b, "t_placebo_shuffle": round(t_pa, 3) if not np.isnan(t_pa) else None,
                "t_placebo_circshift": round(t_pb, 3) if not np.isnan(t_pb) else None,
                "placebo_bar": round(bar, 3),
                "n_holdout": int(n_h), "t_holdout": round(t_h, 3) if not np.isnan(t_h) else None,
                "beta_holdout": beta_h, "verdict": verdict,
            })
effect4_df = pd.DataFrame(effect4_rows)
effect4_df.to_csv(OUT / "effect4_pcr_predictive.csv", index=False)
log(f"Effect 4 (PCR predictive, {len(effect4_df)} sub-trials):\n{effect4_df.to_string()}")
for _, r in effect4_df.iterrows():
    effects_rows.append([f"PCR_{r['signal']}_fwd_{r['dep']}_h{r['horizon']}",
                         f"OLS beta t-stat, build n={r['n_build']}",
                         r["n_build"], r["t_build"], r["placebo_bar"], r["verdict"]])

# =====================================================================================
# EFFECT 5 -- max-pain gravitation
# =====================================================================================
log("Effect 5: max-pain gravitation ...")
cal = pd.read_csv(CAL_PATH)
cal_days = pd.to_datetime(cal["day"]).sort_values().reset_index(drop=True)
cal_index = {d: i for i, d in enumerate(cal_days)}
daily_close_map = dict(zip(daily["date"], daily["close"]))

grouped_chain = opt.groupby(["EXPIRY_DT", "TIMESTAMP"])

predicted_pull = []
actual_move = []
events_used = 0
events_skipped = 0
for e in sorted(weekly_set):
    if e not in cal_index:
        events_skipped += 1
        continue
    i_e = cal_index[e]
    i_t2 = i_e - 2
    if i_t2 < 0:
        events_skipped += 1
        continue
    t2 = cal_days.iloc[i_t2]
    try:
        snap = grouped_chain.get_group((e, t2))
    except KeyError:
        events_skipped += 1
        continue
    if e not in daily_close_map or t2 not in daily_close_map:
        events_skipped += 1
        continue
    ce = snap[snap["OPTION_TYP"] == "CE"].groupby("STRIKE_PR")["OPEN_INT"].sum()
    pe = snap[snap["OPTION_TYP"] == "PE"].groupby("STRIKE_PR")["OPEN_INT"].sum()
    strikes = np.array(sorted(set(ce.index) | set(pe.index)), dtype=float)
    if len(strikes) < 3:
        events_skipped += 1
        continue
    ce_arr = ce.reindex(strikes, fill_value=0).values
    pe_arr = pe.reindex(strikes, fill_value=0).values
    payout = np.array([
        np.sum(ce_arr * np.maximum(S - strikes, 0)) + np.sum(pe_arr * np.maximum(strikes - S, 0))
        for S in strikes
    ])
    mp = strikes[np.argmin(payout)]
    spot_t2 = daily_close_map[t2]
    spot_e = daily_close_map[e]
    predicted_pull.append(mp - spot_t2)
    actual_move.append(spot_e - spot_t2)
    events_used += 1

predicted_pull = np.array(predicted_pull)
actual_move = np.array(actual_move)
beta5, t5, n5 = ols_beta_t(predicted_pull, actual_move)
rng5 = np.random.default_rng(SEED)
perm_ts = np.empty(1000)
for i in range(1000):
    perm = rng5.permutation(actual_move)
    _, tp, _ = ols_beta_t(predicted_pull, perm)
    perm_ts[i] = tp
bar5 = np.nanpercentile(np.abs(perm_ts), 95)
verdict5 = "REAL gravitation (clears permutation null)" if (not np.isnan(t5) and abs(t5) > bar5) \
    else "NO CONTENT (placebo-indistinguishable)"
log(f"Effect5 max-pain: events_used={events_used} events_skipped={events_skipped} "
    f"beta={beta5:.4f} t={t5:.3f} permbar95={bar5:.3f} -> {verdict5}")
effects_rows.append(["max_pain_gravitation", "OLS beta(actual_move ~ predicted_pull), T-2 to expiry",
                     n5, round(t5, 3) if not np.isnan(t5) else None, round(bar5, 3), verdict5])
pd.DataFrame({"predicted_pull": predicted_pull, "actual_move": actual_move}).to_csv(
    OUT / "effect5_maxpain_events.csv", index=False)

# =====================================================================================
# EFFECT 6/8 -- OI concentration (Herfindahl) + Oct-2024 regime-break battery
# =====================================================================================
log("Effect 6/8: OI concentration + Oct-2024 regime break ...")
uniq_expiries_df = pd.DataFrame({"near_expiry": sorted(opt["EXPIRY_DT"].unique())})
uniq_days_df = pd.DataFrame({"TIMESTAMP": sorted(opt["TIMESTAMP"].unique())})
assert uniq_expiries_df["near_expiry"].is_unique and uniq_days_df["TIMESTAMP"].is_unique
near_map = pd.merge_asof(uniq_days_df, uniq_expiries_df, left_on="TIMESTAMP",
                          right_on="near_expiry", direction="forward")
assert near_map["TIMESTAMP"].is_unique, "L4: near_map has duplicate TIMESTAMP -- would fan out"
opt2 = opt.merge(near_map, on="TIMESTAMP", how="left")
opt_near = opt2[opt2["EXPIRY_DT"] == opt2["near_expiry"]]
g = opt_near.groupby(["TIMESTAMP", "STRIKE_PR"])["OPEN_INT"].sum().reset_index()
tot = g.groupby("TIMESTAMP")["OPEN_INT"].transform("sum")
g["share2"] = np.where(tot > 0, (g["OPEN_INT"] / tot) ** 2, np.nan)
herf = g.groupby("TIMESTAMP")["share2"].sum().reset_index(name="herfindahl")
herf = herf.rename(columns={"TIMESTAMP": "date"}).sort_values("date").reset_index(drop=True)
herf.to_csv(OUT / "effect6_oi_herfindahl_daily.csv", index=False)

pre_h = herf.loc[herf["date"] < OCT2024, "herfindahl"].values
post_h = herf.loc[herf["date"] >= OCT2024, "herfindahl"].values
t_herf, m_pre, m_post, n_pre, n_post = welch_t(pre_h, post_h)
d_herf, p_herf = ks_stat(pre_h, post_h)
log(f"Herfindahl pre/post Oct2024 (full 2011-2026 chain): mean_pre={m_pre:.4f}(n={n_pre}) "
    f"mean_post={m_post:.4f}(n={n_post}) t={t_herf:.3f} KS_D={d_herf:.4f} KS_p~{p_herf:.4g}")
log(f"  SANITY: n_pre+n_post={n_pre+n_post} vs total chain-native trading days "
    f"{opt['TIMESTAMP'].nunique()} (should be close/equal)")

pcr_pre = pcr.loc[pcr["date"] < OCT2024, "PCR_OI"].dropna().values
pcr_post = pcr.loc[pcr["date"] >= OCT2024, "PCR_OI"].dropna().values
t_pcr_lvl, m_pcr_pre, m_pcr_post, n_pcr_pre, n_pcr_post = welch_t(pcr_pre, pcr_post)
log(f"PCR_OI level pre/post Oct2024 (full chain 2011-2026): mean_pre={m_pcr_pre:.3f}(n={n_pcr_pre}) "
    f"mean_post={m_pcr_post:.3f}(n={n_pcr_post}) t={t_pcr_lvl:.3f}")

expvol_pre_mask = (valid["date"] < OCT2024) & valid["is_expiry"]
expvol_post_mask = (valid["date"] >= OCT2024) & valid["is_expiry"]
expvol_pre = valid.loc[expvol_pre_mask, "absret"].values
expvol_post = valid.loc[expvol_post_mask, "absret"].values
t_expvol_break, m_expvol_pre, m_expvol_post, n_ev_pre, n_ev_post = welch_t(expvol_pre, expvol_post)
log(f"Expiry-day |ret| pre/post Oct2024 (cash series, 2015-2026 coverage): "
    f"mean_pre={m_expvol_pre:.5f}(n={n_ev_pre}) mean_post={m_expvol_post:.5f}(n={n_ev_post}) "
    f"t={t_expvol_break:.3f}")

diag_pre_mask = (merged["date"] < OCT2024).values
diag_post_mask = (merged["date"] >= OCT2024).values
_, t_pcr_ret5_pre, _ = ols_beta_t(merged.loc[diag_pre_mask, "PCR_OI_z"].values, merged.loc[diag_pre_mask, "fwd_ret_5"].values)
_, t_pcr_ret5_post, _ = ols_beta_t(merged.loc[diag_post_mask, "PCR_OI_z"].values, merged.loc[diag_post_mask, "fwd_ret_5"].values)
_, t_pcr_vol5_pre, _ = ols_beta_t(merged.loc[diag_pre_mask, "PCR_OI_z"].values, merged.loc[diag_pre_mask, "fwd_vol_5"].values)
_, t_pcr_vol5_post, _ = ols_beta_t(merged.loc[diag_post_mask, "PCR_OI_z"].values, merged.loc[diag_post_mask, "fwd_vol_5"].values)
log(f"PCR_OI->fwd_ret_5 t: pre={t_pcr_ret5_pre:.3f} post={t_pcr_ret5_post:.3f} | "
    f"PCR_OI->fwd_vol_5 t: pre={t_pcr_vol5_pre:.3f} post={t_pcr_vol5_post:.3f}")

weekday_switch_near_oct2024 = seg_df[(seg_df["regime_start"] >= pd.Timestamp("2023-01-01")) &
                                      (seg_df["regime_start"] <= pd.Timestamp("2025-12-31"))] if len(seg_df) else seg_df
log(f"Weekday-switch segments starting in 2023-2025 window: \n{weekday_switch_near_oct2024.to_string()}")

n_breaks = sum([abs(t_herf) > 2, abs(t_pcr_lvl) > 2, abs(t_expvol_break) > 2, len(weekday_switch_near_oct2024) > 0])
if n_breaks >= 3:
    regime_verdict = "BROKEN -- multiple structural markers shift at/around Oct-2024"
elif n_breaks >= 1:
    regime_verdict = "PARTIAL -- some but not all structural markers shift"
else:
    regime_verdict = "NOT BROKEN -- no marker shows a clean level/behavior shift at Oct-2024"
log(f"REGIME BREAK VERDICT: {regime_verdict} (n_breaks={n_breaks}/4 markers)")

regime_break_summary = {
    "herfindahl": {"t": t_herf, "mean_pre": m_pre, "mean_post": m_post, "n_pre": n_pre, "n_post": n_post,
                   "ks_D": d_herf, "ks_p_approx": p_herf},
    "pcr_oi_level_full_chain": {"t": t_pcr_lvl, "mean_pre": m_pcr_pre, "mean_post": m_pcr_post,
                                  "n_pre": n_pcr_pre, "n_post": n_pcr_post},
    "expiry_day_vol_cash_2015on": {"t": t_expvol_break, "mean_pre": m_expvol_pre, "mean_post": m_expvol_post,
                                     "n_pre": n_ev_pre, "n_post": n_ev_post},
    "pcr_predictive_diag_h5": {"ret_t_pre": t_pcr_ret5_pre, "ret_t_post": t_pcr_ret5_post,
                                "vol_t_pre": t_pcr_vol5_pre, "vol_t_post": t_pcr_vol5_post},
    "weekday_switch_2023_2025": weekday_switch_near_oct2024.to_dict("records") if len(weekday_switch_near_oct2024) else [],
    "verdict": regime_verdict,
    "n_breaks_of_4": n_breaks,
}
(OUT / "effect8_regime_break_oct2024.json").write_text(json.dumps(regime_break_summary, indent=2, default=str))

# =====================================================================================
# EFFECT 7 -- OI build-up/unwind sign as directional signal
# =====================================================================================
log("Effect 7: OI build-up/unwind sign (CHG_IN_OI) ...")
chg_by_type = opt.groupby(["TIMESTAMP", "OPTION_TYP"])["CHG_IN_OI"].sum().unstack("OPTION_TYP")
chg = pd.DataFrame(index=chg_by_type.index)
chg["CHG_CE"] = chg_by_type.get("CE")
chg["CHG_PE"] = chg_by_type.get("PE")
chg["signal"] = np.sign(chg["CHG_CE"]) - np.sign(chg["CHG_PE"])
chg = chg.reset_index().rename(columns={"TIMESTAMP": "date"}).sort_values("date").reset_index(drop=True)
assert chg["date"].is_unique, "L4: CHG frame has duplicate dates -- would fan out on merge"
merged7 = daily.merge(chg[["date", "signal"]], on="date", how="inner").sort_values("date").reset_index(drop=True)
n7 = len(merged7)
for h in (1, 3, 5):
    arr = np.full(n7, np.nan)
    cl = merged7["close"].values
    for i in range(n7 - h):
        arr[i] = cl[i + h] / cl[i] - 1.0
    merged7[f"fwd_ret_{h}"] = arr

build_mask7 = (merged7["date"] <= BUILD_END).values
hold_mask7 = (merged7["date"] >= HOLDOUT_START).values
rng7 = np.random.default_rng(SEED)
effect7_rows = []
for h in (1, 3, 5):
    xb = merged7.loc[build_mask7, "signal"].values
    yb = merged7.loc[build_mask7, f"fwd_ret_{h}"].values
    beta_b, t_b, n_b = ols_beta_t(xb, yb)
    mask_ok = ~(np.isnan(xb) | np.isnan(yb))
    xv, yv = xb[mask_ok], yb[mask_ok]
    x_shuf = rng7.permutation(xv)
    _, t_pa, _ = ols_beta_t(x_shuf, yv)
    x_roll = np.roll(xv, 126)
    _, t_pb, _ = ols_beta_t(x_roll, yv)
    bar = max(abs(t_pa) if not np.isnan(t_pa) else 0, abs(t_pb) if not np.isnan(t_pb) else 0)
    xh = merged7.loc[hold_mask7, "signal"].values
    yh = merged7.loc[hold_mask7, f"fwd_ret_{h}"].values
    beta_h, t_h, n_h = ols_beta_t(xh, yh)
    cleared = (not np.isnan(t_b)) and (abs(t_b) > bar)
    sign_match = (not np.isnan(beta_h)) and (not np.isnan(beta_b)) and (np.sign(beta_h) == np.sign(beta_b))
    verdict = ("LEAD (clears placebo + holdout sign match)" if cleared and sign_match
               else ("CLEARS PLACEBO but holdout sign flips -> not a lead" if cleared
                     else "NO CONTENT (placebo-indistinguishable)"))
    effect7_rows.append({"horizon": h, "n_build": int(n_b), "t_build": round(t_b, 3) if not np.isnan(t_b) else None,
                         "placebo_bar": round(bar, 3), "n_holdout": int(n_h),
                         "t_holdout": round(t_h, 3) if not np.isnan(t_h) else None, "verdict": verdict})
    effects_rows.append([f"OI_buildup_sign_fwd_ret_h{h}", "OLS beta t-stat, sign(dCE_OI)-sign(dPE_OI)",
                         int(n_b), round(t_b, 3) if not np.isnan(t_b) else None, round(bar, 3), verdict])
effect7_df = pd.DataFrame(effect7_rows)
effect7_df.to_csv(OUT / "effect7_oi_buildup_signal.csv", index=False)
log(f"Effect 7 (OI buildup sign):\n{effect7_df.to_string()}")

# =====================================================================================
# EFFECT 9 -- intraday seasonality (full 1.05M-bar file)
# =====================================================================================
log("Effect 9: intraday seasonality ...")
spot["minute_of_day"] = spot["ts"].dt.hour * 60 + spot["ts"].dt.minute
spot["bucket"] = (spot["minute_of_day"] // 5) * 5
spot = spot.sort_values(["date", "ts"]).reset_index(drop=True)
spot["ret"] = spot.groupby("date")["close"].pct_change()

bucket_stats = spot.groupby("bucket").agg(mean_ret=("ret", "mean"),
                                           mean_absret=("ret", lambda s: s.abs().mean()),
                                           n=("ret", "count")).reset_index()
bucket_stats.to_csv(OUT / "effect9_intraday_bucket_profile_full.csv", index=False)

spot["year"] = spot["date"].dt.year
era_bins = [(2015, 2018, "era1_2015_2018"), (2019, 2022, "era2_2019_2022"), (2023, 2026, "era3_2023_2026")]
era_profiles = {}
for y0, y1, name in era_bins:
    sub = spot[(spot["year"] >= y0) & (spot["year"] <= y1)]
    prof = sub.groupby("bucket")["ret"].apply(lambda s: s.abs().mean())
    era_profiles[name] = prof
era_df = pd.DataFrame(era_profiles)
era_df.to_csv(OUT / "effect9_intraday_bucket_profile_by_era.csv")
corr_e1_e3 = era_df["era1_2015_2018"].corr(era_df["era3_2023_2026"])
stability_verdict = "STABLE (corr>0.7)" if corr_e1_e3 > 0.7 else "DECAYED (corr<=0.7)"
log(f"Effect9 era1-vs-era3 bucket-vol-profile corr={corr_e1_e3:.3f} -> {stability_verdict}")
effects_rows.append(["intraday_seasonality_era_stability", "corr(era1,era3) of per-bucket mean|ret| profile",
                     f"{len(era_df)} buckets", round(corr_e1_e3, 3), "n/a (stability check)", stability_verdict])

b = bucket_stats.set_index("bucket")
first30 = b.loc[(b.index >= 555) & (b.index < 585)]
last30 = b.loc[(b.index >= 900) & (b.index < 930)]
midday = b.loc[(b.index >= 660) & (b.index < 840)]

def weighted_mean_absret(sub: pd.DataFrame) -> float:
    return float(np.average(sub["mean_absret"], weights=sub["n"])) if len(sub) and sub["n"].sum() > 0 else np.nan

wm_first30 = weighted_mean_absret(first30)
wm_last30 = weighted_mean_absret(last30)
wm_midday = weighted_mean_absret(midday)
log(f"Effect9 first30={wm_first30:.5f} last30={wm_last30:.5f} midday={wm_midday:.5f}")

rng9 = np.random.default_rng(SEED)
all_buckets = b.index.values
null_diff_180 = np.empty(500)
for i in range(500):
    win_a = rng9.choice(all_buckets, size=6, replace=False)
    win_b = rng9.choice(all_buckets, size=36, replace=False)
    ma = weighted_mean_absret(b.loc[b.index.isin(win_a)])
    mb = weighted_mean_absret(b.loc[b.index.isin(win_b)])
    null_diff_180[i] = ma - mb

diff_first_vs_midday = wm_first30 - wm_midday
diff_last_vs_midday = wm_last30 - wm_midday
bar_first = np.percentile(np.abs(null_diff_180), 95)
bar_last = bar_first
verdict_first = "REAL (clears random-window null)" if abs(diff_first_vs_midday) > bar_first else "NO CONTENT vs random-window null"
verdict_last = "REAL (clears random-window null)" if abs(diff_last_vs_midday) > bar_last else "NO CONTENT vs random-window null"
log(f"Effect9 first30-vs-midday diff={diff_first_vs_midday:.5f} bar95={bar_first:.5f} -> {verdict_first}")
log(f"Effect9 last30-vs-midday diff={diff_last_vs_midday:.5f} bar95={bar_last:.5f} -> {verdict_last}")
effects_rows.append(["intraday_first30min_vs_midday", "weighted mean|ret| diff vs random-window null",
                     f"n_bar={int(first30['n'].sum())}", round(diff_first_vs_midday, 5), round(bar_first, 5), verdict_first])
effects_rows.append(["intraday_last30min_vs_midday", "weighted mean|ret| diff vs random-window null",
                     f"n_bar={int(last30['n'].sum())}", round(diff_last_vs_midday, 5), round(bar_last, 5), verdict_last])

# =====================================================================================
# EFFECT 10 -- day-of-week / turn-of-month
# =====================================================================================
log("Effect 10: day-of-week / turn-of-month ...")
daily["weekday"] = daily["date"].dt.weekday
valid10 = daily.dropna(subset=["ret"]).reset_index(drop=True)
ret_vals = valid10["ret"].values
wd_vals = valid10["weekday"].values
rng10 = np.random.default_rng(SEED)
dow_rows = []
for wdnum in range(5):
    mask = wd_vals == wdnum
    t_wd, m_wd, m_rest, n_wd, n_rest = welch_t(ret_vals[mask], ret_vals[~mask])
    null_wd = placebo_relabel_null(ret_vals, n_true=int(mask.sum()), draws=500, seed=SEED + wdnum)
    bar_wd = np.percentile(np.abs(null_wd), 95)
    verdict_wd = "REAL (clears placebo)" if abs(t_wd) > bar_wd else "NO CONTENT (placebo-indistinguishable)"
    dow_rows.append({"weekday": WD_NAMES[wdnum], "n": int(n_wd), "mean_ret": m_wd, "t": t_wd,
                     "placebo_bar95": bar_wd, "verdict": verdict_wd})
    effects_rows.append([f"day_of_week_{WD_NAMES[wdnum]}", "Welch t, mean ret vs other days",
                         int(n_wd), round(t_wd, 3), round(bar_wd, 3), verdict_wd])
dow_df = pd.DataFrame(dow_rows)
dow_df.to_csv(OUT / "effect10_day_of_week.csv", index=False)
log(f"Effect10 day-of-week:\n{dow_df.to_string()}")

valid10["ym"] = valid10["date"].dt.to_period("M")
last_td_of_month = valid10.groupby("ym")["date"].max()
first_td_of_month = valid10.groupby("ym")["date"].min()
tom_narrow_set = set(last_td_of_month) | set(first_td_of_month)
valid10["is_tom_narrow"] = valid10["date"].isin(tom_narrow_set)

idx_of_date = {d: i for i, d in enumerate(valid10["date"])}
tom_wide_idx = set()
for d in tom_narrow_set:
    if d in idx_of_date:
        i = idx_of_date[d]
        for off in range(-3, 4):
            j = i + off
            if 0 <= j < len(valid10):
                tom_wide_idx.add(j)
valid10["is_tom_wide"] = valid10.index.isin(tom_wide_idx)

for name, col in (("TOM_narrow", "is_tom_narrow"), ("TOM_wide_pm3", "is_tom_wide")):
    mask = valid10[col].values
    t_tom, m_tom, m_rest, n_tom, n_rest = welch_t(ret_vals[mask], ret_vals[~mask])
    null_tom = placebo_relabel_null(ret_vals, n_true=int(mask.sum()), draws=500, seed=SEED + 100)
    bar_tom = np.percentile(np.abs(null_tom), 95)
    verdict_tom = "REAL (clears placebo)" if abs(t_tom) > bar_tom else "NO CONTENT (placebo-indistinguishable)"
    log(f"Effect10 {name}: t={t_tom:.3f} mean_tom={m_tom:.5f} mean_rest={m_rest:.5f} "
        f"n_tom={n_tom} placebo95={bar_tom:.3f} -> {verdict_tom}")
    effects_rows.append([name, "Welch t, mean ret vs rest-of-month", int(n_tom),
                         round(t_tom, 3), round(bar_tom, 3), verdict_tom])

# =====================================================================================
# WRITE FINAL EFFECTS TABLE
# =====================================================================================
effects_df = pd.DataFrame(effects_rows, columns=["effect", "measurement", "n", "t", "vs_placebo", "verdict"])
effects_df.to_csv(OUT / "EFFECTS_TABLE.csv", index=False)
log(f"\n=== FINAL EFFECTS TABLE ({len(effects_df)} rows) ===\n{effects_df.to_string()}")

(OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"DONE in {time.time()-t_script_start:.1f}s")
