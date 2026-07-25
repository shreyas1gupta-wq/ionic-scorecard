"""Equity curves + full metrics for the three DTE arms, on identical sizing rules.

Sizing = the corrected S1-F model: margin = spot*75*0.15, lots = floor(0.75*equity/margin),
Rs 10L start, NO F1/F2 vetoes (these are the raw arms, so all three are comparable).
Spot proxied by the ATM strike (rounded to 50) -> margin accurate to ~0.2%, immaterial.
"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent
LOT, CAP0, DEPLOY, RATE = 75, 1_000_000.0, 0.75, 0.15
t = pd.read_csv(OUT / "trades_1dte.csv")
t["day"] = pd.to_datetime(t["day"])
t = t.sort_values("day")


def xirr(flows, guess=0.15):
    t0 = flows[0][0]
    yrs = [(d - t0).days / 365.0 for d, _ in flows]
    amt = [a for _, a in flows]
    r = guess
    for _ in range(200):
        f = sum(a / (1 + r) ** y for a, y in zip(amt, yrs))
        df = sum(-y * a / (1 + r) ** (y + 1) for a, y in zip(amt, yrs))
        if abs(df) < 1e-12:
            break
        rn = r - f / df
        if abs(rn - r) < 1e-10:
            r = rn; break
        r = rn
    return r * 100


rows, curves, cumpts = [], {}, {}
for st, g in t.groupby("strat"):
    g = g.sort_values("day").reset_index(drop=True)
    eq, path, lots_all = CAP0, [], []
    for _, r in g.iterrows():
        margin = r.strike * LOT * RATE
        lots = int(DEPLOY * eq / margin)
        eq += r.net * LOT * lots
        path.append(eq); lots_all.append(lots)
    e = pd.Series(path, index=g["day"])
    curves[st] = e
    cumpts[st] = pd.Series(g["net"].cumsum().values, index=g["day"])
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    dd = (e - e.cummax()) / e.cummax()
    step = e.pct_change().fillna(e.iloc[0] / CAP0 - 1)
    rt = step.values
    tpy = len(rt) / yrs
    cagr = ((e.iloc[-1] / CAP0) ** (1 / yrs) - 1) * 100
    sd, dsd = rt.std(ddof=1), rt[rt < 0].std(ddof=1)
    w, l = rt[rt > 0], rt[rt < 0]
    rows.append(dict(
        arm=st, final_equity=round(e.iloc[-1]), CAGR_pct=round(cagr, 2),
        XIRR_pct=round(xirr([(e.index[0].to_pydatetime(), -CAP0),
                             (e.index[-1].to_pydatetime(), e.iloc[-1])]), 2),
        maxDD_pct=round(dd.min() * 100, 2),
        Calmar=round(cagr / abs(dd.min() * 100), 2),
        Sharpe_ann=round(rt.mean() / sd * np.sqrt(tpy), 2),
        Sortino_ann=round(rt.mean() / dsd * np.sqrt(tpy), 2) if dsd > 0 else np.nan,
        PF=round(w.sum() / abs(l.sum()), 2),
        win_pct=round(100 * len(w) / len(rt), 1),
        worst_day_pct=round(rt.min() * 100, 2), best_day_pct=round(rt.max() * 100, 2),
        lots_max=int(max(lots_all)), n=len(g), span_yrs=round(yrs, 2)))

m = pd.DataFrame(rows).sort_values("arm")
m.to_csv(OUT / "EQ_METRICS_1DTE.csv", index=False)
with open(OUT / "EQ_METRICS_1DTE.md", "w", encoding="utf-8") as fh:
    fh.write(m.to_markdown(index=False))
print(m.to_string(index=False))

# era split on raw pts
print("\n=== era split (raw pts/day) ===")
for st, g in t.groupby("strat"):
    a = g[g.day < "2024-01-01"]["net"].mean()
    b = g[g.day >= "2024-01-01"]["net"].mean()
    print(f"  {st:15s} 2021-23 {a:+7.2f} | 2024-26 {b:+7.2f}")

print("\n=== 5 worst days per arm (pts) ===")
for st, g in t.groupby("strat"):
    ws = g.nsmallest(5, "net")[["day", "net"]]
    print(f"  {st}: " + ", ".join(f"{d.date()} {v:.0f}" for d, v in zip(ws.day, ws.net)))

INK, GRID, MUTED, SURF = "#0b0b0b", "#e1e0d9", "#898781", "#fcfcfb"
COL = {"S1_0DTE": "#2a78d6", "S1_1DTE_CLOSE": "#c2413a", "S1_1DTE_OPEN": "#eda100"}
LBL = {"S1_0DTE": "0DTE  entry D0 09:20 (live spec)",
       "S1_1DTE_CLOSE": "1DTE  entry D-1 15:25",
       "S1_1DTE_OPEN": "1DTE  entry D-1 09:20"}
fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.6), dpi=150, width_ratios=[1.25, 1.25, 1])
fig.patch.set_facecolor(SURF)

ax = axes[0]; ax.set_facecolor(SURF)
for st, s in cumpts.items():
    ax.plot(s.index, s.values, color=COL[st], lw=1.9, label=LBL[st])
    ax.annotate(f"{s.iloc[-1]:+.0f}", (s.index[-1], s.iloc[-1]), xytext=(5, 0),
                textcoords="offset points", fontsize=8.5, color=COL[st], va="center")
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_title("Cumulative P&L per 1 lot (NIFTY points), net of 1% slip + TC — 259 weekly expiries",
             fontsize=9.3, color=INK, loc="left")
ax.legend(fontsize=7.6, frameon=False, loc="upper left")

ax = axes[1]; ax.set_facecolor(SURF)
for st, e in curves.items():
    ax.plot(e.index, e / 1e5, color=COL[st], lw=1.9)
    ax.annotate(f"{e.iloc[-1]/1e5:.1f}L", (e.index[-1], e.iloc[-1] / 1e5), xytext=(5, 0),
                textcoords="offset points", fontsize=8.5, color=COL[st], va="center")
ax.axhline(10, color=MUTED, lw=0.8)
ax.set_title("Equity on Rs 10L, identical sizing (dyn margin 15%, 75% deploy, no vetoes) — Rs lakh",
             fontsize=9.3, color=INK, loc="left")

ax = axes[2]; ax.set_facecolor(SURF)
for st, e in curves.items():
    ax.plot(e.index, (e - e.cummax()) / e.cummax() * 100, color=COL[st], lw=1.6)
ax.set_title("Drawdown (%)", fontsize=9.3, color=INK, loc="left")

for ax in axes:
    ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
    for s_ in ax.spines.values(): s_.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "DTE_3ARM.png", facecolor=SURF, bbox_inches="tight")
print("\nsaved ->", OUT / "DTE_3ARM.png")
