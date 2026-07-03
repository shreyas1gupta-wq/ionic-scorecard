"""FIRST REAL-FILL 0DTE — ATM short straddle on actual 1-min option prices
(HF india-index-options-1m), no synthetic BS. Runs on whatever expiry files
have landed. Sell ATM CE+PE at 09:20 on expiry day, buy back 15:15. 0.5% slip."""
from pathlib import Path
import numpy as np, pandas as pd
B = Path(__file__).resolve().parent / "datasets" / "raw" / "hf_index_options_1m"
IDX = "NIFTY"; STEP = 50; LOT = 75; SLIP = 0.005
idx = pd.read_parquet(B / "index" / f"{IDX}.parquet")
idx["t"] = pd.to_datetime(idx["timestamp"]).dt.tz_localize(None)
idx = idx.set_index("t")["close"]
opt_dir = B / "options" / IDX
files = sorted([f for f in opt_dir.glob("*.parquet") if f.stat().st_size > 50000])
print(f"{IDX}: {len(files)} expiry files landed\n")
rows = []
for f in files:
    exp = f.stem
    d = pd.read_parquet(f).drop_duplicates(["timestamp", "strike", "option_type"])
    d["t"] = pd.to_datetime(d["timestamp"]).dt.tz_localize(None)
    d = d[d["trading_day"].astype(str) == exp]                  # 0DTE = expiry-day bars
    if d.empty:
        continue
    t920 = pd.Timestamp(exp + " 09:20:00"); t1515 = pd.Timestamp(exp + " 15:15:00")
    sp = idx.reindex([t920], method="nearest")
    if sp.isna().all():
        continue
    spot = float(sp.iloc[0]); atm = round(spot / STEP) * STEP
    def px(typ, ts):
        r = d[(d["strike"] == atm) & (d["option_type"] == typ)].set_index("t")["close"]
        if r.empty: return None
        v = r.reindex([ts], method="nearest")
        return float(v.iloc[0]) if not v.isna().all() else None
    ce0, pe0, ceX, peX = px("CE", t920), px("PE", t920), px("CE", t1515), px("PE", t1515)
    if None in (ce0, pe0, ceX, peX):
        continue
    spotX = float(idx.reindex([t1515], method="nearest").iloc[0])
    entry = (ce0 + pe0) * (1 - SLIP); exit_ = (ceX + peX) * (1 + SLIP)
    pnl = (entry - exit_) * LOT                                 # naked short straddle, per lot
    rows.append({"expiry": exp, "spot": round(spot), "atm": atm, "move%": round(spotX/spot-1, 4),
                 "straddle_in": round(ce0+pe0, 1), "straddle_out": round(ceX+peX, 1),
                 "pnl_lot": round(pnl)})
res = pd.DataFrame(rows)
print(res.to_string(index=False))
if len(res):
    w = res["pnl_lot"] > 0
    print(f"\nREAL-FILL {IDX} 0DTE naked short straddle: {len(res)} expiries, "
          f"WR {w.mean():.0%}, avg/lot Rs.{res['pnl_lot'].mean():,.0f}, total Rs.{res['pnl_lot'].sum():,.0f}")
    print("(REAL option fills, no BS model. Naked = no hedge. Lot=15, 0.5% slip. Small sample = landed files only.)")
