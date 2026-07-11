"""STACKED BOOK v3: full-deployment feasible sizing. Equity 100L invested (50 midsmall / 50 breakout,
natural sizing) -> pledge ~75L collateral -> S1-F 8 lots (spec-consistent for a 30L allocation)
+ B1b Rs 1.5cr futures notional (22.5L margin). Total F&O margin 44L <= 75L (31L stress headroom).
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711"
CAP = 10_000_000.0
book = pd.read_csv(OUT / "book_daily_pnl.csv", index_col=0, parse_dates=True)
# v1 units: midsmall 50L, breakout 50L, s1f 3 lots, b1b 50L notional
mult = {"midsmall": 1.0, "breakout": 1.0, "s1f": 8 / 3, "b1b": 3.0}
pnl = sum(book[k] * m for k, m in mult.items())
ret = pnl / CAP  # P&L on the 1cr book (approximation: no compounding of sleeve sizes)
eq = CAP * (1 + ret).cumprod()
yrs = (book.index[-1] - book.index[0]).days / 365.25
cagr = (eq.iloc[-1] / CAP) ** (1 / yrs) - 1
dd = ((eq - eq.cummax()) / eq.cummax()).min()
sharpe = ret.mean() / ret.std(ddof=1) * np.sqrt(252)
yr = ret.groupby(ret.index.year).apply(lambda x: (1 + x).prod() - 1)
worst5 = pnl.nsmallest(5)
lines = [f"STACKED BOOK v3 (full deploy: 100L equity + 8-lot S1F + 1.5cr B1b on pledge):",
         f"CAGR {cagr*100:+.1f}% | maxDD {dd*100:.1f}% | Sharpe {sharpe:.2f}",
         "yearly: " + " | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()),
         f"worst-5 days (Rs): " + ", ".join(f"{d.date()}: {v:,.0f}" for d, v in worst5.items()),
         f"F&O margin steady-state 44L vs 75L pledge (stress headroom 31L; S1F crash-halving still applies)"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_V3.txt").write_text(txt, encoding="utf-8")
eq.to_frame("equity").to_csv(OUT / "book_equity_v3.csv")
