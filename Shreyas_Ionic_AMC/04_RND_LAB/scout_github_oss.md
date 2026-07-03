# SCOUT: GitHub/OSS Tooling Adoption Radar (2026)

Status: IN PROGRESS (checkpoint discipline D-023 — appending per finding)
Owner: R&D scout task | Date: 2026-07-04
Mission: identify OSS to ADOPT into our quant stack. Known baseline: qlib, vectorbt,
alphalens/pyfolio-reloaded, quantstats, Riskfolio-Lib, skfolio, mlfinlab, pandas-ta,
zipline-reloaded, OpenBB, jugaad-data.

Five sub-questions being researched:
1. Maintenance status of known libs (active vs abandoned in 2026)
2. Backtest validation tooling (DSR/PBO/CSCV/walk-forward out-of-the-box)
3. India-specific NSE data/API libs, F&O analytics, SPAN margin calculators
4. Execution/paper-trading harnesses adaptable to Angel SmartAPI paper desk
5. LLM-agent trading/research frameworks (TradingAgents, FinRL, ai-hedge-fund) — specific mechanisms we lack

---

## RAW FINDINGS LOG (append as gathered)

Dispatched 3 parallel research agents (2026-07-04):
- Agent A (a3bc615bd9341b787): known-lib maintenance status (Part A: qlib/vectorbt/alphalens/quantstats/Riskfolio-Lib/skfolio/mlfinlab/pandas-ta/zipline-reloaded/OpenBB/jugaad-data) + backtest validation tooling (Part B: DSR/PBO/CSCV/walk-forward OSS packages)
- Agent B (a2ffd1aca6fbb2f41): India NSE/broker SDKs + F&O analytics + SPAN calculators (Part A) + execution/paper-trading harnesses (Part B)
- Agent C (acfb51f0892d23cc0): LLM-agent trading frameworks (TradingAgents, ai-hedge-fund, FinRL, newer 2025-26 entrants) — specific mechanisms

Awaiting results — will append raw findings then synthesize ranked table below.

### Agent A results — known-lib maintenance + backtest validation tooling (2026-07-04)

