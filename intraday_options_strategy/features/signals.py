"""Signal generation A1–A3 (trend) and B1–B2 (mean-reversion), regime-gated,
with the composite-score rule from the spec.

All conditions are evaluated on bar t's close using lookback-only indicators;
execution happens at bar t+1's open (engine's job).

Volume adaptations (PLAN.md caveat 1): "expanding volume" conditions use
true-range expansion: TR(t) > ORB_VOL_MULT × ATR20(t-1).

Composite score (0–3), trade only if score >= COMPOSITE_SCORE_MIN (2):
  +1  signal fires and its category is allowed by the ADX regime
  +1  regime STRONGLY agrees (trend signal in 'trend', meanrev in 'meanrev')
  +1  a second allowed signal of the SAME direction from a DIFFERENT signal id
      fires on the same bar
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    BB_PERIOD, BB_STD, BB_WIDTH_PCTILE_MAX, ORB_VOL_MULT, RSI_OVERBOUGHT,
    RSI_OVERSOLD, RSI_PERIOD, RSI_VWAP_BAND_PCT, StrategyParams,
)
from features.indicators import (  # noqa: E402
    atr, bollinger, ema, orb_levels, rolling_pctile_rank, rsi, session_twap,
    true_range,
)

CATEGORY = {"A1": "trend", "A2": "trend", "A3": "trend",
            "B1": "meanrev", "B2": "meanrev"}
BB_PCTILE_WINDOW = 375 * 5  # trailing ~5 sessions of 1-min bars


def _cross_up(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def _cross_dn(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


def raw_signals(nifty: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Boolean columns '<id>_long'/'<id>_short' for each signal id, plus twap."""
    c = nifty["close"]
    out = pd.DataFrame(index=nifty.index)
    twap = session_twap(nifty)
    expand = true_range(nifty) > ORB_VOL_MULT * atr(nifty, 20).shift(1)

    # A1 — EMA crossover
    f, s = ema(c, params.ema_fast), ema(c, params.ema_slow)
    out["A1_long"], out["A1_short"] = _cross_up(f, s), _cross_dn(f, s)

    # A2 — TWAP (volume-less VWAP) cross with range expansion
    out["A2_long"] = _cross_up(c, twap) & expand
    out["A2_short"] = _cross_dn(c, twap) & expand

    # A3 — opening range breakout with range expansion, first break per day
    orb_h, orb_l = orb_levels(nifty, params.orb_minutes)
    day = nifty.index.normalize()
    brk_up = (c > orb_h) & (c.shift(1) <= orb_h.shift(1).fillna(c.iloc[0]))
    brk_dn = (c < orb_l) & (c.shift(1) >= orb_l.shift(1).fillna(c.iloc[0]))
    first_up = brk_up & (~brk_up.groupby(day).cummax().shift(1).fillna(False).infer_objects(copy=False))
    first_dn = brk_dn & (~brk_dn.groupby(day).cummax().shift(1).fillna(False).infer_objects(copy=False))
    out["A3_long"] = first_up & expand
    out["A3_short"] = first_dn & expand

    # B1 — RSI extremes near TWAP (crossing into the extreme)
    r = rsi(c, RSI_PERIOD)
    near = (c / twap - 1).abs() <= RSI_VWAP_BAND_PCT
    out["B1_long"] = (r < RSI_OVERSOLD) & (r.shift(1) >= RSI_OVERSOLD) & near
    out["B1_short"] = (r > RSI_OVERBOUGHT) & (r.shift(1) <= RSI_OVERBOUGHT) & near

    # B2 — Bollinger touch in squeezed (low-width-percentile) conditions
    _, upper, lower, width = bollinger(c, BB_PERIOD, BB_STD)
    squeezed = rolling_pctile_rank(width, BB_PCTILE_WINDOW, 375) <= BB_WIDTH_PCTILE_MAX
    out["B2_long"] = (c <= lower) & (c.shift(1) > lower.shift(1)) & squeezed
    out["B2_short"] = (c >= upper) & (c.shift(1) < upper.shift(1)) & squeezed

    out["twap"] = twap
    return out


def signal_events(nifty: pd.DataFrame, filters: pd.DataFrame,
                  params: StrategyParams) -> pd.DataFrame:
    """Long-form eligible signal events with composite score >= threshold.

    Returns columns: dt, signal, direction (+1 CE / -1 PE), score, size_mult.
    Eligibility: vix_ok & event_ok & entry_window & category allowed by regime.
    """
    from config import COMPOSITE_SCORE_MIN  # local to keep module constants slim

    raw = raw_signals(nifty, params)
    base_ok = filters["vix_ok"] & filters["event_ok"] & filters["entry_window"]
    regime = filters["regime"]

    allowed = {}
    for sid, cat in CATEGORY.items():
        cat_ok = regime.isin(["trend", "mixed"]) if cat == "trend" \
            else regime.isin(["meanrev", "mixed"])
        for side, col in [(1, f"{sid}_long"), (-1, f"{sid}_short")]:
            allowed[(sid, side)] = raw[col] & base_ok & cat_ok

    # count of allowed same-direction signals per bar (for the +1 confirmation)
    n_long = sum(v for (sid, side), v in allowed.items() if side == 1)
    n_short = sum(v for (sid, side), v in allowed.items() if side == -1)

    rows = []
    for (sid, side), ok in allowed.items():
        if not ok.any():
            continue
        strong = (regime == CATEGORY[sid]).astype(int)
        others = (n_long if side == 1 else n_short) - 1
        score = 1 + strong + (others >= 1).astype(int)
        hit = ok & (score >= COMPOSITE_SCORE_MIN)
        if not hit.any():
            continue
        sub = pd.DataFrame({
            "dt": nifty.index[hit],
            "signal": sid,
            "direction": side,
            "score": score[hit].values,
            "size_mult": filters["size_mult"][hit].values,
        })
        rows.append(sub)
    if not rows:
        return pd.DataFrame(columns=["dt", "signal", "direction", "score", "size_mult"])
    ev = pd.concat(rows, ignore_index=True).sort_values(["dt", "signal"])
    return ev.reset_index(drop=True)
