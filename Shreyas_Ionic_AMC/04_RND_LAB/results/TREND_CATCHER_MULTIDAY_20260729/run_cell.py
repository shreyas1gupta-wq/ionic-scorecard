"""Generic single-cell runner, reused for Stage B / Stage C / forward test.
Usage: python run_cell.py <signal> <dte_key> <strike> <hold> <start:YYYY-MM-DD> <end:YYYY-MM-DD> <tag>
dte_key in {b1_8_12, b2_15_22, b3_25_35}; strike in {ITM1,ATM,OTM1};
hold in {reversal,N5,N10,N20,trail35}.
"""
import datetime as dt
import json
import sys

import trend_catcher as tc
import chain

signal, dte_key, strike, hold, start_s, end_s, tag = sys.argv[1:8]
start = dt.date.fromisoformat(start_s)
end = dt.date.fromisoformat(end_s)

spot_all = chain.load_index()
spot = spot_all[spot_all.index.time >= dt.time(9, 15)].sort_index()
d = tc.daily_bars(spot_all)
all_days = list(d.index.date)

df, meta = tc.build_trades(signal, tc.DTE_BUCKETS[dte_key], strike, hold,
                            d, spot, all_days, start, end)
fp = tc.TRADES_DIR / f"{tag}.csv"
df.to_csv(fp, index=False)
net = tc.perf_stats(df, start, end, tc.CAPITAL, "net_pnl")
gross = tc.perf_stats(df, start, end, tc.CAPITAL, "gross")
out = {"signal": signal, "dte_key": dte_key, "strike": strike, "hold": hold,
       "start": start_s, "end": end_s, "meta": meta, "net": net, "gross": gross,
       "csv": str(fp)}
with open(tc.OUT / f"{tag}.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ("net", "gross")}, default=str))
print("NET  :", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in net.items()})
print("GROSS:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in gross.items()})
