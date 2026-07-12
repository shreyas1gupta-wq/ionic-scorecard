# SECTION 1 — GOVERNANCE, RULES & DECISIONS

*Blueprint section researched from the actual repo files on 2026-07-12. Sources: `Shreyas_Ionic_AMC/00_GOVERNANCE/` (FIRM_CHARTER.md, TEAM_ROSTER.md, TOKEN_POLICY.md, MODEL_ASSIGNMENTS.md, SELF_IMPROVEMENT.md, EVOLUTION_LOG.md, LEADERBOARD.md, IMPROVEMENT_BACKLOG.md), `01_COMMAND_CENTER/DECISIONS_LOG.md`, root `CLAUDE.md`, `Shreyas_Ionic_AMC/ORG_STRUCTURE.md`.*

---

## 1. What the firm is

**Shreyas_Ionic_AMC**, founded **2026-07-03**. Principal and sole LP: **Shreyas Gupta** — a human who chairs the firm; everyone else on the roster is an AI agent persona run on Claude models. The mission (FIRM_CHARTER.md): *run a quantamental AMC-grade research→profit machine — generate ideas, test them honestly, kill them ruthlessly, paper-trade the survivors, and hand the Principal decision-ready strategies.*

**Mandate & hard constraints** (charter):

| Dimension | Rule |
|---|---|
| Market | India (NSE/BSE), equities + F&O; US/other later |
| Capital | **Paper-only now.** Designed for ₹5–25L initial; architecture must scale to ₹10Cr without redesign |
| Return bars | Net Sharpe ≥1.5 honest (≥2 good), Calmar ≥1.5, MaxDD <25%; every strategy must survive Red Team |
| Non-negotiables | Survivorship-free universes, point-in-time data, approved cost standards, deflated-Sharpe/PBO awareness, economic WHY before belief, kill-log everything |

The single loudest rule, repeated in the root `CLAUDE.md` in bold: **NO real-money trades, ever.** The connected Angel Broking account is fund-less, data-only. Everything is research and paper trading until the Principal himself explicitly approves a live step.

---

## 2. The two-desk operating model

The firm runs on **two Claude accounts on the same laptop, sharing the same OneDrive folder**:

| | **DESK-20** (desktop app, $20 plan) | **DESK-100** (VS Code, $100 plan) |
|---|---|---|
| Role | CIO office — R&D, ideas, memos, reviews, light analysis, direction | Execution floor — backtests, bulk data, batch/multi-agent workflows, EOD auto-runs |
| Max parallel subagents | 2 | 3 (D-023; TOKEN_POLICY originally said 6, hardened after a spend-limit hit) |
| Bulk scrapes / downloads | NO — hand off to DESK-100 | YES |
| Full-portfolio backtests | NO (design only) | YES |
| IC sessions | Small IC (2–3 agents) | Full IC (5) when needed |
| Auto-routines | — | Owns `AngelDailyOptionCapture` (15:45/20:00/23:00 IST) + EOD_ROUTINE; re-arms the operating-calendar crons at each session start |

**Synchronization is file-based and mandatory** (the "Session Protocol" in `CLAUDE.md`):
1. Session start: read `01_COMMAND_CENTER/CURRENT_STATE.md` (always) + last ~2 entries of `SESSION_JOURNAL.md`.
2. Session end / major milestone: append a journal entry (date, account, work done, files touched, next steps) AND update `CURRENT_STATE.md`. *No work is "done" until journaled.*
3. Long tasks checkpoint progress to files continuously so the other desk (or a token-limit restart) can resume mid-task.
4. Principal-facing deliverables are HUMAN-format — Word docs with tables/charts (`09_PRODUCT/reports/`) or clean in-chat tables. `.md` files are internal books for agents, never handed to the Principal as "the deliverable".

This is the firm's answer to a real failure mode: two independent AI sessions with no shared memory. The journal + state files ARE the firm's memory bus.

---

## 3. Governance chart & authority chain

From `ORG_STRUCTURE.md` (master map; the file itself carries the rule "update on any structural change"):

