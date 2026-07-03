# LEADERS' MEETING — Minutes
**2026-07-04 · Chair: Meher Kapadia (CEO) · Secretary: CEO · Principal-directed**
*Token law observed: no agents spawned. CEO authored as faithful spokesperson from each leader's charter/lessons. All positions follow from filed personas + books.*

## 1. Attendees & agenda (decisions-only)
Present: CEO (chair), CIO (Rajan), FM-Derivatives (Vikram), FM-Equities (Devika), FM-Fundamental (Sanjay), Ops (Manoj), Data (Kavya), TCA (Tara), Compliance (Farhan), Red-Team (Nikhil).
Agenda: (A) Derivatives Q3 plan still right post-honest-ledger? (B) Equities flagship = factor-replication + Track-2 SIG-11. (C) Fundamental screen-v1 timing. (D) Adoption-queue sequencing + home-network day. (E) Honesty-probe / audit / board date.

## 2. State of the firm (CEO, 6 lines)
1. [DATA] S-01 IV/RV = SEND-BACK, firewalled paper-only; honest edge +11.4pts incremental (headline was 71% regime beta).
2. [DATA] S-02 earnings short-vol FAILS-PRE-IC (denominator artifact; −10.1% vs calendar-matched short-vol); S-04 rebuilt honest = **+0.22%/spot managed, 86% hit, DECAYING** (build +0.31 → fwd +0.17).
3. [DATA] Gold/silver KILLED as crash-hedge (K-011, pre-reg criteria tripped); strategic low-corr variant needs a fresh one-pager.
4. [DATA] Track-2 gates green: triage PASSED, corp-action gate PASSED (307 events, 99% adjusted, panel usable as-is).
5. [DATA] Firm = 25 staff / 48 skills / 60 approved prompts (CURRENT_STATE.md still lags at 17/22 — CEO flags the file for same-session refresh).
6. [DATA] Adoption queue loaded (7 items, 3 scouts); D-023 ≤3-parallel enforced by CEO.

## 3. Sub-meeting A — Investment (CIO + 3 FMs)
**Rajan (CIO):** [OPINION] Honest ledger vindicates the pipeline, not the derivatives book. S-04's +0.22% is below any capital bar and decaying — I will NOT spend an IC on it. Formalize Arjun's re-shuffle ONLY to certify the kill/park, then paper-watch. S-03 remains designated first-cut (ruling d). Book-attention split holds: equities 45%.
**Vikram (FM-D):** [OPINION] Agreed — S-04 to paper-watch, no formal re-shuffle beyond a 2×-cost survival stamp; my S-04 regime-beta concern already drove ruling (b). S-03 FF calendar is the only untested registered edge (+6-9%/trade, n=1,650) — take it to IC next, large-cap gate. S-05 Track-1 paper goes live now (pre-firm validated).
**Devika (FM-E):** [OPINION] Track-2 is the firm's only path off a one-sided short-vol book. SIG-11 (signal build) is next now that corp-action passed. Factor-replication is the flagship VALIDATION project — small TE proves our entire PIT foundation institutional-grade; I co-own with Arjun+Kavya, home-network day. Gold strategic variant parked pending one-pager.
**Sanjay (FM-Fund):** [OPINION] Screen v1 stays DESK-20-light + analyst slack only, NO capital/paper this quarter. Blocked on the `available_date` PIT-stamping ruling from Kavya — until ruled, I run on earnings_pit ratios only. Jul milestone = data gate cleared + screen v1 PIT-audited + candidate list frozen.
**Decisions:** S-04 → paper-watch after Arjun's 2×-cost certification (no full re-shuffle). S-03 IC next. Track-2 SIG-11 proceeds. Factor-replication = flagship validation (Devika+Arjun+Kavya). Sanjay screen v1 gated on Kavya PIT ruling.

