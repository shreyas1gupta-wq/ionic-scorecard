# QFRA-2 frozen model vs the firm's QFRA-1/QFRA-2 skills — reconciliation
**Date:** 2026-08-04 · **Desk:** DESK-20 (CIO office) · **Trigger:** Principal asked for a diff of the frozen
QFRA 2.0 engine against `qfra1-rerun`, `qfra2-rerun` and `ionic-wealth-complete` Part 3.

**Sources of record read:** `QFRA2_HANDOFF.md` (2026-08-04), `QFRA2_FINAL/01_MODEL/{MODEL_CARD,QFRA2_FRAMEWORK,BRAND}.md`,
`mr_x_framework/src/{config,final_model,churn_tracker}.py`, `outputs/recommendations/{QFRA2_current,QFRA2_recommendation_performance}.{csv,md}`,
`data/verified_navs_*.csv`.
**Model NOT modified. Engine NOT re-run** (a re-run overwrites `QFRA2_current.csv` and needs network — see §5).

Tags per `00_GOVERNANCE/EPISTEMIC_CONDUCT.md`: [DATA] measured/quoted · [INFERENCE] derived · [OPINION] judgment.

---

## 0. PRINCIPAL RULINGS (2026-08-04) — all applied to the skills same day

| On | Ruling | Applied |
|---|---|---|
| §2.5 MERIT vs CALIBRE | **CALIBRE is final** (7 pillars). MERIT is the superseded working name; `merit_grade` CSV column is a code artefact. Client-facing word stays "grade". | `qfra2-rerun`, `ionic-wealth-complete` |
| §2.7 cadence | **Apr-end / Oct-end is final.** The repo's Jun/Dec is the QFRA-2-**standalone** cadence; the firm runs QFRA-1 + QFRA-2 **CLUBBED on one calendar**, and the anchor choice is driven by QFRA-1 (6M capture windows are anchor-sensitive; QFRA-2's 3–5y windows are anchor-insensitive by construction, so it is not the discriminator). Not a conflict — different scope. **Do not "correct" back to Jun/Dec.** Evidence pack needed for a PPT → §6. | `qfra2-rerun` |
| §2.4 routing | **Index core stays with Large Cap and Mid Cap.** Large & Mid Cap is `ACTIVE`. Skill wording corrected; the frozen docs' ambiguous "index-core for Large/Mid" is not to be copied. | `qfra2-rerun` |
| §2.2 sell rule | Keep the change. | all three skills + `fund_ctx_adapter.py` docstrings |
| §2.3 non-independence | Keep the change. | all three skills + `fund_ctx_adapter.py` |
| §2.1, §2.6 | Not separately ruled; both are plain factual corrections, applied. | `ionic-wealth-complete`, `qfra2-rerun` |

**Not changed** (needs CEO+CIO under D-025, or a go-ahead): the adapter Sell rule itself (§7), and removing
the fuzzy matching from `fund_ctx_adapter.py` (§8). Both are now documented in-code with WARNING blocks.

---

## 1. Measured facts that reframe everything below

### 1a. The eligible universe is 5–9 funds per deployed category, not 40–60
[DATA] Replicating the engine's own eligibility path (`final_model.py:92-102`: drop Regular-plan
columns → require ≥756 trading days of returns) against `data/verified_navs_*.csv`:

| Category | Deployed? | NAV cols | Direct-plan | Pass ≥3y | AUM floor (cr) |
|---|---|---|---|---|---|
| large | yes | 26 | 8 | **8** | 500 |
| largemid | yes | 22 | 5 | **5** | 300 |
| mid | yes | 26 | 9 | **8** | 300 |
| flexi | yes | 35 | 6 | **6** | 300 |
| multi | yes | 21 | 5 | **5** | 200 |
| small | yes | 25 | 7 | **6** | 200 |
| focused | **no** | 30 | 30 | **30** | 150 |
| value | **no** | 31 | 31 | **31** | 150 |

Independently confirmed by inverting the published `qfra_score` ladder (`score = round(rank(eff, pct)×100)`):
implied N = 8 / 5 / 8 / 6 / 5 / 6 / 33 / 33. Both methods agree.

