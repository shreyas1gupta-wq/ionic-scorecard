"""TOM-VIX (frozen @ 51bfbd9): turn-of-month x VIX gate, 4 cells, non-ToM placebo + mid-month specificity."""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(179)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/TOMVIX_20260713"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0008
V1E = pd.Timestamp("2024-06-30"); S0, S1 = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-06-30")

idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC["nm"] = IC["Index Name"].str.strip().str.upper()
IC["date"] = pd.to_datetime(IC["file_date"])
def iser(nm):
    g = IC[IC.nm == nm].set_index("date").sort_index()
    s = pd.to_numeric(g["Closing Index Value"], errors="coerce")
    return s[~s.index.duplicated()].dropna()
nifty = iser("NIFTY 50")
vix = iser("INDIA VIX").reindex(nifty.index).ffill(limit=3)
vix_pct = vix.rolling(252).rank(pct=True)
ret = nifty.pct_change()
dates = nifty.index
N = len(dates)
month_id = dates.year * 12 + dates.month
last_of_month = np.where(np.diff(month_id, append=month_id[-1] + 1) != 0)[0]
# day-10 anchor per month (10th trading day)
first_of_month = np.r_[0, last_of_month[:-1] + 1]
day10 = first_of_month + 9

def windows(anchors, k_pre, k_post):
    # entry close index = a - k_pre; returns accrue a-k_pre+1 .. a+k_post
    out = []
    for a in anchors:
        e0, e1 = a - k_pre, a + k_post
        if e0 >= 252 and e1 < N:
            out.append((e0, e1))
    return out

def run_windows(wins, gate):
    res = []
    for e0, e1 in wins:
        if gate is not None:
            v = vix_pct.iloc[e0]
            if not (np.isfinite(v) and v >= gate):
                continue
        r = float(np.prod(1 + ret.iloc[e0 + 1:e1 + 1].values) - 1) - 2 * COST
        res.append((dates[e0], r))
    return res

tom_days = set()
for a in last_of_month:
    for k in range(-2, 4):
        tom_days.add(a + k)

CELLS = [("T1_p1p3", 1, 3, None), ("T2_p1p3_v50", 1, 3, 0.50), ("T3_p1p3_v70", 1, 3, 0.70), ("T4_p2p2", 2, 2, None)]
rows, series = [], {}
for tag, kp, ko, gate in CELLS:
    wins = windows(last_of_month, kp, ko)
    res = run_windows(wins, gate)
    dts = pd.DatetimeIndex([x[0] for x in res]); real = np.array([x[1] for x in res])
    mv, ms = dts <= V1E, (dts >= S0) & (dts <= S1)
    n_val = int(mv.sum())
    L = kp + ko
    # placebo: random non-ToM entry days, same length, same gate applied? Card: random same-length windows from non-ToM days.
    cand = [i for i in range(252, N - L - 1) if i not in tom_days]
    cand_val = [i for i in cand if dates[i] <= V1E]; cand_scr = [i for i in cand if S0 <= dates[i] <= S1]
    nulls_v, nulls_s = [], []
    for k in range(200):
        if n_val >= 3:
            pick = rng.choice(cand_val, size=n_val, replace=False)
            rr = [float(np.prod(1 + ret.iloc[i + 1:i + L + 1].values) - 1) - 2 * COST for i in pick]
            nulls_v.append(np.mean(rr))
        if ms.sum() >= 1 and len(cand_scr) > int(ms.sum()):
            pick2 = rng.choice(cand_scr, size=int(ms.sum()), replace=False)
            rr2 = [float(np.prod(1 + ret.iloc[i + 1:i + L + 1].values) - 1) - 2 * COST for i in pick2]
            nulls_s.append(np.mean(rr2))
    p95 = float(np.percentile(nulls_v, 95)) if len(nulls_v) >= 20 else np.nan
    pms = float(np.mean(nulls_s)) if nulls_s else np.nan
    vm = float(real[mv].mean()) if n_val else np.nan
    sm = float(real[ms].mean()) if ms.sum() else np.nan
    scr_alpha = sm - pms if np.isfinite(sm) and np.isfinite(pms) else np.nan
    # specificity: pseudo-ToM at day-10 anchor, same gate
    pres = run_windows(windows(day10, kp, ko), gate)
    pdts = pd.DatetimeIndex([x[0] for x in pres]); preal = np.array([x[1] for x in pres])
    pmv = pdts <= V1E
    pseudo = float(preal[pmv].mean()) if pmv.sum() >= 10 else np.nan
    spec_ok = np.isfinite(pseudo) and np.isfinite(vm) and vm > 0 and pseudo < 0.5 * vm
    if n_val < 60:
        verdict = "NOT-ADJUDICABLE"
    else:
        verdict = "PASS" if (vm > p95 and np.isfinite(scr_alpha) and scr_alpha > 0 and spec_ok) else "FAIL"
    rows.append(dict(cell=tag, n=len(res), n_val=n_val, val=round(vm * 100, 2) if np.isfinite(vm) else None,
                     plac95=round(p95 * 100, 2) if np.isfinite(p95) else None,
                     scr_alpha=round(scr_alpha * 100, 2) if np.isfinite(scr_alpha) else None,
                     pseudo=round(pseudo * 100, 2) if np.isfinite(pseudo) else None,
                     verdict=verdict))
    print(rows[-1], flush=True)
    pos = pd.Series(0.0, index=dates)
    for e0, _ in [(w[0], w[1]) for w in windows(last_of_month, kp, ko)]:
        pass
    dser = pd.Series(0.0, index=dates)
    for (e0, e1) in windows(last_of_month, kp, ko):
        if gate is not None:
            v = vix_pct.iloc[e0]
            if not (np.isfinite(v) and v >= gate):
                continue
        dser.iloc[e0 + 1:e1 + 1] = ret.iloc[e0 + 1:e1 + 1].values
    series[tag] = dser

df = pd.DataFrame(rows)
npass = int((df.verdict == "PASS").sum())
book = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv",
                   index_col=0, parse_dates=True)["total"]
passing = df[df.verdict == "PASS"].cell.tolist() or [df.iloc[0].cell]
g = series[passing[0]]
common = g.index.intersection(book.index)
corr_m = float(pd.concat([g.reindex(common), book.reindex(common) / 1e7], axis=1).resample("ME").sum().corr().iloc[0, 1])
adopt = (npass >= 2) and (corr_m < 0.25)
lines = [df.to_string(index=False),
         f"cells passed: {npass}/4 | monthly corr({passing[0]}, book) = {corr_m:+.2f} (bar < +0.25 signed)",
         f"VERDICT: {'ADOPT-CANDIDATE' if adopt else 'NOT ADOPTED'}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "TOMVIX_RESULTS.txt").write_text(txt, encoding="utf-8")
