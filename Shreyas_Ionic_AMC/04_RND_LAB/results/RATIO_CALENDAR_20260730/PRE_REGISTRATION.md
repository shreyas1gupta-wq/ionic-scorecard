# PRE-REGISTRATION — Ratio Calendar / Diagonal (NIFTY index, sell-near/buy-far)
**Owner:** Aakash Jain (Structurer). **Date:** 2026-07-30. **Frozen before results are read.**
**STATUS (2026-07-30, time of writing):** term-structure measurement DONE (`term_structure.csv`,
3,619 days). Full P&L backtest QUEUED at
`04_RND_LAB/results/BACKTEST_QUEUE_20260730/queue/114_ratio_calendar.py`, smoke-tested on a 3-year
subset (2019-2021, ran clean end-to-end, ~5s) before being dropped in the queue per protocol — NOT
run inline on the full 16-year archive. Two jobs (111, 113b) were ahead of it in the queue at drop
time; results land in `RATIO_CALENDAR_20260730/grid_a_summary_*.csv` and `grid_b_summary.csv` once
the runner processes it. **Everything below the descriptive term-structure finding (§1) is a
pre-registered DESIGN, not yet a measured P&L result — do not read the design as a verdict.**
Signal source: Principal's own idea, verbatim (task brief). Framed as a **vol term-structure trade**:
short near-month vol (fast theta, high gamma) + long far-month vol (slow theta, low gamma, +vega),
profitable when near IV is rich vs far IV and the underlying stays contained.

## 0. Data & method (frozen, executed already for the measurement layer)
- **Instrument:** NIFTY index options, `05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`
  (daily bhavcopy; NOT the 1-min tree — each 1-min expiry file holds only ~10 days of its own life,
  so a next-month leg is simply unpriced there. Bhavcopy carries the full live chain every date.)
- **Monthly expiry identification:** for each (expiry.year, expiry.month), the expiry closest to
  month-end (`max` within group) = the monthly contract. Works across the pre-2019 monthly-only era
  and the post-2019 weekly-expiry era without hardcoding a weekday rule.
- **Near/far definition:** on trading day *d*, the earliest monthly expiry with DTE≥2 = near; the
  NEXT monthly expiry after that = far. (DTE≥2 is a numerical-stability floor for the IV backout, not
  a trading rule — actual entry/exit timing is a tested parameter below.)
- **ATM strike/IV construction (`build_term_structure.py`, DONE, `term_structure.csv`, 3,619 days,
  2011-01-03..2026-07-10, 100% of days have a valid near+far ATM straddle pair):**
  tenor-matched NIFTY **futures forward** price per leg (not spot — spot index history only starts
  2016; futures are in the same archive back to 2011 and correctly price cost-of-carry per tenor,
  material in the 8-9% repo years of 2011-13). ATM strike = the CE/PE pair, **both legs CONTRACTS>0
  that day**, minimizing |strike − forward|. IV backed out via **Black-76** (brentq root-find on the
  closed-form straddle price) — same numerical *mechanic* (brentq on a closed-form price) as
  `INVERSE_VRP_NICHE_20260729/build_iv_rv_series.py`, adapted from spot-Black-Scholes to
  forward-Black-76 for the reason above. Flat discount r=0.065 **[INFERENCE]**, same repo-rate proxy
  the existing script used (only a discount factor here, second-order effect on backout).
  Expanding, no-lookahead percentile (min 60 prior obs) reused verbatim.
- **Gates enforced everywhere:** CONTRACTS>0 required for every leg used in a fill (entry/exit);
  NEVER read SETTLE_PR as an option price (CLOSE only, everywhere — expiry-day SETTLE_PR is the
  underlying's final settlement level, not the option's price — this is the exact bug that produced
  a −15,428-pt fake-loss artifact previously).
- **[DATA quality note caught during build]:** the 2024-25 backfill/extend pass introduces duplicate
  (TIMESTAMP, EXPIRY_DT[, STRIKE, TYPE]) rows in some years; collapsed via `groupby().mean()` before
  indexing (undocumented until this session — flagging for Kavya/DATA_QUALITY_RULES).
