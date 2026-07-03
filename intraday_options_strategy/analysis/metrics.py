"""Full performance metrics suite (spec S8)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RISK_FREE_RATE, TOTAL_CAPITAL, TRADING_DAYS_PER_YEAR  # noqa: E402


def daily_returns(daily: pd.DataFrame) -> pd.Series:
    prev = daily["Running_Capital"].shift(1).fillna(TOTAL_CAPITAL)
    return daily["Daily_PnL"] / prev


def drawdown_series(daily: pd.DataFrame) -> pd.Series:
    cap = daily["Running_Capital"]
    peak = cap.cummax()
    return (cap - peak) / peak


def full_metrics(trades: pd.DataFrame, daily: pd.DataFrame,
                 capital0: float = TOTAL_CAPITAL) -> dict:
    ret = daily_returns(daily)
    n_days = len(daily)
    years = n_days / TRADING_DAYS_PER_YEAR
    cap_end = daily["Running_Capital"].iloc[-1]

    net_pnl = cap_end - capital0
    cagr = (cap_end / capital0) ** (1 / years) - 1 if years > 0 else 0.0
    gross_end = capital0 + daily["Gross_PnL"].cumsum().iloc[-1]
    gross_cagr = (max(gross_end, 1.0) / capital0) ** (1 / years) - 1 if years > 0 else 0.0

    dd = drawdown_series(daily)
    max_dd = float(-dd.min())
    cap = daily["Running_Capital"]
    peak_idx = cap.cummax()
    # drawdown duration: longest run of days below previous peak
    below = cap < peak_idx
    runs, cur = [], 0
    for b in below:
        cur = cur + 1 if b else 0
        runs.append(cur)
    dd_dur = int(max(runs)) if runs else 0

    vol_ann = float(ret.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR))
    mean_ann = float(ret.mean() * TRADING_DAYS_PER_YEAR)
    sharpe = (mean_ann - RISK_FREE_RATE) / vol_ann if vol_ann > 1e-12 else 0.0
    downside = ret[ret < 0]
    dvol = float(downside.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR))
    sortino = (mean_ann - RISK_FREE_RATE) / dvol if dvol > 1e-12 else 0.0
    calmar = cagr / max_dd if max_dd > 1e-12 else 0.0

    var95 = float(-np.percentile(ret, 5) * capital0)
    var99 = float(-np.percentile(ret, 1) * capital0)

    wins = trades["net_pnl"] > 0
    gw = float(trades.loc[wins, "net_pnl"].sum())
    gl = float(-trades.loc[~wins, "net_pnl"].sum())
    avg_w = float(trades.loc[wins, "net_pnl"].mean()) if wins.any() else 0.0
    avg_l = float(-trades.loc[~wins, "net_pnl"].mean()) if (~wins).any() else 0.0
    tpd = trades.groupby(trades["entry_dt"].dt.normalize()).size()

    return {
        # returns
        "net_pnl": float(net_pnl), "net_pnl_pct": float(net_pnl / capital0),
        "cagr_net": float(cagr), "cagr_gross": float(gross_cagr),
        # risk
        "max_dd_pct": max_dd, "max_dd_rs": float(max_dd * cap.cummax().max()),
        "max_dd_duration_days": dd_dur,
        "var95_daily_rs": var95, "var99_daily_rs": var99, "ann_vol": vol_ann,
        # risk-adjusted
        "sharpe": float(sharpe), "sortino": float(sortino), "calmar": float(calmar),
        # trades
        "n_trades": int(len(trades)),
        "trades_per_day_avg": float(tpd.mean()) if len(tpd) else 0.0,
        "trades_per_day_med": float(tpd.median()) if len(tpd) else 0.0,
        "trades_per_day_max": int(tpd.max()) if len(tpd) else 0,
        "win_rate": float(wins.mean()) if len(trades) else 0.0,
        "avg_win_rs": avg_w, "avg_loss_rs": avg_l,
        "profit_factor": gw / gl if gl > 0 else np.inf,
        "risk_reward": avg_w / avg_l if avg_l > 0 else np.inf,
        "avg_hold_min": float(trades["hold_min"].mean()) if len(trades) else 0.0,
        "best_day_rs": float(daily["Daily_PnL"].max()),
        "worst_day_rs": float(daily["Daily_PnL"].min()),
        "pct_days_profitable": float((daily["Daily_PnL"] > 0).mean()),
        # costs
        "total_costs_rs": float(trades["costs"].sum() + trades["slippage_cost"].sum()),
        "explicit_costs_rs": float(trades["costs"].sum()),
        "slippage_rs": float(trades["slippage_cost"].sum()),
        "cost_pct_of_gross": float((trades["costs"].sum() + trades["slippage_cost"].sum())
                                   / abs(trades["gross_pnl"].sum()))
        if len(trades) and trades["gross_pnl"].sum() != 0 else np.nan,
        "avg_cost_per_trade": float((trades["costs"].sum() + trades["slippage_cost"].sum())
                                    / len(trades)) if len(trades) else 0.0,
        # greeks exposure
        "avg_abs_delta": float(trades["delta"].abs().mean()) if len(trades) else 0.0,
        "avg_theta_day": float(trades["theta_day"].mean()) if len(trades) else 0.0,
    }


def by_signal(trades: pd.DataFrame) -> pd.DataFrame:
    g = trades.groupby("signal")
    out = pd.DataFrame({
        "trades": g.size(),
        "win_rate": g.apply(lambda x: (x["net_pnl"] > 0).mean(), include_groups=False),
        "net_pnl": g["net_pnl"].sum(),
        "avg_pnl": g["net_pnl"].mean(),
        "avg_hold_min": g["hold_min"].mean(),
    })
    return out.sort_values("net_pnl", ascending=False)


def format_report(m: dict, title: str) -> str:
    L = [f"═══ {title} ═══",
         f"Net P&L          : Rs.{m['net_pnl']:>14,.0f}  ({m['net_pnl_pct']:+.1%})",
         f"CAGR net / gross : {m['cagr_net']:+.2%} / {m['cagr_gross']:+.2%}",
         f"Max DD           : {m['max_dd_pct']:.2%} (Rs.{m['max_dd_rs']:,.0f}), "
         f"{m['max_dd_duration_days']} days",
         f"VaR 95/99 (daily): Rs.{m['var95_daily_rs']:,.0f} / Rs.{m['var99_daily_rs']:,.0f}",
         f"Ann vol          : {m['ann_vol']:.2%}",
         f"Sharpe/Sortino/Calmar: {m['sharpe']:.2f} / {m['sortino']:.2f} / {m['calmar']:.2f}",
         f"Trades           : {m['n_trades']} "
         f"({m['trades_per_day_avg']:.1f}/day avg, med {m['trades_per_day_med']:.0f}, "
         f"max {m['trades_per_day_max']})",
         f"Win rate         : {m['win_rate']:.1%}   PF: {m['profit_factor']:.2f}   "
         f"R:R: {m['risk_reward']:.2f}",
         f"Avg win/loss     : Rs.{m['avg_win_rs']:,.0f} / Rs.{m['avg_loss_rs']:,.0f}   "
         f"hold {m['avg_hold_min']:.0f} min",
         f"Best/worst day   : Rs.{m['best_day_rs']:,.0f} / Rs.{m['worst_day_rs']:,.0f}   "
         f"days +ve: {m['pct_days_profitable']:.0%}",
         f"Costs            : Rs.{m['total_costs_rs']:,.0f} "
         f"(explicit Rs.{m['explicit_costs_rs']:,.0f} + slip Rs.{m['slippage_rs']:,.0f}; "
         f"avg Rs.{m['avg_cost_per_trade']:,.0f}/trade)",
         f"Avg |delta|      : {m['avg_abs_delta']:.2f}   avg theta/day: "
         f"Rs.{m['avg_theta_day']:,.1f} (per unit)"]
    return "\n".join(L)
