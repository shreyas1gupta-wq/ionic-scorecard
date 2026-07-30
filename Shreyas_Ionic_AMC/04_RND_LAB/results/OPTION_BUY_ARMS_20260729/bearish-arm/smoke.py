import sys, time
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/"OPTION_PL_HARNESS_20260729"))
import opt_pl as H
import run_arm as R
sig = pd.read_csv(HERE/"bearish_signals.csv", parse_dates=["t"]).sort_values("t")
sub = sig[(sig.t>="2023-01-01")&(sig.t<"2023-04-01")][["t","direction","tag"]]
print("smoke signals", len(sub))
t0=time.time()
tr = H.run_signals(sub, R.base_cfg((2,3), 0, R.EXITS["E1_tgt50_stop30"]))
print(f"{time.time()-t0:.0f}s for {len(sub)} signals over ~13 expiries")
H.summarize(tr, "SMOKE dte2_3 ATM E1", capital=3_00_000.0)
H.fill_report(tr, quiet=False)
f = tr[tr.status=="filled"]
print(f[["signal_t","otype","strike","atm","dte_entry","entry_px_raw","exit_px_raw","exit_reason","gross","costs","net_pnl"]].head(12).to_string())
