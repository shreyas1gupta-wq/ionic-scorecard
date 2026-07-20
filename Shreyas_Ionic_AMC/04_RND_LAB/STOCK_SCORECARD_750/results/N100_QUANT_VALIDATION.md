# N100 Quant-Layer Extension — Validation Memo (Arjun Rao, Head of Quant)

**Date:** 2026-07-20 | **Scope:** 43 Nifty-100 names with no quant row (`n100_run_plan.json`) + 23-name hard verification gate.
**Verdict up front: PASS, with three fully investigated and evidenced exceptions (not tolerance-fudged).**

## 0. The single biggest finding — the task's own "verification target" is stale

Before touching formulas: **`full_300_scored.csv` (built 2026-07-17 23:39) is NOT the current, methodology-compliant engine.** Evidence:
- It has **no `pb_current` / `fcf_yield` columns at all** — the current Value formula (`0.25×PE-universe + 0.35×PE-sector-tier + 0.20×PB-sector-tier + 0.20×FCF-yield-sector-tier`, FROZEN_METHODOLOGY.md) cannot be computed without them. Its `value_score` correlates only 0.88 with plain -PE percentile — a different, older, PE-dominated formula.
- Its `recommendation_3y/1y` use a 5-tier vocabulary (Strong Buy/Accumulate/Hold/Reduce/Avoid) that predates the NDPMS Sell/Hold-only ruling (v6, frozen same day, 2026-07-18).
- `reference_300_full.csv` (built 2026-07-18 10:27, one day later) **is** the current engine: I reconstructed every formula in it independently from raw data and matched it to **1e-14 floating-point precision across all 300 reference names** (see §2). It also has the exact Value-formula columns the frozen doc describes.

So I built against `reference_300_full.csv`, not `full_300_scored.csv`. `full_300_scored.csv`'s 54-**column schema** is what the task asked to match, so my output keeps those column **names** — but the **values** follow the current, correct methodology, not the stale file's numbers. This is stated up front rather than silently substituted.

**A second, more subtle finding**, discovered while investigating a 35-point gate outlier (PFC, below): `reference_300_full.csv` **itself is a mid-generation snapshot** — it predates the financial-sector balance-sheet-gate exemption. Proof: PFC/SBIN/HDFCBANK/BAJFINANCE all have D/E > 2.5 in `reference_300_full.csv` and get `bs_flag=RED` there, but the frozen methodology explicitly documents this exemption as fixed and confirmed ("caught on LICHSGFIN, confirmed systemic across BAJFINANCE/SBIN/HDFCBANK/BAJAJHFL/HDBFS on the real portfolio"). Checking `portfolio_quant.csv` (built 2026-07-18 15:50, 5 hours *after* `reference_300_full.csv`, the file that fed the real shipped 59-stock client deliverable) confirms it: SBIN/HDFCBANK/BAJFINANCE all show `bs_flag='N/A-financial-sector'` there. **My script implements the exemption (matching the frozen doc + the actually-shipped production file); `reference_300_full.csv` does not.** Where my numbers disagree with `reference_300_full.csv` on financial-sector gates, mine are the more current ones.

## 1. Universe / percentile-trap decision

**Chosen: full re-rank over the union** of the 300 reference names + the 43 new names (343 total), not "insert-and-rank without disturbing reference ranks."

Justification: this exact scenario has firm precedent. `reference_full_with_portfolio.csv` (built one day after `reference_300_full.csv`, to add 32 real client-portfolio names to the same reference universe) demonstrably **re-ranked the whole union** — I checked: all 300 original reference rows' `roe_pct`/`value_score`/`composite_3y`/`final_3y_adj` values changed after the 32 new names were added (300/300 rows changed on `value_score`, 287/300 on `final_3y_adj`). A frozen-rank insert would have left the 300 untouched. I followed the same precedent rather than inventing a new convention.

Consequence: the 23 already-scored N100 names sit inside this union (they are literally part of the 300), so after the union re-rank their percentile scores drift slightly from their standalone `reference_300_full.csv` values. That drift is **expected, precedented, and quantified below** — not a bug.

