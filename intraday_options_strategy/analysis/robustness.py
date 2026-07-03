"""Robustness checks 9.1–9.5 (all run on the OOS window only)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import full_metrics  # noqa: E402
from backtest.engine import EngineConfig, run_backtest  # noqa: E402
from config import (  # noqa: E402
    MC_ITERATIONS, MC_REMOVAL_FRAC, RANDOM_SEED, TOTAL_CAPITAL,
    VIX_REGIME_SPLIT, StrategyParams,
)


def _key_metrics(tr: pd.DataFrame, daily: pd.DataFrame) -> dict:
    if not len(tr):
        return {"n_trades": 0, "net_pnl": 0.0, "win_rate": 0.0,
                "profit_factor": 0.0, "sharpe": 0.0, "max_dd_pct": 0.0}
    m = full_metrics(tr, daily)
    return {k: m[k] for k in ["n_trades", "net_pnl", "win_rate",
                              "profit_factor", "sharpe", "max_dd_pct"]}


def slippage_sensitivity(nifty, vix, ev, params: StrategyParams) -> pd.DataFrame:
    rows = {}
    for slip in [0.0015, 0.0025, 0.0050, 0.0100]:
        tr, daily = run_backtest(nifty, vix, ev,
                                 EngineConfig(params, slippage_pct=slip))
        rows[f"slippage {slip:.2%}"] = _key_metrics(tr, daily)
    return pd.DataFrame(rows).T


def cost_sensitivity(nifty, vix, ev, params: StrategyParams) -> pd.DataFrame:
    rows = {}
    for mult in [1.0, 2.0, 3.0]:
        tr, daily = run_backtest(nifty, vix, ev,
                                 EngineConfig(params, cost_mult=mult))
        rows[f"costs x{mult:.0f}"] = _key_metrics(tr, daily)
    return pd.DataFrame(rows).T


def parameter_stability(nifty, vix, ev, params: StrategyParams) -> pd.DataFrame:
    """±10% on SL/target (signal params are discrete; SL/TG drive the P&L
    geometry). Degradation >30% in net P&L vs base → fragile."""
    rows = {}
    base_tr, base_d = run_backtest(nifty, vix, ev, EngineConfig(params))
    base = _key_metrics(base_tr, base_d)
    rows["base"] = base
    for ds, dt_ in [(-0.1, -0.1), (-0.1, 0.1), (0.1, -0.1), (0.1, 0.1)]:
        try:
            p = StrategyParams(sl_pct=params.sl_pct * (1 + ds),
                               target_pct=params.target_pct * (1 + dt_),
                               ema_fast=params.ema_fast, ema_slow=params.ema_slow,
                               orb_minutes=params.orb_minutes,
                               max_trades_per_day=params.max_trades_per_day)
        except ValueError:
            continue  # violates target/SL >= 1.5
        tr, d = run_backtest(nifty, vix, ev, EngineConfig(p))
        rows[f"sl{1 + ds:.0%} tg{1 + dt_:.0%}"] = _key_metrics(tr, d)
    out = pd.DataFrame(rows).T
    if base["net_pnl"] > 0:
        out["pnl_vs_base"] = out["net_pnl"] / base["net_pnl"] - 1
        worst = out["pnl_vs_base"].iloc[1:].min()
        out.attrs["fragile"] = bool(worst < -0.30)
    return out


def _rebase_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Rebuild cumulative columns for a subset of days (fresh ₹1Cr base)."""
    d = daily.copy()
    d["Cumulative_PnL"] = d["Daily_PnL"].cumsum()
    d["Running_Capital"] = TOTAL_CAPITAL + d["Cumulative_PnL"]
    return d


def vix_regime_split(trades: pd.DataFrame, daily: pd.DataFrame,
                     vix_daily_open: pd.Series) -> pd.DataFrame:
    """9.4: split OOS days by that day's first available (lagged) VIX."""
    hi_days = set(vix_daily_open[vix_daily_open > VIX_REGIME_SPLIT].index)
    day = trades["entry_dt"].dt.normalize()
    rows = {}
    for label, mask_days in [(f"VIX>{VIX_REGIME_SPLIT}", hi_days),
                             (f"VIX<={VIX_REGIME_SPLIT}",
                              set(vix_daily_open.index) - hi_days)]:
        tr = trades[day.isin(mask_days)]
        d = _rebase_daily(daily[daily.index.isin(mask_days)])
        rows[label] = _key_metrics(tr, d) if len(tr) else {"n_trades": 0}
    return pd.DataFrame(rows).T


def random_removal_mc(trades: pd.DataFrame) -> dict:
    """9.5: remove 10% of trades at random, 100 iterations."""
    rng = np.random.default_rng(RANDOM_SEED)
    pnls = trades["net_pnl"].to_numpy()
    totals = []
    keep_n = int(len(pnls) * (1 - MC_REMOVAL_FRAC))
    for _ in range(MC_ITERATIONS):
        sample = rng.choice(pnls, size=keep_n, replace=False)
        totals.append(sample.sum())
    totals = np.array(totals)
    return {"full_net_pnl": float(pnls.sum()),
            "mc_median": float(np.median(totals)),
            "mc_p5": float(np.percentile(totals, 5)),
            "mc_p95": float(np.percentile(totals, 95))}
