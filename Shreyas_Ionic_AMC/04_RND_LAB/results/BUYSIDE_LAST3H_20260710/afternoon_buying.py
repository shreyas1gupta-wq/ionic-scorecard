"""LAST-3-HOURS 0DTE OPTION BUYING (expiry days, entries only >=12:30). Attempt #17 at the
killed buying family - justified ONLY because afternoon premiums are ~5-10x smaller (cheap gamma).
PRE-REGISTERED (FROZEN): entries 12:30-14:45, one position at a time, max 2/day. Exits: 50%
premium SL (next-close fill) else settle 15:25. Costs 1% slip + 0.2% + Rs20/order per fill.
PASS bar per trigger: net>0 AND day-t>=2 AND PF>=1.2, n>=60. Ledger +5.
TRIGGERS (each independent):
  B1 sigma-momentum: 15-min spot return > 1.0 x rolling-sigma(15-min rets, same day so far,
     min 12 obs) -> buy ATM CE if up / PE if down. Variant B1tp: same + 100% take-profit.
  B2 range-break: first post-12:30 break of the 09:15-12:30 day range -> buy ATM in break direction.
  B3 cheap-straddle: at 13:00, ATM straddle premium as % of spot in BOTTOM quintile of its own
     history (same-minute, trailing 60 expiries) AND day range so far < 0.6% -> buy BOTH legs,
     hold to settle (no SL; the premium IS the risk), betting on late expansion.
  B4 air-pocket: spot crosses a LOW-OI strike (bottom-half 3-bar-lagged OI in +/-1.5% band,
     per T6 method) after 12:30 -> buy ATM in crossing direction.
NO COVID in sample. Everything else = same engine as final_three."""
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
mapping, exps = pq_map, _ = None, None
mapping, exps = chain.build_expiry_index()
END = dt.time(15, 25)
def fee(px): return 0.012 * px + 0.267

strad_hist = {}   # minute -> list of past premium% (for B3 trailing quintile)
rows = []
for exp in exps:
    day = exp
    bars = spot[sd == day]
    if len(bars) < 200:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "open_interest", "trading_day"]).to_pandas()
    except Exception:
        continue
    df = df[df["trading_day"] == str(day)]
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
    def buy(t0, k, cp, sl, tp=None):
        s = leg(k, cp)
        if t0 not in s.index: return None
        e = s.loc[t0]
        if e <= 1: return None
        win = s[(s.index > t0) & (s.index.time <= END)]
        if not len(win): return None
        for i, (t, v) in enumerate(win.items()):
            hit_sl = v <= e * (1 - sl)
            hit_tp = tp is not None and v >= e * (1 + tp)
            if hit_sl or hit_tp:
                rest = win.iloc[i + 1:]
                xp = rest.iloc[0] if len(rest) else v
                return (xp - e) - fee(e) - fee(xp), e
        xp = win.iloc[-1]
        return (xp - e) - fee(e) - fee(xp), e
    c = bars["close"]
    afternoon = c[(c.index.time >= dt.time(12, 30)) & (c.index.time <= dt.time(14, 45))]
    atm_at = lambda t: round(c.asof(t) / 50) * 50
    # --- B1 sigma momentum ---
    r15 = c.pct_change(15)
    for variant, tp in (("B1", None), ("B1tp", 1.00)):
        n_done = 0
        t_iter = afternoon.index
        for t in t_iter:
            if n_done >= 2: break
            hist = r15[(r15.index.date == day) & (r15.index < t)].dropna()
            if len(hist) < 12: continue
            sig = hist.std()
            v = r15.asof(t)
            if pd.isna(v) or sig == 0 or abs(v) < 1.0 * sig or abs(v) < 0.0015: continue
            cp = "CE" if v > 0 else "PE"
            res = buy(t, atm_at(t), cp, 0.50, tp)
            if res:
                rows.append(dict(trigger=variant, day=str(day), net=res[0], prem=res[1])); n_done += 1
    # --- B2 range break ---
    pre = c[c.index.time < dt.time(12, 30)]
    if len(pre) > 50:
        hi, lo = pre.max(), pre.min()
        brk = afternoon[(afternoon > hi) | (afternoon < lo)]
        if len(brk):
            t = brk.index[0]
            cp = "CE" if brk.iloc[0] > hi else "PE"
            res = buy(t, atm_at(t), cp, 0.50)
            if res: rows.append(dict(trigger="B2", day=str(day), net=res[0], prem=res[1]))
    # --- B3 cheap straddle at 13:00 ---
    t13 = c[c.index.time >= dt.time(13, 0)]
    if len(t13):
        t = t13.index[0]
        k = atm_at(t)
        sCE, sPE = leg(k, "CE"), leg(k, "PE")
        if t in sCE.index and t in sPE.index:
            prem_pct = (sCE.loc[t] + sPE.loc[t]) / c.asof(t) * 100
            histq = strad_hist.setdefault("13:00", [])
            rng_pct = (pre.max() - pre.min()) / c.asof(t) * 100 if len(pre) else 9
            if len(histq) >= 60 and prem_pct <= np.quantile(histq[-60:], 0.20) and rng_pct < 0.6:
                pnl = 0.0; okb = True
                for cp, s in (("CE", sCE), ("PE", sPE)):
                    e = s.loc[t]
                    win = s[(s.index > t) & (s.index.time <= END)]
                    if not len(win): okb = False; break
                    xp = win.iloc[-1]
                    pnl += (xp - e) - fee(e) - fee(xp)
                if okb:
                    rows.append(dict(trigger="B3", day=str(day), net=pnl, prem=prem_pct))
            histq.append(prem_pct)
    # --- B4 air pocket ---
    oi = df[df.ts.dt.time <= dt.time(12, 27)].sort_values("ts").groupby(["strike", "option_type"])["open_interest"].last()
    t_iter = afternoon.index
    done = 0
    for t in t_iter:
        if done >= 1: break
        S = c.asof(t)
        band = [k for (k, cp) in oi.index if abs(k - S) / S <= 0.015 and cp == "CE"]
        if len(band) < 4: continue
        tot = {k: oi.get((k, "CE"), 0) + oi.get((k, "PE"), 0) for k in band}
        med = np.median(list(tot.values()))
        prev = c.asof(t - pd.Timedelta(minutes=1))
        for k in band:
            if tot[k] < med and min(prev, S) < k <= max(prev, S):
                cp = "CE" if S > prev else "PE"
                res = buy(t, atm_at(t), cp, 0.50)
                if res:
                    rows.append(dict(trigger="B4", day=str(day), net=res[0], prem=res[1])); done = 1
                break

df = pd.DataFrame(rows)
df.to_csv(OUT / "afternoon_trades.csv", index=False)
lines = ["# Last-3h 0DTE buying triggers (frozen bars: net>0, t>=2, PF>=1.2, n>=60)"]
for tr, g in df.groupby("trigger"):
    daily = g.groupby("day")["net"].sum()
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if len(daily) > 2 else np.nan
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    era = {e2: gg.net.mean() for e2, gg in g.groupby(g.day < "2024-01-01")}
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2) else "KILL") if len(g) >= 60 else "INSUFF"
    lines.append(f"{tr}: n={len(g)} ({len(daily)} days) net={g.net.mean():+.2f} pts avg_prem={g.prem.mean():.1f} | "
                 f"t={t:.2f} PF={pf:.2f} win={len(w)/len(g)*100:.0f}% | era21-23={era.get(True, np.nan):+.2f} "
                 f"era24-26={era.get(False, np.nan):+.2f} | best5={daily.nlargest(5).round(0).to_dict()} | **{verdict}**")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
