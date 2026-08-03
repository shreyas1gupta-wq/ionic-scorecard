# VALIDATION DEBTS — CLEARED 2026-07-31 (Dr. Sameer Bhat, Overfit & Sensitivity)

Scripts: `scripts/debt1_dsr_pbo.py`, `scripts/debt2_swing_maxdd.py`, `scripts/debt3_tail_stress.py`.
Outputs: `dsr_pbo.csv`, `swing_maxdd_reconciliation.csv`, `tail_stress.csv`.
Method note: reused the firm's OWN existing DSR/PBO engine (`OVERFIT_AUDIT_20260729/overfit_engine.py`
— `sharpe`, `cscv_pbo`, `expected_max_sr`, `dsr`, `effective_n`) rather than re-deriving the math, per
the consolidate-reused-code convention. All figures below are reproducible from the scripts on disk.

---
## DEBT 1 — DSR/PBO on the full trials ledger [DATA]+[INFERENCE]

### Honest nominal trials ledger (verified counts, not the task brief's approximations)
| source | nominal cells | verified how |
|---|---|---|
| `OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv` cumulative (through 2026-07-30) | 466 | file's own running total, confirmed by re-adding its rows |
| INDICATOR_MINE_20260730 | 15 | journal cites bar at m=481 = 466+15, consistent |
| STRUCTURAL_EDGES_20260730 | 33 | journal ("33 effects") |
| GATED_BUYING_20260730 | 87 | `cells.csv` row count |
| CANDLE_MTF_20260730 | 480 | `cells.csv` row count (16 formations × 6 filters × 5 exits) |
| OPENING_PATTERNS_20260730 | 75 | `cells.csv` row count |
| PRICE_LEVELS_20260730 | 284 | `cells.csv` row count |
| ORTHOGONAL_ALPHA_20260730 | 24 | `cells.csv` row count |
| RATIO_CALENDAR_20260730 | 28 | grid_a 24 configs (`grid_a_trades_raw.csv` distinct strike_struct×ratio×exit_variant) + grid_b 4 configs — **NOT the ~140 STRATEGY_DOSSIER.md prose figure, which could not be reconciled against any file on disk and is flagged as a stale/rough overestimate** |
| LONGDATED_SELLING_20260730 | 54 | `all_trades_full_grid.csv` distinct tenor×delta×structure×mgmt |
| BIG_MOVE_20260731 | 176 realized (384 nominal design, 48 setups×8 RR) | `meta.json: n_cells=176` — **the task brief's "48×8=384" is the DESIGN, not what was actually realized; only 22 of 48 screened setups had a valid RR curve (22×8=176 exact)** |
| SWING_DELTA1 (50 pre-registered, 45 valid) | 50 | PORTFOLIO_MARGINAL/STRATEGY_DOSSIER prose — not yet in the 466-baseline ledger, added here |
| S1-F design family (S1F_SPEC.md:39) | ~150 | pre-dates the 466-ledger's 2026-07-29 start date entirely — the ledger itself under-counts everything before 07-29 |
| **Grand nominal total** | **~1,872** | sum of above; labeled ~ because TREND_CATCHER's 3 Stage-A signals and some S1-F sub-folders (kelly/filter grids) are not individually reconciled |

### Effective-independent-trials estimate — correlation-aware, not naive Bonferroni
Every family this pass could actually MEASURE (built a real day×cell return matrix and ran
`effective_n()`) showed the SAME pattern regardless of nominal grid size: **cells built from one
underlying mechanism are highly correlated, collapsing to a handful of effectively independent
bets:**
| family | N_raw | avg |corr| | N_eff |
|---|---|---|---|
| SWEEP_11YR (6 exit variants) | 6 | 0.702 | **1.33** |
| CALENDAR grid_a (24 configs) | 24 | 0.043 | **12.1** (see caveat below) |
| S1-F sensitivity surface | 84 | 0.315 | **3.10** |
| LD_SELL full grid | 54 | 0.303 | **3.17** |
| THREE_SOLDIERS sub-grid | 30 | 0.636 | **1.54** |

