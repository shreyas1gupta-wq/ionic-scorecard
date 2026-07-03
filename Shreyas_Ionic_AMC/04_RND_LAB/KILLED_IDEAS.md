# KILLED IDEAS — graveyard with resurrection conditions (D-012)
Append-only. Every kill: what, when, WHY (evidence), and the SPECIFIC condition that would reopen it. Kills are conditional, never dogma — count them in the family trials ledger.

| # | Idea family | Killed | Evidence | Resurrection condition |
|---|---|---|---|---|
| K-001 | Intraday NIFTY option BUYING (~14 variants: ORB, mean-rev, shakeout, doji, gap-fade, regime-gated, 0.7Δ/0.3Δ combos, expiry-vol-breakout, Europe-open, RSI/MACD/S-R timing...) | 2026-06 | ALL net-negative after costs across 2021-26; VRP means buyers structurally overpay; theta+slippage eat every timing edge tested | A sniper-entry variant with <5 trades/mo showing net-positive after 2× COST_STANDARDS on a fresh OOS window |
| K-002 | Reverse calendar (BUY near / SELL far) | 2026-07 | −174% cumulative; structurally short theta-of-term-structure the wrong way | None foreseseen — structural (would need persistent term-structure INVERSION regime detector) |
| K-003 | Double calendar (CE+PE both legs) | 2026-07 | Forward-NEGATIVE on both 88 and 210 universes (−4..−8% fwd at every FF threshold, both slippage tiers) while single-CE positive — PE leg is dead weight (put skew keeps back PEs rich) | PE-leg variant profitable on its own forward window |
| K-004 | Long far-OTM options at high IV (IV>60%, IV/RV>2 "cheap convexity") | 2026-07 | Loses at every distance (−12..−39%); high IV = wings expensive; buying pre-earnings IV = eating the crush; n small and IV prints partly bad | LOW-IV pre-catalyst long-vol variant (buy cheap vol BEFORE the market prices the event) — untested, legitimate |
| K-005 | 0DTE NIFTY iron condor (all configs) | 2026-06 | Negative all parameter cells | Regime-gated variant if intraday IV-crush regime detector built |
| K-006 | Naked-PE-below-50DMA & other regime-gated naked selling variants | 2026-06 | No robust improvement over unconditional; several negative | New regime feature with WALK-FORWARD proof |
| K-007 | Gap-fade CE/PE selling (0.3/0.6/0.9% gates, SL grid) | 2026-07 | Not robust across build/forward after the pre-open-auction bug fix | Re-test post-2026 only if gap-frequency regime returns |
| K-008 | Stop-losses on FF calendars | 2026-07 | Gaps jump through stops (worst only −249%→−182%); loose stops INCREASE blowups 7→11 via whipsaw of recoverable trades | Intraday (not EOD) stop engine with real fill modeling |
| K-009 | Pre-bought both-wing hedges on FF calendars | 2026-07 | Theta bleed kills mean (+16.7%→+1..14%); far-OTM single-stock wings unpriceable (stale prints → −883% artifact) | Index-wing overlay (liquid) hedging a single-stock calendar BOOK, not per-trade wings |
| K-010 | Retro-fit "landmine blacklist" for strangle stocks | 2026-07 | LOOKAHEAD — picked by realized outcomes; only modest persistence (fwd worst −6.2% vs −3.8%) | N/A — replaced by ex-ante inverse-IV sizing + liquidity gate + adaptive stop-list (see KNOWLEDGE_BASE) |

## Watch-list (not killed, demoted pending proof)
- FF calendar on MID-CAPS: fwd edge thins (+6-7%) and single trades hit −141% (KAYNES) — demoted to large-cap-only until liquid-back-month gate is coded.
- Mid-cap earnings short-vol: lottery-like (+150%/−31% swings) — large-cap gate + DTE≥7-to-expiry rule pending codification.
