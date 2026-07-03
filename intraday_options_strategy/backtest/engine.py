"""Event-driven intraday options backtest engine.

Execution model (spec S7):
  - signal on bar t close → enter at bar t+1 OPEN (same day, before 15:20)
  - synthetic option premium via Black-Scholes; IV = 1-min India VIX at the
    signal bar's close (known before entry), sigma = VIX/100
  - SL/target tested on each subsequent bar via BS premium at the bar's
    underlying low/high (premium is monotonic in S); both hit in one bar → SL
  - hard close: exit at BS premium of the 15:20 bar close
  - one open position per (signal id, direction); CE and PE may coexist
  - per-day trade cap, Kelly×0.25 sizing, ₹50L open-delta-notional cap
  - timestamps are bar STARTS; bar t's close occurs at t+1 min (used for T)

P&L bookkeeping:
  fills embed slippage (buy at mid×(1+s), sell at mid×(1−s))
  gross_pnl = (exit_mid − entry_mid) × units      (pre-cost, pre-slippage)
  net_pnl   = (exit_fill − entry_fill) × units − explicit charges
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    DIVIDEND_YIELD, HARD_CLOSE, LOT_SIZE, MAX_OPEN_DELTA_NOTIONAL,
    RISK_FREE_RATE, SLIPPAGE_PCT, StrategyParams, TOTAL_CAPITAL,
)
from backtest.costs import trade_costs  # noqa: E402
from backtest.position_sizer import KellySizer  # noqa: E402
from options.bs_pricing import bs_greeks, bs_price  # noqa: E402
from options.option_selector import ExpiryCalendar, nearest_strike  # noqa: E402

MIN_ENTRY_PREMIUM = 5.0          # skip absurdly cheap synthetic premia
MIN_PER_YEAR = 365.0 * 24 * 60


@dataclass
class EngineConfig:
    params: StrategyParams
    capital0: float = TOTAL_CAPITAL
    slippage_pct: float = SLIPPAGE_PCT
    cost_mult: float = 1.0       # robustness: scale explicit charges


def run_backtest(nifty: pd.DataFrame, vix_on_bars: pd.Series,
                 events: pd.DataFrame, cfg: EngineConfig,
                 ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (trades, daily) DataFrames. `vix_on_bars` must be aligned to
    nifty.index (same-minute close, ffilled — known at each bar's close)."""
    p = cfg.params
    hc_h, hc_m = map(int, HARD_CLOSE.split(":"))
    hard_close_t = dtime(hc_h, hc_m)

    idx = nifty.index
    days = idx.normalize()
    unique_days = pd.DatetimeIndex(days.unique())
    cal = ExpiryCalendar(unique_days)
    sizer = KellySizer(unique_days)

    o = nifty["open"].to_numpy()
    h = nifty["high"].to_numpy()
    lo = nifty["low"].to_numpy()
    c = nifty["close"].to_numpy()
    sig_arr = vix_on_bars.to_numpy() / 100.0
    ts_ns = idx.as_unit("ns").asi8  # force ns: parquet indexes are often [us]

    day_start = np.searchsorted(days.asi8, unique_days.asi8, side="left")
    day_end = np.append(day_start[1:], len(idx))
    day_pos = {d: k for k, d in enumerate(unique_days)}

    ev = events.sort_values("dt").reset_index(drop=True)
    ev_day = ev["dt"].dt.normalize()

    trades: list[dict] = []
    capital = cfg.capital0

    for d, ev_idx in ev.groupby(ev_day).groups.items():
        k = day_pos.get(d)
        if k is None:
            continue
        s0, s1 = day_start[k], day_end[k]
        bar_times = idx[s0:s1]
        # walk window ends at the hard-close bar (inclusive)
        wt = bar_times.time
        hc_mask = wt <= hard_close_t
        last_walk = s0 + int(np.nonzero(hc_mask)[0][-1])  # global idx of 15:20 bar

        expiry = cal.next_expiry(d)
        expiry_ns = (expiry + pd.Timedelta("15:30:00")).value
        dte_days = (expiry - d).days

        open_until: dict[tuple[str, int], int] = {}   # (sid,dir) -> exit ts_ns
        open_deltas: list[tuple[int, float]] = []     # (exit ts_ns, delta notional)
        n_today = 0
        day_trades_start = len(trades)

        for ei in ev_idx:
            if n_today >= p.max_trades_per_day:
                break
            row = ev.loc[ei]
            dt_ns = row["dt"].value
            i = s0 + int(np.searchsorted(ts_ns[s0:s1], dt_ns))
            if i >= s1 or ts_ns[i] != dt_ns:
                continue
            j = i + 1                                   # entry bar
            if j > last_walk or idx[j].time() >= hard_close_t:
                continue
            key = (row["signal"], int(row["direction"]))
            if key in open_until and dt_ns < open_until[key]:
                continue

            is_call = row["direction"] == 1
            s_entry = o[j]
            strike = float(nearest_strike(s_entry))
            sigma = sig_arr[i]
            entry_close_ns = ts_ns[j] + 60_000_000_000  # bar j close moment
            t_entry = max((expiry_ns - entry_close_ns) / 1e9 / 60, 1.0) / MIN_PER_YEAR
            entry_mid = float(bs_price(s_entry, strike, t_entry, sigma,
                                       RISK_FREE_RATE, DIVIDEND_YIELD, is_call))
            if entry_mid < MIN_ENTRY_PREMIUM:
                continue
            entry_fill = entry_mid * (1 + cfg.slippage_pct)

            lots = sizer.lots(d, capital, entry_fill, p.sl_pct, row["size_mult"])
            if lots == 0:
                continue
            g = bs_greeks(s_entry, strike, t_entry, sigma,
                          RISK_FREE_RATE, DIVIDEND_YIELD, is_call)
            # delta-notional cap on concurrently open positions
            open_deltas = [x for x in open_deltas if x[0] > dt_ns]
            used = sum(x[1] for x in open_deltas)
            per_lot_notional = abs(float(g["delta"])) * s_entry * LOT_SIZE
            while lots > 0 and used + lots * per_lot_notional > MAX_OPEN_DELTA_NOTIONAL:
                lots -= 1
            if lots == 0:
                continue

            sl_level = entry_fill * (1 - p.sl_pct)
            tg_level = entry_fill * (1 + p.target_pct)

            # vectorised exit walk over bars j..last_walk
            sl_ = slice(j, last_walk + 1)
            t_arr = np.maximum((expiry_ns - (ts_ns[sl_] + 60_000_000_000)) / 1e9 / 60,
                               1.0) / MIN_PER_YEAR
            sig_walk = sig_arr[sl_]  # market re-prices with live VIX bar by bar
            prem_dn = bs_price(lo[sl_] if is_call else h[sl_], strike, t_arr,
                               sig_walk, RISK_FREE_RATE, DIVIDEND_YIELD, is_call)
            prem_up = bs_price(h[sl_] if is_call else lo[sl_], strike, t_arr,
                               sig_walk, RISK_FREE_RATE, DIVIDEND_YIELD, is_call)
            sl_hits = np.nonzero(prem_dn <= sl_level)[0]
            tg_hits = np.nonzero(prem_up >= tg_level)[0]
            k_sl = sl_hits[0] if len(sl_hits) else np.inf
            k_tg = tg_hits[0] if len(tg_hits) else np.inf

            if k_sl <= k_tg and np.isfinite(k_sl):       # SL first on ties
                k_x, reason = int(k_sl), "SL"
                exit_mid = sl_level
            elif np.isfinite(k_tg):
                k_x, reason = int(k_tg), "TARGET"
                exit_mid = tg_level
            else:
                k_x, reason = last_walk - j, "EOD"
                exit_mid = float(bs_price(c[last_walk], strike, t_arr[-1],
                                          sig_arr[last_walk],
                                          RISK_FREE_RATE, DIVIDEND_YIELD, is_call))
            exit_fill = exit_mid * (1 - cfg.slippage_pct)
            exit_ns = ts_ns[j + k_x] + 60_000_000_000
            units = LOT_SIZE * lots

            costs = trade_costs(entry_fill, exit_fill, lots, entry_mid, exit_mid)
            explicit = costs.explicit_total * cfg.cost_mult
            gross = (exit_mid - entry_mid) * units
            net = (exit_fill - entry_fill) * units - explicit

            capital += net
            sizer.record(d, net)
            open_until[key] = exit_ns
            open_deltas.append((exit_ns, lots * per_lot_notional))
            n_today += 1

            trades.append({
                "entry_dt": idx[j], "exit_dt": pd.Timestamp(exit_ns),
                "signal": row["signal"], "direction": int(row["direction"]),
                "option": "CE" if is_call else "PE", "strike": strike,
                "expiry": expiry, "dte": dte_days, "score": int(row["score"]),
                "spot_entry": float(s_entry), "sigma": float(sigma),
                "entry_mid": entry_mid, "entry_fill": entry_fill,
                "exit_mid": exit_mid, "exit_fill": exit_fill,
                "lots": lots, "units": units,
                "delta": float(g["delta"]), "gamma": float(g["gamma"]),
                "theta_day": float(g["theta"]), "vega": float(g["vega"]),
                "sl_level": sl_level, "tg_level": tg_level, "reason": reason,
                "hold_min": (exit_ns - ts_ns[j]) / 60e9,
                "gross_pnl": gross, "costs": explicit,
                "slippage_cost": costs.slippage, "net_pnl": net,
                "kelly_f": sizer.last_f, "capital_after": capital,
            })

    tr = pd.DataFrame(trades)
    daily = _daily_frame(tr, unique_days, cfg.capital0)
    return tr, daily