**Part A — maintenance status:**
1. **qlib** — SLOWING. Commits continue but last tagged release v0.9.7 (Aug 2024); 298 open issues, MS attention shifted to microsoft/RD-Agent. Usable, pin commits.
2. **vectorbt OSS** — ACTIVE but frozen to bugfixes/py-compat only; maintainer confirms new features go to PRO only (Discussion #619). **vectorbt PRO** — commercial, healthy, new Rust engine Apr 2026, ~$20-25/mo.
3. **alphalens/pyfolio (quantopian)** — DEAD (pyfolio issue #690: "no longer maintained"). **alphalens-reloaded / pyfolio-reloaded** (stefan-jansen) — SUPERSEDED-BY-FORK, both released Jul 2025, low open issues. Use reloaded forks exclusively.
4. **quantstats** — SLOWING (v0.0.81 Jan 2026, slow triage). **quantstats-lumi** (Lumiwealth) fork exists citing unaddressed PRs — safer bet.
5. **Riskfolio-Lib** — ACTIVE, v7.2/7.3 2026, but bus-factor risk (<10 contributors).
6. **skfolio** — ACTIVE, fastest-moving portfolio-opt lib, v0.20.1 Apr 2026, weekly releases, now has commercial backer "Skfolio Labs" (enterprise SLA on top of OSS core). Still smaller (~2k stars) than PyPortfolioOpt (~5.6k)/Riskfolio-Lib (~3.8k).
7. **mlfinlab** — COMMERCIAL-PIVOT COMPLETE. Repo is now a stub, PyPI frozen since 2019, paywalled ~£100+VAT/mo/user via hudsonthames.org. PortfolioLab same model. **ArbitrageLab remains free/BSD-3.** Not usable as free dependency anymore.
8. **pandas-ta** — ABANDONED / messy takeover. Original repo 404s; new "pandas-ta.dev" wiped release history, soliciting donations to avoid archival by Jul 1 2026. Community consolidated on **xgboosted/pandas-ta-classic** (383 stars, v0.6.52 Jun 2026, 2 open issues) — MIGRATE HERE.
9. **zipline-reloaded** — SLOWING. Last commit Nov 2025 (dep bump only), last real release ~2024. Functional, low velocity.
10. **OpenBB** — COMMERCIAL-PIVOT. Free Terminal sunset 2024; core Platform library still ships actively (v4.6/4.7 2026) underpinning paid OpenBB Workspace/Terminal Pro.
11. **jugaad-data** — renamed org jugaad-py/jugaad-data. ACTIVE but thin (v0.33.1 Mar 2026), small team, some bugs unresolved since 2024. nsepython is a healthy fallback.

**Part B — backtest validation tooling:**
- **pypbo** (esvhd) — STALE (~2022 last activity, GitHub-install only, 136 stars) but theoretically most complete: PBO via CSCV, PSR, DSR, Min Track Record Length, Min Backtest Length.
- **quantlite** (PyPI) — ACTIVE (v1.7.1 Jun 2026), single maintainer, unproven; bundles deflated_sharpe_ratio + CSCV/PBO/walk-forward.
- **purgedcv** (eslazarev, PyPI) — ACTIVE, brand-new (v0.1.2 Jun 2026), sklearn-compatible. Bundles PurgedKFold/CombinatorialPurgedCV (CPCV) PLUS probabilistic_sharpe_ratio/deflated_sharpe_ratio/min-track-record-length. Explicitly built as an mlfinlab-paywall replacement. Only 16 stars — unproven but most complete active free option found.
- **True Bailey CSCV**: NO maintained OSS implementation exists anywhere. mlfinlab's own issue #382 (2020) requesting it was never resolved; only academic blog scripts (Quantoisseur, QuantInsti) implement it standalone. **Hand-rolling CSCV remains genuinely necessary — confirmed negative finding, not a search gap.**
- **Purged K-Fold/CPCV splitters (well-served)**: sam31415/timeseriescv (289 stars, stable), eslazarev/purgedcv (newest/most complete).
- **mlfinlab backtest-statistics module**: confirmed fully paywalled, not pip-installable. baobach/mlfinpy is free MIT fork but does NOT reimplement DSR/PBO/CSCV.
- **vectorbt PRO robustness tooling**: PRO-exclusive walk-forward CV with purging, combinatorial CV with purge+embargo, Splitter class, CV automation decorator. Free vectorbt has no purge/embargo logic. Cheap ($20-25/mo) if already vectorbt-based.
- **QuantStats family**: ships probabilistic_sharpe_ratio + "Smart Sharpe/Sortino" as point stats only — no CIs/bootstrap/p-values anywhere in the family.
- **BOTTOM LINE**: no mature package covers DSR+PBO+CSCV+walk-forward together. `purgedcv` is most promising active/free option for DSR+CPCV; CSCV/PBO logic must stay hand-rolled (no living alternative exists).

### Agent C results — LLM-agent trading framework mechanisms (2026-07-04)

1. **TradingAgents** (TauricResearch) — ACTIVE, ~90.6k stars, v0.3.0 Jun 2026, monthly releases. Architecture: 4 Analysts (Fundamentals/Sentiment/News/Technical) -> Bull/Bear Researcher debate -> Research Manager judges (not a debate participant) -> Trader -> 3-persona Risk debate -> Portfolio Manager final veto.
   - MECHANISM 1 (steal): **debate-then-independent-judge**, reused twice (once for idea gen, once for risk) — cleanly separates advocacy from arbitration. Maps directly onto CIO/red-team structure we already have; validates our IC-memo + red-team-gate shape.
   - MECHANISM 2: persistent `trading_memory.md` reflection log — realized returns (raw + vs benchmark) per past decision, auto-reflection injected into next Portfolio Manager prompt. Caveat: paper's own Sharpe 5.6-8.2 backtest flagged by authors as implausible/regime-lucky — steal the architecture, not the performance claim.

2. **AI Hedge Fund** (virattt/ai-hedge-fund) — ACTIVE, ~60.8k stars, v2026.7.3. LangGraph pipeline, 13 investor-persona agents (Buffett/Munger/Ackman/Burry/Wood/etc.) + 4 factor agents -> Risk Manager -> Portfolio Manager.
   - MECHANISM (steal, high value): **Risk Manager is purely programmatic (no LLM)** — computes vol/correlation-adjusted `remaining_position_limit` per ticker as a non-negotiable ceiling; Portfolio Manager LLM only sizes WITHIN that pre-validated envelope. Unanimous persona bullishness cannot override the hard cap. Concrete template for a rule-based (not vibes-based) CIO veto. Each persona's philosophy is also operationalized as hard quant sub-scores (e.g. Buffett: ROE>15%, D/E<0.5, 3-stage DCF) BEFORE the LLM writes persona-voiced reasoning.

3. **FinRL** (AI4Finance) — ACTIVE (~15.6k stars, v0.3.8 Mar 2026), being succeeded by FinRL-X for production (2027+ target); LLM layer is federated (FinGPT/FinRobot/FinRL-DeepSeek), not unified.
   - MECHANISM 1: **turbulence-index circuit breaker** — Mahalanobis-distance measure of current-returns deviation from historical covariance; crossing threshold force-liquidates regardless of policy. Cheap, interpretable, model-agnostic "stand down" layer — usable even in our discretionary/LLM system, independent of any agent's judgment.
   - MECHANISM 2: FinRL Contest runs 10 train/val splits and explicitly REJECTS submissions with high PBO at 10% significance — a formalized rejection gate conceptually adjacent to our own DSR/PBO gate; worth benchmarking against.
   - Caveat: base tx-cost model is flat linear % — known weakness, do not copy.

4. **Newer 2025-26 frameworks** — honest finding: real risk-veto/promotion-gate novelty is SCARCE post-2025; most "risk agents" annotate risk as weighted input, not hard block. **No project found has an explicit backtest->paper->live promotion gate with criteria — this looks like real whitespace**, not a search miss.
   - TradingGroup (UNSW, arXiv:2508.17565) — labels past 20 days' decisions with actual outcomes, compiles written "experience summary," sets vol-scaled stop-loss/take-profit (T_SL = multiplier x 10-day sigma) as post-decision force-exit. No public repo.
   - QuantAgent (~2.8k stars, active) — first LLM multi-agent framework for HFT; Risk agent is weighted input only, not hard veto.
   - Agent Market Arena/LiveTradeBench/DeepFund — argue backtests are "gameable" ("Time Travel is Cheating"), push continuous live-only eval — philosophically relevant to our promotion-gate thinking, no implementation.
   - AgenticTrading (Open-Finance-Lab) — has explicit "audit agent" in pipeline, closest namesake to a promotion gate, but no documented graduation thresholds.

5. **Reflection/memory mechanisms — highest-value gap area for us:**
   - **FinMem** (arXiv:2311.13743) — most mechanistically precise: 3-layer memory (shallow/intermediate/deep) with DIFFERENT DECAY RATES per layer (deep decays slower). Retrieval score gamma = Recency + Relevance + Importance (each normalized [0,1], summed), top-K per layer pulled into working memory. Actively PURGES memories when recency<0.05 or importance below threshold — explicit forgetting, not unbounded accumulation. Directly portable to our markdown memory system: score/decay/prune old trade write-ups instead of flat accumulation.
   - **FinAgent** (arXiv:2402.18485) — dual-level reflection: low-level (tactical/short-horizon) + high-level (strategic/long-horizon), generated and retrieved separately; multimodal inputs (numeric+text+chart-image) into memory. Reports 36% avg profit improvement in ablation vs 9 baselines, memory module identified as key driver.
   - **FinCon** (arXiv:2407.06567, NeurIPS 2024) — most risk-relevant: two-tier risk control (within-episode CVaR-based real-time strategy adjustment; over-episode "Conceptual Verbal Reinforcement" (CVRF) — post-episode self-critique distills winning/losing sequences into an updated BELIEF STATEMENT, propagated ONLY to the specific agent nodes that need it, not broadcast to all). Standout mechanism: **targeted lesson propagation** — directly analogous to updating only the relevant analyst's persona file after a post-mortem/retro, rather than rewriting the whole team's playbook. STRONGEST FIT for strengthening our existing retro/post-mortem loop.

**Overall Agent C recommendation**: most reusable non-generic mechanisms = (1) TradingAgents debate-then-judge protocol, (2) ai-hedge-fund's hard deterministic risk ceiling gating the LLM, (3) FinRL turbulence-index circuit breaker, (4) FinMem/FinCon decaying-scored-selectively-propagated memory (best fit for our retro loop).