Consequences:
- `QFRA2_HANDOFF.md` §1 states eligibility leaves "**~40-60 funds**" per category. [DATA] Wrong by ~7× for
  every deployed category. Handoff should be corrected.
- "top-5 shortlist → final-2" is **the entire eligible field** for largemid and multi (5 of 5), and
  5-of-6 for flexi and small. [INFERENCE] The shortlist stage is close to a no-op in four of six
  deployed categories.
- [INFERENCE] The binding constraint is NAV **data coverage**, not the gates: the Direct-plan filter cuts
  26→8, 22→5, 35→6, 21→5, 25→7 for the deployed cats but 30→30 / 31→31 for focused/value, i.e. the
  focused/value NAV files were assembled Direct-only while the others are mostly Regular-plan columns
  that get dropped. Fixing NAV coverage would materially widen the deployed universe.

### 1b. QFRA Score is NOT comparable across categories
[DATA] 80/100 in Large & Mid = rank 2 of 5. 88/100 in Focused = rank 4 of 33. Same number, different
meaning. Neither the frozen docs nor any of our skills warn about this, and the deck renders it as a
single "fund score /100".

### 1c. The AUM capacity floor is unenforced on 40% of published picks
[DATA] `AUM_Cr` blank on 12 of 40 rows in `QFRA2_current.csv` — including **0 of 5 Focused and 0 of 5
Value/Contra**. The gate cannot bite where AUM is missing. This is handoff TODO #3; the magnitude was
not stated there. [INFERENCE] It is also the mechanism behind §1a's asymmetry surviving into the output.

### 1d. The DEPLOYED book's realized alpha is ~zero — the headline belongs to the RAW book
[DATA] From the engine's own `QFRA2_recommendation_performance.md` (2018-H1..2024-H2, active cats pooled):

| Book | 1Y med α | 1Y win | 3Y med α | 3Y win | 5Y med α | 5Y win | churn/yr |
|---|---|---|---|---|---|---|---|
| **HELD (deployed, τ-hysteresis)** | **−0.09** | 49.7% | **+0.09** | 51.0% | **+0.20** | 51.7% | 3.9 |
| RAW model top-2 (no hysteresis) | +1.62 | 57.2% | +0.56 | 56.7% | +0.85 | 55.9% | 9.8 |

The marketed "**+0.48%/yr, 95% CI [+0.06,+1.05], P(>0)=98.8%**" is a *selection-skill* measure consistent
with the RAW row. The book a client actually holds is the HELD row: **+0.09%/yr at 3Y, win 51.0%**.
[INFERENCE] τ-hysteresis — the feature that makes the product operationally and tax-attractive
(3.9 changes/yr) — absorbs essentially the whole measured edge. The performance file says this plainly
("the low-churn book gives up ~0.5%/yr at 3-5Y"); `MODEL_CARD.md` does not.

[DATA] HELD-book 3Y median α is negative in 5 of 8 categories: Large −0.25, Large&Mid −0.38, Mid −3.16,
Multi −2.35, Small −1.34. Positive: Flexi +2.16, **Focused +0.99, Value/Contra +0.73**.
[OPINION] Worth the CEO's attention: the deployment scope **drops the two categories whose held book was
positive at both 3Y and 5Y** (Focused, Value) and keeps Multi and Small, which were not. The stated
reasons for dropping them (§5 of the handoff: no differentiated median-alpha edge vs a blind pick) are
about *edge over random*, not about *realized alpha* — both are legitimate lenses, but the decision memo
should say which one it used.

---

## 2. Defects in OUR skills (fix these)

