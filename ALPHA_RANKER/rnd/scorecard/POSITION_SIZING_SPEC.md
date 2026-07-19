# CONVICTION-BASED POSITION-SIZE LADDER — buildable spec

**Owner:** Vikram Shah (Fund Manager — Derivatives & Short-Vol, E-002), cross-book methodology contribution.
**Date:** 2026-07-18. **Status:** ARCHITECTURE / DESIGN ONLY — no implementation code here, no new research, no
new data pulls. Same register as `EXIT_TRIGGER_SPEC.md` and `SCORECARD_BLUEPRINT.md` (same tags, same
determinism discipline, same "builder must not decide" convention).

**Scope note on priority (read before anything else):** `MASTER_ROADMAP_2036.md` §3 explicitly lists
"GAP-2 name-level conviction laddering" under **"Explicitly deferred — real, but do not fund this quarter"**,
ranked below the exit-trigger module. This document exists because it was directly commissioned tonight
alongside the exit-trigger work, not because the roadmap's prioritization changed — flagging the tension
honestly rather than silently overriding the CIO's stated sequencing. Recommendation: treat this as a spec
banked for when GAP-2 is actually funded, not a signal to build immediately ahead of Priority-1/2/3.

**Governs against / reuses (do NOT redesign these — reuse the tested pieces):**
- `ALPHA_RANKER/rnd/scorecard/rel_score_1M.parquet`, `rel_score_1Y.parquet`, `rel_score_5Y.parquet` (the
  RELATIVE scorecard, -100..+100, rank_pct construction)
- `ALPHA_RANKER/rnd/scorecard/absolute_scorecard.parquet` (`abs_score`, -100..+100)
- `ALPHA_RANKER/rnd/scorecard/calibration_tables.parquet` + `S8_CALIBRATION_REPORT.md` (score-bucket
  hit-rate / mean-log-realized-return tables, already built, 2026-07-18)