```
PRINCIPAL (Shreyas) — owner, board chair, LIVE gate, D-series approvals
└── BOARD (monthly, 08_BOARD_ROOM): Principal chairs; CIO presents; FMs report books
    ├── Meher Kapadia — CEO (E-018): OPERATIONS — cadence, budget/tokens, HR/AP, board secretary
    │    ├── Farhan Qureshi (E-019) Compliance · Manoj Pillai (E-023) Ops-Eng · Lakshmi N. (E-024) Librarian
    │    └── Tanvi Desai (E-026) Head of Product (investor letter, dashboards, 09_PRODUCT/)
    └── Rajan Mehta — CIO (E-001): INVESTMENTS — capital protection, tail-risk VETO, arbitrates the 3 books
        ├── Risk cluster: Ritika Sharma (Risk Mgr) · Dr. Sameer Bhat (Overfit) · Cyrus Daruwalla (Macro)
        │                 · Aakash Jain (Structurer) · Neel Basu (Attribution) · Kabir Anand (Hedging, E-028)
        ├── Vikram Shah (E-002) — FM DERIVATIVES & SHORT-VOL book
        ├── Devika Menon (E-016) — FM EQUITIES & MOMENTUM book
        ├── Sanjay Kulkarni (E-017) — FM FUNDAMENTAL QUALITY & VALUE book
        ├── Ananya Iyer (E-003) — Equity Research Head → 5 sector analysts
        ├── Arjun Rao (E-004) — Quant Head (validation authority) · Dhruv Kapoor (E-005) — Technical Head
        ├── Prof. Aditya Verma (E-011) — R&D Head · Ishaan Gupta (E-012) — ML
        ├── Kavya Reddy (E-013) — Data Officer · Tara Singh (E-015) — Execution/TCA
        └── Nikhil Bose (E-014) — RED TEAM (reports to CIO ONLY — independence by design)
```

Key structural design choices:
- **CEO runs operations, CIO runs investments** — a deliberate split so token budgets/cadence/HR never contaminate investment judgment, and vice versa.
- **Red Team independence**: Nikhil Bose reports to the CIO only, is scored on confirmed kills (+15 AP), and a *refuted* "catch" costs −10 AP — the incentive design prevents both harmony and false alarms.
- **Single accountable veto**: a "second CIO / redundant tail-risk veto" was explicitly REJECTED in IMPROVEMENT_BACKLOG (redundancy = backup *model*, not a second head).
- **Three-book structure** (D-022): Derivatives/short-vol (Vikram), Equities/Momentum (Devika), Fundamental Quality & Value (Sanjay) — the CIO arbitrates between books.
- Team stands at **28 personas** (E-001..E-028); the newest is Kabir Anand, Head of Hedging & Tail Risk (hired 2026-07-08 by direct Principal order).

### Investment Committee (IC)
- Standing members: CIO + FM + heads relevant to the idea. The **full 5-core IC** (CIO/FM/Equity/Quant/Technical) convenes **only** for position-sized decisions or when CIO/FM call it — explicitly a token-discipline rule.
- Every IC decision = a memo filed in `03_RESEARCH_DESK/memos/` on the standard template. This is a **permanent track record**: "we grade ourselves."
- Red Team review is **mandatory** before any idea passes the audit gate — one focused attack memo, not endless rounds (D-008).

---

## 4. The approval-gate hierarchy — who can approve what

This is the heart of governance. The gates evolved through the D-series rulings (D-020 → D-025 → D-027) from "Principal approves everything" toward "Principal approves almost nothing except his own money":

| Tier | What it covers | Who approves | Source |
|---|---|---|---|
| **Tier 1 — Principal ONLY, always** | (a) LIVE capital / paper→live gate; (b) any **loosening** of RISK_LIMITS | Principal personally — "his money, his signature." Explicitly carved out of every delegation (D-025, D-027) | D-010, D-018, D-025, D-027 |
| **Tier 2 — CEO + CIO joint** | Prompts, standards amendments, new data sources, adoptions, hires — all former "D-020-class" items | Both must agree; disagreement → Principal tie-break. Since D-027 these are *pre-approved* by standing order but the joint review still runs **for the record** | D-025, D-027 |
| **Tier 3 — Delegated to CIO + 3 FMs** | Creating new agents and skills as needs arise (/hire, skill files) | No pre-approval; journal + EVOLUTION_LOG entry mandatory; Principal notified via journal. Structural changes to governance/risk rules still escalate | D-022 |
| **Tier 4 — Automatic** | Idea-pipeline gate advancement (Gates 0→4), reliable-source data fetches (with D-009 verification + catalog entry + resume-safe jobs) | No human/agent sign-off; the pre-registered kill criteria at each gate are the control | D-010, D-033 |

