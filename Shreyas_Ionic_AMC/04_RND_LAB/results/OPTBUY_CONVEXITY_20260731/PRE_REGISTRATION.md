# PRE-REGISTRATION — OPTBUY_CONVEXITY_20260731 (Arm A: buyer gamma-vs-theta)
Written BEFORE any cell is run. NIFTY 50 only.

## Question
Where, if anywhere, does an option BUYER's gamma convexity beat the theta paid for it?
Prior work (SHARED_CONTEXT_20260729) killed 0-7 DTE buying at every gate tried. This arm's
mandate is DTE >= 15 (untested), using the 16-yr daily F&O bhavcopy archive
(`05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2016..2026}.parquet`), restricted to 2016+ where
India VIX daily history exists (`datasets/index_daily/india_vix.parquet`,
`datasets/index_daily/nifty50.parquet` for spot).

## Structure under test
Long ATM straddle (CE+PE at nearest common strike, both gated CONTRACTS>0), rolled on
NON-OVERLAPPING monthly-expiry cycles (one position at a time — no overlap defect). Entry = day
after previous exit. Expiry chosen = the MONTHLY (last-of-calendar-month) expiry nearest a target
calendar DTE. Single-leg CE-only / PE-only tested only for the asymmetry arm at one DTE.

## Grid (pre-registered, ~20 cells, logged in cells.csv regardless of outcome)
1. DTE sweep, hold-to-expiry, unconditional entry: DTE in {15,30,45,60,90}. (5 cells)
2. Partial-hold test at the best-or-representative DTE from (1): exit at ~50% of DTE via option
   CLOSE (CONTRACTS>0 gated, small fallback window), vs hold-to-expiry. (1-2 cells)
3. Vol-level gate at that DTE: entry only when trailing-2yr VIX percentile <=25th (compression)
   vs >=75th (rich) vs unconditional baseline. Percentile computed EXPANDING/TRAILING only past
   data — no full-sample percentile. (2 cells beyond baseline)
4. Realized-vol compression gate (independent of VIX level): 20d realized-vol percentile <=25th
   trailing 2yr at entry. (1 cell)
5. Put vs call asymmetry: CE-only and PE-only, same DTE, hold-to-expiry, unconditional entry.
   (2 cells)

## Method (non-negotiable, matches this mandate's brief)
- Entry price = option daily CLOSE, CONTRACTS>0 gated (fallback forward up to 3 trading days if
  the entry day itself has 0 contracts at the chosen strike; else drop and log).
- Exit at expiry = INTRINSIC from underlying spot close (`nifty50.parquet`), NEVER the expiry-day
  SETTLE_PR (landmine #9). Partial-hold exits = option CLOSE, CONTRACTS>0 gated with fallback.
- Costs: Rs25/lot/side, lot 65 => 1.77 premium points round trip PER LEG (straddle = 2 legs =>
  3.54 pts total round trip), per this mandate's brief. Applied once per trade (entry+exit/settle).
- Capital for a long option/straddle = premium paid (no margin — buyer risk is bounded to premium).
- No stops/trails/targets are used anywhere in this arm (pure time-based entry/exit), so
  `lib/pathsafe.py`'s stop/trail machinery does not apply; there is no path-dependent claim to
  guard. Endpoint-to-endpoint P&L (entry close -> exit close/intrinsic) is exact, not an estimate.
- Percentile filters (VIX, RV) use ONLY trailing/expanding history as of the entry date — never a
  full-sample percentile (that would be lookahead).
- Split: pre-2019 (weekly-launch break) / 2019-2024-09 / 2024-10+ (SEBI tightening break) reported
  separately per firm convention. **2026 H1 is HELD OUT — reported, never selected on.**
- Placebo for every gated cell: same-count RANDOM cycle selection (matched on DTE, not on the
  gate), repeated 500x, reporting the percentile rank of the observed mean vs the null.

## Kill criteria (pre-committed, will not be softened after seeing results)
- HARD KILL (non-negotiable): fails its own placebo; profit concentration >30% in one trade;
  maxDD >25% of average deployed premium; any lookahead (full-sample percentile, same-bar fill,
  expiry-day settle read as option price).
- SOFT (sets tier, never kills): t-stat, Bonferroni, DSR/PBO, small-n. A low-t positive with a
  stateable mechanism is UNDERPOWERED-UNRESOLVED, not DEAD, per the Principal's standing ruling.
- The 1/(1+R) fixed-target null used in the futures RR sweep does NOT apply to a hold-to-expiry
  straddle (no fixed stop/target exists to define R). In its place: hit rate is compared against
  (a) the UNCONDITIONAL baseline hit rate at the same DTE, and (b) the 500x random-cycle placebo.
  This substitution is stated up front, not invented post hoc.
- Trial count for this arm's own Bonferroni bar: ~20 pre-registered cells (see grid above);
  reported honestly regardless of which cells look good.

## Deliverable
`cells.csv` (all cells, not just winners), `FINDINGS.md` (mechanism, decomposition, verdict).
Bank every batch to `checkpoints/` so a crash loses nothing.
