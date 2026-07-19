# MASTER ROADMAP 2036 — CIO synthesis of the 2026-07-18 methodology + scorecard-reset night

**Author:** Rajan Mehta (CIO, E-001). **Date:** 2026-07-18. **Role:** the "Fable/Opus in-between" synthesis-and-roadmap
seat the Principal asked for; Fable unavailable (org spend cap), so Opus per the Principal's explicit instruction.
**Status:** CIO judgment document — not research. It sits ON TOP of, and does not re-derive, the seven source docs.
It ranks, rules, and pushes back. Dissents/uncertainties are named. Tags: **[DATA]** traced to a source doc read in
full · **[INFERENCE]** my reasoning from those · **[OPINION]** my capital-facing judgment.

**Sources read in full tonight:** `ALPHA_RANKER/rnd/scorecard/SCORECARD_FINAL_SUMMARY.md` (S7),
`.../S8_CALIBRATION_REPORT.md` (S8); `FUND_MANAGER_PLAYBOOKS.md` (R1), `PMS_AIF_MF_SYNTHESIS.md` (R2),
`CYCLES_AND_REGIMES_METHODOLOGY.md` (R3), `TECHNOFUNDA_PATTERNS.md` (R4), `AI_FUTURE_EDGE_METHODOLOGY.md` (R5).
**Pending, folded in as placeholders:** `EXIT_TRIGGER_SPEC.md` (R7) and `5Y_INVERTED_U_INVESTIGATION.md` (R8) did
not exist on disk at write time — sections below mark exactly where each lands and what it must decide.

---

## 1. THE SINGLE THROUGHLINE — we built an entry engine inside a capital-protection firm and never built the exit

Everything tonight is the same finding wearing seven costumes. **ALPHA_RANKER scores, with real rigor, *what is
attractive to own*. It has no model of *what price is too high to pay* and no model of *when to stop owning it*.**
The firm's entire charter is capital-protection-first — and the sell side is where capital protection lives. We have
none of it in the scorecard. That is the throughline.

Watch it reappear across the night:

- **[DATA] The scorecard's own data reproduces the lesson.** S8's 5Y inverted-U: the model's *highest-conviction*
  bucket (>75) ties-or-loses to its *lowest* bucket (<0) on both hit-rate and magnitude, in BOTH scorecards; the best
  names sit at 30-50. That is not a bug in the abstract — it is the scorecard independently rediscovering
  **Jain-vs-Maheshwari**: paying up for the top-scored quality/growth ("quality at any price") ties-or-loses to
  quality at a reasonable price. The 5Y top bucket is the pay-any-price bucket, and it underperforms.
