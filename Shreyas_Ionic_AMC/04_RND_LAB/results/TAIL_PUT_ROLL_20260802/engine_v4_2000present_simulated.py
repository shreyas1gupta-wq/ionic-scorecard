"""TAIL_PUT_ROLL_20260802 -- v4: SIMULATED/MODELED 10%-OTM 6M put, roll-3M vs no-roll, 2000-present.
NO REAL OPTION DATA EXISTS BEFORE 2016 -- this is a Black-Scholes RECONSTRUCTION using real NIFTY
spot history (NSE's official back-computed series, 1990-2026) and a REALIZED-VOL PROXY for IV
(no real IV data exists this far back either). This UNDERSTATES true option cost -- it ignores
any variance risk premium (IV historically runs richer than subsequent RV, per this session's own
VOL_SURFACE_20260731 finding). Labeled MODELED throughout; do not confuse with the real-data
TAIL_PUT_ROLL_20260802 engines (v2/v3) covering 2016-2026.
"""
import time

import numpy as np
import pandas as pd
from vollib.black_scholes import black_scholes

RAW = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data"
       r"\NIFTY 50_day.csv")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\TAIL_PUT_ROLL_20260802")

R_FREE = 0.07          # [ASSUMPTION] long-run avg India short rate proxy, fixed throughout
OTM_FRAC = 0.90
TARGET_DTE_DAYS = 180
ROLL_CALDAYS = 91
LEG_COST_RT = 1.77
START = pd.Timestamp("2000-01-01")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading NIFTY 50 daily series (NSE official back-computed, 1990-2026)...")
raw = pd.read_csv(RAW)
raw.columns = [c.strip().lower() for c in raw.columns]
date_col = [c for c in raw.columns if "date" in c][0]
raw[date_col] = pd.to_datetime(raw[date_col])
raw = raw.sort_values(date_col).drop_duplicates(subset=[date_col]).reset_index(drop=True)
raw = raw.rename(columns={date_col: "date"})
log(f"full range {raw['date'].min().date()} .. {raw['date'].max().date()}, {len(raw):,} rows")

raw["logret"] = np.log(raw["close"] / raw["close"].shift(1))
raw["rv50_ann"] = raw["logret"].rolling(50).std() * np.sqrt(252)   # trailing, no lookahead

trading_days = raw["date"]
n0 = trading_days.searchsorted(START)
log(f"warm-up: {n0} rows before 2000-01-01 used only to seed the trailing-50d vol estimate")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days.iloc[pos] if pos < len(trading_days) else None


def row_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return pos


def bs_put_price(spot, strike, t_years, sigma):
    if t_years <= 0 or sigma is None or not np.isfinite(sigma) or sigma <= 0:
        return None
    return black_scholes('p', spot, strike, t_years, R_FREE, sigma)


def open_put(entry_pos):
    spot = raw["close"].iloc[entry_pos]
    sigma = raw["rv50_ann"].iloc[entry_pos]
    K = round(spot * OTM_FRAC / 50) * 50
    prem0 = bs_put_price(spot, K, TARGET_DTE_DAYS / 365.0, sigma)
    if prem0 is None:
        return None
    entry_date = trading_days.iloc[entry_pos]
    return dict(entry_date=entry_date, entry_pos=entry_pos, K=K, prem0=prem0, spot_entry=spot,
                sigma_at_entry=sigma)


def close_at_expiry(pos):
    exp_date = pos["entry_date"] + pd.Timedelta(days=TARGET_DTE_DAYS)
    exit_pos = row_on_or_before(exp_date)
    if exit_pos is None or exit_pos <= pos["entry_pos"]:
        return None
    spot_exit = raw["close"].iloc[exit_pos]
    payoff = max(pos["K"] - spot_exit, 0.0)
    return _finalize(pos, trading_days.iloc[exit_pos], payoff, spot_exit, "expiry_intrinsic")


def close_at_market_modeled(pos, close_date):
    exit_pos = row_on_or_before(close_date)
    if exit_pos is None or exit_pos <= pos["entry_pos"]:
        return None
    spot_t = raw["close"].iloc[exit_pos]
    sigma_t = raw["rv50_ann"].iloc[exit_pos]
    t_remaining = (pos["entry_date"] + pd.Timedelta(days=TARGET_DTE_DAYS) - trading_days.iloc[exit_pos]).days / 365.0
    price = bs_put_price(spot_t, pos["K"], max(t_remaining, 1 / 365.0), sigma_t)
    if price is None:
        return None
    return _finalize(pos, trading_days.iloc[exit_pos], price, spot_t, "rollover_modeled")


