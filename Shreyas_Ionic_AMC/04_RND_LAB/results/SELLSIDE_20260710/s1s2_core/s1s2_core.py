"""SELLSIDE_20260710 core: S1 (0DTE ATM short straddle + per-leg SL) and S2 (weekly premium-targeted
short strangle, seldom rebalancing). Authored directly (agents blocked by spend limit).

PRE-REGISTERED (FROZEN before run):
  S1: every derived expiry day (chain), sell ATM (round-50) CE+PE at entry-bar 1-min close.
      Per-leg SL = leg close >= (1+SL)*entry, evaluated on 1-min closes, FILLED at the NEXT
      1-min close after the breach bar (+cost); survivors settle at last print <=15:25.
      Grid (all reported): entry {09:20, 10:00} x SL {30%, 50%, none}. PRIMARY = 09:20 / 30%.
  S2: per weekly cycle, entry = first trading day with 4<=DTE<=6 in that expiry's file, at 09:30:
      sell OTM CE and PE, each = strike minimizing |premium - 0.30% of spot| (CE>=spot, PE<=spot).
      PRIMARY = hold to expiry settle, zero rebalancing. Variants: (i) exit both legs at first day
      whose 15:20 combined premium <= 50% of collected; (ii) per-leg hard stop at 15:20 close >=
      3x entry (exit that leg only); (iii) biweekly: entry first day with 9<=DTE<=13, hold to expiry.
  Costs: 1.0 pt one-way PER LEG (BASE), 2x for any leg executed before 09:30; STRESS = 2x all.
  PASS bar (each cell): net expectancy > 0 at BASE AND day-clustered t >= 2 AND PF >= 1.2 AND
      max single-day profit < 30% of total profit. Else KILL. n < 60 INSUFFICIENT.
  Honesty: worst-5-days, maxDD, era split (<2024-01-01 vs >=), weekday split (S1 primary),
      2024-06-04 broken out, NO-COVID caveat (sample 2021-06..2026-06). ROM approx at lot 75,
      margin ~Rs 1.2L/side-pair.
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1s2_core"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()

def leg_cost(ts, stress=False):
    c = 2.0 if ts.time() < dt.time(9, 30) else 1.0
    return c * (2 if stress else 1)

def load_exp(exp, day=None):
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception as e:
        print(f"[skip] {exp}: {e}"); return None
    if day is not None:
        df = df[df["trading_day"] == str(day)]
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df.assign(ts=ts)

def leg_series(df, k, cp):
    s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")["close"].sort_index()
    return s[~s.index.duplicated(keep="last")]

def sl_exit(series, t0, entry, sl_mult, t_end):
    """Return (exit_ts, exit_px, hit) for a short leg."""
    win = series[(series.index > t0) & (series.index.time <= t_end)]
    if sl_mult is not None:
        breach = win[win >= entry * (1 + sl_mult)]
        if len(breach):
            after = win[win.index > breach.index[0]]
            xt = after.index[0] if len(after) else breach.index[0]
            return xt, (after.iloc[0] if len(after) else breach.iloc[0]), True
    return (win.index[-1], win.iloc[-1], False) if len(win) else (None, None, False)

# ---------------- S1 ----------------
s1_rows = []
spot_dates = pd.Series(spot.index.date, index=spot.index)
for exp in exps:
    day = exp
    s1d = spot[spot_dates == day]
    if len(s1d) < 100:
        continue
    df = load_exp(exp, day)
    if df is None or not len(df):
        continue
    for ent in ["09:20", "10:00"]:
        h, m = map(int, ent.split(":"))
        cand = s1d[s1d.index.time >= dt.time(h, m)]
        if not len(cand):
            continue
        t0 = cand.index[0]
        spx = s1d["close"].loc[t0]
        K = round(spx / 50) * 50
        legs = {cp: leg_series(df, K, cp) for cp in ("CE", "PE")}
        if any(t0 not in legs[cp].index for cp in legs):
            continue
        for sl in (0.30, 0.50, None):
            pnl_b = pnl_s = 0.0
            ok = True
            for cp in ("CE", "PE"):
                e_px = legs[cp].loc[t0]
                xt, xp, hit = sl_exit(legs[cp], t0, e_px, sl, dt.time(15, 25))
                if xt is None:
                    ok = False; break
                cb = leg_cost(t0) + leg_cost(xt)
                pnl_b += (e_px - xp) - cb
                pnl_s += (e_px - xp) - 2 * cb
            if ok:
                s1_rows.append(dict(test="S1", cell=f"{ent}/{'none' if sl is None else int(sl*100)}",
                                    day=str(day), K=K, net=pnl_b, net_stress=pnl_s))
s1 = pd.DataFrame(s1_rows)
s1.to_csv(OUT / "s1_trades.csv", index=False)

# ---------------- S2 ----------------
s2_rows = []
for exp in exps:
    df = load_exp(exp)
    if df is None or not len(df):
        continue
    days = sorted(df["trading_day"].unique())
    for tag, lo, hi in [("weekly", 4, 6), ("biweekly", 9, 13)]:
        entry_day = None
        for d in days:
            dte = (exp - dt.date.fromisoformat(d)).days
            if lo <= dte <= hi:
                entry_day = d; break
        if entry_day is None:
            continue
        dd = df[df.trading_day == entry_day]
        t0s = dd[dd.ts.dt.time >= dt.time(9, 30)]["ts"]
        if not len(t0s):
            continue
        t0 = t0s.min()
        try:
            spx = spot.loc[spot[(spot_dates == dt.date.fromisoformat(entry_day))
                                & (spot.index >= t0)].index[0], "close"]
        except Exception:
            continue
        snap = dd[dd.ts == t0].set_index(["strike", "option_type"])["close"]
        tgt = 0.003 * spx
        pick = {}
        for cp, side in (("CE", 1), ("PE", -1)):
            cands = [(abs(v - tgt), k) for (k, c), v in snap.items()
                     if c == cp and v > 0.5 and (k - spx) * side >= 0]
            if cands:
                pick[cp] = min(cands)[1]
        if len(pick) < 2:
            continue
        legs = {cp: leg_series(df[df.trading_day >= entry_day], pick[cp], cp) for cp in pick}
        entry_px = {cp: legs[cp].loc[t0] for cp in pick if t0 in legs[cp].index}
        if len(entry_px) < 2:
            continue
        # daily 15:20 marks for variants
        def day_marks(cp):
            s = legs[cp][legs[cp].index.time <= dt.time(15, 20)]
            return s.groupby(s.index.date).last()
        marks = {cp: day_marks(cp) for cp in pick}
        settle = {cp: legs[cp][legs[cp].index.time <= dt.time(15, 25)].iloc[-1] for cp in pick}
        coll = sum(entry_px.values())
        # PRIMARY hold-to-expiry
        net = sum(entry_px[cp] - settle[cp] - 2 * 1.0 for cp in pick)
        s2_rows.append(dict(test="S2", cell=f"{tag}/hold", day=entry_day, exp=str(exp),
                            net=net, net_stress=net - 4.0, coll=coll))
        if tag == "weekly":
            # variant: 50% profit exit
            common = sorted(set(marks["CE"].index) & set(marks["PE"].index))
            exit_v = None
            for d2 in common:
                if d2 <= dt.date.fromisoformat(entry_day):
                    continue
                if marks["CE"][d2] + marks["PE"][d2] <= 0.5 * coll:
                    exit_v = sum(entry_px[cp] - marks[cp][d2] - 2 * 1.0 for cp in pick)
                    break
            if exit_v is None:
                exit_v = net
            s2_rows.append(dict(test="S2", cell="weekly/tp50", day=entry_day, exp=str(exp),
                                net=exit_v, net_stress=exit_v - 4.0, coll=coll))
            # variant: 3x per-leg hard stop
            tot = 0.0
            for cp in pick:
                stopped = None
                for d2, v in marks[cp].items():
                    if d2 > dt.date.fromisoformat(entry_day) and v >= 3 * entry_px[cp]:
                        stopped = v; break
                xp = stopped if stopped is not None else settle[cp]
                tot += entry_px[cp] - xp - 2 * 1.0
            s2_rows.append(dict(test="S2", cell="weekly/stop3x", day=entry_day, exp=str(exp),
                                net=tot, net_stress=tot - 4.0, coll=coll))
s2 = pd.DataFrame(s2_rows)
s2.to_csv(OUT / "s2_trades.csv", index=False)

# ---------------- report ----------------
def stats(g, label):
    if len(g) < 5:
        return f"{label}: n={len(g)} insufficient"
    daily = g.groupby("day")["net"].sum()
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if daily.std(ddof=1) > 0 else np.nan
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    cum = daily.sort_index().cumsum()
    dd = (cum - cum.cummax()).min()
    conc = daily.max() / daily[daily > 0].sum() * 100 if (daily > 0).any() and daily.sum() > 0 else np.nan
    era = {e: gg.net.mean() for e, gg in g.groupby(g.day < "2024-01-01")}
    worst = daily.nsmallest(5).round(1).to_dict()
    el = "2024-06-04"
    elec = daily.get(el, np.nan)
    rom = g.net.mean() * 75 / 120000 * 100
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2 and
                          (np.isnan(conc) or conc < 30)) else "KILL") if len(g) >= 60 else "INSUFF"
    return (f"{label}: n={len(g)} net={g.net.mean():+.2f} stress={g.net_stress.mean():+.2f} pts | "
            f"t={t:.2f} PF={pf:.2f} win={len(w)/len(g)*100:.0f}% | maxDD={dd:.0f} conc={conc:.0f}% "
            f"| era21-23={era.get(True, np.nan):+.2f} era24-26={era.get(False, np.nan):+.2f} | "
            f"ROM/trade={rom:+.2f}% | electionday={elec} | worst5={worst} | **{verdict}**")

lines = ["# S1/S2 sell-side core results (frozen bars in script docstring; NO COVID in sample)"]
for cell, g in s1.groupby("cell"):
    lines.append(stats(g, f"S1 {cell}"))
if len(s1):
    p = s1[s1.cell == "09:20/30"]
    wd = p.assign(w=pd.to_datetime(p.day).dt.day_name()).groupby("w")["net"].agg(["mean", "count"])
    lines.append("S1 PRIMARY weekday split:\n" + wd.round(2).to_string())
for cell, g in s2.groupby("cell"):
    lines.append(stats(g, f"S2 {cell}"))
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("\nsaved ->", OUT)