- `ALPHA_RANKER/rnd/scorecard/exit_trigger_flags.parquet` + `EXIT_TRIGGER_SPEC.md` (`composite_exit_flag`,
  already spec'd 2026-07-18, sibling document)
- `Shreyas_Ionic_AMC/07_RISK_OFFICE/RISK_LIMITS.md` (existing derivatives-book concentration precedent)
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/FUND_MANAGER_PLAYBOOKS.md` (GAP2 mandate, manager
  sizing survey) + `PMS_AIF_MF_SYNTHESIS.md` (Solidarity 3%→15% ladder, convergent-rules table)

**Does NOT touch:** the frozen 7-leg forward test, the RELATIVE/ABSOLUTE scoring paths, or any live capital
(D-025/paper-only, no exception).

**Tags:** **[DATA]** = on-disk verified. **[INFERENCE]** = mechanical construction from tested inputs.
**[OPINION]/[MY CALL]** = my judgment call, flagged, one-line-change-if-overruled.

---

## 0. THE FUND-MANAGER PREMISE THIS SPEC IS BUILT ON

Before any formula: **S8's calibration re-evaluation (2026-07-18) changes what this sizing ladder is allowed
to use as an input, relative to what the task brief lists.** [DATA, `S8_CALIBRATION_REPORT.md`]

| Score | S8 verdict | Usable for sizing? |
|---|---|---|
| `rel_score_1M` | **REAL** — clean monotonic hit-rate (0.475→0.543) AND magnitude (0.004→0.019 log-ret), every single year (20/20), the strongest calibration in the whole study | YES — primary-eligible |
| `rel_score_1Y` | Forward-test candidate — mostly monotonic (0.9 Spearman both dimensions), one dip at 30-50, thin-n/noisy at the top bucket (yearly std 0.274) | YES, with a noise caveat — usable but not over-trusted |
| `rel_score_5Y` | **Inverted-U, NOT calibrated** — top bucket (>75) is WORSE than the 30-50 bucket on both hit-rate (0.506 vs 0.554) and magnitude; same shape as the already-escalated growth-longevity anomaly | **NO — must not feed the sizing formula** |
| `abs_score` | 1M hard-gate KILLED (leakage); 1Y flat/inverted hit-rate; 5Y inverted-U, actively anti-calibrated at the top | **NO — off every PM's screen per S8's own fund-manager-lens verdict, at any horizon** |

**This is the load-bearing fact for this whole spec.** A sizing ladder that mechanically maps "higher score →
bigger position" across all four inputs would, for `rel_score_5Y` and `abs_score`, systematically **size up
exactly the names S8 found are not its best names** — the identical failure mode the exit-trigger spec's leg-4
honesty section warns against, applied to the sizing side instead of the exit side. **Any builder implementing
this spec must gate the formula to `rel_score_1Y` (primary) and `rel_score_1M` (secondary/timing), and must
NOT wire `rel_score_5Y` or `abs_score` into the weight calculation.** §4 gives the full reasoning and the
concrete combination rule.

---

## 1. THE CORE SIZING FUNCTION — recommendation: Kelly-INFORMED discrete step-ladder, not a continuous formula

### 1.1 The three options considered

1. **Linear** (`weight ∝ score`) — rejected. A linear map treats an 8pp hit-rate gradient (S8 1Y: 0.461 at
   the bottom to 0.541 at the top) as if it had the same statistical confidence as a 40pp gradient would.
   It also has no natural cap — a linear function needs an arbitrary clip anyway, so it buys no honesty
   over a step function while implying false precision.
2. **Continuous fractional-Kelly** (`f* = p − (1−p)/b`, then scaled by a fraction) — **the data does not
   support this as a live formula, and this is the central honesty point of this section.**
   - Kelly needs **p** (win probability) and **b** (payoff ratio = avg-win-size / avg-loss-size)
     **per bucket**. [DATA — verified directly] `calibration_tables.parquet`'s actual columns are
     `hit_rate` and `mean_log_realized_return` (**blended** across hits and misses) — there is **no
     win/loss-split magnitude column on disk today**. A literal Kelly fraction cannot be computed from
     what S8 built without one more aggregation pass (split `mean_log_realized_return` by `hit==True` vs
     `hit==False` per bucket, per horizon, per scorecard — a cheap re-run of `S8_calibration_eval.py`
     with one added groupby key, not new data). **This is a concrete, named gap for the builder, not an
     implementation detail to paper over.**
   - Even once that gap is filled, the inter-bucket hit-rate spread at 1Y (≈8pp) is **smaller than the
     within-bucket year-to-year noise** (21-27pp std, per S8 §1). Feeding a continuously-varying Kelly
     fraction off a gradient that is smaller than its own measurement noise is the sizing-side version of
     exactly the "fitting to noise" mistake this program's own Gate-4 sensitivity discipline exists to
     catch. A formula that outputs, say, 6.2% vs 7.8% for two names half a noisy hit-rate-point apart is
     false precision, not real differentiation.
   - **[FM HONESTY, per the task's explicit instruction]** Kelly is also famously aggressive on its own
     terms even with clean inputs — full-Kelly overshoots badly on any mis-estimated `p`/`b`, and ours are
     admittedly thin-sample (S8's own finding: DSR/PBO fail at small-n, and 1Y/5Y "years" overlap ~98% so
     the effective independent sample is far smaller than 20). **If any Kelly-derived number is used at
     all, it must be quarter-Kelly at most (25% of the raw full-Kelly stake), matching Pabrai's own stated
     practice** — never half-Kelly, and never full-Kelly, given this program's calibration is thinner than
     Pabrai's own qualitative company-by-company diligence.
3. **Step-ladder (bands), Kelly-INFORMED not Kelly-derived — RECOMMENDED.** Discrete conviction bands, with
   boundaries chosen so the ORDERING is Kelly-consistent (higher hit-rate-and-magnitude bucket → strictly
   higher weight band) without pretending the gradations within a band carry more precision than the data
   supports. This is also the mechanism every real manager in the survey actually uses — Solidarity's own
   stated rule (3%→5%→8%→10-15%) is a step ladder, not a continuous formula, and Pabrai's "quarter-Kelly in
   practice" is itself a discretionary band, not a computed decimal.

**Recommendation: (3), step-ladder, informed by the (gap-flagged) Kelly geometry, not derived from it
live.** Once the builder fills the win/loss-split gap named above, re-derive the band boundaries as a
one-time calibration exercise (a version bump, `sizing_weights_v1.json` → `_v2`, same determinism contract
as the exit-trigger weights) — but the *live* per-name sizing call stays a table lookup, never a per-name
Kelly computation at runtime.

### 1.2 The bands (keyed on `rel_score_1Y` — see §4 for why 1Y not 1M/5Y is the primary driver)

| `rel_score_1Y` band | Conviction label | Target weight band | S8 1Y hit-rate / mean-log-ret in this bucket |
|---|---|---|---|
| ≥ 75 | HIGH (confirmed) | 6-8% | 0.541 / 0.187 |
| 50-75 | MEDIUM-HIGH | 4-6% | 0.540 / 0.172 |
| 30-50 | MEDIUM | 2-3% | 0.522 / 0.159 |
| 0-30 | LOW / starter only | 0-1% | 0.535 / 0.161 |
| < 0 | NO NEW POSITION | 0% | 0.461 / 0.112 |

[MY CALL] Band edges intentionally reuse S8's own bucket edges (`<0/0-30/30-50/50-75/>75`) rather than
inventing new cut points — one less arbitrary decision, and it keeps the sizing bands and the calibration
evidence trivially cross-referenceable in any future audit. Weight numbers sit inside the Solidarity-cited
3-15% real-world range but are capped BELOW Solidarity's own top band (10-15%) and below Pabrai's ~10% cap
— see §2 for the concentration-cap reasoning (this program's calibration edge is real but thinner than a
discretionary manager's per-name diligence, so the ceiling should be set lower even where the score agrees).

### 1.3 The TEMPORAL ladder — this is the actual "laddering on confirming conviction" mechanism

A band is a **ceiling for that conviction level**, not a same-day jump target. The mandate specifically
asked for laddering, not just a lookup table — Solidarity's own rule confirms size *as the thesis confirms*,
over time, not on a single snapshot. Mechanically:

```
On a name's FIRST entry into a band (rel_score_1Y crosses into that band, coming from below):
  initial_weight = 40% of the band's target weight          # e.g. entering the 6-8% band → open at ~2.8%

On each subsequent monthly re-score (the existing scorecard refresh cadence):
  IF rel_score_1Y is STILL in the same band OR has moved to a higher band
     AND no exit-trigger flag >= ADVISORY is live (see §5 — hard precedence)
  THEN step weight up by one-third of the remaining gap to the CURRENT band's target ceiling
       (i.e., ~2 more monthly confirmations to reach full target weight — mirrors Solidarity's own
       multi-step 3%→5%→8%→10-15% cadence, not a single-jump allocation)

IF rel_score_1Y DROPS to a lower band (but is still >0, i.e. not yet an exit-trigger-driven cut):
  weight steps DOWN to that lower band's target ceiling over the SAME 2-3-month unwind cadence,
  not instantly — this is the score-driven de-size, distinct from and gentler than the exit-trigger-driven
  de-size in §5, which is immediate.
```

[MY CALL] "40% initial, thirds-of-remaining-gap thereafter, ~3 monthly confirmations to full size" is a
frozen prior in `sizing_weights_v1.json`, one-line change if the CIO/FM rules differently. The economic
logic: never bet full conviction on a single noisy monthly snapshot (S8's own warning about yearly std
exceeding the inter-bucket spread applies with equal force to a single month's score), while still reaching
full size inside one quarter if the score holds — consistent with Solidarity's real-world cadence.

---

## 2. CONCENTRATION CAPS

### 2.1 Hard per-name cap: **8%**, not Pabrai's 10% or Solidarity's 10-15%

**[OPINION, reasoned]** Pabrai's ~10% cap and Solidarity's 10-15% top band are backed by qualitative,
name-by-name diligence (moat, management, balance sheet read in depth) on a shortlist of 5-10 ideas. This
program's conviction signal is a scorecard with an 8pp hit-rate gradient at its most reliable usable horizon
(1Y relative) — real, but categorically thinner evidence per name than a discretionary manager's own
research file. A systematic process should therefore run its ceiling BELOW the discretionary greats' ceiling
even at its own top conviction band, because the ceiling is meant to bound how much capital a *single
score-driven judgment* can lose if that judgment is wrong, and this program's own S8 finding is a live
reminder that the model's own top bucket has been wrong before (5Y ABSOLUTE and 5Y RELATIVE both invert at
the top — the discipline of "don't fully trust your own top bucket" should be baked into the cap, not just
into which horizon is used).

### 2.2 Target active-name count: **15 (range 12-18)**

The survey ranges from Li Lu (~5) to Terry Smith (~30). [OPINION, reasoned] Neither extreme fits a
scorecard-driven process:
- **Too concentrated (5-10, Li Lu/Sleep/Pabrai-style)** presumes a depth of qualitative circle-of-competence
  conviction per name that a systematic score does not carry — those managers' concentration is safe
  *because* it sits inside deep individual research, per `FUND_MANAGER_PLAYBOOKS.md`'s own convergent
  finding ("concentration is only safe inside a narrow circle of competence"). A scorecard ranking hundreds
  of names monthly is the opposite of a narrow circle.
- **Too diffuse (25-30, Agrawal/Smith-style)** dilutes the (real but modest) 1Y-relative edge below the
  point where the sizing ladder means anything — at 30 names of ~3% average, the difference between a
  "HIGH" and "MEDIUM" conviction name washes out into portfolio noise, and running 30 independent monthly
  re-score/ladder decisions costs materially more token/analyst attention than the edge's own hit-rate
  gradient justifies.
- **15 names at the recommended bands** (2-8% per name) sums to a fully-invested book with headroom for
  cash/starter positions, is small enough that each name's conviction ladder is individually visible and
  auditable at the weekly WAR_ROOM cadence, and is large enough that no single name's exit-trigger firing
  is catastrophic to the book (a full EXIT_NOW at the 8% cap is a bounded, survivable event, consistent with
  the same "no single judgment sinks the book" logic as the 8% cap itself).

### 2.3 Cross-reference to `RISK_LIMITS.md`

**[DATA]** `Shreyas_Ionic_AMC/07_RISK_OFFICE/RISK_LIMITS.md` is APPROVED (D-021) but is written for the
**derivatives/short-vol book** (per-name notional ≤5% of book for short-vol, 1% max-risk-per-position rule
sized off premium/worst-case MTM, 20% sector cap, 40% aggregate margin ceiling). **It has no equivalent
section for a cash-equity conviction book today.** [MY CALL] This spec's 8%/15-name numbers should NOT be
read as already-approved risk limits — they are this document's recommendation, requiring the same
CEO+CIO joint approval path (D-025) as any other sizing standard before a builder wires them into paper
trading. Recommend Sanjay Kulkarni (fundamental book owner) and Ritika Sharma (risk) co-sign a new
`RISK_LIMITS.md` §Equity-Conviction-Book section mirroring this spec's numbers before build, rather than
silently treating this document as pre-approved.

---

## 3. SECTOR/FACTOR CONCENTRATION LIMITS

**Yes — a sector cap is required, layered ON TOP of, not instead of, the sizing ladder**, and it interacts
with the already-found ~41% sector-timing contamination in two distinct ways:

1. **Score-level fix (already partially done, per `USABLE_ALPHA_INVENTORY.md` §A5):** the reset's own
   finding is that blind sector-neutralization makes the composite monotonically WORSE (a real sector bet
   exists and neutralizing it destroys edge), but ~41% of the *historical* edge was sector-timing riding
   inside what looked like stock selection. The design directive (A5) is to blend sector-relative with
   absolute merit, not neutralize blindly. **This sizing ladder inherits whatever sector-adjustment the
   score itself carries** — it does not re-solve A5, it consumes its output. If the version of `rel_score_1Y`
   feeding this ladder has NOT yet had the A5 sector-relative blend applied, the sizing ladder will inherit
   the same sector-timing contamination the score has, at the position-weight level. **This is a
   precondition, not a detail: confirm which `rel_score_1Y` build (pre- or post-A5-blend) feeds this module
   before wiring it, and flag in `notes` if pre-blend.**
2. **Position-level cap (this document's own addition, independent of what the score does):** even a
   correctly sector-blended score can still cluster picks in one sector by chance (all-scorecard, no
   sector-diversification objective in the ranking itself) — a hard cap is the belt to the score's
   suspenders. **Recommend the SAME 20% sector cap already live in `RISK_LIMITS.md`** for the derivatives
   book, applied by analogy to this book (same Adani-group-counts-as-one-name convention) until a
   book-specific number is separately ruled on. Mechanically: **if a ladder step-up would push a sector's
   aggregate weight over 20%, the step-up is deferred (not silently skipped — logged as `sector_capped` in
   the ladder-state record) until either (a) another name in that sector is trimmed/exited, freeing
   headroom, or (b) the cap is reviewed.** The lowest-conviction name in the over-cap sector is the natural
   trim candidate if a higher-conviction name in the same sector needs the room — first-in-first-trimmed by
   conviction rank, not by entry date.

---

## 4. HORIZON INTERACTION — one position, not three books, but 5Y and abs_score are FENCED OUT

**The mandate's question: does a name that scores well on 1M but not 5Y (or vice versa) get a combined
score, or does this argue for genuinely separate books?**

**Answer: ONE position, sized by a horizon-gated combination rule — NOT a naive blend across all four
scores, and NOT fully separate books either.** [MY CALL, reasoned from S8's reliability findings]

### 4.1 Why not fully separate books
Three genuinely separate horizon-books (1M book, 1Y book, 5Y book) would multiply the position-count and
sector-cap bookkeeping by 3, and — more importantly — would require the firm to actually run and staff a 5Y
book off a score S8 just found is **inverted at its own top end**. Running a real book off an anti-calibrated
signal is worse than not combining horizons at all; "keep them separate" is only the honest answer if all
three are independently usable, and S8 shows they are not.

### 4.2 Why not a naive blend
A naive average or weighted-sum of `rel_score_1M/1Y/5Y` would let the inverted 5Y signal (top bucket WORSE
than mid-bucket) silently drag down the very names the 1Y/1M evidence supports, and vice versa — the same
"blending destroys the actionable information" argument `EXIT_TRIGGER_SPEC.md` §0 already made for keeping
the exit flag separate from the entry score applies here in a different form: blending a REAL signal with
an ANTI-CALIBRATED one does not average out to something usable, it contaminates the real one.

### 4.3 The concrete combination rule

```
sizing_score(name, t) = rel_score_1Y(name, t)                                    # PRIMARY driver, §1.2 bands

timing_adjustment(name, t) =
    +1 band-step-acceleration   if rel_score_1M(name, t) >= 75                   # REAL signal, use it to
                                                                                    # accelerate (not exceed)
                                                                                    # the temporal ladder —
                                                                                    # e.g. skip from 40% to
                                                                                    # 70% of target on entry
                                                                                    # month instead of waiting
                                                                                    # a full extra month
    no adjustment               otherwise (rel_score_1M in any other bucket)     # 1M's calibration does not
                                                                                    # support using it to size
                                                                                    # DOWN or override 1Y —
                                                                                    # only to accelerate an
                                                                                    # already-approved ladder

rel_score_5Y(name, t)  → DISPLAY ONLY, on the PM dashboard/IC pack, never in the formula. [§0 finding]
abs_score(name, t)     → DISPLAY ONLY, same reason, all horizons. [§0 finding]
```

**Reasoning for "1Y primary, 1M as timing-accelerant only, 5Y/abs display-only":**
- **1Y is the natural sizing horizon.** A position meant to be laddered up over a quarter (Solidarity's own
  cadence) should be sized off a score whose horizon roughly matches the holding decision — 1M is a
  short-horizon tactical tilt (the roadmap's own words: "edge is skip-15 momentum... IC decaying 2024"),
  not a conviction-for-a-multi-quarter-position read.
- **1M is nonetheless REAL (the cleanest calibration in the whole study)** — it would be a waste to ignore
  it entirely. Using it only to *accelerate an already-justified ladder step* (never to originate a position
  or override 1Y's band) captures its genuine signal without asking it to answer a question (multi-quarter
  conviction) its own horizon doesn't match.
- **5Y is fenced out of the formula entirely, and this is the single most fund-manager-honest call in this
  document.** A PM should still SEE the 5Y score (it may carry real information the inverted-U masks at
  the aggregate level, and Priority-3 of the roadmap is actively investigating whether de-weighting the
  growth-longevity leg recovers 5Y monotonicity) — but sizing capital on a score proven anti-calibrated at
  its own top end, before that investigation resolves, would repeat the exact mistake S8 exists to catch.
  **If/when `5Y_INVERTED_U_INVESTIGATION.md` (R8, pending per the roadmap) recovers monotonicity via a
  version bump, this section is the first thing to revisit** — 5Y re-entering the formula is a version bump
  of `sizing_weights_v1.json`, not a silent edit.

---

## 5. INTERACTION WITH THE EXIT-TRIGGER OVERLAY — the mirror-image de-sizing rule

**Yes — this is a natural, explicit link, and it is a hard precedence rule, not a suggestion.**

`EXIT_TRIGGER_SPEC.md`'s `composite_exit_flag` (`NONE`/`WATCH`/`ADVISORY`/`TRIM`/`EXIT_NOW`) is checked
**BEFORE** any ladder-up step executes, every re-score cycle:

```
composite_exit_flag == EXIT_NOW
    → position cut to 0% SAME DAY. Ladder state reset. No ladder-up considered until (if ever) the name
      re-enters as a fresh new position with a fresh initial_weight (§1.3), not a resumption.

composite_exit_flag == TRIM
    → position stepped DOWN immediately (same day, NOT the gradual 2-3-month unwind of §1.3's score-driven
      de-size) by one full band — e.g. a name at the 6-8% HIGH band drops immediately to the 4-6%
      MEDIUM-HIGH band's ceiling, or by a flat 30-40% cut of current weight if it is already below a full
      band's floor. [MY CALL, §6.1] This mirrors EXIT_TRIGGER_SPEC §4's own TRIM severity (Jain/Fisher
      leg firing alone = partial profit-take/cut-back, thesis under review, not full exit) — TRIM in the
      exit module and a de-size step here are the SAME event from two sides of one ledger entry.

composite_exit_flag == ADVISORY
    → NO immediate size change, but the ladder-UP mechanism (§1.3) is FROZEN this cycle — even if
      rel_score_1Y alone would justify a step-up, no new capital is added to a name carrying a live,
      uncorroborated technical caution flag. This is the correct-conviction-order application of
      EXIT_TRIGGER_SPEC's own leg-4 honesty section: an ADVISORY flag is "visible, not auto-actioned" on
      the EXIT side; the size-appropriate mirror is "visible, freezes further conviction-adding" on the
      SIZING side — not zero interaction, not full de-size either.

composite_exit_flag == WATCH
    → no size change, no freeze — visible only, same as the exit module's own treatment (Stage-A forensic
      tripwire pending human confirmation; sizing waits for Stage B like the exit module does).
