# IDEA PIPELINE — stage-gated board (R&D Head owns; RESEARCH_SOP §7 governs)
Gates auto-advance on pass (D-010); **LIVE gate = Principal only**. Every kill → KILLED_IDEAS.md with resurrection condition (D-012). Every variant counts toward the family's trials ledger (DSR honesty).

Stages: `1-INTAKE → 2-TRIAGE → 3-CHEAP-TEST → 4-FULL-BACKTEST → 5-RED-TEAM → 6-IC-MEMO → 7-PAPER → 8-LIVE`

## Board
| Idea | Sleeve | Stage | Owner | Trials | Next action | Kill criteria (pre-reg) |
|---|---|---|---|---|---|---|
| IV/RV short straddle — [IC memo: SEND-BACK](../03_RESEARCH_DESK/memos/20260703_S01_ivrv_short_straddle.md) | Options short-vol | **SEND-BACK to Gate-3/backfill (DSR 0.687, PBO 55%)**; paper-tracking approved (firewalled) | Arjun (resurrection) / Vikram (paper) | 13 | backfill 2018+2020 vol-crash data; fix live IV-cap; per-trade sizing | registered edge +11.4pts incremental; resurrection conditions in memo §3c |
| Earnings short-vol (IV crush, large-cap gate) | Event | 6-IC-MEMO | Quant | 3 | IC memo; codify large-cap + DTE≥7 gates | fwd mean <+5%/event over 2 quarters |
| FF calendar CE (FF≥0.25, tiered, LARGE-CAP only) | Options term-structure | 6-IC-MEMO | Quant | 6+ | IC memo; liquid-back-month gate | fwd mean <+3%/trade over 6 cycles |
| Short strangle 14DTE managed (inverse-IV sizing) | Options short-vol | 6-IC-MEMO | Quant | 5 | IC memo; event-gate + ex-ante sizing wiring | fwd mean <+0.5%/spot over 3 cycles |
| Track-1 delta-hedged 0DTE/DTE1 short straddle (≥0.45% filter) | Index short-vol | 7-PAPER-ready | FM | per HANDOFF | register + paper plan | per original spec |
| Track-2 small-cap leadership momentum, regime-gated — [engine spec](ideas/20260703_track2_engine_spec.md) | Momentum | **3-CHEAP-TEST (triage PASSED 2026-07-03)** | FM-Equities (Devika) + DESK-100 | ≥4 (prototype carried as prior: +11.6%/+16.1% OOS post-survivorship-fix) | DESK-100 build list DATA-11→GATE-11; FIRST confirm corporate-action adjustment of daily panel | 6 pre-registered kills in spec; likeliest: volume/liquidity gate erases edge vs N500 B&H |
| Track-3 dealer-gamma/GEX **regime GATE** for S-01..S-04 — [one-pager](ideas/20260703_dealer_gamma_gex.md) | Positioning | 1-INTAKE | ML (Ishaan) | 0 | Data Officer: fix OI-surface cadence gap (only 402/~1300 days, BANKNIFTY stale post-2024-07, no spot/IV col); then quintile cheap-test BOTH sign conventions vs strangle P&L | GEX buckets show no monotonic next-day-range or sleeve-P&L difference under EITHER sign convention |
| Equity Mom-12-1 + LowVol blend | Momentum/Defensive | 4-FULL-BACKTEST | Quant | 2 | re-run on PIT 500-universe with COST_STANDARDS | DSR<0.95 or PBO>25% |
| Sentiment alpha (lexicon-first tone, 210 univ) — [one-pager](ideas/20260703_sentiment_alpha.md) | Sentiment | 1-INTAKE | R&D | 0 | triage: lexicon top-vs-bottom quintile on tier-1 news | tier-1 1-day tone spread <+3bps/day gross OR matches tone-shuffled placebo |
| PEAD via `available_date` (beat/miss proxy, liquidity-gated) — [one-pager](ideas/20260703_pead_available_date.md) | Earnings Revision | 1-INTAKE | R&D | 1 | triage: liquid-bucket surprise-decile 20-day drift | liquid-bucket top-minus-bottom 20d drift <+1.5%/event gross OR edge only in illiquid bucket |
| Gold/Silver ETF sleeve (crash diversifier + trend overlay) — [one-pager](ideas/20260703_gold_silver_sleeve.md) | Commodity | 1-INTAKE | R&D | 0 | triage: gold return in worst-equity-decile days (needs ETF price series — D.O. fetch) | gold mean return in worst equity-decile days <0 OR tail corr to NIFTY >+0.3 |
| Expiry/reconstitution/turn-of-month seasonality (post-Sept-2025 regime) — [one-pager](ideas/20260703_expiry_seasonality.md) | Event & Seasonality | 1-INTAKE | R&D | 0 | triage: reconstitution event study on 42 PIT add/drop snapshots | add-name abnormal return indistinguishable from matched-control placebo OR effect only survives pre/post-Sept-2025 pooling |

## Intake queue (one-pager required before entering board)
_(empty — 2026-07-03: all four queued ideas promoted to the Board at 1-INTAKE with one-pagers filed in `ideas/`.)_
