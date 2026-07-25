"""S1-F full metrics panel + 4-arm comparison.

Arms (all from REAL on-disk trade data, no modelling):
  A SPEC-TRUE   dyn margin (15% notional) + F1/F2 vetoes + crash rule   <- never computed before
  B AS-CHARTED  dyn margin + F1/F2, NO crash rule                       <- the existing 13.4% chart
  C RETRACTED   flat Rs 1.1L margin + F1/F2 + crash rule                <- the 28.8% figure
  D UNCOND      dyn margin, no vetoes, no crash rule                    <- tests filter value honestly

Mirrors the logic of s1f_final_graph.py / s1f_dynmargin_graph.py exactly so numbers are comparable.
Outputs: METRICS.csv, METRICS.md, S1F_4ARM.png
"""
import numpy as np, pandas as pd, datetime as dt
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = Path(__file__).parent
LOT, CAP0, DEPLOY, RATE, FLAT = 75, 1_000_000.0, 0.75, 0.15, 110_000.0

# ---- trades (S1 arm of the frozen final_three set) ----
tr = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three/final_three_trades.csv")
s1 = tr[tr.strat == "S1"].copy()
s1["date"] = pd.to_datetime(s1.day).dt.date
s1 = s1.sort_values("date").reset_index(drop=True)

# ---- NIFTY daily state for vetoes / crash rule / spot ----
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]           # landmine #2: real open >= 09:15
dcl = sp["close"].groupby(sp.index.date).last()

d = dcl.diff()
up = d.clip(lower=0).ewm(alpha=1/5, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1/5, adjust=False).mean()
rsi5 = (100 - 100 / (1 + up / dn)).shift(1)        # as of D-1
pret = dcl.pct_change().shift(1) * 100             # as of D-1
r2 = (sp["close"].pct_change() ** 2).groupby(sp.index.date).sum() ** 0.5
rv3 = r2.rolling(3).mean().shift(1)
rv3med = rv3.rolling(250, min_periods=100).median()

s1["spot"] = s1["date"].map(dcl)
s1["rsi5"] = s1["date"].map(rsi5)
s1["pret"] = s1["date"].map(pret)
s1["veto"] = ((s1.rsi5 >= 80) | (s1.rsi5 <= 20) | (s1.pret.abs() > 1.5)).fillna(False)
s1["halve"] = [bool(rv3.get(x, 0) > 2 * rv3med.get(x, np.inf)) for x in s1["date"]]
s1 = s1.dropna(subset=["spot"]).reset_index(drop=True)


