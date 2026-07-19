# PRINCIPAL SCORECARD — Per-Stock Product
Author: Tanvi Desai (Head of Product, E-026). 2026-07-17.
Scope: INFY, BANDHANBNK, KPIGREEN (Principal-assigned) + a reusable template for any NIFTY-750 name.
Data sources (verified row-counts below), no invented numbers (D-035). Tags: **[DATA]** = read directly
from a named file/row, **[INFERENCE]** = my construction from named data, **[OPINION]** = my editorial
judgment, explicitly flagged as such.

---

## HOW TO READ THIS (one-time note — read before the first scorecard)

1. **There are TWO scoring engines in this building, and they currently disagree with each other.**
   - **Engine 1 — the 7-leg RELATIVE composite** (`rnd/forward_test/scores_asof_20251205.parquet`,
     976 rows, as-of 2025-12-05) is the one Arjun Rao's desk has actually put through a validation
     protocol: PIT-survivorship-corrected, 5-of-7-legs-required, decile-monotone historically
     (IC_IR ~1.76 PIT-corrected in the 2020-25 era). **[DATA: `rnd/forward_test/FROZEN_SPEC.md` §5]**
     BUT — and this is the caveat the Principal must have every time this score is quoted — it is
     **PRE-REGISTERED and NOT YET GRADED**. It was frozen 2026-07-17 against a 2025-12-05 cross-section
     specifically so nobody peeks at forward returns before the evaluation date. **[DATA: FROZEN_SPEC.md §5,
     "PRE-REGISTERED evaluation protocol — READ BEFORE GRADING... Do NOT grade early. Do NOT peek."]**
     It is ALSO true that this same construction's in-sample stats are DSR≈0 and CSCV-PBO≈0.92 — a
     multiple-testing problem from 456 logged historical trials — which is exactly WHY the forward-freeze
     exists rather than a further in-sample re-test. **[DATA: FROZEN_SPEC.md §0]** The honest read: this is
     the firm's best RELATIVE ranker, its historical construction is clean, and its own creator has staked
     a pre-registered forward bar of "~0.11-class realized IC = pass, near-zero or sign-flipped = kill" —
     **we do not yet know which of those two outcomes we're in.**
   - **Engine 2 — the older per-horizon scorer** (`results/universe_final_scores.parquet`, 751 rows) emits
     `score_1M/1Y/5Y/MICRO`, a `band` (REDUCE/HOLD/BUY-class), and a `pup` ("probability-of-upside"-style
     number). **This engine is UNVALIDATED** — no forward-test protocol, no DSR/PBO record has been run on
     it in this pass. Its `pup` field is **NOT a calibrated probability**: it is computed as
     `pup = 1/(1+exp(-score/40))`, a fixed-parameter logistic squash of the score itself, with no fitting
     against realized hit-rates anywhere in the code I read. **[DATA: `src/scoring/universe_combine.py` L95]**
     Treat every `pup` number below as "a monotone transform of the score," never as "this stock has a
     64% chance of rising."
2. **Where the two engines disagree sharply (INFY, KPIGREEN below), do not average them or pick the one
   you like better.** The disagreement itself is the honest finding — it means the two constructions are
   picking up different things (the 7-leg is cross-sectional/relative-only; the older engine's methodology
   was not re-verified in this pass) and no reconciliation exists yet. That reconciliation is a QUANT-DESK
   question (Arjun Rao), not a product-desk judgment call — flagged, not resolved, here.
3. **There is no ABSOLUTE (buy/hold/sell-in-absolute-terms) score in this building today.** Arjun Rao has
   written a design (`rnd/wave4/ABSOLUTE_SCORER_SPEC.md`) for how one COULD be built on top of the relative
   score without corrupting it, but it is explicitly "**design only, not built**." **[DATA: ABSOLUTE_SCORER_SPEC.md
   header]** In place of a fabricated absolute number, each scorecard below gives the current REGIME CONTEXT
   the design would have used, read straight from `results/current_regime.json` (file_last_date 2026-02-27):
   **trend = sideways** (Nifty500 below its 50dma, above its 200dma), **volatility = normal**,
   **breadth = narrow/large-cap-led** (small/midcap relative strength negative both 3M and 6M),
   **risk appetite = risk-off**, **leading factor = Value**. **[DATA]** This is context, not a verdict.