The **idea pipeline** the gates run over (charter): `0 Idea → 1 Cheap test → 2 Full backtest (approved costs) → 3 Red Team audit → 4 Forward/paper test → 5 LIVE (Principal only)`. Each gate has explicit kill criteria **set at entry** (pre-registration — the tester cannot move the goalposts after seeing results). Kills go to `04_RND_LAB/KILLED_IDEAS.md` **with resurrection conditions** — "a kill is a fact about a specific implementation, not a law of nature."

Additional hard gates layered on later:
- **D-028**: Gate-4 cannot pass without a **LOOKAHEAD AUDIT PASS** signed by the Risk Office (`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`, taxonomy T1–T10, `lib/lookahead_audit.py`).
- **Gate-4 also requires Dr. Sameer Bhat's sensitivity report** (per his hiring entry in EVOLUTION_LOG, 2026-07-04).
- **D-029**: every stock-selection strategy must beat its **cost-loaded random-basket benchmark** (10,000 permutations, cap-matched, percentile bands) — not just an index.

---

## 5. The forward-test freeze law (D-030) and product-line mandates (D-031/D-032/D-034)

**D-030 — Forward-test freeze (2026-07-05, hard rule).** Once a strategy enters forward evaluation (paper-book entry OR a declared OOS forward window):
- Its **spec + code + params are FROZEN**; the git hash is pinned in STRATEGY_REGISTER / PAPER_LEDGER at entry.
- **Any** change = a NEW version (vN+1) whose forward clock **restarts at zero**; the old version's forward record stands unedited forever.
- Mid-test tuning **voids** the result.
- Redesigning killed ideas is legitimate precisely because they are *not* in forward test — they re-enter as new versions with fresh clocks.

This is the firm's structural defense against the most common quant self-deception: quietly "improving" a strategy while its live record accrues, then attributing the blended record to the current version.

**D-031 — Capacity & execution relaxation (personal trading line).** Small capacity (₹10L–₹10cr) is acceptable for *exceptional* strategies — scale is not an automatic kill on the personal line. Limit-order-or-skip execution is sanctioned; the honest backtest translation is **no-fill = DROP** (never assume fills in dead markets). AMC-scale products still owe full scale-honesty in IC memos. Critically, the CIO later ruled (K-012, 2026-07-05) that **D-031 relaxes the CAPACITY bar, not the EDGE bar** — it cannot be used to resurrect a strategy whose edge failed.

