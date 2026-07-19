# STOCK_SCORECARD_750 — quantamental 0-100 stock scoring framework
**Launched 2026-07-17 (Principal ask): score the Nifty-750 universe 0-100 across Quality/Growth/Value/Stage/Accumulation + additional pillars (Ownership/Smart-Money Flow, Sector & Macro Positioning, Intrinsic Value/DCF) + 2 overlay gates (Balance-Sheet Safety, Liquidity) + a regime-conditional weight tilt. This is Phase 1 of a 3-phase plan — Phase 2 = per-stock agent qualitative research (not this build), Phase 3 = blend quant + qualitative into a final systematic score (not this build).**
**View/horizon: 3-year holding period (investment-line orientation, D-032) — every lookback window and pillar weight is calibrated to this, not swing-trade timing.**
**Revision history: v1 (equal-weight, snapshot-agnostic) -> v2 (3Y recalibration: fundamentals-tilted weights, longer technical windows) -> v3 this doc (regime tilt swapped from 200DMA to a stable valuation regime; DCF pillar added; Quality made explicitly sector-neutral + cyclicality-aware).**

## Scope
**IN:** a transparent, rule-based (percentile-rank) composite score, 0-100, one row per stock in the 750-universe, PIT-sourced but computed as a current snapshot; a modest regime-conditional tilt on top of a fundamentals-tilted base weight.
**OUT (this phase):** backtesting whether the score predicts forward returns (PIT-sourcing keeps the door open, doesn't do it); the qualitative agent-research layer and final blending; ML-learned weights; any dashboard/UI; investment advice output. The regime-tilt weights and DCF assumptions below are v1 judgment calls, explicitly flagged where they need a sensitivity check (Sameer Bhat's discipline) before being trusted for real capital decisions.