4. **Decile scale**: 1 = worst-ranked tenth of the scored universe, 10 = best-ranked tenth (802 of 976
   names clear the 5-of-7-legs bar and are scored; 174 are correctly left unscored as data-thin).
   **[DATA: FROZEN_SPEC.md §4]**
5. **Business-model / KB coverage**: the firm's business-model knowledge base
   (`rnd/wave4/batch_A.json` + `batch_B.json` + `batch_C.json`, 25 names total) does NOT yet cover any of
   the three names in this batch. Marked **KB PENDING** below, routed to equity-head-ananya-iyer's desk —
   not fabricated from memory.
6. **Forensic screen**: uses `rnd/forensic/FORENSIC_FRAMEWORK_CA.md` (Farhan Qureshi, Compliance). Nearly
   every genuinely diagnostic forensic item in that framework (related-party terms, auditor opinion, CARO
   clauses, receivables ageing) is **FILING-READ-ONLY** — it requires an analyst to read the actual Annual
   Report / auditor's report, which has not been done for these three names in this pass. What CAN be
   screened today is the coarse, DATA-SCREENABLE proxy already sitting inside the 7-leg composite itself
   (`bs_issuance`, `bs_asset_growth`, `quality_cfo_pat`) — connected below to the named framework items they
   proxy for, with the framework's own caution carried forward verbatim: **"every partial tag is a lead for
   the analyst-agent's filing read, never a stand-alone verdict."** **[DATA: FORENSIC_FRAMEWORK_CA.md L506-511]**

---

## SCORECARD 1 — INFY (Infosys)

### Validated 7-leg relative score
**Score: +39.65 | Decile: 7 of 10 | Legs present: 7 of 7 (full composite)**
**[DATA: `rnd/forward_test/scores_asof_20251205.parquet`, row `symbol==INFY`, as-of 2025-12-05]**

| Leg | Value | Plain-English read |
|---|---|---|
| Value (earnings yield) | **+39.9** | Moderately cheap vs the scored universe on earnings yield — not a screaming value name, but above-average cheapness. |
| Momentum (residual, 12-1) | **−42.0** | Clearly weak — price momentum, adjusted for market beta, is in the bottom part of the universe. |
| Trend (65-day MA slope) | **+51.1** | Medium-term trend is actually constructive/improving — this pulls the other way from the momentum leg. |
| Quality (QMJ) | **+81.4** | One of the strongest quality reads in the entire scored universe — this is the single biggest driver of the positive composite. |
| Balance-sheet: net issuance (−) | **−54.1** | Below-average on the issuance-discipline leg — INFY screens as relatively more dilutive / less buyback-active than peers on this metric (this leg is already sign-flipped so higher=better; a negative reading here is a genuine drag, not a data artifact). |
| Balance-sheet: asset growth (−) | **+18.5** | Mildly favorable — asset-base growth is restrained relative to peers (this is the Cooper-Gulen-Schill "overinvestment" leg; a positive score here means LOW growth, which the model treats as good). |
| Quality: CFO/PAT cash-conversion | **−3.5** | Roughly neutral, slight negative — cash-backed earnings are in line with the universe, not a standout either way. |

**What's driving the +40**: exceptional quality (+81) and an improving medium-term trend (+51) more than
offset a genuinely weak momentum read (−42) and a below-average issuance-discipline score (−54). Decile 7
means: above the median of the scored universe, but not a top-decile idea by this construction.

### Thesis (memo-craft voice) — descriptive of what the model shows, NOT a Product-desk investment call
**[INFERENCE], grounded in the leg table above:** INFY is priced for a company whose growth engine looks
tired on trailing price action, but the 7-leg composite's WHAT is that the market may be under-crediting
persistent balance-sheet quality (QMJ +81, one of the best in the scanned universe) against a trend signal
(+51) that has already started to turn, even while the pure momentum leg (−42) has not yet confirmed it.
WHY NOW: the trend-vs-momentum split (+51 vs −42) is itself the thing to watch — it says price direction and
price persistence currently disagree, which is an unresolved state, not a settled one. MARGIN OF SAFETY: the
quality floor (+81) and restrained asset growth (+18.5) mean this is not a balance-sheet risk story even if
the re-rating case is wrong — the downside case here is "no re-rating," not "capital impairment." WHAT WOULD
BREAK IT, ranked: **(1)** the issuance-discipline leg (−54) worsening further alongside a QMJ deterioration
would be the fastest-acting kill — quality is the entire thesis; **(2)** the trend leg (+51) rolling back over
without momentum ever confirming would mean the improving-trend read was noise, not signal; **(3)** — explicitly
NOT a kill signal on its own — the decile staying at 7 rather than rising is not itself informative until the
forward-test grading date; do not over-read month-to-month decile wobble on a pre-registered, ungraded score.

