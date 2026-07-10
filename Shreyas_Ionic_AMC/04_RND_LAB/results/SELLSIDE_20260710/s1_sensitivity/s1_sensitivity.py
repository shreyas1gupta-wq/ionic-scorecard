"""S1 Gate-4 SENSITIVITY SURFACE (Sameer-style). Purpose: plateau-vs-cliff check around the
pre-registered primary (09:20 / ATM straddle / 30% SL). NOT a re-selection exercise: primary
stays primary; any better cell here is in-sample selection until holdout-validated.
Grid: entry {09:20, 09:45, 10:15} x structure {straddle@ATM+off, off in -100..+100 step 50;
symmetric strangle width {50,100}} x SL {20,30,40,50}%. Costs: 1pt/leg one-way, 2x pre-09:30.
Report per cell: n, net, day-t, PF; plateau stats around primary. Ledger: +84 cells (sensitivity).
NO COVID in sample."""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
mapping, exps = chain.build_expiry_index()

ENTRIES = ["09:20", "09:45", "10:15"]
SLS = [0.20, 0.30, 0.40, 0.50]
STRUCTS = [("straddle", off) for off in (-100, -50, 0, 50, 100)] + [("strangle", w) for w in (50, 100)]

def lc(ts): return 2.0 if ts.time() < dt.time(9, 30) else 1.0

def sl_exit(series, t0, entry, sl):
    win = series[(series.index > t0) & (series.index.time <= dt.time(15, 25))]
    if len(win) == 0:
        return None, None
    br = win[win >= entry * (1 + sl)]
    if len(br):
        after = win[win.index > br.index[0]]
        return (after.index[0], after.iloc[0]) if len(after) else (br.index[0], br.iloc[0])
    return win.index[-1], win.iloc[-1]

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
    series_cache = {}
    def leg(k, cp):
        key = (float(k), cp)
        if key not in series_cache:
            s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")["close"].sort_index()
            series_cache[key] = s[~s.index.duplicated(keep="last")]
        return series_cache[key]
    for ent in ENTRIES:
        h, m = map(int, ent.split(":"))
        cand = s1d[s1d.index.time >= dt.time(h, m)]
        if not len(cand):
            continue
        t0 = cand.index[0]
        spx = s1d["close"].loc[t0]
        atm = round(spx / 50) * 50
        for stype, prm in STRUCTS:
            if stype == "straddle":
                kc = kp = atm + prm
            else:
                kc, kp = atm + prm, atm - prm
            L = {"CE": leg(kc, "CE"), "PE": leg(kp, "PE")}
            if any(t0 not in L[c].index for c in L):
                continue
            e = {c: L[c].loc[t0] for c in L}
            for sl in SLS:
                net = 0.0; ok = True
                for c in L:
                    xt, xp = sl_exit(L[c], t0, e[c], sl)
                    if xt is None: ok = False; break
                    net += (e[c] - xp) - lc(t0) - lc(xt)
                if ok:
                    rows.append(dict(day=str(day), ent=ent, struct=f"{stype}{prm:+d}" if stype == "straddle"
                                     else f"strangle_w{prm}", sl=int(sl * 100), net=net))

df = pd.DataFrame(rows)
df.to_csv(OUT / "surface_trades.csv", index=False)

def cellstats(g):
    if len(g) < 60:
        return None
    t = g.net.mean() / (g.net.std(ddof=1) / np.sqrt(len(g)))
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    return g.net.mean(), t, pf, len(g)

lines = ["# S1 sensitivity surface (net pts/trade | t | PF). PRIMARY = 09:20 straddle+0 SL30."]
for ent in ENTRIES:
    lines.append(f"\n## entry {ent}")
    tbl = []
    for stype in [f"straddle{o:+d}" for o in (-100, -50, 0, 50, 100)] + ["strangle_w50", "strangle_w100"]:
        row = [stype]
        for sl in [20, 30, 40, 50]:
            g = df[(df.ent == ent) & (df.struct == stype) & (df.sl == sl)]
            st = cellstats(g)
            row.append("-" if st is None else f"{st[0]:+.1f}|t{st[1]:.1f}|pf{st[2]:.2f}")
        tbl.append(row)
    lines.append(pd.DataFrame(tbl, columns=["struct", "SL20", "SL30", "SL40", "SL50"]).to_string(index=False))

# plateau analysis around primary
prim = df[(df.ent == "09:20") & (df.struct == "straddle+0") & (df.sl == 30)]
neigh = df[(df.ent == "09:20") & (df.struct.isin(["straddle-50", "straddle+0", "straddle+50"]))
           & (df.sl.isin([20, 30, 40]))]
nb = neigh.groupby(["struct", "sl"])["net"].mean()
allc = df.groupby(["ent", "struct", "sl"])["net"].mean()
lines.append(f"\n# Plateau check: primary={prim.net.mean():+.2f} | 3x3 neighborhood mean={nb.mean():+.2f} "
             f"min={nb.min():+.2f} max={nb.max():+.2f} | all-surface: {(allc > 0).sum()}/{len(allc)} cells positive, "
             f"best={allc.max():+.2f} @{allc.idxmax()} (in-sample selection - do NOT adopt), "
             f"median={allc.median():+.2f}")
txt = "\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
