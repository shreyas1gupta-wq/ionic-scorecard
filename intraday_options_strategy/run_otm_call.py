"""Sell ~1% OTM weekly CE at 09:15, buy back at close (0.5% OTM when DTE<=1).
Intraday only, square off daily. Test all-days vs >20DMA vs <20DMA regimes.
Synthetic BS pricing at m=0.80 x VIX (trading-time). Conservative 2% slip/leg."""
import sys; from pathlib import Path
import numpy as np, pandas as pd
R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
from options.bs_pricing import bs_price
from options.option_selector import ExpiryCalendar
from config import RISK_FREE_RATE as r, DIVIDEND_YIELD as q, LOT_SIZE as LOT

P = R / "datasets" / "processed"
nif = pd.read_parquet(P / "nifty_1min.parquet")["close"]
vix = pd.read_parquet(P / "vix_1min.parquet")["vix"]
day = nif.index.normalize()
g = nif.groupby(day)
spot0 = g.first(); spotc = g.last()
vix0 = vix.groupby(vix.index.normalize()).first().reindex(spot0.index).ffill()
days = pd.DatetimeIndex(spot0.index)
sma20 = spotc.rolling(20).mean().shift(1)
above = (spot0 > sma20)
cal = ExpiryCalendar(days); dpos = {d: i for i, d in enumerate(days)}
M, SLIP, TMY = 0.80, 0.02, 252*375

rows = []
for d in days:
    if pd.isna(sma20.get(d)) or pd.isna(vix0.get(d)):
        continue
    exp = cal.next_expiry(d, min_dte=0)
    if exp not in dpos:
        continue
    dte = (exp - d).days; gap = dpos[exp] - dpos[d]
    off = 0.005 if dte <= 1 else 0.01
    s0 = float(spot0[d]); sc = float(spotc[d]); sig = float(vix0[d]) / 100 * M
    k = round(s0 * (1 + off) / 50) * 50
    t_in = (375 + 375 * gap) / TMY; t_out = (1 + 375 * gap) / TMY
    e = float(bs_price(s0, k, t_in, sig, r, q, True))
    x = float(bs_price(sc, k, t_out, sig, r, q, True))
    if e < 1:  # premium too small to bother
        continue
    ef, xf = e * (1 - SLIP), x * (1 + SLIP)
    sell, buy = ef * LOT, xf * LOT
    cost = 0.000625*sell + 0.00053*(sell+buy)*1.18 + 10*(sell+buy)/1e7 + 2*20*1.18
    pnl = (ef - xf) * LOT - cost
    rows.append({"day": d, "above": bool(above[d]), "dte": dte, "entry": e,
                 "moveup": sc/s0-1, "pnl": pnl, "s0": s0})
df = pd.DataFrame(rows)
oos = days[int(len(days)*0.70)]

def rep(sub, label):
    if len(sub) < 30:
        print(f"{label:16} n={len(sub)} (too few)"); return
    p = sub["pnl"]; w = p > 0
    daily = p  # 1 trade/day
    sh = daily.mean()/daily.std()*np.sqrt(252) if daily.std() > 0 else 0
    cum = p.cumsum(); mdd = (cum.cummax()-cum).max()
    o = sub[sub.day >= oos]["pnl"]
    sho = o.mean()/o.std()*np.sqrt(252) if len(o) > 5 and o.std() > 0 else 0
    print(f"{label:16} n={len(sub):4} WR={w.mean():.0%} avg/lot={p.mean():6.0f} "
          f"tot/lot={p.sum():9.0f} Sharpe={sh:5.2f} OOSsh={sho:5.2f} maxDD/lot={mdd:8.0f}")

print(f"SELL ~1% OTM weekly CE @09:15 -> buyback @close (0.5% if DTE<=1), m={M}, slip={SLIP:.0%}\n")
rep(df, "ALL days")
rep(df[df.above], ">20DMA (uptrend)")
rep(df[~df.above], "<20DMA (downtrend)")
print(f"\navg intraday up-move: >20DMA {df[df.above].moveup.mean()*100:+.2f}%  "
      f"<20DMA {df[~df.above].moveup.mean()*100:+.2f}%  | call goes ITM when move>+{0.01*100:.0f}%/0.5%")
