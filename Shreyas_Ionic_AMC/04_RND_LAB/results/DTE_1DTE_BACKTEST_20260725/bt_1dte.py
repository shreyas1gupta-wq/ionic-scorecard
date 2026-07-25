"""1DTE vs 0DTE NIFTY ATM short straddle — resumable backtest.

Mirrors final_three.py conventions EXACTLY so results are comparable to the S1-F baseline:
  fee(px) = 0.012*px + 0.267  (1% slip + 0.20% statutory + Rs20/order at lot 75), charged on
  entry AND exit, per leg. Per-leg SL 30%, fill at the NEXT 1-min close after breach.
  Emits RAW per-day net pts (NO F1/F2 vetoes) — vetoes are a downstream equity-layer concern.

ARMS
  S1_0DTE       entry D0 09:20  -> exit D0 15:25    (CONTROL: must reproduce +10.73 pts/day, t=3.92, PF 1.79)
  S1_1DTE_CLOSE entry D-1 15:25 -> exit D0 15:25    (isolates the overnight + full expiry day)
  S1_1DTE_OPEN  entry D-1 09:20 -> exit D0 15:25    (full D-1 + overnight + D0)

Also emits an OVERNIGHT GAP diagnostic: ATM straddle premium at D-1 15:25 vs D0 first bar >=09:15.

The one deliberate deviation from final_three.short_leg: the window is bounded by an ABSOLUTE
timestamp (D0 15:25) instead of time-of-day, because a time-of-day filter is wrong once a
position spans two dates. For the 0DTE arm the two are equivalent by construction.

Resumable: appends per expiry, skips expiries already in the output CSV.
Usage: bt_1dte.py [--limit N]
"""
import sys, datetime as dt, argparse
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = Path(__file__).parent
TRADES = OUT / "trades_1dte.csv"
GAPS = OUT / "gaps_1dte.csv"
PROG = OUT / "PROGRESS_1DTE.md"
SL, LOT = 0.30, 75

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=0)
args = ap.parse_args()


def fee(px):
    return 0.012 * px + 0.267


def short_leg(series, t0, t_end, sl=SL):
    """Short from t0, SL mult sl, hard exit at t_end. Mirrors final_three.short_leg."""
    if t0 not in series.index:
        return None
    e = series.loc[t0]
    win = series[(series.index > t0) & (series.index <= t_end)]
    if not len(win):
        return None
    br = win[win >= e * (1 + sl)]
    if len(br):
        after = win[win.index > br.index[0]]
        xt, xp = (after.index[0], after.iloc[0]) if len(after) else (br.index[0], br.iloc[0])
        return (e - xp) - fee(e) - fee(xp), True, xt, e
    xp = win.iloc[-1]
    return (e - xp) - fee(e) - fee(xp), False, None, e


spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sdate = pd.Series(spot.index.date, index=spot.index)
tdays = sorted(set(spot.index.date))
tpos = {d: i for i, d in enumerate(tdays)}
mapping, exps = chain.build_expiry_index()

done = set()
if TRADES.exists():
    prev = pd.read_csv(TRADES)
    done = set(prev["day"].astype(str))
    print(f"[resume] {len(done)} expiries already done")

todo = [e for e in exps if str(e) not in done]
if args.limit:
    todo = todo[: args.limit]
print(f"[run] {len(todo)} expiries to process")

