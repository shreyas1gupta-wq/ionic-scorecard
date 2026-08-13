import sys, gc
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")
import numpy as np, pandas as pd
from chainlock import chain_slot, free_ram_gb
import chain

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
CAND = pd.read_csv(f"{OUT}/iv_term_trade_candidates.csv", parse_dates=["entry_day","exit_day","event_day"])

def pick_expiry(entry_day, exit_day):
    need = (exit_day.date() - entry_day.date()).days
    lo = max(need + 1, 2)
    return chain.nearest_expiry(entry_day.date(), min_dte=lo, max_dte=lo + 12)
CAND["expiry"] = CAND.apply(lambda r: pick_expiry(r["entry_day"], r["exit_day"]), axis=1)
CAND = CAND.dropna(subset=["expiry"])
print(CAND)

idx = chain.load_index()

def eod_price(df, day, atm=None):
    day_str = str(day.date())
    dsub = df[df["trading_day"] == day_str]
    if len(dsub) == 0:
        return None
    t_last = dsub["t"].max()
    spot_row = idx.loc[:t_last]
    if len(spot_row) == 0:
        return None
    spot = float(spot_row["close"].iloc[-1])
    if atm is None:
        atm = round(spot/50)*50
        day_strikes = dsub["strike"].unique()
        if atm not in day_strikes and len(day_strikes)>0:
            atm = int(day_strikes[np.argmin(np.abs(day_strikes-atm))])
    win = dsub[dsub["t"] >= t_last - pd.Timedelta(minutes=3)]
    ce = win[(win.strike==atm)&(win.option_type=="CE")].sort_values("t")
    pe = win[(win.strike==atm)&(win.option_type=="PE")].sort_values("t")
    if len(ce)==0 or len(pe)==0:
        return None
    return spot, atm, float(ce.iloc[-1]["close"]), float(pe.iloc[-1]["close"]), t_last

out_rows = []
for exp, grp in CAND.groupby("expiry"):
    with chain_slot("optbuy-volexp-ivterm", min_free_gb=1.0):
        df = chain.load_expiry(exp)
        for _, row in grp.iterrows():
            r_e = eod_price(df, row["entry_day"])
            if r_e is None: continue
            spot_e, atm, ce_e, pe_e, t_e = r_e
            r_x = eod_price(df, row["exit_day"], atm=atm)
            if r_x is None: continue
            spot_x, _, ce_x, pe_x, t_x = r_x
            out_rows.append(dict(cell=row["cell"], entry_day=row["entry_day"], exit_day=row["exit_day"],
                                  event_day=row["event_day"], expiry=exp, atm=atm,
                                  spot_entry=spot_e, spot_exit=spot_x, ce_entry=ce_e, pe_entry=pe_e,
                                  ce_exit=ce_x, pe_exit=pe_x, note=row["note"]))
        del df
    chain.load_expiry.cache_clear(); gc.collect()

R = pd.DataFrame(out_rows)
R.to_parquet(f"{OUT}/ivterm_trades_raw.parquet")
print(R)
print(f"[done] {len(R)} iv-term trades")
