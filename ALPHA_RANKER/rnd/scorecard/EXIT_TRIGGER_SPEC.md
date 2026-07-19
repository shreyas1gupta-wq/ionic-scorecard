# EXIT / DECELERATION-TRIGGER MODULE — buildable spec

**Owner:** Sanjay Kulkarni (Fund Manager — Fundamental Quality & Value, E-017). **Date:** 2026-07-18.
**Status:** ARCHITECTURE / DESIGN ONLY — no implementation code here, no new research, no new data pulls.
This is the buildable spec a builder-agent implements mechanically, in the same register as
`SCORECARD_BLUEPRINT.md` (which this document is a direct sibling of — same tags, same determinism
discipline, same "builder must not decide" convention).

**Why this document exists (read this before anything else — the CIO brief):**
`FUND_MANAGER_PLAYBOOKS.md` (Arjun Rao, 2026-07-18) studied 10 great managers (6 Western + 4 Indian) and
found ONE convergent, highest-value gap: **ALPHA_RANKER's two scorecards (`SCORECARD_FINAL_SUMMARY.md`)
score ENTRY attractiveness only. Neither has an exit, deceleration, or valuation-ceiling trigger.** Three
independent bodies of evidence converge on this being the single highest-value codable addition, not a
nice-to-have:
1. **Prashant Jain** — the best-documented sell discipline in either batch: bought consumer staples at
   <20x PE in 2007, **started selling into strength at ~40x** — an explicit, admitted valuation-ceiling
   round-trip. 17.9% CAGR (1994-2022) vs Sensex 9.6%.
2. **Philip Fisher** — "3 and only 3 reasons to sell": (1) the original purchase was a mistake, (2) the
   company no longer passes the 15-point checklist (management/growth-runway deterioration), (3) a
   distinctly better opportunity exists. Explicitly NOT reasons to sell: the stock went up a lot, fear of
   a market decline, high P/E alone.
3. **The PMS real-money record** (`PMS_STUDY_20260712/SYNTHESIS.md` §3-4): **SageOne** (explicit,
   *ranked* exit hierarchy — deceleration/environment-deterioration first, valuation last and admitted to
   be the trigger Vartak most often gets wrong) delivered **25.1% CAGR over 13.8yr**, the single
   best-verified number in the whole 10-manager PMS study. **Marcellus CCP** — nearly the same entry
   screen (ROCE > cost of capital, growth ≥10%, 10yr track record) but **no disclosed mechanical
   deceleration or valuation exit rule** — has delivered **negative alpha since inception** (11.58% vs
   Nifty50 TRI 12.14%), a live, multi-year quality-trap. SYNTHESIS.md's own verdict: *"a mechanical
   deceleration/valuation exit trigger, not the initial screen, is what separated the outcomes."*

A PM who deploys a scoring system for real capital without an exit discipline is building exactly the
Marcellus failure mode into the book. This is not optional process hygiene — it is the one lesson three
independent lines of evidence (Western greats, Indian greats, domestic PMS track records) all point at,
and it is cheaply buildable from data ALPHA_RANKER already has tested. `PMS_STUDY_20260712/SYNTHESIS.md`
§4 codable-strategy-candidate #1 already spec'd the skeleton; this document completes it to
builder-ready precision and resolves the buy-vs-hold and overlay-vs-blend questions the skeleton left open.

**Governs against / reuses (do NOT redesign these — reuse the tested pieces):**
- `ALPHA_RANKER/rnd/panel/stock_valuation_pit.parquet` (PE, EY per name, PIT)
- `ALPHA_RANKER/rnd/panel/w5bv_stock_percentiles.parquet` (`expensive_pctile_PE`, already-built cross-sectional richness percentile — do not rebuild)
- `ALPHA_RANKER/rnd/scorecard/absolute_scorecard.parquet` (`PE_current`, `PE_fair`, `rerating`, `band` — already-built valuation-ceiling machinery, §3.1 of `SCORECARD_BLUEPRINT.md`)
- `ALPHA_RANKER/rnd/panel/sector_context.parquet` (`sec_earn_yoy`, `sec_val_pctile` — sector-level context, already built)
- `ALPHA_RANKER/rnd/wave4/_w6fg2_scored.parquet` (`earnings_confirm_v2`, `composite_v2_confirmed`, `available_date` — PIT growth-confirmation, already built)
- `ALPHA_RANKER/rnd/scorecard/rel_score_1Y.parquet` (`quality_score` column, already built from `quality_QMJ` + `quality_cfo_pat`)
- `ALPHA_RANKER/results/universe_forensic_score.parquet` + `universe_forensic_flags.parquet` (751-name scored, 14,269 flags, already built and live)
- `ALPHA_RANKER/rnd/forensic/FORENSIC_FRAMEWORK_CA.md` (32-item CA-grade taxonomy, 11 HARD-VETO items)

**Does NOT touch:** the frozen 7-leg forward test, the RELATIVE/ABSOLUTE scorecard scoring paths
(§0 below is the whole point of this section), or any live capital (D-025/paper-only, no exception).

