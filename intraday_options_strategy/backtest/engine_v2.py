"""Engine v2 — multi-leg uniform-side option positions with short-premium
support, combo SL/profit-take, partial profit booking and trailing stops.

Scope/conventions:
  - all legs of a position share one side: +1 (long premium) or -1 (short)
  - combo value V(S, t) = Σ_legs BS_price ≥ 0; longs profit when V rises,
    shorts profit when V falls
  - intrabar bounds via convexity of V in S: max over a bar at the bar's
    L/H endpoints; min at S = clip(K_leg, L, H) (exact for single options
    and straddles)
  - conservative intra-bar ordering: STOP first, then profit-take/partials
  - every trade is simulated PER LOT; portfolio layer scales linearly and
    adds the fixed (per-order) cost component itself
  - sigma path = live 1-min VIX (known at each bar), entry sigma = signal
    bar's VIX (known before next-bar-open entry)

Margin approximations (documented in STRATEGY_V2.md):
  short 2-leg (straddle): 9% of spot notional per lot
  short 1-leg:            6.5% of spot notional per lot
  long:                   premium outlay
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    BROKERAGE_PER_ORDER, DIVIDEND_YIELD, GST_PCT, LOT_SIZE, NSE_TXN_PCT,
    RISK_FREE_RATE, SEBI_PER_CRORE, SLIPPAGE_PCT, STT_SELL_PCT,
)
from options.bs_pricing import bs_greeks, bs_price  # noqa: E402
from options.option_selector import ExpiryCalendar, nearest_strike  # noqa: E402

MIN_PER_YEAR = 365.0 * 24 * 60
MARGIN_PCT_2LEG = 0.09
MARGIN_PCT_1LEG = 0.065
MIN_COMBO_PREMIUM = 5.0


@dataclass(frozen=True)
class ExitPolicy:
    sl: float                      # adverse move as fraction of entry combo value
    pt: float | None = None        # favourable move fraction (profit take)
    partial_at: float | None = None  # long-only: book partial_frac at +partial_at
    partial_frac: float = 0.5
    trail: float | None = None     # retrace fraction from post-partial peak
    hard_exit: str = "15:20"


@dataclass(frozen=True)
class OrderSpec:
    signal_dt: pd.Timestamp        # bar close at which decision was made
    sleeve: str
    side: int                      # +1 long premium, -1 short premium
    legs: tuple[tuple[bool, int], ...]  # (is_call, strike_offset_in_steps)
    exit: ExitPolicy
    min_dte: int = 2               # 0 → same-day expiry allowed (0DTE)
    direction_label: str = ""      # for attribution (CE/PE/STRADDLE)


@dataclass(frozen=True)
class MultiLegSpec:
    """Arbitrary mixed long/short structure (iron fly, condor, spread)."""
    signal_dt: pd.Timestamp
    sleeve: str
    legs: tuple[tuple[bool, int, int], ...]  # (is_call, strike_offset_steps, sign)
    exit: ExitPolicy               # sl/pt as FRACTION of |entry net premium|
    min_dte: int = 0
    label: str = ""


def _combo_value(s_vals: np.ndarray, strikes: np.ndarray, calls: np.ndarray,
                 t: float | np.ndarray, sigma: float | np.ndarray) -> np.ndarray:
    """V for each S in s_vals (legs summed). Broadcasts t/sigma per element."""
    v = np.zeros_like(np.asarray(s_vals, dtype=float))
    for k, c in zip(strikes, calls):
        v += bs_price(s_vals, k, t, sigma, RISK_FREE_RATE, DIVIDEND_YIELD, bool(c))
    return v


def default_iv_mult(dte_days: int) -> float:
    """IV-vs-VIX multiplier m(DTE) = real ATM IV / India VIX, TRADING-TIME.

    AUDIT-CORRECTED default: the EOD-bhavcopy fit (0.897-0.086*ln(DTE)) gave an
    OPTIMISTIC 0.96 at 0DTE, but LIVE intraday calibration at the actual 09:20
    entry (data\\angel_calibrate_live.py, 16JUN2026) measured m≈0.78-0.81. We
    default to the validated live value 0.80 (conservative, flat) rather than
    the extrapolated formula. Re-validate live m each week before trading and
    pass an explicit iv_mult to runs; this default exists only so nothing
    silently uses the optimistic 0.96. (AUDIT.md issue #1.)
    """
    return 0.80


TRADING_MIN_PER_DAY = 375          # 09:15..15:30
TRADING_MIN_PER_YEAR = 252 * TRADING_MIN_PER_DAY
CLOSE_MIN_OF_DAY = 15 * 60 + 30    # 15:30


def simulate_orders(nifty: pd.DataFrame, vix_on_bars: pd.Series,
                    orders: list[OrderSpec], iv_mult=None,
                    clock: str = "trading", slippage_pct: float | None = None,
                    stop_slip_mult: float = 2.0) -> pd.DataFrame:
    """Simulate each order independently at 1 lot. Returns trade rows.

    slippage_pct: per-leg slippage as a fraction of premium (default config
    SLIPPAGE_PCT). For 0DTE/near-expiry options use a realistic 0.5-2%.
    stop_slip_mult: SL exits are market orders into a fast move → their
    slippage is multiplied by this factor (gap-through realism).

    iv_mult: None | float | callable(dte_days)->float. Scales the IV used to
    PRICE every leg at entry and on the exit walk (entry premium, theta and
    gamma sensitivity all move together — the correct VRP mechanism). The
    realized underlying path is untouched (it's the real Nifty 1-min series).

    clock: 'trading' (default) measures time-to-expiry in TRADING minutes only
    (375/day, 252-day year) — correct for intraday options because variance
    accrues only in market hours; calendar-time understates short-DTE premiums
    by ~2x (0DTE) and is wrong for this use. 'calendar' = legacy 365x24 clock,
    kept only for comparison.
    """
    if iv_mult is None:
        iv_fn = default_iv_mult
    elif callable(iv_mult):
        iv_fn = iv_mult
    else:
        iv_fn = lambda _dte, _m=float(iv_mult): _m  # noqa: E731
    slip = SLIPPAGE_PCT if slippage_pct is None else slippage_pct
    idx = nifty.index
    days = idx.normalize()
    unique_days = pd.DatetimeIndex(days.unique())
    cal = ExpiryCalendar(unique_days)
    o = nifty["open"].to_numpy(); h = nifty["high"].to_numpy()
    lo = nifty["low"].to_numpy(); c = nifty["close"].to_numpy()
    sig = vix_on_bars.to_numpy() / 100.0
    ts = idx.as_unit("ns").asi8
    min_of_day = (idx.hour * 60 + idx.minute).to_numpy()   # bar START minute
    day_start = np.searchsorted(days.asi8, unique_days.asi8, "left")
    day_end = np.append(day_start[1:], len(idx))

    def tte_years(bar_i: int, k_bar: int, k_exp: int) -> float:
        """Year-fraction to expiry (15:30 on expiry day) from bar bar_i's CLOSE."""
        rem_today = max(CLOSE_MIN_OF_DAY - (min_of_day[bar_i] + 1), 0)
        if clock == "trading":
            mins = rem_today + TRADING_MIN_PER_DAY * (k_exp - k_bar)
            return max(mins, 1.0) / TRADING_MIN_PER_YEAR
        ns_close = ts[bar_i] + 60e9
        exp_ns = (unique_days[k_exp] + pd.Timedelta("15:30:00")).value
        return max((exp_ns - ns_close) / 1e9 / 60, 1.0) / (365.0 * 24 * 60)
    day_pos = {d: k for k, d in enumerate(unique_days)}

    rows = []
    for od in orders:
        d = od.signal_dt.normalize()
        k = day_pos.get(d)
        if k is None:
            continue
        s0, s1 = day_start[k], day_end[k]
        i = s0 + int(np.searchsorted(ts[s0:s1], od.signal_dt.value))
        if i >= s1 or ts[i] != od.signal_dt.value:
            continue
        j = i + 1
        hh, mm = map(int, od.exit.hard_exit.split(":"))
        hard_t = dtime(hh, mm)
        wt = idx[s0:s1].time
        walk_ok = np.nonzero(wt <= hard_t)[0]
        if not len(walk_ok):
            continue
        last_walk = s0 + int(walk_ok[-1])
        if j > last_walk or idx[j].time() >= hard_t:
            continue

        expiry = cal.next_expiry(d, min_dte=od.min_dte)
        if od.min_dte == 0 and expiry != d:
            continue                       # 0DTE sleeve: only true expiry days
        k_exp = day_pos.get(expiry.normalize(), k)
        dte_days = int((expiry - d).days)
        m_iv = iv_fn(dte_days)             # IV-vs-VIX multiplier for this DTE

        s_entry = o[j]
        atm = float(nearest_strike(s_entry))
        strikes = np.array([atm + off * 50 for _, off in od.legs], dtype=float)
        calls = np.array([ic for ic, _ in od.legs], dtype=bool)
        sigma0 = sig[i] * m_iv
        t0 = tte_years(j, k, k_exp)
        v0 = float(_combo_value(np.array([s_entry]), strikes, calls, t0, sigma0)[0])
        if v0 < MIN_COMBO_PREMIUM:
            continue
        # fills with slippage (long buys up / short sells down at entry)
        v0_fill = v0 * (1 + slip) if od.side == 1 else v0 * (1 - slip)

        sl_lvl = v0 * (1 - od.exit.sl) if od.side == 1 else v0 * (1 + od.exit.sl)
        pt_lvl = (v0 * (1 + od.exit.pt) if od.side == 1 else v0 * (1 - od.exit.pt)) \
            if od.exit.pt is not None else None
        par_lvl = v0 * (1 + od.exit.partial_at) \
            if (od.side == 1 and od.exit.partial_at is not None) else None

        sl_ = slice(j, last_walk + 1)
        n_b = last_walk + 1 - j
        if clock == "trading":
            rem = np.maximum(CLOSE_MIN_OF_DAY - (min_of_day[sl_] + 1), 0.0)
            t_arr = np.maximum(rem + TRADING_MIN_PER_DAY * (k_exp - k), 1.0) / TRADING_MIN_PER_YEAR
        else:
            exp_ns = (unique_days[k_exp] + pd.Timedelta("15:30:00")).value
            t_arr = np.maximum((exp_ns - (ts[sl_] + 60e9)) / 1e9 / 60, 1.0) / (365.0 * 24 * 60)
        sg = sig[sl_] * m_iv
        v_at = {}
        for name, s_arr in (("lo", lo[sl_]), ("hi", h[sl_])):
            v_at[name] = _combo_value(s_arr, strikes, calls, t_arr, sg)
        v_end = np.maximum(v_at["lo"], v_at["hi"])
        v_min_arr = np.minimum(v_at["lo"], v_at["hi"])
        for kk in strikes:                       # interior minimum candidates
            s_c = np.clip(kk, lo[sl_], h[sl_])
            v_min_arr = np.minimum(v_min_arr,
                                   _combo_value(s_c, strikes, calls, t_arr, sg))
        v_fav = v_end if od.side == 1 else v_min_arr     # favourable extreme
        v_adv = v_min_arr if od.side == 1 else v_end     # adverse extreme

        # sequential scan (partial/trailing are path-dependent)
        filled_frac = 1.0
        realized = 0.0          # premium units already banked (per unit combo)
        n_orders = 2 * len(od.legs)
        exit_reason, k_exit, exit_v = "EOD", n_b - 1, None
        peak = v0
        sl_dyn = sl_lvl
        partial_done = False
        for b in range(n_b):
            adverse_hit = (v_adv[b] <= sl_dyn) if od.side == 1 else (v_adv[b] >= sl_dyn)
            if adverse_hit:
                exit_reason = "SL" if not partial_done else "TRAIL"
                # realistic gap-through: fill at the bar's ACTUAL adverse combo
                # value, not the stop level (a fast bar trades through the stop)
                k_exit = b
                exit_v = float(v_adv[b]) if od.side == 1 else float(v_adv[b])
                break
            if pt_lvl is not None:
                pt_hit = (v_fav[b] >= pt_lvl) if od.side == 1 else (v_fav[b] <= pt_lvl)
                if pt_hit:
                    exit_reason, k_exit, exit_v = "TARGET", b, pt_lvl
                    break
            if par_lvl is not None and not partial_done and v_fav[b] >= par_lvl:
                realized += od.exit.partial_frac * (par_lvl * (1 - slip) - v0_fill)
                filled_frac -= od.exit.partial_frac
                partial_done = True
                n_orders += len(od.legs)
                sl_dyn = max(sl_dyn, v0)             # breakeven floor
                peak = par_lvl
            if partial_done and od.exit.trail is not None:
                peak = max(peak, v_fav[b])
                sl_dyn = max(sl_dyn, peak * (1 - od.exit.trail))
        if exit_v is None:                            # EOD close-out
            exit_v = float(_combo_value(np.array([c[last_walk]]), strikes, calls,
                                        t_arr[-1], sg[-1])[0])
        # SL exits are market orders into a fast move → wider slippage
        exit_slip = slip * stop_slip_mult if exit_reason in ("SL", "TRAIL") else slip
        exit_fill = exit_v * (1 - exit_slip) if od.side == 1 else exit_v * (1 + exit_slip)

        # P&L per lot (linear part) — premium diff on remaining + banked partials
        pnl_units = od.side * filled_frac * (exit_fill - v0_fill) + realized
        # linear costs: STT on sell side, NSE on both, GST on NSE, SEBI
        sell_turn = (exit_fill * filled_frac + (par_lvl or 0) * (1 - filled_frac)
                     if od.side == 1 else v0_fill) * LOT_SIZE
        buy_turn = (v0_fill if od.side == 1
                    else exit_fill * filled_frac + 0.0) * LOT_SIZE
        stt = STT_SELL_PCT * sell_turn
        nse = NSE_TXN_PCT * (sell_turn + buy_turn)
        sebi = SEBI_PER_CRORE * (sell_turn + buy_turn) / 1e7
        linear_costs = stt + nse * (1 + GST_PCT) + sebi
        fixed_cost = BROKERAGE_PER_ORDER * n_orders * (1 + GST_PCT)
        pnl_per_lot = pnl_units * LOT_SIZE - linear_costs

        g = {kname: 0.0 for kname in ("delta",)}
        for kk, cc in zip(strikes, calls):
            gg = bs_greeks(s_entry, kk, t0, sigma0, RISK_FREE_RATE,
                           DIVIDEND_YIELD, bool(cc))
            g["delta"] += float(gg["delta"])
        margin_per_lot = (v0 * LOT_SIZE if od.side == 1 else
                          (MARGIN_PCT_2LEG if len(od.legs) >= 2 else MARGIN_PCT_1LEG)
                          * s_entry * LOT_SIZE)
        max_loss_per_lot = od.exit.sl * v0 * LOT_SIZE  # to first stop

        rows.append({
            "sleeve": od.sleeve, "label": od.direction_label,
            "entry_dt": idx[j], "exit_dt": idx[j + k_exit],
            "expiry": expiry, "side": od.side, "n_legs": len(od.legs),
            "spot_entry": float(s_entry), "atm": atm, "sigma": float(sigma0),
            "v0": v0, "exit_v": float(exit_v), "reason": exit_reason,
            "partial_done": partial_done, "hold_min": float(k_exit),
            "pnl_per_lot": float(pnl_per_lot), "fixed_cost": float(fixed_cost),
            "margin_per_lot": float(margin_per_lot),
            "max_loss_per_lot": float(max_loss_per_lot),
            "net_delta": g["delta"],
        })
    return pd.DataFrame(rows)


FUT_SLIP_PTS = 0.5     # Nifty futures are very liquid; ~0.5 index pt/leg


def simulate_delta_hedged(nifty: pd.DataFrame, vix_on_bars: pd.Series,
                          orders: list[OrderSpec], iv_mult=None,
                          slippage_pct: float | None = None,
                          hedge_band: float = 0.15, clock: str = "trading"
                          ) -> pd.DataFrame:
    """0DTE short straddle run DELTA-HEDGED with Nifty futures (~1-min index).

    Each bar: option net delta (BS) is offset by a futures position; rebalanced
    when residual delta exceeds hedge_band (in delta units). Hedge P&L =
    futures_held * spot change; hedge cost = traded-delta*lot*FUT_SLIP_PTS +
    brokerage per rebalance. Held to hard_exit (no premium stop — the hedge
    bounds directional risk). Reports per-lot P&L of (straddle + hedge - costs).
    """
    iv_fn = (default_iv_mult if iv_mult is None else
             iv_mult if callable(iv_mult) else (lambda _d, _m=float(iv_mult): _m))
    slip = SLIPPAGE_PCT if slippage_pct is None else slippage_pct
    idx = nifty.index
    days = idx.normalize()
    unique_days = pd.DatetimeIndex(days.unique())
    cal = ExpiryCalendar(unique_days)
    o, h, lo, c = (nifty[x].to_numpy() for x in ("open", "high", "low", "close"))
    sig = vix_on_bars.to_numpy() / 100.0
    ts = idx.as_unit("ns").asi8
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day_start = np.searchsorted(days.asi8, unique_days.asi8, "left")
    day_end = np.append(day_start[1:], len(idx))
    day_pos = {d: k for k, d in enumerate(unique_days)}

    rows = []
    for od in orders:
        d = od.signal_dt.normalize(); k = day_pos.get(d)
        if k is None:
            continue
        s0, s1 = day_start[k], day_end[k]
        i = s0 + int(np.searchsorted(ts[s0:s1], od.signal_dt.value))
        if i >= s1 or ts[i] != od.signal_dt.value:
            continue
        j = i + 1
        hh, mm = map(int, od.exit.hard_exit.split(":")); hard = dtime(hh, mm)
        walk_ok = np.nonzero(idx[s0:s1].time <= hard)[0]
        if not len(walk_ok):
            continue
        last_walk = s0 + int(walk_ok[-1])
        if j > last_walk or idx[j].time() >= hard:
            continue
        expiry = cal.next_expiry(d, min_dte=od.min_dte)
        if od.min_dte == 0 and expiry != d:
            continue
        k_exp = day_pos.get(expiry.normalize(), k)
        m_iv = iv_fn(int((expiry - d).days))
        s_entry = o[j]; atm = float(nearest_strike(s_entry)); sigma0 = sig[i] * m_iv

        def tte(bi):
            rem = max(CLOSE_MIN_OF_DAY - (mod[bi] + 1), 0.0)
            if clock == "trading":
                return max(rem + TRADING_MIN_PER_DAY * (k_exp - k), 1.0) / TRADING_MIN_PER_YEAR
            exp_ns = (unique_days[k_exp] + pd.Timedelta("15:30:00")).value
            return max((exp_ns - (ts[bi] + 60e9)) / 1e9 / 60, 1.0) / (365.0 * 24 * 60)

        t0 = tte(j)
        prem0 = float(bs_price(s_entry, atm, t0, sigma0, RISK_FREE_RATE, DIVIDEND_YIELD, True)
                      + bs_price(s_entry, atm, t0, sigma0, RISK_FREE_RATE, DIVIDEND_YIELD, False))
        if prem0 < MIN_COMBO_PREMIUM:
            continue
        prem0_fill = prem0 * (1 - slip)                 # short → sell down

        hedge = 0.0          # futures position in index units (per 1 straddle unit)
        hedge_pnl = 0.0
        hedge_cost = 0.0
        n_reb = 1            # initial hedge + final unwind counted below
        prev_s = s_entry
        for b in range(j, last_walk + 1):
            sb = c[b]; tb = tte(b); sgb = sig[b] * m_iv
            hedge_pnl += hedge * (sb - prev_s)          # carry over last bar
            prev_s = sb
            dC = float(bs_greeks(sb, atm, tb, sgb, RISK_FREE_RATE, DIVIDEND_YIELD, True)["delta"])
            dP = float(bs_greeks(sb, atm, tb, sgb, RISK_FREE_RATE, DIVIDEND_YIELD, False)["delta"])
            target = dC + dP                            # = -(short straddle delta)
            if abs(target - hedge) > hedge_band:
                hedge_cost += abs(target - hedge) * FUT_SLIP_PTS
                n_reb += 1
                hedge = target
        # flatten the residual futures hedge at exit (slippage + 1 brokerage order)
        if abs(hedge) > 1e-9:
            hedge_cost += abs(hedge) * FUT_SLIP_PTS
            n_reb += 1
            hedge = 0.0
        # close straddle at exit bar
        premX = float(bs_price(c[last_walk], atm, tte(last_walk), sig[last_walk] * m_iv,
                      RISK_FREE_RATE, DIVIDEND_YIELD, True)
                      + bs_price(c[last_walk], atm, tte(last_walk), sig[last_walk] * m_iv,
                      RISK_FREE_RATE, DIVIDEND_YIELD, False))
        premX_fill = premX * (1 + slip)                 # buy back → pay up
        straddle_pnl = prem0_fill - premX_fill          # per unit
        net_units = straddle_pnl + hedge_pnl - hedge_cost
        # costs: option STT+NSE+GST+SEBI on 2 legs + futures brokerage per rebalance
        sell_turn = prem0_fill * LOT_SIZE; buy_turn = premX_fill * LOT_SIZE
        opt_cost = (STT_SELL_PCT * sell_turn + NSE_TXN_PCT * (sell_turn + buy_turn) * (1 + GST_PCT)
                    + SEBI_PER_CRORE * (sell_turn + buy_turn) / 1e7)
        fixed = BROKERAGE_PER_ORDER * (1 + GST_PCT) * (4 + n_reb)   # 2 opt legs *2 + hedge trades
        pnl_per_lot = net_units * LOT_SIZE - opt_cost
        rows.append({"sleeve": "S3_DH", "entry_dt": idx[j], "exit_dt": idx[last_walk],
                     "expiry": expiry, "dte": int((expiry - d).days),
                     "spot_entry": float(s_entry), "atm": atm, "prem0": prem0,
                     "straddle_pnl_lot": straddle_pnl * LOT_SIZE,
                     "hedge_pnl_lot": hedge_pnl * LOT_SIZE,
                     "n_rebalance": n_reb, "pnl_per_lot": float(pnl_per_lot),
                     "fixed_cost": float(fixed), "reason": "EOD",
                     "hold_min": float(last_walk - j),
                     "margin_per_lot": 0.09 * s_entry * LOT_SIZE,
                     "max_loss_per_lot": 0.25 * prem0 * LOT_SIZE})
    return pd.DataFrame(rows)


def _signed_value(s, strikes, calls, signs, t, sigma):
    """Position liquidation value L(S,t) = sum sign_i * BS_price_i. Long=+1."""
    v = np.zeros_like(np.asarray(s, dtype=float))
    for k, c, sg in zip(strikes, calls, signs):
        v = v + sg * bs_price(s, k, t, sigma, RISK_FREE_RATE, DIVIDEND_YIELD, bool(c))
    return v


def simulate_multileg(nifty: pd.DataFrame, vix_on_bars: pd.Series,
                      orders: list[MultiLegSpec], iv_mult=None,
                      clock: str = "trading", slippage_pct: float | None = None,
                      stop_slip_mult: float = 3.0) -> pd.DataFrame:
    """Simulate arbitrary mixed long/short option structures at 1 lot.

    P&L = L(exit) - L(entry), L = sum sign_i*price_i (long +1 / short -1).
    Slippage hits every leg adversely at entry and exit (buys up / sells down).
    SL/PT thresholds are fractions of |entry net premium|. Intrabar extremes
    are found by evaluating L at the bar's low/high and each strike clipped
    into [low,high] (covers the kinks) — no convexity assumption."""
    iv_fn = (default_iv_mult if iv_mult is None else
             iv_mult if callable(iv_mult) else (lambda _d, _m=float(iv_mult): _m))
    slip = SLIPPAGE_PCT if slippage_pct is None else slippage_pct
    idx = nifty.index
    days = idx.normalize()
    unique_days = pd.DatetimeIndex(days.unique())
    cal = ExpiryCalendar(unique_days)
    o, h = nifty["open"].to_numpy(), nifty["high"].to_numpy()
    lo, c = nifty["low"].to_numpy(), nifty["close"].to_numpy()
    sig = vix_on_bars.to_numpy() / 100.0
    ts = idx.as_unit("ns").asi8
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day_start = np.searchsorted(days.asi8, unique_days.asi8, "left")
    day_end = np.append(day_start[1:], len(idx))
    day_pos = {d: k for k, d in enumerate(unique_days)}

    rows = []
    for od in orders:
        d = od.signal_dt.normalize()
        k = day_pos.get(d)
        if k is None:
            continue
        s0, s1 = day_start[k], day_end[k]
        i = s0 + int(np.searchsorted(ts[s0:s1], od.signal_dt.value))
        if i >= s1 or ts[i] != od.signal_dt.value:
            continue
        j = i + 1
        hh, mm = map(int, od.exit.hard_exit.split(":"))
        hard = dtime(hh, mm)
        walk_ok = np.nonzero(idx[s0:s1].time <= hard)[0]
        if not len(walk_ok):
            continue
        last_walk = s0 + int(walk_ok[-1])
        if j > last_walk or idx[j].time() >= hard:
            continue
        expiry = cal.next_expiry(d, min_dte=od.min_dte)
        if od.min_dte == 0 and expiry != d:
            continue
        k_exp = day_pos.get(expiry.normalize(), k)
        m_iv = iv_fn(int((expiry - d).days))

        s_entry = o[j]
        atm = float(nearest_strike(s_entry))
        strikes = np.array([atm + off * 50 for _, off, _ in od.legs], float)
        calls = np.array([cc for cc, _, _ in od.legs], bool)
        signs = np.array([sg for _, _, sg in od.legs], float)
        sigma0 = sig[i] * m_iv

        def tte(bar_i, n_bar=None):
            rem = max(CLOSE_MIN_OF_DAY - (mod[bar_i] + 1), 0.0)
            if clock == "trading":
                return max(rem + TRADING_MIN_PER_DAY * (k_exp - k), 1.0) / TRADING_MIN_PER_YEAR
            exp_ns = (unique_days[k_exp] + pd.Timedelta("15:30:00")).value
            return max((exp_ns - (ts[bar_i] + 60e9)) / 1e9 / 60, 1.0) / (365.0 * 24 * 60)

        t0 = tte(j)
        prices0 = np.array([float(bs_price(s_entry, strikes[x], t0, sigma0,
                            RISK_FREE_RATE, DIVIDEND_YIELD, bool(calls[x])))
                            for x in range(len(strikes))])
        L0 = float((signs * prices0).sum())
        ref = abs(L0)                                  # |net premium|
        if ref < MIN_COMBO_PREMIUM:
            continue
        # slippage-adjusted establish cost: long pays up, short receives less
        est_cost = float(sum((p * (1 + slip) if s > 0 else -p * (1 - slip))
                             for p, s in zip(prices0, signs)))

        sl_ = slice(j, last_walk + 1)
        n_b = last_walk + 1 - j
        if clock == "trading":
            rem = np.maximum(CLOSE_MIN_OF_DAY - (mod[sl_] + 1), 0.0)
            t_arr = np.maximum(rem + TRADING_MIN_PER_DAY * (k_exp - k), 1.0) / TRADING_MIN_PER_YEAR
        else:
            exp_ns = (unique_days[k_exp] + pd.Timedelta("15:30:00")).value
            t_arr = np.maximum((exp_ns - (ts[sl_] + 60e9)) / 1e9 / 60, 1.0) / (365.0 * 24 * 60)
        sg_arr = sig[sl_] * m_iv

        # intrabar P&L extremes vs entry (mid): evaluate L at candidate S
        cand = [lo[sl_], h[sl_]] + [np.clip(kk, lo[sl_], h[sl_]) for kk in strikes]
        Lvals = np.stack([_signed_value(sc, strikes, calls, signs, t_arr, sg_arr)
                          for sc in cand])
        pnl_min = Lvals.min(axis=0) - L0          # worst P&L per bar
        pnl_max = Lvals.max(axis=0) - L0          # best P&L per bar

        sl_amt = od.exit.sl * ref
        pt_amt = od.exit.pt * ref if od.exit.pt is not None else None
        reason, k_exit = "EOD", n_b - 1
        for b in range(n_b):
            if pnl_min[b] <= -sl_amt:
                reason, k_exit = "SL", b
                break
            if pt_amt is not None and pnl_max[b] >= pt_amt:
                reason, k_exit = "TARGET", b
                break
        # exit fill prices (mid at exit bar's close), slippage on close
        Lc = float(_signed_value(np.array([c[j + k_exit]]), strikes, calls, signs,
                                 np.array([t_arr[k_exit]]), np.array([sg_arr[k_exit]]))[0])
        prices_x = np.array([float(bs_price(c[j + k_exit], strikes[x], t_arr[k_exit],
                             sg_arr[k_exit], RISK_FREE_RATE, DIVIDEND_YIELD, bool(calls[x])))
                             for x in range(len(strikes))])
        exit_slip = slip * stop_slip_mult if reason == "SL" else slip
        # closing: long sells (receive less), short buys (pay more)
        close_proceeds = float(sum((p * (1 - exit_slip) if s > 0 else -p * (1 + exit_slip))
                                   for p, s in zip(prices_x, signs)))
        pnl_units = close_proceeds - est_cost
        # costs: per-leg sell turnover (STT), both-side NSE+GST, SEBI, brokerage
        sell_turn = float(sum(p for p, s in zip(prices0, signs) if s < 0)
                          + sum(p for p, s in zip(prices_x, signs) if s > 0)) * LOT_SIZE
        buy_turn = float(sum(p for p, s in zip(prices0, signs) if s > 0)
                         + sum(p for p, s in zip(prices_x, signs) if s < 0)) * LOT_SIZE
        linear = STT_SELL_PCT * sell_turn + NSE_TXN_PCT * (sell_turn + buy_turn) * (1 + GST_PCT) \
            + SEBI_PER_CRORE * (sell_turn + buy_turn) / 1e7
        n_orders = 2 * len(od.legs)
        fixed_cost = BROKERAGE_PER_ORDER * n_orders * (1 + GST_PCT)
        pnl_per_lot = pnl_units * LOT_SIZE - linear
        # defined max loss = worst possible P&L to expiry (wing-capped)
        wide = np.array([atm * 0.85, atm * 1.15])
        Lw = _signed_value(wide, strikes, calls, signs, 1e-6, sigma0)
        max_loss_per_lot = float(max(L0 - Lw.min(), sl_amt)) * LOT_SIZE
        margin_per_lot = max_loss_per_lot              # defined-risk → margin ~ max loss

        rows.append({
            "sleeve": od.sleeve, "label": od.label, "entry_dt": idx[j],
            "exit_dt": idx[j + k_exit], "expiry": expiry, "n_legs": len(od.legs),
            "spot_entry": float(s_entry), "atm": atm, "net_premium": L0,
            "reason": reason, "hold_min": float(k_exit),
            "pnl_per_lot": float(pnl_per_lot), "fixed_cost": float(fixed_cost),
            "margin_per_lot": margin_per_lot, "max_loss_per_lot": max_loss_per_lot,
        })
    return pd.DataFrame(rows)
