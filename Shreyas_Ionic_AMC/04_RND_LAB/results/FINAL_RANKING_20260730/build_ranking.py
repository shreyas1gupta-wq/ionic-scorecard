"""FINAL CROSS-STRATEGY RANKING + CORRELATION RECHECK (2026-07-30).

Principal ask: "recheck for corl. of selected strategies ... show me top 5 strategies and
their logic and metrics".

METHOD
- Every series is rebuilt from the REAL per-trade CSV on disk. Nothing is re-typed from prose.
- Correlations at DAILY / MONTHLY / QUARTERLY. The firm has established that DAILY sleeve
  correlation is an ARTIFACT (stacked book: 0.08 daily -> 0.53 quarterly), so the VERDICT is
  taken from monthly+quarterly, and only when the two AGREE in sign. Sign disagreement = noise.
- Correlations use only the OVERLAPPING dates of each pair (reported per pair, since spans differ
  wildly: sweep 2015-2026, swing 2021-2026, calendar 2011-2026, book 2022-2025).
- Metrics on a common Rs10L 1-lot convention where the source used it.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = Path(__file__).parent
CAP = 10_00_000.0
LOT = 75


def daily_from(df, datecol, netcol):
    d = df[[datecol, netcol]].copy()
    d[datecol] = pd.to_datetime(d[datecol])
    return d.groupby(d[datecol].dt.normalize())[netcol].sum().sort_index()


series: dict[str, pd.Series] = {}
meta: dict[str, dict] = {}

# ---- 1/2. SWEEP 11yr, configs E and D (delta-1, 1 lot, carry-adjusted here) -------------
CARRY_M = 0.005
for tag, fn in (("SWEEP_E_swing3", "trades_E_swing3_trail60_1lot.csv"),
                ("SWEEP_D_overnight", "trades_D_overnight1_trail40_1lot.csv")):
    p = R / "SWEEP_11YR_20260729" / fn
    t = pd.read_csv(p)
    t["date"] = pd.to_datetime(t["date"])
    hold_sessions = np.maximum(t["hold_min"] / 375.0, 0.5)
    carry = t["entry"] * (CARRY_M / 30.0) * hold_sessions
    eff = t["gross_pts"] - np.sign(t["dir"]) * carry          # long pays, short receives
    t["net_adj"] = eff * LOT - t["cost"]
    series[tag] = daily_from(t, "date", "net_adj")
    meta[tag] = {"source": str(p.relative_to(R)), "n_trades": int(len(t)),
                 "span": f"{t.date.min():%Y-%m-%d}..{t.date.max():%Y-%m-%d}",
                 "pct_short": round(float((t.dir < 0).mean()) * 100, 1),
                 "carry_applied": True}

# ---- 3. SWING delta-1, the IC-flagged low-frequency cell ---------------------------------
p = R / "SWING_DELTA1_20260729" / "all_trades.csv"
sw = pd.read_csv(p)
cell = "D_priorweek_sweep_long__fixed_10"
cand = sw[sw["cell"] == cell]
if cand.empty:                      # fall back to the closest matching cell name
    m = [c for c in sw["cell"].unique() if "priorweek" in c and "fixed_10" in c]
    cand = sw[sw["cell"] == m[0]] if m else sw.iloc[0:0]
    cell = m[0] if m else "NOT_FOUND"
if not cand.empty:
    series["SWING_priorweek_f10"] = daily_from(cand, "exit_date", "net")
    meta["SWING_priorweek_f10"] = {"source": str(p.relative_to(R)), "cell": cell,
                                   "n_trades": int(len(cand)),
                                   "span": f"{pd.to_datetime(cand.exit_date).min():%Y-%m-%d}.."
                                           f"{pd.to_datetime(cand.exit_date).max():%Y-%m-%d}"}

# ---- 4. RATIO CALENDAR, best NET defined-risk cell ---------------------------------------
p = R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv"
rc = pd.read_csv(p)
best = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
if not best.empty:
    b = best.drop_duplicates(subset=["day0", "near_expiry"]).copy()
    b["net_rs"] = b["net_pts"] * LOT
    series["CALENDAR_1x1_3d"] = daily_from(b, "exit_day", "net_rs")
    meta["CALENDAR_1x1_3d"] = {"source": str(p.relative_to(R)),
                               "cell": "ATM_ATM 1x1 exit 3d_before (NET)",
                               "n_trades": int(len(b)),
                               "span": f"{pd.to_datetime(b.day0).min():%Y-%m-%d}.."
                                       f"{pd.to_datetime(b.day0).max():%Y-%m-%d}"}

# ---- 5. INVERSE-VRP niche 1 (bottom-decile IV long straddle) -----------------------------
p = R / "INVERSE_VRP_NICHE_20260729" / "niche1_niche2_trades.csv"
iv = pd.read_csv(p)
n1 = iv[iv["tag"].astype(str).str.contains("BOTTOM_IV", case=False, na=False)] if "tag" in iv else iv.iloc[0:0]
n1 = n1[n1.get("both_filled", True) == True] if "both_filled" in n1 else n1
if not n1.empty and "net_pnl" in n1:
    dc = "exit_t" if "exit_t" in n1 else "day"
    series["IVLOW_straddle"] = daily_from(n1, dc, "net_pnl")
    meta["IVLOW_straddle"] = {"source": str(p.relative_to(R)), "n_trades": int(len(n1)),
                              "span": f"{pd.to_datetime(n1[dc]).min():%Y-%m-%d}.."
                                      f"{pd.to_datetime(n1[dc]).max():%Y-%m-%d}"}

# ---- 6. Existing stacked book + its sleeves ----------------------------------------------
p = R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv"
bk = pd.read_csv(p, index_col=0)
bk.index = pd.to_datetime(bk.index)
for c in ("total", "s1f", "midsmall", "breakout", "b1b"):
    if c in bk.columns:
        series[("BOOK_total" if c == "total" else f"book_{c}")] = bk[c].sort_index()
meta["BOOK_total"] = {"source": str(p.relative_to(R)), "n_days": int(len(bk)),
                      "span": f"{bk.index.min():%Y-%m-%d}..{bk.index.max():%Y-%m-%d}"}


# ---------------------------------------------------------------- metrics
def metrics(s: pd.Series, name: str) -> dict:
    s = s.sort_index()
    if len(s) < 5:
        return {"strategy": name, "n_days": int(len(s))}
    eq = CAP + s.cumsum()
    pk = eq.cummax()
    mdd = float(((eq - pk) / pk).min())
    yrs = max((s.index.max() - s.index.min()).days / 365.25, .01)
    end = float(eq.iloc[-1])
    cagr = (end / CAP) ** (1 / yrs) - 1 if end > 0 else np.nan
    r = s / CAP
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
    mo = s.resample("ME").sum()
    w, l = s[s > 0], s[s <= 0]
    # Newey-West t on daily P&L
    x = s.values.astype(float)
    m_, n_ = x.mean(), len(x)
    dv = x - m_
    v = (dv @ dv) / n_
    for L in range(1, 6):
        v += 2 * (1 - L / 6) * ((dv[L:] @ dv[:-L]) / n_)
    t = m_ / np.sqrt(v / n_) if v > 0 else np.nan
    return {"strategy": name, "span": f"{s.index.min():%Y-%m}..{s.index.max():%Y-%m}",
            "years": round(yrs, 2), "active_days": int((s != 0).sum()),
            "net_total_rs": round(float(s.sum())),
            "CAGR_pct": round(100 * cagr, 2) if np.isfinite(cagr) else None,
            "maxDD_pct": round(100 * mdd, 2),
            "Calmar": round(float(cagr / abs(mdd)), 2) if mdd and np.isfinite(cagr) else None,
            "Sharpe": round(sh, 2), "NW_t": round(float(t), 2),
            "PF": round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
            "months": int(len(mo)), "months_pos": int((mo > 0).sum()),
            "month_win_pct": round(100 * float((mo > 0).mean()), 1),
            "worst_month_rs": round(float(mo.min())), "best_month_rs": round(float(mo.max())),
            "max_day_share_of_profit": round(float(s.abs().max() / max(abs(s.sum()), 1)), 3)}


rows = [metrics(s, k) for k, s in series.items()]
mt = pd.DataFrame(rows)
mt.to_csv(OUT / "metrics_all.csv", index=False)

# ---------------------------------------------------------------- correlations
CAND = [k for k in series if not k.startswith("book_")]


def corr_at(freq: str) -> pd.DataFrame:
    agg = {k: series[k].resample(freq).sum() for k in CAND}
    M = pd.DataFrame(agg)
    return M.corr(min_periods=6)


cors = {}
for lbl, fr in (("daily", "D"), ("monthly", "ME"), ("quarterly", "QE")):
    c = corr_at(fr)
    c.to_csv(OUT / f"corr_{lbl}.csv")
    cors[lbl] = c

# pairwise verdict table with overlap counts
pairs = []
for i, a in enumerate(CAND):
    for b in CAND[i + 1:]:
        ov = series[a].index.intersection(series[b].index)
        mo_a, mo_b = series[a].resample("ME").sum(), series[b].resample("ME").sum()
        common_m = mo_a.index.intersection(mo_b.index)
        m = float(mo_a[common_m].corr(mo_b[common_m])) if len(common_m) >= 6 else np.nan
        q_a, q_b = series[a].resample("QE").sum(), series[b].resample("QE").sum()
        common_q = q_a.index.intersection(q_b.index)
        q = float(q_a[common_q].corr(q_b[common_q])) if len(common_q) >= 6 else np.nan
        if np.isnan(m) or np.isnan(q):
            verdict = "INSUFFICIENT_OVERLAP"
        elif np.sign(m) != np.sign(q):
            verdict = "NOISE (sign disagrees)"
        elif max(abs(m), abs(q)) > 0.53:
            verdict = "TOO_CORRELATED (>0.53 firm ceiling)"
        elif max(abs(m), abs(q)) > 0.35:
            verdict = "YELLOW"
        else:
            verdict = "GREEN (orthogonal)"
        pairs.append({"a": a, "b": b, "overlap_months": len(common_m),
                      "overlap_quarters": len(common_q),
                      "monthly": round(m, 3) if np.isfinite(m) else None,
                      "quarterly": round(q, 3) if np.isfinite(q) else None,
                      "verdict": verdict})
pt = pd.DataFrame(pairs).sort_values("overlap_months", ascending=False)
pt.to_csv(OUT / "correlation_verdicts.csv", index=False)

(OUT / "series_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

print("=" * 118)
print("METRICS (all series rebuilt from real per-trade CSVs)")
print("=" * 118)
cols = ["strategy", "span", "years", "n" if "n" in mt else "active_days", "CAGR_pct",
        "maxDD_pct", "Calmar", "Sharpe", "NW_t", "PF", "month_win_pct", "max_day_share_of_profit"]
cols = [c for c in cols if c in mt.columns]
print(mt[cols].to_string(index=False))
print()
print("=" * 118)
print("PAIRWISE CORRELATION VERDICTS (monthly + quarterly must agree in sign)")
print("=" * 118)
print(pt.to_string(index=False))
print()
print("wrote metrics_all.csv, corr_{daily,monthly,quarterly}.csv, correlation_verdicts.csv, series_meta.json")