```

**Why this ordering (exit-check precedes ladder-up, always) matters:** without this precedence, a name
could theoretically receive a ladder-up step and an exit-flag same cycle if the two overlays were computed
independently and merged carelessly — e.g., a name whose `rel_score_1Y` just crossed into a higher band
(ladder wants to add) while its valuation-ceiling leg just fired (exit module wants to trim). **The exit
overlay must win.** This is the same logic `EXIT_TRIGGER_SPEC.md` §0 used to justify keeping the exit flag
as a separate field rather than blended into the score — here it additionally has to be checked FIRST in
the position-management sequence, not just displayed alongside.

---

## 6. JUDGMENT CALLS (explicit — mine, all one-line changes in `sizing_weights_v1.json`)

1. **§1.2** Band edges reuse S8's own `<0/0-30/30-50/50-75/>75` cut points; target weight bands
   6-8/4-6/2-3/0-1/0%.
2. **§1.3** Temporal ladder: 40% of band target on first entry, thirds-of-remaining-gap per monthly
   confirmation (~3 months to full size); same cadence, reversed, on a score-driven step-down.
3. **§2.1** Hard per-name cap 8% (below Pabrai's ~10%, below Solidarity's 10-15% top band) — reasoned
   downward adjustment for thinner-than-discretionary per-name conviction evidence.
4. **§2.2** Target active-name count 15 (range 12-18).
5. **§3** Sector cap 20%, borrowed by analogy from the existing derivatives-book `RISK_LIMITS.md` figure,
   pending a book-specific ruling.
6. **§4.3** 1Y primary / 1M timing-accelerant-only / 5Y+abs display-only — the single most consequential
   call in this document, directly downstream of S8's calibration re-evaluation.
7. **§5** TRIM = immediate one-band step-down (same day); ADVISORY = freeze ladder-up only, no de-size;
   exit-check precedence is a hard rule, not a judgment call.

All seven are frozen, versioned, one-time economic-prior seeds — same determinism contract as
`SCORECARD_BLUEPRINT.md §4` / `EXIT_TRIGGER_SPEC.md §5` (byte-identical re-run once implemented, no
`.fit()` in the sizing path, a version bump is the only way any number changes and restarts any forward
clock per D-030).

---

## 7. WHAT THIS SPEC DOES NOT DO (the fence)

- **Does not implement anything.** No code, no `sizing_weights_v1.json` file written yet — that is the
  builder's next step, same handoff convention as `EXIT_TRIGGER_SPEC.md`.
- **Does not compute or claim a live Kelly fraction.** §1.1 names the exact data gap (win/loss-split
  magnitude per bucket, not currently in `calibration_tables.parquet`) that would be needed before any
  Kelly-derived number could be computed rather than assumed — flagged for Sameer Bhat / Arjun Rao as a
  cheap follow-on aggregation, not resolved here.
- **Does not touch live capital.** Paper-only, same as everything else in ALPHA_RANKER (D-025).
- **Does not treat its own numbers as approved risk limits.** §2.3 — this requires CEO+CIO joint sign-off
  (D-025) and a new `RISK_LIMITS.md` section before any builder wires it into the paper book.
- **Does not resolve the 5Y inverted-U.** That is `5Y_INVERTED_U_INVESTIGATION.md` / Priority-3 of
  `MASTER_ROADMAP_2036.md`'s own queue — this spec only fences 5Y out of the sizing formula until that
  work lands, and names the exact re-entry condition (§4.3) if it does.
- **Does not override the roadmap's own "do not fund this quarter" call on GAP-2** — see the scope note at
  the top. This is a banked spec, not a build order.

## Files referenced
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036.md` (read in full — GAP-2 mandate
  + deferral note + Priority queue)
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/FUND_MANAGER_PLAYBOOKS.md` (read relevant sections —
  Pabrai/Sleep/Li Lu/Solidarity sizing citations, GAP2 paragraph)
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/PMS_AIF_MF_SYNTHESIS.md` (grepped — Solidarity 3%→15%
  ladder, convergent-rules table row on position-size laddering)
