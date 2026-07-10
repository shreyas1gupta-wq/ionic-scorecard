"""WINDOWED 0/1-DTE BUYING (attempt #18, Principal spec): entries 09:15-10:45 and 13:15-15:15
(no new entries 10:45-13:15; positions opened before 10:45 may RUN with trailing through midday);
ALL positions flat by 15:15. Strategies x {0DTE, 1DTE}:
  W1 sigma-momentum: 15-min |ret| > 1 sigma (day-adaptive, min 12 obs) -> ATM with the move.
  W2 range-break: morning = break of first-15-min opening range (entries from 09:30); afternoon =
     break of full morning range after 13:15.
  W3 V7-pullback (5-min bars): EMA9>EMA26, pullback to EMA9/26, rejection close, RSI>50 -> CE
     (mirrored for PE).
EXITS: initial SL 50% of premium; TRAIL once premium >= 1.5x entry: stop = 0.7x running peak;
  time exit 15:15. Max 2 entries/day/strategy, one position at a time per strategy.
COSTS 1% slip + 0.2% + Rs20/order per fill. PASS bar (frozen): net>0 AND day-t>=2 AND PF>=1.2,
  n>=60. Ledger +6. 1DTE = trade on day D where expiry E-D = 1 (uses richer premiums, less gamma)."""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BUYSIDE_LAST3H_20260710"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
mapping, exps = chain.build_expiry_index()
expset = set(exps)
FLAT = dt.time(15, 15)
def fee(px): return 0.012 * px + 0.267
def in_window(t):
    return (dt.time(9, 15) <= t.time() <= dt.time(10, 45)) or (dt.time(13, 15) <= t.time() <= dt.time(15, 15))

def manage(series, t0):
    """long with 50% SL, trail 0.7*peak after 1.5x, flat by 15:15."""
    e = series.loc[t0]
    if e <= 1: return None
    win = series[(series.index > t0) & (series.index.time <= FLAT)]
    if not len(win): return None
    peak, trail_on = e, False
    for i, (t, v) in enumerate(win.items()):
        peak = max(peak, v)
        if not trail_on and v >= 1.5 * e: trail_on = True
        stop = 0.7 * peak if trail_on else 0.5 * e
        if v <= stop:
            rest = win.iloc[i + 1:]
            xp = rest.iloc[0] if len(rest) else v
            return (xp - e) - fee(e) - fee(xp)
    xp = win.iloc[-1]
    return (xp - e) - fee(e) - fee(xp)

def day_signals(bars):
    """yield (strategy, ts, direction) respecting windows."""
    c = bars["close"]
    sigs = []
    # W1
    r15 = c.pct_change(15)
    for t in c.index:
        if not in_window(t) or t.time() > dt.time(15, 0): continue
        hist = r15[r15.index < t].dropna()
        if len(hist) < 12: continue
        v = r15.loc[t]
        s = hist.std()
        if pd.notna(v) and s > 0 and abs(v) >= s and abs(v) >= 0.0015:
            sigs.append(("W1", t, 1 if v > 0 else -1))
    # W2
    orng = c[c.index.time <= dt.time(9, 30)]
    if len(orng) > 5:
        hi, lo = orng.max(), orng.min()
        post = c[(c.index.time > dt.time(9, 30)) & (c.index.time <= dt.time(10, 45))]
        b = post[(post > hi) | (post < lo)]
        if len(b): sigs.append(("W2", b.index[0], 1 if b.iloc[0] > hi else -1))
    morning = c[c.index.time < dt.time(12, 30)]
    if len(morning) > 30:
        hi2, lo2 = morning.max(), morning.min()
        post2 = c[(c.index.time >= dt.time(13, 15)) & (c.index.time <= dt.time(15, 0))]
        b2 = post2[(post2 > hi2) | (post2 < lo2)]
        if len(b2): sigs.append(("W2", b2.index[0], 1 if b2.iloc[0] > hi2 else -1))
    # W3 on 5-min
    b5 = bars.resample("5min", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    e9 = b5["close"].ewm(span=9, adjust=False).mean()
    e26 = b5["close"].ewm(span=26, adjust=False).mean()
    d = b5["close"].diff(); rup = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    rdn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 - 100 / (1 + rup / rdn)
    for i in range(20, len(b5)):
        t = b5.index[i]
        if not in_window(t) or t.time() > dt.time(15, 0): continue
        if e9.iloc[i] > e26.iloc[i] and (b5["low"].iloc[i] <= e9.iloc[i]) and \
           b5["close"].iloc[i] > b5["open"].iloc[i] and rsi.iloc[i] > 50:
            sigs.append(("W3", t, 1))
        elif e9.iloc[i] < e26.iloc[i] and (b5["high"].iloc[i] >= e9.iloc[i]) and \
             b5["close"].iloc[i] < b5["open"].iloc[i] and rsi.iloc[i] < 50:
            sigs.append(("W3", t, -1))
    return sorted(sigs, key=lambda x: x[1])

rows = []
all_days = sorted(set(sd))
for day in all_days:
    dte_tags = []
    if day in expset: dte_tags.append(("0DTE", day))
    e1 = chain.nearest_expiry(day, 1, 1)
    if e1 is not None: dte_tags.append(("1DTE", e1))
    if not dte_tags: continue
    bars = spot[sd == day]
    if len(bars) < 200: continue
    sigs = day_signals(bars)
    if not sigs: continue
    for tag, exp in dte_tags:
        try:
            df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                      "close", "trading_day"]).to_pandas()
        except Exception:
            continue
        df = df[df["trading_day"] == str(day)]
        if not len(df): continue
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
        busy_until = {}
        counts = {}
        for strat, t, dirn in sigs:
            if counts.get(strat, 0) >= 2: continue
            if t < busy_until.get(strat, pd.Timestamp.min): continue
            k = round(bars["close"].asof(t) / 50) * 50
            cp = "CE" if dirn > 0 else "PE"
            s = leg(k, cp)
            if t not in s.index: continue
            r = manage(s, t)
            if r is None: continue
            rows.append(dict(cell=f"{strat}/{tag}", day=str(day), net=r))
            counts[strat] = counts.get(strat, 0) + 1
            busy_until[strat] = t + pd.Timedelta(minutes=30)

df = pd.DataFrame(rows)
df.to_csv(OUT / "windowed_trades.csv", index=False)
lines = ["# Windowed 0/1-DTE buying (frozen bars: net>0, t>=2, PF>=1.2, n>=60)"]
for cell, g in df.groupby("cell"):
    daily = g.groupby("day")["net"].sum()
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if len(daily) > 2 else np.nan
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    era = {e2: gg.net.mean() for e2, gg in g.groupby(g.day < "2024-01-01")}
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2) else "KILL") if len(g) >= 60 else "INSUFF"
    lines.append(f"{cell}: n={len(g)} days={len(daily)} net={g.net.mean():+.2f} | t={t:.2f} PF={pf:.2f} "
                 f"win={len(w)/len(g)*100:.0f}% | era21-23={era.get(True, np.nan):+.2f} era24-26={era.get(False, np.nan):+.2f} | **{verdict}**")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY_WINDOWED.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