**Tags:** **[DATA]** = on-disk verified. **[INFERENCE]** = mechanical construction from tested inputs.
**[OPINION]/[MY CALL]** = my judgment call, flagged, one-line-change-if-overruled.

---

## 0. THE CORE DESIGN DECISION — overlay, not blend

**Question the mandate posed:** does the exit trigger modify `rel_score`/`abs_score` directly, or ship as
a separate overlay flag alongside the score?

**Answer: SEPARATE OVERLAY. Never blended.** [MY CALL, firm decision, one-line if overruled]

Reasoning (the FM lens, not a stats argument):
- A real PM wants to see **"this was a buy at a 7.2/10 score, and it is now flashing a Jain valuation-
  ceiling exit"** as two distinct, separately-actionable pieces of information — not a single blended
  number where the exit signal silently drags the score down and becomes indistinguishable from "always
  was mediocre." Blending destroys exactly the information a PM needs to act (WAS this a good idea that
  has run its course, or was it never a good idea?).
- Fisher's own doctrine is explicit that "the stock went up a lot" is **not** a valid reason to sell —
  which means the exit signal cannot be a monotonic function of the entry score (a rising score would
  otherwise look identical to "getting richer," conflating the two). They must be orthogonal fields.
- S7/S4-absolute's own finding (cited in `FUND_MANAGER_PLAYBOOKS.md` GAP1) is that the current absolute
  model has **no drawdown control because it has no exit logic** — a blended score cannot fix this; only
  a distinct, actionable flag that a portfolio-construction layer can act on (trim/exit) can.
- Consistent with the existing C1/C2 overlay pattern already in `USABLE_ALPHA_INVENTORY.md` §(c): the
  analyst-context layer and the forensic layer already sit as GATES on top of raw scores, never blended
  into them. This module is architecturally the third member of that same overlay family, not a new
  pattern.

**Output artifact:** `ALPHA_RANKER/rnd/scorecard/exit_trigger_flags.parquet`, one row per (date, symbol)
for every currently-scored name, columns:

| Column | Type | Meaning |
|---|---|---|
| `date` | date | PIT date of the flag |
| `symbol` | str | ticker |
| `entry_thesis_type` | enum | `VALUE_GROWTH` \| `MOMENTUM` \| `UNKNOWN` — see §1.4 |
| `leg1_valuation_ceiling` | bool | Jain-style trigger fired (§1) |
| `leg2_fundamental_deterioration` | bool | Fisher-style trigger fired (§2) |
| `leg3_forensic_override` | bool | hard-veto fired (§3) |
| `leg3_pending_confirmation` | bool | quantitative tripwire fired, awaiting analyst filing-read confirmation (§3.2) |
| `leg4a_hard_stop` | bool | Minervini 7-8% hard stop fired (§3.5, FASTEST-REACTING, ADVISORY conviction) |
| `leg4b_climax_trim` | bool | sell-into-strength climax-run trim fired (§3.5, ADVISORY conviction) |
| `leg4c_stage_transition` | bool | confirmed Weinstein Stage 2→3/4 exit fired (§3.5, TRIM conviction alone / escalates with leg1 or leg2) |
| `composite_exit_flag` | enum | `NONE` \| `WATCH` \| `ADVISORY` \| `TRIM` \| `EXIT_NOW` — see §4 combination rule |
| `notes` | str | which sub-condition(s) fired, human-readable |

This artifact sits ALONGSIDE `rel_score_1Y.parquet` / `absolute_scorecard.parquet`, joined only at
display/portfolio-construction time (e.g., in a PM dashboard or the IC pack), never inside the scoring
formula itself. **The builder must not add any of these columns to the scorecard parquets.**

---

## 1. LEG 1 — VALUATION-CEILING EXIT (Jain-style)

**FM logic:** Jain didn't refuse to ever hold a 40x name — he watched HIS OWN holdings, bought cheap,
re-rate, and got out. The trigger needs an entry-anchored reference point (a round trip), not just a
static "PE is high" screen. This is precisely why it is a HOLDING-exit rule, distinct from a BUY screen
(resolved in §1.5).

### 1.1 Three already-built valuation signals, combined (no new data)

```
richness_vs_entry(t)   = PE_current(t) / PE_current(entry_date)          # stock_valuation_pit.PE
richness_cross_sec(t)  = expensive_pctile_PE(t)                          # w5bv_stock_percentiles.parquet, ALREADY BUILT
richness_vs_fair(t)    = PE_current(t) / PE_fair(t)                      # absolute_scorecard.parquet, ALREADY BUILT
                                                                          # (PE_fair already embeds sector-median PE +
                                                                          # regime tilt — SCORECARD_BLUEPRINT §3.1)
```

### 1.2 Own-N-year trailing percentile (mechanical derivation, no new data — one rolling quantile over the existing PE panel)