| # | Our skill says | Frozen reality | Sev |
|---|---|---|---|
| 1 | `ionic-wealth-complete`: QFRA-2 source = "`QFRA2_current.csv` (**40 curated funds only**)"; coverage = "focused + value/contra that QFRA-1 has no sheet for"; anything else gets "needs a QFRA-2 scoring run" | That file is 8 cats × top-5 = 40 **rows**, a publication slice. The engine ranks **99 Direct-plan funds** across 8 cats (§1a). And Focused/Value are **excluded from deployment** — the opposite of "that's what QFRA-2 is for". | **Critical** — already caused 6 wrong scores in a shipped client deck (§3) |
| 2 | Both skills: "a fund Sell requires **BOTH frameworks independently at Sell**" | QFRA-2 has **no Sell verdict**. Verdicts are `ACTIVE` / `INDEX CORE (+ satellites)`. It is a top-2 *selection* engine for the next 3–5y. The rule is unsatisfiable as written. | **Critical** |
| 3 | Both skills present the two frameworks as **independent** confirmation | QFRA-1's ranking metric (6M total capture = up-capture ÷ down-capture) **is** QFRA-2's `_cap6` (`final_model.py:105-107`), which carries **w=0.30** in the final blend; 3y down-capture is a further 1/6 of base (≈10.5% of the blend). Capture-family ≈ **40% of the QFRA-2 score**. | **High** |
| 4 | `qfra2-rerun` §After-running: "Note **Large & Mid Cap** run an index core + satellites" | Engine routes **Large Cap** and **Mid Cap** to `INDEX CORE`; **Large & Mid Cap is `ACTIVE`, conviction High, rank-1 = 100/A**. We named the wrong category. Root cause: the source docs' phrase "index-core for Large/Mid" is ambiguous and we read it as the Large&Mid category — `QFRA2_recommendation_performance.md`'s own footer makes the same slip while its table contradicts it. | **High** — inverts the advice for 2 categories |
| 5 | Both skills use **MERIT** (5 pillars) | `BRAND.md` (locked) renames it **CALIBRE** and expands to **7 pillars** (Conviction/Alpha/Leadership/Integrity/Benchmark/Resilience/Edge). Code + CSV column are still `merit_grade`; `MODEL_CARD.md` + `QFRA2_FRAMEWORK.md` still say MERIT/5-pillar. Docs disagree with each other and with code. | Medium |
| 6 | `ionic-wealth-complete`: "QFRA-1 category cutoffs: Large/Multi = 90%, Mid = 80%" | `qfra1-rerun` (verified against the live workbook) has **large 0.9, mid 0.8, multi 0.9, flexi/small/largemid 1.0**. `ionic-wealth-complete` omits flexi/small/largemid entirely — an analyst reading only that skill applies no cutoff to 3 of 6 categories. | Medium |
| 7 | Our skills carry the **Apr-end/Oct-end** anchor (Principal 2026-07-26) | `config.py` comment still says "Deployment is 2/yr (**Jun/Dec**)". Our skills are ahead; the repo is stale. A re-run from the repo will not reflect the anchor change. | Low |

