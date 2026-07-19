# ALPHA_RANKER — Wave-4 Hypotheses (orthogonal mechanisms only)
Author: Prof. Aditya Verma (R&D), 2026-07-17. Machine-readable twin: `rnd/wave4/hypotheses_w4.json`.

## Design constraint (why this list looks the way it does)
The 7-leg composite is PARKED on multiplicity alone (457 trials, DSR≈0). **Correlated variant-trials
make that worse.** Every W4 idea is therefore (a) a mechanism NO current leg carries, verified against
440 existing cards + FINAL_MODEL §4 rejected-list + KILLED.md resurrection conditions, (b) capped at
1 base trial + 1 pre-registered refinement child, logged per-family in the trials ledger, (c) built
ONLY from verified on-disk columns (schemas checked 2026-07-17: MASTER_fundamentals_pit metrics,
panel_long 31 cols, macro_state 127×23, market_state 249×27, cube_volume 1,238×751 [5yr-only]).

**Prior-art exclusions (checked, NOT re-proposed — honoring kills):** frog-in-the-pan / information
discreteness & trend-R² (MOMQ_fiptilt/r2tilt cards — dilute momentum, rejected); 52w-high (H006 +
H041 horse-race); downside beta/semideviation (H012 family); fundamental-momentum deltas (H025
growth-accel, H044 margin-expansion, ΔROA — single deltas fragile, only durable inside QMJ);
shareholder yield (= QMJ payout leg + net-issuance leg recombined, corr-doomed; dividend col is also
only ~15% coverage); coskewness/tail-beta (H012+MAX-lottery family adjacency); rank-product
interactions (H029/H030/H046 — note W4-12 tests a DIFFERENT operator, sequential gating); PEAD in
any form (event-time re-test 2026-07-17 = confirmed dead); sector rotation (W2S-11, IDG-I-15, S1 —
three kills); OBV/volume-price divergence (H036); vol-scaled momentum, Hurst, seasonality, size.

---

## A. Forensic / balance-sheet (full-coverage fundamentals, untested mechanisms)

### W4-01 — Net Operating Assets (Hirshleifer bloat) — **H**, sign −
NOA_proxy = (fixed assets + cwip + other assets − other liabilities) / total assets, PIT asof-join.
(No cash line in screener BS format; 'investments' treated as the financial leg — [INFERENCE] proxy, labeled.)
Orthogonality gates: asset-growth (composition-level vs size-growth; kill if corr>0.6), CFO/PAT,
tested accruals H022. Money: bloated balance sheets presage write-downs; 49k-row coverage, free.
Refinement: ΔNOA (flow version).

