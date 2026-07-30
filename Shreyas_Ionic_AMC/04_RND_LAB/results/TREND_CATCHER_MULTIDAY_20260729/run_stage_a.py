"""Stage A — signal screen. 3 cells: each signal, DTE=(15,22), strike=ATM, hold=trail35.
Pre-registered pass bar: NET ret_pct NW-t >= 2.0, net PF > 1.2, n >= 30. See PRE_REGISTRATION.md.
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
    df, meta = tc.build_trades(name, tc.DTE_BUCKETS["b2_15_22"], "ATM", "trail35",
                                d, spot, all_days, tc.BUILD_START, tc.BUILD_END)
    fp = tc.TRADES_DIR / f"stageA_{name}_b2_ATM_trail35.csv"
    df.to_csv(fp, index=False)
    net = tc.perf_stats(df, tc.BUILD_START, tc.BUILD_END, tc.CAPITAL, "net_pnl")
    gross = tc.perf_stats(df, tc.BUILD_START, tc.BUILD_END, tc.CAPITAL, "gross")
    passed = (net.get("n", 0) >= 30 and net.get("nw_t_retpct", float("nan")) >= 2.0
              and net.get("pf", 0) > 1.2)
    results[name] = {"meta": meta, "net": net, "gross": gross, "pass_stage_a": bool(passed),
                      "csv": str(fp)}
    print(f"\n=== {name} ===")
    print("meta:", meta)
    print("NET :", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in net.items()})
    print("GROSS:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in gross.items()})
    print("PASS STAGE A BAR:", passed)

with open(tc.OUT / "stage_a_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved:", tc.OUT / "stage_a_results.json")
