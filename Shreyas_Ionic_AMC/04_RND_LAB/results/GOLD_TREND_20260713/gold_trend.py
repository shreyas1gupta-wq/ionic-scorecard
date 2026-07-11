"""GOLD-TREND (frozen @ a0bf3f9): 4 pre-registered trend cells on XAUUSD daily, same-long-fraction placebos."""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(163)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/GOLD_TREND_20260713"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.0012  # per side

m = pd.concat([pd.read_parquet(p) for p in
               sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/commodities_1m").glob("XAUUSD_1m_*.parquet"))])
px = m.set_index("ts")["close"].resample("1D").last().dropna()
ret = px.pct_change().fillna(0.0)
dates = px.index
month_start = pd.Series(dates.month, index=dates).diff().ne(0)
month_start.iloc[0] = False  # no signal before history
ma50, ma200 = px.rolling(50).mean(), px.rolling(200).mean()

def cell(sig_fn, tag):
    # signal evaluated at month-start close; position held from D+1 until next review
    want = pd.Series(np.nan, index=dates)
    for i in np.where(month_start.values)[0]:
        s = sig_fn(i)
        if s is not None:
            want.iloc[i] = float(s)
    pos = want.ffill().shift(1).fillna(0.0)  # D+1 execution
    trades = pos.diff().abs().fillna(0.0)
    r = pos * ret - trades * COST
    return r, pos

def perf(r, idx0=None):
    r = r if idx0 is None else r.loc[idx0:]
    e = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return e.iloc[-1] ** (1 / yrs) - 1, (e / e.cummax() - 1).min(), r.mean() / r.std(ddof=1) * np.sqrt(252)

W0 = dates[max(252, 200)] + pd.Timedelta(days=30)  # start after longest lookback warmup
bh_cagr, bh_dd, bh_sh = perf(ret, W0)

def sig_ts(look):
    return lambda i: (px.iloc[i] > px.iloc[i - look]) if i >= look else None
def sig_gc(i):
    v1, v2 = ma50.iloc[i], ma200.iloc[i]
    return (v1 > v2) if np.isfinite(v1) and np.isfinite(v2) else None

CELLS = [("G1_ts12m", sig_ts(252)), ("G2_ts6m", sig_ts(126)), ("G3_ts3m", sig_ts(63)), ("G4_gc", sig_gc)]
rows, series = [], {}
ms_idx = np.where(month_start.values)[0]
ms_idx = ms_idx[dates[ms_idx] >= W0]
for tag, fn in CELLS:
    r, pos = cell(fn, tag)
    r = r.loc[W0:]; pos = pos.loc[W0:]
    cg, dd_, sh = perf(r)
    longfrac = float((pos > 0).mean())
    # placebo: random monthly long/flat with same long fraction
    nulls = []
    for k in range(200):
        mask = pd.Series(np.nan, index=dates)
        mask.iloc[ms_idx] = (rng.random(len(ms_idx)) < longfrac).astype(float)
        p2 = mask.ffill().shift(1).fillna(0.0).loc[W0:]
        t2 = p2.diff().abs().fillna(0.0)
        r2 = p2 * ret.loc[W0:] - t2 * COST
        nulls.append(r2.mean() / r2.std(ddof=1) * np.sqrt(252))
    p95 = float(np.percentile(nulls, 95))
    ok = (sh > p95) and (dd_ > bh_dd) and (cg >= 0.08)
    rows.append(dict(cell=tag, cagr=round(cg * 100, 1), maxdd=round(dd_ * 100, 1), sharpe=round(sh, 2),
                     longfrac=round(longfrac, 2), plac95=round(p95, 2), verdict="PASS" if ok else "fail"))
    series[tag] = r
    print(rows[-1], flush=True)

df = pd.DataFrame(rows)
npass = int((df.verdict == "PASS").sum())
# corr bar vs stacked book (monthly, overlap)
book = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv",
                   index_col=0, parse_dates=True)["total"]
best = df.sort_values("sharpe", ascending=False).iloc[0].cell
g = series[best]
common = g.index.intersection(book.index)
corr_m = float(pd.concat([g.reindex(common), book.reindex(common) / 1e7], axis=1)
               .resample("ME").sum().corr().iloc[0, 1])
adopt = (npass >= 2) and (abs(corr_m) < 0.25)
lines = [f"buy&hold gold: CAGR {bh_cagr*100:+.1f}% maxDD {bh_dd*100:.1f}% Sharpe {bh_sh:.2f} (window {W0.date()}..{dates[-1].date()})",
         df.to_string(index=False),
         f"cells passed: {npass}/4 | monthly corr({best}, book) = {corr_m:+.2f} (bar |0.25|)",
         f"VERDICT: {'ADOPT-CANDIDATE' if adopt else 'NOT ADOPTED'}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "GOLD_TREND_RESULTS.txt").write_text(txt, encoding="utf-8")
pd.DataFrame({k: (1 + v).cumprod() for k, v in series.items()}).to_csv(OUT / "gold_trend_equity.csv")
