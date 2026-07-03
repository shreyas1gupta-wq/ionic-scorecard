"""Central configuration — all parameters and constants for the strategy.

No global mutable state: everything here is a frozen constant or a frozen
dataclass. Modules import from here; nothing writes back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent
DATASETS_DIR: Path = PROJECT_ROOT / "datasets"
RAW_DIR: Path = DATASETS_DIR / "raw"
PROCESSED_DIR: Path = DATASETS_DIR / "processed"
RESULTS_DIR: Path = PROJECT_ROOT / "results"

# ── Capital & sizing ─────────────────────────────────────────────────────
TOTAL_CAPITAL: float = 1_00_00_000.0          # ₹1 Crore
KELLY_FRACTION: float = 0.25                  # fractional Kelly multiplier
LOT_SIZE: int = 75                            # Nifty lot (per spec; see PLAN.md notes)
MIN_LOTS: int = 1
MAX_LOTS: int = 20
MAX_OPEN_DELTA_NOTIONAL: float = 50_00_000.0  # ₹50L
MAX_PREMIUM_OUTLAY_PCT: float = 0.10          # 10% of capital per trade
KELLY_REFRESH_DAYS: int = 60                  # rolling re-estimation window

# ── Transaction costs (per spec, conservative) ───────────────────────────
BROKERAGE_PER_ORDER: float = 20.0             # flat ₹, Zerodha-style
STT_SELL_PCT: float = 0.0625 / 100            # on sell-side premium
NSE_TXN_PCT: float = 0.053 / 100              # on premium turnover
GST_PCT: float = 0.18                         # on brokerage + txn charges
SEBI_PER_CRORE: float = 10.0                  # ₹10 per ₹1Cr turnover
SLIPPAGE_PCT: float = 0.15 / 100              # of premium, per leg (base case)

# ── Options pricing ──────────────────────────────────────────────────────
RISK_FREE_RATE: float = 0.065                 # 6.5% p.a.
DIVIDEND_YIELD: float = 0.012                 # 1.2% Nifty
STRIKE_STEP: int = 50
MIN_DTE_CAL_DAYS: int = 2                     # < 2 days → roll to next weekly
TRADING_DAYS_PER_YEAR: int = 252
REALISED_VOL_WINDOW: int = 20                 # fallback IV proxy (days)

# ── Session / time rules (IST, tz-naive timestamps in data) ──────────────
SESSION_START: str = "09:15"
TRADE_START: str = "09:30"                    # C3: no entries before
HARD_CLOSE: str = "15:20"                     # square-off & no-entry cutoff
SESSION_END: str = "15:30"

# ── Regime filters ───────────────────────────────────────────────────────
VIX_MAX: float = 25.0                         # C1
ADX_TREND_MIN: float = 30.0                   # C2: > → trend-only
ADX_MEANREV_MAX: float = 20.0                 # C2: < → mean-rev-only
ADX_MIXED_SIZE_MULT: float = 0.5              # C2: 20–30 band
VIX_REGIME_SPLIT: float = 18.0                # 9.4 robustness split

# ── Signal parameters (defaults; SL/target/EMA/ORB optimised via WFO) ────
EMA_FAST_DEFAULT: int = 5
EMA_SLOW_DEFAULT: int = 21
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 30.0
RSI_OVERBOUGHT: float = 70.0
RSI_VWAP_BAND_PCT: float = 0.005              # B1: within ±0.5% of VWAP
BB_PERIOD: int = 20
BB_STD: float = 2.0
BB_WIDTH_PCTILE_MAX: float = 0.30             # B2: lower 30th percentile
ORB_MINUTES_DEFAULT: int = 15
ORB_VOL_MULT: float = 1.5                     # breakout vol > 1.5× 20-bar avg
ADX_PERIOD: int = 14
COMPOSITE_SCORE_MIN: int = 2

# ── Walk-forward optimisation ────────────────────────────────────────────
IS_FRACTION: float = 0.70
WFO_OPT_DAYS: int = 60
WFO_FWD_DAYS: int = 15
WFO_STEP_DAYS: int = 15

SL_PCT_GRID: tuple[float, ...] = (0.20, 0.25, 0.30, 0.35)
TARGET_PCT_GRID: tuple[float, ...] = (0.35, 0.45, 0.55)
EMA_FAST_GRID: tuple[int, ...] = (3, 5, 8)
EMA_SLOW_GRID: tuple[int, ...] = (13, 21, 34)
ORB_MINUTES_GRID: tuple[int, ...] = (10, 15, 20)
MAX_TRADES_PER_DAY_GRID: tuple[int, ...] = (10, 20, 30)

MIN_WIN_RATE: float = 0.55
MIN_PROFIT_FACTOR: float = 1.5
MAX_DRAWDOWN_LIMIT: float = 0.20
MIN_TARGET_SL_RATIO: float = 1.5

# ── Reproducibility ──────────────────────────────────────────────────────
RANDOM_SEED: int = 42
MC_ITERATIONS: int = 100                      # 9.5 random-removal Monte Carlo
MC_REMOVAL_FRAC: float = 0.10


@dataclass(frozen=True)
class StrategyParams:
    """One optimisable parameter set (a point on the WFO grid)."""
    sl_pct: float = 0.25
    target_pct: float = 0.45
    ema_fast: int = EMA_FAST_DEFAULT
    ema_slow: int = EMA_SLOW_DEFAULT
    orb_minutes: int = ORB_MINUTES_DEFAULT
    max_trades_per_day: int = 20

    def __post_init__(self) -> None:
        if self.target_pct / self.sl_pct < MIN_TARGET_SL_RATIO:
            raise ValueError(
                f"target/SL = {self.target_pct / self.sl_pct:.2f} < {MIN_TARGET_SL_RATIO}"
            )
