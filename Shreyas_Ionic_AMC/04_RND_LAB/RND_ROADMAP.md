---
title: R&D Roadmap
type: roadmap
status: living document
created: 2026-07-24
owner: R&D Head (Aditya Verma) — Principal-readable
tags: [rnd, roadmap, integration]
---

# R&D Roadmap

**What this file is:** an integration map, not a fresh research plan. Everything below either points at existing firm infrastructure that already answers a question, or scopes a genuinely new contribution from the 2026-07-24 DESK-20 session against that existing baseline. Written after discovering — mid-session — that several things built fresh this session already existed in more rigorous form. Read this before starting new R&D work in any of the areas below, so the same rediscovery doesn't happen a third time.

## 1. What already exists (read these before rebuilding anything)

| Document | What it covers | Why it matters |
|---|---|---|
| [[IDEA_PIPELINE]] | Stage-gated board (1-INTAKE → 8-LIVE), every live/killed idea with pre-registered kill criteria | The process. Any new idea enters here, not as a standalone analysis. |
| [[KNOWLEDGE_BASE]] | 25+ hard-earned firm lessons (Section A) + reference library of papers/books/repos (Section B) | Check Section B before scouting papers/repos "from scratch" — much of it is already there. |
| [[FACTOR_LIBRARY]] | The research menu — Value/Quality/Momentum/Size/Earnings-Revision/Microstructure + proprietary sleeves, data status per factor | Scope check for any new factor idea: is this already READY/PARTIAL in our data? |
| `scout_github_oss.md` | Complete OSS-library maintenance-status audit (2026-07-04), 3 sub-agents, ranked adoption table + keep-out list | **pandas-ta is ABANDONED** (original repo 404s; successor "pandas-ta.dev" wiped history, soliciting donations) — community moved to `pandas-ta-classic` (xgboosted). quantstats is "slowing"; `quantstats-lumi` fork is the safer bet. This session's own gs-quant/quantstats/pandas-ta work (below) needs correcting against this. |
| `scout_papers_agents.md` | India-specific quant paper scouting (VRP, F&O-expiry, PEAD, dealer-gamma) + agent self-improvement methods (Reflexion/LLM-judge/Voyager/FinCon) | Don't re-scout India VRP/PEAD/dealer-gamma papers — done. The agent-self-improvement half (Part B) is directly relevant to "improve the agentic system" asks — several mechanisms already ranked ADOPT/ADOPT-LITE, worth checking before any future agentic-system work. |
| `scout_hf_kaggle.md` | HuggingFace models + Kaggle methods survey — FinBERT baseline, TSFM verdict (WATCH not ADOPT, they mostly don't beat random walk), Indian Kaggle datasets (thin, skip) | Relevant if ML-signal work resumes. |
| `openalgo_eval.md` | Angel-native options paper-trading sandbox eval — VERDICT: pilot one strategy | Directly relevant to the Principal's own options-trading use case; not yet piloted. |
| **`datasets/derived/benchmarks_random/` (D-029)** | THE firm's random-basket benchmark suite — Principal-mandated minimum bar for every equity strategy. 10,000 permutations, quarterly rebalance, proper PIT segments (Large=N100/Mid=N200-N100/Small=N500-N200), stale-price + circuit-lock guards, corrected terminal-percentile methodology | **Supersedes this session's ad-hoc random-benchmark work (see §3 below) as the reference.** Any strategy evaluation — including STOCK_SCORECARD_750 — should be checked against this, not a fresh rebuild. |

## 2. This session's genuinely new contributions (2026-07-24, DESK-20)

Scoped honestly against §1 — these are additions, not replacements of existing infra, except where flagged:

- **`lib/scorecard_common.py`** + the token-wise §10 reuse convention — new shared code library for STOCK_SCORECARD_750, plus a firm-wide (not just scorecard) rule about consolidating genuinely-reused functions. Not covered by any existing scout.
- **`gs-quant-timeseries` skill** — verified which `gs_quant.timeseries` functions are genuinely credential-free (RSI/SMA/vol/returns/beta/correlation/MACD/Bollinger/drawdown/z-score) vs. which look free but need Goldman Marquee (`sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `skew`, `information_ratio`). This specific trap wasn't in `scout_github_oss.md` (gs-quant wasn't in its known-baseline list) — genuinely new.
- **`options-python-libs` + `nse-data-libs` skills** — verified by execution: `vollib` (adopt, replaces `py_vollib` naming), `QuantLib` (adopt-partial, installs fine on our Python 3.14 via cp39-abi3 wheel), `optopsy` (adopt-partial, silent-empty-on-no-match trap found), `jugaad-data` (adopt, confirmed office-network-safe for historical options+bhavcopy), `nsepython` (home-net only), `nsepy` (confirmed broken on Python 3.14, PEP 667 `f_locals` issue). This is MORE current and execution-verified than `scout_github_oss.md`'s Agent B pass (which covered nsepy/nsepython/jugaad-data at the maintenance-status level, not with live smoke tests) — worth keeping both, cross-link them.
- **Momentum-50 / Low-Vol-30 replication validation** — built our own approximation of NIFTY 500 Momentum 50 and NIFTY 100 Low Vol 30 using the canonical `pit_union_panel_v1` + real historical membership, checked against the actual official index NAVs already sitting in `factor_navs_principal.parquet`. Low Vol 30 tracks well (TE 4.5%, CAGR within 0.9%/yr); Momentum 50 captures direction but has a real ~2.9%/yr full-window CAGR gap traced to pre-2015 universe-matching thinness + likely ex-dividend vs TRI basis. This is a genuinely new data-pipeline-quality check, not previously done. **Files:** `Shreyas_Ionic_AMC/04_RND_LAB/results/FACTOR_REPLICATION_CHECK_20260724/`.
- **Extended random-benchmark-vs-Nifty series (v5-v8)** — pushed a fresh random-basket analysis back to 2005 using real NIFTY500_TICKER PIT snapshots, tested N=25/50/100 at equal- and rank-mcap-weighting, found the "impossibly high bar" the Principal originally flagged was mostly a short-window artifact (36mo window landed entirely inside the 2022-24 melt-up). **Flagged, not resolved:** this does NOT have D-029's stale-price/circuit-lock guards — the numbers may be inflated by exactly the kind of frozen-price artifact D-029's README documents catching. **Open action: re-run with the stale-mask guard before trusting v5-v8's absolute levels; the qualitative lesson (window length matters enormously) likely survives regardless.**
- **Options research bibliography** (0DTE short-duration + PutWrite/LEAPS long-DTE literature, explicitly skipping the 21-45 DTE institutional zone) — direct answer to "why avoid mid-duration as retail," sourced from CBOE/SSRN, not previously in `scout_papers_agents.md`.
- **`KNOWLEDGE_BASE/` folder** (india_equity_investing, quantamental_investing bibliographies written; microcap_investing, deep_value_investing barely started) — **INTERRUPTED by an org session spend-limit hit before any PDFs were actually downloaded.** A real bug was caught and fixed here: both completed bibliographies initially claimed 9 papers as "LOCAL" when the papers/ folders were empty — corrected to LINK-ONLY-pending-download. **Do not trust any "LOCAL" claim in these files without checking the papers/ folder directly until this is re-verified.**

## 3. Corrections needed (found this session, not yet applied)

1. **If/when `quantstats` or `pandas-ta` skills get filed** (drafted by an earlier agent this session, never filed — see conversation), incorporate `scout_github_oss.md`'s finding first: prefer `pandas-ta-classic` over `pandas-ta` (original abandoned), consider `quantstats-lumi` over base `quantstats` (slowing, unaddressed PRs).
2. **Re-verify v5-v8 random-benchmark numbers against D-029's stale-price guard** (see §2 above) before quoting their absolute CAGR levels anywhere client-facing or in an IC memo. The relative/qualitative findings (window length, weighting scheme) are likely robust; the exact numbers may not be.
3. **KNOWLEDGE_BASE/ paper folders**: microcap_investing and deep_value_investing need their agent wave re-run (queued, blocked on the session spend-limit reset ~9:40pm IST); india_equity_investing and quantamental_investing need the actual PDF-download pass completed (bibliography text exists, downloads don't).
4. **Cross-reference gap**: this session's `KNOWLEDGE_BASE/` folder and the firm's existing `KNOWLEDGE_BASE.md` file should be read as a pair (folder = detailed per-topic bibliographies with paper text; file = firm-earned lessons + terse reference pointers) — they are not currently linked to each other. Add a one-line pointer in `KNOWLEDGE_BASE.md`'s Section B to the new folder once it's complete.

## 4. Near-term next steps (once the spend limit resets)

- Finish the interrupted paper-collection wave: microcap + deep-value bibliographies, then actually download every open-access PDF across all four KNOWLEDGE_BASE topics (citations exist, files mostly don't yet).
- Algo/systematic-trading papers wave (queued, never started — this session's original "quant related" ask still has one uncovered domain).
- Pilot `openalgo`'s Angel-native paper-trading sandbox on one low-stakes sleeve, per `openalgo_eval.md`'s own recommendation (already scoped, never executed).
- Decide whether to formally adopt `vollib`/`jugaad-data` into the STOCK_SCORECARD_750 / options-desk toolchain now that both skills exist and are verified.

## 5. Open items from earlier in this session (not R&D, flagged for the Principal, still unresolved)

- STOCK_SCORECARD_750 production (V1) runs an equal-weighted composite that a rigorous decile/IC backtest found to be a significant NEGATIVE predictor on the primary 3Y horizon — never resolved whether to message DESK-100 about this.
- Client Excel format still diverges between this account's frozen minimal format and DESK-100's elaborate Ionic Wealth-branded build.
- Kordes portfolio review remains self-blocked (PII + out-of-scope-recommendation findings) pending Principal/CIO attention.

## See also
[[shreyas-ionic-amc-firm]] · [[stock-scorecard-750-frozen-methodology]] · [[feedback-consolidate-reused-code]]