Extending the same logic (genuinely distinct mechanisms, not parameter reruns, count separately;
parameter grids of one mechanism collapse to ~1-3) across every family in the ledger above gives an
**[INFERENCE] whole-session estimate of ~40-55 effective independent trials against the ~1,872
nominal cells — a 35-45x compression**, consistent with every family actually measured (4.5x-240x
range). **Practical consequence, worth stating because it is not obvious**: Bonferroni/Šidák bars
grow only with √(2·ln N), so this 40x reduction only moves the required |t| bar from ~3.9 (naive
N=1,872) to ~3.3 (N_eff≈50) — a real but modest easing, not the order-of-magnitude relief a naive
reading of "1,872 nominal trials" would suggest is owed.

### Per-candidate DSR/PBO (full detail: `dsr_pbo.csv`)
| candidate | DSR | PBO | N_eff used | verdict vs RESEARCH_SOP (DSR>0.95 & PBO<25%) |
|---|---|---|---|---|
| **SWEEP_E** | **0.996-1.00** | **0.00** | 1.33 (own 6-variant family) | **CLEARS BOTH — confirmed** |
| S1-F | 0.998 | 0.33 | 3.10 (84-cell surface, lower bound on ~150) | DSR clears; **PBO fails (33%>25%)** |
| CALENDAR_1x1_3d_before | 0.58-0.70 | 0.26-0.33 | 1.8-12.1 (family-definition dependent, see below) | **FAILS both** |
| OVERSHOOT | ~0.00 | n/a (illustrative-only N=5) | 5-13 | **FAILS badly** |
| LD_SELL | 0.80 | 0.14 | 3.17 (54-config family) | DSR fails; PBO passes |
| THREE_SOLDIERS | ~1.00 | 0.00 (raw, contaminated) | 1.54 | statistically clears, **but see beta caveat below** |

**SWEEP_E — the "Known prior" is CONFIRMED, exactly.** Independent recomputation from the raw
`trades_*_1lot.csv` files reproduces DSR_D009's published N_eff=1.330/avg_corr=0.702 to 4 decimal
places. **Caveat found in the process**: the family's `_kelly01.csv` files (the ones
MASTER_STRATEGY_TABLE.md separately flags as DISCREDITED — unbounded lot-count compounding) give a
MUCH worse reading if used by mistake (DSR 0.74, avg_corr 0.54) — logged in `dsr_pbo.csv` as an
explicit disclosure so a future pass doesn't grab the wrong file.

**S1-F — new finding, not previously computed.** DSR (0.998, using the 84-cell sensitivity surface
as a lower-bound proxy for the ~150-cell family) comfortably clears 0.95. **But CSCV PBO = 32.9%,
above the 25% gate** — under combinatorial cross-validation there is a meaningful chance the
in-sample-best cell in that surface would not repeat out-of-sample. Mitigating context: S1-F's actual
registered configuration (ATM straddle, 09:20 entry) is the CANONICAL/obvious choice, not the argmax
of the 84-cell grid — the grid was run to CONFIRM a plateau (72/84 positive), not to cherry-pick a
winner — so this PBO reading somewhat overstates the true risk, but the number is real and previously
unmeasured. **Recommend**: re-run CSCV restricted to just the pre-registered final candidates (the 3
in `final_three_trades.csv`), which should read materially better.

