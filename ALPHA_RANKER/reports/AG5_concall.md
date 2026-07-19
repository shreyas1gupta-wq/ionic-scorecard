# AG5 — Management-Commentary (Concall) Scoring Rubric + Prototype Extractor

**Phase 3 deliverable.** Module: `ALPHA_RANKER/src/themes/concall_rubric.py`. Demo: `src/themes/run_concall_demo.py` → `results/concall_demo_extract.json`.
Owner (per `10_AGENT_ARCHITECTURE.md`): Concall/Management module agent → sector analysts.

## 1. What this is (and isn't)

Management commentary is a **scored INPUT**, not a classifier and not a standalone 8th theme. The
scoring engine (`02_SCORING_ENGINE.md`) has exactly 7 official themes — Momentum · Value · Quality ·
Growth · Sentiment/Flow · Catalyst · Forensic/Risk. This rubric produces a **Management/Commentary
composite (0-100)** for interpretability/reporting, then **distributes** it into those 7 themes
(mirrors `10_AGENT_ARCHITECTURE.md`: "Output feeds Growth (1Y), Management (5Y), and Forensic
themes"). No LLM is called and no score is fabricated in this prototype — the extractor produces
**candidate sentences (evidence)** per dimension; a human or the later LLM agent assigns the 0-5.

## 2. The 8 dimensions (7 scored + 1 red-flag penalty)

| # | Dimension | 0 (anchor) | 5 (anchor) | Feeds theme(s) |
|---|---|---|---|---|
| 1 | **Guidance credibility & specificity** | No numeric guidance, or vague boilerplate ("we remain confident of growth") with no basis; methodology changed without explanation | Specific, quantified, multi-metric guidance (revenue/margin/capex range) with a clear bridge, consistent quarter-to-quarter, addressed directly under analyst pushback | Growth, Catalyst |
| 2 | **Tone shift vs prior quarter** | Marked deterioration: more hedging ("largely", "broadly", "should", "hopefully"), shorter/deflecting answers, avoiding previously-given numbers, new defensiveness | Stable-or-improving: same/greater specificity and confidence as prior call(s), management raises the hard question first, no new hedging | Growth |
| 3 | **Capex/expansion & growth-runway language** | No capex/expansion commentary; or plans repeatedly delayed/downsized with no new explanation; generic "we continue to invest" | Concrete capacity/capex plan — amount, timeline, expected utilization/payback — explicitly linked to a demand driver | Growth |
| 4 | **Promise-vs-delivery tracking** | Prior quarter's specific guidance missed by a wide margin, unacknowledged; or guidance quietly dropped/redefined | Prior guidance met/exceeded, explicitly reconciled on this call ("as we said last quarter... we delivered...") | Growth, Quality |
| 5 | **Demand/order-book commentary** | No order-book/demand color; or demand softness/cancellations/push-outs acknowledged with no credible offset | Order book/pipeline growth vs prior quarter, book-to-bill/backlog metrics, broad-based (not one large one-off) demand | Growth, Catalyst |
| 6 | **Margin outlook** | Margin guidance withdrawn/degraded with vague "cost pressures", no specific levers, no forward view | Specific trajectory with named levers (mix, pricing, cost actions, operating leverage), credible bridge to guided range | Growth, Quality |
| 7 | **Capital-allocation discipline** | Capital into unrelated/related-party ventures, dilutive raises with no use-of-funds clarity, no stated debt/buyback/dividend policy, or reversed priorities | Clear, consistently-applied framework (stated ROIC hurdle, dividend/buyback policy, debt targets) with actions matching words over multiple quarters | Quality |
| 8 | **RED-FLAG language** (evasion / blame-external / accounting-defensiveness / management churn) — **penalty, 5=clean → 0=severe** | Multiple/severe instances: hostile/evasive non-answers, repeated "one-off"/external blame for recurring misses, defensive/legalistic accounting answers, unexplained CFO/auditor/management departure | No evasion, direct answers to tough questions, no externalization of controllable misses, no accounting defensiveness, stable management team | Forensic/Risk |

## 3. Composite formula

```
management_commentary_score(dims 1-7)  = Σ (dim_score/5 · weight) · 100         # weights below, renormalized over present dims
apply_redflag_penalty(base, redflag)   = base − severity(redflag) · 40 · horizon_emphasis   # severity = (5-redflag)/5
```

Positive-dimension weight prior (equal-weight-ish, `promise_vs_delivery` up-weighted as the least
narrative-able/most falsifiable dimension — a prior to be calibrated later, same status as every
other weight in this repo):

| Dim | Weight |
|---|---|
| guidance_credibility | 0.16 |
| tone_shift | 0.10 |
| capex_growth_runway | 0.14 |
| promise_vs_delivery | 0.20 |
| demand_orderbook | 0.16 |
| margin_outlook | 0.12 |
| capital_allocation | 0.12 |

Missing dimensions are **excluded and weights renormalized** — never silently imputed (D-035 / `02` Step 1).
The red-flag penalty is a lightweight, concall-scoped version of `08_FORENSICS_REDFLAGS.md`'s
severity model (`base_severity × size_mult × regime_mult × offset`); full context-scaling (size/regime/company-strength
offsets) stays owned by the forensic module for consistency — this only guarantees the concall
red-flag signal actually bites before it reaches Forensic/Risk.

## 4. How it differs by horizon

| Horizon | Positive-dims emphasis | Red-flag emphasis | Why |
|---|---|---|---|
| **1M** | 0.0 (off) | 1.0 | Not in `04_FRAMEWORK_1M.md`'s factor library at all — too slow-moving for a 1-month lens, except a fresh evasive/withdrawn-guidance call is itself a fast risk catch |
| **1Y** | 0.6 | 1.0 | `05_FRAMEWORK_1Y.md` lists "Management/Guidance (medium weight)" — guidance & promise-tracking feed the high-weight Growth theme (estimate-revision engine); capital allocation feeds Quality |
| **5Y** | 1.0 (full) | 1.0 | `06_FRAMEWORK_5Y.md` + `01_PHILOSOPHY_AND_ARCHITECTURE.md`: Management & Promoter is **dominant** at 5Y — years of promise-vs-delivery, capital-allocation track record, and integrity accumulate into the single highest-conviction downside-protective read |
| **Microcap** | 0.9 | 1.2 | `07_FRAMEWORK_MICROCAP.md`: sell-side estimates barely exist, so the desk "relies on primary reading (annual reports, RHPs, **concalls**, filings)" — and thinner governance means red flags get an extra multiplier, not less |

## 5. Data source & coverage (verified, not assumed)

- **CSV metadata** (`datasets/india_earnings_calls/final_train/test/valid.csv`, 1,042 rows, 133
  unique tickers, Feb-2019→Nov-2024): `transcript_link` is a **link-only** BSE PDF URL column
  (822/1042 rows non-null) — but that is NOT the text source we use.
- **Actual text IS embedded**: `datasets/india_earnings_calls/extracted_texts.zip` contains
  181,376 per-page `.txt` files across 5,731 folders (2,549 transcript folders + 3,182 PPT
  folders), keyed `<TICKER>_<Mon-YYYY>_transcript/page_N.txt`. No web fetch needed for this
  prototype; `TranscriptStore` reads directly from the zip.
- **Pilot coverage (verified by listing, not assumed):**

| Ticker | # transcript quarters | Range |
|---|---|---|
| TCS | 30 | Aug-2017 → Oct-2024 |
| MARUTI | 26 | — |
| INFY | 27 | — |
| ASIANPAINT | 25 | Dec-2018 → latest |
| HINDALCO | 8 | — |
| TATASTEEL | 8 | — |
| HDFCBANK | 11 | Apr-2022 → Oct-2024 |
| NESTLEIND | 3 | — |
| **GRAVITA** | **0** | not in this curated dataset |
| **SHAKTIPUMP** | **0** | not in this curated dataset |

**8 of 10 pilot names have transcript text; 2 (GRAVITA, SHAKTIPUMP — the small/microcaps) do not**
appear in this curated 133-ticker set at all (consistent with the dataset skewing to
larger/more-liquid NIFTY names with reliable BSE-hosted transcript PDFs). This is an honest gap,
not a bug — a follow-up data-sourcing task (screener.in concall links, per `09_DATA_LAYER.md`) is
needed for microcap coverage before the concall rubric can run on names like these.

## 6. Prototype extractor

`extract_candidate_sentences(text, max_per_dim)` — regex/keyword heuristics per dimension over
sentence-split transcript text, returning up to N candidate sentences per dimension as an
**evidence pool** (not a score). Verified on live text: e.g. for HDFCBANK Oct-2024, the red-flag
heuristic correctly surfaced *"I don't have that particularly handy..."* as an evasion-pattern hit.

`llm_score_dimension(dimension_key, candidate_sentences, prior_quarter_context)` is a **clearly-marked
stub** — returns `{score: None, rationale: "LLM SCORING HOOK NOT WIRED", evidence: [...]}`. It documents
the intended interface (dimension anchors as the rubric prompt, candidate sentences + prior-quarter
context as input, `{score 0-5, rationale, evidence}` as output, confidence-gated per `02`'s
human-in-the-loop rule) for the later LLM agent layer, without calling an LLM or inventing a number now.

Demo output for the 2 highest-coverage-but-first-available pilot names (HDFCBANK Oct-2024,
ASIANPAINT latest) is in `results/concall_demo_extract.json` — per-dimension candidate-sentence
counts and text, plus the full pilot coverage table.
