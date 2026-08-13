"""RANDOM-ENTRY PLACEBO for the surviving candle cells.

THE QUESTION THIS ANSWERS, AND IT IS THE ONLY ONE THAT MATTERS HERE:
  A cell is "formation X inside trend filter Y, harvested at Z". If it makes money, that could be the
  FORMATION or it could be the FILTER. A 9/21-EMA-bull filter alone selects for up-trending regimes,
  and a 1.5-RR long harvest inside an uptrend will look good with NO pattern recognition at all.

  So for each cell I draw random entry bars that are matched on:
    - the same trend-filter state (only bars where filter Y is true)
    - the same time-of-day distribution (sampled within the cell's own hh:mm histogram)
    - the same count
  and run the IDENTICAL stop/target/trail machinery. If the formation adds nothing, the placebo
  earns the same and the cell is the filter wearing a costume.

  This is the control that INDICATOR_MINE used to kill 9 of its 15 cells, and it is the one control
  that would have caught the 226% loss-clip and the +3.03 trail if they had been run through it.
"""
from __future__ import annotations

import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathsafe import simulate_exit      # noqa: E402

OUT = Path(__file__).parent
N_DRAW = 200
BREAK = pd.Timestamp("2024-10-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
MAX_BARS, SLIP = 78, 0.5
RNG = np.random.default_rng(4242)

R = pd.read_csv(OUT / "cells.csv")
print(f"[load] {len(R)} cells", flush=True)

# rebuild the exact same bar frame the sweep used
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
b15 = (p1.resample("15min", origin="start_day", offset="9h15min")
       .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna())
b15 = b15[(b15.index.time >= pd.Timestamp("09:15").time()) &
          (b15.index.time <= pd.Timestamp("15:15").time())]
b15["d"] = b15.index.normalize()
dly = p1.resample("1D").agg(h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna()
dly["dma_bull"] = (dly.c.rolling(10).mean() > dly.c.rolling(20).mean()).shift(1)
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
wk = p1.resample("W-FRI").agg(c=("close", "last")).dropna()
wk["wk_bull"] = (wk.c.ewm(span=9, adjust=False).mean()
                 > wk.c.ewm(span=21, adjust=False).mean()).shift(1)
b15["ema9"] = b15.c.ewm(span=9, adjust=False).mean()
b15["ema21"] = b15.c.ewm(span=21, adjust=False).mean()
b15["e_bull"] = b15.ema9 > b15.ema21
b15 = b15.join(dly[["dma_bull", "atr14"]], on="d")
b15["wk_bull"] = pd.Series(wk.wk_bull.values, index=wk.index).reindex(
    b15.index, method="ffill").values

FILTERS = {
    "none": np.ones(len(b15), bool),
    "15m_ema": b15.e_bull.to_numpy(bool),
    "d_dma": b15.dma_bull.fillna(False).to_numpy(bool),
    "wk_ema": pd.Series(b15.wk_bull).fillna(False).to_numpy(bool),
    "d+wk": (b15.dma_bull.fillna(False).to_numpy(bool) &
             pd.Series(b15.wk_bull).fillna(False).to_numpy(bool)),
    "all3": (b15.e_bull.to_numpy(bool) & b15.dma_bull.fillna(False).to_numpy(bool) &
             pd.Series(b15.wk_bull).fillna(False).to_numpy(bool)),
}
o, h, l, c = (b15[x].to_numpy(float) for x in ("o", "h", "l", "c"))
p_h = np.r_[np.nan, h[:-1]]
p_l = np.r_[np.nan, l[:-1]]
atr = b15.atr14.to_numpy(float)
ds = b15.d.dt.strftime("%Y-%m-%d").to_numpy()
days = b15.d.to_numpy()
hhmm = np.array([t.hour * 100 + t.minute for t in b15.index])


def one_trade(i, side, exit_kind):
    if i + 3 >= len(b15) or ds[i] in SCH:
        return None
    entry = c[i]
    a = atr[i]
    if not np.isfinite(a) or a <= 0:
        return None
    raw = (entry - min(l[i], p_l[i])) if side > 0 else (max(h[i], p_h[i]) - entry)
    stop = max(raw, 0.4 * a)
    if not np.isfinite(stop) or stop <= 0 or stop > 3 * a:
        return None
    fut = b15.iloc[i + 1:i + 1 + MAX_BARS]
    if len(fut) < 4:
        return None
    bars = fut.rename(columns={"h": "high", "l": "low", "c": "close"})[
        ["high", "low", "close"]].astype(float)
    if exit_kind.startswith("RR"):
        rr = float(exit_kind[2:])
        pp = simulate_exit(bars, entry, side, stop=stop, target=rr * stop).pnl_pessimistic
    elif exit_kind == "PARTIAL_1R_trail":
        pp = (0.5 * simulate_exit(bars, entry, side, stop=stop, target=stop).pnl_pessimistic +
              0.5 * simulate_exit(bars, entry, side, stop=stop, trail=stop).pnl_pessimistic)
    else:
        pp = simulate_exit(bars, entry, side, stop=stop, trail=stop).pnl_pessimistic
    ct = (4.47 if pd.Timestamp(days[i]) < BREAK else 5.97) + SLIP
    return pp - ct


# only cells worth the compute: enough trades, in the retail band, positive, and t above 2
cand = R[(R.n >= 80) & (R.mean > 0) & (R.per_month >= 5) & (R.per_month <= 150) & (R.t >= 2.0)]
print(f"[cand] {len(cand)} cells qualify for the placebo "
      f"(n>=80, mean>0, 5-150/mo, t>=2.0)", flush=True)
if cand.empty:
    print("NO CELL QUALIFIES. Nothing to placebo-test — that is itself the verdict.", flush=True)
    json.dump([], open(OUT / "placebo.json", "w"))
    sys.exit(0)

store = pickle.load(open(OUT / "trades.pkl", "rb"))
out = []
print(f"\n{'cell':<48}{'n':>6}{'real':>9}{'plc mean':>10}{'plc p95':>9}{'p':>7}{'verdict':>13}",
      flush=True)
for _, row in cand.iterrows():
    key = row["cell"]
    fname, flt, ex = key.split("|")
    side = +1 if any(k in fname for k in ("BULL", "HAMMER", "PIERCING", "SOLDIERS",
                                          "MORNING", "BOTTOM", "UP")) else -1
    tr = store.get(key)
    if tr is None or len(tr) == 0:
        continue
    fmask = FILTERS[flt]
    pool_mask = fmask if (side > 0 or flt == "none") else ~fmask
    # match the time-of-day histogram
    want = pd.Series([t.hour * 100 + t.minute for t in pd.to_datetime(tr.t)]).value_counts()
    pools = {hm: np.where(pool_mask & (hhmm == hm))[0] for hm in want.index}
    draws = []
    for _d in range(N_DRAW):
        pnls = []
        for hm, k in want.items():
            pool = pools[hm]
            if len(pool) == 0:
                continue
            pick = RNG.choice(pool, size=min(k, len(pool)), replace=len(pool) < k)
            for i in pick:
                v = one_trade(int(i), side, ex)
                if v is not None:
                    pnls.append(v)
        if pnls:
            draws.append(float(np.mean(pnls)))
    if len(draws) < 20:
        continue
    draws = np.array(draws)
    real = float(row["mean"])
    pv = float((draws >= real).mean())
    v = "FORMATION REAL" if pv < 0.05 else ("weak" if pv < 0.20 else "FILTER ONLY")
    out.append(dict(cell=key, n=int(row["n"]), per_month=float(row["per_month"]),
                    real_mean=real, placebo_mean=round(float(draws.mean()), 3),
                    placebo_p95=round(float(np.quantile(draws, .95)), 3),
                    p_value=pv, verdict=v, win=float(row["win"]),
                    avg_RR=row.get("avg_RR"), t=float(row["t"])))
    print(f"{key:<48}{int(row['n']):>6}{real:>9.2f}{draws.mean():>10.2f}"
          f"{np.quantile(draws, .95):>9.2f}{pv:>7.3f}{v:>13}", flush=True)

pd.DataFrame(out).to_csv(OUT / "placebo.csv", index=False)
json.dump(out, open(OUT / "placebo.json", "w"), indent=2, default=str)
print(f"\nwrote placebo.csv/.json  ({len(out)} tested, "
      f"{sum(1 for x in out if x['verdict'] == 'FORMATION REAL')} with a real formation effect)",
      flush=True)
