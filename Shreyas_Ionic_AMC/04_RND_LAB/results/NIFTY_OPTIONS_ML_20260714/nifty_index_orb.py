"""
TRUE 15-min ORB on the NIFTY INDEX itself (real 1-min spot data, 2015-2026) —
the one instrument we actually have genuine intraday spot bars for.
Break above opening-range (9:15-9:30) high -> long to EOD; break below low ->
short to EOD. Reports raw edge (spot terms); a real options implementation
would need the day's option premium, which decays against a slow move -
flagged as a translation gap, not tested here (would need per-day option
selection identical to the straddle dataset's ATM logic).
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

F = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"

d = pd.read_parquet(F).reset_index()
d = d.rename(columns={d.columns[0]: "dt"}) if "dt" not in d.columns else d
d["dt"] = pd.to_datetime(d["dt"])
d["date"] = d["dt"].dt.date
d["time"] = d["dt"].dt.time

OR_END = pd.to_datetime("09:30:00").time()

rows = []
for day, g in d.groupby("date"):
    g = g.sort_values("dt")
    orb = g[g["time"] < OR_END]
    if len(orb) < 10:
        continue
    or_hi, or_lo = orb["high"].max(), orb["low"].min()
    rest = g[g["time"] >= OR_END]
    if len(rest) < 5:
        continue
    close = g["close"].iloc[-1]
    # first breakout direction+bar after OR window
    brk_up = rest[rest["high"] > or_hi]
    brk_dn = rest[rest["low"] < or_lo]
    up_t = brk_up["dt"].iloc[0] if len(brk_up) else pd.NaT
    dn_t = brk_dn["dt"].iloc[0] if len(brk_dn) else pd.NaT
    direction = 0
    entry_px = np.nan
    if pd.notna(up_t) and (pd.isna(dn_t) or up_t < dn_t):
        direction = 1; entry_px = or_hi
    elif pd.notna(dn_t):
        direction = -1; entry_px = or_lo
    if direction == 0:
        continue
    ret_pct = (close/entry_px - 1) * 100 * direction
    rows.append({"date": day, "or_range_pct": (or_hi-or_lo)/orb["close"].iloc[-1]*100,
                "direction": direction, "entry_px": entry_px, "close": close, "ret_pct": ret_pct})

r = pd.DataFrame(rows)
print(f"NIFTY 15-min ORB: {len(r)} days with a breakout ({len(r)/d['date'].nunique()*100:.1f}% of all days)")
print(f"  long days: {(r['direction']==1).sum()}, short days: {(r['direction']==-1).sum()}")
print(f"  mean ret {r['ret_pct'].mean():.3f}% | win {(r['ret_pct']>0).mean()*100:.1f}% | "
      f"Sharpe(raw,no cost) {r['ret_pct'].mean()/r['ret_pct'].std()*np.sqrt(252):.2f}")
r["year"] = pd.to_datetime(r["date"]).dt.year
print(r.groupby("year")["ret_pct"].agg(["count","mean",lambda x:(x>0).mean()*100]).to_string())
r.to_csv(os.path.join(OUT, "nifty_index_orb_results.csv"), index=False)
