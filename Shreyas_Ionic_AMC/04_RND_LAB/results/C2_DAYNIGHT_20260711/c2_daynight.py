"""C2-CARD: day-night decomposition of NIFTY ATM short-straddle premium.
Card frozen in INDEX_PROGRAM_2026/MASTER_PLAN.md BEFORE this run (2026-07-11).
Segments per day D, nearest expiry E > D (DTE>=1), ATM re-struck at entry:
  INTRADAY(D):  sell CE+PE @ first close >=09:20, buy back @ last print <=15:25.
  OVERNIGHT(D): sell CE+PE @ last print <=15:25 D, buy back @ first close >=09:20 D+1.
Gross primary; net at 1pt/leg one-way (2x before 09:30). No SL.
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/C2_DAYNIGHT_20260711"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()
exps = sorted(exps)

spot_dates = pd.Series(spot.index.date, index=spot.index)
all_days = sorted(set(spot_dates.values))
day_next = {all_days[i]: all_days[i + 1] for i in range(len(all_days) - 1)}

def px_at_open(series, day):
    """First 1-min close >= 09:20 on day (< 09:45 sanity window)."""
    w = series[(series.index.date == day) & (series.index.time >= dt.time(9, 20)) &
               (series.index.time <= dt.time(9, 45))]
    return (w.index[0], w.iloc[0]) if len(w) else (None, None)

def px_at_close(series, day):
    """Last print <= 15:25 (>= 15:00 sanity window) on day."""
    w = series[(series.index.date == day) & (series.index.time >= dt.time(15, 0)) &
               (series.index.time <= dt.time(15, 25))]
    return (w.index[-1], w.iloc[-1]) if len(w) else (None, None)

def spot_at(day, t_open):
    d = spot[spot_dates == day]
    if not len(d):
        return None
    w = d[d.index.time >= dt.time(9, 20)] if t_open else d[d.index.time <= dt.time(15, 25)]
    if not len(w):
        return None
    return w["close"].iloc[0] if t_open else w["close"].iloc[-1]

rows, skips = [], {"no_expiry": 0, "load": 0, "spot": 0, "prints": 0}
for ei, exp in enumerate(exps):
    # days D with this expiry as nearest E > D: previous expiry < D < E
    prev = exps[ei - 1] if ei > 0 else dt.date(2021, 5, 1)
    days = [d for d in all_days if prev <= d < exp]
    if not days:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception as e:
        skips["load"] += len(days); print(f"[skip] {exp}: {e}"); continue
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    legs = {}  # (strike, cp) -> series

    def leg(k, cp):
        key = (float(k), cp)
        if key not in legs:
            s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")["close"].sort_index()
            legs[key] = s[~s.index.duplicated(keep="last")]
        return legs[key]

    for d in days:
        dnx = day_next.get(d)
        # ---- intraday segment on d ----
        sp_o = spot_at(d, True)
        if sp_o is None:
            skips["spot"] += 1
        else:
            k = round(sp_o / 50) * 50
            eo = [px_at_open(leg(k, cp), d) for cp in ("CE", "PE")]
            xo = [px_at_close(leg(k, cp), d) for cp in ("CE", "PE")]
            if all(v[1] is not None for v in eo + xo):
                gross = sum(v[1] for v in eo) - sum(v[1] for v in xo)
                cost = sum(2.0 if v[0].time() < dt.time(9, 30) else 1.0 for v in eo) + 2 * 1.0
                rows.append(dict(day=d, seg="intraday", dte=(exp - d).days, strike=k,
                                 entry_prem=sum(v[1] for v in eo), gross=gross, net=gross - cost,
                                 gap=np.nan, weekend=False))
            else:
                skips["prints"] += 1
        # ---- overnight segment d -> dnx (contract must be alive on dnx: dnx <= exp) ----
        if dnx is None or dnx > exp:
            continue
        sp_c = spot_at(d, False)
        sp_no = spot_at(dnx, True)
        if sp_c is None or sp_no is None:
            skips["spot"] += 1; continue
        k = round(sp_c / 50) * 50
        ec = [px_at_close(leg(k, cp), d) for cp in ("CE", "PE")]
        xn = [px_at_open(leg(k, cp), dnx) for cp in ("CE", "PE")]
        if all(v[1] is not None for v in ec + xn):
            gross = sum(v[1] for v in ec) - sum(v[1] for v in xn)
            cost = 2 * 1.0 + sum(2.0 if v[0].time() < dt.time(9, 30) else 1.0 for v in xn)
            rows.append(dict(day=d, seg="overnight", dte=(exp - d).days, strike=k,
                             entry_prem=sum(v[1] for v in ec), gross=gross, net=gross - cost,
                             gap=(sp_no / sp_c - 1) * 100, weekend=(dnx - d).days > 1))
        else:
            skips["prints"] += 1
    if ei % 25 == 0:
        print(f"...{ei}/{len(exps)} expiries, rows={len(rows)}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "c2_segments.csv", index=False)
print(f"\nsegments: {len(r)} | skips: {skips}")

def stat(x):
    x = np.asarray(x, float)
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan
    return len(x), x.mean(), t, np.median(x), (x > 0).mean() * 100

with open(OUT / "RESULTS_RAW.txt", "w", encoding="utf-8") as f:
    def emit(s):
        print(s); f.write(s + "\n")
    for basis in ("gross", "net"):
        emit(f"\n==== {basis.upper()} (pts/segment) ====")
        emit(f"{'cut':<38}{'n':>6}{'mean':>8}{'t':>7}{'med':>8}{'win%':>7}")
        for seg in ("overnight", "intraday"):
            s = r[r.seg == seg]
            cuts = [("ALL", s),
                    ("no-weekend", s[~s.weekend]),
                    ("weekend-only", s[s.weekend]),
                    ("ex-jump |gap|>1%", s[(s.gap.abs() <= 1) | s.gap.isna()])]
            for dte_lo, dte_hi, lbl in [(1, 1, "DTE=1"), (2, 2, "DTE=2"), (3, 3, "DTE=3"), (4, 99, "DTE>=4")]:
                cuts.append((lbl, s[(s.dte >= dte_lo) & (s.dte <= dte_hi)]))
            for lbl, ss in cuts:
                if not len(ss):
                    continue
                n, m, t, md, w = stat(ss[basis])
                emit(f"{seg + ' ' + lbl:<38}{n:>6}{m:>8.2f}{t:>7.2f}{md:>8.2f}{w:>6.0f}%")
        emit("---- by year (overnight | intraday, mean " + basis + ") ----")
        r["yr"] = pd.to_datetime(r.day.astype(str)).dt.year
        for yr, g in r.groupby("yr"):
            on, idy = g[g.seg == "overnight"][basis], g[g.seg == "intraday"][basis]
            emit(f"{yr}: overnight {on.mean():+7.2f} (n={len(on)}) | intraday {idy.mean():+7.2f} (n={len(idy)})")

print("\nsaved:", OUT / "c2_segments.csv", "and RESULTS_RAW.txt")