rows, gaps, n_ok = [], [], 0
for i, exp in enumerate(todo, 1):
    d0 = exp
    if d0 not in tpos or tpos[d0] == 0:
        continue
    dm1 = tdays[tpos[d0] - 1]
    s0, s1_ = spot[sdate == d0], spot[sdate == dm1]
    if len(s0) < 100 or len(s1_) < 100:
        continue

    t_end = pd.Timestamp(d0) + pd.Timedelta(hours=15, minutes=25)
    c0 = s0[s0.index.time >= dt.time(9, 20)]
    c1o = s1_[s1_.index.time >= dt.time(9, 20)]
    c1c = s1_[s1_.index.time <= dt.time(15, 25)]
    if not len(c0) or not len(c1o) or not len(c1c):
        continue

    ARMS = {
        "S1_0DTE":       c0.index[0],
        "S1_1DTE_OPEN":  c1o.index[0],
        "S1_1DTE_CLOSE": c1c.index[-1],
    }
    atm = {k: round(spot["close"].loc[t] / 50) * 50 for k, t in ARMS.items()}
    strikes = sorted({float(v) for v in atm.values()})

    try:
        df = pq.read_table(
            mapping[exp],
            columns=["timestamp", "strike", "option_type", "close", "trading_day"],
            filters=[("trading_day", "in", [str(d0), str(dm1)]), ("strike", "in", strikes)],
        ).to_pandas()
    except Exception as ex:
        print(f"  ! {exp} read failed: {ex}")
        continue
    if not len(df):
        continue
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)

    cache = {}
    def leg(k, cp):
        key = (float(k), cp)
        if key not in cache:
            s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")["close"].sort_index()
            cache[key] = s[~s.index.duplicated(keep="last")]
        return cache[key]

    for arm, t0 in ARMS.items():
        k = atm[arm]
        L = {"CE": leg(k, "CE"), "PE": leg(k, "PE")}
        if any(t0 not in L[c].index for c in L):
            continue
        pnl, entry_prem, ok, breaches = 0.0, 0.0, True, 0
        for c in L:
            r = short_leg(L[c], t0, t_end)
            if r is None:
                ok = False
                break
            pnl += r[0]; entry_prem += r[3]; breaches += int(r[1])
        if ok:
            rows.append(dict(strat=arm, day=str(d0), net=pnl, entry_prem=entry_prem,
                             legs_stopped=breaches, strike=k, dm1=str(dm1)))

    # overnight gap diagnostic on the 1DTE-CLOSE strike
    k = atm["S1_1DTE_CLOSE"]; t1c = ARMS["S1_1DTE_CLOSE"]
    ce, pe = leg(k, "CE"), leg(k, "PE")
    if t1c in ce.index and t1c in pe.index:
        p_close = ce.loc[t1c] + pe.loc[t1c]
        nxt = [s[(s.index >= pd.Timestamp(d0) + pd.Timedelta(hours=9, minutes=15))] for s in (ce, pe)]
        if all(len(s) for s in nxt):
            p_open = nxt[0].iloc[0] + nxt[1].iloc[0]
            gaps.append(dict(day=str(d0), strike=k, prem_dm1_1525=p_close, prem_d0_open=p_open,
                             gap_ratio=p_open / p_close if p_close else np.nan,
                             spot_dm1=spot["close"].loc[t1c],
                             spot_d0_open=spot["close"].loc[nxt[0].index[0]]
                             if nxt[0].index[0] in spot.index else np.nan))
    n_ok += 1
    if i % 20 == 0 or i == len(todo):
        pd.DataFrame(rows).to_csv(TRADES, mode="a", header=not TRADES.exists(), index=False)
        pd.DataFrame(gaps).to_csv(GAPS, mode="a", header=not GAPS.exists(), index=False)
        rows, gaps = [], []
        PROG.write_text(f"# 1DTE backtest progress\nlast expiry: {exp}\ndone: {i}/{len(todo)}\n",
                        encoding="utf-8")
        print(f"  [{i}/{len(todo)}] through {exp}", flush=True)

if rows:
    pd.DataFrame(rows).to_csv(TRADES, mode="a", header=not TRADES.exists(), index=False)
if gaps:
    pd.DataFrame(gaps).to_csv(GAPS, mode="a", header=not GAPS.exists(), index=False)

# ---- summary ----
t = pd.read_csv(TRADES)
print(f"\n=== PER-TRADE EDGE (raw pts/day, no vetoes, net of 1% slip + TC) ===")
out = []
for st, g in t.groupby("strat"):
    d = g["net"]
    tstat = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    w, l = d[d > 0], d[d <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else np.inf
    cum = d.cumsum(); dd = (cum - cum.cummax()).min()
    out.append(dict(strat=st, n=len(d), net_pts=round(d.mean(), 2), t=round(tstat, 2),
                    PF=round(pf, 2), win_pct=round(100 * len(w) / len(d), 1),
                    maxDD_pts=round(dd, 0), avg_entry_prem=round(g.entry_prem.mean(), 1),
                    legs_stopped_avg=round(g.legs_stopped.mean(), 2),
                    total_1lot_Rs=round(d.sum() * LOT)))
s = pd.DataFrame(out).sort_values("strat")
print(s.to_string(index=False))
s.to_csv(OUT / "SUMMARY_1DTE.csv", index=False)

if GAPS.exists():
    gg = pd.read_csv(GAPS)
    r = gg["gap_ratio"].dropna()
    print(f"\n=== OVERNIGHT GAP on ATM straddle premium (D-1 15:25 -> D0 open), n={len(r)} ===")
    print(f"  mean {r.mean():.3f}x | median {r.median():.3f}x | p05 {r.quantile(.05):.3f}x "
          f"| p95 {r.quantile(.95):.3f}x | max {r.max():.3f}x")
    print(f"  premium DECAYED overnight on {100*(r<1).mean():.1f}% of nights "
          f"(good for a seller); EXPANDED on {100*(r>=1).mean():.1f}%")
    print(f"  nights breaching the 30% SL level at the open alone: {100*(r>=1.30).mean():.1f}%")
print("\nsaved ->", OUT)
