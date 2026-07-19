# 10 — Agent Architecture (LLM agents = analyst checklist + orchestration + human gate)

Per brief Q17: agents are **LLM (Claude) research agents that double as a human-analyst checklist**, with **human oversight** and the right to **ask the human on edge cases** — no silent assumptions, no ruinous fallbacks. Reuse the firm's existing 28-agent roster where roles map; add ALPHA_RANKER-specific module agents. Respect max 3 parallel agents (firm D-023).

## Module agents (one responsibility each → one theme/layer)
| Agent | Responsibility | Firm reuse |
|---|---|---|
| **Data/Ingestion** | run scrapers/loaders, enforce D-009 & landmines, freeze schemas | data-officer-kavya-reddy |
| **Technicals & Momentum** | price action, RS, mean-reversion, base/stage — 1M lead | technical-head-dhruv-kapoor |
| **Sentiment/Flow/Positioning** | volume/delivery, F&O OI/PCR/basis, bulk deals, IV | execution-tca-tara-singh (mechanics) |
| **Growth/Earnings-revision** | trajectory, revision breadth, guidance-linked | ml-expert-ishaan-gupta (revision models) |
| **Valuation** | own-history/peer multiples, re-rating, reverse-DCF sanity | quant-head-arjun-rao |
| **Quality/Balance-sheet** | ROCE/FCF/accruals/debt trend, resilience | equity-head-ananya-iyer |
| **Concall/Management** | transcript parsing, promise-vs-delivery, tone shift (rubric below) | sector analysts |
| **Forensic/Red-flag** | full `08` battery → forensic score + flags | compliance-farhan-qureshi |
| **Macro/Oversight** | `03` cascade, regime classification → `regime_state.json` | macro-strategist-cyrus-daruwalla |
| **Sector specialists** | sector tailwind/headwind, structural-disruption read | 5 firm sector analysts |
| **Scoring/Synthesis** | combine themes → [-100,+100] + P + thesis (per `02`) | quant-head + fm |
| **Devil's-advocate / Red-team** | mandatory kill-attempt on 1Y/5Y & any high-conviction call | red-team-nikhil-bose |
| **Overfit/Validation** | IC/DSR/PBO, lookahead audit, sensitivity | overfit-analyst-sameer-bhat |
| **Portfolio/Risk oversight** | sizing, liquidity caps, correlation, veto | cio-rajan-mehta / risk-manager-ritika-sharma |

## Concall / management rubric (the "promise-tracking" engine)
Parse each transcript into structured items and score across quarters:
- **Guidance items** extracted (revenue/margin/capex/demand) → tracked vs *actual delivery* next quarters → a **credibility score** per management.
- **Tone shift** vs prior calls (confidence, hedging language, defensiveness on hard questions).
- **Capex/capital-allocation language**, new-order/demand commentary, competitive commentary.
- **Red-flag phrases** (recurring "one-off", blaming externals, evasive answers, sudden guidance withdrawal).
Output feeds Growth (1Y), Management (5Y), and Forensic themes.

## Orchestration (per-stock pipeline)
```
Data/Ingestion ─▶ [Technicals ∥ Sentiment ∥ Growth ∥ Valuation ∥ Quality ∥ Concall ∥ Forensic]  (parallel, ≤3 at a time)
                        │
   Macro/Oversight + Sector (regime_state, tailwind/headwind) ─┐
                        ▼                                        ▼
                 Scoring/Synthesis  ──▶  Devil's-advocate/Red-team  ──▶  Human gate (edge cases / low-confidence)
                        │                                                        │
                        ▼                                                        ▼
              score + P + thesis                                     analyst override (logged) or issue
```
- **Human-in-the-loop triggers:** low `confidence`, data gaps on load-bearing factors, hard-veto flag active, red-team and synthesis disagree, or score near a sizing threshold. The agent surfaces the specific question — it never guesses.
- **Cost discipline:** cheapest model per role (haiku=mechanical parsing/ingestion; sonnet=analysis/forensics/red-team; opus=final synthesis/IC judgment). Batch stocks; scripts over agents for anything computational (firm TOKEN_POLICY). D-036: don't default synthesis to opus for routine re-scores — reserve opus for genuinely ambiguous, capital-facing calls.

## Run modes
- **Batch re-score** (monthly 1M / semi-annual 1Y & 5Y & microcap): scripted factor computation → agents only for qualitative themes + synthesis on the shortlist.
- **Single-stock deep dive**: full agent pipeline + mandatory red-team.
- **Alert-driven**: forensic flag / bulk deal / guidance change → targeted re-score.

## Output & audit
Every issued score writes the full `02` §5 contract + `overrides[]` (who/what/why) to `reports/<ticker>/<lens>_<date>.json` and a human-readable one-pager. Track-record is permanent (like the firm's IC memos) so calibration and self-improvement have ground truth.
