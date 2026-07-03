"""Store the MAX-POSSIBLE year-wise list of big winners + all computable
characteristics → results CSVs. Captures every eligible name with year-return
>= 50% (and a top-40/year table), with start-of-year + intra-run features.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent / "processed"
OUT = Path(__file__).resolve().parent / "multibaggers"
OUT.mkdir(exist_ok=True)
cl = pd.read_parquet(P / "eq_close.parquet")
mem = pd.read_parquet(P / "membership.parquet")
close = cl.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()].ffill(limit=10)
mem["month"] = pd.to_datetime(mem["month"])
mw = mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
     aggfunc="any").reindex(columns=close.columns)
memmask = mw.reindex(close.index, method="ffill").fillna(False).astype(bool)

sma50 = close.rolling(50, min_periods=40).mean()
sma150 = close.rolling(150, min_periods=120).mean()
sma200 = close.rolling(200, min_periods=150).mean()
hi52 = close.rolling(252, min_periods=180).max()
lo52 = close.rolling(252, min_periods=180).min()
r3 = close / close.shift(63) - 1
r6 = close / close.shift(126) - 1
r12 = close / close.shift(252) - 1
vol60 = close.pct_change().rolling(60, min_periods=40).std() * np.sqrt(252)
rs = (0.6 * r12 + 0.4 * r6)

allrows = []
for y in range(2007, 2026):
    yd = close.index[close.index.year == y]
    if len(yd) < 100:
        continue
    t0, t1 = yd[0], yd[-1]
    elig = memmask.loc[t0] & close.loc[t0].notna() & close.loc[t1].notna() & (close.loc[t0] >= 10)
    syms = elig[elig].index
    if not len(syms):
        continue
    win = close.loc[t0:t1, syms]
    yr_ret = win.iloc[-1] / win.iloc[0] - 1
    peak_gain = win.max() / win.iloc[0] - 1
    intra_dd = ((win.cummax() - win) / win.cummax()).max()
    # time to first 2x (trading days)
    dbl = (win / win.iloc[0] >= 2.0)
    t2x = dbl.apply(lambda c: int(c.values.argmax()) if c.any() else -1)
    rs_rank0 = rs.loc[t0, syms].rank(pct=True)
    df = pd.DataFrame({
        "year": y, "symbol": syms,
        "year_ret": yr_ret.values, "peak_gain": peak_gain.values,
        "intra_yr_maxDD": intra_dd.values, "days_to_2x": t2x.values,
        "start_price": close.loc[t0, syms].values,
        "prior_3m": r3.loc[t0, syms].values, "prior_6m": r6.loc[t0, syms].values,
        "prior_12m": r12.loc[t0, syms].values, "rs_rank_start": rs_rank0.values,
        "above_50dma_start": (close.loc[t0, syms] > sma50.loc[t0, syms]).values,
        "above_200dma_start": (close.loc[t0, syms] > sma200.loc[t0, syms]).values,
        "dist_from_52wH_start": (close.loc[t0, syms] / hi52.loc[t0, syms] - 1).values,
        "pct_above_52wL_start": (close.loc[t0, syms] / lo52.loc[t0, syms] - 1).values,
        "prior_vol_ann": vol60.loc[t0, syms].values,
    })
    allrows.append(df)

full = pd.concat(allrows, ignore_index=True)
winners = full[full["year_ret"] >= 0.50].sort_values(["year", "year_ret"], ascending=[True, False])
winners.to_csv(OUT / "winners_yearwise_50pct.csv", index=False)
top40 = (full.sort_values(["year", "year_ret"], ascending=[True, False])
         .groupby("year").head(40))
top40.to_csv(OUT / "top40_per_year.csv", index=False)

print(f"stored {len(winners)} winners (>=50%) and {len(top40)} top-40/yr rows -> {OUT}")
print(f"\nyear-wise counts: >=50% / >=100%(2x) / >=200%(3x):")
g = full.groupby("year")["year_ret"]
cnt = pd.DataFrame({">=50%": g.apply(lambda s: (s >= .5).sum()),
                    ">=2x": g.apply(lambda s: (s >= 1).sum()),
                    ">=3x": g.apply(lambda s: (s >= 2).sum())})
print(cnt.to_string())
print("\ntop-8 winners per year (symbol  year_ret  intraDD  rs_start  prior12m):")
for y in sorted(full["year"].unique()):
    t = winners[winners.year == y].head(8)
    s = "  ".join(f"{r.symbol}+{r.year_ret*100:.0f}%(dd{r.intra_yr_maxDD*100:.0f},rs{r.rs_rank_start*100:.0f})"
                  for _, r in t.iterrows())
    if s:
        print(f"{y}: {s}")
