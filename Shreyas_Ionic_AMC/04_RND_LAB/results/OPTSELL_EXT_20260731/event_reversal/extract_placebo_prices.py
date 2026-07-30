"""
Step 2: extract REAL EOD ATM-straddle entry/exit prices for the placebo pool built in
build_placebo_pool.py. Mirrors Arm B's run_eod_option_extract.py exactly (same chainlock RAM
protocol, same eod_price() convention: last 3 minutes of the day's bar, ATM = nearest strike to
spot at that moment) so the placebo is priced on an IDENTICAL basis to the real event trades.
"""
import sys, gc, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")
import numpy as np
import pandas as pd
from chainlock import chain_slot, free_ram_gb
import chain

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTSELL_EXT_20260731\event_reversal"
CAND = pd.read_csv(f"{OUT}/placebo_candidates.csv", parse_dates=["entry_day", "exit_day", "event_day"])
print(f"[extract] {len(CAND)} placebo candidates", flush=True)

def pick_expiry(entry_day, exit_day):
    need = (exit_day.date() - entry_day.date()).days
    lo = max(need + 1, 2)
    return chain.nearest_expiry(entry_day.date(), min_dte=lo, max_dte=lo + 12)

CAND["expiry"] = CAND.apply(lambda r: pick_expiry(r["entry_day"], r["exit_day"]), axis=1)
missing = CAND["expiry"].isna().sum()
print(f"[expiry] {missing} candidates with no suitable expiry (dropped)", flush=True)
CAND = CAND.dropna(subset=["expiry"])

idx = chain.load_index()

def eod_price(df, day, atm=None, spot=None):
    day_str = str(day.date())
    dsub = df[df["trading_day"] == day_str]
    if len(dsub) == 0:
        return None
    t_last = dsub["t"].max()
    if spot is None:
        spot_row = idx.loc[:t_last]
        if len(spot_row) == 0:
            return None
        spot = float(spot_row["close"].iloc[-1])
    if atm is None:
        atm = round(spot / 50) * 50
        day_strikes = dsub["strike"].unique()
        if atm not in day_strikes and len(day_strikes) > 0:
            atm = int(day_strikes[np.argmin(np.abs(day_strikes - atm))])
    last_min = dsub["t"].max()
    win = dsub[dsub["t"] >= last_min - pd.Timedelta(minutes=3)]
    ce = win[(win["strike"] == atm) & (win["option_type"] == "CE")].sort_values("t")
    pe = win[(win["strike"] == atm) & (win["option_type"] == "PE")].sort_values("t")
    if len(ce) == 0 or len(pe) == 0:
        return None
    return spot, atm, float(ce.iloc[-1]["close"]), float(pe.iloc[-1]["close"]), t_last

out_rows = []
groups = CAND.groupby("expiry")
n_groups = len(groups)
print(f"[extract] {n_groups} distinct expiries", flush=True)
done = 0
t0 = time.time()
for exp, grp in groups:
    with chain_slot("aakash-optsell-placebo", min_free_gb=1.0):
        try:
            df = chain.load_expiry(exp)
        except Exception as e:
            print(f"[skip] expiry {exp} failed to load: {e}", flush=True)
            chain.load_expiry.cache_clear(); gc.collect()
            done += 1
            continue
        for _, row in grp.iterrows():
            r_entry = eod_price(df, row["entry_day"])
            if r_entry is None:
                continue
            spot_e, atm, ce_e, pe_e, t_e = r_entry
            r_exit = eod_price(df, row["exit_day"], atm=atm)
            if r_exit is None:
                continue
            spot_x, _, ce_x, pe_x, t_x = r_exit
            out_rows.append(dict(
                cell=row["cell"], entry_day=row["entry_day"], exit_day=row["exit_day"],
                event_day=row["event_day"], expiry=exp, atm=atm,
                spot_entry=spot_e, spot_exit=spot_x,
                ce_entry=ce_e, pe_entry=pe_e, ce_exit=ce_x, pe_exit=pe_x,
                note=row.get("note", ""),
            ))
        del df
    chain.load_expiry.cache_clear(); gc.collect()
    done += 1
    if done % 15 == 0 or done == n_groups:
        pd.DataFrame(out_rows).to_parquet(f"{OUT}/placebo_trades_raw.parquet")
        elapsed = time.time() - t0
        print(f"[ckpt] {done}/{n_groups} expiries, {len(out_rows)} trades, free RAM {free_ram_gb():.2f}GB, "
              f"elapsed {elapsed:.0f}s", flush=True)

R = pd.DataFrame(out_rows)
R.to_parquet(f"{OUT}/placebo_trades_raw.parquet")
print(f"[done] {len(R)} placebo trades extracted", flush=True)
print(R.groupby("cell").size())
