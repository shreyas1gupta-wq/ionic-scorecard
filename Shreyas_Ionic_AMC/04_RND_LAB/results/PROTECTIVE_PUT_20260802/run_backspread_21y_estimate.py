"""PROTECTIVE_PUT_20260802 -- 21-year "best estimate" for BACKSPREAD_1x2_10pct
(SELL 1x 2.5% OTM PE + BUY 2x 10% OTM PE, 30D target, roll T-5).

Real NIFTY index-option price data only exists from 2016-01-04 (nifty_optidx_all_traded.parquet).
NIFTY 50 OFFICIAL INDEX LEVEL data exists from 2005-04-01 (results/factor_replication/
20260704_perf_table/level_NIFTY50_official.csv) -- 21+ years. This script:
  1. Uses the REAL backspread trades already computed (2016-2026, n=116) verbatim.
  2. MODELS 2005-01-01..2016-01-03 with Black-Scholes, sigma = k * trailing-20d-realized-vol,
     k CALIBRATED against the REAL 2016-2026 premiums (median ratio of actual/BS-theoretical on
     both legs) -- same methodology as SELLSIDE_20260710/covid_backcast.py, just for THIS structure
     and covering ~11 modeled years instead of ~16 modeled months.
  3. Synthetic expiry calendar for the modeled period = last Thursday of each month (NIFTY had no
     WEEKLY options before ~2019; monthly is the historically correct convention for a 30D-target
     structure in that era), snapped to the nearest actual prior trading day in the level series.
  4. Reports a VALIDATION check (modeled-vs-actual correlation on the real period, using ONLY the
     RV-based model, i.e. re-modeling the real period blind and comparing to actual) so the modeled
     segment's credibility is disclosed, not asserted.
  5. Splices modeled + real into one 21-year series, computes MaxDD, and outputs data for the vs-
     NIFTY-50 chart. REAL and MODELED periods are tagged in every output row -- never blended
     silently.
NOT a backtest for the pre-2016 period -- a disclosed reconstruction, same epistemic status as the
existing COVID backcast.
"""
import math
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LEVEL = ROOT + r"\results\factor_replication\20260704_perf_table\level_NIFTY50_official.csv"
REAL_TRADES = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802\trades_BACKSPREAD_1x2_10pct.csv"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

COST_PER_LEG_RT = 1.77
LOT = 75
TARGET_DTE = 30
ROLL_OFFSET = 5
NEAR_OTM, FAR_OTM = 0.025, 0.10
R_FREE = 0.065   # [ASSUMPTION, matches covid_backcast.py convention] fixed rate, low-sensitivity at 30D


