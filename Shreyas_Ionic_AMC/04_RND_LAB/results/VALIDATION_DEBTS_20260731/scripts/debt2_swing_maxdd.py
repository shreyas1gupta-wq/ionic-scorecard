"""
DEBT 2 -- SWING maxDD CONTRADICTION, independent resolution.
Owner: Sameer Bhat (Overfit & Sensitivity). 2026-07-31.

Question: PORTFOLIO_MARGINAL_20260729/DECISION_RULE_AND_VERDICT.md:96 claims adding
SWING_DELTA1 (cell D_priorweek_sweep_long__fixed_10, aka "SWING_pw10") to the 4-sleeve
book cuts book maxDD from -18.4% to -9.5/-9.6% at 50% weight. FINAL_RANKING_20260730/
marginal_add.csv shows book maxDD basically FLAT/slightly worse (-19.07 to -19.6%) as
SWING_pw10 weight rises from 5% to 20%. Both use the SAME book file
(STACKED_BOOK_20260711/book_daily_pnl.csv) and the SAME candidate cell -- so this is a
genuine apples-to-apples conflict, not a different-book artifact. Resolve it by
recomputing both blend models from the raw data myself.
"""
import numpy as np
import pandas as pd

R = r"Shreyas_Ionic_AMC/04_RND_LAB/results"
BOOK_CAP = 1.0e7  # Rs 1cr, RISK_LIMITS D-026

# 1. Book (same file both reports use)
book = pd.read_csv(f"{R}/STACKED_BOOK_20260711/book_daily_pnl.csv", index_col=0, parse_dates=True)
book.index.name = "date"
book_rupee = book["total"]  # rupee P&L/day, Rs1cr base
book_ret = book_rupee / BOOK_CAP

# 2. SWING candidate -- isolate EXACTLY the long fixed_10 cell (54 trades per firm docs)
sw = pd.read_csv(f"{R}/SWING_DELTA1_20260729/all_trades.csv", parse_dates=["entry_date", "exit_date"])
cell = "D_priorweek_sweep_long__fixed_10"
m = sw[sw["cell"] == cell].copy()
print(f"[SWING candidate] cell={cell}  n={len(m)}")
eq_before_first = (m["equity_after"] - m["net"]).iloc[0]
print(f"[SWING candidate] equity_before of FIRST trade = Rs{eq_before_first:,.0f} "
      f"-> confirms native capital base is Rs1cr (BOOK_EQUITY0 in swing_engine.py:25)")

# collapse same-day duplicates, reindex onto book's real trading-day calendar, 0-fill
swing_daily_rupee = m.groupby(m["exit_date"].dt.normalize())["net"].sum()
swing_on_book_dates = swing_daily_rupee.reindex(book_rupee.index, fill_value=0.0)
n_active_days_in_book_window = int((swing_on_book_dates != 0).sum())
print(f"[SWING candidate] active (non-zero) days inside book's {book_rupee.index.min().date()}"
      f"..{book_rupee.index.max().date()} window: {n_active_days_in_book_window} of {len(book_rupee)} "
      f"({100*n_active_days_in_book_window/len(book_rupee):.1f}% -- confirms 'idle most of the time')")


