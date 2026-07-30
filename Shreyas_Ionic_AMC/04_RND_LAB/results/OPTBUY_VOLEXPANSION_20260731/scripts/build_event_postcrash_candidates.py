"""Build EOD-granularity trade candidates for:
  EVENT-DRIVEN  (BUDGET/RBI/FED/ELECTION/EARNINGS): entry T-2 close, exit at/after the event close
  POST-CRASH    (>=2*ATR20 daily move): entry T+1 (day after the shock) close-to-close-based hold

All entry/exit prices will be real 1-min-file end-of-day closes (last bar ~15:29), no lookahead:
the event calendar is public/scheduled information; the post-crash trigger only uses data through
day T's close to decide the T+1 entry.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
OPT_START = pd.Timestamp("2021-05-24")
OPT_END = pd.Timestamp("2026-06-02")

px = pd.read_parquet(IDX, columns=["close"]).sort_index()
px = px[(px.index.time >= pd.Timestamp("09:15").time()) & (px.index.time <= pd.Timestamp("15:30").time())]
px["d"] = px.index.normalize()
dly = px.groupby("d").agg(c=("close", "last"))
trading_days = dly.index

def next_trading_day(d, n=1):
    idx_ = trading_days.searchsorted(pd.Timestamp(d))
    j = idx_ + n
    return trading_days[j] if 0 <= j < len(trading_days) else None

def prior_trading_day(d, n=1):
    idx_ = trading_days.searchsorted(pd.Timestamp(d))
    j = idx_ - n
    return trading_days[j] if 0 <= j < len(trading_days) else None

def on_or_after(d):
    """first trading day >= d"""
    d = pd.Timestamp(d)
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None

# ------------------------------------------------------------------ EVENT-DRIVEN candidates
ev = pd.read_csv(f"{OUT}/events_scheduled.csv", parse_dates=["date"])
cl = pd.read_csv(f"{OUT}/earnings_clusters.csv", parse_dates=["start", "end"])

ev = ev[(ev.date >= OPT_START) & (ev.date <= OPT_END)].reset_index(drop=True)
cl = cl[(cl.start >= OPT_START) & (cl.start <= OPT_END)].reset_index(drop=True)

rows = []
N_PRE = 2   # pre-registered primary: entry 2 trading days before the event day (EOD close)
for _, r in ev.iterrows():
    event_day = on_or_after(r["date"])
    if event_day is None:
        continue
    entry_day = prior_trading_day(event_day, N_PRE)
    if entry_day is None:
        continue
    # FED decisions land after Indian market close (US afternoon = IST night) -> exit T+1 close
    m_days = 1 if r["category"] == "FED" else 0
    exit_day = next_trading_day(event_day, m_days) if m_days else event_day
    if exit_day is None:
        continue
    rows.append(dict(cell=f"EVENT_{r['category']}", entry_day=entry_day, exit_day=exit_day,
                      event_day=event_day, note=r["note"]))

for _, r in cl.iterrows():
    cluster_start = on_or_after(r["start"])
    if cluster_start is None:
        continue
    entry_day = prior_trading_day(cluster_start, N_PRE)
    exit_day = next_trading_day(cluster_start, 3)   # fixed 3-trading-day hold from cluster start
    if entry_day is None or exit_day is None:
        continue
    rows.append(dict(cell="EVENT_EARNCLUSTER", entry_day=entry_day, exit_day=exit_day,
                      event_day=cluster_start, note=r["names"]))

E = pd.DataFrame(rows).drop_duplicates(subset=["cell", "entry_day", "exit_day"]).sort_values("entry_day")
print(f"[event candidates] {len(E)} rows")
print(E.groupby("cell").size())

# one-position-at-a-time WITHIN each cell (categories evaluated as independent candidate strategies)
kept = []
for cell, g in E.groupby("cell"):
    g = g.sort_values("entry_day")
    next_free = None
    for _, r in g.iterrows():
        if next_free is not None and r["entry_day"] < next_free:
            continue
        kept.append(r)
        next_free = r["exit_day"]
E = pd.DataFrame(kept)
print(f"[event candidates after one-at-a-time] {len(E)} rows")
print(E.groupby("cell").size())
E.to_csv(f"{OUT}/event_trade_candidates.csv", index=False)

# ------------------------------------------------------------------ POST-CRASH candidates
tr = (dly.c.diff().abs())
atr20 = tr.rolling(20, min_periods=10).mean().shift(1)   # PIT: only info through T-1
shock = (dly.c.diff().abs() >= 2.0 * atr20)
shock_days = dly.index[shock.fillna(False)]
shock_days = shock_days[(shock_days >= OPT_START) & (shock_days <= OPT_END)]
print(f"\n[post-crash] {len(shock_days)} shock days (>=2*ATR20 close-to-close) in option-covered span")

pc_rows = []
HOLD = 2   # pre-registered primary hold (trading days), robustness variants tested separately
for d in shock_days:
    entry_day = next_trading_day(d, 1)   # T+1 (the day AFTER the shock) — no same-day lookahead
    if entry_day is None:
        continue
    exit_day = next_trading_day(entry_day, HOLD - 1)
    if exit_day is None:
        continue
    pc_rows.append(dict(cell="POSTCRASH", entry_day=entry_day, exit_day=exit_day, event_day=d,
                         note=f"shock={dly.c.diff().abs().loc[d]:.1f}pts vs atr20={atr20.loc[d]:.1f}"))

PC = pd.DataFrame(pc_rows).drop_duplicates(subset=["entry_day", "exit_day"]).sort_values("entry_day")
# one-at-a-time
kept = []
next_free = None
for _, r in PC.iterrows():
    if next_free is not None and r["entry_day"] < next_free:
        continue
    kept.append(r)
    next_free = r["exit_day"]
PC = pd.DataFrame(kept)
print(f"[post-crash after one-at-a-time] {len(PC)} rows")
PC.to_csv(f"{OUT}/postcrash_trade_candidates.csv", index=False)

ALL = pd.concat([E, PC], ignore_index=True)
ALL.to_csv(f"{OUT}/eod_trade_candidates.csv", index=False)
print(f"\n[combined] {len(ALL)} EOD-granularity candidates written to eod_trade_candidates.csv")
print(ALL.groupby("cell").size())
