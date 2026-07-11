"""ALPHA FORGE assembly PREVIEW (NOT certification - zero formal passes; frozen rules require
wave-B). Preview book on the 5 both-window-positive sleeves per frozen assembly mechanics:
|corr|<=0.35 greedy, equal-risk, 200DMA hedge, <=1.25x. Full 2016-2026.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/ALPHA_FORGE"
CAND = ["AF07", "AF03", "AF01", "AF08", "AF05"]  # both-window-positive, ordered by combined strength
S = {t: pd.read_parquet(OUT / "series" / f"{t}.parquet")[t] for t in CAND}
df = pd.DataFrame(S).fillna(0).loc["2016-01-01":"2026-06-30"]
corr = df.corr()
print("corr matrix:\n", corr.round(2).to_string(), flush=True)

# greedy corr filter
chosen = []
for t in CAND:
    if all(abs(corr.loc[t, c]) <= 0.35 for c in chosen):
        chosen.append(t)
print("chosen:", chosen, flush=True)

sub = df[chosen]
vols = sub.std(ddof=1) * np.sqrt(252)
w = (1 / vols); w = w / w.sum()
book = (sub * w).sum(axis=1)

# hedge overlay: Nifty<200DMA -> short index futures 25% of net exposure (index short allowed)
idxf = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
IC = pd.concat(idxf, ignore_index=True)
IC = IC[IC["Index Name"].str.strip().str.upper() == "NIFTY 50"]
nifty = pd.Series(pd.to_numeric(IC["Closing Index Value"], errors="coerce").values,
                  index=pd.to_datetime(IC["file_date"])).sort_index()
nifty = nifty[~nifty.index.duplicated()]
bad = (nifty < nifty.rolling(200).mean()).reindex(book.index, method="ffill").fillna(False)
nret = nifty.pct_change().reindex(book.index).fillna(0)
hedge = np.where(bad.shift(1).fillna(False), -0.25 * nret, 0.0)

# leverage to 1.25x
lev = 1.25
r = (book * lev) + hedge
eq = (1 + r).cumprod()
yrs = (r.index[-1] - r.index[0]).days / 365.25
cagr = eq.iloc[-1] ** (1 / yrs) - 1
dd = (eq / eq.cummax() - 1).min()
sh = r.mean() / r.std(ddof=1) * np.sqrt(252)
yr_tbl = " | ".join(f"{y}: {(1+v).prod()-1:+.1%}" for y, v in r.groupby(r.index.year))
lines = [f"PREVIEW BOOK ({'+'.join(chosen)}, equal-risk, 1.25x, 200DMA hedge), 2016-2026:",
         f"CAGR {cagr*100:+.1f}% | maxDD {dd*100:.1f}% | Sharpe {sh:.2f}",
         yr_tbl,
         "STATUS: PREVIEW ONLY - zero sleeves formally passed the frozen dual bar; wave-B required before certification."]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "PREVIEW_BOOK.txt").write_text(txt + "\n" + corr.round(2).to_string(), encoding="utf-8")
eq.to_frame("equity").to_csv(OUT / "preview_book_equity.csv")
