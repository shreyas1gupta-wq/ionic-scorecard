# SELF-DECAY / DOCTRINE-FRAGILITY MONITOR — buildable spec

**Owner:** Dr. Sameer Bhat (Overfit & Sensitivity Analyst, Risk Office, E-027). **Date:** 2026-07-18.
**Status:** ARCHITECTURE / DESIGN ONLY — no implementation code here, no new research, no new data pulls.
Same register as `ALPHA_RANKER/rnd/scorecard/EXIT_TRIGGER_SPEC.md` and `POSITION_SIZING_SPEC.md` — same
tags, same determinism discipline, same "builder must not decide" convention. This document governs
ALPHA_RANKER's own composite scores; it does not touch market-regime gating logic, which already exists
and is out of scope here (see "Does NOT touch").

**Scope note on sequencing (read before anything else — honesty check requested by the brief):**
`FUND_MANAGER_PLAYBOOKS.md` GAP 3 names this exact need ("a self-decay tripwire on the scorecard itself
... flag as a design item, not a gap to build today"). I checked whether `MASTER_ROADMAP_2036.md` sequenced
or deferred GAP 3 the way it explicitly deferred GAP 2 (§3, "Explicitly deferred — do not fund this
quarter: ... GAP-2 name-level conviction laddering ..."). **It did not.** `MASTER_ROADMAP_2036.md` is
silent on GAP 3 by name — it appears nowhere in the Priority list, the deferred list, or the ledger,
except one incidental line (P1 row, §2) noting the 1M leg's "IC decaying 2024" as a known wart, without
connecting it to a monitor proposal. Per the task's own instruction ("if the roadmap is silent on it,
proceed"), I am proceeding — but flagging this honestly, the same way `POSITION_SIZING_SPEC.md` flagged
GAP-2's explicit deferral rather than silently building past the CIO's stated sequencing. **Difference
from the GAP-2 precedent:** GAP-2 was deferred on purpose (a CIO sequencing call); GAP-3 was simply not
re-litigated in the roadmap synthesis pass — an omission, not a ruling. This spec is commissioned directly
(tonight's task), same footing as `EXIT_TRIGGER_SPEC.md`/`POSITION_SIZING_SPEC.md` were. Recommendation:
bank this spec; let the CIO/Arjun decide funding priority against Priority 1-4 in the next roadmap pass.

**Governs against / reuses (do NOT redesign these — reuse the tested pieces):**
- `ALPHA_RANKER/rnd/scorecard/SCORECARD_BLUEPRINT.md` §4 (the frozen determinism contract — this monitor
  is built to respect it, not override it; see §3 below for the explicit tension resolution)
- `ALPHA_RANKER/rnd/scorecard/weights_v1.json` (the frozen weights file this monitor may recommend, but
  never itself write, a new version of)
- `ALPHA_RANKER/rnd/scorecard/S1_RELATIVE_1M_REPORT.md` (already-computed era-split IC, drop-one-leg,
  regime breakdown — the exact artifacts this monitor is built to read, not re-derive)
- `ALPHA_RANKER/rnd/wave4/REGIME_SPEC_V2.md` (the regime-conditional gates table — layers A/B/C/D/F — this
  monitor's core job is distinguishing decay FROM this table's already-licensed underperformance)
- `Shreyas_Ionic_AMC/01_COMMAND_CENTER/OPERATING_CALENDAR.md` (existing monthly "Edge-decay review (full)"
  cadence and its "2 consecutive fails → auto-demote" convention — this monitor is a companion check
  folded into that cadence, not a new calendar invention)
- `Shreyas_Ionic_AMC/06_TRADING_DESK/STRATEGY_REGISTER.md` (precedent language: S-05's "2 consecutive
  negative quarters", S-07's "3 consecutive quarters" insignificance triggers — this spec's persistence bar
  mirrors that existing house convention rather than inventing a new one)
- `rnd/lib/harness.py` (the one evaluation code path every leg already goes through — rolling-IC and
  era-split outputs this monitor consumes should come from the SAME harness, not a parallel implementation)

**Does NOT touch:** `REGIME_SPEC_V2.md`'s regime-classification logic itself (that is a separate, already-
certified module); the frozen 7-leg forward test (`rnd/forward_test/FROZEN_SPEC.md`); any live capital
(D-025/paper-only, no exception); and it never writes to `weights_v1.json` directly (§3).

**Tags:** **[DATA]** = on-disk verified from existing reports. **[INFERENCE]** = mechanical construction
from tested inputs. **[OPINION]/[MY CALL]** = my judgment call, flagged, one-line-change-if-overruled.

---

## 0. THE PROBLEM THIS SPEC ANSWERS (the Smith-2026 lesson, restated precisely)

Terry Smith ran "quality-at-any-price, buy-and-do-nothing" successfully for over a decade, then underperformed
**5 straight years (2021-2026)** before publicly capitulating in July 2026 (turnover 2-3%/yr → 51.8% in six
months). **The failure mode was not that the doctrine underperformed — quality legs SHOULD underperform in
some regimes by design. The failure was that there was no built-in tripwire forcing an EARLIER, ORDERLY
reassessment**, so the eventual change was abrupt and reactive instead of managed. [OPINION] The 5-year lag
is itself the indictment: a monitor with a 12-24 month runway would have surfaced the same signal roughly
3-4 years before the capitulation, giving Fundsmith time to adapt on its own terms rather than under public
pressure.

ALPHA_RANKER's regime-conditional gating (`REGIME_SPEC_V2` layers A-F) is a **partial structural answer** —
it is not one static doctrine; momentum is already suppressed in `BEAR_OVERSOLD`, gated off at both
valuation-band tails, replaced by `rev5d` in oversold-extremes, and the book de-grosses to gold/cash at
richness ≥160. **What is missing is a monitor for the composite's OWN drift relative to what the regime
gating itself predicts** — i.e., is a leg failing where the blueprint SAYS it should fail (no action needed,
the gate is working), or is it failing where the blueprint says it should be at full strength (a genuine
doctrine break, the Smith failure mode)?

---

## 1. WHAT "DECAY" LOOKS LIKE QUANTITATIVELY

Three complementary signals, all built from artifacts the S1-S4 scorecard reports already produce — no new
computation infrastructure, only a new reading of existing outputs plus one new joint cross-tab (§2).

### 1.1 Rolling IC/Sharpe vs the leg's OWN long-run distribution

```
rolling_IC(t) = mean(Spearman IC) over trailing 12-24mo window, ending at t     # via rnd/lib/harness.py, unchanged
baseline_dist = the leg's full-sample distribution of rolling_IC (all trailing windows to date)
WATCH   if rolling_IC(t) < 25th percentile of baseline_dist
ESCALATE-candidate if rolling_IC(t) < 10th percentile of baseline_dist
```
**Self-referential, not cross-leg.** A momentum leg's IC and a value leg's IC live on different absolute
scales; comparing a leg only to its OWN history avoids a common false-positive mode (penalizing a
structurally lower-IC-but-real leg for not matching a higher-IC leg's bar).

### 1.2 Era-split IC turning persistently negative in the MOST RECENT era specifically

Every scorecard leg (S1/S2/S3 reports) already computes an era-split table (`FINAL_MODEL`/`SCORECARD_BLUEPRINT`
convention: ~3yr buckets + single-year slices). The decay read is NOT "any era is weak" (some eras are
expected to be weak — see §2) but:
```
TREND   = the last 3 era buckets in the table are monotonically declining (each ≤ the prior)
FLOOR   = the most recent era bucket's IC < a pre-registered floor (e.g. IC < 0.03 for a 1M-horizon
          cross-sectional factor, roughly a third of the leg's own full-sample mean — set BEFORE looking
          at any specific leg's numbers, applied identically to every leg)
NEGATIVE = the most recent single-year slice is < 0 (sign flip, not just shrinkage)
```
Any TWO of {TREND, FLOOR, NEGATIVE} true together = a decay candidate worth the §2 test. This is
deliberately a soft OR-of-two bar, not a single-metric trigger — one weak signal alone (e.g. one noisy
negative year in an otherwise-flat series) should NOT trip anything; see the false-positive-fatigue warning
in §3.

### 1.3 A leg's correlation to an already-validated regime variable shifting SIGN

For any leg whose economic rationale is explicitly regime-conditional (e.g. momentum's relationship to the
rate-cycle-turn `R3` already flagged as real in `CYCLES_AND_REGIMES_METHODOLOGY.md`, or its relationship to
the richness band `REGIME_SPEC_V2` layer C/D), track:
```
sign(t) = sign( corr(leg_score, regime_variable) ) over a rolling window
```
A sign flip relative to the DESIGNED sign (e.g. momentum's IC should be flat-to-positive across trend
regimes per `REGIME_SPEC_V2` table A, negative only in `BEAR_OVERSOLD`) is a decay candidate. A sign flip
that matches an ALREADY-KNOWN regime dependency (e.g. momentum going negative specifically inside
`BEAR_OVERSOLD`) is NOT decay — it is the gate doing its job (§2).

**Companion diagnostic — drop-one-leg, not just composite-level IC.** A composite's headline IC can mask
one leg quietly dying while another compensates (exactly `S1`'s own finding: `earn_1M` is ~inert dilution,
not signal, despite carrying 40% nominal weight). Any decay check MUST run drop-one-leg (already a
harness-standard robustness cut, `SCORECARD_BLUEPRINT §2.4`) alongside the composite check, so a
compensating leg cannot hide a genuinely decaying one.

---

## 2. THE HARD PART — distinguishing REGIME-EXPECTED underperformance from REAL decay

This is the actual point of the spec, and where a lazy monitor would either (a) fire constantly on normal
regime-conditional noise (false-positive fatigue → ignored, the exact failure mode the brief warns about),
or (b) never fire at all because a genuinely-decaying leg's bad periods get explained away as "regime."

### 2.1 The core distinction, stated precisely

A leg's overall IC can fall for two structurally different reasons, and they require a decomposition to
tell apart — not a single-number check:

- **Mix effect (regime-expected, NOT decay):** the leg's conditional performance in each regime bucket is
  UNCHANGED, but recent history simply spent MORE time in a regime where the blueprint already says the leg
  should be weak/zero-weighted (e.g. more months in `BEAR_OVERSOLD`, or more months in the `OVERVALUED`
  band where momentum is designed to be gated to 0). The gate is working exactly as intended.
- **Within-regime effect (real decay):** the leg's conditional performance, evaluated ONLY inside the
  regime bucket where the blueprint says it should be at FULL or near-full weight (e.g. `NORMAL_CHOPPY` /
  `BOOMING_BULL` for momentum, `NEUTRAL` richness band for the momentum-weight gate), has itself degraded.
  This is the Smith failure mode — the doctrine breaking in the conditions it was designed to work in, not
  in the conditions it was always expected to struggle in.

### 2.2 The concrete statistical test — a shift-share decomposition + a within-regime bootstrap

**Step 1 — shift-share attribution** (standard performance-attribution identity, applied to IC instead of
return):
```
For each regime bucket r (the leg's own designed weight-buckets, e.g. r ∈ {BOOMING_BULL, NORMAL_CHOPPY,
BEAR_OVERSOLD} for momentum, or r ∈ {UNDERVALUED, NEUTRAL, OVERVALUED} for the valuation-band gate):

  w_r,baseline = fraction of dates in regime r, over the leg's full-sample baseline window
  w_r,recent   = fraction of dates in regime r, over the most recent era window
  IC_r,baseline = mean IC conditional on regime r, baseline window
  IC_r,recent   = mean IC conditional on regime r, recent window

  ΔIC_total   = IC_recent(unconditional) − IC_baseline(unconditional)
  Mix effect  = Σ_r (w_r,recent − w_r,baseline) · IC_r,baseline
  Within effect = Σ_r w_r,recent · (IC_r,recent − IC_r,baseline)
  (cross-term absorbed into within effect; standard two-term shift-share)
```
**Step 2 — attribute the verdict:**
```
IF |Mix effect| accounts for > 60% of ΔIC_total, AND the within-regime IC for the leg's OWN full/near-full-
   weight bucket(s) is NOT below its own historical distribution's 10th percentile (Step 3)
   → REGIME-EXPECTED. No tripwire. Log and move on.
ELSE (within effect dominates, OR the full-weight-bucket's conditional IC has itself degraded)
   → proceed to Step 3 to confirm statistically, not just point-estimate.
```
**Step 3 — bootstrap confirmation, conditioned ONLY on the leg's designed full-weight regime** (this is
the piece that makes "check for decay" a real test, not a vague instruction):
```
1. Isolate ONLY the dates falling in the leg's full/near-full-weight regime bucket(s) (e.g. NORMAL_CHOPPY +
   BOOMING_BULL for momentum, NEUTRAL band for the valuation-momentum gate) — across the ENTIRE sample.
2. Block-bootstrap these dates (block length ≈ one era, 200 draws minimum) to build the empirical null
   distribution of era-length-matched mean IC, CONDITIONAL ON THIS REGIME ONLY.
3. Compare the OBSERVED most-recent-era mean IC, computed on the SAME regime-restricted date set, against
   this conditional distribution.
4. REAL DECAY confirmed if the observed value falls below the 10th percentile of the regime-conditional
   bootstrap distribution, AND this holds for ≥2 consecutive independent sub-windows (not one blip) — the
   same "2 consecutive" persistence bar already used elsewhere in the firm (`STRATEGY_REGISTER` S-05/S-07
   demotion triggers, `OPERATING_CALENDAR`'s edge-decay auto-demote convention).
```
This is the one test that cannot be satisfied by "the market was in a bad regime for us" — the regime is
already held fixed at the leg's OWN best-case bucket before the test runs.

### 2.3 Worked example of the distinction (illustrative, not a live claim)

Momentum underperforming during `BEAR_OVERSOLD` or `OVERVALUED`-band months = expected, the gate already
suppresses/zero-weights it there — irrelevant to this test by construction (excluded from Step 1's r-bucket
comparison entirely on the "full-weight" side). Momentum underperforming specifically during
`NORMAL_CHOPPY`/`NEUTRAL`-band months — where the blueprint prescribes 12m skip-month momentum at or near
full weight — is the pattern that would fail Step 3 and constitute real decay.

---

## 3. TRIPWIRE THRESHOLDS AND ACTIONS — detection triggers a RULING, never a re-weight

### 3.1 The tension, stated and resolved explicitly

`SCORECARD_BLUEPRINT.md §4` is a hard, testable determinism contract: weights live in ONE versioned frozen
file (`weights_v1.json`), chosen ONCE (economic prior or one-time frozen fit), **no per-run refit, ever** —
"the scoring path contains zero `.fit()` calls." A decay monitor that silently re-weights a leg on a
tripped flag would violate this contract exactly as badly as a per-run refit would — it would just be
refitting on a monthly/quarterly cadence instead of every run, the same multiple-testing hole restated.

**Resolution: this monitor NEVER writes to any weights file.** Its only output is a flag + evidence
report. Any change to `weights_v1.json` requires a human/CIO-level ruling that produces a NEW versioned
file (`weights_v2.json`), exactly as `SCORECARD_BLUEPRINT §4` point 6 already specifies — "a version bump
is the ONLY way any number changes, and it restarts any forward clock (D-030 discipline)." The monitor's
role is strictly DETECTION; the weight change, if any, is a deliberate, disclosed, forward-clock-restarting
act by a person, never an automatic adjustment by the monitor itself.

### 3.2 Tier ladder

| Tier | Trigger | Action | Who decides |
|---|---|---|---|
| **WATCH** | §1.2's soft OR-of-two bar trips (TREND+FLOOR, or TREND+NEGATIVE, or FLOOR+NEGATIVE) OR rolling IC < 25th percentile (§1.1) | Log in the monthly companion report (§4). No escalation, no capital action. | Monitor (mechanical) |
| **ESCALATE** | §2.2 Step 3 bootstrap test confirms real decay (observed < 10th percentile, regime-conditional) for ≥2 consecutive independent sub-windows | Written escalation to CIO + Arjun Rao (Head of Quant) with the full shift-share + bootstrap evidence. Human ruling required: (a) accept as noise and re-baseline the monitor's own thresholds [rare, must be justified], (b) commission a NEW versioned weights file with the leg down-weighted (a specific, disclosed number — e.g. halve the leg's nominal weight, redistribute per the same economic-prior logic §4 of the blueprint used originally, NOT a re-fit), or (c) commission a full re-spec of the leg. **The monitor recommends; it does not act.** | CIO + Arjun Rao (joint, per D-025 register-adjacent discipline) |
| **REMOVE-PENDING-RESPEC** | Within-regime conditional IC (§2.2 Step 3) has flipped SIGN and stayed negative for ≥2 consecutive sub-windows in the leg's OWN designed full-weight regime (i.e. the leg is now anti-predictive exactly where it is supposed to work, not merely weaker) | Immediate CIO notification; leg flagged INACTIVE (weight forced to 0 in a new versioned file) pending a full re-spec from first principles — same discipline as a `STRATEGY_REGISTER` auto-demote, but requiring the version-bump mechanism rather than a silent in-place edit | CIO (can act unilaterally at this tier per existing risk-veto authority; Arjun co-signs the re-spec) |

**Explicit non-action:** WATCH never touches capital, weights, or the register. This is deliberate — most
WATCH trips will resolve as regime-expected once §2's decomposition runs, and firing loudly at the WATCH
tier is exactly the false-positive-fatigue risk that gets a monitor ignored. WATCH is a paper trail, not an
alarm.

---

## 4. MONITORING CADENCE — tied to existing firm infrastructure, not "periodically"

`OPERATING_CALENDAR.md` already runs a monthly **"Edge-decay review (full)"** (last working day, 09:00 IST,
owner Arjun/Ritika, `/edge-decay` → `STRATEGY_REGISTER`, "every STRATEGY_REGISTER row re-scored; 2
consecutive fails → auto-demote") and a lighter weekly quick-scan folded into the Friday risk pack ("only
if a sleeve is live"). ALPHA_RANKER's scorecards are not yet live `STRATEGY_REGISTER` rows (forward-test
candidates, per `SCORECARD_BLUEPRINT §0.2`), so the weekly quick-scan does not apply yet — but the monthly
cadence is the right anchor:

- **MONTHLY (folded into the existing month-end analytics run, `/edge-decay` companion):** the §1 light
  checks only — rolling-IC percentile read + era-table refresh + drop-one-leg refresh. Cheap, mechanical,
  reuses `rnd/lib/harness.py` outputs already produced for other purposes. Produces WATCH flags only.
  **Not weekly** — the underlying windows (12-24mo rolling, ~3yr era buckets) barely move week to week;
  a weekly cadence would be pure noise-amplification on the same data, the exact false-positive-fatigue
  risk the brief calls out.
- **QUARTERLY (aligned to the existing quarterly `/review-team` + `/probe-honesty` cadence):** the full
  §2.2 shift-share decomposition + regime-conditional bootstrap test, run on every leg carrying a WATCH flag
  from any of the prior three monthly scans. This is the tier that can produce ESCALATE. Quarterly is
  deliberately chosen over monthly for this heavier test: (a) it needs enough new out-of-sample dates
  accumulated since the last run for the bootstrap to say anything new, and (b) it matches the cadence at
  which the firm already re-examines strategy-level performance (`review-team`) and deliberately probes its
  own analysis for false positives/negatives (`probe-honesty`) — reusing an existing human-attention slot
  rather than creating a new one competing for the same CIO bandwidth.
- **Runway check:** a WATCH flag persisting monthly for 2 consecutive quarters without resolving at the
  quarterly deep-dive (i.e., the decomposition keeps landing ambiguous) is itself escalated for a CIO
  ruling on whether to fund a dedicated investigation — this is the 12-24 month runway the brief asks for:
  WATCH (month 1) → confirmed/ambiguous at Q1 deep-dive → still WATCH at month-end scans through Q2 → forced
  ruling by month ~18-24 at the latest, well before an abrupt Smith-style capitulation would be forced.

---

## 5. SELF-APPLICATION — does S1's 1M leg trip this monitor RIGHT NOW?

Applying §1-§2 to `S1_RELATIVE_1M_REPORT.md`'s ALREADY-DISCLOSED numbers (no new backtest run; reading the
existing report only). [DATA] unless marked otherwise.

