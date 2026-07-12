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

### Improvement opportunities

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
