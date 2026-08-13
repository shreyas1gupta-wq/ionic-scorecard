# ORTHOGONAL ALPHA — hypothesis list, pre-registered priors (Aditya Verma, R&D)
Written 2026-07-30 BEFORE running any cell below. Per D-035, this file is not edited after results
land; a changed mind is a dated addendum, not a silent rewrite.

## Scope discipline (read SHARED_CONTEXT_20260729.md first)
Today's parallel effort already tested, on THIS dataset, everything that is a transform of NIFTY's
OWN price/option-chain series: 23 price triggers (`EMA_INTRADAY_BUYING`), MA/RSI (`MA_RSI_BREAK`),
multi-timeframe sweeps (`SWEEP_MULTITF`), candle patterns (`CANDLE_MTF` — this very folder's sibling),
regime-ML on price (`REGIME_ML`/`REGIME_GATE`), option-chain volume/OI/IV-skew/VIX-RV indicators
(`INDICATOR_MINE`, `CHAIN_MICRO` pre-reg), calendar/expiry/PCR/OI-Herfindahl/day-of-week/turn-of-month
(`STRUCTURAL_EDGES`), and FII/DII participant flow (`B1_FII_FLOW` KILL, `B1b_FII_CLIENT_SPREAD` PASS
t=2.53, `B1c_DII_FLOW`). None of that is repeated here. My mandate is sources of information the
NIFTY price+chain+domestic-flow series does not itself carry: **cross-market and cross-asset
information, market-internals/breadth, and structural/event mechanisms not yet tried.**

## Ranked hypothesis list with priors (before testing)

| # | Hypothesis | Mechanism (one sentence) | Prior | Data | Decision |
|---|---|---|---|---|---|
| 1 | **Overnight cross-asset shock (US equities/vol/INR/rates/crude) predicts NIFTY's intraday continuation (open->close) direction/magnitude** | Global risk-on/off and FII-flow expectations transmit overnight via ADRs, futures desks and INR; the open should reflect most of it but continuation/fade through the day is a separate, testable question | **MEDIUM** for the overnight move existing (well documented spillover literature); **LOW-MEDIUM** for it being INCREMENTAL beyond the open once GIFT Nifty (launched formally 2022, arbitrages the SGX-Nifty overnight gap into NIFTY's 9:15 open in real time) has already priced it in — my prior is the OPEN captures most of it and continuation is closer to a coin flip, but this is untested here so worth the cheap look | SPX daily close, CBOE VIX daily, USDINR daily (FRED, noon-NY basis), US 10Y yield daily, WTI crude daily (fetched today, D-009 spot-checked) — all in `05_DATA_OFFICE/data/`; NIFTY 1-min spot for the intraday target | **TEST — cheapest, all data already local or one quick verified fetch** |
| 2 | **NIFTY vs BANKNIFTY intraday relative-value dispersion mean-reverts** | Two highly-correlated large-cap indices; BANKNIFTY is financials-concentrated, NIFTY diversified — a sector-driven divergence (financials news, PSU-bank moves) that outpaces the broad market may be a temporary dislocation that reverts as the rotation completes | **MEDIUM** mechanism is sound and textbook (pairs/stat-arb), but professional desks already run this exact trade on these two names — retail-accessible residual edge after cost is uncertain | Both 1-min spot files exist locally (`processed/banknifty_1min.parquet`, `hf_index_options_1m/index/NIFTY.parquet`) | **TEST — cheap, direct** |
| 3 | **NIFTY50 constituent breadth (advance/decline) leads the index's own forward return** | Classic market-internals thesis: when fewer names are participating in a move the index is more fragile (breadth divergence) — an index-LEVEL signal built from 50 individual stock closes, information the index series itself discards | **MEDIUM** mechanism, but classically a multi-day signal not an intraday one — expect this to show up (if at all) at 1-5 day horizons, which still qualifies as "short-horizon" | PIT membership: `Historical stock composition of Nifty 50 and Nifty Next 50.xlsx` (monthly Yes/No, to 2025-10); daily closes: `datasets/derived/pit_union_panel_v1/close_panel_price_v11.parquet` (survivorship-safe, 2000-2026) | **TEST — cheap, daily data only, no 1-min load needed** |
| 4 | Earnings-season clustering of NIFTY's top-10-weight constituents drives index-level vol clusters | 5-6 names are ~35-40% of index weight; their reporting days can move the index materially | LOW-MEDIUM — mechanism real, but the firm's existing event-avoidance work (measured to cut tails 4-8x) likely already captures most of this as a KNOWN-events overlay, not a fresh information source | `datasets/earnings_pit/unified_quarterly_pit.parquet` + NIFTY weights | **DEPRIORITIZED — incremental content over existing event-vol work looks thin; not tested today, flag for later if H1-H3 come back weak** |
| 5 | RBI/MPC policy-day vol pattern as an alpha SOURCE (not just an avoidance filter) | Pre-scheduled event with known date; IV often overstates the realized move | LOW — this is a vol-selling mechanism, and the firm's certified edge (S1-F, 12.57% CAGR) is already a vol-selling strategy; a fresh cut of the same VRP well is not orthogonal in the sense this mandate asks for (new INFORMATION source), it is the same source at a different date filter | Firm macro calendar | **NOT TESTED — not a new information source, just a date filter on an already-owned edge** |
| 6 | Index-vs-sum-of-constituents replication tracking error | If our reconstructed free-float basket diverges from the official index, the gap might mean-revert | LOW — NSE's free-float/adjustment methodology is precise and not cheaply replicable from raw closes; any measured "gap" is more likely OUR reconstruction error than a real tradeable dislocation, and retail cannot cheaply trade a 50-stock basket vs index futures at the tick sizes involved | Would need exact free-float weights, day-count conventions | **NOT TESTED — high build cost, low prior it is anything but a data artifact** |
| 7 | Asian-session lead-lag (Nikkei/Hang Seng opens, both open well before NIFTY's 9:15) | Nikkei opens ~05:30 IST, HSI ~07:00 IST — genuinely SAME-MORNING information NIFTY traders can react to, unlike the US close which is ~7-8 hours stale by 9:15 and already arbed via GIFT Nifty | MEDIUM-HIGH mechanism (better timing story than #1), but **NO LOCAL DATA** — Nikkei/HSI series not found in `05_DATA_OFFICE` or anywhere in this repo | **NOT TESTED TODAY — flag as a D-009 data-acquisition proposal (FRED/Stooq-class or exchange archive for `^N225`/`^HSI`), highest-mechanism candidate on this list if the Principal wants a next step** |

## Cheapest-first order actually executed
H1 (cross-asset, all data local/fetched) → H2 (dispersion, both 1-min files local) → H3 (breadth,
daily-only, no 1-min load). No infrastructure built for #4-6 given weak/duplicated priors; #7 flagged
as the best NEXT step but requires new data outside today's scope.

## Method (binding on every cell below, per task brief)
- Entry at the NEXT 1-min bar's real open (>=09:15, landmine #2) STRICTLY after the signal is fully
  known (overnight signals are known hours before 09:15 IST by construction — verified via
  merge_asof(direction='backward', allow_exact_matches=False) so only a STRICTLY prior session's
  data is used, never same-day).
- Split 2024-10-01; 2026 H1 HELD OUT, reported, selected on nothing (quintile thresholds fixed from
  build data only, applied unchanged to 2026).
- Costs: futures round trip 4.47pts (pre-2024-10-01, STT 0.0125%) / 5.97pts (post, STT 0.020%) +0.5pt
  slippage. BANKNIFTY-leg cost has no firm-approved figure — reported as an [OPINION] proportional
  scaling of the NIFTY futures cost by spot-price ratio, flagged, never presented as approved.
- Placebo: day-block permutation (500 draws, fixed seed), shuffling which day's SIGNAL is paired with
  which day's TARGET while holding each series' own marginal distribution and intraday structure
  fixed. p = fraction of |placebo spread| >= |observed spread|.
- Every cell enters the trials ledger below regardless of outcome.