**§1.2 light check — trips WATCH clearly, on disclosed numbers alone:**

| Era | IC mean |
|---|---|
| 2012-2015 | 0.091 |
| 2015-2018 | 0.090 |
| 2018-2021 | 0.086 |
| 2021-2024 | **0.048** |
| 2024-2026 | **0.015** |

Single-year slices: 2018=0.136, 2020=0.023, 2022=0.054, **2024=−0.014**.

- **TREND:** true — the last 3 era buckets (0.086 → 0.048 → 0.015) are monotonically declining.
- **FLOOR:** true — the most recent era bucket (0.015) is well under a generic 0.03 floor (roughly a third
  of the leg's own full-sample mean of ~0.072).
- **NEGATIVE:** true — the latest single-year slice (2024 = −0.014) is a sign flip, not just shrinkage.

All three of §1.2's signals fire together (the bar only requires two of three) — this is not a marginal
WATCH call. The `S1` report's own verdict independently confirms it is not a sampling artifact: "the
2024-2026 bucket's 22 dates run through Nov-2025 with essentially full name coverage... The recent-era IC
decay is real data, not a small-n artifact of the tail."

**Drop-one-leg reinforces that this is a leg-level (not composite-masking) finding:** dropping the momentum
component roughly halves composite IC (0.0716 → 0.035) and cuts LS Sharpe to a quarter (0.950 → 0.260) —
momentum IS what's decaying, not a leg whose decline is being hidden by others.

**§2 — does it clear the HARDER bar (real decay, not regime-expected)?** This is where honesty matters most.
`S1`'s own regime breakdown gives a FULL-SAMPLE (not era-conditional) split: IC is fairly stable across
trend regimes (bear 0.080, bull 0.073, sideways 0.066) and weak only in the high-vol state (0.029) — a
known momentum-crash pattern, not new. Momentum is suppressed by design only in `BEAR_OVERSOLD`
(`REGIME_SPEC_V2` table A); it is supposed to be at 12m full weight in `NORMAL_CHOPPY`/`BOOMING_BULL`. The
2021-2026 window that is decaying was NOT dominantly a `BEAR_OVERSOLD` stretch for Indian equities (mostly
bull/choppy with a 2022 vol episode) — so a mix-effect explanation (momentum decaying because more of
recent history fell in its already-gated-off regime) does not have an obvious basis. **[INFERENCE, one
step short of confirmed]** — this points toward real decay, not regime-expected weakness, but the exact
§2.2 joint cross-tab this spec calls for (era × regime, not era alone and regime alone as `S1` currently
reports them separately) has **not actually been run yet**. That joint computation is the precise next
action needed to move this from a strong WATCH-with-supporting-evidence to a formally CONFIRMED ESCALATE
under this monitor's own Step-3 bar.

**Verdict: YES, this is a live, actionable tripwire right now, at the WATCH-to-ESCALATE boundary, on the
firm's newest and best-verdicted (REAL, per `S1`'s own gate results) scorecard leg.** [MY CALL] I am not
waiting for the formal quarterly cadence to flag this — the evidence already on disk (3-era monotonic
decline, negative latest year, momentum-specific via drop-one-leg, and no obvious regime-mix alternative
explanation given the actual 2021-2026 regime mix) clears the bar for an immediate CIO/Arjun notification
recommending the §2.2 joint era×regime cross-tab be run as the very next piece of analysis on this leg —
not a routine wait-for-next-quarter item. This is exactly the kind of finding a monitor that only fired at
the ESCALATE tier after full confirmation would have delayed by a full quarter for no good reason; flagging
the strong-WATCH state immediately, with the explicit caveat that Step 3 is not yet run, is the more honest
and more useful action than either staying silent or overclaiming a confirmed verdict.

