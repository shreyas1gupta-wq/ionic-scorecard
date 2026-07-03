"""23-Jun-2026 0DTE estimate on REAL Nifty index path + VIX (synthetic option
pricing, m=0.80 trading-time) — since the real expired option contract is not
retrievable from Angel. Delta-hedged ATM short straddle, 09:20 entry -> 14:30."""
import os, sys; from pathlib import Path
import numpy as np, pandas as pd
import truststore; truststore.inject_into_ssl()
R = Path(__file__).resolve().parent; sys.path.insert(0, str(R))
from options.bs_pricing import bs_price, bs_greeks
from config import RISK_FREE_RATE as r, DIVIDEND_YIELD as q, LOT_SIZE as LOT
import pyotp; from SmartApi import SmartConnect
o = SmartConnect(api_key=os.environ["ANGEL_API_KEY"])
o.generateSession(os.environ["ANGEL_CLIENT"], os.environ["ANGEL_PIN"], pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now())
def cd(tok):
    d = o.getCandleData({"exchange":"NSE","symboltoken":tok,"interval":"ONE_MINUTE",
        "fromdate":"2026-06-23 09:15","todate":"2026-06-23 15:30"}).get("data",[])
    df = pd.DataFrame(d, columns=["dt","o","h","l","c","v"]); df["dt"]=pd.to_datetime(df["dt"]).dt.tz_localize(None)
    return df.set_index("dt")
nif = cd("99926000")["c"]; vix = cd("99926017")["c"]
if not len(nif): print("no index data for 23-Jun"); sys.exit()
exp_close = pd.Timestamp("2026-06-23 15:30"); TMY = 252*375; M, SLIP = 0.80, 0.02
t0 = pd.Timestamp("2026-06-23 09:20"); te = pd.Timestamp("2026-06-23 14:30")
bars = [b for b in nif.index if t0 <= b <= te]
s0 = float(nif[bars[0]]); atm = round(s0/50)*50; sig0 = float(vix.reindex(nif.index).ffill()[bars[0]])/100*M
def tte(b): return max((exp_close-b).total_seconds()/60,1)/TMY
strd0 = float(bs_price(s0,atm,tte(bars[0]),sig0,r,q,True)+bs_price(s0,atm,tte(bars[0]),sig0,r,q,False))
hedge=0.0; hpnl=0.0; prev=s0; nreb=0; vser=vix.reindex(nif.index).ffill()
for b in bars:
    s=float(nif[b]); hpnl+=hedge*(s-prev); prev=s; sig=float(vser[b])/100*M; t=tte(b)
    dC=float(bs_greeks(s,atm,t,sig,r,q,True)["delta"]); dP=float(bs_greeks(s,atm,t,sig,r,q,False)["delta"])
    tgt=dC+dP
    if abs(tgt-hedge)>0.25: nreb+=1; hedge=tgt
sx=float(nif[bars[-1]]); sigx=float(vser[bars[-1]])/100*M
strdX=float(bs_price(sx,atm,tte(bars[-1]),sigx,r,q,True)+bs_price(sx,atm,tte(bars[-1]),sigx,r,q,False))
straddle=(strd0*(1-SLIP)-strdX*(1+SLIP))*LOT
hedge_rs=(hpnl-abs(hedge)*0.5)*LOT
cost=0.000625*strd0*(1-SLIP)*LOT+0.00053*(strd0+strdX)*LOT*1.18+20*1.18*(4+nreb+1)
net=straddle+hedge_rs-cost
print(f"23-Jun-2026 0DTE (synthetic on REAL index path): spot {s0:.0f}->{sx:.0f} (move {sx/s0-1:+.2%})")
print(f"  ATM {atm} straddle credit {strd0:.1f} -> buyback {strdX:.1f}")
print(f"  per lot: straddle {straddle/LOT:+.0f} + hedge {hedge_rs/LOT:+.0f} - cost {cost/LOT:.0f} = NET {net/LOT:+.0f}/lot ({nreb} rebal)")
print(f"  29 lots (~Rs1Cr 0.6% risk): NET Rs.{net*29:,.0f} ({net*29/1e7:+.2%})")
print("NOTE: SYNTHETIC option prices (m=0.80xVIX), NOT real fills — real 23-Jun contract unavailable from Angel.")