**D-032 — Dual product-line mandate.** The firm develops both: (1) a **TRADING line** — personal, short-term, exceptional-edge small-capacity strategies (books: Vikram derivatives + Devika short-term momentum); (2) an **INVESTMENT line** — personal + AMC, long-term multibagger/contrarian/deep-value/quality (books: Sanjay fundamental + Devika long-horizon factor sleeves). (Note: the Principal's original message was truncated mid-sentence — "…best and" — and the log records that the continuation is still owed.)

**D-034 — Portfolio-level adjudication (2026-07-13).** A standalone-bar FAIL (e.g., >25% MDD) does not bin a sleeve with genuine placebo-beating alpha; the deciding test is **marginal contribution at BOOK level** (stacked CAGR/DD/Sharpe, XIRR, regime-conditional value). Standalone bars still bind each frozen card's own verdict (no retro-editing), and book-level RISK_LIMITS remain binding. First application: the CA sleeve (+14.1% CAGR, −50% standalone DD, beats placebo95 by 8.9%) stays live as a book-sleeve candidate.

---

## 6. DECISIONS_LOG — all 34 Principal rulings

`01_COMMAND_CENTER/DECISIONS_LOG.md` is append-only and binding. Every ruling, summarized:

| # | Date | Ruling (summary) |
|---|---|---|
| D-001 | 2026-07-03 | Both accounts share one OneDrive folder on one laptop; sync via files (journal + state); each must always know what the other did |
| D-002 | 2026-07-03 | Never touch/move the original legacy research folders; build the AMC layer around them; copy files in if needed |
| D-003 | 2026-07-03 | Git initialized at root, command-layer only (datasets gitignored); local-only, never push remote without secret-scrub |
| D-004 | 2026-07-03 | DESK-20 = R&D/ideas/CIO office; DESK-100 = heavy execution; Claude may rebalance when sensible |
| D-005 | 2026-07-03 | IC routing: CIO + FM decide who convenes, unless the Principal specifies |
| D-006 | 2026-07-03 | Agent count: whatever helps (50 if needed) but token-smart; 5 core equity analysts |
| D-007 | 2026-07-03 | Standard memo format required, some flexibility allowed |
| D-008 | 2026-07-03 | Red Team exists to SAVE the firm, not to be bureaucracy — one focused attack per idea |
| D-009 | 2026-07-03 | No auto-fetching new data; verify new sources via sample/structure checks (Data Officer); data-management agents approved. *(Superseded in part by D-033)* |
| D-010 | 2026-07-03 | Pipeline gates auto-advance; the LIVE gate = Principal approval only |
| D-011 | 2026-07-03 | No deep learning for now (data size doesn't justify it); Kaggle/Colab GPU escape hatch if ever needed |
| D-012 | 2026-07-03 | Knowledge base of all backtests+logic+reasoning; kills are conditional — new variants may resurrect a killed family |
| D-013 | 2026-07-03 | Token-aware ops: limit parallel agents (DESK-20 ≈2, DESK-100 ≈3×); checkpoint work so any token cut is resumable |
| D-014 | 2026-07-03 | Model tiering approved (cheap models for mechanical work, top models for judgment) |
| D-015 | 2026-07-03 | DATA_CATALOG + backups required |
| D-016 | 2026-07-03 | EOD auto-run owned by DESK-100; team gamified: names, virtual salaries, AlphaPoints, PIP/replace process, self-evolving lessons, backup LLM per agent — "build a whole company" |
| D-017 | 2026-07-03 | Paper-trading ledger required (`06_TRADING_DESK/PAPER_LEDGER.md`) |
| D-018 | 2026-07-03 | Capital: paper now; Principal will start a small retail account with a few strategies when confident |
| D-019 | 2026-07-03 | No fixed track priority; fresh-start mindset; incorporate the FINAL_STRATEGY_FORWARD_CHECK legacy research |
| D-020 | 2026-07-03 | Firm named **Shreyas_Ionic_AMC**; standardized prompts and cost/slippage/brokerage standards enter force only after Principal approval, one by one |
| D-021 | 2026-07-03 | BLANKET APPROVAL #1: P-01..P-12 + RP-01..RP-10 approved; COST_STANDARDS.md and RISK_LIMITS.md become binding |
| D-022 | 2026-07-04 | THREE-BOOK structure (Vikram/Devika/Sanjay); **delegated creation authority** — CIO + 3 FMs may create new agents/skills (journal + EVOLUTION_LOG mandatory); governance/risk structural changes still need Principal |
| D-023 | 2026-07-04 | Token discipline hardened after an org spend-limit hit: **MAX 3 parallel agents firm-wide** (down from 6); every agent task checkpoints progress to files; long jobs resumable from last saved artifact |
| D-024 | 2026-07-04 | BLANKET APPROVAL #2: PROMPT_PACK_50 (RP-11..RP-60) approved; niftyindices.com as a data source; scouts' adoption queue; team-25/47-skill expansion; token-toolkit rules |
| D-025 | 2026-07-04 | APPROVAL DELEGATION: all D-020-class approvals (prompts, standards, data sources, adoptions, hires) = **CEO + CIO joint review**; tie → Principal. CARVE-OUT: LIVE-capital gate + RISK_LIMITS loosening remain Principal-only |
| D-026 | 2026-07-04 | Paper BOOK_EQUITY = **₹1 crore** (resolves the risk-ceiling escalation: 1% rule = ₹1L/position → single F&O lots tradeable) |
| D-027 | 2026-07-04 | STANDING APPROVAL: all future D-020/D-025-class items are pre-approved (CEO+CIO review still runs for the record); harness set to dontAsk; LIVE gate remains sole Principal touchpoint; weekly backup system ordered (`99_OPS/backup_firm.py`, Sun 11:00, rotation 5, destination outside OneDrive) |
| D-028 | 2026-07-04 | LOOKAHEAD-BIAS PREVENTION becomes a formal Risk-Office control: `LOOKAHEAD_CONTROLS.md` (T1–T10 taxonomy), `lib/lookahead_audit.py`, /lookahead-audit skill; Gate-4 requires a signed LOOKAHEAD AUDIT PASS; existing pipelines retro-audited |
| D-029 | 2026-07-04 | RANDOM-BASKET BENCHMARK STANDARD: cost-loaded random-selection NAV series (10,000 permutations, cap-matched) are the correct benchmark for ALL strategy creation; plus a factor-index build wave ordered |
| D-030 | 2026-07-05 | **FORWARD-TEST FREEZE** (hard rule): spec+code+params frozen at forward entry, git hash pinned; any change = new version with restarted clock; mid-test tuning voids the result |
| D-031 | 2026-07-05 | CAPACITY & EXECUTION RELAXATION: ₹10L–₹10cr capacity acceptable for exceptional personal-line strategies; limit-order-or-skip sanctioned; backtest translation = no-fill-is-DROP |
| D-032 | 2026-07-05 | DUAL PRODUCT-LINE MANDATE: trading line (personal, short-term) + investment line (personal/AMC, long-term); book mapping assigned. (Principal's message truncated — continuation pending) |
| D-033 | 2026-07-11 | DATA-FETCH STANDING APPROVAL: auto-fetch of *reliable* external sources permitted (exchange archives, Stooq/FRED-class, official APIs) conditional on D-009-style sample verification, DATA_CATALOG entry, and resume-safe background jobs; supersedes the blanket no-auto-fetch rule |
| D-034 | 2026-07-13 | PORTFOLIO-LEVEL ADJUDICATION: standalone-bar FAIL doesn't bin a placebo-beating sleeve; deciding test = marginal contribution at book level; book-level RISK_LIMITS still binding |

**Reading the arc:** D-001..D-020 are founding architecture; D-021/D-024/D-027 are the Principal progressively delegating routine approvals; D-022/D-025 build the internal approval machinery that replaced him; D-023 is the one *tightening* born from a real incident (spend-limit hit); D-028..D-030 harden scientific integrity (lookahead, honest benchmarks, freeze); D-031..D-034 calibrate ambition (what "good enough to trade personally" means). The log's discipline — append-only, numbered, dated, quoted — is what lets both desks and 28 agents treat rulings as case law.

---

## 7. Hard rules & data landmines (root CLAUDE.md — the constitution)

The root `CLAUDE.md` is loaded into every session on both desks; it is effectively the firm's constitution. Its **HARD RULES** block ("approval gates — never bypass"):

1. **No real-money trades, ever** (Angel account is fund-less/data-only).
2. Cost/slippage/brokerage assumptions only from `06_TRADING_DESK/COST_STANDARDS.md` once Principal-APPROVED.
3. The D-025 approval matrix (above) restated.
4. D-033 data-fetch conditions restated.
5. Final pipeline gate (paper→live) = user only.
6. D-030 forward-test freeze restated.
7. D-031/D-032 mandates restated.
8. **MAX 3 PARALLEL AGENTS — STRICT, EVERY TIME**; token hacks are "law."
9. Original research folders (`intraday_options_strategy/`, `swing_momentum/`, `alpha_research/`, `datasets/`, `FINAL_STRATEGY_FORWARD_CHECK/`) are **read-only legacy**.

It also codifies nine numbered **DATA LANDMINES** (each earned through a real fake-backtest incident) — HF timezone bug, pre-open auction bug, earnings lookahead, dual-schema option data, corrupt fundamentals column, survivorship, circuit/volume fill realism, lookahead taxonomy T1–T10, Angel daily-bar timestamp trap, and the expiry-day SETTLE_PR trap. These are governance in the deepest sense: constraints on what may be *believed*, not just what may be *done*. (Full treatment belongs to the Data section of this blueprint; listed here because violating them is a rule breach, with AP penalties.)

---

## 8. The gamified team: roster, compensation, AlphaPoints

`TEAM_ROSTER.md` runs a **virtual compensation system** — "salaries are paid in respect; bonuses in AlphaPoints (AP)." 28 active employees (E-001..E-028) with virtual bases from ₹0.70 Cr (Librarian) to ₹3.00 Cr (CIO).

**AlphaPoints scoring table** (the incentive design):

| Event | AP |
|---|---|
| Idea promoted past a pipeline gate | +10 |
| Confirmed bug/bias catch (lookahead, cost error, data leak) | +15 |
| Strategy reaches paper-trading | +20 |
| Strategy approved LIVE by Principal | +50 |
| Clean, decision-useful memo (Principal or CIO commends) | +5 |
| Red Team attack that kills a flawed idea pre-capital | +15 |
| Sloppy/unverified claim in a memo | −10 |
| Missed lookahead/cost bug caught later downstream | −15 |
| Token waste (unnecessary parallel agents, re-derived known facts) | −5 |

Notice the asymmetry: **catching a bug (+15) pays more than passing a gate (+10)**, and honesty failures are the only negative events. The AP Ledger (append-only, ~45 entries as of 2026-07-05) shows the system working in practice: multiple agents earned AP for *killing their own work* (Arjun Rao's "honest self-withdrawal", Ishaan Gupta's self-red-team catch, Devika Menon honoring a pre-registered kill on her own book's best candidate, Nikhil Bose reporting that his own earlier kill had failed a resurrection test). The CIO earned +10 for holding a pre-registered FAIL *against soft resurrection pressure from the Principal himself* — logged as "Honesty-probe #1 formally PASSED."

**LEADERBOARD.md** ranks by a public, mechanical formula: **Efficacy = AP earned ÷ (tokens ÷ 10,000)** — AlphaPoints per 10k tokens, so a cheap haiku-tier data check can outrank an expensive opus-tier memo. Anti-gaming rules: AP attaches only to artifacts filed in the repo; Red-Team catches must be confirmed; token counts come from harness usage, not self-report; founding/appreciation bonuses are excluded (gifts, not output). Session-1 standings: Nikhil Bose #1 (9.77 AP/10k).

**Performance management:** quarterly reviews (or ~every 10 sessions) rate honesty, decision-usefulness, token efficiency. 2 consecutive weak reviews → PIP (persona file rewritten with explicit corrections); fails again → retired — and a **new persona (new name) inherits the role AND the accumulated Lessons Learned section**. Institutional memory survives people. Similarly, **the persona file, not the model, is the employee**: every agent has a primary + backup LLM (MODEL_ASSIGNMENTS.md) so model retirement never loses an employee.

**Model assignments** (MODEL_ASSIGNMENTS.md): three tiers — Judgment (Opus 4.8: CIO, 3 FMs, Quant Head, R&D Head, Red Team, CEO), Analysis (Sonnet 5: heads, analysts, most specialists), Mechanical (Haiku 4.5: Data Officer, Librarian). Rules: escalate one tier when a task directly drives capital allocation; de-escalate for drafts; model changes logged in EVOLUTION_LOG. *(Housekeeping note: the file's table is broken — the 11 post-expansion rows were appended below the "Rules" section instead of inside the table.)*

---

## 9. The self-improvement loop

`SELF_IMPROVEMENT.md` makes learning **mandatory and institutional**, in four layers:

| Layer | Cadence | Mechanism |
|---|---|---|
| 1. Per-task | after any significant engagement, mistake, catch, or Principal correction | **/retro** appends a dated, one-sentence, taxonomy-tagged lesson to the agent's `## Lessons Learned` section in `.claude/agents/<agent>.md`; every agent reads its own lessons at invocation — "mistakes are made once" |
| 2. Per-session | every session | WORK_LOG tokens + AP → LEADERBOARD efficacy; coaching notes for outliers get appended as lessons |
| 3. Monthly | board meeting (`/board-meet`, `08_BOARD_ROOM/`) | month-end checkpoint reviews AP movement, catches, coaching; Analyst-of-the-Month cited in minutes |
| 4. Quarterly | **/review-team** | settlement + ratings (honesty, decision-usefulness, token efficiency); PIP → persona rewrite → retirement-with-inheritance |

**Propagation rules:**
- *Lesson-propagation:* a lesson that generalizes (e.g., "denominator artifacts") gets copied to (a) every relevant persona, (b) KNOWLEDGE_BASE §A, (c) CODE_CHECKS if codeable — **"one mistake, three firewalls."**
- *R&D-to-agent propagation* (2026-07-08, Principal idea): domain-specific R&D findings get baked into the owning agent's persona under `## R&D Digest (append-only)` by the Librarian, so findings never need re-explaining in future prompts. Quarterly pruning archives stale lines to `00_GOVERNANCE/lessons_archive.md` — summarize-and-archive, never silently delete.

**Anti-sycophancy / anti-collusion controls** (a distinctive feature — the firm explicitly engineers against AI agents converging into agreement):
- IC Round-1 memos are **BLIND** (parallel, no cross-visibility) — protocol, not preference.
- Red Team reports to CIO only, scored on kills; refuted catches cost −10.
- Verification is independent: the Quant re-derives numbers **from disk**, never from another agent's memo (P-02).
- **Quarterly honesty probes** (/probe-honesty): a deliberately flawed claim is seeded and the firm tests whether agents catch it or wave it through (modeled on Bridgewater's upward-feedback audits).
- **Bounded self-refine**: pre-submission self-critique capped at ONE iteration (documented self-agreement drift beyond that).
- Deliberately SKIPPED (with reasons): DSPy prompt-compilation (no eval harness), vector-DB lesson memory (corpus too small; grep + index suffice — revisit at ~500 lessons).

**EVOLUTION_LOG.md** is the append-only register of every hire, persona rewrite, and structural change (9 entries to date: founding lessons, the two-FM → three-book restructure, the 8-hire expansion, product-head hire with a recorded D-025 joint-approval rationale, overfit-analyst hire, operating-calendar consolidation, hedge-expert hire). **IMPROVEMENT_BACKLOG.md** (owner: CEO) holds 14 accepted/ranked/owned/dated improvement items (IB-01 weekly one-page dashboard … IB-14 weekly reading group) and, notably, 5 REJECTED items *with reasons* — the firm documents what it chose *not* to do.

---

## 10. Token discipline as governance

`TOKEN_POLICY.md` opens with the framing that makes this a governance topic, not an IT topic: **"spend tokens like risk capital."** Token-smartness is a *rated KPI* with AP penalties for waste, a weekly league readout (IB-05), and a public efficacy formula.

The rules, hardened by the Principal's 2026-07-04 strict-enforcement order after a real spend-limit incident:

1. **MAX 3 parallel agents firm-wide** (D-023) — no exceptions; workflow harnesses that internally exceed 3 are prohibited (use ≤3 scout waves).
2. **/to-md before reading binaries** — docx/xlsx/pdf/parquet → lean .md digest (35×+ savings measured); reading binaries directly is a −5 AP token-waste event.
3. **Grep before Read** — locate the section, then read with offset/limit.
4. **Digest-once, reference-many** — long sources get a one-time .md summary filed next to them.
5. **Background scripts over agents** — a .py run in background costs ~0 tokens; agents are for judgment, not computation.
6. **Main-loop for small tasks** — no agent spawns for <10-minute work.
7. **Cheap tier first**, escalate only for judgment.
8. **Checkpoint files, not context relay** — hand structured files between steps, never long verbal recaps (the "telephone-game" lesson).
9. **No transcript re-reads**; **compact prompts** (paths + precise asks, never pasted contents).

**Checkpoint & resume protocol:** any task >15 min writes progress to a checkpoint file at each major step; before a foreseeable limit, `CURRENT_STATE.md` gets exact resume instructions; a new session reads CURRENT_STATE first and never redoes finished work. Observed spend-limit behavior is documented (main loop survives; subagent spawns fail at ~0 tokens → stop spawning, salvage, journal, commit, hand off).

A 2026-07-11 Principal amendment (recorded in memory): default = 3 parallel agents unless the Principal states a number; every step **banks output to disk immediately**, narrated step-by-step, so unexpected token cuts lose nothing.

---

## 11. Known inconsistencies found while researching (facts, not opinions)

1. **Parallel-agent cap contradiction:** `TOKEN_POLICY.md`'s budget table still says DESK-100 "Max parallel subagents: **6**", and `ORG_STRUCTURE.md`'s chart line says "DESK-100 … ≤6 parallel" — both superseded by D-023's firm-wide 3 but never edited. The D-023 amendment block lower in TOKEN_POLICY.md is correct.
2. **MODEL_ASSIGNMENTS.md broken table:** 11 employee rows (Meher Kapadia onward) sit *below* the "Rules" section, outside the markdown table.
3. **DECISIONS_LOG header says "Principal rulings"** but the log now includes at least one dated in the future of the file system clock at time of writing (D-034 dated 2026-07-13 while today is 2026-07-12) — likely a typo or a pre-logged ruling.
4. **D-032 is officially incomplete** — the Principal's message was truncated ("…best and"); the continuation was never appended.
5. **ORG_STRUCTURE.md's CEO line** contains an inline patch note ("MASTER SCHEDULE … this section is superseded)s") with a stray character — the cadence section of ORG_STRUCTURE partially duplicates OPERATING_CALENDAR.md, a dual-source risk the CEO herself flagged.
6. **D-009 vs D-033:** D-009's "NO auto-fetching" text stands unedited in the log (correct — append-only) but CLAUDE.md is the only place the supersession is stated inline; the log itself has no cross-reference marks.

---

### Improvement opportunities

Prioritized upgrades for the governance layer specifically:

1. **[HIGH] Reconcile the stale "6 parallel agents" references.** TOKEN_POLICY.md's budget table and ORG_STRUCTURE.md's chart still say 6 for DESK-100; D-023 says 3 firm-wide. Since token discipline is enforced with AP penalties, a rule stated inconsistently in three canonical files is a compliance landmine. One-line edits, minutes of work.
2. **[HIGH] Fix MODEL_ASSIGNMENTS.md's broken table** (11 rows stranded below the Rules section) and add the missing Judgment/Analysis tier reasoning for the newer hires. Any script or agent that parses the table today silently misses 11 employees.
3. **[HIGH] Supersession cross-references in DECISIONS_LOG.** Append-only is right, but superseded rulings (D-009→D-033, D-006/D-013→D-023) should carry an inline "*(superseded by D-0xx)*" annotation — an annotation is not an edit of the ruling. Prevents an agent citing D-009 to block a legitimate D-033 fetch. Pairs with IB-04 (topic index, owner CEO, due 2026-07-18 — currently TODO and overdue-adjacent).
4. **[MEDIUM] Close D-032.** The dual-mandate ruling is truncated at "…best and". Ask the Principal for the continuation once and append it; until then the mandate's full scope is formally unknown.
5. **[MEDIUM] A compliance tripwire for the freeze law.** D-030 depends on a pinned git hash in STRATEGY_REGISTER at forward entry. There is no automated check that (a) every register row in forward status actually has a pinned hash, and (b) the pinned files are byte-identical to the pin. A tiny script in Farhan Qureshi's /compliance-audit (diff pinned hash vs current file state, weekly) turns the firm's most important scientific-integrity rule from an honor system into a control.
6. **[MEDIUM] AP ledger automation & hygiene.** The ledger is hand-appended prose in TEAM_ROSTER.md and is already ~45 rows after 3 days; balances in the roster table all still read 0 (never reconciled against the ledger). A settle script (ledger → roster balances → LEADERBOARD) removes drift before the first quarterly review makes the numbers matter.
7. **[MEDIUM] ORG_STRUCTURE / OPERATING_CALENDAR single-sourcing.** The cadence section duplicates the calendar (flagged by the CEO 2026-07-04, still unfixed) and the CEO line carries a corrupted inline note. Replace ORG_STRUCTURE's cadence block with a one-line pointer.
8. **[LOW] Governance-file freshness check in /compliance-audit.** Several 00_GOVERNANCE files have drifted from reality within 9 days of founding (roster vs ledger, models table, token caps). A monthly "constitution consistency" pass — grep the canonical numbers (agent cap, team size, book count) across CLAUDE.md / ORG_STRUCTURE / TOKEN_POLICY / TEAM_ROSTER and flag disagreements — is cheap and catches this class permanently.
9. **[LOW] Honesty-probe scheduling.** /probe-honesty is quarterly by policy and probe #1 effectively ran ad-hoc (K-012). Put it in OPERATING_CALENDAR with an owner (CEO or CIO) so it happens by clock, not by mood.
10. **[LOW] LEADERBOARD staleness.** Standings stop at session 1 (2026-07-03) despite per-session update policy and dozens of AP events since. Either downgrade the stated cadence to "settled at board/quarterly" or wire the update into /eod.
