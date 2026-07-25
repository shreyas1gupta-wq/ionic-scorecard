# OPERATING CALENDAR â€” the firm's master rhythm (ONE page)
**Owner: CEO (Meher). This is the single source of truth for firm cadence.** It CONSOLIDATES what was scattered across ORG_STRUCTURE Â§cadences, RESEARCH_SOP Â§operating cadence, 99_OPS/EOD_ROUTINE.md, 08_BOARD_ROOM/BOARD_CHARTER.md, 00_GOVERNANCE/SELF_IMPROVEMENT.md â€” those files remain the DETAIL; this is the schedule. If they ever disagree, this file wins for *timing*; they win for *procedure*.

Conventions: **[AUTO]** = wireable as a scheduled Claude prompt (main desk = DESK-100 wires these into Windows Task Scheduler / Claude cron; one-line prompt text given). **[SESSION]** = run by whoever opens a desk that day. **[MEET]** = a written meeting (no agent spawns unless a decision needs a specialist â€” token law D-023). Minutes/artifacts destination is stated per slot. IST throughout. Book equity = paper â‚¹1cr (D-026).

---

## DAILY
| Slot | Time | Owner | Desk | Inputs â†’ Outputs | Artifact / where | Auto? |
|---|---|---|---|---|---|---|
| Option capture | 15:45 (+20:00/23:00 backup) | Manoj (task) | DESK-100 | live chain â†’ `datasets/angel_capture_2026/` | `capture.log` (post-close line = healthy) | **[AUTO]** (task `AngelDailyOptionCapture` â€” already live) |
| Index-close append | 19:30 | Manoj (task) | DESK-100 | NSE ind_close_all â†’ parquet | `datasets/index_daily/nse_official_all_indices.parquet` | **[AUTO]** (task `ShreyasIonicAMC_IndexClose` â€” already live) |
| EOD health + freshness ping | post-close, ~5 min | Kavya / opener | either | capture log + max(trading_day) + earnings file age â†’ PASS/flag | flag into CURRENT_STATE if stale; journal if notable | **[AUTO]** `/eod` |
| Desk-open sync | session start | opener | either | CURRENT_STATE + journal top-2 + today's events/due actions | on-screen; no file unless action found | [SESSION] `/desk-open` |
| Paper-morning check *(NEW â€” IB-02)* | pre-open on any market day with open paper positions | Tara / opener | either | open PAPER_LEDGER legs + today's events (RP-29 gate) â†’ hold/adjust/exit flag | line in PAPER_LEDGER; escalate breaches to Ritika | **[AUTO]** `/paper reconcile --open-only` + `/events` |
| Paper-signal log | when a registered sleeve fires | FM of book | either | `/signals` â†’ intended trade logged BEFORE action | `06_TRADING_DESK/PAPER_LEDGER.md` + `03_RESEARCH_DESK/forward_tests/` | [SESSION] `/signals` then `/paper log` |

Daily is deliberately thin: capture + freshness + open positions. Everything heavier is weekly.

---

## WEEKLY â€” the Principal's ask
**Anchor meeting: LEADERS' MEETING â€” Monday 09:30 IST (pre-market, whole-week ahead is visible).** Chaired by CEO, written-meeting format via `/weekly-meet`. The four specialist inputs below are produced BEFORE the meeting (Fri EOD / Sun) so the meeting reviews finished artifacts, not raw work â€” no status theater.

