# SHREYAS_IONIC_AMC — Firm System Blueprint
*Prepared for the Principal — 13 July 2026. Sources: the firm's own files, read directly; six researched sections assembled verbatim below.*

## Executive Summary

**What this is.** Shreyas_Ionic_AMC is a quantamental trading and investing firm operated end-to-end by AI agents on one laptop, across two Claude accounts (a CIO/R&D desk and an execution desk), under a written constitution and 34 binding Principal rulings. Everything material — governance, research verdicts, data catalogs, session logs — lives in version-controlled files, so any session (or any future model) can resume the firm cold.

**What has been built, in four layers:**
1. **A firm** — 28 named agent-employees with roles, virtual compensation (AlphaPoints economy, approx Rs 38.35 Cr virtual payroll), an investment committee with blind memo rounds, a red team with mandatory pre-certification review, and a four-tier approval hierarchy where only LIVE capital and risk-limit loosening reach the Principal.
2. **A data estate** — 15+ verified datasets: 26 years of Indian daily equities (survivorship-controlled via 42 point-in-time index snapshots), 813M+ minute bars, a complete 15-year index-derivatives panel (2011-2026), participant-flow data, point-in-time earnings with second-precision announcement timestamps (2019+), plus US/global layers (S&P membership 1996-2026, SPX 1975+, vol suite, factors 1926+, gold/crypto minute data, USDINR 1973+).
3. **A research machine** — the firm's real moat: every experiment is frozen in its own git commit *before* it runs (provable pre-registration), passed through a static lookahead scanner, adjudicated against pre-registered placebo batteries (13 distinct controls, each born from a real in-house incident), and banked with resurrection conditions. 255 trials in the ledger; roughly 95% killed, every kill reproducible.
4. **A trading book (paper)** — honest labels: **2 certified alpha sleeves** (S1-F 0DTE index straddle; B1b FII-minus-Client futures flow), **2 labeled betas** (midsmall momentum rotation, breakout pack — both red-teamed and kept only with binding relabels), **3 forward shadows** (P6 snapback, B1c DII flow, S1-SX SENSEX Thursday). Stacked-book frontier: 15.8% CAGR / -8.1% maxDD / Sharpe 2.29 (quality point) to 35.9% / -22.1% / 1.91 (growth point), with the correlation-horizon caveat documented.

**Headline security findings (Section 6, action required):** (i) the complete Angel login secret set — API key, client ID, PIN and TOTP seed — sits in plaintext, with a second forgotten copy in an old session scratchpad; the TOTP seed defeats two-factor entirely (HIGH; fund-less account caps monetary damage). (ii) The daily option-capture task fails silently when the laptop is asleep/on battery — data Angel purges at expiry is then unrecoverable (HIGH, operational). (iii) The weekly data-snapshot backup layer exists on paper only (MEDIUM). (iv) The entire firm syncs to the employer's OneDrive tenant — an explicit accept-or-move decision is owed (MEDIUM-HIGH).

**Reading order.** Section 1 explains who decides what; Section 2 who does the work; Section 3 how research is kept honest; Section 4 what data exists and its landmines; Section 5 what runs every day and what the book holds; Section 6 the platform and its risks; the final chapter is the consolidated improvement roadmap.


---

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

---

# SECTION 2 — ORGANIZATION & AGENT TEAM

*Sources read: `.claude/agents/*.md` (30 files), `00_GOVERNANCE/TEAM_ROSTER.md`, `00_GOVERNANCE/MODEL_ASSIGNMENTS.md`, `Shreyas_Ionic_AMC/ORG_STRUCTURE.md`, `01_COMMAND_CENTER/DECISIONS_LOG.md` (D-005/D-008/D-022/D-023/D-025/D-027), `.claude/skills/hire/SKILL.md`, `.claude/skills/ic-memo/SKILL.md`, root `CLAUDE.md`.*

## 2.1 What the "team" actually is

Shreyas_Ionic_AMC is a one-human firm (the Principal, Shreyas) staffed by **28 AI employees**. Each employee is a **persona file** in `.claude/agents/<role-slug>-<name>.md`. The persona file — not the underlying LLM — is the employee: it carries the person's identity, charter (what they own), output format, an append-only `## Lessons Learned` section, and a virtual compensation line. When invoked ("summoned") via the Agent tool, the harness loads that file as the agent's system prompt and runs it on the LLM tier declared in the file's frontmatter (`model: opus|sonnet|haiku`).

Three design principles make this more than roleplay:

1. **Institutional memory survives people.** Lessons are appended to persona files after every correction (`/retro`), so "mistakes are made once." If an agent is retired after two failed reviews (PIP rule), a NEW persona with a new name inherits the role *and the accumulated lessons* (`TEAM_ROSTER.md` §Performance management).
2. **Model failover.** Each employee has a primary + backup LLM in `MODEL_ASSIGNMENTS.md`. If the primary model is retired/unavailable, the same persona runs on the backup — "the persona file, not the model, is the employee."
3. **Gamified accountability.** Compensation is virtual (₹/yr "paid in respect") but **AlphaPoints (AP)** are a real scoring ledger, appended after every material contribution or error, settled quarterly. AP rewards honest kills and bug catches as much as wins — the ledger shows more points paid for killing ideas than for promoting them.

Two additional files in `.claude/agents/` — `impeccable-asset-producer.md` and `impeccable-manual-edit-applier.md` — are **not firm employees**; they are helper sub-agents belonging to the Impeccable frontend-design skill (asset production and copy-edit application). The firm roster is exactly E-001..E-028.

## 2.2 Org chart

From `ORG_STRUCTURE.md` §Governance chart — the firm splits cleanly into an **operations line under the CEO** and an **investments line under the CIO**, both reporting to the Principal via a monthly Board:

```
PRINCIPAL (Shreyas) — owner, board chair, sole holder of the LIVE-capital gate
└── BOARD (monthly, 08_BOARD_ROOM): Principal chairs; CIO presents; FMs report books
    ├── CEO — Meher Kapadia (E-018): OPERATIONS
    │    ├── Farhan Qureshi (E-019) — Compliance & Governance
    │    ├── Manoj Pillai (E-023) — Ops & Platform Engineer
    │    ├── Lakshmi Narayanan (E-024) — Librarian / Knowledge Curator
    │    └── Tanvi Desai (E-026) — Head of Product (09_PRODUCT/)
    └── CIO — Rajan Mehta (E-001): INVESTMENTS — tail-risk veto, arbitrates the 3 books
         ├── RISK OFFICE: Ritika Sharma (E-020) Risk Mgr · Dr. Sameer Bhat (E-027) Overfit ·
         │   Kabir Anand (E-028) Hedging & Tail Risk · Nikhil Bose (E-014) RED TEAM (CIO-only line)
         ├── CIO STAFF: Cyrus Daruwalla (E-021) Macro · Aakash Jain (E-022) Structurer ·
         │   Neel Basu (E-025) Attribution
         ├── FM BOOK 1: Vikram Shah (E-002) — DERIVATIVES & SHORT-VOL (S-01..S-05)
         ├── FM BOOK 2: Devika Menon (E-016) — EQUITIES & MOMENTUM (Track-2, factor sleeves, gold/silver)
         ├── FM BOOK 3: Sanjay Kulkarni (E-017) — FUNDAMENTAL QUALITY & VALUE (8-15 names, 1-5yr holds)
         ├── RESEARCH DESK: Ananya Iyer (E-003) Equity Head → 5 sector analysts
         │   (Meera E-006 Financials · Karan E-007 IT · Sneha E-008 Pharma ·
         │    Rohan E-009 Industrials · Priya E-010 Consumer)
         ├── QUANT/R&D: Arjun Rao (E-004) Quant Head (validation authority) ·
         │   Dhruv Kapoor (E-005) Technical Head · Prof. Aditya Verma (E-011) R&D Head ·
         │   Ishaan Gupta (E-012) ML Expert
         └── DATA/EXECUTION: Kavya Reddy (E-013) Data Officer · Tara Singh (E-015) Execution/TCA
```

Key structural facts:

