"""
DEBT 3 -- 2008/Black-Monday-class tail stress, using long DAILY history (not backtests).
Owner: Sameer Bhat. 2026-07-31.

DATA REALITY CHECK (done before writing this): searched the firm's holdings for a genuine
INDEX-level NIFTY/SENSEX daily series reaching back to 2008 or earlier.
  - Nifty500_Master_Dataset_2005_2025.xlsx (root) = a 1200-column STOCK-level price panel
    (no index column at all) -- cannot serve as an index series without reconstructing one,
    which is out of scope for an audit pass (and Nikhil/Kavya have not validated it as an
    index-replication input).
  - datasets/index_daily/{nifty50,nifty500,banknifty}.parquet: start 2016-01 only.
  - 05_DATA_OFFICE/data/indices_close/indices_{2012..2026}.parquet: official NSE daily
    index closes (Index Name incl. 'S&P CNX Nifty' pre-rename / 'Nifty 50' post-rename),
    DAILY OHLC, starting 2012-01-03. LONGEST genuine index-level series found on disk.
  - No SENSEX series, no pre-2012 index series, found anywhere (data/ or git history).
CONCLUSION: 2008 GFC and any pre-2012 "Black Monday"-class event (1992 Harshad Mehta, 2001
Ketan Parekh, 2004 election crash) CANNOT be measured from what the firm holds -- flagged
per instruction rather than guessed/fabricated. What IS covered by 2012-2026: 2013 taper
tantrum, 2015-16 China deval, 2018-19 correction, Aug-2019 surcharge shock, COVID Mar-2020,
2022 rate-hike selloff -- a genuine, non-trivial tail sample, just not 2008.
"""
import numpy as np
import pandas as pd

R = r"Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close"

# NAME-ALIAS LANDMINE (caught during this pass, not inherited from any prior verified note):
# the underlying 50-stock index has been renamed TWICE in this archive -- 'S&P CNX Nifty'
# (2012-2013) -> 'CNX Nifty' (2013-2015, dropped the S&P prefix) -> 'Nifty 50' (from
# 2015-11-09). A first version of this script matched only 'S&P CNX Nifty'/'Nifty 50' and
# MISSED 'CNX Nifty' entirely, silently dropping 2013-11..2015-11-06 -- which produced a
# fabricated-looking "+33% in one day" on 2015-11-09 (real cause: pct_change() computed
# against a stale value from BEFORE the multi-month gap, not a real market move). Caught by
# spot-checking that print against known reality (no real +33% NIFTY day exists) before
# reporting it. ALSO: 'Index Date' is not one consistent format across years (dash vs slash
# separators seen) -- use format='mixed', dayfirst=True, matching the firm's established
# fix for the same class of bug in the F&O bhavcopy archive (SHARED_CONTEXT).
ALIASES = ["S&P CNX Nifty", "CNX Nifty", "Nifty 50", "NIFTY 50"]
frames = []
for yr in range(2012, 2027):
    try:
        d = pd.read_parquet(f"{R}/indices_{yr}.parquet")
    except FileNotFoundError:
        continue
    d = d[d["Index Name"].isin(ALIASES)].copy()
    frames.append(d)
nf = pd.concat(frames, ignore_index=True)
nf["date"] = pd.to_datetime(nf["Index Date"], format="mixed", dayfirst=True)
for c in ["Open Index Value", "High Index Value", "Low Index Value", "Closing Index Value"]:
    nf[c] = pd.to_numeric(nf[c], errors="coerce")
# verify no two aliases silently disagree on the SAME date before dropping duplicates
dupe_dates = nf[nf.duplicated(subset="date", keep=False)].sort_values("date")
if len(dupe_dates):
    disagree = dupe_dates.groupby("date")["Closing Index Value"].nunique()
    n_disagree = int((disagree > 1).sum())
    print(f"[CHECK] {dupe_dates['date'].nunique()} dates have >1 alias row; "
          f"{n_disagree} of those DISAGREE on Closing Index Value (should be 0).")
nf = nf.sort_values("date").drop_duplicates(subset="date").reset_index(drop=True)
print(f"[DATA] NIFTY 50 daily, {nf['date'].min().date()}..{nf['date'].max().date()}, n={len(nf)}")
# sanity: max gap between consecutive trading days should be a long-weekend/holiday cluster,
# never a multi-month silent alias-drop like the bug above
gaps = nf["date"].diff().dt.days
print(f"[CHECK] max gap between consecutive rows: {gaps.max()} days "
      f"(on {nf.loc[gaps.idxmax(), 'date'].date() if gaps.notna().any() else 'n/a'})")

close = nf.set_index("date")["Closing Index Value"]
ret = close.pct_change().dropna()

# --- worst 1/3/5/20-day moves (rolling cumulative return, both directions) ---
horizons = [1, 3, 5, 20]
rows = []
for h in horizons:
    roll = close.pct_change(h).dropna()
    worst_down = roll.min()
    worst_down_date = roll.idxmin()
    worst_up = roll.max()
    worst_up_date = roll.idxmax()
    rows.append(dict(horizon_days=h, worst_down_pct=100 * worst_down, worst_down_date=str(worst_down_date.date()),
                      worst_up_pct=100 * worst_up, worst_up_date=str(worst_up_date.date())))
