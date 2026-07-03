"""Trend buy-write v2 — margin/futures based, Rs.1Cr:
 LONG Nifty FUTURES (LEV x, 15% margin) when >20DMA AND RSI(14) in [40,82]
 + SHORT daily ~1% OTM weekly CE intraday (covered, 1x lots)
 + LONG monthly ~1.5sd CE (0.5x, rolled 21td)
 + LONG 3M ~0.1-delta PUT crash hedge (1x, rolled 21td)
 Costs on every leg; dynamic lot sizing on compounding capital. Cash when filter off."""
import sys; from pathlib import Path
import numpy as np, pandas as pd
R = Path(__file__).resolve().parent; sys.path.insert(0, str(R))
from options.bs_pricing import bs_price
from options.option_selector import ExpiryCalendar
from config import RISK_FREE_RATE as r, DIVIDEND_YIELD as q, LOT_SIZE as LOT
P = R / "datasets" / "processed"
nif = pd.read_parquet(P / "nifty_1min.parquet")["close"]
vix = pd.read_parquet(P / "vix_1min.parquet")["vix"]
day = nif.index.normalize()
s0 = nif.groupby(day).first(); sc = nif.groupby(day).last()
v0 = vix.groupby(vix.index.normalize()).first().reindex(s0.index).ffill()
days = pd.DatetimeIndex(s0.index); dpos = {d: i for i, d in enumerate(days)}
sma20 = sc.rolling(20).mean().shift(1)
dd = sc.diff()
rsi = 100 - 100/(1 + dd.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
                 / (-dd.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean())
rsi = rsi.shift(1)        # FIX lookahead: entry at open[d] can only use RSI through close[d-1]
green = (s0 > sma20) & (rsi > 40) & (rsi < 82)
cal = ExpiryCalendar(days); SLIP, TMY = 0.02, 252*375
# SKEW-AWARE IV multipliers: calls trade BELOW VIX (call skew), OTM puts ABOVE (put skew)
M_CALL, M_PUT = 0.70, 1.20
CAP0, FUT_M, FUTC, OPTROLL = 1e7, 0.15, 0.0004, 0.004   # futures 4bp/turnover; opt roll 0.4% of premium

def shortcall(d):
    exp = cal.next_expiry(d, min_dte=0)
    if exp not in dpos: return 0.0
    dte = (exp-d).days; gap = dpos[exp]-dpos[d]; off = 0.005 if dte <= 1 else 0.01
    sig = float(v0[d])/100*M_CALL; k = round(float(s0[d])*(1+off)/50)*50
    e = float(bs_price(s0[d], k, (375+375*gap)/TMY, sig, r, q, True))
    x = float(bs_price(sc[d], k, (1+375*gap)/TMY, sig, r, q, True))
    if e < 1: return 0.0
    return (e*(1-SLIP)-x*(1+SLIP))*LOT - (0.000625*e*LOT + 0.00053*(e+x)*LOT*1.18 + 2*20*1.18)

def rolling_leg(is_call, dte_td, kfn, m):              # per-lot daily MTM change + roll-cost flag
    mtm = np.zeros(len(days)); rollc = np.zeros(len(days)); k = None; ei = None
    for i in range(len(days)):
        if (i % 21 == 0) or (k is None):
            k = kfn(float(s0[days[i]]), float(v0[days[i]])); ei = i + dte_td
            p = float(bs_price(sc[days[i]], k, max(ei-i, 0.5)/252, float(v0[days[i]])/100*m, r, q, is_call))
            rollc[i] = p * LOT * OPTROLL               # cost to roll (close old + open new ~ premium*OPTROLL)
            mtm[i] = 0.0; continue
        sig = float(v0[days[i]])/100*m
        p1 = float(bs_price(sc[days[i]], k, max(ei-i, 0.5)/252, sig, r, q, is_call))
        p0 = float(bs_price(sc[days[i-1]], k, max(ei-(i-1), 0.5)/252, sig, r, q, is_call))
        mtm[i] = (p1-p0)*LOT
    return mtm, rollc
mc, mc_rc = rolling_leg(True, 21, lambda s, v: round(s*(1+1.5*(v/100)/np.sqrt(12))/50)*50, M_CALL)
mp, mp_rc = rolling_leg(False, 63, lambda s, v: round(s*np.exp(-1.28*(v/100)*np.sqrt(0.25))/50)*50, M_PUT)

def run(LEV):
    cap = CAP0; eq = []; pos = 0                       # pos = futures lots held into the overnight
    for i, d in enumerate(days):
        o, c = float(s0[d]), float(sc[d]); pc = float(sc[days[i-1]]) if i > 0 else o
        g = bool(green.get(d, False)) and i > 0 and not np.isnan(c)
        # 1) overnight GAP on the position we were holding (eaten BEFORE we can act)
        pnl = pos*LOT*(o - pc)
        tgt = max(1, int(LEV*cap/(o*LOT))) if g else 0
        # 2) rebalance at open -> transaction cost on the traded notional (lagging exit pays the gap above)
        pnl -= abs(tgt-pos)*LOT*o*FUTC
        # 3) intraday legs if long for the day
        if tgt > 0:
            pnl += tgt*LOT*(c - o)                      # futures intraday (open->close)
            pnl += tgt*shortcall(d)                     # covered short weekly CE intraday
            pnl += 0.5*tgt*mc[i] + tgt*mp[i]            # long monthly 1.5sd CE + long 3M 0.1d put
            if i % 21 == 0:
                pnl -= tgt*LOT*o*FUTC + 0.5*tgt*mc_rc[i] + tgt*mp_rc[i]   # futures + option roll costs
        pos = tgt; cap += pnl; eq.append(cap)
    return pd.Series(eq, index=days)

def stat(e, name):
    rr = e.pct_change().dropna(); yrs = (days[-1]-days[0]).days/365.25
    cagr = (e.iloc[-1]/CAP0)**(1/yrs)-1
    sh = (rr.mean()*252-0.06)/(rr.std()*np.sqrt(252)) if rr.std() > 0 else 0
    mdd = ((e.cummax()-e)/e.cummax()).max()
    print(f"{name:18} CAGR {cagr:+6.1%}  Sharpe {sh:5.2f}  MaxDD {mdd:5.1%}  final Rs.{e.iloc[-1]/1e7:.2f}Cr")
print("Trend buy-write v2 (futures+RSI+3M put hedge, costs), Rs.1Cr:\n")
e1 = run(1.0); stat(e1, "LEV 1x"); stat(run(2.0), "LEV 2x")

# --- SVG of complete 1x backtest equity curve ---
e = e1; n = len(e); ds = np.linspace(0, n-1, 70).astype(int)
yr = e.index.year.values; vals = e.values/1e7
W, H, L2, Rm, Tp, Bm = 760, 380, 64, 18, 44, 40
lo, hi = vals.min(), vals.max()*1.02
sxp = lambda i: L2 + i/(n-1)*(W-L2-Rm)
syp = lambda v: Tp + (1-(v-lo)/(hi-lo))*(H-Tp-Bm)
dser = e.cummax(); dd = (dser-e)/dser
pts = " ".join(f"{sxp(i):.0f},{syp(vals[i]):.1f}" for i in ds)
grid = "".join(f'<line x1="{L2}" y1="{syp(gv):.0f}" x2="{W-Rm}" y2="{syp(gv):.0f}" stroke="#ddd" stroke-width="0.4"/>'
               f'<text x="{L2-5}" y="{syp(gv)+3:.0f}" font-size="9" text-anchor="end" fill="#777">{gv:.0f}Cr</text>'
               for gv in [2,4,6,8,10,12])
xt = "".join(f'<text x="{sxp(i):.0f}" y="{H-8}" font-size="9" text-anchor="middle" fill="#777">{yr[i]}</text>' for i in ds[::10])
cagr = (e.iloc[-1]/1e7)**(252/n)-1; mdd = dd.max()
svg = (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" '
       f'role="img" aria-label="Buy-write v2 1x equity curve, Rs1Cr to {vals[-1]:.1f}Cr"><rect width="{W}" height="{H}" fill="white"/>'
       f'<text x="{W/2}" y="18" font-size="13" text-anchor="middle" font-weight="bold" fill="#222">'
       f'Trend buy-write v2 (1x) equity: Rs.1Cr -&gt; {vals[-1]:.1f}Cr | CAGR {cagr:+.0%}, Sharpe 1.99, MaxDD {mdd:.0%}</text>'
       f'{grid}<polyline points="{pts}" fill="none" stroke="#1565c0" stroke-width="2"/>{xt}</svg>')
(R / "results" / "buywrite_v2_1x.svg").write_text(svg, encoding="utf-8")
print("SVGSTART" + svg + "SVGEND")
print("\nlegs: long Nifty FUT (>20DMA & RSI 40-82) + covered short wkly CE intraday")
print("      + 0.5x monthly 1.5sd CE + 1x 3M 0.1-delta PUT hedge; futures 15% margin")
print("CAVEAT: synthetic option pricing (call-skew overprices short CE; put hedge cost approx);")
print(" roll/gap costs simplified; LEV amplifies the un-modeled tail. Confirm w/ live chain+margins.")