### Business-model summary
**KB PENDING.** INFY is not one of the 25 names covered in `rnd/wave4/batch_A/B/C.json`. Routed to
equity-head-ananya-iyer / analyst-it-karan-malhotra's desk for a business-model KB entry before any
Principal-facing deep-dive is built on top of this scorecard.

### Forensic screen
No HARD-VETO or HEAVY-PENALTY pattern visible in the coarse, data-screenable legs: issuance (−54) is a
below-average score but well inside a normal range (compare KPIGREEN's −93 below), asset-growth (+18.5) is
favorable, and CFO/PAT (−3.5) is essentially neutral. **No forensic red-flag connection to raise here** —
this is a "nothing showing in the coarse proxy" read, not a "filing-confirmed clean" read (filing-level items
— auditor opinion, RPT terms, CARO clauses — remain FILING-READ-ONLY and have not been checked).

### Honest caveats — the two-engine disagreement
| | Engine 1 (7-leg, validated construction, forward-test NOT graded) | Engine 2 (older per-horizon, UNVALIDATED) |
|---|---|---|
| Score | **+39.65** (decile 7/10) | **1M: −52 (band REDUCE, pup 0.21)**, 1Y: −25 (HOLD, pup 0.35), 5Y: −9 (HOLD, pup 0.44), MICRO: −17 (HOLD, pup 0.39) |
**[DATA: `results/universe_final_scores.parquet`, row `symbol==INFY`]**

This is a genuine, sharp disagreement — Engine 1 says moderately above-average, Engine 2 says negative
across every horizon (most negative at 1-month, −52, flagged REDUCE). **[INFERENCE]** The two engines likely
weight momentum very differently: Engine 2's negative read across all horizons is directionally consistent
with Engine 1's own weak momentum leg (−42) if Engine 2 weights momentum/trend more heavily and quality less
heavily — but I have not verified Engine 2's actual leg weights in this pass, so this is a hypothesis, not a
reconciliation. **Do not resolve this by picking the number you prefer — route to quant-head-arjun-rao.**
Remember `pup` on Engine 2 (0.21-0.44 range here) is an uncalibrated logistic transform of its own score, not
a probability.

### Regime context (not an absolute score — see note 3 above)
Sideways trend, normal volatility, narrow/large-cap-led breadth, risk-off appetite, Value leading factor
(as of 2026-02-27, `results/current_regime.json`). A risk-off, Value-led regime is not obviously friendly to
a quality-momentum-split name like INFY either way; no absolute-scorer number exists to quantify this.

---

## SCORECARD 2 — BANDHANBNK (Bandhan Bank)

### Validated 7-leg relative score
**Score: +50.87 | Decile: 8 of 10 | Legs present: 7 of 7 (full composite)**
**[DATA: `rnd/forward_test/scores_asof_20251205.parquet`, row `symbol==BANDHANBNK`, as-of 2025-12-05]**

| Leg | Value | Plain-English read |
|---|---|---|
| Value (earnings yield) | **+88.0** | Very cheap — near the top of the entire scored universe on earnings yield. This is by far the single biggest driver of the positive composite. |
| Momentum (residual, 12-1) | **−6.6** | Roughly neutral, slightly below average. |
| Trend (65-day MA slope) | **−48.9** | Clearly poor — the stock is in a genuine medium-term downtrend by this measure, the single biggest drag on the composite. |
| Quality (QMJ) | **+5.5** | Roughly neutral quality. |
| Balance-sheet: net issuance (−) | **+21.4** | Mildly favorable — better issuance discipline than the average scored name. |
| Balance-sheet: asset growth (−) | **+26.4** | Mildly favorable — asset-base growth restrained relative to peers. |
| Quality: CFO/PAT cash-conversion | **+30.2** | Good — cash-backed earnings, a genuine positive on the cash-authenticity leg. |

**What's driving the +51**: extreme value cheapness (+88) plus a consistently modest-positive
balance-sheet/quality trio (issuance +21, asset-growth +26, CFO/PAT +30) overwhelms a clearly negative
price trend (−48.9) and neutral momentum. Decile 8 places this in the top quintile of the scored universe —
this is a genuine "cheap-and-clean-balance-sheet, but currently out of favor on price" profile.

### Thesis (memo-craft voice) — descriptive of what the model shows, NOT a Product-desk investment call
**[INFERENCE], grounded in the leg table above:** WHAT — BANDHANBNK is priced for continued price weakness
(trend −48.9), but the composite's variant read is that the balance-sheet and cash-authenticity signals
(issuance +21, asset-growth +26, CFO/PAT +30, all pointing the same modest-positive direction) plus extreme
earnings-yield cheapness (+88) are not showing the deterioration a −49 trend score would suggest if this
were a genuine fundamental unravel rather than a price-only rout. WHY NOW: the fact that all three
balance-sheet/quality legs point the same (positive) direction simultaneously, while price alone is negative,
is the specific divergence worth flagging — it is timely precisely because it is unresolved right now, not
because of any single new catalyst identified in this pass. MARGIN OF SAFETY: the +88 value score is
unusually extreme — even a partial re-rating from this level provides real cushion, and none of the three
balance-sheet legs show the asset-growth/issuance/CFO-PAT co-firing pattern that flags a capital-guzzler or
earnings-quality problem (contrast KPIGREEN below). WHAT WOULD BREAK IT, ranked: **(1)** any of the three
balance-sheet legs (issuance/asset-growth/CFO-PAT) turning negative together would flip this from "cheap and
clean, out of favor" to "cheap for a reason" — the fastest-acting kill; **(2)** the trend leg (−48.9)
deteriorating further without any of the fundamental legs confirming would mean the price weakness is
starting to look self-fulfilling rather than a pure sentiment gap; **(3)** — explicitly NOT a kill signal —
the value leg being "too good to be true" is not itself a reason to distrust the score; per SageOne's own
documented mistake pattern (`MEMO_CRAFT.md` §3), valuation richness/cheapness alone should not be the
primary trigger either way.

### Business-model summary
**KB PENDING.** BANDHANBNK is not one of the 25 names covered in `rnd/wave4/batch_A/B/C.json`. Routed to
equity-head-ananya-iyer / analyst-financials-meera-krishnan's desk (banks/NBFC coverage) for a business-model
KB entry, including the MFI-heavy asset-quality context that a bank of this profile typically carries and
that this scorecard cannot verify without a filing-level read.

### Forensic screen
No HARD-VETO or HEAVY-PENALTY pattern in the coarse, data-screenable legs — issuance (+21.4), asset-growth
(+26.4), and CFO/PAT (+30.2) are all mildly POSITIVE, the opposite direction of a red flag. **No forensic
red-flag connection to raise here** on the coarse proxy. As with INFY, this is "nothing showing in the
data-screenable legs," not a filing-confirmed clean bill — RPT terms, auditor opinion, and CARO-clause items
remain FILING-READ-ONLY and unchecked, and a bank's asset-quality/NPA disclosure (a filing-only item, not
present in this fundamentals panel) is the single most important thing an analyst deep-dive would need to add
for a lender specifically.

