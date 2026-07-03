"""Orchestrator: final IS + OOS evaluation with WFO consensus parameters,
full metrics, 8 charts, robustness suite, and report files.

Prerequisites (run once, in order):
  1. data/build_dataset.py
  2. optimisation/precompute.py
  3. optimisation/walk_forward.py     (long; checkpointed)

Then:  python main.py
Outputs to results/: trades_*.parquet, daily_*.csv, REPORT.md, charts/*.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis.charts import all_charts  # noqa: E402
from analysis.metrics import by_signal, format_report, full_metrics  # noqa: E402
from analysis.robustness import (  # noqa: E402
    cost_sensitivity, parameter_stability, random_removal_mc,
    slippage_sensitivity, vix_regime_split,
)
from backtest.costs import round_trip_example  # noqa: E402
from backtest.engine import EngineConfig, run_backtest  # noqa: E402
from config import IS_FRACTION, PROCESSED_DIR, RESULTS_DIR, StrategyParams  # noqa: E402

CONSENSUS_JSON = RESULTS_DIR / "wfo_consensus.json"


def consensus_params() -> StrategyParams:
    c = json.loads(CONSENSUS_JSON.read_text())
    return StrategyParams(sl_pct=c["sl_pct"], target_pct=c["target_pct"],
                          ema_fast=int(c["ema_fast"]), ema_slow=int(c["ema_slow"]),
                          orb_minutes=int(c["orb"]),
                          max_trades_per_day=int(c["max_tpd"]))


def main() -> None:
    t0 = time.time()
    params = consensus_params()
    print(f"consensus params: {params}")

    nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
    vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
    ev = pd.read_parquet(
        PROCESSED_DIR / "events" /
        f"ev_f{params.ema_fast}s{params.ema_slow}o{params.orb_minutes}.parquet")

    days = pd.read_csv(PROCESSED_DIR / "trading_calendar.csv", parse_dates=["day"])["day"]
    n_is = int(len(days) * IS_FRACTION)
    oos_start = days.iloc[n_is]
    print(f"OOS: {oos_start.date()} .. {days.iloc[-1].date()}")

    segs = {}
    for name, d0, d1 in [("IS", days.iloc[0], days.iloc[n_is - 1]),
                         ("OOS", oos_start, days.iloc[-1])]:
        nf = nifty.loc[d0:d1 + pd.Timedelta(days=1)]
        vx = vix.loc[nf.index.min():nf.index.max()]
        e = ev[(ev["dt"] >= d0) & (ev["dt"] < d1 + pd.Timedelta(days=1))]
        tr, daily = run_backtest(nf, vx, e, EngineConfig(params))
        segs[name] = (tr, daily)
        tr.to_parquet(RESULTS_DIR / f"trades_{name.lower()}.parquet")
        daily.to_csv(RESULTS_DIR / f"daily_{name.lower()}.csv")

    report = [f"# STRATEGY REPORT — consensus params {params}",
              f"\n```\n{round_trip_example(150.0, 1)}\n```\n"]
    for name, (tr, daily) in segs.items():
        m = full_metrics(tr, daily)
        report.append(f"\n```\n{format_report(m, name)}\n```\n")
        report.append(f"\n### {name} attribution by signal\n\n"
                      + by_signal(tr).to_markdown() + "\n")
        print(format_report(m, name))

    # combined chart set (IS+OOS stitched for the equity curve)
    tr_all = pd.concat([segs["IS"][0], segs["OOS"][0]], ignore_index=True)
    d_is, d_oos = segs["IS"][1].copy(), segs["OOS"][1].copy()
    d_oos2 = d_oos.copy()
    d_oos2["Cumulative_PnL"] += d_is["Cumulative_PnL"].iloc[-1]
    d_oos2["Running_Capital"] = d_is["Running_Capital"].iloc[-1] + d_oos["Cumulative_PnL"]
    d_all = pd.concat([d_is, d_oos2])
    paths = all_charts(tr_all, d_all, oos_start=oos_start)
    print(f"charts: {len(paths)} saved -> {paths[0].parent}")

    # robustness (OOS only)
    tr_o, dly_o = segs["OOS"]
    nf_o = nifty.loc[oos_start:]
    vx_o = vix.loc[nf_o.index.min():]
    ev_o = ev[ev["dt"] >= oos_start]
    print("\nrobustness 9.1 slippage:")
    s1 = slippage_sensitivity(nf_o, vx_o, ev_o, params); print(s1.round(3).to_string())
    print("\nrobustness 9.2 costs:")
    s2 = cost_sensitivity(nf_o, vx_o, ev_o, params); print(s2.round(3).to_string())
    print("\nrobustness 9.3 param stability (SL/TG +/-10%):")
    s3 = parameter_stability(nf_o, vx_o, ev_o, params); print(s3.round(3).to_string())
    if s3.attrs.get("fragile"):
        print("  *** FLAG: strategy FRAGILE (>30% degradation within +/-10%) ***")
    print("\nrobustness 9.4 VIX regime split:")
    vix_day = vx_o.groupby(nf_o.index.normalize()).first()
    s4 = vix_regime_split(tr_o, dly_o, vix_day); print(s4.round(3).to_string())
    print("\nrobustness 9.5 random 10% removal MC:")
    s5 = random_removal_mc(tr_o); print({k: f"{v:,.0f}" for k, v in s5.items()})

    for name, df in [("rob_slippage", s1), ("rob_costs", s2),
                     ("rob_params", s3), ("rob_vix_regime", s4)]:
        df.to_csv(RESULTS_DIR / f"{name}.csv")
        report.append(f"\n### {name}\n\n" + df.round(4).to_markdown() + "\n")
    report.append(f"\n### rob_mc_removal\n\n```\n{json.dumps(s5, indent=2)}\n```\n")

    (RESULTS_DIR / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nREPORT.md + outputs -> {RESULTS_DIR}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
