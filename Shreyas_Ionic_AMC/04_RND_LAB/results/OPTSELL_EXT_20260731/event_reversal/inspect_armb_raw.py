import pandas as pd
ARMB = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"

e = pd.read_parquet(f"{ARMB}/eod_trades_raw.parquet")
print("eod_trades_raw:", e.shape, list(e.columns))
print(e[e.cell.isin(['EVENT_BUDGET','EVENT_FED'])].groupby('cell').size())
print(e[e.cell=='EVENT_BUDGET'].to_string())

iv = pd.read_parquet(f"{ARMB}/ivterm_trades_raw.parquet")
print("\nivterm_trades_raw:", iv.shape, list(iv.columns))
print(iv.to_string())
