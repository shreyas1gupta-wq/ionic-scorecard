# SCOUT: GitHub/OSS Tooling Adoption Radar (2026)

Status: COMPLETE (checkpoint discipline D-023 — findings appended incrementally, ranked table finalized)
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

### Agent B results — India NSE/broker SDKs + F&O analytics + execution/paper-trading harnesses (2026-07-04)

**Part A — data libs:**
- **NSEPython** (aeron7/nsepython) — ACTIVE, GitHub commits through Mar 2026 (PyPI lags ~10mo, install from master). Broader option-chain/index coverage than jugaad-data; migrated nsepy/nsetools function names for near drop-in swap.
- **nsepy** — CONFIRMED DEAD, last commit Dec 2023, broke when NSE retired old site (Apr 2023). Maintainer's own README names jugaad-data/NSEPython as successors. Do not use.
- **jugaad-data** — healthiest of the three, GitHub+PyPI both current to Mar 2026, same-day release cadence. Our current choice remains well-justified.

**Part A — broker SDKs** (order-abstraction quality + sandbox support):
| Broker | Maintenance | Order model | Sandbox? |
|---|---|---|---|
| Zerodha kiteconnect | Active but triage lags | Clean 3-axis model (order_type/variety/product) — de facto vocabulary OpenAlgo reuses | NO — Zerodha confirms no sandbox exists |
| Fyers fyers-apiv3 | Active, ~monthly | Thin raw-dict wrapper, no typed classes | No native sandbox (paid "API Bridge" add-on separate product) |
| Dhan dhanhq | Active (Apr 2026) | Raw dict/JSON | YES — real sandbox but static-price-100 fills, no live feed |
| Upstox SDK | Active (Swagger auto-gen) | Typed `PlaceOrderRequest` — most structured | YES — genuine sandbox, order-mgmt only, no market data yet |

Zerodha/SEBI note: Feb 2025 SEBI algo-trading circular imposed static-IP whitelisting, 2FA, algo-ID tagging, exchange registration above 10 orders/sec — compliance overhead not an API shutdown; enforcement date slipped repeatedly (~Apr 2026 provisional). Data API pricing CUT (Rs.2000->Rs.500/mo), not restricted.

**Part A — SPAN margin**: thin category. Only real hit: **marginism** (marketcalls/marginism) — parses NSE Clearing's actual .spn files, computes SPAN+exposure+margin for a basket. Small/young (~11 commits), MIT, author disclaims accuracy. No mature OSS SPAN engine exists — fork as reference only, don't depend on it.

**Part A — option-chain/Greeks analytics**: split field, no single repo does it all.
- Python-NSE-Option-Chain-Analyzer (VarunS2002, 630 stars, active) — OI/volume analytics, no Greeks, no broker link.
- mirajgodha/options — real Greeks+strategy P&L+broker execution, but only ICICI Direct/Nuvama (not Angel).
- markov404/AngelOneOptionChainSmartApi — Angel-native but just a data-dump script.

**Part A — STANDOUT FINDING: openalgo** (marketcalls/openalgo) — extremely active (v2.0.1.4 Jun 2026, 4,252 commits), self-hosted Flask/React server unifying 30+ Indian brokers INCLUDING ANGEL NATIVELY, with a real Rs.1cr paper-trading sandbox (margin sim, auto square-off), built-in Greeks/margin calculators, AGPL-3.0 license. **Fenix** (TheHardeep/fenix) is a lighter pure-Python alternative (15 brokers incl. Angel, no server needed) if AGPL/server footprint is unwanted.