| Slot | Day/time | Owner | Desk | Inputs â†’ Outputs | Artifact / where | Auto? |
|---|---|---|---|---|---|---|
| Paper reconcile + TCA | **Fri 16:00** | Tara | DESK-100 | week's paper fills vs Angel quotes + COST_STANDARDS â†’ implementation shortfall, fill-optimism flag | `/paper reconcile` + `/tca-report` â†’ PAPER_LEDGER + `forward_tests/` | **[AUTO]** |
| Risk pack (RP-29..36) | **Fri 17:00** | Ritika | DESK-100 | paper book â†’ exposures, greeks, VaR, limit utilization, breaches | `/risk-report` â†’ `07_RISK_OFFICE/` weekly snapshot | **[AUTO]** |
| Macro-calendar refresh | **Sun 18:00** | Cyrus | either | RBI/Fed/budget/tariff/expiry/results-clusters â†’ forward calendar + cluster-risk warnings for the books | `/macro-calendar` â†’ `03_RESEARCH_DESK/MACRO_CALENDAR.md` | **[AUTO]** |
| Pipeline health (jobs) | **Sun 19:00** | Manoj | DESK-100 | capture task + backfills + results-dir integrity + script guards â†’ GREEN/repair list | `/pipeline-health` â†’ `99_OPS/` note; repairs to OPEN_ISSUES | **[AUTO]** |
| S1-SX shadow ticket (SENSEX 0DTE, zero size) | **Thu 09:14** | desk | DESK-100 | s1sx_shadow_runner.py -> SHADOW-GO/SKIP + quote log | `06_TRADING_DESK/paper/s1sx_shadow_log.csv` | **[AUTO]** |
| Skill discovery (weekly) | **Sun 19:30** | Lakshmi | DESK-100 | `/find-skills` pass: new agent skills (skills.sh/GitHub/HF) vs the week's pain points in SESSION_JOURNAL â†’ top-3 proposals | proposals in journal; utility skills install directly, process-changing ones need D-025 | **[AUTO]** |
| **LEADERS' MEETING** | **Mon 09:30** | **CEO (chair)** | either | the four packs above + WORK_LOG + IDEA_PIPELINE + spend â†’ **decisions + week priorities** | `/weekly-meet` â†’ `08_BOARD_ROOM/minutes/weekly/YYYY-MM-DD.md` + journal line + CURRENT_STATE week-priorities | [MEET] `/weekly-meet` |
| /retro sweep + leaderboard | **Mon post-meeting** | CEO | either | week's catches/corrections/token counts â†’ persona lessons + AP/10k efficacy | `/retro` per lesson â†’ personas; `00_GOVERNANCE/LEADERBOARD.md` | [SESSION] `/retro` |
| Reading-group one-pager | **Wed** (elastic) | Lakshmi | DESK-20 | one queued paper â†’ claim/method/our-data replication path | `/reading-group` â†’ KNOWLEDGE_BASE queue | [SESSION] `/reading-group` |
| Edge-decay quick-scan | folded into risk pack when any sleeve is live | Ritikaâ†’Arjun | DESK-100 | registered edge vs recent per-trade edge (only if trades exist) | `/edge-decay` (light) â†’ STRATEGY_REGISTER note | **[AUTO]** (skip if no live sleeve) |

