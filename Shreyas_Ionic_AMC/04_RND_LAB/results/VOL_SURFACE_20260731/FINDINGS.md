[DRAFT IN PROGRESS - placeholders below will be replaced once full-sample extraction (2021-05..2026-06)
completes under the fleet chainlock. PRE_OCT2024 numbers are directionally stable across successive
partial checkpoints (n=153/366/508 rows so far) but POST_OCT2024 and HELDOUT_2026 rows do not exist
yet -- expiries are walked in date order, so those eras only populate once ~68% / ~92% of the way
through the 261-expiry loop.]

# FINDINGS -- VOL_SURFACE_20260731 (NIFTY 50 volatility-surface signals)
Owner: quant (vol-surface arm). Data: 1-min NIFTY weekly option chain 2021-05..2026-06, EOD
(15:15-15:29 last-print) snapshots, BS-inverted IV (r=0.065), FRONT = min-dte listed weekly that
day, NEXT = 2nd-nearest weekly (a different contract). Full method + kill criteria: PRE_REGISTRATION.md.

## Headline structural fact (holds at n=500+ pre-Oct-2024 so far; confirming on full sample)
NIFTY weekly term structure is INVERTED (front ATM IV > next ATM IV) on ~90% of days measured so far
-- backwardation looks like the NORMAL state for NIFTY weeklies, not a rare stress marker. Checking
whether this attenuates post-Oct-2024 given the Herfindahl/PCR regime break STRUCTURAL_EDGES already
documented.

## 1. SKEW (25-delta put IV - 25-delta call IV)
[fill from predictive_cells.csv rows cell~skew_level_*, skew_chg_*]

## 2. TERM STRUCTURE (next ATM IV - front ATM IV)
[fill from term_slope_* rows + atm_calendar_cells.csv calendar_shortfront_longnext_*]

## 3. IV-RV SPREAD (percentile, 5-min & 15-min realized vol)
[fill from iv_rv*_pct rows]

## 4. SURFACE PCA (level/slope/curvature, loadings fit PRE-OCT-2024 only)
[fill from pc1_*/pc2_* rows + explained variance ratio]

## 5. VARIANCE RISK PREMIUM (implied - forward realized, vol points, by tenor x era)
[fill from vrp_table.csv]

## 6. CROSS-SECTIONAL (front vs next richness; sell-wing structure P&L)
[fill from structure_cells.csv, strangle_cells.csv, atm_calendar_cells.csv]

## Best 10 cells
[table]

## Trials count & Bonferroni
49 pre-registered cell definitions (PRE_REGISTRATION.md), ~150 individual era-split t-stats. Firm
cumulative trial count before this session ~481+ (SHARED_CONTEXT); combined bar ~t>=3.8 for
CERTIFIED. VRP-vs-zero t-stats (20-30+ seen already) clear this trivially; directional predictive
cells are judged against their own placebo_bar (see PRE_REGISTRATION.md), not t alone, per the
2026-07-30 evaluation-framework ruling (t-stat sets tier, never kills).

## 4-line verdict
[fill once full sample lands]
