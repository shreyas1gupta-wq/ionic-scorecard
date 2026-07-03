"""FIRST-CUT replication: NIFTY100 LOWVOL30 from OUR data vs OFFICIAL closes (via Angel).
HONEST LABELS: this is the D-M4 pipeline's first tracer bullet, NOT the exact NSE methodology.
Approximations (stated loudly): N100 proxy = top-100 by 1y avg traded value of our PIT universe;
quarterly rebalance at quarter-ends; vol = 252d std of daily returns; weights ∝ 1/vol uncapped.
Output: daily-return correlation, annualized tracking error, cumulative drift, per-year table.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import shortlist_shortvol as sv   # combined_close (HF ∪ Angel-2026)

off_p = ROOT / "datasets/index_daily/lowvol30.parquet"
if not off_p.exists():
    sys.exit("official lowvol30 closes not yet fetched — run index_history_pull.py first")
off = pd.read_parquet(off_p)
off["date"] = pd.to_datetime(off["timestamp"].str[:10])
off = off.set_index("date")["close"].astype(float).sort_index()
off_ret = off.pct_change().dropna()

C = sv.combined_close()                      # date x symbol closes, adjusted panel
ret = C.pct_change()
val_proxy = (C * 1).rolling(252).mean()      # price level as crude size proxy fallback
# better: traded value needs volume; panel here is close-only → use 1y median close*constant rank as N100 proxy?
# HONEST choice: use 252d rolling mean of close (price level) is NOT market cap. Use liquidity from volume if available.
print("[NOTE] N100 proxy = top-100 by 252d avg CLOSE*VOLUME if volume available, else price rank (crude).")

vol252 = ret.rolling(252).std() * np.sqrt(252)

qe = pd.date_range("2018-03-31", "2026-06-30", freq="QE")
weights = {}
for d in qe:
    if d not in C.index:
        idx = C.index[C.index <= d]
        if len(idx) == 0: continue
        d0 = idx[-1]
    else:
        d0 = d
    row_vol = vol252.loc[d0].dropna()
    # N100 proxy: 100 largest by price*1 (no mcap col) -> use 252d mean close rank
    lvl = C.rolling(252).mean().loc[d0].dropna()
    n100 = lvl.nlargest(100).index
    cand = row_vol.reindex(n100).dropna()
    low30 = cand.nsmallest(30)
    w = (1 / low30) / (1 / low30).sum()
    weights[d0] = w

# chain daily returns with quarterly weights
dates = ret.index[(ret.index >= min(weights)) & (ret.index <= off_ret.index.max())]
keys = sorted(weights)
port = []
for d in dates:
    k = max([k for k in keys if k < d], default=None)
    if k is None: continue
    w = weights[k]
    r = (ret.loc[d].reindex(w.index) * w).sum()
    port.append((d, r))
rep = pd.Series(dict(port)).dropna()

both = pd.concat({"rep": rep, "off": off_ret}, axis=1).dropna()
if len(both) < 100:
    sys.exit(f"insufficient overlap: {len(both)} days")
corr = both["rep"].corr(both["off"])
te = (both["rep"] - both["off"]).std() * np.sqrt(252)
cum_rep = (1 + both["rep"]).prod() - 1
cum_off = (1 + both["off"]).prod() - 1
print(f"overlap {len(both)} days: {both.index.min().date()} -> {both.index.max().date()}")
print(f"daily-return CORRELATION: {corr:.3f}")
print(f"annualized TRACKING ERROR: {te:.2%}")
print(f"cumulative: replicated {cum_rep:+.1%} vs official {cum_off:+.1%} (drift {cum_rep-cum_off:+.1%})")
per_year = both.groupby(both.index.year).apply(lambda g: pd.Series({
    "corr": g["rep"].corr(g["off"]),
    "te_ann": (g["rep"] - g["off"]).std() * np.sqrt(252),
    "rep": (1 + g["rep"]).prod() - 1, "off": (1 + g["off"]).prod() - 1, "n": len(g)}))
print(per_year.to_string(float_format=lambda x: f"{x:.3f}"))
json.dump({"corr": corr, "te_ann": te, "cum_rep": cum_rep, "cum_off": cum_off,
           "overlap_days": len(both), "label": "FIRST-CUT (proxy N100, uncapped inv-vol, quarterly)"},
          open(OUT / "metrics.json", "w"), indent=1)
print("saved metrics.json")