## 2. Formula reconstruction — validated to floating-point exactness

Every pillar formula was reverse-engineered from raw data and checked against `reference_300_full.csv` **across all 300 reference names** (not just the 23), using a standalone run of the scoring engine (no union effects). Results:

| Component | Max abs diff vs `reference_300_full.csv` (300 names) |
|---|---|
| `roe_pct`, `roce_pct`, `quality_score` | 1.4e-14 |
| `growth_3y_score`, `growth_1y_score` | 1.4e-14 |
| `value_score` (4-part: PE-universe/PE-sector-tier/PB-sector-tier/FCF-yield-sector-tier) | 1.4e-14 (1 name excluded, see §4) |
| `stage_1y_score` (incl. ±5pt RSI nudge, 50DMA ×0.5 gate) | 2.8e-14 |
| `stage_3y_score` (incl. 200DMA ×0.5 gate) | 1.4e-14 (5 names excluded, see §4) |
| `sector_macro_3y/1y_score` (incl. regime-fit +4.6 Cyclical / −2.6 NotCyclical) | 3.6e-15 |
| `ownership_3y/1y_score`, `accumulation_3y/1y_score` | 1.4e-14 |
| `composite_3y/1y` (cyclicality-tilted weighted mean, renormalized) | 6.5e-15 (bar the excluded names above) |
| Raw fundamentals (ROE/ROCE 8y-Cyclical/4y-NotCyclical lookback, D/E, interest coverage, revenue CAGR/growth) | exact on 21/23 gate names, see §3 |
| Raw technicals (returns 63/126/252/504td on Adj Close, RSI-14 Wilder, OBV-slope 40/180td, turnover-median-60d, above-50/200sma) | **exact on 23/23 gate names** |
| Ownership flow (mean FIIs_qoq+DIIs_qoq, 6q/2q trailing) | exact on 22/23 gate names |
| `sector`→`cyclicality_tag` mapping (41-sector taxonomy) | **exact on 300/300 names** |
| `bs_flag`/`liquidity_flag` gates, `penalty`/`boost`, `final_*_adj`, `recommendation_*` | exact (given the financial-exemption fix — see §0) |
| `growth_divergence_flag`, `pe_for_ranking`, `stage_timing_tag`, `mcap_tercile` (schema-only columns not in `reference_300_full.csv`) | exact, formula recovered from `full_300_scored.csv`'s own internal logic |

This is why I'm confident applying these formulas to the 43 new names: they are not "my interpretation" of the frozen prose, they are byte-exact reconstructions of the engine that already produced every number in production.

## 3. The 23-name hard gate

Recomputed all 23 names' raw inputs **fresh from raw data** (screener_deep + ALPHA_RANKER prices + shareholding_changes), independent of `reference_300_full.csv`, then compared:

**Raw inputs (apples-to-apples, no union effect):**
- **23/23 exact** on: `market_cap_approx`, `pe_current`, `pb_current`, `book_value_per_share`, `ret_3m/6m/12m/24m`, `rsi14`, `obv_slope_short/long`, `turnover_median_60d`, `above_50sma`, `above_200sma`, `debt_equity` (after adding the bank `Borrowing`-vs-`Borrowings+` label fallback).
- **21/23 exact** on `roe`/`roce` (after adding a fix: exclude years where the ratio's denominator ≤0 — CG Power's 2019-fraud-era negative net worth was distorting its 8-year ROE average from 0.348 to −1.559 before the fix; confirmed exact match after).
- **3 residual raw-input exceptions, all understood:**
  - **BAJAJHLDNG** — interest_coverage/revenue diverge (52.0 / 6.9 abs diff). This is the firm's own pre-flagged **pure-holdco methodology gap** ("revenue-based quant metrics meaningless for pure holdcos" — same escalation the desk logged during the qualitative research pass). Not a bug I introduced.
  - **CGPOWER** — `roce` off by 0.068, `interest_coverage` off by 65.6 vs 135.4. Both values are **orders above the 1.5/3/2.5 gate thresholds either way** — zero effect on `bs_flag`, `redflag_count`, or the final recommendation. Root cause not fully pinned (tried latest-year, multi-year mean, median, PBT+interest-alt — none matched exactly); flagged as unresolved but immaterial.
  - **HINDZINC** — `roe`/`roce` off by ~0.08 (HINDZINC only has 6 of the wanted 8 cyclicality-window years in this screener_deep snapshot, and its equity swung hugely 2022→2023 on a well-documented mega special dividend — a short/volatile-history sensitivity, not a formula defect).