**Where our skills are RIGHT and the handoff is wrong** — do not "correct" these back:
- `qfra2-rerun`'s 2026-07-27 note: `final_model.py:98` `if len(fr) < C.MIN_HISTORY_D: continue` is a **hard
  3-year gate**. [DATA] Verified. The handoff's "<3y watchlist" tier and `config.py`'s own comment ("it is
  NOT a hard exclusion... newer funds ride the qualitative track at capped conviction") are both wrong;
  `gates.py history_tier()`'s <3y branch is unreachable.
- The "~40-60 funds" figure (§1a).

---

## 3. This already reached a client deliverable (Talaulikar NDPMS deck)

[DATA] `pr_template/data/talaulikar_family.py` `_QFRA2_SCORES` holds **24 entries from three different
provenances in one client-facing field** (`qfra` + `merit`, rendered as "fund score /100" + grade):
8 real engine scores · 3 web-researched desk estimates · 13 QFRA-1 percentile ranks.

[DATA] **6 of the 16 non-engine scores had a real frozen-engine score available** and got a substitute:

| Deck fund | My substitute | Present in engine universe as |
|---|---|---|
| HDFC Focused Fund | 90 / A (web estimate) | `HDFC Focused Fund - Growth Option - Direct Plan` (focused, N=30) |
| ICICI Prudential Focused Equity Fund | 78 / B (web estimate) | `ICICI Prudential Focused Equity Fund` (focused) |
| Invesco India Focused Fund | 72 / B (web estimate) | `Invesco India Focused Fund` (focused) |
| Aditya Birla Sun Life Flexi Cap Fund | 54 / C (QFRA-1 pctile) | `Aditya Birla SL Flexi Cap Fund(G)` (flexi, N=6) |
| ICICI Prudential Large Cap Fund | 87 / A (QFRA-1 pctile) | `ICICI Pru Bluechip Fund(G)` (large) — rename is in our OWN `lib/mf_mapping.py` `SCHEME_RENAMES` |
| Kotak Midcap Fund | 71 / B (QFRA-1 pctile) | `Kotak Emerging Equity Fund(G)` (mid) — rename also in our own `SCHEME_RENAMES` |

The other 10 genuinely have no engine coverage (Motilal Midcap, HDFC L&M, DSP L&M, Bandhan L&M, quant
Large Cap, Canara Robeco Multicap, Invesco Small Cap, Tata Small Cap, HDFC Small Cap, Kotak Multicap).

**Root cause:** defect §2.1 — believing coverage was 40 named funds, any held fund absent from
`QFRA2_current.csv` was treated as uncovered. The two rename cases are the sharpest: the mapping table
that would have resolved them was built in this same project and the fund-scoring path never consulted it
against the QFRA-2 universe.

**Second defect:** `score_is_estimate` is wired for **equities only** (`talaulikar_family.py:1739` →
`modules/sell_cards.py:58,90`). There is no fund-side equivalent, so the deck does **not** disclose which
fund scores are engine output vs estimate. Three provenances render identically.

---

## 4. Contradictions inside the frozen docs (not our doing — but our deliverables quote them)

1. [DATA] `MODEL_CARD.md`: "edge strongest in **Small (+2.86%/yr alpha, 76% hit)**". Per handoff §5,
   **+2.86 is Large & Mid's 3Y edge**; Small's 3Y edge is **+0.17** (a blind pick wins nearly as often)
   and 76% is Small's 5Y *win rate*. The handoff explicitly corrects this. MODEL_CARD is the doc that
   declares itself "the single source of truth for every QFRA 2.0 deliverable" — so any deck or report
   built from it inherits a category-transposed edge claim.
2. [DATA] Jan-2025 live alpha: `MODEL_CARD.md` says **+2.63%/yr**; `QFRA2_FRAMEWORK.md` and the engine's
   own performance file say **+0.87%/yr** (all cats), ~+1.9% active.
3. [DATA] `MODEL_CARD.md` claims "**+4%/yr net-of-tax vs naive** in backtest". Not present in
   `QFRA2_recommendation_performance.{csv,md}`. Unsourced as far as the outputs go.
4. [DATA] HELD-vs-RAW conflation (§1d) — the biggest one.
5. [DATA] `config.py:123` comment says the live churn rule is **TAU=0.10**; `churn_tracker.py:44` is
   **TAU=0.15** ("Raised 0.10->0.15 (2026)"). Docs/handoff/MODEL_CARD all say 0.15. Stale comment only,
   no model impact — but it is the kind of line someone quotes.
6. [DATA] "**~2.8%/yr de-inflation**" from the Direct+TRI corrections appears in `MODEL_CARD.md`'s
   changelog and `BRAND.md` point 1. Handoff §9 retracts it: "roughly offset on alpha (~net 0) — the
   earlier narrative was **overstated**; don't repeat it." Two locked docs still repeat it.
7. [DATA] `HML = Value30 − Quality30` is collinear with QUAL by construction (handoff §3). Left as-is
   because α-invariant. [OPINION] Fine for α, but it means the published "quality-beta" leg — which is
   1 of 6 base signals **and** 1 of 3 SENTINEL flags — is estimated from a partly-collinear design. Worth
   one honest line in any methodology page, since quality-beta drives a veto.

---

## 5. Recommended actions (none taken yet — all need a go-ahead)

| # | Action | Cost | Blocker |
|---|---|---|---|
| 1 | Fix `ionic-wealth-complete` Part 3 + `qfra2-rerun` for defects §2.1–§2.6 | small | none |
| 2 | Extract real engine scores for the 6 Talaulikar funds in §3, replace the substitutes, add a fund-side `score_is_estimate` + provenance label | medium | needs a **read-only** engine run; snapshot `QFRA2_current.csv` first (handoff §9), network required for the TRI build |
| 3 | Re-issue the Talaulikar deck's fund pages after #2 | medium | Principal sign-off — it is a shipped client artifact |
| 4 | Replace the "both frameworks agree" rule with one that is satisfiable and states the 40% shared-signal overlap | small | CEO+CIO joint (D-025: it is a standard) |
| 5 | Correct the handoff (§1a "40-60 funds", "<3y watchlist") and `MODEL_CARD.md` (§4.1–4.3, 4.6) | small | model owner's call; these are docs, not the frozen model |
| 6 | Put HELD-book alpha next to the +0.48% headline in every QFRA-2 deliverable | small | [OPINION] non-negotiable for honesty; the PAC deck and QFRA2 committee deck both currently quote the raw figure alone |
| 7 | Close the NAV coverage gap for the 6 deployed categories (§1a) — the single highest-value data fix | large | data feed work; would widen 5-9 funds/cat toward the focused/value 30-31 |

**Not recommended:** any change to scoring, weights, screens, or TAU. The model is frozen and every tested
retune was rejected on the OOS bar (handoff §7).

---

## 6. Apr/Oct cadence — PPT evidence pack (Principal asked for this 2026-08-04)

Source: `04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md`.
Chart: `09_PRODUCT/scripts/chart_anchor_pair.py` → `pr_template/out/anchor_pair_evidence.png`.

**Method line for the slide:** all six possible 6-month month-pairs replayed through QFRA-1's *live*
decision logic (6M downside-capture cutoff → total-capture rank → BUY top-3; SELL = trailing-12M
excess < 0 AND quadrant-4) at every month-end anchor Jan-2012 → Jul-2024, on all six category sheets,
scored on forward 6M excess vs the category benchmark. **906 formations, ~150 per pair.**

| Pair | BUY median | BUY trim-mean | Buy−Sell spread (med) | Hit rate | n |
|---|---|---|---|---|---|
| **Apr / Oct** | **+2.59%** | **+2.59%** | +2.31% | **66%** | 150 |
| Feb / Aug | +2.34% | +2.04% | +2.23% | 58% | 150 |
| Jun / Dec *(prior)* | +2.22% | +2.34% | +2.13% | **66%** | 150 |
| May / Nov | +1.94% | +1.98% | +1.38% | 58% | 150 |
| Mar / Sep | +1.82% | +2.10% | +1.90% | 55% | 150 |
| Jan / Jul | +1.31% | +1.77% | +1.77% | 58% | 156 |

**Anchor = month-END** (`freq="ME"`, window `(t−6m, t]`). "Apr/Oct" = data through **30-Apr** and
**31-Oct**. It has never meant month-start.

**UNTRIMMED RESULTS ADDED 2026-08-04 — and they retract two claims.** Full tables in the study doc's
extension section; `anchor_pair_study_ext.py`, 906 formations reconciled exactly.

| Pair | BUY median | **BUY plain mean** | BUY 10%-trim | Hit |
|---|---|---|---|---|
| **Apr / Oct** | **+2.59%** | +2.62% | **+2.59%** | **66.0%** |
| Feb / Aug | +2.34% | +1.99% | +2.04% | 58.0% |
| Jun / Dec | +2.22% | **+2.65%** | +2.34% | **66.0%** |
| May / Nov | +1.94% | +1.94% | +1.98% | 58.0% |
| Mar / Sep | +1.82% | +2.08% | +2.10% | 54.7% |
| Jan / Jul | +1.31% | +2.20% | +1.77% | 57.7% |

**Do not say (both were in my earlier draft, both are wrong):**
- ~~"Apr/Oct is first on every point estimate"~~ — **Jun/Dec wins the plain untrimmed mean, +2.65% vs
  +2.62%.** A 0.03pp gap is noise, but the sentence is false.
- ~~"Jan/Jul is near the bottom on every metric"~~ — last on the median (+1.31%) but **3rd on the plain
  mean (+2.20%)**. Its typical formation is poor while a few big winners carry the average.

**The four points to make, in this order:**
1. **We tested all six pairs, not just the convenient one.** Apr/Oct leads on the median (+2.59%) and
   the trimmed mean (+2.59%).
2. **Two anchors are good and four are mediocre — and this is the claim that survives untrimming.**
   Hit rate has no trimming parameter: Apr/Oct and Jun/Dec both **66%**, the other four **54.7–58%**.
   ~8pp, and it is the load-bearing evidence.
3. **The calendar-intuitive pair is the worst in the typical case.** Jan/Jul — fiscal half-years, the
   default anyone reaches for — is last on the median, **−1.28pp vs Apr/Oct**.
4. **Theory agrees, independently of the backtest.** Apr-end reads prices that have digested the
   March-quarter (full-year) results; Oct-end reads post-September-quarter/H1. Jan/Jul sits
   mid-digestion — Dec-quarter results land mid-Jan to Feb, Jun-quarter mid-Jul to Aug — so the 6M
   capture window closes exactly as new information lands.

**Say this out loud on the slide (do not let PAC find it first):** Apr/Oct and Jun/Dec are a **statistical
tie** — n≈150/pair with cross-category correlation, and they split the three central measures (Apr/Oct
takes median + trimmed, Jun/Dec takes the raw mean). The desk recommended keeping Jun/Dec on tie-break
grounds; the Principal ruled Apr/Oct. The defensible claim: *"we tested all six, the top two are a tie,
Apr/Oct wins on the typical formation while Jun/Dec's edge is outlier-carried, and the intuitive default
was measurably the worst in the typical case."* **Not** *"Apr/Oct is proven superior."*

**Smallcap-only (Principal asked): do NOT put it in the deck.** Apr/Oct is **3rd of 6** on the smallcap
median (+3.49%) and 4th on the plain mean (+2.80%), and Jun/Dec beats it on hit rate (76% vs 72%). n=25
per pair — nothing is meaningful. Smallcap's real message is that *every* anchor works there (+1.08% to
+3.94% median, 68–76% hit), a rising tide, consistent with QFRA-2's own finding that a blind pick also
wins in Small. The pooled 906-formation result is the only defensible anchor evidence.

