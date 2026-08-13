"""TAIL_PUT_ROLL_20260802 -- v6: more-realistic-cost rerun (VRP-adjusted IV) + chart data export.
[ASSUMPTION, disclosed]: real IV historically trades ABOVE subsequent realized vol (variance risk
premium) -- this session's own VOL_SURFACE_20260731 established this is real and large at the
front tenor (+6.05 vol pts pre-Oct-2024). VRP is typically smaller at longer (6M) tenors; applying
a conservative +3 vol-point ADDITIVE premium to the realized-vol proxy used in v4/v5 (not the
~6pt front-tenor figure, which would overstate a 6M tenor's premium). This makes the put more
EXPENSIVE to buy (more realistic), re-run alongside a plain-NIFTY comparison and daily drawdown.
"""
import json
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
LEG_COST_RT = 1.77
START_DATE = pd.Timestamp("2015-01-01")
VRP_ADDON = 0.03   # [ASSUMPTION] +3 vol points added to realized vol as an IV proxy


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


raw = pd.read_csv(RAW)
raw.columns = [c.strip().lower() for c in raw.columns]
date_col = [c for c in raw.columns if "date" in c][0]
raw[date_col] = pd.to_datetime(raw[date_col])
raw = raw.sort_values(date_col).drop_duplicates(subset=[date_col]).reset_index(drop=True)
raw = raw.rename(columns={date_col: "date"})
raw["logret"] = np.log(raw["close"] / raw["close"].shift(1))
raw["rv50_ann"] = raw["logret"].rolling(50).std() * np.sqrt(252)
raw["iv_proxy"] = raw["rv50_ann"] + VRP_ADDON
trading_days = raw["date"]


def pos_on_or_after(d):
    return trading_days.searchsorted(d)


def pos_on_or_before(d):
    return trading_days.searchsorted(d, side="right") - 1


def bs_put(spot, K, t_years, sigma):
    if t_years <= 0 or not np.isfinite(sigma) or sigma <= 0:
        return None
    return black_scholes('p', spot, K, max(t_years, 1 / 365.0), R_FREE, sigma)


def rebalance(cash, lots, spot):
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


def run_passive(use_vrp):
    vol_col = "iv_proxy" if use_vrp else "rv50_ann"
    start_pos = pos_on_or_after(START_DATE)
    p0 = raw["close"].iloc[start_pos]
    cash = CASH_TARGET_FRAC / (1 - CASH_TARGET_FRAC) * START_LOTS * LOT_SIZE * p0
    lots = START_LOTS
    rows = []
    pos = start_pos
    while pos < len(raw) - 1:
        entry_date = trading_days.iloc[pos]
        exp_date = entry_date + pd.Timedelta(days=TENOR_DAYS)
        if exp_date > trading_days.iloc[-1]:
            break
        spot0 = raw["close"].iloc[pos]
        sigma0 = raw[vol_col].iloc[pos]
        K = round(spot0 * OTM_FRAC / 50) * 50
        prem0 = bs_put(spot0, K, TENOR_DAYS / 365.0, sigma0) or 0
        exit_pos = pos_on_or_before(exp_date)
        spot_exit = raw["close"].iloc[exit_pos]
        payoff = max(K - spot_exit, 0.0)
        hedge_pnl_rs = ((payoff - prem0) - LEG_COST_RT) * LOT_SIZE * lots
        cash += hedge_pnl_rs
        cash, lots, n_traded, ttype = rebalance(cash, lots, spot_exit)
        total_val = lots * LOT_SIZE * spot_exit + cash
        rows.append(dict(entry_date=entry_date, exit_date=trading_days.iloc[exit_pos],
                          spot_exit=spot_exit, lots_after=lots, cash=cash,
                          total_value=total_val, rebal_trade=ttype, rebal_n=n_traded,
                          prem0=prem0, sigma0=sigma0))
        pos = pos_on_or_after(exp_date + pd.Timedelta(days=1))
    return pd.DataFrame(rows)