### Honest caveats — the two-engine disagreement
| | Engine 1 (7-leg, validated construction, forward-test NOT graded) | Engine 2 (older per-horizon, UNVALIDATED) |
|---|---|---|
| Score | **+50.87** (decile 8/10) | **1M: +23 (band HOLD, pup 0.64)**, 1Y: +9 (HOLD, pup 0.56), 5Y: −8 (HOLD, pup 0.45), MICRO: −3 (HOLD, pup 0.48) |
**[DATA: `results/universe_final_scores.parquet`, row `symbol==BANDHANBNK`]**

This is the mildest of the three disagreements in this batch — both engines read BANDHANBNK as
constructive-to-neutral, with Engine 2 actually most positive at the 1-month horizon (+23) and fading to
mildly negative by 5-year (−8). Directionally consistent, not identical. Still route any precise
reconciliation to quant-head-arjun-rao rather than treating agreement here as confirmation of either engine's
validity — Engine 2 remains unvalidated regardless of directional overlap.

### Regime context (not an absolute score — see note 3 above)
Sideways trend, normal volatility, narrow/large-cap-led breadth, risk-off appetite, Value leading factor
(as of 2026-02-27). A Value-leading, risk-off regime is arguably the single most consonant backdrop of the
three names in this batch for BANDHANBNK's own extreme-value profile — noted as context only, not quantified
into any score.

