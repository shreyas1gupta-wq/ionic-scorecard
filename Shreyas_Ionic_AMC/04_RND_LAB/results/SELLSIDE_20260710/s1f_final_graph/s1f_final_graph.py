"""S1-F FINAL SPEC equity graph. Basis: final_three S1 daily net (1% slip + TC model).
Spec: F1 (skip RSI5(D-1)>=80/<=20) + F2 (skip |prior-day ret|>1.5%); size = floor(0.75*eq/1.1L)
lots, HALVED when RV3 > 2x 1-yr rolling median; compounded on Rs 10L. Shadow: unconditional S1,
same sizing. Lot 75."""
import numpy as np, pandas as pd, datetime as dt
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1f_final_graph"
OUT.mkdir(parents=True, exist_ok=True)

tr = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three/final_three_trades.csv")
s1 = tr[tr.strat == "S1"].copy()
s1["date"] = pd.to_datetime(s1.day).dt.date
s1 = s1.sort_values("date").set_index("date")["net"]

sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv", parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dcl = sp["close"].groupby(sp.index.date).last()
d = dcl.diff(); u = d.clip(lower=0).ewm(alpha=1/5, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1/5, adjust=False).mean()
rsi5 = (100 - 100 / (1 + u / dn)).shift(1)
pret = (dcl.pct_change().shift(1) * 100)
r2 = (sp["close"].pct_change() ** 2).groupby(sp.index.date).sum() ** 0.5
rv3 = r2.rolling(3).mean().shift(1)
rv3med = rv3.rolling(250, min_periods=100).median()

f = pd.DataFrame({"net": s1})
f["rsi5"] = [rsi5.get(dd, np.nan) for dd in f.index]
f["pret"] = [pret.get(dd, np.nan) for dd in f.index]
f["halve"] = [bool(rv3.get(dd, 0) > 2 * rv3med.get(dd, np.inf)) for dd in f.index]
f["veto"] = ((f.rsi5 >= 80) | (f.rsi5 <= 20) | (f.pret.abs() > 1.5)).fillna(False)

MARGIN, LOT, CAP0 = 110000.0, 75, 1_000_000.0
def run(vetoed):
    eq, path, lots_used = CAP0, [], []
    for dd, row in f.iterrows():
        lots = int(0.75 * eq / MARGIN)
        if row.halve: lots = max(lots // 2, 0)
        if vetoed and row.veto: lots = 0
        eq += row.net * LOT * lots
        path.append(eq); lots_used.append(lots)
    return pd.Series(path, index=f.index), lots_used

eq_f, lots_f = run(True)
eq_u, _ = run(False)
yrs = (pd.Timestamp(f.index[-1]) - pd.Timestamp(f.index[0])).days / 365.25
stats = []
for name, s in (("S1-F (final spec)", eq_f), ("S1 unconditional (shadow)", eq_u)):
    ddpct = ((s - s.cummax()) / s.cummax()).min() * 100
    cagr = ((s.iloc[-1] / CAP0) ** (1 / yrs) - 1) * 100
    stats.append(f"{name}: final Rs {s.iloc[-1]:,.0f} | CAGR {cagr:.1f}% | maxDD {ddpct:.1f}%")
stats.append(f"veto days: {int(f.veto.sum())}/{len(f)} | size-halved days: {int(f.halve.sum())} | span {yrs:.1f} yrs")
print("\n".join(stats))

INK, BLUE, AQUA, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#1baf7a", "#e1e0d9", "#898781", "#fcfcfb"
x = pd.to_datetime(pd.Series(f.index.astype(str)))
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), dpi=150, width_ratios=[1.6, 1])
fig.patch.set_facecolor(SURF)
ax = axes[0]; ax.set_facecolor(SURF)
ax.plot(x, eq_f / 1e5, color=BLUE, lw=2.2, label="S1-F final spec (F1+F2 vetoes, crash rule)")
ax.plot(x, eq_u / 1e5, color=AQUA, lw=1.6, label="S1 unconditional (shadow)")
ax.annotate(f"S1-F {eq_f.iloc[-1]/1e5:.1f}L", (x.iloc[-1], eq_f.iloc[-1] / 1e5), xytext=(6, 4),
            textcoords="offset points", fontsize=9, color=INK)
ax.annotate(f"S1 {eq_u.iloc[-1]/1e5:.1f}L", (x.iloc[-1], eq_u.iloc[-1] / 1e5), xytext=(6, -10),
            textcoords="offset points", fontsize=9, color=INK)
vd = f.index[f.veto]
ax.scatter(pd.to_datetime(pd.Series(vd.astype(str))), [CAP0 / 1e5 * 0.92] * len(vd), marker="|",
           color=MUTED, s=30, label=f"veto days (n={len(vd)})")
ax.set_title("S1-F final spec — equity on Rs 10L (Rs lakh), net of 1% slippage + TC, 259 expiry days 2021-26",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=7.5, frameon=False, loc="upper left")
for s_ in ax.spines.values(): s_.set_visible(False)
ax = axes[1]; ax.set_facecolor(SURF)
ddf = (eq_f - eq_f.cummax()) / eq_f.cummax() * 100
ax.fill_between(x, ddf, 0, color=BLUE, alpha=0.35, lw=0)
ax.plot(x, ddf, color=BLUE, lw=1.4)
ax.set_title("S1-F drawdown (%)", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
for s_ in ax.spines.values(): s_.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "S1F_FINAL_EQUITY.png", facecolor=SURF, bbox_inches="tight")
(OUT / "SUMMARY.md").write_text("\n".join(stats) + "\n", encoding="utf-8")
print("saved ->", OUT)
