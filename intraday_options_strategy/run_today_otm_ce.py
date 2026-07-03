"""Today's live trade: SELL ~1% OTM Nifty CE at 10:00, square off 15:20 (and show
expiry-intrinsic). Real Angel 1-min data. Creds via env only."""
from __future__ import annotations
import os, sys
from pathlib import Path
import truststore; truststore.inject_into_ssl()
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (BROKERAGE_PER_ORDER, GST_PCT, LOT_SIZE, NSE_TXN_PCT,
                    RAW_DIR, SEBI_PER_CRORE, STT_SELL_PCT, TOTAL_CAPITAL)
import pyotp
from SmartApi import SmartConnect
SLIP = 0.02
obj = SmartConnect(api_key=os.environ["ANGEL_API_KEY"])
obj.generateSession(os.environ["ANGEL_CLIENT"], os.environ["ANGEL_PIN"],
                    pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now())
today = pd.Timestamp.now().normalize()
m = pd.read_csv(RAW_DIR / "options" / "angel_nfo_nifty.csv", parse_dates=["expiry_dt"])
m = m[m["name"] == "NIFTY"]; expiry = m[m["expiry_dt"] >= today]["expiry_dt"].min()

def candles(tok, exch="NFO"):
    p = {"exchange": exch, "symboltoken": str(tok), "interval": "ONE_MINUTE",
         "fromdate": f"{today:%Y-%m-%d} 09:15", "todate": f"{today:%Y-%m-%d} 15:30"}
    d = obj.getCandleData(p).get("data", [])
    df = pd.DataFrame(d, columns=["dt","o","h","l","c","v"])
    if len(df): df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize(None); df = df.set_index("dt")
    return df

nif = candles("99926000", "NSE")
t10 = today + pd.Timedelta("10:00:00")
spot10 = float(nif["c"].get(t10, nif["c"].iloc[-1])) if len(nif) else 24000
strike = round(spot10 * 1.01 / 50) * 50
r = m[(m["expiry_dt"] == expiry) & np.isclose(m["strike"], strike) & m["symbol"].str.endswith("CE")]
print(f"today {today:%Y-%m-%d}, expiry {expiry:%Y-%m-%d} {'(0DTE)' if expiry.normalize()==today else ''}; "
      f"spot@10:00 {spot10:.0f}, 1%OTM CE strike {strike} ({r.iloc[0]['symbol'] if len(r) else 'NOT FOUND'})")
if not len(r): sys.exit("strike not in master")
ce = candles(r.iloc[0]["token"])
if not len(ce): sys.exit("no CE candles (market closed/early?)")
sell_t = ce.index[ce.index.get_indexer([t10], method="nearest")[0]]
entry = float(ce.loc[sell_t, "c"])
x = ce.index[ce.index.get_indexer([today + pd.Timedelta('15:20:00')], method="nearest")[0]]
exit_px = float(ce.loc[x, "c"])
spot_close = float(nif["c"].iloc[-1]) if len(nif) else spot10
intrinsic = max(spot_close - strike, 0)
lots = max(1, int(0.006 * TOTAL_CAPITAL / (0.25 * entry * LOT_SIZE))) if entry > 0 else 1
units = lots * LOT_SIZE
ef = entry * (1 - SLIP); xf = exit_px * (1 + SLIP)
turn = (ef + xf) * units
cost = STT_SELL_PCT * ef * units + NSE_TXN_PCT * turn * (1 + GST_PCT) + SEBI_PER_CRORE * turn / 1e7 \
       + BROKERAGE_PER_ORDER * 2 * (1 + GST_PCT) * lots
pnl_sqoff = (ef - xf) * units - cost
pnl_expiry = (ef - intrinsic * (1 + SLIP)) * units - cost
print(f"\nSELL {lots} lot ({units} qty) {strike}CE @10:00 = {entry:.1f} (fill {ef:.1f} post-slip)")
print(f"premium collected: Rs.{ef*units:,.0f}")
print(f"  square-off 15:20: CE={exit_px:.1f} -> NET P&L Rs.{pnl_sqoff:,.0f} ({pnl_sqoff/TOTAL_CAPITAL:+.3%})")
print(f"  held-to-expiry  : spot_close {spot_close:.0f}, intrinsic {intrinsic:.1f} -> NET Rs.{pnl_expiry:,.0f} ({pnl_expiry/TOTAL_CAPITAL:+.3%})")
print(f"  (costs Rs.{cost:,.0f}; naked-CE risk: unlimited if spot spikes > {strike})")