**Why QFRA-2 doesn't drive the anchor choice** (expect this question, it is also the answer to why our
cadence differs from the source repo's Jun/Dec): QFRA-2 estimates over 3–5 year windows and is
anchor-insensitive by construction. QFRA-1's 6-month capture windows are anchor-sensitive. Since the firm
runs both frameworks clubbed on one calendar, QFRA-1 is the discriminator and sets the date for both.

---

## 7. How a "QFRA-2 Sell" is actually produced today

`09_PRODUCT/scripts/fund_ctx_adapter.py:96` (feeds `call_lt` → `merge_calls()` at :120):
```python
call = "Sell" if (loser_flags or 0) > 0 or qfra_score < 40 else "Hold"
```
[DATA] This is **ours**, not the engine's. The frozen engine emits `ACTIVE` / `INDEX CORE (+ satellites)`
and nothing else. Status per `qfra2-rerun`: **UNVALIDATED, never backtested, not CEO+CIO ratified.**

**Defect 1 — it sells the engine's own recommendations.** `loser_flags > 0` fires on **Franklin India
Equity Advantage Fund(G)**: rank **2** in Large & Mid Cap, QFRA score **80**, grade **A**, conviction
**High**, verdict **ACTIVE** — a published final-2 pick. 15 of the 40 published rows carry ≥1 flag.
Cause: SENTINEL is a shortlist-refinement screen *inside* selection (`eff = blend − loser`, prefer
loser-clean into the top-5). A flag down-ranks a **candidate**; it was never a verdict on a holding.

