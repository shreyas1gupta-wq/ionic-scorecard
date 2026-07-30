import sys, time, json; from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(__file__).resolve().parent; sys.path.insert(0, str(OUT))
import arm1_lib as L, opt_pl as H, run_grid as G
sigs = L.build_signals()
need = L.needed_strikes(list(sigs.values()))
print("map", len(need), "avg", np.mean([len(v) for v in need.values()]))
store = L.install_global_store(needed=need, maxsize=70)
T1 = "T1_sweep_priorday_reclaim"
cells = L.grid(T1)[:6] + L.probe_grid(T1)[:2]
t0=time.time()
res = G.run_phase("smoke", cells, sigs, [2023], L.BUILD_START, L.BUILD_END, store)
print(f"{time.time()-t0:.0f}s for {len(cells)} cells on 2023")
for lab,m in res.items():
    print(f"{lab:52s} sig{m['signals']:4d} fill{m['filled']:4d} net {m.get('net_total',float('nan')):+10.0f} "
          f"gross {m.get('gross_total',float('nan')):+10.0f} t {m.get('t_nw',float('nan')):+.2f} top1 {m.get('top1_profit_share',float('nan')):.2f}")
print("reject sample:", list(res.values())[0]["reject_reasons"])