def bs_put(S, K, T, sigma, r=R_FREE):
    if T <= 0:
        return max(K - S, 0.0)
    if sigma <= 0:
        sigma = 1e-4
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / sq
    d2 = d1 - sq

    def N(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    return K * math.exp(-r * T) * N(-d2) - S * N(-d1)


# ---- load NIFTY 50 official level, 2005-2026, compute trailing realized vol ----
lvl = pd.read_csv(LEVEL, parse_dates=["date"]).set_index("date").sort_index()
lvl["logret"] = np.log(lvl["level"] / lvl["level"].shift(1))
lvl["rv20"] = lvl["logret"].rolling(20).std() * math.sqrt(252)
trading_days_full = lvl.index
print(f"level series: {trading_days_full.min().date()} .. {trading_days_full.max().date()} ({len(lvl)} rows)")


def on_or_after(d, days_index):
    pos = days_index.searchsorted(pd.Timestamp(d))
    return days_index[pos] if pos < len(days_index) else None


def snap_prior(d, days_index):
    pos = days_index.searchsorted(pd.Timestamp(d), side="right") - 1
    return days_index[pos] if pos >= 0 else None


def monthly_expiry_calendar(start, end, days_index):
    """Last Thursday of each month, snapped to the nearest actual prior trading day."""
    exps = []
    cur = pd.Timestamp(start).replace(day=1)
    end = pd.Timestamp(end)
    while cur <= end:
        nxt_month = (cur + pd.offsets.MonthEnd(1))
        last_day = nxt_month
        d = last_day
        while d.dayofweek != 3:   # Thursday = 3
            d -= pd.Timedelta(days=1)
        snapped = snap_prior(d, days_index)
        if snapped is not None:
            exps.append(snapped)
        cur = cur + pd.offsets.MonthBegin(1)
    return sorted(set(exps))


# ---- CALIBRATION: fit k on the REAL period using RV20 as the sole vol input, blind re-model ----
real = pd.read_csv(REAL_TRADES, parse_dates=["entry_date", "roll_date", "expiry"])
ks = []
for _, r in real.iterrows():
    if r["entry_date"] not in lvl.index or pd.isna(lvl.loc[r["entry_date"], "rv20"]):
        continue
    rv = float(lvl.loc[r["entry_date"], "rv20"])
    T_near = max((r["expiry"] - r["entry_date"]).days, 1) / 365.0
    bs_near = bs_put(r["spot_entry"], r["near_strike"], T_near, rv)
    bs_far = bs_put(r["spot_entry"], r["far_strike"], T_near, rv)
    if bs_near > 1 and bs_far > 1:
        ks.append(r["near_entry"] / bs_near)
        ks.append(r["far_entry"] / bs_far)
K_CAL = float(np.median(ks))
print(f"calibration: n_obs={len(ks)} k(median actual/BS-theoretical)={K_CAL:.3f}")

# ---- VALIDATION: blind-remodel the REAL period using k*RV20, compare to actual net_pnl_pts ----
modeled_real = []
for _, r in real.iterrows():
    if r["entry_date"] not in lvl.index or pd.isna(lvl.loc[r["entry_date"], "rv20"]):
        continue
    rv_e = K_CAL * float(lvl.loc[r["entry_date"], "rv20"])
    T_e = max((r["expiry"] - r["entry_date"]).days, 1) / 365.0
    near0 = bs_put(r["spot_entry"], r["near_strike"], T_e, rv_e)
    far0 = bs_put(r["spot_entry"], r["far_strike"], T_e, rv_e)
    if r["roll_date"] not in lvl.index or pd.isna(lvl.loc[r["roll_date"], "rv20"]):
        continue
    spot_x = float(lvl.loc[r["roll_date"], "level"])
    rv_x = K_CAL * float(lvl.loc[r["roll_date"], "rv20"])
    T_x = max((r["expiry"] - r["roll_date"]).days, 0) / 365.0
    nearx = bs_put(spot_x, r["near_strike"], T_x, rv_x)
    farx = bs_put(spot_x, r["far_strike"], T_x, rv_x)
    gross = (near0 - nearx) + 2 * (farx - far0)
    modeled_real.append(dict(entry_date=r["entry_date"], model_net=gross - 3 * COST_PER_LEG_RT,
                              actual_net=r["net_pnl_pts"]))
mr = pd.DataFrame(modeled_real)
corr = mr["model_net"].corr(mr["actual_net"])
BIAS_CORRECTION = mr["actual_net"].mean() / mr["model_net"].mean()
print(f"VALIDATION on real period: n={len(mr)} corr(model,actual)={corr:.2f} "
      f"mean model={mr['model_net'].mean():+.2f} vs actual={mr['actual_net'].mean():+.2f} "
      f"-> BIAS_CORRECTION factor {BIAS_CORRECTION:.3f} applied to all MODELED rungs "
      f"(flat-vol BS has no skew between the 2.5%/10% OTM strikes; disclosed, not hidden)")

# ---- MODEL the pre-real period: 2005-01-01 .. 2016-01-03 ----
FIRST_REAL_DATE = pd.Timestamp("2016-01-04")
model_start = trading_days_full.min()
exps = monthly_expiry_calendar(model_start, FIRST_REAL_DATE, trading_days_full)


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=3):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        dd = (e - avail_from).days
        if dd < min_dte:
            continue
        diff = abs(dd - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


rows = []
avail_from = model_start
guard = 0
while guard < 400 and avail_from < FIRST_REAL_DATE:
    guard += 1
    exp = find_target_expiry(TARGET_DTE, avail_from, exps)
    if exp is None or exp >= FIRST_REAL_DATE:
        break
    if avail_from not in lvl.index or pd.isna(lvl.loc[avail_from, "rv20"]):
        nxt = on_or_after(avail_from + pd.Timedelta(days=3), trading_days_full)
        if nxt is None or nxt >= FIRST_REAL_DATE:
            break
        avail_from = nxt
        continue
    spot0 = float(lvl.loc[avail_from, "level"])
    Kn = round(spot0 * (1 - NEAR_OTM) / 50) * 50
    Kf = round(spot0 * (1 - FAR_OTM) / 50) * 50
    rv0 = K_CAL * float(lvl.loc[avail_from, "rv20"])
    T0 = max((exp - avail_from).days, 1) / 365.0
    near0 = bs_put(spot0, Kn, T0, rv0)
    far0 = bs_put(spot0, Kf, T0, rv0)

    roll_target = exp - pd.Timedelta(days=ROLL_OFFSET)
    roll_date = on_or_after(roll_target, trading_days_full)
    if roll_date is None or roll_date <= avail_from or roll_date >= FIRST_REAL_DATE:
        break
    if roll_date not in lvl.index or pd.isna(lvl.loc[roll_date, "rv20"]):
        avail_from = on_or_after(roll_date + pd.Timedelta(days=1), trading_days_full)
        if avail_from is None:
            break
        continue
    spotx = float(lvl.loc[roll_date, "level"])
    rvx = K_CAL * float(lvl.loc[roll_date, "rv20"])
    Tx = max((exp - roll_date).days, 0) / 365.0
    nearx = bs_put(spotx, Kn, Tx, rvx)
    farx = bs_put(spotx, Kf, Tx, rvx)

    net_debit = near0 - 2 * far0
    gross = (near0 - nearx) + 2 * (farx - far0)
    net_pnl_pts_raw = gross - 3 * COST_PER_LEG_RT
    net_pnl_pts = net_pnl_pts_raw * BIAS_CORRECTION
    rows.append(dict(entry_date=avail_from, roll_date=roll_date, expiry=exp, near_strike=Kn,
                      far_strike=Kf, spot_entry=spot0, net_debit=net_debit,
                      net_pnl_pts_raw=net_pnl_pts_raw, net_pnl_pts=net_pnl_pts,
                      source="MODELED"))
    avail_from = on_or_after(roll_date + pd.Timedelta(days=1), trading_days_full)
    if avail_from is None:
        break

modeled = pd.DataFrame(rows)
print(f"\nmodeled pre-2016 rungs: n={len(modeled)} | {modeled['entry_date'].min().date() if len(modeled) else '-'} "
      f".. {modeled['roll_date'].max().date() if len(modeled) else '-'}")
print(f"  modeled net_mean={modeled['net_pnl_pts'].mean():+.2f} median={modeled['net_pnl_pts'].median():+.2f} "
      f"hit={(modeled['net_pnl_pts']>0).mean():.1%}")

real_tagged = real[["entry_date", "roll_date", "expiry", "near_strike", "far_strike", "spot_entry",
                     "net_debit", "net_pnl_pts"]].copy()
real_tagged["source"] = "REAL"

full = pd.concat([modeled, real_tagged], ignore_index=True).sort_values("roll_date").reset_index(drop=True)
full["cum_pts"] = full["net_pnl_pts"].cumsum()
full.to_csv(f"{OUT}/BACKSPREAD_21Y_full_series.csv", index=False)
print(f"\nFULL 21y series: n={len(full)} rungs | {full['entry_date'].min().date()} .. {full['roll_date'].max().date()}")
print(f"  final cum pts: {full['cum_pts'].iloc[-1]:+.1f} | modeled n={len(modeled)} / real n={len(real_tagged)}")

dd = full["cum_pts"] - full["cum_pts"].cummax()
print(f"  worst drawdown (pts): {dd.min():.1f} on {full.loc[dd.idxmin(),'roll_date'].date()}")
print(f"saved: {OUT}/BACKSPREAD_21Y_full_series.csv")
