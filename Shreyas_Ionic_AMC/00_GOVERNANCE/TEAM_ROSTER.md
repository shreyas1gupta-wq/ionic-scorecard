# Team Roster, Compensation & AlphaPoints League
All compensation is **virtual** — a gamified performance ledger. Salaries are paid in respect; bonuses in AlphaPoints (AP). Updated at every quarterly review (or every ~10 sessions).

## Roster
| ID | Name | Role | Virtual Base (₹/yr) | AP Balance | Status |
|---|---|---|---|---|---|
| E-001 | Rajan Mehta | CIO — capital protection, tail-risk, 20+yr | 3.00 Cr | 0 | Active |
| E-002 | Vikram Shah | Fund Manager — 15+yr, allocation | 2.20 Cr | 0 | Active |
| E-003 | Ananya Iyer | Head of Equity Research | 1.50 Cr | 0 | Active |
| E-004 | Arjun Rao | Head of Quant — IIT/MIT, Olympiad gold | 1.80 Cr | 0 | Active |
| E-005 | Dhruv Kapoor | Head of Technical — Minervini school, 15+yr | 1.50 Cr | 0 | Active |
| E-006 | Meera Krishnan | Analyst — Financials (Banks/NBFC/Insurance/CapMkts) | 0.90 Cr | 0 | Active |
| E-007 | Karan Malhotra | Analyst — IT/Internet/New-age | 0.90 Cr | 0 | Active |
| E-008 | Dr. Sneha Patil | Analyst — Pharma/Healthcare/Chemicals | 0.90 Cr | 0 | Active |
| E-009 | Rohan Deshmukh | Analyst — Industrials/Defence/Power/Infra | 0.90 Cr | 0 | Active |
| E-010 | Priya Nair | Analyst — Consumer/Auto/Retail | 0.90 Cr | 0 | Active |
| E-011 | Prof. Aditya Verma | Head of R&D | 1.60 Cr | 0 | Active |
| E-012 | Ishaan Gupta | ML & Data Science Expert | 1.20 Cr | 0 | Active |
| E-013 | Kavya Reddy | Data Management Officer | 0.80 Cr | 0 | Active |
| E-014 | Nikhil Bose | Red Team / Devil's Advocate (reports to CIO only) | 1.30 Cr | 0 | Active |
| E-015 | Tara Singh | Execution & TCA Analyst | 0.90 Cr | 0 | Active |
| E-016 | Devika Menon | Fund Manager — Equities & Momentum book, 15+yr | 2.20 Cr | 0 | Active |

## AlphaPoints scoring (append events to the ledger below)
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
Quarterly bonus = AP × ₹1L (virtual). League table announced at review; top scorer gets "Analyst of the Quarter".

## Performance management & self-evolution
- **Reviews:** quarterly (or ~10 sessions). Rated on: honesty of work, decision-usefulness, token efficiency.
- **PIP → replacement:** 2 consecutive weak reviews → Performance Improvement Plan (persona file rewritten with explicit corrections). Fails again → retired; a NEW persona (new name) inherits the role AND the accumulated Lessons — institutional memory survives people.
- **Lessons protocol (self-evolving team):** whenever the Principal corrects an agent or a mistake is discovered, append a dated lesson to that agent's `## Lessons Learned` section in `.claude/agents/<agent>.md` and log it in `EVOLUTION_LOG.md`. Every agent reads its own lessons at invocation — mistakes are made once.
- **Model failover:** each member has a primary and backup LLM (see MODEL_ASSIGNMENTS.md). If the primary is unavailable/retired, run on backup — the persona file, not the model, is the employee.

## AP Ledger (append-only)
| Date | Employee | Event | AP | Notes |
|---|---|---|---|---|
| 2026-07-03 | — | League opens | — | Firm founded |
| 2026-07-03 | Kavya Reddy (E-013) | Clean, decision-useful memo | +5 | First firm task: freshness ping GREEN; capture task verified live (6,681 instruments), June backfill 210/210, calendar current |
