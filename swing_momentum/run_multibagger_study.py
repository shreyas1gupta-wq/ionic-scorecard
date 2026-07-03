"""MULTIBAGGER ANATOMY + regime-scaled leverage compounding.

A) For each year, find the biggest winners (>=2x) and measure what they SHOWED
   at the start of the year and during the run: prior momentum, trend stage
   (above 200DMA), distance from 52w high (base-breakout vs extended), prior
   volatility, price tier, and — critically — the MAX DRAWDOWN you'd have endured
   holding them (the heat that shakes people out). Plus: would our trend-template
   have flagged them, and how early?
B) Regime-scaled leverage + cash: compound aggressively only when the regime is
   strong; cash in weak regimes. Honest CAGR/MaxDD/Calmar leverage tradeoff.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent / "processed"
cl = pd.read_parquet(P / "eq_close.parquet")
mem = pd.read_parquet(P / "membership.parquet")
close = cl.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()].ffill(limit=10)
mem["month"] = pd.to_datetime(mem["month"])
mwide = mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
        aggfunc="any").reindex(columns=close.columns)
memmask = mwide.reindex(close.index, method="ffill").fillna(False).astype(bool)

sma200 = close.rolling(200, min_periods=150).mean()
hi52 = close.rolling(252, min_periods=180).max()
ret252 = close / close.shift(252) - 1
vol60 = close.pct_change().rolling(60, min_periods=40).std() * np.sqrt(252)
sma50 = close.rolling(50, min_periods=40).mean(); sma150 = close.rolling(150, min_periods=120).mean()
lo52 = close.rolling(252, min_periods=180).min()
trend_ok = ((close > sma150) & (sma150 > sma200) & (close > sma50) & (sma50 > sma150)
            & (close >= 1.25 * lo52) & (close >= 0.75 * hi52))

years = range(2007, 2026)
rows, anat = [], []
for y in years:
    yd = close.index[close.index.year == y]
    if len(yd) < 100:
        continue
    t0, t1 = yd[0], yd[-1]
    elig = memmask.loc[t0] & (close.loc[t0] >= 20) & close.loc[t1].notna() & close.loc[t0].notna()
    yr_ret = (close.loc[t1] / close.loc[t0] - 1).where(elig)
    mb = yr_ret[yr_ret >= 1.0].dropna()           # >=2x in the year
    if not len(mb):
        continue
    # intra-year max drawdown per multibagger (peak-to-trough heat)
    win = close.loc[t0:t1, mb.index]
    dd = ((win.cummax() - win) / win.cummax()).max()
    # features AT START
    f = pd.DataFrame({
        "year_ret": mb,
        "prior_12m": ret252.loc[t0, mb.index],
        "above_200dma_start": (close.loc[t0, mb.index] > sma200.loc[t0, mb.index]),
        "pct_from_52wH_start": (close.loc[t0, mb.index] / hi52.loc[t0, mb.index] - 1),
        "prior_vol": vol60.loc[t0, mb.index],
        "start_price": close.loc[t0, mb.index],
        "intra_yr_maxDD": dd,
        "passed_trend_in_yr": trend_ok.loc[t0:t1, mb.index].any(),
    })
    anat.append(f.assign(year=y))
    rows.append({"year": y, "n_2x": int((yr_ret >= 1).sum()), "n_3x": int((yr_ret >= 2).sum()),
                 "best": f"{mb.idxmax()} {mb.max():.0%}",
                 "med_prior12m": f.prior_12m.median(), "pct_above200_start": f.above_200dma_start.mean(),
                 "med_from52wH": f.pct_from_52wH_start.median(), "med_priorvol": f.prior_vol.median(),
                 "med_intraDD": f.intra_yr_maxDD.median(), "pct_caught": f.passed_trend_in_yr.mean()})

summ = pd.DataFrame(rows).set_index("year")
A = pd.concat(anat)
pd.set_option("display.width", 200)
print("=== MULTIBAGGER (>=2x) ANATOMY BY YEAR ===")
print(summ.assign(med_prior12m=summ.med_prior12m.map("{:+.0%}".format),
                  pct_above200_start=summ.pct_above200_start.map("{:.0%}".format),
                  med_from52wH=summ.med_from52wH.map("{:.0%}".format),
                  med_priorvol=summ.med_priorvol.map("{:.0%}".format),
                  med_intraDD=summ.med_intraDD.map("{:.0%}".format),
                  pct_caught=summ.pct_caught.map("{:.0%}".format)).to_string())

print("\n=== POOLED PROFILE of all multibaggers (what they showed) ===")
print(f"  count: {len(A)} multibagger-years")
print(f"  median prior-12m momentum at year start : {A.prior_12m.median():+.0%}")
print(f"  %% already ABOVE 200DMA at year start    : {A.above_200dma_start.mean():.0%}  (stage-2 uptrend)")
print(f"  median distance from 52w high at start   : {A.pct_from_52wH_start.median():.0%}")
print(f"  median prior 60d volatility (annualised) : {A.prior_vol.median():.0%}")
print(f"  median start price                       : Rs.{A.start_price.median():.0f}")
print(f"  median INTRA-year max drawdown (the heat): {A.intra_yr_maxDD.median():.0%}  <-- stops must respect this")
print(f"  %% that passed our trend-template in-year : {A.passed_trend_in_yr.mean():.0%}  (catchable)")
print(f"  %% that were ALREADY uptrend+near-high at start (pre-identifiable leaders): "
      f"{((A.above_200dma_start) & (A.pct_from_52wH_start > -0.25)).mean():.0%}")

# --- B) regime-scaled leverage + cash compounding on momentum weekly returns ---
nif = pd.read_csv(Path(__file__).resolve().parents[1] /
      "intraday_options_strategy/datasets/raw/nifty50_daily.csv", parse_dates=["Date"]
      ).set_index("Date")["Close"].sort_index()
nif = nif[~nif.index.duplicated()].reindex(close.index).ffill()
breadth = (close > sma200).where(memmask).mean(axis=1)
strong = ((nif > nif.rolling(200, min_periods=200).mean()) & (nif > nif.rolling(50, min_periods=50).mean()))
# exposure: 0 if not strong(cash); else scale 0.5..base_lev by breadth (40%..75%)
def exposure(base):
    e = ((breadth.clip(0.40, 0.75) - 0.40) / 0.35) * (base - 0.5) + 0.5
    return e.where(strong, 0.0).fillna(0.0)

# momentum weekly returns (reuse simple top-20 RS leadership, regime via exposure)
rs = (0.6 * ret252 + 0.4 * (close / close.shift(126) - 1)).where(trend_ok & memmask & (close >= 20))
rsr = rs.rank(axis=1, pct=True)
rebal = close.index[::5]; fwd = close.shift(-5) / close - 1
def lev_run(base):
    eq=[1.0]; idx=[close.index[0]]
    for t in rebal:
        if t not in rsr.index: continue
        picks=list(rsr.loc[t].dropna().sort_values(ascending=False).head(20).index)
        r=fwd.loc[t,picks].replace([np.inf,-np.inf],np.nan).dropna()
        base_ret=r.mean() if len(r) else 0.0
        ex=float(exposure(base).get(t,0.0))
        eq.append(eq[-1]*(1+ex*base_ret-0.003*ex*0.25)); idx.append(t)
    return pd.Series(eq[1:],index=pd.DatetimeIndex(idx[1:]))
print("\n=== REGIME-SCALED LEVERAGE + CASH (compounding) ===")
print(f"{'base_lev':>9} {'CAGR':>8} {'MaxDD':>7} {'Calmar':>7}")
for base in [1.0, 1.25, 1.5, 2.0]:
    e=lev_run(base); yrs=(e.index[-1]-e.index[0]).days/365.25
    cagr=e.iloc[-1]**(1/yrs)-1; mdd=((e.cummax()-e)/e.cummax()).max()
    print(f"{base:>9.2f} {cagr:>+7.1%} {mdd:>7.1%} {cagr/mdd if mdd>0 else 0:>7.2f}")
print("(exposure=0 in weak regime [cash], scales 0.5x->base_lev by breadth in strong regime)")
