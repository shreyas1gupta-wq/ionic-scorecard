"""SELLSIDE_20260710/hedged: defined-risk (hedged) selling. PRE-REGISTERED (FROZEN):
  H1 0DTE IRON FLY: S1-primary shorts (ATM straddle @09:20 1-min close, 30% per-leg SL,
     SL fill = next close after breach) + BUY wings at round-50(spot*(1+/-1.5%)) @09:20,
     wings HELD TO SETTLE (15:25 last print). Day skipped if any of 4 legs has no 09:20 print.
  H2 WEEKLY IRON CONDOR: S2-weekly shorts (premium-target 0.30% of spot per side, 4-6 DTE,
     09:30) + wings = strike strictly further OTM minimizing |prem - 0.10% spot|, all legs held
     to expiry settle. Variant tp50: close all 4 legs at first 15:20 mark where combined SHORT
     premium <= 50% of collected.
  H3 BIWEEKLY IRON CONDOR: H2 at 9-13 DTE, hold-to-settle only.
  Costs: 1.0 pt one-way PER LEG (2x pre-09:30). PASS bar per cell: net>0 @BASE AND day-clustered
  t>=2 AND PF>=1.2 AND max-day <30% of profits; n<60 INSUFFICIENT. Tail comparison vs unhedged
  S1/S2 required in output. ROM approx: fly/condor margin ~Rs 50k/lot (labeled approx).
  NO COVID in sample (2021-06..2026-06)."""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/hedged"
OUT.mkdir(parents=True, exist_ok=True)
spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
spot_dates = pd.Series(spot.index.date, index=spot.index)
mapping, exps = chain.build_expiry_index()

def lc(ts): return 2.0 if ts.time() < dt.time(9, 30) else 1.0

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

def sl_exit(series, t0, entry, sl_mult, t_end=dt.time(15, 25)):
    win = series[(series.index > t0) & (series.index.time <= t_end)]
    if sl_mult is not None and len(win):
        br = win[win >= entry * (1 + sl_mult)]
        if len(br):
            after = win[win.index > br.index[0]]
            return (after.index[0], after.iloc[0]) if len(after) else (br.index[0], br.iloc[0])
    return (win.index[-1], win.iloc[-1]) if len(win) else (None, None)

rows = []
# ---- H1 0DTE iron fly ----
for exp in exps:
    s1d = spot[spot_dates == exp]
    if len(s1d) < 100: continue
    df = load_exp(exp, exp)
    if df is None or not len(df): continue
    cand = s1d[s1d.index.time >= dt.time(9, 20)]
    if not len(cand): continue
    t0 = cand.index[0]; spx = s1d["close"].loc[t0]
    K = round(spx / 50) * 50
    KwC = round(spx * 1.015 / 50) * 50; KwP = round(spx * 0.985 / 50) * 50
    legs = {("s", "CE"): leg_series(df, K, "CE"), ("s", "PE"): leg_series(df, K, "PE"),
            ("w", "CE"): leg_series(df, KwC, "CE"), ("w", "PE"): leg_series(df, KwP, "PE")}
    if any(t0 not in s.index for s in legs.values()): continue
    net = 0.0; ok = True
    for cp in ("CE", "PE"):
        e = legs[("s", cp)].loc[t0]
        xt, xp = sl_exit(legs[("s", cp)], t0, e, 0.30)
        if xt is None: ok = False; break
        net += (e - xp) - lc(t0) - lc(xt)
    for cp in ("CE", "PE"):
        s = legs[("w", cp)]
        e = s.loc[t0]
        w = s[s.index.time <= dt.time(15, 25)]
        net += (w.iloc[-1] - e) - lc(t0) - 1.0
    if ok:
        rows.append(dict(cell="H1_0dte_ironfly", day=str(exp), net=net, net_stress=net - 8.0))

