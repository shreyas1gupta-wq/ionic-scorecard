"""B1b-CARD: FII-minus-Client net-flow spread quintiles vs NIFTY forward returns (T+1).
Spec frozen @ 4d9c6f1. Construction locked to B1. Bars: >=10 bps/day AND t>=2.5 at best k.
FAIL -> participant-flow stream closes entirely.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1b_FII_CLIENT_SPREAD_20260711"
OUT.mkdir(parents=True, exist_ok=True)

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
tdays = sorted(close.index)
pos = {d: i for i, d in enumerate(tdays)}

flow = flow[flow.index.isin(pos)]
fs = flow.sort_index()
rank = fs.rolling(252, min_periods=250).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True).dropna()
quint = np.minimum((rank * 5).astype(int), 4)

rows = []
for d, q in quint.items():
    i = pos.get(d)
    if i is None or i + 6 >= len(tdays):
        continue
    e = close[tdays[i + 1]]
    rows.append(dict(day=d, q=int(q),
                     r1=(close[tdays[i + 2]] / e - 1) * 1e4,
                     r3=(close[tdays[i + 4]] / e - 1) * 1e4,
                     r5=(close[tdays[i + 6]] / e - 1) * 1e4))
df = pd.DataFrame(rows)
df.to_csv(OUT / "b1b_panel.csv", index=False)

out_lines = [f"n={len(df)} signal days {df.day.min()}..{df.day.max()}"]
best = None
for k, col in [(1, "r1"), (3, "r3"), (5, "r5")]:
    g = df.groupby("q")[col].mean()
    top, bot = df[df.q == 4][col], df[df.q == 0][col]
    spread_day = (top.mean() - bot.mean()) / k
    tt = (top.mean() - bot.mean()) / np.sqrt(top.var(ddof=1)/len(top) + bot.var(ddof=1)/len(bot))
    out_lines.append(f"k={k}: " + " ".join(f"q{q}={g.get(q, np.nan):+.1f}" for q in range(5)) +
                     f" | top-bot={top.mean()-bot.mean():+.1f} bps ({spread_day:+.1f}/day), t={tt:.2f}")
    if best is None or abs(spread_day) > abs(best[1]):
        best = (k, spread_day, tt)
era = pd.to_datetime(df.day.astype(str))
for lab, m in [("2019-21", era < "2022-01-01"), ("2022-26", era >= "2022-01-01")]:
    s = df[m]
    if len(s):
        t1, b1 = s[s.q == 4]["r1"], s[s.q == 0]["r1"]
        out_lines.append(f"era {lab}: k=1 top-bot={t1.mean()-b1.mean():+.1f} bps (n={len(s)})")

k, spread_day, tt = best
passed = abs(spread_day) >= 10 and abs(tt) >= 2.5
verdict = "PASS bar -> Gate-4 spec next" if passed else "KILL -> participant-flow stream CLOSED (both constructions exhausted)"
out_lines.append(f"BEST k={k}: {spread_day:+.1f} bps/day, t={tt:.2f} -> VERDICT: {verdict}")
txt = "\n".join(out_lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "B1b-CARD", "frozen_commit": "4d9c6f1", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "b1b_spread.py", "data": ["participant_oi_normalized", "kaggle NIFTY minute"],
        "n_obs": int(len(df)), "metrics": {"best_k": k, "spread_bps_day": round(float(spread_day), 2), "t": round(float(tt), 2)},
        "validation": {"era_split": " || ".join(out_lines[-3:-1]), "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight; construction locked to B1 (rolling-252, T+1)", "one_day_lag": "T+1 by construction"},
        "verdict": verdict, "bars_hit": ["spread>=10bps/day", "t>=2.5"] if passed else [],
        "trials_increment": 3, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written")
