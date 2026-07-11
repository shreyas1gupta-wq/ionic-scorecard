"""T-E-CARD: PEAD multi-year event study 2015-2026. Frozen @ b12264b BEFORE run.
Buckets: B1 YoY NP growth>=100%, B2 loss->profit. PIT universe gate, close_all prices (delisted incl).
Entry D+1 close; exit close<DMA50 trail (DMA20 secondary) or 120td cap; costs 25bps/side.
Controls: event-matched universe drift + 200x random-event placebo.
Bars: PASS t>=2.5 & n>=300 & eras both>0 & real>placebo95. KILL t<1.5 or era conflict. Else PARK.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(7)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TE_PEAD_MULTIYEAR_20260711"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0050  # 25 bps/side round trip

# ---- prices: close_all panel -> per-symbol series dict ----
px = pd.read_parquet(ROOT / "datasets/nse_bhavcopy_daily/close_all.parquet")
px["date"] = pd.to_datetime(px["date"])
px = px.sort_values(["symbol", "date"])
tdays = np.array(sorted(px.date.unique()))
print(f"panel: {len(px):,} rows, {px.symbol.nunique()} syms, {tdays[0].date()}..{tdays[-1].date()}", flush=True)
series = {s: g.set_index("date")["close"] for s, g in px.groupby("symbol")}

# ---- PIT universe snapshots (long format: Month-Year, Ticker) ----
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
snaps = {d: set(g["Ticker"].dropna().astype(str).str.strip()) for d, g in uni.groupby("snap")}
snap_dates = sorted(snaps)
print(f"PIT snapshots: {len(snap_dates)} ({snap_dates[0]}..{snap_dates[-1]})", flush=True)

def in_universe(sym, d):
    prior = [s for s in snap_dates if s <= d]
    if not prior:
        return False
    return sym in snaps[prior[-1]]

# ---- PIT earnings events ----
ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
npc = next((c for c in ev.columns if c in ("np", "net_profit", "netprofit", "pat")), None)
symc = next(c for c in ev.columns if "symbol" in c or c == "ticker")
avc = next(c for c in ev.columns if "available" in c)
qc = next((c for c in ev.columns if "quarter" in c or "period" in c), None)
print("earnings cols used:", symc, avc, npc, qc, "| all:", list(ev.columns)[:14], flush=True)
ev[avc] = pd.to_datetime(ev[avc])
ev = ev.dropna(subset=[avc, npc]).sort_values([symc, qc or avc])
# YoY: same quarter previous year = shift(4) within symbol (quarterly rows)
ev["np_yoy_base"] = ev.groupby(symc)[npc].shift(4)
ev = ev[(ev[avc] >= "2015-01-01") & (ev[avc] <= "2026-04-30")].dropna(subset=["np_yoy_base"])
b1 = (ev["np_yoy_base"] > 0) & (ev[npc] >= 2 * ev["np_yoy_base"])
b2 = (ev["np_yoy_base"] < 0) & (ev[npc] > 0)
ev["bucket"] = np.where(b1, "B1", np.where(b2, "B2", ""))
ev = ev[ev.bucket != ""]
print(f"events pre-gate: {len(ev)} (B1 {sum(ev.bucket=='B1')}, B2 {sum(ev.bucket=='B2')})", flush=True)

def next_tday(d):
    i = np.searchsorted(tdays, np.datetime64(d), side="right")
    return tdays[i] if i < len(tdays) else None

def run_trade(sym, e_date, dma_n):
    s = series.get(sym)
    if s is None:
        return None
    ed = next_tday(e_date)
    if ed is None or ed not in s.index:
        return None
    dma = s.rolling(dma_n).mean()
    win = s[s.index > ed]
    entry = s[ed]
    if not np.isfinite(entry) or entry <= 0:
        return None
    for i, (d, c) in enumerate(win.items()):
        if i >= 120 or (np.isfinite(dma.get(d, np.nan)) and c < dma[d]):
            return (c / entry - 1) - COST, False, i + 1
    if len(win):
        return (win.iloc[-1] / entry - 1) - COST, True, len(win)  # censored
    return None

rows = []
for _, r in ev.iterrows():
    sym = str(r[symc]).strip()
    d = r[avc].date()
    if not in_universe(sym, d):
        continue
    res = run_trade(sym, r[avc], 50)
    if res is None:
        continue
    ret, censored, held = res
    res20 = run_trade(sym, r[avc], 20)
    rows.append(dict(sym=sym, event=d, bucket=r.bucket, ret50=ret, censored=censored,
                     held=held, ret20=res20[0] if res20 else np.nan))
tr = pd.DataFrame(rows)
tr.to_csv(OUT / "te_events.csv", index=False)
print(f"trades: {len(tr)} (censored {tr.censored.sum()})", flush=True)

# ---- regime control: mean same-length drift of universe names at each event date (sampled) ----
def control_ret(d, held):
    ed = next_tday(d)
    if ed is None:
        return np.nan
    prior = [s for s in snap_dates if s <= d]
    if not prior:
        return np.nan
    names = list(snaps[prior[-1]])
    pick = rng.choice(names, size=min(20, len(names)), replace=False)
    rets = []
    for sym in pick:
        s = series.get(sym)
        if s is None or ed not in s.index:
            continue
        win = s[s.index > ed]
        if len(win) < 1:
            continue
        j = min(int(held), len(win)) - 1
        if j < 0:
            continue
        rets.append(win.iloc[j] / s[ed] - 1)
    return np.mean(rets) if rets else np.nan

live = tr[~tr.censored].copy()
live["ctrl"] = [control_ret(d, h) for d, h in zip(live.event, live.held)]
live = live.dropna(subset=["ctrl"])
live["excess"] = live.ret50 - live.ctrl - 0  # control has no cost; trade ret already net

def stat(x):
    x = np.asarray(x, float)
    return len(x), x.mean() * 100, x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

n, m, t = stat(live.excess)
era1 = live[pd.to_datetime(live.event.astype(str)) < "2021-01-01"]
era2 = live[pd.to_datetime(live.event.astype(str)) >= "2021-01-01"]
_, m1, t1 = stat(era1.excess) if len(era1) > 2 else (0, np.nan, np.nan)
_, m2, t2 = stat(era2.excess) if len(era2) > 2 else (0, np.nan, np.nan)

# placebo: 200x random symbol-date events, same n, excess vs control skipped (costly) ->
# use raw net ret distribution vs live raw net ret (declared simplification: same control regime)
null = []
all_syms = list(series)
for _ in range(200):
    picks = rng.integers(0, len(tr), size=min(len(tr), 400))
    rets = []
    for i in picks:
        sym = rng.choice(all_syms)
        d = tr.event.iloc[i]
        res = run_trade(sym, pd.Timestamp(d), 50)
        if res and not res[1]:
            rets.append(res[0])
    if rets:
        null.append(np.mean(rets))
null = np.array(null)
real_raw = live.ret50.mean()
p95 = np.percentile(null, 95)

bars = {"t>=2.5": t >= 2.5, "n>=300": n >= 300,
        "eras_both_pos": (m1 > 0) and (m2 > 0),
        "beat_placebo95": real_raw > p95}
kill = (t < 1.5) or ((m1 > 0) != (m2 > 0))
verdict = "PASS -> Gate-4 realism next" if all(bars.values()) else ("KILL" if kill else "PARK")

lines = [f"events gated+traded: {len(tr)} | live(non-censored): {n} | censored: {int(tr.censored.sum())}",
         f"B1 (>=100% YoY): {sum(live.bucket=='B1')} | B2 (turnaround): {sum(live.bucket=='B2')}",
         f"net ret/trade (DMA50): {live.ret50.mean()*100:+.2f}% | DMA20 secondary: {live.ret20.mean()*100:+.2f}%",
         f"EXCESS over control: {m:+.2f}%/trade, t={t:.2f} (bars: t>=2.5, n>=300)",
         f"eras: 2015-20 {m1:+.2f}% (t={t1:.1f}, n={len(era1)}) | 2021-26 {m2:+.2f}% (t={t2:.1f}, n={len(era2)})",
         f"placebo x{len(null)}: null mean {null.mean()*100:+.2f}%, 95th {p95*100:+.2f}% vs real raw {real_raw*100:+.2f}%",
         "bars: " + ", ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "T-E-CARD", "frozen_commit": "b12264b", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "te_pead.py", "data": ["unified_quarterly_pit", "close_all bhavcopy panel", "PIT NIFTY500 snapshots"],
        "n_obs": int(n), "metrics": {"excess_pct": round(float(m), 2), "t": round(float(t), 2),
        "net_ret_pct": round(float(live.ret50.mean() * 100), 2)},
        "validation": {"era_split": f"{m1:+.2f}/{m2:+.2f}", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight", "one_day_lag": "entry D+1 close after available_date (PIT)"},
        "verdict": verdict, "bars_hit": [k for k, v in bars.items() if v],
        "trials_increment": 2, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written", flush=True)