### W4-02 — CWIP commissioning / capex-cycle inflection — **H**, sign +
z_cs(ΔFA/TA_lag) − z_cs(ΔCWIP/TA_lag): CWIP converting into commissioned fixed assets = capacity
online = operating leverage ahead (the firm's own documented microcap-multibagger engine). CRITICAL
gate vs asset-growth (completion-phase ≠ total growth; kill if corr>0.6). Money: mid-capex-cycle
India, nobody screens CWIP systematically. Refinement: binary commissioning-event version.

### W4-03 — Tax-rate authenticity — **H**, sign +
3-FY median 'tax %', winsorized [0,40]. Near-statutory tax = earnings the taxman certifies; near-zero
tax with high PAT = manufactured. Extends the earnings-authenticity edge (CFO/PAT, IC_IR 1.14, but
~7.6k-row coverage) to the FULL universe (48.6k rows) via a different verifier — coverage is itself
alpha (2026-07 lesson). Gate: corr vs CFO/PAT on overlap sample, kill if >0.6. Refinement: Δtax trend.

### W4-04 — Other-income dependence — **M**, sign −
OI_share = Σ(other income, 3FY)/Σ(PBT, 3FY), winsorized, financials excluded (sector col). Profits
made of treasury/one-offs fade; market prices headline PAT. Gate vs QMJ profitability leg (partial
complement, kill if corr>0.6). Refinement: ΔOI_share.

### W4-05 — Reporting-lag governance signal — **H**, sign + (short/stable lag)
lag_days = available_date − fiscal-period end, from MASTER_fundamentals_pit's own metadata; score =
−z(4-period median lag) with a penalty for lag lengthening >30d vs own history. Filing delay is the
earliest observable symptom of trouble, PIT by construction (the timestamp IS the data), full
coverage, costs nothing. No current leg uses filing metadata as information. Refinement: pure
lag-lengthening sell-flag.

### W4-06 — Debt-issuance anomaly — **M**, sign −
Δborrowings/TA_lag (yoy). The untested debt channel of the financing anomaly — NOT the killed
deleveraging idea (that was distress-repair on levels). Main risk = asset-growth overlap (debt funds
assets): kill/fold if corr>0.6. Refinement: composite external financing Δ(borrowings+equity)/TA as
a REPLACEMENT candidate for both balance-sheet legs (leg-count reduction).

### W4-07 — Issuance-leg purification (bonus adjustment) — **H**, leg-repair
bonus_flag = FY with Δequity>0 AND Δreserves ≤ −0.8×Δequity (reserves capitalization); zero those
years in the %ch-equity-capital proxy. ONE comparison, adopt-if-better, ISSUANCE family ledger.
Removes the disclosed ~8% bonus/split noise from a live survivor — cheapest possible IC gain, no new
family, no new multiplicity.

## B. Liquidity / microstructure (category untouched by all 440 cards)

### W4-08 — Amihud illiquidity premium, cost-aware — **H**, sign +
ILLIQ = 252d mean |ret|/(₹volume), log, size-residualized as the PRIMARY construct (size corr 0.6-0.8
expected — H028 already tested size itself). Structurally orthogonal: no leg uses volume. Mandatory
cost honesty: 2x-slippage net eval + top-half-liquidity subuniverse eval + long-leg ADV capacity
report. Even if the premium is cost-eaten, it prices the microcap lens and OUR own capacity.
CAVEAT: cube_volume is 5yr-only → no 21yr cross-regime check (disclosed). Refinement: share turnover
(₹vol/mktcap, Datar).

## C. Macro cross-sectional (untested category; regime work so far was market-level only)

### W4-09 — Currency-sensitivity rotation — **M**, sign + (conditional)
beta_fx (36m rolling, monthly stock ret on ΔUSDINR) × sign(usdinr_chg_3m): own names whose FX
exposure is a current tailwind. Gates: corr vs residual momentum (kill >0.6); concentration check —
must not be a concealed IT/pharma bet (sector-neutral robustness). CAVEAT: macro_state = 127 monthly
rows (~10.5yr, no 2008). Refinement: rate-sensitivity version (india10y 3m change).

## D. Price / overreaction (long price history = our deepest asset)

### W4-10 — Long-term reversal 36-60m (De Bondt-Thaler) — **M**, sign −
Cumret(t−60m → t−12m), skip-momentum-window, primarily a 5Y-lens candidate (the horizon where the
model is thinnest — currently value+quality only). CRITICAL gate: 5y losers ARE cheap — must add
leave-one-out increment over EY specifically or die. Refinement: EY-residualized version.

### W4-11 — Listing-age / IPO seasoning — **L**, sign + (seasoned)
Months since first non-NaN close in cube_close_long (mask cube-start-censored names); <24m = penalty
(lockups, overhang). India IPO boom keeps feeding young names into the universe. Gates: net-issuance
and size corr checks. Refinement: binary <24m exclusion gate at composite level.

## E. Combination methods (innovation on HOW legs combine — not new variant factors)

### W4-12 — Conditional double-sort: momentum WITHIN quality — **H**
Sequential gate: top-50% QMJ first, rank residual momentum only inside it (bottom half unscored).
This is NOT the killed rank-product interaction (symmetric blend) — different operator. Pre-registered
win: high-vol-regime IC (the momentum leg's documented fragility) improves ≥ +0.05 with <10% full-period
IC_IR cost. Junk-momentum is what crashes; quality-gating is the crash hedge that costs no premium.
Refinement: cheap-within-improving (EY inside positive-Δopm half).

### W4-13 — Factor-momentum leg-weighting — **M**
weight_leg ∝ max(floor, trailing 12m mean IC of that leg), vs the static equal rank-average. Causal,
no regime variable — NOT the killed return-blend overlay. K-015 bar applies: must beat the static
composite net-of-cost AND on Sharpe. Refinement: value-spread conditioning on the EY weight only.

## F. Regime / sizing layer (the highest-value open problem)

### W4-14 — LEADING bear-regime classifier — **H**, sizing
Walk-forward expanding logit, refit annually, label = NIFTY500 fwd-3m < −5%. Features (all causal):
21yr set from market_state (breadth level + 3m thrust, EY_hist_zscore, market_vol slope, ERP_proxy);
10yr secondary set from macro_state (term_spread_us, us10y_chg_3m, usdinr_chg_3m, gold_vs_equity_1m).
Use: momentum weight ×(1−p_bear), QMJ/EY ×(1+p_bear) floored at 0; gross scalar min(breadth scalar,
1−p_bear). Pre-registered bar (K-015 law): beat BOTH static composite AND the existing trailing-breadth
scalar on Sharpe with maxDD no worse — judged as a RISK overlay, never on CAGR. The parked overlay
failed because it was TRAILING; the novelty here is strictly the predictive feature set.
Refinement: 2-feature rule fallback (breadth<40% & falling, OR curve inverted & vix rising) if
walk-forward AUC <0.6.

### W4-15 — Cap-tier conditional composite (microcap 4th lens) — **M**, allocation
Canonical 7-leg composite's IC per PIT mktcap quartile (no refit, no new factor). If IC concentrates
in small tiers, tier-weighted allocation subject to W4-08 capacity caps and the 2.4-4.2pp/yr smallcap
drag hurdle (KNOWLEDGE_BASE #17). Either answer pays: more money per signal, or proof our capacity is
large. Distinct from the tested smallcap-tier EY factor (absorbed by EY at 0.94). Refinement: 3-tier
version.

## G. Event

### W4-16 — Earnings-announcement-month premium — **M**, sign +, 1M only
Flag names whose next announcement is expected in the forward month (predicted from own PIT filing
cadence). Frazzini-Lamont anticipation premium — DISTINCT from PEAD (killed): no surprise variable,
pre-scheduled attention/uncertainty-resolution effect. The 1M lens is currently empty; this is the
cheapest possible 1M leg. CAVEAT: 1M has no 21yr cross-check (structural, disclosed).
Refinement: flag × QMJ rank.

---

## Priority summary
- **H (8):** W4-01 NOA, W4-02 CWIP-commissioning, W4-03 tax-authenticity, W4-05 reporting-lag,
  W4-07 issuance-purification, W4-08 Amihud, W4-12 double-sort mom|quality, W4-14 leading regime classifier.
- **M (7):** W4-04 other-income, W4-06 debt-issuance, W4-09 FX-rotation, W4-10 LT-reversal,
  W4-13 factor-momentum weights, W4-15 cap-tier lens, W4-16 announcement-month.
- **L (1):** W4-11 listing-age.

## BLOCKED (real ideas, data not on disk — do NOT start; propose via Data Officer D-009/D-033)
1. **Credit-spread regime input** for W4-14 — no Indian corporate-bond spread series on disk
   (FIMMDA/CCIL or a AAA-vs-gsec composite needed). The single best-documented leading bear feature.
2. **Shareholder yield / dividend events** — 'dividend payout %' has ~7.7k rows (~15% coverage);
   needs full NSE corporate-actions dividend history before H039 can run honestly.
3. **Promoter/insider accumulation drift** — proven signal (IC_IR 1.33, gates clean) blocked on stale
   2023-12 shareholding; already a standing resurrection candidate (CONSOLIDATION §resurrection).
4. **Analyst estimate revisions / SUE** — no feed (Trendlyne is the named D-009 candidate).
5. **Delivery-% accumulation** — H035 PARKED, data stale; needs D-033 refresh.
6. **Overnight-vs-intraday return share** (retail/institutional tug) — needs daily OPEN prices;
   only closes on disk.
7. **Single-stock options-flow cross-section** — coverage too thin/patchy per W2_OPT_DATA_COVERAGE.md.

## Trials-ledger commitment
16 base trials + at most 16 pre-registered children across 15 NEW families (W4-07 logs into the
existing ISSUANCE family, W4-15 into COMPO). No further variants without a new wave brief — that is
the whole point.
