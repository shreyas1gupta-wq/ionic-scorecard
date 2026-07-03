"""What the swing strategy would HOLD as of the latest data date (today's signal)."""
from pathlib import Path
import numpy as np, pandas as pd
P = Path(__file__).resolve().parent / "processed"
cl = pd.read_parquet(P / "eq_close.parquet")
close = cl.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()].ffill(limit=10)
mem = pd.read_parquet(P / "membership.parquet"); mem["month"] = pd.to_datetime(mem["month"])
mw = mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v", aggfunc="any").reindex(columns=close.columns)
mm = mw.reindex(close.index, method="ffill").fillna(False).astype(bool)
s50=close.rolling(50,min_periods=40).mean(); s150=close.rolling(150,min_periods=120).mean()
s200=close.rolling(200,min_periods=150).mean(); hi=close.rolling(252,min_periods=180).max(); lo=close.rolling(252,min_periods=180).min()
r6=close/close.shift(126)-1; r12=close/close.shift(252)-1
trend=((close>s150)&(s150>s200)&(s200>s200.shift(21))&(close>s50)&(s50>s150)&(close>=1.25*lo)&(close>=0.75*hi))
elig=trend&mm&r12.notna()&(close>=20)
rs=(0.6*r12+0.4*r6).where(elig).rank(axis=1,pct=True)
nif=pd.read_csv(Path(__file__).resolve().parents[1]/"intraday_options_strategy/datasets/raw/nifty50_daily.csv",parse_dates=["Date"]).set_index("Date")["Close"].sort_index()
nif=nif[~nif.index.duplicated()].reindex(close.index).ffill()
breadth=(close>s200).where(mm).mean(axis=1)
green=(nif>nif.rolling(200,min_periods=200).mean())&(nif>nif.rolling(50,min_periods=50).mean())&(breadth>0.40)
t=close.index[-1]
print(f"AS-OF data date: {t.date()}  (NOTE: panel ends here; fetch live equity data to update to real today)")
print(f"REGIME: {'GREEN (deploy)' if bool(green.loc[t]) else 'RED (cash)'}  | breadth %>200DMA = {breadth.loc[t]:.0%}  | eligible leaders = {int(elig.loc[t].sum())}")
top=rs.loc[t].dropna().sort_values(ascending=False).head(20)
print(f"\nTOP-20 leader picks (would hold if GREEN):")
for s,v in top.items():
    print(f"  {s:14} RS {v*100:.0f}  px {close.loc[t,s]:.0f}  12m {r12.loc[t,s]*100:+.0f}%")
