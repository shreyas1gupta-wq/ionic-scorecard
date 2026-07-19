# ALPHA_RANKER — Standing Research Queue (continuous mode)

## >>> SCORECARD RESET (2026-07-17/18): DONE — see `rnd/scorecard/SCORECARD_FINAL_SUMMARY.md` for full honest
## verdicts (1M relative REAL; 1Y/5Y relative FRAGILE-usable; ALL of absolute NOT-usable-yet). S8 recalibration
## (new eval philosophy, memory item #8) + R8 diagnosis of the 5Y inverted-U (real effect, growth_longevity
## leg over-weights cyclical/commodity earnings peaks) both landed — PENDING PRINCIPAL/CIO ruling on whether to
## adopt the R9 dampening fix as v2 (blueprint §5 locks the leg list, builders can't self-authorize this).
## HEADLINE FOLLOW-ON (from the parallel firm-methodology research, `Shreyas_Ionic_AMC/04_RND_LAB/
## FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036.md`): the scorecards have NO exit/deceleration trigger — spec'd
## (`rnd/scorecard/EXIT_TRIGGER_SPEC.md`, 4 legs) + build in progress (`rnd/scorecard/exit_trigger_flags.parquet`).
## This is now the #1 priority next build, per the roadmap's CIO-lens synthesis.

## CONCURRENCY (Principal 2026-07-17): GLIDE DOWN to steady-state 3 concurrent agents. Do NOT stop running
## agents — let all currently-assigned ones finish; stop replenishing above 3; top back up only to a max of 3.
## (Was 8-9; now 3. Sustainable pace, aligns with diminishing-returns on factor-mining + D-023 default.)

## >>> [DONE, see banner above] RE-OPENED (Principal 2026-07-17): SCORECARD RESET — full switch. The R&D became an over-corrected
## spider-web; mandate now = SIMPLE, LOGIC-FIRST, two clean SCORECARDS from ALREADY-FOUND (and wrongly-rejected)
## alpha — NO new research. Logic > statistics (don't reject real alpha on t/PBO). Deterministic, no-overfit.
## RELATIVE scorecard (LS benchmark, Sharpe + monotonic): 1M = momentum(regime lookback, SKIP latest ~15-20d)
##   + earnings growth/surprise + funda check + NO-NEGATIVE-NEWS; 1Y = val+growth+momentum, gate top-90%ile
##   quality + regime; 5Y = valuation+growth primary, gate top-80%ile quality + regime.
## ABSOLUTE scorecard (long-only, CAGR+Calmar): prob + intensity of future return = expected-EPS-growth ×
##   PE-re-rating (from current valuation + regime). NOT relative->absolute. NOT the final model — a scorecard.
## 2 Opus (review/consolidate + design — Fable retired, org spend cap; SWITCHED TO OPUS 2026-07-18 per Principal)
## + 7 Sonnet (build components + assemble). Reuse tested components.
## FUND-MANAGER LENS (Principal 2026-07-18): every agent below re-reviews its inputs not just statistically
## (t/p/n/DSR/PBO) but with FM WISDOM — does this make business/market sense, would a PM actually size this,
## is the logic sound even where the sample is thin. Statistics inform; they do not overrule sound logic.
## >>> LAUNCH-AFTER-COMPACT — the 9 agents (all: no-new-research, logic-first, deterministic, no-overfit,
## FM-lens re-review of all backtests/savings/results before use):
##  F1 (opus, rnd-head-aditya-verma): REVIEW everything + diagnose the spider-web + consolidate MISSED/REJECTED
##     alpha (incl. the reclassified forward-watch: oversold-MR certified, credit-convex-hedge, clean-surplus,
##     5Y cond-inflection IC_IR~0.40, promoter-drift IC_IR 1.33 data-blocked) into a usable-alpha inventory.
##     Logic > stats; apply FM lens to each candidate (does it make sense, not just does it pass a test).
##  F2 (opus, quant-head-arjun-rao): DESIGN the two-scorecard blueprint by logic (relative 1M/1Y/5Y + absolute),
##     per the spec above. FM lens: sanity-check each design choice against how a real PM would build this.
##  S1 (sonnet): RELATIVE 1M — momentum(regime lookback, SKIP latest 15-20d) + earnings surprise/growth +
##     funda check + no-neg-news → LS Sharpe+monotonic. Reuse capstone momentum + earnings-PIT + S6 news screen.
##  S2 (sonnet): RELATIVE 1Y — val+growth+momentum blend, GATE top-90%ile quality + regime → LS Sharpe+monotonic.
##  S3 (sonnet): RELATIVE 5Y — valuation+growth primary, GATE top-80%ile quality + regime; blend sector-relative
##     WITH absolute-merit (memory #7, not blind neutralization) → LS Sharpe+monotonic.
##  S4 (sonnet): ABSOLUTE scorecard — expected return = expected-EPS-growth × PE-re-rating (current valuation +
##     regime) → probability + intensity, long-only → CAGR + Calmar. (EPS growth from fundamentals PIT; PE-rerating
##     from valuation-vs-history + regime band 0/65/160.)
##  S5 (sonnet): CONSOLIDATE all backtests → workflows + metrics (feeds F1; the significance-reclassification sweep).
##  S6 (sonnet): NO-NEGATIVE-NEWS screen from news data (india_fin_news 125K etc.) for the 1M funda gate.
##  S7 (sonnet): ASSEMBLE both scorecards + verify DETERMINISM (same-data→same-score) + NO-OVERFIT + metrics
##     (relative: LS Sharpe/monotonic; absolute: CAGR/Calmar). Prep EPS-growth/PE-rerating inputs.
## RESUME 2026-07-18 (Fable->Opus swap; org spend cap cleared): 3-CAP (D-023) means staged waves, not all 9 at
## once. Wave A (launched): F1 review/inventory, F2 blueprint, S6 no-neg-news screen (none depend on the
## blueprint). Wave B (after F2 blueprint lands): S1/S2/S3/S4 builders, 3 at a time. Wave C (last): S5 consolidate
## + S7 assemble+determinism+metrics. Determinism + no-overfit + logic-first + FM-lens throughout.