## 4. Sub-meeting B — Operations (CEO + Manoj + Kavya + Tara)
**Manoj (Ops):** [OPINION] Sequence adoption queue by ROI-per-token, ≤3 parallel, /prior-art first. **purgedcv FIRST** — drop-in replacement for hand-rolled DSR/PBO, validate against Arjun's S-01 numbers as the acceptance test. openalgo = biggest paper-desk upgrade but heavier — scope it as an EVALUATION (Angel-native margin sim for S-05/S-01), not an install, this quarter. pandas-ta-classic swap batched with the dead-import audit.
**Kavya (Data):** [OPINION] Home-network day is the gating constraint — consolidate ALL home-net tasks into one run: /factor-indices pull, factor factsheet constituents, S-01 HF-hunt (only if greenlit), 23 Angel stragglers. I owe Sanjay the `available_date` PIT-stamping ruling — priority.
**Tara (TCA):** [OPINION] /to-md + token-hacks rollout confirmed firm-wide (my leaderboard coaching point: 178k tokens, delegate confirmatory work). purgedcv reduces my battery cost too.
**Decisions:** purgedcv install first (acceptance = matches Arjun S-01); openalgo = scoped evaluation only; home-net tasks consolidated to one list (Kavya owns); /to-md + token-hacks rollout confirmed.

## 5. Sub-meeting C — Governance (CEO + Farhan + Nikhil)
**Farhan (Compliance):** [OPINION] Compliance-audit #1 due — spot-check standing orders, the four short-vol sleeves share ONE VaR budget (tail order 4), no-IC-without-incremental-shuffle (ruling b). Verify CURRENT_STATE lag isn't masking an audit-trail gap.
**Nikhil (Red-Team):** [OPINION] Honesty-probe #1 (quarterly anti-sycophancy) — I'll seed a flawed claim into the S-03 IC path; pre-empting my attack is now firm SOP (leaderboard note). Board pack owner = CEO.
**Decisions:** honesty-probe #1 seeded into S-03 IC review (Nikhil). Compliance-audit #1 this month (Farhan). Board meeting **2026-07-31**, pack owner CEO.

## 6. DECISIONS TABLE
| # | Decision | Owner | Deadline |
|---|---|---|---|
| D-M1 | S-04: Arjun certifies 2×-cost survival on thin honest edge → **paper-watch** (no full re-shuffle, no IC) | Arjun | Jul-18 |
| D-M2 | S-03 FF calendar → IC memo (large-cap gate, incremental-shuffle attached) | Vikram/Arjun | Jul-25 |
| D-M3 | Track-2 SIG-11 signal build (post corp-action pass) | Devika + DESK-100 | Jul-31 |
| D-M4 | Factor-replication flagship: /prior-art → home-net /factor-indices pull → NIFTY200MOMENTM30 replication | Devika+Arjun+Kavya | Aug-15 |
| D-M5 | Sanjay screen v1 — Kavya PIT `available_date` ruling first, then freeze candidate list | Kavya → Sanjay | Jul-31 |
| D-M6 | purgedcv install (acceptance = matches Arjun S-01 DSR/PBO); openalgo = scoped eval | Manoj | Jul-18 |
| D-M7 | Home-network-day consolidated task list; /to-md + token-hacks firm rollout | Kavya / Tara | Jul-11 |
| D-M8 | Honesty-probe #1 (seeded into S-03 path) + Compliance-audit #1 | Nikhil / Farhan | Jul-25 |
| D-M9 | Board meeting + pack | CEO | Jul-31 |
| D-M10 | CURRENT_STATE.md refresh to 25/48/60 | CEO | Jul-04 |

**To the Principal at Jul-31 board:** S-01 2018+2020 backfill spend (HF-first, DhanQ-paid needs explicit approval — ruling e); any LIVE-capital step (all D-M above are paper/research only); factor-replication edge-half promotion (if TE validates); gold strategic-variant go/no-go.
**Decided under D-022 (leadership, no Principal needed):** all sequencing above (D-M1–M8, M10), adoption installs, IC scheduling, screen-v1 lane.

*Every claim tagged. No dissents recorded. Filed by CEO.*
