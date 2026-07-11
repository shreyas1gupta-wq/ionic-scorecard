"""B1c-CARD (frozen @ 83259ac): DII futnet 5d-flow, k=3, B1b construction. Certify-or-kill.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(97)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1c_DII_FLOW_20260712"
OUT.mkdir(parents=True, exist_ok=True)
COST = 4.0  # bps RT
K = 3

poi = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet")
dii = poi[poi["Client Type"] == "DII"].set_index("date").sort_index()
dii.index = pd.to_datetime(dii.index).date
net = (dii["Future Index Long"] - dii["Future Index Short"]).sort_index()
flow = net.diff(5).dropna()

sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[(sp.index.time >= dt.time(9, 15)) & (sp.index.time <= dt.time(15, 25))]
close = sp["close"].groupby(pd.Series(sp.index.date, index=sp.index)).last()
tdays = sorted(close.index)
pos = {dd: i for i, dd in enumerate(tdays)}
flow = flow[[d in pos for d in flow.index]]
rank = flow.rolling(252, min_periods=250).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True).dropna()

def run(rank_series, lag=1):
    """enter close(D+lag) when rank>=0.8, exit close(D+lag+K). Returns per-trade bps list + dates."""
    rets, dts = [], []
    for dd, rk in rank_series.items():
        if rk < 0.8:
            continue
        i = pos.get(dd)
        if i is None or i + lag + K >= len(tdays):
            continue
        e = close[tdays[i + lag]]
        rets.append((close[tdays[i + lag + K]] / e - 1) * 1e4 - COST)
        dts.append(dd)
    return np.array(rets), dts

real, dts = run(rank)
n = len(real)
t = real.mean() / (real.std(ddof=1) / np.sqrt(n))
print(f"real: n={n}, {real.mean():+.1f} bps/trade, t={t:.2f}", flush=True)

# battery
null1 = []
rv = rank.values.copy()
for k in range(200):
    shuf = pd.Series(rng.permutation(rv), index=rank.index)
    rr, _ = run(shuf)
    if len(rr):
        null1.append(rr.mean())
null1 = np.array(null1)
lag_real, _ = run(rank, lag=2)
sig_days = set(dts)
all_r = pd.Series(1.0, index=rank.index)
null3 = []
for k in range(200):
    pick = rng.choice(len(rank), size=n, replace=False)
    fake = pd.Series(0.0, index=rank.index)
    fake.iloc[pick] = 1.0
    rr, _ = run(fake.where(fake > 0, 0.0).replace(0, np.nan).dropna() * 0.9)  # rank 0.9 -> triggers
    if len(rr):
        null3.append(rr.mean() / (rr.std(ddof=1) / np.sqrt(len(rr))))
null3 = np.array(null3)
real_sh = t

bars = {"expectancy>=8bps": real.mean() >= 8.0, "t>=2.5": t >= 2.5,
        "beats_shuffle95": real.mean() > np.percentile(null1, 95),
        "lag_decay": lag_real.mean() < real.mean(),
        "beats_randomdays95_t": real_sh > np.percentile(null3, 95)}
verdict = "CERTIFIED - SLEEVE #5" if all(bars.values()) else "KILL"
era = pd.to_datetime(pd.Series([str(d) for d in dts]))
e1 = real[(era < "2023-01-01").values]; e2 = real[(era >= "2023-01-01").values]
lines = [f"B1c DII 5d-flow k=3: n={n}, {real.mean():+.1f} bps/trade, t={t:.2f}",
         f"shuffle null95 {np.percentile(null1,95):+.1f} | lag+1 {lag_real.mean():+.1f} (decay {'yes' if lag_real.mean()<real.mean() else 'NO'}) | random-days t null95 {np.percentile(null3,95):.2f}",
         f"eras: 2019-22 {e1.mean():+.1f} (n={len(e1)}) | 2023-26 {e2.mean():+.1f} (n={len(e2)})",
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
card = {"card": "B1c-CARD", "frozen_commit": "83259ac", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "b1c_dii.py", "n_obs": int(n),
        "metrics": {"bps_per_trade": round(float(real.mean()), 1), "t": round(float(t), 2)},
        "verdict": verdict, "bars_hit": [k for k, v in bars.items() if v], "trials_increment": 1,
        "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