tail_df = pd.DataFrame(rows)
print("\n" + "=" * 100)
print("WORST N-DAY MOVES, NIFTY 50, 2012-01..2026-07 (verified daily index closes)")
print(tail_df.to_string(index=False))

# --- named crisis windows for context ---
print("\n" + "=" * 100)
print("NAMED WINDOWS IN THIS SAMPLE (for context, not exhaustive)")
windows = {
    "2013 Taper Tantrum (Jun-Sep 2013)": ("2013-06-01", "2013-09-15"),
    "2015-16 China Deval / Aug15-Feb16": ("2015-08-01", "2016-02-29"),
    "2018 correction (Jan-Oct)": ("2018-01-01", "2018-10-31"),
    "Aug-2019 surcharge shock": ("2019-08-01", "2019-08-31"),
    "COVID crash (Feb-Apr 2020)": ("2020-02-01", "2020-04-30"),
    "2022 rate-hike selloff (Jan-Jun)": ("2022-01-01", "2022-06-30"),
}
for name, (s, e) in windows.items():
    seg = close.loc[s:e]
    if len(seg) < 2:
        continue
    dd = (seg / seg.cummax() - 1).min()
    print(f"{name}: {seg.index.min().date()}..{seg.index.max().date()}, n={len(seg)}, "
          f"peak-to-trough {100*dd:.2f}%")

# --- short-strangle stress: unhedged margin = 10% of notional (D-030 margin ruling) ---
print("\n" + "=" * 100)
print("SHORT-STRANGLE STRESS -- unhedged 10% margin convention (SHARED_CONTEXT margin ruling)")
print("Model: naked short strangle, strikes at +-W% OTM each side. A move of X% beyond the")
print("strike is charged at FULL notional past the strike (intrinsic, no vol/gamma cushion --")
print("a deliberately simple LOWER BOUND, since it ignores IV expansion that would make a real")
print("crash worse, not better). Loss reported as a MULTIPLE of the 10% margin capital.")
print("[INFERENCE]: strike widths are illustrative (no 2012-2018 option chain exists to price a")
print("real historical strangle) -- this is an order-of-magnitude stress illustration, not a")
print("backtested P&L.")

widths = [0.0, 0.03, 0.05]  # 0% = ATM straddle proxy (S1-F's own structure), 3%, 5% OTM
strangle_rows = []
for h in horizons:
    roll = close.pct_change(h).dropna()
    worst_abs = roll.abs().max()  # worst of either direction (strangle is symmetric risk)
    worst_date = roll.abs().idxmax()
    for w in widths:
        breach_pct = max(0.0, worst_abs - w)
        loss_as_pct_of_notional = breach_pct
        loss_as_multiple_of_margin = loss_as_pct_of_notional / 0.10
        strangle_rows.append(dict(
            horizon_days=h, strike_width_otm_pct=100 * w, worst_move_pct=100 * worst_abs,
            worst_move_date=str(worst_date.date()),
            loss_pct_of_notional=100 * loss_as_pct_of_notional,
            loss_as_multiple_of_10pct_margin=round(loss_as_multiple_of_margin, 2)))
strangle_df = pd.DataFrame(strangle_rows)
print(strangle_df.to_string(index=False))

# --- combine + write ---
tail_df["kind"] = "index_move"
strangle_df["kind"] = "strangle_stress"
out = pd.concat([tail_df, strangle_df], ignore_index=True, sort=False)
out.to_csv("Shreyas_Ionic_AMC/04_RND_LAB/results/VALIDATION_DEBTS_20260731/tail_stress.csv", index=False)
print("\nWrote tail_stress.csv")

# --- what this means for the 3 selling sleeves whose OWN option-priced sample starts 2021-05 ---
print("\n" + "=" * 100)
print("GAP-THROUGH-STRIKE RISK FOR SELLING SLEEVES WITH NO CRASH IN THEIR OWN OPTION SAMPLE")
print("=" * 100)
print("""
S1-F, CALENDAR, and OVERSHOOT are all priced from option chains starting 2021-05 (the HF 1-min
tree) or, for CALENDAR, the daily F&O bhavcopy from 2011 -- but CALENDAR's own regime-split finding
(STRATEGY_DOSSIER.md) already shows its entire edge is POST-2019, so even its longer data window
does not contain a real crash-tested live edge period. NONE of the three ever saw 2018-19 or COVID
IN AN OPTION-PRICED BACKTEST. The index-level table above is the best available substitute: it shows
NIFTY 50 has produced 1-day moves beyond 8% (worst 1-day roll) and 20-day drawdowns beyond 20% within
this 2012-2026 sample (see tail_df for exact dates/values) WITHOUT the firm's option-selling sleeves
ever having been tested against a comparable option-priced event. The strangle-stress table above
translates those same moves into margin-multiple terms: at 0% OTM (S1-F's actual ATM structure) ANY
of the worst 1-day/3-day moves in this sample would consume more than 100% of the 10%-margin capital
in a single session if unhedged and un-stopped -- S1-F's own 30% per-leg stop is the ONLY thing
standing between this arithmetic and a real blowup, and that stop has never been tested against a
move this size in real option prices (it has only been tested via BS-model backcasts, per the firm's
own covid_backcast work, which is a model, not a measurement).
""")
