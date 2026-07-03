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
| D-023 | 2026-07-04 | Token discipline hardened after org spend-limit hit mid-flight: **MAX 3 parallel agents firm-wide** (was 6 on DESK-100); every agent task must checkpoint progress to files so a limit-hit loses nothing; long jobs designed resumable from their last saved artifact. |
| D-024 | 2026-07-04 | BLANKET APPROVAL #2 — Principal: "approved everything from my side". Covers: PROMPT_PACK_50 (RP-11..RP-60) → approved/; niftyindices.com as a data source (Principal-contributed scraper); the scouts' adoption queue; team-25/47-skill expansion; token-toolkit rules. |
| D-025 | 2026-07-04 | APPROVAL DELEGATION — Principal: "assume instead of me giving approval ceo cio both check and give approval only in case of tie i vote". All D-020-class approvals (prompts, standards amendments, data sources, adoptions, hires) now = CEO + CIO JOINT review; both must approve; disagreement → Principal tie-break. CARVE-OUT (unchanged unless Principal overrides): LIVE-capital gate (D-010/D-018) and RISK_LIMITS loosening remain Principal-only — his money, his signature. |
| D-026 | 2026-07-04 | Principal: paper BOOK_EQUITY = ₹1 crore. Resolves the risk-ceiling escalation (1% rule = ₹1L/position → single F&O lots tradeable, max_lots ~2-3 typical). Applied to execution_scanner enforce_risk_ceiling. |
| D-027 | 2026-07-04 | STANDING APPROVAL — Principal: "i am giving all approvals now only no further approvals needed" + "bypass my permission". All future D-020/D-025-class items are pre-approved (CEO+CIO joint review still runs for the record, but nothing waits on the Principal). Harness permission mode set to dontAsk + wildcard allows. LIVE-capital gate remains the sole Principal touchpoint (D-010 — his signature, unchanged). Backup system ordered → 99_OPS/backup_firm.py + weekly task ShreyasIonicAMC_WeeklyBackup (Sun 11:00, rotation 5, destination OUTSIDE OneDrive). |
| D-028 | 2026-07-04 | Principal: "ensure no lookahead bias add that too in risk management" — LOOKAHEAD-BIAS PREVENTION becomes a FORMAL RISK-OFFICE CONTROL (a tightening; effective immediately). New: 07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md (taxonomy T1-T10 + audit gate), lib/lookahead_audit.py (programmatic checks), /lookahead-audit skill. Gate-4 cannot pass without a LOOKAHEAD AUDIT PASS signed by the Risk Office (Dr. Bhat owns, Ritika monitors live/paper parity, Nikhil attacks it at red-team). Existing live pipelines to be retro-audited. |
