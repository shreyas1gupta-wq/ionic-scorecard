# `alpha_research/` — honest current-state assessment
**By:** Prof. Aditya Verma, Head of R&D · 2026-07-18 · [DATA]/[INFERENCE]/[OPINION] tagged throughout.
**Scope:** legacy read-only folder `alpha_research/` (never moved/edited), cross-checked against the
much larger `ALPHA_RANKER/` program (473-card cross-sectional cash-equity research).

## 1. What was planned
`alpha_research/PLAN.md` (153 lines, built 2026-06-16) proposes an 8-hypothesis portfolio (H1-H8) under
one thesis: stop predicting price/value (saturated/crowded) and instead model the **state & fragility of
the market's own constrained participants** (dealers, retail F&O, FIIs/DIIs, leveraged shorts) — direction-
agnostic, capacity-limited moats (B: forced flows, C: complexity, D: new modality). Ranked:
H1 dealer-gamma/GEX ★lead, H2 retail-F&O crowding, H3 liquidity-fragility/air-pocket, H4 lead-lag network,
H5 LLM narrative-inflection, H6 meta-regime allocator, H7 reflexivity/squeeze, H8 FII/DII participant flow.
A 6-phase program (P1 frontier scan → P6 paper/live) was specified. **[DATA]** Next-session entry point
named: H1 sub-task 1 (reconstruct NIFTY OI/gamma surface, compute GEX & zero-gamma flip).

## 2. What's actually been done — INSIDE `alpha_research/` itself: NOTHING
**[DATA] Verified via `git log --all --follow -- alpha_research/`: exactly one commit touches this folder
(`e27a578`, 2026-07-03), and `git show --stat` on it shows a single file added — `PLAN.md`, 153 insertions,
0 deletions.** `find alpha_research -type f` returns only `PLAN.md`. No code, no data, no results, no
kill log has ever been written inside this folder. It is a pure plan, untouched since creation — P1-P6 are
all still `[ ]` unchecked. This is the single most important honest fact in this assessment: **the folder
itself is 100% planned, 0% executed.**

## 3. But the *ideas* leaked into other sessions — per-hypothesis reality check
Searching the rest of the repo (code+docs, `git log`, `IDEA_PIPELINE.md`, `KILLED_IDEAS.md`,
`SESSION_JOURNAL.md`) shows several H1-H8 mechanisms were independently picked up elsewhere, at varying
degrees of completion — never inside `alpha_research/`, and never cross-referenced back to this plan.