**Defect 2 — `qfra_score < 40` sells a fixed fraction by construction.** The score is
`round(rank(eff, pct=True) × 100)`, a within-category rank: N=5 → bottom 20%, N=8 → bottom 37%, N=30 →
bottom 40%. The Sell *rate* is an artefact of category size and of whether SENTINEL runs (**Mid and Value
have SENTINEL OFF by design, so leg 1 can essentially never fire there**), and carries no information
about whether the fund beats its benchmark.

**Did this reach a client?** [DATA] **No.** Every fund Sell in the Talaulikar deck is sourced from either
(a) liquid/debt/sectoral out-of-scope, (b) a directed liquidity call, or (c) QFRA-1 — e.g. HDFC Small Cap:
"Ranks 19th of 29 in its category on capture ratio — our short-term framework independently flags this
fund for exit." No Sell cites the long-term leg. But the rule **is** live in code on `client_intake.py`'s
default path, so the next client built without hand-set fund calls would exercise it.

### RESOLVED — Principal ruling 2026-08-04: **do A + B + C**, sell basis = QFRA-1. IMPLEMENTED.

New rule, "**originate and veto**" (`fund_ctx_adapter.py:merge_calls()`):
- **A — `loser_flags` RETIRED** from the sell path entirely. It survives as a disclosure field only.
- **B — the sell BASIS is QFRA-1**, the only framework with a Sell verdict and a replayed backtest.
  `qfra_score < 40` is gone as a sell trigger.
