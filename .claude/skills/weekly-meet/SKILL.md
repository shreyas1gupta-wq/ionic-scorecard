---
name: weekly-meet
description: Run the weekly Shreyas_Ionic_AMC leaders' meeting — CEO chairs a written, decisions-focused review off the four pre-produced packs (paper reconcile, risk, macro, pipeline-health), sets the week's priorities. Use for /weekly-meet, "run the weekly meeting", "leaders' meeting", Monday cadence.
---

# /weekly-meet — weekly leaders' meeting (chair: CEO Meher; cadence: OPERATING_CALENDAR §WEEKLY)

**Format law (token discipline D-023): this is a WRITTEN meeting.** The CEO speaks for the firm off already-produced artifacts. **Do NOT spawn any sub-agent** unless a specific agenda item needs a *decision only a named specialist can make* (e.g., a risk breach needs the CIO's ruling, a data landmine needs Kavya). Even then: at most ONE specialist, and only for that item. Default is zero spawns — the four packs were produced during the week; the meeting reads them.

## 0. Pre-flight (mechanical, cheap tier)
1. Read `01_COMMAND_CENTER/CURRENT_STATE.md` + journal top-2 (session protocol).
2. Confirm the four weekly packs exist for this week; read them (grep-first for the headline lines, don't dump whole files):
   - Paper reconcile + TCA (Tara) — `06_TRADING_DESK/PAPER_LEDGER.md` + latest `forward_tests/`
   - Risk pack (Ritika) — latest `07_RISK_OFFICE/` weekly snapshot
   - Macro calendar (Cyrus) — `03_RESEARCH_DESK/MACRO_CALENDAR.md`
   - Pipeline health (Manoj) — latest `99_OPS/` note / OPEN_ISSUES
   - If a pack is MISSING: note it as an accountability item (owner failed the cadence), proceed with what exists. Do not re-run the pack inside the meeting (that is the owner's slot, not the meeting's).
3. Skim `00_GOVERNANCE/WORK_LOG.md` for the week's entries and `04_RND_LAB/IDEA_PIPELINE.md` for stage state.

## 1. Fixed agenda (never reorder — same 7 items every week, from OPERATING_CALENDAR)
Work top to bottom. For each: state the input read, the finding, and the DECISION (or "no action"). Keep each item to a few lines — decisions, not status theater.
1. **WORK_LOG review** — what got done; any UNOWNED item gets an owner + date here.
2. **Pipeline stage moves** — advance or kill each in-flight idea per its gate evidence. Record the gate + verdict. (Final paper→live gate is Principal-only — never auto-advance it.)
3. **Risk report readout** — Ritika's pack. ANY limit breach or new tail = stop, escalate to CIO in the minutes (this is the one item that may pull in the CIO agent).
4. **Paper reconcile + TCA** — Tara's pack. Watch fill-optimism (S-04 managed-exit is the standing concern). Divergence >2x modeled → flag a /post-mortem for the week.
5. **Macro calendar refresh** — Cyrus's pack. Name any event window that touches an open or pending entry; the FM of that book carries the warning.
6. **Token spend vs TOKEN_POLICY** — this week's burn by desk/agent from WORK_LOG. Call out any >3-parallel violation (D-023) or an efficiency outlier (AP/10k) for a coaching lesson.
7. **Week priorities** — 3-5 named deliverables for the week ahead, each with an owner + a date. These become CURRENT_STATE's week-priorities block.

## 2. Outputs (all three, every time)
1. **Minutes** → `08_BOARD_ROOM/minutes/weekly/YYYY-MM-DD.md`. Use the block below. Decisions that are Principal rulings become D-series and also go to DECISIONS_LOG; CEO/CIO joint calls are noted as such.
2. **Journal line** → append one line to `01_COMMAND_CENTER/SESSION_JOURNAL.md` (date, desk, "weekly-meet chaired", key decisions, next).
3. **CURRENT_STATE week-priorities** → overwrite the week-priorities block with agenda item 7's list.

## Minutes template
```
# Weekly leaders' meeting — YYYY-MM-DD (chair: CEO Meher)
Packs in: [paper ✓/✗] [risk ✓/✗] [macro ✓/✗] [pipeline ✓/✗]  ·  Desk: DESK-xx  ·  Spawns: none / <specialist+why>
1. WORK_LOG: <done; unowned→owner+date>
2. Pipeline: <moves + gate/verdict>
3. Risk: <utilization; breaches→CIO or "none">
4. Paper/TCA: <shortfall; fill-optimism note>
5. Macro: <event windows touching open/pending>
6. Spend: <burn; parallel-cap compliance; outliers>
7. WEEK PRIORITIES: <3-5 lines, owner + date each>
Decisions: <D-xx if Principal ruling; else CEO/CEO+CIO note>   Dissents: <or none>
```

## Guardrails
- Cheapest capable tier; the meeting is mechanical synthesis, not analysis.
- No verdict on an investment call — that is the CIO/IC chain. This meeting arbitrates PRIORITY and RESOURCES only.
- If two books contend for the same scarce resource (desk time, a data pull), CEO decides here and logs it; a CIO disagreement on resourcing goes to the Principal (log the dissent).
- Checkpoint the minutes file as you go so a token-limit restart resumes mid-meeting.
