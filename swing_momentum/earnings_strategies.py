"""Event-driven equity strategies using earnings dates (Episodic Pivot + PEAD).

Uses datasets/nse_earnings_dates/earnings_dates.csv (2020-2026) + the daily price/volume
panel. Two strategies:
  EP  : on earnings, if the stock reacts +>=X% on volume spike -> buy next open, hold H days.
  PEAD: post-earnings drift — event-study of forward returns by earnings-day reaction bucket.
Portfolio = equal-weight all active EP positions each day, realistic costs. Build/forward.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DAY = ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet"
EARN = ROOT / "datasets/nse_earnings_dates/earnings_dates.csv"
SPLIT = dt.date(2024, 6, 30)      # earnings data starts 2020; build 2020-2024H1, fwd 2024H2-2026
COST_RT = 0.004
RET_CLIP = 0.25


def load_panel():
    df = pq.read_table(DAY, columns=["symbol", "timestamp", "open", "close", "volume"]).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    df = df[df["close"] > 0]
    C = df.pivot_table("close", "date", "symbol").sort_index()
    O = df.pivot_table("open", "date", "symbol").reindex(C.index)
    V = df.pivot_table("volume", "date", "symbol").reindex(C.index)
    return C, O, V


def load_events(valid_symbols):
    e = pd.read_csv(EARN)
    e["date"] = pd.to_datetime(e["date"], format="%d-%b-%Y", errors="coerce")
    e = e.dropna(subset=["date"])
    e = e[e["purpose"].str.contains("Financial Results", case=False, na=False)]
    e = e[e["symbol"].isin(valid_symbols)]
    return e[["symbol", "date"]].drop_duplicates()


LIQ_MIN = 5e7        # >= Rs 5 crore/day 60d-median turnover (liquidity gate; kills penny junk)
FWD_CLIP = 0.60      # winsorize forward returns to kill uncaught split/bonus artifacts


def build_events(C, O, V, events):
    """For each earnings event: reaction (t0 close/prev close), volume ratio, LIQUIDITY-gated,
    forward returns (winsorized) from t0+1 open. t0 = first trading day >= announcement date."""
    dates = C.index
    rows = []
    vol50 = V.rolling(50, min_periods=20).mean()
    turn60 = (C * V).rolling(60, min_periods=30).median()   # liquidity
    for sym, grp in events.groupby("symbol"):
        if sym not in C.columns:
            continue
        c = C[sym]; o = O[sym]; vr = (V[sym] / vol50[sym]); tu = turn60[sym]
        for ann in grp["date"]:
            pos = dates.searchsorted(ann)
            if pos <= 60 or pos >= len(dates) - 65:
                continue
            if not (np.isfinite(tu.iloc[pos]) and tu.iloc[pos] >= LIQ_MIN):
                continue                             # LIQUIDITY GATE
            react = c.iloc[pos] / c.iloc[pos - 1] - 1
            vspike = vr.iloc[pos]
            entry = o.iloc[pos + 1]
            if not (np.isfinite(react) and np.isfinite(vspike) and np.isfinite(entry) and entry > 0):
                continue
            fwd = {}
            for h in (5, 20, 40, 60):
                px = c.iloc[pos + 1 + h] if pos + 1 + h < len(dates) else np.nan
                fwd[h] = np.clip(px / entry - 1, -FWD_CLIP, FWD_CLIP) if np.isfinite(px) else np.nan
            rows.append({"symbol": sym, "t0": dates[pos], "entry_idx": pos + 1,
                         "react": react, "vspike": vspike, **{f"f{h}": fwd[h] for h in (5, 20, 40, 60)}})
    return pd.DataFrame(rows)


def event_study(ev):
    print("\n=== PEAD event-study: forward return by earnings-day reaction bucket ===")
    ev = ev.copy()
    ev["bucket"] = pd.cut(ev["react"], [-1, -0.05, -0.02, 0.02, 0.05, 1],
                          labels=["<-5%", "-5..-2", "-2..2", "2..5", ">5%"])
    g = ev.groupby("bucket", observed=True).agg(
        n=("react", "size"),
        f20_med=("f20", "median"), f40_med=("f40", "median"), f60_med=("f60", "median"),
        f40_mean=("f40", "mean"))
    fmt = {c: "{:+.2%}".format for c in ["f20_med", "f40_med", "f60_med", "f40_mean"]}
    print(g.to_string(formatters=fmt))
    print("MEDIAN forward returns (robust). PEAD = monotonic positive drift across reaction buckets.")


def ep_portfolio(C, ev, react_min=0.05, vspike_min=2.0, hold=40, label=""):
    """Buy each EP-qualifying event at entry, hold `hold` days; equal-weight active positions."""
    dates = C.index
    r = C.pct_change().clip(-RET_CLIP, RET_CLIP)
    q = ev[(ev["react"] >= react_min) & (ev["vspike"] >= vspike_min)].copy()
    # daily portfolio return = mean of active positions' daily returns; cost on entry+exit
    active = {}   # symbol -> exit_idx
    daily = pd.Series(0.0, index=dates)
    entries_by_idx = {}
    for _, row in q.iterrows():
        entries_by_idx.setdefault(row["entry_idx"], []).append(row["symbol"])
    n_trades = 0
    for i in range(len(dates)):
        # open new
        for sym in entries_by_idx.get(i, []):
            if sym not in active:
                active[sym] = i + hold
                n_trades += 1
        if active:
            syms = [s for s in active if s in C.columns]
            if syms and i > 0:
                day_ret = r[syms].iloc[i].mean()
                daily.iloc[i] += day_ret if np.isfinite(day_ret) else 0.0
        # cost: rough — apply COST_RT/hold per active name per day (amortized round trip)
        if active:
            daily.iloc[i] -= (COST_RT / hold) * (len(active) / max(len(active), 1))
        # close expired
        for sym in [s for s, xi in active.items() if xi <= i]:
            del active[sym]
    b = daily[daily.index.date <= SPLIT]; f = daily[daily.index.date > SPLIT]

    def m(x):
        x = x.dropna()
        if len(x) < 30 or x.std() == 0:
            return (0, 0, 0)
        eq = (1 + x).cumprod()
        return (x.mean()/x.std()*np.sqrt(252), eq.iloc[-1]**(252/len(x))-1, (eq/eq.cummax()-1).min())
    sb, cb, ddb = m(b); sf, cf, ddf = m(f)
    print(f"  EP {label:22s}: trades={n_trades:4d} | BUILD Sharpe {sb:5.2f} CAGR {cb:+6.1%} DD {ddb:4.0%} "
          f"| FWD Sharpe {sf:5.2f} CAGR {cf:+6.1%} DD {ddf:4.0%}")
    return daily


if __name__ == "__main__":
    print("[load] panel + events...")
    C, O, V = load_panel()
    ev = build_events(C, O, V, load_events(set(C.columns)))
    print(f"[events] {len(ev):,} usable earnings events {ev['t0'].min().date()}..{ev['t0'].max().date()}")
    event_study(ev)
    print("\n=== EPISODIC PIVOT portfolios (buy earnings gap-up + volume, hold N days) ===")
    for rm, vs, h in [(0.05, 2.0, 40), (0.08, 3.0, 40), (0.05, 2.0, 20), (0.10, 3.0, 60)]:
        ep_portfolio(C, ev, rm, vs, h, f"react>={rm:.0%} vsp>={vs:g} hold{h}")