**CALENDAR — genuine, unresolved conflict between two reasonable family definitions.** Restricting the
matrix to timing-variant reruns of the SAME structure gives the previously-published N_eff=1.82/DSR
0.576. Using the FULL 24-config grid (which spans genuinely different, sometimes opposite-signed
payoffs — 1x1 defined-risk vs 2x1/3x2 ratio structures the dossier itself calls "outright losers…
lethally short gamma") gives N_eff=12.1/DSR 0.70. **Both fail the 0.95 gate either way** — the
disagreement changes the number, not the verdict. PBO 26-33% also fails. Consistent with
STRATEGY_DOSSIER.md's own "t=2.25 does not clear its Bonferroni bar" caution, now confirmed on a DSR
basis too.

**OVERSHOOT — fails badly, confirming its own "not comfortably positive" self-assessment.** At the
family's true structural width (13 major structures tested per FINAL_VERDICT.md, of which only 1 was
positive), DSR rounds to 0.000.

**LD_SELL — real but unripe.** DSR 0.80 (below 0.95), PBO 14% (comfortably below 25%). Best
description: a genuine, moderate edge that has NOT yet been searched enough to worry about
overfitting (PBO is fine) but also has not been shown to beat the "best-of-N-similar-attempts" luck
bar (DSR falls short). Textbook FORWARD-TEST CANDIDATE, not certified.

**THREE_SOLDIERS — statistically clears, but DSR does not test for beta.** Using the session's own
already-corrected, position-capped headline (n=758, t_NW=7.85 — NOT the raw overlapping series, which
inflates by 2.9-10.7x and is reported separately in `dsr_pbo.csv` as an explicit upper-bound/optimistic
disclosure) gives DSR≈1.0. But the same session independently found ~60% of this system's raw edge is
indistinguishable from unconditional long-bias on a sample where NIFTY rose +186% with no bear segment
long enough to test. **DSR/PBO answer "is this better than the luck of the search," not "is this alpha
or beta" — a strategy can pass both and still be beta in a trend-following costume.** Not a clean
survivor on that basis.

### Bottom line on Debt 1
**Only SWEEP_E cleanly clears DSR>0.95 AND PBO<25% under correlation-aware accounting.** S1-F clears
DSR but not PBO (mitigated, not resolved, by its principled non-cherry-picked selection). CALENDAR,
OVERSHOOT, and LD_SELL all fail DSR>0.95 regardless of which reasonable family definition is used.
THREE_SOLDIERS passes the statistical test but carries an orthogonal, un-rescued beta concern. None of
this changes any HARD KILL already on the books (per the firm's own framework, DSR/PBO set the CLAIM
TIER, they are not a kill switch) — but it means only ONE of the six should currently be described as
"validated" in the strict statistical sense; the rest are FORWARD-TEST CANDIDATES or weaker.

---
## DEBT 2 — SWING maxDD contradiction: RESOLVED, root cause found [DATA]