## Data foundation
- **Universe:** `ALPHA_RANKER/data/universe/symbols_750.txt` + `sector_map.parquet` — data reuse only, not methodology (ALPHA_RANKER is a separate project per Principal instruction).
- **Fundamentals:** `ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet` primary (has PIT `available_date`, 4,613 symbols ⊃ 750), filtered to `available_date <= as_of_date`. Requires a D-009 spot-check before trust, and a `DATA_CATALOG.md` entry (currently missing — flag to Kavya).
- **Cross-check only, not a parallel build:** firm's own `datasets/screener_deep/` + `datasets/screener_dump_20260704/` (T+90 restatement lag) — sample-verify a slice, don't rebuild the pipeline twice.
- **Prices/technicals:** `ALPHA_RANKER/data/prices/` or firm's own bhavcopy / PIT union panel — whichever has cleaner coverage, decide in Phase 1.
- **Ownership flow:** `datasets/derived/shareholding_changes.parquet` (firm's own, READY).
- **Sector momentum pattern:** reuse the methodology shape (not the strategy) from `results/NEW_ALPHA2_20260714/alpha_sector_rotation.py` — sector_map + trailing sector-return ranking — recalibrated to 6-12M windows.
- **Regime classifier (NEW, this revision):** firm's own `HEDGING_ANALYSIS_20260708` study already built an India NIFTY50 PE/PB regime series (2016-present, local data) — reuse that CAPE/PB-percentile bucketing pattern (this is the firm's own prior work, fully reusable as both data and methodology, unlike ALPHA_RANKER). Refreshed **monthly**, not daily.
- **DCF inputs:** trailing FCF history (from screener cash-flow statements), India 10Y G-sec yield (risk-free rate, already in firm's macro data), 3yr weekly beta vs NIFTY (computed from price history already on hand).

## Methodology
**Percentile-rank composite**: every metric → cross-sectional percentile (0-100) within the universe (sector-neutral for Quality/Value/DCF, universe-wide otherwise) → averaged within pillar → weighted sum across pillars (base weight × regime tilt) → overlay gates applied last.

Chosen over z-score (more outlier-sensitive on this repo's messy screener data) and ML-learned weights (no clean pre-2020 PIT panel to train on; explicit v2 candidate, already on the firm's `ADOPTION_QUEUE`).

## Regime-conditional weight tilt (NEW this revision)
**Problem with v2:** a fast-moving signal like NIFTY-vs-200DMA would flip the tilt often, which fights the 3-year holding view — weights would whipsaw on noise the underlying pillars are deliberately smoothed against.
**Fix:** classify a **stable valuation regime** using India NIFTY50 PE/PB percentile vs its own 10-15yr history (reusing the `HEDGING_ANALYSIS_20260708` 3-bucket pattern: Cheap <33rd pctile / Neutral / Rich >67th pctile), recomputed **monthly**. This is structurally slow — valuation regimes persist for quarters-to-years, not days.

| Regime | Tilt (additive delta on base weights below — each row's deltas net to zero by construction, so no rescaling step is needed) |
|---|---|
| **Rich** (market expensive) | Quality +3, DCF +3 (capital-preservation posture); Stage −3, Accumulation −3 (momentum-chasing riskier when the market's already expensive); Liquidity gate strictness increases one notch |
| **Neutral** | Base weights unchanged |
| **Cheap** (market cheap) | Value +3, DCF +3, Growth +2 (buying growth cheap); Quality −4, Sector&Macro −4 (funds the tilt) |

This is a hand-set 3-preset lookup table, not a tuned model — kept simple and auditable — but it is genuinely new scope beyond "simple model," and the tilt magnitudes above are illustrative v1 judgment calls that need their own sensitivity/perturbation check (Sameer Bhat) before being trusted, same discipline the firm applies to every other parameter choice.

## Pillars — 3-year-view calibrated, sector-bias corrected

| # | Pillar | Base weight | Sub-metrics | Lookback | Rank basis |
|---|---|---|---|---|---|
| 1 | Quality | 18% | ROE, ROCE, Piotroski-style profitability/leverage/efficiency, accruals (CFO vs NP), margin stability | **Cyclicality-aware** (see below): 7-10yr through-cycle average for Cyclical-tagged sectors, 3-5yr for Defensive/Stable sectors | **sector-neutral** (ranked within own sector, not the whole 750 — see bias note below) |
| 2 | Growth | 18% | Revenue/EPS CAGR, QoQ earnings acceleration | 3yr CAGR is the scored input; 5yr CAGR computed only as a Phase-4 QA sanity check (flags sharp 3y-vs-5y divergence as a possible base-effect distortion), never feeds the rank itself | universe-wide |
| 3 | Value (Relative) | 15% | P/E vs own 3yr history & sector median, P/B, EV/EBITDA, div yield (inverted: cheap = high score) | 3yr own-history window; sector-median comparison is horizon-agnostic | sector-neutral |
| 4 | **Intrinsic Value (DCF)** — NEW | 12% | DCF-implied upside/downside vs current price (methodology below) | 3yr avg FCF base, 5yr explicit forecast fading to terminal growth | sector-neutral (discount rates/growth ceilings differ by sector risk profile) |
| 5 | Stage/Technical | 12% | Structural stage (Weinstein 1-4), trend strength, relative strength vs sector | 12M+24M relative-return percentile, 40-week (≈200-day) structural MA, monthly-smoothed | universe-wide |
| 6 | Sector & Macro Positioning | 10% | Sector relative strength, cyclical/defensive fit | 6-12 month sector relative strength + the sector's own cyclicality tag (below) | universe-wide |
| 7 | Ownership/Smart-Money Flow | 8% | FII/DII/promoter holding change | Trailing 4-8 quarter (1-2yr) sustained-accumulation trend | universe-wide |
| 8 | Accumulation | 7% | OBV trend, A-D line trend, volume-on-up vs down days | 6-12 month trend slope | universe-wide |

Base split: **Fundamentals+Valuation (Quality+Growth+Value+DCF) = 63%, Technical/Flow (Stage+Sector&Macro+Ownership+Accumulation) = 37%** — regime tilt above adjusts this by a few points either way, never inverts it.

### Quality sector-bias fix (this revision)
Raw ROE/ROCE structurally favors asset-light sectors (IT, FMCG) over capital-intensive ones (industrials, cement, metals, banks) regardless of how good a capital-intensive company actually is *for its sector*. Fix: Quality is ranked **sector-neutral** (percentile within its own sector), and the output surfaces **both** `quality_sector_percentile` (what actually feeds the composite) **and** `quality_universe_percentile` (shown for context only, not scored) — so a cement company at the 85th percentile *within cement* but only the 40th percentile *across all 750* is visibly and correctly scored on the 85, not silently penalized for operating in a structurally lower-ROE sector.

### Cyclicality-aware Quality (this revision)
Every stock gets a `sector_cyclicality_tag` (Cyclical / Defensive-Stable / Sensitive-hybrid) from a static sector→tag lookup (v1 approximation — flagged as an open risk below). Only **Cyclical**-tagged sectors (commodity-style: metals, cement, capital goods) get the **longer through-cycle average** (7-10yr, or max available history) for Quality's ROE/ROCE/margin inputs, so they aren't scored purely on where their sector's cycle happens to sit today (peak-cycle ROE looks falsely excellent, trough-cycle looks falsely broken). **Defensive-Stable and Sensitive-hybrid** (e.g. banks/NBFCs — rate-sensitive but without the same peak-trough ROE swings as commodity cyclicals) both keep the standard 3-5yr window.

### Intrinsic Value (DCF) methodology (NEW pillar)
- **Cash flow base:** FCFF = EBIT×(1-tax) + D&A − Capex − ΔWC, trailing 3yr average (smooths single-year noise).
- **Forecast:** explicit 5yr projection, starting from the stock's own Growth-pillar 3yr CAGR (capped at a sane ceiling, e.g. 25-30%, to block absurd extrapolation) and fading linearly to a **terminal growth rate** — assumption to be fixed and **labeled in the output**, not hidden (e.g. ~India long-run nominal GDP proxy).
- **Discount rate:** CAPM cost of equity = India 10Y G-sec yield (risk-free) + stock beta (3yr weekly vs NIFTY) × equity risk premium — ERP is a single assumed constant, **labeled as [ASSUMPTION]** in the output per the firm's epistemic-conduct rule, not silently baked in.
- **Terminal value:** Gordon growth model at the terminal rate.
- **Output:** intrinsic value/share vs current price → upside/downside %, sector-neutral percentile rank.
- **Graceful degradation:** requires ≥5yrs of consistent-sign FCF and positive book equity; else DCF is marked not-computable (`dcf_coverage_flag = N/A`) and excluded from that stock's composite — never a fabricated placeholder number. This will be a meaningful chunk of the smallcap tail given the firm's own documented <40% coverage lesson.
- **Every assumption surfaced as its own output column** (`dcf_discount_rate_used`, `dcf_terminal_growth_assumed`, `dcf_fcf_years_used`) so nothing is a silent input — this is by far the most assumption-heavy pillar in the framework and should be treated with proportionally more skepticism than the others.

**Stage pillar internal resolution** (unchanged from v2): the 0-100 score = structural stage + trend strength + relative strength only. RSI/stochastic overbought-oversold is a **separate timing tag**, not blended in.

## Overlay gates (multiplicative, applied after the weighted composite)

| Gate | Signals | Effect | Notes |
|---|---|---|---|
| Balance-Sheet Safety | D/E, interest coverage, promoter pledge %, distress flags | RED caps final score ≤40; AMBER ×0.85; GREEN unchanged | Strictness increases one notch in a Rich regime |
| Liquidity/Tradability | 20/60d avg turnover (₹), free-float market cap | Cap/discount + explicit "illiquid" flag | **Size-relative threshold**: turnover bar scales by market-cap tercile (Large/Mid/Small) rather than one fixed number for all 750 names — a smallcap needs a stricter bar than a largecap to earn the same liquidity score |

## Missing data & coverage
A missing metric is excluded from that stock's pillar average (never zero-filled). Every stock carries `data_coverage_pct` + `coverage_flag` (High/Med/Low) per pillar — matters more on a 750-name universe reaching deep into smallcaps (<40% coverage is a documented firm lesson), and especially for the new DCF pillar's harder data bar.

## Output schema (one row per stock, parquet + csv)
`symbol | sector | sector_cyclicality_tag | as_of_date | regime_state | quality_sector_percentile | quality_universe_percentile | growth | value_relative | dcf_upside_pct | dcf_discount_rate_used | dcf_terminal_growth_assumed | dcf_fcf_years_used | dcf_coverage_flag | stage | stage_timing_tag | sector_macro | ownership_flow | accumulation | composite_raw | bs_flag | liquidity_flag | final_score | coverage_pct | coverage_flag`
Reserved for Phase 2/3 (not populated by this build): `qualitative_score`, `blended_final_score`.
Location: `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/<as_of_date>/scores.parquet` (+`.csv`), with a human-readable leaderboard summary alongside.

## Build phases (→ writing-plans next)
1. **Data foundation** — pull/validate ALPHA_RANKER data (D-009 spot-check), assemble the 750-universe + sector map + static cyclicality tag table, add the missing `DATA_CATALOG.md` entry, build the monthly valuation-regime series from `HEDGING_ANALYSIS_20260708`'s pattern.
2. **Metric library** — per-pillar calculators, reusing existing code where it exists (RSI/z-score scripts, `tf1_composite.py`, `alpha_sector_rotation.py`'s sector-momentum logic recalibrated to 6-12M, `shareholding_changes.parquet`), plus the new DCF calculator.
3. **Percentile-rank + aggregation engine** — config-driven base weights + regime-tilt lookup table, overlay gates (size-relative liquidity bar).
4. **Output + validation** — schema, coverage flags, sanity spot-checks (a known quality compounder scores high; a known distressed name gets red-flagged; a known cyclical isn't unfairly punished vs IT/FMCG; DCF assumptions are visibly labeled, not hidden).
5. **(Future, not this build)** Phase 2 qualitative agent research + Phase 3 blended final score.

## Addendum 2026-07-17 (post-implementation-review): real schema + robustness findings
Two independent review passes (data-quality lens + ops/repeatability lens) on the first implementation-plan draft verified the actual data files on disk and found the draft's assumed schemas were wrong throughout. Folded back into this spec before any code runs:

- **Fundamentals are raw line items, not pre-computed ratios.** `MASTER_fundamentals_pit.parquet` (verified: columns `key_symbol, nse_symbol, company, fiscal_year, period_label, statement, metric, metric_norm, value, available_date, source, is_fresh`) carries Screener-style raw P&L/Balance-Sheet/Cash-Flow line items only (`sales, net profit, operating profit, opm %, eps in rs, equity capital, reserves, borrowings/borrowing, interest, cash from operating activity, total assets, free cash flow, ...` — 33 values total, exhaustively checked) — NOT `roe/roce/pe/pb/debt_equity`. Every ratio this framework needs is now **derived** by a new module (`derived_ratios.py`) inserted between raw loading and the pillar functions: ROE = net profit / (equity capital + reserves); ROCE = operating profit / (equity + borrowings); D/E = borrowings / equity; Interest Coverage = operating profit / interest; Accruals = (net profit − CFO) / total assets; P/E and P/B need current price joined in from the prices panel, with shares-outstanding **approximated** as net profit / EPS (not directly reported — an [INFERENCE], not a [DATA] figure, labeled as such downstream). `market_cap` is derived the same way (price × approximated shares), not read from fundamentals.
- **Promoter pledge % is not available in any current data source** — not a Screener P&L/BS/CF line item. The Balance-Sheet-Safety gate's three signals reduce to two (D/E, Interest Coverage) until pledge data is separately sourced — a data-intake gap, not solved by this build.
- **Real sector taxonomy (41 `macro_sector` values in `sector_map.parquet`, verified) has case-duplicate categories** ("Consumer durables" vs "Consumer Durables", "Consumer services" vs "Consumer Services") — the cyclicality lookup normalizes case, or half of two real sectors would silently fall through to the default tag. Column is named `macro_sector`, not `sector` — renamed on load.
- **Prices carry both `Close` and `Adj Close`** (verified column names, Title Case, `Date` as an index not a column). Return-based pillars (Stage, Accumulation, Sector&Macro) use `Adj Close` to avoid split/dividend artifacts; turnover/liquidity math uses raw `Close` × `Volume` (actual traded value, not a back-adjusted proxy).
- **Ownership data (`shareholding_changes.parquet`, verified columns `FIIs, DIIs, Promoters, ..._qoq, ..._yoy, available_date`) already carries pre-computed QoQ/YoY columns and its own `available_date`** — the Ownership Flow pillar now applies the same PIT filter as fundamentals (previously it didn't — a live lookahead + non-reproducibility gap) and uses the pre-computed `_qoq` columns directly rather than re-deriving a diff.
- **New non-functional requirements** (ops-robustness pass): the orchestrator isolates pillar-GROUP failures (a missing ownership file shouldn't kill the 63%-weighted fundamentals pillars — each pillar group runs in its own try/except, degrading to NaN+Low-coverage rather than crashing the whole run); output writes atomically (temp file + rename, not a direct overwrite that could leave a truncated file on a mid-write crash); the composite no longer `fillna(0)`s a missing pillar — it re-weights across only the pillars a stock actually has data for, so missing data lowers coverage_flag rather than silently depressing the score.
- **Tiny-sector percentile degenerate case**: a sector with <5 members can't produce a meaningful within-sector percentile (a lone stock trivially ranks 100th regardless of quality) — `percentile_rank` falls back to universe-wide ranking for those sectors.

## Dual-horizon scoring: 1-Year view added alongside 3-Year view (2026-07-17)
Every stock gets **two independent composite scores**, not a blend — a 3-Year view (original design, fundamentals-tilted) and a 1-Year view (technical-tilted) — since the same stock can be a good 3-year hold and a poor 1-year trade, or vice versa, and collapsing them into one number would hide that.

| Pillar | 3Y weight | 1Y weight | 1Y lookback (recalibrated from the 3Y table above) |
|---|---|---|---|
| Quality | 18% | 15% | unchanged — 7-10yr/3-5yr cyclicality-aware; a business's quality doesn't reset because your holding period is shorter |
| Growth | 18% | 15% | 1yr/TTM growth is the scored input (was 3yr CAGR); latest-quarter YoY is the divergence/consistency check (was 5yr CAGR) |
| Value-Relative | 15% | 15% | P/E vs OWN **1yr** history (was 3yr); sector-median comparison unchanged (horizon-agnostic) |
| Intrinsic Value (DCF) | 12% | 5% | same methodology, sharply lower weight — DCF's multi-year convergence thesis isn't why a 1-year holder buys |
| Stage/Technical | 12% | 25% | **3M+6M** relative-return percentile (was 12M+24M); structural MA shortened to **10-week/50-day** (was 40-week/200-day); RSI/OB-OS is now blended in as a small direct adjustment (±5pts), not just a side-tag — near-term entry timing matters more at this horizon |
| Sector & Macro | 10% | 12% | **1-3 month** sector relative strength (was 6-12 month) — closer to the original monthly-rotation pattern (`alpha_sector_rotation.py`) this pillar was built from |
| Ownership/Smart-Money Flow | 8% | 8% | latest **1-2 quarters** (was trailing 4-8 quarters) — near-term flow, not sustained multi-year conviction |
| Accumulation | 7% | 5% | **1-3 month** OBV/A-D trend (was 6-12 month) |

**1Y split: Fundamentals+Valuation = 40%, Technical/Flow = 60%** — inverted from 3Y's 63/37, since near-term price action is driven far more by momentum/technical positioning than slow fundamental convergence. The same regime-tilt mechanism (currently inert, "Neutral", pending the real index-valuation series) applies to both horizons' base weights.

**Recommendation tiers** (identical score→label mapping, applied independently to each horizon):
| Score | Label |
|---|---|
| ≥80 | Strong Buy |
| 65-79 | Accumulate |
| 45-64 | Hold |
| 30-44 | Reduce |
| <30 | Avoid |

## Standardized commentary output (schema locked now — for Phase-2 research agents to fill in later)
Every stock's final record carries exactly 5 short paragraphs, in this order, each crisp (target 40-80 words, no padding, no restating the raw numbers already visible in the score columns):
1. **final_note** — cross-cutting synthesis: why this score, why this recommendation, spanning both horizons in one paragraph.
2. **three_year_positive** — the bull case for the 3-year view.
3. **three_year_negative** — the bear case / key risk for the 3-year view.
4. **one_year_positive** — the bull case for the 1-year view.
5. **one_year_negative** — the bear case / key risk for the 1-year view.

This is the fixed contract Phase-2 qualitative research agents (news, management quality, moat, competitive dynamics) must write into when that layer is built. For any sample produced before Phase 2 exists, these 5 fields are instead populated by **synthesizing the already-computed quantitative pillar scores** into plain-English paragraphs — a mechanical, data-grounded writeup, not yet real qualitative research. Label it as such wherever it appears so nobody mistakes a synthesized note for analyst research.

## Output schema v2 (supersedes the single-horizon schema earlier in this doc)
`symbol | sector | sector_cyclicality_tag | as_of_date | regime_state |` then, duplicated once per horizon (`_3y` / `_1y` suffix) for every pillar sub-score, `composite_raw`, `final_score`, `coverage_pct`, `coverage_flag`, `recommendation` — plus the shared overlay flags `bs_flag | liquidity_flag` (horizon-agnostic, computed once) — plus the 5 commentary columns above (`final_note, three_year_positive, three_year_negative, one_year_positive, one_year_negative`).

## Open risks carried forward
- Three screener sources disagree on coverage — mitigated by a D-009 spot-check on the ALPHA_RANKER pull, not fully resolved.
- Smallcap fundamentals coverage <40% will produce Low-coverage-flagged scores for a meaningful slice of the 750, worse still for DCF specifically (needs 5yr+ consistent FCF).
- Sector cyclicality tagging is a static v1 lookup table, not a dynamic model — reasonable starting approximation, flagged for review once built.
- **Regime-tilt weights and DCF assumptions (discount rate, terminal growth, ERP) are v1 judgment calls** — both need a dedicated sensitivity/perturbation pass before being trusted for anything beyond a research-ranking signal; neither has been validated against forward returns yet (out of scope for this phase by design).