def run(dyn_margin, use_veto, use_crash):
    eq, path, lots_path = CAP0, [], []
    for _, r in s1.iterrows():
        margin = (r.spot * LOT * RATE) if dyn_margin else FLAT
        lots = int(DEPLOY * eq / margin)
        if use_crash and r.halve:
            lots = max(lots // 2, 0)
        if use_veto and r.veto:
            lots = 0
        eq += r.net * LOT * lots
        path.append(eq); lots_path.append(lots)
    return pd.Series(path, index=pd.to_datetime(s1["date"])), lots_path


def xirr(cashflows, guess=0.15):
    """cashflows = [(date, amount)]; single-stake curve -> should equal CAGR."""
    t0 = cashflows[0][0]
    yrs = [(dd - t0).days / 365.0 for dd, _ in cashflows]
    amts = [a for _, a in cashflows]
    r = guess
    for _ in range(200):
        f = sum(a / (1 + r) ** t for a, t in zip(amts, yrs))
        df = sum(-t * a / (1 + r) ** (t + 1) for a, t in zip(amts, yrs))
        if abs(df) < 1e-12:
            break
        rn = r - f / df
        if abs(rn - r) < 1e-10:
            r = rn; break
        r = rn
    return r * 100


def metrics(eq, lots_path, label):
    idx = eq.index
    yrs = (idx[-1] - idx[0]).days / 365.25
    traded = np.array(lots_path) > 0
    # per-trade returns on equity (only on days size was taken)
    step = eq.pct_change().fillna(eq.iloc[0] / CAP0 - 1)
    rets = step[traded].values
    n_tr = int(traded.sum())
    tpy = n_tr / yrs
    dd = (eq - eq.cummax()) / eq.cummax()
    cagr = ((eq.iloc[-1] / CAP0) ** (1 / yrs) - 1) * 100
    x = xirr([(idx[0].to_pydatetime(), -CAP0), (idx[-1].to_pydatetime(), eq.iloc[-1])])
    sd = rets.std(ddof=1)
    sharpe = (rets.mean() / sd * np.sqrt(tpy)) if sd > 0 else np.nan
    dsd = rets[rets < 0].std(ddof=1)
    sortino = (rets.mean() / dsd * np.sqrt(tpy)) if dsd > 0 else np.nan
    wins, losses = rets[rets > 0], rets[rets < 0]
    pf = (wins.sum() / abs(losses.sum())) if losses.size and losses.sum() != 0 else np.nan
    return {
        "arm": label,
        "final_equity": round(eq.iloc[-1]),
        "CAGR_%": round(cagr, 2),
        "XIRR_%": round(x, 2),
        "maxDD_%": round(dd.min() * 100, 2),
        "Calmar": round(cagr / abs(dd.min() * 100), 2) if dd.min() != 0 else np.nan,
        "Sharpe_ann": round(sharpe, 2),
        "Sortino_ann": round(sortino, 2),
        "profit_factor": round(pf, 2) if pf == pf else np.nan,
        "trades": n_tr,
        "skipped": int(len(s1) - n_tr),
        "win_%": round(100 * wins.size / max(rets.size, 1), 1),
        "best_day_%": round(rets.max() * 100, 2),
        "worst_day_%": round(rets.min() * 100, 2),
        "lots_min": int(min(lots_path)),
        "lots_max": int(max(lots_path)),
        "span_yrs": round(yrs, 2),
    }


ARMS = [
    ("A SPEC-TRUE (dyn margin + F1/F2 + crash rule)", True,  True,  True),
    ("B AS-CHARTED (dyn margin + F1/F2, no crash)",   True,  True,  False),
    ("C RETRACTED (flat Rs1.1L + F1/F2 + crash)",     False, True,  True),
    ("D UNCONDITIONAL (dyn margin, no filters)",      True,  False, False),
]

rows, curves = [], {}
for label, dynm, vet, crash in ARMS:
    eq, lots = run(dynm, vet, crash)
    curves[label] = eq
    rows.append(metrics(eq, lots, label))

m = pd.DataFrame(rows)
m.to_csv(OUT / "METRICS.csv", index=False)
print(m.to_string(index=False))
print()
print("NOTE XIRR vs CAGR: single Rs10L stake, no interim flows -> XIRR is mathematically the same")
print("     quantity as CAGR. They differ only if capital is added/withdrawn during the run.")

with open(OUT / "METRICS.md", "w", encoding="utf-8") as fh:
    fh.write(m.to_markdown(index=False))

# ---- chart ----
INK, GRID, MUTED, SURF = "#0b0b0b", "#e1e0d9", "#898781", "#fcfcfb"
COL = {"A": "#2a78d6", "B": "#1baf7a", "C": "#c2413a", "D": "#8a8a8a"}
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.9), dpi=150, width_ratios=[1.55, 1])
fig.patch.set_facecolor(SURF)
ax = axes[0]; ax.set_facecolor(SURF)
for label, eq in curves.items():
    k = label[0]
    ls = "--" if k == "C" else ("-." if k == "D" else "-")
    ax.plot(eq.index, eq / 1e5, color=COL[k], lw=2.2 if k == "A" else 1.5, ls=ls, label=label)
    ax.annotate(f"{eq.iloc[-1]/1e5:.1f}L", (eq.index[-1], eq.iloc[-1] / 1e5),
                xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=COL[k], va="center")
ax.axhline(10, color=MUTED, lw=0.8)
ax.set_title("S1-F equity on Rs 10L, 4 arms — net of 1% slippage + TC, 259 NIFTY weekly expiries 2021-26 (Rs lakh)",
             fontsize=9.5, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=7.2, frameon=False, loc="upper left")
for s_ in ax.spines.values(): s_.set_visible(False)

ax = axes[1]; ax.set_facecolor(SURF)
for label, eq in curves.items():
    k = label[0]
    dd = (eq - eq.cummax()) / eq.cummax() * 100
    ls = "--" if k == "C" else ("-." if k == "D" else "-")
    ax.plot(eq.index, dd, color=COL[k], lw=2.0 if k == "A" else 1.3, ls=ls)
ax.set_title("Drawdown (%) — same 4 arms", fontsize=9.5, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
for s_ in ax.spines.values(): s_.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "S1F_4ARM.png", facecolor=SURF, bbox_inches="tight")
print("\nsaved ->", OUT / "S1F_4ARM.png")
