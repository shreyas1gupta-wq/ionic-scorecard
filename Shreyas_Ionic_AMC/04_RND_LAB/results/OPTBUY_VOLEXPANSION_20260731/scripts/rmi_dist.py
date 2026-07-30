import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
A = pd.read_parquet(f"{OUT}/trades_all.parquet")
for cell in ["G2_VOV","G1_ML","G3_ATRCONS"]:
    g = A[A.cell==cell]["realized_minus_implied"]
    print(f"\n{cell} realized-minus-implied distribution (n={len(g)}):")
    print(g.describe(percentiles=[.1,.25,.5,.75,.9]))
    print("frac positive (realized move EXCEEDED breakeven):", (g>0).mean())
