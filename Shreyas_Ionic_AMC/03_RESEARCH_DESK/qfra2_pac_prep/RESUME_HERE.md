# QFRA-2 PAC deck — RESUME CHECKPOINT
**Saved 2026-08-04, 17:xx IST · DESK-20 · branch `claude/sweet-austin-283067` (worktree sweet-austin-283067)**
**Principal said: "soft save and we will continue next session."**

READ THIS FILE FIRST next session, then `QFRA2_SKILL_RECONCILIATION_2026-08-04.md` in
`03_RESEARCH_DESK/`. Everything below is banked to disk. Nothing is committed to git yet.

---

## THE DELIVERABLE STILL TO BUILD (this is the next step)

An upgraded **QFRA 2.0 Product Approval Committee deck**, rebuilt in the firm's `pr_template` house
style (navy/gold, `slidekit.py` primitives), replacing
`C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\QFRA2\QFRA2_DECK_committee.pptx`
(28 slides, built by that repo's `src/qfra2_deck_v4.py`).

**NOT STARTED.** All six research inputs are done and banked (below). The build script does not exist yet.
Suggested path: `09_PRODUCT/scripts/build_qfra2_pac_deck.py`, mirroring the structure of the existing
`09_PRODUCT/scripts/build_pac_showcase.py` (same `co()` self-sizing-callout helper, same QA gates).

**Principal's page-specific asks** (his numbers are the deck's FOOTER numbers, which run 2 behind the
physical slide index — footer 3 = physical slide 5):

| His pg | Physical | Ask | Input ready |
|---|---|---|---|
| 3 | 5 | AI/ML: where do we use it, does it improve results, keep or remove? | `AI_ML_AUDIT.md` — verdict: **FALSE, remove** |
| 4 | 6 | "client aligned" -> make it **alpha focused** | not yet drafted. Slide 6 is "Four things rating houses don't do"; point 4 is "RADICAL honesty". Confirm with him which line he means before rewriting |
| 5 | 8 | CALIBRE: Integrity pillar doesn't mean integrity; Conviction wording ("clamped to track-record tier") too jargony | `CALIBRE_PILLARS.md` §6 — new lines ready |
| 8 | 12 | Why QFRA-1 is complementary in mid/small/multi; **plus** comparison vs 3Y-topper buying | `FRAMEWORK_COMPLEMENTARITY.md` + `3Y_TOPPER_BENCHMARK.md` |
| 16 | 22 | History: continuing fund must keep its slot; show every H1/H2, no gaps | `QFRA2_history_rebuilt.csv/.md` — done, 136 rows |

Also to fold in: the Apr/Oct cadence evidence (chart already rendered) and the number-audit corrections.

---

## RESEARCH BANKED (all in `03_RESEARCH_DESK/qfra2_pac_prep/`)

