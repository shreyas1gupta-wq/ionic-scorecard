"""Directional option-BUYING backtest engine for NIFTY weekly options.

Edge premise (honest): buying options fights theta + costs + the vol-risk-premium.
It only works if a directional/timing signal catches moves big enough to overcome
that drag, with fast loss-cutting. So: momentum breakout + trend gate -> buy ATM/ITM
CE or PE (optionally as a debit spread to cut cost/theta), cut losers fast, trail
winners, square off intraday (no overnight theta/gap bleed by default).

Fills use REAL 1-min option OHLC from the chain. Exits evaluated on 1-min CLOSE
(conservative for a retail market-order fill), plus a hard EOD square-off.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import chain

STEP = 50

# ---- costs (retail, Angel-One-like; option buying) ---------------------------
BROKERAGE_PER_ORDER = 20.0        # flat per order
STT_SELL_PCT = 0.0625 / 100       # STT on SELL-side premium (options)
EXCH_TXN_PCT = 0.0495 / 100       # NSE txn charge on premium turnover (approx 2025)
GST_PCT = 0.18                    # on (brokerage + exch txn)
SEBI_PER_CRORE = 10.0
STAMP_BUY_PCT = 0.003 / 100       # stamp duty on buy


# -----------------------------------------------------------------------------
@dataclass
class Config:
    # signal
    orb_min: int = 15                 # opening-range window (minutes)
    entry_from: str = "09:30"         # earliest entry
    entry_to: str = "14:00"           # latest new entry (leave room before EOD)
    breakout_buf: float = 0.0005      # break OR by this fraction of price
    atr_min_mult: float = 0.0         # require break >= atr_min_mult * ATR beyond OR
    ema_fast: int = 9
    ema_slow: int = 21
    require_twap: bool = True         # price on correct side of session TWAP
    # instrument
    min_dte: int = 1
    max_dte: int = 4
    strike_offset: int = 0            # 0=ATM; -1 => 1 strike ITM (dir-adjusted)
    spread_width: int = 0             # 0=single long; >0 => sell leg N strikes OTM
    # exits (on premium of the position, net for spreads)
    target_pct: float = 0.50
    stop_pct: float = 0.30
    trail_pct: float = 0.0            # 0=off; else trail from peak
    time_stop_min: int = 90           # exit if held this long w/o target
    eod_exit: str = "15:15"
    # portfolio / risk
    max_trades_per_day: int = 3
    cooldown_min: int = 20            # min gap between entries
    slippage_pct: float = 0.005       # per leg (weekly ATM retail ~0.5%)
    capital: float = 3_00_000.0
    risk_per_trade: float = 0.02      # fraction of capital as premium outlay/trade
    lot_size: int = 75


# ---- indicators (lookback-only) ---------------------------------------------
def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]).abs(),
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def _hhmm(day: dt.date, hhmm: str) -> pd.Timestamp:
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


# ---- signals -----------------------------------------------------------------
def day_signals(spot: pd.DataFrame, day: dt.date, cfg: Config) -> list[dict]:
    """Return list of {t, direction} entry signals for the day (ORB + trend)."""
    d = spot[spot.index.date == day].copy()
    if len(d) < 60:
        return []
    or_end = _hhmm(day, "09:15") + pd.Timedelta(minutes=cfg.orb_min)
    orng = d[d.index < or_end]
    if orng.empty:
        return []
    or_hi, or_lo = orng["high"].max(), orng["low"].min()

    d["ema_f"] = _ema(d["close"], cfg.ema_fast)
    d["ema_s"] = _ema(d["close"], cfg.ema_slow)
    d["atr"] = _atr(d, 14)
    d["twap"] = d["close"].expanding().mean()

    lo_t, hi_t = _hhmm(day, cfg.entry_from), _hhmm(day, cfg.entry_to)
    win = d[(d.index >= max(or_end, lo_t)) & (d.index <= hi_t)]

    sigs: list[dict] = []
    last_t = None
    for t, row in win.iterrows():
        if last_t is not None and (t - last_t) < pd.Timedelta(minutes=cfg.cooldown_min):
            continue
        px, atr = row["close"], row["atr"]
        up_lvl = or_hi * (1 + cfg.breakout_buf) + cfg.atr_min_mult * atr
        dn_lvl = or_lo * (1 - cfg.breakout_buf) - cfg.atr_min_mult * atr
        long_ok = px > up_lvl and row["ema_f"] > row["ema_s"] and \
            (not cfg.require_twap or px > row["twap"])
        short_ok = px < dn_lvl and row["ema_f"] < row["ema_s"] and \
            (not cfg.require_twap or px < row["twap"])
        if long_ok:
            sigs.append({"t": t, "direction": 1}); last_t = t
        elif short_ok:
            sigs.append({"t": t, "direction": -1}); last_t = t
        if len(sigs) >= cfg.max_trades_per_day:
            break
    return sigs


# ---- option pick + fill ------------------------------------------------------
def _atm(spot: float) -> int:
    return int(round(spot / STEP) * STEP)


def _leg_ohlc(cdf: pd.DataFrame, strike: int, otype: str) -> pd.DataFrame:
    s = cdf[(cdf["strike"] == strike) & (cdf["option_type"] == otype)]
    return s.set_index("t")[["open", "high", "low", "close"]].sort_index()


def _costs(entry_prem: float, exit_prem: float, lots: int, lot_size: int,
           has_short: bool) -> float:
    """Round-trip costs in rupees for the whole position (per `lots`)."""
    qty = lots * lot_size
    n_orders = 2 * (2 if has_short else 1)     # legs * (entry+exit)
    brok = BROKERAGE_PER_ORDER * n_orders
    turnover = (entry_prem + exit_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    # STT: on sell-side premium. Long leg sold at exit; short leg sold at entry.
    stt = STT_SELL_PCT * (exit_prem * qty)
    if has_short:
        stt += STT_SELL_PCT * (entry_prem * qty)  # approx: short leg sold at entry
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (entry_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


def simulate_trade(cdf: pd.DataFrame, sig: dict, spot_at: float, day: dt.date,
                   exp: dt.date, cfg: Config) -> dict | None:
    direction = sig["direction"]
    otype = "CE" if direction == 1 else "PE"
    avail = sorted(cdf["strike"].unique())
    if not avail:
        return None
    atmk = _atm(spot_at)
    # strike_offset: negative => ITM. For CE ITM = lower strike; PE ITM = higher.
    k = atmk - cfg.strike_offset * STEP * direction
    k = min(avail, key=lambda x: abs(x - k))
    long_leg = _leg_ohlc(cdf, k, otype)
    if long_leg.empty:
        return None

    # entry at next bar after signal
    after = long_leg[long_leg.index > sig["t"]]
    if after.empty:
        return None
    entry_bar = after.index[0]
    long_entry = after.iloc[0]["open"]
    if not np.isfinite(long_entry) or long_entry <= 0:
        return None

    # optional short leg (debit spread) OTM by spread_width strikes
    has_short = cfg.spread_width > 0
    short_leg = None
    short_entry = 0.0
    if has_short:
        sk = k + cfg.spread_width * STEP * direction
        sk = min(avail, key=lambda x: abs(x - sk))
        short_leg = _leg_ohlc(cdf, sk, otype)
        if short_leg.empty:
            has_short = False
        else:
            sa = short_leg[short_leg.index >= entry_bar]
            if sa.empty:
                has_short = False
            else:
                short_entry = sa.iloc[0]["open"]

    # net premium path (position value); for spread = long - short
    def net_series() -> pd.Series:
        lc = long_leg["close"]
        if has_short:
            sc = short_leg["close"].reindex(lc.index).ffill()
            return (lc - sc)
        return lc

    net = net_series()
    net = net[net.index >= entry_bar]
    entry_debit = long_entry - short_entry
    if entry_debit <= 0:
        return None

    # entry fill with slippage (buy long +slip; sell short -slip)
    fill_debit = long_entry * (1 + cfg.slippage_pct) - \
        (short_entry * (1 - cfg.slippage_pct) if has_short else 0.0)

    eod_t = _hhmm(day, cfg.eod_exit)
    tgt = entry_debit * (1 + cfg.target_pct)
    stp = entry_debit * (1 - cfg.stop_pct)

    peak = entry_debit
    exit_t, exit_val, reason = None, None, None
    for t, val in net.items():
        if t <= entry_bar:
            continue
        if t >= eod_t:
            exit_t, exit_val, reason = t, val, "eod"; break
        if val >= tgt:
            exit_t, exit_val, reason = t, val, "target"; break
        if val <= stp:
            exit_t, exit_val, reason = t, val, "stop"; break
        if cfg.trail_pct > 0:
            peak = max(peak, val)
            if peak > entry_debit and val <= peak * (1 - cfg.trail_pct):
                exit_t, exit_val, reason = t, val, "trail"; break
        if (t - entry_bar) >= pd.Timedelta(minutes=cfg.time_stop_min):
            exit_t, exit_val, reason = t, val, "time"; break
    if exit_t is None:
        exit_t, exit_val, reason = net.index[-1], net.iloc[-1], "eod"

    # exit fill with slippage (sell long -slip; buy back short +slip)
    # approximate on net using half-slip each side
    fill_exit = exit_val * (1 - cfg.slippage_pct) if not has_short else \
        exit_val - cfg.slippage_pct * (long_leg["close"].reindex([exit_t]).iloc[0]
                                       if exit_t in long_leg.index else exit_val)

    # sizing: premium outlay ~ risk_per_trade * capital
    outlay_per_lot = fill_debit * cfg.lot_size
    lots = max(1, int((cfg.risk_per_trade * cfg.capital) // max(outlay_per_lot, 1)))
    qty = lots * cfg.lot_size

    gross = (fill_exit - fill_debit) * qty
    costs = _costs(fill_debit, max(fill_exit, 0.0), lots, cfg.lot_size, has_short)
    net_pnl = gross - costs

    return {
        "day": day, "exp": exp, "dte": (exp - day).days, "dir": direction,
        "otype": otype, "strike": k, "spread": has_short,
        "entry_t": entry_bar, "exit_t": exit_t, "reason": reason,
        "entry_debit": entry_debit, "fill_debit": fill_debit,
        "exit_val": exit_val, "fill_exit": fill_exit,
        "lots": lots, "qty": qty, "gross": gross, "costs": costs,
        "net_pnl": net_pnl, "ret_pct": (fill_exit / fill_debit - 1),
        "hold_min": int((exit_t - entry_bar).total_seconds() / 60),
    }


# ---- day / range runners -----------------------------------------------------
def run_day(spot: pd.DataFrame, day: dt.date, cfg: Config) -> list[dict]:
    sigs = day_signals(spot, day, cfg)
    if not sigs:
        return []
    exp = chain.nearest_expiry(day, cfg.min_dte, cfg.max_dte)
    if exp is None:
        return []
    cdf = chain.day_chain(exp, day)
    if cdf.empty:
        return []
    d_spot = spot[spot.index.date == day]
    trades = []
    for sig in sigs:
        spot_at = d_spot.asof(sig["t"])["close"]
        tr = simulate_trade(cdf, sig, spot_at, day, exp, cfg)
        if tr:
            trades.append(tr)
    return trades


def run_range(cfg: Config, start: dt.date, end: dt.date,
              progress: bool = True) -> pd.DataFrame:
    spot = chain.load_index()
    days = sorted({d for d in spot.index.date if start <= d <= end})
    all_tr = []
    for i, day in enumerate(days):
        try:
            all_tr.extend(run_day(spot, day, cfg))
        except Exception as e:
            if progress:
                print(f"  {day}: ERR {type(e).__name__}: {e}")
        if progress and i % 100 == 0:
            print(f"  ...{day} ({i}/{len(days)}) trades={len(all_tr)}")
    return pd.DataFrame(all_tr)


if __name__ == "__main__":
    cfg = Config()
    df = run_range(cfg, dt.date(2024, 1, 1), dt.date(2024, 12, 31))
    print(f"\nTRADES: {len(df)}")
    if len(df):
        wr = (df["net_pnl"] > 0).mean()
        print(f"win rate: {wr:.1%}  total net: Rs.{df['net_pnl'].sum():,.0f}  "
              f"avg/trade: Rs.{df['net_pnl'].mean():,.0f}")
        print(f"avg ret%: {df['ret_pct'].mean():+.1%}  "
              f"gross sum: Rs.{df['gross'].sum():,.0f}  costs: Rs.{df['costs'].sum():,.0f}")
        print(df["reason"].value_counts().to_dict())
