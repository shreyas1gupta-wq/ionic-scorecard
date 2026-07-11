"""Follow-up live pull: TCS front-month (2026-07-28) OTM CE candidates above the
2100 ATM strike -- real OI/volume, for Aakash's near-month vertical hedge-leg sanity check.
Reuses the same login pattern; ONE extra bulk quote call."""
from __future__ import annotations
import json, time
from pathlib import Path
import pandas as pd
import truststore; truststore.inject_into_ssl()
import pyotp
from SmartApi import SmartConnect

CAP_DIR = Path(r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
CREDS = json.loads((CAP_DIR / "creds.json").read_text())
scrip = json.loads((CAP_DIR / "scrip_master.json").read_bytes())

obj = SmartConnect(api_key=CREDS["api_key"])
totp = pyotp.TOTP(CREDS["totp_secret"]).now()
s = obj.generateSession(CREDS["client_id"], CREDS["pin"], totp)
assert s.get("status"), s
print("login OK")

tcs_ce_front = sorted(
    [x for x in scrip if x.get("exch_seg") == "NFO" and x.get("instrumenttype") == "OPTSTK"
     and x.get("name") == "TCS" and x.get("expiry") == "28JUL2026" and x["symbol"].endswith("CE")],
    key=lambda x: float(x["strike"]))
strikes = [float(x["strike"]) / 100 for x in tcs_ce_front]
print("TCS 28JUL2026 CE strikes available:", strikes)

atm = 2100.0
higher = sorted([x for x in tcs_ce_front if float(x["strike"]) / 100 > atm], key=lambda x: float(x["strike"]))
cands = higher[:5]
toks = [x["token"] for x in cands]
r = obj.getMarketData("FULL", {"NFO": toks})
time.sleep(1.2)
fetched = {str(f["symbolToken"]): f for f in r.get("data", {}).get("fetched", [])}
rows = []
for x in cands:
    f = fetched.get(str(x["token"]))
    rows.append(dict(strike=float(x["strike"]) / 100, symbol=x["symbol"],
                      ltp=f.get("ltp") if f else None,
                      oi=f.get("opnInterest") if f else None,
                      vol=f.get("tradeVolume") if f else None))
df = pd.DataFrame(rows)
print(df.to_string(index=False))