- **Daily granularity:** close-to-close only. No intraday stop/trail modelling. Stated, not hidden.
- **Equity curve / drawdown methodology:** P&L is computed at ENTRY and EXIT fills per cycle (cycle-
  level jumps), not from a full daily MTM path within a cycle. This is consistent with "close-to-
  close only, no intraday precision" above, but it means **intra-cycle drawdown is NOT captured** —
  a calendar that is briefly deep underwater mid-cycle (large gap) but recovers by the exit day will
  show no drawdown here. Stated as a limitation, not silently assumed away; maxDD/worst-day figures
  are a FLOOR on true risk, not a ceiling.

## 1. Descriptive finding that motivates the entry-filter design (NOT itself a backtest)
From `term_structure.csv`, forward 10-trading-day changes (H=10, descriptive/ex-post, no trading
rule implied):
| regime | n | mean fwd Δ near-IV (10d) | mean fwd \|underlying move\| (10d) |
|---|---|---|---|
| contango (near cheap, spread<-0.02) | 314 | **+3.12 vol pts** | 2.31% |
| flat | 2,983 | +0.03 | 2.38% |
| inversion (near rich, spread>+0.02) | 312 | **−3.67 vol pts** | **3.99%** |
| near-IV top decile (pct≥90) | 209 | **−4.77 vol pts** | **4.84%** |
| inversion AND top-decile | 137 | **−5.44 vol pts** | (not separately tabled, higher) |

**Reading:** inversion/top-decile-near-IV DOES predict near-IV mean-reverting down (tailwind for a
short-near/long-far vega position) — but it co-occurs with **materially larger underlying moves**
(the exact risk that hurts a short-gamma near leg). This is the central tension the backtest must
price, not assume away: the entry filter that helps the vega P&L is the same filter that raises
containment risk. Both effects must appear in the net result, not just the vega-friendly one.

## 2. Hypotheses (ranked, falsifiable)
- **H1 (primary):** entering when near-IV is in INVERSION (near rich vs far) beats entering in
  CONTANGO and beats UNCONDITIONAL entry, net of costs, because the vega/theta tailwind dominates
  the added containment risk.
