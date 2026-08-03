"""TAIL_PUT_ROLL_20260802 -- v5: dynamic NIFTY + put-hedge rebalancing, 2015-present.
MODELED (Black-Scholes off trailing-50d realized vol, same convention as v4) throughout for
consistency across the full 2015-present window -- NOT real option prices.

Portfolio: start with 100 NIFTY lots (LOT=75, fixed simplification) + a 5%-of-portfolio cash
buffer. Every ~6 months, hedge the CURRENT lot count with a 10%-OTM put (sized 1:1 to lots held
at that cycle's start). On settlement: hedge P&L (rupees) -> cash. Rebalance to the 5% cash
TARGET: cash above target buys back lots; cash below target (incl. negative) sells lots to
restore it. This is the "profit -> buy more, loss -> trim to cover" rule, operationalized as a
target-cash-fraction rebalance (disclosed interpretation, not the only possible one).

Two variants:
  PASSIVE   -- hold each 6M hedge to its own expiry, no interim monitoring.
  SIGMA3_ME -- check the -3-sigma trigger ONLY at month-end (not daily/mid-month); if it fires,
              monetize there (modeled BS price) and DO NOT re-hedge for the next 2 calendar
              months (cooldown -- equity runs naked during that window), then resume.
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

R_FREE = 0.07
OTM_FRAC = 0.90
TENOR_DAYS = 180
LOT_SIZE = 75
START_LOTS = 100
CASH_TARGET_FRAC = 0.05
COOLDOWN_MONTHS = 2
LEG_COST_RT = 1.77
START_DATE = pd.Timestamp("2015-01-01")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading NIFTY 50 daily series...")
raw = pd.read_csv(RAW)
raw.columns = [c.strip().lower() for c in raw.columns]
date_col = [c for c in raw.columns if "date" in c][0]
raw[date_col] = pd.to_datetime(raw[date_col])
raw = raw.sort_values(date_col).drop_duplicates(subset=[date_col]).reset_index(drop=True)
raw = raw.rename(columns={date_col: "date"})
raw["logret"] = np.log(raw["close"] / raw["close"].shift(1))
raw["rv50_ann"] = raw["logret"].rolling(50).std() * np.sqrt(252)
trading_days = raw["date"]
raw["is_month_end"] = raw["date"].dt.to_period("M") != raw["date"].shift(-1).dt.to_period("M")
month_end_dates = raw.loc[raw["is_month_end"], "date"].reset_index(drop=True)
log(f"range {raw['date'].min().date()}..{raw['date'].max().date()}, "
    f"{len(month_end_dates)} month-end dates")


def pos_on_or_after(d):
    return trading_days.searchsorted(d)


def pos_on_or_before(d):
    return trading_days.searchsorted(d, side="right") - 1


def spot_sigma_at(pos):
    return float(raw["close"].iloc[pos]), float(raw["rv50_ann"].iloc[pos])


def bs_put(spot, K, t_years, sigma):
    if t_years <= 0 or not np.isfinite(sigma) or sigma <= 0:
        return None
    return black_scholes('p', spot, K, max(t_years, 1 / 365.0), R_FREE, sigma)


def rebalance(cash, lots, spot):
    """Return (new_cash, new_lots, n_traded, trade_type) after moving cash toward the 5% target."""
    total = lots * LOT_SIZE * spot + cash
    target_cash = CASH_TARGET_FRAC * total
    lot_notional = LOT_SIZE * spot
    if cash > target_cash:
        n_buy = int((cash - target_cash) // lot_notional)
        if n_buy > 0:
            cash -= n_buy * lot_notional
            lots += n_buy
            return cash, lots, n_buy, "buy"
    else:
        deficit = target_cash - cash
        n_sell = int(np.ceil(deficit / lot_notional)) if deficit > 0 else 0
        n_sell = min(n_sell, lots)
        if n_sell > 0:
            cash += n_sell * lot_notional
            lots -= n_sell
            return cash, lots, n_sell, "sell"
    return cash, lots, 0, "none"


def run_passive():
    start_pos = pos_on_or_after(START_DATE)
    p0 = raw["close"].iloc[start_pos]
    cash = CASH_TARGET_FRAC / (1 - CASH_TARGET_FRAC) * START_LOTS * LOT_SIZE * p0
    lots = START_LOTS
    log_rows = []
    pos = start_pos
    while pos < len(raw) - 1:
        entry_date = trading_days.iloc[pos]
        exp_date = entry_date + pd.Timedelta(days=TENOR_DAYS)
        if exp_date > trading_days.iloc[-1]:
            break
        spot0, sigma0 = spot_sigma_at(pos)
        K = round(spot0 * OTM_FRAC / 50) * 50
        prem0 = bs_put(spot0, K, TENOR_DAYS / 365.0, sigma0)
        exit_pos = pos_on_or_before(exp_date)
        spot_exit, _ = spot_sigma_at(exit_pos)
        payoff = max(K - spot_exit, 0.0)
        hedge_pnl_pts = (payoff - (prem0 or 0)) - LEG_COST_RT
        hedge_pnl_rs = hedge_pnl_pts * LOT_SIZE * lots
        cash += hedge_pnl_rs
        cash, lots, n_traded, ttype = rebalance(cash, lots, spot_exit)
        total_val = lots * LOT_SIZE * spot_exit + cash
        log_rows.append(dict(entry_date=entry_date, exit_date=trading_days.iloc[exit_pos],
                              spot_entry=spot0, spot_exit=spot_exit, lots_hedged=lots,
                              hedge_pnl_rs=hedge_pnl_rs, cash=cash, lots_after=lots,
                              rebal_trade=ttype, rebal_n=n_traded, total_value=total_val))
        pos = pos_on_or_after(exp_date + pd.Timedelta(days=1))
    return pd.DataFrame(log_rows)


def run_sigma3_monthend():
    start_pos = pos_on_or_after(START_DATE)
    p0 = raw["close"].iloc[start_pos]
    cash = CASH_TARGET_FRAC / (1 - CASH_TARGET_FRAC) * START_LOTS * LOT_SIZE * p0
    lots = START_LOTS
    log_rows = []
    pos = start_pos
    cooldown_until = None
    while pos < len(raw) - 1:
        entry_date = trading_days.iloc[pos]
        if cooldown_until is not None and entry_date < cooldown_until:
            pos = pos_on_or_after(cooldown_until)
            continue
        exp_date = entry_date + pd.Timedelta(days=TENOR_DAYS)
        if exp_date > trading_days.iloc[-1]:
            break
        spot0, sigma0 = spot_sigma_at(pos)
        K = round(spot0 * OTM_FRAC / 50) * 50
        prem0 = bs_put(spot0, K, TENOR_DAYS / 365.0, sigma0)
        # month-end-only monitoring (NOT daily) between entry and expiry
        me_dates = month_end_dates[(month_end_dates > entry_date) & (month_end_dates < exp_date)]
        trigger_pos = None
        trigger_z = None
        for me_d in me_dates:
            me_pos = pos_on_or_before(me_d)
            spot_me, _ = spot_sigma_at(me_pos)
            t_elapsed = me_pos - pos
            z = (spot_me / spot0 - 1) / (sigma0 / np.sqrt(252) * np.sqrt(max(t_elapsed, 1)))
            if z <= -3.0:
                trigger_pos, trigger_z = me_pos, z
                break
        if trigger_pos is not None:
            spot_t, sigma_t = spot_sigma_at(trigger_pos)
            t_rem = (exp_date - trading_days.iloc[trigger_pos]).days / 365.0
            price_t = bs_put(spot_t, K, t_rem, sigma_t)
            hedge_pnl_pts = ((price_t or 0) - (prem0 or 0)) - LEG_COST_RT
            exit_pos_used = trigger_pos
            exit_type = "sigma3_monthend"
            cooldown_until = trading_days.iloc[trigger_pos] + pd.DateOffset(months=COOLDOWN_MONTHS)
        else:
            exit_pos_used = pos_on_or_before(exp_date)
            spot_exit, _ = spot_sigma_at(exit_pos_used)
            payoff = max(K - spot_exit, 0.0)
            hedge_pnl_pts = (payoff - (prem0 or 0)) - LEG_COST_RT
            exit_type = "expiry_intrinsic"
            cooldown_until = None
        spot_exit_val, _ = spot_sigma_at(exit_pos_used)
        hedge_pnl_rs = hedge_pnl_pts * LOT_SIZE * lots
        cash += hedge_pnl_rs
        cash, lots, n_traded, ttype = rebalance(cash, lots, spot_exit_val)
        total_val = lots * LOT_SIZE * spot_exit_val + cash
        log_rows.append(dict(entry_date=entry_date, exit_date=trading_days.iloc[exit_pos_used],
                              spot_entry=spot0, spot_exit=spot_exit_val, lots_hedged=lots,
                              hedge_pnl_rs=hedge_pnl_rs, cash=cash, lots_after=lots,
                              rebal_trade=ttype, rebal_n=n_traded, total_value=total_val,
                              exit_type=exit_type, trigger_z=trigger_z,
                              cooldown_until=cooldown_until))
        nxt = cooldown_until if cooldown_until is not None else trading_days.iloc[exit_pos_used] + pd.Timedelta(days=1)
        pos = pos_on_or_after(nxt)
    return pd.DataFrame(log_rows)


log("running PASSIVE (100 lots, 6M hold, buy/sell-lots rebalance)...")
passive = run_passive()
passive.to_csv(f"{OUT}\\checkpoints\\rebalance_passive.csv", index=False)
p_final = passive.iloc[-1]
p_first_spot = passive.iloc[0]["spot_entry"]
bh_lots_value = START_LOTS * LOT_SIZE * passive.iloc[-1]["spot_exit"]
log(f"  -> {len(passive)} cycles, {passive['entry_date'].min().date()}..{passive['exit_date'].max().date()}")
log(f"  -> final: lots={p_final['lots_after']:.0f} cash={p_final['cash']:,.0f} "
    f"total={p_final['total_value']:,.0f}")
log(f"  -> buy-and-hold-100-lots-no-hedge comparison value: {bh_lots_value:,.0f}")

log("running SIGMA3_MONTHEND (month-end-only monitoring, 2-month cooldown after monetizing)...")
sig = run_sigma3_monthend()
sig.to_csv(f"{OUT}\\checkpoints\\rebalance_sigma3_monthend.csv", index=False)
s_final = sig.iloc[-1]
log(f"  -> {len(sig)} cycles, {sig['entry_date'].min().date()}..{sig['exit_date'].max().date()}")
log(f"  -> final: lots={s_final['lots_after']:.0f} cash={s_final['cash']:,.0f} "
    f"total={s_final['total_value']:,.0f}")
n_trig = (sig["exit_type"] == "sigma3_monthend").sum()
log(f"  -> monetized (month-end 3-sigma) in {n_trig}/{len(sig)} cycles")

log("DONE -- ALL FIGURES MODELED (Black-Scholes off realized vol), NOT REAL OPTION PRICES")
