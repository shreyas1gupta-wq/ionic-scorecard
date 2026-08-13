import sys; from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(__file__).resolve().parent; sys.path.insert(0, str(OUT))
import arm1_lib as L, opt_pl as H
sigs = L.build_signals()
t1 = L.split(sigs["T1_sweep_priorday_reclaim"], L.BUILD_START, L.BUILD_END)
d = pd.to_datetime(t1["t"]).dt.date
sub = t1[(d >= pd.Timestamp("2023-01-01").date()) & (d <= pd.Timestamp("2023-06-30").date())].iloc[::3].reset_index(drop=True)
cfg = H.OptCfg(min_dte=2, max_dte=3, strike_offset=-2, **L.BASE, target_pct=1.0, stop_pct=0.35, trail_pct=None)
A = H.run_signals(sub, cfg)
L.install_global_store()
B = H.run_signals(sub, cfg)
print("rows", len(A), len(B), "filled", (A.status=="filled").sum(), (B.status=="filled").sum())
for c in ["exp","otype","entry_t","reject_reason","exit_reason","cash_settled"]:
    xa, xb = A[c], B[c]
    print(f"--- {c}: dtypeA={xa.dtype} dtypeB={xb.dtype}")
    sa, sb = xa.astype(str), xb.astype(str)
    m = sa != sb
    print("   ndiff", int(m.sum()), "| samples:", [(i, repr(xa.iloc[i]), repr(xb.iloc[i])) for i in list(np.where(m.values)[0])[:3]])
print("status equal:", (A.status.values==B.status.values).all())
print("net equal:", np.nanmax(np.abs(A.net_pnl.astype(float).values - B.net_pnl.astype(float).values)))
