"""BOOK-LEVEL monthly heatmap + maxDD + metrics (2026-07-30).

CAPITAL-BASE HONESTY (the thing that makes or breaks this):
the sleeves are denominated differently on disk, so they CANNOT simply be added.
  - STACKED_BOOK book_daily_pnl.csv .... rupee P&L generated on a Rs1cr base
  - SWEEP trades_*_1lot.csv ............ rupee P&L at a FIXED 1 lot (natural unit, indep. of capital)
  - SWING all_trades.csv ............... rupee P&L sized on Rs1cr at 1% risk/trade (has a `lots` col)
  - CALENDAR grid_a_trades_raw.csv ..... net_pts -> x75 = 1-lot rupees
Construction used below, stated so it can be argued with:
  BOOK_CAP = Rs1cr. Each new sleeve gets a 10% allocation = Rs10L.
  * SWEEP at 1 lot already IS a ~Rs10L-margin position (10% margin ruling) -> raw P&L used as-is.
  * CALENDAR at 1 lot is a much smaller position; reported as-is AND scaled to equal-risk.
  * SWING was sized on Rs1cr, so it is scaled by 0.10 to represent a Rs10L allocation.
Because spans differ wildly (book 2022-2025, sweep 2015-2026, swing 2021-2026, calendar 2011-2026)
TWO books are produced:
  BOOK_A = full 4-sleeve existing book + sweep + swing + calendar, on the COMMON window only.
  BOOK_B = the NEW sleeves only (sweep + calendar), which have long history, 2015-2026.
Both get a monthly heatmap, maxDD on the real equity path, and a metrics block.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = Path(__file__).parent
BOOK_CAP = 1_00_00_000.0     # Rs 1 crore
LOT, CARRY_M = 75, 0.005


def dsum(df, dcol, vcol):
    d = df[[dcol, vcol]].copy()
    d[dcol] = pd.to_datetime(d[dcol])
    return d.groupby(d[dcol].dt.normalize())[vcol].sum().sort_index()


S = {}

# existing 4-sleeve book (Rs1cr basis) ------------------------------------------------------
bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0)
bk.index = pd.to_datetime(bk.index)
S["existing_book"] = bk["total"].sort_index()

# sweep E, carry-adjusted, 1 lot ------------------------------------------------------------
t = pd.read_csv(R / "SWEEP_11YR_20260729" / "trades_E_swing3_trail60_1lot.csv")
t["date"] = pd.to_datetime(t["date"])
carry = t["entry"] * (CARRY_M / 30.0) * np.maximum(t["hold_min"] / 375.0, 0.5)
t["net_adj"] = (t["gross_pts"] - np.sign(t["dir"]) * carry) * LOT - t["cost"]
S["sweep_E"] = dsum(t, "date", "net_adj")

# calendar 1x1 3d_before, NET, 1 lot --------------------------------------------------------
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
c["net_rs"] = c["net_pts"] * LOT
S["calendar_1x1"] = dsum(c, "exit_day", "net_rs")

# swing prior-week fixed_10, scaled 0.10 (was sized on Rs1cr) -------------------------------
sw = pd.read_csv(R / "SWING_DELTA1_20260729" / "all_trades.csv")
m = [x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
if m:
    q = sw[sw["cell"] == m[0]].copy()
    q["net_scaled"] = q["net"] * 0.10
    S["swing_pw10"] = dsum(q, "exit_date", "net_scaled")


def metrics(s: pd.Series, cap: float, name: str) -> dict:
    s = s.sort_index()
    eq = cap + s.cumsum()
    pk = eq.cummax()
    dd = (eq - pk) / pk
    yrs = max((s.index.max() - s.index.min()).days / 365.25, .01)
    cagr = (float(eq.iloc[-1]) / cap) ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else np.nan
    r = s / cap
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
    so = float(r.mean() / r[r < 0].std() * np.sqrt(252)) if (r < 0).any() else np.nan
    mo = s.resample("ME").sum()
    w, l = s[s > 0], s[s <= 0]
    x = s.values.astype(float); mu, n = x.mean(), len(x); dv = x - mu
    v = (dv @ dv) / n
    for L in range(1, 6):
        v += 2 * (1 - L / 6) * ((dv[L:] @ dv[:-L]) / n)
    tst = mu / np.sqrt(v / n) if v > 0 else np.nan
    # drawdown duration
    under = dd < -1e-9
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return {"book": name, "span": f"{s.index.min():%Y-%m}..{s.index.max():%Y-%m}",
            "years": round(yrs, 2), "capital_rs": int(cap),
            "net_total_rs": round(float(s.sum())),
            "CAGR_pct": round(100 * cagr, 2) if np.isfinite(cagr) else None,
            "maxDD_pct": round(100 * float(dd.min()), 2),
            "maxDD_rs": round(float((eq - pk).min())),
            "longest_DD_days": int(longest),
            "Calmar": round(float(cagr / abs(dd.min())), 2) if dd.min() else None,
            "Sharpe": round(sh, 2), "Sortino": round(so, 2),
            "NW_t": round(float(tst), 2),
            "PF": round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
            "months": int(len(mo)), "months_pos": int((mo > 0).sum()),
            "month_win_pct": round(100 * float((mo > 0).mean()), 1),
            "best_month_pct": round(100 * float(mo.max() / cap), 2),
            "worst_month_pct": round(100 * float(mo.min() / cap), 2),
            "worst_day_pct": round(100 * float(s.min() / cap), 2),
            "years_pos": int((s.resample("YE").sum() > 0).sum()),
            "years_total": int(len(s.resample("YE").sum()))}


def heat(s: pd.Series, cap: float, title: str) -> pd.DataFrame:
    mo = s.resample("ME").sum()
    d = pd.DataFrame({"y": mo.index.year, "m": mo.index.month, "v": 100 * mo.values / cap})
    p = d.pivot_table(index="y", columns="m", values="v", aggfunc="sum").reindex(columns=range(1, 13))
    p["YEAR"] = p.sum(axis=1, min_count=1)
    print(f"\n{'=' * 104}\n{title}   (monthly % of Rs{cap/1e7:.2f}cr book capital)\n{'=' * 104}")
    hdr = "Year |" + "".join(f"{x:>7}" for x in
                             ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                              "Nov", "Dec"]) + f"{'YEAR':>9}"
    print(hdr); print("-" * len(hdr))
    for y, row in p.iterrows():
        cells = "".join(("      ." if pd.isna(row[mm]) else f"{row[mm]:>7.2f}") for mm in range(1, 13))
        yv = row["YEAR"]
        print(f"{int(y)} |{cells}{('     .' if pd.isna(yv) else f'{yv:>9.2f}')}")
    yr = p["YEAR"].dropna()
    print(f"  positive years {(yr > 0).sum()}/{len(yr)}   positive months "
          f"{int((mo > 0).sum())}/{len(mo)} ({100*(mo>0).mean():.1f}%)")
    return p


rows = []

# ---------------- BOOK A: everything, common window
common_lo = max(s.index.min() for s in S.values())
common_hi = min(s.index.max() for s in S.values())
idx = pd.date_range(common_lo, common_hi, freq="D")
A = sum(s.reindex(idx).fillna(0.0) for s in S.values())
A = A[A.index >= common_lo]
print(f"\nBOOK A window = {common_lo:%Y-%m-%d} .. {common_hi:%Y-%m-%d}  (all {len(S)} sleeves live)")
for k, s in S.items():
    seg = s[(s.index >= common_lo) & (s.index <= common_hi)]
    print(f"   {k:<16} {len(seg):>4} active days  net Rs{seg.sum():>12,.0f}")
heat(A, BOOK_CAP, "BOOK A  = existing book + sweep_E + calendar + swing(x0.10)").to_csv(OUT / "heatmap_bookA.csv")
rows.append(metrics(A, BOOK_CAP, "BOOK_A_all_sleeves"))
# baseline for comparison
eb = S["existing_book"]
eb = eb[(eb.index >= common_lo) & (eb.index <= common_hi)]
rows.append(metrics(eb, BOOK_CAP, "BASELINE_existing_book_only"))

# ---------------- BOOK B: new sleeves only, long history
NEW = ["sweep_E", "calendar_1x1"]
lo = max(S[k].index.min() for k in NEW); hi = min(S[k].index.max() for k in NEW)
idx2 = pd.date_range(lo, hi, freq="D")
B = sum(S[k].reindex(idx2).fillna(0.0) for k in NEW)
CAP_B = 20_00_000.0     # Rs10L sweep + Rs10L calendar
print(f"\nBOOK B window = {lo:%Y-%m-%d} .. {hi:%Y-%m-%d}  (sweep_E + calendar only, long history)")
heat(B, CAP_B, "BOOK B  = sweep_E + calendar_1x1  (new sleeves, 2015-2026)").to_csv(OUT / "heatmap_bookB.csv")
rows.append(metrics(B, CAP_B, "BOOK_B_new_sleeves"))
for k in NEW:
    rows.append(metrics(S[k], 10_00_000.0, f"solo_{k}"))

mt = pd.DataFrame(rows)
mt.to_csv(OUT / "book_level_metrics.csv", index=False)
print(f"\n{'=' * 104}\nBOOK-LEVEL METRICS\n{'=' * 104}")
show = ["book", "span", "years", "CAGR_pct", "maxDD_pct", "longest_DD_days", "Calmar", "Sharpe",
        "Sortino", "NW_t", "PF", "month_win_pct", "worst_month_pct", "worst_day_pct",
        "years_pos", "years_total"]
print(mt[[c for c in show if c in mt.columns]].to_string(index=False))
print("\nwrote heatmap_bookA.csv, heatmap_bookB.csv, book_level_metrics.csv")