## >>> [superseded] SOFT-CLOSED (Principal 2026-07-17): STOP — no more research, no new agent launches. The 2 agents that
## were mid-compute (earnings-inflection, best-Pup/CAGR-Sharpe-MDD absolute model) finish + save; nothing else
## dispatched. Standing-order PAUSED. Do NOT auto-resume on restart. Awaiting Principal's next instruction.
## Everything durable: WAVE4_FINDINGS.md (master + all reclassifications), REGIME_SPEC_V2.md, this queue,
## analyst_layer/, forensic/, cards/. Resume = read WAVE4_FINDINGS then this queue.

## NEXT-LAUNCH TODO (only when Principal says START):
1. Sector-relative composite rebuild BUT NOT BLIND (Principal 2026-07-17): blend sector-relative WITH
   absolute quality/growth/valuation merit — a true high-ROE/high-growth/fair-value name deserves absolute
   credit beyond its within-sector rank (sector-neutral 8/10 -> real ~8.5/10). 5Y: weight GROWTH LONGEVITY +
   VALUATION heavily. See memory alpha-ranker-valuation-band-momentum-rule #7.
2. Significance-reclassification re-audit: sweep all wave KILLs, pull any significance/robustness-only (sound
   logic + correct sign + decent effect) into forward-watch. Language: never "KILL (PBO)".
3. Finish reading earnings-inflection verdict off W5IN_* cards + fold absolute-model-v2 (CAGR/Sharpe/MDD/best-Pup).
4. Then: forward-test design + data-ask package (Principal decisions).

## STANDING ORDER (was: keep researching until Principal says STOP) — PAUSED per soft-close above.
Maintain a steady agent pipeline; replenish from this queue as agents complete; checkpoint every result to
disk so a context-limit restart resumes cleanly. GOVERNOR (unchanged): distinct ORTHOGONAL mechanisms only
(no variant-spam — it deepens the multiple-testing hole per FRONTIER_OPUS + COMPLETENESS_CRITIC); hard gates
= lag+placebo only; low-t rule (logic+effect+drop-one, PBO/DSR advisory); money-first incl. absolute return
BUT on a RECONCILED net-LS figure (critic: current net_LS_v2 is internally inconsistent — reconcile first);
everything = candidate NEXT-SLEEVE on its own forward clock; NEVER touch the frozen 7-leg (grades ~Dec 2026).

