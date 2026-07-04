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
| E-017 | Sanjay Kulkarni | Fund Manager — Fundamental Quality & Value book, 18+yr | 2.20 Cr | 0 | Active |
| E-018 | Meher Kapadia | CEO — firm operations, cadence, budget, HR (20+yr) | 2.50 Cr | 0 | Active |
| E-019 | Farhan Qureshi | Compliance & Governance Officer (12+yr SEBI) | 1.00 Cr | 0 | Active |
| E-020 | Ritika Sharma | Portfolio Risk Manager (10+yr, reports to CIO) | 1.20 Cr | 0 | Active |
| E-021 | Cyrus Daruwalla | Macro & Events Strategist (15+yr) | 1.30 Cr | 0 | Active |
| E-022 | Aakash Jain | Derivatives Structurer (12+yr) | 1.10 Cr | 0 | Active |
| E-023 | Manoj Pillai | Ops & Platform Engineer (10+yr) | 1.00 Cr | 0 | Active |
| E-024 | Lakshmi Narayanan | Knowledge Curator / Librarian | 0.70 Cr | 0 | Active |
| E-025 | Neel Basu | Performance Attribution Analyst (8+yr) | 1.00 Cr | 0 | Active |
| E-026 | Tanvi Desai | Head of Product, 12+yr | 1.20 Cr | 0 | Active |
| E-027 | Dr. Sameer Bhat | Overfit & Sensitivity Analyst (risk office), 10+yr | 1.20 Cr | 0 | Active |

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
| 2026-07-03 | Nikhil Bose (E-014) | Red Team kill pre-capital + bias catch | +30 | IC-1 S-01: regime-beta decomposition (71% of +37.6% headline = beta; true edge +11.4pts); halted mis-sized sleeve |
| 2026-07-03 | Arjun Rao (E-004) | Formal battery + honest self-withdrawal | +20 | DSR 0.687/PBO 55.3% verdict against his own R1 support; results/S-01/20260703_validation |
| 2026-07-03 | Tara Singh (E-015) | Clean, decision-useful memo | +5 | IC-1 TCA: caught live-feed IV-cap gap + mid-cap slippage thinness |
| 2026-07-03 | Vikram Shah (E-002) | Clean, decision-useful memo | +5 | IC-1 allocation memo; event-gate operating rule adopted |
| 2026-07-03 | Prof. Aditya Verma (E-011) | Pipeline intake milestone | +5 | 4 one-pagers filed w/ pre-registered kills; intake queue cleared; honest PEAD trials=1 |
| 2026-07-03 | Ishaan Gupta (E-012) | Confirmed data-bug catch | +15 | OI-surface 'READY' tag wrong: 31% day-coverage, BANKNIFTY stale post-2024-07, no spot/IV cols; catalog corrected |
| 2026-07-03 | Devika Menon (E-016) | Clean, decision-useful memo | +5 | Track-2 triage PASS + engine spec (5 params, 6 kills, honest prior); corp-action adjustment flag |
| 2026-07-04 | ALL 16 employees | FOUNDING-DAY BONUS (Principal) | +10 each | Principal's appreciation for firm build + IC-1 integrity. Excluded from efficacy ranking (gift, not output). |
| 2026-07-04 | Nikhil Bose (E-014) | Analyst-of-the-Day | +10 | Principal + Chair citation: the regime-beta catch is the firm's quality benchmark |
| 2026-07-04 | Vikram Shah (E-002) | Clean, decision-useful memo | +5 | Q3 book plan; pre-IC shuffle proposal adopted as firm SOP; cap-1.0× position vindicated by CIO ruling |
| 2026-07-04 | Devika Menon (E-016) | Clean, decision-useful memo | +5 | Q3 book plan; zero-non-short-vol-exposure case won 45% book-attention + gold fast-track |
| 2026-07-04 | Sanjay Kulkarni (E-017) | FOUNDING-DAY BONUS (Principal) | +10 | Joined day 2; same founding grant as all employees |
| 2026-07-04 | Sanjay Kulkarni (E-017) | Confirmed bias catch + clean memo (first task) | +20 | screener_deep has NO available_date (lookahead hazard) — caught on day-1 disk check; addendum filed within binding plan |
| 2026-07-04 | Arjun Rao (E-004) | Confirmed artifact catch (pre-IC shuffle #1) | +15 | S-02 +21.6% = denominator artifact; honest crush +4.8% fragile; saved a full IC cycle |
| 2026-07-04 | Tara Singh (E-015) | Confirmed guardrail-gap closure (P1, adversarially proven) | +15 | 6 unguarded IV paths -> sane_iv() everywhere; garbage-injection test rejected 3/3; zero regression on real data. Q3 blocking item CLEAR day 1 |
| 2026-07-04 | Arjun Rao (E-004) | Confirmed DATA-CORRUPTION catch (pre-IC shuffle #2) | +15 | S-04 future-expiry fabricated wins; physical-impossibility bound (max profit = premium) beat the generic explosion guard |
| 2026-07-04 | Kavya Reddy (E-013) | Clean D-009 gate (gold/silver) | +5 | 2 ETF series fetched, 7/7 checks, catalog-ready; cheap-test unblocked |
| 2026-07-04 | E-018..E-025 (8 new hires) | FOUNDING BONUS (Principal expansion order) | +10 each | CEO + institutional bench joined |
| 2026-07-04 | Tanvi Desai (E-026) | FOUNDING BONUS (Principal order — product team) | +10 | Head of Product joined; CEO+CIO joint approval per D-025 |
| 2026-07-04 | Manoj Pillai (E-023) | Ops bundle 3/3 + policy catch | +15 | 23/23 stragglers (500/500 coverage), risk ceiling live, openalgo PILOT verdict; caught the 10L-book/1%-rule lot-size impossibility (CIO escalation) |
| 2026-07-04 | Dr. Sameer Bhat (E-027) | FOUNDING BONUS (Principal-ordered hire) | +10 | Overfit/sensitivity specialist joins risk office |
| 2026-07-04 | Tanvi Desai (E-026) | Product ship (ahead of target) + 4 data catches | +10 | Execution-Sheet v2; blank-PE-price/max_lots/macro-calendar gaps routed; anti-data-dump self-edit |
| 2026-07-04 | Arjun Rao (E-004) | Artifact catch #3 (S-03) + S-04 certification + purgedcv adoption + honest self-correction (units trap) | +20 | The last original sleeve examined; denominator disease made a hard rule |
| 2026-07-04 | Arjun Rao (E-004) | D-M4 exact replication (TE 6.9% modern era) + data forensics: REFUTED the adjustment hypothesis with evidence (14/14 clean), isolated depth-not-adjustment root cause, honest blast-radius call on BT-11 | +15 | Replication + forensics same day; two D-028 self-audits PASS |
| 2026-07-04 | Kavya Reddy (E-013) | Screener-dump D-009 verification: PASS with honest PIT restatement warning + delisted-coverage caveat (FALLBACK-only) | +5 | Gate did its job — approved AND fenced |
| 2026-07-04 | Manoj Pillai (E-023) | PIT union panel v1: ground-truth inverted the basis hypothesis (Master=RETURN not HF), stop-rule honored, 3 dev bugs caught (Mar/Sep snapshots, splice fabrication, 159 fake-stock symbols), 2 canonical panels shipped | +15 | Flagship data task, same-day |
| 2026-07-04 | Arjun Rao (E-004) | D-M4 final leg: LOWVOL30 TE 4.58% (goal met), momentum TE halved, task-3 basis caveat self-issued, detectors clean | +10 | D-M4 declared DATA-VALIDATION COMPLETE |
| 2026-07-04 | Devika Menon (E-016) | BT-11 union re-run: survivorship cost measured (~4pp/yr, one-year concentration), honest-null shuffle insight (KB 13), edge survives haircut, cost constraint honestly held | +10 | Did not soften the 2x-cost fail |
| 2026-07-04 | Arjun Rao (E-004) | N500M50 replica (first build, corr 0.93) + six-series 1/3/5/10Y perf table; honest replica-drift flags per window | +5 | Same-day Principal request |
| 2026-07-04 | Dr. Sameer Bhat (E-027) | FIRST TASK IN ROLE: S-04 Gate-4 sensitivity (plateau proof, 5 honest flags, decay zero-cross bracketing) + D-028 lookahead audit (bit-exact T8 verification, 5-7% suspect-fill quantification under the new circuit rule) | +12 | Both PASS-WITH-FLAGS; nothing softened |
| 2026-07-04 | Arjun Rao (E-004) | D-029 factor family: 6 indices built w/ honest cost stack; cadence-kills-factor finding (KB 16); N500 LowVol50 promotion candidate identified; quality-coverage fiction exposed | +12 | 5th major deliverable today |
| 2026-07-04 | Ishaan Gupta (E-014) | D-029 benchmark suite (8 specs x 10k perms, cost-loaded) + 3 REAL panel bugs found (phantom rows, delisting NaNs, 212 stale-price symbols + stale_mask shipped) + size-premium inversion finding | +15 | The suite audited the panel better than the panel audits did |
