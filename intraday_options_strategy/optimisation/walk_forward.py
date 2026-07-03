"""Walk-forward optimisation (spec S5).

Data split: first 70% of trading days = in-sample (IS), last 30% = OOS
(never touched here). Within IS: optimise on 60 trading days, test forward
on the next 15, step 15 — per-fold winners + forward results checkpointed to
results/wfo_folds.csv (safe to kill & restart: completed folds are skipped).

Grid (648 combos/fold): 27 cached signal variants × 8 valid SL/target pairs
× 3 max-trades-per-day. Objective: modified Sharpe on the optimisation
window, feasibility-first w.r.t. WinRate>=55%, PF>=1.5, MaxDD<=20%.

Run:  python optimisation/walk_forward.py [n_workers]
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    EMA_FAST_GRID, EMA_SLOW_GRID, IS_FRACTION, MAX_DRAWDOWN_LIMIT,
    MAX_TRADES_PER_DAY_GRID, MIN_PROFIT_FACTOR, MIN_TARGET_SL_RATIO,
    MIN_WIN_RATE, ORB_MINUTES_GRID, PROCESSED_DIR, RESULTS_DIR,
    RISK_FREE_RATE, SL_PCT_GRID, TARGET_PCT_GRID, TOTAL_CAPITAL,
    TRADING_DAYS_PER_YEAR, WFO_FWD_DAYS, WFO_OPT_DAYS, WFO_STEP_DAYS,
    StrategyParams,
)

FOLDS_CSV = RESULTS_DIR / "wfo_folds.csv"
CONSENSUS_JSON = RESULTS_DIR / "wfo_consensus.json"

SL_TG = [(sl, tg) for sl, tg in product(SL_PCT_GRID, TARGET_PCT_GRID)
         if tg / sl >= MIN_TARGET_SL_RATIO]
VARIANTS = list(product(EMA_FAST_GRID, EMA_SLOW_GRID, ORB_MINUTES_GRID))

# ── worker globals (loaded once per process) ─────────────────────────────
_G: dict = {}


def _init_worker() -> None:
    _G["nifty"] = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
    _G["vix"] = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
    _G["events"] = {v: pd.read_parquet(
        PROCESSED_DIR / "events" / f"ev_f{v[0]}s{v[1]}o{v[2]}.parquet")
        for v in VARIANTS}


def window_metrics(daily: pd.DataFrame, trades: pd.DataFrame) -> dict:
    """Window-level metrics for objective + constraints."""
    n_days = len(daily)
    ret = daily["Daily_PnL"] / daily["Running_Capital"].shift(1).fillna(TOTAL_CAPITAL)
    total_ret = daily["Running_Capital"].iloc[-1] / TOTAL_CAPITAL - 1 if n_days else 0.0
    ann_ret = (1 + total_ret) ** (TRADING_DAYS_PER_YEAR / max(n_days, 1)) - 1
    vol = ret.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (ann_ret - RISK_FREE_RATE) / vol if vol > 1e-12 else -99.0
    peak = daily["Running_Capital"].cummax()
    maxdd = float(((peak - daily["Running_Capital"]) / peak).max()) if n_days else 0.0
    if len(trades):
        wins = trades["net_pnl"] > 0
        wr = float(wins.mean())
        gw = float(trades.loc[wins, "net_pnl"].sum())
        gl = float(-trades.loc[~wins, "net_pnl"].sum())
        pf = gw / gl if gl > 0 else (np.inf if gw > 0 else 0.0)
    else:
        wr, pf = 0.0, 0.0
    return {"n_trades": len(trades), "win_rate": wr, "profit_factor": pf,
            "max_dd": maxdd, "sharpe": float(sharpe), "ann_ret": float(ann_ret),
            "net_pnl": float(trades["net_pnl"].sum()) if len(trades) else 0.0}


def _run_window(variant: tuple, sl: float, tg: float, mtpd: int,
                d0: pd.Timestamp, d1: pd.Timestamp) -> dict:
    from backtest.engine import EngineConfig, run_backtest
    nifty = _G["nifty"].loc[d0:d1 + pd.Timedelta(days=1)]
    vix = _G["vix"].loc[nifty.index.min():nifty.index.max()]
    ev = _G["events"][variant]
    ev = ev[(ev["dt"] >= d0) & (ev["dt"] < d1 + pd.Timedelta(days=1))]
    p = StrategyParams(sl_pct=sl, target_pct=tg, ema_fast=variant[0],
                       ema_slow=variant[1], orb_minutes=variant[2],
                       max_trades_per_day=mtpd)
    tr, daily = run_backtest(nifty, vix, ev, EngineConfig(p))
    return window_metrics(daily, tr)


def eval_combo(args: tuple) -> dict:
    (variant, sl, tg, mtpd, d0, d1) = args
    m = _run_window(variant, sl, tg, mtpd, d0, d1)
    feasible = (m["win_rate"] >= MIN_WIN_RATE and m["profit_factor"] >= MIN_PROFIT_FACTOR
                and m["max_dd"] <= MAX_DRAWDOWN_LIMIT and m["n_trades"] >= 10)
    return {"ema_fast": variant[0], "ema_slow": variant[1], "orb": variant[2],
            "sl_pct": sl, "target_pct": tg, "max_tpd": mtpd,
            "feasible": feasible, **m}


def main(n_workers: int) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    days = pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                       parse_dates=["day"])["day"]
    n_is = int(len(days) * IS_FRACTION)
    is_days = days.iloc[:n_is].reset_index(drop=True)
    print(f"IS: {is_days.iloc[0].date()} .. {is_days.iloc[-1].date()} "
          f"({n_is} days); OOS starts {days.iloc[n_is].date()}", flush=True)

    folds = []
    a = 0
    while a + WFO_OPT_DAYS + WFO_FWD_DAYS <= n_is:
        folds.append((a, a + WFO_OPT_DAYS, a + WFO_OPT_DAYS + WFO_FWD_DAYS))
        a += WFO_STEP_DAYS
    print(f"{len(folds)} folds x {len(VARIANTS) * len(SL_TG) * len(MAX_TRADES_PER_DAY_GRID)} combos",
          flush=True)

    done = set()
    if FOLDS_CSV.exists():
        done = set(pd.read_csv(FOLDS_CSV)["fold"].astype(int))
        print(f"resume: {len(done)} folds already complete", flush=True)

    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init_worker) as ex:
        for fi, (a0, a1, a2) in enumerate(folds):
            if fi in done:
                continue
            d0, d1 = is_days[a0], is_days[a1 - 1]      # optimisation window
            f0, f1 = is_days[a1], is_days[a2 - 1]      # forward window
            tasks = [(v, sl, tg, m, d0, d1) for v in VARIANTS
                     for sl, tg in SL_TG for m in MAX_TRADES_PER_DAY_GRID]
            res = pd.DataFrame(list(ex.map(eval_combo, tasks, chunksize=16)))
            res = res.sort_values(["feasible", "sharpe"], ascending=False)
            best = res.iloc[0]

            _init_worker_main()
            fwd = _run_window((int(best.ema_fast), int(best.ema_slow), int(best.orb)),
                              float(best.sl_pct), float(best.target_pct),
                              int(best.max_tpd), f0, f1)
            row = {"fold": fi, "opt_start": d0.date(), "opt_end": d1.date(),
                   "fwd_start": f0.date(), "fwd_end": f1.date(),
                   "ema_fast": int(best.ema_fast), "ema_slow": int(best.ema_slow),
                   "orb": int(best.orb), "sl_pct": float(best.sl_pct),
                   "target_pct": float(best.target_pct), "max_tpd": int(best.max_tpd),
                   "opt_feasible": bool(best.feasible),
                   "opt_sharpe": float(best.sharpe), "opt_wr": float(best.win_rate),
                   "opt_pf": float(best.profit_factor), "opt_dd": float(best.max_dd),
                   **{f"fwd_{k}": v for k, v in fwd.items()}}
            pd.DataFrame([row]).to_csv(FOLDS_CSV, mode="a", index=False,
                                       header=not FOLDS_CSV.exists())
            print(f"fold {fi + 1}/{len(folds)}: best f{row['ema_fast']}/s{row['ema_slow']}"
                  f"/o{row['orb']} sl{row['sl_pct']} tg{row['target_pct']} "
                  f"m{row['max_tpd']} feas={row['opt_feasible']} "
                  f"oSharpe={row['opt_sharpe']:.2f} fwd_pnl={fwd['net_pnl']:,.0f} "
                  f"fwd_wr={fwd['win_rate']:.0%}", flush=True)

    _write_consensus()


def _init_worker_main() -> None:
    if "nifty" not in _G:
        _init_worker()


def _write_consensus() -> None:
    df = pd.read_csv(FOLDS_CSV)
    cons = {c: (df[c].mode().iloc[0].item() if df[c].dtype != float
                else float(df[c].mode().iloc[0]))
            for c in ["ema_fast", "ema_slow", "orb", "sl_pct", "target_pct", "max_tpd"]}
    cons["n_folds"] = len(df)
    cons["pct_feasible"] = float(df["opt_feasible"].mean())
    CONSENSUS_JSON.write_text(json.dumps(cons, indent=2))
    print(f"consensus -> {CONSENSUS_JSON}: {cons}", flush=True)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(2, __import__("os").cpu_count() - 2)
    main(workers)