- **[DATA] The absolute book losing to a coin-flip on Calmar (S7 escalation #3) is the same gap, one level down.**
  Worse max-drawdown than a random draw at *every* horizon (−54% to −59% vs −35% to −46%). R4 names the mechanism
  exactly: the model "has no drawdown control because it has no exit logic." No sell rule → no capital protection →
  loses to random on the one metric a long-only PM should trust most.
- **[DATA] `earnings_confirm_v2` is the entry-side symptom.** R4 read the build script (`w6fg2_build.py`): the flag
  fires on a *multi-year, backward-looking* fundamental confirmation — it "fires on stale, already-priced-in good
  news." It is a confirmation that arrives *late*, carries ~zero incremental IC, and has no timing content. A signal
  with no sense of *when* is the entry-side face of a system with no sense of *when to exit*.
- **[DATA] The methodology research triangulates the gap from three independent directions.** R1: of 10 legendary
  managers, only 3 (Jain valuation-ceiling round-trip, Pabrai 3-year rule, Fisher 3-reasons) have an *operational*
  sell rule; the failures (Marcellus quality-trap, Porinju's un-de-risked −25% year) cluster on the no-sell-rule end.
  R2: the *real-money* split — SageOne HAS a deceleration/valuation exit (25.1% CAGR/13.8yr, best-verified number in
  the study) vs Marcellus which does NOT (negative alpha, textbook quality-trap). R4 adds a third, mechanical exit
  candidate (Minervini stage-exit). **Western greats, Indian greats, and the domestic PMS record independently point
  at the same missing piece.**
- **[DATA] R5 supplies the temperament half.** Its Priority-1 edge — patient owner-capital + behavioral discipline —
  is *precisely the precondition for a sell rule to pay*. R5's own line: "discipline without the structural freedom
  to act on it is just well-documented paralysis." Patience is the sell discipline you can afford to hold; the exit
  trigger is patience made operational.
- **[INFERENCE] R3 supplies the macro reason the gap is biting *now*.** The post-2022 rate-regime turn mechanically
  punishes paying a premium multiple for long-duration cash flows. That is the macro explanation for *why the 5Y
  top-bucket (highest growth-longevity, presumably highest-multiple names) underperforms*. The inverted-U is not only
  a construction artifact candidate — it may be the discount-rate regime doing exactly what R3 says it does.

**[OPINION] Name it plainly for the firm: the round-trip gap.** ALPHA_RANKER is half a strategy — the buy half. Seven
independent workstreams tonight, using different data and different traditions, all landed on the sell half being
absent. When the scorecard's own parquet, twenty managers, a real-money PMS track record, and the rate cycle all
indict the same missing piece, that is not a coincidence to note in passing. **It is the firm's single most important
research finding of the quarter, and it is more important than any of its individual authors framed it.**

---

## 2. THE LEDGER — PROVEN / PROVISIONAL / REJECTED

### PROVEN — treat as settled; stop re-litigating

| # | Finding | Evidence | So what |
|---|---|---|---|
| P1 | **1M RELATIVE ranker is REAL and usable** (low-conviction) | S7 hard gates clean (lag 0.199 / placebo −0.002); S8 calibration perfectly monotonic 1.0/1.0 on hit-rate AND magnitude, every one of 20 years — the strongest calibration in the study, via a completely different lens | The *one* usable output of the whole reset. Ship as a momentum/quality *tilt*, forward-test clock, sized only by the Principal. Know its warts: edge is skip-15 momentum, earnings leg inert, IC decaying 2024. |
| P2 | **The round-trip / exit gap is the highest-value buildable piece** | Triangulated: R1 (managers), R2 (SageOne vs Marcellus real money), R4 (mechanical candidate) + the scorecard's own Calmar failure | Priority #1 build (§3). Settle that it beats a third entry horizon. |
| P3 | **`earnings_confirm_v2` is mislabeled** — a multi-year fundamental confirm flag, NOT an earnings-surprise/price-reaction signal | R4 read `w6fg2_build.py` directly | Epistemic-conduct defect in a *frozen* artifact. Fix the docs now (§3b). |
| P4 | **The entire ABSOLUTE scorecard is NOT usable at any horizon** | 1M structurally broken + leakage-killed (S7/S8 both hold the KILL); 1Y/5Y lose to random on Calmar and are flat-to-anti-calibrated on hit-rate (S8) | Off every PM screen until reworked. No exceptions — it *looks* respectable (23-28% CAGR) and is the more dangerous for it. |
| P5 | **Reliability ordering is 1M > 1Y > 5Y**, not the hoped 5Y > 1Y > 1M | S8 §2 | The reversal's *cause* is understood enough to settle: overlapping-window sample shrinkage (5Y monthly obs overlap ~98% → ~1.5 independent draws). It is NOT evidence long-horizon investing is unreliable. |
| P6 | **Demographic dividend = highest-confidence usable prior; rate-regime-turn = most actionable process rule** | R3 §4, §2 | Both are near-arithmetic / high-confidence-on-fact. Encode as slow priors (§3d), never as timing signals. |

### PROVISIONAL — live open questions; do not build load-bearing structure on these yet

- **V1 — The 5Y inverted-U's *cause* (R8 pending).** Real "quality-at-reasonable-price beats quality-at-any-price"
  economic effect, vs growth-longevity-leg construction artifact, vs pure overlapping-window n. **[OPINION] My lean:
  it is *both*, and the fix direction is the same regardless.** The evidence already stacked before R8 lands: drop-one
  IMPROVES 5Y IC in *both* scorecards when the growth-longevity leg is removed (S3 escalation #2); S8 shows the
  inverted-U in both; the manager literature (Jain/Maheshwari) predicts it; R3's rate mechanism predicts it. Four
  arrows at the same leg. R8's job is to *quantify* whether de-weighting recovers monotonicity, not to discover the
  suspect — the suspect is already named.
- **V2 — 1Y and 5Y RELATIVE rankers.** Usable-with-disclosed-caveats *forward-test candidates* (hard gates clean,
  logic sane; FRAGILE only on thin independent-n — a power problem, not a no-effect finding, per the firm's low-t
  re-screen rule). On the forward clock; adjudicate on live behavior; never claim 2008/2011-bear behavior.
- **V3 — R4's narrow volume-accumulation filter on the confirm flag, and the "tape-leads-fundamentals" (RS→fundamental
  lead-lag) test.** Both well-posed, non-prior-art-violating cheap-tests that could go either way. Genuine, but they
  rank *below* the exit module — do not let them jump the queue.

### REJECTED — explicitly off the table; cite this when they resurface

- **R-a — Kondratiev / tech long-wave, great-power hegemonic cycle, dollar 15-20yr cycle, debt-supercycle
  *periodicity*** as capital-allocation inputs. Fail R3's honesty gate on independent-episode count / dating consensus.
  (Their underlying *indicators* — debt/GDP, DXY level, capex/sales — survive as ordinary live regime data, stripped
  of the "cycle" wrapper.)
- **R-b — "beat a random/cap-weighted placebo on Calmar/Sharpe" as THE certification gate.** The Principal's S8
  correction reprioritized the real test to *consistency / accuracy / monotonicity via score-bucket calibration*.
  Placebo-beating stays a hard *hygiene* gate (a model that loses to a coin-flip is dead); it is no longer the pass
  criterion. [OPINION — this is a genuine improvement: a model can beat a placebo by taking more risk, exactly the
  absolute book's failure mode.]
- **R-c — the multi-agent AI research process as the firm's *moat*.** R5 self-red-teamed this using our own WS-4
  finding (single Opus 16/16 vs pipeline 14-15/16 at ~4.5× cost) and rejected it outright. Keep the infra as
  falsification hygiene, not as edge (§4, §5).
- **R-d — rebuilding PEAD / "buyable gap-up."** Already a certified kill on our universe (R4: REGIME_SPEC_V2 layer G,
  IC ≈ −0.003). Any proposal that is "PEAD in a Minervini costume" is rejected on prior art, not re-tested.
- **R-e — the "125K AIF industry data" provenance.** R2 verified `raw/AIF_Final.xlsx` is a *private single-strategy
  trend-rotation backtest* ("Navigator Passive", operator unidentified, hand-set 0.5% cost, no lookahead audit), NOT
  industry-census data. Reject any downstream claim that leans on it as "industry data." Log the correction.

---

## 3. PRIORITIZED NEXT 90 DAYS

Ranked by (conviction × evidence) ÷ cost. I am deliberately *narrowing* the queue — the failure mode after a big
research night is to fan the budget across ten follow-ups. Do these four, in this order.

### PRIORITY 1 — Build the EXIT-TRIGGER module (the round-trip). *Highest conviction, cheapest, most evidence-backed.*
- **[OPINION] CIO ruling on scope:** the next scorecard research item is an **EXIT scorecard, not a third entry
  horizon.** This is settled by §1/§2-P2.
- **Composition — compose as an OR-gate (exit fires on whichever trips first), four candidate legs:**
  1. **Jain valuation-ceiling** — name's own valuation crosses cheap-relative → rich-relative (uses `stock_valuation_pit`
     PE + the richness band).
  2. **Fisher fundamental-deterioration** — confirmed growth decelerates below the entry threshold / quality checklist
     breaks (uses `_w6fg2_scored` / `capstone_legs`).
  3. **Forensic hard-veto** — the existing C2 forensic layer trips (already built; wire it as an exit, not only an
     entry gate).
  4. **[from R4] Minervini mechanical stage/stop** — 7-8% hard stop below entry, sell-into-strength trim on a
     climax-run, full exit on a confirmed Stage 2→3/4 transition. **This is the *fast* layer** (price/volume move
     before multiples or reported fundamentals); Jain/Fisher are the slower fundamental confirmations.
- **Why it wins:** no new data (PIT fundamentals + PE + richness + OHLCV all on disk); directly fixes the P4 Calmar/
  drawdown failure (a mechanical stage-exit starts de-risking *before* max-DD realizes); and it is the operational
  form of the firm's patient-capital identity (§4).
- **Dependency / R7:** `EXIT_TRIGGER_SPEC.md` (R7) is the buildable 3-leg spec (Jain + Fisher + forensic). **When it
  lands, fold R4's mechanical leg in as leg 4 and rule on whether it is a scorecard column or a portfolio-overlay
  rule.** My prior: the fundamental legs (1-3) are scorecard-native; the mechanical leg (4) is a *portfolio overlay*,
  because a stop is a position-management action, not a cross-sectional score. R7 must also carry a lookahead audit
  (D-028) before any quoted result — an exit rule is trivially easy to leak future prices into.
- **Owner:** Arjun Rao (build) + Dhruv Kapoor (mechanical leg) + Sameer Bhat (Gate-4 / lookahead) + Nikhil Bose (red
  team before any gate pass). Cheap-test first (pre-registered kill), not a full build.

### PRIORITY 2 — Fix the `earnings_confirm_v2` naming in the scorecard docs. *Cheapest, do it this week.*
- **[DATA/P3]** A mislabeled signal in a *frozen v1 artifact* that downstream consumers will misread as an
  earnings-surprise leg. This is an EPISTEMIC_CONDUCT issue (D-035), not a research task. Correct S7's "earnings leg"
  and the blueprint §2.1 "earnings-surprise" language to "multi-year fundamental confirmation flag." One-day mechanical
  fix (Arjun/Kavya). Highest value-per-token item on the list. Do not let it wait behind Priority 1.

### PRIORITY 3 — Resolve the 5Y inverted-U and rule on 5Y construction. *(R8 pending.)*
- **[DATA/V1]** This is also scorecard escalation #2 (the growth-longevity drop-one anomaly), which needs a CIO/
  Principal ruling regardless. When `5Y_INVERTED_U_INVESTIGATION.md` (R8) lands, it must answer one question: **does
  de-weighting or removing the 2.0× growth-longevity overweight recover 5Y monotonicity?** If yes (my prior), the
  blueprint's mandated overweight is wrong and 5Y needs a version bump. **[OPINION] CIO ruling in advance:** the
  blueprint-locked leg does NOT get a free pass on doctrine — four independent arrows (drop-one, S8 both scorecards,
  manager literature, rate mechanism) point at it. R8 quantifies the fix; it does not get to conclude "leave it,
  it's mandated." Cheap-test the de-weight; if it recovers monotonicity, escalate a v2 to the Principal.

### PRIORITY 4 — Two near-zero-cost process wins from the cycles research (R3).
- **(a) Rate-cycle-turn reassessment rule.** Institutionalize R3's process rule #2 as a firm cadence: an **annual**
  (not monthly) explicit review of duration/leverage tolerance and the quality-vs-value / pay-up-for-growth tilt,
  triggered when rate direction reasserts for 2+ consecutive years. **[INFERENCE] This dovetails with Priority 3:**
  the rate turn is the *macro* reason the 5Y pay-any-price bucket underperforms; the review rule and the inverted-U
  fix are the same phenomenon at two horizons. Near-zero maintenance cost.
- **(b) Demographic-dividend floor-raiser.** Encode R3's process rule #3 — long-horizon (5Y+) India growth priors
  start from a structurally elevated working-age base rate, with the job-absorption caveat travelling *with it every
  time*. This is the prior that should feed the 5Y valuation-vs-growth leg (the same leg under investigation in
  Priority 3), not a scorer feature.
- **Governance hygiene rider:** log the R-e provenance correction (AIF_Final.xlsx ≠ industry data) to the DATA_CATALOG
  and OPEN_ISSUES so no future pass cites it as a census. Trivial, prevents a future fabrication.

**Explicitly deferred (real, but do not fund this quarter):** V3 (volume-accumulation filter, RS-leads-fundamentals),
GAP-2 name-level conviction laddering, the Navigator-rotation-vs-B4 reconciliation. All genuine; all below the exit
module. Say no now so Priority 1 actually ships.

---

## 4. TEN-YEAR POSITIONING — allocation of attention, not a hedge

R5's strategic sentence is correct and I adopt it: *be the patient, disciplined, on-ground-honest specialist in the
corner of the Indian market too small, too frictional, and too opaque for commodity-AI capital to reach — and use the
AI-research infrastructure purely as the cheap, ruthless falsification engine that keeps that specialist honest.*

**[OPINION] The uncomfortable CIO call first:** the firm's *revealed* behavior over the last quarter has been to pour
most of its effort into quant-scorecard-building (ALPHA_RANKER, STOCK_SCORECARD_750, tonight). The honest return on
that program tonight is **one usable, low-conviction 1M momentum tilt.** That is a thin harvest from a large program.
I am willing to say it plainly: **quant-scorecard-building is table-stakes tooling, not the firm's edge — and it has
been over-weighted relative to its yield.** R5 is right to rank it Priority 3.

**Where I push back on R5:** it slightly over-separates "scorecard-building" from "forensic/small-cap depth." The
forensic layer (C2: 751 names, 14,269 flags) *lives inside* ALPHA_RANKER. The scorecard is the **chassis** that
operationalizes the forensic/microcap edge and keeps it honest at scale. So the framing is not "scorecard OR
specialist depth" — it is: the specialist knowledge is the **engine**, the scorecard is the **chassis**, patient
capital is the **fuel and the temperament**. Build the chassis only as far as it carries the engine; stop gold-plating
it as if it were the car.

**My allocation of firm attention/resources over the 10-year horizon (a real split, not a hedge):**

| Weight | Pillar | Why this number |
|---|---|---|
| **~45%** | **Patient owner-capital + behavioral discipline + the D-032 long-horizon investment line — operationalized by the exit-trigger module.** | R5's Priority 1; the only §3 candidate that passes the "can a funded AI competitor buy it in 5 years?" test cleanly (answer: no). Tonight's #1 build IS this pillar made concrete — patience without a sell rule is paralysis. The 10-year edge and the 90-day priority are the *same thing*. |
| **~35%** | **Small/micro-cap India + India-friction knowledge + forensic/CA-grade fraud detection, as ONE fused specialist edge.** | The firm's most *proven* and *currently-owned* edge (the CLAUDE.md landmine list and the CA-forensic framework ARE this edge written down). But a *depreciating* asset (T+1, tighter circuits, XBRL filings shrink the friction surface) — harvest now, renew continuously. Longest half-life sub-edge: **promoter-*intent* forensic judgment**, which pattern-matching genuinely cannot do. |
| **~15%** | **Multi-agent research infra as cost-honest falsification hygiene — NOT the moat.** | R5 §4 self-red-team + WS-4. Optimize it for ruthless *disproof* (the value is in the kill, not the discovery — §1.2 of R5), not for scale of hypothesis generation (more hypotheses faster = more mirages faster). Its moat-grade residue is the epistemic *culture*, which belongs to the 45% discipline pillar, not the software. |
| **~5%** | **Slow macro priors (demographic floor, rate-regime review).** | Near-zero maintenance, annual cadence, high-confidence-on-fact. Sets base rates; never times. |

**Identity in 2036:** *the patient, forensic, small/mid-cap India specialist that runs a cheap AI falsification engine
to stay honest* — explicitly NOT "the quant scorecard shop." The scorecard is how we keep that specialist honest and
scalable; it is not who we are. **[OPINION] I am deliberately assigning quant-scorecard-building a *lower* resource
claim (~15%, inside the infra pillar) than its recent share of effort. That is the intended correction.**

---

## 5. WHAT TONIGHT TELLS US ABOUT RUNNING THE MULTI-AGENT PROCESS ITSELF

The discomfort is real and I will not wave it away: WS-4 found a single Opus call (16/16) *beat* the multi-agent
pipeline (14-15/16) at ~4.5× the cost on defect detection. Tonight's session ran ~9+ agents over several hours to
produce these seven docs. Was that worth it? **Honest answer: partially — and the parts that were worth it teach the
decision rule.**

**Where tonight's fan-out earned its cost:**
- The exit-gap triangulation (§1/P2) is *more credible because three independent agents, reading three different
  corpora (Western greats, Indian greats, real-money PMS), converged on it independently.* A single call asserting
  "managers value sell discipline" is a claim; three disjoint sources converging is *evidence*. The convergence WAS
  the deliverable.
- The `earnings_confirm_v2` bug (P3) required a domain expert (Dhruv) to actually *read the build script*. A
  generalist synthesis pass would have inherited the mislabel, not caught it.
- S8 added a genuinely new lens (score-bucket calibration) that surfaced the inverted-U where S3's IC/decile framing
  had only hinted at it.

**Where tonight's fan-out was lower-value than it looked:**
- R3 (cycles) largely re-confirmed a prior scan (`LONG_CYCLES.md`, 2026-07-17) and mostly produced SKIP verdicts —
  valuable as a firewall against narrative, but a single well-prompted call would likely have reproduced ~85% of it.
- R2's quant-landscape web pass surfaced exactly one usable name (Alpha Alternatives). Thin.
- R5 is excellent *judgment*, but judgment is precisely what a single strong model does well — a well-prompted single
  Opus call might have reached most of it.

**[OPINION] The decision rule for the firm — when to fan out vs when one well-prompted call suffices:**

> **Fan out to multiple agents ONLY when at least one of these three holds:**
> 1. **Independent convergence is the deliverable** — you want N genuinely-different domains/methods to test the *same*
>    claim, and the value is in whether they agree (tonight's exit gap). If you would trust one call's answer on its
>    own, you do not need N.
> 2. **Genuinely separable domains over disjoint source material** — each agent reads a *different* corpus (scorecard
>    parquets vs manager literature vs macro data vs build scripts). Fan-out is parallelism over disjoint inputs, not
>    N views of one input.
> 3. **A domain expert must actually read something specific** a generalist would skip (Dhruv on `w6fg2_build.py`).
>
> **Otherwise: one well-prompted call, cheapest capable model (D-036).** And structurally: **cheap Sonnet/mechanical
> agents for gathering + falsification; ONE Opus call for the synthesis/judgment on top** (this document). That is the
> right shape — expensive judgment is spent once, on the high-ambiguity capital-facing layer, never on the gathering.

Applied to tonight: the fan-out was justified for the scorecard re-read, the manager/PMS/technical triangulation, and
the build-script bug hunt (rules 1-3 all fired). It was *over-provisioned* for the cycles re-confirm and the light web
passes — those could have been one call each. Net: tonight was worth it, but a disciplined application of the rule
above would have run it at perhaps 60-70% of the agent-hours for the same conclusions.

**One-sentence verdict:** Fan out only for independent-convergence evidence, disjoint-corpus breadth, or
expert-must-read-this depth — for everything else one well-prompted cheap call beats the pipeline, and the expensive
model is reserved for the single synthesis-and-judgment layer on top of cheap parallel gathering, never for the
gathering itself.

---

## CIO verdict block (memo format)

**VERDICT: APPROVE the roadmap; the round-trip/exit gap is the firm's #1 research priority.**

- **Rationale (3 lines):** (1) Seven independent workstreams converged on one missing half — the sell side — which is
  where a capital-protection-first firm's edge must live. (2) The one usable scorecard output (1M relative) is a thin
  harvest that confirms quant-scorecard-building is tooling, not moat. (3) The durable identity is patient + forensic
  + small-cap specialist, with the exit module as the operational bridge between the 90-day work and the 10-year edge.
- **Tail-risk assessment:** the live tail is the ABSOLUTE book — it looks respectable (23-28% CAGR) and loses to a
  coin-flip on drawdown at every horizon (worst month/DD −54% to −59%). Correlated-blowup scenario: a PM sizes off the
  absolute score in a rate-punished, high-multiple 5Y top bucket = maximum drawdown into exactly the names the
  inverted-U says are worst. **Kept off every screen until reworked — this is the tail this reset existed to prevent.**
- **Sizing ruling:** only the 1M RELATIVE ranker may be touched, low-conviction tilt, forward-clock, sized by the
  Principal alone. Everything else is research/forward-test. Zero capital on the absolute book.
- **Kill criteria + review date:** exit-module cheap-test carries a pre-registered kill threshold + lookahead audit
  before any gate pass; 1M relative demoted if live IC stays negative 2 consecutive quarters. **Review: 2026-10-18**
  (90 days), or on R7/R8 landing — whichever first.
- **Dissents recorded:** none at write time (single-author synthesis). R8, when it lands, has standing to dissent from
  my §3-P3 prior that the growth-longevity leg is the culprit — its quantification governs, not my prior.

**Pending fold-ins:** R7 (`EXIT_TRIGGER_SPEC.md`) → Priority 1 leg composition + overlay-vs-column ruling. R8
(`5Y_INVERTED_U_INVESTIGATION.md`) → Priority 3 construction ruling. Update this file in place when each lands.