---

## SCORECARD 3 — KPIGREEN (KPI Green Energy)

### Validated 7-leg relative score
**Score: −90.52 | Decile: 1 of 10 (bottom decile) | Legs present: 7 of 7 (full composite)**
**[DATA: `rnd/forward_test/scores_asof_20251205.parquet`, row `symbol==KPIGREEN`, as-of 2025-12-05]**

| Leg | Value | Plain-English read |
|---|---|---|
| Value (earnings yield) | **+36.2** | Moderately cheap — this is the ONLY leg pulling in the positive direction. |
| Momentum (residual, 12-1) | **+17.5** | Mildly positive — price momentum is actually a modest positive, not part of the problem. |
| Trend (65-day MA slope) | **−61.9** | Poor — a clear medium-term downtrend. |
| Quality (QMJ) | **−33.6** | Below-average quality. |
| Balance-sheet: net issuance (−) | **−93.3** | Extreme — near the very bottom of the entire scored universe. Heavy share/capital issuance relative to peers. |
| Balance-sheet: asset growth (−) | **−97.0** | Extreme — one of the fastest-growing asset bases in the ENTIRE scored universe (976 names); this leg exists specifically to penalize overinvestment (Cooper-Gulen-Schill anomaly), and KPIGREEN sits at its worst extreme. |
| Quality: CFO/PAT cash-conversion | **−62.2** | Poor — reported earnings are notably not backed by operating cash flow; a real CFO/PAT divergence. |

**What's driving the −90.5**: this is NOT one bad leg — it is three balance-sheet/quality legs co-firing at
once (issuance −93.3, asset growth −97.0, CFO/PAT −62.2), on top of a poor trend (−61.9) and below-average
quality (−33.6). Only value (+36.2) and momentum (+17.5) are positive, and they are nowhere near enough to
offset the rest. Decile 1 means this is in the worst-ranked tenth of the 802 fully-scored names.

### Thesis (memo-craft voice) — descriptive of what the model shows, NOT a Product-desk investment call
**[INFERENCE], grounded in the leg table above:** WHAT — KPIGREEN's composite reads as a company raising
capital fast (issuance −93), deploying it into a rapidly-growing asset base (asset-growth −97), while
reported profit is running well ahead of actual cash generation (CFO/PAT −62.2) — the textbook shape the
asset-growth-anomaly and CFO/PAT legs exist to catch. WHY NOW: all three legs are firing TOGETHER in the same
scoring window, not one in isolation, which is the co-firing pattern the firm's own forensic framework treats
as materially more diagnostic than any single flag (`FORENSIC_FRAMEWORK_CA.md`'s "non-additive escalation"
rule for co-firing items). MARGIN OF SAFETY: value (+36.2) and momentum (+17.5) are the only things holding
this above the absolute floor — thin, and explicitly NOT described as a safety net here. WHAT WOULD BREAK
(or CONFIRM) THIS, ranked: **(1)** if the next 1-2 PIT quarters show CFO/PAT convergence (the cash-flow catching
up to reported profit) WHILE the asset base finishes its growth phase and starts converting to revenue, this
flips from "capital-guzzler red flag" to "growth-inflection story" — this is THE single fact to watch, ranked
first because it is the fastest-acting and most diagnostic; **(2)** conversely, if issuance/asset-growth
continue at this pace with NO corresponding CFO/PAT convergence, the co-firing pattern strengthens and this
stays a genuine balance-sheet concern, not a timing artifact; **(3)** the trend leg (−61.9) alone is
explicitly NOT the thing to watch — a trend reversal on price with no change in the three balance-sheet legs
would not, by itself, resolve the underlying question.

