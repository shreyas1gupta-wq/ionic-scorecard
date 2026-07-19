# ALPHA_RANKER — Oversight Roadmap (Fable high-level guidance log)

## 2026-07-17 08:46 IST — Fable oversight #1 (post-FINAL_MODEL freeze)

### VERDICT: ON-TRACK
Research is where the plan says it should be at this hour: FINAL_MODEL.md written, orthogonality-pruned
(~12 raw survivors → 7 independent legs), magnitudes honestly corrected (×12 annualization bug), regime
reframed as SIZING not blending after a proper root-cause decomposition (gross-return shortfall, not cost),
and the return-blend overlay PARKED instead of variant-churned — stop-conditions are being respected.
H009 Weinstein kill via 21yr sign-flip is exactly the discipline the plan asked for. 406 cards, no evidence
of senseless failure-combo loops. We are correctly in VALIDATE/CONVERGE mode. Do not re-broaden.

### NEXT 2H PRIORITIES (in order)
1. **Leave-one-leg-out incremental-value test on the 1Y composite** (the core converge task): for each of
   the ~7 legs, recompute composite IC_IR / monotonicity / net-LS without it, on BOTH panels. Any leg whose
   removal doesn't hurt = drop (simpler model wins). Also drop the 6 unscored CAPSTONE cards into
   scoreboard_v2 (406 cards vs ~399 scored rows).
2. **Regime-sizing spec finalized + one 21yr equity-curve validation**: pre-register the causal p_bear
   definition (breadth %>200DMA + India-VIX), the leg-weight flex rule (floor 0), run the SIZED composite
   net-of-cost through 2008/2011/2020 once. One run, not a parameter sweep.
3. **Sector-robustness child of the composite**: per-sector IC of the final 1Y composite (is the edge broad
   or one sector-bet in disguise?). Momentum already peer-relative (0.72→0.92); this is the composite-level
   confirmation. One card.
4. **Wave-3 rejected-sources pass — now due per plan, but BOUNDED**: resurrect only where a NEW method/data
   exists — event-time (daily) PEAD, FII/DII + promoter-buying drift (only if data is fresh; shareholding is
   stale-2023 → PARK if not), quality-in-bear gate. Cap ~6 hypotheses, 1 test + max 1 child each. Anything
   killed for lack-of-data stays PARKED with a note.
5. **Then pre-IC packaging**: MODEL_SPEC.md finalized weights/rules, sensitivity + lookahead-audit skill
   passes queued, IC-memo draft skeleton. Deep per-stock phase stays OFF until Principal returns.

### STOP (explicit)
- No more MA-length sweeps, overlay-blend variants, or forced-interaction composites (all resolved/killed).
- No new broad factor families; no social/sentiment; no 1M-horizon expansion (honestly unconfirmable).
- No per-stock deep-dives before model freeze sign-off (Principal order).

### RED FLAGS (watch)
- **Internal inconsistency to reconcile before IC**: SURVIVORS.md shows H003 momentum net_LS +17.3%/yr and
  H004 +11-19%/yr on the 5yr panel, while FINAL_MODEL §5 claims "low single-digit %/yr" spreads. Likely
  bull-sample vs 21yr difference — state the 21yr net numbers explicitly in FINAL_MODEL so the IC memo
  doesn't carry two stories.
- Net-issuance leg uses equity-capital %chg proxy (~8% bonus/split noise) — note as data-quality caveat in
  MODEL_SPEC; a true shares-outstanding source is a wave-3+ improvement, not a blocker.
- Delivery (2024) / shareholding (2023) staleness: any wave-3 resurrection leaning on these must be flagged
  low-confidence or parked.
- Budget: waves of 8-10 sustained fine; keep it — no 25-agent bursts.

## 2026-07-17 — Fable oversight #2 (post-CONVERGENCE): PARK confirmed; switch to custody-mode

### 1. CONVERGENCE VERDICT: REAL — confirmed, one bounded caveat.
The chain is sound: canonical build reconciled (min_legs=5; IC_IR 1.345 biased / 1.760 PIT), T5 survivorship
remediated and shown NOT to be the inflation source (ratio moved via lower ic_std, not a higher mean), PEAD
honestly closed at event-time, quality-gate revived as sizing-only, cleanup pass found only 3 stragglers (all
KILL). The binding blocker — 456 logged trials → DSR≈0 / PBO 0.92 on BOTH universes — is a multiplicity
problem no in-sample computation can deflate away; the sole remedy IS a fresh forward/held-out test. Backlog
genuinely exhausted. STOP-BROADENING directive is correct — do not re-open.
*Caveat (last legitimate in-sample task, ~15 min): `bs_asset_growth` was never independently lag-tested
(§5-RISKOFFICE gap). Close it once, log the card, stop.*

### 2. FORWARD-TEST TRACKER: BUILD NOW — do not wait for the Principal's design.
Calendar time is the scarce resource; banking predictions ≠ evaluating them, so recording scores spends NO
held-out data and leaves every design decision (horizon, success bar, universe) fully open to the Principal.
Requirements:
- FREEZE the spec (TRUE7, min_legs=5, exposure-scalar params) + pin the git hash in the tracker header (D-030).
- Record TODAY's full-universe scores → `rnd/forward_test/scores_YYYYMMDD.parquet` + manifest (hash, universe,
  date). Re-record each month-end (needs a data-refresh step — note it, don't over-engineer).
- **HARD RULE: the tracker NEVER grades.** No forward-IC computation, no peeking, no interim dashboards.
  Evaluate ONCE at the Principal-designed horizon; any interim grading burns the held-out set.
- Waits for Principal: horizon, pre-registered success criteria (set a realistic bar — IC decay 0.19→0.11 says
  expect ~0.11-class forward IC, not 1.76 IC_IR), universe choice, optional paper-portfolio companion.

### 3. WASTED-COMPUTE FLAG: YES — pause the hourly tick after the tracker exists.
Two session crons live (43ccb64b hourly research tick :17; 7e307056 Fable 2-hourly :43). With the backlog
exhausted, an hourly tick is pure token burn re-reading context to conclude "idle". Recommendation: ONE more
tick to (a) lag-test bs_asset_growth, (b) build the tracker + bank today's scores, then DELETE 43ccb64b.
Fable 2-hourly can also be deleted once the tracker is confirmed built — crons are session-only and the
Principal reopens in the morning regardless.

### 4. STANDING STATE (for the morning)
Model = PARKED, custody-mode. Awaiting Principal: forward-test design, calibration, IC memo (CIO+FM),
promoter-drift data refresh (resurrection candidate IC_IR 1.33, blocked on stale-2023 shareholding), deep
per-stock phase. No new red flags beyond the bs_asset_growth lag-test gap and the already-disclosed IC decay.
