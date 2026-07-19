# Management-Credibility ("Promise-vs-Delivery") Signal — Design Memo

**Author:** Ishaan Gupta (ML) | **Date:** 2026-07-17 | **Status:** DESIGN + ILLUSTRATIVE PILOT (not a certified backtest)
**Tags:** [DATA] coverage facts verified below · [INFERENCE] extraction rules & hypothesis · no [OPINION] sentiment scores invented

---

## 0. What this builds on (read-first, not duplicated)

- `ALPHA_RANKER/results/CONCALL_VALUE_PROBE_20260717/` tested a crude **keyword-tone-density** proxy
  (positive-dim hits minus red-flag hits, per 1000 words) vs forward returns on 139 tickers, 2,499
  ticker-quarters. Result: **~zero correlation**, pooled and cross-sectional (pearson -0.02 to +0.03,
  spearman -0.05 to +0.03). [DATA, verified by re-reading `SUMMARY.txt`]
  **Conclusion carried forward:** tone/word-counting is not where the edge is. This memo deliberately
  builds a **structurally different mechanism** — not "how positive did they sound" but "did what they
  said come true" — per the task's explicit orthogonality requirement.
- `ALPHA_RANKER/src/themes/concall_rubric.py` already has a structured 8-dimension rubric with a
  `promise_vs_delivery` dimension (weighted highest, 0.20, explicitly because it is "the single most
  falsifiable, least narrative-able dimension") and a `TranscriptStore` reader. This memo operationalizes
  that dimension mechanically (regex extraction + fundamentals fact-check) instead of leaving it as an
  LLM-scoring stub, and adds explicit delivery verification against PIT fundamentals — nothing here uses
  `llm_score_dimension()` (still an unimplemented stub, correctly, per D-035).

## 1. Coverage — confirmed, honest, PILOT-scale

Two **disjoint** transcript assets exist (zero ticker overlap):

| Asset | N companies | Quarters/name | Date range | Text ready? | Quarter labels |
|---|---|---|---|---|---|
| `ALPHA_RANKER/data/concalls/_coverage.csv` (raw PDF downloads) | 264 OK of 275 attempted (1,439 OK rows / 1,506 total) | mean 5.45, max 6 | **unknown** — filenames are `q1..q6` (download sequence), no date field in the CSV | **NO** — PDFs only, no text extraction run | not calendar-mapped |
| `datasets/india_earnings_calls/extracted_texts.zip` (used by `concall_rubric.TranscriptStore`), source-indexed by `MiMIC_Multi-Modal_Indian_Earnings_Calls.xlsx` | 139 (zip) / 133 (MiMIC index, 1,042 rows total incl. PPT-only) | mean 18.3, range Jul-2015 to Nov-2024 | text ready, real `Mon-YYYY` quarter labels | **YES** | real |

**Overlap between the two ticker sets = 0.** The task brief's "~267 companies" figure is the raw-PDF
pull; it is NOT yet usable for extraction (no OCR/text-layer parse done, no confirmed per-call date).
The dataset that is *actually analyzable today* is the 139-ticker zip. **This memo's pilot and all
correlations below use the 139-ticker set, not the 264.** Treating the 264 as "coverage" without
saying this would overstate readiness — flagging it explicitly per D-035.

`MiMIC_...xlsx` also carries a genuine `RESULT DATE` timestamp per call (e.g. `2024-07-16 15:30:00`)
— materially more precise than the `Mon-YYYY` → "day=20 proxy" both the prior probe and this pilot
currently use for PIT anchoring. **Build item P0**: switch to the real `RESULT DATE` for the call-date
anchor (currently a design gap, not yet fixed — see §5).

Overlap of the 139-ticker zip with `MASTER_fundamentals_pit.parquet` (`key_symbol`) = **139/139 (100%)**
— every zip ticker has fundamentals PIT coverage, so the delivery-check join is not the bottleneck;
transcript breadth is.

**Honest verdict on backtest feasibility: PILOT-ONLY, not a real backtest.** 139 names, most with
2015-2024 history, is enough for **within-company time-series illustration** (which is what §4 does)
but too thin and too clustered (large/mid-cap names that hold BSE-PDF earnings calls) for a
properly-sized cross-sectional DSR/PBO battery per RESEARCH_SOP §10. A defensible cross-sectional
backtest needs the 264-PDF set OCR'd/dated and merged in first (see data-expansion ask, §6).

## 2. Signal design

### 2.1 Guidance extraction (rule-based, no LLM)

For each transcript-quarter, split into sentences (`concall_rubric.split_sentences`) and regex-tag
each sentence into one of 5 commitment types by cue pattern, **direction-classified by a small
pos/neg lexicon** (not numeric-target parsing — see limitation below):

| Type | Cue example | Fundamentals proxy for delivery check |
|---|---|---|
| `revenue` | "revenue... growth... guidance" | `Sales` / `Revenue` (metric_norm) |
| `margin` | "margin... expect/target/maintain" | `OPM %` |
| `capex` | "capex/capacity expansion... FY__/Q_" | `CWIP`, `Fixed Assets` |
| `debt` | "debt reduction/deleverage/repay" | `Borrowings` |
| `orderbook` | "order book/backlog/pipeline... growth" | **none** — order-book/backlog is not a line item in the 34-metric fundamentals set; **not verifiable from this data source, full stop** (would need an exchange order-book-disclosure dataset) |

### 2.2 Delivery check (PIT, no lookahead)

For a commitment made at `call_date` (quarter label → date), look up the **first** fundamentals row
for the matching `metric_norm` with `available_date > call_date` inside a `[call_date+30d, call_date+200d]`
window (captures "next results release," rejects same-call restatements and stale data). Compare
actual QoQ direction (`value` vs the immediately-prior observation) against the guided direction.
`DELIVERED` (direction matches) / `PARTIAL` (flat) / `MISSED` (direction inverted) /
`NO_MATCHING_ACTUAL_IN_WINDOW` (honest "don't know," never imputed) /
`NOT_VERIFIABLE_FROM_FUNDAMENTALS` (orderbook, capex-for-financials sectors).

### 2.3 Bluff markers (lexicon only, per `concall_rubric.py`'s existing dimensions — reused, not reinvented)

- **Repeated misses**: rolling count of `MISSED` verdicts per company over trailing N calls.
- **Evasion**: `red_flag_language` dimension keywords ("will get back to you," "not the right forum,"
  "take this offline," etc.) — counted per call as `evasion_hits_this_call`.
- **Tone-shift QoQ**: `concall_rubric`'s `tone_shift` dimension (hedging-language delta vs prior quarter)
  — not yet wired into this pilot's scoring, flagged as a build item, not fabricated.
- **Prepared-remarks vs Q&A split**: task-specified requirement, join only on `available_date`.
  **NOT implemented in this pilot** — see critical limitation below.

## 3. Critical limitation found DURING the pilot (self-red-team)

Manually inspecting matched "commitment" sentences surfaced a real extraction bug, not a hypothetical
one: several "commitments" are **analyst questions, not management answers** —

> `AARTIIND Mar-2017 debt | "Surya Patra Also you indicated something repayment of debt, so can you
> tell me what is the current debt and how much that you have paid..."` — this is the analyst
> (Surya Patra) asking, not management promising, and was counted as a `MISSED` "debt commitment."

The current regex has **no speaker attribution**. Transcripts do carry speaker names inline
("Rajendra Gogri We had a 10% volume growth..."), so a speaker-turn parser is buildable, but it is
NOT built yet. **This means every verdict number in §4 below is directionally illustrative only and
should not be read as a scored signal.** This is also exactly the mechanism needed for the task's
"prepared-remarks vs Q&A separately" requirement (item 3) — one fix serves both. Flagged as **build
priority P0** (above even the RESULT DATE fix), since without it the delivery scores are contaminated
by analyst-side language.

## 4. Illustrative pilot (25 tickers, 1,422 commitment-sentences — LABELLED, not a signal)

Script: `ALPHA_RANKER/results/MGMT_CREDIBILITY_PILOT_20260717/` (`commitment_delivery_pilot.csv`,
`company_credibility_pilot.csv`, `SUMMARY.txt`). 25 tickers = zip∩fundamentals sample, first 25
alphabetically, no cherry-picking.

```
verdict distribution (n=1,422):
  NO_MATCHING_ACTUAL_IN_WINDOW     765   (54%: window/coverage gap, honestly unscored)
  NOT_VERIFIABLE_FROM_FUNDAMENTALS 282   (20%: mostly capex-for-financials, no CWIP data)
  DELIVERED                        243   (17%)
  MISSED                            76   (5%)
  NO_FUNDAMENTAL_PROXY (orderbook)  52   (4%: no line-item exists, by design)
  PARTIAL                            4
```

Company-level illustrative credibility (`DELIVERED − MISSED` mean, n≥1 only, **do not rank-trade
on this** — see §3 caveat): ranges from AUBANK/BAJFINANCE at -1.0 (small n=2-3, noisy) to
ASIANPAINT/BEL/ASHOKLEY/ANGELONE/360ONE at +1.0 (also small n). Mid-sample names with more
commitments (n=18-36) — APOLLOHOSP, BLUESTARCO, ALKEM, ASTRAL, BHARTIARTL — sit in the +0.43 to
+0.88 range, i.e. mostly-delivered on revenue-direction guidance, which is unsurprising given most
Indian large/mid-caps grow revenue most quarters in nominal terms (a **base-rate problem**, not yet
corrected — see §5 item 2).

**This table is evidence the pipeline runs end-to-end and produces sane, auditable output — it is
NOT a validated signal.** No IC, no sizing, no sleeve entry on this data.

## 5. Known gaps / build-spec (priority order)

1. **P0 — speaker attribution** (§3): parse transcript turns to isolate management statements from
   analyst questions. Transcripts have inline speaker names; a name-boundary regex + a small
   management-vs-analyst name list per call (prepared-remarks speaker block is usually named upfront)
   is buildable without an LLM.
2. **P0 — base-rate correction**: score delivery **relative to sector/index median revenue growth
   that quarter**, not absolute direction. "Grew 3% when nominal sector growth was 12%" is a soft
   miss even though the sign is positive. Cross-sectional demeaning (same technique the prior probe
   already used for `fwd_1q_xs`) applies here too.
3. **P1 — real call-date anchor**: switch from `Mon-YYYY → day-20 proxy` to `MiMIC_...xlsx`'s actual
   `RESULT DATE` column (has time-of-day too — most results are released ~15:30 IST, after market
   close, relevant for same-day-vs-next-day return attribution).
4. **P1 — numeric-target extraction**: current direction-only classifier ("up"/"down") is a
   deliberately conservative choice to avoid fabricating precision from noisy PDF-extracted text;
   a build could extract explicit % figures ("guidance of 12-14% growth") for a tighter magnitude-match,
   but only where the regex captures a clean number — never interpolated/guessed.
5. **P2 — orderbook verifiability**: needs an external order-book/backlog disclosure dataset (not in
   `MASTER_fundamentals_pit.parquet`'s 34 metrics); until then this commitment type stays
   flagged-not-scored, honestly, rather than proxied by something unrelated.
6. **P2 — capex-for-financials**: CWIP/Fixed Assets are not meaningful for banks/NBFCs (18 of the
   282 `NOT_VERIFIABLE` rows, `AUBANK`/`BAJFINANCE`/`AXISBANK` etc. in the pilot are here); capex
   commitments should be sector-gated to capex-heavy sectors (industrials/pharma/cement) only.
7. **P2 — 264-ticker PDF set**: needs OCR/text-layer extraction + per-transcript date parse (most
   earnings PDFs state the call date on page 1) before it can be merged in as coverage expansion.

## 6. Hypothesis, expected sign, test design

**H (W4M-01):** Companies whose management **delivers** on prior quantified guidance (high
promise-vs-delivery score, low evasion/red-flag hit rate) earn **positive** forward abnormal returns
relative to companies that repeatedly miss/walk back guidance, **sector-neutral**, over a 1Y-3Y
horizon (matches `concall_rubric.HORIZON_EMPHASIS`: this dimension is near-irrelevant at 1M, dominant
at 5Y — a slow-moving reputational signal, not a fast one).

**Expected sign:** credibility score (rolling `DELIVERED − MISSED`, cross-sectionally demeaned) →
POSITIVE forward return, strongest at 1Y+ horizons, near-zero at <1M (per the existing horizon-emphasis
prior already encoded in `concall_rubric.py` — not invented for this memo).

**Test design once P0/P0 fixes above are done:**
- **Primary: cross-section on the 139-name (or expanded) coverage set.** Rank companies quarterly by
  trailing rolling credibility score (min 3 prior verifiable commitments to be scored, else excluded
  — never impute). Long-short decile or full-rank IC against sector-neutral forward return, same
  purge/embargo CV discipline as any other factor (purge = the commitment's own delivery-check window,
  embargo = 1 quarter beyond it to avoid contaminating the NEXT commitment's training fold).
- **Secondary: event-time** around the delivery-check disclosure date itself (does the market re-rate
  when a miss/walk-back becomes visible, i.e. is this instead a post-earnings-drift proxy rather than
  a distinct credibility factor — a placebo the overfit desk should run).
- **Per FACTOR_LIBRARY rule**: before any ML variant, a rank/linear baseline (simple credibility-score
  rank, no LGBM) must clear costs (`COST_STANDARDS.md`, once Principal-approved) on the expanded
  coverage set. This memo does not attempt that yet — coverage is pilot-scale (§1).
- **Leakage placebos to run before any certification**: (a) shuffle-placebo — randomly permute
  credibility scores across companies within a quarter, confirm IC collapses to ~0; (b) lag-placebo —
  shift the credibility score forward by one quarter (i.e. score computed AFTER the return window it's
  meant to predict) and confirm no residual signal, catching any accidental lookahead in the
  `available_date` join; (c) sector-placebo — confirm the signal isn't just re-deriving sector
  momentum (test within-sector demeaned only, per §5 item 2).

## 7. Orthogonality vs the existing 7 legs (expected, to be measured post-fix)

Distinct mechanism from all of: price momentum, value, quality (accrual/ROIC-based), low-vol,
official "Sentiment" theme (news/social tone), Growth (historical realized growth), Catalyst
(forward events). This signal specifically measures **track-record-of-honesty about the future**,
which quality/value factors do not capture (a company can have great ROIC and still over-promise on
guidance) and which the prior tone-density probe (§0) already showed is NOT captured by simple
keyword sentiment. Expected low correlation to Quality (weak positive — capital-allocation-discipline
overlap) and near-zero to Momentum/Value. To be measured empirically once P0 fixes land and coverage
is large enough for a real orthogonality run (`/orthogonality` skill), not asserted here.

## 8. Verdict

**NOT gate-ready.** Design is sound and reuses an already-approved rubric structure
(`concall_rubric.py`'s `promise_vs_delivery` dimension, weighted highest for exactly this reason).
Pilot proves the extraction-to-delivery-check pipeline runs and produces auditable, honest
"don't know" buckets rather than forced scores. Two P0 fixes (speaker attribution, base-rate
correction) are required before ANY number from this pipeline is treated as a signal, and coverage
is pilot-scale (139 names) — a real cross-sectional backtest needs the data-expansion ask below.
Candidate for **NEXT-SLEEVE** material once P0s are fixed and a rank baseline clears costs.

**Data-expansion ask:** OCR + date-parse the 264-company `ALPHA_RANKER/data/concalls/` PDF set
(Data Officer gate) to roughly double coverage and reduce the large/mid-cap skew of the current
139-name set (microcap-heavy PDF-pull tickers would add exactly the segment
`07_FRAMEWORK_MICROCAP.md` says leans hardest on primary-source concall reading).