def _daily_frame(tr: pd.DataFrame, unique_days: pd.DatetimeIndex,
                 capital0: float) -> pd.DataFrame:
    out = pd.DataFrame(index=unique_days)
    if len(tr):
        by = tr.groupby(tr["entry_dt"].dt.normalize())
        out["Daily_PnL"] = by["net_pnl"].sum()
        out["Daily_Trades"] = by.size()
        out["Win_Trades"] = by.apply(lambda x: int((x["net_pnl"] > 0).sum()),
                                     include_groups=False)
        out["Gross_PnL"] = by["gross_pnl"].sum()
    else:
        out["Daily_PnL"] = 0.0
        out["Daily_Trades"] = 0
        out["Win_Trades"] = 0
        out["Gross_PnL"] = 0.0
    out = out.fillna(0.0)
    out["Loss_Trades"] = out["Daily_Trades"] - out["Win_Trades"]
    out["Cumulative_PnL"] = out["Daily_PnL"].cumsum()
    out["Running_Capital"] = capital0 + out["Cumulative_PnL"]
    out["Net_PnL_after_costs"] = out["Daily_PnL"]
    out.index.name = "Date"
    return out[["Daily_PnL", "Cumulative_PnL", "Running_Capital", "Daily_Trades",
                "Win_Trades", "Loss_Trades", "Gross_PnL", "Net_PnL_after_costs"]]
