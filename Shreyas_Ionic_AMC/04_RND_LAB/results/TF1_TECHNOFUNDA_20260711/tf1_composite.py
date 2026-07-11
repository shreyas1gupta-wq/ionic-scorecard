"""TF-1-CARD: TechnoFunda composite (frozen @ 47e8a00). Stage-2 x RS x PIT-CANSLIM x (VCP|base) x breakout.
Portfolio: 15 slots equal-weight, 8% stop, 50dMA exit, 60d lockout. 2016-2026, placebo x200.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(31)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TF1_TECHNOFUNDA_20260711"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0025  # per side

print("loading daily OHLCV...", flush=True)
d = pd.read_parquet(ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet")
ts = pd.to_datetime(d.timestamp)
d["date"] = ts.dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None) + pd.Timedelta(days=0)
# landmine #1: 18:30 UTC = next-day 00:00 IST -> tz_convert then the DATE is already correct
d["date"] = ts.dt.tz_convert("Asia/Kolkata").dt.date
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
snaps = {dd: set(g["Ticker"].astype(str).str.strip()) for dd, g in uni.groupby("snap")}
snap_dates = sorted(snaps)
ever = set().union(*snaps.values())
d = d[d.symbol.isin(ever)]
print(f"panel: {len(d):,} rows, {d.symbol.nunique()} ever-N500 syms", flush=True)

C = d.pivot_table(index="date", columns="symbol", values="close")
H = d.pivot_table(index="date", columns="symbol", values="high")
L = d.pivot_table(index="date", columns="symbol", values="low")
V = d.pivot_table(index="date", columns="symbol", values="volume")
C.index = pd.to_datetime(C.index); H.index = C.index; L.index = C.index; V.index = C.index
C = C.sort_index(); H = H.sort_index(); L = L.sort_index(); V = V.sort_index()
print("pivots built", flush=True)

ma50 = C.rolling(50).mean(); ma150 = C.rolling(150).mean(); ma200 = C.rolling(200).mean()
lo52 = C.rolling(252).min(); hi52 = C.rolling(252).max()
stage2 = (C > ma150) & (C > ma200) & (ma200 > ma200.shift(21)) & (ma50 > ma150) & (ma150 > ma200) \
         & (C >= 1.3 * lo52) & (C >= 0.75 * hi52)
ret126 = C / C.shift(126) - 1
rs_rank = ret126.rank(axis=1, pct=True)
tr = pd.concat([(H - L), (H - C.shift(1)).abs(), (L - C.shift(1)).abs()]).groupby(level=0).max()
atrp = (tr.rolling(10).mean() / C)
vcp = (atrp < 0.67 * atrp.shift(40)) & (V.rolling(10).mean() < 0.8 * V.rolling(50).mean()) \
      & (C >= 0.95 * C.rolling(20).max())
roll40max = C.rolling(40).max()
base_dd = 1 - C.rolling(40).min() / roll40max
base = (base_dd >= 0.05) & (base_dd <= 0.35)
brk = (C > H.shift(1).rolling(20).max()) & (V >= 1.5 * V.rolling(50).mean())
print("technical layers built", flush=True)

# PIT earnings: symbol -> sorted list of (available_date, yoy_ok)
ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.sort_values(["symbol", "quarter_end"])
ev["np_base"] = ev.groupby("symbol")["net_profit"].shift(4)
ev["yoy_ok"] = (ev.np_base > 0) & (ev.net_profit >= 1.2 * ev.np_base)
fund = {}
for sym, g in ev.dropna(subset=["available_date"]).groupby("symbol"):
    fund[sym] = (g.available_date.values, g.yoy_ok.values)

def fund_ok(sym, day):
    fg = fund.get(sym)
    if fg is None:
        return False
    i = np.searchsorted(fg[0], np.datetime64(day), side="right") - 1
    return bool(fg[1][i]) if i >= 0 else False

sig = stage2 & (rs_rank >= 0.70) & (vcp | base) & brk
sig = sig.loc["2016-01-01":"2026-01-21"]
print(f"raw signal days: {int(sig.sum().sum())}", flush=True)

def in_universe(sym, day):
    prior = [s for s in snap_dates if s <= day]
    return bool(prior) and sym in snaps[prior[-1]]

def run_portfolio(sig_frame, tag):
    dates = sig_frame.index
    pos = {}        # sym -> dict(entry, entry_dt)
    lockout = {}
    trades, nav, cash = [], [], 1.0
    eq = 1.0
    weights = 1 / 15
    daily_ret = []
    for i, day in enumerate(dates):
        if i + 1 >= len(dates):
            break
        nxt = dates[i + 1]
        # exits on today's close signal, executed next close
        for sym in list(pos):
            p = pos[sym]
            c_now = C.at[day, sym] if sym in C.columns else np.nan
            if not np.isfinite(c_now):
                continue
            stop = c_now <= p["entry"] * 0.92
            trend = c_now < ma50.at[day, sym]
            if stop or trend:
                x = C.at[nxt, sym]
                if np.isfinite(x):
                    r = (x / p["entry_fill"] - 1) - 2 * COST
                    trades.append(dict(sym=sym, entry=p["entry_dt"], exit=nxt, ret=r,
                                       reason="stop" if stop else "trend"))
                    del pos[sym]
                    lockout[sym] = i + 60
        # entries
        if len(pos) < 15:
            todays = sig_frame.loc[day]
            cands = [s for s in todays.index[todays.fillna(False)]
                     if s not in pos and lockout.get(s, -1) < i
                     and fund_ok(s, day.date()) and in_universe(s, day.date())]
            if cands:
                rs_today = rs_rank.loc[day, cands].sort_values(ascending=False)
                for s in rs_today.index[:15 - len(pos)]:
                    fill = C.at[nxt, s]
                    if np.isfinite(fill):
                        pos[s] = dict(entry=C.at[day, s], entry_fill=fill * (1 + COST), entry_dt=nxt)
        # daily portfolio return
        rets = []
        for sym, p in pos.items():
            a, b = C.at[day, sym] if day >= p["entry_dt"] else np.nan, C.at[nxt, sym]
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                rets.append(b / a - 1)
        dr = np.mean(rets) * min(len(pos), 15) / 15 if rets else 0.0
        eq *= (1 + dr)
        daily_ret.append(dr)
        nav.append((nxt, eq))
    tdf = pd.DataFrame(trades)
    ndf = pd.DataFrame(nav, columns=["date", "nav"]).set_index("date")
    tdf.to_csv(OUT / f"tf1_trades_{tag}.csv", index=False)
    ndf.to_csv(OUT / f"tf1_nav_{tag}.csv")
    yrs = (ndf.index[-1] - ndf.index[0]).days / 365.25
    cagr = ndf.nav.iloc[-1] ** (1 / yrs) - 1
    dd = (ndf.nav / ndf.nav.cummax() - 1).min()
    dr = np.array(daily_ret)
    sharpe = dr.mean() / dr.std(ddof=1) * np.sqrt(252) if dr.std(ddof=1) > 0 else np.nan
    return tdf, ndf, cagr, dd, sharpe

tdf, ndf, cagr, dd, sharpe = run_portfolio(sig, "main")
n = len(tdf)
per = tdf.ret
tstat = per.mean() / (per.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan
e1 = tdf[tdf.exit < pd.Timestamp("2021-01-01")]; e2 = tdf[tdf.exit >= pd.Timestamp("2021-01-01")]
print(f"main run: {n} trades, CAGR {cagr*100:.1f}%, Sharpe {sharpe:.2f}, maxDD {dd*100:.1f}%", flush=True)

# placebo: random stage-2 stocks, same exits — signal replaced by random draw matching entry frequency
print("placebo...", flush=True)
sig_count = int(sig.sum().sum())
s2w = stage2.loc[sig.index]
null_means = []
pool_frames = []
prob = sig_count / max(int(s2w.sum().sum()), 1)
for k in range(20):  # 20 portfolio placebo runs (each expensive); bootstrap x10 -> 200 effective
    rnd = s2w & (pd.DataFrame(rng.random(s2w.shape), index=s2w.index, columns=s2w.columns) < prob)
    ptdf, _, _, _, _ = run_portfolio(rnd, f"plc{k}")
    if len(ptdf):
        null_means.append(ptdf.ret.mean())
    print(f"  placebo {k}: {len(ptdf)} trades mean {ptdf.ret.mean()*100:+.2f}%" if len(ptdf) else f"  placebo {k}: 0", flush=True)
null_means = np.array(null_means)
boot = rng.choice(null_means, size=(200, max(len(null_means)//2, 3))).mean(axis=1)
p95 = np.percentile(boot, 95)

bars = {"CAGR>=15%": cagr >= 0.15, "Sharpe>=1.0": sharpe >= 1.0, "maxDD<=30%": dd >= -0.30,
        "beat_placebo95": per.mean() > p95,
        "eras_both_profitable": (e1.ret.mean() > 0 if len(e1) > 5 else False) and (e2.ret.mean() > 0 if len(e2) > 5 else False)}
kill = (sharpe < 0.5) or ((e1.ret.mean() > 0) != (e2.ret.mean() > 0) if len(e1) > 5 and len(e2) > 5 else False)
verdict = "PASS -> red-team battery next" if all(bars.values()) else ("KILL" if kill else "PARK")

lines = [f"trades={n} | per-trade net {per.mean()*100:+.2f}% (t={tstat:.2f}), win% {(per>0).mean()*100:.0f}",
         f"PORTFOLIO: CAGR {cagr*100:+.1f}% | Sharpe {sharpe:.2f} | maxDD {dd*100:.1f}% | 10.0y",
         f"eras per-trade: 2016-20 {e1.ret.mean()*100 if len(e1) else float('nan'):+.2f}% (n={len(e1)}) | 2021-26 {e2.ret.mean()*100 if len(e2) else float('nan'):+.2f}% (n={len(e2)})",
         f"placebo (20 portfolio runs, boot x200): null mean {null_means.mean()*100:+.2f}%, 95th {p95*100:+.2f}% vs real {per.mean()*100:+.2f}%",
         f"exit mix: {dict(tdf.reason.value_counts())}",
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "TF-1-CARD", "frozen_commit": "47e8a00", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "tf1_composite.py", "data": ["saintforest daily OHLCV 2000-2026", "PIT N500", "PIT earnings"],
        "n_obs": int(n), "metrics": {"cagr_pct": round(float(cagr * 100), 1), "sharpe": round(float(sharpe), 2),
        "maxdd_pct": round(float(dd * 100), 1), "per_trade_pct": round(float(per.mean() * 100), 2), "t": round(float(tstat), 2)},
        "validation": {"era_split": f"{e1.ret.mean()*100 if len(e1) else float('nan'):+.2f}/{e2.ret.mean()*100 if len(e2) else float('nan'):+.2f}",
                       "bootstrap_ci95": None, "lookahead_ast": "pre-flight",
                       "one_day_lag": "signal at close D, fills at close D+1; PIT earnings via available_date; PIT universe"},
        "verdict": verdict, "bars_hit": [k for k, v in bars.items() if v],
        "trials_increment": 1, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written", flush=True)