### KPIGREEN-specific open question: capital-guzzler vs. growth-inflection (routed, not resolved)
**[OPINION, framed for routing — this is precisely the tension the Principal asked to have surfaced, not
adjudicated by Product.]** The firm's own knowledge base holds BOTH sides of this tension as documented
patterns, and KPIGREEN's leg profile sits exactly at the fork between them:
- **The bear read**: `rnd/FRAMEWORK_CATALOG.md` L64 — "Asset-growth anomaly (overinvestment): high asset
  growth predicts LOWER future returns" (Cooper-Gulen-Schill), cited as the reason `bs_asset_growth` is
  built sign-flipped into the composite in the first place. KPIGREEN's −97.0 on this exact leg is about as
  extreme a hit on this specific anomaly as the universe contains.
- **The bull read**: `rnd/FRAMEWORK_CATALOG.md` L61-62 — "Margin trajectory/operating-leverage inflection...
  THE microcap-multibagger upside engine per firm's own model" and "Earnings-inflection + multi-year-base-
  breakout coincidence... Universal winning setup across ALL eras studied (2007-2025)." A capex-heavy
  balance-sheet build-out is the PRECURSOR condition both patterns require — the same asset-growth signature
  that penalizes KPIGREEN in the anomaly framing is also the raw material of the multibagger framing, and the
  composite as built cannot tell these two stories apart from the fundamentals panel alone.
- **What would settle it, and who owns settling it**: whether KPIGREEN is currently mid-overinvestment (bear
  case) or mid-inflection (bull case) is a filing-read / business-model question — has revenue/margin started
  converting off the expanded asset base yet, is the capex funding genuine capacity that is already
  contracted/off-take-secured (would matter enormously for a renewable-energy-type capex profile) versus
  speculative build-out. **This is explicitly NOT a call Product can make** — routed to
  fm-fundamental-sanjay-kulkarni (forensic-gated entries) and equity-head-ananya-iyer's desk for a proper
  deep-dive before this name is used in any Principal-facing decision, with the CFO/PAT convergence question
  above as the single most useful thing that desk could check first.

### Business-model summary
**KB PENDING.** KPIGREEN is not one of the 25 names covered in `rnd/wave4/batch_A/B/C.json`. No business-model
narrative is asserted here beyond what the fundamentals legs above directly support — routed to
equity-head-ananya-iyer / analyst-industrials-rohan-deshmukh's desk (capex-cycle/renewables coverage) for a
proper KB entry, which is a precondition for resolving the capital-guzzler-vs-growth-inflection question above.

### Forensic screen — the flags ARE visible in the legs; connecting them
Per the CA-grade forensic framework, none of KPIGREEN's coarse leg readings can be escalated to a confirmed
HARD-VETO or HEAVY-PENALTY tier from this data alone — the framework is explicit that FILING-READ-ONLY
confirmation (auditor opinion, RPT terms, CARO clauses, ageing schedules) is required before any tier is
assigned, and none of that reading has been done here. What CAN honestly be said, connecting the visible legs
to the named framework items:
- **`bs_issuance` = −93.3** proxies toward **PT-01/PT-02** (ICDs / investments in unrelated entities) and the
  general capital-raising-pace concern in **RP-04** (rising related-party-transaction ratio as trend) — the
  framework tags the underlying `investments` metric_norm proxy as **PARTIAL DATA-SCREENABLE (coarse)**,
  counterparty identity remains FILING-READ-ONLY. **[DATA: FORENSIC_FRAMEWORK_CA.md, PT-01/PT-02 sections]**
- **`bs_asset_growth` = −97.0** proxies toward **PT-03** (capex gold-plating / CWIP that never capitalizes) —
  the framework flags `cwip` metric_norm level/trend vs total assets as an already-computable coarse base,
  with the genuinely new CA-grade layer (ageing breakdown, related-party vendor identity) FILING-READ-ONLY.
  **[DATA: FORENSIC_FRAMEWORK_CA.md, PT-03 section]**
