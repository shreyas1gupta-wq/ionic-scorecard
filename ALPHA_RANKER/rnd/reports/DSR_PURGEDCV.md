# DSR/PBO PROPER FIX -- purgedcv (purged+embargoed CV) -- Gate 3
Owner: Dr. Sameer Bhat (E-027). Target: `rnd/cards/AUDIT_TRUE7_1Y.json` (7-leg composite) + its 7 legs. Replaces the saturated single-factor CSCV/PBO in `harness.compute_pbo_cscv()`/`compute_dsr()` (PREIC_AUDIT.md S3: every leg -- good or dead -- returned PBO 0.85-1.00, DSR~0, uninformative). Uses the pip-installed `purgedcv` package (Bailey/Borwein/Lopez de Prado/Zhu 2014 CSCV-PBO; Bailey & Lopez de Prado 2014 DSR), embargo = horizon length (365D) per instruction.

Common date grid: 90 monthly dates (2017-06-30..2024-11-29).

## 1. PBO -- true multi-configuration CSCV, purge+embargo=365D

Configurations = the 7 individual legs' LS-decile-spread return series + the composite (8 competing series over the same rebalance dates) -- this is the genuine 'if you had picked whichever ONE looked best in-sample, how often would that choice disappoint OOS' question the CSCV/PBO literature answers, unlike the harness's single-series adaptation which cannot ask a selection question at all (there was nothing to select among).

**n_splits sweep (n_obs=90 common monthly dates, purge_horizon=embargo=365D ~= 12 monthly periods):**

| n_splits | purged PBO | slope | n_combos used | max possible | empty-IS combos dropped |
|---|---|---|---|---|---|
| 12 | 0.857 | -0.326 | 56 | 924 | 868 |
| 8 | 0.500 | -0.069 | 10 | 70 | 60 |
| 6 | 0.250 | 0.013 | 8 | 20 | 12 |
| 4 | 0.000 | 0.029 | 2 | 6 | 4 |

**Real finding, not a footnote: NO split count leaves the full combinatorial set intact.** At n_splits=12 (the harness's own default block count), a 365-day purge+embargo destroys 868/924 combinations' in-sample set entirely. Coarsening the splits reduces but never eliminates the drop-out: even at n_splits=4 (the coarsest usable split), 4/6 combos are dropped and only 2 genuine combinations remain to estimate PBO from. The PBO read SWINGS from 0.857 (n_splits=12, 56 surviving combos) to 0.000 (n_splits=4, 2 surviving combos) purely as a function of split granularity -- with denominators this small (2, 8, 10, 56 combos) none of these four numbers is a trustworthy point estimate on its own. **This IS the honest Gate-3 finding**: with n_obs=90 common monthly observations, a 1-year forward-return horizon, and a 1-year embargo (embargo=horizon, per instruction), this composite's usable sample is too short to support a properly-purged CSCV/PBO at ANY split granularity that keeps both a meaningful combo count AND a fully non-degenerate in-sample set. The fix (purge+embargo machinery) is correctly applied; the DATA cannot feed it enough clean combinations to certify PBO either way. This is a materially different, more honest conclusion than the old harness's confident-looking (but uninformative) PBO~0.93.

- PBO (naive, NO purge/embargo, same 8 configs, n_splits=4) = 0.500, slope=0.300 -- shown for reference only; without purge/embargo this number is exactly the kind of overlap-contaminated estimate Gate 3 was called to replace, not a valid substitute for the swept figures above.

## 2. DSR -- proper formula, empirically-estimated var_sharpe

var_sharpe estimated empirically at **0.3646** from the spread of `signed_ic_ir` across 407 real logged program trials (scoreboard_v2.csv) -- an [INFERENCE] proxy (IC_IR is not literally the same statistic as the LS-return Sharpe DSR deflates), but a defensible replacement for the harness's disclosed sigma_sr=1.0 simplification, which PREIC_AUDIT.md already flagged as crushing every card (good or dead) toward DSR=0.

| n_trials assumption | DSR (var_sharpe=empirical 0.365) | DSR (var_sharpe=1.0, old assumption) |
|---|---|---|
| N=1 (this exact composite build, no correction) | 1 | 1 |
| N=1_family_AUDIT_TRUE7 (this family's own ledger) | 1 | 1 |
| N=90 (n_distinct research families that fed leg selection) | 3.446e-11 | 1.59e-45 |
| N=454 (global program trial count) | 1.573e-19 | 5.953e-74 |

sr_hat (composite, common-date grid) = 0.6577

## 3. Does the composite clear a PROPER purged-CV Gate-4 bar?

Gate thresholds (RESEARCH_SOP): DSR>0.95, PBO<25%.
- **PBO: NO PASS/FAIL CAN BE HONESTLY ISSUED.** The purged PBO ranges 0.000-0.857 across split granularities that each keep only 2-56 genuine surviving combinations (table above) -- it is not a stable enough estimate at n_obs=90 to clear or fail a <25% bar either way. Quoting any single cell from that sweep as 'the' purged PBO would be exactly the kind of number-shopping this gate exists to prevent.
- DSR at the family's own trial count (N=1) -> PASS -- but N=1 is not an honest trial count for a 7-leg composite selected out of a 90-family, 454-trial search.
- DSR at the global 454-trial count -> FAIL -- and at the more defensible N=90 (distinct research families) it also FAILs (DSR=0.000, see table). Even with the empirically-estimated var_sharpe replacing the harsh sigma_sr=1.0 assumption, ANY honest n_trials count above ~5-10 fails the DSR>0.95 bar for this composite.

**Verdict.** The purged multi-config PBO machinery is now correctly wired (purge_horizon/embargo genuinely remove IS/OOS boundary contamination when there is enough data to support it) -- but this composite's 90-observation common sample is too short, given a 1-year horizon and a matching 1-year embargo, to produce a STABLE purged-PBO estimate at any split count. This is itself the Gate-3 finding: informativeness was restored (the number now visibly MOVES with genuine methodology choices instead of pinning at ~1.0/~0 for everything), but the composite cannot be certified PBO-PASS via purged CV at this sample length -- it can only be certified NOT-YET-TESTABLE-RELIABLY, which is a materially more honest status than the old uninformative KILL. On DSR, the honest-trial-count question is resolved in the negative: at any plausible count above single digits, the composite does not clear DSR>0.95. The DSR side is STILL dominated by n_trials at any honest count above ~1-5: with an empirically-grounded var_sharpe instead of the old unit-variance assumption the deflation is less brutal, but this composite's DSR-eligible track record (n_obs=90, sr_hat=0.6577, restricted to the common 8-configuration date grid; the full 145-obs composite card's own sr_hat is 0.856, higher, on a longer but non-common window) cannot survive deflation at N=90-454 trials under ANY reasonable var_sharpe -- this is a genuine small-sample constraint of the data, not a broken metric anymore. Read the exact numbers above rather than a single pass/fail label; they are reported, not smoothed.