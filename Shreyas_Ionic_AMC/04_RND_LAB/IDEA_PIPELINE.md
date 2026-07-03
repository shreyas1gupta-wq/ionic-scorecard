# IDEA PIPELINE — stage-gated board (R&D Head owns; RESEARCH_SOP §7 governs)
Gates auto-advance on pass (D-010); **LIVE gate = Principal only**. Every kill → KILLED_IDEAS.md with resurrection condition (D-012). Every variant counts toward the family's trials ledger (DSR honesty).

Stages: `1-INTAKE → 2-TRIAGE → 3-CHEAP-TEST → 4-FULL-BACKTEST → 5-RED-TEAM → 6-IC-MEMO → 7-PAPER → 8-LIVE`

## Board
| Idea | Sleeve | Stage | Owner | Trials | Next action | Kill criteria (pre-reg) |
|---|---|---|---|---|---|---|
| IV/RV short straddle (rich-IV, 210 univ) | Options short-vol | 6-IC-MEMO | Quant | 4 | IC memo + owner + kill criteria | fwd mean <+10%/trade over rolling 6 cycles |
| Earnings short-vol (IV crush, large-cap gate) | Event | 6-IC-MEMO | Quant | 3 | IC memo; codify large-cap + DTE≥7 gates | fwd mean <+5%/event over 2 quarters |
| FF calendar CE (FF≥0.25, tiered, LARGE-CAP only) | Options term-structure | 6-IC-MEMO | Quant | 6+ | IC memo; liquid-back-month gate | fwd mean <+3%/trade over 6 cycles |
| Short strangle 14DTE managed (inverse-IV sizing) | Options short-vol | 6-IC-MEMO | Quant | 5 | IC memo; event-gate + ex-ante sizing wiring | fwd mean <+0.5%/spot over 3 cycles |
| Track-1 delta-hedged 0DTE/DTE1 short straddle (≥0.45% filter) | Index short-vol | 7-PAPER-ready | FM | per HANDOFF | register + paper plan | per original spec |
| Track-2 small-cap momentum machine (Minervini/VCP D1-D14) | Momentum | 2-TRIAGE | Technical+Quant | 0 | engine build spec (data ready) | pre-register before build |
| Track-3 dealer-gamma/GEX regime (OI surface H1) | Positioning | 2-TRIAGE | R&D+ML | 0 | cheap test design | pre-register before build |
| Equity Mom-12-1 + LowVol blend | Momentum/Defensive | 4-FULL-BACKTEST | Quant | 2 | re-run on PIT 500-universe with COST_STANDARDS | DSR<0.95 or PBO>25% |

## Intake queue (one-pager required before entering board)
- Sentiment alpha: FinBERT tone on news tiers (data READY) — needs one-pager.
- PEAD via `available_date` (proxy feed READY) — needs one-pager.
- Gold/Silver ETF sleeve (crisis hedge; tokens on disk) — needs one-pager.
- Expiry-day/reconstitution seasonality (OI surface + snapshots) — needs one-pager.
