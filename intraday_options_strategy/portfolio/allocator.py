"""Portfolio layer: combine sleeve trade streams (simulated at 1 lot) into a
single equity curve with vol-parity weights, Kelly caps, margin caps and a
drawdown governor. All statistics are trailing (no lookahead).

Sizing chain per day:
  budget = equity × RISK_BUDGET × governor_mult
  sleeve weight ∝ 1/vol_60d × 1{sharpe_60d > SHARPE_KILL}, capped at 50%
  sleeve lots  = floor(weight × budget / Σ max_loss_per_lot of its trades)
  lots capped by 0.25×Kelly (per sleeve trailing stats) and MAX_LOTS_LEG,
  shorts also by total margin ≤ MARGIN_CAP × equity.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import TOTAL_CAPITAL  # noqa: E402

RISK_BUDGET = 0.006          # 0.6% of equity at risk per day (sum of stops)
MAX_WEIGHT = 0.50
MAX_LOTS_LEG = 10
MARGIN_CAP = 0.60
SHARPE_KILL = -1.0           # disable sleeve if trailing 60d Sharpe below
KELLY_MULT = 0.25
ROLL = 60
DD_STEPS = ((0.08, 0.25), (0.04, 0.5))   # (trigger, multiplier), descending


def _kelly_lots_cap(pnls: list[float], max_loss: float) -> int:
    if len(pnls) < 30 or max_loss <= 0:
        return 1
    arr = np.asarray(pnls)
    wins, losses = arr[arr > 0], -arr[arr <= 0]
    if not len(wins) or not len(losses):
        return MAX_LOTS_LEG if len(wins) else 0
    w = len(wins) / len(arr)
    f = (w * wins.mean() - (1 - w) * losses.mean()) / wins.mean()
    if f <= 0:
        return 0
    # capital fraction at risk ≤ 0.25 f*  →  lots ≤ 0.25 f* × eq / max_loss
    return int(np.floor(KELLY_MULT * f * _kelly_lots_cap.equity / max_loss))


def run_portfolio(sleeve_trades: pd.DataFrame, trading_days: pd.DatetimeIndex,
                  capital0: float = TOTAL_CAPITAL) -> tuple[pd.DataFrame, pd.DataFrame]:
    """sleeve_trades: engine_v2 rows for ALL sleeves (1-lot sims).
    Returns (portfolio_daily, scaled_trades)."""
    tr = sleeve_trades.sort_values("entry_dt").copy()
    tr["day"] = tr["entry_dt"].dt.normalize()
    sleeves = sorted(tr["sleeve"].unique())
    hist: dict[str, list[tuple[pd.Timestamp, float]]] = {s: [] for s in sleeves}

    equity = capital0
    eq_hist: list[float] = []
    governor, rows, scaled = 1.0, [], []

    by_day = dict(tuple(tr.groupby("day")))
    for d in trading_days:
        # --- drawdown governor (trailing 20d, hysteresis at half-trigger) ---
        if len(eq_hist) >= 2:
            peak = max(eq_hist[-20:])
            dd = 1 - equity / peak
            new_g = 1.0
            for trig, mult in DD_STEPS:
                if dd > trig:
                    new_g = mult
                    break
            if new_g < governor:
                governor = new_g
            elif governor < 1.0:
                trig_for = next((t for t, m in DD_STEPS if m == governor), 0.04)
                if dd < trig_for / 2:
                    governor = min(1.0, governor * 2)

        day_pnl = 0.0
        todays = by_day.get(d)
        if todays is not None:
            # --- trailing sleeve stats (strictly before today) ---
            stats = {}
            for s in sleeves:
                pnls = [p for dt_, p in hist[s] if dt_ < d][-ROLL * 3:]
                if len(pnls) >= 10:
                    arr = np.asarray(pnls[-ROLL:])
                    vol = arr.std(ddof=0)
                    shp = arr.mean() / vol if vol > 1e-9 else 0.0
                else:
                    vol, shp = np.nan, 0.0
                stats[s] = (vol, shp, pnls)
            inv_vol = {s: (1.0 / stats[s][0]) if stats[s][0] and not np.isnan(stats[s][0])
                       else 1.0 for s in sleeves}
            alive = {s for s in sleeves if stats[s][1] > SHARPE_KILL or
                     len(stats[s][2]) < 30}
            present = [s for s in todays["sleeve"].unique() if s in alive]
            wsum = sum(inv_vol[s] for s in present) or 1.0
            weights = {s: min(MAX_WEIGHT, inv_vol[s] / wsum) for s in present}

            budget = equity * RISK_BUDGET * governor
            margin_used = 0.0
            for s in present:
                sub = todays[todays["sleeve"] == s]
                tot_maxloss = sub["max_loss_per_lot"].sum()
                if tot_maxloss <= 0:
                    continue
                lots = int(np.floor(weights[s] * budget / tot_maxloss))
                _kelly_lots_cap.equity = equity
                kcap = _kelly_lots_cap(stats[s][2],
                                       float(sub["max_loss_per_lot"].mean()))
                lots = max(0, min(lots, kcap, MAX_LOTS_LEG))
                if lots == 0:
                    continue
                for _, t in sub.iterrows():
                    if t["side"] == -1:
                        need = t["margin_per_lot"] * lots
                        if margin_used + need > MARGIN_CAP * equity:
                            lots_adj = int((MARGIN_CAP * equity - margin_used)
                                           // t["margin_per_lot"])
                            if lots_adj < 1:
                                continue
                            need = t["margin_per_lot"] * lots_adj
                        else:
                            lots_adj = lots
                        margin_used += need
                    else:
                        lots_adj = lots
                    pnl = t["pnl_per_lot"] * lots_adj - t["fixed_cost"]
                    day_pnl += pnl
                    scaled.append({**t.to_dict(), "lots": lots_adj,
                                   "net_pnl": pnl, "weight": weights[s],
                                   "governor": governor})
            # record 1-lot pnl into history AFTER sizing (no lookahead)
            for _, t in todays.iterrows():
                hist[t["sleeve"]].append((d, t["pnl_per_lot"] - t["fixed_cost"]))

        equity += day_pnl
        eq_hist.append(equity)
        rows.append({"Date": d, "Daily_PnL": day_pnl, "Running_Capital": equity,
                     "governor": governor})

    daily = pd.DataFrame(rows).set_index("Date")
    daily["Cumulative_PnL"] = daily["Daily_PnL"].cumsum()
    return daily, pd.DataFrame(scaled)
