"""STACKED BOOK v2: equal-risk (vol-parity) weights across the 4 sleeves, margin-feasible,
scaled to a 12% target book vol. Same banked ledgers, same window. The assembly-math version.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711"
CAP = 10_000_000.0
book = pd.read_csv(OUT / "book_daily_pnl.csv", index_col=0, parse_dates=True)
sleeves = ["midsmall", "breakout", "s1f", "b1b"]
base_units = {"midsmall": 5_000_000, "breakout": 5_000_000, "s1f": 3, "b1b": 5_000_000}  # v1 sizing

# per-sleeve daily return at v1 sizing (on CAP base) -> realized vol
r = book[sleeves] / CAP
vols = r.std(ddof=1) * np.sqrt(252)
print("v1 sleeve ann-vol (on 1cr):", (vols * 100).round(1).to_dict())

# equal-risk: weight_i proportional to 1/vol_i, then scale all to hit target book vol
w = (1 / vols); w = w / w.sum()
port = (r * w).sum(axis=1) * len(sleeves)  # unit-scale combo
tgt = 0.12
scale = tgt / (port.std(ddof=1) * np.sqrt(252))
port_s = port * scale
mult = (w * len(sleeves) * scale).round(2)
print("sleeve multipliers vs v1 sizing:", mult.to_dict())

# margin feasibility at multipliers
s1_lots = 3 * mult["s1f"]
b1b_notional = 5_000_000 * mult["b1b"]
eq_gross = 5_000_000 * (mult["midsmall"] + mult["breakout"])
margin_fo = s1_lots * 270_000 + 0.15 * b1b_notional
print(f"feasibility: equity gross Rs {eq_gross/1e5:.0f}L (cap 100L incl 25% headroom OK if <=100), "
      f"S1F {s1_lots:.1f} lots + B1b {b1b_notional/1e7:.2f}cr notional -> F&O margin Rs {margin_fo/1e5:.0f}L "
      f"vs pledge ~0.75x equity = Rs {0.75*eq_gross/1e5:.0f}L -> {'FEASIBLE' if margin_fo <= 0.75*eq_gross else 'INFEASIBLE - capped'}")
if margin_fo > 0.75 * eq_gross:
    cap_scale = (0.75 * eq_gross) / margin_fo
    port_s = port * scale * cap_scale  # crude uniform cap
    print(f"applied uniform cap x{cap_scale:.2f}")

eq_curve = CAP * (1 + port_s).cumprod()
yrs = (book.index[-1] - book.index[0]).days / 365.25
cagr = (eq_curve.iloc[-1] / CAP) ** (1 / yrs) - 1
dd = ((eq_curve - eq_curve.cummax()) / eq_curve.cummax()).min()
sharpe = port_s.mean() / port_s.std(ddof=1) * np.sqrt(252)
# yearly table
yr = port_s.groupby(port_s.index.year).apply(lambda x: (1 + x).prod() - 1)
lines = [f"STACKED BOOK v2 (equal-risk, 12% vol target): CAGR {cagr*100:+.1f}% | maxDD {dd*100:.1f}% | Sharpe {sharpe:.2f}",
         f"yearly: " + " | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()),
         f"multipliers vs v1: {mult.to_dict()}"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_V2.txt").write_text(txt, encoding="utf-8")
eq_curve.to_frame("equity").to_csv(OUT / "book_equity_v2.csv")