**Part B — execution/paper-trading harnesses:**
- **OpenAlgo's sandbox** — fastest path, Angel-native, real order-flow sim, BUT quote-crossing only (no order-book depth/partial fills/slippage modeling — author admits "95% of issues, last 5% only shows on live").
- **Nautilus Trader** — very active (24.4k stars, Jun 2026 release), architecturally most rigorous, dedicated Sandbox execution context with true backtest/sandbox/live parity. NO India broker adapter exists (confirmed absence) — building one is a multi-week Rust+Python effort but yields a much better long-term matching engine than OpenAlgo's.
- **Freqtrade** — not directly usable (crypto/ccxt-only) but IStrategy/Exchange separation is a good design pattern; its own community treats backtest-vs-dry-run fill divergence as a documented, unsolved pitfall — useful checklist for us.
- **Broker-adapter pattern reference**: no dedicated tutorial exists; best examples are TradeFlow (makedirectory/tradeflow, Alpaca-only) and OpenAlgo's own internal brokers/<name>.py module layout (most India-relevant).
- **Angel SmartAPI has NO official sandbox** (confirmed on Angel's own dev forum) — any paper-trading must synthesize fills locally against Angel's live quote feed. This is exactly our current paper-desk situation.

**Agent B recommendation**: adopt/fork OpenAlgo's sandbox module for near-term paper-trading (Angel-native, active, real margin sim), bolt on custom slippage/partial-fill logic; treat Nautilus Trader as long-horizon target if execution realism becomes the bottleneck later.

---
## ALL THREE AGENTS COMPLETE — synthesizing final ranked table below.

## FINAL RANKED ADOPTION TABLE (max 12)

| # | Repo/Package | Maintenance status (2026) | What it replaces/adds in OUR stack | Integration cost | 
|---|---|---|---|---|
| 1 | **eslazarev/purgedcv** (PyPI) | ACTIVE, brand-new (v0.1.2 Jun 2026), 16 stars, unproven | Gives us PurgedKFold/CombinatorialPurgedCV (CPCV) + probabilistic_sharpe_ratio/deflated_sharpe_ratio/min-track-record-length OUT OF THE BOX — stop hand-rolling DSR and purged CV splitting; still must hand-roll true Bailey CSCV (no living alt exists) | Day — pip install, swap into existing DSR script, validate against our hand-rolled numbers before trusting |
| 2 | **marketcalls/openalgo** | Very active (4,252 commits, v2.0.1.4 Jun 2026) | Angel-native self-hosted paper-trading sandbox (Rs.1cr sim, margin sim, auto square-off) + built-in Greeks/margin calculators — directly upgrades our Angel SmartAPI paper desk, which currently has zero official sandbox | Week — self-host Flask/React server, wire our Angel creds, validate fill assumptions (quote-crossing only, no depth/slippage — must bolt on our own slippage model) |
| 3 | **xgboosted/pandas-ta-classic** | ACTIVE (v0.6.52 Jun 2026, 2 open issues) | Drop-in replacement for pandas-ta, which is ABANDONED (original repo 404s, successor "pandas-ta.dev" wiped history, soliciting donations to avoid archival Jul 2026) | Trivial — same API surface, swap the import/dependency pin |
| 4 | **stefan-jansen/alphalens-reloaded + pyfolio-reloaded** | ACTIVE (Jul 2025 releases, low open issues) | Replace quantopian/alphalens+pyfolio, which are CONFIRMED DEAD (pyfolio issue #690: "no longer maintained") — if we still import the originals anywhere, this is a silent landmine | Trivial — same API, swap package name |
| 5 | **FinCon's CVRF mechanism** (arXiv:2407.06567 — pattern to implement, not a library) | Academic (NeurIPS 2024), not a pip package | Adds targeted lesson-propagation to our retro/post-mortem loop: post-episode self-critique distills belief statements, routed ONLY to the specific persona files that need the update, not broadcast to the whole team. Directly strengthens our existing `/retro` skill logic | Day — encode as a rule in the retro skill: "update only the implicated agent's persona file, not all personas" |
| 6 | **ai-hedge-fund's deterministic risk-ceiling pattern** (virattt/ai-hedge-fund — pattern, not a dependency) | ACTIVE, ~60.8k stars, v2026.7.3 | Template for a rule-based (non-LLM) hard position-limit ceiling that CIO/quant-head personas cannot override regardless of conviction — formalizes what we already do informally in pre-trade-check; makes the veto auditable/deterministic rather than judgment-based | Day — codify existing informal sizing caps into an explicit pre-LLM-call gate function |
| 7 | **aeron7/nsepython** | ACTIVE (GitHub commits to Mar 2026; install from master, PyPI lags) | Fallback/supplement to jugaad-data with broader option-chain/index coverage; near drop-in (migrated nsepy/nsetools function names) — insurance against jugaad-data's "thin team" bus-factor risk | Trivial-Day — install alongside jugaad-data, use for endpoints jugaad-data lacks |
| 8 | **dcajasn/Riskfolio-Lib** (status re-confirm) | ACTIVE, v7.2/7.3 2026 (already in our known list) | No change to adoption — CONFIRM continued reliance is safe; flag bus-factor risk (<10 contributors) as a watch item, not a reason to drop | None (already adopted) — just a monitoring note |
| 9 | **skfolio** (status re-confirm + increase reliance) | ACTIVE, fastest-moving portfolio-opt lib in the space, weekly releases, v0.20.1 Apr 2026, now commercially backed (SLA available) | Already known; upgrade priority — this is now the safest long-term bet of our two portfolio-opt libs given its release cadence and new commercial backing (reduces abandonment risk vs Riskfolio-Lib) | Trivial — no new integration, just prioritize its features over Riskfolio-Lib's for new work |
| 10 | **TradingAgents' debate-then-independent-judge protocol** (TauricResearch — pattern, not a dependency) | ACTIVE, ~90.6k stars, v0.3.0 Jun 2026 | Validates and sharpens our existing IC-memo + red-team-gate structure: formalizes "bull/bear debate -> a NON-participant judge renders verdict" reused identically for risk (3-persona risk debate -> portfolio-manager judge). We already have the shape; this is a checklist to confirm our red-team/CIO separation matches the pattern precisely (judge must not have argued a side) | Day — audit ic-memo/red-team skills against this checklist, tighten if any persona is both advocate and judge |
| 11 | **AI4Finance/FinRL's turbulence-index circuit breaker** (pattern, not a dependency) | ACTIVE (~15.6k stars, v0.3.8 Mar 2026) | Adds a cheap, interpretable, model-agnostic "stand down" layer: Mahalanobis-distance deviation from historical covariance structure, force-liquidate/de-risk regardless of any agent's judgment when crossed. Complements our existing event-gates (which are calendar-based) with a pure statistical regime trigger | Week — needs a covariance-tracking job across our universe + wiring into kill-switch-drill logic |
| 12 | **TheHardeep/fenix** | ACTIVE, lighter alternative to openalgo | Pure-Python (no server) unifying 15 Indian brokers incl. Angel — a lower-footprint fallback to #2 if AGPL license or self-hosted server overhead is unwanted for the sandbox | Day — evaluate as alternative/complement to openalgo before committing infra |

## KEEP-OUT LIST (popular but WRONG for us — do not adopt)

- **hudson-and-thames/mlfinlab** — fully paywalled since ~2019 (PyPI frozen, repo is a stub, ~£100+VAT/mo/user). The DSR/PBO/CSCV module we'd want is specifically the paid "Backtest Overfitting" deliverable — not accessible free. Use purgedcv instead (adoption #1).
- **twopirllc/pandas-ta (original)** — ABANDONED, repo 404s. Its claimed successor "pandas-ta.dev" wiped release history and is soliciting donations to avoid archival — do not adopt that either. Use pandas-ta-classic (adoption #3).
- **quantopian/alphalens, quantopian/pyfolio (originals)** — confirmed dead by maintainer's own issue tracker. Any lingering import of these in our codebase is a silent landmine — audit and replace with -reloaded forks.
- **vectorbt PRO** — real feature gap (purge/embargo-aware CV, Rust engine) but commercial commitment ($20-25/mo) for capability we can get free via purgedcv + our own hand-rolled CSCV; revisit only if hand-rolled validation becomes the bottleneck, not before.
- **nsepy** — confirmed dead since Dec 2023, broke when NSE changed its site; maintainer's own README points elsewhere. Never build on this.
- **Zerodha kiteconnect / Fyers fyers-apiv3 as our execution SDK** — we trade via Angel SmartAPI already; no reason to migrate brokers. Worth reading their order-model vocabulary (kiteconnect's 3-axis order_type/variety/product) as a design reference only, not as a dependency.
- **Nautilus Trader (near-term)** — architecturally superior but NO India broker adapter exists; building one is a multi-week Rust+Python effort. Right call is to defer this to long-horizon (only revisit if OpenAlgo's execution realism becomes a hard bottleneck), not adopt now.
- **marketcalls/marginism (SPAN calculator)** — real but immature (~11 commits), author explicitly disclaims accuracy. Do not trust position sizing to it; fork for reference/learning only, never wire into live risk calcs.
- **FinRL for actual deployment** — interesting circuit-breaker pattern (adoption #11) but the framework itself is deep-RL-first with a flat linear-% transaction cost model (known weakness) and is being superseded by FinRL-X (2027+ target). Steal the turbulence-index concept; do not adopt the framework.
- **mirajgodha/options** — has real Greeks+broker execution but hardwired to ICICI Direct/Nuvama, not Angel. Not worth adapting; openalgo's built-in Greeks calculator (bundled in adoption #2) covers this need natively for Angel.

## KEY CROSS-CUTTING FINDING (whitespace)
No project surveyed — commercial, academic, or OSS — implements an explicit backtest -> paper -> live PROMOTION GATE with pre-registered graduation criteria. This is confirmed whitespace, not a search gap (Agent C explicitly checked and found none). Our own gate-pipeline (idea intake -> cheap test -> full backtest -> IC memo -> red team -> deploy) may already be ahead of the open-source field here — worth writing up as a differentiator rather than assuming we're behind.

STATUS: COMPLETE — all 3 research streams synthesized, ranked table finalized 2026-07-04.


