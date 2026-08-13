r"""SHARED intraday/multi-day NIFTY OPTION P&L HARNESS  (Shreyas_Ionic_AMC, DESK-100)
=====================================================================================
ONE place where a signal list becomes real option P&L. Every option-buying study should
call this instead of re-implementing fills. Built 2026-07-29, validated against
UNIT-1..4 + REG-1 + SANITY-5/6 in PREREG.md (same folder).

WHAT IT DOES
------------
  signals (timestamp + direction)  ->  per-trade DataFrame with REAL 1-min option fills,
                                       gross P&L, costs, net P&L, liquidity diagnostics.

Data: intraday_options_strategy/datasets/raw/hf_index_options_1m  (via `chain.py`)
Costs: reuses `engine._costs` / `frictions.option_costs` rate constants and
       06_TRADING_DESK/COST_STANDARDS.md (APPROVED D-021, binding).

HARD RULES BAKED IN
-------------------
* Entry = the option's FIRST 1-min bar STRICTLY AFTER the signal timestamp, filled at that
  bar's OPEN. Never the signal bar itself (no lookahead).
* Strike is chosen from the underlying's close AT OR BEFORE the signal timestamp.
* Exits are evaluated on 1-min CLOSES only. No intrabar high/low touch is ever assumed
  (the dataset gives OHLC but an intrabar touch is not a fillable price you can prove).
* Pre-open auction prints (09:00-09:07) in the INDEX file are filtered out (landmine #2).
* A position that reaches its expiry date is CASH-SETTLED AT INTRINSIC from the underlying
  (NSE rule proxy: mean of the index's 1-min closes 15:00-15:30 on expiry day). No
  expiry-day option print is ever used as that exit price (firm landmine #9).
* This dataset is SPARSE: a 1-min bar exists only if that strike traded that minute.
  A missing bar therefore means "no trade" -> the harness records `entry_lag_min` and
  rejects fills that would require waiting more than `max_entry_lag_min` minutes.
* Zero-volume bar = NO FILL by default (COST_STANDARDS Dynamic-slippage rule).

PUBLIC API  (see docstrings for full argument meanings)
------------------------------------------------------
  OptCfg(...)                          - frozen config dataclass
  run_signals(signals, cfg, ...)       - MAIN ENTRY POINT -> per-trade DataFrame
  summarize(trades, label=..)          - metrics dict + printed block (filters to filled)
  fill_report(trades)                  - liquidity / reject-reason honesty report
  round_trip_costs(...)                - the cost model, callable standalone
  intrinsic(spot, strike, otype)       - option intrinsic value
  load_spot()                          - NIFTY 1-min spot, pre-open filtered, naive IST

RETURN CONVENTION (important for blind callers)
----------------------------------------------
`run_signals` returns ONE ROW PER INPUT SIGNAL. Rows carry `status` in
{"filled","rejected"}; rejected rows have NaN P&L and a `reject_reason`. NOTHING is
silently dropped -- that is deliberate, so a caller can always report what fraction of
signals were untradeable. ALWAYS filter `df[df.status=="filled"]` before computing stats,
or just call `summarize()` which does it for you.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- reuse prior art
_BUYING_DIR = Path(
    r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
    r"\NIFTY 500\intraday_options_strategy\buying"
)
if str(_BUYING_DIR) not in sys.path:
    sys.path.insert(0, str(_BUYING_DIR))

import chain          # noqa: E402  build_expiry_index/load_expiry/nearest_expiry/load_index
import engine as _eng  # noqa: E402  _costs, STEP  (incumbent cost model)
import frictions as _fr  # noqa: E402  option_costs, slippage_pct, liquid_enough

__all__ = [
    "OptCfg", "run_signals", "summarize", "fill_report", "round_trip_costs",
    "intrinsic", "load_spot", "STEP", "TICK",
]

STEP = _eng.STEP          # 50  NIFTY strike step
TICK = 0.05               # NSE option tick
SESSION_OPEN = dt.time(9, 15)
SESSION_CLOSE = dt.time(15, 30)

# ---- cost constants -----------------------------------------------------------
# COST_STANDARDS.md (APPROVED D-021) rates:
BROKERAGE_PER_ORDER = 20.0
STT_OPT_SELL_CS = 0.001          # 0.1%   of premium, sell side          [COST_STANDARDS]
STT_OPT_EXERCISE = 0.00125       # 0.125% of INTRINSIC on exercise       [COST_STANDARDS]
EXCH_TXN_OPT_CS = 0.00035        # 0.035% of premium                     [COST_STANDARDS]
GST_PCT = 0.18                   # on (brokerage + exch + SEBI)          [COST_STANDARDS]
SEBI_PER_CRORE = 10.0
STAMP_BUY_PCT = 0.00003          # 0.003% on buy premium
# Incumbent (engine.py / frictions.py) rates -- kept ONLY for regression comparability:
STT_OPT_SELL_INC = _eng.STT_SELL_PCT      # 0.0625%  (pre-Oct-2024 STT regime)
EXCH_TXN_OPT_INC = _eng.EXCH_TXN_PCT      # 0.0495%
STT_HIKE_DATE = dt.date(2024, 10, 1)      # [INFERENCE] options STT 0.0625% -> 0.1%


# ==============================================================================
#  CONFIG
# ==============================================================================
@dataclass(frozen=True)
class OptCfg:
    """Everything that defines an option trade. All fields are keyword-settable.

    INSTRUMENT
      min_dte, max_dte     : pick the nearest expiry E with min_dte <= (E-signal_day).days
                             <= max_dte. min_dte=0 allows same-day (0DTE) expiries.
      strike_offset        : steps from ATM in MONEYNESS terms, direction-aware and
                             UNAMBIGUOUS:  +1 = one step OUT of the money,
                                           -1 = one step IN the money,
                             for BOTH CE and PE.  (strike = ATM + offset*step*direction)
                             NOTE: this is the OPPOSITE SIGN of the legacy
                             engine.py/engine_swing.py `strike_offset`, whose code and
                             comment disagreed -- their "-2 = ITM2" actually bought
                             2 strikes OTM. Use +2 here to reproduce their "ITM2".
      step, lot_size       : 50 / 75. lot_size is CONSTANT (see LIMITATIONS in module doc
                             of validate.py) -- percentage returns are the honest metric.

    EXITS  (all optional; whichever triggers FIRST on a 1-min CLOSE wins)
      target_pct           : exit when premium >= entry*(1+target_pct).  None = off.
      stop_pct             : exit when premium <= entry*(1-stop_pct).    None = off.
      trail_pct            : once premium has exceeded entry, exit when it falls
                             trail_pct below the running peak.           None = off.
      time_stop_min        : exit after this many minutes held.          None = off.
      max_hold_days        : 0 = intraday only (flat the same day). >0 = allow overnight
                             holds for that many days (calendar days unless
                             hold_days_are_trading_days=True). Capped by the expiry.
                             If the Nth calendar day is not a trading day the square-off
                             ROLLS FORWARD to the next available session.
      squareoff_hhmm       : mandatory flat time on the last allowed day ("15:25").
      allow_opposite_signal_exit : if True, an opposite-direction signal in the input
                             closes the position at the next bar after it.
      expiry_handling      : what to do when the last allowed day IS the expiry date.
                             "settle_intrinsic" (DEFAULT, conservative): no trade-out
                               square-off on expiry day. Stop/target/trail/time may still
                               fire on the option's REAL 1-min closes during that session;
                               anything still open at the end of it is CASH-SETTLED at
                               intrinsic from the underlying's 15:00-15:30 mean (zero time
                               value). An expiry-day *settle print* is never used.
                             "trade_out": exit at squareoff_hhmm using the option's real
                               1-min close (a genuine traded print, not a bhavcopy settle).
                             *** INTRADAY / 0DTE CALLERS: if your signals can fire on the
                             expiry day and you want a realistic 15:25 exit, pass
                             expiry_handling="trade_out". The default will otherwise strip
                             the remaining time value from those trades. ***
      expiry_settle_window_min : minutes before close averaged for the settlement price (30).
      levels_off           : "fill" (DEFAULT, correct: target/stop/trail measured off the
                             slippage-inclusive fill) or "raw" (measured off the bar open,
                             which is what the legacy engines did).
      exit_from_entry_bar  : if True the entry bar's own CLOSE can trigger an exit.
                             Default False (matches legacy engines).

    FILLS / COSTS
      slippage_pct         : per-leg slippage as a fraction of premium (0.005 = 0.5%,
                             i.e. 2x the COST_STANDARDS liquid-ATM-index floor).
      slippage_min_rs      : absolute per-leg floor in rupees (1 tick = 0.05). Prevents the
                             absurdity of 0.5% slippage on a Rs.2 option.
      slippage_mode        : "dynamic" (DEFAULT): multiply slippage by 1x/2x/3x when the
                             fill bar's volume is >=50% / 20-50% / <20% of that strike's
                             median bar volume that day -- an adaptation of the BINDING
                             equity Dynamic-slippage rule (COST_STANDARDS 2026-07-04) to
                             option bars [INFERENCE on the mapping, not on the rule].
                             "fixed": no multiplier.
      cost_model           : "cost_standards" (DEFAULT, binding rates: STT 0.1%,
                             exch 0.035%), "incumbent" (calls engine._costs verbatim:
                             STT 0.0625%, exch 0.0495% -- for regression only), or
                             "date_aware" (STT 0.0625% before 2024-10-01 else 0.1%).

    LIQUIDITY HONESTY
      exclude_zero_volume  : reject a fill on a zero-volume bar (COST_STANDARDS: "zero/
                             absent volume -> NO FILL"). Default True.
      thin_frac            : bar volume < thin_frac * that strike's median bar volume that
                             day => flagged `thin`. Reported, not excluded.
      min_entry_volume     : hard minimum contracts in the entry bar (0 = off).
      max_entry_lag_min    : reject if the first tradeable option bar is more than this
                             many minutes after the signal (the strike was not trading).
      max_strike_miss_steps: reject if the nearest LISTED strike is more than this many
                             steps from the requested one.

    SIZING
      lots                 : fixed lot count. None (DEFAULT) = legacy sizing:
                             max(1, floor(risk_per_trade*capital / (fill*lot_size))).
      capital, risk_per_trade : only used when lots is None.
      no_overlap           : if True, skip a signal that arrives while a previous trade
                             from THIS run is still open (crude single-position book).
    """
    # instrument
    min_dte: int = 0
    max_dte: int = 7
    strike_offset: int = 0
    step: int = STEP
    lot_size: int = 75
    # exits
    target_pct: Optional[float] = None
    stop_pct: Optional[float] = None
    trail_pct: Optional[float] = None
    time_stop_min: Optional[int] = None
    max_hold_days: int = 0
    hold_days_are_trading_days: bool = False
    squareoff_hhmm: str = "15:25"
    allow_opposite_signal_exit: bool = True
    expiry_handling: str = "settle_intrinsic"
    expiry_settle_window_min: int = 30
    levels_off: str = "fill"
    exit_from_entry_bar: bool = False
    # fills / costs
    slippage_pct: float = 0.005
    slippage_min_rs: float = TICK
    slippage_mode: str = "dynamic"
    cost_model: str = "cost_standards"
    # liquidity
    exclude_zero_volume: bool = True
    thin_frac: float = 0.20
    min_entry_volume: int = 0
    max_entry_lag_min: int = 5
    max_strike_miss_steps: int = 1
    # sizing
    lots: Optional[int] = None
    capital: float = 3_00_000.0
    risk_per_trade: float = 0.03
    no_overlap: bool = False

    def __post_init__(self):
        if self.expiry_handling not in ("settle_intrinsic", "trade_out"):
            raise ValueError(f"expiry_handling={self.expiry_handling!r}")
        if self.slippage_mode not in ("dynamic", "fixed"):
            raise ValueError(f"slippage_mode={self.slippage_mode!r}")
        if self.cost_model not in ("cost_standards", "incumbent", "date_aware"):
            raise ValueError(f"cost_model={self.cost_model!r}")
        if self.levels_off not in ("fill", "raw"):
            raise ValueError(f"levels_off={self.levels_off!r}")


# ==============================================================================
#  COSTS
# ==============================================================================
def _rates(cost_model: str, exit_date: Optional[dt.date]) -> tuple[float, float]:
    if cost_model == "incumbent":
        return STT_OPT_SELL_INC, EXCH_TXN_OPT_INC
    if cost_model == "date_aware":
        stt = STT_OPT_SELL_INC if (exit_date and exit_date < STT_HIKE_DATE) else STT_OPT_SELL_CS
        return stt, EXCH_TXN_OPT_CS
    return STT_OPT_SELL_CS, EXCH_TXN_OPT_CS


def round_trip_costs(entry_px: float, exit_px: float, qty: int,
                     cost_model: str = "cost_standards",
                     exit_date: Optional[dt.date] = None,
                     exercised: bool = False) -> float:
    """Round-trip rupee cost of ONE long option position of `qty` contracts.

    entry_px / exit_px : per-contract premium actually paid / received (post-slippage).
    exercised          : True when the exit is cash settlement at expiry -> no exit
                         brokerage / exchange charge, and STT is 0.125% of INTRINSIC
                         instead of 0.1% of premium (COST_STANDARDS line 11).
    """
    entry_px = max(float(entry_px), 0.0)
    exit_px = max(float(exit_px), 0.0)
    if cost_model == "incumbent" and not exercised:
        # verbatim reuse of the incumbent model (lots=1, lot_size=qty => qty contracts)
        return float(_eng._costs(entry_px, exit_px, 1, qty, False))
    stt_rate, exch_rate = _rates(cost_model, exit_date)
    to_in, to_out = entry_px * qty, exit_px * qty
    if exercised:
        n_orders, exch, stt = 1, exch_rate * to_in, STT_OPT_EXERCISE * to_out
    else:
        n_orders, exch = 2, exch_rate * (to_in + to_out)
        stt = stt_rate * to_out
    brok = BROKERAGE_PER_ORDER * n_orders
    sebi = SEBI_PER_CRORE * (to_in + to_out) / 1e7
    gst = GST_PCT * (brok + exch + sebi)
    stamp = STAMP_BUY_PCT * to_in
    return float(brok + exch + stt + gst + sebi + stamp)


def _slip_rs(px: float, cfg: OptCfg, bar_vol: float, day_med_vol: float) -> float:
    """Per-leg slippage in rupees."""
    s = max(cfg.slippage_min_rs, cfg.slippage_pct * max(px, 0.0))
    if cfg.slippage_mode == "dynamic" and day_med_vol and np.isfinite(day_med_vol) and day_med_vol > 0:
        r = (bar_vol or 0.0) / day_med_vol
        s *= 1.0 if r >= 0.50 else (2.0 if r >= 0.20 else 3.0)
    return s


# ==============================================================================
#  DATA HELPERS
# ==============================================================================
def intrinsic(spot: float, strike: float, otype: str) -> float:
    """Option intrinsic value. otype in {'CE','PE'}."""
    return max(0.0, spot - strike) if otype == "CE" else max(0.0, strike - spot)


_SPOT: Optional[pd.DataFrame] = None


def load_spot() -> pd.DataFrame:
    """NIFTY 1-min spot OHLC, naive IST index, PRE-OPEN AUCTION BARS REMOVED (>=09:15).

    Landmine #2: the raw file contains 09:00-09:07 pre-open auction prints; a naive
    first()/asof() on it silently returns auction prices.
    """
    global _SPOT
    if _SPOT is None:
        s = chain.load_index()
        _SPOT = s[(s.index.time >= SESSION_OPEN) & (s.index.time <= SESSION_CLOSE)].copy()
    return _SPOT


class _ExpiryStore:
    """Small LRU over expiry files, MultiIndexed by (strike, option_type) for O(1) legs."""

    def __init__(self, maxsize: int = 2):
        self.maxsize = maxsize
        self._d: dict[dt.date, pd.DataFrame] = {}
        self._order: list[dt.date] = []
        self._days: dict[dt.date, list[dt.date]] = {}

    def get(self, exp: dt.date) -> pd.DataFrame:
        if exp in self._d:
            return self._d[exp]
        raw = chain.load_expiry(exp)
        chain.load_expiry.cache_clear()          # we keep our own copy; free chain's
        df = raw[["t", "open", "high", "low", "close", "volume",
                  "open_interest", "trading_day", "strike", "option_type"]].copy()
        df = df.set_index(["strike", "option_type"]).sort_index()
        self._d[exp] = df
        self._order.append(exp)
        while len(self._order) > self.maxsize:
            self._d.pop(self._order.pop(0), None)
        return df

    def leg(self, exp: dt.date, strike: int, otype: str) -> Optional[pd.DataFrame]:
        df = self.get(exp)
        try:
            leg = df.loc[(strike, otype)]
        except KeyError:
            return None
        if isinstance(leg, pd.Series):
            leg = leg.to_frame().T
        return leg.set_index("t").sort_index()

    def strikes(self, exp: dt.date, otype: str) -> np.ndarray:
        df = self.get(exp)
        ks = df.index.get_level_values(0)[df.index.get_level_values(1) == otype]
        return np.unique(ks.values)

    def days(self, exp: dt.date) -> list[dt.date]:
        """Sorted trading days that this expiry file actually contains (all strikes)."""
        if exp not in self._days:
            u = pd.to_datetime(pd.unique(self.get(exp)["trading_day"]))
            self._days[exp] = sorted(d.date() for d in u)
        return self._days[exp]


def _hhmm(day: dt.date, hhmm: str) -> pd.Timestamp:
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


def _settle_spot(exp: dt.date, window_min: int) -> Optional[float]:
    """NSE-style index-option settlement proxy: mean of the underlying's 1-min closes in
    the last `window_min` minutes of the expiry session. None if no spot data that day."""
    sp = load_spot()
    d = sp[sp.index.date == exp]
    if d.empty:
        return None
    lo = _hhmm(exp, "15:30") - pd.Timedelta(minutes=window_min)
    w = d[d.index >= lo]
    if w.empty:
        w = d.tail(min(window_min, len(d)))
    return float(w["close"].mean())


# ==============================================================================
#  MAIN
# ==============================================================================
_TRADE_COLS = [
    "signal_t", "direction", "tag", "status", "reject_reason",
    "exp", "dte_entry", "otype", "strike", "atm", "spot_entry", "strike_miss_steps",
    "moneyness_pct", "entry_t", "entry_lag_min", "entry_px_raw", "entry_fill",
    "entry_vol", "entry_oi", "entry_thin", "entry_slip_mult",
    "exit_t", "exit_reason", "exit_px_raw", "exit_fill", "exit_vol", "exit_oi",
    "exit_thin", "exit_on_expiry_day", "cash_settled", "settle_spot",
    "lots", "qty", "gross", "costs", "net_pnl", "ret_pct_gross", "ret_pct_net",
    "hold_min", "hold_days", "n_bars", "exit_stale",
]


def _reject(sig_t, direction, tag, reason, **extra) -> dict:
    row = {c: np.nan for c in _TRADE_COLS}
    row.update(signal_t=sig_t, direction=direction, tag=tag,
               status="rejected", reject_reason=reason)
    row.update(extra)
    return row


def run_signals(signals, cfg: OptCfg = OptCfg(), progress: int = 0,
                entry_rule: str = "next_bar") -> pd.DataFrame:
    """MAIN ENTRY POINT. Turn signals into per-trade real-fill option P&L.

    Parameters
    ----------
    signals : DataFrame / list[dict] / list[tuple]
        Must yield a timestamp and a direction per signal.
          - DataFrame: columns `t` (or `signal_t`/`timestamp`) and `direction`
            (+1 = bullish -> BUY CE, -1 = bearish -> BUY PE). Optional `tag` column is
            carried through untouched (use it to label sub-strategies).
          - list[dict]: {"t": ts, "direction": +1, "tag": "..."}
          - list[tuple]: (ts, direction)
        Timestamps must be NAIVE IST 1-min bar stamps (the same convention as
        `chain.load_index()` / `load_spot()`), i.e. the OPEN time of the signal bar.
    cfg : OptCfg
        See OptCfg docstring. Defaults = 0-7 DTE, ATM, intraday-only, flat 15:25,
        binding COST_STANDARDS rates, dynamic slippage, zero-volume fills excluded.
    progress : int
        Print a line every N signals (0 = silent).
    entry_rule : {"next_bar","at_or_after"}
        "next_bar" (DEFAULT, no lookahead): fill at the first option bar STRICTLY AFTER
        the signal timestamp. Use this if `t` is the timestamp of the signal bar.
        "at_or_after": fill at the first option bar at or after `t`. ONLY use this if the
        caller has ALREADY advanced `t` past the signal bar; otherwise it is lookahead.

    Returns
    -------
    DataFrame, ONE ROW PER INPUT SIGNAL, columns as in `_TRADE_COLS`.
      status         : "filled" | "rejected"
      reject_reason  : why an untradeable signal was dropped (NaN when filled)
      entry_px_raw   : the option bar's OPEN (no slippage)          <- audit trail
      entry_fill     : what we actually pay (open + slippage)
      exit_px_raw    : the 1-min CLOSE we exit on, or the intrinsic when cash settled
      exit_fill      : what we actually receive (close - slippage; = intrinsic if settled)
      gross          : (exit_fill - entry_fill) * qty      [rupees, slippage INCLUDED]
      costs          : round-trip statutory + brokerage costs [rupees]
      net_pnl        : gross - costs
      ret_pct_net    : net_pnl / (entry_fill*qty)
      entry_vol/exit_vol, entry_oi/exit_oi, entry_thin/exit_thin : liquidity audit
      cash_settled   : True when the exit was intrinsic at expiry (no option print used)
      exit_stale     : True when the option stopped printing before the intended exit time

    NOTE: `gross` is stated AFTER slippage and BEFORE statutory costs/brokerage. That is
    deliberate -- slippage is part of the price you get, not a charge. If you need a
    truly frictionless gross, use (exit_px_raw - entry_px_raw)*qty from the raw columns.
    """
    if entry_rule not in ("next_bar", "at_or_after"):
        raise ValueError(entry_rule)

    sig = _normalize_signals(signals)
    if sig.empty:
        return pd.DataFrame(columns=_TRADE_COLS)

    spot = load_spot()
    sp_idx = spot.index.values
    sp_close = spot["close"].values
    sp_dates = np.array([d for d in spot.index.date])

    store = _ExpiryStore(maxsize=2)
    rows: list[dict] = []
    busy_until: Optional[pd.Timestamp] = None

    for i, s in enumerate(sig.itertuples(index=False)):
        if progress and i % progress == 0:
            print(f"  [opt_pl] {i}/{len(sig)} signals, filled={sum(1 for r in rows if r['status']=='filled')}")
        t0: pd.Timestamp = s.t
        direction = int(s.direction)
        tag = s.tag
        if direction not in (1, -1):
            rows.append(_reject(t0, direction, tag, "bad_direction")); continue
        if cfg.no_overlap and busy_until is not None and t0 <= busy_until:
            rows.append(_reject(t0, direction, tag, "overlap_skip")); continue

        day = t0.date()
        # ---- spot AT OR BEFORE the signal (never after) -> ATM
        j = np.searchsorted(sp_idx, np.datetime64(t0), side="right") - 1
        if j < 0 or sp_dates[j] != day:
            rows.append(_reject(t0, direction, tag, "no_spot_at_signal")); continue
        spot_at = float(sp_close[j])

        exp = chain.nearest_expiry(day, cfg.min_dte, cfg.max_dte)
        if exp is None:
            rows.append(_reject(t0, direction, tag, "no_expiry_in_dte_window")); continue

        otype = "CE" if direction == 1 else "PE"
        atm = int(round(spot_at / cfg.step) * cfg.step)
        k_want = atm + cfg.strike_offset * cfg.step * direction
        try:
            avail = store.strikes(exp, otype)
        except Exception as e:                                   # unreadable file
            rows.append(_reject(t0, direction, tag, f"expiry_read_error:{type(e).__name__}",
                                exp=exp)); continue
        if avail.size == 0:
            rows.append(_reject(t0, direction, tag, "no_strikes", exp=exp)); continue
        k = int(avail[np.argmin(np.abs(avail - k_want))])
        miss = abs(k - k_want) / cfg.step
        if miss > cfg.max_strike_miss_steps:
            rows.append(_reject(t0, direction, tag, "strike_not_listed", exp=exp,
                                strike=k, atm=atm, strike_miss_steps=miss)); continue

        leg = store.leg(exp, k, otype)
        if leg is None or leg.empty:
            rows.append(_reject(t0, direction, tag, "no_leg_data", exp=exp, strike=k,
                                atm=atm)); continue

        # ---- ENTRY: first bar strictly after the signal bar
        after = leg[leg.index > t0] if entry_rule == "next_bar" else leg[leg.index >= t0]
        after = after[after.index.date == day] if cfg.max_hold_days == 0 else after
        if after.empty:
            rows.append(_reject(t0, direction, tag, "no_bar_after_signal", exp=exp,
                                strike=k, atm=atm)); continue
        e_t = after.index[0]
        lag = (e_t - t0).total_seconds() / 60.0
        if e_t.date() != day or lag > cfg.max_entry_lag_min:
            rows.append(_reject(t0, direction, tag, "entry_lag_too_large", exp=exp,
                                strike=k, atm=atm, entry_t=e_t, entry_lag_min=lag))
            continue
        e_row = after.iloc[0]
        e_px = float(e_row["open"])
        e_vol = float(e_row["volume"])
        e_oi = float(e_row["open_interest"])
        if not np.isfinite(e_px) or e_px <= 0:
            rows.append(_reject(t0, direction, tag, "bad_entry_price", exp=exp, strike=k,
                                atm=atm, entry_t=e_t)); continue
        if cfg.exclude_zero_volume and e_vol <= 0:
            rows.append(_reject(t0, direction, tag, "zero_volume_entry", exp=exp, strike=k,
                                atm=atm, entry_t=e_t, entry_vol=e_vol)); continue
        if e_vol < cfg.min_entry_volume:
            rows.append(_reject(t0, direction, tag, "thin_entry_below_min", exp=exp,
                                strike=k, atm=atm, entry_t=e_t, entry_vol=e_vol)); continue

        # per-day median bar volume of THIS strike (liquidity reference)
        day_med = _day_median_vol(leg, day)
        e_slip = _slip_rs(e_px, cfg, e_vol, day_med)
        _base_slip = max(cfg.slippage_min_rs, cfg.slippage_pct * e_px)
        e_mult = (e_slip / _base_slip) if _base_slip > 0 else 1.0
        e_fill = e_px + e_slip
        e_thin = bool(day_med > 0 and e_vol < cfg.thin_frac * day_med)

        # ---- exit window (square-off day)
        sess = [d for d in store.days(exp) if d >= day]
        if cfg.max_hold_days == 0:
            last_day = day
        elif cfg.hold_days_are_trading_days:
            last_day = sess[min(cfg.max_hold_days, len(sess) - 1)] if sess else day
        else:
            want = day + dt.timedelta(days=cfg.max_hold_days)
            fwd = [d for d in sess if d >= want]
            # calendar target rolls FORWARD to the next available session (matches how a
            # real desk behaves when the Nth calendar day is a weekend/holiday)
            last_day = fwd[0] if fwd else (sess[-1] if sess else day)
        last_day = min(last_day, exp)
        so_t = _hhmm(last_day, cfg.squareoff_hhmm)
        settle_mode = (last_day >= exp) and (cfg.expiry_handling == "settle_intrinsic")

        base = e_fill if cfg.levels_off == "fill" else e_px
        tgt = base * (1 + cfg.target_pct) if cfg.target_pct is not None else None
        stp = base * (1 - cfg.stop_pct) if cfg.stop_pct is not None else None

        # first opposite-direction signal after entry (if any)
        opp_t = None
        if cfg.allow_opposite_signal_exit:
            m = (sig["t"] > e_t) & (sig["direction"] == -direction)
            if m.any():
                opp_t = sig.loc[m, "t"].iloc[0]

        path = leg[(leg.index > e_t) if not cfg.exit_from_entry_bar else (leg.index >= e_t)]
        path = path[path.index.date <= last_day]

        x_t = x_px = x_vol = x_oi = None
        reason = None
        peak = base
        for t, r in zip(path.index, path.itertuples(index=False)):
            v = float(r.close)
            if not np.isfinite(v):
                continue
            if t >= so_t and not settle_mode:
                x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "squareoff"
                break
            # settle_mode: NO trade-out square-off. Real 1-min prices may still trigger
            # stop/target/trail/time on expiry day; anything surviving the session is
            # cash-settled at intrinsic below (landmine #9).
            if opp_t is not None and t > opp_t:
                x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "opposite"
                break
            if stp is not None and v <= stp:
                x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "stop"
                break
            if tgt is not None and v >= tgt:
                x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "target"
                break
            if cfg.trail_pct is not None and cfg.trail_pct > 0:
                peak = max(peak, v)
                if peak > base and v <= peak * (1 - cfg.trail_pct):
                    x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "trail"
                    break
            if cfg.time_stop_min is not None and (t - e_t) >= pd.Timedelta(minutes=cfg.time_stop_min):
                x_t, x_px, x_vol, x_oi, reason = t, v, float(r.volume), float(r.open_interest), "time"
                break

        cash_settled = False
        settle_px = np.nan
        stale = False
        if x_t is None:
            if settle_mode:
                # ---- LANDMINE #9: never read an expiry-day option print here.
                ss = _settle_spot(exp, cfg.expiry_settle_window_min)
                if ss is None:
                    rows.append(_reject(t0, direction, tag, "expiry_no_underlying_data",
                                        exp=exp, strike=k, atm=atm, entry_t=e_t))
                    continue
                settle_px = ss
                x_t = _hhmm(exp, "15:30")
                x_px = intrinsic(ss, k, otype)
                x_vol = x_oi = np.nan
                reason = "expiry_settle"
                cash_settled = True
            elif len(path):
                lr = path.iloc[-1]
                x_t, x_px = path.index[-1], float(lr["close"])
                x_vol, x_oi = float(lr["volume"]), float(lr["open_interest"])
                reason, stale = "data_end", True
            else:
                rows.append(_reject(t0, direction, tag, "no_exit_bar", exp=exp, strike=k,
                                    atm=atm, entry_t=e_t)); continue

        if cash_settled:
            x_fill = max(x_px, 0.0)                 # cash settlement: no market slippage
            x_thin = False
        else:
            ref = day_med if x_t.date() == day else _day_median_vol(leg, x_t.date())
            x_fill = max(x_px - _slip_rs(x_px, cfg, x_vol, ref), 0.0)
            x_thin = bool(ref > 0 and (x_vol or 0) < cfg.thin_frac * ref)

        # ---- sizing
        if cfg.lots is not None:
            lots = int(cfg.lots)
        else:
            outlay = e_fill * cfg.lot_size
            lots = max(1, int((cfg.risk_per_trade * cfg.capital) // max(outlay, 1)))
        qty = lots * cfg.lot_size

        gross = (x_fill - e_fill) * qty
        costs = round_trip_costs(e_fill, x_fill, qty, cfg.cost_model,
                                 x_t.date(), exercised=cash_settled)
        net = gross - costs

        # ---- no-lookahead invariants (fail loudly, never silently)
        assert e_t > t0 or entry_rule == "at_or_after", (t0, e_t)
        assert x_t >= e_t, (e_t, x_t)

        rows.append(dict(
            signal_t=t0, direction=direction, tag=tag, status="filled", reject_reason=np.nan,
            exp=exp, dte_entry=(exp - day).days, otype=otype, strike=k, atm=atm,
            spot_entry=spot_at, strike_miss_steps=miss,
            moneyness_pct=(spot_at - k) / spot_at * direction,
            entry_t=e_t, entry_lag_min=lag, entry_px_raw=e_px, entry_fill=e_fill,
            entry_vol=e_vol, entry_oi=e_oi, entry_thin=e_thin, entry_slip_mult=e_mult,
            exit_t=x_t, exit_reason=reason, exit_px_raw=x_px, exit_fill=x_fill,
            exit_vol=x_vol, exit_oi=x_oi, exit_thin=x_thin,
            exit_on_expiry_day=bool(x_t.date() == exp), cash_settled=cash_settled,
            settle_spot=settle_px, lots=lots, qty=qty,
            gross=gross, costs=costs, net_pnl=net,
            ret_pct_gross=gross / (e_fill * qty), ret_pct_net=net / (e_fill * qty),
            hold_min=(x_t - e_t).total_seconds() / 60.0,
            hold_days=(x_t.date() - e_t.date()).days, n_bars=len(path), exit_stale=stale,
        ))
        busy_until = x_t

    out = pd.DataFrame(rows)
    for c in _TRADE_COLS:
        if c not in out.columns:
            out[c] = np.nan
    return out[_TRADE_COLS]


def _day_median_vol(leg: pd.DataFrame, day: dt.date) -> float:
    d = leg[leg.index.date == day]
    if d.empty:
        return 0.0
    v = d["volume"].values
    v = v[v > 0]
    return float(np.median(v)) if v.size else 0.0


def _normalize_signals(signals) -> pd.DataFrame:
    if isinstance(signals, pd.DataFrame):
        df = signals.copy()
        tcol = next((c for c in ("t", "signal_t", "timestamp", "ts") if c in df.columns), None)
        if tcol is None:
            raise ValueError("signals DataFrame needs a 't' (or signal_t/timestamp) column")
        df = df.rename(columns={tcol: "t"})
        if "direction" not in df.columns:
            raise ValueError("signals DataFrame needs a 'direction' column (+1/-1)")
    else:
        recs = []
        for x in signals:
            if isinstance(x, dict):
                recs.append({"t": x.get("t", x.get("signal_t")),
                             "direction": x["direction"], "tag": x.get("tag", "")})
            else:
                recs.append({"t": x[0], "direction": x[1],
                             "tag": x[2] if len(x) > 2 else ""})
        df = pd.DataFrame(recs)
    if "tag" not in df.columns:
        df["tag"] = ""
    df["t"] = pd.to_datetime(df["t"])
    if getattr(df["t"].dt, "tz", None) is not None:
        df["t"] = df["t"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df["direction"] = df["direction"].astype(int)
    df["tag"] = df["tag"].fillna("")
    return df.sort_values("t").reset_index(drop=True)[["t", "direction", "tag"]]


# ==============================================================================
#  REPORTING
# ==============================================================================
def summarize(trades: pd.DataFrame, label: str = "", capital: Optional[float] = None,
              quiet: bool = False) -> dict:
    """Metrics on the FILLED subset. Reports GROSS and NET separately (D-035)."""
    n_sig = len(trades)
    f = trades[trades["status"] == "filled"] if "status" in trades.columns else trades
    m: dict = {"label": label, "signals": n_sig, "filled": len(f),
               "fill_rate": (len(f) / n_sig) if n_sig else np.nan}
    if f.empty:
        if not quiet:
            print(f"\n--- {label}: 0 filled of {n_sig} signals ---")
        return m
    g, n = f["gross"], f["net_pnl"]
    wins_n, loss_n = n[n > 0], n[n <= 0]
    wins_g, loss_g = g[g > 0], g[g <= 0]
    m.update(
        gross_total=float(g.sum()), net_total=float(n.sum()), costs_total=float(f["costs"].sum()),
        gross_mean=float(g.mean()), net_mean=float(n.mean()),
        wr_gross=float((g > 0).mean()), wr_net=float((n > 0).mean()),
        pf_gross=float(wins_g.sum() / abs(loss_g.sum())) if loss_g.sum() != 0 else np.inf,
        pf_net=float(wins_n.sum() / abs(loss_n.sum())) if loss_n.sum() != 0 else np.inf,
        ret_pct_net_mean=float(f["ret_pct_net"].mean()),
        ret_pct_net_t=float(f["ret_pct_net"].mean() / f["ret_pct_net"].std() * np.sqrt(len(f)))
        if f["ret_pct_net"].std() > 0 else np.nan,
        best=float(n.max()), worst=float(n.min()),
        avg_hold_min=float(f["hold_min"].mean()), avg_hold_days=float(f["hold_days"].mean()),
        zero_vol_entry_frac=float((f["entry_vol"] == 0).mean()),
        thin_entry_frac=float(f["entry_thin"].fillna(False).astype(bool).mean()),
        thin_exit_frac=float(f["exit_thin"].fillna(False).astype(bool).mean()),
        cash_settled_frac=float(f["cash_settled"].fillna(False).astype(bool).mean()),
        stale_exit_frac=float(f["exit_stale"].fillna(False).astype(bool).mean()),
        reasons=f["exit_reason"].value_counts().to_dict(),
    )
    pos = n[n > 0].sum()
    m["top1_profit_share"] = float(n.max() / pos) if pos > 0 else np.nan
    m["fragile_concentration"] = bool(m["top1_profit_share"] > 0.30) if pos > 0 else False
    if capital:
        d = f.sort_values("exit_t").groupby(pd.to_datetime(f.sort_values("exit_t")["exit_t"]).dt.date)["net_pnl"].sum()
        eq = capital + d.cumsum()
        m["total_ret_on_capital"] = float(n.sum() / capital)
        m["maxdd"] = float(((eq - eq.cummax()) / eq.cummax()).min())
        mm = f.copy()
        mm["month"] = pd.to_datetime(mm["exit_t"]).dt.to_period("M")
        gm = mm.groupby("month")[["gross", "net_pnl"]].sum()
        m["pos_months_gross"] = float((gm["gross"] > 0).mean())
        m["pos_months_net"] = float((gm["net_pnl"] > 0).mean())
        m["n_months"] = int(len(gm))
    if not quiet:
        print(f"\n--- {label} ---")
        print(f"signals {n_sig} | filled {len(f)} ({m['fill_rate']:.1%})")
        print(f"GROSS  total Rs.{m['gross_total']:>12,.0f}  mean Rs.{m['gross_mean']:>9,.0f}  "
              f"WR {m['wr_gross']:.1%}  PF {m['pf_gross']:.2f}")
        print(f"NET    total Rs.{m['net_total']:>12,.0f}  mean Rs.{m['net_mean']:>9,.0f}  "
              f"WR {m['wr_net']:.1%}  PF {m['pf_net']:.2f}   (costs Rs.{m['costs_total']:,.0f})")
        print(f"per-trade net ret {m['ret_pct_net_mean']:+.2%}  t={m['ret_pct_net_t']:.2f}  "
              f"best Rs.{m['best']:,.0f}  worst Rs.{m['worst']:,.0f}")
        print(f"hold {m['avg_hold_min']:.0f}min / {m['avg_hold_days']:.1f}d | exits {m['reasons']}")
        print(f"liquidity: zero-vol entry {m['zero_vol_entry_frac']:.2%}, thin entry "
              f"{m['thin_entry_frac']:.2%}, thin exit {m['thin_exit_frac']:.2%}, "
              f"stale exits {m['stale_exit_frac']:.2%}, cash-settled {m['cash_settled_frac']:.2%}")
        if pos > 0:
            print(f"concentration: top trade = {m['top1_profit_share']:.1%} of gross profit"
                  f"{'  <-- FRAGILE (>30%)' if m['fragile_concentration'] else ''}")
        if capital:
            print(f"on Rs.{capital:,.0f}: {m['total_ret_on_capital']:+.1%} total, maxDD "
                  f"{m['maxdd']:.1%} | positive months gross {m['pos_months_gross']:.1%} vs "
                  f"net {m['pos_months_net']:.1%} (n={m['n_months']})")
    return m


def fill_report(trades: pd.DataFrame, quiet: bool = False) -> dict:
    """Where option backtests lie: rejects, entry lag, zero/thin volume, stale exits."""
    n = len(trades)
    rej = trades[trades["status"] == "rejected"]
    f = trades[trades["status"] == "filled"]
    out = {"signals": n, "filled": len(f), "rejected": len(rej),
           "reject_reasons": rej["reject_reason"].value_counts().to_dict()}
    if len(f):
        out.update(
            entry_lag_min_mean=float(f["entry_lag_min"].mean()),
            entry_lag_min_p95=float(f["entry_lag_min"].quantile(0.95)),
            entry_lag_gt1min_frac=float((f["entry_lag_min"] > 1.0).mean()),
            entry_vol_median=float(f["entry_vol"].median()),
            exit_vol_median=float(f["exit_vol"].median()),
            zero_vol_entry_frac=float((f["entry_vol"] == 0).mean()),
            zero_vol_exit_frac=float((f["exit_vol"].fillna(-1) == 0).mean()),
            thin_entry_frac=float(f["entry_thin"].fillna(False).astype(bool).mean()),
            thin_exit_frac=float(f["exit_thin"].fillna(False).astype(bool).mean()),
            slip_mult_gt1_frac=float((f["entry_slip_mult"] > 1.01).mean()),
            stale_exit_frac=float(f["exit_stale"].fillna(False).astype(bool).mean()),
            oi_zero_entry_frac=float((f["entry_oi"].fillna(0) == 0).mean()),
        )
    if not quiet:
        print("\n--- FILL / LIQUIDITY HONESTY REPORT ---")
        print(f"signals {n} | filled {out['filled']} | rejected {out['rejected']}")
        for k, v in out["reject_reasons"].items():
            print(f"   reject {k}: {v}")
        for k, v in out.items():
            if k not in ("signals", "filled", "rejected", "reject_reasons"):
                print(f"   {k}: {v:,.4f}" if isinstance(v, float) else f"   {k}: {v}")
    return out


if __name__ == "__main__":
    # 3-signal smoke test
    sp = load_spot()
    print(f"[opt_pl] spot bars {len(sp):,}  {sp.index[0]} .. {sp.index[-1]}")
    sigs = [(pd.Timestamp("2023-03-28 10:30"), 1), (pd.Timestamp("2023-03-28 13:00"), -1),
            (pd.Timestamp("2024-05-15 11:00"), 1)]
    cfg = OptCfg(min_dte=1, max_dte=7, strike_offset=0, target_pct=0.5, stop_pct=0.3,
                 lots=1, allow_opposite_signal_exit=False)
    tr = run_signals(sigs, cfg)
    print(tr[["signal_t", "otype", "strike", "entry_t", "entry_px_raw", "exit_t",
              "exit_px_raw", "exit_reason", "gross", "costs", "net_pnl"]].to_string())
