# Model Assignments — primary + backup LLM per employee
The persona file (.claude/agents/*.md) is the employee; the model is the brain it runs on today. If a primary model is retired/unavailable, switch to backup — no persona change needed. Conceptual mapping (adjust names as Anthropic ships new models; keep tier logic).

| Employee | Tier | Primary | Backup | Frontmatter `model:` |
|---|---|---|---|---|
| Rajan Mehta (CIO) | Judgment | Opus 4.8 | Opus 4.6 | opus |
| Vikram Shah (FM) | Judgment | Opus 4.8 | Sonnet 5 | opus |
| Ananya Iyer (Equity Head) | Analysis | Sonnet 5 | Opus 4.6 | sonnet |
| Arjun Rao (Quant Head) | Judgment | Opus 4.8 | Opus 4.6 | opus |
| Dhruv Kapoor (Technical Head) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Meera Krishnan (Financials) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Karan Malhotra (IT) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Dr. Sneha Patil (Pharma) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Rohan Deshmukh (Industrials) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Priya Nair (Consumer) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Prof. Aditya Verma (R&D Head) | Judgment | Opus 4.8 / Fable 5 | Opus 4.6 | opus |
| Ishaan Gupta (ML) | Analysis | Sonnet 5 | Opus 4.6 | sonnet |
| Kavya Reddy (Data Officer) | Mechanical | Haiku 4.5 | Sonnet 5 | haiku |
| Nikhil Bose (Red Team) | Judgment* | Sonnet 5 | Opus 4.8 | sonnet |
| Tara Singh (Execution/TCA) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Devika Menon (FM-Equities) | Judgment | Opus 4.8 | Sonnet 5 | opus |
| Sanjay Kulkarni (FM-Fundamental) | Judgment | Opus 4.8 | Sonnet 5 | opus |
| Meher Kapadia (CEO) | Judgment | Opus 4.8 | Sonnet 5 | opus |
| Farhan Qureshi (Compliance & Governance Officer) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Ritika Sharma (Portfolio Risk Manager) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Cyrus Daruwalla (Macro & Events Strategist) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Aakash Jain (Derivatives Structurer) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Manoj Pillai (Ops & Platform Engineer) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Lakshmi Narayanan (Knowledge Curator / Librarian) | Mechanical | Haiku 4.5 | Sonnet 5 | haiku |
| Neel Basu (Performance Attribution Analyst) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Tanvi Desai (Product) | Analysis | Sonnet 5 | Haiku 4.5 | sonnet |
| Dr. Sameer Bhat (Overfit) | Analysis | Sonnet 5 | Opus 4.6 | sonnet |
| Kabir Anand (Head of Hedging & Tail Risk) | Analysis | Sonnet 5 | Opus 4.6 | sonnet |

Rules:
- Escalate one tier when a task will directly drive a capital-allocation decision.
- De-escalate for drafts/mechanical passes.
- Model changes are logged in EVOLUTION_LOG.md (who, when, why).
- **D-036 (2026-07-16, WS-4 benchmark):** verification/defect-review passes (red-team, audits, sensitivity checks) default one tier down from the employee's broad tier, regardless of role seniority — measured evidence showed Sonnet ties or beats Opus on this task type at ~1/10-1/15th the cost. Design/creative/portfolio-judgment work (backtest design, IC verdicts, capital sizing) is unaffected — that's a different task type the benchmark didn't test. Escalate to the backup model only for a genuinely hard or capital-sized kill attempt, not by default. *Nikhil Bose's "Judgment" tier label is kept for escalation purposes; his default working model is now Sonnet.