---

## 6. WHAT THE BUILDER MUST NOT DECIDE (locked by this spec)

- The three-signal decay definition (§1), the shift-share + bootstrap decomposition method and its 10th/25th
  percentile cutoffs and 2-consecutive-window persistence bar (§2.2), the tier ladder and its triggers (§3.2),
  the never-writes-weights rule (§3.1), and the monthly/quarterly cadence split (§4) are all FIXED here.
- The builder implements the rolling-IC/era/drop-one-leg computation (reusing `rnd/lib/harness.py`, no new
  evaluation code path) and the shift-share/bootstrap routine; it does not choose different percentile
  cutoffs, does not shorten the persistence bar, does not let the monitor write to any weights file under
  any circumstance, and does not skip the regime-conditional bootstrap in favor of a simpler unconditional
  check (that would silently collapse §2's entire distinction back into §1's naive read).

## 7. JUDGMENT CALLS (explicit — mine, not the Principal's or CIO's)

1. **§1.2 floor = 0.03, generic across legs, set before reading any leg's specific numbers.** Could be
   wrong for a structurally lower-IC leg (e.g. a 5Y valuation factor); if so, the fix is a per-leg
   pre-registered floor at spec-adoption time, not a post-hoc adjustment once a leg is already near it.
2. **§2.2 10th-percentile bootstrap cutoff + 2-consecutive-sub-window persistence bar** — chosen to mirror
   the firm's existing convention (`STRATEGY_REGISTER` S-05/S-07, `OPERATING_CALENDAR` edge-decay
   auto-demote) rather than an arbitrary new number, on the logic that a house-standard threshold already
   vetted for false-positive tolerance elsewhere is safer than inventing a fresh one for this monitor alone.