The mandate literally asks for "own N-year trailing percentile," which is distinct from the
already-built CROSS-SECTIONAL percentile above (that is "how rich vs. peers today," not "how rich vs.
its own history"). This is a trivial rolling computation over `stock_valuation_pit.PE`, not a new pull:

```
own_trailing_pctile(t) = percentile_rank( PE_current(t) ,  { PE_current(τ) : τ ∈ [t − 8yr, t] } )
                          # N = 8 years [MY CALL, §5.1] — inside the mandate's own PMS-study precedent
                          # (SYNTHESIS §4 candidate #1 cites "5-10yr distribution"); 8yr chosen as the
                          # midpoint, single frozen value, no per-run refit.
```

### 1.3 The fire condition — exact, joint, no vague language

```
FIRE leg1_valuation_ceiling(t, name)  if ALL of:
  (a) entry_thesis_type(name) == VALUE_GROWTH                              # §1.4 gate — leg does NOT apply to momentum entries
  (b) richness_vs_entry(t) >= 2.0                                          # Jain's literal round-trip: ~20x -> ~40x
        OR own_trailing_pctile(t) >= 0.90                                  # top decile of ITS OWN history
        OR richness_cross_sec(t) >= 0.90                                  # top decile vs the CURRENT cross-section
  (c) richness_vs_fair(t) >= 1.3                                           # AND priced meaningfully above the
                                                                            # sector-anchored fair PE (not just
                                                                            # "high in absolute terms" — high
                                                                            # relative to what this stock/sector
                                                                            # normally commands)
```
Thresholds (2.0, 0.90, 0.90, 1.3) are FROZEN priors in `exit_weights_v1.json` [MY CALL, §5.2] — economic
logic (a genuine 2x-or-top-decile-AND-above-sector-fair combination), not fitted. One-line change if
overruled; changing any of them is a version bump (`_v1`→`_v2`), same determinism contract as
`SCORECARD_BLUEPRINT.md §4`.

### 1.4 `entry_thesis_type` — how it is set, without inventing a new data pull

At BUY time (whichever process executes the entry — paper ledger / STRATEGY_REGISTER / a future live
book), tag the position using fields the entry decision ALREADY computed:

```
entry_thesis_type = VALUE_GROWTH   if  rerating_at_entry > 1.0     # absolute_scorecard.rerating at entry:
                                                                     # bought BELOW PE_fair, i.e. bought cheap
                                                                     # expecting re-rating UP (Jain's engine)
                   = MOMENTUM       if  rerating_at_entry <= 1.0    # bought AT/ABOVE fair value, momentum-
                                                                     # or growth-momentum-carried (high PE was
                                                                     # already expected/priced in — Maheshwari's
                                                                     # engine — leg 1 does NOT apply)
                   = UNKNOWN        if no `rerating` was computed at entry (pre-dates this module, or entry
                                     was sourced outside the two scorecards) — leg 1 does not fire (fail-safe
                                     to no-trigger, not a false trigger, on missing provenance) [MY CALL]
```
This requires ONE new field logged at buy time (`rerating_at_entry`, `PE_current` at entry, `entry_date`)
— a process requirement on whoever books the trade, not a new data source. `absolute_scorecard.parquet`
already computes `rerating` for every (date, symbol) in the universe; the entry process only needs to
persist the value on the day of entry.

### 1.5 BUY screen vs HOLD exit — the distinction the mandate asked to keep clear

- **NEW BUY screen:** does NOT reuse leg 1's round-trip logic (there is no entry yet to anchor a ratio
  to). A buy-side valuation discipline already exists and needs no new logic: the RELATIVE 1Y/5Y
  scorecard's `value_EY` rank and the ABSOLUTE scorecard's `rerating` field already tilt entries toward
  cheap names — a name at `richness_cross_sec ≥ 0.90` AND `richness_vs_fair ≥ 1.3` **today** (i.e., it
  would already fail today's own version of §1.3(b)+(c) with no entry reference needed) is simply a poor
  SCORE on the existing scorecards (low `value_EY` rank, `rerating < 1`) — it does not need a NEW buy-side
  gate; the existing scoring already discourages buying it. **Optionally**, a portfolio-construction rule
  can hard-exclude any name at that static richness level from the buy list regardless of its other-leg
  score — that is a one-line addition to portfolio construction, not a scorecard change, and is a static
  screen, not this module's round-trip logic.
- **HOLDING exit (this module, leg 1):** requires the entry-anchored ratio (§1.1's `richness_vs_entry`)
  — this is Jain's actual insight and cannot be replicated by a static buy screen, because it is
  specifically about a name that WAS cheap re-rating to rich, not about a name that was always rich.
  A PM's job here is different in kind from the buy decision: watch positions you already hold move
  from cheap to rich, and act on the round trip.

---

## 2. LEG 2 — FUNDAMENTAL-DETERIORATION EXIT (Fisher-style)

**FM logic:** Fisher's 2nd reason to sell ("company no longer passes the checklist") = growth runway
matured or management/quality deteriorated. Requires: (i) confirmed deceleration, (ii) a quality drop
from the name's OWN entry-time standing (not an absolute quality floor — a name can still be "good" in
absolute terms and still have deteriorated from what justified the original buy), and (iii) idiosyncratic,
not macro (a broad market/sector-wide growth slowdown is not a company-specific thesis break).

### 2.1 Growth-deceleration confirmation (reuses `_w6fg2_scored.parquet`, PIT via `available_date`)

```
growth_decel(t, name) =  earnings_confirm_v2(entry_date) == 1                 # confirmed acceleration AT ENTRY
                          AND earnings_confirm_v2(t) == 0                     # confirmation has REVERSED
                          AND composite_v2_confirmed(t) < composite_v2_confirmed(entry_date)
                                                                                # and the confirmed composite
                                                                                # itself has fallen, not just
                                                                                # the binary flag flipping on
                                                                                # noise
```
All fields already PIT-stamped via `available_date` in `_w6fg2_scored.parquet` — no lookahead risk beyond
what the base panel already guards against (T1-T10 taxonomy, `LOOKAHEAD_CONTROLS.md`, applies unchanged).

### 2.2 Quality drop from entry-time standing (reuses `quality_score`, already built)

```
quality_score(t, name)          # already a column in rel_score_1Y.parquet, built from quality_QMJ + quality_cfo_pat
entry_decile(name) = decile_rank( quality_score(entry_date, name) )   # w.r.t. the cross-section AT ENTRY
current_decile(t, name) = decile_rank( quality_score(t, name) )        # w.r.t. the cross-section TODAY

FIRE quality_drop(t, name)  if  current_decile(t, name) < entry_decile(name) - 1
                                 # at least a full decile (10 percentile points) worse than at entry
                                 # [MY CALL, §5.3: "-1 decile" not "-2" — Fisher's bar is deterioration
                                 # becoming visible, not becoming catastrophic; a 2-decile bar would let
                                 # too much genuine deterioration run before firing]
```

### 2.3 Idiosyncratic-not-macro filter (reuses `sector_context.parquet`, already built)

```
idiosyncratic(t, name) =  sec_earn_yoy(t, sector(name)) >= 0                  # the SECTOR's own earnings
                                                                                # growth is flat-or-positive
                                                                                # while the name itself
                                                                                # decelerated — i.e., this is
                                                                                # a company-specific break,
                                                                                # not the whole sector
                                                                                # slowing down together
```
If `sec_earn_yoy(t, sector) < 0` at the same time the name decelerates, the deterioration is presumptively
sector-wide/macro and leg 2 does NOT fire on that basis alone — it is a market/regime event, which is the
CIO's/macro desk's call (Cyrus Daruwalla / regime overlays), not a stock-specific thesis-break call.

### 2.4 The fire condition

```
FIRE leg2_fundamental_deterioration(t, name)  if  growth_decel(t,name) AND quality_drop(t,name) AND idiosyncratic(t,name)
```

Note: leg 2 does NOT gate on `entry_thesis_type` — Fisher's checklist applies to any held name regardless
of whether it was bought on a value or momentum thesis (a momentum name whose fundamentals deteriorate is
just as broken a thesis as a value name whose growth stalls).

---

## 3. LEG 3 — FORENSIC OVERRIDE (hard veto, reuse don't rebuild)

**FM logic (Sanjay's own charter, verbatim discipline):** "any single red flag is an automatic pass... a
governance flag gets you out same-day, no averaging down on a lie." This leg does not invent forensic
logic — it wires in what already exists and is already live.

### 3.1 Two existing layers, correctly distinguished (do not conflate them)

1. **`FORENSIC_FRAMEWORK_CA.md`'s 11-item HARD-VETO taxonomy** (RP-02, RP-03, PT-06, FA-01, FA-02, AG-01,
   AG-02, AG-07, AG-08a, AG-08b, CO-04) — this is a **reading framework**. Per that document's own
   `data_screenable` accounting, **26 of 32 total items are FILING-READ-ONLY** (require reading the actual
   Annual Report / CARO annexure / auditor's opinion text — no structured field exists in
   `MASTER_fundamentals_pit`). This layer CANNOT be auto-fired from data; it is analyst-desk (Ananya
   Iyer's team) / Sanjay's own reading work at deep-dive and at thesis review.
2. **The live quantitative scorer** — `ALPHA_RANKER/results/universe_forensic_score.parquet` (751 names,
   `forensic_risk_score_0_100` badness) + `universe_forensic_flags.parquet` (14,269 rows, per-flag
   `badness` 0-1, `data_status` ok/insufficient-data/not-applicable) — this IS automatable. It covers a
   DIFFERENT, narrower, DATA-SCREENABLE 19-flag set (accruals divergence, Sloan-accrual proxy,
   cash-conversion, other-income dependence, tax-rate anomaly, receivables/inventory-days trend, 6-item
   Beneish M-score family, interest-cover/debt-to-EBITDA/contingent-liability trend, promoter
   holding/pledge level-and-trend) — a real but PARTIAL proxy for the same underlying siphoning/distress
   concern, already built, already scored, already live.

**This module wires in BOTH, in the correct honest order — it does not pretend the quantitative scorer
IS the CA-grade hard-veto list.**

### 3.2 The two-stage trigger

```
STAGE A — automatic quantitative tripwire (fires from data alone, no new build):
  FIRE leg3_pending_confirmation(t, name)  if ANY of:
    forensic_risk_score_0_100(name) >= 70                          # frozen threshold [MY CALL, §5.4]
       OR  forensic_risk_score_0_100(name) − forensic_risk_score_0_100(name, entry_date) >= 20
                                                                     # NEW deterioration since entry, not
                                                                     # just a static high score the analyst
                                                                     # already underwrote at buy time
       OR  any flag in {beneish_M_score_composite, cfo_pat_divergence_multiyear,
                          sloan_accruals_asset_scaled_proxy, promoter_pledge_pct_and_trend}
             has data_status=='ok' AND badness >= 0.9               # a single severe, data-confirmed flag
                                                                     # in the four highest-conviction
                                                                     # categories (accruals/Beneish/pledge)

STAGE B — mandatory human confirmation (NOT automatic, per FORENSIC_FRAMEWORK_CA.md's own governing
principle: "no hard cutoffs are self-executing"):
  Stage A firing routes SAME-DAY to equity-head-ananya-iyer's analyst desk (or Sanjay directly) to confirm
  against the actual filing per the 11-item CA-grade taxonomy (auditor's report, CARO annexure, RPT note).
  ONLY on confirmation does leg3_forensic_override flip TRUE.
```

### 3.3 Cadence

Re-score currently-held names against `universe_forensic_score.parquet`/`universe_forensic_flags.parquet`
on Sanjay's existing weekly WAR_ROOM/thesis-review cadence (not continuously — the scorer is a periodic
snapshot job, `src/forensic/universe_forensic.py`, not a dated PIT panel column like legs 1/2). This is a
process/cadence note, not new code: run the existing scorer script against the held-names subset each week.

### 3.4 Severity

Once STAGE B confirms, `leg3_forensic_override = TRUE` is an **immediate, same-day EXIT_NOW** regardless
of leg 1 or leg 2 state — a cheap, growing, high-quality-scoring name with a confirmed hard-veto still
exits same-day. This leg OVERRIDES, it does not average or blend with, the other two.

---

## 3.5 LEG 4 — TECHNICAL STOP/TRIM (Minervini/Weinstein, fastest-reacting, lowest conviction)

**Added 2026-07-18, post-hoc, sourced from** `FUND_METHODOLOGY_2036/TECHNOFUNDA_PATTERNS.md` (Dhruv
Kapoor, R4) §6 candidate #3 — landed after legs 1-3 were built (timing race, not a real gap; confirmed
present and read in full before this addition). Reuses `cube_close_long.parquet` (price, 2005-2025) and
`cube_volume.parquet` (volume) — **no new data pull**, same "reuse don't rebuild" discipline as legs 1-3.

