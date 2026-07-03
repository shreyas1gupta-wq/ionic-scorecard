"""Backfill the 8 blank live_price legs (25AUG2026 earnings PE legs) in the execution CSVs.
Root cause: execution_scanner prices only FRONT-month PEs; the earnings pairs carry a
BACK-month (25AUG) PE leg that never got a quote. Tanvi catch #1 (2026-07-04).
Weekend note: LTP fetched on a non-trading day = last close. iv_source is annotated.
Run from this directory (needs scrip_master.json + angel_cfg on path).
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")  # creds OUTSIDE repo (D-003)
import angel_cfg as A

ROOT = HERE.parents[2]  # NIFTY 500 root
OUTD = ROOT / "FINAL_STRATEGY_FORWARD_CHECK" / "08_Execution"

obj, sess = A.login()
print("login OK")
scrip = json.loads(Path(r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\scrip_master.json").read_bytes())

df = pd.read_csv(OUTD / "execution_ALL.csv")
blanks = df[df["live_price"].isna()].copy()
print(f"blank legs: {len(blanks)}")

# (name, expiry, opt_type, strike) -> token
chain = {}
for x in scrip:
    if x.get("exch_seg") == "NFO" and x.get("instrumenttype") == "OPTSTK":
        k = round(float(x["strike"]) / 100, 2)
        chain[(x["name"], x["expiry"], x["symbol"][-2:], k)] = x["token"]

need = {}
for i, r in blanks.iterrows():
    key = (r["symbol"], r["expiry"], str(r["opt"]).upper(), round(float(r["strike"]), 2))
    tok = chain.get(key)
    if tok is None:
        print("  NO TOKEN for", key)
    else:
        need[i] = str(tok)

ltp = {}
toks = list(dict.fromkeys(need.values()))
for j in range(0, len(toks), 45):
    r = obj.getMarketData("LTP", {"NFO": toks[j:j + 45]})
    for f in r.get("data", {}).get("fetched", []):
        ltp[str(f["symbolToken"])] = f.get("ltp")
    time.sleep(0.5)

stamp = dt.date.today().isoformat()
filled = 0
for i, tok in need.items():
    px = ltp.get(tok)
    if px:
        df.loc[i, "live_price"] = float(px)
        df.loc[i, "iv_source"] = f"backfilled_close_{stamp}"
        filled += 1
        print(f"  {df.loc[i,'symbol']:<12} {df.loc[i,'expiry']} {df.loc[i,'strike']:>8} PE -> {px}")

print(f"filled {filled}/{len(blanks)}")
if filled:
    df.to_csv(OUTD / "execution_ALL.csv", index=False)
    # keep the per-strategy + scored CSVs consistent
    sub = df[df["strategy"] == "Earnings_ShortVol"]
    sub.to_csv(OUTD / "execution_Earnings_ShortVol.csv", index=False)
    scored = pd.read_csv(OUTD / "execution_scored.csv")
    keycols = ["strategy", "symbol", "expiry", "strike", "opt", "action"]
    m = df.set_index(keycols)["live_price"]
    mask = scored["live_price"].isna()
    scored.loc[mask, "live_price"] = scored.loc[mask].set_index(keycols).index.map(m).values
    if "iv_source" in scored.columns:
        scored.loc[mask & scored["live_price"].notna(), "iv_source"] = f"backfilled_close_{stamp}"
    scored.to_csv(OUTD / "execution_scored.csv", index=False)
    print("patched execution_ALL / execution_Earnings_ShortVol / execution_scored")
print("DONE")