## QUEUED (dispatch as slots free)
1. ETF cross-asset sleeve — gold/silver/copper, Nasdaq/SP500, Nifty50/midcap/smallcap/microcap, momentum/
   lowvol ETFs. Score AS ASSETS (TS-momentum, relative-momentum, carry, index-valuation-vs-history, vol
   regime), horizon-differentiated 1M/1Y/5Y. [LAUNCHED]
2. Business-model KB — per-stock "how it makes money / unit economics / value chain / moat" from concalls
   (139+267) + screener business descriptions + annual-report business sections; structured for analyst
   agents' forward per-stock phase. Equity-research-report CORPUS = DATA-ASK (broker PDFs need sourcing;
   use reports for BUSINESS-MODEL understanding, NOT their buy/sell/targets).
2b. [PRIORITY] FIX + RE-RUN drop-one — the drop-one script is BUGGY (leave-one-year-out returned identical
   full-sample numbers for every dropped year; only clean-surplus of 4 ran). Rewrite the LOYO/LOSO loop
   correctly, run all 4 candidates. ALSO note: clean-surplus STANDALONE has mono~0.006 + negative LS spread
   — it's a COMPOSITE-INGREDIENT candidate (adds to 8-leg IR), NOT a standalone sleeve. Re-check the others
   for the same standalone-vs-composite distinction.
