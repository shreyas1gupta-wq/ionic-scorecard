"""S1-F equity curve under CORRECTED dynamic margin (15% of notional), F1/F2 vetoes, 75% deploy."""
import numpy as np, pandas as pd, datetime as dt
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1f_final_graph"
tr = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three/final_three_trades.csv")
s1 = tr[tr.strat == "S1"].copy(); s1["date"] = pd.to_datetime(s1.day).dt.date
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dcl = sp["close"].groupby(sp.index.date).last()
s1["spot"] = s1["date"].map(dcl)
s1 = s1.dropna(subset=["spot"]).sort_values("date")
d = dcl.diff(); up = d.clip(lower=0).ewm(alpha=1/5, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1/5, adjust=False).mean()
rsi5 = (100 - 100 / (1 + up / dn)).shift(1)
pret = dcl.pct_change().shift(1) * 100
s1["veto"] = s1["date"].map(lambda x: bool((rsi5.get(x, 50) >= 80) | (rsi5.get(x, 50) <= 20) | (abs(pret.get(x, 0)) > 1.5)))

LOT, RATE, CAP0 = 75, 0.15, 1_000_000.0
eq, path, lots_path = CAP0, [], []
for _, r in s1.iterrows():
    margin = r.spot * LOT * RATE
    lots = 0 if r.veto else int(0.75 * eq / margin)
    eq += r.net * LOT * lots
    path.append(eq); lots_path.append(lots)
eqs = pd.Series(path, index=s1["date"].values)
ddpct = (eqs - eqs.cummax()) / eqs.cummax() * 100
yrs = 5.0
print(f"final Rs {eqs.iloc[-1]:,.0f} | CAGR {((eqs.iloc[-1]/CAP0)**(1/yrs)-1)*100:.1f}% | maxDD {ddpct.min():.1f}% | lots {min(lots_path)}-{max(lots_path)}")

INK, BLUE, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#e1e0d9", "#898781", "#fcfcfb"
x = pd.to_datetime(pd.Series([str(dd) for dd in eqs.index]))
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), dpi=150, width_ratios=[1.6, 1])
fig.patch.set_facecolor(SURF)
ax = axes[0]; ax.set_facecolor(SURF)
ax.plot(x, eqs / 1e5, color=BLUE, lw=2.2)
ax.annotate(f"Rs {eqs.iloc[-1]/1e5:.1f}L", (x.iloc[-1], eqs.iloc[-1] / 1e5), xytext=(6, 0),
            textcoords="offset points", fontsize=10, color=INK, va="center")
ax.axhline(10, color=MUTED, lw=0.8)
ax.set_title("S1-F equity, CORRECTED dynamic margin (15% notional) — Rs 10L start, 75% deploy, "
             "net of 1% slip + TC (Rs lakh)", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
for s_ in ax.spines.values(): s_.set_visible(False)
ax = axes[1]; ax.set_facecolor(SURF)
ax.fill_between(x, ddpct, 0, color=BLUE, alpha=0.35, lw=0)
ax.plot(x, ddpct, color=BLUE, lw=1.4)
ax.set_title("Drawdown (%) — max -4.4%", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
for s_ in ax.spines.values(): s_.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "S1F_EQUITY_DYNMARGIN.png", facecolor=SURF, bbox_inches="tight")
print("saved:", OUT / "S1F_EQUITY_DYNMARGIN.png")
