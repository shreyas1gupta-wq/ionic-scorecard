"""IRONFLY_LADDER_20260802 -- step 2: build the shared roll schedule.
At each ~7-calendar-day roll date, find the ATM entry (nearest expiry to 13 calendar days),
compute ATM straddle implied vol (vollib Black-Scholes/Jackel), trailing 50d realized vol, a
GARCH(1,1) forecast (expanding window, arch package, no lookahead), and IV's own trailing
percentile. This schedule + its filter flags are SHARED across all 32 grid cells -- the roll
dates and filter pass/fail do not depend on OTM distance or roll-mode, only on the ATM entry.
"""
import time
import warnings

import numpy as np
import pandas as pd
from vollib.black_scholes.implied_volatility import implied_volatility
from arch import arch_model

warnings.filterwarnings("ignore")

ALL_TRADED = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
              r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
              r"\nifty_optidx_all_traded.parquet")
SV_EXT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
          r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\cache\spot_vix_ext.parquet")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\cache")

TARGET_DTE = 13
ROLL_CADENCE_CALDAYS = 7
LAST_OK = pd.Timestamp("2026-07-03")   # last date with spot/vix data (matches existing engine)
R_FREE = 0.065   # [ASSUMPTION, disclosed in PRE_REGISTRATION.md] fixed India short-rate proxy


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading tables...")
tbl = pd.read_parquet(ALL_TRADED)
n_before = len(tbl)
tbl = tbl.drop_duplicates(subset=["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"], keep="first")
if n_before != len(tbl):
    log(f"deduped {n_before - len(tbl)} exact-duplicate rows (2024-07-01..05 bhavcopy double-print; "
        f"verified all value cols identical across dupes, not a data-conflict)")
