"""T-C-CARD: post-breakout ORB window. Frozen @ 4692e17 BEFORE run.
V1-EOD (literal ask, 40bps gross hurdle) + V2-HOLD (overnight trail, cost-regime changer).
Placebo: one pooled run of random stage-2 non-breakout stock-days -> bootstrap 200 means
(declared equivalent-and-cheaper implementation of the 200x placebo bar).
Minute panel: UTC timestamps (landmine #1) -> IST via +5:30; span 2022-01..2026-01-21.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
import pyarrow.dataset as pads
import pyarrow.compute as pc
from pathlib import Path

rng = np.random.default_rng(23)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TC_POSTBREAKOUT_ORB_20260711"
OUT.mkdir(parents=True, exist_ok=True)
COST, COST_SL = 0.0015, 0.0030  # per side

# minute shards (path from data_audit/audit_saintforest_panel.py)
shard_dir = ROOT / "swing_momentum" / "data" / "hf_stock_minute" / "minute"
print("minute shards:", shard_dir, flush=True)
mds = pads.dataset(str(shard_dir), format="parquet")

# calendar + daily panel for stage-2 placebo pool
px = pd.read_parquet(ROOT / "datasets/nse_bhavcopy_daily/close_all.parquet")
px["date"] = pd.to_datetime(px["date"])
tdays = np.array(sorted(px.date.unique()))

ev = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BREAKOUT_SCAN_20260710/signal_triggers_pit.csv",
                 parse_dates=["Date"])
ev = ev[(ev.Date >= "2022-01-15") & (ev.Date <= "2025-12-31")]
print(f"events in minute span: {len(ev)}", flush=True)

def window_days(e_date, k=10):
    i = np.searchsorted(tdays, np.datetime64(e_date), side="right")
    return [pd.Timestamp(t) for t in tdays[i:i + k]]

# build (symbol -> set of window dates) map
need = {}
ev_windows = []
for _, r in ev.iterrows():
    wd = window_days(r.Date)
    ev_windows.append((r.Symbol, r.Date, wd))
    need.setdefault(r.Symbol, set()).update(d.date() for d in wd)

# placebo pool: random stage-2 stock-days NOT in any event window (from ever-N500 close_all)
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
ever = set(uni["Ticker"].dropna().astype(str).str.strip())
evset = {(s, d) for s, ds_ in need.items() for d in ds_}
pool = []
px2 = px[px.symbol.isin(ever & set(px.symbol.unique()))]
for sym, g in px2.groupby("symbol"):
    c = g.set_index("date")["close"]
    if len(c) < 260:
        continue
    d200 = c.rolling(200).mean(); d50 = c.rolling(50).mean()
    ok = c.index[(c > d200) & (d50 > d200) & (c.index >= "2022-01-15") & (c.index <= "2025-12-31")]
    for d in ok[:: max(1, len(ok) // 8)]:
        if (sym, d.date()) not in evset:
            pool.append((sym, d.date()))
rng.shuffle(pool)
pool = pool[:2500]
for sym, d in pool:
    need.setdefault(sym, set()).add(d)
print(f"placebo pool: {len(pool)} stock-days | symbols to scan: {len(need)}", flush=True)

def orb_day(bars):
    """bars: DataFrame with ist (datetime), open/high/low/close. Return trade dict or None."""
    t = bars.ist.dt.time
    orw = bars[(t >= dt.time(9, 15)) & (t < dt.time(9, 30))]
    if len(orw) < 10:
        return None
    or_hi, or_lo = orw.high.max(), orw.low.min()
    post = bars[(t >= dt.time(9, 30)) & (t <= dt.time(15, 25))].reset_index(drop=True)
    trig = post[post.close > or_hi]
    if not len(trig):
        return None
    i0 = trig.index[0]
    if i0 + 1 >= len(post):
        return None
    entry = post.close.iloc[i0 + 1]
    sl_hit = None
    seg = post.iloc[i0 + 2:]
    breach = seg[seg.close < or_lo]
    if len(breach):
        j = breach.index[0]
        sl_hit = post.close.iloc[j + 1] if j + 1 < len(post) else post.close.iloc[j]
    eod = post.close.iloc[-1]
    exit_v1 = sl_hit if sl_hit is not None else eod
    cost_v1 = COST + (COST_SL if sl_hit is not None else COST)
    return dict(entry=entry, or_lo=or_lo, day_low=post.low.min(), eod=eod,
                v1=(exit_v1 / entry - 1) - cost_v1, v1_sl=sl_hit is not None)

rows, done_syms = [], 0
sym_list = sorted(need)
for b0 in range(0, len(sym_list), 40):
    batch = sym_list[b0:b0 + 40]
    tbl = mds.to_table(columns=["symbol", "timestamp", "open", "high", "low", "close"],
                       filter=pc.field("symbol").isin(batch))
    df = tbl.to_pandas()
    if not len(df):
        continue
    df["ist"] = df.timestamp.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df["d"] = df.ist.dt.date
    for sym, g in df.groupby("symbol"):
        want = need.get(sym, set())
        g = g[g.d.isin(want)]
        for d, bars in g.groupby("d"):
            res = orb_day(bars.sort_values("ist"))
            if res:
                res.update(sym=sym, day=d)
                rows.append(res)
    done_syms += len(batch)
    print(f"...{done_syms}/{len(sym_list)} symbols, day-trades so far {len(rows)}", flush=True)

idf = pd.DataFrame(rows)
idf.to_csv(OUT / "tc_daytrades_raw.csv", index=False)

# label event vs placebo day-trades; V2 build per event (hold across window w/ daily trail)
evday = {}
for sym, e, wd in ev_windows:
    for d in wd:
        evday.setdefault((sym, d.date()), []).append(e)
idf["is_event"] = [((r.sym, r.day) in evday) for r in idf.itertuples()]
evt = idf[idf.is_event]; plc = idf[~idf.is_event]

# V2: first ORB trigger day per (event window); then trail on daily closes (from minute-day aggregates)
daily_close = idf.set_index(["sym", "day"]).eod.to_dict()
daily_low = idf.set_index(["sym", "day"]).day_low.to_dict()
v2 = []
for sym, e, wd in ev_windows:
    for d in wd:
        key = (sym, d.date())
        if key in evday and key in daily_close:
            row = idf[(idf.sym == sym) & (idf.day == d.date())]
            if not len(row) or not np.isfinite(row.entry.iloc[0]):
                continue
            r0 = row.iloc[0]
            entry, trail = r0.entry, r0.or_lo
            # if SL same day -> V2 == V1 outcome
            if r0.v1_sl:
                v2.append(dict(sym=sym, event=e.date(), ret=r0.v1, held=1)); break
            exit_px, held = None, 1
            prev_low = r0.day_low
            for d2 in [x for x in wd if x.date() > d.date()]:
                k2 = (sym, d2.date())
                if k2 not in daily_close:
                    break
                trail = max(trail, prev_low)
                if daily_close[k2] < trail:
                    exit_px, held = daily_close[k2], held + 1
                    break
                prev_low = daily_low[k2]; held += 1
            if exit_px is None:
                lastk = (sym, wd[-1].date())
                exit_px = daily_close.get(lastk, r0.eod)
            v2.append(dict(sym=sym, event=e.date(), ret=(exit_px / entry - 1) - 2 * COST, held=held))
            break  # one trade per event window
v2df = pd.DataFrame(v2)
v2df.to_csv(OUT / "tc_v2_trades.csv", index=False)

def stat(x):
    x = np.asarray(x, float)
    return len(x), x.mean() * 1e4, x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

n1, m1, t1 = stat(evt.v1)
gross1 = (evt.v1 + np.where(evt.v1_sl, COST + COST_SL, 2 * COST)).mean() * 1e4
n2, m2, t2 = stat(v2df.ret)
pf2 = v2df[v2df.ret > 0].ret.sum() / abs(v2df[v2df.ret < 0].ret.sum()) if len(v2df[v2df.ret < 0]) else np.inf
# placebo bootstrap 200 means (V1 engine)
null = np.array([plc.v1.sample(min(len(plc), n1), replace=True, random_state=i).mean() for i in range(200)])
p95 = np.percentile(null, 95) * 1e4
era_cut = dt.date(2024, 7, 1)
e1v2 = v2df[v2df.event < era_cut]; e2v2 = v2df[v2df.event >= era_cut]
_, me1, _ = stat(e1v2.ret) if len(e1v2) > 2 else (0, np.nan, 0)
_, me2, _ = stat(e2v2.ret) if len(e2v2) > 2 else (0, np.nan, 0)

v1_bars = {"net>0": m1 > 0, "gross>=40bps": gross1 >= 40, "t>=2.5": t1 >= 2.5, "n>=150": n1 >= 150}
v2_bars = {"net>0": m2 > 0, "t>=2.5": t2 >= 2.5, "PF>=1.3": pf2 >= 1.3, "beat_placebo95": (m2 / 1e4) > p95 / 1e4,
           "n>=150": n2 >= 150, "eras_both_pos": (me1 > 0) and (me2 > 0)}
v1_verdict = "PASS" if all(v1_bars.values()) else "KILL"
v2_verdict = "PASS" if all(v2_bars.values()) else ("KILL" if (t2 < 1.5 or ((me1 > 0) != (me2 > 0))) else "PARK")

lines = [f"event day-trades: {n1} (of {len(evt)} event stock-days w/ trigger) | placebo day-trades: {len(plc)}",
         f"V1-EOD: net {m1:+.1f} bps/trade (gross {gross1:+.1f}, hurdle 40), t={t1:.2f}, SL-rate {evt.v1_sl.mean()*100:.0f}%",
         f"  bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in v1_bars.items()) + f" -> {v1_verdict}",
         f"V2-HOLD: n={n2}, net {m2:+.1f} bps/trade, t={t2:.2f}, PF={pf2:.2f}, held avg {v2df.held.mean():.1f}d",
         f"  eras: {me1:+.1f} / {me2:+.1f} bps | placebo95 (V1 engine): {p95:+.1f} bps, null mean {null.mean()*1e4:+.1f}",
         f"  bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in v2_bars.items()) + f" -> {v2_verdict}",
         f"VERDICT: V1={v1_verdict}, V2={v2_verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "T-C-CARD", "frozen_commit": "4692e17", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "tc_orb.py", "data": ["stock minute panel 2022-2026 (audited)", "signal_triggers_pit", "close_all"],
        "n_obs": int(n1 + n2), "metrics": {"v1_net_bps": round(float(m1), 1), "v1_gross_bps": round(float(gross1), 1),
        "v2_net_bps": round(float(m2), 1), "v2_t": round(float(t2), 2), "v2_pf": round(float(pf2), 2)},
        "validation": {"era_split": f"v2 {me1:+.1f}/{me2:+.1f}", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight", "one_day_lag": "PIT triggers; entry post-confirm bar"},
        "verdict": f"V1={v1_verdict}, V2={v2_verdict}", "bars_hit": [],
        "trials_increment": 2, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written", flush=True)