3. **§4 monthly/quarterly split** — deliberately NOT weekly, to avoid noise-amplification on windows that
   are inherently multi-year; if the CIO judges even monthly too frequent for a still-forward-test-only
   scorecard, folding the light check into the quarterly cadence only is a one-line change, at the cost of
   a slower runway (roughly halves the 12-24mo early-warning margin this spec targets).
4. **§5 verdict — flagging S1's 1M leg as a live WATCH-to-ESCALATE tripwire today, ahead of the formal
   quarterly cadence.** This is a judgment call to surface now rather than wait for the mechanical schedule
   in §4 to reach it; if overruled, the finding still stands on disk in `S1_RELATIVE_1M_REPORT.md` and will
   resurface at the first quarterly deep-dive regardless.

## 8. NON-GOALS (the fence)

NOT a re-weighting mechanism — detection only, every action gated behind a human/CIO ruling and a versioned
file (§3.1). NOT a replacement for `REGIME_SPEC_V2`'s regime classification — it consumes that table's
buckets as an input, it does not redefine them. NOT a new backtest or new data pull — every input is an
artifact the S1-S4 scorecard reports and `rnd/lib/harness.py` already produce. NOT applicable to the frozen
7-leg forward test (`FROZEN_SPEC.md`) or any live capital. Does not fire on regime-expected
underperformance by construction (§2) — a monitor that cannot make this distinction is not this spec.
