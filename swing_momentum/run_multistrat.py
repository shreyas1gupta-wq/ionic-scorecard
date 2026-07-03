"""Multi-strategy proof: do MOMENTUM (buy strength) + MEAN-REVERSION (buy
oversold dips in uptrends) — naturally low-correlated equity sleeves — combine
into a higher-Sharpe, lower-DD book than either alone? Same survivorship-safe
panel, same regime gate / costs / survivorship handling as run_swing V2.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent / "processed"
COST_BPS, TOP_N, RF = 30, 20, 0.06

cl = pd.read_parquet(P / "eq_close.parquet")
mem = pd.read_parquet(P / "membership.parquet")
close = cl.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()].ffill(limit=10)
mem["month"] = pd.to_datetime(mem["month"])
mwide = mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
        aggfunc="any").reindex(columns=close.columns)
memmask = mwide.reindex(close.index, method="ffill").fillna(False).astype(bool)

dl = pd.read_excel(Path(__file__).resolve().parents[1] / "Nifty500_Delisted_2005_2025.xlsx")
dl = dl.rename(columns={dl.columns[0]: "date"}); dl["date"] = pd.to_datetime(dl["date"], errors="coerce")
dl = dl.dropna(subset=["date"]).set_index("date")
delist_date = {str(s).upper(): pd.to_numeric(dl[s], errors="coerce").dropna().index.max()
               for s in dl.columns if pd.to_numeric(dl[s], errors="coerce").notna().any()}

sma50 = close.rolling(50, min_periods=40).mean()
sma150 = close.rolling(150, min_periods=120).mean()
sma200 = close.rolling(200, min_periods=150).mean()
hi52 = close.rolling(252, min_periods=180).max(); lo52 = close.rolling(252, min_periods=180).min()
ret6, ret12 = close / close.shift(126) - 1, close / close.shift(252) - 1
ret10 = close / close.shift(10) - 1
d = close.diff()
rsi = 100 - 100 / (1 + (d.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean() /
      (-d.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()))
uptrend = (close > sma200) & memmask & (close >= 20) & ret12.notna()

# regime (clean Nifty)
nif = pd.read_csv(Path(__file__).resolve().parents[1] /
      "intraday_options_strategy/datasets/raw/nifty50_daily.csv", parse_dates=["Date"]
      ).set_index("Date")["Close"].sort_index()
nif = nif[~nif.index.duplicated()].reindex(close.index).ffill()
breadth = (close > sma200).where(memmask).mean(axis=1)
green = ((nif > nif.rolling(200, min_periods=200).mean()) &
         (nif > nif.rolling(50, min_periods=50).mean()) & (breadth > 0.40)).fillna(False)

# MOMENTUM sleeve score: trend template pass, ranked by RS
trend = (uptrend & (close > sma150) & (sma150 > sma200) & (close > sma50) & (sma50 > sma150)
         & (close >= 1.25 * lo52) & (close >= 0.75 * hi52))
mom_score = (0.6 * ret12 + 0.4 * ret6).where(trend).rank(axis=1, pct=True)
# MEAN-REVERSION sleeve score: oversold (low rsi, recent dip) WITHIN an uptrend
mrev_ok = uptrend & (rsi < 40) & (ret10 < 0)
mrev_score = (-ret10).where(mrev_ok).rank(axis=1, pct=True)   # most oversold = highest rank

rebal = close.index[::5]
fwd = close.shift(-5) / close - 1


def run(score):
    eq, dates, held = [1.0], [close.index[0]], set()
    for t in rebal:
        if t not in score.index:
            continue
        if green.get(t, False):
            picks = list(score.loc[t].dropna().sort_values(ascending=False).head(TOP_N).index)
        else:
            picks = []
        if picks:
            vals = []
            for s in picks:
                v = fwd.at[t, s] if s in fwd.columns else np.nan
                if pd.isna(v) or np.isinf(v):
                    dd = delist_date.get(s)
                    v = -0.5 if (dd is not None and t <= dd <= t + pd.Timedelta(days=12)) else None
                if v is not None:
                    vals.append(v)
            port = float(np.mean(vals)) if vals else 0.0
        else:
            port = 0.0
        turn = len(held.symmetric_difference(set(picks))) / max(TOP_N, 1)
        eq.append(eq[-1] * (1 + port - turn * COST_BPS / 1e4)); dates.append(t); held = set(picks)
    return pd.Series(eq[1:], index=pd.DatetimeIndex(dates[1:]))


def stats(e, label):
    r = e.pct_change().dropna(); yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1; vol = r.std() * np.sqrt(52)
    sh = (r.mean() * 52 - RF) / vol if vol > 0 else 0
    mdd = ((e.cummax() - e) / e.cummax()).max()
    print(f"{label:20} CAGR {cagr:+6.1%}  Sharpe {sh:5.2f}  MaxDD {mdd:5.1%}  Calmar {cagr/mdd if mdd>0 else 0:4.2f}")
    return r


print("multi-strategy: momentum + mean-reversion (same panel, regime-gated, V2 rules)\n")
em, er = run(mom_score), run(mrev_score)
rm, rr = stats(em, "MOMENTUM"), stats(er, "MEAN-REVERSION")
# align weekly returns, correlation, inverse-vol (risk-parity) combo
df = pd.DataFrame({"mom": rm, "mrev": rr}).dropna()
corr = df["mom"].corr(df["mrev"])
wv = 1 / df.std(); wv /= wv.sum()
combo = (df * wv).sum(axis=1)
ce = (1 + combo).cumprod()
print(f"\ncorrelation(momentum, mean-reversion) weekly = {corr:+.2f}")
stats(ce, "COMBO (risk-parity)")
print(f"weights: mom {wv['mom']:.0%} / mrev {wv['mrev']:.0%}")
print("\n=> if combo Sharpe/Calmar > best single sleeve, the uncorrelated-stack thesis holds.")