log("re-running PASSIVE with VRP-adjusted (more realistic) IV proxy...")
passive_vrp = run_passive(use_vrp=True)
passive_vrp.to_csv(f"{OUT}\\checkpoints\\rebalance_passive_VRP.csv", index=False)
n_years = (passive_vrp["exit_date"].max() - passive_vrp["entry_date"].min()).days / 365.25
cagr = (passive_vrp["total_value"].iloc[-1] / passive_vrp["total_value"].iloc[0]) ** (1 / n_years) - 1
log(f"  -> {len(passive_vrp)} cycles, final={passive_vrp['total_value'].iloc[-1]:,.0f}, CAGR={cagr:.2%}")
log(f"  -> avg premium paid, RV-only vs +3vol VRP-adjusted: "
    f"{run_passive(False)['prem0'].mean():.1f} vs {passive_vrp['prem0'].mean():.1f} pts")

# ---- daily equity curves for charting: hedged (passive, RV-only + VRP) vs plain NIFTY ----
log("building daily comparison series (plain NIFTY vs hedged, both cost bases)...")


def daily_curve_from_cycles(cycle_df, start_pos):
    """Between cycle boundaries, lots/cash are constant (no interim MTM of the option leg --
    same simplification as the summary tables); value = lots*LOT_SIZE*spot + cash each day."""
    daily = raw.iloc[start_pos:].copy()
    lots_series = pd.Series(index=daily.index, dtype=float)
    cash_series = pd.Series(index=daily.index, dtype=float)
    lots, cash = START_LOTS, cycle_df.iloc[0]["cash"] if len(cycle_df) else 0
    # initial cash before first cycle settles
    p0 = raw["close"].iloc[start_pos]
    cash = CASH_TARGET_FRAC / (1 - CASH_TARGET_FRAC) * START_LOTS * LOT_SIZE * p0
    ci = 0
    for idx in daily.index:
        d = raw["date"].iloc[idx]
        while ci < len(cycle_df) and d > cycle_df.iloc[ci]["exit_date"]:
            lots = cycle_df.iloc[ci]["lots_after"]
            cash = cycle_df.iloc[ci]["cash"]
            ci += 1
        lots_series.loc[idx] = lots
        cash_series.loc[idx] = cash
    daily["lots"] = lots_series
    daily["cash"] = cash_series
    daily["hedged_value"] = daily["lots"] * LOT_SIZE * daily["close"] + daily["cash"]
    return daily[["date", "close", "hedged_value"]]


start_pos = pos_on_or_after(START_DATE)
daily = daily_curve_from_cycles(passive_vrp, start_pos)
p0 = raw["close"].iloc[start_pos]
daily["plain_nifty_value"] = START_LOTS * LOT_SIZE * daily["close"] / p0 * p0  # = lots*LOT*close, no cash drag
daily["plain_nifty_value"] = START_LOTS * LOT_SIZE * daily["close"]
# plain NIFTY starts at the SAME total initial capital (equity + cash buffer), fully deployed, for fair comparison
init_total = START_LOTS * LOT_SIZE * p0 / (1 - CASH_TARGET_FRAC)
daily["plain_nifty_fullcapital"] = init_total / p0 * daily["close"]

daily["dd_hedged"] = daily["hedged_value"] / daily["hedged_value"].cummax() - 1
daily["dd_plain"] = daily["plain_nifty_fullcapital"] / daily["plain_nifty_fullcapital"].cummax() - 1

log(f"DAILY MDD -- hedged(VRP,passive): {daily['dd_hedged'].min():.1%} on "
    f"{daily.loc[daily['dd_hedged'].idxmin(),'date'].date()}")
log(f"DAILY MDD -- plain NIFTY (same capital): {daily['dd_plain'].min():.1%} on "
    f"{daily.loc[daily['dd_plain'].idxmin(),'date'].date()}")

# downsample to ~monthly for a manageable chart payload
ds = daily.iloc[::20].copy()
chart_data = dict(
    dates=ds["date"].dt.strftime("%Y-%m").tolist(),
    hedged=ds["hedged_value"].round(0).tolist(),
    plain=ds["plain_nifty_fullcapital"].round(0).tolist(),
    dd_hedged=(ds["dd_hedged"] * 100).round(2).tolist(),
    dd_plain=(ds["dd_plain"] * 100).round(2).tolist(),
)
with open(f"{OUT}\\checkpoints\\equity_dd_chart_data.json", "w") as f:
    json.dump(chart_data, f)
log(f"saved downsampled chart data ({len(ds)} points)")
log("DONE")
