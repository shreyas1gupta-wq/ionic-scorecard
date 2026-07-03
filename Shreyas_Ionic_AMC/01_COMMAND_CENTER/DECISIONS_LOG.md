# Decisions Log — Principal rulings (append-only, binding)
| # | Date | Decision |
|---|---|---|
| D-001 | 2026-07-03 | Both accounts share this OneDrive folder on one laptop; sync via files (journal + state). Both must always know what the other did. |
| D-002 | 2026-07-03 | Do NOT touch/move original folders. Build the AMC layer around them; copy files if needed. Neat & clean. |
| D-003 | 2026-07-03 | Git: initialized at root, command-layer only (datasets gitignored). Local-only; never push remote without secret-scrub. |
| D-004 | 2026-07-03 | DESK-20 = R&D/ideas/CIO office; DESK-100 = heavy execution. Claude may rebalance when sensible. |
| D-005 | 2026-07-03 | IC routing: CIO + FM decide who convenes, unless Principal specifies. |
| D-006 | 2026-07-03 | Agent count: everything that helps (50 if needed) but token-smart, use only when needed. 5 core equity analysts. |
| D-007 | 2026-07-03 | Standard memo format required, some flexibility allowed. |
| D-008 | 2026-07-03 | Red Team exists to SAVE us, not to be a bureaucratic hurdle. One focused attack per idea. |
| D-009 | 2026-07-03 | NO auto-fetching new data. Verify new sources via sample/structure checks (Data Officer). Data-management agents approved. |
| D-010 | 2026-07-03 | Pipeline gates auto-advance; LIVE gate = Principal approval only. |
| D-011 | 2026-07-03 | No deep learning for now (data size doesn't justify); Kaggle/Colab GPU escape hatch if ever needed. |
| D-012 | 2026-07-03 | Knowledge base with all backtests+logic+reasoning. Kills are conditional — new variants (e.g., sniper-entry option buying) may resurrect a killed family. |
| D-013 | 2026-07-03 | Token-aware ops: limit parallel agents (DESK-20 ≈2, DESK-100 ≈3×), checkpoint work so any token cut is resumable. |
| D-014 | 2026-07-03 | Model tiering approved (cheap models for mechanical work, top models for judgment). |
| D-015 | 2026-07-03 | DATA_CATALOG + backups required. |
| D-016 | 2026-07-03 | EOD auto-run owned by DESK-100 (already live as AngelDailyOptionCapture). Team is gamified: names, virtual salary/bonus (AlphaPoints), appreciation, PIP/replace process, self-evolving lessons, backup LLM per agent. Build "a whole company." |
| D-017 | 2026-07-03 | Paper-trading ledger required (06_TRADING_DESK/PAPER_LEDGER.md). |
| D-018 | 2026-07-03 | Capital: paper now; Principal will start small retail account with a few strategies when confident. |
| D-019 | 2026-07-03 | No fixed track priority; fresh start mindset; incorporate VS Code's FINAL_STRATEGY_FORWARD_CHECK research. |
| D-020 | 2026-07-03 | Firm name: **Shreyas_Ionic_AMC**. Standardized prompts and cost/slippage/brokerage standards enter force ONLY after Principal approval, one by one. |
| D-021 | 2026-07-03 | BLANKET APPROVAL — Principal: "my approval on everything okay continue". P-01..P-12 + RP-01..RP-10 moved to approved/; COST_STANDARDS.md and RISK_LIMITS.md banners set APPROVED and now binding. |
| D-022 | 2026-07-04 | THREE-BOOK structure: FM-Derivatives (Vikram), FM-Equities/Momentum (Devika), FM-Fundamental Quality&Value (Sanjay Kulkarni, E-017 — 'pure traditional equity research type' per Principal). **Delegated creation authority: the CIO + 3 FMs may create new agents and skills as needs arise** (via /hire and skill files) — journal + EVOLUTION_LOG entry mandatory, Principal notified via journal; no pre-approval needed. Structural changes to governance/risk rules still require Principal. |
