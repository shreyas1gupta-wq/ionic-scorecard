# EVALUATION FRAMEWORK — analyze any NAV, product, idea, strategy, or fund manager

> **STATUS: LIVE.** Composed 2026-07-05 per Principal capability-build order ("a very detailed
> framework to analyze NAVs / products / ideas / live strategies / fund managers... god level").
> Owner: Librarian (Lakshmi Narayanan, E-024) curates/cross-links/keeps paths verified against
> `05_DATA_OFFICE/DATA_CATALOG.md`. Methodology authority: CIO (Rajan Mehta) + Quant Head (Arjun
> Rao). New scoring thresholds introduced here (§A/§B) are D-025-class standards — CEO+CIO joint
> record-review applies, but D-027 standing approval means this document is usable immediately;
> the review is for the record, not a gate.
> **This file COMPOSES, it does not override.** On any conflict, the underlying binding doc wins:
> `04_RND_LAB/IDEA_PIPELINE.md`, `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`, `07_RISK_OFFICE/RISK_LIMITS.md`,
> `06_TRADING_DESK/COST_STANDARDS.md`, `06_TRADING_DESK/STRATEGY_REGISTER.md`. This document is the
> INDEX + the NEW material (holdings/product/manager modules, master rubric, red-flag library).

**If you were asked to "analyze" something, start here.** Six modules, one scoring rubric, one
red-flag library, one verified data-asset map, one engagement checklist. Composed from what the
firm already has — nothing below duplicates a binding standard; where it extends one, it says so.

## Table of contents
- §0 How to use this document (decision tree + universal conventions)
- §1 Module 1 — NAV / Track-Record Forensics
- §2 Module 2 — Holdings-Based Attribution
- §3 Module 3 — Product / Structure Analysis
- §4 Module 4 — Fund-Manager Forensics
- §5 Module 5 — Idea / Strategy Evaluation (internal — pointer)
- §6 Module 6 — Live-Strategy Monitoring
- §A Master Scoring Rubric (0-100, hard-fail overrides)
- §B Red-Flag Library (tagged by module)
- §C Data-Asset Map (verified against DATA_CATALOG.md 2026-07-05)
- §D Engagement Checklist (60-min / 1-day / full IC-grade)
- §E Proposed External Sources — NOT fetched, NEEDS CEO+CIO APPROVAL
- Appendix: Case studies
- Provenance / changelog

---

## §0. How to use this document

### Decision tree
1. **It's a return series / NAV only (no holdings disclosed)** → Module 1. This is the Principal's
   highlighted case (returns-based analysis) and the most common ask.
2. **Holdings/portfolio ARE disclosed** → Module 1 + Module 2.
3. **It's a new product/vehicle (MF/PMS/AIF/structured note) before or alongside 1/2** → add Module 3.
4. **It's "should we trust this fund manager"** → Module 4, which calls Module 1 on each of the
   manager's vehicles and Module 3 on the wrapper(s).
5. **It's one of OUR OWN ideas/strategies (pre-capital)** → Module 5 — do not re-derive; the gates
   already exist and are stricter than anything below.
6. **It's one of OUR OWN strategies already live/paper** → Module 6.
7. Not sure how deep to go → §D Engagement Checklist picks the tier.

### Universal conventions (inherited firm-wide; do not restate per module below)
- **Evidence tagging (P-01..P-12, `02_PROMPT_LIBRARY/approved/`):** every claim tagged
  **[DATA]** (on disk, cite path+row count+max date) / **[INFERENCE]** (derived, show the derivation)
  / **[OPINION]** (judgment — say so). A number with no path behind it does not exist for this firm
  (Data Catalog rule, `DATA_CATALOG.md` line 2).
- **DENOMINATOR-FREE REPORTING RULE (KNOWLEDGE_BASE §A.8 — three of our own sleeves died of this):**
  any per-period or per-trade return must be cross-checked in a SECOND, denominator-free basis
  (rupee/points, or % of a stable base like AUM or spot) before it is believed. If the sign or
  order-of-magnitude changes between the ratio basis and the stable basis, the number is an artifact,
  not an edge. Applies identically to a fund's "since-inception annualized return" as to our own
  backtests — the trap doesn't care whose number it is.
- **STANDARD REGIME SLICES:** 2018 (smallcap crash) · 2020 (COVID) · 2022 (rate shock) · 2024
  (election vol) · 2026 YTD. Every track record long enough to span one gets sliced on it
  (RESEARCH_SOP.md validation battery; reused here for external NAVs).
- **TURNOVER-MATCHED COMPARATOR RULE (KNOWLEDGE_BASE §A.20, Nikhil/I-016):** beating a benchmark's
  MEAN is necessary but not sufficient — a low-turnover claimant can "beat" a full-churn benchmark
  by cost-avoidance alone. Always ask whether the comparator's turnover matches the claimant's before
  crediting selection skill.
- **Window-shopping test:** recompute the headline stat with start/end shifted ±1m/±3m/±6m. Move
  >2pp on CAGR = the headline is date-cherry-picked (used in Module 1 and Module 3/NFO-timing).
- **The firm's own history is a dataset (Librarian lesson, 2026-07):** the trophy wall — return-on-
  net-debit, decaying-leg-premium, back-leg-premium denominators (FF v1, S-02, S-03) — predicts
  where the next fake number comes from. When a claimed return looks too clean, check the
  denominator before the model.
- **Reproducibility bar:** if a number cannot be regenerated from a file this firm can point to
  (or, for external claims, from the counterparty's own primary disclosure), it does not clear
  the evidence bar regardless of how it scores elsewhere (§A hard-fail).

---

## §1. Module 1 — NAV / Track-Record Forensics (returns-based)

**When:** any ask that starts from a return series / NAV — the Principal's highlighted case.
**Owner / who to summon:** Arjun Rao (Quant Head, stats authority) + Neel Basu (Attribution) +
Sameer Bhat (DSR/PBO, sensitivity) for the luck-vs-skill leg.

### Inputs required
NAV or return series (daily/weekly/monthly, as long as available) · stated benchmark · stated
inception/go-live date · stated mandate/strategy description · AUM history if available.

### Data assets (verified against DATA_CATALOG.md 2026-07-05; see §C for the full map)
| Need | Path | Verified |
|---|---|---|
| Factor/style regression library (22 series) | `datasets/index_daily/factor_navs_principal.parquet` | On-disk confirmed; D-009 verified vs independent Angel series (2026-02-27 exact match) |
| Official benchmark index closes (174 indices, incl. sector) | `datasets/index_daily/nse_official_all_indices.parquet` | On-disk confirmed; triple-verified 0.000% diff vs factor_navs over 1,365 overlap days |
| Honest null for stock-selection claims (cost-loaded random baskets) | `datasets/derived/benchmarks_random/` (8 `nav_*.parquet` specs + `summary.csv` + `terminal_cagr_percentiles.csv`) | On-disk confirmed |
| Ground-truth price cross-check (catches fabricated/rebased series) | `datasets/nse_bhavcopy_daily/close_all.parquet` (5.57M rows, 3,716 symbols, 2013-01-01→2026-07-03) | On-disk confirmed |
| DSR/PBO canonical computation | `purgedcv` (pip pkg, installed 0.1.2) — acceptance-tested at `results/S-01/20260704_purgedcv_acceptance/purgedcv_recompute.py` | Script on-disk confirmed |
| Cost/slippage assumptions for drag reconstruction | `06_TRADING_DESK/COST_STANDARDS.md` (APPROVED D-021) | — |
| Landmine guards (tz, PIT, same-bar, settlement) | `04_RND_LAB/lib/guards.py`, `04_RND_LAB/lib/lookahead_audit.py` | On-disk confirmed (L1-L7b) |
| MF-universe cross-check (if the NAV is a covered direct-growth equity MF) | QFRA 2.0 / "Mr. X" — **EXTERNAL, outside this repo**, `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\`, re-run via skill `qfra2-rerun` | Frozen v1.0 (2026-06-30), 6-monthly cadence — see Module 4 |

### Procedure
1. **Stats battery.** `CAGR = (NAV_T/NAV_0)^(365.25/days) − 1` · ann. vol = stdev(periodic
   returns) × √(periods/yr) — **match the units to `purgedcv`'s `bars_per_year` guard; a mismatch
   silently inflates every ratio downstream (Arjun's trap, KNOWLEDGE_BASE §A.8)** · Sharpe =
   (ann. return − rf)/ann. vol · Sortino = (ann. return − rf)/downside deviation (semi-dev below 0
   or MAR) · MaxDD = min(NAV_t / running-max(NAV_0..t) − 1) · Calmar = ann. return / |MaxDD|.
   Rolling 1y/3y/5y windows, walked monthly. Drawdown anatomy: depth, peak-to-trough length,
   trough-to-recovery length, % time underwater, count of >10% drawdowns/decade.
2. **Benchmark honesty check.** Does the stated benchmark's sector/cap/vol profile actually match
   the mandate? Construct a fairer one: (a) the matching D-029 random-basket spec from
   `benchmarks_random/` by segment+position-count (mean = floor, p95 = genuine-skill bar per
   `BENCHMARKS_README.md` — **use `terminal_cagr_percentiles.csv`, NOT a percentile read off the
   chained `nav_*.parquet` path, which is an envelope-only fiction, KNOWLEDGE_BASE §A.18**); (b) a
   turnover-matched cut of that same basket if turnover is knowable (§0 rule).
3. **Returns-based style analysis.** Constrained regression of the NAV's periodic returns on the
   factor library: `R_p,t = Σ βᵢ·Fᵢ,t + εₜ`, s.t. `βᵢ ≥ 0, Σβᵢ = 1` (classic Sharpe-style
   analysis; quadratic program, e.g. `scipy.optimize` with bounds+constraint or `cvxpy`). Run on a
   rolling 24-36 month window to get a **style-drift timeline**; R² = style-explained, `1−R²` +
   sign/magnitude of α from `εₜ`'s mean = selection-vs-allocation split. **Related tooling:**
   `/attribution` skill (owner Neel Basu, `.claude/skills/attribution/SKILL.md`) already implements
   incremental-vs-base + factor/regime decomposition for INTERNAL targets (register row / results
   run / PAPER_LEDGER slice) — **its current input surface does not accept an arbitrary external
   NAV file**; extend it rather than hand-roll a second decomposition engine (flagged as a build
   gap, see final memo).
4. **Luck-vs-skill.** Deflated Sharpe Ratio (Bailey & López de Prado; KNOWLEDGE_BASE §B reference
   list) given track length and a PLAUSIBLE trial count (a fund that is the survivor of an AMC's
   internal multi-scheme incubation has an honest trial count > 1 — ask): `DSR = Φ[(ŜR−SR*)·√(n−1)
   / √(1 − γ₃ŜR + ((γ₄−1)/4)ŜR²)]`, Φ = normal CDF, SR* = expected max Sharpe under N independent
   trials, γ₃/γ₄ = return skew/kurtosis, n = observation count. PBO via CSCV (split into S slices,
   all IS/OOS combinations, logit of OOS-rank-of-IS-best; PBO = P(logit≤0)). **Both via `purgedcv`**
   — use the acceptance script as the call-site template, not a hand-rolled recompute. Calibration:
   this firm's own I-016 (DSR 0.9995/PBO 19.8%, 47 honest trials) is what a clean pass looks like;
   S-01 (DSR 0.687/PBO 55%, FAIL) is what a borrowed-beta headline looks like.
5. **Backtest-vs-live discontinuity (splice detection).** At the stated go-live/AUM-scale date,
   test for a structural break: (a) variance ratio (F-test, pre vs post return variance), (b)
   rolling-beta shift (regress on the benchmark in 6-12m windows either side, look for a jump), (c)
   Sharpe-ratio equality test (Jobson-Korkie, Memmel-corrected) pre vs post, (d) autocorrelation
   profile shift (a backtest that's smoother than the live marks is a smoothing/staleness tell, not
   skill). A break exactly at go-live = the same disease as our own K-012 v1→v2 rewrite introducing
   a leak (KNOWLEDGE_BASE T-log) — something changed at the boundary; find out what.
6. **Window-shopping detection.** §0 rule, ±1/3/6 months. Also check whether the DISPLAYED
   since-inception date itself was chosen after the fact (an NFO/fund that "restarts the clock"
   after a bad early stretch is the vehicle-level version of this — cross-ref Module 3).
7. **Fee/slippage drag reconstruction.** Rebuild gross-of-fee returns from disclosed TER + exit
   load + an impact-cost estimate (COST_STANDARDS-equivalent tiers scaled for the AUM in question —
   bigger AUM ⇒ higher market impact, not lower). Compare gross vs net vs benchmark; a fund that
   only clears the benchmark gross is a fee problem, not a skill problem.
8. **Capacity inference.** AUM history vs stated strategy's turnover and cap-tier; run
   **`/capacity-check` (RP-14)** logic — ADV participation, impact, edge-vs-size curve. Calibrate
   against our own I-017 precedent: capacity, not CAGR, was the real kill (60% of weight in
   <₹25cr-ADV names at 370% turnover) — a fund can be statistically real and still un-investable at
   the ticket size being discussed.
9. Optional depth: **`/crowding-check` (RP-15)** if the "edge" is a named, publishable factor
   (has it decayed post-publication, McLean-Pontiff, KNOWLEDGE_BASE §B) — relevant when a fund
   markets a factor tilt as proprietary.

### Red-flag checklist
See §B, tag `[M1]`. Headline items: denominator instability, window-shopping >2pp, splice at
go-live, DSR/PBO quoted without honest trial count, degenerate-result heuristics (Sharpe>4 or
CAGR>60% with MaxDD<10% — same test as `CODE_CHECKS.md`'s post-run detector, applied to an
external claim), NFO timed off a cherry trailing window, capacity outrun by AUM.

### Scoring rubric contribution
Feeds §A components 1 (statistical validity, 25pts), 2 (selection skill, 20pts), 3 (cost/capacity
realism, 15pts — cost/capacity half).

### Output template
`Series ID · window · CAGR/vol/Sharpe/Sortino/MaxDD/Calmar · vs benchmark(s) incl. random-basket
mean+p95+turnover-matched · style-regression β's + rolling drift chart + α residual · DSR/PBO +
honest trial count · splice test verdict · window-shopping delta · gross-vs-net drag · capacity
estimate vs discussed ticket size · verdict tag [DATA/INFERENCE/OPINION] throughout.`

---

## §2. Module 2 — Holdings-Based Attribution (when portfolio disclosed)

**When:** Module 1 PLUS the current or historical holdings list is available.
**Owner / who to summon:** Neel Basu (Attribution) primary; Ananya Iyer's sector desk for
factor/sector reads; Kavya Reddy (Data Officer) if a data-quality question surfaces mid-analysis.

### Inputs required
Holdings snapshot(s) with weights + dates (ideally a time series, not one cross-section) ·
benchmark holdings/sector weights for the same dates.

### Data assets (verified)
| Need | Path | Verified / caveat |
|---|---|---|
| Cross-sectional price/return panel for factor exposure | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}_v11.parquet` (v1.1 canonical: 2,522/2,566 symbols, 97-100% N500 coverage 2014+) | On-disk confirmed. Use `_v11`; plain (non-`_v11`) files are frozen for reproducing already-audited runs only |
| PIT fundamentals (earnings-revision factor, event dating) | `datasets/earnings_pit/unified_quarterly_pit.parquet` (`available_date`, 86.2% exact) | On-disk confirmed — THE join key, never quarter-end dates |
| Value/Quality raw fundamentals | `datasets/earnings_pit/ratios_pit.parquet`, `yearly_balance_sheet_pit.parquet`, `yearly_profit_loss_pit.parquet` | **On-disk confirmed but NOT YET individually described in `DATA_CATALOG.md`** — catalog gap, verify schema/PIT-safety with Kavya before use (flagged to Data Office, see final memo) |
| Sector classification | `datasets/derived/sector_industry_map.parquet` (~976 symbols) | **UNVERIFIED provenance per DATA_CATALOG.md itself** — do not quote a sector-tilt result off this without Kavya's pending validation |
| Screener fundamentals (Value/Quality overlay only) | `datasets/screener_deep/` (BS/CF/PL parquets) | On-disk confirmed. **PIT WARNING: no `available_date` — T+90 lag minimum, FORBIDDEN for event/earnings-reaction dating** |
| Modern-era true mcap weights + sectors | `stocks_data_cache.pkl` (435 tickers, 2020-06→2026-01) | Per DATA_CATALOG, D-009 adjustment-verified |
| Official sector indices for sector attribution | `datasets/index_daily/nse_official_all_indices.parquet` (174 indices incl. sector) | On-disk confirmed |
| Ownership/flow context | `datasets/derived/shareholding_changes.parquet` (21,713 QoQ/YoY) [books] | Per DATA_CATALOG |
| Days-to-liquidate / crowding | Volume history feeding `lib/execution_realism.py` slippage tiers | Code on-disk confirmed |

### Procedure
1. **Brinson allocation/selection/interaction** vs the stated (or a fairer, Module-1-derived)
   benchmark, at sector level: `Allocation = Σ(w_p,i − w_b,i)·R_b,i`; `Selection = Σ w_b,i·(R_p,i −
   R_b,i)`; `Interaction = Σ(w_p,i − w_b,i)·(R_p,i − R_b,i)`; sum = total active return. A manager
   whose active return is ALL allocation and near-zero/negative selection is a sector-rotator, not
   a stock-picker, regardless of the marketing.
2. **Factor exposure of holdings** — cross-sectional regression of holding-level (or portfolio
   look-through) exposures against the `pit_union_panel_v1` + PIT-fundamentals factor set
   (FACTOR_LIBRARY.md categories: Value/Quality/Momentum/Size/Earnings-Revision). Compare against
   the Module 1 returns-based style regression — **they should broadly agree; a large gap between
   holdings-based and returns-based factor reads is itself a red flag** (either stale holdings
   disclosure or return-series integrity issue).
3. **Sector attribution vs official sector indices** (`nse_official_all_indices.parquet`), not a
   broad index, when the fund is sector-concentrated.
4. **Turnover + implied costs.** Reconstruct turnover from holdings-snapshot deltas; apply
   COST_STANDARDS-equivalent tiers (scaled for the fund's AUM/liquidity tier) — does the disclosed
   alpha survive its own implied trading costs?
5. **Crowding/liquidity.** Days-to-liquidate = position size ÷ 20d ADV per name, using the firm's
   own volume data where the name overlaps our universe. Flag any position where days-to-liquidate
   materially exceeds the VEHICLE's redemption terms (Module 3 cross-link — a "daily liquidity"
   fund holding illiquid small-caps is a structural mismatch, not a paper risk).
6. **Style-box drift timeline.** Plot the rolling factor exposures (step 2) over time — does the
   fund migrate toward whatever just outperformed? Performance-chasing is visible here before it
   shows up in returns.

### Red-flag checklist
See §B, tag `[M2]`. Headline items: selection effect persistently negative/allocation-only,
sector attribution vs the wrong benchmark, turnover-implied costs exceeding disclosed alpha,
days-to-liquidate breaching the vehicle's own redemption terms, style-box drift toward recent
winners.

### Scoring rubric contribution
Feeds §A component 2 (selection skill, 20pts — this module's Brinson selection effect is the
preferred input over Module 1's residual-α when holdings ARE disclosed) and component 3
(cost/capacity realism, liquidity half).

### Output template
`Holdings date(s) · Brinson table (allocation/selection/interaction, total) · factor-exposure table
+ comparison to Module 1 returns-based read · sector attribution table vs official sector index ·
turnover + implied-cost estimate · days-to-liquidate distribution vs redemption terms · style-box
drift chart.`

---

## §3. Module 3 — Product / Structure Analysis

**When:** any new product/vehicle evaluation, or as an input to Module 4 for each of a manager's
wrappers. Standalone use: "should we (or a client) buy into this vehicle at all, structurally."
**Owner / who to summon:** Aakash Jain (Structurer) for vehicle/fee/margin mechanics; Farhan
Qureshi (Compliance) for tax/regulatory currency — **his sign-off is required before any tax
claim from this module is quoted, since Finance Act amendments move these rules annually and this
framework's tax section is not a substitute for that review.**

### Procedure
1. **Vehicle + regulatory wrapper.** Identify: Mutual Fund (SEBI MF Regs, daily NAV, retail
   min-ticket) vs PMS (SEBI PMS Regs, ≥₹50L min ticket, discretionary/non-discretionary/advisory)
   vs AIF (Cat I/II/III, ≥₹1cr min ticket, Cat III has the widest derivative/leverage latitude and
   the least standardized public disclosure) vs insurance-wrapped (ULIP) vs index fund/ETF. The
   wrapper determines which of the rest of this module even applies.
2. **Fee stack.** TER (regulated slab for MF; negotiated for PMS/AIF — typically flat management
   fee + performance fee over a hurdle for PMS/AIF) · exit load · hidden costs (GST on management
   fee, transaction costs not in the headline TER) · for AIF Cat III specifically: hurdle rate,
   catch-up mechanics, high-water mark (or its absence), crystallization frequency (frequent
   crystallization on a volatile strategy pays the manager on noise, not durable skill — red flag).
3. **Tax treatment — India, [OPINION/INFERENCE: Farhan to confirm current-year rules before
   quoting].** As framed by the Principal's brief: equity-oriented (≥65% domestic equity) gets
   equity LTCG/STCG treatment; 35-65% equity hybrid funds get a materially different (less
   favorable / later-triggering) long-term treatment; <35% equity ("specified mutual fund" /
   debt-oriented) is taxed at slab rate with no indexation. **The gross-equity-via-arbitrage
   trick:** an arbitrage fund can hold >65% "equity" (cash leg + an offsetting derivative) to
   qualify for equity tax treatment on what is economically a low-volatility, near-riskless
   return stream — tax-efficient, but marketing that implies equity-like RISK on an
   equity-taxed-but-arbitrage-economics product is the exact mismatch to catch. **Do not treat the
   specific rate/holding-period numbers above as current without Compliance verification — Finance
   Act amendments (most recently effective Budget 2024) change these, and another Budget cycle
   (Feb) sits between this framework's writing and today's live use.**
4. **Liquidity terms vs underlying liquidity honesty.** Redemption notice period / gate provisions
   / lock-in, checked against Module 2's days-to-liquidate distribution if holdings are known, or
   against the STATED strategy's typical liquidity tier if not (a "daily liquidity" smallcap fund
   is a structural tell even before you see the holdings).
5. **Benchmark-gaming check.** Was the benchmark changed after a period of underperformance vs the
   original one? Is the current benchmark's risk/sector profile actually representative of the
   mandate (Module 1 benchmark-honesty check, applied at the product-disclosure level)?
6. **Incentive alignment.** Sponsor/manager co-investment ("skin in the game") as a % of AUM ·
   AUM-based fee (grows regardless of performance — asset-gathering incentive) vs performance fee
   (hurdle + high-water mark quality, per step 2) · does the fee structure reward asset growth or
   return generation?
7. **NFO-timing analysis.** Was the product launched right after its model/backtested portfolio's
   best trailing window? This is the vehicle-level instance of Module 1's window-shopping and
   splice-detection tests — run both on the pre-launch "track record" the NFO marketing leans on.

### Red-flag checklist
See §B, tag `[M3]`. Headline items: fee stack consumes most of the pre-fee edge, infrequent/absent
high-water mark, token co-investment, gross-equity-via-arbitrage tax mismatch vs marketed risk,
liquidity terms mismatched to underlying, benchmark changed after underperformance, NFO timed off
a cherry window.

### Scoring rubric contribution
Feeds §A component 3 (cost/capacity realism, fee half) and component 4 (structure/incentive
alignment, 15pts — this module owns it).

### Output template
`Vehicle+regulator · fee stack table (mgmt/perf/exit/hidden) · tax treatment (with Compliance
sign-off status) · liquidity terms vs underlying · incentive-alignment read · NFO-timing verdict
(window-shopping + splice tests on the pre-launch record) · benchmark-gaming verdict.`

---

## §4. Module 4 — Fund-Manager Forensics

**When:** "should we trust this manager/team," across whatever vehicles they run.
**Owner / who to summon:** Ananya Iyer (Equity Research Head) to coordinate; CIO (Rajan Mehta) for
the final trust judgment; reuses Arjun/Neel/Sameer (Module 1) on each prior vehicle.

### Procedure
1. **Cross-vehicle record assembly.** Find EVERY vehicle the manager/team has run (MF + PMS + AIF
   disclosures), not just the one being marketed. A manager showing one strong fund while a sibling
   fund was quietly closed/merged/renamed is manager-level survivorship — the same disease as our
   own universe-membership landmine (T5), one level up.
2. **Style consistency vs claimed process.** Run Module 1's returns-based style regression on EACH
   vehicle, across time. Does the loading pattern match the stated process, or does it drift by
   vehicle/period toward whatever was working?
3. **Drawdown behavior.** Using the STANDARD REGIME SLICES (§0: 2018/2020/2022/2024/2026), did the
   manager hold the stated process through stress, or capitulate (sell into the bottom) / style-
   drift (chase what was working)? This is the single highest-value manager-forensic question and
   is directly checkable from the return series alone if holdings aren't available.
4. **AUM-growth vs alpha decay.** Plot AUM over time against rolling (Module 1) alpha. Decay
   correlated with AUM growth = capacity-constrained skill the fee structure never priced in (the
   post-publication-decay pattern, McLean-Pontiff, KNOWLEDGE_BASE §B, applied to "the manager
   became known/scaled" rather than "the factor was published").
5. **Key-person and team depth.** Is the entire disclosed record attributable to one PM/CIO with no
   visible bench? Any recent, undisclosed, or soon-vesting key-person change?
6. **Attribution of prior success.** Re-run Module 1 (DSR/PBO + style regression) on the manager's
   PRIOR vehicles specifically to separate beta/regime/luck from repeatable process — this firm's
   own S-01 finding (71% of a headline return was regime beta, not signal) is the calibration
   example for how large this correction can be.
7. **QFRA 2.0 cross-reference — MANDATORY prior-art step for any direct-growth equity MF.** The
   firm already runs a frozen, out-of-sample-validated fund-ranking engine ("Mr. X" / QFRA 2.0,
   v1.0 frozen 2026-06-30, 6-monthly cadence) — **external to this repo**, at
   `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\`,
   re-run via the `qfra2-rerun` skill. If the fund is in QFRA's coverage universe, PULL its QFRA
   score (/100), MERIT grade, and SENTINEL red-flags (`CLOSET_INDEX`, `NEG_ALPHA`, `WEAK_CONSIST`,
   `DEEP_DRAWDOWN`, `DOWN_CAP_HI`) from `QFRA2_current.csv` / `red_flag_monitor.csv` as INPUTS to
   this module — **do not recompute a parallel score for a QFRA-covered fund.** This
   framework's Module 4 is the manual/deep-dive complement (any manager, any vehicle, ad hoc
   timing) to QFRA's systematic 6-monthly direct-growth-equity-MF screen, not a replacement for it.
   PMS/AIF managers and one-off analyses (e.g. the AlphaGrep MAAF case study, Appendix) sit outside
   QFRA's universe and run the full manual module.

### Red-flag checklist
See §B, tag `[M4]`. Headline items: manager-level survivorship (only the best vehicle shown), style
regression revealing regime-beta dressed as skill, capitulation/style-drift at a stress low,
alpha decay uncorrected by fee/capacity action, key-person concentration, an unacknowledged QFRA
SENTINEL flag.

### Scoring rubric contribution
Feeds §A component 5 (manager/process quality, 15pts — this module owns it) and contributes to
component 1 (statistical validity) via the reused Module 1 runs on prior vehicles.

### Output template
`Vehicle list (incl. closed/renamed) · per-vehicle Module-1 summary · style-consistency verdict ·
regime-slice drawdown-behavior read · AUM-vs-alpha chart · key-person risk note · QFRA cross-
reference (score/MERIT/SENTINEL if covered, else "outside QFRA universe") · overall trust verdict.`

---

## §5. Module 5 — Idea / Strategy Evaluation (internal) — POINTER ONLY

**This module deliberately does not re-derive anything.** Internal ideas/strategies already have a
stricter, battle-tested pipeline than anything above — use it, don't parallel it.

- **Gates:** `04_RND_LAB/IDEA_PIPELINE.md` — `1-INTAKE → 2-TRIAGE → 3-CHEAP-TEST → 4-FULL-BACKTEST
  → 5-RED-TEAM → 6-IC-MEMO → 7-PAPER → 8-LIVE` (gates auto-advance, D-010; LIVE = Principal only).
- **Red-team:** `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md` — one focused attack + placebo battery
  (D-008), verdict REAL/FRAGILE/FAKE. Skill: `/red-team`.
- **Lookahead audit:** `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` — T1-T10 taxonomy, mandatory at
  Gate-4, `lib/lookahead_audit.py` + one-day-lag test, signed by Dr. Bhat. Skill: `/lookahead-audit`.
- **Cost stress:** `06_TRADING_DESK/COST_STANDARDS.md` promotion rule — must survive 2× all costs
  before paper. Skill inputs: `/fill-audit` (RP-39), `/tca-report` (RP-37).
- **Benchmark hurdles:** `datasets/derived/benchmarks_random/` (D-029) — cap-matched random
  basket, mean = floor, p95 = skill bar, **turnover-matched** per the §0 rule (SOP amended
  2026-07-05 after the I-016 red-team finding).
- **D-030 forward-test freeze (`01_COMMAND_CENTER/DECISIONS_LOG.md`):** once a strategy enters
  forward/paper evaluation, spec+code+params are FROZEN (git hash pinned in STRATEGY_REGISTER /
  PAPER_LEDGER). Any change mid-test voids the result; it restarts as a new version with a fresh
  clock. This is a hard-fail condition in §A if violated and not disclosed as such.
- **D-031 personal-line capacity/limit-or-skip lens (`DECISIONS_LOG.md`):** for the personal
  trading line only, ₹10L-10cr capacity is NOT an automatic kill, and limit-order-or-skip execution
  (no-fill = drop, honestly simulated) is sanctioned. AMC-scale products still owe full scale
  honesty in IC memos — this relaxation does not travel there.
- **Output:** `03_RESEARCH_DESK/IC_MEMO_TEMPLATE.md` → filed to `03_RESEARCH_DESK/memos/`. Do not
  invent a second memo format.

### Scoring rubric contribution
None — Module 5 targets are scored by the EXISTING pipeline vocabulary (gate stage, Red Team
verdict, DSR/PBO, IC verdict). §A's 0-100 rubric is for Modules 1/2/3/4/6 (external NAVs, products,
managers, live monitoring); forcing internal ideas through a second numeric score would create two
competing truths for the same object. If a single comparable number is ever needed across internal
and external candidates, use DSR as the common currency, not a re-scored §A total.

---

## §6. Module 6 — Live-Strategy Monitoring

**When:** an internal strategy is already paper or live and needs an ongoing health check.
**Owner / who to summon:** Tara Singh (Execution/TCA) for fill/slippage reconciliation; Ritika
Sharma (Risk) for regime/limit health.

### Procedure
1. **Live-vs-sim slippage reconciliation.** Weekly, per `forward_tests/README.md` conventions:
   signal logged BEFORE action, fills marked vs actual Angel quotes, tracking-error decomposed
   (slippage/timing/fill/decay). Skills: `/tca-report` (RP-37 implementation-shortfall vs
   COST_STANDARDS), `/fill-audit` (RP-39 optimistic-fill bias in bps). **The honest direction is
   live WORSE than sim** — live fills systematically BETTER than the backtest assumed is itself a
   red flag (§B), not good news.
2. **Rolling edge decay vs backtest cone.** `/decay-check` (RP-16, era-split: stable / decaying /
   regime-dependent). Monthly edge-decay cadence: 2 consecutive fails → auto-demote to paper
   (RESEARCH_SOP.md operating cadence).
3. **Regime-conditioned health flags.** Cross-reference the macro/event calendar (`/macro-calendar`)
   and the STANDARD REGIME SLICES (§0) — is underperformance regime-explained or silent decay?
4. **Pre-registered kill criteria.** Per the strategy's `STRATEGY_REGISTER.md` row — never
   improvised after the fact.
5. **Paper-ledger conventions.** `06_TRADING_DESK/PAPER_LEDGER.md`, append-only. **Firewall rule
   IC-1 (`forward_tests/README.md`): paper results NEVER anchor sizing for an uncertified sleeve —
   they collect behavior, not confidence.** This is a hard-fail condition in §A if violated.
6. Book-level cross-checks as needed: `/risk-report` (RP-32), `/var-sanity` (RP-34),
   `/kill-switch-drill` (RP-33), `/orthogonality` (RP-17 — does this sleeve still add anything the
   book doesn't already own).

### Red-flag checklist
See §B, tag `[M6]`. Headline items: live fills better than sim, paper P&L used to size an
uncertified sleeve, silent multi-cycle decay with no regime explanation, kill criteria improvised
rather than pre-registered.

### Scoring rubric contribution
Feeds §A component 6 (live-discipline / forward-test integrity, 10pts).

### Output template
`Strategy ID · reconciliation window · TE decomposition table · edge-decay verdict (stable/
decaying/regime-dependent) · regime-health flag · kill-criteria distance · firewall-compliance
check (paper not anchoring sizing).`

---

## §A. Master Scoring Rubric — 0-100

**Scope:** Modules 1/2/3/4/6 (external NAVs, products, managers, live monitoring). Internal ideas
use the existing pipeline vocabulary (§5). Components not applicable to a given engagement (e.g.
no holdings disclosed → Module 2 unavailable) are DROPPED and the rest re-normalized:
`Score = 100 × Σ(applicable weighted contributions) / Σ(applicable weights)`.

| # | Component | Weight | Primary module(s) |
|---|---|---|---|
| 1 | Track-record statistical validity (stats battery honesty, DSR/PBO, benchmark honesty, splice/window-shopping tests) | 25 | Module 1 |
| 2 | Selection skill / true attribution (Brinson selection effect if disclosed, else style-regression residual α) | 20 | Module 2 (preferred) / Module 1 |
| 3 | Cost, capacity & liquidity realism (fee/slippage drag survives; capacity vs AUM/ADV; liquidity terms match underlying) | 15 | Module 1 + Module 3 |
| 4 | Structure, fees & incentive alignment (fee stack, tax efficiency vs marketed risk, skin-in-game) | 15 | Module 3 |
| 5 | Manager/process quality (style consistency, drawdown behavior, AUM-vs-alpha, key-person) | 15 | Module 4 |
| 6 | Live-discipline / forward-test integrity (freeze compliance, firewall compliance, honest fill direction) | 10 | Module 6 (or D-030 compliance for internal) |

**Total 100.**

### Hard-fail overrides (apply as a CAP on the computed weighted score, after normalization)
| Trigger | Cap | Precedent |
|---|---|---|
| Fabricated, unverifiable, or non-reproducible core claim (return series can't reconcile to a primary source; a "backtest" that can't be regenerated from disk/config) | **40** | Task's own instruction; S-04's future-settlement fabrication (T8) |
| Lookahead-class defect (T1-T10) on any internal-data component, undisclosed | **40** | D-028; LOOKAHEAD_CONTROLS.md |
| Denominator instability uncorrected (edge sign/magnitude flips between ratio and stable basis) | **50** | KNOWLEDGE_BASE §A.8 — 3 of our own sleeves |
| Benchmark-gaming discovered (benchmark changed post-underperformance, or mismatched to mandate) undisclosed | **55** | Module 3 |
| Style-box drift materially beyond stated mandate, undisclosed | **60** | Module 2/4 |
| D-030-equivalent freeze violation (spec changed mid-forward-test, presented as continuous) | **40** | D-030 |
| Paper/live firewall violation (uncertified paper P&L used to size/greenlight) | **50** | Module 6, forward_tests/README.md IC-1 |

### Score bands → verdict (mirrors, does not replace, the firm's existing verdict vocabulary)
| Band | Verdict | Firm-vocabulary analog |
|---|---|---|
| 85-100 | IC-GRADE / approve-candidate | APPROVE (IC_MEMO_TEMPLATE §1) |
| 70-84 | ADVANCE with named, binding conditions | "ADVANCE-TO-INTAKE" (I-017 pattern) |
| 55-69 | FRAGILE / diversifier-or-watch only | FRAGILE (Red Team) / PAPER-WATCH (S-04) |
| 40-54 | SEND-BACK — rebuild before re-scoring | SEND-BACK (S-01, S-02) |
| <40 or any hard-fail cap | REJECT | KILLED / FAILS-PRE-IC (S-03/K-012, pre-fix S-04) |

---

## §B. Red-Flag Library (tagged by detecting module)

| # | Flag | Module | Why it matters / precedent |
|---|---|---|---|
| 1 | Single ratio-denominator headline with no rupee/points or %-of-stable-base cross-check | M1 | Killed 3 of our own sleeves (FF v1, S-02, S-03) — KB §A.8 |
| 2 | Headline CAGR moves >2pp when start/end shifts ±1/3/6 months | M1 | Window-shopping |
| 3 | Structural break in variance/beta/autocorrelation exactly at the backtest→live boundary | M1 | Splice; same family as K-012's v1→v2 leak |
| 4 | DSR/PBO quoted without a stated honest trial count | M1 | The number is meaningless without its denominator of attempts |
| 5 | Return-smoothing tell: serial correlation too low for the stated illiquid/small-cap holdings | M1 | Classic backtest/valuation-smoothing artifact |
| 6 | Sharpe > 4 or CAGR > 60% with MaxDD < 10% | M1 | CODE_CHECKS.md degenerate-result heuristic, applies to external claims too |
| 7 | Track record's start date sits suspiciously close after a strong trailing period for that strategy type | M1/M3 | NFO-timing / cherry-start |
| 8 | AUM has grown past the ADV-implied capacity ceiling for the stated turnover/cap-tier | M1 | I-017 precedent: capacity, not CAGR, was the real kill |
| 9 | Brinson selection effect persistently ~0/negative while allocation carries all the active return | M2 | Sector-rotator marketed as a stock-picker |
| 10 | Sector attribution computed vs a broad index for a sector-concentrated fund | M2 | Wrong benchmark hides true skill/luck |
| 11 | Turnover-implied costs exceed the entire disclosed alpha at honest slippage tiers | M2 | COST_STANDARDS-equivalent stress |
| 12 | Days-to-liquidate exceeds the vehicle's own redemption terms for a material % of the book | M2/M3 | Liquidity mismatch hiding inside a "liquid" wrapper |
| 13 | Style-box drift toward whatever factor/sector just outperformed | M2/M4 | Performance-chasing, not process |
| 14 | Fee stack consumes most/all of the margin by which the fund beats its honest benchmark | M3 | Pre-fee alpha real, post-fee alpha not — always compute both |
| 15 | Frequent performance-fee crystallization with no true high-water mark | M3 | Rewards volatility, not durable skill |
| 16 | Sponsor/manager co-investment is zero or token-sized vs AUM | M3 | Incentive misalignment |
| 17 | "Equity-oriented" tax status achieved via cash-futures arbitrage on a low-vol return stream | M3 | Gross-equity-via-arbitrage trick — tax-efficient, risk-mismatched marketing |
| 18 | Daily-liquidity terms offered against genuinely illiquid underlying holdings | M3 | Structural redemption-gate risk |
| 19 | Benchmark changed after a period of underperformance vs the original one | M3 | Benchmark-gaming after the fact |
| 20 | Marketed track record is from one vehicle while sibling vehicles (same manager/team) are undisclosed, closed, or merged away | M4 | Manager-level survivorship |
| 21 | Style regression on the manager's prior "successful" vehicle shows heavy regime-beta, not the claimed idiosyncratic process | M4 | Mirrors our own S-01 finding: 71% of a headline was regime beta |
| 22 | Manager capitulated or style-drifted during a stress window instead of holding the stated process | M4 | Regime-slice drawdown-behavior test |
| 23 | Rolling alpha decayed as AUM scaled, with no fee/capacity action taken | M4 | Capacity decay / post-publication-decay analog |
| 24 | Entire disclosed record is one key person with no visible bench, tenure status unclear | M4 | Key-person concentration |
| 25 | QFRA 2.0 SENTINEL flag present (CLOSET_INDEX/NEG_ALPHA/WEAK_CONSIST/DEEP_DRAWDOWN/DOWN_CAP_HI) and unacknowledged in marketing | M4 | Existing firm engine already caught it — don't re-discover, cross-check |
| 26 | Any T1-T10 lookahead class present without a filed `LOOKAHEAD_AUDIT.md` PASS | M5 | D-028, mandatory at Gate-4 |
| 27 | Strategy beats a random basket's MEAN but not a TURNOVER-MATCHED cut of the same basket | M5 | I-016: "beating random" can be pure cost-saving from trading less |
| 28 | Spec/parameter change occurs inside a declared forward-test window, presented as continuous | M5 | D-030 freeze violation — voids, doesn't just discount |
| 29 | Paper/live fills are systematically BETTER than the backtest's slippage assumption | M6 | Wrong-direction optimism — fill-audit (RP-39) territory |
| 30 | Paper results are used to size or greenlight an uncertified sleeve | M6 | Violates forward_tests/README.md firewall rule IC-1 |
| 31 | Realized edge sits below the backtest's own worst historical era for 2+ review cycles with no regime explanation | M6 | Silent decay, not bad luck |
| 32 | Any core return/holdings claim cannot be reconciled to a primary-source file this firm (or the counterparty) can point to | ALL | Fabrication/unverifiable-core-claim — automatic §A cap |
| 33 | A quoted result traces to a run with no `config.json`/data-snapshot behind it | ALL | Non-reproducible — same family as #32 |
| 34 | Conviction-style 0-100 score from `05_DATA_OFFICE/scripts/conviction_scorer.py` (per-TRADE execution conviction) confused with this framework's §A 0-100 fund/strategy score | ALL (hygiene) | Different objects, same numeric range — do not conflate in a memo |

---

## §C. Data-Asset Map (paths verified against `DATA_CATALOG.md` + on-disk `Glob`, 2026-07-05)

| Dataset | Path | Window | Basis | Enables |
|---|---|---|---|---|
| Factor/style NAV library (22 series) | `datasets/index_daily/factor_navs_principal.parquet` | 2005-04-01→2026-02-27 daily | Price-index NAV | M1 style regression |
| Official index closes (174, incl. sector) | `datasets/index_daily/nse_official_all_indices.parquet` | 2016-01→2026-07-03 (momentum family from 2016-07) | OHLC+PE/PB/divyield | M1 benchmark honesty, M2 sector attribution |
| Random-basket benchmark suite (D-029) | `datasets/derived/benchmarks_random/nav_*.parquet` (8 specs) + `summary.csv` + `terminal_cagr_percentiles.csv` | 2005-03-31→2025-12-31, 83 quarterly periods, 10,000 perms/spec | Net & gross, cost-loaded | M1/M5 honest null — use `terminal_cagr_percentiles.csv` for the skill bar |
| PIT union panel v1.1 (canonical) | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}_v11.parquet` | 2005→2026, 97-100% N500 coverage 2014+ | price 2,522 sym / return 2,566 sym | M2 factor exposure, cross-sectional attribution |
| PIT quarterly earnings | `datasets/earnings_pit/unified_quarterly_pit.parquet` | `available_date`-stamped, 86.2% exact | PIT fundamentals | M2 earnings-revision factor; mandatory join key |
| Value/Quality raw fundamentals (catalog gap) | `datasets/earnings_pit/ratios_pit.parquet`, `yearly_balance_sheet_pit.parquet`, `yearly_profit_loss_pit.parquet` | on-disk, window unverified | raw fundamentals | M2 Value/Quality construction — **verify with Kavya before use, not in DATA_CATALOG.md yet** |
| Permanent bhavcopy ground truth | `datasets/nse_bhavcopy_daily/close_all.parquet` | 2013-01-01→2026-07-03, 5.57M rows, 3,716 symbols | official as-traded close | Fabrication/rebasing cross-check for ANY claimed series |
| Universe membership (survivorship) | `NIFTY500_TICKER_2005_2025_Final.xlsx` (root) | 42 PIT snapshots 2005-2025 | membership | M1/M2 survivorship-safe universe, M3 NFO-era peers |
| Sector/industry map | `datasets/derived/sector_industry_map.parquet` | ~976 symbols | classification | M2 sector attribution — **UNVERIFIED provenance per DATA_CATALOG.md**, Kavya validation pending |
| Screener deep fundamentals | `datasets/screener_deep/` (BS/CF/PL parquets) | Mar-2013→TTM-ish | Value/Quality overlay | M2 — **PIT WARNING: no `available_date`, T+90 lag minimum, never for event dating** |
| Modern-era true weights/fundamentals | `stocks_data_cache.pkl` (root) | 2020-06→2026-01, 435 tickers | adjusted OHLCV+shares out+TTM funda+sectors | M2 true mcap weights, quality overlay |
| Ownership/flow | `datasets/derived/shareholding_changes.parquet` | 21,713 QoQ/YoY [books] | FII/DII/promoter deltas | M2 flow attribution, M4 conviction check |
| Corporate actions | `datasets/derived/corporate_action_factors` | 613 events [books] | adjustment factors | M1/M2 dividend/split integrity |
| Cost/slippage standard | `06_TRADING_DESK/COST_STANDARDS.md` | APPROVED D-021 | charges/slippage/circuit rules | M1 drag reconstruction, M2 turnover cost, M3 fee comparator |
| Landmine guards + audit battery | `04_RND_LAB/lib/guards.py`, `lib/lookahead_audit.py`, `lib/execution_realism.py` | code, L1-L7b / T1-T10 / fill_check | — | M1 fabrication/splice checks, M5/M6 lookahead + fill realism |
| DSR/PBO canonical call-site | `results/S-01/20260704_purgedcv_acceptance/purgedcv_recompute.py` | — | `purgedcv` 0.1.2 | M1/M5 DSR/PBO (mind the `bars_per_year` units guard) |
| Principal-facing docx builder | `09_PRODUCT/scripts/build_principal_report.py` | reusable | python-docx + matplotlib, dataviz palette | Output layer for ANY module when the deliverable is Principal-facing (session protocol #4) |
| QFRA 2.0 / "Mr. X" (EXTERNAL — outside this repo) | `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\` + skill `qfra2-rerun` | Frozen v1.0 (2026-06-30), 6-monthly cadence | Direct-Growth NAV vs TRI | M4 (and M1 for MF-universe names) — PULL its score/MERIT/SENTINEL, don't rebuild |

---

## §D. Engagement Checklist — which steps run at each tier

| Step | 60-min quick screen | 1-day deep dive | Full IC-grade |
|---|---|---|---|
| Stats battery (CAGR/vol/Sharpe/Sortino/MaxDD/Calmar) | Yes | Yes | Yes |
| Benchmark honesty (eyeball vs constructed) | Eyeball only | Constructed (random-basket + turnover-matched) | Constructed + documented |
| Window-shopping test | One shift (±6m) | Full ±1/3/6m grid | Full grid, filed |
| Degenerate/red-flag library pass | Quick visual (§B headline items) | Full §B pass for applicable modules | Full §B pass, each flag disposed in writing |
| QFRA cross-reference (if MF-universe) | Yes (5 min, just read the CSV) | Yes | Yes |
| Style regression (returns-based) | No | Yes, single window | Yes, rolling + drift timeline |
| DSR/PBO | No | If trials count is knowable | Mandatory, honest trial count justified |
| Splice/discontinuity test | No | Yes if a go-live/NFO date exists | Yes, formal tests (variance ratio, Jobson-Korkie) |
| Holdings-based attribution (Module 2) | No | If holdings readily available | Mandatory if holdings exist at all |
| Product/structure module (Module 3) | Fee headline only | Full pass | Full pass + Compliance sign-off on tax claims |
| Manager forensics (Module 4) | No | Single-vehicle style consistency only | Full cross-vehicle assembly |
| Red-team-style adversarial attack | No | Self-attack (one placebo) | Route through `/red-team` (Nikhil) or equivalent independent attack |
| Capacity inference | No | Quick ADV check | `/capacity-check` (RP-14) formal |
| Output | In-chat table + one-paragraph verdict | One-pager / memo draft | Full IC memo (`IC_MEMO_TEMPLATE.md`), filed to `03_RESEARCH_DESK/memos/`, CIO sign-off |
| §A score computed | Directional only (2-3 components) | All applicable components | All applicable components, hard-fails checked explicitly |

---

## §E. Proposed External Sources — NOT fetched, NEEDS CEO+CIO APPROVAL (D-009/D-025)

| Source | Feeds | Status |
|---|---|---|
| AMFI daily NAV archive (scheme-wise historical NAV, all AMCs) | Module 1 for any MF outside QFRA's current coverage/cadence, or for daily (vs 6-monthly) monitoring | NEEDS APPROVAL — sample-check per `DATA_QUALITY_RULES.md` §New-source protocol before go-live |
| SEBI AIF/PMS disclosure reports (SEBI AIF quarterly activity reports; PMS disclosure documents via APMI/individual providers) | Module 3/4 for PMS/AIF vehicles, which have no MF-style public factsheet | NEEDS APPROVAL |
| MF factsheet scrapers (AMC monthly factsheets for portfolio holdings; secondary aggregators — flag ToS considerations before scraping any aggregator) | Module 2 holdings-based attribution on external funds | NEEDS APPROVAL |
| Morningstar / Value Research category-average & style-box data | Peer benchmarking beyond our own India-equity random-basket suite (which is not MF-category-specific) | NEEDS APPROVAL |

---

## Appendix: Case studies

### Case study #1 — AlphaGrep MAAF (stub, in flight)
Running in parallel to this framework's construction: `09_PRODUCT/reports/ALPHAGREP_MAAF_ANALYSIS_2026-07-05.docx`
(not yet on disk as of this writing — confirmed via repo search 2026-07-05). When filed, this
becomes the framework's first worked example: expected to exercise Module 1 (NAV forensics) fully
and Module 4 (fund-manager forensics) since AlphaGrep is a manager, not just a product. Whoever
files that report should backfill this stub with: engagement tier used, §A score, which §B flags
fired, and any gaps this framework had that the real engagement exposed — the fastest way to
pressure-test a brand-new framework is to run the first real case through it and log what broke.

---

## Provenance / changelog
- 2026-07-05 (Lakshmi Narayanan, Librarian, E-024): first issue, per Principal capability-build
  order. Composed from (never duplicating): `04_RND_LAB/IDEA_PIPELINE.md`,
  `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`, `07_RISK_OFFICE/RISK_LIMITS.md`,
  `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md`, `04_RND_LAB/RESEARCH_SOP.md`, `04_RND_LAB/CODE_CHECKS.md`,
  `04_RND_LAB/FACTOR_LIBRARY.md`, `04_RND_LAB/KNOWLEDGE_BASE.md`, `04_RND_LAB/KILLED_IDEAS.md`,
  `06_TRADING_DESK/COST_STANDARDS.md`, `06_TRADING_DESK/STRATEGY_REGISTER.md`,
  `datasets/derived/benchmarks_random/BENCHMARKS_README.md`, `05_DATA_OFFICE/DATA_CATALOG.md`,
  `05_DATA_OFFICE/DATA_QUALITY_RULES.md`, `01_COMMAND_CENTER/DECISIONS_LOG.md`,
  `03_RESEARCH_DESK/IC_MEMO_TEMPLATE.md`, `03_RESEARCH_DESK/ANALYST_CHECKLISTS.md`,
  `03_RESEARCH_DESK/forward_tests/README.md`, `00_GOVERNANCE/SELF_IMPROVEMENT.md`,
  `09_PRODUCT/scripts/build_principal_report.py`, the `qfra2-rerun` and `attribution` skills.
  Prior-art check (this framework's own first application of its rule): no existing firm document
  or skill does general NAV/product/manager forensics — the closest capabilities are QFRA 2.0
  (external, MF-specific, systematic) and `/attribution` (internal-target-only) — both cross-linked
  above, neither duplicated.