print("CAVEAT: OTM calls trade at LOWER IV than ATM in India (call skew) -> m=0.80 likely "
      "OVERPRICES the call = seller looks too good. Real edge thinner; confirm with live option data.")

# --- equity curves (>20DMA strategy): 1-lot cumulative vs 0.25-Kelly compounded ---
sub = df[df.above].sort_values("day").reset_index(drop=True)
pl = sub["pnl"].values; mar = (0.09 * sub["s0"] * LOT).values
cum1 = np.cumsum(pl)                                   # 1 lot, cumulative Rs
cap = 1e7; eqk = np.empty(len(sub))
for i in range(len(sub)):
    if i >= 60:
        w = pl[i-60:i]; wn = w[w > 0]; ls = -w[w <= 0]
        if len(wn) and len(ls):
            W = len(wn)/60.0; aw = wn.mean(); al = ls.mean()
            frac = max(0.0, 0.25 * (W*aw - (1-W)*al) / aw)
        else:
            frac = 0.0
    else:
        frac = 0.05
    lots = int(min(20, max(0, frac * cap / mar[i])))
    cap += lots * pl[i]; eqk[i] = cap
print(f"\n1-LOT >20DMA: total Rs.{cum1[-1]:,.0f} over {len(sub)} trades")
print(f"0.25-KELLY >20DMA: Rs.1Cr -> Rs.{eqk[-1]:,.0f} "
      f"(CAGR {(eqk[-1]/1e7)**(252/len(sub))-1:+.0%}, peak lots ~{int(0.25*0.5*1e7/mar.mean())})")

# build 2-panel SVG
W2, H2, L2, R2 = 760, 470, 70, 20
n = len(sub); ds = np.linspace(0, n-1, 60).astype(int)
yrs = sub["day"].dt.year.values
def panel(y0, h, series, col, lab, fmt):
    lo, hi = series.min(), series.max(); rng = hi - lo or 1
    sxp = lambda i: L2 + i/(n-1)*(W2-L2-R2)
    syp = lambda v: y0 + (1-(v-lo)/rng)*h
    pts = " ".join(f"{sxp(i):.0f},{syp(series[i]):.1f}" for i in ds)
    grid = "".join(f'<line x1="{L2}" y1="{y0+f*h:.0f}" x2="{W2-R2}" y2="{y0+f*h:.0f}" stroke="#ddd" stroke-width="0.4"/>'
                   f'<text x="{L2-5}" y="{y0+f*h+3:.0f}" font-size="9" text-anchor="end" fill="#777">{fmt(hi-f*rng)}</text>'
                   for f in (0,0.5,1))
    base = syp(0) if lo <= 0 <= hi else None
    zl = f'<line x1="{L2}" y1="{base:.0f}" x2="{W2-R2}" y2="{base:.0f}" stroke="#999" stroke-width="0.6"/>' if base else ""
    return (grid + zl + f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>'
            f'<text x="{L2}" y="{y0-6:.0f}" font-size="12" font-weight="bold" fill="{col}">{lab}</text>')
xt = "".join(f'<text x="{L2+(i/(n-1))*(W2-L2-R2):.0f}" y="{H2-8}" font-size="9" text-anchor="middle" fill="#777">{yrs[i]}</text>'
             for i in ds[::12])
svg = (f'<svg viewBox="0 0 {W2} {H2}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" '
       f'role="img" aria-label="P and L curves: 1-lot cumulative and 0.25-Kelly compounded, short OTM call above 20DMA">'
       f'<title>Short OTM call (>20DMA) P&amp;L</title><rect width="{W2}" height="{H2}" fill="white"/>'
       + panel(35, 165, cum1, "#1565c0", "1 lot - cumulative Rs", lambda v: f"{v/1e5:.1f}L")
       + panel(265, 165, eqk, "#2e7d32", "0.25-Kelly on Rs.1Cr - compounded", lambda v: f"{v/1e7:.1f}Cr")
       + xt + '</svg>')
(R / "results" / "otm_call_pnl.svg").write_text(svg, encoding="utf-8")
print("SVGSTART" + svg + "SVGEND")
