# QUARTERLY PLAN — Jul→Oct 2026 (Q3-FY27)
**Author: Rajan Mehta (CIO, E-001) · synthesized from BLIND book-plans by Vikram Shah (Derivatives) & Devika Menon (Equities) · Status: BINDING (Principal delegated, D-021/D-022) · Filed by DESK-100 2026-07-04.**
*FM-Fundamental addendum FILED (below, 2026-07-04) — displaces nothing in P1-P6.*

---
## ADDENDUM — Fundamental Quality & Value book (Sanjay Kulkarni, E-017)
**Lane (DESK-20 light + analyst-desk slack only):** QUALITY/VALUE SCREEN v1 over the 42-snapshot PIT universe — F-score, 5-yr ROCE stability, net-debt/equity, accruals (CFO-vs-PAT), valuation percentile vs own history, all as-of `available_date` → 15-25 candidates → **Ananya's forensic checklist as ENTRY GATE (any single flag = automatic pass-over)** → 2-3 deep-dives per analyst → watchlist v1 with margin-of-safety bands. **NO portfolio, no capital, no paper this quarter.**
**Milestones:** Jul = data gate cleared + screen v1 PIT-audited + candidate list frozen · Aug = deep-dives (every rejection logged with killing flag + resurrection) · Sep-Oct = watchlist v1 (8-15 names, MoS bands, thesis-break triggers) → red-team → IC presentation scheduled around GATE-11.
**DATA CATCH (verified on disk):** `screener_deep` has NO `available_date` column (fiscal-period cols only) — naive use = LOOKAHEAD. Request to Data Officer: rule a PIT-stamping method (join to unified_quarterly_pit where mappable, else conservative +6-month lag on annuals). Until ruled, screen v1 runs on earnings_pit ratios ONLY.
**Kill discipline:** no momentum/RS inputs, no derivatives, no narrative stocks, no buying through a forensic flag, no paid data, no headline stats without DSR/PBO.
**Ask to CIO (first monthly review):** confirm analyst-slack claim survives event-calendar spikes; pre-agree promotion criterion — a red-team-surviving watchlist v1 earns a capital discussion in the Q4 plan, not before.

## 1. Firm priorities P1..P6 (WHO / WHERE)
**DESK-100 contention ruling: INTERLEAVE** — derivatives IC batteries run as short bursts (days each); Track-2 engine is the primary heavy tenant between them. Front-load cheap certainty (built ideas awaiting certification), keep the expensive bet (unbuilt engine) moving. [INFERENCE]

- **P1 — Live IV-cap fix (BLOCKING).** Tara Singh, DESK-20. Gates all short-vol paper. [DATA: IC-1 condition]
- **P2 — S-02 Earnings IC, then S-04 Strangle IC — each PRECEDED by the incremental-shuffle.** Vikram/Quant, DESK-100 bursts. S-02 first (cleanest mechanical WHY); S-04's 88% hit is the calm-block suspect.
- **P3 — Track-2 momentum engine DATA-11→GATE-11.** Devika, DESK-100 primary tenant. Week-1 corp-action check with Data Officer pairing, non-negotiable.
- **P4 — Gold/Silver cheap-test.** Devika + Data Officer, DESK-20. Cheapest real diversifier.
- **P5 — S-05 Track-1 index paper, live NOW.** Vikram, DESK-20. Pre-firm validated.
- **P6 — S-03 FF calendar IC + S-06 re-run.** Quant/Devika, DESK-100 last burst.

## 2. RULINGS (binding)
- **(a) Inverse-IV sizing capped at 1.0×** until a regime gate (Track-3 GEX) exists — upsizing into calm is procyclical (IC-1's core lesson). Downsizing into high IV stays. → RISK_LIMITS amendment.
- **(b) Pre-IC incremental-shuffle = standing Gate-5 deliverable.** No headline hit-rate reaches an IC without the incremental-vs-unconditional edge number.
- **(c) Gold/Silver fast-track APPROVED, D-009 gated:** Kavya sample-verifies the ETF series (provenance, available_date integrity, corp-action adjustment, second-source reconciliation) BEFORE any cheap-test compute.
- **(d) S-03 = designated first-cut** if capacity binds (slips to Aug/Sep; never displaces Track-2 or gold).
- **(e) S-01 2018+2020 data: HF-hunt first (time-boxed ≤3 days), DhanQ-paid only on failure and only with Principal's explicit approval.** No paid data for a SEND-BACK sleeve by default.

## 3. Monthly milestones
| | Jul | Aug | Sep–Oct |
|---|---|---|---|
| **Derivatives (Vikram)** | IV-cap FIXED; S-02+S-04 IC'd w/ incremental edges; S-05 paper LIVE | S-03 IC'd; paper on survivors; first reconcile | 6-wk paper track; shared-VaR sizing proposal |
| **Equities (Devika)** | DATA-11+SIG-11+REG-11 done; gold cheap-test VERDICT | BT-11+COST-11+VAL-11; S-06 re-run; PEAD triage | GATE-11 → Red Team → IC → paper if 2× survives |
| **Data/Infra (Kavya)** | Corp-action pairing day 1; gold D-009; IV-cap support | 23 Angel stragglers; OI-surface cadence | Freshness cadence; HF S-01 hunt (if greenlit) |

## 4. Book-attention split [OPINION, CIO]
**Derivatives 35% · Equities 45% · Data/Infra 20%.** Track-2 is the firm's only path off a one-sided short-vol book (IC-1: derivatives headlines are majority regime beta); data gates everything and has already burned us three times.

## 5. Tail-risk standing orders (non-negotiable this quarter)
1. NO live capital without Principal sign-off (D-010/D-018). Paper only.
2. NO naked short-vol through any binary event — gate re-checked before EVERY entry.
3. NO IC memo without the incremental-shuffle number; headline CAGR/hit-rate inadmissible.
4. NO position above 1.0× reference size; the four short-vol sleeves share ONE VaR budget.
5. NO paid data for a SEND-BACK sleeve without explicit Principal approval.
6. Any single-day paper loss >3% halts the book for CIO review.

*Dissents: none. Vikram's S-04 regime-beta concern is adopted (drives ruling b), not overruled.*
