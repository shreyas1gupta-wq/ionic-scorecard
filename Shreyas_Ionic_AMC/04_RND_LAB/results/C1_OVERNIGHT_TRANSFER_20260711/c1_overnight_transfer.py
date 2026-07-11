"""C1-CARD: overnight transfer — regress NIFTY opening gap on prior US session (SPX ret, dVIX).
Card frozen in MASTER_PLAN BEFORE run. KILL if R2 < 0.15. Stage 2 (if pass): |pred gap|>0.75% veto on S1 days.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/C1_OVERNIGHT_TRANSFER_20260711"
OUT.mkdir(parents=True, exist_ok=True)

# ---- NIFTY gaps from kaggle minute data (pre-open bug: >=09:15 only) ----
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
sp = sp[sp.index >= "2015-01-01"]
dates = pd.Series(sp.index.date, index=sp.index)
opens = sp["close"].groupby(dates).first()          # first 1-min close >= 09:15
closes = sp[sp.index.time <= dt.time(15, 25)]["close"].groupby(
    dates[sp.index.time <= dt.time(15, 25)]).last()  # last print <= 15:25
gap = (opens / closes.shift(1) - 1) * 100
gap = gap.dropna()

# ---- US regressors (known before NIFTY open) ----
spx = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/us_sp500_daily.parquet")
spx = spx.set_index(pd.to_datetime(spx.Date).dt.date)["Close"].sort_index()
vix = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/cboe_vix_daily.parquet")
vix.columns = [c.upper() for c in vix.columns]
vix = vix.set_index(pd.to_datetime(vix["DATE"]).dt.date)["CLOSE"].sort_index()

spx_ret = (spx / spx.shift(1) - 1) * 100
dvix = vix.diff()
us_dates = np.array(sorted(spx_ret.dropna().index))

rows = []
for d, g in gap.items():
    i = np.searchsorted(us_dates, d)  # first us_date >= d
    if i == 0:
        continue
    ud = us_dates[i - 1]              # most recent US session strictly before d
    if (d - ud).days > 5:
        continue
    r = spx_ret.get(ud, np.nan)
    v = dvix.get(ud, np.nan)
    if np.isnan(r) or np.isnan(v):
        continue
    rows.append((d, g, r, v))
df = pd.DataFrame(rows, columns=["day", "gap", "spxret", "dvix"])
df.to_csv(OUT / "c1_panel.csv", index=False)

X = np.column_stack([np.ones(len(df)), df.spxret, df.dvix])
y = df.gap.values
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
pred = X @ beta
resid = y - pred
r2 = 1 - resid.var() / y.var()
se = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * resid.var(ddof=3))
t = beta / se

lines = []
lines.append(f"n={len(df)} days {df.day.min()}..{df.day.max()}")
lines.append(f"gap = {beta[0]:+.4f} + {beta[1]:+.4f}*spxret (t={t[1]:.1f}) + {beta[2]:+.4f}*dVIX (t={t[2]:.1f})")
lines.append(f"R2 = {r2:.4f}  |  FROZEN BAR: KILL if R2 < 0.15 (prior ~0.3)")
verdict = "PASS -> stage 2" if r2 >= 0.15 else "KILL (gap-model stream dead)"
lines.append(f"STAGE-1 VERDICT: {verdict}")
lines.append(f"era split R2: " + " | ".join(
    f"{lab}: {1 - (df[m].gap - np.column_stack([np.ones(m.sum()), df[m].spxret, df[m].dvix]) @ beta).var() / df[m].gap.var():.3f}"
    for lab, m in [("2015-19", pd.to_datetime(df.day.astype(str)) < "2020-01-01"),
                   ("2020-22", (pd.to_datetime(df.day.astype(str)) >= "2020-01-01") & (pd.to_datetime(df.day.astype(str)) < "2023-01-01")),
                   ("2023-26", pd.to_datetime(df.day.astype(str)) >= "2023-01-01")]))

# ---- stage 2 (conditional) ----
if r2 >= 0.15:
    tr = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three/final_three_trades.csv")
    s1 = tr[tr.strat == "S1"].copy()
    s1["day"] = pd.to_datetime(s1.day).dt.date
    m = df.set_index("day")
    s1["pgap"] = s1.day.map(pd.Series(pred, index=df.day))
    s1 = s1.dropna(subset=["pgap"])
    veto = s1.pgap.abs() > 0.75
    keep = s1[~veto]
    worst10 = set(s1.nsmallest(10, "net").day)
    removed_worst = len([d for d in s1[veto].day if d in worst10])
    lines.append(f"STAGE 2: S1 days matched={len(s1)}, vetoed={veto.sum()}")
    lines.append(f"  mean net all={s1.net.mean():+.2f} | after veto={keep.net.mean():+.2f} | vetoed days mean={s1[veto].net.mean():+.2f}")
    lines.append(f"  worst-10 removed by veto: {removed_worst}/10 (lead bar: >=3 AND mean improves)")
    lead = (keep.net.mean() > s1.net.mean()) and removed_worst >= 3
    lines.append(f"STAGE-2 VERDICT: {'LEAD -> propose S1-F v1.1 (shadow only, D-030)' if lead else 'PARK'}")

txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
print("\nsaved:", OUT / "c1_panel.csv")
