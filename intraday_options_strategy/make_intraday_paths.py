"""Intraday Nifty path 09:15->close, normalized to 09:15=0%, split by 20DMA regime.
Plots all-day paths (faint) + median + mean+-1sigma + 5/95 pct, for >20DMA and <20DMA."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = Path(__file__).resolve().parent / "datasets" / "processed"
nif = pd.read_parquet(P / "nifty_1min.parquet")["close"]
day = nif.index.normalize()
mins = nif.index.hour * 60 + nif.index.minute            # minute-of-day
grid = np.arange(9*60+15, 15*60+30)                      # 09:15..15:29
# per-day path matrix (days x minutes), % from 09:15
paths = {}
for d, s in nif.groupby(day):
    m = (s.values / s.values[0] - 1) * 100
    mm = (s.index.hour*60 + s.index.minute).values
    ser = pd.Series(m, index=mm)
    ser = ser[~ser.index.duplicated(keep="last")]
    paths[d] = ser.reindex(grid).ffill()
M = pd.DataFrame(paths).T                                 # rows=days, cols=minutes
# 20DMA regime: day open vs prior-20-day-close SMA (no lookahead)
dclose = nif.groupby(day).last(); dopen = nif.groupby(day).first()
sma20 = dclose.rolling(20).mean().shift(1)
above = (dopen > sma20)
M = M.loc[M.index.isin(above.dropna().index)]
above = above.reindex(M.index)

x = (grid - grid[0]) / 60.0                               # hours from open
fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
for ax, reg, ttl in [(axes[0], above, "Nifty > 20DMA (uptrend)"),
                     (axes[1], ~above, "Nifty < 20DMA (downtrend)")]:
    sub = M.loc[reg.values]
    n = len(sub)
    for _, row in sub.sample(min(120, n), random_state=1).iterrows():
        ax.plot(x, row.values, color="grey", alpha=0.04, lw=0.5)
    med = sub.median(); mu = sub.mean(); sd = sub.std()
    ax.plot(x, med.values, "b-", lw=2, label="median")
    ax.plot(x, (mu+sd).values, "r--", lw=1.5, label="mean +1 SD")
    ax.plot(x, (mu-sd).values, "r--", lw=1.5, label="mean -1 SD")
    ax.plot(x, sub.quantile(.95).values, "g:", lw=1, label="95th pct")
    ax.plot(x, sub.quantile(.05).values, "g:", lw=1, label="5th pct")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title(f"{ttl}  (N={n} days)"); ax.set_xlabel("hours from 09:15")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
axes[0].set_ylabel("intraday move from 09:15 (%)")
fig.suptitle("Nifty intraday path distribution 09:15->15:30 by 20DMA regime (2015-2026)")
fig.tight_layout()
out = Path(__file__).resolve().parent / "results" / "intraday_paths_by_20dma.png"
out.parent.mkdir(exist_ok=True); fig.savefig(out, dpi=130)
print(f"saved -> {out}")

# --- compact SVG (downsampled, both regimes overlaid: median + -+1 SD band) ---
W, H, L, R, T, B = 760, 430, 60, 20, 40, 50
ymin, ymax = -2.6, 2.6
def sx(h): return L + (h / x[-1]) * (W - L - R)
def sy(v): return T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B)
ds = np.linspace(0, len(grid) - 1, 26).astype(int)
xs = x[ds]
def band(sub, col, fill):
    mu, sd = sub.mean().values[ds], sub.std().values[ds]
    md = sub.median().values[ds]
    up = " ".join(f"{sx(h):.0f},{sy(m+s):.1f}" for h, m, s in zip(xs, mu, sd))
    dn = " ".join(f"{sx(h):.0f},{sy(m-s):.1f}" for h, m, s in zip(xs[::-1], mu[::-1], sd[::-1]))
    mp = " ".join(f"{sx(h):.0f},{sy(v):.1f}" for h, v in zip(xs, md))
    return (f'<polygon points="{up} {dn}" fill="{fill}" opacity="0.18"/>'
            f'<polyline points="{mp}" fill="none" stroke="{col}" stroke-width="2.5"/>')
g1 = band(M.loc[above.values], "#1565c0", "#1565c0")
g2 = band(M.loc[(~above).values], "#c62828", "#c62828")
gl = "".join(f'<line x1="{L}" y1="{sy(v):.0f}" x2="{W-R}" y2="{sy(v):.0f}" stroke="#ccc" stroke-width="0.5"/>'
             f'<text x="{L-6}" y="{sy(v)+3:.0f}" font-size="10" text-anchor="end" fill="#666">{v:+.0f}%</text>'
             for v in [-2, -1, 0, 1, 2])
xt = "".join(f'<text x="{sx(h):.0f}" y="{H-B+15:.0f}" font-size="10" text-anchor="middle" fill="#666">{int(9+h)}:{"15" if h==0 else "00" if (9+h)%1==0 else ""}</text>'
             for h in [0,1,2,3,4,5,6])
svg = (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">'
       f'<rect width="{W}" height="{H}" fill="white"/>'
       f'<text x="{W/2}" y="20" font-size="14" text-anchor="middle" font-weight="bold">Nifty intraday path 09:15-15:30 by 20DMA regime (median +- 1 SD)</text>'
       f'{gl}{g1}{g2}'
       f'<text x="{W-R}" y="{T+14}" font-size="11" text-anchor="end" fill="#1565c0">&gt;20DMA (uptrend, N={int(above.sum())}): SD 0.64%</text>'
       f'<text x="{W-R}" y="{T+30}" font-size="11" text-anchor="end" fill="#c62828">&lt;20DMA (downtrend, N={int((~above).sum())}): SD 1.05%</text>'
       f'{xt}<text x="{W/2}" y="{H-8}" font-size="10" text-anchor="middle" fill="#666">time of day</text></svg>')
(out.parent / "intraday_paths.svg").write_text(svg, encoding="utf-8")
print("SVG_WRITTEN")
print(f"days: >20DMA={int(above.sum())}  <20DMA={int((~above).sum())}")
for reg, ttl in [(above, ">20DMA"), (~above, "<20DMA")]:
    sub = M.loc[reg.values]; eod = sub.iloc[:, -1]
    print(f"{ttl}: EOD move median {eod.median():+.2f}%  mean {eod.mean():+.2f}%  "
          f"SD {eod.std():.2f}%  |move|median {eod.abs().median():.2f}%")
