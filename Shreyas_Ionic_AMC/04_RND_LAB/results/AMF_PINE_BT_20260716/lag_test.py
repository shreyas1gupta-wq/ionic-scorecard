"""One-day-lag lookahead audit on the default cell (Efficiency/MACD/V1), per SPEC + D-028.
run_with_lag(extra_lag_days): re-derives entry/exit transaction index with an ADDITIONAL
extra_lag_days beyond the normal +1 (confirm->execute) shift, and returns total pooled
net P&L (%units, sum of net_ret across all closed trades) as the metric.
A real momentum-crossover edge should degrade gracefully with +1 extra day of delay
(you're entering the move one day later); a same-bar leak collapses instead.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import lookahead_audit as LA  # noqa: E402
from amf_engine import compute_amf  # noqa: E402
from amf_backtest import (load_panel, load_universe, eligibility_mask, variant_events,
                           build_state, BT_START, BT_END, COST_RT,
                           FAST_LEN, SLOW_LEN, SIGNAL_LEN, PHASE)

t0 = time.time()
panel = load_panel()
snap_dates, members = load_universe()
all_tickers = set().union(*members.values())
panel_syms = set(panel["symbol"].unique())
overlap = sorted(all_tickers & panel_syms)
panel = panel[panel["symbol"].isin(overlap)].sort_values(["symbol", "date"])
by_sym = {sym: g.reset_index(drop=True) for sym, g in panel.groupby("symbol", sort=False)}
print(f"[load] {len(by_sym)} symbols, {time.time()-t0:.1f}s")


def run_with_lag(extra_lag_days: int) -> float:
    total_net = 0.0
    n_trades = 0
    for sym, g in by_sym.items():
        dates = g["date"].values
        close = g["close"].values.astype(float)
        n = len(close)
        if n < 60:
            continue
        eligible = eligibility_mask(dates, sym, snap_dates, members)
        in_window = (dates >= np.datetime64(BT_START)) & (dates <= np.datetime64(BT_END))
        if not in_window.any():
            continue
        r = compute_amf(close, fast_len=FAST_LEN, slow_len=SLOW_LEN, signal_len=SIGNAL_LEN,
                         phase=PHASE, engine="Efficiency", mode="MACD")
        entry_cond, exit_cond = variant_events(r, r["osc"], "V1")
        state = build_state(entry_cond, exit_cond, eligible, in_window)
        d = np.diff(state, prepend=state[0] if n else 0.0)
        entry_idx = np.where(d == 1.0)[0]
        exit_idx = np.where(d == -1.0)[0]
        lag = 1 + extra_lag_days
        entry_tx = entry_idx + lag
        exit_tx = exit_idx + lag
        entry_tx = entry_tx[entry_tx < n]
        exit_tx = exit_tx[exit_tx < n]
        events = sorted([(t, "E") for t in entry_tx] + [(t, "X") for t in exit_tx])
        cur_entry = None
        for t, kind in events:
            if kind == "E":
                if cur_entry is None:
                    cur_entry = t
            else:
                if cur_entry is not None:
                    gross = close[t] / close[cur_entry] - 1.0
                    net = gross - COST_RT
                    total_net += net
                    n_trades += 1
                    cur_entry = None
    print(f"  [lag={extra_lag_days}] n_trades={n_trades} total_net_pct_sum={total_net*100:.2f}")
    return total_net * 100  # metric: pooled sum of net trade returns, in % units


base = run_with_lag(0)
lagged = run_with_lag(1)
result = LA.one_day_lag_test(run_with_lag, base_metric=base)
result["lagged"] = lagged  # already computed above; avoid double compute inconsistency
result["collapse_ratio"] = round((base - lagged) / abs(base), 3) if base != 0 else None
verdict = ("FAIL -- collapse >50%: strongly suggests leakage" if result["collapse_ratio"] and result["collapse_ratio"] > 0.50 else
           "WARN -- 25-50% decay in one day: fast edge or partial leak, review" if result["collapse_ratio"] and result["collapse_ratio"] > 0.25 else
           "PASS -- graceful decay")
result["verdict"] = verdict
print("\n=== ONE-DAY-LAG AUDIT: Efficiency/MACD/V1 ===")
print(f"base (lag=0, normal next-bar exec)  total_net_pct_sum = {base:.2f}")
print(f"lagged (lag=+1 extra day)            total_net_pct_sum = {lagged:.2f}")
print(f"collapse_ratio = {result['collapse_ratio']}")
print(f"verdict = {verdict}")
print(f"elapsed {time.time()-t0:.1f}s")

with open(HERE / "lag_test_result.txt", "w") as f:
    f.write(f"base={base}\nlagged={lagged}\ncollapse_ratio={result['collapse_ratio']}\nverdict={verdict}\n")