# ---- H2/H3 condors ----
for exp in exps:
    df = load_exp(exp)
    if df is None or not len(df): continue
    days = sorted(df["trading_day"].unique())
    for tag, lo, hi in [("H2_weekly", 4, 6), ("H3_biweekly", 9, 13)]:
        eday = next((d for d in days if lo <= (exp - dt.date.fromisoformat(d)).days <= hi), None)
        if eday is None: continue
        dd = df[df.trading_day == eday]
        t0s = dd[dd.ts.dt.time >= dt.time(9, 30)]["ts"]
        if not len(t0s): continue
        t0 = t0s.min()
        try:
            spx = spot.loc[spot[(spot_dates == dt.date.fromisoformat(eday))
                                & (spot.index >= t0)].index[0], "close"]
        except Exception:
            continue
        snap = dd[dd.ts == t0].set_index(["strike", "option_type"])["close"]
        def pick(cp, side, tgt, beyond=None):
            c = [(abs(v - tgt), k) for (k, o), v in snap.items() if o == cp and v > 0.5
                 and (k - spx) * side >= 0 and (beyond is None or (k - beyond) * side > 0)]
            return min(c)[1] if c else None
        ksC = pick("CE", 1, 0.003 * spx); ksP = pick("PE", -1, 0.003 * spx)
        if ksC is None or ksP is None: continue
        kwC = pick("CE", 1, 0.001 * spx, beyond=ksC); kwP = pick("PE", -1, 0.001 * spx, beyond=ksP)
        if kwC is None or kwP is None: continue
        sub = df[df.trading_day >= eday]
        L = {("s", "CE"): leg_series(sub, ksC, "CE"), ("s", "PE"): leg_series(sub, ksP, "PE"),
             ("w", "CE"): leg_series(sub, kwC, "CE"), ("w", "PE"): leg_series(sub, kwP, "PE")}
        if any(t0 not in s.index for s in L.values()): continue
        e = {k: s.loc[t0] for k, s in L.items()}
        settle = {k: s[s.index.time <= dt.time(15, 25)].iloc[-1] for k, s in L.items()}
        net = sum(e[("s", cp)] - settle[("s", cp)] - 2.0 for cp in ("CE", "PE")) + \
              sum(settle[("w", cp)] - e[("w", cp)] - 2.0 for cp in ("CE", "PE"))
        rows.append(dict(cell=f"{tag}_hold", day=eday, net=net, net_stress=net - 8.0))
        if tag == "H2_weekly":
            coll = e[("s", "CE")] + e[("s", "PE")]
            def dm(key):
                s = L[key][L[key].index.time <= dt.time(15, 20)]
                return s.groupby(s.index.date).last()
            m = {k: dm(k) for k in L}
            common = sorted(set.intersection(*[set(v.index) for v in m.values()]))
            netv = None
            for d2 in common:
                if d2 <= dt.date.fromisoformat(eday): continue
                if m[("s", "CE")][d2] + m[("s", "PE")][d2] <= 0.5 * coll:
                    netv = sum(e[("s", cp)] - m[("s", cp)][d2] - 2.0 for cp in ("CE", "PE")) + \
                           sum(m[("w", cp)][d2] - e[("w", cp)] - 2.0 for cp in ("CE", "PE"))
                    break
            rows.append(dict(cell="H2_weekly_tp50", day=eday, net=netv if netv is not None else net,
                             net_stress=(netv if netv is not None else net) - 8.0))

df = pd.DataFrame(rows)
df.to_csv(OUT / "hedged_trades.csv", index=False)
lines = ["# Hedged selling (iron fly / condors) vs frozen bars — NO COVID in sample",
         "Unhedged references: S1 09:20/30 = +8.02 pts t=2.94 PF1.56 maxDD-231 worst-102 | S2 weekly/hold = +7.03 t=0.67 maxDD-2350 worst-654"]
for cell, g in df.groupby("cell"):
    daily = g.groupby("day")["net"].sum()
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if len(daily) > 2 else np.nan
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    cum = daily.sort_index().cumsum(); dd = (cum - cum.cummax()).min()
    conc = daily.max() / daily[daily > 0].sum() * 100 if daily.sum() > 0 and (daily > 0).any() else np.nan
    era = {e2: gg.net.mean() for e2, gg in g.groupby(g.day < "2024-01-01")}
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2 and (np.isnan(conc) or conc < 30))
               else "KILL") if len(g) >= 60 else "INSUFF"
    rom = g.net.mean() * 75 / 50000 * 100
    lines.append(f"{cell}: n={len(g)} net={g.net.mean():+.2f} stress={g.net_stress.mean():+.2f} | "
                 f"t={t:.2f} PF={pf:.2f} win={len(w)/len(g)*100:.0f}% | maxDD={dd:.0f} conc={conc:.0f}% | "
                 f"era21-23={era.get(True, np.nan):+.2f} era24-26={era.get(False, np.nan):+.2f} | "
                 f"ROM/trade~{rom:+.2f}% (50k margin) | worst5={daily.nsmallest(5).round(1).to_dict()} | **{verdict}**")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
