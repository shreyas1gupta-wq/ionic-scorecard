# BROAD RESEARCH ROADMAP 2036 — firm-wide investing/trading research program
**Owner:** Prof. Aditya Verma (R&D). **Opened:** 2026-07-18 (Principal standing order: "continue researching investing/trading across folders, multiple agents, with roadmaps, until I say stop — Sonnet 5, occasional higher model for checks/roadmaps/task-assignment").
**Status:** LIVING DOCUMENT. Update after every wave (mark tasks DONE / KILLED / PROMOTED, append new threads, move settled items to §c). This is a scoping/assignment book, not a results ledger — results live in `04_RND_LAB/results/`, verdicts in `IDEA_PIPELINE.md` / `KILLED_IDEAS.md`.

**Execution model:** each §b task is scoped so a single Sonnet agent can pick it up and run standalone. Max 3 parallel agents (D-023). Roadmap/check/task-assignment passes may use a higher model (Principal's carve-out). Every task inherits the firm's non-negotiable discipline (see §DISCIPLINE below) — a Sonnet agent must read that block before starting.

---

## 2026-07-18 MID-SWEEP CONSOLIDATION (CIO — Rajan Mehta, Opus check-in between Sonnet waves)

*Scope: 11 wave-1 assessment files landed in `BROAD_RESEARCH_2036/`. R14 (revers_5d) landed AFTER the roadmap was written — its verdict is folded in below. R8 (real-cost swing rerun), R15 (D1 special-situations), R16 (PEAD/sector-rotation closure) NOT yet landed — flagged in §4, not waited on.*

### 1. Honest signal-to-noise — this wave was CORRECTION, not DISCOVERY

Read plainly: **~10 agents ran, and the net new TRADEABLE alpha discovered tonight is zero.** That is not a failure — kills and corrections are paid-for answers — but the wave's volume oversells its novelty. The honest tally:

- **NEW knowledge (genuine):** (a) **S-05 is unverified/likely false** — the single most important output of the night, and it is a *governance* finding, not alpha; (b) **H1 dealer-gamma/GEX = clean KILL** — never executed before, now falsified (no coherent theory-consistent sign under either convention; the US SpotGamma mechanism does not survive contact with India's retail-seller-dominated, 31%-coverage OI); (c) **gold's near-zero/slightly-negative correlation to the short-vol book, confirmed at book level** (was previously only index-level) — modest, real, but the crisis-*offset* claim remains untested because this book has never had a crisis.
- **CORRECTION of things we half-knew (the bulk):** revers_5d "looks great on the corrected panel" → **OVERFIT** (fails plateau, placebo, drop-one-year — Line B's original "failed forward" was closer to truth); Line B survivorship fix → edge on mom_12_1 / Mom12+LowVol **survives on return but true build MaxDD is −74%, not −35%** (tail risk was understated); "MSQ_BASE" **does not exist** — it is `swing_momentum/`, which uses **equal-weight not Kelly**, and whose 30bps flat cost is a placeholder that fails the firm's own approved tiered COST_STANDARDS; `alpha_research/` is **literally 0% executed** (one PLAN.md commit, ever) — the "data-ready frontier" is real but the lead hypothesis (H1) is now dead; the cross-asset ETF sleeve was already built + honestly killed, just never marked in its queue.

**Ratio: roughly 3:1 correction-over-discovery, and the one big discovery is an error we made, not an edge we found.** State that to the Principal without inflation.

### 2. Throughline — YES, and it is epistemic, not survivorship

The earlier ALPHA_RANKER wave had "the round-trip gap" (no exit trigger). **Tonight's throughline is candidate (b), stronger than (a): unverified headline numbers travel further than their evidence.** Survivorship bias (candidate a) is real but it is a *known, already-handled* landmine (Line A fixed it; it is documented) — not the systemic finding. The systemic finding is a **provenance/traceability gap in how our own research gets summarized and passed along:**

- **S-05:** register + pipeline assert "+5.9% CAGR / 6-6 positive"; traces to ONE narrative sentence (`SESSION_JOURNAL.md:334`), no script/CSV; the one real-fill test says **Sharpe −0.83**.
- **This roadmap's own T1** quoted "Sharpe 2.6/3.6 sitting idle" — it was **synthetic Black-Scholes pricing**, and the source audit had already re-headlined it to 1.65–2.0.
- **Line B** shipped "fwd Sharpe 0.86, MaxDD −35%, forward-robust" — real DD −74%; and its "revers_5d failed" flag was itself wrong, and correcting *that* produced a mirage (1.08) that would have entered an IC memo had Sameer not run the skeptical pass. **Numbers wrong in both directions.**
- **"MSQ_BASE / Kelly sizing"** (memory note) — no such file, no Kelly anywhere.
- **ETF queue item** stamped `[LAUNCHED]` with no disposition for a completed, killed study.

This is the same disease as the original "Sharpe 2.6–3.6" conflation. **It is a genuine epistemic-hygiene gap and it is the more important finding than any single strategy result tonight.**

### 3. Updated priority ranking

1. **[IMMEDIATE — governance] S-05 FORMAL FREEZE + firm-wide headline-provenance audit.** This outranks every speculative new-alpha item. See CIO ruling below.
2. **[R8 — the decisive cost gate] Real-cost swing_momentum rerun** (tiered slippage + circuit no-fill + 10%-ADV cap, at 1× and 2× COST_STANDARDS). This is the honest gate on the one modest-but-real equity edge (mom_12_1 / Mom12+LowVol, OOS Sharpe ~0.60/Calmar 0.70 under an *underpriced* 30bps). Cheap, decisive: it either promotes Track-2 or kills it. Already in flight.
3. **[T3 — highest-value BUILD] Exit overlay / round-trip gap.** Unchanged; spec'd + half-built; improves every long book at once.
4. **[DOWNGRADE] The participant-state frontier (Wave-2, T5/T6/T7/T8).** Thinner than the survey implied: the lead (H1) is dead, H8 is data-access-gated, and `alpha_research/` is 0% executed. Do not launch a fresh Wave-2 push until items 1–3 are resolved.
5. **[carry to portfolio construction, do NOT size on crisis-offset] Gold static diversifier** — route to Devika (owns the 50/50 sleeve); the correlation property is real, the "saves the book in a crash" claim is untested at book level.

**The "verify the process, not just this number" action item (cheap, do now):** a lightweight **provenance audit** — for every headline number cited this week in `STRATEGY_REGISTER.md`, `IDEA_PIPELINE.md`, `CURRENT_STATE.md`, and `SESSION_JOURNAL.md`, confirm a script/CSV backs it, or tag it `[NARRATIVE-ONLY — UNVERIFIED]`. S-05 proves this is not one bad row; it is a class. Owner: Compliance (Farhan) + Data Officer (Kavya), one Sonnet pass, kill-list output.

### 4. Still-in-flight — fold in when they land, don't wait

- **R8 (real-cost swing):** the go/no-go for Track-2. Fold directly into whether swing_momentum is promotable *at all* — the current 30bps result is not shown to survive the firm's own cost floor.
- **R14 (revers_5d):** **LANDED — verdict OVERFIT.** Standing instruction: **do NOT cite the 1.08 forward Sharpe** in any IC memo or register row. Closed.
- **R15 (D1 special-situations):** the first genuinely-*new* equity edge candidate of the sweep. When it lands, demand a pre-registered kill + same-exit placebo before any excitement — treat with the skepticism revers_5d earned.
- **R16 (PEAD / sector-rotation closure):** want a clean KILL-or-PROMOTE verdict WITH `IDEA_PIPELINE`/`KILLED_IDEAS` rows, so these abandoned folders stop getting re-mined blind. Interpretation + one confirmatory test only — not new research.

### CIO RULING — S-05

**VERDICT: FREEZE (formal, effective now).** Beyond the URGENT FLAG's recommendation, I am issuing this as a CIO ruling.
- **Rationale (3 lines):** The register/pipeline "+5.9% CAGR, 6/6 years positive" claim traces to a single narrative sentence with no backing artifact; the only real-fill reconstruction of the same family gives Sharpe −0.83. A strategy carrying an unverified/contradicted headline must not accrue forward-clock time or be automated. No capital-equivalent risk is live (signal log empty), so this is a paperwork freeze, not an unwind.
- **Tail-risk assessment:** the true tail exposure here is *reputational/process*, not market — an untraceable number wired to "live NOW" is exactly how a bad result gets sized later. That is the tail I am protecting against.
- **Action:** do NOT stand up the S-05 automated morning signal task. Mark STRATEGY_REGISTER S-05 and IDEA_PIPELINE row 16 `[FROZEN — CLAIM UNVERIFIED, CIO 2026-07-18]`.
- **Kill/resolve criteria:** re-run `run_realfill_deltahedged.py` WITH its coded IV-gate (`IV_GATE_PCT=0.0045`) + F1/F2 vetoes on real fills (~half-day, all pieces on disk). Reproduces ≈+5.9%/6-6-positive → evidence the claim, then re-apply landmine-#9 / 2×-cost / D-031 gates before any paper clock. Does not reproduce → KILL S-05, correct both rows, log to KILLED_IDEAS with −0.83 as the honest number.
- **Review date:** next weekly meeting (2026-07-20). **Dissents:** none recorded; Vikram (FM, S-05 owner) authored the reconciliation and concurs.

---

## (a) SURVEY — what exists across the whole research surface (2026-07-18)

The firm sits on a **mature short-vol options book, a half-validated equity-momentum sleeve, a large graveyard of honest kills, and a big untouched "participant-state" frontier.** On the **options sell-side** (`intraday_options_strategy/` + `FINAL_STRATEGY_FORWARD_CHECK/`) there is substantial validated work: four short-vol strategies with real build/forward numbers (short strangle = most robust; earnings short-vol = robust; IV/RV straddle passed small; FF calendar fragile/now killed as a vehicle), and — the standout — a **delta-hedged 0DTE expiry-day short straddle at OOS Sharpe ~2.6, extended to a DTE0+DTE1 book at OOS Sharpe ~3.6, audited/qualified-pass but NOT live and apparently idle**; option-BUYING (~14 variants) and overnight-drift-as-a-strategy are both tested-and-killed. On **equities**, `swing_momentum/` has a working, honestly-stress-tested regime-gated leadership-momentum backtest (~11.6% CAGR full / ~16% OOS after the survivorship fix, MaxDD <23%, Calmar 0.70) whose single biggest remaining optimism source is a **missing liquidity/volume gate**, plus a 10-sleeve "god-tier" expansion (D1–D11) that is **entirely unbuilt**; the closely related `MIDSMALL_MOM_ROTATION` result found the alpha is regime-timing/drawdown-avoidance, not stock-selection. On **fundamentals/quantamental**, tonight's `ALPHA_RANKER` scorecard reset leaves only the **1M relative** scorecard usable (1Y/5Y relative = thin-sample watchlist; the entire absolute scorecard is not usable), and the night's cross-cutting headline — echoed independently by the `PMS_STUDY_20260712` (SageOne-with-exit beats Marcellus-without-exit on an identical entry screen) — is that **none of the long books have a deceleration/exit trigger** ("the round-trip gap"), already spec'd in `ALPHA_RANKER/rnd/scorecard/EXIT_TRIGGER_SPEC.md`. `STOCK_SCORECARD_750` is a Gate-3-passed forward-test candidate (single-regime caveat). Two threads are **abandoned unsynthesized** (`PEAD_ALPHA_20260714`, `NEW_ALPHA2` sector rotation — raw scripts/CSVs, no verdict written); `EARN_MOM_SWEEP` (long-only earnings momentum) and `AMF_PINE_BT` are effectively dead. The **largest genuinely-untapped surface** is `alpha_research/`'s participant-state program — dealer-gamma/GEX (H1), FII/DII & participant-wise flow (H8), retail-F&O crowding/fragility (H2/H3), lead-lag networks (H4) — **planned in detail, data-mostly-ready, but never executed.**

---

## (b) PRIORITIZED TASK LIST (assignable to a single Sonnet agent each)

Priority = value × (cheapness-to-test) × data-readiness × orthogonality-to-existing-book. Wave-1 = launch now; Wave-2 = queue behind wave-1.

### WAVE 1 — launch now

---
**T1 — Reconcile and revive the idle 0DTE / DTE0+DTE1 delta-hedged short straddle (HIGHEST VALUE).**
- **Domain/folders:** `intraday_options_strategy/` (read-only source: `buying/SELLING_REPORT.md`, `results/V3_FINDINGS.md`, `results/AUDIT.md`, `results/STRATEGIES_COMPARISON.md`); reconcile against `06_TRADING_DESK/STRATEGY_REGISTER.md` and `04_RND_LAB/results/OPT_SWEEP50_PHASE1_20260707/`.
- **Concrete question:** Is the audited delta-hedged 0DTE expiry-day short straddle (OOS Sharpe ~2.6; DTE0+DTE1 book ~3.6) a NEW edge, or is it the same thing already carried in the register as S-04 (strangle, certified/paper-watch) / S-05 (straddle, paper-ready) / S1-F? Establish overlap-vs-redundancy FIRST. If genuinely incremental, what is the honest post-cost, post-fill-realism Sharpe, and is it paper-ready?
- **Why high-value:** it is the single most-validated-yet-unrealized asset in the whole survey — a strong result sitting idle. If real and distinct, it is a near-term addition to the live short-vol book; if a duplicate, closing that out prevents double-counting an edge we already own.
- **Standalone context for the agent:** Do NOT re-run a fresh grid; this is a reconciliation + honest-fill audit, not a hunt. (1) Read the three legacy result docs and extract the exact strategy spec (strikes, hedge rule, entry/exit clock, DTE definition). (2) Read STRATEGY_REGISTER S-04/S-05/S1-F specs and diff them. (3) The Sharpe 2.6/3.6 came from a backtest whose fills need auditing against firm landmines: **landmine #9** (expiry-day option SETTLE_PR = underlying settlement, NOT option price — cash-settle at intrinsic from the underlying), **#7b** (no fills on circuit/thin bars; 2–3× slippage), the delta-hedge leg's own round-trip cost, and **D-031** limit-or-skip (no-fill = DROP). Re-cost at approved `06_TRADING_DESK/COST_STANDARDS.md` AND 2× COST_STANDARDS. (4) If it survives 2× cost and honest fills and is distinct from the register, write an IDEA_PIPELINE intake + recommend a frozen paper spec (D-030 freeze: pin git hash). If it is a duplicate, say so plainly and close it. Deliverable: `results/ZERODTE_STRADDLE_RECON_<date>/SUMMARY.md`.

---
**T2 — Close swing_momentum's #1 validity hole (liquidity/volume gate) and cheap-test the D1 special-situations sleeve.**
- **Domain/folders:** `swing_momentum/` (read-only source: `PLAN.md`, `RESULTS.md`, `GOD_TIER_EXPANSION.md`, existing `data/build_panel.py` + `run_swing.py` logic — copy/extend into `04_RND_LAB/results/SWING_MOM_V3_<date>/`, never edit legacy).
- **Concrete question:** (Part A) When a realistic ADV liquidity/volume gate is added (cap entry/exit at ≤10–20% of that day's volume; no fill on lower-circuit bars; slippage scaled by ADV participation), how much of the ~16% OOS CAGR survives, and does MaxDD stay <25%? (Part B) The top-ranked unbuilt god-tier sleeve, D1 special-situations/event-driven, has zero backtests — run the cheapest falsification: does an event set (buybacks, demergers, promoter-stake changes, index-inclusion) show forward drift beyond the momentum sleeve already captures?
- **Why high-value:** swing is the closest thing to a real, tradable, DIFFERENT-FACTOR equity sleeve (trend/leadership) to sit alongside the short-vol book — but its headline number is optimistic until the liquidity gate exists; that fix is the honest gate before anything in this track scales. D1 is the top-ranked expansion sleeve and is capacity-friendly for the ≤₹10Cr personal line (D-031).
- **Standalone context for the agent:** Use the survivorship-corrected panel (`datasets/derived/pit_union_panel_v1/close_panel_price.parquet` — PRICE basis, correct for P&L; NOT the return panel; watch the 2020-era DELISTED two-scale corruption flagged in CURRENT_STATE 2026-07-16 — gate to liquid N500-PIT). PIT universe via `NIFTY500_TICKER_2005_2025_Final.xlsx`. Regime filter (Nifty>200DMA + breadth) is load-bearing — keep it. **Do NOT re-add a standalone mean-reversion sleeve** (already tested, correlated, dragged the book — see §c). Part A is the priority; Part B only if A leaves time. Deterministic, no per-run refit; report CAGR/MaxDD/Calmar split by regime era. Deliverable: `SWING_MOM_V3_<date>/SUMMARY.md` + equity curve + per-trade blotter.

**Part B — DONE 2026-07-18 (Aditya):** see `D1_SPECIAL_SITUATIONS_FIRSTCUT.md` in this folder + `results/D1_SPECIAL_SITS_CHEAPTEST_20260718/`. Confirmed `disc_event_in_window` is guard-only (no event-type label) and `corporate_action_factors.parquet` is bonus/split/dividend only — neither usable for D1 as originally scoped. Found an untapped source, `datasets/nse_earnings_dates/board_meetings_all.json` (94,136 rows, PIT `bm_timestamp`), that DOES carry classifiable free-text event types; ran a genuine cheap-test on buyback-consideration intimations (282 events/161 symbols vs same-symbol placebo): +1d/+5d excess significant (p=0.005/0.025), evaporates by +10-20d, lag-robustness confirms real announcement effect not lookahead, thin-but-positive net of 2x cost at +5d. Stage 3-CHEAP-TEST PASS-WITH-FLAGS, filed to IDEA_PIPELINE.md. Part A (liquidity gate) still open.

---
**T3 — Codify the "Anti-Marcellus-Trap": a mandatory deceleration/valuation-ceiling EXIT overlay (the round-trip gap).**
- **Domain/folders:** `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/` + `ALPHA_RANKER/rnd/scorecard/EXIT_TRIGGER_SPEC.md` + `exit_trigger_flags.parquet` (legs 1–3 already built) + `FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036.md` (this is its Priority 1).
- **Concrete question:** On a quality-screen entry universe (ROE/ROCE floor + growth-adjusted valuation, the PMS convergent skeleton), does adding a mandatory exit rule — sell on (a) earnings deceleration below a threshold OR (b) valuation-ceiling breach OR (c) a forensic hard-veto OR (d) a Minervini technical stop, OR-gated — beat the same entry screen held to buy-and-hold, on CAGR AND drawdown, out-of-sample? SageOne (with exit, 25.1% CAGR) vs Marcellus (no exit, negative alpha since inception) on an IDENTICAL entry screen is the real-money natural experiment motivating this.
- **Why high-value:** seven independent workstreams tonight converged on "no long book here has an exit trigger" as the single biggest gap. This overlay improves EVERY long book at once — ALPHA_RANKER, STOCK_SCORECARD_750, swing_momentum, and the personal investment line (D-032). It is spec'd and half-built; this task finishes and validates it as a blendable overlay.
- **Standalone context for the agent:** Read EXIT_TRIGGER_SPEC.md — legs 1–3 exist as `exit_trigger_flags.parquet` (a SEPARATE overlay, never blended into rel_score/abs_score by design); leg 4 (Minervini technical stop) may need adding. Build the exit as an overlay on a held portfolio and measure incremental CAGR + MaxDD reduction vs no-exit, PIT (use `datasets/earnings_pit/unified_quarterly_pit.parquet` with `available_date`, NEVER quarter-end; dedup — 1,278 dup rows landmine). Judge on the Principal's rule: consistency/accuracy/drawdown-control, not a fixed Calmar/Sharpe bar; deterministic, no per-run refit. Cross-reference the Principal's valuation-band memory (0-65/65-160/160+, sign-only) for the valuation-ceiling leg. Deliverable: `results/EXIT_OVERLAY_<date>/SUMMARY.md` with a keep/re-spec/drop recommendation for the S3 growth-longevity leg question already pending Principal.

---
**T4 — Cheap closure passes on the two abandoned/unsynthesized threads (PEAD_ALPHA + NEW_ALPHA2 sector rotation).**
- **Domain/folders:** `04_RND_LAB/results/PEAD_ALPHA_20260714/` and `04_RND_LAB/results/NEW_ALPHA2_20260714/` (both = raw scripts/CSVs/PNG, no verdict ever written).
- **Concrete question:** For each: read what already exists, re-run only what's needed to interpret the outputs, and write the missing verdict — is there an edge (PROMOTE to a proper Gate-3 cheap-test), or is it dead/redundant (KILL with resurrection condition)? PEAD specifically: post-earnings-announcement DRIFT is a distinct classic factor from the (dead) long-only earnings-momentum sweep; the sole survivor thread from EARN_MOM_SWEEP was B3 (SUE top-quintile + above-50DMA + 40d hold) — fold that in: run B3 against a FRESH-SEED calendar-matched placebo + a /sensitivity pass to settle it.
- **Why high-value:** cheapest possible value — work already exists on disk, it just needs interpreting and filing so future waves don't re-mine it blind. Kills are paid-for output. PEAD is a genuinely robust factor in the literature and deserves a real verdict rather than an abandoned folder.
- **Standalone context for the agent:** This is interpretation + one confirmatory test, NOT new research. Verdicts must be pre-registered before the B3 re-run. PIT discipline (available_date), one-day-lag audit, same-exit placebo is the arbiter (KB lesson: the placebo-with-same-exits test is the only reliable arbiter in drifting markets). Long-only earnings momentum is CLOSED beyond B3 (§c) — do not widen the sweep. Deliverable: a `VERDICT.md` written into each of the two folders' firm-side mirror (do not edit legacy; write to `results/PEAD_NEWALPHA2_CLOSURE_<date>/`), plus IDEA_PIPELINE/KILLED_IDEAS rows.

### WAVE 2 — queue behind wave-1 (the untapped participant-state frontier + diversifiers)

---
**T5 — Dealer-gamma / GEX positioning fields for NIFTY (alpha_research H1 — the lead new dimension, data-ready, never executed).**
- **Domain/folders:** `alpha_research/PLAN.md` §H1; data = NSE F&O bhavcopy OI by strike/expiry (2021-26, in `stocks_options/` + `intraday_options_strategy/datasets/raw/options/`) + Angel live chain. Build into `04_RND_LAB/results/GEX_H1_<date>/`.
- **Concrete question:** Reconstruct a daily net-gamma-exposure surface and zero-gamma flip level for NIFTY from option OI. Does price (a) pin to high-OI strikes into expiry, (b) trend below the flip / mean-revert above it, (c) treat the flip as support/resistance? Effect size vs a matched random-level placebo.
- **Why high-value:** direction-agnostic, capacity-fit ≤₹10Cr, orthogonal to every current sleeve, and a moat-B edge (dealer hedging is forced) that is mature in the US but barely formalized in India. Highest-conviction genuinely-new dimension in the whole plan. Feeds the H6 meta-allocator later.
- **Standalone context for the agent:** Estimate dealer sign heuristically (calls vs puts, OI-change vs price). DUAL SCHEMA landmine in `stocks_options/` (HF 1-min tz-aware vs bhavcopy daily with `settle`, 0.00-price untraded strikes) — use `04_RND_LAB/lib/guards.py`; gate every leg on CONTRACTS>0 (landmine #9). This is an EXISTENCE/event-study first (is price conditioned on gamma state?), a tradeable rule only if the event study clears. KILL only if no robust price-conditioning after the placebo — NOT on low t alone.

---
**T6 — FII/DII & participant-wise-OI positioning extremes and divergence (alpha_research H8 — ex the killed DII-persistence).**
- **Domain/folders:** `alpha_research/PLAN.md` §H8. Data = NSE FII/DII daily cash + participant-wise F&O OI (client/FII/DII/pro long-short) + index-rebalance calendar — **DATA-ACCESS GATED: several NSE `/api` endpoints 403 on the office proxy; needs home-network/VPN + a Data Officer D-009 verification pass BEFORE any signal work.** Route the pull request through Kavya (D-009) first.
- **Concrete question:** Distinct from the KILLED B1c daily-DII-flow-persistence signal (§c), do (a) FII-vs-DII divergence, (b) extreme FII F&O net-position as a contrarian/continuation signal, (c) index-reconstitution front-running of forced passive buying, carry forward predictive content beyond price momentum, OOS?
- **Why high-value:** Indian FII/DII flows are uniquely transparent (published daily) and the dominant directional driver — moat A+B. The naive persistence angle is already killed; these positioning-extreme/divergence/forced-flow angles are the untested, more defensible ones.
- **Standalone context for the agent:** Step 0 is the data D-009 gate — do not fabricate flow data; if the pull is blocked, write the scoping + data-ask and stop. B1c (daily DII 5d-flow rank q≥0.8→3d hold) is killed forward-data-only — do NOT re-test it in-sample. Same-exit / matched-placebo arbiter; PIT; one-day-lag audit.

---
**T7 — Cross-asset macro-regime diversifier sleeve (valuation-band × rate-cycle, different-FACTOR).**
- **Domain/folders:** `FUND_METHODOLOGY_2036/CYCLES_AND_REGIMES_METHODOLOGY.md` (rate-cycle-turn + demographic-dividend passed as usable priors); the banked 50/50 NIFTY-gold benchmark (`results/KIRU_PKG/20260713/`); USDINR (cataloged); `etf_gold_silver/` (NIFTYBEES/GOLDBEES 2013-26). Build into `results/MACRO_REGIME_SLEEVE_<date>/`.
- **Concrete question:** Does a deterministic macro-regime allocation across NIFTY / gold / cash (and optionally USDINR), tilted by the Principal's valuation band (0-65/65-160/160+, sign-only) and the rate-cycle-turn prior, beat the dominant 50/50 monthly-rebal NIFTY-gold benchmark on risk-adjusted terms (Sharpe / DD budget), OOS?
- **Why high-value:** the stacked-book correlation study proved new sleeves must be DIFFERENT-FACTOR (equity variants cap the Sharpe multiplier ~1.7×); a macro/cross-asset sleeve is one of the few genuine frontier-movers left, and it aligns directly with the Principal's own market-layer memory. Capacity-friendly.
- **Standalone context for the agent:** The bar to beat is the 50/50 benchmark, NOT buy-and-hold (K-016 lesson). Judge on Sharpe/DD, never raw CAGR vs a parent (K-015 lesson). Deterministic, no per-run refit; momentum-OFF at valuation extremes (Principal rule); GT-2 signed-corr template for any correlation claim. Do NOT re-propose the ratio-Donchian rotation (K-016, killed) — this is a valuation/rate-regime allocator, a different construction.

---
**T8 — Retail-F&O crowding × liquidity-fragility: selective long-convexity (alpha_research H2+H3 fused — the ONE legitimate door back to option buying).**
- **Domain/folders:** `alpha_research/PLAN.md` §H2 (retail forced-action) + §H3 (liquidity fragility). Data = 1-min NIFTY/BankNifty/VIX (2015-26) + OTM weekly OI/turnover. Build into `results/FRAGILITY_H23_<date>/`.
- **Concrete question:** Can a fragility/crowding state (retail crowded far-OTM OI + 1-min range-expansion/volume-dry-up-then-spike features) predict next-window realized > implied vol, well enough to BUY cheap convexity selectively on only those days (and sell/stay-flat otherwise)?
- **Why high-value:** direction-agnostic long-vol complement to the short-vol book, and the only legitimate re-entry to option buying — K-001 killed unconditional buying but left an explicit resurrection door: a sniper-entry variant, <5 trades/mo, net-positive after 2× costs on fresh OOS. This is exactly that door, entered through a fragility predictor rather than a timing indicator.
- **Standalone context for the agent:** The gate is whether fragility features beat VIX-implied as a realized-vol forecaster OOS — if they don't, KILL (this is the pre-registered kill). Respect K-001: must be <5 trades/mo and net-positive after 2× COST_STANDARDS, else it is just option-buying again. Pre-open auction bug (use bars ≥09:15), HF timezone landmine. This is speculative — cheapest existence test first, no capital talk until the forecaster clears.

---

## (c) DON'T RE-RESEARCH — settled/killed (check here before proposing anything)

Re-opening any of these requires its stated resurrection condition to be MET with NEW data — not a parameter reshuffle. Full detail in `KILLED_IDEAS.md`.

- **Intraday option BUYING** — all ~14 variants (directional, cheap-vol, mean-reversion, delta 0.3/0.5/0.7, debit/credit spreads, ORB, gap-fade, expiry-vol-breakout, RSI/MACD/S-R timing). K-001. Net-negative after cost; VRP means buyers overpay; no intraday convexity (MFE/MAE≈1.0). ONLY door: sniper <5 trades/mo, net-positive after 2× cost on fresh OOS (that door = T8, via a fragility predictor).
- **Overnight-drift AS A STANDALONE STRATEGY** — TESTED AND KILLED (corrects the original brief's framing). Real drift is only +0.075–0.08%/night, smaller than round-trip cost (net Sharpe 0.63 build / −1.70 fwd); capturable only via index/futures/ETF, never options. It is a measured side-fact, not an edge. (The ~2.6pp/yr KIRU "15:25 exec" figure is an execution-timing artifact on a rotation strategy, not a tradeable drift edge.)
- **Adding a standalone mean-reversion sleeve to swing_momentum** — already tried; correlated, dragged the book down. Also K-stock-meanrev-standalone (RSI3/zscore pullback buying) killed (t=−4.8/−7.2). Mean-reversion timing is real only as a zero-marginal-cost overlay on trades already being made.
- **Long-only earnings MOMENTUM** — EARN_MOM_SWEEP, 2/30 beat placebo (chance). CLOSED for this window beyond the single unproven B3 thread (SUE-Q5 + 50DMA + 40d), which T4 settles. (PEAD = drift, is DISTINCT and still open — that's T4.)
- **AMF "Adaptive Momentum Fusion" Pine engines** — clean re-run loses to NIFTF500 buy-hold after removing the DELISTED price-scale corruption; efficiency legs fail placebo, momentum legs fake/negative. Low priority, not worth pursuing.
- **FF calendar (all vehicles)** — K-012, signal real but vehicle dead (61% dead back-leg markets; edge ≤0 causally). Only a NEW liquidity-native vehicle meeting 5 pre-registered kills, per CIO ruling.
- **NIFTYBEES↔GOLDBEES ratio-Donchian rotation** — K-016, edge is a same-bar illusion; loses to the 50/50 rebal benchmark. (The 50/50 strategic-gold sleeve itself is ALIVE, routed to Devika — and feeds T7.)
- **Also killed** (do not re-propose as-is): reverse/double calendars (K-002/003), long far-OTM at high IV (K-004), 0DTE iron condor (K-005), regime-gated naked selling (K-006), gap-fade selling (K-007), SL/wings on FF calendars (K-008/009), landmine blacklist (K-010, lookahead), gold same-day crash hedge (K-011), MQ50 semiannual (K-014), mom-lowvol dynamic-regime basket (K-015), air-pocket leg-buyback (K-air-pocket), ORB on stocks (K-postbreakout-orb, killed across all universes/windows/vehicles), AF07 stage-turn (K-AF07), B1c DII-flow (K-B1c, forward-data-only), ADX-ATR entry family (K-adx-atr, 8 constructions 0 pass), PMS GARP replication (managers' alpha = uncodable gates), cross-asset/ETF-rotation/downside-capture/technical-patterns from the ALPHA_RANKER wave (dead/redundant).

**Reusable components banked (free to use inside new systems, no re-test needed):** VIX-252d-percentile regime gate; signed-corr bar template (GT-2); ATR-trailing EXITS (credit belongs to exits, not entries); 50/50 NIFTY-gold benchmark as the diversifier hurdle; oversold-mean-reversion regime switch (CERTIFIED); the same-exit placebo as the arbiter of any drifting-market signal.

---

## DISCIPLINE (every task inherits — a Sonnet agent must read this first)
1. **Never kill on t / p / DSR / PBO / small-n alone** if the logic and effect size are sound. Only STRUCTURAL failures kill: leakage/lookahead, wrong sign, redundancy, gross post-cost shortfall, flat/zero effect, data artifact. Low-power ≠ no-effect — resurrect low-t-but-sound signals as forward-test candidates for the Principal.
2. **PIT / no-lookahead always.** Earnings via `available_date` (never quarter-end). Run the one-day-lag test. Respect all CLAUDE.md DATA LANDMINES (#1–#9, esp. #9 expiry-day settle, #4 dual-schema, the 2020 DELISTED price corruption).
3. **Deterministic, no per-run refit** — same data → same output.
4. **Costs = approved `COST_STANDARDS.md` only**, and always report a 2× COST_STANDARDS stress. Rupee-points + %spot for options (denominator disease killed 3 sleeves). No-fill = DROP (D-031).
5. **Logic-first, fund-manager lens** — state the economic WHY (who loses money to us, and why do they keep doing it?) before believing any backtest. Pre-register kill criteria BEFORE touching data.
6. **The same-exit / matched placebo is the arbiter** in drifting markets — engine-level portfolio sims can manufacture edge from queue mechanics alone (K-AF07 lesson).
7. **Checkpoint to disk continuously** (a token-limit or restart must lose nothing); bank early, don't hold for one final write.
8. **Forward-test freeze (D-030):** once anything enters paper, spec+code+params freeze; pin the git hash. Scraping/new data → Data Officer D-009 + Principal (T6's gate).
9. **Report format:** hypothesis one-pager OR stage-gate report (stage, evidence, PASS/KILL, honest trials count, next cheapest step). File verdicts to IDEA_PIPELINE.md / KILLED_IDEAS.md.
