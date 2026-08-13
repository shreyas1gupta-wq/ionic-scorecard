import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from scipy import stats
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"

LOT=65; COST_PER_SIDE = 25.0/LOT + 0.5; TOTAL_COST = 4*COST_PER_SIDE

P = pd.read_parquet(f"{OUT}/placebo_trades_raw.parquet")
P["gross"] = (P.ce_exit+P.pe_exit) - (P.ce_entry+P.pe_entry)
P["net"] = P["gross"] - TOTAL_COST
P["realized_move"] = (P.spot_exit-P.spot_entry).abs()
P["breakeven"] = (P.ce_entry+P.pe_entry) + TOTAL_COST
P["rmi"] = P["realized_move"] - P["breakeven"]

A = pd.read_parquet(f"{OUT}/trades_all.parquet")
g2 = A[A.cell=="G2_VOV"]

print(f"PLACEBO (random, matched time-of-day, ungated): n={len(P)}")
print(f"  mean net = {P['net'].mean():.3f}  win%={100*(P['net']>0).mean():.1f}  mean rmi={P['rmi'].mean():.2f}")
print(f"REAL G2_VOV (gated on vol-spike): n={len(g2)}")
print(f"  mean net = {g2['net'].mean():.3f}  win%={100*(g2['net']>0).mean():.1f}  mean rmi={g2['realized_minus_implied'].mean():.2f}")

t, p = stats.ttest_ind(g2["net"], P["net"], equal_var=False)
print(f"\nWelch two-sample t-test  G2_VOV net vs PLACEBO net:  t={t:.3f}  p={p:.4f}")
print(f"  (gate is {'MORE negative than' if g2['net'].mean()<P['net'].mean() else 'similar to or better than'} the ungated baseline)")

P.to_parquet(f"{OUT}/placebo_scored.parquet")