| # | Hypothesis | Real status found | Evidence |
|---|---|---|---|
| **H1** Dealer-gamma/GEX | **Hypothesis one-pager exists, cheap-test SPEC'D, 0 trials run.** Stage 1-INTAKE in `IDEA_PIPELINE.md`. Blocked/HOLD on a data caveat: NIFTY OI surface (`datasets/derived/nifty_oi_surface.parquet`, 377,034 rows) is only a **402-date sparse snapshot (~31% of ~1,300 trading days)**, BANKNIFTY OI stops 2024-07, and the one-pager states **no spot/underlying price column exists** so GEX can't be computed. | `Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260703_dealer_gamma_gex.md`; `IDEA_PIPELINE.md` row |
| **H2** Retail-F&O crowding/PCR | **Never tested as a signal.** FACTOR_LIBRARY lists PCR/max-pain/GEX as "READY" data-wise but only as descriptive context for the live short-vol sleeves (S-01..S-04), never as a standalone cheap-tested predictive signal. No results file anywhere. | `FACTOR_LIBRARY.md` row 23; no hits in `USABLE_ALPHA_INVENTORY.md` |
| **H3** Liquidity fragility/air-pocket | **A narrower version WAS tested and KILLED (2026-07-11).** `B2_AIRPOCKET_OVERLAY_20260711`: leg-buyback overlay on S1, 259 expiry days, spec frozen. **Real numbers:** baseline +8.02 pts/day (t=2.94) vs overlay +7.79 pts/day (t=2.87); mean uplift required ≥+1.0pt got **−0.23**; worst-10 improvement required ≥+15pts got **+5.9**; SL-hit-day improvement required >0 got **−0.16**. Triggers fired 77/259 days (30%); on non-event days overlay dragged **−1.87 pts/day**. The underlying "air-pocket" price-traverse effect measured *real* (T6 control +4.4 pts/30min, t=3.94) but monetizing it via early leg-buyback is net-negative — false triggers cost more than true-positive tail savings. **This kills the narrow "trade the discontinuity" construction, NOT the broader H3 framing** ("does a fragility feature beat implied vol as a realized-vol forecaster" — that framing was never tested). | `Shreyas_Ionic_AMC/04_RND_LAB/results/B2_AIRPOCKET_OVERLAY_20260711/RESULTS.md` |
| **H4** Lead-lag network | **Started, abandoned mid-session, no verdict.** `MIDCAP_LEADLAG_20260714/` has `leadlag_discovery.py`, `swing_reversal_test.py`/`_v2.py`, and a merged midcap+NIFTY 1-min parquet — but no results/verdict file, and no `IDEA_PIPELINE`/`KILLED_IDEAS` entry. Journal (2026-07-14): work began per Principal request on midcap/microcap intraday lead-lag for NIFTY options timing, but "per-stock intraday spot data confirmed NOT available this session" — genuinely **unfinished**, not killed, not proven. | `Shreyas_Ionic_AMC/01_COMMAND_CENTER/SESSION_JOURNAL.md` line 566 |
| **H5** LLM narrative-inflection | **Zero hits anywhere in the repo** outside `PLAN.md`. Completely untouched. | grep across all `.md`/`.py` |
| **H6** Meta-regime allocator | **Zero hits anywhere.** Completely untouched (the closest analog, WAVE4's cross-asset sizing-scalar work, is a different, narrower question — VIX/breadth-vs-copper/gold sizing dials, not a cross-*sleeve* Sharpe-predicting allocator). | grep across all `.md`/`.py`; `WAVE4_FINDINGS.md` §2 |
| **H7** Reflexivity/squeeze | **Zero hits anywhere.** Untouched (depends on H1+H2, both themselves largely untested). | grep |
| **H8** FII/DII participant flow | **A DIFFERENT mechanism was tested and killed — do not conflate.** ALPHA_RANKER's "FII/DII accumulation" (`builders_w2_flow.py`, card W2S-03) is a **stock-level quarterly shareholding-drift cross-sectional factor** (rising FII+DII % ownership QoQ → forward return), killed **wrong-sign**, on `FRONTIER_OPUS.md`'s do-not-retest list. H8 as stated in `alpha_research/PLAN.md` proposes **daily index-level FII/DII cash+F&O net flow + participant-wise OI as a market-TIMING signal for next-day/week NIFTY direction** — a different granularity and a different mechanism entirely. `MACRO_XASSET.md` line 185 explicitly flags: *"FII/DII flow data — mentioned in this agent's charter (regime notes) but not available."* **The daily flow series was never even acquired — H8-as-stated remains untested, and its kill on the ALPHA_RANKER side would be a false-equivalence if cited.** | `ALPHA_RANKER/rnd/lib/builders_w2_flow.py`; `ALPHA_RANKER/rnd/wave4/COVERAGE_MAP.md` line 88; `MACRO_XASSET.md` line 185 |

## 4. Overlap vs ALPHA_RANKER — the real gap
ALPHA_RANKER is a ~473-card program, entirely **cash-equity cross-sectional stock-selection**
(fundamentals, momentum, quality, forensic-accounting, sector/market regime gates, cross-asset sizing
scalars). It has **never** touched: dealer/options positioning, liquidity-fragility-as-vol-forecast,
daily index-level FII/DII flow timing, lead-lag networks, or LLM narrative-inflection. The one
superficial-looking overlap (H8/"FII-DII") is a false match on mechanism, per §3 above.
**[INFERENCE] `alpha_research/`'s 8 dimensions are almost entirely orthogonal to ALPHA_RANKER by asset
class and mechanism (derivatives/positioning/flow vs. cash-equity cross-sectional factors) — this is a
genuine gap, not a re-test risk**, and is consistent with this quarter's Lessons Learned that universe/
data-coverage expansion (not new stock-selection signals) has been the highest-value recent unlock.

## 5. Light first-pass done this session: H1's stated data blocker is FALSE — it's unblocked
The H1 one-pager's kill-relevant blocker was "no spot/underlying price column" for GEX. **[DATA] Verified
`datasets/index_daily/nifty50.parquet` exists: 2,581 rows, daily OHLC, 2016-01-04 → 2026-07-03, tz-aware
IST timestamps** — this file was simply not searched for in the earlier pass (`datasets/derived/` only).
Joined against the OI surface's 402 distinct `trade_date` values: **400/402 (99.5%) match**, the 2 misses
being Jan-1 (non-trading days that shouldn't be in the OI surface at all — worth a separate data-quality
flag to Kavya Reddy). The S-04 strangle P&L file for the third kill-criterion leg is also confirmed present
(`FINAL_STRATEGY_FORWARD_CHECK/04_Short_Strangle/strangle_trades.csv`, 5,031 rows).
**This means the pre-registered H1 cheap-test (bucket ~402 NIFTY snapshot days by GEX sign under both
candidate conventions, compare next-day realized range + S-04 strangle P&L by bucket) can run TODAY** —
no new data acquisition needed, no D-009/D-033 gate required (all files already on disk and previously
verified). I did not build the full IV-back-solve + Black-Scholes-gamma pipeline myself in this pass —
that is genuine options-quant engineering (Newton-Raphson IV solve across ~377K rows, sign-convention
handling, lookahead audit) that belongs with Ishaan Gupta (ML) or Arjun Rao (Quant), not a 10-minute
side-check — but the blocker that was stalling it is resolved.

## 6. Single most valuable next step
**Run H1's already-fully-specified cheap-test now** (`ideas/20260703_dealer_gamma_gex.md`), using
`datasets/derived/nifty_oi_surface.parquet` + the now-confirmed `datasets/index_daily/nifty50.parquet`
spot join + `strangle_trades.csv`. It has the most infrastructure already built of any of the 8 hypotheses,
its only stated blocker just evaporated, it is genuinely untested by ALPHA_RANKER (orthogonal mechanism —
derivatives positioning, not a cash-equity factor), and its kill criteria are already pre-registered
(no p-hacking risk). Per this firm's discipline, the ~402-day sample (~80/quintile) means a null or weak
result should NOT be treated as a kill on small-n grounds alone — only a wrong-sign-under-both-conventions
or genuinely-flat result kills it; a low-t-but-correctly-signed result should route to forward-test/watch,
same treatment ALPHA_RANKER gave its own low-t rescues this wave.
Second-priority, cheaper still: log H4 (lead-lag) properly into `IDEA_PIPELINE.md`/`KILLED_IDEAS.md` as
UNFINISHED (not silently dropped) — the code and merged dataset already exist and just need someone to
re-check whether the "no per-stock intraday spot data" blocker from 2026-07-14 has since been resolved by
the universe-expansion / bhavcopy work done since.

## Files referenced (absolute paths)
- `alpha_research/PLAN.md`
- `Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260703_dealer_gamma_gex.md`
- `Shreyas_Ionic_AMC/04_RND_LAB/IDEA_PIPELINE.md`
- `Shreyas_Ionic_AMC/04_RND_LAB/results/B2_AIRPOCKET_OVERLAY_20260711/RESULTS.md`
- `Shreyas_Ionic_AMC/04_RND_LAB/results/MIDCAP_LEADLAG_20260714/` (leadlag_discovery.py, swing_reversal_test.py, swing_reversal_test_v2.py, midcap_nifty_merged_1min.parquet)
- `Shreyas_Ionic_AMC/01_COMMAND_CENTER/SESSION_JOURNAL.md` (line 566)
- `ALPHA_RANKER/rnd/lib/builders_w2_flow.py`
- `ALPHA_RANKER/rnd/wave4/COVERAGE_MAP.md`, `ALPHA_RANKER/rnd/wave4/FRONTIER_OPUS.md`, `ALPHA_RANKER/rnd/wave4/MACRO_XASSET.md`
- `ALPHA_RANKER/rnd/wave4/WAVE4_FINDINGS.md`, `ALPHA_RANKER/rnd/scorecard/USABLE_ALPHA_INVENTORY.md`
- `datasets/derived/nifty_oi_surface.parquet` (377,034 rows, 402 dates), `datasets/derived/banknifty_oi_surface.parquet`
- `datasets/index_daily/nifty50.parquet` (2,581 rows, 2016-01-04→2026-07-03) — **newly confirmed usable for the H1 spot join**
- `FINAL_STRATEGY_FORWARD_CHECK/04_Short_Strangle/strangle_trades.csv` (5,031 rows)
