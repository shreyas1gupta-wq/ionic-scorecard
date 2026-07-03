"""All 8 spec visualisations (S8), saved as PNGs to results/charts/."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import daily_returns, drawdown_series  # noqa: E402
from config import RESULTS_DIR, RISK_FREE_RATE, TRADING_DAYS_PER_YEAR  # noqa: E402

CHARTS_DIR = RESULTS_DIR / "charts"


def _save(fig: plt.Figure, name: str) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    p = CHARTS_DIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def all_charts(trades: pd.DataFrame, daily: pd.DataFrame,
               oos_start: pd.Timestamp | None = None) -> list[Path]:
    paths = []
    d = daily.copy()
    d.index = pd.DatetimeIndex(d.index)

    # 1 equity curve
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(d.index, d["Running_Capital"] / 1e7, lw=0.9)
    if oos_start is not None:
        ax.axvline(oos_start, color="red", ls="--", lw=1)
        ax.text(oos_start, ax.get_ylim()[1], " OOS", color="red", va="top")
    ax.set_title("Equity curve (Running Capital, Rs.Cr)")
    ax.set_ylabel("Rs. Crore")
    paths.append(_save(fig, "01_equity_curve"))

    # 2 underwater drawdown
    dd = drawdown_series(d)
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.fill_between(d.index, dd * 100, 0, color="firebrick", alpha=0.6)
    ax.set_title("Drawdown (%)")
    paths.append(_save(fig, "02_drawdown"))

    # 3 daily P&L histogram + normal overlay
    pnl = d["Daily_PnL"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(pnl, bins=80, density=True, alpha=0.7)
    x = np.linspace(pnl.min(), pnl.max(), 300)
    mu, sd = pnl.mean(), pnl.std()
    if sd > 0:
        ax.plot(x, np.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi)),
                "r-", lw=1.5, label=f"Normal(mu={mu:,.0f}, sd={sd:,.0f})")
    ax.legend()
    ax.set_title("Daily P&L distribution")
    paths.append(_save(fig, "03_daily_pnl_hist"))

    # 4 monthly P&L heatmap
    m = d["Daily_PnL"].groupby([d.index.year, d.index.month]).sum().unstack() / 1e5
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(m.values, cmap="RdYlGn", aspect="auto",
                   vmin=-np.nanmax(np.abs(m.values)), vmax=np.nanmax(np.abs(m.values)))
    ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(len(m.index)), m.index)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, label="Rs. Lakh")
    ax.set_title("Monthly net P&L (Rs. Lakh)")
    paths.append(_save(fig, "04_monthly_heatmap"))

    # 5 trades/day distribution
    fig, ax = plt.subplots(figsize=(8, 4.5))
    tpd = trades.groupby(trades["entry_dt"].dt.normalize()).size()
    ax.hist(tpd, bins=range(0, int(tpd.max()) + 2), alpha=0.8)
    ax.set_title(f"Trades per day (mean {tpd.mean():.1f})")
    paths.append(_save(fig, "05_trades_per_day"))

    # 6 win rate by signal
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ws = trades.groupby("signal").apply(lambda x: (x["net_pnl"] > 0).mean(),
                                        include_groups=False)
    ax.bar(ws.index, ws.values * 100)
    ax.axhline(55, color="red", ls="--", lw=1, label="55% target")
    ax.set_title("Win rate by signal (%)")
    ax.legend()
    paths.append(_save(fig, "06_winrate_by_signal"))

    # 7 rolling 30-day Sharpe
    r = daily_returns(d)
    roll_mean = r.rolling(30).mean() * TRADING_DAYS_PER_YEAR
    roll_vol = r.rolling(30).std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (roll_mean - RISK_FREE_RATE) / roll_vol.replace(0, np.nan)
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(d.index, sharpe, lw=0.8)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title("Rolling 30-day Sharpe (annualised)")
    paths.append(_save(fig, "07_rolling_sharpe"))

    # 8 Kelly fraction evolution
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(trades["entry_dt"], trades["kelly_f"], lw=0.6)
    ax.set_title("Fractional Kelly (0.25 x f*) used per trade")
    paths.append(_save(fig, "08_kelly_fraction"))

    return paths