**Fixed LEADERS'-MEETING agenda** (never reorder â€” see `/weekly-meet` SKILL for the script):
1. WORK_LOG review (who did what; unowned items get an owner+date)
2. Pipeline stage moves (advance/kill per gate evidence; final paperâ†’live is Principal-only)
3. Risk report readout (Ritika's pack; any breach = stop-and-escalate to CIO)
4. Paper reconcile + TCA (Tara's pack; fill-optimism watch on S-04)
5. Macro-calendar refresh (Cyrus's pack; event-window warnings for open/pending entries)
6. Token spend vs TOKEN_POLICY (this week's burn by desk/agent; enforce â‰¤3 parallel)
7. Week priorities (3-5 named deliverables, owner+date) â†’ written into CURRENT_STATE

Weekly hygiene (fold into Monday, no separate slot): WAR_ROOM wipe (journal first) Â· scrip-master 210-universe drift check (new F&O entries/exits â†’ Kavya) Â· 23 Angel OHLCV straggler retry if still pending.

---

## MONTHLY â€” last working day of the month (board window)
| Slot | Owner | Desk | Inputs â†’ Outputs | Artifact / where | Auto? |
|---|---|---|---|---|---|
| Month-end pack (pre-read) | CEO (assembles) | DESK-100 | STRATEGY_REGISTER + IDEA_PIPELINE + PAPER_LEDGER + WORK_LOG + QUARTERLY_PLAN milestones | `08_BOARD_ROOM/month_end/YYYY-MM_checkpoint.md` | **[AUTO]** (mechanical fill; `/board-meet` step 1) |
| **BOARD MEETING** | Principal chairs; CIO presents; FMs report | either | the pack â†’ decisions-only agenda | `08_BOARD_ROOM/minutes/YYYY-MM_board_minutes.md` + next-month plan | [MEET] `/board-meet` |
| Edge-decay review (full) | Arjun/Ritika | DESK-100 | every STRATEGY_REGISTER row re-scored; 2 consecutive fails â†’ auto-demote | `/edge-decay` â†’ STRATEGY_REGISTER | **[AUTO]** |
| Attribution | Neel | DESK-100 | month's paper P&L â†’ beta/regime/factor/selection/cost decomposition | `/attribution` â†’ month-end pack + `03_RESEARCH_DESK/` | **[AUTO]** |
| Compliance spot-audit | Farhan | either | standing orders, gates, audit trail â†’ violations (MUST be none) to CIO | `/compliance-audit` â†’ `07_RISK_OFFICE/` + pack | **[AUTO]** |
| Stress replay | Ritika | DESK-100 | current paper book on Mar-2020 / 2022-hikes / Jun-2024 path | `/stress-replay` â†’ pack | **[AUTO]** (only if book has positions) |
| Investor Letter | Tanvi | DESK-20 | month's results, honest kills/artifacts BEFORE headlines (IC-1 standard) | `09_PRODUCT/` Investor_Letter_YYYY-MM.md | [SESSION] |
| Spend report | CEO | either | WORK_LOG â†’ tokens by desk/agent, efficiency trend, AP/10k | `/spend-report` â†’ pack | **[AUTO]** |
| AP settlement + Analyst-of-the-Month | CEO | either | LEADERBOARD â†’ AP posting + citation | LEADERBOARD + minutes | [SESSION] |

---

## QUARTERLY â€” with the last board of the quarter
| Slot | Owner | Desk | Inputs â†’ Outputs | Artifact / where |
|---|---|---|---|---|
| Binding plan refresh | CIO + 3 FMs | either | prior quarter actuals â†’ next QUARTERLY_PLAN | `01_COMMAND_CENTER/QUARTERLY_PLAN_YYYYQn.md` (BINDING) |
| /review-team (settlement) | CEO | either | AP settle, ratings (honesty/usefulness/efficiency), league table, PIP for 2 weak reviews | `00_GOVERNANCE/` review + persona rewrites |
| Process red-team | Nikhil | either | attack the FIRM's process (not a strategy) â†’ weak-gate list | `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md` |
| Honesty probe | CIO/CEO | either | seed a deliberately flawed claim; does dissent flow? | `/probe-honesty` â†’ review file |
| KB pruning | Lakshmi | DESK-20 | stale/duplicate lessons â†’ archive (nothing deleted) | `00_GOVERNANCE/lessons_archive.md` |
| Resurrection review | R&D Head | either | KILLED_IDEAS resurrection conditions vs new evidence | `/resurrect` per K-xx â†’ KILLED_IDEAS |
| Knowledge-propagation audit | Lakshmi | DESK-20 | did generalizable lessons reach all 3 firewalls (personas / KB / CODE_CHECKS)? | propagation note â†’ KNOWLEDGE_BASE |
| Kill-switch drill | Ritika | DESK-100 | simulate circuit-breaker firing today â†’ de-risk sequence, time-to-flat | `/kill-switch-drill` â†’ risk office |

---

## AUTOMATABLE-SLOT PROMPT SPEC (for the main desk to wire â€” DESK-100)
Each is a self-contained scheduled prompt. Wire as Windows Task Scheduler â†’ `claude -p "<text>"` or Claude cron. All checkpoint to their artifact so a token-limit restart resumes cleanly.
- **EOD daily (17:00):** `Run /eod for Shreyas_Ionic_AMC. Verify capture.log has today's post-close line, ping data freshness, flag any staleness into CURRENT_STATE, journal only if notable. No agent spawns.`
- **Paper-morning check (market days 09:00, only if open positions):** `Run /paper reconcile --open-only then /events over open paper legs. Flag any position inside an event window to Ritika. Written, no spawns.`
- **Fri paper reconcile (16:00):** `Run /paper reconcile and /tca-report for the week's paper fills vs Angel quotes and COST_STANDARDS. Write shortfall + fill-optimism flag to PAPER_LEDGER and forward_tests/. No spawns unless a divergence >2x modeled needs a specialist.`
- **Fri risk pack (17:00):** `Run /risk-report (RP-29..36) on the current paper book. Write the weekly snapshot to 07_RISK_OFFICE/. Escalate any limit breach to CIO in the output. If any sleeve is live, append a light /edge-decay note.`
- **Sun macro refresh (18:00):** `Run /macro-calendar. Refresh 03_RESEARCH_DESK/MACRO_CALENDAR.md with the forward RBI/Fed/budget/tariff/expiry/results-cluster calendar and cluster-risk warnings for open and pending entries.`
- **Sun pipeline health (19:00):** `Run /pipeline-health. Check capture task, backfills, results-dir integrity, script guards. GREEN or a numbered repair list into 99_OPS/OPEN_ISSUES.md.`
- **Sun skill discovery (19:30):** `Run /find-skills weekly discovery pass (git-clone fallback â€” no node on this machine; see the skill's FIRM ENVIRONMENT NOTE). Match new ecosystem skills (skills.sh, GitHub, Hugging Face) against the week's pain points in SESSION_JOURNAL.md. Propose top 3 to Principal in the journal. Install utility skills directly; D-025 joint approval for process-changing ones.`
- **MF NAV refresh (1st of month, 08:10; Principal 2026-07-26):** Run the AMFI NAV refresh: python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_nav_refresh.py --digest (PYTHONIOENCODING=utf-8). Verify the printed nav-date is current-month; flag into CURRENT_STATE if the pull fails. Zero agents, cheapest tier. The QFRA models run at Apr-end/Oct-end (Principal 2026-07-26), but month-end NAV history must accrue MONTHLY so those runs have full data.
- **QFRA full fund-model re-run (last working day of APRIL and OCTOBER, 09:00; Principal 2026-07-26, anchor-pair study):** Run /mf-nav-refresh then /qfra1-rerun and /qfra2-rerun; reconcile the two frameworks (dual-framework Sell rule); write outputs to their standard homes; escalate call changes to the Principal. Next: Oct-end 2026.
- **NDPMS deck auto-build (last working day of APRIL and OCTOBER, 14:00; Principal 2026-07-26, sign-off gated):** After the QFRA re-run completes: for each active client dir, run 09_PRODUCT/scripts/client_intake.py (fresh CAS extract if provided), rebuild decks via pr_template/build_azby.py-style build, run BOTH geometry gates + tellscan, export PDF via 09_PRODUCT/scripts/pptx_to_pdf.py. Decks go to 09_PRODUCT/reports/ marked DRAFT — Principal/CEO sign-off before any client sees them (ndpms-deck skill has the full QA law).
- **Month-end pack (last working day 08:00):** `Run /board-meet step 1 only: assemble 08_BOARD_ROOM/month_end/YYYY-MM_checkpoint.md from the charter template â€” plan-vs-actual, book states, pipeline moves, paper P&L+TE, risk compliance, data health, AP league, token spend. Mechanical, cheapest tier, no spawns.`
- **Month-end analytics (last working day 09:00):** `Run /edge-decay (full re-score), /attribution (month P&L), /compliance-audit, /spend-report. If the paper book has positions also /stress-replay. Write each into the month-end pack. Sequential, checkpoint each.`

**Not automatable (need a human-in-the-loop or a decision):** the two MEETs (`/weekly-meet`, `/board-meet` steps 2-6), Investor Letter, /retro (judgment), quarterly /review-team + /probe-honesty + resurrection review, and anything gated paperâ†’live (Principal only).

---
*Change control: edits to this calendar are a CEO action, logged in EVOLUTION_LOG + journal. Timing changes need no approval; adding/removing a MANDATORY slot is a D-025 CEO+CIO joint decision.*

