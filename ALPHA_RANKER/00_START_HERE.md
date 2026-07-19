# ALPHA_RANKER — START HERE

**What this is:** a multi-horizon, regime-aware, probabilistic **conviction engine** for Indian equities that guides a techno-funda research analyst — NOT a rigid classifier. It outputs a conviction score in **[-100, +100]** plus an explicit probability of a positive return, an expected-return distribution, a win-rate, and a one-paragraph thesis, for four holding-period lenses.

**Four frameworks (one per lens — factors AND their weights differ by horizon):**
| Lens | Universe | Character | Update cadence |
|---|---|---|---|
| **1M** | NIFTY 750 | Systematic / quant-heavy (price action, flow, positioning, catalyst, mean-reversion, trigger, volume-news-gapup/down) | Month-end |
| **1Y** | NIFTY 750 | Blend (earnings trajectory + revisions + valuation re-rating + relative strength) | Semi-annual (Dec/Jul) + quarterly track |
| **5Y** | NIFTY 750 | Discretionary / growth-valuation-quality-moat heavy | Semi-annual → annual |
| **MICROCAP** | Beyond top 750 | Exclusive lens: promoter integrity, business model, base formation, forensics, mispricing-from-neglect | Semi-annual + event-driven |

**Non-negotiable design principles** (from the Principal's brief):
1. **No hard thresholds** (no `ROE>15%`, no `growth>20%`). Every factor is scored *relative to* peer set, own history, sector, cap, and regime.
2. **Weights are a function of (horizon × regime × sector × cap × stock idiosyncrasy)** — never fixed.
3. **Red flags scale with size and regime.** A promoter pledge is near-benign in a low-yield uptrend on a cheap quality name; it is near-suicidal in a high-yield credit-scare downtrend on an overvalued name. Judgment, not rules.
4. **Cross-horizon coupling:** a large negative 1M score taxes the 5Y score (entry-timing penalty). Otherwise the four scores are independent.
5. **Human-in-the-loop, no silent fallbacks.** Agents ask the analyst on edge cases; no assumption that could ruin a call is made silently.
6. **Alpha must be earned, not assumed.** Every factor/weight enters only after the R&D loop (backtest + IC + DSR/PBO + ablation) shows it adds probability or alpha. This requires the **1000+ test iteration program** (see `13_EXECUTION_PIPELINE.md` Phase 7).

## Read order
1. `01_PHILOSOPHY_AND_ARCHITECTURE.md` — the thesis, why-not-a-classifier, horizon theory, the whole stack.
2. `02_SCORING_ENGINE.md` — how factors become a [-100,+100] score + probability + win-rate.
3. `03_OVERSIGHT_CASCADE.md` — global→national→sector→stock regime & tailwind/headwind layer.
4. `04..07_FRAMEWORK_*.md` — the four lenses (1M / 1Y / 5Y / MICROCAP).
5. `08_FORENSICS_REDFLAGS.md` — AMC-grade forensic/red-flag module.
6. `09_DATA_LAYER.md` — exact sources, scrapers, screener fields, Bloomberg screen mnemonics, HF datasets.
7. `10_AGENT_ARCHITECTURE.md` — LLM agents = analyst checklist + orchestration + human gate.
8. `11_BACKTEST_CALIBRATION.md` — PIT universe, walk-forward, IC/DSR/PBO, score→probability calibration.
9. `12_RND_READING_LIST.md` — papers/books/AMC methodologies to mine for edge.
10. `13_EXECUTION_PIPELINE.md` — the phased roadmap + massive subplan tree for the execution session.
11. `PROGRESS.md` — living checkpoint; update after every step.

## How this transfers to the $100 execution session (the handoff)
- This laptop is the shared medium (same pattern as the firm's DESK-20/DESK-100). The **folder itself is the transfer vehicle** — the other session reads `ALPHA_RANKER/` directly. Nothing needs to be pasted except the kickoff prompt.
- Paste `PROMPT_FOR_HANDOFF_SESSION.md` into the $100 session verbatim. It tells that session to read this folder, adopt the plan, and begin at `13_EXECUTION_PIPELINE.md` Phase 0.
- If the other session is on a **different machine**, zip the whole `ALPHA_RANKER/` folder and drop it in; the docs are fully self-contained.
- Every session updates `PROGRESS.md` (goal / DONE / exact NEXT / output paths) so any restart or the other login resumes mid-task with zero context loss.

## Relationship to the firm
This is a standalone R&D build but reuses the firm's assets where they help: the PIT universe file, earnings-PIT dataset, `04_RND_LAB/lib/guards.py`, `lib/lookahead_audit.py`, the overfit/DSR-PBO tooling, and the 28-agent roster (sector analysts, red team, overfit analyst, quant head). See `10_AGENT_ARCHITECTURE.md`.