- `ALPHA_RANKER/rnd/scorecard/S8_CALIBRATION_REPORT.md` (read in full — bucket calibration tables,
  reliability-ordering finding, fund-manager lens)
- `ALPHA_RANKER/rnd/scorecard/calibration_tables.parquet` (schema verified directly: `scorecard, horizon,
  bucket, bucket_rank, n, n_years, hit_rate, mean_log_realized_return, yearly_hitrate_std,
  frac_years_beats_below` — confirms no win/loss-split column, §1.1 gap)
- `ALPHA_RANKER/rnd/scorecard/EXIT_TRIGGER_SPEC.md` (read in full — overlay-not-blend precedent,
  `composite_exit_flag` severity levels, leg-4 honesty-caveat register this spec mirrors)
- `ALPHA_RANKER/rnd/scorecard/exit_weights_v1.json` (read — determinism-contract format template)
- `ALPHA_RANKER/rnd/scorecard/USABLE_ALPHA_INVENTORY.md` (read in full — §A5 sector-relative construction
  finding, ~41% sector-timing contamination, overlay-layer precedent for C1/C2)
- `Shreyas_Ionic_AMC/07_RISK_OFFICE/RISK_LIMITS.md` (read in full — existing derivatives-book concentration
  precedent: 5%/name short-vol, 20%/sector, D-021 approval status)
