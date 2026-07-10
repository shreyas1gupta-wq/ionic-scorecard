"""CHEAP-TEST F-FVG (fvg-flags) -- pre-registered 2026-07-10.

Fair-value-gap (3-candle imbalance) constructs on NIFTY spot, 1-min & 5-min TF.
Sub-test (a) GLBS-A: PDH/PDL sweep + reversal-direction FVG forms + price retests it -> reversal.
Sub-test (b) GLBS-E: impulse FVG forms, price retraces into the zone -> continuation in impulse dir.

PRE-REGISTERED (FROZEN before run):
- FVG def: bullish  = low(c3) > high(c1), zone [high(c1), low(c3)];
           bearish  = high(c3) < low(c1), zone [high(c3), low(c1)];
           min gap size = 0.02% of c2 close (single fixed value, both TFs).
- FVG lifecycle: first-touch retest only; FVG dead once fully traded through.
- (b) retest window: within 12 bars of formation; event = first touch of zone edge;
  entry = next bar open; direction = impulse direction.
- (a) sweep: TF bar high > PDH & close < PDH (short) / low < PDL & close > PDL (long);
  then reversal-direction FVG must FORM within 12 bars of sweep, then be retested
  within 12 bars of formation; entry = next bar open after retest; direction = reversal.
- Forward horizon: 30 min (5-min TF: 6 bars) / 15 min (1-min TF: 15 bars), close-to-open-entry, in POINTS.
- Last entry 14:45. Bars < 09:15 dropped by loader (landmine #2); tz landmine #1 handled by loader.
- Baseline: time-of-day matched (30-min buckets), same horizon, all days, signed by event direction.
  Effect = mean(signed event fwd pts - signed baseline pts).
- t-stat: day-clustered (t over day-mean excess).
- KILL (each sub-test separately, per pre-registration): effect < 5 pts OR t < 2.5.
  A sub-test survives only if >=1 TF clears BOTH thresholds.
- Era split mandatory: 2021-2022 vs 2023-2026; pooled verdict, era table reported.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl  # landmine-enforced loader (tz + >=09:15)

OUT = Path(__file__).parent
GAP_MIN_PCT = 0.0002      # 0.02% of c2 close
FORM_WIN = 12             # bars: FVG must form within 12 bars of sweep (a)
RETEST_WIN = 12           # bars: retest must occur within 12 bars of formation
LAST_ENTRY_HM = 14 * 60 + 45
HORIZON_MIN = {1: 15, 5: 30}   # forward horizon in minutes per TF

s = dl._spot()
daily = s.groupby("d").agg(hi=("high", "max"), lo=("low", "min"))
pdh = daily["hi"].shift(1)
pdl = daily["lo"].shift(1)
by_day = {d: g[["hm", "open", "high", "low", "close"]].to_numpy()
          for d, g in s.groupby("d")}
days = sorted(by_day)


def fold(arr, tf):
    """1-min -> tf bars. Returns rows (close_hm, o, h, l, c). close_hm = bar END time."""
    hm, o, h, l, c = arr.T
    idx = ((hm - 555) // tf).astype(int)
    out = []
    for j in np.unique(idx):
        m = idx == j
        out.append((555 + (int(j) + 1) * tf, o[m][0], h[m].max(), l[m].min(), c[m][-1]))
    return np.array(out)


def fwd_pts(arr1m, entry_hm, horizon):
    """Entry at first 1-min open with hm >= entry_hm; fwd = close at entry+horizon - entry."""
    hm = arr1m[:, 0]
    i0 = np.searchsorted(hm, entry_hm)
    if i0 >= len(arr1m) or hm[i0] > entry_hm + 3:
        return None, None
    e = arr1m[i0, 1]
    j = np.searchsorted(hm, entry_hm + horizon, side="right") - 1
    if j <= i0:
        return None, None
    return arr1m[j, 4] - e, e


def find_fvgs(bars, gap_min_pct):
    """Return list of (form_i, dir, zlo, zhi). dir=+1 bullish, -1 bearish. form_i = index of c3."""
    out = []
    for i in range(2, len(bars)):
        c1h, c1l = bars[i - 2, 2], bars[i - 2, 3]
        c3h, c3l = bars[i, 2], bars[i, 3]
        c2c = bars[i - 1, 4]
        thr = gap_min_pct * c2c
        if c3l - c1h >= thr:
            out.append((i, 1, c1h, c3l))     # bullish gap zone
        elif c1l - c3h >= thr:
            out.append((i, -1, c3h, c1l))    # bearish gap zone
    return out


def first_retest(bars, form_i, direction, zlo, zhi, win):
    """First bar after form_i (within win) whose range touches the zone.
    Returns (retest_i, filled_through_flag). FVG dead if fully traded through before touch counts anyway
    (first touch IS the trade-through start, so first-touch-only is automatic)."""
    for k in range(form_i + 1, min(form_i + 1 + win, len(bars))):
        if direction == 1:
            if bars[k, 3] <= zhi:            # low dips into bullish zone
                return k
        else:
            if bars[k, 2] >= zlo:            # high pokes into bearish zone
                return k
    return None


rows = []
for di, d in enumerate(days):
    if di == 0 or d not in pdh.index or np.isnan(pdh.loc[d]):
        continue
    arr1m = by_day[d]
    PDH, PDL = pdh.loc[d], pdl.loc[d]
    for tf in (1, 5):
        bars = arr1m if tf == 1 else fold(arr1m, tf)
        if len(bars) < 10:
            continue
        horizon = HORIZON_MIN[tf]
        fvgs = find_fvgs(bars, GAP_MIN_PCT)

        # ---- (b) continuation: retest of impulse FVG ----
        for (fi, dr, zlo, zhi) in fvgs:
            ri = first_retest(bars, fi, dr, zlo, zhi, RETEST_WIN)
            if ri is None:
                continue
            entry_hm = bars[ri, 0]           # next bar open == first 1-min open at/after bar close
            if entry_hm > LAST_ENTRY_HM:
                continue
            f, e = fwd_pts(arr1m, entry_hm, horizon)
            if f is None:
                continue
            rows.append((d, tf, "b_cont", dr, entry_hm, e, dr * f))

        # ---- (a) sweep + reversal FVG retest ----
        sweeps = []
        for i in range(len(bars)):
            if bars[i, 2] > PDH and bars[i, 4] < PDH:
                sweeps.append((i, -1))       # PDH sweep -> short bias
            elif bars[i, 3] < PDL and bars[i, 4] > PDL:
                sweeps.append((i, 1))        # PDL sweep -> long bias
        used = set()
        for (si, dr) in sweeps:
            cand = [(fi, fdr, zlo, zhi) for (fi, fdr, zlo, zhi) in fvgs
                    if fdr == dr and si < fi <= si + FORM_WIN and fi not in used]
            if not cand:
                continue
            fi, fdr, zlo, zhi = cand[0]
            used.add(fi)
            ri = first_retest(bars, fi, fdr, zlo, zhi, RETEST_WIN)
            if ri is None:
                continue
            entry_hm = bars[ri, 0]
            if entry_hm > LAST_ENTRY_HM:
                continue
            f, e = fwd_pts(arr1m, entry_hm, horizon)
            if f is None:
                continue
            rows.append((d, tf, "a_sweep", dr, entry_hm, e, dr * f))

ev = pd.DataFrame(rows, columns=["d", "tf", "test", "dir", "entry_hm", "entry_px", "signed_fwd_pts"])
ev["d"] = pd.to_datetime(ev["d"])
ev["year"] = ev["d"].dt.year
ev["era"] = np.where(ev["year"] <= 2022, "2021-22", "2023-26")
ev["tod_bucket"] = (ev["entry_hm"] - 555) // 30

# ---- baselines: unconditional signed fwd at every (tf, tod_bucket), all days ----
base_rows = []
for d in days:
    arr1m = by_day[d]
    for tf in (1, 5):
        horizon = HORIZON_MIN[tf]
        step = 5  # sample baseline every 5 minutes for tractability
        for hm0 in range(555 + tf, LAST_ENTRY_HM + 1, step):
            f, e = fwd_pts(arr1m, hm0, horizon)
            if f is None:
                continue
            base_rows.append((tf, (hm0 - 555) // 30, f))
bs = pd.DataFrame(base_rows, columns=["tf", "tod_bucket", "fwd_pts"])
bmean = bs.groupby(["tf", "tod_bucket"])["fwd_pts"].mean().rename("base_fwd")

ev = ev.merge(bmean, left_on=["tf", "tod_bucket"], right_index=True, how="left")
ev["base_signed"] = ev["dir"] * ev["base_fwd"]
ev["excess_pts"] = ev["signed_fwd_pts"] - ev["base_signed"]
ev.to_csv(OUT / "events.csv", index=False)


def cluster_t(sub):
    dm = sub.groupby("d")["excess_pts"].mean()
    n = len(dm)
    if n < 3:
        return np.nan, n
    return dm.mean() / (dm.std(ddof=1) / np.sqrt(n)), n


lines = []
res = []
for (test, tf), sub in ev.groupby(["test", "tf"]):
    eff = sub["excess_pts"].mean()
    raw = sub["signed_fwd_pts"].mean()
    t, ndays = cluster_t(sub)
    wr = (sub["signed_fwd_pts"] > 0).mean()
    res.append(dict(test=test, tf=tf, n_events=len(sub), n_days=ndays,
                    raw_signed_pts=round(raw, 2), effect_pts=round(eff, 2),
                    t_dayclust=round(t, 2), wr=round(wr, 3),
                    verdict="PASS" if (eff >= 5 and t >= 2.5) else "KILL"))
    for era, se in sub.groupby("era"):
        te, nd = cluster_t(se)
        res.append(dict(test=test, tf=tf, era=era, n_events=len(se), n_days=nd,
                        raw_signed_pts=round(se["signed_fwd_pts"].mean(), 2),
                        effect_pts=round(se["excess_pts"].mean(), 2),
                        t_dayclust=round(te, 2) if not np.isnan(te) else None,
                        wr=round((se["signed_fwd_pts"] > 0).mean(), 3)))
rd = pd.DataFrame(res)
rd.to_csv(OUT / "results.csv", index=False)
print(rd.to_string(index=False))
print(f"\nspot days={len(days)}  range {days[0]} .. {days[-1]}  events={len(ev)}")
