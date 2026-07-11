"""B1b red-team placebo battery + sensitivity (stage mandated by frozen Gate-4 spec @ aebdaca).
Battery composition (pinned before run, standard construction):
 P1 signal-shuffle x200: permute q labels across days -> null distribution of net bps/trade.
 P2 extra-lag: enter T+2 instead of T+1 (real information should decay, placebo shouldn't).
 P3 frequency-matched random days x200: random 21% of days -> null Sharpe distribution.
 S  sensitivity 3x3x2 (rank window x quintile edge x cost) - DIAGNOSTIC, reported not selected.
Kill rule (pinned): if real result is within the top 5% of either null -> survives that placebo;
if real sits below the 95th pct of nulls on BOTH P1 and P3 -> red-team KILL.
"""
import json
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1b_GATE4_20260711"
COST = 4.0

panel = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1b_FII_CLIENT_SPREAD_20260711/b1b_panel.csv",
                    parse_dates=["day"]).sort_values("day").reset_index(drop=True)
real_bps = panel[panel.q == 4].r1.mean() - COST
n4 = int((panel.q == 4).sum())

# P1: shuffle q labels
null1 = []
qvals = panel.q.values.copy()
for _ in range(200):
    qs = rng.permutation(qvals)
    null1.append(panel.r1[qs == 4].mean() - COST)
null1 = np.array(null1)
p1_pct = (real_bps > null1).mean() * 100

# P2: extra lag — rebuild with r at +1 more day: approximate by shifting r1 by one row (panel is daily-ordered)
lag = panel.r1.shift(-1)
p2_bps = lag[panel.q == 4].mean() - COST

# P3: frequency-matched random days -> Sharpe null
def sharpe_of(mask):
    d = np.where(mask, panel.r1 - COST, 0.0) / 1e4
    return d.mean() / d.std(ddof=1) * np.sqrt(252)
real_sharpe = sharpe_of(panel.q.values == 4)
null3 = []
for _ in range(200):
    pick = rng.choice(len(panel), size=n4, replace=False)
    m = np.zeros(len(panel), bool); m[pick] = True
    null3.append(sharpe_of(m))
null3 = np.array(null3)
p3_pct = (real_sharpe > null3).mean() * 100

# S: sensitivity — recompute signal from normalized panel under variants
poi = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet")
poi["net"] = poi["Future Index Long"] - poi["Future Index Short"]
piv = poi.pivot_table(index="date", columns="Client Type", values="net")
spread = (piv["FII"] - piv["Client"]).dropna()
spread.index = spread.index.date
flow = spread.sort_index().diff().dropna()
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[(sp.index.time >= dt.time(9, 15)) & (sp.index.time <= dt.time(15, 25))]
close = sp["close"].groupby(pd.Series(sp.index.date, index=sp.index)).last()
tdays = sorted(close.index); pos = {d: i for i, d in enumerate(tdays)}
flow = flow[flow.index.isin(pos)].sort_index()

sens = []
for win in (200, 252, 300):
    rank = flow.rolling(win, min_periods=win - 2).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True).dropna()
    for edge in (0.85, 0.80, 0.75):
        sig_days = rank[rank >= edge].index
        rets = []
        for d in sig_days:
            i = pos.get(d)
            if i is None or i + 2 >= len(tdays):
                continue
            rets.append((close[tdays[i + 2]] / close[tdays[i + 1]] - 1) * 1e4)
        for cost in (4.0, 8.0):
            if len(rets) > 30:
                sens.append((win, edge, cost, len(rets), np.mean(rets) - cost))
sdf = pd.DataFrame(sens, columns=["win", "edge", "cost", "n", "net_bps"])
pos_cells = (sdf.net_bps > 0).sum()

survives = (p1_pct >= 95) or (p3_pct >= 95)
kill = (p1_pct < 95) and (p3_pct < 95)
verdict = "RED-TEAM SURVIVED" if survives and not kill else "RED-TEAM KILL"

lines = [f"real: +{real_bps:.1f} bps/trade net, Sharpe {real_sharpe:.2f}, n={n4}",
         f"P1 shuffle x200: null mean {null1.mean():+.1f}, 95th pct {np.percentile(null1,95):+.1f} -> real at {p1_pct:.0f}th pct",
         f"P2 extra-lag: {p2_bps:+.1f} bps (real {real_bps:+.1f}; decay expected if information is timely)",
         f"P3 random-days x200: null Sharpe 95th pct {np.percentile(null3,95):.2f} -> real at {p3_pct:.0f}th pct",
         f"S sensitivity: {pos_cells}/{len(sdf)} cells net-positive; worst cell {sdf.net_bps.min():+.1f} bps "
         f"(win/edge/cost={sdf.loc[sdf.net_bps.idxmin(), ['win','edge','cost']].tolist()})",
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt)
sdf.to_csv(OUT / "sensitivity_cells.csv", index=False)
(OUT / "REDTEAM_RAW.txt").write_text(txt, encoding="utf-8")