def _finalize(pos, exit_date, exit_value, spot_exit, exit_type):
    gross = exit_value - pos["prem0"]
    net = gross - LEG_COST_RT
    return dict(entry_date=pos["entry_date"], exit_date=exit_date, K=pos["K"],
                spot_entry=pos["spot_entry"], spot_exit=spot_exit, prem0=pos["prem0"],
                sigma_at_entry=pos["sigma_at_entry"], exit_value=exit_value, gross_pnl=gross,
                net_pnl=net, exit_type=exit_type)


def run_no_roll():
    trades = []
    pos_idx = max(n0, 51)
    while True:
        entry_pos = pos_idx
        if entry_pos >= len(raw) - 1:
            break
        entry_date = trading_days.iloc[entry_pos]
        exp_check = entry_date + pd.Timedelta(days=TARGET_DTE_DAYS)
        if exp_check > trading_days.iloc[-1]:
            break
        pos = open_put(entry_pos)
        if pos is None:
            pos_idx += 5
            continue
        t = close_at_expiry(pos)
        if t is None:
            pos_idx += 5
            continue
        trades.append(t)
        nxt_date = on_or_after(t["exit_date"] + pd.Timedelta(days=1))
        if nxt_date is None:
            break
        pos_idx = trading_days.searchsorted(nxt_date)
    return pd.DataFrame(trades)


def run_roll_3m():
    trades = []
    pos_idx = max(n0, 51)
    while True:
        entry_pos = pos_idx
        if entry_pos >= len(raw) - 1:
            break
        entry_date = trading_days.iloc[entry_pos]
        if entry_date + pd.Timedelta(days=TARGET_DTE_DAYS) > trading_days.iloc[-1]:
            break
        pos = open_put(entry_pos)
        if pos is None:
            pos_idx += 5
            continue
        roll_target = pos["entry_date"] + pd.Timedelta(days=ROLL_CALDAYS)
        if roll_target >= pos["entry_date"] + pd.Timedelta(days=TARGET_DTE_DAYS):
            t = close_at_expiry(pos)
        else:
            t = close_at_market_modeled(pos, roll_target)
            if t is None:
                t = close_at_expiry(pos)
        if t is None:
            pos_idx += 5
            continue
        trades.append(t)
        nxt_date = on_or_after(t["exit_date"] + pd.Timedelta(days=1))
        if nxt_date is None:
            break
        pos_idx = trading_days.searchsorted(nxt_date)
    return pd.DataFrame(trades)


log("running NO_ROLL (modeled, 2000-present)...")
no_roll = run_no_roll()
no_roll.to_csv(f"{OUT}\\checkpoints\\trades_2000present_no_roll_MODELED.csv", index=False)
n_years = (no_roll["exit_date"].max() - no_roll["entry_date"].min()).days / 365.25
log(f"  -> {len(no_roll)} cycles, {no_roll['entry_date'].min().date()}..{no_roll['exit_date'].max().date()} "
    f"({n_years:.1f}yr), total {no_roll['net_pnl'].sum():.0f} pts, ann. {no_roll['net_pnl'].sum()/n_years:.1f} pts/yr")

log("running ROLL_3M (modeled, 2000-present)...")
roll_3m = run_roll_3m()
roll_3m.to_csv(f"{OUT}\\checkpoints\\trades_2000present_roll_3m_MODELED.csv", index=False)
n_years2 = (roll_3m["exit_date"].max() - roll_3m["entry_date"].min()).days / 365.25
log(f"  -> {len(roll_3m)} cycles, {roll_3m['entry_date'].min().date()}..{roll_3m['exit_date'].max().date()} "
    f"({n_years2:.1f}yr), total {roll_3m['net_pnl'].sum():.0f} pts, ann. {roll_3m['net_pnl'].sum()/n_years2:.1f} pts/yr")

# crash-window spotcheck: 2000-01 dotcom, 2008 GFC, 2020 COVID
log("crash-window spotcheck (no_roll cycles overlapping known crises):")
for name, start, end in (("dotcom 2000-01", "2000-01-01", "2001-12-31"),
                          ("GFC 2008", "2008-01-01", "2009-03-31"),
                          ("COVID 2020", "2020-01-01", "2020-06-30")):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    sub = no_roll[(no_roll["entry_date"] <= e) & (no_roll["exit_date"] >= s)]
    if len(sub):
        log(f"  {name}: {len(sub)} cycle(s) overlap, net_pnl={sub['net_pnl'].tolist()}")
    else:
        log(f"  {name}: no cycle overlaps this window")

log("DONE -- ALL NUMBERS ABOVE ARE MODELED (Black-Scholes off realized vol), NOT REAL OPTION PRICES")