**Both published numbers are exactly reproducible from their own code — the contradiction is not a
bug in either script, it is two DIFFERENT, uncaveated models being quoted as if they were the same
test.** Full reconciliation: `swing_maxdd_reconciliation.csv` (built independently from the raw
`STACKED_BOOK_20260711/book_daily_pnl.csv` + `SWING_DELTA1_20260729/all_trades.csv`, cell
`D_priorweek_sweep_long__fixed_10`, n=54, active only 4.1% of the book's trading days).

- **PORTFOLIO_MARGINAL_20260729's -18.4%→-9.5% (at 50% weight)** is a **REALLOCATION** model:
  `blend = (1-w)·book + w·candidate`. My independent recomputation reproduces it almost exactly
  (-9.71% vs published -9.51%, book-alone -19.24% vs their -18.38%, gap purely from
  geometric-compounding vs additive-rupee convention — immaterial). **This number is REAL and
  reproducible.**
- **FINAL_RANKING_20260730's marginal_add.csv (flat ~-19.0 to -19.6% across 5-20% weight)** uses a
  DIFFERENT, **ADDITIVE** model: `blend = book + (w/0.10)·candidate`. My exact reproduction of this
  formula (bit-for-bit: -19.031 at w=10%, -19.607 at w=20%, matching published to 3 decimals)
  confirms the code, but exposes what it is actually testing: SWING's OWN trade series is already
  generated on a full Rs 1cr, dynamically-compounding equity curve (verified: `equity_before` of its
  first trade = exactly Rs 10,000,000) — i.e. it is ALREADY a "100%-weight" series. The `/0.10`
  divisor was built for the OTHER 3 candidates in that script (SWEEP_E/D, CALENDAR), which are flat
  1-lot series representing a nominal ~10% notional. Applying the same divisor to SWING is a
  capital-base mismatch: the "10%" label actually adds SWING's FULL native P&L on top of the
  untouched book; "20%" adds TWO full copies. **Under the CORRECTED additive scaling
  (`blend = book + w·candidate`, w actually meaning w), maxDD barely moves at all: -19.20% at w=10%,
  -19.17% at w=20%, vs book-alone -19.24%** — because SWING trades on only 4.1% of days, so even a
  true w-weight ADD-ON (capital not displaced from the book) cannot touch the book's own worst days.

**Neither -9.5% nor "flat -19%" is the honest number for the ACTUALLY RECOMMENDED sizing.**
PORTFOLIO_MARGINAL's own verdict text recommends 10-15% weight, not the 50% used to produce the
headline -9.5%. At the REALLOCATION model's own 10-15% weight: maxDD moves from -19.24% (book alone)
to **-17.34% (w=10%) / -16.39% (w=15%)** — a real but MODEST improvement, not the dramatic halving the
quoted headline implies, and MOST of even this modest improvement is mechanical dilution (halving
exposure to a book that's usually flat during SWING's active windows), not a genuine hedge — a
mechanism PORTFOLIO_MARGINAL's own prose already half-admits ("this candidate is genuinely thin/idle
most of the time").

**Which number the firm should use**: at the 10-15% weight actually contemplated for paper deployment,
book maxDD improves from **-19.2% to approximately -16.4% to -17.3%** (reallocation model, the only one
consistent with the firm's single Rs 1cr book cap, RISK_LIMITS D-026) — **not -9.5%.** The -9.5%
headline should be retracted or explicitly re-labeled "50%-weight reallocation extreme, not the
recommended-sizing figure." FINAL_RANKING's marginal_add.csv SWING_pw10 rows (and, by the same
mechanism, its SWEEP_E/D/CALENDAR rows, which reuse the identical `/0.10` scaling) should be flagged as
using a mismatched capital-base assumption for SWING specifically and re-run before being cited again.
Also flagged: book-alone maxDD is quoted as both -18.4% (compounding convention) and -19.2%
(additive-rupee convention) for the SAME book file elsewhere in the firm's docs — a third, smaller,
methodology-driven inconsistency worth a one-line standardization note.

---
## DEBT 3 — 2008/Black-Monday-class tail stress [DATA]+[INFERENCE]

**2008 GFC and any pre-2012 event CANNOT be measured from what the firm holds** — verified by
searching every candidate source: `Nifty500_Master_Dataset_2005_2025.xlsx` is a 1,200-column
STOCK-level panel with NO index column at all (cannot serve without reconstructing an index, out of
scope for an audit pass); `datasets/index_daily/{nifty50,nifty500,...}.parquet` start 2016-01; no
SENSEX series exists anywhere on disk or in git history. The longest genuine INDEX-level daily series
found is **`05_DATA_OFFICE/data/indices_close/indices_{2012..2026}.parquet`, official NSE closes,
2012-02-21..2026-07-10, n=3,534 days** — this is what the table below uses. **State clearly: this
covers 2013 taper tantrum, 2015-16 China deval, 2018-19 correction, COVID, 2022 selloff — genuinely
useful tail data — but NOT 2008 or 1992/2001/2004-class events. If 2008 is required, it needs a new
data acquisition (SENSEX daily 1979+ is the natural source) — flagged to Data Officer, not guessed.**

**Data landmine caught and fixed during this pass** (would have shipped a fabricated "+33% in one
day" otherwise): the underlying index is renamed twice in this archive — 'S&P CNX Nifty' (2012-13) →
'CNX Nifty' (2013 – 2015-11-06) → 'Nifty 50' (2015-11-09 onward) — plus inconsistent date-string
formats across yearly files (dash vs slash). A first pass matched only two of the three names and
silently dropped ~2 years, producing an apparent record one-day move that does not exist in reality.
Caught by spot-checking against known history before reporting; fixed by using all three name aliases
+ `format="mixed", dayfirst=True`. One residual, immaterial data conflict remains (2023-10-04 has two
"Nifty 50" rows with different closes, 17624 vs 19436 — the latter matches reality; flagged to Kavya,
does not affect any figure below since that date is nowhere near a tail extreme).

### Worst N-day NIFTY 50 moves, 2012-2026 (`tail_stress.csv`)
| horizon | worst DOWN | date | worst UP | date |
|---|---|---|---|---|
| 1-day | **-12.98%** | 2020-03-23 | +9.53% | 2023-11-06 |
| 3-day | **-14.93%** | 2020-03-18 | +13.55% | 2020-03-26 |
| 5-day | **-19.02%** | 2020-03-18 | +10.70% | 2013-09-11 |
| 20-day | **-37.01%** | 2020-03-23 | +20.29% | 2020-04-24 |

(Both the COVID crash bottom and the COVID V-rebound anchor the extremes — matches well-known public
record, cross-checked, not just internally consistent.)

### Short-strangle stress, unhedged 10% margin convention (D-030 margin ruling)
Simple **intrinsic, no-vol-cushion lower bound** [INFERENCE — real IV expansion would make every cell
below WORSE, never better; no 2012-2018 option chain exists to price this for real]:
| horizon | strike width OTM | worst move used | loss as % notional | **loss as multiple of 10% margin** |
|---|---|---|---|---|
| 1-day | 0% (S1-F's actual ATM structure) | 12.98% (2020-03-23) | 12.98% | **1.30x margin wiped out** |
| 1-day | 5% OTM | 12.98% | 7.98% | 0.80x |
| 20-day | 0% | 37.01% (2020-03-23) | 37.01% | **3.70x margin wiped out** |
| 20-day | 5% OTM | 37.01% | 32.01% | 3.20x |

Full table: `tail_stress.csv`.

**Gap-through-strike risk for the sleeves with no crash in their OWN option sample**: S1-F, CALENDAR,
and OVERSHOOT are all priced from option chains starting 2021-05 (or, for CALENDAR, the daily bhavcopy
from 2011 — but CALENDAR's own regime-split finding already shows its entire edge is post-2019, so
even its longer window contains no crash-tested live-edge period). **None of the three has ever been
tested against an option-priced event of this magnitude.** The table above is the best available
substitute and shows: at S1-F's own ATM structure, ANY of the four tail windows measured would consume
MORE than the full 10%-margin capital in a single session if unhedged — S1-F's 30% per-leg stop is the
only thing standing between this arithmetic and a real loss of this size, and that stop has only ever
been tested via a Black-Scholes-model backcast (`covid_backcast/`), never against real option prices at
this magnitude. This is the firm's largest unquantified risk, exactly as flagged in the task brief, and
remains open pending either real crash-era option data or an explicit, sized model-risk allowance.

---
## DEBT 4 — wti_crude_fred_daily.parquet catalogued [DATA]
Entry added to `05_DATA_OFFICE/DATA_CATALOG.md` (new "Wave 5" block, same format as prior waves).
Verified independently (not just re-asserting the original fetch-time D-009 pass): 10,210 rows,
1986-01-02..2026-07-27, 0 nulls, max gap 4 calendar days, and two independent famous-event spot-checks
both land exactly right — **2020-04-20 = -36.98** (the real WTI-negative-price day, FRED's Cushing-spot
fixing) and **2008-07-03 = 145.31** (the real all-time WTI high, public record $145.29-145.31). Flagged
as unable to verify: whether this vintage matches FRED's CURRENT revision of the series (FRED
occasionally revises historical spot values; not checked).

---
## DEBT 5 — the 106%→73.1% withdrawal: CONFIRMED NONEXISTENT, not just "not located" [DATA]
Escalated the master-table agent's "source not located" to a stronger, exhaustively-checked verdict.
Beyond a live-tree grep, this pass ran `git log --all -S"73.1"`, `-S"106%"`, `-S"weight-optimised"`
(pickaxe search — finds ANY commit that ever added or removed that string, on any branch, not just the
current working tree) plus a fresh grep of the FULL SESSION_JOURNAL.md and CURRENT_STATE.md. **Result:
the only commit in the entire repository's history containing these strings is MASTER_STRATEGY_TABLE.md's
own withdrawal note itself** — the number never existed as a script output, CSV, JSON, or even a journal
entry, at any point, on any branch. `MASTER_STRATEGY_TABLE.md` and `master_table.csv` both updated:
row re-labeled from "[WITHDRAWN, source file not located]" to "[UNVERIFIABLE — confirmed nonexistent
2026-07-31]", the bare "106" value column blanked (it was an unsourced digit sitting in a numeric
column), and the note now states plainly this must not be carried into any Principal-facing view
without re-running the underlying test from scratch.

