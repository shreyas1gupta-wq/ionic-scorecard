"""Chunk-neutrality for the MULTI-DAY probe across a YEAR BOUNDARY.
run_parity.py proved chunking for intraday cells; a 5-day hold can span 31-Dec, so
that case is proved separately here."""
import sys; from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(__file__).resolve().parent; sys.path.insert(0, str(OUT))
import arm1_lib as L, opt_pl as H
from run_parity import cmp_tables, say
sigs = L.build_signals()
need = L.needed_strikes(list(sigs.values()))
L.install_global_store(needed=need, maxsize=70)
t1 = sigs["T1_sweep_priorday_reclaim"]
d = pd.to_datetime(t1["t"]).dt.date
sub = t1[(d >= pd.Timestamp("2023-12-01").date()) & (d <= pd.Timestamp("2024-01-31").date())].reset_index(drop=True)
cfg = L.probe_grid("T1_sweep_priorday_reclaim")[7][1]   # dte2-3, one of the offsets
print(f"probe cfg: dte {cfg.min_dte}-{cfg.max_dte} off {cfg.strike_offset} hold {cfg.max_hold_days}d "
      f"{cfg.expiry_handling} | {len(sub)} signals across the 2023/2024 boundary")
A = H.run_signals(sub, cfg)
parts = [H.run_signals(sub[pd.to_datetime(sub["t"]).dt.year == y], cfg) for y in (2023, 2024)]
B = pd.concat(parts, ignore_index=True)
f = A[A.status=="filled"]
print("filled", len(f), "| trades spanning >0 days:", int((f.hold_days.astype(float)>0).sum()),
      "| cash-settled:", int(f.cash_settled.fillna(False).astype(bool).sum()))
ok = cmp_tables(A, B, "one-call", "year-chunked")
print("VERDICT:", "PASS" if ok else "FAIL")