- **C — QFRA-2 can never originate a Sell.** Its contribution is a stance: **CALIBRE A or B grade
  VETOES** a QFRA-1 Sell → Hold. C/D grades do not veto.
- **Contradiction surfacing (the Principal's explicit requirement; NEXT_WEEK_QUEUE item 1d, now built):**
  a QFRA-1 Sell against a QFRA-2 A/B grade returns a `contradiction` string that is pushed into BOTH the
  dedicated `contradictions` list and `gaps`. `build_fund_entries()` now returns a **3-tuple**
  `(entries, gaps, contradictions)` so a caller cannot lose it. The reverse case (QFRA-1 Buy vs a D
  grade) is logged too. Nothing resolves silently.
- A QFRA-1 Sell with **no** QFRA-2 coverage still sells, but raises a `SINGLE-FRAMEWORK SELL` flag
  requiring FM sign-off.

Verified: `merge_calls` 9/9 cases pass; on real CSV data Franklin India Equity Advantage
(rank 2, score 80, grade A, ACTIVE) now returns **Hold + CONTRADICTION** where the old rule returned Sell.

**But the premise behind B needs correcting.** [DATA] The Principal's basis for leaning on QFRA-1 was
that its Sell is backtested. Measured 2026-08-04 on the same 906 formations: **the BUY leg is strong and
the SELL leg is weak.** `sell_hit` (share of formations where the sold cohort went on to underperform) is
**below 50% in all six anchor pairs**; Apr/Oct pooled is 49.3% with a median of −0.57% and a plain mean of
−0.13%. On three of six anchors the sold cohort's mean excess was **positive**. Smallcap is the exception
(median −1.05%, mean −0.92%, trimmed −1.72%, hit 44% — rarely right but very right when it is).

[OPINION] So the rule is now structurally sound but its originating leg is a modest signal. A QFRA-1 Sell
should stand on the analyst's stated reason with the capture statistic as *support* — never on "the
backtest says sell". Written into `merge_calls()`'s docstring and both QFRA skills. The queued sell-rule
backtest (NEXT_WEEK_QUEUE item 1) should now be re-scoped: the question is no longer "does the QFRA-2
proxy work" but "can any absolute measure in the QFRA-2 output (`hit_3y_pct`, trailing excess) beat
QFRA-1's coin-flip sell leg".

---

## 8. Standing-order violation found in passing

[DATA] `fund_ctx_adapter.py` still fuzzy-matches — `_fuzzy_get()` (:64-65) and `qfra2_lookup()` (:86-95),
both longest-prefix at an 85%-of-shorter-name bar. Principal 2026-08-01: *"REMOVE FUZZY ENTIRELY ALWAYS USE
SONNET AND ONE FUND AT A TIME MAPPING GOOGLE SEARCH AND LOGICALLY EVALUATION ONLY."* `client_intake.py` was
converted; this path was missed. Fix = normalized-exact + `SCHEME_RENAMES` only, everything else to the
gaps list for a one-fund-at-a-time Sonnet pass. **Not done** — it is on the client-intake path and needs a
go-ahead. Documented in-code meanwhile.
