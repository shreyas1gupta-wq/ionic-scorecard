"""T6 (pilot) - OI-wall / trapped-writer trigger. CHEAPTEST_SPEC_20260710.

PRE-REGISTERED (FROZEN before run):
  Event: NIFTY spot 1-min close crosses UP through a CE "wall" strike, where wall =
    strike (50-pt grid, above spot, within +1.5% of spot) whose 3-BAR-LAGGED CE OI is
    in the TOP DECILE (>= q90) of lagged CE OI across all grid strikes within +/-1.5% of spot.
    First crossing per (day, strike) only.
  Metric: forward spot points close[t] -> close[t+h], h in {15, 30, 60} min, EXCESS of a
    time-of-day-matched baseline (30-min buckets, all minutes all days).
  PRIMARY = 30-min horizon. KILL if effect < +5 pts OR day-clustered t < 2.
    (t = mean of per-day mean excess / SE across days.)
  Secondary (report only): 15m, 60m, era split (2021-06..2023-12 vs 2024-01..2026-06),
    non-wall crossing contrast (bottom-half OI strikes), +1-bar lag robustness.
  Trials ledger: 1 primary.

Guards: drop_preopen (>=09:15), OI 0->NaN->ffill (late-era dissemination gaps),
  3-bar OI lag (exchange dissemination, T-series control), first-cross dedupe,
  truncation guard (t <= session_end - h).
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import chain  # noqa: E402
import guards  # noqa: E402  (drop_preopen used inline on spot)

OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "CHEAPTEST_SPEC_20260710" / "t6-oi-wall"
HORIZONS = [15, 30, 60]
OI_LAG = 3
BAND = 0.015     # +/-1.5% strike band for decile ranking
GRID = 50        # NIFTY strike grid
Q_WALL = 0.90

# ---- spot ----
spot = chain.load_index()                       # naive IST index, ohlc
spot = spot[spot.index.time >= dt.time(9, 15)]  # pre-open auction guard
spot = spot[spot.index.time <= dt.time(15, 30)]
spot_days = pd.Series(spot.index.date, index=spot.index)

mapping, exps = chain.build_expiry_index()

# assign each trading day to its nearest expiry (0<=dte<=6)
all_days = sorted(set(spot.index.date))
day2exp = {}
for d in all_days:
    e = chain.nearest_expiry(d, 0, 6)
    if e is not None:
        day2exp[d] = e

events = []          # dicts: day, t, strike, wall(bool), fwd15/30/60
base_acc = {h: {} for h in HORIZONS}   # bucket -> [sum, n] over ALL minutes of processed days

def bucket(ts):
    return ts.hour * 2 + (1 if ts.minute >= 30 else 0)

processed_days = 0
for exp in exps:
    days = [d for d, e in day2exp.items() if e == exp]
    if not days:
        continue
    try:
        df = pq.read_table(mapping[exp],
                           columns=["timestamp", "strike", "option_type",
                                    "open_interest", "trading_day"]).to_pandas()
    except Exception as ex:
        print(f"[skip] {exp}: {ex}")
        continue
    df = df[df["option_type"] == "CE"]
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates(["t", "strike"])
    df["trading_day"] = df["trading_day"].astype(str)

    for d in days:
        dstr = d.isoformat()
        cd = df[df["trading_day"] == dstr]
        if cd.empty:
            continue
        sp = spot.loc[spot_days.values == d, "close"]
        if len(sp) < 90:
            continue
        # OI matrix: time x strike; 0 -> NaN -> ffill; then 3-bar dissemination lag
        oi = cd.pivot_table(index="t", columns="strike", values="open_interest", aggfunc="last")
        oi = oi[oi.index.time >= dt.time(9, 15)]
        oi = oi.replace(0, np.nan).ffill().shift(OI_LAG)
        oi = oi.reindex(sp.index).ffill()

        closes = sp.values
        times = sp.index
        n = len(sp)
        # baseline accumulation (all minutes)
        for h in HORIZONS:
            fwd = np.full(n, np.nan)
            fwd[:n - h] = closes[h:] - closes[:n - h]
            for i in range(n - h):
                b = bucket(times[i])
                s = base_acc[h].setdefault(b, [0.0, 0])
                s[0] += fwd[i]; s[1] += 1

        seen = set()
        strikes = oi.columns.to_numpy()
        for i in range(max(OI_LAG + 1, 1), n):
            pc, c = closes[i - 1], closes[i]
            if c <= pc:
                continue
            k0 = int(np.floor(pc / GRID) * GRID) + GRID
            crossed = [k for k in range(k0, int(np.floor(c / GRID) * GRID) + 1, GRID)]
            if not crossed:
                continue
            row = oi.iloc[i]
            lo, hi = c * (1 - BAND), c * (1 + BAND)
            band_mask = (strikes >= lo) & (strikes <= hi)
            band_oi = row.values[band_mask]
            band_oi = band_oi[~np.isnan(band_oi)]
            if len(band_oi) < 5:
                continue
            q90 = np.quantile(band_oi, Q_WALL)
            q50 = np.quantile(band_oi, 0.50)
            for k in crossed:
                if k in seen or k > c * (1 + BAND):
                    continue
                seen.add(k)
                v = row.get(k, np.nan)
                if np.isnan(v):
                    continue
                is_wall = v >= q90
                is_nonwall = v <= q50
                rec = {"day": dstr, "t": times[i], "strike": k, "oi": v,
                       "wall": is_wall, "nonwall": is_nonwall, "spot": c}
                for h in HORIZONS:
                    rec[f"fwd{h}"] = closes[i + h] - c if i + h < n else np.nan
                    rec[f"b{h}"] = bucket(times[i])
                events.append(rec)
        processed_days += 1

ev = pd.DataFrame(events)
print(f"days processed={processed_days}, raw crossing events={len(ev)}, walls={int(ev['wall'].sum())}")

# baseline lookup
base = {h: {b: s[0] / s[1] for b, s in base_acc[h].items()} for h in HORIZONS}
for h in HORIZONS:
    ev[f"x{h}"] = ev[f"fwd{h}"] - ev[f"b{h}"].map(base[h])

ev.to_csv(OUT / "events.csv", index=False)

def cluster_t(sub, col):
    d = sub.dropna(subset=[col]).groupby("day")[col].mean()
    if len(d) < 3:
        return np.nan, np.nan, len(d)
    return d.mean(), d.mean() / (d.std(ddof=1) / np.sqrt(len(d))), len(d)

def report(sub, tag):
    rows = []
    for h in HORIZONS:
        m = sub[f"x{h}"].mean()
        eff, t, ndays = cluster_t(sub, f"x{h}")
        rows.append({"set": tag, "h": h, "n_events": sub[f"x{h}"].notna().sum(),
                     "n_days": ndays, "mean_excess_pts": round(m, 2),
                     "day_mean_excess_pts": round(eff, 2) if eff == eff else np.nan,
                     "t_dayclust": round(t, 2) if t == t else np.nan})
    return rows

res = []
W = ev[ev["wall"]]
NW = ev[ev["nonwall"]]
res += report(W, "WALL")
res += report(NW, "NONWALL_bottom50")
for era, tag in [((ev["day"] < "2024-01-01"), "era1_2021-23"), ((ev["day"] >= "2024-01-01"), "era2_2024-26")]:
    res += report(ev[ev["wall"] & era], f"WALL_{tag}")
rdf = pd.DataFrame(res)
rdf.to_csv(OUT / "results.csv", index=False)
print(rdf.to_string(index=False))

# +1-bar lag robustness on primary: recompute wall 30m excess with entry shifted 1 bar
# (approx: fwd from t+1 -> t+1+30 == fwd31 - 1-bar move; do it properly via events re-eval is heavy,
#  approximate with fwd 31m minus first-minute move using stored day closes is not stored -> skip approx,
#  instead: OI_LAG+1 sensitivity noted in SUMMARY as follow-up if PASS.)
