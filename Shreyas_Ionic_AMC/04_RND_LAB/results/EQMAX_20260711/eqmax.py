"""EQ-MAX-CARD (frozen @ 94786d2, SINGLE-SHOT): 3 stock sleeves + vol-target 12%/20d cap [0.25,1.5]
+ 200DMA regime gate (x0.25). Window Oct-2022..Dec-2025. Bars: >=30% CAGR AND <=10% maxDD.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
R = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results"
OUT = R / "EQMAX_20260711"
OUT.mkdir(parents=True, exist_ok=True)

# sleeve A: breakout realistic REGIME NAV -> daily returns
b = pd.read_csv(R / "BREAKOUT_SCAN_20260710/realistic_nav_SL10pct_20d_REGIME.csv")
bd = next(c for c in b.columns if "date" in c.lower()); bn = next(c for c in b.columns if c != bd)
b[bd] = pd.to_datetime(b[bd])
ra = b.set_index(bd)[bn].pct_change()

# sleeve B: midsmall Var-B
g = pd.read_csv(R / "MIDSMALL_MOM_ROTATION_20260707/growth_of_1cr.csv")
dc = g.columns[0]; g[dc] = pd.to_datetime(g[dc])
vb = next(c for c in g.columns if "b" in c.lower() and ("var" in c.lower() or "variant" in c.lower()))
rb = g.set_index(dc)[vb].pct_change()

# sleeve C: TF-1 NAV
t = pd.read_csv(R / "TF1_TECHNOFUNDA_20260711/tf1_nav_main.csv", parse_dates=["date"])
rc = t.set_index("date")["nav"].pct_change()

W0, W1 = "2022-10-01", "2025-12-31"
df = pd.concat([ra, rb, rc], axis=1, keys=["brk", "mid", "tf1"]).loc[W0:W1]
df = df.dropna(how="all").fillna(0)
combo = df.mean(axis=1)  # equal-weight sleeves
print(f"days={len(combo)}, sleeve corr:\n{df.corr().round(2)}", flush=True)

# regime gate: Nifty 50 vs 200DMA
frames = [pd.read_parquet(p) for p in sorted((ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
ic = pd.concat(frames, ignore_index=True)
ic = ic[ic["Index Name"].str.strip().str.upper() == "NIFTY 50"]
nifty = pd.Series(pd.to_numeric(ic["Closing Index Value"], errors="coerce").values,
                  index=pd.to_datetime(ic["file_date"])).sort_index()
nifty = nifty[~nifty.index.duplicated()]
gate = (nifty >= nifty.rolling(200).mean()).reindex(combo.index, method="ffill").fillna(True)

# vol targeting on combined
rv = combo.rolling(20).std() * np.sqrt(252)
expo = (0.12 / rv).clip(0.25, 1.5).shift(1).fillna(1.0)   # yesterday's info only
expo = expo * np.where(gate.shift(1).fillna(True), 1.0, 0.25)
drag = 0.0002 * (pd.Series(expo, index=combo.index).diff().abs() / 0.10).fillna(0)
net = combo * expo - drag

for tag, r in [("RAW equal-weight", combo), ("EQ-MAX (vol-target + gate)", net)]:
    eqc = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eqc.iloc[-1] ** (1 / yrs) - 1
    dd = (eqc / eqc.cummax() - 1).min()
    sh = r.mean() / r.std(ddof=1) * np.sqrt(252)
    yr_tbl = " | ".join(f"{y}: {(1+v).prod()-1:+.1%}" for y, v in r.groupby(r.index.year))
    print(f"\n{tag}: CAGR {cagr*100:+.1f}% | maxDD {dd*100:.1f}% | Sharpe {sh:.2f}\n  {yr_tbl}", flush=True)
    if tag.startswith("EQ-MAX"):
        bars = (cagr >= 0.30) and (dd >= -0.10)
        stretch = cagr >= 0.40
        verdict = ("DELIVERED + STRETCH" if stretch else "DELIVERED") if bars else \
                  f"NOT DELIVERED (CAGR {cagr*100:.1f} vs 30, DD {dd*100:.1f} vs -10)"
        print(f"\nVERDICT: {verdict}", flush=True)
        (OUT / "RESULTS_RAW.txt").write_text(
            f"{tag}: CAGR {cagr*100:+.1f}% maxDD {dd*100:.1f}% Sharpe {sh:.2f}\n{yr_tbl}\nVERDICT: {verdict}\n"
            f"expo mean {expo.mean():.2f}, gate-off days {(~gate).sum()}\n", encoding="utf-8")
        eqc.to_frame("equity").to_csv(OUT / "eqmax_equity.csv")
