"""SWING (multi-day) delta-1 NIFTY futures arm. Daily-bar signals, next-session-open
entries, 5-way exit grid, era-correct futures costs, fixed-fractional risk sizing that
cannot drive equity negative. Spec: PRE_REGISTRATION.md (read that first; this script
implements it verbatim, no post-hoc changes).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OUT = Path(__file__).parent
NIFTY_INDEX = Path(
    r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
    r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m"
    r"\index\NIFTY.parquet"
)

BUILD_END = dt.date(2025, 12, 31)
LOT = 75
BOOK_EQUITY0 = 1.0e7          # Rs1cr, RISK_LIMITS D-026 paper-book convention
RISK_FRAC = 0.01              # 1% of current equity per position (RISK_LIMITS)
STOP_ATR_MULT = 3.0
MARGIN_FRAC_OF_NOTIONAL = 0.15
MARGIN_CAP_OF_EQUITY = 0.50   # single-position margin usage cap
STT_HIKE_DATE = dt.date(2024, 10, 1)
COST_PTS_PRE = 4.47 + 0.5     # 4.97
COST_PTS_POST = 5.97 + 0.5    # 6.47
HAIRCUT_CAP_FRAC = 0.03       # single-trade loss floor, % of equity-at-entry
N_DAYS_GRID = (5, 10, 20)


# ---------------------------------------------------------------- data / indicators
def load_daily() -> pd.DataFrame:
    df = pq.read_table(NIFTY_INDEX).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").set_index("t").sort_index()
    tod = df.index.time
    df = df[(tod >= dt.time(9, 15)) & (tod <= dt.time(15, 30))]   # landmine #2
    rows = []
    for d, day in df.groupby(df.index.date):
        rows.append({"date": d, "open": float(day["open"].iloc[0]),
                     "high": float(day["high"].max()), "low": float(day["low"].min()),
                     "close": float(day["close"].iloc[-1])})
    daily = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    return daily


def wilder_atr(daily: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = daily["high"], daily["low"], daily["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_indicators(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    c = d["close"]
    d["sma50"] = c.rolling(50).mean()
    d["sma150"] = c.rolling(150).mean()
    d["sma200"] = c.rolling(200).mean()
    d["sma200_22ago"] = d["sma200"].shift(22)
    d["ema20"] = c.ewm(span=20, adjust=False).mean()
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    d["ema50_5ago"] = d["ema50"].shift(5)
    d["atr14"] = wilder_atr(d, 14)
    d["hi252"] = c.rolling(252, min_periods=252).max()
    d["lo252"] = c.rolling(252, min_periods=252).min()
    for L in (20, 50):
        d[f"rollhigh{L}"] = d["high"].rolling(L, min_periods=L).max().shift(1)
        d[f"rolllow{L}"] = d["low"].rolling(L, min_periods=L).min().shift(1)
    # prior COMPLETED ISO week's swing high/low, broadcast to every day of the current week
    iso = pd.to_datetime(d["date"]).apply(lambda x: x.isocalendar()[:2])
    d["iso_year"] = [x[0] for x in iso]
    d["iso_week"] = [x[1] for x in iso]
    wk = (d.groupby(["iso_year", "iso_week"])
            .agg(week_high=("high", "max"), week_low=("low", "min"))
            .reset_index().sort_values(["iso_year", "iso_week"]).reset_index(drop=True))
    wk["prior_week_high"] = wk["week_high"].shift(1)
    wk["prior_week_low"] = wk["week_low"].shift(1)
    d = d.merge(wk[["iso_year", "iso_week", "prior_week_high", "prior_week_low"]],
                on=["iso_year", "iso_week"], how="left")
    d = d.sort_values("date").reset_index(drop=True)   # merge order isn't guaranteed
    assert d["date"].is_monotonic_increasing, "daily index not chronological after merge"
    return d


# ---------------------------------------------------------------- signal families
def build_streams(d: pd.DataFrame) -> dict:
    """Returns {stream_name: (direction, entry_trigger: pd.Series[bool], exit_signal: pd.Series[bool])}
    entry_trigger[t] fires on day t's CLOSE info; execution is at day t+1's open (in simulate()).
    exit_signal[t] is the family's 'signal_reversal' condition, also evaluated at close of day t
    (executed at day t+1's open in simulate(), matching the entry convention)."""
    streams = {}
    c, sma50, sma150, sma200 = d["close"], d["sma50"], d["sma150"], d["sma200"]

    # --- A. Minervini trend template (index-level adaptation; criteria 8,9 dropped, documented)
    long_ok = ((c > sma150) & (c > sma200) & (sma150 > sma200) &
               (d["sma200"] > d["sma200_22ago"]) &
               (sma50 > sma150) & (sma150 > sma200) & (c > sma50) &
               (c >= 1.30 * d["lo252"]) & (c >= 0.75 * d["hi252"]))
    short_ok = ((c < sma150) & (c < sma200) & (sma150 < sma200) &
                (d["sma200"] < d["sma200_22ago"]) &
                (sma50 < sma150) & (sma150 < sma200) & (c < sma50) &
                (c <= 0.70 * d["hi252"]) & (c <= 1.25 * d["lo252"]))
    long_ok = long_ok.fillna(False)
    short_ok = short_ok.fillna(False)
    streams["A_trend_template_long"] = (
        1, long_ok & ~long_ok.shift(1).fillna(False), ~long_ok)
    streams["A_trend_template_short"] = (
        -1, short_ok & ~short_ok.shift(1).fillna(False), ~short_ok)

    # --- B. EMA20/50 regime + pullback
    uptrend = (d["ema20"] > d["ema50"]) & (d["ema50"] > d["ema50_5ago"])
    downtrend = (d["ema20"] < d["ema50"]) & (d["ema50"] < d["ema50_5ago"])
    uptrend, downtrend = uptrend.fillna(False), downtrend.fillna(False)
    pullback_long = uptrend & (c.shift(1) <= d["ema20"].shift(1)) & (c > d["ema20"])
    pullback_short = downtrend & (c.shift(1) >= d["ema20"].shift(1)) & (c < d["ema20"])
    streams["B_ema_pullback_long"] = (1, pullback_long.fillna(False), ~uptrend)
    streams["B_ema_pullback_short"] = (-1, pullback_short.fillna(False), ~downtrend)

    # --- C. 20d / 50d Donchian breakout (prior N sessions, excludes today)
    for L in (20, 50):
        rh, rl = d[f"rollhigh{L}"], d[f"rolllow{L}"]
        fresh_long = (c > rh) & (c.shift(1) <= rh.shift(1))
        fresh_short = (c < rl) & (c.shift(1) >= rl.shift(1))
        streams[f"C_breakout{L}_long"] = (1, fresh_long.fillna(False), (c < rh).fillna(False))
        streams[f"C_breakout{L}_short"] = (-1, fresh_short.fillna(False), (c > rl).fillna(False))

    # --- D. Prior-week sweep + reclaim
    pwh, pwl = d["prior_week_high"], d["prior_week_low"]
    sweep_long = (d["low"] < pwl) & (c > pwl)
    sweep_short = (d["high"] > pwh) & (c < pwh)
    streams["D_priorweek_sweep_long"] = (1, sweep_long.fillna(False), sweep_short.fillna(False))
    streams["D_priorweek_sweep_short"] = (-1, sweep_short.fillna(False), sweep_long.fillna(False))

    return streams


# ---------------------------------------------------------------- cost + sizing
def cost_pts(entry_date: dt.date) -> float:
    return COST_PTS_PRE if entry_date < STT_HIKE_DATE else COST_PTS_POST


def size_position(equity: float, entry_px: float, stop_pts: float):
    if stop_pts <= 0 or not np.isfinite(stop_pts):
        return 0
    risk_rupees = RISK_FRAC * equity
    lots_risk = int(risk_rupees // (stop_pts * LOT))
    margin_per_lot = MARGIN_FRAC_OF_NOTIONAL * entry_px * LOT
    lots_margin = int((MARGIN_CAP_OF_EQUITY * equity) // margin_per_lot) if margin_per_lot > 0 else 0
    return max(0, min(lots_risk, lots_margin))


# ---------------------------------------------------------------- trade simulation
def simulate(d: pd.DataFrame, direction: int, entry_trig: pd.Series, exit_sig: pd.Series,
             exit_cfg: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = len(d)
    dates = d["date"].values
    o, h, l, c = d["open"].values, d["high"].values, d["low"].values, d["close"].values
    atr = d["atr14"].values
    trig = entry_trig.values
    rev = exit_sig.values

    equity = BOOK_EQUITY0
    trades = []
    daily_equity = np.full(n, np.nan)
    haircut_binds = 0

    pos_open = False
    i = 0
    while i < n:
        if not pos_open:
            daily_equity[i] = equity
            if i + 1 < n and trig[i] and np.isfinite(atr[i]) and atr[i] > 0:
                entry_i = i + 1
                entry_px = o[entry_i]
                stop_pts = STOP_ATR_MULT * atr[i]
                lots = size_position(equity, entry_px, stop_pts)
                if lots > 0:
                    hard_stop = entry_px - stop_pts if direction > 0 else entry_px + stop_pts
                    trail_stop = hard_stop
                    run_extreme = entry_px
                    pos_open = True
                    open_entry_i, open_entry_px = entry_i, entry_px
                    open_lots, open_hard_stop, open_trail = lots, hard_stop, trail_stop
                    open_run_extreme = run_extreme
                    equity_at_entry = equity
                    pending_exit_open = False
                    i = entry_i  # jump straight to entry day for exit-scan below
                    continue
            i += 1
            continue

        # --- position is open on day i ---
        stop_level = open_trail if exit_cfg == "atr_trail" else open_hard_stop
        exit_reason, exit_px = None, None

        if pending_exit_open:
            exit_px = o[i]
            exit_reason = "signal_reversal"
        else:
            # 1) intraday stop / trail check (gap-aware fill)
            if direction > 0:
                if l[i] <= stop_level:
                    exit_px = min(o[i], stop_level)
                    exit_reason = "atr_trail_stop" if exit_cfg == "atr_trail" else "hard_stop"
            else:
                if h[i] >= stop_level:
                    exit_px = max(o[i], stop_level)
                    exit_reason = "atr_trail_stop" if exit_cfg == "atr_trail" else "hard_stop"

            if exit_reason is None:
                # 2) exit-config-specific close-based test
                if exit_cfg == "signal_reversal" and rev[i]:
                    pending_exit_open = True   # execute at tomorrow's open
                elif exit_cfg.startswith("fixed_"):
                    ndays = int(exit_cfg.split("_")[1])
                    if i >= open_entry_i + ndays:
                        exit_px = o[i]
                        exit_reason = "fixed_days"
                elif exit_cfg == "atr_trail":
                    # ratchet the trailing stop using TODAY's close + ATR (ready for tomorrow)
                    if direction > 0:
                        open_run_extreme = max(open_run_extreme, c[i])
                        cand = open_run_extreme - STOP_ATR_MULT * atr[i] if np.isfinite(atr[i]) else open_trail
                        open_trail = max(open_trail, cand)
                    else:
                        open_run_extreme = min(open_run_extreme, c[i])
                        cand = open_run_extreme + STOP_ATR_MULT * atr[i] if np.isfinite(atr[i]) else open_trail
                        open_trail = min(open_trail, cand)

        # mark-to-market equity for today (position still open at today's close, or just exited)
        mtm_px = exit_px if exit_px is not None else c[i]
        unreal = direction * (mtm_px - open_entry_px) * LOT * open_lots
        daily_equity[i] = equity + unreal

        if exit_reason is not None or (i == n - 1 and pos_open):
            if exit_reason is None:  # forced close at data end
                exit_px, exit_reason = c[i], "data_end_cutoff"
            gross_pts = direction * (exit_px - open_entry_px)
            gross = gross_pts * LOT * open_lots
            cpts = cost_pts(dates[open_entry_i])
            cost = cpts * LOT * open_lots
            net = gross - cost
            cap = HAIRCUT_CAP_FRAC * equity_at_entry
            if net < -cap:
                net = -cap
                haircut_binds += 1
            equity = equity + net
            trades.append({
                "entry_date": dates[open_entry_i], "exit_date": dates[i], "dir": direction,
                "entry_px": open_entry_px, "exit_px": exit_px, "lots": open_lots,
                "reason": exit_reason, "gross_pts": gross_pts, "gross": gross,
                "cost": cost, "net": net, "equity_after": equity,
                "cost_era": "pre_hike" if dates[open_entry_i] < STT_HIKE_DATE else "post_hike",
                "hold_days": i - open_entry_i + 1,
            })
            pos_open = False
        i += 1

    tr = pd.DataFrame(trades)
    eq = pd.DataFrame({"date": dates, "equity": daily_equity}).dropna().reset_index(drop=True)
    if haircut_binds:
        eq.attrs["haircut_binds"] = haircut_binds
    return tr, eq


# ---------------------------------------------------------------- metrics
def nw_tstat(x: np.ndarray, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float("nan")
    m = x.mean()
    dvec = x - m
    var = (dvec @ dvec) / n
    for L in range(1, min(lags, n - 1) + 1):
        gL = (dvec[L:] @ dvec[:-L]) / n
        var += 2 * (1 - L / (lags + 1)) * gL
    if var <= 0:
        return float("nan")
    return m / np.sqrt(var / n)


def perf_from_equity(eq: pd.DataFrame) -> dict:
    if len(eq) < 5:
        return {}
    e = eq["equity"].values
    dates = pd.to_datetime(eq["date"])
    ret = np.diff(e) / e[:-1]
    yrs = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    cagr = (e[-1] / e[0]) ** (1 / yrs) - 1 if e[0] > 0 and e[-1] > 0 else float("nan")
    peak = np.maximum.accumulate(e)
    mdd = float(((e - peak) / peak).min())
    sharpe = float(np.mean(ret) / np.std(ret) * np.sqrt(252)) if np.std(ret) > 0 else float("nan")
    calmar = float(cagr / abs(mdd)) if mdd else None
    return {"CAGR_pct": round(100 * cagr, 2) if np.isfinite(cagr) else None,
            "maxDD_pct": round(100 * mdd, 2), "Sharpe": round(sharpe, 2) if np.isfinite(sharpe) else None,
            "Calmar": round(calmar, 2) if calmar is not None and np.isfinite(calmar) else None,
            "start_equity": round(float(e[0])), "end_equity": round(float(e[-1])),
            "n_days": int(len(eq))}


def trade_metrics(tr: pd.DataFrame, label: str) -> dict:
    if tr.empty:
        return {"label": label, "n": 0}
    net, gross = tr["net"], tr["gross"]
    wins = net[net > 0]
    m = tr.copy()
    m["ym"] = pd.to_datetime(m["exit_date"]).dt.to_period("M")
    monthly_net = m.groupby("ym")["net"].sum()
    monthly_gross = m.groupby("ym")["gross"].sum()
    pf = float(wins.sum() / abs(net[net <= 0].sum())) if net[net <= 0].sum() != 0 else float("inf")
    return {
        "label": label, "n": int(len(tr)),
        "gross_rupees": round(float(gross.sum())), "net_rupees": round(float(net.sum())),
        "cost_rupees": round(float(tr["cost"].sum())),
        "mean_pts_per_trade": round(float(tr["gross_pts"].mean()), 2),
        "hit_rate_net": round(float((net > 0).mean()), 4),
        "hit_rate_gross": round(float((gross > 0).mean()), 4),
        "t_nw_net": round(nw_tstat(net.values), 3),
        "PF_net": round(pf, 2) if np.isfinite(pf) else None,
        "months": int(len(monthly_net)),
        "month_win_rate_net": round(float((monthly_net > 0).mean()), 4),
        "month_win_rate_gross": round(float((monthly_gross > 0).mean()), 4),
        "largest_trade_share_of_profit": (
            round(float(net.max() / wins.sum()), 4) if len(wins) and wins.sum() > 0 else None),
        "avg_hold_days": round(float(tr["hold_days"].mean()), 1),
        "long_n": int((tr["dir"] > 0).sum()), "short_n": int((tr["dir"] < 0).sum()),
        "long_net": round(float(tr.loc[tr["dir"] > 0, "net"].sum())),
        "short_net": round(float(tr.loc[tr["dir"] < 0, "net"].sum())),
    }


def buy_and_hold(d: pd.DataFrame, start: dt.date, end: dt.date) -> dict:
    sub = d[(d["date"] >= start) & (d["date"] <= end)]
    if len(sub) < 5:
        return {}
    c = sub["close"].values
    ret = np.diff(c) / c[:-1]
    dates = pd.to_datetime(sub["date"])
    yrs = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    cagr = (c[-1] / c[0]) ** (1 / yrs) - 1
    peak = np.maximum.accumulate(c)
    mdd = float(((c - peak) / peak).min())
    sharpe = float(np.mean(ret) / np.std(ret) * np.sqrt(252)) if np.std(ret) > 0 else float("nan")
    return {"CAGR_pct": round(100 * cagr, 2), "maxDD_pct": round(100 * mdd, 2),
            "Sharpe": round(sharpe, 2), "Calmar": round(float(cagr / abs(mdd)), 2) if mdd else None,
            "start": str(start), "end": str(end), "start_px": round(float(c[0]), 1),
            "end_px": round(float(c[-1]), 1)}


# ---------------------------------------------------------------- main
def main():
    d = load_daily()
    print(f"[daily] {len(d)} sessions {d['date'].iloc[0]}..{d['date'].iloc[-1]}", flush=True)
    d = add_indicators(d)
    streams = build_streams(d)
    print(f"[streams] {len(streams)} entry streams", flush=True)

    exit_cfgs = ["signal_reversal", "atr_trail"] + [f"fixed_{n}" for n in N_DAYS_GRID]
    assert len(exit_cfgs) == 5
    trials = 0
    report = {"n_streams": len(streams), "exit_cfgs": exit_cfgs, "cells": []}
    all_trades = []

    for sname, (direction, entry_trig, exit_sig) in streams.items():
        n_trig = int(entry_trig.sum())
        for ecfg in exit_cfgs:
            trials += 1
            tr, eq = simulate(d, direction, entry_trig, exit_sig, ecfg)
            cell_name = f"{sname}__{ecfg}"
            if tr.empty:
                report["cells"].append({"cell": cell_name, "n_triggers": n_trig, "build": {"n": 0}})
                print(f"  {cell_name}: 0 trades (triggers={n_trig})", flush=True)
                continue
            tr["cell"] = cell_name
            all_trades.append(tr)
            b_tr = tr[tr["entry_date"] <= BUILD_END]
            h_tr = tr[tr["entry_date"] > BUILD_END]
            b_eq = eq[pd.to_datetime(eq["date"]).dt.date <= BUILD_END]
            h_eq = eq[pd.to_datetime(eq["date"]).dt.date > BUILD_END]
            cell = {
                "cell": cell_name, "n_triggers": n_trig,
                "build_trades": trade_metrics(b_tr, "build"),
                "build_perf": perf_from_equity(b_eq),
                "holdout_trades": trade_metrics(h_tr, "holdout_2026H1"),
                "holdout_perf": perf_from_equity(h_eq) if len(h_eq) else {},
                "haircut_binds": int(eq.attrs.get("haircut_binds", 0)),
            }
            report["cells"].append(cell)
            bt, bp = cell["build_trades"], cell["build_perf"]
            print(f"  {cell_name}: n={bt.get('n')} pts/trade={bt.get('mean_pts_per_trade')} "
                  f"net={bt.get('net_rupees')} CAGR={bp.get('CAGR_pct')}% MDD={bp.get('maxDD_pct')}% "
                  f"Calmar={bp.get('Calmar')} t={bt.get('t_nw_net')} "
                  f"monthWin(net/gross)={bt.get('month_win_rate_net')}/{bt.get('month_win_rate_gross')}",
                  flush=True)

    assert trials == 50, f"trials={trials}, expected 50 per pre-registration"
    report["trials_count"] = trials

    # buy-and-hold benchmarks
    d0, d1 = d["date"].iloc[0], d["date"].iloc[-1]
    report["buy_and_hold"] = {
        "build": buy_and_hold(d, d0, BUILD_END),
        "holdout_2026H1": buy_and_hold(d, dt.date(2026, 1, 1), d1),
        "full_period": buy_and_hold(d, d0, d1),
    }
    report["S1F_benchmark"] = {"CAGR_pct": 12.57, "maxDD_pct": -4.44, "Calmar": 2.83,
                                "Sharpe": 2.15, "PF": 2.21, "n": 204, "win_rate": 0.74}

    (OUT / "swing_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv(OUT / "all_trades.csv", index=False)
    print("\nwrote swing_report.json + all_trades.csv", flush=True)


if __name__ == "__main__":
    main()
