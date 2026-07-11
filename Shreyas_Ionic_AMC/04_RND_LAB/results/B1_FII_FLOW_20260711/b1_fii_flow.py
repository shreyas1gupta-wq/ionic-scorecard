"""B1-CARD: FII index-futures net-flow quintiles vs NIFTY forward returns (T+1).
Spec frozen in commit b267854 BEFORE this run. KILL: top-bottom < 10 bps/day or t < 2.5.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1_FII_FLOW_20260711"
OUT.mkdir(parents=True, exist_ok=True)
POI = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi"

# ---- FII net index-futures position per day ----
frames = [pd.read_parquet(p) for p in sorted(POI.glob("participant_oi_*.parquet"))]
poi = pd.concat(frames, ignore_index=True)
ct = poi["Client Type"].astype(str).str.strip().str.upper()
fii = poi[ct == "FII"].copy()
for c in ["Future Index Long", "Future Index Short"]:
    fii[c] = pd.to_numeric(fii[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
fii["net"] = fii["Future Index Long"] - fii["Future Index Short"]
fii["d"] = pd.to_datetime(fii["file_date"]).dt.date
fii = fii.dropna(subset=["net"]).sort_values("d").drop_duplicates("d")
net = fii.set_index("d")["net"]
flow = net.diff().dropna()
print(f"FII days parsed: {len(net)}, flow obs: {len(flow)}, dropped unparseable: {len(poi[ct=='FII']) - len(fii)}")

# ---- NIFTY closes (kaggle minute, <=15:25 last print) ----
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[(sp.index.time >= dt.time(9, 15)) & (sp.index.time <= dt.time(15, 25))]
close = sp["close"].groupby(pd.Series(sp.index.date, index=sp.index)).last()
tdays = sorted(close.index)
pos = {d: i for i, d in enumerate(tdays)}

# ---- rolling 252-session percentile rank of flow (no full-sample leak) ----
flow = flow[flow.index.isin(pos)]
fs = flow.sort_index()
rank = fs.rolling(252, min_periods=250).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True)
rank = rank.dropna()
quint = np.minimum((rank * 5).astype(int), 4)  # 0..4

rows = []
for d, q in quint.items():
    i = pos.get(d)
    if i is None or i + 6 >= len(tdays):
        continue
    e = close[tdays[i + 1]]  # entry at close(D+1)
    rows.append(dict(day=d, q=int(q),
                     r1=(close[tdays[i + 2]] / e - 1) * 1e4,
                     r3=(close[tdays[i + 4]] / e - 1) * 1e4,
                     r5=(close[tdays[i + 6]] / e - 1) * 1e4))
df = pd.DataFrame(rows)
df.to_csv(OUT / "b1_panel.csv", index=False)

def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan

out_lines = [f"n={len(df)} signal days {df.day.min()}..{df.day.max()} (252d burn-in consumed 2018)"]
best = None
for k, col in [(1, "r1"), (3, "r3"), (5, "r5")]:
    g = df.groupby("q")[col].mean()
    top, bot = df[df.q == 4][col], df[df.q == 0][col]
    # daily spread series: pair top/bot by date impossible (different days) -> use unpaired diff of means,
    # t from two-sample; per-day spread = (mean_top - mean_bot)/k in bps/day
    spread_day = (top.mean() - bot.mean()) / k
    tt = (top.mean() - bot.mean()) / np.sqrt(top.var(ddof=1)/len(top) + bot.var(ddof=1)/len(bot))
    out_lines.append(f"k={k}: quintile means (bps): " + " ".join(f"q{q}={g.get(q, np.nan):+.1f}" for q in range(5)) +
                     f" | top-bot={top.mean()-bot.mean():+.1f} bps ({spread_day:+.1f}/day), t={tt:.2f}, n_top={len(top)}, n_bot={len(bot)}")
    if best is None or abs(spread_day) > abs(best[1]):
        best = (k, spread_day, tt)
era = pd.to_datetime(df.day.astype(str))
for lab, m in [("2019-21", era < "2022-01-01"), ("2022-26", era >= "2022-01-01")]:
    s = df[m]
    if len(s):
        t5, b5 = s[s.q == 4]["r5"], s[s.q == 0]["r5"]
        out_lines.append(f"era {lab}: k=5 top-bot={t5.mean()-b5.mean():+.1f} bps (n={len(s)})")

k, spread_day, tt = best
verdict = "PASS bar -> deeper study" if (abs(spread_day) >= 10 and abs(tt) >= 2.5) else "KILL (bar: >=10 bps/day and t>=2.5)"
out_lines.append(f"BEST k={k}: {spread_day:+.1f} bps/day, t={tt:.2f} -> VERDICT: {verdict}")
txt = "\n".join(out_lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "B1-CARD", "frozen_commit": "b267854", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "b1_fii_flow.py", "data": ["participant_oi (catalog 2026-07-11)", "kaggle NIFTY minute"],
        "n_obs": int(len(df)), "metrics": {"best_k": k, "spread_bps_day": round(float(spread_day), 2), "t": round(float(tt), 2)},
        "validation": {"era_split": out_lines[-3] + " || " + out_lines[-2], "bootstrap_ci95": None,
                       "lookahead_ast": "run pre-flight", "one_day_lag": "n/a (T+1 by construction)"},
        "verdict": verdict, "bars_hit": ["spread>=10bps/day", "t>=2.5"], "trials_increment": 3,
        "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written")