**FM logic:** Jain and Fisher both need something to happen in fundamentals/valuation first — a PE has to
re-rate, or a reported quarter has to show deceleration. Both can lag a real break by weeks-to-months
(TECHNOFUNDA_PATTERNS.md §6: "by the time growth 'visibly' decelerates in reported numbers, the stock may
already be down 30-40%"). The technical layer needs neither — it reads price/volume directly, which moves
first. **It is the fastest-reacting of the four legs, precisely because it is the least informed of the
four** (no valuation, no fundamentals, no filing-read) — hence the lower-conviction treatment in §4, not
equal weight with legs 1-3.

### 3.5.1 Three sub-triggers (all mechanical, price/volume-only)

```
leg4a_hard_stop(t, name) =  close(t) <= entry_price(name) × (1 − 0.075)                # 7-8% hard stop,
                                                                                          # 7.5% frozen midpoint
                                                                                          # [MY CALL, §5.6]; OR
                                                                                          # below the VCP pivot
                                                                                          # if entry was a
                                                                                          # breakout entry.
                              # Sizing tie-in (already-existing firm mechanism, not new): position size at
                              # entry must be set so stop-distance × shares <= 1.0% of book equity, per the
                              # deterministic risk ceiling already live in execution_scanner.py
                              # (RISK_LIMITS.md convention) — the stop is decided BEFORE entry, sizing
                              # follows from it, never the reverse (TECHNOFUNDA_PATTERNS.md §6a).

leg4b_climax_trim(t, name) =  ret(t−15trading_days, t) >= 0.25                          # >=25% move in
                                                                                          # <=~3 weeks
                               OR ( gap_open(t) >= 0.05  AND  volume(t) >= 1.5 × avg_volume_20d(t) )
                                                                                          # "blow-off" bar:
                                                                                          # >=5% gap on
                                                                                          # >=1.5x average
                                                                                          # volume, well
                                                                                          # above the base
                              # Action, if fired: scale out 20-30% of the position [MY CALL, §5.6: 25%
                              # frozen midpoint] — a partial trim, not a full exit; fires independent of
                              # any valuation ceiling (a pace-of-advance signal, not a PE signal).

leg4c_stage_transition(t, name) =  ma50(t) crosses below ma150(t)
                                    AND close(t) < ma50(t)  on above-average volume
                                    AND distribution_day_count(t, 20trading_days) >= 4
                              # "distribution day" = a down-day (close < prior close) on volume >= prior
                              # day's volume, count within a rolling 20-trading-day window; 4-5 within
                              # 3-4 weeks = the Minervini/O'Neil cluster tell. ma50/ma150 computed fresh
                              # from cube_close_long.parquet (mechanical rolling-mean derivation, no new
                              # data — analogous to the already-existing trend_ma65_slope leg's own
                              # construction).
                              # Action, if fired: FULL EXIT signal, independent of whether the fundamental
                              # thesis (legs 1/2) is intact or clean — TECHNOFUNDA_PATTERNS.md §6c is
                              # explicit that this is deliberate, not a bug: the technical layer doing its
                              # job faster than the fundamental layer can.
```

### 3.5.2 Why this leg carries LOWER conviction than legs 1-3, not equal weight — the honest caveat

Per `TECHNOFUNDA_PATTERNS.md`'s own mandatory self-red-team section, carried forward here verbatim
because it directly governs how leg 4 must be gated before it is trusted:

1. **Circuit-filter distortion in small/micro-caps.** A stock frozen at the upper/lower circuit for
   several sessions shows near-zero traded volume — indistinguishable, read naively, from a genuine
   tight-VCP/low-volume contraction or a clean "distribution day" count. It is a liquidity artifact, not
   a genuine signal (root `CLAUDE.md` §7b landmine). **Leg 4 MUST be gated on a liquidity/circuit-day
   filter (CONTRACTS>0-style, same discipline as the F&O bhavcopy landmine #9) before firing below the
   liquid large/mid-cap tier** — ungated, it will systematically misread circuit-frozen names as clean
   technical setups.
2. **Thin-ADV block-trade false volume surges.** In a name trading ₹5-10L ADV, a single institutional
   block can trip a ">1.5x average volume" filter without representing genuine broad-based
   participation — the pattern was developed on liquid US large-caps where volume surges reflect many
   independent participants. Leg 4b in particular needs a minimum-ADV floor (aligned to
   `COST_STANDARDS`'s untradeable-tier definition), not just a volume-ratio threshold.
3. **`cube_volume.parquet` has NO history before 2021-07-16** (confirmed data landmine, same file this
   program already flagged in `ALPHA_RANKER/rnd/wave4/TECHNICAL_PATTERNS.md`). Leg 4b and the
   volume-dependent half of leg 4c are therefore only evaluable 2021-2025 — any era-split or
   robustness check on this leg is structurally limited to that window, reported as a gap, not
   silently worked around.
4. **Momentum-crash exposure.** A raw breakout/volume-surge read is mechanistically a momentum bet, and
   `REGIME_SPEC_V2` already found momentum crashes at valuation extremes (richness <65 or ≥160) and in
   BEAR_OVERSOLD. Leg 4 must inherit the SAME regime/richness gating already certified for `mom_1M`
   before any of its sub-triggers are treated as an "act" verdict — a clean-looking Stage-2 breakout
   during a certified BEAR_OVERSOLD regime or at richness≥160 is downgraded to advisory-only regardless
   of the chart, per the same guardrail already wired into the RELATIVE 1M leg.
5. **No standalone technical entry/timing signal has cleared this program's own bar yet** — the sibling
   study `ALPHA_RANKER/rnd/wave4/TECHNICAL_PATTERNS.md` (Dhruv Kapoor, 2026-07-17, ENTRY-side confirmation
   overlays, a different question from this EXIT-side rule) returned an explicit negative verdict on all
   six patterns it tested. That result does not directly falsify leg 4 (different question — exit
   discipline, not entry confirmation — and Minervini's stop/trim rules were not among the six patterns
   tested there), but it is the honest reason leg 4 ships ADVISORY, not equal-weight with legs 1-3: this
   program has, so far, a stronger positive track record on fundamental/valuation signals than on
   mechanical technical ones.

**Net: leg 4 is the fastest-reacting leg and also the noisiest in this firm's actual (India small/microcap-
heavy) universe. It ships gated behind the liquidity/circuit filter above, and — per §4 below — its
sub-triggers (4a, 4b) raise an ADVISORY flag alone, not a TRIM/EXIT_NOW, until corroborated by a
fundamental leg or the ADV/regime gates are independently satisfied. Only 4c (full stage-transition) alone
reaches TRIM conviction, reflecting Weinstein stage-analysis being the more mature, higher-conviction half
of technical desk's toolkit (Dhruv Kapoor's own school) vs. the noisier stop/climax reads.**

---

## 4. COMBINATION RULE — how the four legs roll up to `composite_exit_flag`

```
composite_exit_flag =
    EXIT_NOW   if  leg3_forensic_override == TRUE                                      # hard veto, always wins
    EXIT_NOW   if  leg1_valuation_ceiling == TRUE  AND  leg2_fundamental_deterioration == TRUE
                                                                                          # Jain AND Fisher both
                                                                                          # firing = round-tripped
                                                                                          # AND the growth that
                                                                                          # justified paying up
                                                                                          # is gone — no reason
                                                                                          # left to hold
    EXIT_NOW   if  leg4c_stage_transition == TRUE  AND  ( leg1_valuation_ceiling == TRUE  OR  leg2_fundamental_deterioration == TRUE )
                                                                                          # technical stage-exit
                                                                                          # CORROBORATED by a
                                                                                          # fundamental signal —
                                                                                          # escalates past TRIM
    TRIM       if  leg1_valuation_ceiling == TRUE  (alone)                              # Jain-style partial
                                                                                          # profit-take, thesis
                                                                                          # intact, just rich
    TRIM       if  leg2_fundamental_deterioration == TRUE  (alone)                      # Fisher-style — cut
                                                                                          # back while confirming
                                                                                          # whether it is a
                                                                                          # blip or a real break
    TRIM       if  leg4c_stage_transition == TRUE  (alone)                              # full technical stage-
                                                                                          # exit fires ALONE —
                                                                                          # TRIM not EXIT_NOW,
                                                                                          # because uncorroborated
                                                                                          # it could still be a
                                                                                          # circuit/thin-vol
                                                                                          # artifact (§3.5.2) —
                                                                                          # lower conviction than
                                                                                          # legs 1-3's own TRIM
    ADVISORY   if  ( leg4a_hard_stop == TRUE  OR  leg4b_climax_trim == TRUE )  AND  no other leg fired
                                                                                          # fastest, noisiest
                                                                                          # sub-triggers alone —
                                                                                          # VISIBLE to the PM,
                                                                                          # NOT auto-actioned;
                                                                                          # exactly the OR-gate
                                                                                          # the mandate asked
                                                                                          # for (any leg firing
                                                                                          # raises a flag) but
                                                                                          # at lower conviction,
                                                                                          # not equal weight
    WATCH      if  leg3_pending_confirmation == TRUE  (Stage A only, Stage B pending)   # visible to the PM,
                                                                                          # not yet actioned
    NONE       otherwise
```
[MY CALL, §5.5] — TRIM (not immediate exit) for a single non-forensic fundamental leg firing alone reflects
Sanjay's own stated discipline: hold through noise, thesis-break or governance flags get you out; a single
valuation-ceiling OR single deterioration signal alone is a real but partial signal (not yet a confirmed
double-break), so it earns a size cut and heightened review, not an automatic full exit. Leg 4's ADVISORY/
TRIM split (§3.5.2) extends the same logic one notch further down: a mechanical, unconfirmed technical
read in a noisy universe earns visibility, not automatic action, until either corroborated by a fundamental
leg or independently cleared through the liquidity/regime gates. This is a frozen prior in
`exit_weights_v1.json`, one-line change if the CIO/FM rules differently at the IC that reviews this spec.

---

## 5. JUDGMENT CALLS (explicit — mine, not the CIO's/Principal's; all one-line changes in `exit_weights_v1.json`)

1. **§1.2** Own-trailing-percentile window = 8 years (inside the PMS-study's cited 5-10yr range).
2. **§1.3** Valuation-ceiling thresholds: round-trip ratio ≥2.0, own/cross-sectional percentile ≥0.90,
   richness-vs-fair ≥1.3 — economic-logic seeds, not fitted.
3. **§2.2** Quality-drop bar = at least 1 full decile below entry-time standing (not 2).
4. **§3.2** Forensic tripwire: absolute badness ≥70, OR +20-point deterioration since entry, OR a single
   badness≥0.9 confirmed flag in the four highest-conviction categories.
5. **§4** Combination rule: EXIT_NOW requires either the forensic hard veto alone, or BOTH leg1+leg2
   jointly, or leg4c corroborated by leg1/leg2; either leg1 or leg2 alone (or leg4c alone) is TRIM;
   leg4a/leg4b alone are ADVISORY only, not TRIM/EXIT_NOW.
6. **§3.5.1** Technical thresholds: hard stop 7.5% (inside Minervini's stated 7-8% band), climax-trim
   scale-out 25% (inside the stated 20-30% band), climax-run bar ≥25%/≤15 trading days, blow-off bar
   ≥5% gap on ≥1.5x 20-day average volume, distribution-day cluster ≥4 within 20 trading days — all
   inside the bands stated in `TECHNOFUNDA_PATTERNS.md §6`, frozen midpoints, not fitted.

All six are frozen, versioned, one-time economic-prior seeds — same determinism contract as
`SCORECARD_BLUEPRINT.md §4` (byte-identical re-run, no `.fit()` in the scoring path, a version bump is the
only way any number changes and it restarts any forward clock per D-030).

---

## 6. WHAT THIS MODULE DOES NOT DO (the fence)

- **Does not modify `rel_score_*` or `absolute_scorecard.E_return`/`p_up` in any way** — §0 is a hard
  constraint, not a suggestion.
- **Leg 4 (technical stop/trim, §3.5) ships at ADVISORY/lower conviction than legs 1-3, by design, not
  by oversight.** `FUND_METHODOLOGY_2036/TECHNOFUNDA_PATTERNS.md` did not exist at the time legs 1-3 were
  first drafted (2026-07-18, timing race with sibling agent R4, not a real research gap); it has since
  landed and leg 4 was added on the same day per the coordinator's instruction. Unlike legs 1-3, leg 4 is
  NOT corroborated by this program's own track record on technical signals — the sibling ENTRY-side study
  `ALPHA_RANKER/rnd/wave4/TECHNICAL_PATTERNS.md` (Dhruv Kapoor, 2026-07-17) returned a negative verdict on
  all six patterns it tested (a different question — entry confirmation, not exit discipline — so it does
  not directly falsify leg 4, but it is the honest reason leg 4 is gated and downweighted rather than
  trusted at par). Leg 4 is also structurally noisier in this firm's actual small/micro-cap-heavy universe
  (circuit-filter distortion, thin-ADV false volume surges, `cube_volume.parquet`'s 2021-07-16 data floor
  — §3.5.2). **It has not been backtested/cheap-tested by this spec** — that is Gate-3 work for whoever
  builds this module, same as legs 1-3.
- **Does not touch live capital.** Paper-only, same as everything else in ALPHA_RANKER (D-025).
- **Does not run once and freeze forever** — re-evaluated on the same quarterly/monthly cadence as the
  rest of the research program; any threshold change is a version bump per §5's determinism note.
- **No new data pulls, no new research.** Every input cited in §1-3 is an already-on-disk, already-tested
  file. The only NEW mechanical work is: (a) one rolling percentile over an existing PE column (§1.2),
  (b) persisting `rerating_at_entry`/`entry_date`/`PE_current`-at-entry at buy time (§1.4, a logging
  requirement on the entry process, not a data pull), (c) a decile-vs-entry lookup on an existing quality
  score (§2.2), (d) a re-run of the existing forensic scorer script against the held-names subset on a
  weekly cadence (§3.3).

## 7. EVALUATION HARNESS (for the builder, when this is implemented and tested)

Same discipline as `SCORECARD_BLUEPRINT.md §2.4/§3.4` — lag-test and placebo-shuffle are HARD GATES on the
exit signal too (an exit trigger that only "fires" with hindsight is exactly the kind of lookahead this
firm's T1-T10 taxonomy exists to catch). Era-split and drop-one-leg are robustness reporting, not gates.
Primary evaluation metric: **avoided-drawdown** on names that fired `EXIT_NOW`/`TRIM` vs a placebo
("held-through" / random-exit-timing) portfolio over the same names and window — directly answering
"would this trigger have avoided a Marcellus-style quality-trap stretch had it been running," the
motivating question from §0 of `FUND_MANAGER_PLAYBOOKS.md` GAP1. **Leg 4 additionally requires** the
liquidity/circuit-day gate and the `mom_1M` regime/richness gate (§3.5.2) to be applied and reported
BEFORE any ADVISORY/TRIM rate is quoted — an ungated leg-4 firing-rate on the small/microcap universe is
not a real evaluation, it is a circuit-artifact count.

## Files referenced
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/FUND_MANAGER_PLAYBOOKS.md` (read in full, GAP1 = the mandate)
- `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/SYNTHESIS.md` §3-4 (read in full, codable strategy #1 = the skeleton this completes)
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/TECHNOFUNDA_PATTERNS.md` (Dhruv Kapoor/R4, read in
  full §1/§6/fund-manager-honesty/actionable sections — source of leg 4, added post-hoc 2026-07-18)
- `ALPHA_RANKER/rnd/scorecard/SCORECARD_BLUEPRINT.md` (format/discipline template, read in full)
- `ALPHA_RANKER/rnd/scorecard/SCORECARD_FINAL_SUMMARY.md`, `USABLE_ALPHA_INVENTORY.md` (context, read relevant sections)
- `ALPHA_RANKER/rnd/forensic/FORENSIC_FRAMEWORK_CA.md` (read in full, 11 hard-veto items)
- `ALPHA_RANKER/rnd/wave4/TECHNICAL_PATTERNS.md` (checked — negative verdict on ENTRY-side patterns, a
  different question from leg 4's exit-discipline; cross-referenced for the volume-data-floor landmine)
- Schemas verified directly (row counts, columns) 2026-07-18: `stock_valuation_pit.parquet` (148,297 rows),
  `sector_context.parquet` (4,720 rows), `_w6fg2_scored.parquet` (143,907 rows), `capstone_legs.parquet`
  (1,310,958 rows), `rel_score_1Y.parquet` (32,973 rows), `absolute_scorecard.parquet` (298,245 rows),
  `universe_forensic_score.parquet` (751 rows), `universe_forensic_flags.parquet` (14,269 rows).
