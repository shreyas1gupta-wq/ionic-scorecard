import sys, gc, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")
import numpy as np
import pandas as pd
from chainlock import chain_slot, free_ram_gb
import chain

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
FWD_MIN = 120

T = pd.read_parquet(f"{OUT}/placebo_trade_candidates.parquet")
T["d"] = pd.to_datetime(T["d"]).dt.date
print(f"[extract] {len(T)} placebo candidates", flush=True)
T["expiry"] = T["d"].map(lambda d: chain.nearest_expiry(d, min_dte=0, max_dte=6))
T = T.dropna(subset=["expiry"])
idx = chain.load_index()
groups = T.groupby("expiry")
n_groups = len(groups)
print(f"[extract] {n_groups} distinct expiries", flush=True)

out_rows = []
done = 0
t0s = time.time()
for exp, grp in groups:
    with chain_slot("optbuy-volexp-placebo", min_free_gb=1.0):
        df = chain.load_expiry(exp)
        for _, row in grp.iterrows():
            t0 = row["t"]
            entry_ts = t0 + pd.Timedelta(minutes=1)
            exit_ts = t0 + pd.Timedelta(minutes=FWD_MIN)
            spot_row = idx.loc[:t0]
            if len(spot_row) == 0:
                continue
            spot = float(spot_row["close"].iloc[-1])
            atm = round(spot / 50) * 50
            day_str = str(row["d"])
            sub = df[(df["trading_day"] == day_str) & (df["strike"] == atm)]
            if len(sub) == 0:
                day_strikes = df.loc[df["trading_day"] == day_str, "strike"]
                if len(day_strikes) == 0:
                    continue
                atm = int(day_strikes.iloc[(day_strikes - atm).abs().argsort()[:1]].values[0])
                sub = df[(df["trading_day"] == day_str) & (df["strike"] == atm)]
                if len(sub) == 0:
                    continue
            ce = sub[sub["option_type"] == "CE"].sort_values("t")
            pe = sub[sub["option_type"] == "PE"].sort_values("t")
            if len(ce) == 0 or len(pe) == 0:
                continue
            ce_e = ce[ce["t"] >= entry_ts]; pe_e = pe[pe["t"] >= entry_ts]
            ce_x = ce[ce["t"] >= exit_ts]; pe_x = pe[pe["t"] >= exit_ts]
            if len(ce_e) == 0 or len(pe_e) == 0 or len(ce_x) == 0 or len(pe_x) == 0:
                continue
            out_rows.append(dict(
                t=t0, gate=row["gate"], expiry=exp, atm=atm,
                spot_entry=spot,
                spot_exit=float(idx.loc[:ce_x.iloc[0]["t"], "close"].iloc[-1]),
                ce_entry=float(ce_e.iloc[0]["open"]), pe_entry=float(pe_e.iloc[0]["open"]),
                ce_exit=float(ce_x.iloc[0]["close"]), pe_exit=float(pe_x.iloc[0]["close"]),
            ))
        del df
    chain.load_expiry.cache_clear(); gc.collect()
    done += 1
    if done % 20 == 0 or done == n_groups:
        pd.DataFrame(out_rows).to_parquet(f"{OUT}/placebo_trades_raw.parquet")
        print(f"[ckpt] {done}/{n_groups} expiries, {len(out_rows)} trades, "
              f"{time.time()-t0s:.0f}s, free {free_ram_gb():.2f}GB", flush=True)

R = pd.DataFrame(out_rows)
R.to_parquet(f"{OUT}/placebo_trades_raw.parquet")
print(f"[done] {len(R)} placebo trades", flush=True)
