# FACTOR LIBRARY v1 — the research menu (Principal's mandate; R&D Head curates)
Every idea maps to a sleeve here. Per-sleeve production gate: IC memo with economic WHY, expected decay horizon, capacity estimate, crowding check.

## Traditional factors (long-term, academically validated premia)
| Factor | Definition | Primary metrics | Data status |
|---|---|---|---|
| Value | cheap vs fundamentals | earnings yield, P/B, P/CF, EV/EBITDA | READY — screener_deep, ratios_pit, mc_fundamentals |
| Quality | durable profitability | ROE/ROCE, low leverage, earnings stability, F-score, accruals | READY — same |
| Momentum | 6–12M price strength | 12-1 momentum, 52w-high proximity, residual momentum | READY — daily 2005-26 + 42 PIT snapshots |
| Size | smaller-cap premium | mcap rank — only WITH quality + liquidity screens | READY |
| Earnings Revision | upgrades/surprise | SUE, beat/miss streaks, revision breadth | PROXY — beat_miss (31,891) + PEAD via available_date; real estimates feed = D-009 candidate (Trendlyne) |
| Microstructure | flow/liquidity effects | volume spikes, Amihud, VWAP deviation, auction behavior | READY — 813M 1-min bars (mind landmines 1-2) |

## Commodity sleeve
Gold = crisis + inflation hedge · Silver = precious + industrial hybrid. ETF route (GOLDBEES/SILVERBEES — tokens in `datasets/angel_instrument_list.json`), no MCX needed. Status: data trivial, one-pager pending.

## Proprietary edge sleeves
| Sleeve | Content | Data status |
|---|---|---|
| Sentiment Alpha | NLP tone on news/social/call-transcripts (FinBERT; lexicon baseline FIRST) | READY — india_fin_news 125K + MiMIC 1,042 calls |
| Flow & Ownership | FII/DII pressure, ETF flows, promoter/institutional deltas, volume spikes | PARTIAL — shareholding_changes (21,713) READY; daily FII/DII + bulk/block = NSE-blocked → home-network list |
| Event & Seasonality | corporate actions, quarterly patterns, index reconstitution, expiry effects | READY — corporate_action_factors (613), PIT calendar, snapshots, OI surface |
| Options/Positioning (firm extension) | PCR, max-pain, dealer-gamma/GEX regimes; VRP harvesting (the live short-vol sleeves) | READY — OI surface 633K rows; S-01..S-04 in production pipeline |
| ML Signals | non-linear/regime-specific (LightGBM ranker, HMM vol-states); NO deep learning (D-011) | READY — rule: linear/rank baseline must clear costs first |

## Sleeve rules of engagement
1. One-pager (RESEARCH_SOP) before any code. 2. Cheapest falsification first. 3. Family trials ledger feeds DSR honesty. 4. Cap-tier gating is sleeve-specific (KNOWLEDGE_BASE lesson 5). 5. Every production sleeve gets a monthly edge-decay score; 2 consecutive fails → auto-demote to paper.