| File | Headline |
|---|---|
| `AI_ML_AUDIT.md` | **No ML anywhere in the frozen engine.** 137 src files, zero sklearn/lightgbm/xgboost/torch/keras. Only estimated coefficients in the whole path: one `np.linalg.lstsq` OLS in `factors_live.py:223` feeding 2 of ~6 ranked inputs. Everything else is percentile ranks blended with hand-set constants (0.9/0.1, 0.7/0.3). **The deck contradicts itself**: `qfra2_deck_v4.py:359` renders "ML on the cross-section -> too small; it memorises one era" while :~137 renders "AI/ML-assisted ranking". Verdict: remove the claim, defend the parsimony. Legacy `34_ml_alpha_predictor.py` (real RandomForest) and `32_ai_agent_overlay.py` (a HARDCODED "AI agent", self-admittedly mocked) are dead code outside the engine. LLM-agent research exists only stock-side (STOCK_SCORECARD_750); zero cross-reference to the MF model. |
| `NUMBER_AUDIT.md` | **5 of 9 headline deck numbers must not be carried forward.** Worst: slide 20's "P(beat 3-5y) ~56%" is a **hardcoded string** (`qfra2_deck_v4.py:315`) on the slide headed CLIENT-FACING, and `MODEL_SPEC.md` Part D says the metric is DEFERRED and "do not promise it client-facing". Also: "~2.6/yr churn" is CONTRADICTED (the same script's own chart data computes 3.9/yr); Small's "+2.2%/yr, +9pp" is the RAW book while the HELD book did **-1.34%/yr, win exactly 50.0%**; "+0.9%/yr live" only holds if you include Focused, which this deck's own ask excludes (true figure for the 6 in scope: **+0.65%/yr**); "~40-60 funds" is ~7x overstated. SAFE to reuse: slide 12 edges, SENTINEL 48.5->56.6, mid-momentum +9%/87%/100%, slide 27 "6 categories". Logged to `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md`. |
| `3Y_TOPPER_BENCHMARK.md` | **New evidence, answers "why not just buy the last 3 years' best?"** Pooled: QFRA-2 final-2 **+0.48% 3Y median / 56.4% win** vs 3Y-alpha Top-2 +0.37%/53.4% vs Top-3 +0.31%/53.2% vs random -0.76%/42.8%. QFRA-2 wins 6 of 8 pooled cells; Top-2's thin 5Y win reverses under the non-factor-adjusted cross-check. **Small Cap is the one robust exception** — Top-2/Top-3 beat QFRA-2 there on both metrics and both horizons. Turnover: deployed 3.9/yr, QFRA-2 raw 11.1, Top-2 7.8, Top-3 10.8 — so the topper does NOT churn worse than our own raw ranking; our low churn comes from the hysteresis rule, not from a steadier signal. Script `qfra2_3y_topper.py`, CSV `_3y_topper_benchmark.csv`. |
| `FRAMEWORK_COMPLEMENTARITY.md` | Per-category cores: Large = plain index (QFRA-2) · Large&Mid = active as-is · **Mid = factor-momentum index** (confirms the Principal's thesis: active edge ~0, HELD alpha -3.16% worst of 8, factor sleeve +9.5%/yr, 87%/100% win) · Flexi = active (only category where realized +2.16% beats theoretical) · **Multi = plain index, provisional** (worst edge -0.10, HELD -2.35%, no evidenced factor substitute yet -> R&D ticket) · **Small = plain index core + QFRA-1 as a NAMED TACTICAL SATELLITE, not core active selection.** Smallcap claim is **half right**: ~92% of the +2.20% is available to a blind pick (+2.03), so it is a size/rising-tide effect; QFRA-1's smallcap BUY leg (+3.49% median, 72% hit) is real but is short-horizon capture persistence, not stock-picking. Don't badge it "our smallcap alpha". |
| `CALIBRE_PILLARS.md` | Root cause found: the source framework says **"Integrity of portfolio"** and the deck's shortening dropped "of portfolio" — an incomplete MERIT->CALIBRE rename, not a judgment call. Two claimed metrics are not computed: **ROCE has no formula anywhere in src** (tagged "AI: parse holdings" = analyst judgment) and **"P/E discipline" is not fundamental P/E** but a NAV-trend proxy that disclaims itself. Final lines in §6 (below). |
| `HISTORY_REBUILD.md` + `QFRA2_history_rebuilt.{csv,md}` | Source CSV was **complete all along** — 17 periods (2018-H1..2026-H1) x 8 categories, no nulls. Defect 2 was purely a rendering artifact of `qfra2_deck_v4.py`'s hand-curated `HIST` dict. Rebuilt: 136 rows (43 shown before, **93 hidden, 68%**); continuing-fund slot swaps **15 -> 0**. Concrete case: JM Large Cap showed as Pick 2 then Pick 1 for one continuous holding. Script `09_PRODUCT/scripts/qfra2_history_rebuild.py`. **Slide-fit warning: 17 rows/category is too tall for the old 2-tables-per-slide layout — recommend an 8x17 heat-strip as the headline visual with per-category tables in an appendix. Heat-strip NOT built yet.** |

### CALIBRE final copy (from `CALIBRE_PILLARS.md` §6) — pending Principal's OK
| | Pillar | Line |
|---|---|---|
| C | Conviction | 3 ranked candidates: (1) "Top-of-category funds earn our biggest calls, while new ones start smaller." (2) "The higher the category rank, the bigger the call, track record permitting." (3) "Category standing sets the call's size, though a short record caps it." |
| A | Alpha | Factor alpha and appraisal ratio, gated on genuine activeness, shrunk. |
| L | Leadership | Manager tenure, key-person exit risk, AMC governance, true to mandate. |
| I | Integrity | "Fair fees versus category, with nothing hidden from the investor." (evidenced by TER vs category, Direct-plan basis — always available) |
| B | Benchmark | Win rate and up/down capture versus TRI, fairly measured. |
| R | Resilience | Down-capture, drawdown, alpha stability, concentration, and holdings quality. |
| E | Edge | A validated edge, cost-efficient and clean of red flags. |
Relocations, acronym unchanged: Active Share -> folds into Alpha's "gated"; concentration + ROCE -> Resilience; **P/E "discipline" is DROPPED from client-facing copy** rather than relocated. Our-own-process integrity (Direct+TRI, veto-only overlay, rejected-ideas log) stays in the existing Governance bullet rather than being duplicated into the pillar.

---

## CADENCE EVIDENCE — COMPLETE
`04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md` now carries three
appended sections (all 906 formations, reconciled exactly against the 2026-07-26 run):
1. **Untrimmed results.** Presented measure is the **10% trimmed mean** (Principal ruling) and it is
   **pre-registered** — his own 2026-07-26 framing said "judge on median + trimmed mean". Apr/Oct is
   1st on trim (+2.59%) and on median (+2.59%); Jan/Jul last on both. Only the plain mean disagrees
   (Jun/Dec +2.65 vs Apr/Oct +2.62). **Principal ruled: do NOT show the untrimmed mean on the chart.**
   It stays in this doc so the question is answerable if PAC asks.
2. **1-Apr vs 30-Apr TESTED** (`anchor_monthstart_vs_monthend.py`, `ANCHOR_MS_VS_ME.csv`):
   **month-END wins — trim +2.59% vs +2.00%, hit 66.0% vs 53.3% (+12.7pp).** Mechanically, a 1-Apr
   anchor closes its window on ~31-Mar, so month-start month *m* == month-end month *m-1*; verified
   across all six pairs (MS May/Nov +2.64 ~ ME Apr/Oct +2.59). The optimum is the same real window
   either way; only the label changes. Gives the earnings-digestion theory its first direct support.
3. **Smallcap-only, trimmed and untrimmed** — Apr/Oct is only 3rd of 6 on the smallcap median.
   **Do not put a smallcap-only anchor claim in the deck**; n=25/pair, nothing is meaningful.
Chart (untrimmed tick removed per ruling): `09_PRODUCT/scripts/chart_anchor_pair.py` ->
`09_PRODUCT/pr_template/out/anchor_pair_evidence.png`.

---

## CODE SHIPPED THIS SESSION (all verified, nothing committed)

`09_PRODUCT/scripts/fund_ctx_adapter.py` — three changes:
1. **Fuzzy matching REMOVED** (Principal standing order 2026-08-01). `_fuzzy_get`'s 85%-prefix matcher
   replaced by `_canon()`: canonical-exact only (AMC aliases -> scheme renames -> verified
   abbreviations -> strip a closed list of decoration words). Misses go to `gaps` for a
   one-fund-at-a-time Sonnet pass. Caught a bug in my own first cut: stripping "g" as a substring
   turned "large" into "lare"; rewritten with word-boundary regex.
2. **Sell rule = A+B+C "originate and veto"** (Principal ruling). `loser_flags>0 OR qfra_score<40`
   RETIRED. QFRA-1 originates; **QFRA-2 CALIBRE A/B grade vetoes**; C/D do not.
3. **Contradiction gate built** (was NEXT_WEEK_QUEUE item 1d). `build_fund_entries()` now returns a
   **3-tuple `(entries, gaps, contradictions)`** so it cannot be lost. Real case: Franklin India
   Equity Advantage (rank 2, score 80, grade A, ACTIVE) now returns **Hold + CONTRADICTION** where the
   old rule returned Sell.

Verification: `09_PRODUCT/scripts/test_fund_matching.py` -> **20/20 must-match, 8/8 must-not-match,
40/40 distinct canonical keys, ALL PASS**. `fund_ctx_adapter.selftest_merge()` -> **9/9 cases pass**.
`pr_template/lib/mf_mapping.py` — added `ADITYA BIRLA SL -> ABSL` (+3 more); without it that pair
silently missed.

**Skills updated:** `.claude/skills/ionic-wealth-complete/SKILL.md` (Part 3 rewritten),
`.claude/skills/qfra1-rerun/SKILL.md`, and the USER-level `~/.claude/skills/qfra2-rerun/SKILL.md`.
All three now carry: CALIBRE-is-final, index-core = **Large Cap + Mid Cap** (not the Large&Mid
category), 99-fund coverage, the rank-not-quality trap, the new sell rule, the clubbed Apr/Oct
cadence lock, and the **40.5-47.5%** capture-family overlap (a RANGE — corrected from my earlier flat
"~40%"; the down-capture leg's share floats with whether a live factor cache is present).

---

## NEXT STEPS, IN ORDER
1. **Confirm with the Principal what "pg 4 client aligned -> alpha focused" refers to** — physical
   slide 6 is "Four things rating houses don't do" and none of its four points says "client aligned".
   This is the one ask I could not pin down from the deck text. Do not guess.
2. Build the heat-strip visual for the 17-period history (8 cats x 17 periods).
3. Write `09_PRODUCT/scripts/build_qfra2_pac_deck.py` in house style; fold in every input above.
4. QA gates, in order: `check_geometry.py`, `check_geometry2.py`, `tellscan.py`, then the **mandatory
   visual PDF read** (the first two inspect declared shape positions, not pixels — a genuinely
   clipped table has passed both before). Grep the build log for `[ERR ]`: `engine.build()` swallows
   module exceptions, so a half-drawn slide can pass every gate.
5. Decide the open items in `QFRA2_SKILL_RECONCILIATION_2026-08-04.md` §5 (esp. #6: put HELD-book
   alpha next to the +0.48% headline in every QFRA-2 deliverable) and §7/§8.

## NOT DONE / OPEN
- **Nothing is committed since `994a9d6`.** One command away: see the journal entry.
- The 6 Talaulikar fund scores that have real engine scores available (reconciliation §3) — still
  substituted. Needs a read-only engine run; snapshot `QFRA2_current.csv` first (handoff §9).
- Branch `claude/sweet-austin-283067` is not merged to master; master still serves analyst skill v2.
- `MODEL_CARD.md`'s transposed "+2.86 = Small" and the other doc defects (reconciliation §4) are the
  model owner's call, not fixed here.
