"""DEVIATION from PRE_REGISTRATION.md, logged BEFORE running (not after seeing results):
Stage A (trail35 only) failed all 3 signals outright. Diagnosis on the ema_cross cell showed
28/36 exits were "trail" reason with only a 19% win rate -- i.e. many trades peaked in profit
but the 35% giveback band is wide enough to still hand back a net LOSS. That is a property of
the EXIT RULE, not proof the signal has zero skill. Before declaring a full-arm kill, extend
the Stage-A screen to the other 4 hold rules (N5/N10/N20/reversal), same signals, same fixed
DTE=(15,22)/ATM, same pre-registered pass bar (NET ret_pct NW-t>=2.0, PF>1.2, n>=30). This adds
12 cells (screen total 15) -- still far below the 135-cell full cross product, and it tests the
exit-mechanism confound rather than searching for an arbitrary winner. If NONE of these 15
cells clear the bar, the kill stands, now on a firmer footing.
"""
import datetime as dt
import json

import pandas as pd
import trend_catcher as tc
import chain

spot_all = chain.load_index()
spot = spot_all[spot_all.index.time >= dt.time(9, 15)].sort_index()
d = tc.daily_bars(spot_all)
all_days = list(d.index.date)

results = {}
for name in tc.SIGNAL_NAMES:
    for hold in ["N5", "N10", "N20", "reversal"]:
        df, meta = tc.build_trades(name, tc.DTE_BUCKETS["b2_15_22"], "ATM", hold,
                                    d, spot, all_days, tc.BUILD_START, tc.BUILD_END)
        fp = tc.TRADES_DIR / f"stageAext_{name}_b2_ATM_{hold}.csv"
        df.to_csv(fp, index=False)
        net = tc.perf_stats(df, tc.BUILD_START, tc.BUILD_END, tc.CAPITAL, "net_pnl")
        gross = tc.perf_stats(df, tc.BUILD_START, tc.BUILD_END, tc.CAPITAL, "gross")
        passed = (net.get("n", 0) >= 30 and net.get("nw_t_retpct", float("nan")) >= 2.0
                  and net.get("pf", 0) > 1.2)
        key = f"{name}__{hold}"
        results[key] = {"meta": meta, "net": net, "gross": gross, "pass_stage_a": bool(passed),
                         "csv": str(fp)}
        print(f"{key:45s} n={net.get('n',0):4d} NWt={net.get('nw_t_retpct',float('nan')):+.2f} "
              f"PF={net.get('pf',float('nan')):.2f} win={net.get('win_rate',float('nan')):.1%} "
              f"CAGR={net.get('cagr',float('nan')):+.1%} PASS={passed}")

with open(tc.OUT / "stage_a_ext_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved:", tc.OUT / "stage_a_ext_results.json")
