"""DIMENSION 5 -- cumulative-delta / order-flow PROXIES reconstructed from 1-min spot OHLC.
STATED EXPLICITLY: these are PROXIES, not real order flow (no bid/ask, no trade-by-trade tape).
Two proxies, both computed PER DAY (reset each session, no lookahead):
  tick_delta(t)  = sign(close_t - close_{t-1})              -- a tick-rule approximation
  range_delta(t) = 2*close_t - high_t - low_t                -- close-location-in-bar, weighted
                   by that bar's own range (a bar where close prints at the high scores +range,
                   at the low scores -range; a bar with close at the midpoint scores 0)
cum_tick / cum_range = running intraday sum of each, from 09:15.
Two signal families:
  A. Z-EXTREME: rolling 60-min (min_periods 30) z-score of the cumulative series; |z|>=2 fires.
     Both REJECT (fade the pressure -- bet on exhaustion/reversion) and CONTINUE (ride the
     pressure) tested, one trigger per day per proxy per side (first of the day).
  B. DIVERGENCE: bar sets a new INTRADAY high in price but cum_range fails to also set a new
     intraday high (bearish divergence -> short) / mirror at intraday lows (bullish -> long).
     One trigger per day per type (first of the day).
Entries at next 1-min bar's open; exits via pathsafe ATR-scaled stop/target (same tight_atr/
wide_atr configs as every other dimension, same cost model).
"""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
LIB = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib"
PL = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
sys.path.insert(0, LIB)
sys.path.insert(0, PL)
from pathsafe import simulate_exit  # noqa: E402
from touch_engine import EXIT_CFGS, BREAK_CONFIRM_K, build_day_arrays, add_costs  # noqa: E402

Z_WIN = 60
Z_MIN = 30
Z_THRESH = 2.0


def rolling_z(x: np.ndarray, win: int, minp: int) -> np.ndarray:
    n = len(x)
    z = np.full(n, np.nan)
    s = pd.Series(x)
    m = s.rolling(win, min_periods=minp).mean().to_numpy()
    sd = s.rolling(win, min_periods=minp).std().to_numpy()
    valid = sd > 1e-9
    z[valid] = (x[valid] - m[valid]) / sd[valid]
    return z


def emit_trade(rows, base, day, i, direction, atr):
    h, l, o, c = day["h"], day["l"], day["o"], day["c"]
    n = len(h)
    ei = i + 1
    if ei >= n:
        return
    entry_price = o[ei]
    exit_bars = pd.DataFrame({"high": h[ei:], "low": l[ei:], "close": c[ei:]})
    if len(exit_bars) < 3:
        return
    for cfg_name, cfg in EXIT_CFGS.items():
        stop, target = cfg["stop_f"] * atr, cfg["target_f"] * atr
        try:
            res = simulate_exit(exit_bars, entry_price, direction, stop=stop, target=target)
        except Exception:
            continue
        rows.append(dict(**base, exit_cfg=cfg_name, direction=direction,
                          pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic,
                          is_ambiguous=res.is_ambiguous, tmin=int(day["tmin"][i])))


def main():
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()

    rows = []
    for date, day in day_arrays.items():
        atr = atr_by_date.get(date, np.nan)
        if not np.isfinite(atr) or atr <= 0:
            continue
        h, l, o, c = day["h"], day["l"], day["o"], day["c"]
        n = len(c)
        if n < 40:
            continue
        tick = np.sign(np.diff(c, prepend=c[0]))
        tick[0] = 0
        rdelta = 2 * c - h - l
        cum_tick = np.cumsum(tick)
        cum_range = np.cumsum(rdelta)

        for proxy_name, cum in [("TICK", cum_tick), ("RANGE", cum_range)]:
            z = rolling_z(cum, Z_WIN, Z_MIN)
            hit_hi = np.where(z >= Z_THRESH)[0]
            hit_lo = np.where(z <= -Z_THRESH)[0]
            for side, hits in [("HIGH_Z", hit_hi), ("LOW_Z", hit_lo)]:
                if len(hits) == 0:
                    continue
                i = hits[0]
                base_reject = dict(date=date, proxy=proxy_name, signal="ZEXTREME", side=side, hypothesis="REJECT")
                base_cont = dict(date=date, proxy=proxy_name, signal="ZEXTREME", side=side, hypothesis="CONTINUE")
                dir_reject = -1 if side == "HIGH_Z" else 1   # fade the pressure
                dir_cont = 1 if side == "HIGH_Z" else -1     # ride the pressure
                emit_trade(rows, base_reject, day, i, dir_reject, atr)
                emit_trade(rows, base_cont, day, i, dir_cont, atr)

        # ---- divergence: new intraday high in price, cum_range fails to confirm ----
        run_max_h = np.maximum.accumulate(h)
        run_max_range_excl = np.concatenate(([-np.inf], np.maximum.accumulate(cum_range)[:-1]))
        run_min_l = np.minimum.accumulate(l)
        run_min_range_excl = np.concatenate(([np.inf], np.minimum.accumulate(cum_range)[:-1]))
        new_high = h >= run_max_h
        new_low = l <= run_min_l
        div_bear = np.where(new_high & (cum_range < run_max_range_excl))[0]
        div_bull = np.where(new_low & (cum_range > run_min_range_excl))[0]
        div_bear = div_bear[div_bear >= Z_MIN]
        div_bull = div_bull[div_bull >= Z_MIN]
        if len(div_bear):
            i = div_bear[0]
            emit_trade(rows, dict(date=date, proxy="RANGE", signal="DIVERGENCE", side="BEAR_AT_HIGH",
                                   hypothesis="AS_HYPOTHESIZED"), day, i, -1, atr)
        if len(div_bull):
            i = div_bull[0]
            emit_trade(rows, dict(date=date, proxy="RANGE", signal="DIVERGENCE", side="BULL_AT_LOW",
                                   hypothesis="AS_HYPOTHESIZED"), day, i, 1, atr)

    trades = pd.DataFrame(rows)
    trades = add_costs(trades)
    trades.to_parquet(f"{OUT}/orderflow_trades.parquet")
    print("trades", trades.shape)
    print(trades.groupby(["proxy", "signal", "side", "hypothesis", "exit_cfg"])["net_pess"].agg(["count", "mean"]))


if __name__ == "__main__":
    main()