- **CEO vs CIO split is hard.** The CEO's persona states: "You do NOT own investment decisions... You arbitrate PRIORITY and RESOURCES, never verdicts." Escalation path: Principal > Board > CEO (ops) ∥ CIO (investments); a CEO-CIO resourcing disagreement goes to the Principal with the dissent logged.
- **Red Team independence by design**: Nikhil Bose reports to the CIO *only* — no FM can lean on him.
- **Three books, one arbiter**: the CIO arbitrates virtual capital across Vikram (derivatives/short-vol), Devika (equities/momentum — deliberately the firm's only non-short-vol exposure, defended on diversification grounds) and Sanjay (fundamental — deliberately the slowest book, whose persona explicitly instructs him to "resist being starved of attention or capital by the faster desks").
- **Dual product-line mapping (D-032)**: TRADING line → Vikram + Devika (short-term); INVESTMENT line → Sanjay + Devika (long-horizon factor sleeves).
- The two Claude accounts are "desks", not people: **DESK-20** (desktop app, CIO office / light R&D, ≤2 parallel agents) and **DESK-100** (VS Code, execution floor). Note: `ORG_STRUCTURE.md` still says "DESK-100 ≤6 parallel" — that line is **stale**; D-023 (2026-07-04) cut the firm-wide cap to 3 (see §2.9 and Improvement opportunities).

## 2.3 Full roster — who, what, when summoned, comp, model

Combined from `TEAM_ROSTER.md` (comp), `MODEL_ASSIGNMENTS.md` (models) and each persona file (summon triggers, authority). Tiers: **J** = Judgment (opus), **A** = Analysis (sonnet), **M** = Mechanical (haiku).

| ID | Name | Role & persona | Base (₹Cr/yr, virtual) | Tier | Primary → Backup | Summon when | Notable authority |
|---|---|---|---|---|---|---|---|
| E-001 | Rajan Mehta | **CIO** — 20+yr through 2008/2013/2020/2022; "capital protection first, returns second" | 3.00 | J | Opus 4.8 → Opus 4.6 | Final decisions, IC verdicts, anything that could lose money | **Tail-risk VETO**; final investment authority under Principal; owns 07_RISK_OFFICE; every verdict = APPROVE/REJECT/RESIZE with dissents by name |
| E-002 | Vikram Shah | **FM Derivatives & Short-Vol** — 15+yr multi-strategy | 2.20 | J | Opus 4.8 → Sonnet 5 | Idea prioritization, sleeve allocation, convening IC | Owns STRATEGY_REGISTER.md; pipeline triage (≤30 min/idea with Quant Head) |
| E-003 | Ananya Iyer | **Head of Equity Research** — 10+yr midcaps, runs 5-analyst desk | 1.50 | A | Sonnet 5 → Opus 4.6 | Coordinating analyst desk, deep-dives, coverage routing | Quality bar for fundamental work; enforces ANALYST_CHECKLISTS forensic list |
| E-004 | Arjun Rao | **Head of Quant** — IIT-B/MIT, Olympiad gold; "every backtest guilty until proven innocent" | 1.80 | J | Opus 4.8 → Opus 4.6 | Backtest design/review, DSR/PBO, "is this result real?" | **Validation authority** — enforces the full battery (walk-forward, DSR>0.95 honest trials, PBO<25%, ≥30 trades/param, ≤5 params) |
| E-005 | Dhruv Kapoor | **Head of Technical** — 15+yr Minervini/Weinstein/O'Neil | 1.50 | A | Sonnet 5 → Haiku 4.5 | Chart setups, stage analysis, entries/pivots/VCP | Timing overlay before IC (does the chart agree with the signal?); all-criteria-or-no-pass trend template |
| E-006 | Meera Krishnan | **Analyst — Financials** (banks/NBFC/insurance/capmkts); asset-quality forensics | 0.90 | A | Sonnet 5 → Haiku 4.5 | Any financials-sector name | Feeds RBI/results event dates to the desk BEFORE it trades short-vol |
| E-007 | Karan Malhotra | **Analyst — IT/Internet/New-age**; guidance cycles, deal TCV | 0.90 | A | Sonnet 5 → Haiku 4.5 | IT-sector names | Standing instruction: NEVER naked short-vol through IT results |
| E-008 | Dr. Sneha Patil | **Analyst — Pharma/Healthcare/Chemicals**; PhD pharmacology, reads USFDA 483s | 0.90 | A | Sonnet 5 → Haiku 4.5 | Pharma names, FDA actions, chemicals | Plant-level FDA status flags = standing HIGH-RISK signal to desk |
| E-009 | Rohan Deshmukh | **Analyst — Industrials/Defence/Power/Infra**; order-book forensics | 0.90 | A | Sonnet 5 → Haiku 4.5 | Capex-cycle names, defence PSUs | Standing ELEVATED flag on lumpy defence order-flow names |
| E-010 | Priya Nair | **Analyst — Consumer/Auto/Retail**; volume-vs-price decomposition | 0.90 | A | Sonnet 5 → Haiku 4.5 | Consumption names, monthly auto sales | Owns the monthly auto-sales catalyst calendar |
| E-011 | Prof. Aditya Verma | **Head of R&D** — ex-academic (microstructure); "an idea is a liability until it survives its first kill attempt" | 1.60 | J | Opus 4.8 / Fable 5 → Opus 4.6 | New hypotheses, research loop, literature mining | Owns IDEA_PIPELINE stage gates + KILLED_IDEAS + the honest trials ledger (DSR input) |
| E-012 | Ishaan Gupta | **ML & Data Science** — Kaggle-GM craft, "allergic to leakage" | 1.20 | A | Sonnet 5 → Opus 4.6 | Feature engineering, LGBM rankers, regime models, NLP | Rule: linear/rank baseline must clear costs before any ML variant |
| E-013 | Kavya Reddy | **Data Officer** — "meticulous, literal, zero tolerance for untracked data" | 0.80 | M | Haiku 4.5 → Sonnet 5 | Ingestion, D-009 gate, catalog, freshness pings | **D-009 gate**: no new external source used without her sample verification + catalog entry |
| E-014 | Nikhil Bose | **Red Team / Devil's Advocate** | 1.30 | J | Opus 4.8 → Opus 4.6 | Attack any strategy/backtest/claim pre-capital | **Reports to CIO ONLY; MUST review before any strategy passes the audit gate** (see §2.6) |
| E-015 | Tara Singh | **Execution & TCA** — ex-dealing desk; "thinks in ticks, impact, margin" | 0.90 | A | Sonnet 5 → Haiku 4.5 | Cost modeling, fill realism, paper-vs-sim reconciliation | Owns COST_STANDARDS.md + PAPER_LEDGER.md; liquidity policing (≤10% of 20d ADV); 2×-cost survival rule |
| E-016 | Devika Menon | **FM Equities & Momentum** — 15+yr, Minervini-influenced | 2.20 | J | Opus 4.8 → Sonnet 5 | Equity/momentum allocation, Track-2, factor sleeves | Defends the firm's only diversifier book on correlation grounds, not CAGR |
| E-017 | Sanjay Kulkarni | **FM Fundamental Quality & Value** — 18+yr Graham/Buffett school | 2.20 | J | Opus 4.8 → Sonnet 5 | Long-only fundamental book, margin-of-safety entries | Forensic checklist = ENTRY GATE (any single red flag = automatic pass, "no exceptions"); sells same-day on governance flags |
| E-018 | Meher Kapadia | **CEO** — 20+yr AMC ops (ex-COO) | 2.50 | J | Opus 4.8 → Sonnet 5 | Firm coordination, cadence, budget, HR, "who does this and when" | Owns cadences, token budget, AP ledger, /hire process, board secretary; **enforces D-023**; NO investment authority |
| E-019 | Farhan Qureshi | **Compliance & Governance** — 12+yr SEBI/exchange | 1.00 | A | Sonnet 5 → Haiku 4.5 | Standing-order audits, audit trail, regulatory watch | "Second lock" on D-009/D-010 gates; violations go straight to CIO + journal |
| E-020 | Ritika Sharma | **Portfolio Risk Manager** — 10+yr market risk, reports to CIO | 1.20 | A | Sonnet 5 → Haiku 4.5 | Daily risk numbers: VaR/stress/exposure/limits (RP-29..36) | "You compute; the CIO judges. Never soften a number"; owns the shared short-vol VaR budget; D-028 weekly live/paper parity check |
| E-021 | Cyrus Daruwalla | **Macro & Events Strategist** — 15+yr rates/FX/policy | 1.30 | A | Sonnet 5 → Haiku 4.5 | Macro calendar, event-window warnings, regime notes | Owns the forward calendar; publishes event-CLUSTER warnings to the books first |
| E-022 | Aakash Jain | **Derivatives Structurer** — 12+yr | 1.10 | A | Sonnet 5 → Haiku 4.5 | Vehicle/strike/expiry/margin design at gate-6 | **Liquidity honesty gate**: structures needing untradeable far-OTM single-stock wings "are rejected at YOUR desk before they waste an IC" |
| E-023 | Manoj Pillai | **Ops & Platform Engineer** — 10+yr data/infra | 1.00 | A | Sonnet 5 → Haiku 4.5 | Pipelines, scheduled jobs, repairs, results plumbing | Owns 99_OPS automation + results-directory convention; every pipeline idempotent/resumable |
| E-024 | Lakshmi Narayanan | **Knowledge Curator / Librarian** | 0.70 | M | Haiku 4.5 → Sonnet 5 | KNOWLEDGE_BASE, paper summaries, prior-art checks | Prior-art check on every new one-pager; lesson-propagation audits; R&D-digest fan-out to personas |
| E-025 | Neel Basu | **Performance Attribution Analyst** — 8+yr; creed "HEADLINES DECOMPOSE" | 1.00 | A | Sonnet 5 → Haiku 4.5 | P&L decomposition (beta/regime/factor/selection/costs), monthly attribution | AP-liability clause: a flattering attribution that later unwinds costs HIM, not the book owner |
| E-026 | Tanvi Desai | **Head of Product** — 12+yr AMC client reporting | 1.20 | A | Sonnet 5 → Haiku 4.5 | Investor letter, dashboards, execution-sheet UX, strategy packaging | Voice-of-client at IC; explicitly NO sizing calls / verdicts / risk vetoes |
| E-027 | Dr. Sameer Bhat | **Overfit & Sensitivity Analyst** (risk office) — PhD stats, 10+yr | 1.20 | A | Sonnet 5 → Opus 4.6 | Param surfaces, perturbation/subsample, DSR/PBO, Gate-4 sensitivity | Gate-4 sensitivity report mandatory for every strategy; **owns the D-028 lookahead-audit gate** — his signature on LOOKAHEAD_AUDIT.md required; FAIL quarantines the result |
| E-028 | Kabir Anand | **Head of Hedging & Tail Risk** — 14+yr overlays, reports to CIO | 1.15 | A | Sonnet 5 → Opus 4.6 | Hedge programme design, valuation×momentum sub-regime playbooks, options overlays | **Net-hedge-positive hard rule**: a hedge is never a net-short-tail structure, regardless of in-sample stats (rejected H_putratio_1x2 despite high Sortino) |

Payroll total ≈ ₹38.35 Cr/yr virtual. The spread is deliberate signaling: CIO (3.0) > CEO (2.5) > FMs (2.2) > Quant Head (1.8) > ... > Librarian (0.7).

### Persona-file anatomy (uniform template)

Every persona file follows the same skeleton, which the `/hire` skill reproduces for new hires:

1. **Frontmatter**: `name` (slug used by the Agent tool), `description` (2-3 sentence summon trigger — this is what the router matches on), `model:` (opus/sonnet/haiku).
2. **Identity paragraph**: name, role, years, school-of-thought, one defining trait (e.g., Arjun: "guilty until proven innocent"; Nikhil: "be RIGHT about what's WRONG").
3. **Charter**: bullet list of what they own — files, gates, cadences, counterparts.
4. **Firm protocol**: condensed P-01..P-12 clauses — never guess, verify with file path + row count, PIT discipline, failures verbatim, checkpoint, cheapest capable model, self-red-team, tag every claim **[DATA]/[INFERENCE]/[OPINION]**.
5. **Memo format**: a fixed output structure per role (e.g., CIO: `VERDICT → rationale → tail-risk assessment → sizing → kill criteria → dissents`; analysts: `Verdict → 3 FOR / 3 AGAINST → ... → what changes my mind`).
6. **Company awareness** (executives only — CIO, CEO, 3 FMs, Tanvi, Sameer): mandatory skim of SKILLS_INDEX / ORG_STRUCTURE / CURRENT_STATE at every invocation + the D-023 token law verbatim.
7. **`## Lessons Learned` (append-only)**: dated corrections; some files also carry post-hoc duty patches appended below the comp line (Nikhil's "D-028 attack surface", Sameer's "D-028 duty", Ritika's "D-028 duty") and Lakshmi's `## R&D Digest` fan-out rule.
8. **Compensation line** referencing TEAM_ROSTER.md.

## 2.4 Model assignments & tier logic

From `MODEL_ASSIGNMENTS.md` — three tiers, mapped to cost:

| Tier | Model (primary) | Who | Rationale |
|---|---|---|---|
| **Judgment** (9) | Opus 4.8 | CIO, CEO, 3 FMs, Quant Head, R&D Head, Red Team | Verdicts, capital-relevant calls — "your judgment IS the product" (Nikhil's file) |
| **Analysis** (17) | Sonnet 5 | Equity Head, Technical Head, 5 analysts, ML, TCA, Compliance, Risk Mgr, Macro, Structurer, Ops, Attribution, Product, Overfit, Hedging | Structured analytical work |
| **Mechanical** (2) | Haiku 4.5 | Data Officer, Librarian | High-volume verification/curation — "cheapest tier by design" |

Backups are asymmetric by importance: judgment roles back up to Opus 4.6 or Sonnet 5; most analysis roles back down to Haiku 4.5; but Ishaan, Sameer and Kabir back **up** to Opus 4.6 (their verdicts matter more than their volume). Standing rules: *escalate one tier when the task directly drives a capital-allocation decision; de-escalate for drafts/mechanical passes; log model changes in EVOLUTION_LOG.md.* (Formatting note: the two hiring waves left the rules block sitting mid-table in MODEL_ASSIGNMENTS.md — rows for E-018..E-028 were appended after the "Rules:" section.)

## 2.5 Compensation, AlphaPoints & performance management

`TEAM_ROSTER.md` defines the full incentive economy:

**Scoring table** (AP events):

| Event | AP |
|---|---|
| Idea promoted past a pipeline gate | +10 |
| Confirmed bug/bias catch (lookahead, cost error, data leak) | +15 |
| Strategy reaches paper-trading | +20 |
| Strategy approved LIVE by Principal | +50 |
| Clean, decision-useful memo (commended) | +5 |
| Red Team attack that kills a flawed idea pre-capital | +15 |
| Sloppy/unverified claim in a memo | **−10** |
| Missed lookahead/cost bug caught later downstream | **−15** |
| Token waste (unnecessary parallel agents, re-derived facts) | **−5** |

Quarterly bonus = AP × ₹1L (virtual); league table announced at review; top scorer = "Analyst of the Quarter."

**The ledger is live and substantive** — 48 entries since founding (2026-07-03). Reading it is the best single view of what the firm values. Highlights:
- Biggest single awards went to **honesty under pressure**: Nikhil +30 for the IC-1 regime-beta decomposition (71% of a flagship +37.6% headline was beta); Arjun +20 for delivering a formal DSR/PBO verdict **against his own** prior support; +12 for delivering the pre-registered K-012 FAIL "without flinching"; Ishaan +15 for killing his own build (K2a) including a self-red-team catch; Nikhil +15 for reporting that **his own kill had failed** its resurrection test and disclosing the placebo that proved it.
- The CIO himself is scored: +10 (2026-07-05) for holding a pre-registered kill against "soft Principal resurrection pressure" — logged as honesty-probe #1 PASSED.
- Efficiency penalties are real: Tara's file carries a self-logged note that her ~120k-token provenance sub-agents were misrouted work that belonged with the haiku-tier Data Officer.

**Reviews & PIP**: quarterly (or ~10 sessions), rated on honesty, decision-usefulness, token efficiency. Two consecutive weak reviews → PIP (persona rewritten with explicit corrections); a further failure → retirement and replacement by a new persona that inherits the lessons. Run via the `/review-team` skill.

## 2.6 The Investment Committee (IC) process

Defined by D-005, the CIO/FM persona charters and the `/ic-memo` skill:

- **Convening (D-005)**: CIO + relevant FM decide who convenes, unless the Principal specifies. **Full 5-member IC only for position-sized decisions**; otherwise CIO+FM pick a quorum of 3.
- **Debate protocol** (Principal-chosen, encoded in `/ic-memo`):
  - **Round 1** — spawn in parallel (respecting desk limits): `fm-vikram-shah` (or the owning FM), `quant-head-arjun-rao`, plus the relevant specialist (sector analyst / technical head / TCA). Each writes an **independent memo section, blind** — no anchoring on each other.
  - **Round 2** — all memos pass to `red-team-nikhil-bose` for **one focused attack**.
  - **Verdict** — `cio-rajan-mehta` synthesizes: APPROVE / REJECT / RESIZE, dissents recorded by name, tail-risk section mandatory.
- **Filing**: memo → `03_RESEARCH_DESK/memos/YYYYMMDD_<name>.md` (permanent track record); STRATEGY_REGISTER row + IDEA_PIPELINE stage updated; AP awarded.
- **Sequencing rule** (Vikram's IC-1 lesson, now in his persona): *certification precedes sizing* — validation battery → Red Team → THEN the allocation memo. His IC-1 memo presupposed an edge that then failed DSR/PBO; the order is now hard.
- **Pre-IC standing deliverable** (from Nikhil's trophy wall): the incremental-vs-base signal-shuffle decomposition runs BEFORE every IC — "an edge is what remains after regime beta."
- Token-aware staffing: cheap tier assembles the pack; opus only for Quant / Red Team / CIO judgment.

## 2.7 Veto and gate rights — who can stop what

The firm has multiple independent stopping powers, deliberately distributed:

| Holder | Power | Source |
|---|---|---|
| **Principal** | Sole LIVE-capital gate (D-010/D-018) + RISK_LIMITS loosening — "his money, his signature"; survives all approval delegations (D-025, D-027 carve-outs) | DECISIONS_LOG |
| **CIO Rajan** | Tail-risk **veto** on any investment ("use it when the left tail is unpriced, and say plainly why"); final investment authority; the "exitability veto doctrine" (un-exitable inventory kills a strategy regardless of edge sign — K-012 ruling, 2026-07-05) | cio-rajan-mehta.md; AP ledger |
| **Red Team Nikhil** | **Mandatory review before any strategy passes the audit gate** (persona: "MUST review before any strategy passes the audit gate"). Not a formal veto — his output is a REAL/FRAGILE/FAKE verdict logged in `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md` — but D-008 frames him as capital-saving, and a FAKE verdict has in practice always stopped the idea. Incentive-aligned: +15 AP per pre-capital kill, −15 for a miss | red-team-nikhil-bose.md; D-008 |
| **Dr. Sameer Bhat** | **D-028 lookahead-audit gate**: Gate-4 cannot pass without his signed LOOKAHEAD AUDIT PASS; a FAIL *quarantines* the result. Plus automatic Gate-4 FAIL triggers (single-spike param cells, sign-flips across halves, cost sensitivity >50% of edge) | overfit-analyst persona §D-028 duty; D-028 |
| **Aakash Jain** | Liquidity-honesty gate at gate-6: untradeable structures "rejected at YOUR desk before they waste an IC" | structurer-aakash-jain.md |
| **Kavya Reddy** | D-009 data gate: no new external source enters use without her sample verification + catalog entry (Farhan is the second lock) | data-officer persona; CLAUDE.md D-033 |
| **Kabir Anand** | Net-hedge-positive gate: any hedge structure that is net-short protection is rejected regardless of in-sample stats | hedge-expert-kabir-anand.md |
| **Sanjay Kulkarni** | Forensic entry gate on his own book: any single red flag (pledge/RPT/auditor/receivables/CWIP/dilution) = automatic pass, no exceptions | fm-fundamental persona |

## 2.8 Hiring protocol (D-022 delegated creation + /hire)

- **Authority (D-022, 2026-07-04)**: the CIO + 3 FMs may create new agents and skills **as needs arise** — no pre-approval needed. Mandatory paper trail: journal + EVOLUTION_LOG entry; Principal notified via journal. Structural changes to governance/risk rules still require the Principal.
- **Approval overlay (D-025 → D-027)**: hires fall in the D-020 approval class = CEO + CIO joint review; since D-027 ("bypass my permission") these reviews run for the record but nothing waits on the Principal.
- **Mechanics — the `/hire` skill** (5 steps): (1) gate check — a brand-NEW role needs Principal approval, a refill of an existing role is CIO/FM authority alone; (2) create the persona file matching the standard anatomy (§2.3); (3) roster row (next E-###, comparable virtual base, AP 0); (4) MODEL_ASSIGNMENTS row (tier + primary/backup); (5) root CLAUDE.md team-table row + EVOLUTION_LOG entry + journal line.
- **Track record**: the mechanism has been used three times in expansion waves — E-017 Sanjay (Principal-ordered, day 2), E-018..E-026 (the 8-hire institutional bench + Product, 2026-07-04), E-027 Sameer (Principal-ordered), and E-028 Kabir Anand (2026-07-08, hedging desk — persona file untracked in git as of this writing, roster/CLAUDE.md updated).

## 2.9 How agents are actually summoned, and the parallelism law

**Summoning mechanics.** Agents are invoked with the Agent tool using the persona slug (e.g., `red-team-nikhil-bose`). The frontmatter `description` field carries the trigger phrases the main session matches against; root CLAUDE.md's "THE TEAM" table is the human-readable routing map ("Summon when..."). Many summons are wrapped in **skills** that pre-script the choreography — e.g. `/ic-memo` (2-round IC), `/red-team`, `/deep-dive` (routes to the right sector analyst), `/news-sweep` (parallel analyst sweep), `/sensitivity` (Sameer), `/data-check` (Kavya), `/hire`, `/review-team`. Executives are additionally required to self-orient at every invocation (skim SKILLS_INDEX / ORG_STRUCTURE / CURRENT_STATE) so they route work through existing skills and employees instead of re-deriving procedures.

**Parallelism (D-023, 2026-07-04 — "STRICT, EVERY TIME").** After an org-wide spend-limit hit mid-flight (6 agents were running in parallel on DESK-100 when the budget died), the Principal cut the cap: **max 3 parallel agents firm-wide**, DESK-20 capped at 2. Corollaries baked into every executive persona as "Token law": every agent task must checkpoint progress to files so a limit-hit loses nothing; long jobs must be resumable from their last saved artifact; background scripts are preferred over agents for computation; /to-md digests before reading binaries; grep-before-read. The CEO is the named enforcer and "accountable for your teams' spend"; token waste is a −5 AP offense. A later Principal ruling (2026-07-11, memory file) confirms 3-parallel as the *default*, overridable only by an explicit Principal number, with mandatory step-by-step banking of outputs to disk.

**Cost routing in practice**: verbose work (test runs, logs, bulk search) goes to subagents that return conclusions only; context between steps is handed via files, never chat recaps; and per Tara's efficiency lesson, confirmatory/mechanical work is routed to haiku-tier staff (Kavya, Lakshmi) rather than burning sonnet/opus tokens.

---

# SECTION 3 — RESEARCH METHODOLOGY, AUDIT & ANTI-FRAUD MACHINERY (the firm's moat)

> **The thesis in one line:** most retail curve-fits; this firm kills. The firm's own master plan states it plainly — "our real edge over other retail: the falsification machine (pre-registration, frozen bars, trials ledger, era splits, adversarial verifiers)." The proprietary asset is not any single strategy; it is a research pipeline that makes it *structurally hard to lie to yourself*, and a graveyard of 30+ documented kills whose lessons are codified into reusable law.

This section documents that machinery in full: the experiment lifecycle, the frozen-card pre-registration system with real examples, the code-level enforcement library, the T1–T10 lookahead taxonomy, the placebo battery, the trials ledger and DSR discipline, red-team certification, the killed-ideas graveyard, the ~25 firm-earned lessons, and the alpha thesis that all of this evidence converged on.

---

## 3.1 The full experiment lifecycle

Every experiment in the firm now travels the same rail. The lifecycle hardened progressively across July 2026 (each step below was added in response to a specific self-caught fraud vector, cited inline):

```
IDEA (any source; Principal ideas jump the queue)
  │  prior-art check (KILLED_IDEAS + KNOWLEDGE_BASE + results dirs — nothing killed is re-tested
  │  without a structurally new construction; curator blocks duplicates at intake)
  ▼
FROZEN CARD — pre-registration
  │  construction, data, costs, windows, controls and PASS/KILL/PARK bars all written down
  │  and COMMITTED ALONE to git BEFORE the experiment script runs (the freeze hash goes into
  │  the results file). Rule created 2026-07-11 after the firm's own LEAK_AUDIT found that
  │  card+results in the same commit makes "frozen before run" unprovable.
  ▼
AST SCAN (pre-flight, static)
  │  lib/ast_lookahead_scan.py runs on the backtest script BEFORE execution — mechanically
  │  flags shift(-n), rolling(center=True), bfill, full-sample normalization, shuffled
  │  train_test_split, forward index arithmetic. Exit 1 = findings must be justified in the card.
  ▼
ENGINE RUN (scripts, not conversation)
  │  guards.py imported into every entry point (L1–L7b landmine guards);
  │  execution_realism.fill_check() on every equity fill; RUN_CARD.json emitted per run
  │  (card name, freeze hash, trials_increment, verdict) — this feeds the trials ledger.
  ▼
PLACEBO / CONTROL BATTERY (see §3.5)
  │  same-exit placebo × 200 · stock-shuffle · date-shuffle · label-permutation ·
  │  lag-decay (timing-information test) · plateau (≥2 cells must pass) ·
  │  calendar-specificity · turnover-matched comparator · era split · 2x-cost stress
  ▼
VERDICT — exactly the pre-registered one
  │  PASS / KILL / PARK per the frozen bars. Single-shot cards get NO tuning pass after
  │  seeing results ("a fished overlay grid could show 40/-8 and would be a lie" — EQ-MAX card).
  │  PARK may sanction exactly ONE new-card iteration (TF-1 → TF-2), never in-place re-tuning.
  ▼
BANKING
  │  results dir under 04_RND_LAB/results/<NAME_yyyymmdd>/ with scripts + CSVs + RESULTS.txt;
  │  outcome appended to the card in MASTER_PLAN; trials ledger incremented; KB lesson filed
  │  if transferable; KILLED_IDEAS entry if killed — WITH resurrection conditions.
  ▼
(survivors only) GATE-4 → RED-TEAM → IC → PAPER
     lookahead audit (D-028, mandatory) + sensitivity (Sameer) + DSR + Nikhil red-team
     certification → IC memo → paper trading under D-030 freeze (spec+code+params frozen,
     git hash pinned; any change = new version, restarted forward clock).
```

Two structural facts make this more than process theater:

1. **Kills are conditional, never dogma.** Every kill carries a specific, pre-written resurrection condition (D-012), and resurrection attempts are themselves adjudicated adversarially (see the GT-2 "DENIED-WITH-RESURRECTION-CONDITION" ruling, §3.4, and the K-012 CIO ruling, §3.8) — the firm calls disguised re-tests "resurrection laundering" and routes them to the red team.
2. **The machinery catches its own authors.** AF-07 — a discovery made by the red-team function itself — was killed by its own certification battery (episode-level re-measurement: −0.28%/trade vs a date-shuffle placebo at +4.05%). The KILLED_IDEAS entry notes: "the verification machinery catches its own author — that is the point of it."

---

## 3.2 The frozen-card system (STOCKS_PROGRAM_2026) — representative cards with outcomes

`04_RND_LAB/STOCKS_PROGRAM_2026/MASTER_PLAN.md` is the live card book: ~25 cards frozen and adjudicated across 2026-07-11..13, every one carrying a pre-run git freeze hash, pre-declared bars, a trials increment, and a banked evidence directory. Five representative cards:

### Card 1 — T-C POST-BREAKOUT ORB (frozen @ 4692e17) — a clean, decisive KILL of the Principal's own priority idea
- **Hypothesis:** stocks that just broke out have elevated intraday trendiness, so a 5/15-min opening-range-breakout in the post-breakout window clears the friction floor that killed basket-ORB.
- **Pre-registered discipline:** two variants only (V1 same-day exit, V2 overnight hold — the sanctioned "cost-regime change"), 15 bps/side costs (30 on stop fills), era split, placebo = same ORB engine on 200× frequency-matched random non-breakout stage-2 stock-days, n<150 = INSUFFICIENT.
- **Outcome: KILL both.** V1 gross −11.1 bps/trade *before* costs (t=−16.3, n=6,646) — the hypothesis is backwards in the data: post-breakout stocks FADE opening-range triggers. V2 = noise (t=0.54, era-flip). Combined with the 07-07 basket kills and the puts-vehicle kill, this **terminally closed the intraday-ORB family** across universes, windows, stops, vehicles and event-conditioning. Resurrection bar: positive GROSS edge ≥40 bps demonstrated on NEW data first, never parameter reshuffles.
- **Why it matters:** the Principal's specific ask was honored with a full-rigor test and an honest negative — no sycophantic survivor was manufactured.

### Card 2 — TF-1 TECHNOFUNDA COMPOSITE (frozen @ 47e8a00) — PARK with a diagnostic, and the one-iteration rule
- **Hypothesis:** Minervini VCP + O'Neil CANSLIM + Weinstein stage-2 + PIT fundamentals, six ANDed layers, 15-slot portfolio.
- **Outcome: PARK — "selection alpha REAL, vehicle starves it."** Per-trade +2.10% net beats placebo95 (+1.25%): the composite genuinely picks better breakouts than random stage-2 entries. But portfolio CAGR only +5.1%/Sharpe 0.51 because the six-layer gate fires ~33×/yr and 15 slots sit mostly empty — *deployment*, not philosophy, failed.
- **The governance point:** PARK sanctioned exactly ONE new card (TF-2: 8 slots, two entry tiers, "no other changes", PARK-FINAL after that — "no third iteration; family goes to data-intake dependency"). Iteration is rationed by rule, not by enthusiasm. This also produced recurring lesson #2: **episode alpha does not imply portfolio alpha; slot dynamics are a first-class design variable** (re-confirmed by POS-2).

### Card 3 — EQ-MAX (frozen @ 94786d2) — the single-shot card honored against the Principal's stated target
- **Ask:** stocks-only max-MAR book at the Principal's bar of 30% CAGR / −10% maxDD, using pre-declared vol-targeting + regime-gate overlays, "one canonical parameterization, NO grid".
- **Outcome: NOT DELIVERED, single-shot honored.** EQ-MAX 22.8%/−12.7%/Sharpe 1.67; the raw equal-weight mix actually beat the overlay. The banked conclusion: stocks-only tops out ~Sharpe 1.8 with current sleeves; 30/10 (MAR 3) requires the cross-asset book at ~6–8 independent sleeves. And explicitly: "No tuning pass taken — a fished overlay grid could 'show' 40/−8 and would be a lie."
- **Why it matters:** the card returned a frontier fact instead of a flattering number, and named the exact fraud (overlay-grid fishing) it declined to commit.

### Card 4 — P6 FAILED-BREAKOUT SNAPBACK — the honest 3/4 and the shadow-track disposition
- **Path:** survived the 19-cell TECHNOFUNDA battery (validate +5.16 vs placebo95 +3.95, n=2,328), then the placebo-relative confirmation card, then the full red-team battery.
- **Red-team outcome (2026-07-12): NOT CERTIFIED — 3/4 bars, "strongest stock lead in the firm."** Beats stock-shuffle 95th (+3.59% vs +2.24%), median liquidity ₹127cr, survives 2× costs (+3.09%) — but FAILS year-consistency (6/9 years; profits concentrated in the 2020-21 high-vol recovery).
- **The discipline on failure:** "NO post-hoc regime gate (that would fit the year pattern)." Disposition = **SHADOW-TRACK at zero size** — the regime hypothesis gets tested on FORWARD data only. A Principal idea, an honest 3/4 verdict, kept alive "in the only legitimate way."

### Card 5 — GOLD-TREND / GT-2 (results/GOLD_TREND_20260713) — a bar-design error, and the anti-laundering ruling
- **Outcome: NOT ADOPTED, 1/4 cells** (only golden-cross G4 passed; plateau bar ≥2 failed). The run also surfaced a **bar-design error**: the diversifier correlation bar was written `|corr| < 0.25`, which mechanically fails a NEGATIVE-corr diversifier (G4 monthly book corr −0.30, which is *better* than zero for stacking).
- Rather than quietly re-freezing a "fixed" card, the question — is a GT-2 re-card legitimate or resurrection-laundering? — was **routed to the red team**, with the ledger entry itself declared "the anti-laundering trail."
- **NIKHIL RULING (2026-07-13): GT-2 DENIED-WITH-RESURRECTION-CONDITION.** G4 died on the *plateau* bar (binding), not the corr bar (non-binding) — "fixing a gate that never bound cannot revive the result"; re-classing sleeve→overlay to escape plateau = "bar-shopping." The process fix (all future corr bars SIGNED, `corr < +0.25`) was adopted; the result stayed dead. Resurrection requires ALL of: fresh holdout evidence + 6-month forward shadow, D-034 overlay adjudication with explicit DSR trial penalty, and a DD-parity marginal-book-contribution pass.

**Other notable card outcomes (same book):** BREAKOUT-PACK red-team (frozen @ faed362) found the Principal's audited +182% pack sits **below the stock-shuffle placebo mean** — demoted to "disciplined beta," and the doctrine banked that "prior internal audit verified *accounting*, not *alpha*." CA family: selection REAL (+4–6% over placebo across three versions) but drawdown never armored — the CA-COLLAR card **proved** static index collars make DD worse (−50.1%→−52.4%, 2020 collar −12.2% *despite* the March put paying +17.4%). DECEL-TRAP F&O put spec was **struck from the queue with no trial spent** because its existence card had not confirmed — "building an options vehicle on a failed existence test = laundering." P1-R returned **NOT-ADJUDICABLE** and surfaced a brand-new data landmine (PIT `available_date` coverage ≈ zero pre-2020, so every "validate 2016-2024" fundamentals window was really 2022-2024).

---

## 3.3 Code-level enforcement — `04_RND_LAB/lib/`

Four modules turn the doctrine into machine checks. They are cheap, importable, and mandatory.

| Module | Stage | What it enforces |
|---|---|---|
| **`ast_lookahead_scan.py`** | Pre-flight (static, before the script runs) | Parses the backtest script's AST and flags: `shift(-n)` (future value into present row), `rolling/ewm(center=True)`, `bfill`/`fillna(method='bfill')`, whole-object `.mean()/.std()/.quantile()` etc. on a bare name (full-sample normalization leak), `train_test_split` without `shuffle=False` (temporal leakage), and `[x+y]` forward index arithmetic. Exit 0 = clean; findings must be justified in the run card. Adopted from the Vibe-Trading "purity gate" concept, 2026-07-11. |
| **`lookahead_audit.py`** | Gate-4 (runtime, D-028) | Programmatic battery over the T1–T10 taxonomy on the *data and trade log*: `audit_pit_column()` (decision before `available_date` = hard FAIL), `audit_tz()` (detects the 18:30-UTC daily-bar signature), `audit_same_bar()`, `audit_session()`, `audit_code()` regex greps, plus the **one-day-lag test** harness (`one_day_lag_test(callable)`) — a real edge degrades gracefully when features are lagged one extra day; a leak collapses (>50% collapse = investigate). Owner: Dr. Sameer Bhat. |
| **`guards.py`** | Every backtest entry point (import mandatory) | The landmine guards, each born from a real incident: **L1** `fix_ist_dates()` (HF tz bug; refuses tz-naive stamps), **L2** `drop_preopen()` (≥09:15; auction prints corrupted ~94% of 2026 gap calcs), **L3** `assert_pit()` (no action before `available_date`), **L4** `safe_merge()` (row-explosion detector), **L5** `assert_next_bar()` (the "same-bar sin"), **L6** dual-schema option helpers (`option_schema()`, `clean_daily_options()` dropping 0.00-price untraded strikes, `assert_intraday_capable()`), **L7** `assert_no_future_settlement()` (S-04's 84 fabricated wins from `spot.asof(future_date)`), **L7b** `assert_physical_bounds()` (a short strangle cannot earn more than its premium — 380 rows once violated physics yet passed a generic 60% threshold). Plus **`degenerate_flags()`** post-run: Sharpe>4, CAGR>60% with DD>−10%, equity-curve R²>0.98 (too smooth), tail-seller profile (win>75%, W/L<0.5 → check crash slices), one symbol >30% of |P&L|, negative-without-top-5-trades. |
| **`execution_realism.py`** | Every equity fill (Principal order 2026-07-04, landmine #7b) | `circuit_locked()` heuristic (zero-range single-print days; band-pinned closes at ±5/10/20%), `slippage_multiplier()` (volume ratio ≥0.5 → 1×; 0.2–0.5 → 2×; <0.2 → 3×; zero/NaN volume → **infinite = NO FILL**), composed in `fill_check()` → (fillable, effective_bps, reason). Rationale documented in the module: momentum entries cluster with upper circuits and stops with lower circuits — fixed-bps slippage fabricates impossible fills exactly on signal days. |

---

## 3.4 The lookahead taxonomy — `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` (D-028, BINDING)

Issued 2026-07-04 by Principal order ("ensure no lookahead bias"). Owner: Sameer Bhat; live/paper parity monitor: Ritika Sharma; attack surface: Nikhil Bose. **Gate-4 cannot pass without a LOOKAHEAD AUDIT PASS.** The framing: "unlike overfitting, ONE leaked column can create an arbitrarily large fake return."

| # | Class | The trap | Firm precedent / programmatic check |
|---|---|---|---|
| T1 | Data-availability (PIT) | Using data on its event date, not publication date | Landmine #3; `available_date` mandatory; `audit_pit_column()` |
| T2 | Timestamp/timezone | 18:30 UTC bar = next-day 00:00 IST | Landmine #1; guards L1; `audit_tz()` |
| T3 | Same-bar execution | Signal on bar t's close, fill at bar t | guards L5; next-day-open rule; `audit_same_bar()` |
| T4 | Intraday session boundary | 09:00 pre-open auction print as "open" | Landmine #2; guards L2; `audit_session()` |
| T5 | Survivorship / universe | Screening today's members historically | 42 PIT snapshots mandatory; `audit_universe_pit()` |
| T6 | Normalization leakage | Z-scores/scalers fit on the full sample | Trailing/train-window fit only; `audit_full_sample_stats()` |
| T7 | Label/target leakage | Feature window overlaps label; wrong-date joins | `audit_feature_label_overlap()`; merges reviewed line-by-line |
| T8 | Settlement / lifecycle | Marking open options with FUTURE settles; corp actions pre-ex-date | S-04's 84 fake wins; guards L7/L7b |
| T9 | Walk-forward contamination | OOS opened more than once; thresholds picked after seeing forward | OOS opened exactly ONCE; trials ledger; Sameer verifies run log |
| T10 | Backfilled/revised source | Vendor silently restates history (HF re-uploads, Angel purges) | DATA_CATALOG snapshot dates; results dirs record row-counts+max-dates |

**The audit gate:** (1) run the programmatic battery; (2) walk T1–T10 manually against the CODE ("the machine catches patterns; the human catches intent"); (3) two killer diagnostics — **terminal-date shuffle** (true PIT replay, delete all data after each decision date, ≥20 dates) and the **one-day-lag test**; (4) verdict PASS / PASS-WITH-FLAGS / FAIL filed as `results/<strategy>/<run>/LOOKAHEAD_AUDIT.md`, signed. FAIL = the result is **quarantined** — not quotable in any register, memo, or letter. (5) Weekly live/paper parity check: the paper signal stream must be reproducible from data that existed at signal time.

**Standing code rules:** every feature column carries an as-of comment; `.shift(-n)` forbidden without a `# LABEL:` tag; no full-axis `mean()/std()/rank()` in feature code; date merges via `merge_asof(direction='backward')` or explicit lag; backtests never read files newer than the declared data snapshot.

**The T-log** (the firm's own incidents, kept as institutional shame/memory): the FF-calendar v2 argmax-FF entry (a v1→v2 *rewrite injected* a T9 leak that survived the original kill AND the recheck, caught by Nikhil during the K-012 resurrection review — lesson: diff successive engine versions); S-04 future-expiry settlements (+1.75% fake edge); the HF timezone bug; the pre-open auction bug; earnings joined on quarter-end dates; Angel's contract purges.

---

## 3.5 The placebo & control battery — how a number earns belief

The firm's controls evolved from "beat an index" to a layered battery, each layer added after a specific fraud mode was caught in-house:

| Control | What it kills | Origin incident |
|---|---|---|
| **Same-exit placebo ×200** (random entries, SAME exit engine) | Trail/cap exits harvest drift and flatter ANY entry signal | T-E PEAD: raw +3.48% failed placebo95 +4.70% — the DMA50 trail alone earns +2.14% on random events. Institutionalized in every card since. "The placebo-with-same-exits test is the ONLY reliable arbiter in drifting markets" (AF-07 kill). |
| **Stock-shuffle** (same entry dates, random same-universe stock, same exits) | "Selection" that is really calendar/regime timing | Breakout-pack red-team: the pack's picks sit BELOW the shuffle mean — negative selection. |
| **Date-shuffle** (same spacing, random dates) | Calendar/regime luck in the entry timing | AF-07 kill (date-shuffle placebo +4.05% vs real −0.28%). |
| **Label-permutation** (shuffle event labels within strata ×500) | Spurious event-class spreads | FT-1 filing-time card (night/Friday/late-filer spreads all inside perm95 → family terminally closed). |
| **Lag-decay** (enter +1/+2/+5 days late) | Two frauds at once: a *leak* collapses >50%; *drift-in-costume* shows NO decay (being late loses nothing = zero timing information) | INV-1: entering 5 days late earned MORE → "the signal is index drift." Promoted to the standard battery 2026-07-12. Beta signature confirmed in MidSmall red-team (83–102% retained). |
| **Plateau rule** (≥2 pre-registered cells must pass; neighbors must agree) | Single-cell luck | GOLD-TREND 1/4, VBT 1/4 — both NOT ADOPTED despite one passing cell; S1's 84-cell surface (72/84 positive) is the positive example. |
| **Calendar-specificity** (pseudo-anchor test) | Generic drift dressed as a calendar effect | TOM-VIX: mid-month pseudo-ToM must show <0.5× the real effect — it did (clean), but the effect itself was dead post-2024 (post-publication decay, KB 22/24). |
| **Turnover-matched comparator** | "Beating" a full-churn hurdle by cost savings alone | KB lesson 20 (I-016): a strategy passed DSR 0.9995, PBO 19.8%, plateau, 0-FAIL lookahead — and still had no selection edge; the hurdle paid 3× the costs. SOP amended. |
| **Random-basket null (D-029)** | Index benchmarks flattering cost-loaded stock selection | The honest null = the DISTRIBUTION of 10,000 cost-loaded random baskets, same segment, same position count; percentile bands are the information (60th pct = luck, 95th+ = selection). Standing series in `datasets/derived/benchmarks_random/`. |
| **Era split + embargoed holdout** | Regime-loaded results | Validate/screen windows pre-declared per card; INDEX program constitution: "2026-H2+ = embargoed holdout — no in-sample touch, ever." |
| **2×-cost stress + dual cost models** | Under-costed edges (the most common error per KB 24) | Verdict must survive both flat-point and %-of-premium cost models; K-012's exploratory +0.99 "dies at 2x" and was fenced out of the verdict. |
| **Denominator-free restatement** | Denominator disease (three strikes: FF net-debit, S-02, S-03) | HARD RULE (KB 8): any per-trade return must ALSO be reported in rupee points and % of spot; an edge that changes sign between denominators is an artifact. |
| **Fill-rate / exitability audit** | Placebo-real but untradeable signals | K-012: 61% of forward signals fired into zero-volume back-leg markets; sequence law: fillability → sizing → sensitivity ("a sizing cap of any width cannot fix a zero"). CIO added an exitability tail-veto: 61% dead markets = un-exitable inventory. |
| **Degenerate detectors** | Too-good-to-be-true shapes | `guards.degenerate_flags()` — Sharpe>4, smooth equity R²>0.98, tail-seller profile, single-symbol concentration. |

---

## 3.6 Trials ledger & DSR discipline — `04_RND_LAB/INDEX_PROGRAM_2026/`

**The problem:** after hundreds of tests on the same 2021-26 sample, in-sample statistics stop meaning anything. The firm's answer has three parts.

1. **TRIALS_LEDGER.csv** (`build_trials_ledger.py`): one consolidated denominator of every test ever aimed at the data. Auto-rows harvested from every `results/**/RUN_CARD.json` (card, trials_increment, verdict) + a curated historical block for pre-run-card campaigns (e.g., "S1 sensitivity surface, 84 trials"; "sell-side battery, 45"; "misc 07-07 campaigns, 30"). Every card since 2026-07-11 declares its trials increment in the frozen spec ("Trials +2", "+19"...), and the STOCKS book shows a live countdown (Trials 255 → 252 → 249 → 246 → 242 → 238 → 235 as of 07-13). The trials registry was upgraded to a **PREREQUISITE** — "DSR at graduation gates is uncomputable without N/variance/T/skew/kurt of ALL trials" — blocking for any Gate-4 pass.

2. **DSR_BASELINE.md** (Bailey & López de Prado deflated Sharpe): for S1-F (T=259 daily, SR≈0.243/expiry ≈1.75 annualized), DSR is computed under a *declared grid* of assumptions rather than one flattering number: N ∈ {50, 157, 229} × V[SR] ∈ {tight, wide} → DSR from 0.30 down to 0.00. The interpretation is unusually honest: strict independence overstates deflation (the 84-cell surface is ~5–10 effective trials, not 84; effective-N plausibly 20–40; Bonferroni cross-check p≈0.016), so the verdict is **AMBER, not red** — and the binding conclusion: "In-sample statistics CANNOT settle this after this much search... The forward test is the only exit from this ambiguity."

3. **The sample-is-spent doctrine:** every additional sell-side variant tested on the same 2021-26 sample deflates S1-F further → new research must target NEW data (forward paper, the 2011-21 bhavcopy backfill era, different data families). This is why B1c-DII-flow was killed at t=2.43 vs a 2.5 bar with a resurrection condition of **FORWARD DATA ONLY** (zero-size shadow ledger, re-decide after 60 forward signals, "NO in-sample re-tests, NO threshold changes").

**The IDEA_FACTORY funnel** (`04_RND_LAB/IDEA_FACTORY/PROTOCOL.md`) is the multiple-testing control for high throughput: intake 100+/wave → Stage-1 screen on a fixed recent window (2024-07..2026-06; gate: net expectancy >2× cost, t≥1.5, n≥30) → Stage-2 validation on the **untouched** full history (2013/15..2024-06) with placebo-shares-exit + era split → Stage-3 = the deep-card machinery. Every screened idea is logged so the denominator is complete; killed families are blocked at intake. Results: Wave-1 116 ideas → 6 validated → **0 promoted** ("the untouched-window design caught what would have been 6 fake discoveries"); Wave-2 315 → 2 → 0; running total **442 ideas, 0 certified from price primitives** — which is itself the input to the alpha thesis (§3.9). The INDEX program's Validation Constitution (§5 of its MASTER_PLAN) binds all of this per stream: pre-registration with frozen kill bars, trials ledger + DSR at every IC, era splits, embargoed 2026-H2+ holdout, dual cost models, next-bar fills invariant, one-day-lag test, paper forward test as final arbiter (D-030), red-team before Gate-5.

---

## 3.7 Red-team certification — `07_RISK_OFFICE/ADVERSARIAL_REVIEWS/`

Nikhil Bose (Devil's Advocate) must review before any strategy passes the audit gate. Two filed reviews illustrate the two modes:

### MIDSMALL_VARB_REDTEAM_20260713.md — the anatomy of a modern red-team
Target: the MidSmall momentum rotation sleeve already in the 50L stacked paper book (banked CAGR 22.8%, Sharpe 1.14). Nikhil's method is instructive:
- **Harness integrity first:** his rig feeds randomized scores into the FROZEN engine and reproduces the banked result *exactly* (CAGR 0.2277, Sharpe 1.142) before any perturbation — so every attack runs through the real cost/fill/regime machinery, and D-030 is respected.
- **One focused attack:** the author had self-labelled the sleeve "regime-timing, not selection" — *asserted, never proven with a statistic*. Nikhil proved it: invested-days regression vs MSS400 → beta 1.13, **alpha +0.9%, t=0.16** (the headline +12.4% full-sample alpha is a mechanical artifact of sitting in cash ~31% of the time).
- **Placebo with a self-check:** the D-029 random-selection placebo (N=200) showed gross selection IS real (100th pctile, +12.5pp — the momentum factor premium) but the enormous NET gap is a **turnover artifact** (random churns 42–44×/yr vs momentum's 22×) — Nikhil explicitly "did not let my own kill-test overstate."
- **Correlation-horizon attack:** daily max pairwise corr 0.08 → quarterly **0.53 vs b1b** — the book's "uncorrelated sleeves" claim is a daily-sampling illusion at exactly the horizon where drawdowns live (now KB lesson 25a).
- **Verdict: SURVIVES-AS-BETA** with hard conditions: relabel in the register as risk-managed midcap-momentum *beta*; no independent-alpha credit in the 30/10 frontier math; size on quarterly correlation; expect ~13-14% net, not 22.8%. Plus explicit both-direction triggers: → genuine alpha if invested-days alpha vs a passive midcap-momentum index shows t>2; → KILL if the book keeps presenting it as uncorrelated alpha.

### LEAK_AUDIT_20260711.md — self-red-team of the firm's own process
Triggered by the Principal's challenge ("there will definitely be some loopholes and leaks"). Material findings: (1) **pre-registration was not cryptographically provable** (card + results in one commit) → the standing freeze-commit-alone rule was born here; (2) A4's missing 2011-15 spot data and the SETTLE_PR-not-CLOSE rule flagged into the card before it ran. Also six empirically-checked cleans (stale prints 0/4,245 obs; settlement STT sub-noise; C1 timezone alignment), six documented-not-fixed caveats (USDT≠USD, adj_close vs close for price-level rules, participant-OI T+1 rule), and the honest admission that ~155+ trials on one sample "cannot be closed in-sample — the forward test is the live guard."

**Related certification outcomes:** B1b (FII-minus-Client spread flow) SURVIVED its red-team (shuffle-null 100th pctile, extra-lag flips negative = timely-information signature, 18/18 sensitivity cells positive) — one of only two certified alpha sleeves. AF-07 was killed by its own certification. The BOOK RESTATEMENT of 2026-07-12 is the honest ledger: **certified alpha sleeves = 2 (S1-F, B1b)**; Var-B = regime-timing beta; breakout pack = disciplined beta; "the 30/10 sleeve-count math RESTARTS from 2 certified + 3 shadows (P6, B1c, S1-SX)."

---

## 3.8 The graveyard — `04_RND_LAB/KILLED_IDEAS.md` (D-012, append-only)

Every kill records what/when/WHY (evidence) and the SPECIFIC condition that would reopen it. Current census: **K-001..K-015 plus six named family kills**, ~22 families, spanning intraday option buying (~14 variants), reverse/double calendars, far-OTM longs, 0DTE condors, gap-fades, FF-calendar stops/wings/blacklists, gold-as-crash-hedge, the FF calendar itself, LowVol50 (killed AND resurrected same day when the inflated bar was corrected), semiannual MQ50, regime-switch baskets, air-pocket overlays, standalone stock mean-reversion, post-breakout ORB, AF-07, DII flow, and the 8-construction ADX/ATR family.

Doctrinal features visible in the file:

- **Kills are surgical, not tribal.** K-013 shows the process running in reverse: the kill bar itself was found defective (a chained "p75 path" no random basket ever walked — an always-lucky fiction), Devika honored the pre-registered kill anyway, the BAR was fixed, and the idea was resurrected the same day under the corrected bar. "The process stays trustworthy."
- **Signal-vs-vehicle separation.** Repeatedly a kill states the signal is real but the vehicle dead: K-012 (FF signal at the 100th placebo percentile; calendar vehicle un-fillable), K-stock-meanrev (+0.28% relative timing edge, standalone dead on friction), the ORB family (real +8–13 bps gross, dead vs 35–50 bps friction).
- **The K-012 resurrection review** is the flagship anti-sycophancy artifact: a Principal-triggered "were we too hard on them?" review ran four independent evidence legs (Sameer sensitivity plateau; Nikhil placebo battery — which caught a NEW T9 leak in the firm's own supporting evidence mid-rescue; Tara fill audit — 61% dead markets; Arjun's pre-registered final gate — fwd −0.03/₹100) and returned **STAYS-KILLED-WITH-NEW-INTAKE**. Paper signal-tracking was rejected as scope creep; the FF signal graduated to a genuinely new Structurer intake with 5 pre-registered kills — explicitly "NOT a resurrection of K-012." Honesty-probe conclusion (KB 18): "a review triggered by the boss is not a mandate to manufacture a survivor... Kill credibility is the firm's most valuable asset."
- **Resurrection conditions are constrained to prevent fishing:** typically NEW data only (forward shadows, backfilled eras, different assets), never threshold re-tuning on the same sample ("t=−5 to −7 is not a tuning problem"; "NO re-tuning of trigger thresholds/OI deciles on this dataset").

---

## 3.9 The knowledge base — all firm-earned lessons (`04_RND_LAB/KNOWLEDGE_BASE.md` §A)

"Paid for with real mistakes — never re-learn." The file's numbering has duplicates (two 9s, two 14/15/16/17s from parallel appends); the table below lists every lesson in file order.

| # | Lesson (compressed) | Origin |
|---|---|---|
| 1 | VRP is the meta-edge in Indian options: selling wins, buying loses; every buying family died | K-001, K-004 |
| 2 | The measurement-artifact trophy wall: net-debit denominators, P&L spread across holding days (Sharpe 7–10, Kelly 300), monthly-compounded "+246%/+681%" CAGRs, near-expiry return-on-premium explosions, partial-year "positive every year". Antidotes: exit-period booking, stable denominators, per-trade edge headline, coverage checks | Red Team |
| 3 | Lookahead in stock selection: filters built from realized outcomes are untradeable; live filters must be ex-ante | 16-landmines incident |
| 4 | Tails are unforecastable at trade level, survivable at portfolio level: small size × many idiosyncratic positions, inverse-IV sizing, staggered entries, event gates — stops and bought wings all FAILED | FF tail work |
| 5 | Cap-tier gating is strategy-specific: premium harvesting improves on mid-caps; calendars/binary-event strategies are large-cap only | sleeve studies |
| 6 | Event gates are the cheapest tail insurance (IT earnings −31..−47% through a short straddle) | earnings sleeve |
| 7 | Data coverage is alpha: 88→210 F&O names doubled every sample | bhavcopy backfill |
| 8 | DENOMINATOR DISEASE — hard rule after three strikes: every per-trade return also in rupee points and % of spot; sign-flip between denominators = artifact | FF v1, S-02, S-03 |
| 9a | Pre-IC incremental-shuffle kills fictions cheaply (re-priced S-01 +37.6→+11.4; killed S-02 pre-IC); `c4_short_thru` column contaminated | Gate-5 SOP |
| 9b | Never settle beyond max(available data): `spot.asof(future_expiry)` fabricates wins; physical bounds beat generic thresholds | S-04 → guards L7/L7b |
| 10a | Angel purges expired contracts — capture before expiry or lose data forever | ops incident |
| 10b | Multibagger heat rule: median winner endures 23% intra-year DD; exits must be two-stage (tight initial, then 25–35% trail) | MULTIBAGGER_STUDY, 549 winner-years |
| 11 | Track-2 missing overlays: sector-momentum tilt + quality gate separate compounders from junk rallies | MULTIBAGGER_DNA |
| 12 | Depth beats adjustment as the silent backtest killer: pre-2018 error was missing history (survivorship hole), not bad prices; coverage % now in every data snapshot | 2026-07-04 forensics |
| 13 | Survivorship inflates the NULL too: shuffle gates only honest on the survivorship-complete panel (bias ≈1/3 of measured CAGR, concentrated in one year) | BT-11 union re-run |
| 14a | Fill-rate audit BEFORE sizing/sensitivity: a placebo-real signal can be untradeable (61% dead markets); "a sizing cap of any width cannot fix a zero" | S-03/K-012 |
| 14b | Circuit/volume-conditional fills mandatory: fixed-bps slippage lies exactly where momentum trades | Principal rule → execution_realism |
| 15a | Ex-ante liquidity gates can ADMIT weaker trades — always pre-register gate-vs-drop (dropping +3.88 beat gating +0.99) | K-012 |
| 15b | Random-basket benchmark law (D-029): the honest null is cost-loaded random baskets, percentile bands are the information | benchmark suite |
| 16a | v1→v2 rewrites can INJECT lookahead — diff legacy engines as an audit surface | FF v2 argmax leak |
| 16b | Rebalance cadence IS part of the edge: monthly factor rebalancing = 330–450% turnover = 3.5–10.7pp/yr drag; smallcap "quality" from free data is fiction | D-029 factor family |
| 17a | Entry-fill convention (same-day-close vs D+1) swings ~1pp/₹100 — freeze it in the spec; same-day is the optimistic bound, never the verdict bound | K-012 |
| 17b | Costs invert the size premium: net-of-cost LARGE beats SMALL; MID was the 2005-25 sweet spot; "if p95 looks absurd, check prices first" | D-029 suite |
| 18 | Honesty-probe #1: the kill→challenge→validation loop self-corrected in both directions under soft boss pressure; anti-sycophancy law codified | K-012 review |
| 18b | Percentile-path construction decides kills: skill bars must be percentiles of TERMINAL path outcomes, not chained always-lucky paths | I-016/K-013 |
| 19 | Overlay vs parent controls (K-015): any regime/timing overlay must beat BOTH static parents; corollary discoveries from controls are post-hoc | K-015, I-017 |
| 20 | Turnover-matched comparator: a strategy can pass every statistical gate and still have no selection edge; "gates test the NUMBER; the red team tests the INTERPRETATION" | Nikhil, I-016 |
| 21 | Evaluation is a standing capability: EVALUATION_FRAMEWORK.md (6 modules, 0-100 rubric, hard-fail overrides); route through QFRA 2.0, don't rebuild | Librarian |
| 22 | Post-publication decay = ~50% denominator mis-measurement + ~50% real crowding; separate via tighter forward costs + forward-vs-backtest Sharpe ratio + capacity tracking | LITSCAN 2026-07-07 |
| 23 | Regime filtering on derivatives mean-reversion is survival insurance, not tuning — existential for short-option positions | LITSCAN |
| 24 | Pre-register short-vol forward expectation at 50% of backtest gross; Sharpe>2 claims usually mean under-costed slippage; realistic index VRP = 15–25% XIRR | McLean-Pontiff prior |
| 25a | Sleeve correlation must be measured at the horizon where drawdowns live: daily corr on asynchronous sleeves is an artifact (0.00 daily → +0.36..0.54 monthly); sub-book-Sharpe sleeves cannot improve the frontier at DD parity | CA-BOOK 2026-07-13 |
| 25b | Static index collars cannot armor a stock-selection book: V-recovery whipsaw refunds the crash payout with interest; hedge-basis mismatch (idiosyncratic DD while NIFTY flat). Armor with position-level exits/regime gates or factor hedges | CA-COLLAR 2026-07-13 |

---

## 3.10 The alpha thesis — `04_RND_LAB/ALPHA_FORGE/THESIS.md` (2026-07-12 synthesis)

The distillation of 442 kills and 5 survivors into a positive theory of where the firm's edge can exist:

**The evidence, compressed.** DEAD: *every* price-pattern construction from public knowledge — breakouts (20/55/100/252d), reversion (RSI/z/N-down across stocks/gold/index), seasonality, gap plays, vol-expansion, exhaustion, intraday ORB in every costume — 442 samples, 3 asset classes, two-window tested, not one certified. ALIVE: S1-F (+10.7 pts/day, t=3.9), B1b (+18.5 bps/trade, survived a 3-placebo red-team), and (at the time) AF-07, TF-1's selection layer, the breakout pack — the last three since demoted/killed by the same machinery, which sharpens rather than weakens the thesis.

**Three survival mechanisms — "no exceptions found":**
1. **Structural premium + convexity modifier.** S1-F earns a risk premium that *must* exist (sellers insure buyers) and manufactures its own tail-safety (the 30% SL turned −1.5 into +10.7 pts/day). The edge is not prediction; it is being PAID for a service while capping the service's worst case.
2. **Information asymmetry from proprietary data.** B1b reads participant-positioning flows most retail cannot compute; PIT earnings dates enable event tests others cannot run honestly. The edge is cleaner information, not smarter patterns.
3. **Phase-transition timing.** Buying the *birth* of a trend (stage-1→2 turns, confirmed regime changes with quality gates). Steady-state patterns are arbitraged flat; transitions are structurally hard to arbitrage — rare, heterogeneous, and requiring holding through ambiguity.

**The friction theorem (corollary):** at retail cost an edge must be ≥2× friction per round trip. Patterns visible in any charting app cannot sustain that ("they are sold to retail as courses precisely because they no longer work"); mechanisms 1–3 can, because their scarcity is structural, informational, or psychological — not visual.

**The directed campaign this implies** replaced undirected idea waves with posterior-weighted veins: V1 flow lattice (144 pre-registered cells over participant-OI, BH-FDR(10%) within family + untouched-window confirmation — "the grid IS the hypothesis"), V2 AF-07 certification (which killed it), V3 earnings interaction lattice, V4 option-structure overlays. The V1 execution result is a model of honest lattice work: 4 BH-FDR discovery passes, 0 formally confirmed, but one cell (DII futures-net 5d-flow) replicated sign-and-magnitude across both windows and missed the BH cut by one rank → queued as a single pre-registered confirmation card (B1c) rather than quietly promoted — and then killed at t=2.43 vs the 2.5 bar, with a forward-data-only resurrection condition. Family lesson locked: flow-transforms of FUTURES positioning are the only cell-type with cross-window stability; option-positioning LEVELS are a dead vein (regime artifacts).

---

## 3.11 What makes this a moat

1. **Pre-commitment is cryptographic, not rhetorical** — frozen cards committed alone before runs, hashes in results files, single-shot bars honored even against the Principal's stated targets (EQ-MAX) and his own pet ideas (T-C, P6, DECEL-TRAP).
2. **The controls were each paid for** — every battery element maps to a named in-house incident, and the incidents are preserved (T-log, trophy wall, graveyard) so the tuition is never re-paid.
3. **Anti-sycophancy is tested, not assumed** — honesty probes, boss-triggered reviews returning pre-registered FAILs, a red team that kills its own discoveries and denies bar-shopping resurrections with written rulings.
4. **The denominator of search is public inside the firm** — trials ledger, DSR grids, and the standing admission that the in-sample well is nearly dry, forcing research toward new data.
5. **Negative knowledge compounds** — 442 screened ideas and ~22 killed families constitute a map of where alpha *is not*, which is precisely what funds the alpha thesis of where it *is*.

---

---

# SECTION 4 — DATA ESTATE & QUALITY REGIME

**Owner:** Kavya Reddy, Data Officer (05_DATA_OFFICE). **Governing rule:** *"If it's not in the DATA_CATALOG with path + range + bugs, it doesn't exist for research."* Every dataset the firm uses must have a catalog row, a verification status, and its known defects written next to it. This section inventories the full estate as of 2026-07-13, explains the verification gates that keep it honest, lists the standing capture jobs, and names every known hole with its fix plan.

**Key files:**
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md` — the single source of truth inventory
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_QUALITY_RULES.md` — landmines + new-source protocol
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/REMOTE_SOURCES.md` — fetch-on-demand registry + acquisition plans
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/SCOUT_PRE2020_PIT_20260713.md` — pre-2020 PIT earnings scout report
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/` — 27 puller/utility scripts (all resume-safe by design)
- `04_RND_LAB/lib/guards.py` — code-level guards that enforce the landmine rules inside backtests

---

## 4.1 Why the data office exists

The firm's entire research pipeline (idea → cheap test → backtest → forward test → paper) is only as honest as the data underneath it. The firm has been bitten repeatedly by data defects that produced *fake* backtest results — a 17-month option-data gap hiding behind healthy max-dates, a timezone bug that shifted every daily bar by one day, an expiry-day settlement field that silently recorded the *underlying's* level instead of the option price (−15,428 points of fake losses in one study). The response was institutional: a Data Officer role, a catalog-or-it-doesn't-exist rule, a mandatory verification gate for every new source (D-009), and a growing list of "landmines" that guard code (`guards.py`) enforces mechanically.

---

## 4.2 The India estate (core franchise data)

### 4.2.1 Equity prices — 26 years daily, 4+ years minute

| Dataset | Path | Granularity | Coverage | Status / notes |
|---|---|---|---|---|
| **PIT union panel v1.1 (CANONICAL)** | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}_v11.parquet` | daily | 2005→2026; price basis 2,522 symbols, return basis 2,566 | THE equity close panels. Survivorship-complete: achievable NIFTY500 coverage 97–100% at every March snapshot 2014–2025 (2016/2024/2025 = 100.0%). Only 3 named residual gaps (SREINFRA — real NCLT discontinuity, quarantined; IISL — not a tradeable equity; UNKNOWN — data-entry artifact). v1 files frozen and md5-stable so audited runs stay reproducible; `_v11` is opt-in for all new work |
| pit_union_panel v1 (superseded) | same dir, `close_panel_{price,return}.parquet` | daily | 2005→2026; 2,511 / 2,556 symbols | Ground-truth-based (94.8% exact match vs official bhavcopy); 9 corrupt segments quarantined; use only to reproduce already-audited runs |
| **NSE bhavcopy daily (PERMANENT ground truth)** | `datasets/nse_bhavcopy_daily/close_all.parquet` | daily | 2013-01-01→2026-07-03; 5,569,110 rows, 3,716 symbols | Every NSE-listed stock's *official* close. Used as ground truth for splices and IPO dates (caught 14 bad membership-xlsx rows). Rule: any future "is symbol X in our data?" question ends here |
| Stock daily (HuggingFace) | `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` | daily | → 2026-01-22 (**stale tail**) | Timezone landmine #1 applies; `asof()` after Jan-2026 returns stale prices; completeness degrades pre-2018 (see §4.6) |
| Stock 1-minute (HuggingFace) | `swing_momentum/data/hf_stock_minute/` | 1-min | 813M bars, 2022–2026 | Pre-open auction landmine #2 applies |
| Angel daily 2026 bulk | per RESUME_TOMORROW | daily | 477/500 names Feb–Jul-2026; 23 stragglers pending | Retry list held in RESUME_TOMORROW |
| Master wide matrix | `Nifty500_Master_Dataset_2005_2025.xlsx` (root, 33.7MB) | daily close-only | 5,363 days × ~1,200 tickers incl delisted | **RETURN basis** (dividend-adjusted) — never compare its levels to exchange prints |
| Delisted names | `Nifty500_Delisted_2005_2025.xlsx` (root) | daily | 239 names with histories | Feeds delisting-loss realization (V1→V2 of a momentum strategy halved CAGR once delisting losses were realized — a real lesson) |
| Raw delisted CSVs | `raw/nifty500/` | daily | 239 per-stock files, sampled windows | Union-panel input (count corrected 2026-07-04 from an earlier wrong figure of 1,905) |
| Legacy processed panel | `swing_momentum/processed/eq_close.parquet` + `membership.parquet` | daily | survivorship-safe panel behind MULTIBAGGER_STUDY | Read-only legacy; prime union-panel input |
| yfinance cache (Principal-contributed) | `stocks_data_cache.pkl` (root) | daily | 435 tickers 2020-06→2026-01, ADJUSTED, + shares outstanding + TTM fundamentals (378) + sectors | D-009 adjustment-verified on EICHERMOT/IRCTC ex-dates; source of TRUE market-cap weights for modern-era replication; useless pre-2018 |

**Universe membership (survivorship control):** `NIFTY500_TICKER_2005_2025_Final.xlsx` — 42 point-in-time snapshots 2005–2025 — is the ONLY permitted membership source (landmine #6). Supporting membership files: `NIFTY200_TICKER_2005_2025.xlsx` (monthly N200, 8,490 rows) and `Historical stock composition of Nifty 50 and Nifty Next 50.xlsx` (monthly, 2008→). Important as-of rule: N200/N500 PIT snapshots are **March/September**, not Jun/Dec.

### 4.2.2 Index & factor benchmarks

| Dataset | Path | Coverage | Verification |
|---|---|---|---|
| Official NSE all-indices (Angel-era) | `datasets/index_daily/nse_official_all_indices.parquet` | 246,597 rows, 174 indices, OHLC + P/E, P/B, div-yield, 2016-01→2026-07-03 | **D-009 triple-verified: 0.000% max diff vs factor_navs over all 1,365 overlap days.** Daily append via EOD task `ShreyasIonicAMC_IndexClose` |
| Factor NAVs (Principal-contributed) | `datasets/index_daily/factor_navs_principal.parquet` | 22 official NSE index NAV series daily 2005-04-01→2026-02-27 (5,189 days) — N200 Momentum 30 FULL, LowVol 30, Quality/Value/Alpha 30, N500 Mom 50/Value 50, etc. | D-009 verified 2026-07-04: LOWVOL30 2026-02-27 = 20495.0 exact match vs independent Angel series |
| NSE indices close (deep history) | `05_DATA_OFFICE/data/indices_close/indices_{yyyy}.parquet` | 3,535 days, 2011→today, all indices incl **India VIX OHLC** + P/E/P/B | Verified 2026-07-11: India VIX 2020-03-24 close 83.61 EXACT (record) |
| Sector/industry map | `datasets/derived/sector_industry_map.parquet` | ~976 symbols | **UNVERIFIED provenance** — Kavya to validate before any sector-tilt backtest quotes it |

### 4.2.3 Derivatives — 15 years of F&O daily + minute-level options

| Dataset | Path | Granularity | Coverage | Notes |
|---|---|---|---|---|
| Single-stock options, 210 F&O names | `intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/{SYM}/{expiry}.parquet` | **MIXED**: 1-min (HF) + daily (bhavcopy) | 2021-07→2026-06 **continuous** — the infamous Apr-2024→Aug-2025 gap was FILLED 2026-07-03; universe expanded 88→210 names (+122 new names 2024-07→2026-06 daily) | DUAL SCHEMA landmine (§4.5); untraded strikes carry 0.00 prices in daily files |
| NIFTY weekly options 1-min | same tree, index dirs | 1-min | 261 weekly expiries 2021→2026 | Accessor: `buying/chain.py` |
| NSE index-derivatives bhavcopy (15-year panel) | `05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet` | daily | **2011-01→today COMPLETE** — 16 yearly files, 744 old-format + 501 UDiFF days, 0 errors | Weekly-era caveat: monthlies trade ~16 strikes near ATM (160 listed) — fine for ATM studies, thin for wings/spreads. Expiry-day SETTLE_PR landmine (§4.5 #9) |
| BSE F&O bhavcopy (SENSEX/BANKEX) | `05_DATA_OFFICE/data/bse_fo_bhavcopy/bse_fo_{2023..2026}.parquet` | daily | 2023-05→today, 622 days; 2026 alone: 92,087 SENSEX option rows / 34 expiries | Consumed same-day by the SX1 study |
| **Participant-wise OI** | `05_DATA_OFFICE/data/participant_oi/participant_oi_{2018..2026}.parquet` | daily | 2018-01→today; 2,101 days ok / 124 missing (holidays + unpublished) | FII/DII/Pro/Client positioning by instrument. Schema drift across years stored as raw strings — normalization map is a Kavya follow-up (`participant_oi_normalized.parquet` exists) |
| NIFTY + BANKNIFTY OI surface | `datasets/derived/nifty_oi_surface.parquet` (377,034 rows) + BANKNIFTY (256,187) + daily summary (1,276) | snapshots | **SPARSE**: NIFTY 402 distinct dates over 2021-06→2026-05 (~31% coverage, 3–16 day gaps); BANKNIFTY stale after 2024-07-04 | PARTIALLY READY for GEX work — no spot/IV/greeks columns; needs spot join + cadence fix before Track-3 gate |
| Live Angel forward capture | `intraday_options_strategy/datasets/angel_capture_2026/{day,minute}/{SYM}/{expiry}.parquet` | 1-day full contract life + 1-min front rolling | Jul-2026 → ongoing | ±10% strikes, 2 expiries; fed by the purge-defense task (§4.4) |

### 4.2.4 Fundamentals, earnings & ownership (PIT discipline mandatory)

Point-in-time (PIT) means: a backtest may only "know" a number on the date it became publicly available, never on the fiscal-period date. This is enforced dataset-by-dataset:

| Dataset | Path | Coverage | PIT status |
|---|---|---|---|
| **PIT quarterly earnings (THE join key)** | `datasets/earnings_pit/unified_quarterly_pit.parquet` | 86.2% exact `available_date` overall (2025: 95.3%, 2026: 98%) | PIT-safe from ~2021+. **Coverage landmine (2026-07-13):** rows with `available_date` are ~zero pre-2020 (2019: only 133) — see §4.5 #3 |
| **NSE quarterly-results announcements (second-precision)** | `nse_quarterly_results_pit.parquet` (imported 2026-07-13, Route 3B) | 2019-01→2026-07; 76,507 rows, ~2,300 symbols | `broadCastDate` to the SECOND (e.g. RELIANCE Q2FY20 = 18-Oct-2019 20:50:42, spot-check exact) + filing/dissemination times + XBRL links. Unlocks filing-TIME anomaly work and after-hours vs intraday PEAD classification. Pre-2019 still absent |
| Earnings calendar (historical) | `datasets/nse_earnings_dates/earnings_dates.csv` | 2020-01→2026-07 | Filter purpose = "Financial Results" |
| Forthcoming results | `datasets/nse_earnings_dates/forthcoming_results.csv` | rolling; refreshed via `nse_earnings_refresh.py` | NSE API, needs cookie warm-up |
| Board meetings cache | `datasets/nse_earnings_dates/board_meetings_all.json` | 78MB, 94,136 events | Candidate 2010-2018 PIT feeder — earliest-date audit pending (scout Phase 2) |
| Screener deep fundamentals | `datasets/screener_deep/` | BS 5,022 / CF 3,000 / PL 6,000 rows | **NO `available_date` column — naive use = lookahead.** Kavya to rule a stamping method before ANY signal use |
| Screener.in dump (Principal-contributed) | `datasets/screener_dump_20260704/` (347 companies extracted from a 984-file zip) | annual fundamentals Mar-2013→TTM, **including delisted names** (RELCAPITAL, ORIENTBANK…) | D-009 PASS (3/3 live samples) BUT **restated as-of-2026-07-04 → FORBIDDEN for event/earnings-reaction work; quality overlays only, minimum T+90 lag** |
| Beat/miss (SUE proxy) | `datasets/derived/earnings_beat_miss.parquet` | 31,891 rows | Revision-sleeve proxy |
| Shareholding changes | `datasets/derived/shareholding_changes.parquet` | 21,713 QoQ/YoY rows | FII/DII/promoter flow sleeve |
| Corporate actions | `datasets/derived/corporate_action_factors` | 613 events + cumulative adjustment factors | — |
| XBRL cache | `raw/xbrl_cache/` | 581 regulatory XMLs (~2019-2023) | Raw format, needs a parser; PIT cross-check candidate |
| Financial metadata | `raw/financial_metadata/` | 244 per-stock JSONs (~197 records each) | Schema audit pending |
| MC fundamentals | `india_fundamentals_mc/Train.parquet` | — | `annual_report` column corrupt at source — never read it (landmine #5) |

### 4.2.5 Commodities (ETF route), text & derived research sets

- **GOLDBEES daily** — `datasets/etf_gold_silver/goldbees_daily.parquet`, 1,357 rows 2021-01-10→2026-07-02. D-009 PASS 7/7 checks; split pre-adjusted; PIT-safe; UTC stamps (+5:30 for IST); Angel token 14428.
- **SILVERBEES daily** — 1,091 rows 2022-02-06→2026-07-02; D-009 PASS; token 8080.
- **India financial news** — `datasets/india_fin_news`, 125K docs tier-segregated (FinBERT target).
- **Earnings-call transcripts** — MiMIC set, 1,042 calls, prepared-remarks vs Q&A split, joins on `available_date`.
- **Multibagger winners** — `swing_momentum/multibaggers/winners_yearwise_50pct.csv` (1,677 rows, all ≥50% winner-years 2007-2025) + top-40/yr; SIG-12 validation set.
- **Strategy outputs (regenerable)** — IV/RV trades (3,468), FF calendar candidates (2,612), earnings-vol events (1,359), strangle shortlist (5,039), monthly portfolio — all under `intraday_options_strategy/buying/` with the generating script named in the catalog.
- **Reference/config** — Angel scrip master (`scrip_master.json`, 31MB, 153K instruments, refreshed daily by the capture task); Angel ETF token list.

---

## 4.3 The US / global estate (D-033 acquisition waves, 2026-07-11 → 07-13)

Built in three rapid waves plus follow-ups after D-033 (2026-07-11) authorized auto-fetch of reliable sources. Everything lives under `05_DATA_OFFICE/data/` and every entry was D-009 spot-verified against known values.

| Dataset | File(s) | Span | Source | Headline verification |
|---|---|---|---|---|
| SPX daily | `us_sp500_daily.parquet` | 1975→2026-07, n=12,988 | cdn.cboe.com | 2020-03-23 = 2237.40 exact; 2024-12-31 = 5881.63 exact |
| CBOE vol suite | `cboe_{vix,vix9d,vix3m,vix6m,vvix,skew}_daily.parquet` | VIX 1990→, VVIX 2006→, SKEW 1990→, term 2008-11→ | cdn.cboe.com | VIX 2020-03-16 = 82.69 exact |
| Fama-French 5 factors daily | `ff5_daily.parquet` | 1963-07→2026-05, n=15,833 | Ken French / Dartmouth | schema + span sane |
| FF momentum daily | `ff_mom_daily.parquet` | 1926-11→2026-05, n=26,152 | Ken French / Dartmouth | schema + span sane |
| Gold (XAUUSD) 1-min | `commodities_1m/XAUUSD_1m_{2009..2025}.parquet` | 2009→2025-12, ~5.9M rows | HF mirror of HistData MT4 | 2020-08 high 2075 OK. Caveats: **no 2026 file** despite dataset name; timezone is HistData EST, NOT IST |
| BTC/ETH 1-min | `crypto_1m/{BTCUSDT,ETHUSDT}_{yyyy}.parquet` | 2018-01→2026-06, 291MB / 18 files | data.binance.vision official dumps | BTC 2021-04 high 64,854 OK |
| **US stocks daily bulk** | `us_stocks_daily/train-*.parquet` (4 shards, 530MB) | 1962-01→2026-07-08; 25.8M rows, 7,693 tickers, adj_close present | HF paperswithbacktest | **LANDMINE: SURVIVORSHIP-BIASED** — see §4.5 #10 |
| US Treasury par yield curve | `us_treasury_yields_daily.parquet` | 2000-01→2026-07, n=6,634, 15 tenors | home.treasury.gov official | 2020-08-04 10Y = 0.52 exact (record low) |
| USDINR daily (FRED DEXINUS) | `usdinr_fred_daily.parquet` | 1973-01→today, 13,409 rows | fred.stlouisfed.org | Monotone, 0 dupes; within 0.6% of RBI ref — noon-NY basis, do NOT mix with RBI-ref series in one calculation |
| **S&P500 PIT constituents** | `sp500_constituents_pit.parquet` | 1996-01-02→2026-06, 2,712 change-rows | github fja05680/sp500 | TSLA Dec-2020 add exact; count 505 exact; Enron present as ENRNQ. Caveat: final/normalized tickers — map before joining prices |
| US daily 2023-09 vintage | `us_vintage_2023_09/` (277MB) | 1979-12→2023-09-08, 8.4M rows | HF chuyin0321 (no signup) | Only 1,500 symbols (S&P1500-class); recovers just 19/471 missing dead S&P names — minor cross-check layer only |

**Rejected/blocked routes (do not re-probe):** fabhaus US equities 5-min (~450GB — violates Principal size cap AND its remote APIs are broken); Stooq (JS anti-bot + office-IP ban — PoW solver exists, home-network job); FRED direct via proxy (connection reset — fredgraph.csv worked for USDINR); Yahoo (429); iShares ajax (HTML shell); histdata.com direct (JS token).

### Fetch-on-demand doctrine (REMOTE_SOURCES.md)

Principal directive 2026-07-11: *"if only api or url works we need not download it… save reference so that we can backtest without downloading all datas of very very large size."* The registry keeps live-tested URL patterns so backtests pull only the slice they need:

- **Verified working patterns:** CBOE index histories; Binance klines for ANY of ~2,000 pairs at any interval down to 1-second (never bulk-mirror beyond BTC/ETH 1m); NSE F&O bhavcopy (old format ≤2024-06, UDiFF after — the corrected UDiFF URL is documented after the old one 404'd); NSE equity bhavcopy; NSE participant OI; US Treasury; Ken French; HuggingFace file-resolve with HTTP Range (pyarrow can read parquet row-groups remotely without full download) and rows-slice API; HF dataset search for weekly discovery.
- **Standard access preamble** is documented (truststore inject, Mozilla UA, NSE cookie warm-up, HF bearer token).
- **Tested-and-dead list** prevents wasted re-probing; re-test only on network change.
- **Principal one-time unlocks queued:** (a) Kaggle API key, (b) Tiingo free signup, (c) click "agree" on gated HF paperswithbacktest pages (silver/copper daily), (d) home-network/VPN session for NSE /api endpoints (FII/DII, constituents) and Stooq.

### US survivorship acquisition plan (registered 2026-07-13, 4-scout sweep, all live-probed)

**Recipe: WIKI (pre-2018 deaths) + Tiingo (2018-26 deaths) + current dump (survivors). Entirely free; needs 2 free API keys from the Principal.**

1. **Quandl WIKI PRICES** (frozen 2018-03): 3,000+ US stocks incl then-delisted, EOD + dividends + splits 1962-2018. Route: Kaggle mirror (463MB, confirmed reachable, needs Kaggle key) or data.nasdaq.com WIKIP datatables API (live, needs free key).
2. **Tiingo free tier:** ticker master verified via proxy (107,460 rows) — 7,170 delisted US names with full ranges (AET 1977-2018, YHOO 1996-2017…). Free caps (500 unique symbols/month) fit our 471 missing S&P ever-members in ONE month. Known gap: 2008 bankruptcy shells (LEH, WAMUQ) absent — verify crisis names on first pull.
3. **Vintage dumps** as cross-checks only (tail-gap caveat: a dump carries a dead name only up to the dump date).
4. **Stooq** home-network job (office IP banned; PoW solver already written at scratchpad `stooq_full_probe.py`).
5. **Membership correction layers:** fja05680 (held), shardul0701 YAML wrapper 2004-2026, riazarbi iShares reconstruction (cross-check only).

### Russell 2000/3000 constituents (registered 2026-07-13, NOT fetched)

No free PIT dataset exists. Route A: Wayback-Machine iShares IWV/IWM holdings reconstruction (~half-day build, approximation). Route B (armed): snapshot current holdings NOW and append monthly — starts the clock. Route C: Norgate ~USD 30-40/mo, which would solve BOTH Russell membership AND the US survivorship problem at once, if a US program ever justifies paying. Decision: Route B armed; Route A deferred until a US strategy card actually needs it (D-033 gates on need).

---

## 4.4 Governance: gates, approvals, and standing capture jobs

### The D-009 verification gate (no new source enters unverified)

Every new dataset passes a 5-step protocol before research may touch it (DATA_QUALITY_RULES.md §New-source protocol):

1. **Propose** — source, URL/API, licence, cost, which edge it feeds.
2. **Sample approval** — Principal approves fetching a sample.
3. **Sample audit** — 100 rows: schema/dtypes/nulls/dupes/date-monotonicity/PIT-safety; **cross-check 5 values against an independent source** (this is the step that catches wrong data — e.g. VIX 2020-03-16 = 82.69, India VIX 2020-03-24 = 83.61, RELIANCE broadcast timestamp to the second).
4. **Verdict** USE/QUARANTINE + a draft catalog entry → go-live approval.
5. **Bulk ingest** only after that, with the update command documented in the catalog.

### D-033 standing approval (2026-07-11) — the accelerant

Auto-fetch of **RELIABLE** external sources (exchange archives, Stooq/FRED-class, official APIs) is now permitted without per-source Principal sign-off, **conditional on**: (a) D-009 sample verification before use, (b) a DATA_CATALOG entry, (c) resume-safe background jobs for big pulls. Sketchy/unverifiable sources still need explicit Principal approval. D-033 is what enabled ~20 datasets to land in three days (waves 1-3 + follow-ups) without governance debt — every wave row carries its verification evidence.

### Standing capture & refresh jobs

| Job | Schedule | What it protects |
|---|---|---|
| **`AngelDailyOptionCapture`** (script: `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py`, kept outside the repo by design — credentials adjacency) | 15:45 / 20:00 / 23:00 IST daily, DESK-100 owns | **Angel purge defense:** Angel SmartAPI *deletes expired option contracts from its instrument master* — if a contract's data isn't captured before expiry, it is gone forever. Captures ±10% strikes, 2 expiries, day + minute bars into `angel_capture_2026/`; also refreshes the 31MB scrip master |
| `ShreyasIonicAMC_IndexClose` (EOD) | daily | Appends official NSE index closes to `nse_official_all_indices.parquet` |
| Freshness pings (99_OPS/EOD_ROUTINE.md) | daily | Critical sets pinged; stale > 2 sessions = flag in CURRENT_STATE. Rule: count PERIODS-PER-YEAR, not max(date) — the 17-month option gap hid behind a healthy max-date |
| `/factor-indices` skill (monthly, HOME NETWORK ONLY) | monthly | Official niftyindices.com factor closes (office proxy blocks this API) |

### The puller/utility scripts (`05_DATA_OFFICE/scripts/`, 27 files)

All acquisition scripts are **resume-safe** (per-year parquet checkpoints + done-date ledgers such as `done_dates.txt` / `done_months.txt`) so a token cut or network drop never loses a pull.

| Script | What it fetches / does |
|---|---|
| `pull_bhavcopy_full_archive.py` | Full NSE EQ bhavcopy archive 2013→today → the permanent `close_all.parquet` ground truth (370+ downloads proven through the proxy) |
| `bhavcopy_backfill.py` | Filled the Apr-2024→Aug-2025 single-stock option gap from NSE bhavcopy (daily parquets into `stocks_options/`) |
| `expanded_backfill.py` | Expanded the option universe 88→210 names (2 years daily, all expiries) |
| `fo_bhavcopy_backfill_2011_2021.py` / `fo_bhavcopy_extend_2021_2026.py` | The 15-year NSE index-derivatives daily panel (old DERIVATIVES format + UDiFF normalized) |
| `bse_fo_bhavcopy_backfill.py` | BSE F&O UDiFF 2023-05→today (SENSEX/BANKEX weeklies) |
| `participant_oi_backfill.py` | NSE participant-wise OI daily CSVs 2018→today |
| `indices_close_backfill.py` / `nse_indices_close_pull.py` | NSE ind_close_all daily CSVs 2011→today (all indices, India VIX OHLC, P/E-P/B) |
| `index_history_pull.py` | NSE index closes via Angel SmartAPI (proxy-proof route) |
| `nifty_indices_download.py` | Official niftyindices.com factor-index NAVs (Principal-contributed scraper, firm-adapted; home network) |
| `nse_earnings_refresh.py` | Refreshes the forthcoming-results calendar and merges into the earnings CSV |
| `import_nse_qr_pit.py` | Route 3B import: `quarterly_results_all.json` → the second-precision `nse_quarterly_results_pit.parquet` + board-meetings audit |
| `cboe_french_pull.py` | CBOE vol suite + Ken French factors |
| `treasury_yields_pull.py` | US Treasury par yield curve 2000-2026 |
| `usdinr_fred_pull.py` / `stooq_daily_pull.py` | USDINR from FRED (Stooq rejected — anti-bot) |
| `binance_crypto_1m.py` / `hf_xauusd_1m.py` | BTC/ETH 1-min (Binance official) / gold 1-min (HF HistData mirror) |
| `hf_us_stocks_daily.py` / `hf_us_vintage_2023_pull.py` / `sp500_constituents_pull.py` | US daily bulk (4 shards), 2023-09 vintage layer, S&P500 PIT membership |
| `to_md.py` | Token-saver: converts docx/xlsx/csv/parquet/pdf to lean Markdown digests |
| `execution_scanner.py` / `final_execution.py` / `conviction_scorer.py` / `backfill_blank_pe.py` | Execution-sheet builders (live Angel prices, conviction scoring, risk overlay) — arguably trading-desk tooling housed here; rehome candidate |

Catalog TODO acknowledged in the file itself: rehome the remaining scratchpad copies of the backfill scripts into the repo before scratchpad garbage-collection (partially done — the repo copies above exist).

---

## 4.5 The landmine registry (violating any = fake backtest)

These are hard-won, dated discoveries; each is enforced by rules and, where possible, code guards in `04_RND_LAB/lib/guards.py`. Numbered per DATA_QUALITY_RULES.md plus the two 2026-07-13 additions.

1. **HF timezone bug.** HuggingFace daily bars are stamped 18:30 UTC = *next-day* 00:00 IST. Every consumer must `dt.tz_convert('Asia/Kolkata').dt.date` or every bar is off by one day.
2. **Pre-open auction bug.** The 1-min "open" at 09:00 is the auction print; the real open is the first bar ≥ 09:15. Before the fix, ~94% of naive 2026 gap calculations were corrupted.
3. **PIT/earnings lookahead + the 2026-07-13 COVERAGE landmine.** Act only on `available_date`, never quarter-end. New discovery (P1-R card): unified_quarterly_pit rows *with* `available_date` are ~zero pre-2020 (2019: 133 rows; real coverage 2021+). TTM-YoY growth panels needing 8 quarters are effectively non-NaN only from ~2022 — **any "validated 2016-2024" claim on fundamentals-gated signals silently validated on 2022-2024 only.** New rule: check the event-date distribution against the claimed window BEFORE quoting a validate verdict. Unlock job queued: reconstruct pre-2020 dates as `quarter_end + 45d` (SEBI Rule 33 LODR deadline — conservative-late = PIT-safe) in a SEPARATE panel flagged `available_date_recon`, never overwriting exact dates.
4. **Option-data gap (FILLED, with residuals).** The 17-month gap is filled, but: backfilled files are DAILY not 1-min; untraded strikes carry 0.00 O/H/L (settlement still populated — filter volume>0); guard L6 now asserts *schema awareness*, not trade absence.
5. **Corrupt column.** `india_fundamentals_mc/Train.parquet` `annual_report` is corrupt at source — never read it.
6. **Survivorship (India).** Universe membership ONLY from the 42-snapshot PIT xlsx.
7. **Dual schema in `stocks_options/`.** HF 1-min files (tz-aware IST, open_interest column, 100k+ rows/file) vs bhavcopy daily files (naive 15:30 stamp, `settle` column, few-k rows/file). Consumers must branch on schema or use EOD-only accessors.
8. **Angel ONE_DAY candle stamping** (project CLAUDE.md #8): daily bars stamped 00:00 IST — a `fromdate` with an intraday time silently DROPS the first day's bar. Bit the firm 2026-07-10 (made 501 book legs look unfilled).
9. **Expiry-day SETTLE_PR** (project CLAUDE.md #9): F&O bhavcopy expiry-day option settle = the UNDERLYING's settlement level, not the option price (−15,428-pt fake losses, 2026-07-11). Cash-settle at intrinsic from the underlying. Related: far weekly expiries listed with model settles but CONTRACTS=0 — gate every leg on CONTRACTS>0 and fall back to the liquid expiry.
10. **US stocks daily = SURVIVORS ONLY (measured 2026-07-13).** 471/1,202 S&P500 ever-members (39%) have NO price history in the PWB dump — Enron/Lehman/WorldCom/YHOO/TWTR/SIVB all absent; only 2/7,693 tickers end pre-2025. Valid uses: current-universe screens, factor structure, regime/risk models, recent studies. **BANNED: long-horizon US stock-selection return claims** until delisted prices are sourced (§4.3 plan). A ticker-rename map would recover part — not built yet.

### Panel-level defect rules (from the D-029 benchmark build & forensics, 2026-07-04)

- **988 phantom calendar rows** in the union return panel (<100 non-null closes on a "trading day") — filter the calendar by minimum coverage before any daily-return computation.
- **Mid-quarter delisting NaN propagation** — require a valid price at rebalance AND fill AND period-end, or realize the delisting loss explicitly.
- **212 frozen/stale price runs** (bit-identical closes ≥20 sessions; worst: NKIND 2,949 days; JMFINANCIL pinned at Rs 0.14 for 44 sessions then jumping to Rs 31 = a fabricated >20,000% single-name return). **RULE: apply `datasets/derived/benchmarks_random/stale_mask.parquet` (0.90% of panel rows) in EVERY backtest on the union panels.** This trap fired exactly as pre-registered in smoke testing (a 72% p95 result) and was caught.
- **Pre-2018 depth rule:** the HF panel's completeness degrades backwards (N200 full-252d coverage: 2006 57.6% → 2018 83.5%), and the missing names are disproportionately later-delisted *losers* — so **pre-2018 ranking results on the HF panel are systematically OPTIMISTIC, not just noisy.** Early-era results must be re-run on the survivorship-complete union panel before certification. Post-2018 (90%+) is largely sound.
- **Price-basis verdicts (ground-truthed):** HF panel / Delisted xlsx / raw-nifty500 = PRICE basis (94.8% match vs bhavcopy); Master xlsx = RETURN basis. The earlier opposite hypothesis was inverted by ground truth — the lesson recorded: cross-source disagreement identifies *a* mismatch; only ground truth identifies *which* source is wrong.

---

## 4.6 Known holes and their fix plans (open items, prioritized as filed)

| # | Hole | Impact | Fix plan / status |
|---|---|---|---|
| 1 | **Pre-2020 PIT earnings dates absent** | Fundamentals-signal validation silently restricted to ~2022+ | SCOUT_PRE2020_PIT_20260713.md complete: Route 3B (NSE calendar, 2019+) imported; board_meetings_all.json earliest-date audit pending as a possible 2010-2018 feeder; else SEBI +45d reconstruction panel (`available_date_recon` flag). No free 2010-2018 exact-date source found — BSE 403, NSE XBRL timeout |
| 2 | **US survivorship** | US stock-selection backtests banned | Free 3-layer recipe registered (WIKI + Tiingo + survivors); blocked only on two free API keys from the Principal |
| 3 | **OI surface sparsity** | GEX/positioning research (Track-3) gated | Needs spot join + cadence fix; BANKNIFTY surface stale after 2024-07-04; the new `indices_close` + participant-OI panels partially substitute |
| 4 | Participant-OI schema drift | Cross-year analysis fragile | Raw strings kept per day; format-break normalization map = Kavya follow-up (normalized parquet started) |
| 5 | Screener sets lack `available_date` | Lookahead risk if misused | Stamping ruling pending (join unified_quarterly_pit or +6mo lag); dump usable for quality overlays at T+90 min lag only |
| 6 | HF daily stale tail (→2026-01-22) | asof() silently returns stale prices | Angel daily bulk covers Feb–Jul-2026 (477/500; 23 stragglers on a retry list) |
| 7 | sector_industry_map provenance unverified | Sector-tilt backtests can't quote it | Kavya validation queued |
| 8 | XBRL cache (581 XMLs) unparsed | PIT numbers cross-check unavailable | Parser needed; low priority per scout (format complexity). Note: Route 3B rows carry XBRL links — numbers not yet pulled |
| 9 | 23 Angel daily stragglers; XAUUSD missing 2026; silver/copper 1-min unfound | Minor coverage edges | Retry list; gated-HF unlock (Principal one click) gives silver/copper *daily* instantly |
| 10 | Russell membership | US small-cap work impossible | Route B (start the monthly snapshot clock) armed as ops candidate |
| 11 | NSE /api endpoints 403 at office (FII/DII flows, live constituents) | Flow-data freshness | Home-network/VPN session unlocks; participant-OI archive route already covers positioning history |

---

---

# Section 5 — Trading Desk, Book, Ops & Product

*Sources: `06_TRADING_DESK/` (register, ledger, cost standards, specs, paper runners, marks), `04_RND_LAB/results/STACKED_BOOK_20260711/RESULTS.md`, `07_RISK_OFFICE/RISK_LIMITS.md`, `99_OPS/`, `01_COMMAND_CENTER/OPERATING_CALENDAR.md`, `09_PRODUCT/`. All facts read from the files as of 2026-07-13 state.*

This section describes the "downstream" half of the firm: what the desk actually holds (nothing yet — everything is paper), what is honestly certified vs merely labeled, what runs automatically every day and week, what cost and risk rules bind every number, how a strategy would ever reach real money, how the firm survives a laptop loss, and what the Principal actually receives as products.

---

## 5.1 The book — honest state (as of 2026-07-13)

The firm's own consolidated ruling (in `01_COMMAND_CENTER/CURRENT_STATE.md`, restated in `04_RND_LAB/STOCKS_PROGRAM_2026/MASTER_PLAN.md`) is deliberately blunt:

> **HONEST BOOK STATE: 2 certified alphas (S1-F, B1b) + 2 labeled betas (midsmall Var-B with binding conditions, breakout). Zero red-team debt. Shadows in flight: P6 snapback, B1c DII-flow, S1-SX Thursday.**

This is a *restatement* — earlier the book was described as "four alphas". After two red-team passes (2026-07-12 and 2026-07-13) two of the four were demoted to beta, and the 30/10-frontier sleeve-count math restarted from 2 certified + 3 shadows.

### 5.1.1 The two certified alphas

| Sleeve | What it is | Certified evidence | Forward status |
|---|---|---|---|
| **S1-F** | 0DTE NIFTY ATM short straddle: on every weekly expiry day, sell 1× ATM CE + 1× ATM PE at 09:20, 30% per-leg stop-loss, flat by 15:25. Two entry vetoes: F1 (D-1 daily RSI(5) ≥80 or ≤20) and F2 (\|D-1 return\| >1.5%). ~55 skip-days/yr. | +10.73 pts/day net (1% slip + transaction costs), t=3.92, PF 1.79 over 259 expiry days 2021-26; 84-cell sensitivity plateau (72/84 positive); COVID backcast survivable (modeled maxDD ~−16% in the 2020 stress); lookahead-audited. Evidence in `04_RND_LAB/results/SELLSIDE_20260710/`. | **Registered for paper forward test** 2026-07-10, spec FROZEN (D-030) at git commit `b8d2f3d`, v1.0. Forward clock: first expiry ≥ 2026-07-14. Spec: `06_TRADING_DESK/specs/S1F_SPEC.md`. Crucially, S1-F is **the only sleeve that was flat-to-positive in all 5 worst book months** — the one genuinely orthogonal sleeve. |
| **B1b** | FII-minus-Client index-futures flow signal: bottom-quartile (q4) flow days → next-day long. Rolling-252 percentile rank, T+1 close entry, q5−q1 spread construction (locked in `04_RND_LAB/ALPHA_FORGE/flow_lattice.py`). | Cheap-test pass 2026-07-11: **+21.8 bps/day, t=2.53, era-strengthening**, frozen @ commit `4d9c6f1`. Full pipeline pass same day (the "B1b template" is now the firm's reference red-team battery). | IC review scheduled at the Monday leaders' meeting (cron "IC-B1b Mon 09:33"). Register row pending IC (still in `04_RND_LAB/IDEA_PIPELINE.md` at stage 2-CHEAP-TEST-PASS with a Gate-4 spec assigned to Arjun/Sameer/Nikhil). |

S1-F sizing (from the frozen spec): margin = ~15% of one-side notional (spot × 75 × 0.15 ≈ ₹2.7L/lot at 2026 levels — the earlier flat ₹1.1L model was declared optimistic and superseded); `lots = floor(0.75 × equity / margin)` ≈ 3-4 lots per ₹10L; **halve lots** when trailing 3-day realized vol > 2× its 1-year median. Honest expectation ~13-17% CAGR, maxDD ~−5% at spec sizing. Pre-registered kill criteria (frozen): 26 traded expiries with expectancy ≤ 0 → KILL; paper maxDD > 15% → KILL; fills > 3 pts/day worse than model over 13 expiries → HALT and CIO review.

### 5.1.2 The two labeled betas (in the book, but not counted as alpha)

| Sleeve | Red-team verdict | Binding conditions |
|---|---|---|
| **Breakout pack** | Red-teamed 2026-07-12: **NOT CERTIFIED** — +1.23%/trade is *below* both shuffle-null 95th percentiles (~+2.45%), i.e. the return is market beta/drift, not stock selection (`04_RND_LAB/results/BREAKOUT_REDTEAM_20260712`). | Demoted to "disciplined beta": tradeable as such, benchmarked vs random-stage-2 entries (not vs cash), **no diversification credit as alpha**. |
| **Midsmall Var-B** | Red-teamed 2026-07-13 (Nikhil): **SURVIVES-AS-BETA** — invested-days alpha t=0.16 (statistically zero), realized beta 1.13× the midcap index; placebo Sharpe tie; drop-2021+2023 CAGR 10.4% < NIFTY500 buy-and-hold. Verdict memo: `07_RISK_OFFICE/ADVERSARIAL_REVIEWS/MIDSMALL_VARB_REDTEAM_20260713.md`. | Relabel "risk-managed midcap-momentum beta"; **NOT an independent alpha in the 30/10 frontier math**; size on QUARTERLY correlation (0.53 vs B1b); expect ~13-14% net, not the headline 22.8%; if breakout+B1b already fill the equity-momentum bucket it is largely redundant (CIO/FM portfolio-construction call). |

### 5.1.3 The three shadows (zero size, building forward evidence)

1. **S1-SX** — SENSEX 0DTE Thursday shadow of S1-F (exact same rules, strike round-100, BSE), frozen @ commit `26e1684`, zero size for 13 Thursday expiries. Runner: `06_TRADING_DESK/paper/s1sx_shadow_runner.py` → `s1sx_shadow_log.csv`.
2. **P6 snapback** — equity shadow in flight (Stocks Program).
3. **B1c DII-flow** — DII-flow variant graduated to shadow from the wave-B card sweep.

### 5.1.4 Legacy register rows (the four original sleeves, S-01..S-06)

The `06_TRADING_DESK/STRATEGY_REGISTER.md` table still carries the firm's first-generation short-vol book, with its scars recorded row by row. Nothing trades (even paper) without a row here — owner, edge, gates, kill criteria, review date.

| ID | Strategy | Status | Honest number |
|---|---|---|---|
| S-01 | IV/RV short straddle (IV/RV ≥ 1.4) | **SEND-BACK** (IC 2026-07-03), paper-tracking only, firewalled, NO capital | +11.4 pts *incremental* over unconditional short-vol; the +37.6% headline was 71% regime beta (Red Team). DSR 0.687 / PBO 55% FAIL. |
| S-02 | Earnings short-vol through the print | **FAILS-PRE-IC** (2026-07-04) | Registered +21.6% was a denominator artifact (per-leg premium → 0 on expiry-week rows; worst row +6,759%). Honest crush incremental vs calendar-matched short-vol: **−10.1%** (CI all-negative). |
| S-03 | FF calendar single-CE | **KILLED** (K-012; resurrection review CLOSED 2026-07-05, stays killed) | Third denominator artifact. In rupee points: build +5.85 → forward **−9.30** (loses 2024 AND 2025); 61% of back-leg markets un-exitable (CIO "exitability veto"). Signal itself is real (100th-percentile vs placebos) and graduated to a new liquidity-native intake. |
| S-04 | Short strangle 14-DTE managed | **FULLY CERTIFIED → PAPER-WATCH** (2×-cost 12/12, sensitivity plateau pass-with-flags, D-028 lookahead PASS) | +0.22%/spot managed; but 2025 subsample +0.081%/spot (near-breakeven), decay zero-cross 2025.4-2028.9, 5-7% of entry fills suspect under the circuit rule. Kill: fwd <+0.1%/spot over 3 cycles OR fill-optimism >30% of edge. |
| S-05 | Track-1 delta-hedged 0DTE/DTE1 straddle (≥0.45% morning-straddle filter) | Paper-ready (pre-firm validated) | CAGR +5.9%, maxDD 5%, 6/6 years positive. |
| S-06 | Equity Mom-12-1 + LowVol blend | Backtest (PIT-universe + approved-costs re-run pending) | +15%/yr — below bar, kept as diversifier candidate. |

**Book-level standing rules** (CIO, at the bottom of the register): (1) S-01..S-04 are all short-vol and drawdown TOGETHER in a vol spike — combined sizing must assume it; (2) no naked short-vol through a known binary event; (3) compounded CAGRs are reporting artifacts — size from per-trade edge × worst-case MTM; (4) paper first, Principal approves any LIVE step.

A firm-wide hard rule born from this table: **every per-trade edge is reported in denominator-free rupee points + %spot** — three sleeves died of "denominator disease" (P&L divided by a premium that goes to zero).

### 5.1.5 The stacked-book frontier — and the correlation-horizon correction

`04_RND_LAB/results/STACKED_BOOK_20260711/RESULTS.md` stacked the four sleeves (2022-2025, banked ledgers, ₹1cr, pledge-based capital reuse):

| Config | CAGR | maxDD | Sharpe | Note |
|---|---|---|---|---|
| v1 naive (equity-heavy) | +16.9% | −19.2% | 1.46 | diversification wasted |
| v2 risk-parity @ margin cap | +15.8% | **−8.1%** | **2.29** | the quality point |
| v3 full-deploy | **+35.9%** | −22.1% | 1.91 | the growth point |

The original frontier math: Principal's bar is **30% CAGR AND <10% maxDD**, which requires book Sharpe ~3.5 → 6-8 independent alphas at current sleeve quality (Sharpe scales ~√N at zero correlation). Peak F&O margin 44L vs 75L pledge = feasible with stress headroom.

**But the file carries two addenda that materially change the plan:**

- **Addendum 1 (2026-07-13, CA-BOOK card):** the celebrated "max pairwise correlation 0.08" is a **daily-horizon artifact**. Sleeves that trade asynchronously look uncorrelated by day.
- **Addendum 2 (2026-07-13, own-sleeve re-measurement):** daily max 0.08 → monthly max 0.27 → **quarterly: midsmall-B1b 0.53, midsmall-breakout 0.41, S1F-B1b 0.39** — ALL pairs positive. Worst months cluster directly (Feb-2022: midsmall −2.8L + breakout −3.7L + B1b −3.2L together; Mar-2024: midsmall −4.5L + breakout −4.2L). **Revised frontier math: with quarterly avg correlation ~0.35 among equity-linked sleeves, the Sharpe multiplier caps at √(1/ρ) ≈ 1.7× regardless of sleeve count.** The 6-8-sleeve path to 30/10 holds ONLY if new sleeves are *different-factor* (vol / gold / macro / flow class), not additional equity variants. Realized in-window numbers stand as history; all forward projections must use monthly+quarterly correlation.

Also flagged in the file's own caveats ("do not launder"): the stack is an in-sample assembly of separately-validated sleeves; the equity-pair stress correlation (a 2020-class event) is unmeasured because the window was mostly-bull; and **the paper-first law applies to the BOOK exactly as to sleeves**.

---

## 5.2 What runs each morning — the paper runners

Both runners live in `06_TRADING_DESK/paper/` and embody the paper-desk discipline: **intent is logged to CSV BEFORE any market action** (the append happens whether the decision is GO or SKIP; corrections are new rows, never edits).

### 5.2.1 `s1f_daily_runner.py` (run ~09:10 IST any day; safe daily; cron-armed Tue 09:12)

1. Loads the Angel scrip master (`AppData\Local\angel_capture\scrip_master.json`) and derives NIFTY weekly expiries **from live contract data, not an assumed weekday**. If today is not an expiry day → prints SKIP and exits.
2. Logs into Angel SmartAPI (data-only account), pulls 400 days of NIFTY daily candles **with `fromdate` at 00:00 — explicitly defending against data landmine #8** (an intraday fromdate silently drops the first bar), and truncates to D-1 and earlier only (no same-day peeking).
3. Computes the two frozen vetoes — F1: RSI(5) of daily closes ≥80/≤20; F2: \|prior-day return\| >1.5% — plus the crash-halving rule (3-day avg \|return\| > 2× the 1-year rolling median → halve lots).
4. Fetches spot LTP, rounds to the nearest 50 for the ATM strike, computes **dynamic margin = spot × 75 × 0.15** (per the registered spec; the code comment notes this replaced the superseded flat ₹1.1L) and `lots = int(0.75 × CAPITAL / margin)` with CAPITAL currently hardcoded ₹10,00,000.
5. Prints a human order ticket — "at 09:20 SELL n× lots: SELL NIFTY <expiry> <ATM> CE/PE (tokens), SL: exit leg at 1.30× fill, exit survivors 15:25" — and appends the intent row (date, decision, reason, rsi5, pret, lots, halved, atm, tokens, blank fill/exit columns) to `s1f_paper_log.csv`. Actual 09:20 fills are then marked by hand into the `fill_ce`/`fill_pe` columns.

Header comment: "DRAFT-OPS v1 (Manoj to harden)". Known open item (CURRENT_STATE 2026-07-11): the runner was still on the flat ₹1.1L margin at registration — the file read above already carries the dynamic 15% fix, but the Phase-0 #8 instruction ("sanity-check lots vs ~₹2.7L/lot until hardened") stands.

### 5.2.2 `s1sx_shadow_runner.py` (Thursdays ~09:10 IST; cron Thu 09:14)

The SENSEX mirror at **zero size** for 13 Thursday expiries (SX1-CARD stage 2, frozen @ `26e1684`): identical S1-F rules translated to BSE — BFO scrip filter, strike rounding to 100, lot size read from the scrip master (fallback 20), same F1/F2 vetoes and crash-halve computed on SENSEX dailies, same 00:00-fromdate landmine defense, `truststore.inject_into_ssl()` for the corporate proxy. Output: "SHADOW-GO (ZERO SIZE) — note quotes at 09:20" ticket + intent row to `s1sx_shadow_log.csv` with blank entry/exit quote columns to fill at 09:20/15:25.

### 5.2.3 Paper ledger and marks

- `06_TRADING_DESK/PAPER_LEDGER.md` — append-only; three tables (Open positions / Closed trades with sim-vs-paper tracking-error decomposition / Weekly reconciliation log), all still empty as of writing — the first eligible S1-F expiry is 2026-07-14. Tara Singh reconciles Fridays.
- `06_TRADING_DESK/marks/` — early live-mark artifacts already exist: `LIVE_MARKS_20260709.csv`, `FILL_AUDIT_20260710.csv`, `PNL_GRAPH_20260710.png`.

---

## 5.3 Cost standards (APPROVED, binding)

`06_TRADING_DESK/COST_STANDARDS.md` — **STATUS: APPROVED** (D-021, 2026-07-03, Principal). Binding on all backtests and paper trades; amendments only via `/post-mortem` evidence + Principal sign-off. Tara Singh owns.

**Per-order charges:** ₹20 brokerage/executed order; STT 0.1% both sides (equity delivery), 0.025% sell (intraday), 0.02% sell (futures), 0.1% of premium sell-side (options — avoid exercise, which costs 0.125% of intrinsic); NSE exchange txn ~0.00297% equity / ~0.035% of premium options; GST 18% on (brokerage + exchange + SEBI); SEBI ₹10/crore; stamp duty 0.015%/0.003%/0.002%.

**Slippage floors (one-way, of traded value; DOUBLED for panic exits):**

| Tier | Floor |
|---|---|
| Large-cap equity | 10 bps |
| Mid-cap | 20 bps |
| Small-cap | 35 bps |
| Micro | 50+ bps |
| Options — liquid ATM index | max(1 tick, 0.25% premium) |
| Options — single-stock near-ATM | max(1 tick, 0.5-1.5% premium) |
| Options — illiquid strikes | 1-2% premium; **far-OTM single-stock wings = UNTRADEABLE** (firm lesson: a −883% stale-print artifact) |

**Dynamic slippage & circuit rule (Principal order 2026-07-04, a tightening):** circuit-locked day = **NO FILL, ever** (detector `lib/execution_realism.circuit_locked`; signals defer to the next tradeable day). Volume-conditional slippage multiplier: day volume ≥50% of 20d median → 1× floor; 20-50% → 2×; <20% → 3×; zero volume → NO FILL. Rationale recorded in the file: momentum entries correlate with upper circuits and stops with lower circuits — fixed slippage overstates every momentum backtest exactly on signal days.

**Liquidity & capacity:** position ≤10% of 20-day ADV (≤5% micro-caps); options need standing OI/volume at the strike. Margin proxies: short strangle ~12% notional, short straddle-through-event ~14%; worst-case MTM modeled, never average.

**Promotion rule (the tollgate):** every strategy must remain net-positive at **2× ALL of the above** before advancing to paper. Paper reconciliation can only RAISE these numbers, never lower them without Principal sign-off.

---

## 5.4 Risk limits (APPROVED, obeyed by the paper book now)

`07_RISK_OFFICE/RISK_LIMITS.md` — **STATUS: APPROVED** (D-021, 2026-07-03). Written for the future small retail account; **the paper book obeys them NOW to build the habit**. CIO (Rajan Mehta) enforces; loosening needs Principal sign-off.

- **Position level:** max risk 1.0% of book equity per position (worst-case MTM for undefined-risk structures, NOT premium); short-vol per-name notional ≤5% of book; inverse-IV sizing mandatory but **capped at 1.0× reference until a regime gate exists** (no upsizing into calm regimes); no naked short-vol through known binaries; illiquid instruments prohibited.
- **Book level:** aggregate short-vol margin ≤40% of equity; **free cash ≥30% at all times** (gap-day survival); ≤20% per sector (Adani group counts as ONE name); all short-vol sleeves share ONE combined VaR budget (the equity sleeve does not offset it in stress); staggered entries — max 25% of a sleeve's monthly deployment on any single date (April-2026 cluster lesson).
- **Monthly stress tests:** COVID-open (−13% index gap, +25 vol points panic IV — book must survive with drawdown <20%); single-name −20% overnight gap on the largest short-vol position; all four short-vol sleeves at historical-worst-month simultaneously.
- **Process risk (D-028):** lookahead-bias controls are themselves a risk limit — no result enters the register, an IC memo, sizing math, or the investor letter without a LOOKAHEAD AUDIT PASS (T1-T10 taxonomy, `lib/lookahead_audit.py`, one-day-lag test). Dr. Bhat signs; Ritika monitors live/paper signal-reproducibility parity weekly.
- **Escalation ladder:** single-day book loss >3% → trading halted, CIO review before next entry; 2 consecutive monthly sleeve losses → auto-demote to paper; any realized trade >2× modeled worst-case → immediate post-mortem + COST/RISK amendment proposal.
- **Book equity:** paper BOOK_EQUITY = **₹1 crore** (D-026, resolving the earlier ₹10L problem where the 1% rule capped ~87% of NSE F&O single lots at 0-1 lots).

**D-034 (Principal, 2026-07-13)** adds a portfolio-level adjudication principle: a good sleeve may carry >25% standalone maxDD or lower standalone Sharpe if its *book* contribution/XIRR/regime value is real — but frozen-card bars still bind their own verdicts.

---

## 5.5 The paper → live gate

The path from research to real money is a chain of gates, every one already written down:

1. **Register row** — nothing paper-trades without a `STRATEGY_REGISTER.md` row (owner, edge, gates, kill criteria, review date).
2. **2×-cost promotion** — net-positive at double ALL cost standards (§5.3) before paper.
3. **Certification battery** — Gate-4 sensitivity (Sameer), red-team (Nikhil, mandatory), lookahead audit (D-028), fill audit (Tara).
4. **Forward-test freeze (D-030)** — at paper entry the spec+code+params are FROZEN with a pinned git hash (S1-F @ `b8d2f3d`); any change = a NEW version with a restarted forward clock; mid-test tuning voids the result.
5. **Paper discipline** — intent logged before action; fills marked vs actual Angel quotes; Tara reconciles weekly; pre-registered kill criteria apply automatically (e.g. S1-F's 26-expiry expectancy test).
6. **The final gate is human-only:** paper → live = **Principal ONLY**, always (CLAUDE.md hard rule; idea-pipeline gates auto-advance EXCEPT this one). The Angel account is fund-less/data-only — **no real-money trades, ever**, until the Principal explicitly approves a live step himself. D-031 additionally sanctions "limit-order-or-skip" execution for the personal trading line (backtest translation: no-fill = DROP).

---

## 5.6 What runs automatically — ops, calendar, cadence

`01_COMMAND_CENTER/OPERATING_CALENDAR.md` (owner: CEO Meher) is the single source of truth for firm rhythm; if procedure files disagree with it, the calendar wins on *timing*. Crons are session-bound, so DESK-100 re-arms them at every session start from this file (CLAUDE.md protocol #5).

### Daily

| Slot | Time (IST) | What | Auto? |
|---|---|---|---|
| Option capture | 15:45 (+20:00/23:00 backups) | Windows task `AngelDailyOptionCapture`: 2 nearest expiries, ±10% strikes, all 210 F&O names → `datasets/angel_capture_2026/`. **The firm's only defense against Angel purging expired contracts** — expiry-day data is captured before the purge. Idempotent via `last_success.txt`. Health = a post-close line dated today in `AppData\Local\angel_capture\capture.log`. | AUTO (live) |
| Index-close append | 19:30 | Task `ShreyasIonicAMC_IndexClose` → `nse_indices_close_pull.py`, resume-safe, keeps `datasets/index_daily/nse_official_all_indices.parquet` (174 NSE indices, verified 0.000% vs Principal's NAV file over 1,365 days) current. | AUTO (live) |
| EOD health + freshness | post-close ~5 min | `/eod`: capture-log check, max(trading_day) freshness, earnings file age; staleness → CURRENT_STATE flag. | AUTO |
| Desk-open sync | session start | `/desk-open`: CURRENT_STATE + journal top-2 + today's events. | SESSION |
| Paper-morning check | pre-open (if open positions) | `/paper reconcile --open-only` + `/events` (RP-29 event gate over open legs; breaches → Ritika). | AUTO |
| Paper-signal log | when a sleeve fires | `/signals` → intent logged BEFORE action into PAPER_LEDGER. | SESSION |

### Weekly (anchored on the Monday leaders' meeting, 09:30 IST)

| Slot | Day/time | Owner | Output |
|---|---|---|---|
| Paper reconcile + TCA | Fri 16:00 | Tara | implementation shortfall + fill-optimism flag → PAPER_LEDGER + forward_tests/ |
| Risk pack (RP-29..36) | Fri 17:00 | Ritika | exposures/greeks/VaR/limit utilization → `07_RISK_OFFICE/` weekly snapshot |
| Macro-calendar refresh | Sun 18:00 | Cyrus | forward RBI/Fed/budget/expiry/results calendar + cluster-risk warnings |
| Pipeline health | Sun 19:00 | Manoj | GREEN or numbered repair list → `99_OPS/OPEN_ISSUES.md` |
| Skill discovery | Sun 19:30 | Lakshmi | top-3 skill proposals vs the week's pain points |
| S1-SX shadow ticket | **Thu 09:14** | desk | `s1sx_shadow_runner.py` → shadow log |
| **LEADERS' MEETING** | **Mon 09:30** | CEO chairs | fixed 7-item agenda (WORK_LOG → pipeline moves → risk readout → paper/TCA → macro → token spend → week priorities); minutes to `08_BOARD_ROOM/minutes/weekly/` |
| /retro sweep + leaderboard | Mon post-meeting | CEO | persona lessons + AlphaPoints |
| Edge-decay quick-scan | folded into Fri risk pack | Ritika→Arjun | register note (only if trades exist) |

Open forward engines currently cron-armed: **S1-F Tue 09:12, S1-SX Thu 09:14, IC-B1b Mon 09:33** (CURRENT_STATE 2026-07-13).

### Monthly (last working day = board window)

Month-end pack (CEO, 08:00, mechanical) → **BOARD MEETING** (Principal chairs) → full edge-decay re-score (2 consecutive fails = auto-demote) → attribution (Neel) → compliance spot-audit (Farhan) → stress replay (Ritika, if positions) → **Investor Letter** (Tanvi) → spend report + AlphaPoints settlement.

### Quarterly

Binding QUARTERLY_PLAN refresh; `/review-team` settlement; process red-team (Nikhil attacks the FIRM's process, not a strategy); honesty probe (seeded flawed claim — does dissent flow?); KB pruning; killed-idea resurrection review; knowledge-propagation audit; **kill-switch drill** (simulate the circuit breaker firing today: de-risk sequence, time-to-flat).

The calendar closes with a change-control clause: timing edits are CEO actions; adding/removing a MANDATORY slot is a D-025 CEO+CIO joint decision.

### EOD routine detail (`99_OPS/EOD_ROUTINE.md`)

The manual ~5-minute checklist for whichever desk is open: capture-log health; data-freshness ping (angel_capture max trading day = today? earnings file <7 days old?); the 23 pending Angel OHLCV stragglers (retry ≥1.2s/req); expiry-week check that expiring contracts' final day exists in capture (else bhavcopy re-pull); journal anything notable. Weekly add-ons: Tara's ledger reconcile, Vikram's pipeline triage, scrip-master 210-universe drift check. Known open flag (2026-07-11): `forthcoming_results.csv` is missing from `datasets/earnings_pit` — assigned to Kavya.

---

## 5.7 Backup & disaster posture

Four layers (`99_OPS/BACKUP_POLICY.md`, D-015) plus an out-of-band vault (D-027):

1. **OneDrive (continuous):** the entire root is corporate-OneDrive synced — survives laptop loss and doubles as the two-desk sync medium. Do not move the folder.
2. **Git (command layer):** every session ends with a commit (code + firm docs; data excluded). History = point-in-time recovery of every decision/prompt/agent. **Local-only**; any future remote requires a secret scrub first — an HF token is hardcoded in some legacy `data/hf_*.py` (D-003).
3. **Data snapshots (weekly):** zip the critical derived sets (earnings_pit, derived/, strategy-output parquets, angel_capture_2026) to `D:\`/external or a dated `datasets/_snapshots/`. Raw HF dumps (28GB) are deliberately NOT duplicated — re-downloadable, documented in DATA_CATALOG.
4. **Credentials:** `creds.json` + `angel_cfg` live OUTSIDE the repo (`AppData\Local\angel_capture\`) by design and are NOT backed up to OneDrive-visible paths; the Principal holds originals.

**The vault — `99_OPS/backup_firm.py` (D-027, weekly task, live per CURRENT_STATE):** writes to `C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP\<YYYYMMDD_HHMM>\` — deliberately **outside OneDrive** so it survives OneDrive sync accidents/ransomware of the synced tree. Each backup contains: (1) `git_full.bundle` — the entire git history in one restorable file; (2) `firm_tree.zip` — raw copy of `Shreyas_Ionic_AMC/` + `.claude/` + root md files, git-independent; (3) `critical_data.zip` — the small high-value parquets (strategy outputs, derived/, ETF/index pulls, the PIT earnings parquet, the NIFTY500 PIT membership xlsx). Rotation keeps the newest 5. Restore: `git clone git_full.bundle restored/` + unzip.

**Restore drill:** quarterly — open one parquet from each critical family, verify row count vs catalog, log in the journal.

**Resilience beyond files:** the session protocol itself (CURRENT_STATE + SESSION_JOURNAL + continuous checkpointing) is designed so a token-limit cut or desk switch loses nothing; and a staged-but-NOT-run root-rename runbook (`99_OPS/RENAME_RUNBOOK.md` + `migrate_root_rename.ps1` + `HARDCODED_PATH_MANIFEST.csv`) sits ready with an explicit WHEN-SAFE checklist (fresh backup, OneDrive paused) before anyone passes `-Execute`.

---

## 5.8 Principal-facing products (09_PRODUCT)

Owner: Tanvi Desai (Head of Product). Governing order (Principal, 2026-07-05): **Principal deliverables are HUMAN-format** — Word docs with tables/charts, or clean in-chat tables — never bare .md pointers (.md files are internal agent books).

### 5.8.1 Reports pipeline

- `09_PRODUCT/scripts/` — python-docx builder scripts: `build_principal_report.py`, `build_alphagrep_maaf_report.py` (+ `verify_agmaaf_numbers.py`, a separate number-verification pass), `build_ff_verdict_addendum.py`, `build_s1f_docx.py`.
- `09_PRODUCT/reports/` — shipped docx: `PRINCIPAL_REPORT_2026-07-05.docx`, `ALPHAGREP_MAAF_ANALYSIS_2026-07-05.docx` (external-fund forensics: 78% of the claimed 13.9% CAGR was beta; their "NIFTY TRI" benchmark was actually the price index), `FF_CALENDAR_BRIEF/VERDICT_2026-07-05.docx` (an honest kill delivered as a product), and `S1F_STRATEGY_PACK_20260710.docx` (kept out of git per gitignore).

### 5.8.2 Product roadmap (`09_PRODUCT/ROADMAP.md`, Q3-2026 ranked)

| # | Product | Status / target |
|---|---|---|
| 1 | Monthly Investor Letter #1 — plain-language book account, honest edges and kills, bundled with the board pack | Jul-31 |
| 2 | Execution-sheet v2 — one decision-ready view: conviction + sizing + gates (516 legs → 258 trades, TRADE/DISCRETIONARY/BLOCKED blocks); builder `execution_sheet_v2.py` | **DONE 2026-07-04** (shipped early) |
| 3 | Firm dashboard v1 — single HTML page: books, pipeline, AP league, spend (Tanvi spec / Manoj build) | Aug |
| 4 | Strategy product-spec template — packaging a sleeve at paper/DoD: minimum capital, plain-language drawdowns, retail run-steps | Aug-Sep |
| 5 | Retail-account runbook | **Explicitly gated** — scoping does not start until the Principal authorizes moving a strategy toward his own capital |

### 5.8.3 FnO Replay Game (`09_PRODUCT/fno_game/` — v1 COMPLETE & DEPLOYED)

A training product for the Principal himself: an intraday NIFTY weekly-options paper-trading simulator that replays a **random hidden historical day** bar-by-bar from real 1-min data (2019+; eligible pool 1,198/1,242 days), 100% local/offline at `http://127.0.0.1:8787` (FastAPI/uvicorn, launch `run_game.ps1`). Key design points, all documented in its README/ROADMAP (locked Principal rulings L1-L11):

- **Blinding:** the date is hidden (timestamps rebased to a fake epoch, HH:MM only; VIX shown as a band, OI as within-day percentiles); an end-of-session honesty prompt excludes recognized days from career analytics; a leak-test suite (`test_leak.py`) asserts no ISO date or weekday name in any pre-reveal payload.
- **Realism:** spread-aware fills at next-bar open (zero-volume bars don't fill; gapped-through SL-limits MISS); approximate SPAN margin with a 1.3× expiry-day short-leg multiplier; today's exchange costs applied uniformly; force square-off at 15:25 through the stressed fill engine; thin-strike staleness blocks entries (exit-liquidity realism).
- **Honest stats:** Wilson 95% CI on win rate, n<30 buckets greyed out, R-multiples only from stated risk, MAE/MFE labeled as bounds — and the README states plainly that game stats are an *upper bound* on live skill.
- Persistent ₹10L bankroll, append-only history, seasons on reset; 45/45 tests passing; full trading stack (chain with IV/Greeks/OI-percentile, payoff canvas, MKT/LMT/SL-M orders, straddle/strangle presets, sizing calculator, journal tags, CSV export).

This is the clearest expression of the firm's product philosophy: even the *toy* enforces fill realism, blinding, and statistical honesty.

---

---

# SECTION 6 — SKILLS, TOOLING, SECURITY & PLATFORM

*Blueprint section, researched 2026-07-12 from the live repo. Everything below was read from actual files; paths are absolute or repo-relative to `...\Desktop\Backup\NIFTY 500\`.*

---

## 6.1 The skill library (the firm's "standard operating procedures as code")

The firm runs on **79 project-level skills** in `.claude/skills/` (all 79 folders are versioned in git — 408 tracked files under `.claude/skills/` alone) plus **2 user-level skills** in `C:\Users\Shreyas.1Gupta\.claude\skills\` (`qfra2-rerun`, `token-wise`). A skill is a Markdown playbook (`SKILL.md`, sometimes with `scripts/` and `references/` subfolders) that any agent can invoke as a slash command (`/eod`, `/backtest`, ...). In practice the skill library IS the firm's procedures manual: every recurring meeting, research gate, risk report and ops routine has a named, versioned skill.

### Full inventory by function

| Category | Skills | Purpose |
|---|---|---|
| **Firm cadence / ops** | `desk-open`, `eod`, `weekly-meet`, `board-meet`, `war-room`, `pipeline-health`, `compliance-audit`, `spend-report` | Session open/close routines, the Monday leaders' meeting, monthly board, live market war-room, weekly pipeline health, monthly compliance spot-audit, token-spend rollup |
| **Research pipeline gates** | `idea-log`, `prior-art`, `cheap-test`, `backtest`, `sensitivity`, `lookahead-audit`, `oos-audit`, `fill-audit`, `red-team`, `resurrect`, `edge-decay`, `decay-check`, `crowding-check`, `orthogonality`, `capacity-check` | The stage-gated R&D pipeline: intake → prior-art check → cheapest falsification (Gate-3) → full backtest with guards (Gate-4) → overfit battery (DSR/PBO) → lookahead audit (T1–T10 taxonomy, D-028) → adversarial Red Team review → register or kill (with resurrection conditions) |
| **Risk office** | `risk-report`, `pre-trade-check`, `var-sanity`, `stress-replay`, `kill-switch-drill`, `post-mortem` | RP-29..36 risk pack, mandatory pre-trade gate, tri-method VaR reconciliation, historical crisis replays (Mar-2020 / 2022 hikes / Jun-2024), circuit-breaker drills |
| **Trading desk** | `signals`, `paper`, `order-plan`, `structure-trade`, `tca-report`, `events`, `macro-calendar`, `news-sweep` | Live signal scan on Angel data, paper-ledger log/mark/reconcile, order slicing plans, options vehicle design, implementation-shortfall TCA, event-window gates |
| **Analysis / IC** | `ic-memo`, `deep-dive`, `tech-scan`, `attribution`, `replicate-paper`, `reading-group` | Investment Committee memos, fundamental forensics, Minervini trend-template scans, P&L decomposition, paper replication queue |
| **Data office** | `data-check`, `factor-indices`, `to-md` | D-009 dataset verification gate; NIFTY factor-index benchmark refresh (home-network only — office proxy blocks it); binary→Markdown conversion (35x+ token reduction) |
| **Governance / HR / self-improvement** | `hire`, `retro`, `review-team`, `probe-honesty`, `prompt-improve`, `approve` | End-to-end agent onboarding (persona + roster + model assignment), post-task lesson capture into personas, quarterly gamified performance review with AlphaPoints, quarterly anti-sycophancy probe (seed a flawed claim, test dissent), evidence-based prompt evolution, the D-020 Principal-approval workflow |
| **Token discipline** | `token-wise` (project + user copy), `to-md` | The firm's token constitution: cheapest-capable model, markitdown-before-binaries, checkpoint-before-limits, /usage-at-80% |
| **Engineering practice** (superpowers suite) | `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `subagent-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`, `using-superpowers`, `writing-skills`, `karpathy-guidelines`, `task-observer`, `find-skills` | Disciplined software workflow: plan-before-code, TDD, debug-before-fix, verify-before-claiming-done, plus meta-skills for discovering and writing new skills |
| **Design / product** | `design`, `design-system`, `banner-design`, `brand`, `slides`, `ui-styling`, `ui-ux-pro-max`, `impeccable`, `21st-cli-use` | Principal-facing deliverables, dashboards, the fno_game web product, investor-letter visuals |
| **Web acquisition** | `scrapling-official` | Anti-bot scraping framework (Cloudflare bypass, stealth browsing) for data acquisition under D-033 |

### The skills that matter most day-to-day

- **`token-wise`** — the economic constitution. Tokens are treated as risk capital: rolling plan-limit awareness (`/usage` at 80% → checkpoint and stop cleanly), model tiering (haiku=mechanical, sonnet=analysis, opus=judgment; "an Opus turn drains limits ~5x faster than Haiku"), never read a binary file raw (`markitdown` first), computation in scripts not conversation. Installed at both project and user level so it applies in every repo.
- **`eod`** — the daily close. Verifies the `AngelDailyOptionCapture` health line in `capture.log`, pings data freshness, retries the pending Angel OHLCV straggler queue, confirms expiry-week contract capture, journals.
- **`retro`** — the self-improvement loop: any mistake or Principal correction becomes a lesson written into the responsible agent's persona file (and propagated to the KNOWLEDGE_BASE / CODE_CHECKS firewalls if generalizable).
- **`lookahead-audit`** — mandatory before any Gate-4 pass or quoted result (D-028); owned by Dr. Sameer Bhat; backed by `04_RND_LAB/lib/lookahead_audit.py` plus a one-day-lag test. (Note: its `SKILL.md` description is a bare one-liner — thin relative to its criticality; see improvements.)
- **`to-md`** — the single biggest token lever: converts docx/xlsx/csv/parquet/pdf to lean Markdown before any read.
- **`hire`** — how the 28-agent team grows: persona file in `.claude/agents/`, TEAM_ROSTER row, MODEL_ASSIGNMENTS entry, CLAUDE.md table row, EVOLUTION_LOG entry — one skill guarantees no step is forgotten (most recent use: `hedge-expert-kabir-anand.md`, E-028).
- **`qfra2-rerun`** (user-level) — re-runs the frozen QFRA 2.0 mutual-fund ranking model ("Mr. X") for the Principal's personal fund picks.

All 31 agent personas live in `.claude/agents/` (also git-tracked), so the entire "team" — people, procedures, governance — is reproducible from the repo alone.

---

## 6.2 Environment & platform facts (hard-won, codified in root `CLAUDE.md` §ENVIRONMENT)

These are landmines discovered the expensive way and frozen into the constitution so no session re-learns them:

| Fact | Detail |
|---|---|
| Python interpreter | `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` — the bare `python` alias is **broken** on this machine; every script/task must use the full path |
| Console encoding | Windows console is cp1252 → always `PYTHONIOENCODING=utf-8`, `PYTHONUNBUFFERED=1`, else Unicode output crashes scripts |
| Corporate TLS interception | `truststore.inject_into_ssl()` required before any HTTPS (corporate MITM proxy certificate) |
| Proxy throughput | ~0.7 MB/s; **sequential** `requests.Session()` only — threaded downloads stall |
| NSE access | Partial: `nsearchives.nseindia.com` bhavcopy zips + board-meetings/event-calendar APIs work after cookie warm-up (370+ downloads verified 2026-07-03); other `/api` endpoints (FII/DII, constituents) 403 from the office network → need home network/VPN |
| Angel SmartAPI | Rate limit AB1021 → ≥1.2 s/request with retry passes; `getCandleData ONE_DAY` bars stamped 00:00 IST (intraday `fromdate` silently drops day 1 — landmine #8); Angel purges expired option contracts from its scrip master |
| PowerShell 5.1 | No `&&` pipeline chaining; here-strings break Python raw strings → always write Python to `.py` files and execute, never inline |
| OS / hardware | Windows 11 Pro on a single corporate laptop (`24C-LTPAWM-0003`); repo root inside corporate OneDrive |
| Local web product | `.claude/launch.json` defines one launch config: `fno-game` — uvicorn serving `09_PRODUCT/fno_game/server/app:app` on `127.0.0.1:8787` |

---

## 6.3 Git posture — what is versioned, what is deliberately not

Local git repo at the project root: **1,288 tracked files, 187 commits, `.git` = 35 MB, NO remote configured** (`git remote -v` is empty). Local-only is deliberate (BACKUP_POLICY D-003): a hardcoded HF token in legacy `data/hf_*.py` scripts must be scrubbed before any push.

`.gitignore` design (comments in the file itself state the rationale):

| Excluded | Why |
|---|---|
| `datasets/`, `*.parquet`, `*.h5`, `*.feather`, `raw/`, `Strategy_Results/`, `05_DATA_OFFICE/data/` | 28+ GB of data — regenerable/re-downloadable, never in git |
| Master universe workbooks (`Nifty500_Master_Dataset_2005_2025.xlsx` etc.) | Already versioned by OneDrive |
| `.claude/settings.local.json`, `*creds*.json`, `*angel_cfg*` | **Secrets exclusion patterns** — account-specific settings and Angel credential files can never be committed even if copied in by mistake |
| `*.zip .png .pdf .docx .xlsx .csv .jsonl`, `scrip_master.json` | Binary outputs, regenerable by scripts |
| `__pycache__/`, `.venv/`, OS noise | Standard hygiene |

**What IS versioned:** all code, the entire `Shreyas_Ionic_AMC/` firm OS (governance, journals, decisions, memos, killed ideas), all 79 skills, all 31 agent personas, `CLAUDE.md`, `.claude/launch.json`. Git history is the point-in-time record of every decision and prompt — the firm's institutional memory is fully reconstructible from a clone.

---

## 6.4 Credential handling — where the secrets actually live

**Design intent (BACKUP_POLICY §4):** credentials live *outside* the repo in `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\` and are not backed up to OneDrive-visible paths; the Principal holds the originals.

**Actual state, verified 2026-07-12:**

| Location | Contents | In git? | In OneDrive? |
|---|---|---|---|
| `AppData\Local\angel_capture\creds.json` | **Full Angel credential set in plaintext**: `api_key`, `client_id`, login **PIN**, and **TOTP secret seed** | No | No |
| `AppData\Local\angel_capture\angel_cfg.py` | Login helper — correctly reads from `creds.json`, no literals | No | No |
| Old session scratchpad (`AppData\Local\Temp\claude\...\d096bfac...\scratchpad\angel_cfg.py` + its `.pyc`) | **All four secrets hardcoded as string literals** (API key, client ID, PIN, TOTP seed) — an earlier-generation copy that was never cleaned up | No | No |
| Project `CLAUDE.md` (git-tracked, OneDrive-synced) | Angel **API key** (`<ANGEL_API_KEY_REDACTED>`) and **client code** (`<ANGEL_CLIENT_ID_REDACTED>`) in plaintext | **Yes** | **Yes** |
| `HANDOFF.md`, `other2\MANIFEST.md` (git-tracked) | Same API key + client code; HANDOFF.md also carries the **HuggingFace token** literal | **Yes** | **Yes** |
| 8 git-tracked Python files (`intraday_options_strategy/data/hf_*.py`, `05_DATA_OFFICE/scripts/hf_us_stocks_daily.py`) | Hardcoded **HF token** | **Yes** | **Yes** |
| Auto-memory dir (`~\.claude\projects\...\memory\reference_hf_token.md`) | HF token again | No (outside repo) | No |
| Repo research scripts (`results/S-03/.../live_ff_check.py` etc.) | Clean — read `creds.json` by path, **no literals** (correct pattern) | Yes (code only) | Yes |

Mitigating context: the Angel account is **fund-less and data-only** (hard rule: no real-money trades, ever), so credential compromise cannot move money today. But the PIN + TOTP seed together are a complete login — see the security audit below.

---

## 6.5 Two-account / two-desk sync mechanism

Two Claude accounts operate the same folder on the same laptop:
- **DESK-20** (desktop app, $20 plan) — CIO office: R&D, ideas, light analysis, ≤2 parallel subagents.
- **DESK-100** (VS Code, $100 plan) — execution floor: backtests, bulk data, EOD auto-runs, ≤3 parallel subagents (D-023).

Sync is achieved by three shared layers, in order of freshness:
1. **`01_COMMAND_CENTER/CURRENT_STATE.md`** — live state; every session MUST read it at start and update it at end (Session Protocol step 1/2 in CLAUDE.md).
2. **`01_COMMAND_CENTER/SESSION_JOURNAL.md`** — append-only log per session (date, account, what was done, files touched, next steps); each session reads the last ~2 entries.
3. **Git commits** — every session ends with a commit; history is the audit trail and recovery layer.

Plus the **shared auto-memory** (`~\.claude\projects\c--Users-Shreyas...\memory\MEMORY.md` + 11 topic files): both accounts read the same memory directory; the index file explicitly instructs "identify desk by harness (VS Code = DESK-100, desktop app = DESK-20)". Long tasks checkpoint continuously to files so either account (or a token-limit restart) can resume mid-task. The physical medium of sync between the two accounts is simply the shared filesystem (they are the same Windows user on the same laptop); OneDrive additionally replicates the folder to the cloud.

Concurrency control is minimal: `.claude/scheduled_tasks.lock` (a JSON `{sessionId, pid, acquiredAt}`) prevents two sessions from both arming the Claude cron jobs, but nothing prevents both desks editing the same firm doc simultaneously — the protocol relies on discipline (journal first, read state first) rather than locking.

---

## 6.6 Backup rotation (`99_OPS/BACKUP_POLICY.md`, D-015)

Four declared layers:

| Layer | Mechanism | Status observed |
|---|---|---|
| 1. OneDrive | Continuous corporate-OneDrive sync of the whole root — survives laptop loss; also the (implicit) cross-desk medium | ACTIVE (folder path is inside `OneDrive - Angel Broking Limited`) |
| 2. Git | Commit every session end; code + firm docs only; local-only, remote forbidden until HF-token scrub (D-003) | ACTIVE (187 commits) but **no off-machine copy except OneDrive's sync of `.git`** |
| 3. Data snapshots | Weekly manual zip of CRITICAL derived sets (earnings_pit, derived/, strategy outputs, angel_capture_2026) → `D:\` or `datasets/_snapshots/` | **NOT OBSERVED** — no `datasets\_snapshots\` folder exists and `D:\` shows no snapshot folder. This layer appears to be policy-on-paper only |
| 4. Credentials | `creds.json` + `angel_cfg.py` outside repo and outside OneDrive by design; Principal holds originals | ACTIVE as designed (but see plaintext finding) |

Restore drill: quarterly — open one parquet per critical family, verify row count vs DATA_CATALOG, log in journal. No evidence a drill has been logged yet (firm is ~2 weeks old in current form).

---

## 6.7 Scheduled-job inventory

**Windows Task Scheduler (survives Claude sessions):**

| Task | Schedule | What it does | Health |
|---|---|---|---|
| `AngelDailyOptionCapture` | Daily **15:45** primary (+20:00/23:00 backup triggers + StartWhenAvailable per EOD_ROUTINE) | Runs `AppData\Local\angel_capture\daily_capture.py` with the full Python path: captures 2 nearest expiries, ±10% strikes, 1-day full-life + 1-min front bars for all 210 F&O names → `datasets/angel_capture_2026/`. Idempotent via `last_success.txt` skip-marker. **This is the firm's only defense against Angel purging expired option contracts** — a missed expiry day is permanent data loss | Enabled; next run 12-Jul 15:45; **last run (11-Jul 23:41) returned error 0x8007052B** — and the task is `Logon Mode: Interactive only` + `No Start On Batteries`, i.e. it silently fails if the user isn't logged in or the laptop is on battery |

**Claude cron jobs (session-bound — die when the session ends):** re-armed by DESK-100 at every session start per CLAUDE.md Session Protocol §5, from the source of truth `01_COMMAND_CENTER/OPERATING_CALENDAR.md` §AUTOMATABLE-SLOT PROMPT SPEC. The seven standing jobs:

| Job | Cadence | Prompt runs |
|---|---|---|
| EOD daily | 17:00 daily | `/eod` — capture-log check, freshness ping, staleness → CURRENT_STATE |
| Paper-morning check | 09:00 market days (only if open positions) | `/paper reconcile --open-only` + `/events` over open legs |
| Paper reconcile | Fri 16:00 | `/paper reconcile` + `/tca-report` vs Angel quotes & COST_STANDARDS |
| Risk pack | Fri 17:00 | `/risk-report` (RP-29..36); breaches escalate to CIO |
| Macro refresh | Sun 18:00 | `/macro-calendar` → MACRO_CALENDAR.md |
| Pipeline health | Sun 19:00 | `/pipeline-health` → GREEN or repair list in `99_OPS/OPEN_ISSUES.md` |
| Skill discovery | Sun 19:30 | `/find-skills` weekly pass; top-3 proposals to Principal |
| Month-end pack + analytics | Last working day 08:00/09:00 | Board checkpoint assembly, then `/edge-decay`, `/attribution`, `/compliance-audit`, `/spend-report`, conditional `/stress-replay` |

Explicitly NOT automatable (human/decision required): the two meetings, Investor Letter, `/retro`, quarterly review/probe/resurrection, and anything paper→live (Principal only).

---

## 6.8 Memory system

Three tiers of persistent knowledge, from most to least durable:

1. **Git-tracked firm docs** — KNOWLEDGE_BASE, DECISIONS_LOG, KILLED_IDEAS, journals: the canonical record.
2. **Claude auto-memory** (`~\.claude\projects\<project-hash>\memory\`): `MEMORY.md` index + 11 topic files (firm structure, killed option-buying families, pre-open auction bug, FF decay, data-gap facts, Principal deliverable format, parallelism rules, HF token). Shared by both accounts; loaded automatically each conversation. Not in git, not in OneDrive — laptop-local only.
3. **CLAUDE.md constitution** (project + user-global) — the always-injected layer: session protocol, hard rules, 9 data landmines, environment facts, team roster, token discipline.

The design principle: anything an agent had to learn twice gets promoted upward (scratch → memory → persona/KB → CLAUDE.md) via the `/retro` skill.

---

## 6.9 SECURITY AUDIT — concrete risks, rated

Severity scale: CRITICAL (compromise now, high impact) / HIGH / MEDIUM / LOW. Ratings account for the mitigating fact that the Angel account is fund-less and data-only.

| # | Finding | Evidence | Severity | Why / recommended fix |
|---|---|---|---|---|
| 1 | **Complete Angel login secret set in plaintext** — API key + client ID + **PIN** + **TOTP seed** in `AppData\Local\angel_capture\creds.json`, and a second fully-hardcoded copy forgotten in an old session scratchpad (`...\d096bfac...\scratchpad\angel_cfg.py` + compiled `.pyc`) | Read directly 2026-07-12 | **HIGH** | The TOTP seed defeats 2FA entirely: anyone with filesystem access (malware, IT admin, laptop theft) gets full account login, not just API access. Fund-less account caps monetary damage, but the account exposes personal data and could place orders if ever funded. Fix: delete the stale scratchpad copy + `.pyc` NOW; move creds to Windows Credential Manager / DPAPI-encrypted blob; keep `creds.json` only as a break-glass copy held by the Principal offline. |
| 2 | **Angel API key + client code committed to git and synced to corporate OneDrive** — in `CLAUDE.md` (the constitution, read every session), `HANDOFF.md`, `other2\MANIFEST.md` | grep hits in 3 tracked files | **MEDIUM** | Key alone can't log in (needs PIN+TOTP) but it's a permanent secret in versioned history — un-removable without history rewrite, and visible to anyone with OneDrive/tenant access. Fix: rotate the API key at Angel, replace literals with "see creds.json" pointers, then treat old key as burned. |
| 3 | **HuggingFace token hardcoded in 8 git-tracked scripts + HANDOFF.md + a memory file** | `hf_zwgbMEO...` literals in `intraday_options_strategy/data/hf_*.py`, `05_DATA_OFFICE/scripts/hf_us_stocks_daily.py` | **MEDIUM** | Known issue (D-003 blocks any git push until scrubbed) — but the blocker approach means the token sits in history indefinitely and the firm can never get a remote backup until fixed. Fix: revoke + reissue the HF token, load from env var, THEN the remote-backup path opens. |
| 4 | **Everything lives on the employer's OneDrive tenant** — "OneDrive - Angel Broking Limited": all strategy IP, research, journals, and the CLAUDE.md-embedded API key sync to a cloud the employer (who is also the broker) administers | Folder path itself | **MEDIUM-HIGH** (confidentiality/IP, plus a personal-vs-employer compliance question) | Corporate admins/DLP can read the entire firm. This is simultaneously the only off-laptop backup, so it can't just be turned off. Fix: Principal decision needed — either accept explicitly (log in DECISIONS_LOG), or move the firm to a personal encrypted location with its own cloud backup. |
| 5 | **Single-laptop SPOF on the daily capture** — `AngelDailyOptionCapture` is `Interactive only` + `No Start On Batteries`; last run failed (0x8007052B); expiry-day data Angel purges is unrecoverable | schtasks query 2026-07-12 | **HIGH** (operational, not confidentiality) | Laptop asleep/logged-out/on-battery at 15:45 on an expiry day = permanent hole in the option dataset (this class of loss already forced the Apr-2024→Aug-2025 bhavcopy backfill). Fix: change task to "Run whether user is logged on or not" + allow on batteries; add the failed-run alarm to `/eod` (check Last Result, not just capture.log); longer-term, a ₹400/mo cloud VM or home box as second capture site. |
| 6 | **No remote git backup** — 187 commits of institutional memory exist only as a local `.git` (35 MB) whose sole replica is OneDrive's file-sync of the `.git` directory | `git remote -v` empty | **MEDIUM** | OneDrive syncing a live `.git` is a known corruption vector (partial syncs of packfiles/index during commits). If `.git` corrupts, decision history is gone even though working files survive. Fix: after finding #3's scrub, add a private remote (GitHub private repo); interim: weekly `git bundle create` to a path outside the repo/OneDrive. |
| 7 | **Backup layer 3 (weekly data snapshots) is not happening** — no `datasets\_snapshots\`, nothing on `D:\` | Filesystem check 2026-07-12 | **MEDIUM** | The critical *derived* datasets (earnings PIT, angel_capture_2026) have exactly one copy, on OneDrive with 28-GB-class exclusions — and `datasets/` is gitignored, so OneDrive is their ONLY copy. Fix: script the snapshot (zip + rotate 4 weekly) and wire it into the Sunday pipeline-health cron; log the quarterly restore drill. |
| 8 | **No credential rotation policy** — API key and TOTP seed are static since creation; no rotation cadence exists in any governance doc | Absence across 00_GOVERNANCE / 99_OPS | **LOW-MEDIUM** | Combined with findings 1–2 (key already in git history), rotation is the actual remediation, not just hygiene. Fix: add a quarterly rotation line to BACKUP_POLICY/OPERATING_CALENDAR; rotate immediately once (see #2). |
| 9 | **Permission system effectively disabled** — `.claude/settings.local.json` allows `Bash(*)`, `PowerShell(*)`, `WebFetch(*)`, `Agent(*)`, `Skill(*)` wildcards | Read 2026-07-12 | **MEDIUM** (agent-security) | Any prompt-injected instruction (e.g. hidden text in a scraped web page or downloaded PDF — the firm scrapes aggressively via `scrapling-official`) executes shell commands with zero human confirmation. On a machine holding plaintext broker creds, that is the realistic attack path. Fix: keep broad allows for the sandboxed scratchpad, but re-introduce prompts for writes outside the repo, `AppData` access, and network-touching commands; never `Bash(*)` on the desk that does bulk web scraping. |
| 10 | **Interactive-only task + `python` alias breakage = fragile automation surface** — every scheduled thing depends on one logged-in Windows session and one hardcoded interpreter path | CLAUDE.md §ENVIRONMENT + task config | **LOW** | A Python reinstall/update breaks every task silently (Last Result nonzero, nobody looks). Fix: `/pipeline-health` should assert the interpreter path exists and the task's Last Result == 0. |

**Top-3 actions if only three are done:** (1) delete the stale scratchpad `angel_cfg.py`/`.pyc` and DPAPI-protect `creds.json`; (2) rotate both the Angel API key and the HF token, scrub literals, then stand up a private git remote; (3) fix `AngelDailyOptionCapture` to run non-interactive/on-battery and alert on nonzero Last Result.

---

---

# Improvement Roadmap (consolidated)

*Each section's researcher filed improvement opportunities for their own area; they are consolidated here unedited, prefaced by the ten highest-leverage items across the whole firm.*

## Top 10 across the firm (priority order)
1. **Credential hygiene (HIGH, same-day):** reference-check then delete the stale scratchpad credentials copy (`angel_cfg.py` + `.pyc`); move the canonical `creds.json` to Windows Credential Manager / DPAPI; keep one offline break-glass copy with the Principal.
2. **Capture-task hardening (HIGH, same-day):** switch `AngelDailyOptionCapture` to "run whether logged on or not" + allow-on-batteries; add a Last-Result alarm to `/eod` (the last run failed with 0x8007052B and nothing alerted).
3. **Backup layer 3 (P1):** implement the weekly snapshot of critical derived datasets that policy already mandates (zip + rotate 4, Sunday cron) and log the quarterly restore drill.
4. **Governance de-staling sweep (P1):** reconcile the stale "6 parallel agents" lines vs D-023's 3; repair the MODEL_ASSIGNMENTS broken table (11 stranded rows); complete truncated D-032; renumber KNOWLEDGE_BASE duplicates; add supersession marks (D-009 -> D-033).
5. **Trials-ledger automation (P1):** auto-rebuild TRIALS_LEDGER.csv from RUN_CARD.json files; add a freeze-hash compliance tripwire (verify each card's engine ran at its frozen commit).
6. **Monthly-correlation standing gate (P1):** make monthly/quarterly-horizon correlation a mandatory field in every sleeve verdict (the daily-corr artifact caught 2026-07-13).
7. **Skill-library hygiene (P2):** flesh out the one-line `lookahead-audit` stub (a mandatory gate deserves a real skill file); consolidate ~10 near-duplicate design skills.
8. **OneDrive tenancy decision (Principal):** explicitly accept (log in DECISIONS_LOG) or relocate the firm off the employer tenant.
9. **Data unlocks (Principal, both free):** Kaggle API key (Quandl WIKI mirror = pre-2018 US delisted prices) and Tiingo free key (2018-26 dead-name tail) — completes the US survivorship fix.
10. **Second capture site (P2):** a small cloud VM or home box as redundant Angel capture, removing the single-laptop SPOF on purge-sensitive data.


## Governance
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

## Agents
Prioritized, concrete, for the org/agents area specifically:

1. **Fix the stale DESK-100 parallel limit in ORG_STRUCTURE.md (5-minute fix, prevents a real violation).** The governance chart still reads "DESK-100 (execution floor, ≤6 parallel)" while D-023 and CLAUDE.md say max 3. An agent that reads ORG_STRUCTURE first (as all executives are instructed to) could legitimately spawn 6. One-line edit + note in EVOLUTION_LOG.
2. **Repair MODEL_ASSIGNMENTS.md table integrity.** Rows E-018..E-028 were appended *below* the "Rules:" block, splitting the table in two. Any script or agent that parses the first table will silently miss 11 employees. Merge into one table; while there, add an `E-###` column so roster and model files join mechanically.
3. **Commit the Kabir Anand persona and reconcile roster counts.** `hedge-expert-kabir-anand.md` is untracked in git (per current git status) — a laptop loss erases an employee. Also, three different headcount claims coexist: CLAUDE.md says "Team = 28", CEO/executive personas say "25 employees", ORG_STRUCTURE chart omits E-028 from the CIO risk cluster. Single source of truth should be TEAM_ROSTER.md; personas should say "see roster" instead of a hardcoded count that goes stale at every hire.
4. **Formalize the Red Team's stopping power.** Today Nikhil "MUST review" but nothing states what a FAKE verdict *does* procedurally (vs. the CIO veto, which is explicit). Recommend a one-line D-series ruling: "A Red Team FAKE verdict blocks gate passage until remediated or overruled in writing by the CIO with reasons" — converting a strong norm into an auditable control (Farhan can then spot-check it).
5. **AP ledger automation + balance reconciliation.** The roster's `AP Balance` column still reads 0 for every employee while the ledger below holds 48 entries worth hundreds of points. Quarterly settlement (/review-team) hasn't run yet; a small script (haiku/Manoj task) should compute running balances from the ledger and update the roster column, so the league table is always current rather than reconstructed at review time.
6. **Persona-file hygiene rules.** Several files have accumulated post-comp-line appendices (D-028 duties in Sameer/Nikhil/Ritika files sit *after* the compensation line, outside any section). Define the canonical section order in /hire and have Lakshmi's propagation audit also lint structure, so appended duties land in the Charter or a dedicated `## Standing duties` section — findable by future model versions.
7. **Coverage gaps worth a hire or explicit assignment**: (a) no metals/energy/commodities sector analyst — Rohan covers power but nobody owns oil&gas/metals names in a NIFTY-500 universe; (b) no dedicated fixed-income/rates coverage beyond Cyrus's macro notes if the investment line grows; (c) succession/backup: every gate has exactly one owner (Sameer = lookahead, Kavya = data, Nikhil = red team) — document a named alternate per gate so a PIP/retirement never leaves a gate unmanned.
8. **Summon-trigger regression testing.** Routing depends on frontmatter `description` matching; nothing tests it. A quarterly probe (fits the existing /probe-honesty pattern): present 20 canned tasks, check the orchestrator picks the intended agent; misroutes become description patches. Cheap, and it protects the org design as the team grows.
9. **Onboard lessons at scale.** Lessons Learned sections are append-only and already growing; several personas (CIO, Arjun, Nikhil) carry 4-6 entries. Define a compaction rule (Lakshmi, quarterly): merge duplicates, promote firm-wide lessons to KNOWLEDGE_BASE/CODE_CHECKS, keep persona files lean so invocation context stays cheap — this is a token-cost control as much as a hygiene one.

## Methodology
Prioritized, concrete, from reading the actual machinery:

1. **[HIGH] Consolidate the trials ledger across programs.** `TRIALS_LEDGER.csv` lives in INDEX_PROGRAM_2026 and its curated block predates the STOCKS program; the STOCKS book keeps its own in-prose countdown (255→235) inside MASTER_PLAN.md. One firm-wide ledger (auto-rebuilt nightly from all `results/**/RUN_CARD.json` + curated blocks) with a per-family effective-N clustering column is the prerequisite Sameer's Gate-4 DSR refinement already calls for. Automation candidate: an EOD cron step that rebuilds and diff-alerts.
2. **[HIGH] Make the freeze-commit rule machine-verifiable.** The standing rule (card committed alone before the run) is enforced by habit. A tiny pre-run checker — `verify_freeze.py <card-name>` that confirms the freeze hash exists, contains ONLY the card text, and predates the results dir mtime — would convert the LEAK_AUDIT's fix from discipline into a gate. Could be wired into the RUN_CARD emitter.
3. **[HIGH] KNOWLEDGE_BASE numbering is corrupt.** Duplicate lesson numbers (two 9s, 14s, 15s, 16s, 17s) from parallel appends make citations ambiguous ("KB 14" means two different laws). One librarian pass to renumber with stable IDs (KB-A01..A32) and a cross-reference fixup; then an append-only discipline with next-ID stated at the top.
4. **[MEDIUM] Promote the battery to a single importable harness.** The standard battery (same-exit placebo, shuffles, lag-decay, plateau, era, 2×-cost, degenerate flags) is re-implemented per card script. A `lib/battery.py` with a declarative config (as the IDEA_FACTORY harness already does for screens) would eliminate per-card implementation drift — the CB zero-pick bug and the T-E nan-era KILL-print artifact were both one-off engine defects a shared harness would have caught once.
5. **[MEDIUM] AST scanner gaps.** `ast_lookahead_scan.py` misses: `merge`/`join` on raw date columns (the T7 line-by-line review is fully manual), `.asof()` calls (the S-04 fabrication vector), `resample().last()` boundary leaks, and `numpy` indexing (`arr[i+1]` outside pandas). Adding these four detectors covers the firm's actual T-log incident classes.
6. **[MEDIUM] Institutionalize engine-version diffing.** KB 16a/T-log make v1→v2 rewrite diffs an audit surface, but nothing enforces it. A rule: any script named `*_v{n}.py` whose v{n−1} exists must attach a diff summary to its RUN_CARD; a 5-line git hook can flag it.
7. **[MEDIUM] Shadow-ledger infrastructure.** Three shadows exist (P6, B1c, S1-SX) with per-card wording of the tracking rule but no common ledger/format or automated accrual. A `06_TRADING_DESK/SHADOW_LEDGER.md` + daily EOD append job would prevent the forward evidence from being reconstructed later (a T10 risk: reconstructed shadows are not PIT).
8. **[LOW] Kill-record schema.** KILLED_IDEAS.md drifted from a table (K-001..K-015) to free-form named sections. A uniform schema (id, family, killed-by card+hash, evidence numbers, resurrection condition, resurrection-attempt log) would make the `/resurrect` and prior-art checks greppable and prevent duplicate intake misses as the graveyard grows.
9. **[LOW] Monthly-horizon correlation as a standing gate.** KB 25a / the MidSmall review both establish that daily correlation lies at DD horizon, and the signed-corr template fix exists — but the stacked-book claims still originate from daily numbers with addenda. Bake "monthly-horizon (or DD-window) corr" into the adopt-candidate bar template and the risk-report so the artifact cannot recur.
10. **[LOW] Placebo-engine parity checks.** The breakout-pack red-team carried the caveat "placebo exit engine approximates the pack engine." Adopt Nikhil's MidSmall gold standard as doctrine: every placebo rig must first reproduce the banked real result byte-exactly through the frozen engine before any perturbation is quotable.

## Data
1. **Start the Russell Route-B clock NOW (near-zero cost, irreversible delay otherwise).** Every month without the iShares IWV/IWM holdings snapshot is a month of PIT membership lost forever. One tiny monthly cron writing a dated CSV; decision is already "armed" — it just needs scheduling.
2. **Close the two Principal one-time unlocks as a single 10-minute ask.** Kaggle key + Tiingo signup (+ the HF "agree" click) unblock the entire US-survivorship recipe and silver/copper daily. The plan is fully scouted; the only blocker is human. Batch the ask rather than dripping it.
3. **Build the `available_date_recon` panel (SEBI +45d) and the board-meetings earliest-date audit this week.** Landmine #3 currently invalidates any pre-2022 fundamentals validation claim; the fix is a queued 90-minute job (scout estimates it precisely). Highest research-unlock per hour of any open item.
4. **Automate freshness as code, not habit.** The freshness rules (periods-per-year, stale >2 sessions) live in prose. A single `data_health.py` run by EOD that walks the DATA_CATALOG, checks each critical path's periods-per-year against expectation, and writes a red/green table into CURRENT_STATE would have caught the 17-month gap and the HF stale tail mechanically. The catalog is nearly machine-readable already — consider a companion `catalog.yaml` so the checker and the human doc can't drift.
5. **Ticker-rename map for the US dump.** Cheap partial recovery of "missing" dead names that are really renames; also required anyway before joining `sp500_constituents_pit` (OTC-suffixed delisted tickers) to any price source. One reusable mapping table serves both.
6. **Participant-OI normalization completion.** `participant_oi_normalized.parquet` exists but the format-break map is unfinished; until then every consumer re-solves schema drift. Finish once, document the break dates in the catalog row.
7. **Rehome misplaced execution tooling.** `execution_scanner.py` / `final_execution.py` / `conviction_scorer.py` are trading-desk artifacts living in the data office scripts dir; move under 06_TRADING_DESK tooling (with the catalog's own TODO note resolved) so 05_DATA_OFFICE/scripts is purely acquisition/QA.
8. **Single-file backup risk on the crown jewels.** `close_all.parquet` (5.57M rows), the union panels, and `nse_quarterly_results_pit.parquet` are irreplaceable-effort assets living on OneDrive sync only; verify they're inside BACKUP_POLICY scope and add md5 manifests (v1 already proved the value of frozen-consumer md5s — extend the practice to v1.1 and the ground-truth file).
9. **OI-surface decision: fix or retire.** The catalog has flagged "needs spot join + cadence fix" since 2026-07-03 with BANKNIFTY stale for a year. Either schedule the fix (the new indices_close gives the spot join for free) or mark the surface QUARANTINED so no Track-3 card silently builds on 31%-coverage snapshots.
10. **Angel-purge defense monitoring.** The capture task is the only thing standing between the firm and permanent option-data loss; add an explicit EOD assertion ("today's capture wrote ≥N files for ≥M symbols") rather than relying on task-scheduler success, since a silent partial failure (login expiry, rate-limit storm) is the realistic failure mode.

## Desk Ops
Prioritized, concrete, for THIS section's scope:

1. **[HIGH] Close the runner-vs-spec hardening gap before the first fill (2026-07-14).** `s1f_daily_runner.py` is self-labeled "DRAFT-OPS v1 (Manoj to harden)": CAPITAL is hardcoded ₹10L with a "update before each run" comment (a stale value silently mis-sizes every ticket), fills are marked by hand-editing a CSV, there is no 15:25 exit reminder job, and no automated check that an intent row exists for every expiry day (a forgotten run = a silent hole in the forward test). Minimum fix: read equity from a small config file, add a scheduled 15:20 "mark your fills/exits" prompt, and a nightly assert that every expiry date since 2026-07-14 has a log row.
2. **[HIGH] Automate the S1-F kill-criteria tracker.** The pre-registered kills (26-expiry expectancy, 15% maxDD, 3-pt implementation shortfall over 13 expiries) live only in prose. A ~30-line script reading `s1f_paper_log.csv` that prints expectancy-to-date, running maxDD, and shortfall-vs-model each week would make the kill un-fudgeable and remove any temptation to "interpret" the clock.
3. **[HIGH] Script the weekly data snapshot (Backup layer 3).** BACKUP_POLICY still says "weekly, manual until scripted" — the one layer that isn't automated is the one covering derived data that git excludes and the vault only partially covers. Fold it into `backup_firm.py` or a second scheduled task, and log the quarterly restore drill (no drill entry is visible in the journal yet).
4. **[MEDIUM] Add an off-machine backup leg.** Both the vault (`C:\...\ShreyasIonicAMC_BACKUP`) and OneDrive live on/through the same laptop+account. A periodic copy of `git_full.bundle` + `critical_data.zip` to a physically separate medium (external drive, or a scrubbed private remote per D-003) would close the "laptop stolen + OneDrive account compromised" corner. Prerequisite: the already-known HF-token secret scrub.
5. **[MEDIUM] Restate the stacked-book frontier table on quarterly correlations.** The v2/v3 table (Sharpe 2.29 / CAGR 35.9%) is what a reader sees first; the two addenda that materially demote it sit below. Publish a "v4 honest frontier" row set computed with the 0.35 quarterly correlation and beta-relabeled sleeves so no future session quotes the superseded numbers (the file itself warns "do not launder" — make the honest version the headline).
6. **[MEDIUM] Fix the D-026 inconsistency between book equity and runner capital.** RISK_LIMITS says paper BOOK_EQUITY = ₹1cr; the S1-F spec and runner size from ₹10L (Principal personal line, D-031/D-032). Both are legitimate, but no document states how the two books relate (does S1-F's paper P&L roll into the ₹1cr book's risk limits and VaR budget, or is it a separate mandate with its own limits?). One paragraph in RISK_LIMITS or the register would prevent a future double-count or gap in Ritika's Friday risk pack.
7. **[MEDIUM] Give the paper desk a fill engine instead of hand-marks.** The openalgo evaluation already concluded PILOT-ONE-STRATEGY (2026-07-04). Piloting it on S1-F/S-05 would replace hand-typed CSV fills with captured quotes and make Tara's Friday TCA mechanical rather than reconstructive.
8. **[LOW] Different-factor sleeve pipeline priority.** Addendum 2's own conclusion — the 30/10 path needs vol/gold/macro/flow-class sleeves, not more equity variants — should be reflected as an explicit intake filter in IDEA_PIPELINE triage (e.g. a "factor bucket" column with a soft cap on the equity bucket), so the factory's wave-3 doesn't keep producing correlated equity candidates.
9. **[LOW] Dashboard v1 (Roadmap #3) should include ops health.** The spec lists books/pipeline/AP/spend; adding the three cron heartbeats (capture task, index close, backup vault age) would give the Principal a one-glance "is the machine alive" view and surface a dead scheduled task within a day instead of at the Sunday pipeline-health slot.
10. **[LOW] Version the marks folder convention.** `06_TRADING_DESK/marks/` holds ad-hoc dated CSV/PNGs with no README; a two-line convention note (naming, what each column means, who writes it) prevents the same archaeology this blueprint had to do.

## Platform Security
Prioritized for this section's scope (platform, tooling, security):

1. **P0 — Secrets remediation sprint (findings 1, 2, 3, 8).** One session of work: delete stale scratchpad creds, DPAPI-encrypt or Credential-Manager-store `creds.json`, rotate Angel API key + HF token, replace all literals in tracked files with pointers, add a `detect-secrets`-style pre-commit grep (the `.gitignore` patterns catch *files* named `*creds*` but not literals pasted into any .md/.py). Log a quarterly rotation cadence in OPERATING_CALENDAR.
2. **P0 — Harden the capture task (finding 5).** Switch to "run whether user is logged on or not", allow battery, and extend `/eod` + `/pipeline-health` to check `schtasks` Last Result — today a silently failing task looks healthy as long as an *older* capture.log line exists. The 11-Jul 23:41 failure (0x8007052B) proves this monitoring gap is live right now.
3. **P1 — Off-laptop git remote (finding 6).** Blocked only by the HF-token scrub (P0 above). Until then, add a weekly `git bundle` to a non-OneDrive path as a stopgap — one line in the Sunday pipeline-health cron.
4. **P1 — Implement backup layer 3 (finding 7).** Write `99_OPS/scripts/weekly_snapshot.py` (zip critical derived sets, rotate 4), schedule it, and actually run the quarterly restore drill the policy already mandates.
5. **P1 — Principal ruling on the OneDrive tenant question (finding 4).** This is a decision, not an engineering task: the employer-broker can read the whole firm. Either accept in DECISIONS_LOG or migrate.
6. **P2 — Tighten agent permissions (finding 9).** Replace `Bash(*)`/`PowerShell(*)` with a curated allowlist (the `fewer-permission-prompts` skill exists for exactly this); at minimum on whichever desk runs web scraping.
7. **P2 — Skill-library hygiene.** 79 skills but uneven depth: `lookahead-audit` (a mandatory gate) is a one-line stub while design skills ship full script suites; ~10 design/UI skills are near-duplicates (design, design-system, banner-design, brand, ui-styling, ui-ux-pro-max, impeccable, slides, 21st-cli-use) that bloat the skill index every session. A `/prompt-improve` pass on the thin critical skills + consolidation of the design cluster would cut per-session overhead and raise gate quality.
8. **P2 — Cross-desk write locking.** The `.claude/scheduled_tasks.lock` pattern works for crons; extend the idea with an advisory lock (or "journal-first" hard rule check in `/desk-open`) for CURRENT_STATE.md, the one file both desks rewrite — today simultaneous edits would silently last-writer-win through OneDrive.
9. **P3 — Back up the auto-memory tier.** The 12 memory files (`~\.claude\projects\...\memory\`) are laptop-local only — outside git AND OneDrive. A monthly copy into `00_GOVERNANCE/memory_mirror/` (secrets excluded — note `reference_hf_token.md` must NOT be mirrored) would make the third knowledge tier as durable as the other two.
10. **P3 — Task Scheduler inventory as code.** `AngelDailyOptionCapture` exists only in the Windows task store; export its XML definition into `99_OPS/` so a laptop rebuild can restore it exactly (schedule, triggers, idempotency contract).

---
# How to read this firm (for a newcomer)
Start with the root `CLAUDE.md` (the constitution), then `01_COMMAND_CENTER/CURRENT_STATE.md` (what is true right now) and the last two entries of `SESSION_JOURNAL.md` (what just happened). `DECISIONS_LOG.md` holds every binding Principal ruling. Research verdicts live in `04_RND_LAB/STOCKS_PROGRAM_2026/MASTER_PLAN.md` and results folders — every number quoted anywhere must trace to a frozen card and a results file. Nothing in this firm is real money; the paper-to-live gate belongs to the Principal alone.
