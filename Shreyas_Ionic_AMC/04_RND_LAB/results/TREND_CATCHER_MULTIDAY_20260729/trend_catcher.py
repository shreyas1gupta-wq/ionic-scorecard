"""Multi-day Trend Catcher long-options backtest. See PRE_REGISTRATION.md in this folder
for the locked design (signals, grid, exit menu, staging, thresholds). Do not change any
grid/threshold here without logging the deviation in SUMMARY.md.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import chain                       # noqa: E402
from engine import _costs, STEP    # noqa: E402
import guards as G                 # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "TREND_CATCHER_MULTIDAY_20260729"
TRADES_DIR = OUT / "trades"
TRADES_DIR.mkdir(parents=True, exist_ok=True)

LOT_SIZE = 75
CAPITAL = 3_00_000.0
RISK_PER_TRADE = 0.03
SLIPPAGE = 0.005
STOP_PCT = 0.40
TRAIL_PCT = 0.35
ENTRY_HHMM = (9, 20)
SQUARE_HHMM = (15, 15)
INTRINSIC_CUTOFF_HHMM = (15, 25)

WARMUP_DAYS = 60
BUILD_START = dt.date(2021, 8, 17)
BUILD_END = dt.date(2025, 12, 31)
FWD_START = dt.date(2026, 1, 1)
FWD_END = dt.date(2026, 6, 3)

DTE_BUCKETS = {"b1_8_12": (8, 12), "b2_15_22": (15, 22), "b3_25_35": (25, 35)}
STRIKES = ["ITM1", "ATM", "OTM1"]
HOLD_RULES = ["reversal", "N5", "N10", "N20", "trail35"]
SIGNAL_NAMES = ["ema_cross", "breakout20", "sweep_priorweek_reclaim"]


# ---------------------------------------------------------------------------
# daily bars + signals (all lookback-only; signal on CLOSE, entry NEXT session)
# ---------------------------------------------------------------------------
def daily_bars(spot: pd.DataFrame) -> pd.DataFrame:
    s = spot[spot.index.time >= dt.time(9, 15)]
    g = s.groupby(s.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                      "low": g["low"].min(), "close": g["close"].last()})
    d.index = pd.to_datetime(d.index)
    return d.sort_index()


def sig_ema_cross(d: pd.DataFrame) -> pd.Series:
    ema = d["close"].ewm(span=50, adjust=False).mean()
    up = (d["close"] > ema) & (d["close"].shift(1) <= ema.shift(1))
    dn = (d["close"] < ema) & (d["close"].shift(1) >= ema.shift(1))
    out = pd.Series(np.nan, index=d.index)
    out[up] = 1
    out[dn] = -1
    return out.dropna()


def sig_breakout20(d: pd.DataFrame) -> pd.Series:
    hh = d["high"].rolling(20).max().shift(1)
    ll = d["low"].rolling(20).min().shift(1)
    up = d["close"] > hh
    dn = d["close"] < ll
    out = pd.Series(np.nan, index=d.index)
    out[up] = 1
    out[dn] = -1
    return out.dropna()


def sig_sweep_priorweek(d: pd.DataFrame) -> pd.Series:
    wk = d.copy()
    wk["period"] = wk.index.to_period("W-FRI")
    wk_agg = wk.groupby("period").agg(high=("high", "max"), low=("low", "min"))
    periods = list(wk_agg.index)
    prior = {periods[i]: wk_agg.iloc[i - 1] for i in range(1, len(periods))}
    out = pd.Series(np.nan, index=d.index)
    for ts, row in d.iterrows():
        p = pd.Timestamp(ts).to_period("W-FRI")
        if p not in prior:
            continue
        ph, pl = prior[p]["high"], prior[p]["low"]
        if row["high"] > ph and row["close"] < ph:
            out.loc[ts] = -1
        elif row["low"] < pl and row["close"] > pl:
            out.loc[ts] = 1
    return out.dropna()


SIGNALS = {"ema_cross": sig_ema_cross, "breakout20": sig_breakout20,
           "sweep_priorweek_reclaim": sig_sweep_priorweek}


def trigger_stream(d: pd.DataFrame, signal_name: str) -> list[tuple[dt.date, int]]:
    raw = SIGNALS[signal_name](d)
    all_days = list(d.index.date)
    pos = {dd: i for i, dd in enumerate(all_days)}
    out: dict[dt.date, int] = {}
    for ts, direction in raw.items():
        dd = pd.Timestamp(ts).date()
        i = pos[dd]
        if i + 1 < len(all_days):
            out[all_days[i + 1]] = int(direction)
    return sorted(out.items())


# ---------------------------------------------------------------------------
# instrument selection + single-trade simulation
# ---------------------------------------------------------------------------
def _atm(spot0: float) -> int:
    return int(round(spot0 / STEP) * STEP)


def _strike_for(spot0: float, direction: int, strike_choice: str) -> int:
    atm = _atm(spot0)
    if strike_choice == "ATM":
        return atm
    if direction == 1:      # CE: ITM = lower strike, OTM = higher strike
        return atm - STEP if strike_choice == "ITM1" else atm + STEP
    else:                   # PE: ITM = higher strike, OTM = lower strike
        return atm + STEP if strike_choice == "ITM1" else atm - STEP


def _leg(df: pd.DataFrame, strike: int, otype: str) -> pd.DataFrame:
    s = df[(df["strike"] == strike) & (df["option_type"] == otype)]
    return s.set_index("t")[["open", "high", "low", "close"]].sort_index()


def _nth_trading_day(all_days: list[dt.date], entry_date: dt.date, n: int):
    pos = {dd: i for i, dd in enumerate(all_days)}
    if entry_date not in pos:
        return None
    i = pos[entry_date] + n
    return all_days[i] if i < len(all_days) else None


def simulate_trade(spot: pd.DataFrame, all_days: list[dt.date], entry_date: dt.date,
                    direction: int, dte_bucket: tuple[int, int], strike_choice: str,
                    hold_rule: str, reversal_target) -> dict | None:
    lo, hi = dte_bucket
    exp = chain.nearest_expiry(entry_date, lo, hi)
    if exp is None:
        return None
    df = chain.load_expiry(exp)
    et = pd.Timestamp(entry_date) + pd.Timedelta(hours=ENTRY_HHMM[0], minutes=ENTRY_HHMM[1])
    row0 = spot[spot.index <= et]
    if row0.empty or row0.index[-1].date() != entry_date:
        return None
    s0 = row0["close"].iloc[-1]
    otype = "CE" if direction == 1 else "PE"
    avail = sorted(df["strike"].unique())
    if not avail:
        return None
    k_target = _strike_for(s0, direction, strike_choice)
    k = min(avail, key=lambda x: abs(x - k_target))
    leg = _leg(df, k, otype)
    leg = leg[leg.index >= et]
    if leg.empty:
        return None
    entry_bar = leg.index[0]
    # CRITICAL GUARD: the option FILE's own recorded history may start later than the
    # intended entry_date (many "15-22"/"25-35" DTE matches are only satisfied by a file
    # whose earliest recorded row is days after entry_date). Silently taking leg.index[0]
    # in that case fabricates an entry on the WRONG, LATER date at a materially different
    # true DTE. Refuse: no valid instrument was actually available at the intended time.
    if entry_bar.date() != entry_date:
        return None
    entry_raw = leg.iloc[0]["open"]
    if not np.isfinite(entry_raw) or entry_raw <= 0:
        return None
    entry_fill = entry_raw * (1 + SLIPPAGE)

    target_day = None
    if hold_rule.startswith("N"):
        target_day = _nth_trading_day(all_days, entry_date, int(hold_rule[1:]))
    elif hold_rule == "reversal":
        target_day = reversal_target

    stop_level = entry_fill * (1 - STOP_PCT)
    peak = entry_fill
    close_s = leg["close"]
    cutoff = pd.Timestamp(exp) + pd.Timedelta(hours=INTRINSIC_CUTOFF_HHMM[0],
                                               minutes=INTRINSIC_CUTOFF_HHMM[1])

    exit_t = exit_val = reason = None
    for t, val in close_s.items():
        if t <= entry_bar:
            continue
        d_ = t.date()
        if d_ == exp and t >= cutoff:
            ssp = spot[spot.index <= cutoff]
            s_final = ssp["close"].iloc[-1] if not ssp.empty else s0
            intrinsic = max(direction * (s_final - k), 0.0)
            exit_t, exit_val, reason = t, intrinsic, "expiry_intrinsic"
            break
        if val <= stop_level:
            exit_t, exit_val, reason = t, val, "stop"
            break
        if hold_rule == "trail35":
            peak = max(peak, val)
            if peak > entry_fill and val <= peak * (1 - TRAIL_PCT):
                exit_t, exit_val, reason = t, val, "trail"
                break
        elif hold_rule in ("N5", "N10", "N20", "reversal"):
            if target_day is not None and d_ >= target_day:
                sq = pd.Timestamp(d_) + pd.Timedelta(hours=SQUARE_HHMM[0], minutes=SQUARE_HHMM[1])
                if t >= sq:
                    exit_t, exit_val = t, val
                    reason = "reversal" if hold_rule == "reversal" else "holdrule_time"
                    break
    if exit_t is None:
        exit_t, exit_val, reason = close_s.index[-1], float(close_s.iloc[-1]), "data_end"

    exit_fill = max(exit_val, 0.0) * (1 - SLIPPAGE) if reason != "expiry_intrinsic" else max(exit_val, 0.0)
    outlay_per_lot = entry_fill * LOT_SIZE
    lots = max(1, int((RISK_PER_TRADE * CAPITAL) // max(outlay_per_lot, 1)))
    qty = lots * LOT_SIZE
    gross = (exit_fill - entry_fill) * qty
    costs = _costs(entry_fill, exit_fill, lots, LOT_SIZE, False)
    net_pnl = gross - costs
    return {
        "entry_date": entry_date, "direction": direction, "otype": otype, "strike": k,
        "exp": exp, "dte0": (exp - entry_date).days, "entry_t": entry_bar, "exit_t": exit_t,
        "exit_date": exit_t.date(), "reason": reason, "entry_fill": entry_fill,
        "exit_val": exit_val, "exit_fill": exit_fill, "lots": lots, "qty": qty,
        "gross": gross, "costs": costs, "net_pnl": net_pnl,
        "ret_pct": exit_fill / entry_fill - 1,
        "hold_days": (exit_t.date() - entry_date).days,
    }


# ---------------------------------------------------------------------------
# sequential (non-overlapping) trade construction per cell
# ---------------------------------------------------------------------------
def build_trades(signal_name: str, dte_bucket, strike_choice: str, hold_rule: str,
                  d: pd.DataFrame, spot: pd.DataFrame, all_days: list[dt.date],
                  window_start: dt.date, window_end: dt.date) -> tuple[pd.DataFrame, dict]:
    stream = trigger_stream(d, signal_name)
    rows = []
    skipped_no_expiry = 0
    next_avail = window_start
    n = len(stream)
    for i in range(n):
        edate, edir = stream[i]
        if edate < next_avail or edate > window_end:
            continue
        rtarget = None
        if hold_rule == "reversal":
            for j in range(i + 1, n):
                if stream[j][1] != edir:
                    rtarget = stream[j][0]
                    break
        try:
            tr = simulate_trade(spot, all_days, edate, edir, dte_bucket, strike_choice,
                                 hold_rule, rtarget)
        except Exception as e:
            print(f"  ERR {edate} {signal_name}/{hold_rule}: {type(e).__name__}: {e}")
            tr = None
        if tr is not None:
            tr["signal"] = signal_name
            tr["dte_bucket"] = f"{dte_bucket[0]}-{dte_bucket[1]}"
            tr["strike_choice"] = strike_choice
            tr["hold_rule"] = hold_rule
            rows.append(tr)
            next_avail = tr["exit_date"] + dt.timedelta(days=1)
        else:
            skipped_no_expiry += 1
            next_avail = edate + dt.timedelta(days=1)
    meta = {"n_triggers_in_window": sum(1 for e, _ in stream if window_start <= e <= window_end),
            "n_trades": len(rows), "skipped_no_valid_leg": skipped_no_expiry}
    return pd.DataFrame(rows), meta


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def nw_tstat(x: pd.Series, maxlags: int | None = None) -> float:
    x = pd.Series(x).dropna().values
    n = len(x)
    if n < 5:
        return float("nan")
    if maxlags is None:
        maxlags = max(1, int(4 * (n / 100) ** (2 / 9)))
    X = np.ones((n, 1))
    model = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return float(model.tvalues[0])


def equity_curve(trades: pd.DataFrame, start: dt.date, end: dt.date, capital: float,
                  pnl_col: str = "net_pnl") -> pd.Series:
    days = pd.date_range(start, end, freq="D")
    if trades.empty:
        return pd.Series(capital, index=days)
    pnl_by_exit = trades.groupby("exit_date")[pnl_col].sum()
    cap = capital
    curve = []
    for dday in days:
        dd = dday.date()
        if dd in pnl_by_exit.index:
            cap += pnl_by_exit.loc[dd]
        curve.append(cap)
    return pd.Series(curve, index=days)


def perf_stats(trades: pd.DataFrame, start: dt.date, end: dt.date, capital: float,
               pnl_col: str = "net_pnl") -> dict:
    if trades.empty:
        return {"n": 0}
    eq = equity_curve(trades, start, end, capital, pnl_col)
    yrs = max((end - start).days / 365.25, 1e-9)
    cagr = (eq.iloc[-1] / capital) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    ret = eq.pct_change().dropna()
    sharpe = (ret.mean() / (ret.std() + 1e-12)) * np.sqrt(252) if ret.std() > 0 else float("nan")
    calmar = cagr / abs(dd) if dd < 0 else float("nan")
    wins = trades[trades[pnl_col] > 0][pnl_col]
    losses = trades[trades[pnl_col] <= 0][pnl_col]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    t = trades[pnl_col]
    tot = t.sum()
    grosswin = wins.sum()
    top1 = t.max()
    top4 = t.nlargest(min(4, len(t))).sum()
    m = trades.copy()
    m["month"] = pd.to_datetime(m["exit_date"]).dt.to_period("M")
    monthly_pnl = m.groupby("month")[pnl_col].sum()
    return {
        "n": len(trades), "cagr": cagr, "maxdd": dd, "calmar": calmar, "sharpe": sharpe,
        "pf": pf, "win_rate": float((t > 0).mean()), "total_pnl": float(tot),
        "nw_t_retpct": nw_tstat(trades["ret_pct"]) if "ret_pct" in trades else float("nan"),
        "top1_share_of_total": float(top1 / tot) if tot != 0 else float("nan"),
        "top4_share_of_total": float(top4 / tot) if tot != 0 else float("nan"),
        "top1_share_of_grosswin": float(top1 / grosswin) if grosswin != 0 else float("nan"),
        "top4_share_of_grosswin": float(top4 / grosswin) if grosswin != 0 else float("nan"),
        "monthly_win_rate": float((monthly_pnl > 0).mean()) if len(monthly_pnl) else float("nan"),
        "n_months": len(monthly_pnl),
    }


def deflated_sharpe(sr: float, n_obs: int, n_trials: int, sr_std_trials: float,
                     skew: float, kurt_excess: float) -> float:
    """Bailey & Lopez de Prado (2014). kurt_excess = pandas .kurtosis() (normal=0)."""
    if n_trials <= 1 or sr_std_trials <= 0 or n_obs < 5:
        return float("nan")
    gamma = 0.5772156649
    sr0 = sr_std_trials * ((1 - gamma) * norm.ppf(1 - 1.0 / n_trials) +
                           gamma * norm.ppf(1 - 1.0 / (n_trials * np.e)))
    kurt = kurt_excess + 3.0
    denom = np.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    z = (sr - sr0) * np.sqrt(n_obs - 1) / denom
    return float(norm.cdf(z))


if __name__ == "__main__":
    print("trend_catcher.py loaded OK — use run_stages.py to execute the pre-registered plan.")
