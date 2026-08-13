# CALIBRE pillar fix — Integrity + Conviction (QFRA 2.0 PAC deck, slide 8)
**Author:** Tanvi Desai (Head of Product) · **Date:** 2026-08-04 · **For:** Principal, ahead of PAC committee
**Source repo (read-only, not modified):** `Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\` — BRAND.md, MODEL_SPEC.md, MERIT_FRAMEWORK.md, `mr_x_framework\src\*`

---

## 1. Root cause of the Integrity complaint [DATA]

CALIBRE (7-pillar) is a rename of the earlier **MERIT** (5-pillar) framework — confirmed in `BRAND.md`:
*"CALIBRE supersedes the earlier MERIT working name... propagation to the engine output label is a pending rename cascade."*

MERIT's own pillar was never bare "Integrity" — its full name in `MERIT_FRAMEWORK.md` is **"I — Integrity of portfolio"**, glossed as *"what the fund actually owns now."* When CALIBRE's deck copy (`qfra2_deck_v3.py:137`, `qfra2_deck_v4.py:197`) shortened this to bare **"Integrity"**, it dropped the qualifier "of portfolio" that was doing the disambiguating work. That single dropped phrase is the whole bug: "Integrity of portfolio" (= portfolio construction quality) reads fine; "Integrity" alone reads as stewardship/honesty, which is not what the five listed metrics measure. The Principal's objection is correct and traces to an incomplete rename, not a new judgment call.

## 2. What the engine actually evidences, item by item

| Slide item | Status | Evidence |
|---|---|---|
| **Active Share** | **[DATA] computed**, but data-gated | `holdings_metrics.py:333` `active_share(fund, category)` = `0.5·Σ\|w_fund,i − w_bench,i\|`. Returns NaN and the check is skipped ("no holdings/bench data (skip)") when holdings/benchmark-constituent data is absent — `stage2_overlay.py:151` calls this "no-op until data exists." |
| **Concentration (top-10 / HHI)** | **[DATA] computed**, same data-gating | `holdings_metrics.py:364` `concentration(fund)` → `{top10_wt, hhi}` from real holdings weights. Same NaN/skip behavior as Active Share. |
| **Return gap** (KSZ-2008: actual return vs. return implied by lagged disclosed holdings) | **[DATA] computed**, same data-gating | `holdings_metrics.py:428` `return_gap(fund, category)`. Not on the current slide at all — this is the genuine academic "disclosure honesty" metric and is sitting unused. |
| **P/E discipline** | **NOT what it claims to be** | `fund_pe_proxy.py` computes a *NAV-trend valuation-extension z-score* (is the price stretched vs its own 3y trend), explicitly self-documented: *"this is a PRICE-based proxy... NOT fundamental portfolio P/E. True portfolio P/E needs a stock-fundamentals feed via the AI/holdings agent."* No fundamental P/E is computed anywhere in `src`. Not confirmed wired into the live `final_model.py` scoring path — reads as a standalone research probe. |
| **ROCE quality** | **[OPINION] analyst/AI judgment, not a coded formula** | `PARAMETERS.md` item 7 tags this `[H]` with note *"AI: parse latest holdings → stock fundamentals"* — no ROCE-computation function found in `src`. `qfra2_report.py:102` calls the whole holdings/P-E/ROCE bundle *"currently data-gated."* |
| **No style-drift / true-to-label** | **[DATA] partially computed** | `PARAMETERS.md` item 10: holdings cap/style tracked over time (computed when holdings data exists) + a mechanical SEBI-recategorization override mentioned in `FINAL_MODEL.md:67`. |
| **PM-exit** | **[DATA] computed, mechanical** | `manager_feed.py` `pm_exit_flag()` string-compares scraped manager name vs. prior cycle; explicit rule "never invent a manager name... unknown is reported as such." Depends on a successful external scrape. Currently sits under **Leadership**, not Integrity — left there (see §4). |
| **TER / fee fairness** | **[DATA] real, reliably available** | AMFI/factsheet field, used at the Stage-1 eligibility gate (`MODEL_SPEC.md` A7; `qfra2_deck_v3.py:158` "ELIGIBILITY... TER/label/liquidity"). Unlike holdings data, this is *not* patchy — it exists for every fund. |
| Portfolio turnover (fund's own buy/sell activity — the "no window-dressing" candidate) | **Not evidenced** | Grepped `src` for `turnover`: the only computed turnover is the **model's own recommendation churn** (tau-hysteresis, ~3-4 swaps/yr) — a different thing entirely. No fund-level turnover/window-dressing check exists. Ruled out. |
| SIP-investor-equal-treatment | **Not evidenced** | No reference anywhere in `src` or the spec docs. Ruled out. |

**Bottom line on evidence:** of the five items currently on the slide, three are genuinely computed formulas (Active Share, concentration, style-drift) but gated on holdings-data coverage that is often absent today; one (P/E discipline) is mislabeled — the code computes something else; one (ROCE) has no coded formula at all today, only an AI-agent-judgment intent. A pillar cannot honestly claim to "measure" all five as if they were equally hard numbers.

## 3. Proposed fix

### Integrity (I) — redefined around what genuinely means integrity AND is evidenced
**New one-liner:** *"Fee fairness versus category, and holdings that don't quietly drift."*
- **Fee fairness** = TER vs category, Direct-plan basis — [DATA], always available, already a Stage-1 gate input.
- **Holdings that don't quietly drift** = style-drift (holdings cap/style over time) + the SEBI-recategorization mechanical flag — [DATA] when holdings data exists, [DATA] mechanical otherwise. (Return gap is the natural next addition here if/when holdings coverage improves — it is coded and unused today; flagging as a roadmap item, not claiming it now.)
- This is deliberately distinct from Leadership's "true to mandate" (a people/governance promise) — Integrity's version is about the **portfolio itself** not silently becoming something other than what it discloses. `true-to-label` / `true-to-mandate` is **left in Leadership, unchanged** — nothing needs to backfill it there since it was never moved out.

### Displaced content — where it goes (acronym stays C-A-L-I-B-R-E, all 7 words unchanged)
- **Active Share → folds into Alpha.** The firm's own `PARAMETERS.md` item 5 already frames this correctly: *"genuine activeness is a precondition for alpha (Cremers-Petajisto)."* A closet indexer's alpha claim isn't credible — Active Share becomes part of Alpha's existing "gated" language, not a new concept.
- **Concentration (HHI/top-10) + ROCE holdings quality → fold into Resilience.** Both are about whether the *current book* can survive/compound going forward (MERIT's own language: "repeatable process + survives bad regimes"), pairing naturally with Resilience's existing backward-looking down-capture/max-DD.
- **P/E "discipline" → dropped from client-facing pillar language.** [OPINION] It is not fundamental P/E today; relocating a mislabeled metric would just move the dishonesty. If/when a real fundamentals-based valuation signal is built and confirmed live-wired, it belongs in Alpha (it's tested as a forward-alpha predictor in `fund_pe_proxy.py`, not a construction-quality check).

### Conviction (C) — plain-English rewrite
Old: *"within-category rank, clamped to track-record tier"* (jargon: "clamped," "tier").
**New one-liner:** *"How strongly we back a fund, capped when its record is short."*
Meaning preserved exactly: the call's strength = the fund's rank inside its own category; a short track record puts a ceiling on how much conviction we're willing to express, per `MODEL_SPEC.md` Part E1's tiered conviction ceiling (High / Medium / Watchlist-Low by track-record band).

## 4. Final seven one-liners (8-12 words each, plain English, no acronym soup, no em-dashes)

| Letter | Pillar | New one-liner |
|---|---|---|
| C | Conviction | How strongly we back a fund, capped when its record is short. |
| A | Alpha | Factor alpha and appraisal ratio, gated on genuine activeness, shrunk. |
| L | Leadership | Manager tenure, key-person exit risk, AMC governance, true to mandate. |
| I | Integrity | Fee fairness versus category, and holdings that don't quietly drift. |
| B | Benchmark | Win rate and up/down capture versus TRI, fairly measured. |
| R | Resilience | Down-capture, drawdown, alpha stability, concentration, and holdings quality. |
| E | Edge | A validated edge, cost-efficient and clean of red flags. |

## 5. Open items for the owning desks (not answered here, routed)
- Whether to actually build return-gap into the client-facing Integrity number (currently coded, unused, data-gated) — Quant Head (Arjun Rao) / Data Officer (Kavya Reddy) call on holdings-coverage investment.
- Whether `fund_pe_proxy.py` is live-wired into `final_model.py`'s production score — not traced here; flag to Quant Head before any future re-introduction of a valuation pillar.
- This memo does not touch the PPTX file itself — Manoj Pillai or the deck owner applies the copy change.

---

## 6. REVISION 1 — 2026-08-04 (same session) — Principal rejected I and C; other five approved and NOT touched below

Principal reviewed §4. **Alpha, Leadership, Benchmark, Resilience, Edge stand exactly as written — out of scope for this revision.** Integrity and Conviction rebuilt per his explicit sequencing.

### 6a. What integrity actually means — established BEFORE re-checking data [OPINION, definitional]
In stewardship/fiduciary usage: **integrity means acting honestly and consistently in the unit-holder's interest — doing what was promised, not extracting value at the investor's expense, and disclosing the truth even when it's unflattering.** That is the bar; the engine's data does not get to redefine it.

### 6b. Re-checked against that definition (not against what we happen to compute)
| Candidate | Speaks to the definition? | Status |
|---|---|---|
| TER vs category (fee fairness) | Yes — "not extracting value at the investor's expense" | **[DATA]** real, always available, fund-varying (unchanged from §3) |
| True-to-label / style-drift | Yes — "doing what was promised" | [DATA] only when holdings data exists (often NaN); also substantively duplicates Leadership's "true to mandate" |
| Direct-plan NAV + TRI-not-PRI basis | Yes — refusing the flattering basis is "truth even when unflattering" | **[DATA]** real (MODEL_SPEC.md A1) — but this is **our** honesty, not the fund's |
| NAV identity check + point-in-time enforcement | Yes — same test, applied to our own inputs | **[DATA]** real (MODEL_SPEC.md Part D step 0: NAV must correlate >0.98 with known history before use) — again **our** process |
| Stage-2 overlay is one-directional: veto/trim only, never inflate | Yes — we cannot use judgment to flatter a fund we like | **[DATA]** real, confirmed in `stage2_overlay.py`'s own docstring twice — again **our** process |
| Return gap (KSZ-2008) | Yes, in principle | [DATA] coded, unused, data-gated — still a roadmap item, not claimed now (unchanged from §2) |
| Portfolio turnover / SIP-fairness | — | Still not evidenced (unchanged from §2) |

**Honest pattern:** almost everything that actually clears this definition today is a property of **our own process**, not the fund. Fee fairness is the one fund-varying exception.

### 6c. Fund-facing vs "our own integrity" — argued both ways

**For the reframe:** our-process integrity is the best-evidenced content on the whole slide — Direct-plan, TRI, NAV-identity, point-in-time, veto-only overlay are all [DATA], none judgment, none holdings-data-gated. Genuine differentiator, matches the existing "Honest by design" alt tagline (BRAND.md).

**Against:** every other CALIBRE letter scores the FUND and varies fund-to-fund. "Our methodology is honest" is a constant — identical for every fund — so it cannot produce a per-fund CALIBRE grade contribution the way Alpha/Resilience do. It also risks reading at PAC as "we couldn't measure the fund's integrity, so we graded ourselves" if not handled carefully.

**Decisive point: the reframe is unnecessary because this content already has a home.** `qfra2_deck_v3.py:356` / `qfra2_deck_v4.py:384` already carry a **Governance** bullet on this exact deck: *"Direct-plan + TRI basis, SENTINEL loser-screen, Stage-2 discretionary veto/trim gate, full audit trail (recommendation history + rejected-ideas log)."* That is our-process integrity, already stated correctly, elsewhere. Duplicating it into CALIBRE's I would be redundant, not additive.

**Recommendation: keep Integrity fund-facing**, carried by fee fairness alone (the one real fund-varying leg), and leave our-process integrity where it already lives — the deck's existing Governance bullet.

### 6d. New Integrity one-liner ("quietly drift" dropped entirely, per instruction)
**"Fair fees versus category, with nothing hidden from the investor."** (10 words)
Evidence: TER (Direct-plan) vs category peers — **[DATA]**, real, always available, used at the Stage-1 eligibility gate (MODEL_SPEC.md A7). "Nothing hidden from the investor" is scoped strictly to fee transparency — not a disclosure-quality or style-drift claim, since neither clears the bar cleanly enough to headline.

### 6e. Conviction — 3 ranked rewrites (positive first, cap as consequence not caveat)
1. **"Top-of-category funds earn our biggest calls, while new ones start smaller."** (11 words) — most concrete/active; states what earns size first.
2. **"The higher the category rank, the bigger the call, track record permitting."** (12 words) — same logic, more formal cadence, plain qualifier instead of "clamped/tier."
3. **"Category standing sets the call's size, though a short record caps it."** (12 words) — same meaning; the "though" clause reads slightly more caveat-like, hence third.
All three preserve the original meaning exactly (category rank drives size; short track record caps it — MODEL_SPEC.md Part E1's tiered conviction ceiling), zero jargon.
