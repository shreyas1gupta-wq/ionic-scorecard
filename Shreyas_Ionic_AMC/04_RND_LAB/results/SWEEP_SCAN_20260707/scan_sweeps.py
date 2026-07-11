"""Liquidity-sweep / shakeout / candle-pattern scan on NIFTY spot 1-min (2021-2026).
Goal: find SNIPER-grade events (K-001 resurrection clause: <5 trades/mo) whose forward
spot move is fast+large enough to fund option BUYING after costs.
Method: signals on COMPLETED 5m/15m bars only; entry = next 1-min bar open; forward
metrics walked on the 1-min path. Exploratory scan - NOT a backtest (no Gate-4 claim).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl  # landmine-enforced loader (tz + >=09:15)

OUT = Path(__file__).parent
WIN_BPS = 20.0     # +-20bps race defines a tradable win for ATM option buying
LAST_ENTRY = 870   # 14:30 - need runway
EOD = 924          # 15:24 mark

s = dl._spot()
daily = s.groupby("d").agg(hi=("high", "max"), lo=("low", "min"))
pdh = daily["hi"].shift(1); pdl = daily["lo"].shift(1)
pwh = pdh.rolling(5).max(); pwl = pdl.rolling(5).min()
days = list(daily.index)

by_day = {d: g[["hm", "open", "high", "low", "close"]].to_numpy() for d, g in s.groupby("d")}

def fold(arr, tf):
    hm, o, h, l, c = arr.T
    idx = ((hm - 555) // tf).astype(int)
    out = []
    for j in np.unique(idx):
        m = idx == j
        out.append((555 + (int(j) + 1) * tf, o[m][0], h[m].max(), l[m].min(), c[m][-1]))
    return np.array(out)  # entry_hm, o, h, l, c

def forward(arr, e_hm, sgn):
    hm = arr[:, 0]
    i0 = np.searchsorted(hm, e_hm)
    if i0 >= len(arr) or hm[i0] > e_hm + 3:
        return None
    e = arr[i0, 1]
    end = min(len(arr), i0 + 60)
    seg = arr[i0:end]
    seg = seg[seg[:, 0] <= EOD]
    if len(seg) < 15:
        return None
    hi = sgn * (seg[:, 2] - e) / e * 1e4 if sgn == 1 else sgn * (seg[:, 3] - e) / e * 1e4
    lo = sgn * (seg[:, 3] - e) / e * 1e4 if sgn == 1 else sgn * (seg[:, 2] - e) / e * 1e4
    win = None
    for k in range(len(seg)):
        if lo[k] <= -WIN_BPS and hi[k] >= WIN_BPS:
            win = 0; break          # both same minute -> conservative loss
        if lo[k] <= -WIN_BPS:
            win = 0; break
        if hi[k] >= WIN_BPS:
            win = 1; break
    if win is None:
        win = 1 if sgn * (seg[-1, 4] - e) / e * 1e4 > 0 else 0  # timeout: sign of drift
    def ret(n):
        j = min(n, len(seg) - 1)
        return sgn * (seg[j, 4] - e) / e * 1e4
    ieod = np.searchsorted(arr[:, 0], EOD, side="right") - 1
    return dict(win=win, f15=ret(14), f30=ret(29), f60=ret(59),
                mfe=float(hi.max()), mae=float(lo.min()),
                eod=sgn * (arr[ieod, 4] - e) / e * 1e4)

events = []
for di, d in enumerate(days):
    if di < 6 or pd.isna(pdl.iloc[di]) or pd.isna(pwl.iloc[di]):
        continue
    arr = by_day[d]
    if len(arr) < 360:
        continue
    PDH, PDL, PWH, PWL = pdh.iloc[di], pdl.iloc[di], pwh.iloc[di], pwl.iloc[di]
    for tf in (5, 15):
        f = fold(arr, tf)
        ehm, o, h, l, c = f.T
        rng = np.maximum(h - l, 1e-9)
        body = np.abs(c - o)
        cpos = (c - l) / rng                      # close position in range
        or_end = 555 + max(30, tf)                # opening range = first 30 min
        m_or = ehm <= 555 + 30
        ORH, ORL = h[m_or].max(), l[m_or].min()
        dlow = np.minimum.accumulate(l); dhigh = np.maximum.accumulate(h)
        for j in range(2, len(f)):
            if ehm[j] > LAST_ENTRY or ehm[j] <= or_end:
                continue
            base = dict(d=str(d), tf=tf, e_hm=int(ehm[j]),
                        depth=0.0, cpos=float(cpos[j]))
            sigs = []
            # --- level sweeps (penetrate level, close back through = reclaim) ---
            for lv, nm in ((PDL, "pdl"), (PWL, "pwl"), (ORL, "orl")):
                if l[j] < lv and c[j] > lv and o[j] > l[j]:
                    sigs.append((f"{nm}_sweep", 1, (lv - l[j]) / lv * 1e4))
            for lv, nm in ((PDH, "pdh"), (PWH, "pwh"), (ORH, "orh")):
                if h[j] > lv and c[j] < lv:
                    sigs.append((f"{nm}_sweep", -1, (h[j] - lv) / lv * 1e4))
            # --- shakeout / spring: break N-bar low, strong reclaim close ---
            N = 12 if tf == 5 else 6
            if j > N:
                sup = l[j - N:j].min(); res = h[j - N:j].max()
                if l[j] < sup and c[j] > h[j - 1] and cpos[j] >= 0.6:
                    sigs.append(("spring", 1, (sup - l[j]) / sup * 1e4))
                if h[j] > res and c[j] < l[j - 1] and cpos[j] <= 0.4:
                    sigs.append(("upthrust", -1, (h[j] - res) / res * 1e4))
            # --- pin bar at day extreme ---
            lw = (min(o[j], c[j]) - l[j]); uw = h[j] - max(o[j], c[j])
            if lw >= 2 * body[j] and lw >= 0.6 * rng[j] and l[j] <= dlow[j] + 1e-9:
                sigs.append(("pin", 1, lw / l[j] * 1e4))
            if uw >= 2 * body[j] and uw >= 0.6 * rng[j] and h[j] >= dhigh[j] - 1e-9:
                sigs.append(("pin", -1, uw / h[j] * 1e4))
            # --- engulfing at day extreme ---
            if (c[j] > o[j] and c[j - 1] < o[j - 1] and c[j] > o[j - 1] and o[j] < c[j - 1]
                    and l[j] <= dlow[j] + 1e-9):
                sigs.append(("engulf", 1, body[j] / c[j] * 1e4))
            if (c[j] < o[j] and c[j - 1] > o[j - 1] and c[j] < o[j - 1] and o[j] > c[j - 1]
                    and h[j] >= dhigh[j] - 1e-9):
                sigs.append(("engulf", -1, body[j] / c[j] * 1e4))
            if not sigs:
                continue
            fwd = forward(arr, int(ehm[j]), sigs[0][1])
            for nm, sgn, depth in sigs:
                fw = fwd if sgn == sigs[0][1] else forward(arr, int(ehm[j]), sgn)
                if fw is None:
                    continue
                events.append({**base, "pattern": nm, "dir": sgn, "depth": float(depth),
                               "confl": len(sigs) > 1, **fw})
    # baseline: every 5m bar (long side) for base-rate comparison
    f = fold(arr, 5)
    for j in range(6, len(f), 6):
        if f[j, 0] > LAST_ENTRY:
            break
        fw = forward(arr, int(f[j, 0]), 1)
        if fw:
            events.append(dict(d=str(d), tf=5, e_hm=int(f[j, 0]), depth=0, cpos=0,
                               pattern="BASELINE", dir=1, confl=False, **fw))

ev = pd.DataFrame(events)
ev["year"] = ev["d"].str[:4]
ev["hour"] = (ev["e_hm"] // 60)
ev.to_csv(OUT / "events.csv", index=False)

MONTHS = 60.0
def agg(g):
    return pd.Series(dict(n=len(g), tr_mo=round(len(g) / MONTHS, 1),
                          win=round(g["win"].mean() * 100, 1),
                          f30=round(g["f30"].mean(), 1), f60=round(g["f60"].mean(), 1),
                          eod=round(g["eod"].mean(), 1),
                          mfe=round(g["mfe"].median(), 1), mae=round(g["mae"].median(), 1)))

lines = ["# SWEEP/SHAKEOUT SCAN — NIFTY spot 1-min 2021-06..2026-06 (exploratory, D-028: not a backtest)",
         f"win = +{WIN_BPS:.0f}bps before -{WIN_BPS:.0f}bps on 1-min path (60m window); entries next 1-min open; last entry 14:30",
         "", "## All pattern cells (dir: 1=long/buy-CE, -1=short/buy-PE)"]
t = ev.groupby(["pattern", "tf", "dir"]).apply(agg, include_groups=False).reset_index()
lines.append(t.sort_values("win", ascending=False).to_string(index=False))

lines += ["", "## Sniper filters (depth>=8bps & close-strength) and confluence"]
snip = ev[(ev.pattern != "BASELINE") & (ev.depth >= 8)
          & (((ev["dir"] == 1) & (ev.cpos >= 0.65)) | ((ev["dir"] == -1) & (ev.cpos <= 0.35)))]
t2 = snip.groupby(["pattern", "tf", "dir"]).apply(agg, include_groups=False).reset_index()
lines.append(t2.sort_values("win", ascending=False).to_string(index=False))
conf = ev[ev.confl & (ev.pattern != "BASELINE")]
lines += ["", "### Confluence (>=2 patterns same bar)",
          conf.groupby(["dir"]).apply(agg, include_groups=False).reset_index().to_string(index=False)]

lines += ["", "## Time-of-day (all sweep patterns pooled, by entry hour)"]
sw = ev[ev.pattern.str.contains("sweep")]
lines.append(sw.groupby(["hour", "dir"]).apply(agg, include_groups=False).reset_index().to_string(index=False))

lines += ["", "## Year stability for cells with n>=50 & win>=53%"]
for (p, tf_, dr), g in ev[ev.pattern != "BASELINE"].groupby(["pattern", "tf", "dir"]):
    if len(g) >= 50 and g["win"].mean() >= 0.53:
        yr = g.groupby("year").apply(agg, include_groups=False)
        lines += [f"### {p} tf{tf_} dir{dr}", yr.to_string()]

(OUT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
print(f"events: {len(ev)} -> events.csv; SUMMARY.md written")
print("\n".join(lines[:8]))
