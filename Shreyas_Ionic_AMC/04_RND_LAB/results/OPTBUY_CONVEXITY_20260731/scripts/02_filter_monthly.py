"""Shrink cache/nifty_optidx_daily.parquet (5.5M rows, all expiries incl weeklies) down to just
the MONTHLY (last-of-calendar-month per underlying-expiry) expiries with CONTRACTS>0 -- the only
rows this arm's backtest needs. Cuts RAM footprint for the engine step by >90%.
"""
import gc
import pandas as pd

OUT_DIR = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
           r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache")

df = pd.read_parquet(f"{OUT_DIR}\\nifty_optidx_daily.parquet")
print(f"loaded {len(df):,} rows")

# identify monthly expiries: the LAST distinct EXPIRY_DT within each (year, month) of the expiry itself
all_exp = pd.Series(df["EXPIRY_DT"].unique()).sort_values()
exp_df = pd.DataFrame({"EXPIRY_DT": all_exp})
exp_df["ym"] = exp_df["EXPIRY_DT"].dt.to_period("M")
monthly_exp = set(exp_df.groupby("ym")["EXPIRY_DT"].max())
print(f"{len(all_exp)} distinct expiries total -> {len(monthly_exp)} monthly expiries "
      f"{min(monthly_exp).date()}..{max(monthly_exp).date()}")

traded = df[df["CONTRACTS"] > 0].copy()
traded["OPTION_TYP"] = traded["OPTION_TYP"].astype("category")
traded = traded.reset_index(drop=True)
print(f"ALL expiries, contracts>0: {len(traded):,} rows")
traded.to_parquet(f"{OUT_DIR}\\nifty_optidx_all_traded.parquet", index=False)

monthly = traded[traded["EXPIRY_DT"].isin(monthly_exp)].copy().reset_index(drop=True)
print(f"MONTHLY expiries only, contracts>0: {len(monthly):,} rows")
monthly.to_parquet(f"{OUT_DIR}\\nifty_optidx_monthly.parquet", index=False)

# also save the monthly expiry list itself for the engine
pd.Series(sorted(monthly_exp)).to_frame("expiry").to_parquet(f"{OUT_DIR}\\monthly_expiry_list.parquet")
print("DONE")
del df, traded, monthly
gc.collect()