def metrics(rupee_series, cap=BOOK_CAP):
    x = rupee_series.dropna()
    eq = cap + x.cumsum()
    dd = (eq - eq.cummax()) / eq.cummax()
    maxdd = 100 * dd.min()
    yrs = max((x.index.max() - x.index.min()).days / 365.25, 0.01)
    total_ret = (eq.iloc[-1] / cap) - 1
    cagr = 100 * ((1 + total_ret) ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else np.nan
    r = x / cap
    sharpe = (r.mean() / r.std()) * np.sqrt(252) if r.std() > 0 else np.nan
    calmar = (cagr / abs(maxdd)) if maxdd < 0 else np.nan
    worst_mo = 100 * (x.resample("ME").sum().min() / cap)
    return dict(CAGR=cagr, Sharpe=sharpe, maxDD=maxdd, Calmar=calmar, worst_mo=worst_mo)


book_alone = metrics(book_rupee)
print("\n[BOOK ALONE] ", {k: round(v, 3) for k, v in book_alone.items()})

WEIGHTS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

rows = []

# --- MODEL A: REALLOCATION (PORTFOLIO_MARGINAL's own method) ---
# blend = (1-w)*book + w*candidate, both at native Rs1cr scale -- capital is MOVED
# from the existing book into SWING, consistent with the firm's single Rs1cr book cap
# (RISK_LIMITS D-026): you cannot deploy new capital you don't have.
for w in WEIGHTS:
    blended = (1 - w) * book_rupee + w * swing_on_book_dates
    mm = metrics(blended)
    rows.append(dict(model="A_reallocation(PORTFOLIO_MARGINAL method)", weight=w, **mm))

# --- MODEL B: ADDITIVE, CORRECTED SCALING ---
# blend = book + w*candidate (candidate native series IS a 100%-weight Rs1cr series,
# so a true w-weight incremental sleeve is w*candidate). This models deploying SEPARATE
# new capital alongside the untouched book (no capital taken FROM the book).
for w in WEIGHTS:
    blended = book_rupee + w * swing_on_book_dates
    mm = metrics(blended)
    rows.append(dict(model="B_additive_CORRECTED", weight=w, **mm))

# --- MODEL C: ADDITIVE, AS-CODED IN marginal_add.py (reproduces the FINAL_RANKING bug) ---
# marginal_add.py does: comb = BOOK.add(s*(w/0.10)) -- i.e. scales the candidate's
# ALREADY-Rs1cr-native series by (w/0.10), a factor built for the OTHER 3 candidates in
# that script (SWEEP_E/SWEEP_D/CALENDAR_1x1), which are flat 1-LOT series implicitly
# representing only ~Rs10L (10% of book) notional. Applying that same /0.10 divisor to
# SWING's OWN full-Rs1cr equity-curve series is a capital-base mismatch: at the "10%"
# label the code adds the FULL native (100%-scale) SWING series on top of the untouched
# book; at "20%" it adds 2x SWING's native series. Reproduced here to verify the bug
# explains FINAL_RANKING's flat/worse maxDD reading.
for w in WEIGHTS:
    if w > 0.20:
        continue  # marginal_add.py only tested 5/10/15/20%
    blended = book_rupee + (w / 0.10) * swing_on_book_dates
    mm = metrics(blended)
    rows.append(dict(model="C_additive_AS_CODED(reproduces bug)", weight=w, **mm))

out = pd.DataFrame(rows)
print("\n" + "=" * 100)
print(out.to_string(index=False))

out.to_csv("Shreyas_Ionic_AMC/04_RND_LAB/results/VALIDATION_DEBTS_20260731/swing_maxdd_reconciliation.csv",
           index=False)
print("\nWrote swing_maxdd_reconciliation.csv")

# --- Verification against each report's own published numbers ---
print("\n--- Reproduction check vs PORTFOLIO_MARGINAL's own marginal_weight_sweep.csv (w=0.5) ---")
print("Published: sharpe=1.5828 calmar=1.3576 maxDD=-9.510 (uses (1+ret)-compounding, not additive-rupee)")
a50 = out[(out.model.str.startswith("A_")) & (out.weight == 0.5)].iloc[0]
print(f"My model A (additive-rupee, w=0.5): maxDD={a50.maxDD:.3f}  Calmar={a50.Calmar:.3f}  Sharpe={a50.Sharpe:.3f}")

print("\n--- Reproduction check vs FINAL_RANKING's marginal_add.csv (SWING_pw10, w=0.10/0.20) ---")
print("Published (marginal_add.csv): w=0.10 maxDD=-19.031 | w=0.20 maxDD=-19.607")
for w in (0.10, 0.20):
    c = out[(out.model.str.startswith("C_")) & (out.weight == w)].iloc[0]
    print(f"My model C (as-coded, w={w}): maxDD={c.maxDD:.3f}")

print("\n--- What the CORRECTED additive scaling would actually show ---")
for w in (0.10, 0.20):
    b = out[(out.model.str.startswith("B_")) & (out.weight == w)].iloc[0]
    print(f"My model B (corrected, w={w}): maxDD={b.maxDD:.3f}  (book alone = {book_alone['maxDD']:.3f})")

print("\n--- Reallocation model AT THE FIRM'S OWN RECOMMENDED WEIGHT (10-15%, not 50%) ---")
for w in (0.10, 0.15):
    a = out[(out.model.str.startswith("A_")) & (out.weight == w)].iloc[0]
    print(f"Model A (reallocation, w={w}): maxDD={a.maxDD:.3f}  (book alone = {book_alone['maxDD']:.3f})")