3. Turnover/fill/capacity audit on the momentum rescues (critic's "most likely to evaporate live").
4. Book-level factor CO-CRASH model (7 legs + additions unwinding together in a junk rip — never modelled).
5. RECONCILED net-of-cost decile-LS figure (one number, verified EY~2%/yr) — after harness-fix lands.
6. [Principal 2026-07-17] MOMENTUM-AT-VALUATION-EXTREMES test — momentum IC/return by valuation-band tertile
   (0-65 / 65-160 / 160+); confirm momentum fails BOTH tails; encode valuation-conditional momentum gate.
7. [Principal 2026-07-17] LONG MULTIYEAR CYCLE scan (5/10/20/50/200-250yr) — debt supercycle (Dalio), rate
   supercycle, commodity supercycle, demographic dividend, Kondratiev, dollar/reserve-currency, geopolitical.
   HONESTY GATE: only surface cycles we can CONFIDENTLY use as CONTEXT/PRIOR for next 1-25yr; SKIP narrative/
   non-backtestable ones (most 50-250yr are stories, not signals on ~20yr IN / ~100yr US data). Not tradeable formulas.
8. Rolling books/papers + forensic idea-gen (Opus tick) when queue runs low — distinct mechanisms only.

## DIRECTIVE UPDATES (2026-07-17): M-term uses Principal's 0/65/160 band ONLY (sign-only); Buffett indicator
## DROPPED; momentum gated OFF at valuation extremes. See memory alpha-ranker-valuation-band-momentum-rule.
## GOLD/CASH DE-RISK (Principal 2026-07-17): in bear/crisis, leg correlations converge to 1 & everything
## falls together — relative selection CANNOT protect; only ASSET ALLOCATION (gold/cash) does. This is the
## core rationale for the ABSOLUTE scorer: at the 160+/crisis band it routes to GOLD/CASH via the ETF sleeve.
## => ETF sleeve MUST treat CASH as the explicit default safe asset (not just rotate risk-assets); gold =
## crisis hedge. Absolute crisis state = de-gross equities + allocate gold/cash. Co-crash agent quantifies corr->1.

## W5 IDEA BATCH (Aditya Verma, 2026-07-17) — full specs in `wave4/hypotheses_w5.json`
10 distinct mechanisms, ZERO momentum variants, biased convex/forensic per wave-4 learnings. All
constructions verified against the 34 on-disk metric_norm fields (dividend payout % + CF set = ~750-firm
subsets, disclosed). Every test must report PAYOFF SHAPE (skew/crash-episode conditional means, per
TAIL_CONVEXITY.md method) alongside rank-IC — critic blind-spot #4. One base + max one refinement each.
- **W5-01 [H]** Cost-elasticity discipline (anti-sticky costs; expenses vs sales elasticity in DOWN-sales
  years) — behavioral, convex, no leg touches cost response.
- **W5-02 [H]** Implied borrowing cost (interest/avg borrowings, size+sector-residualized) — imports the
  CREDIT market's information; convex via short-leg blowup avoidance.
- **W5-04 [H]** Net financial slack ((investments−borrowings)/assets) — explicit crisis-conditional
  convexity bet; graded on stress-month payoff, not unconditional IC.
- W5-03 [M] Fundamental operating leverage (op-profit sensitivity to sales; kill if corr>0.6 vs killed H023).
- W5-05 [M] Treasury bloat / diworsification penalty (composition of asset growth — capital-allocation agency).
- W5-06 [M] Dividend continuity under earnings stress (payout persistence; ~750-firm subset).
- W5-07 [M] Borrowed dividends red flag (payout held while debt rises, CFO can't cover; forensic).
- W5-08 [M] Moat proxy: OPM level x stability, 5Y (the coverage-map's own named untested gap; H023 caveat).
- W5-09 [M] Realized fundamental stress-beta (COVID-FY21 operating drawdown as PIT trait; pilot-grade).
- W5-10 [L→H on data] Debt-maturity/refi wall — DATA-BLOCKED (needs current/non-current borrowings split).
Buildable-now 7 · subset-limited 2 · data-blocked 1. Dispatch order: W5-01/02/04 first as slots free.

## PRINCIPAL DIRECTIVES (2026-07-17, batch 2):
- PEAD-CLUBBED: plain PEAD is dead in India (IC -0.003); test earnings-surprise CLUBBED with top-decile +
  volume-surge + gap-up + uptrend (Minervini earnings-breakout). Volume data 2021+ only → recent-era, flag. [LAUNCHED]
- OVERBOUGHT-CONTEXT RULE: an "overbought" reading must NOT trigger a fade/sell when it's a SHARP RECOVERY
  off a fall (that's short-covering / oversold-rebound, not froth). Only fade froth-overbought in a SUSTAINED
  uptrend. Encode in the mean-reversion/overbought logic: overbought-in-recovery = hold/ride, not fade.
- MOMENTUM RESCUES = DEAD END (drop-one v2 + turnover/fill): hurt the composite (-0.05 to -0.17 incremental),
  era-fragile (2021-26-cube-only, same bug class as H046/H009), ~1 crowded bet (null-sweep), and 76-78% of
  the short leg is unborrowable in India. Not a new sleeve. Stop testing momentum variants.

## PRINCIPAL DIRECTIVES (2026-07-17, batch 3):
- BREADTH-AT-EXTREMES ONLY + VIX=NOISE: the sizing/de-risk trigger fires only at breadth TAILS — washout
  (>~30% of Nifty500 below 200DMA) or froth (<~5% below 50/200DMA); breadth does nothing in the middle.
  DROP/down-weight VIX (mostly noise). This IS the junk-rip conditioner the co-crash analysis called for.
  Replaces the continuous breadth+VIX scalar in the absolute-scorer sizing layer. (thresholds soft, not rigid.)
- EARNINGS-SUPPRESSION-THEN-BOUNCE + TURNAROUND/CYCLICAL: test investment-suppressed-earnings pre-inflection
  as alpha, CONDITIONAL on quality+revenue-traction (raw high-investment = the NEGATIVE asset-growth anomaly;
  edge is the conditional subset only). 2x-SURE BAR (drop-one + era-split + orthogonality + economic-clean).
  No-lookahead crux: identify suppression phase PIT, never from the future bounce. [LAUNCHED]

## W6 IDEA BATCH (Aditya Verma, 2026-07-17) — full specs in `wave4/hypotheses_w6.json`
9 distinct mechanisms, ZERO momentum variants. Steered by the W5 outcome: the one win was W5-02
implied-borrow-cost as a CONVEX HEDGE (worst-decile-mkt-month LS +3.5%, COVID +4.4%, weak linear IC) —
W6 is biased convex/counterparty-information/authenticity. EVALUATION FIX encoded in the batch: the
W5 verdict logic called W5-02 "not convex" from UNCONDITIONAL skew; W6's pre-registered primary
convexity statistic is mean_LS_worst_decile_mkt_months + episode conditional means, NOT skew.
All constructions verified against the 34 on-disk metric_norm fields (re-checked 2026-07-17; CF set
~750 firms + financing-schema 1,158 rows flagged where used). NOT re-proposed (killed): cyclical-EY,
sector-rotation, plain PEAD, NOA, reinvestment_runway, moat, distress-composite. H040-overlap rule:
W6-01/02/03/05 touch universe_forensic flag space — corr vs H040 composite BEFORE spend.
- **W6-01 [H]** Investment-book yield authenticity (other income / avg investments; phantom-cash tell,
  Satyam/Cox&Kings §B "cash reality") — convex via short-avoidance.
- **W6-02 [H]** Revenue-mix drift / business-model-mix anomaly (other-income share drift while core OP
  stagnates; Ricoh pattern; refinement = financing-schema-appearance event flag) — the fraud library's
  requested diworsification signal.
- **W6-03 [H]** Stale-CWIP: capex that never capitalizes (CWIP high 3Y + fixed assets flat; the coverage
  map's own named untested forensic gap, cwip verified 49,274 rows) — convex penalty.
- W6-04 [M] Extend-and-pretend: 3Y cash interest coverage <1 + rising debt (CFO subset; cash-based
  resurrection of what the accrual distress composite got wrong; penalty-only).
- W6-05 [M] Effective-tax authenticity (tax authority's information set — the W5-02 counterparty-
  certification template, second counterparty).
- W6-06 [M] Pseudo-working-capital intensity drift (Δ other-assets/sales; stopgap proxy, retired when
  DATA-ASK #4 receivables split lands).
- W6-07 [M] ROIIC on incremental capital (two-sided read; kill-cheap corr vs killed reinvestment_runway
  / asset-growth / QMJ before any harness spend).
- W6-08 [M] Repurchase-when-cheap discipline (issuance-timing skill; kill-cheap corr vs bs_issuance >0.7).
- W6-09 [M-pilot] Concall prepared-vs-Q&A tone delta (139-firm MiMIC set; P0 speaker-attribution bugfix
  is a precondition; shape-graded pilot).
Buildable-now 6 · subset 1 · pilot 1 · thin-refinement 1 · data-blocked-as-tests 0.
Dispatch: W6-01/02/03 first; W6-05 next; W6-07/08 corr-prechecks cost ~nothing.
DATA-ASKS (ranked, in the json): (1) promoter pledge, (2) credit-rating action history, (3) auditor-
resignation events, (4) receivables/DSO/inventory split, (5) current/non-current borrowings,
(6) related-party/ICD schedules, (7) 264-name concall OCR, (8) segment revenue.

## TOP NEXT (launch when a slot frees, maintain 3-cap):
- SECTOR-RELATIVE COMPOSITE REBUILD (Principal EY directive + SECTOR_BIAS_AUDIT): ~41% of the composite edge
  is sector-TIMING, ~59% stock-selection; EY standalone LS ≈0 (sector tilt did the work); issuance most
  contaminated (40% retention), cfo-pat clean. Rebuild composite with legs ranked WITHIN-sector (priority:
  issuance, mom, MA65, QMJ, EY; leave cfo-pat). Re-measure true sector-neutral edge (expected IC ~0.113,
  ann-LS ~1.5) AND decide: neutralize the sector bet OR carve the 41% sector-timing into an explicit budgeted
  sector-rotation sleeve (don't hide it inside 'stock-selection'). Determinism + drop-one discipline.

## NEXT-2 (launch as slots free, maintain 3-cap):
- DOWNSIDE CAPTURE RATIO (Principal 2026-07-17): trailing 1/3/6m downside-capture = stock cumret during
  market-DOWN sub-periods / market cumret over those — ASYMMETRIC (down-only), distinct from BAB/low-vol.
  Test: does LOW downside-capture predict better fwd returns (defensive premium)? CONDITIONAL on regime
  (protects in bear/washout?) + payoff SKEW/crash-month mean (convex?). MANDATORY orthogonality check vs
  BAB + low-vol (kill if just repackaged). Data: cube_close_long + benchmark, market_state. low-t/drop-one,
  determinism. Ties to the de-risk/tail sleeve.

## ACTIVE / DONE — see WAVE4_PLAN.md + WAVE4_FINDINGS.md (living).
## Idea fuel: when <2 queued, run an Opus idea-gen tick against coverage_map gaps + new sources.
