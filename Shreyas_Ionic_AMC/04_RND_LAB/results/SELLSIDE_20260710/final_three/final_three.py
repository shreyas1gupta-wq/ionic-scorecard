"""FINAL THREE (registration candidates) under upgraded realistic costs. One data pass.
  A) S1  : 0DTE ATM straddle @09:20, 30% per-leg SL
  B) S1b : 0DTE ATM-50 straddle @09:20, 30% per-leg SL (challenger)
  C) V2  : 0DTE +-50 strangle @09:20, 35% per-leg SL + on-breach ITM-long defense (25% SL)
COSTS per fill (entry & exit, per leg): slippage 1.0% of traded premium (Principal spec)
  + statutory 0.20% of premium (STT sell-side 0.1% + exchange 0.035% + SEBI/stamp + GST, rounded up)
  + brokerage Rs20/order = 0.267 pts/lot(75). SL fills at NEXT 1-min close after breach.
Settle 15:25 last print. Frozen bars unchanged (net>0, t>=2, PF>=1.2, conc<30%).
NO COVID in sample (2021-06..2026-06)."""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
mapping, exps = chain.build_expiry_index()
END = dt.time(15, 25)

def fee(px):
    return 0.012 * px + 0.267   # 1% slip + 0.2% statutory + Rs20/order at lot 75

def short_leg(series, t0, sl):
    """short from t0 with SL mult; returns pnl net of fees, plus (breach, fill_ts)."""
    e = series.loc[t0]
    win = series[(series.index > t0) & (series.index.time <= END)]
    if not len(win):
        return None
    br = win[win >= e * (1 + sl)]
    if len(br):
        after = win[win.index > br.index[0]]
        xt, xp = (after.index[0], after.iloc[0]) if len(after) else (br.index[0], br.iloc[0])
        return (e - xp) - fee(e) - fee(xp), True, xt
    xp = win.iloc[-1]
    return (e - xp) - fee(e) - fee(xp), False, None

def long_leg(series, t0, sl):
    e = series.loc[t0]
    win = series[(series.index > t0) & (series.index.time <= END)]
    if not len(win):
        return 0.0
    br = win[win <= e * (1 - sl)]
    if len(br):
        after = win[win.index > br.index[0]]
        xp = after.iloc[0] if len(after) else br.iloc[0]
    else:
        xp = win.iloc[-1]
    return (xp - e) - fee(e) - fee(xp)

rows = []
for exp in exps:
    day = exp
    s1d = spot[sd == day]
    if len(s1d) < 100:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
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
    cand = s1d[s1d.index.time >= dt.time(9, 20)]
    if not len(cand):
        continue
    t0 = cand.index[0]
    atm = round(s1d["close"].loc[t0] / 50) * 50
    # A: ATM straddle 30
    for name, k0, off in (("S1", atm, 0), ("S1b", atm - 50, 0)):
        L = {"CE": leg(k0, "CE"), "PE": leg(k0, "PE")}
        if any(t0 not in L[c].index for c in L):
            continue
        pnl = 0.0; ok = True
        for c in L:
            r = short_leg(L[c], t0, 0.30)
            if r is None: ok = False; break
            pnl += r[0]
        if ok:
            rows.append(dict(strat=name, day=str(day), net=pnl))
    # C: V2
    LS = {"CE": leg(atm + 50, "CE"), "PE": leg(atm - 50, "PE")}
    if all(t0 in LS[c].index for c in LS):
        pnl = 0.0; ok = True
        for c in LS:
            r = short_leg(LS[c], t0, 0.35)
            if r is None: ok = False; break
            pnl += r[0]
            if r[1]:
                xt = r[2]
                spx = s1d["close"].asof(xt)
                if pd.isna(spx):
                    continue
                k0 = round(spx / 50) * 50
                k_itm = k0 - 50 if c == "CE" else k0 + 50
                li = leg(k_itm, c)
                if xt in li.index:
                    pnl += long_leg(li, xt, 0.25)
        if ok:
            rows.append(dict(strat="V2", day=str(day), net=pnl))

df = pd.DataFrame(rows)
df.to_csv(OUT / "final_three_trades.csv", index=False)
LOT = 75
lines = ["# FINAL THREE under 1% slippage + statutory TC + brokerage (frozen bars unchanged)"]
series = {}
for st, g in df.groupby("strat"):
    g = g.sort_values("day")
    daily = g.set_index("day")["net"]
    series[st] = daily
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily)))
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    cum = daily.cumsum(); dd = (cum - cum.cummax()).min()
    conc = daily.max() / daily[daily > 0].sum() * 100 if daily.sum() > 0 else np.nan
    era = {e2: gg.net.mean() for e2, gg in g.groupby(g.day < "2024-01-01")}
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2 and conc < 30) else "KILL") if len(g) >= 60 else "INSUFF"
    rupees = daily.sum() * LOT
    lines.append(f"{st}: n={len(g)} net={g.net.mean():+.2f} pts/day | t={t:.2f} PF={pf:.2f} win={len(w)/len(g)*100:.0f}% "
                 f"| maxDD={dd:.0f}pts conc={conc:.0f}% | era21-23={era.get(True, np.nan):+.2f} era24-26={era.get(False, np.nan):+.2f} "
                 f"| total 1-lot P&L=Rs {rupees:,.0f} | worst5={daily.nsmallest(5).round(1).to_dict()} | **{verdict}**")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")

INK, BLUE, AQUA, YELLOW, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#1baf7a", "#eda100", "#e1e0d9", "#898781", "#fcfcfb"
fig, ax = plt.subplots(figsize=(11, 4.8), dpi=150)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for (st, col) in (("S1", BLUE), ("S1b", AQUA), ("V2", YELLOW)):
    if st not in series: continue
    daily = series[st]
    x = pd.to_datetime(daily.index)
    y = daily.cumsum() * LOT / 1e5
    ax.plot(x, y, color=col, lw=2, label=st)
    ax.annotate(f"{st} {y.iloc[-1]:+.2f}L", (x[-1], y.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", fontsize=8.5, color=INK, va="center")
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_title("Final three — cumulative P&L per 1 lot (Rs lakh), net of 1% slippage + all TC, 2021-26",
             fontsize=10.5, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8, frameon=False, loc="upper left")
for sp in ax.spines.values(): sp.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "FINAL_THREE_PNL.png", facecolor=SURF, bbox_inches="tight")
print("saved ->", OUT)
