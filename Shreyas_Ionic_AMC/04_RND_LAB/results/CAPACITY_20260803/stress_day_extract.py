"""EXIT LIQUIDITY on a stressed tape -- real bhavcopy volumes around 2020-03-23 (NIFTY worst 1-day,
-12.98%) and the surrounding 20-day tail window, for both FUTIDX and OPTIDX NIFTY.
Source: Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_2020.parquet (verified row counts
printed below). No 1-min intraday data exists for this period in any dataset this firm holds (HF options
1-min starts 2021-05; HF NIFTY futures 1-min starts 2015-01 per SWEEP_11YR but was not re-pulled here --
see note in writeup on what a full intraday reconstruction would need).
"""
import pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DATA = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CAPACITY_20260803"

d = pd.read_parquet(DATA / "fo_idx_2020.parquet",
                     columns=["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP",
                              "CLOSE", "CONTRACTS", "OPEN_INT", "TIMESTAMP"])
print(f"[loaded] fo_idx_2020.parquet: {len(d):,} rows")
d["TS"] = pd.to_datetime(d["TIMESTAMP"], format="%d-%b-%Y", errors="coerce")

# ---------------- FUTURES: daily volume around the crash --------------------------------------
fut = d[(d.INSTRUMENT == "FUTIDX") & (d.SYMBOL == "NIFTY")]
fut_day = fut.groupby("TS")["CONTRACTS"].sum().sort_index()
window = fut_day.loc["2020-02-15":"2020-04-10"]
pre_crash_adv20 = fut_day.loc["2020-02-01":"2020-03-22"].tail(20).median()
window_df = window.to_frame("all_expiries_contracts")
window_df["ratio_to_pre_crash_adv20"] = window_df["all_expiries_contracts"] / pre_crash_adv20
window_df.to_csv(OUT / "stress_2020_futures_daily.csv")
print(f"\npre-crash ADV20 (2020-02 into 2020-03-22): {pre_crash_adv20:,.0f} lots/day")
print(window_df.to_string())
print(f"\n2020-03-23 volume = {fut_day.loc['2020-03-23']:,.0f} lots "
      f"= {fut_day.loc['2020-03-23']/pre_crash_adv20:.2f}x pre-crash ADV20")
print(f"2020-03-13 volume = {fut_day.loc['2020-03-13']:,.0f} lots "
      f"= {fut_day.loc['2020-03-13']/pre_crash_adv20:.2f}x pre-crash ADV20  (the day the market-wide halt is publicly documented)")
print(f"min day in window = {window.min():,.0f} on {window.idxmin().date()}  "
      f"({window.min()/pre_crash_adv20:.2f}x ADV20)")

# ---------------- OPTIONS: was there a live weekly/0DTE NIFTY expiry near 2020-03-23? ----------
opt = d[(d.INSTRUMENT == "OPTIDX") & (d.SYMBOL == "NIFTY")]
opt["EXPIRY_DT2"] = pd.to_datetime(opt["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce")
near = opt[(opt.EXPIRY_DT2 >= "2020-03-01") & (opt.EXPIRY_DT2 <= "2020-04-05")]
expiries = sorted(near.EXPIRY_DT2.dropna().unique())
print(f"\nNIFTY option expiries listed 2020-03-01..2020-04-05: {[str(pd.Timestamp(e).date()) for e in expiries]}")
zdte = opt[opt.TS == opt.EXPIRY_DT2]
zdte_2020 = zdte[(zdte.TS >= "2020-01-01") & (zdte.TS <= "2020-12-31")]
print(f"0DTE (TS==EXPIRY_DT) NIFTY option rows found in ALL of 2020: {len(zdte_2020):,} "
      f"across {zdte_2020.TS.nunique()} distinct 0DTE days")
if zdte_2020.TS.nunique() > 0:
    print("distinct 0DTE days in 2020:", sorted(d.date() for d in zdte_2020.TS.dt.date.unique())[:10], "...")