tbl = tbl.set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV_EXT).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl.index.get_level_values(0).unique())
log(f"tbl {len(tbl):,} rows | trading days {len(trading_days)} | expiries {len(all_exp)}")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def next_trading_day(d, n=1):
    pos = trading_days.searchsorted(d)
    pos += n
    return trading_days[pos] if pos < len(trading_days) else None


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=3, band_mult=3):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        d = (e - avail_from).days
        if d < min_dte:
            continue
        if d > target_dte * band_mult + 30:
            break
        diff = abs(d - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


def find_atm_entry(expiry, avail_from, ref_spot, tol_days=5):
    strike0 = round(ref_spot / 50) * 50
    for off in (0, 50, -50, 100, -100, 150, -150, 200, -200):
        K = strike0 + off
        try:
            ce = tbl.loc[(expiry, K, "CE")]["CLOSE"]
            pe = tbl.loc[(expiry, K, "PE")]["CLOSE"]
        except KeyError:
            continue
        common = ce.index.intersection(pe.index)
        common = common[common >= avail_from]
        if len(common) == 0:
            continue
        d = common.min()
        if (d - avail_from).days > tol_days:
            continue
        return d, K, float(ce.loc[d]), float(pe.loc[d])
    return None


def solve_iv(ce0, pe0, K, spot, dte_days):
    t = max(dte_days, 1) / 365.0
    try:
        iv_c = implied_volatility(ce0, spot, K, t, R_FREE, 'c')
    except Exception:
        iv_c = np.nan
    try:
        iv_p = implied_volatility(pe0, spot, K, t, R_FREE, 'p')
    except Exception:
        iv_p = np.nan
    vals = [v for v in (iv_c, iv_p) if np.isfinite(v)]
    return float(np.mean(vals)) if vals else np.nan


def garch_forecast_annualized(logrets_pct, dte_calendar_days):
    """Expanding-window GARCH(1,1) fit on daily log returns (in %), forecast over the option's
    remaining life, returned as an ANNUALIZED decimal vol (same scale as IV) for direct comparison.
    """
    if len(logrets_pct) < 252:
        return np.nan
    horizon_td = max(1, round(dte_calendar_days * 5 / 7))   # calendar days -> trading days
    try:
        am = arch_model(logrets_pct, vol="Garch", p=1, q=1, dist="normal", rescale=False)
        res = am.fit(disp="off", show_warning=False)
        fc = res.forecast(horizon=horizon_td, reindex=False)
        var_h = fc.variance.values[-1]          # length horizon_td, in pct^2/day
        avg_daily_var = var_h.sum() / horizon_td
        ann_vol_pct = np.sqrt(avg_daily_var * 252)
        return float(ann_vol_pct / 100.0)
    except Exception:
        return np.nan


def trailing_percentile(values, min_win=252, max_win=504):
    """values: chronological list (may contain NaN). Row i uses ONLY values[lo:i] -- strictly
    prior, matches the existing vix_pct_trail/rv20_pct_trail convention (no lookahead)."""
    out = [np.nan] * len(values)
    for i in range(len(values)):
        lo = max(0, i - max_win + 1)
        hist = np.array([v for v in values[lo:i] if np.isfinite(v)])
        if len(hist) < min_win or not np.isfinite(values[i]):
            continue
        out[i] = float((hist < values[i]).mean())
    return out


rows = []
avail_from = trading_days[0]
guard = 0
max_cycles = 700
logret_series = sv["logret"]

log("walking ~7-calendar-day roll schedule...")
while guard < max_cycles:
    guard += 1
    exp = find_target_expiry(TARGET_DTE, avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        log(f"stop at guard={guard}: no more expiries in range")
        break
    ref = spot_on_or_before(avail_from)
    if ref is None:
        break
    _, ref_spot = ref
    res = find_atm_entry(exp, avail_from, ref_spot)
    if res is None:
        nxt = next_trading_day(avail_from, 3)
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
        continue
    entry_date, K, ce0, pe0 = res
    dte_actual = (exp - entry_date).days
    if dte_actual < 3:
        nxt = next_trading_day(exp, 1)
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
        continue
    spot_res = spot_on_or_before(entry_date)
    if spot_res is None:
        nxt = on_or_after(entry_date + pd.Timedelta(days=ROLL_CADENCE_CALDAYS))
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
        continue
    _, spot_entry = spot_res

    iv = solve_iv(ce0, pe0, K, spot_entry, dte_actual)

    row_sv = sv.loc[entry_date] if entry_date in sv.index else None
    rv50 = (float(row_sv["rv50_ann"]) / 100.0
            if row_sv is not None and not pd.isna(row_sv.get("rv50_ann", np.nan)) else np.nan)
    rv20 = (float(row_sv["rv20_ann"]) / 100.0
            if row_sv is not None and not pd.isna(row_sv.get("rv20_ann", np.nan)) else np.nan)

    # GARCH: expanding window strictly BEFORE entry_date (excludes entry_date's own return)
    hist_rets = logret_series.loc[:entry_date].iloc[:-1].dropna().to_numpy() * 100.0
    garch_fc = garch_forecast_annualized(hist_rets, dte_actual)

    rows.append(dict(roll_date=entry_date, expiry=exp, dte_actual=dte_actual, atm_strike=K,
                      spot_entry=spot_entry, ce0=ce0, pe0=pe0, iv=iv, rv20=rv20, rv50=rv50,
                      garch_fc=garch_fc))

    if guard % 25 == 0 or guard <= 3:
        log(f"  [{guard}] {entry_date.date()} exp={exp.date()} dte={dte_actual} K={K:.0f} "
            f"iv={iv} rv50={rv50} garch={garch_fc}")

    nxt = on_or_after(entry_date + pd.Timedelta(days=ROLL_CADENCE_CALDAYS))
    if nxt is None or nxt > LAST_OK:
        break
    avail_from = nxt

log(f"schedule built: {len(rows)} roll dates")
sched = pd.DataFrame(rows)

# IV trailing percentile -- second pass, chronological, strictly-prior only (no lookahead)
sched["iv_pct_trail"] = trailing_percentile(sched["iv"].tolist())

# filter flags (all NaN-safe: NaN comparisons -> False, i.e. "cannot confirm cheap -> don't enter")
sched["filter_unconditional"] = True
sched["filter_iv_lt_rv50"] = (sched["iv"] < sched["rv50"]).fillna(False)
sched["filter_iv_lt_garch"] = (sched["iv"] < sched["garch_fc"]).fillna(False)
sched["filter_iv_pct_low"] = (sched["iv_pct_trail"] <= 0.25).fillna(False)

n = len(sched)
log(f"filter pass rates: unconditional=100% "
    f"iv_lt_rv50={sched['filter_iv_lt_rv50'].mean():.1%} "
    f"iv_lt_garch={sched['filter_iv_lt_garch'].mean():.1%} "
    f"iv_pct_low={sched['filter_iv_pct_low'].mean():.1%} (n={n})")
log(f"IV solve coverage: {sched['iv'].notna().mean():.1%} | "
    f"GARCH coverage: {sched['garch_fc'].notna().mean():.1%} | "
    f"IV-percentile coverage: {sched['iv_pct_trail'].notna().mean():.1%}")

sched.to_parquet(f"{OUT}\\schedule.parquet", index=False)
sched.to_csv(f"{OUT}\\schedule.csv", index=False)
log(f"-> cache/schedule.parquet + .csv ({len(sched)} rows)")
log("DONE")
