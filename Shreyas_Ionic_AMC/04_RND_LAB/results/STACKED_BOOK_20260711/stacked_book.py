"""STACKED BOOK: combine the 4 banked alphas on Rs 1cr with capital reuse (pledged collateral),
2022-01..2025-12. Sleeves: midsmall rotation VarB (50L equity), breakout swing (50L equity),
S1-F 0DTE straddle (3 lots on expiry days, margin from pledge), B1b flow (Rs 50L notional
futures when q4, margin from pledge). Honest correlations + contributions reported.
Capital feasibility: equity 1cr pledged ~ 75L collateral >> S1-F 8L + B1b 7.5L peak concurrent margin.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
R = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results"
OUT = R / "STACKED_BOOK_20260711"
OUT.mkdir(parents=True, exist_ok=True)
W0, W1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2025-12-31")
CAP = 10_000_000.0

# --- sleeve daily rupee P&L series ---
# 1. midsmall VarB: 50L tracking its NAV
g = pd.read_csv(R / "MIDSMALL_MOM_ROTATION_20260707/growth_of_1cr.csv")
dcol = g.columns[0]; g[dcol] = pd.to_datetime(g[dcol])
vb = next(c for c in g.columns if "b" in c.lower() and ("var" in c.lower() or "variant" in c.lower()))
nav_m = g.set_index(dcol)[vb].loc[W0:W1]
pnl_mid = (nav_m.pct_change() * 5_000_000).fillna(0)

# 2. breakout swing: realistic regime ledger P&L was on its own sizing; rescale to 50L book
b = pd.read_csv(R / "BREAKOUT_SCAN_20260710/realistic_nav_SL10pct_20d_REGIME.csv")
bd = next(c for c in b.columns if "date" in c.lower()); bn = next(c for c in b.columns if c != bd)
b[bd] = pd.to_datetime(b[bd])
nav_b = b.set_index(bd)[bn].loc[W0:W1]
pnl_brk = (nav_b.pct_change() * 5_000_000).fillna(0)

# 3. S1-F: expiry-day nets (pts) x 75 x 3 lots
tr = pd.read_csv(R / "SELLSIDE_20260710/final_three/final_three_trades.csv")
s1 = tr[tr.strat == "S1"].copy(); s1["day"] = pd.to_datetime(s1.day)
s1 = s1[(s1.day >= W0) & (s1.day <= W1)]
pnl_s1 = pd.Series(s1.net.values * 75 * 3, index=s1.day)

# 4. B1b: daily trade bps on Rs 50L notional
g4 = pd.read_csv(R / "B1b_GATE4_20260711/gate4_daily.csv", parse_dates=["day"])
g4 = g4[(g4.day >= W0) & (g4.day <= W1)]
pnl_b1b = pd.Series(g4.trade.values / 1e4 * 5_000_000, index=g4.day)

cal = pd.date_range(W0, W1, freq="D")
book = pd.DataFrame(index=cal)
for name, s in [("midsmall", pnl_mid), ("breakout", pnl_brk), ("s1f", pnl_s1), ("b1b", pnl_b1b)]:
    book[name] = s.groupby(s.index).sum().reindex(cal).fillna(0)
book = book[book.abs().sum(axis=1) > 0]  # trading days only
book["total"] = book.sum(axis=1)

eq = CAP + book.total.cumsum()
ret = book.total / eq.shift(1).fillna(CAP)
yrs = (book.index[-1] - book.index[0]).days / 365.25
cagr = (eq.iloc[-1] / CAP) ** (1 / yrs) - 1
dd = ((eq - eq.cummax()) / eq.cummax()).min()
sharpe = ret.mean() / ret.std(ddof=1) * np.sqrt(252)

corr = book[["midsmall", "breakout", "s1f", "b1b"]].corr().round(2)
contrib = book[["midsmall", "breakout", "s1f", "b1b"]].sum() / 1e5

lines = [f"STACKED BOOK Rs 1cr, {book.index[0].date()}..{book.index[-1].date()} ({yrs:.1f}y)",
         f"final equity Rs {eq.iloc[-1]:,.0f} | CAGR {cagr*100:+.1f}% | maxDD {dd*100:.1f}% | Sharpe {sharpe:.2f}",
         f"sleeve contributions (Rs lakh): {contrib.round(1).to_dict()}",
         "sleeve correlations:", corr.to_string(),
         f"peak concurrent F&O margin needed: ~Rs {8+7.5:.0f}L vs ~75L pledge collateral -> feasible",
         "NOTE: in-sample assembly of separately-validated sleeves; sleeve stage varies (S1-F/B1b gauntlet-passed;",
         "breakout/midsmall pre-red-team). Paper-first law applies to the BOOK exactly as to sleeves."]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
book.to_csv(OUT / "book_daily_pnl.csv")
eq.to_frame("equity").to_csv(OUT / "book_equity.csv")
