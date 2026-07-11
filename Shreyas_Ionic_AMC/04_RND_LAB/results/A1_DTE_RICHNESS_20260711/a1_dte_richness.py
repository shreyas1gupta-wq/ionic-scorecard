"""A1-CARD: DTE richness — which trading-DTE bucket pays ATM-straddle sellers best per day.
Card frozen in INDEX_PROGRAM_2026/MASTER_PLAN.md BEFORE this run (2026-07-11).
One obs per (expiry, k): entry k trading days before expiry E at 09:20, ATM straddle expiry E,
hold to expiry, payoff = intrinsic from spot settle. Net = gross - 4 pts entry cost.
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/A1_DTE_RICHNESS_20260711"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()
exps = sorted(exps)

spot_dates = pd.Series(spot.index.date, index=spot.index)
all_days = sorted(set(spot_dates.values))
day_pos = {d: i for i, d in enumerate(all_days)}

def spot_at_open(day):
    d = spot[(spot_dates == day) & (spot.index.time >= dt.time(9, 20))]
    return d["close"].iloc[0] if len(d) else None

def spot_settle(day):
    d = spot[(spot_dates == day) & (spot.index.time <= dt.time(15, 25))]
    return d["close"].iloc[-1] if len(d) else None

rows, skip = [], 0
for ei, exp in enumerate(exps):
    if exp not in day_pos:
        continue
    settle = spot_settle(exp)
    if settle is None:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception as e:
        print(f"[skip] {exp}: {e}"); continue
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    ep = day_pos[exp]
    for k in range(0, 7):
        if ep - k < 0:
            continue
        d0 = all_days[ep - k]
        sp = spot_at_open(d0)
        if sp is None:
            skip += 1; continue
        K = round(sp / 50) * 50
        prem = 0.0, 0.0
        legs = []
        ok = True
        for cp in ("CE", "PE"):
            s = df[(df.strike == float(K)) & (df.option_type == cp)]
            s = s[(s.ts.dt.date == d0) & (s.ts.dt.time >= dt.time(9, 20)) &
                  (s.ts.dt.time <= dt.time(9, 45))].sort_values("ts")
            if not len(s):
                ok = False; break
            legs.append(s["close"].iloc[0])
        if not ok:
            skip += 1; continue
        entry_prem = sum(legs)
        intrinsic = abs(settle - K)
        gross = entry_prem - intrinsic
        net = gross - 4.0
        rows.append(dict(expiry=exp, k=k, day=d0, strike=K, entry_prem=entry_prem,
                         intrinsic=intrinsic, gross=gross, net=net,
                         per_day_net=net / max(k, 1), per_day_gross=gross / max(k, 1)))
    if ei % 25 == 0:
        print(f"...{ei}/{len(exps)}, rows={len(rows)}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "a1_obs.csv", index=False)
print(f"\nobs: {len(r)} | skips: {skip}")

def stat(x):
    x = np.asarray(x, float)
    if len(x) < 3 or x.std(ddof=1) == 0:
        return len(x), np.nan, np.nan, np.nan, np.nan
    return (len(x), x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))),
            np.median(x), (x > 0).mean() * 100)

with open(OUT / "RESULTS_RAW.txt", "w", encoding="utf-8") as f:
    def emit(s):
        print(s); f.write(s + "\n")
    emit(f"{'k':>3}{'n':>6}{'prem':>8} | {'gross':>8}{'t':>7} | {'net':>8}{'t':>7} | "
         f"{'net/day':>9}{'t':>7}{'med/day':>9}{'win%':>6}{'worst5':>9}")
    for k in range(0, 7):
        s = r[r.k == k]
        if not len(s):
            continue
        n, mg, tg, _, _ = stat(s.gross)
        _, mn, tn, _, _ = stat(s.net)
        _, mpd, tpd, mdpd, w = stat(s.per_day_net)
        worst5 = s.net.nsmallest(5).mean()
        emit(f"{k:>3}{n:>6}{s.entry_prem.mean():>8.1f} | {mg:>8.2f}{tg:>7.2f} | "
             f"{mn:>8.2f}{tn:>7.2f} | {mpd:>9.2f}{tpd:>7.2f}{mdpd:>9.2f}{w:>5.0f}%{worst5:>9.1f}")
    emit("\n---- era split (net/day mean, t) ----")
    r["era"] = np.where(pd.to_datetime(r.day.astype(str)) < "2024-01-01", "2021-23", "2024-26")
    for k in range(0, 7):
        line = f"k={k}: "
        for era, g in r[r.k == k].groupby("era"):
            n, m, t, _, _ = stat(g.per_day_net)
            line += f"{era} {m:+6.2f} (t={t:4.1f}, n={n})   "
        emit(line)

print("\nsaved:", OUT / "a1_obs.csv", "and RESULTS_RAW.txt")