- **H2:** near-IV top-decile (session's established reversal lead: "IV top-decile is where SELLING
  pays") improves entries further, alone and combined with inversion.
- **H3 (Principal's explicit ask):** closing 1-2 days before near expiry preserves more edge than
  holding to expiry, once the rupee gamma cost of the final days is measured (not assumed).
- **H4:** the roll variant (keep the far leg, roll only the near leg each cycle) is a viable
  "income machine" distinct from the single-cycle version — test, don't assume.
- **Null/placebo built into the grid, not bolted on after:** the `unconditional` entry-filter cell
  is itself one of the 5 filter arms — H1/H2 are only "real" if inversion/top-decile beats it.

## 3. Test matrix (frozen before run — exact cell count = trials count)
**A. Main grid — single adjacent-month cycle (near, far=next monthly), flat after exit:**
| Axis | Values | count |
|---|---|---|
| Ratio (short-near : long-far) | 1×1, 2×1, 3×2 | 3 |
| Strike structure | ATM/ATM, short-leg ≈0.25Δ OTM (Black-76 delta solve on ATM-IV, **skew ignored — [INFERENCE], flagged**) / long-leg ATM | 2 |
| Entry filter | unconditional, contango (spread<-0.02), inversion (spread>+0.02), near-IV top-decile (pct≥90), inversion∩top-decile | 5 |
| Exit timing | hold-to-expiry (cash-settle intrinsic, landmine #9), close 3d-before, 2d-before, 1d-before near expiry | 4 |
| **Subtotal A** | | **3×2×5×4 = 120 cells** |

**B. Roll ("income machine") grid — a STRUCTURALLY DIFFERENT tenor gap, not a 5th axis on grid A.**
Worked through explicitly (a naive "same adjacent gap, just re-sell near forever" reading doesn't
work: once cycle 1's near leg expires, the old far leg IS the new near-month contract — there is no
room left to sell a fresh nearer-dated short against it while still calling it "far"). The mechanic
that actually matches "keep the long far leg as a multi-cycle asset" needs a **skip-one-month gap**:
- far leg bought once, 2 monthly cycles out (near1, skip near2, buy near3).
- Sub-cycle 1: sell near1 against long near3(=far). At near1's exit (per the SAME exit-timing rule),
  close near1 only — near3 still has ~1 cycle of life left and is untouched.
- Sub-cycle 2: sell a FRESH near2 (now the nearest monthly) against the SAME held near3. At near2's
  exit (same rule), close near2 AND close near3 — super-cycle ends (bounded to 2 sub-cycles, not
  open-ended — a deliberate scope limit, not an oversight).
- Compared against the matching **NO-ROLL baseline**: two fully independent, fully-flattened
  adjacent-month cycles back-to-back over the same span (cycle A = near1/near2 entered day0, exited
  at cycle-1's exit day — near2 bought as A's FAR leg and sold flat at that exit; cycle B = a FRESH
  near2/near3 entered right after — near2 sold AGAIN, freshly, as B's near leg). Worked through
  fill-by-fill: near1 and near3 each see exactly 2 fee-events (one open, one close) in BOTH roll and
  no-roll. **near2 is where they differ** — no-roll buys it once (A's far leg) then sells it flat,
  THEN separately sells it again fresh (B's near leg): 4 fee-events. Roll never owns near2 as a long
  at all (near3 is bought directly as the far leg from day0) — near2 only ever exists there as the
  sub-cycle-2 short: 2 fee-events. **The saving is one full extra round-trip on the near2 contract
  specifically** — a superfluous buy-then-sell-flat that the no-roll baseline pays and roll skips by
  going straight from "no position" to "short" in one order. That saved friction is H4.
- Tested at 1×1 / ATM-ATM only (the roll MECHANIC is the question, not its interaction with ratio/
  strike — crossing those in would 5× the grid for a question that doesn't need it).
| Axis | Values | count |
|---|---|---|
| Entry filter (evaluated at near1) | same 5 as grid A | 5 |
| Exit timing (applied to each sub-cycle) | same 4 as grid A | 4 |
| **Subtotal B** | | **5×4 = 20 cells** (each compared against its no-roll-baseline twin) |

**TOTAL TRIALS = 120 + 20 = 140 cells.** (Corrected from an initial 240-cell draft during pre-reg
design, BEFORE any result was read — the roll mechanic above was worked through on paper first;
this is a design fix, not a post-hoc tune.)

One entry opportunity per near-monthly cycle (the first day that cycle becomes "near"); if the
filter fails that day, the WHOLE cycle is skipped (no mid-cycle re-tries) — a deliberate
simplification, stated up front so it cannot look like retroactive cherry-picking.
Every cell enters the trials ledger (`trials_ledger.csv`) — headline reporting shows marginal
slices (one axis varied, others at a stated base case) plus the single pre-registered "best design"
cell; the full 140-row grid is the honest record, not a search space to mine post-hoc.

## 4. Costs & friction (COST_STANDARDS.md, D-021 binding; SHARED_CONTEXT Rs25/lot/side)
- **Rs25/lot/side per leg.** 1×1 = 2 legs = Rs50/side = Rs100 round trip PLUS the exit trip = Rs200
  full round-trip on a single-cycle 1×1. **2×1 = 3 legs, 3×2 = 5 legs** (short+long principal legs,
  ratio counted per contract) — friction scales with total leg count, not spread count.
- Slippage: liquid-ATM-index floor (max(1 tick, 0.25% premium)) per COST_STANDARDS; OTM short leg at
  ~0.25Δ still liquid-index tier (NOT the "illiquid strikes" 1-2% tier — that tier is for far-OTM
  *single-stock* wings, the −883% artifact class; NIFTY monthly ATM-to-0.25Δ is not that).
- **Friction reported as % of GROSS for every one of the 140 cells, prominently** — this is where
  the ratio-heavy variants either justify themselves or die exactly like NS-1 (costs ate 55-84% of
  gross on multi-leg designs collecting small premium).
- Roll variant adds a full near-leg round-trip cost EVERY cycle on top of the base structure.

## 5. Margin (Principal ruling, ambiguous for cross-expiry — test BOTH, do not pick the flattering one)
Calendar = CROSS-expiry (not naked, not same-expiry hedged) → real SPAN sits BETWEEN the two ruled
bounds. Report return-on-capital at **BOTH 5% (same-expiry-hedged bound) and 10% (unhedged bound)**
of notional; state plainly that the true number depends on the broker's actual SPAN cross-margining
of a calendar, which is an execution question for Tara Singh, not something this desk assumes away.
Ratio variants (2×1, 3×2) have a NET SHORT leg beyond the hedge — margin treatment must reflect the
unhedged excess (the extra short near contract(s) are naked beyond the 1:1 hedged core), quantified
per cell, not glossed as "still a calendar."

## 6. K-012 differentiation (read BEFORE claiming this is new — `KILLED_IDEAS.md`, `STRATEGY_REGISTER.md` S-03)
K-012 (FF calendar, S-03) was: **single-CE, SINGLE-STOCK universe** (large-cap gated), entry driven
by an "FF"/forward-factor signal (`forward_factor_strategy.forward_vol`) that had a real T9 lookahead
bug in v2, 1×1 double-calendar structure (`standard_calendar.py` confirms: iterates individual stock
option folders, TARGET_DTE=30). It died on: (a) **61.3% of forward signals fired into DEAD back-leg
markets** (zero volume, mostly zero OI, even in mega-caps) — a LIQUIDITY death, not a signal death;
(b) the pre-registered causal gate still nets **-0.03/Rs100 @1x, -2.36 @2x** even after the liquidity
problem is acknowledged.
**This design is mechanically different on 3 of 4 axes:**
1. **Instrument:** NIFTY INDEX, not single-stock. `term_structure.csv` shows **100% of trading days**
   have a valid, CONTRACTS>0 near+far ATM straddle over 16 years — the exact failure mode that killed
   K-012 (dead back-leg markets) does not exist here for ATM/near-ATM strikes.
2. **Entry signal:** measured vol term-structure STATE (real Black-76 backout), not a fundamental/
   forward-vol factor with a demonstrated lookahead history.
3. **Ratio:** 1×1, 2×1, 3×2 tested; K-012 was a straight 1×1 double calendar only.
4. **Same on:** exit-timing discipline was not K-012's focus; this design's exit-timing test (§H3) is
   novel relative to that family.
**Verdict up front, to be confirmed or falsified by the run, not asserted:** if this design STILL
fails, the honest reading is that liquidity was necessary-but-not-sufficient for K-012's failure —
i.e., the calendar VEHICLE itself may be structurally weak on NIFTY too, not just illiquidity-driven.
The backtest must distinguish these two explanations, not default to "liquidity fixed it."

## 7. Benchmark & reporting requirements
Benchmark: **S1-F** (12.57% CAGR / -4.44% maxDD / Calmar 2.83 / Sharpe 2.15 / PF 2.21).
Report per cell (140) + headline slices: GROSS/NET pts and % of margin-capital (both 5%/10%),
monthly win-rate GROSS vs NET, CAGR/maxDD/Calmar/Sharpe/PF, Newey-West t, full return distribution
(skew matters — asymmetric payoff), worst month, COVID (2020-03) / 2018 / 2015-16 behaviour, held-out
2026H1 reported separately (selected on NOTHING there), gamma-cost-of-last-1-2-days in rupees,
friction as % of gross, and the K-012 differentiation verdict.

## 8. Pre-registered kill criteria (frozen — no re-tuning after results are seen)
- **Promotion bar:** best cell must be NET-positive at 2× ALL COST_STANDARDS frictions (per the
  firm's binding promotion rule) at BOTH the 5% and 10% margin bound, AND beat the `unconditional`
  entry-filter cell at the same ratio/strike/exit/roll settings (placebo test — a filter that doesn't
  beat doing nothing-conditional is not earning its keep).
- **Family kill:** if the best cell's friction consumes >50% of gross, OR if inversion/top-decile
  filters do NOT beat unconditional net of costs, OR if NET Sharpe/Calmar is negative at both margin
  bounds — report as KILLED, same standard applied to K-012, no softening.
- **This is a valid, valuable result either way.** A clean kill with the liquidity confound removed
  is itself the finding the Principal asked for ("check once again" energy, pre-empted this time).
