"""T-B-CARD: mean reversion in stage-2 uptrend (stocks, daily). Frozen @ e4de961 BEFORE run.
RSI(3)<15 primary / zscore(5)<-1.5 secondary, PIT NIFTY500, entry next close, exit close>5DMA or 10td.
Placebo shares the exit engine (T-E lesson). Bars: beat placebo95 + t>=2.5 + n>=300 + eras both>0.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(11)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TB_MEANREV_UPTREND_20260711"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0050

px = pd.read_parquet(ROOT / "datasets/nse_bhavcopy_daily/close_all.parquet")
px["date"] = pd.to_datetime(px["date"])
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
snaps = {d: set(g["Ticker"].dropna().astype(str).str.strip()) for d, g in uni.groupby("snap")}
snap_dates = sorted(snaps)
ever = set().union(*snaps.values())
px = px[px.symbol.isin(ever)].sort_values(["symbol", "date"])
print(f"panel filtered to ever-N500: {len(px):,} rows, {px.symbol.nunique()} syms", flush=True)

def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def in_universe(sym, d):
    prior = [s for s in snap_dates if s <= d]
    return bool(prior) and sym in snaps[prior[-1]]

trades = {"rsi3": [], "z5": []}
stage2_days = []  # (sym, date) population passing the gate — placebo pool
for sym, g in px.groupby("symbol"):
    c = g.set_index("date")["close"]
    if len(c) < 260:
        continue
    d200 = c.rolling(200).mean(); d50 = c.rolling(50).mean(); d5 = c.rolling(5).mean()
    r3 = rsi(c, 3)
    z5 = (c - d5) / c.rolling(5).std()
    stage2 = (c > d200) & (d50 > d200)
    dates = c.index
    sig_r = stage2 & (r3 < 15)
    sig_z = stage2 & (z5 < -1.5)
    idx = {d: i for i, d in enumerate(dates)}

    def exit_ret(i_entry):
        entry = c.iloc[i_entry]
        for j in range(i_entry + 1, min(i_entry + 1 + 10, len(c))):
            if c.iloc[j] > d5.iloc[j]:
                return (c.iloc[j] / entry - 1) - COST, j - i_entry
        j = min(i_entry + 10, len(c) - 1)
        return (c.iloc[j] / entry - 1) - COST, j - i_entry

    for name, sig in [("rsi3", sig_r), ("z5", sig_z)]:
        s_dates = dates[sig.values]
        last_exit = -1
        for d in s_dates:
            if d.date() < dt.date(2015, 1, 1) or not in_universe(sym, d.date()):
                continue
            i = idx[d]
            if i + 1 >= len(c) or i <= last_exit:
                continue
            ret, held = exit_ret(i + 1)
            trades[name].append(dict(sym=sym, day=d.date(), ret=ret, held=held))
            last_exit = i + held
    # placebo pool: stage-2 days 2015+
    ok = dates[(stage2 & (dates >= pd.Timestamp("2015-01-01"))).values]
    stage2_days.extend((sym, d) for d in ok[:: max(1, len(ok) // 60)])  # thinned pool

series = {s: g.set_index("date")["close"] for s, g in px.groupby("symbol")}
d5map = {s: c.rolling(5).mean() for s, c in series.items()}

def placebo_once(n):
    picks = rng.integers(0, len(stage2_days), size=n)
    rets = []
    for k in picks:
        sym, d = stage2_days[k]
        c = series[sym]; d5 = d5map[sym]
        i = c.index.get_loc(d)
        if i + 1 >= len(c):
            continue
        entry = c.iloc[i + 1]
        r = None
        for j in range(i + 2, min(i + 12, len(c))):
            if c.iloc[j] > d5.iloc[j]:
                r = (c.iloc[j] / entry - 1) - COST; break
        if r is None:
            j = min(i + 11, len(c) - 1)
            r = (c.iloc[j] / entry - 1) - COST
        rets.append(r)
    return np.mean(rets) if rets else np.nan

def stat(x):
    x = np.asarray(x, float)
    return len(x), x.mean() * 100, x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

results = {}
lines = []
for name in ("rsi3", "z5"):
    tdf = pd.DataFrame(trades[name])
    tdf.to_csv(OUT / f"tb_{name}_trades.csv", index=False)
    n, m, t = stat(tdf.ret)
    e1 = tdf[pd.to_datetime(tdf.day.astype(str)) < "2021-01-01"]
    e2 = tdf[pd.to_datetime(tdf.day.astype(str)) >= "2021-01-01"]
    _, m1, t1 = stat(e1.ret); _, m2, t2 = stat(e2.ret)
    null = np.array([placebo_once(min(n, 400)) for _ in range(200)])
    p95 = np.nanpercentile(null, 95)
    bars = {"beat_placebo95": (m / 100) > p95, "t>=2.5": t >= 2.5, "n>=300": n >= 300,
            "eras_both_pos": (m1 > 0) and (m2 > 0)}
    kill = (t < 1.5) or ((m1 > 0) != (m2 > 0))
    verdict = "PASS" if all(bars.values()) else ("KILL" if kill else "PARK")
    results[name] = dict(n=n, mean=m, t=t, e1=m1, e2=m2, p95=p95 * 100, verdict=verdict, bars=bars)
    lines += [f"{name}: n={n}, net {m:+.2f}%/trade (t={t:.2f}), eras {m1:+.2f}/{m2:+.2f}, "
              f"placebo95 {p95*100:+.2f}, null_mean {np.nanmean(null)*100:+.2f} -> {verdict} "
              f"[{', '.join(k for k, v in bars.items() if not v) or 'all bars met'}]"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

prim = results["rsi3"]
card = {"card": "T-B-CARD", "frozen_commit": "e4de961", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "tb_meanrev.py", "data": ["close_all", "PIT NIFTY500 snapshots"],
        "n_obs": prim["n"], "metrics": {"net_pct": round(prim["mean"], 2), "t": round(prim["t"], 2),
        "placebo95_pct": round(prim["p95"], 2)},
        "validation": {"era_split": f"{prim['e1']:+.2f}/{prim['e2']:+.2f}", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight", "one_day_lag": "entry next close after signal"},
        "verdict": f"rsi3={prim['verdict']}, z5={results['z5']['verdict']}",
        "bars_hit": [k for k, v in prim["bars"].items() if v], "trials_increment": 2, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written", flush=True)