- **`quality_cfo_pat` = −62.2** is the framework's own named cash-vs-reported-earnings authenticity leg
  (referenced directly in `FORENSIC_METHODS.md` line 92/136/154 as "the incumbent forensic leg... CFO/PAT
  authenticity") and is the closest thing in this dataset to **FA-01/FA-02**'s underlying concern (cash/
  receivables not backing reported profit) — though FA-01/FA-02 themselves require bank-confirmation or
  auditor-qualification evidence this dataset does not carry.
**Net**: three named, DATA-SCREENABLE forensic-adjacent proxies are ALL firing in the same (bad) direction
for KPIGREEN simultaneously — this is a genuine, connect-the-dots red flag worth a priority filing-read, but
it is **NOT** a confirmed fraud/HARD-VETO finding, and this scorecard does not represent it as one.

### Honest caveats — the two-engine disagreement (the sharpest of the three names in this batch)
| | Engine 1 (7-leg, validated construction, forward-test NOT graded) | Engine 2 (older per-horizon, UNVALIDATED) |
|---|---|---|
| Score | **−90.52** (decile 1/10, bottom decile) | **1M: −9 (HOLD, pup 0.44)**, 1Y: +12 (HOLD, pup 0.58), 5Y: +22 (HOLD, pup 0.64), MICRO: +10 (HOLD, pup 0.56) |
**[DATA: `results/universe_final_scores.parquet`, row `symbol==KPIGREEN`]**

This is a HARD disagreement, and the widest of the three names in this batch — Engine 1 places KPIGREEN in
the worst-ranked tenth of the entire scored universe; Engine 2 reads it as mildly POSITIVE at 1Y (+12) and
5Y (+22). **[INFERENCE]** One plausible reconciliation: Engine 1's extreme negative is dominated by the
balance-sheet/forensic-adjacent legs (issuance/asset-growth/CFO-PAT), which Engine 2's methodology — not
re-verified in this pass — may weight lightly or not carry at all, while Engine 2's positive read may instead
be picking up a growth/momentum-style signal consistent with the "growth-inflection" side of the open question
above. **This is a hypothesis, not a verified reconciliation** — it is exactly the kind of disagreement that
should be resolved by the quant desk BEFORE either number is used in a Principal decision, not smoothed over
by this product. If forced to choose which engine to trust more on FORENSIC grounds specifically: Engine 1's
underlying legs are the ones directly connected to named, CA-grade forensic proxies above; Engine 2's
methodology has not been re-examined for whether it even carries a forensic dimension at all.

### Regime context (not an absolute score — see note 3 above)
Sideways trend, normal volatility, narrow/large-cap-led breadth, risk-off appetite, Value leading factor
(as of 2026-02-27). A risk-off, narrow-breadth regime is generally the least forgiving backdrop for a
smaller, capex-heavy, currently-downtrending name — noted as context, not quantified into any score, and not
a substitute for the filing-read work the open question above actually requires.

---

## REUSABLE TEMPLATE — for any NIFTY-750 name

Copy this block per new ticker. Every bracketed field must be filled from a named file+row — if a data
source doesn't cover the name, write the honest gap (KB PENDING / not scored / not covered), never a filled-in
guess.