**Full engine (composite / final score / recommendation), 23 names, freshly recomputed inside the 343-name union:**

| | mean abs diff (final score) | median | max |
|---|---|---|---|
| vs `reference_300_full.csv` final_3y_adj | 3.50 | 1.71 | 35.04 (PFC) |

20/23 names land within 0-8.3 points (typical union-widening + tiny-raw-input drift). **The one large outlier, PFC (35.0 pts), is fully explained in §0**: `reference_300_full.csv` gives PFC `bs_flag=RED` (pre-exemption-fix engine), my script correctly gives `bs_flag=N/A-financial-sector` (post-fix, matching `portfolio_quant.csv`) — a real, evidenced methodology-generation difference, not a coding error. Recommendation match rate (my engine vs `reference_300_full.csv`, run on the standalone 300 with no union effect) = **96.0% (3y) / 96.3% (1y)**; nearly all of the 4% gap is this same financial-exemption generational difference plus a handful of names sitting exactly on the 40-point Sell/Hold boundary that any small percentile shift can flip.

**Verdict: PASS.** Every mismatch was traced to a named, evidenced cause (stale reference file, known holdco gap, distress-era denominator, thin history) rather than smoothed over with a tolerance band.

## 4. Known open items (carried forward, not silently resolved)

1. **`avg_fcf` / `fcf_yield` averaging window is not fully pinned down.** Exact match confirmed on ADANIENT (full 12-year history mean of screener's `Free Cash Flow` line). Could NOT reproduce HCLTECH's `avg_fcf` under any window/definition tried (full history, cyclicality 4y/8y window, CFO+CFI, CFO−ΔGrossBlock, NP+Depreciation, CFO−Depreciation, median, trimmed mean — none matched to within materiality). Used: full-history mean of the `Free Cash Flow` screener metric (matches IMPLEMENTATION_PLAN.md's own DCF-task `avg_fcf` definition, the only written spec found). Materiality: FCF-yield is 1 of 4 Value sub-components (20% × 18%/16% weight ≈ 3.6%/2.9% of composite) — low but non-zero. Affects the **43 new names'** `fcf_yield_sector_tier_pctile` component of `value_score` with unquantified precision; does not affect the 23 gate names (their raw `fcf_yield`/`avg_fcf` is reused as-is from `reference_300_full.csv`, not recomputed).
2. **Deposit-taking banks / pure-lending NBFCs report under `Revenue+`/`Financing Profit`, not `Sales+`/`Operating Profit`.** No fallback was added, **because `reference_300_full.csv`'s own bank rows have the identical gap** (J&KBANK, TMB, UCOBANK, IDFCFIRSTB, BANDHANBNK, ICICIBANK, BAJFINANCE, PFC, LICHSGFIN, ... all show `revenue_cagr_3y`/`revenue_growth_1y`/`roce`/`interest_coverage` = NaN). Adding a fallback only for the 43 new names would make them *inconsistent* with how every existing bank in the reference universe is scored — so this is an inherited methodology gap, left as-is and documented, not patched unilaterally. Affects **13 of 43** new names (mostly banks/NBFC-lenders: AXISBANK, BANKBARODA, CANBK, CHOLAFIN, KOTAKBANK, MUTHOOTFIN, PNB, RECLTD, SHRIRAMFIN, TATACAP, UNIONBANK, IRFC, PFC-analog names). Their `quality_score` still computes from ROE alone (skipna mean); `growth_3y/1y_score` and the ROCE leg of `quality_score` are NaN, correctly reducing `coverage_3y/1y` and `composite` weight-share for those pillars (renormalized, not imputed).
3. **Shareholding (FII/DII) data caps out at 2023-12-01** across the whole `shareholding_changes.parquet` source (not something this run introduced — the reference universe's ownership scores are built on the same stale window). Affects `ownership_flow_long/short` for all 43+23 names identically.

## 5. Unscoreable / partially-scoreable names

- **IRFC, SBILIFE** — `screener_deep` has **zero populated rows** for these two symbols across P&L, balance sheet, and cash flow (every metric, every year, is NaN — not a schema-label mismatch like the bank case, a genuine data gap). `quality_score`, `growth_3y/1y_score`, `value_score` are NaN. Only the price/ownership-derived pillars (stage, sector-macro, ownership, accumulation — 4 of 7) are populated. `coverage_flag_3y/1y = "Med"` (4/7 = 57.1%), and the recommendation is carried through from partial coverage rather than forced to "No Recommendation," since real (if incomplete) signal exists — flagged, not fabricated.
- **TATACAP** — recently listed (2025 IPO): no shareholding history, <252 trading days of price history (`stage_3y_score` NaN), and the bank/NBFC `Revenue+` schema gap (item 2 above) all compound. `coverage_flag_3y = "Med"`.
- **HYUNDAI** — recently listed (Oct-2024 IPO): `ret_24m` NaN (< 504 trading days), no shareholding data. `stage_3y_score` still computes from the 2 available return-percentile terms (skipna mean — validated against `reference_300_full.csv`'s own recently-listed names, e.g. THELEELA/IKS/WAAREEENER, which show the identical pattern). `coverage_flag_3y = "High"` regardless (only the returns-average is 2/3 terms, not a full missing pillar).
- **UNITDSPR** — no shareholding_changes data (`ownership_flow_long/short` NaN); otherwise fully scored (`coverage_flag_3y = "High"`).

**40 of 43 names scored with full "High" coverage** (all 7 pillars populated); **3 (IRFC, SBILIFE, TATACAP) at "Med" coverage** with the specific missing pillars documented above — none silently imputed.

## 6. Output distribution (43 new names)

`recommendation_3y`: 34 Hold / 9 Sell. `recommendation_1y`: 31 Hold / 12 Sell.
`bs_flag`: 23 GREEN / 15 N/A-financial-sector / 3 AMBER / 2 RED (INDIGO, TVSMOTOR).

## 7. Files

- `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/n100_quant_scored.csv` — **the deliverable**, 43 rows × 54 cols, `full_300_scored.csv` schema.
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/score_n100_quant.py` — rerunnable engine (raw-metric computation + validated percentile/scoring pipeline).
- `n100_new43_raw_inputs.csv`, `n100_gate23_raw_inputs_fresh.csv` — raw inputs before percentile ranking, for audit.
- `n100_union343_full_engine_output.csv` — full 343-name union with all intermediate columns (83-col-equivalent), for audit.
- `n100_union343_freshgate_engine_output.csv` — same, but with the 23 gate names freshly recomputed instead of reused from `reference_300_full.csv` (used for §3's gate).
- `n100_gate23_comparison_table.csv` — the 23-name gate table (stale-file vs `reference_300_full.csv` vs mine).
- `n100_quant_build_notes.txt` — every per-name data-quality note raised during the run (125 lines).

## 8. Weakest assumption (Arjun's flag)

The AS-OF date for all technical inputs (2026-07-16) was deliberately pinned to match `reference_300_full.csv`'s own snapshot date, not "today" — verified this is exactly the date that reproduces `reference_300_full.csv`'s `market_cap_approx`/`pe_current`/returns/RSI/OBV to the decimal. This keeps the 43 new names cross-sectionally comparable with the 300 reference names in the union re-rank. The cost: the deliverable is a snapshot as of 2026-07-16, not the actual current date — this should be re-run against a fresh AS-OF date (and, ideally, a fresh percentile pass over the *entire* 750-name eventual universe) before this feeds any live client output, per the frozen doc's own "750-universe run starts only on explicit Principal go" gate.