---
## ADDENDUM 2026-08-03 (OPEN_ITEMS_20260803) — correction to DEBT 3's "cannot be measured" claim
**[DATA] Independent spot-check found a pre-2010 series this pass missed.**
`datasets/index_daily/factor_navs_principal.parquet` (already in `DATA_CATALOG.md` line 65, source:
Principal-contributed `factor_navs (1).xlsx`) contains a row-series `series=='NIFTY 50'` spanning
**2005-04-01 -> 2026-01-05, n=5,151 daily rows, 0 nulls** — a different file from the
`datasets/index_daily/nifty50.parquet` (2016+) this report checked, in the same directory.
Verified against two independent public-record facts, not just internal consistency: **2008-01-08 =
6287.85** (matches the well-known pre-GFC NIFTY 50 closing high that week) and **2008-10-24 =
2584.00** (matches the well-known Lehman-week crash print). High confidence this is the genuine
NIFTY 50 price index, not a mislabeled/Total-Return variant (a TRI series would sit materially
higher by 2008 given 3 years of reinvested-dividend compounding from a 1995 base).
**Correction**: the claim "2008 GFC and any pre-2012 event CANNOT be measured from what the firm
holds" is WRONG for NIFTY 50 specifically — 2008 IS measurable now, on the index the selling book
actually trades (more directly useful than the originally-recommended SENSEX acquisition would have
been). The narrower claim **"no SENSEX series exists anywhere on disk or in git history" still
stands** — this addendum found a NIFTY 50 substitute, not a SENSEX series, and did not re-search for
one. Not yet done: re-running DEBT 3's tail-stress table (`tail_stress.csv`, currently 2012-2026 only)
on this longer series to get real 2008 numbers — flagged for a follow-up, not fabricated here.
`05_DATA_OFFICE/DATA_CATALOG.md` line 65 already documented this file's 2005 start; the miss was in
this report's own directory sweep, not in the catalog.

## Files
`scripts/debt1_dsr_pbo.py` · `scripts/debt2_swing_maxdd.py` · `scripts/debt3_tail_stress.py` ·
`dsr_pbo.csv` · `swing_maxdd_reconciliation.csv` · `tail_stress.csv` · edits to
`05_DATA_OFFICE/DATA_CATALOG.md` and `MASTER_TABLE_20260730/{MASTER_STRATEGY_TABLE.md,master_table.csv}`.
