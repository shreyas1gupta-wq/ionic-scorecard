import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
C = pd.read_csv(f"{OUT}/cells.csv")
TOTAL_COST = 3.538
C["reverse_net_if_sold"] = -C["mean_gross_pts"] - TOTAL_COST
print(C[["cell","mean_gross_pts","mean_net_pts","reverse_net_if_sold"]].to_string(index=False))
