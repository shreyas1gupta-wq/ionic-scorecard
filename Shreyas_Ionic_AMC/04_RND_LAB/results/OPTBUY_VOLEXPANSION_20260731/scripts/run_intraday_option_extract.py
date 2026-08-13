"""Extract ATM straddle entry/exit prices for the intraday-gate candidates (G1_ML/G2_VOV/G3_ATRCONS),
2-hour hold, using the RAM-safe chainlock protocol (grab-extract-release, one expiry at a time).
"""
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
CHECKPOINT_EVERY = 20

T = pd.read_parquet(f"{OUT}/intraday_trade_candidates.parquet")
T["d"] = pd.to_datetime(T["d"]).dt.date
print(f"[extract] {len(T)} candidates over {T['d'].nunique()} distinct days", flush=True)

# nearest_expiry() is cheap (no chain load), safe to call outside a slot
T["expiry"] = T["d"].map(lambda d: chain.nearest_expiry(d, min_dte=0, max_dte=6))
missing = T["expiry"].isna().sum()
print(f"[expiry] {missing} candidates with no expiry found (dropped)", flush=True)
T = T.dropna(subset=["expiry"])

idx = chain.load_index()   # small (spot only), fine outside a slot, cached
print(f"[index] {len(idx):,} spot bars loaded for ATM-strike lookup", flush=True)

groups = T.groupby("expiry")
n_groups = len(groups)
print(f"[extract] {n_groups} distinct expiries to process", flush=True)

out_rows = []
done_expiries = 0
t_start = time.time()

# resume support: skip expiries already checkpointed
ckpt_path = f"{OUT}/intraday_trades_raw.parquet"
already = set()
if False:
    pass

for exp, grp in groups:
    if free_ram_gb() < 1.0:
        print(f"[LOW RAM {free_ram_gb():.2f}GB] checkpointing and continuing cautiously", flush=True)
    with chain_slot("optbuy-volexp-intraday", min_free_gb=1.0):
        df = chain.load_expiry(exp)
        for _, row in grp.iterrows():
            t0 = row["t"]
            entry_ts = t0 + pd.Timedelta(minutes=1)
            exit_ts = t0 + pd.Timedelta(minutes=FWD_MIN)
            # spot at signal time for ATM strike selection (use index, nearest <= t0)
            spot_row = idx.loc[:t0]
            if len(spot_row) == 0:
                continue
            spot = float(spot_row["close"].iloc[-1])
            atm = round(spot / 50) * 50
            day_str = str(row["d"])
            sub = df[(df["trading_day"] == day_str) & (df["strike"] == atm)]
            if len(sub) == 0:
                # fall back to nearest available strike that day
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
            ce_e = ce[ce["t"] >= entry_ts]
            pe_e = pe[pe["t"] >= entry_ts]
            ce_x = ce[ce["t"] >= exit_ts]
            pe_x = pe[pe["t"] >= exit_ts]
            if len(ce_e) == 0 or len(pe_e) == 0 or len(ce_x) == 0 or len(pe_x) == 0:
                continue
            ce_entry_px = float(ce_e.iloc[0]["open"])
            pe_entry_px = float(pe_e.iloc[0]["open"])
            ce_entry_t = ce_e.iloc[0]["t"]
            pe_entry_t = pe_e.iloc[0]["t"]
            ce_exit_px = float(ce_x.iloc[0]["close"])
            pe_exit_px = float(pe_x.iloc[0]["close"])
            ce_exit_t = ce_x.iloc[0]["t"]
            pe_exit_t = pe_x.iloc[0]["t"]
            spot_exit_row = idx.loc[:ce_exit_t]
            spot_exit = float(spot_exit_row["close"].iloc[-1]) if len(spot_exit_row) else np.nan
            out_rows.append(dict(
                t=t0, gate=row["gate"], expiry=exp, atm=atm,
                spot_entry=spot, spot_exit=spot_exit,
                ce_entry=ce_entry_px, pe_entry=pe_entry_px,
                ce_exit=ce_exit_px, pe_exit=pe_exit_px,
                entry_t=ce_entry_t, exit_t=ce_exit_t,
            ))
        del df
    chain.load_expiry.cache_clear(); gc.collect()
    done_expiries += 1
    if done_expiries % CHECKPOINT_EVERY == 0 or done_expiries == n_groups:
        pd.DataFrame(out_rows).to_parquet(ckpt_path)
        elapsed = time.time() - t_start
        print(f"[ckpt] {done_expiries}/{n_groups} expiries, {len(out_rows)} trades extracted, "
              f"{elapsed:.0f}s elapsed, free RAM {free_ram_gb():.2f}GB", flush=True)

R = pd.DataFrame(out_rows)
R.to_parquet(ckpt_path)
print(f"[done] {len(R)} trades extracted -> {ckpt_path}", flush=True)
print(R.groupby("gate").size())