```
## SCORECARD — {TICKER} ({Company name if known, else "name not verified in this pass"})

### Validated 7-leg relative score
Score: {score} | Decile: {decile} of 10 | Legs present: {n_legs_present} of 7
[DATA: rnd/forward_test/scores_asof_20251205.parquet, row symbol=={TICKER}, as-of {date}]
-- if the ticker is ABSENT from this parquet or scored_as_true7==False: state "NOT SCORED — fewer than
   5 of 7 legs present" or "not in the 976-name scored panel" explicitly. Do not extrapolate a score.

| Leg | Value | Plain-English read |
|---|---|---|
| Value (earnings yield) | {subscore_value_EY} | {cheap/expensive vs universe, magnitude-qualified} |
| Momentum (residual, 12-1) | {subscore_mom_resid_plain} | {strong/weak, beta-adjusted} |
| Trend (65-day MA slope) | {subscore_trend_ma65_slope} | {up/down/flat medium-term trend} |
| Quality (QMJ) | {subscore_quality_QMJ} | {quality tier vs universe} |
| Balance-sheet: net issuance (-) | {subscore_bs_issuance} | {issuance-discipline read; remember sign-flipped, higher=better} |
| Balance-sheet: asset growth (-) | {subscore_bs_asset_growth} | {overinvestment-anomaly read; remember sign-flipped, higher=better} |
| Quality: CFO/PAT cash-conversion | {subscore_quality_cfo_pat} | {cash-authenticity read} |

**What's driving the {score}**: {name the 2-3 legs with the largest absolute magnitude and state whether
they push up or down; state the net}.

### Thesis (memo-craft voice, per rnd/wave4/MEMO_CRAFT.md — descriptive of the model, not a Product-desk call)
WHAT: {specific, checkable claim the leg pattern supports}.
WHY NOW: {the specific divergence/co-firing pattern that makes this timely, not a standing truism}.
MARGIN OF SAFETY: {which legs bound the downside, and how thin/thick that margin is}.
WHAT WOULD BREAK IT, ranked: (1) {fastest-acting/most diagnostic}; (2) {next}; (3) {explicitly state what is
NOT a kill signal on its own, per SageOne's documented mistake pattern in MEMO_CRAFT.md §3}.

### Business-model summary
{If ticker in rnd/wave4/batch_A.json / batch_B.json / batch_C.json: quote how_it_makes_money,
unit_economics, competitive_position fields verbatim with [DATA] tag.}
{Else: "KB PENDING." + name the sector analyst this should route to.}

### Forensic screen
{Check subscore_bs_issuance, subscore_bs_asset_growth, subscore_quality_cfo_pat for extreme values
(rule of thumb used in this batch: beyond ±60 is worth flagging, beyond ±85 is worth prioritizing).
Connect any extreme reading to the specific named item in rnd/forensic/FORENSIC_FRAMEWORK_CA.md (PT-01/
PT-02/PT-03/FA-01/FA-02/RP-04 etc.), tag DATA-SCREENABLE-coarse vs FILING-READ-ONLY per that document, and
state explicitly that no coarse proxy alone confirms a HARD-VETO tier.}
{If all three legs are unremarkable (roughly within ±40-50 and not all pointing the same direction):
"No forensic red-flag connection to raise — nothing showing in the coarse proxy, not a filing-confirmed
clean bill."}

### Honest caveats — the two-engine disagreement
| | Engine 1 (7-leg, forward-test NOT graded) | Engine 2 (older per-horizon, UNVALIDATED) |
|---|---|---|
| Score | {score} (decile {decile}/10) | 1M: {score_1M} ({band_1M}, pup {pup_1M}), 1Y: {score_1Y} ({band_1Y}, pup {pup_1Y}), 5Y: {score_5Y} ({band_5Y}, pup {pup_5Y}), MICRO: {score_MICRO} ({band_MICRO}, pup {pup_MICRO}) |
[DATA: results/universe_final_scores.parquet, row symbol=={TICKER}]
-- if ABSENT from this file: state "not covered by Engine 2" explicitly.
{State whether the two engines agree/disagree/sharply disagree. Never average or pick a favorite —
route reconciliation to quant-head-arjun-rao. Restate: pup is an uncalibrated logistic transform of the
score (src/scoring/universe_combine.py L95), never a real probability.}

### Regime context (NOT an absolute score — see "how to read this" note 3)
{Pull trend/volatility/breadth/risk_appetite/leading_factor from results/current_regime.json, cite its
as_of date(s) verbatim, state plainly that no absolute score exists to combine this with the relative
score above.}
```

---

**Filed by**: Tanvi Desai (Head of Product, E-026). Data verified against: `rnd/forward_test/scores_asof_20251205.parquet`
(976 rows), `results/universe_final_scores.parquet` (751 rows), `rnd/wave4/batch_A.json`/`batch_B.json`/`batch_C.json`
(25 names, none of the 3 covered), `rnd/forensic/FORENSIC_FRAMEWORK_CA.md`, `rnd/wave4/MEMO_CRAFT.md`,
`rnd/forward_test/FROZEN_SPEC.md`, `rnd/wave4/ABSOLUTE_SCORER_SPEC.md`, `results/current_regime.json`,
`src/scoring/universe_combine.py`. Open items routed: business-model KB (equity-head-ananya-iyer +
sector analysts), engine-disagreement reconciliation (quant-head-arjun-rao), KPIGREEN filing-read
(fm-fundamental-sanjay-kulkarni + equity-head-ananya-iyer).
