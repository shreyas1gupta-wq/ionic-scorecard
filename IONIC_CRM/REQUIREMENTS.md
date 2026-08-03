# Internal Ticket & Status CRM — Requirements

**Status:** DRAFT for Principal review
**Date:** 2026-08-03
**Scope:** Internal task/ticket tracking for ~10–50 employees at Ionic Wealth
**Deliberately technology-free.** Architecture, hosting and compliance sections are in `DESIGN.md` (pending research completion). This document says *what the system must do*, so it stays valid whether we build from scratch or fork an existing app.

---

## 1. Purpose

One place where work is assigned with a deadline, the person doing it records progress over time, and managers can see the true state of everything without asking anyone.

The system's value rests on one property: **the progress record cannot be quietly rewritten.** A tool where a missed deadline can be edited away measures nothing. Every design decision below serves that.

### What it is not
Not a client-facing portal. Not a CRM in the sales sense (no leads, no pipeline, no deals). Not a billing or timesheet system. Not a chat tool.

---

## 2. Roles

| Role | Can see | Can do |
|---|---|---|
| **Employee** | Own tickets, plus any ticket they raised or watch | Punch status, raise tickets, request deadline change |
| **Manager** | Own + their reports' tickets | Assign, reassign, approve deadline changes, reopen |
| **Admin** | Everything | User lifecycle, roles, config, exports, audit log |

**V2:** a read-only **Auditor** role — sees everything, changes nothing. Cheap to add, useful when compliance asks questions.

Role changes are themselves audited. Nobody can change their own role.

---

## 3. The ticket

### Fields
| Field | Notes |
|---|---|
| ID | `TKT-2026-0001` — sequential, never reused |
| Title | Required, short |
| Description | Required |
| Category | From an admin-managed list |
| Priority | P1 / P2 / P3 — drives SLA and stale-check cadence |
| Assignee | One person. Exactly one, always. |
| Raiser | Auto-set, immutable |
| Watchers | Optional, get notified |
| **Deadline** | Current deadline (a date, IST — "end of that day") |
| **Original deadline** | Set once at creation, **never changes** |
| Status | See lifecycle below |
| `client_ref` | Optional. **An opaque code only — never a client name.** See §8. |
| Created / closed at | Server timestamps |

### Lifecycle

```
Open ──> In Progress ──> Done
  │           │  ↑
  │           ↓  │
  │        Blocked
  │
  └──> Cancelled (reason required)

Done ──> Reopened (manager only, reason required) ──> In Progress
```

- **Assignee** moves the ticket through Open → In Progress → Blocked → Done.
- **Manager** can Reopen a Done ticket. This creates a new cycle on the same ticket; the earlier cycle's record stands unedited.
- **Cancelled** requires a reason and is terminal. Cancelled ≠ Done in every report.
- A ticket always has exactly one assignee. Reassignment requires a **handover note** and is audited.

**V2:** an optional per-category "requires verification" flag, adding `Done → Closed` confirmed by the raiser. Adds friction; only worth it if we find people closing things that aren't done.

---

## 4. The status punch — the core mechanism

A **punch** is one immutable record of progress. Punches are the system's memory.

### Punch fields
| Field | Required? |
|---|---|
| Ticket | Yes |
| Actor | Yes — server-set, never user-supplied |
| Timestamp | Yes — server-set, IST |
| Status at punch | Yes |
| Note | Yes when status is Blocked; otherwise optional but prompted |
| Blocked reason | Required when Blocked |
| Time spent (minutes) | Optional |
| Next action | Optional |
| Next action by (date) | Optional |

### Rules — these are the non-negotiable ones

1. **A punch is never edited and never deleted.** Not by the author, not by a manager, not by an admin.
2. **Corrections are new punches.** A correction punch references the punch it corrects and is displayed alongside it. The original stays visible.
3. **Every punch enters the tamper-evident audit chain** (mechanism in `DESIGN.md`). Removing or altering a past punch is detectable.
4. **A deadline change requires a punch first.** You must say where things stand before you can move the date.
5. **Status changes are punches.** There is no way to change status without creating a record of it.

### Stale-ticket rule
A ticket that is `In Progress` or `Blocked` with no punch for N working days is flagged **stale** and appears on the manager's dashboard. Default N by priority: P1 = 1 day, P2 = 3 days, P3 = 5 days. Admin-configurable.

This is what makes the tool enforce the discipline rather than just record it.

---

## 5. Deadlines

- Deadlines are **dates**, not timestamps — "end of day, IST".
- **Overdue** = today (IST) > deadline AND status is not Done or Cancelled. Computed when read, never by a scheduled job — this avoids the entire class of midnight and timezone bugs.
- **Working-day arithmetic** for SLA and stale checks, using a holiday calendar the admin maintains for the year. No dependency on an external holiday API that may go stale or disappear.
- **Deadline changes:** require a reason, a preceding punch, and manager approval. The raiser and manager are notified. The original deadline is preserved forever.
- **Both numbers get reported:** on-time against the *original* deadline, and against the *current* one. The gap between those two figures is itself the interesting metric.

---

## 6. Views

| View | For | Default |
|---|---|---|
| My Tickets | Everyone | Open items, deadline ascending |
| Due Today / This Week / Overdue | Everyone | — |
| Team board | Manager | Their reports, grouped by status |
| All Tickets | Admin | Filters: person, status, category, priority, overdue, date range |
| Per-person load | Manager, Admin | Open count, overdue count, oldest open, stale count |
| Ticket detail | Anyone with access | Full punch history, chronological, including corrections |

Free-text search across title, description and punch notes.

---

## 7. Reports

- On-time completion %, per person and per category, against original *and* current deadline
- Cycle time (created → Done): median and 90th percentile
- Ageing buckets: 0–3, 4–7, 8–14, 15+ working days open
- Stale tickets
- Reassignment and deadline-change frequency — where work keeps moving
- Export to CSV and Excel

Reports are read-only derivations. No report can alter a record.

---

## 8. Scope boundary — what this tool must never hold

The most important section in the document. Research into the SEBI Portfolio Managers and Research Analysts Regulations found several provisions that would pull an internal task tracker into regulated-records territory, carrying obligations this design cannot meet — five-year preservation, Principal Officer custody, and SEBI-specified formats. Staying outside them is a *design rule*, not a preference.

### 8.1 No client identifiers
The `client_ref` field holds **an opaque code only**. Client names, portfolio values, PAN, contact details and account numbers never go anywhere in this system.

### 8.2 No investment reasoning — Regulation 27(1)(e)
Reg 27(1)(e) requires a Portfolio Manager to keep *"records in support of every investment transaction or recommendation which will indicate the data, facts and opinion leading to that investment decision"*, and Reg 29 preserves those records for **five years**. The proviso adds that such records must be maintained *"under the hands of the Principal Officer"*.

If a punch note contains the analysis, reasoning or approval trail behind an investment decision, **that punch becomes a Reg 27(1)(e) record** — five-year preservation, producible on SEBI inspection under Reg 35, and required to be in the Principal Officer's custody. An append-anything-by-anyone log structurally is not that.

So: tickets may say *"prepare the Q2 review deck for account 4471"*. They may not say *why we bought or sold anything.*

### 8.3 No client complaints — Regulation 11(d)
Reg 11(d) requires grievance redressal within one month and that SEBI be kept informed of *"the number, nature and other particulars of the complaints received"*. **If client complaints are logged as tickets, this tool becomes the firm's complaints register** — with SCORES obligations attached. Complaints go wherever the firm already handles them.

### 8.4 No client-report or account evidence — Regulations 30–31
Reg 29 preserves *"records and documents mentioned under this chapter"*, and that chapter — **Chapter IV, Regulations 21 to 34** — also contains Reg 30 (separate client-wise accounts) and Reg 31 (periodic reports to the client). So a ticket that *evidences* a client report having been produced, checked or sent is itself inside the preserved set.

Tickets may reference *that* a deliverable exists. They must not become the record of its content or its sign-off.

### 8.5 No client correspondence, if the firm holds RA registration
SEBI (Research Analysts) Reg 25(1) was amended on 16 December 2024 to add clause **(vii): *"records of communication including emails, call recordings etc. with all clients including prospective clients in such manner as may be specified"***. This is wider than the investment-reasoning rule — it captures client *correspondence* generally, and lets SEBI specify the manner of keeping it.

### 8.6 Why this matters more than it looks
**A correction from the research verification.** My first draft called the five-year preserved set "a closed enumeration" that an employee-only tracker escapes entirely. That was wrong and gave false comfort: the set is defined by **subject matter across all of Chapter IV**, not by a short list. A ticketing tool used by an APM at an NDPMS house plausibly touches §8.3 and §8.4, not just §8.2.

Keeping all five categories out means the tool holds only **employee task data**, which carries no preservation duty. That is the difference between an internal convenience and a regulated record system, and it is far cheaper to decide now than to unwind.

**What this does NOT buy.** It does not put the app outside SEBI's cybersecurity framework. CSCRF scope follows *what the system is used for*, and a tracker holding NDPMS deliverables is used for regulated activity whether or not client names appear in it. The realistic target is **in scope but classified non-critical**, which SEBI expressly permits for business-non-critical internal tools on a documented risk assessment. `DESIGN.md` §8.5 covers this.

**One hard rule follows from it:** **no integration, no data feed, no shared credential and no link between this tool and any other firm system that handles client or regulated data.** Connected systems get pulled into audit scope. Segregation is the control.

Honest limitation: this is **policy, not enforcement.** Nothing can stop someone typing a client name — or an investment rationale — into a free-text box. Mitigations: an inline warning on description and note fields, the rule stated at first login, and an admin able to see and act on violations. But the boundary is ultimately held by the people using it, and it should be said out loud when the tool is introduced.

Be clear on what is *not* a mitigation: descriptions and punch notes are **not encrypted at rest in V1**, because encrypting them would break the full-text search in §6 and make the tool materially less useful. Only `client_ref` is encrypted. `DESIGN.md` §7 states that tradeoff in full. If the firm later needs genuinely client-linked records, that is a different system with a different compliance posture — not a new field on this one.

---

## 9. Administration

- **Create user:** admin adds the person's work email to the allow-list. First login emails them a one-time PIN. There is no password to issue, store, reset or forget.
- **Deactivate user:** never a hard delete. Their tickets and punch history remain intact and attributed; they simply cannot log in. Open tickets must be reassigned before deactivation completes.
- **Revoke access:** removing someone from the allow-list ends their sessions immediately. Security-sensitive — requires a logged reason and notifies the user.
- Role assignment, category and priority config, holiday calendar, stale-day thresholds.
- **Access review report:** every account, its role, last login, and inactive accounts flagged.
- **Audit log viewer** with a visible chain-integrity indicator.
- Full export.

No impersonation feature. An admin viewing data is fine; an admin *acting as* someone else destroys the attribution the whole system rests on.

---

## 10. Non-functional

- **Scale:** 10–50 users, roughly 50–200 tickets/month. Trivially small. Performance is not a design constraint; correctness and auditability are.
- **IST throughout.** Server time is authoritative for every punch.
- **Mobile-responsive.** People punch status from their phones; if that is awkward they will not do it, and the tool dies.
- **Every write audited**, including reads of the audit log itself.
- **Access and authentication events recorded by the application itself**, retained **two years — at least six months queryable, the remainder archived**. This is a SEBI CSCRF obligation on all regulated entities, and no free-tier vendor log meets it: Cloudflare Access retains authentication logs for about a day, Supabase for one day (one hour for auth). If the app does not write these rows, "who logged in, when, and what did they see" is unrecoverable. See `DESIGN.md` §8.
- **Sessions:** governed by the Cloudflare Access policy, not by application code — see `DESIGN.md` §3. Revocation is an Access action, not a feature we build.
- **Availability:** an internal tool. Brief downtime is an inconvenience, not an incident. No HA requirement.
- **Recoverable:** a documented restore drill that has actually been run, not just written down.

---

## 11. Explicitly out of scope

Named so they don't creep in: client-facing access · sales pipeline / leads / deals · billing or invoicing · timesheets for payroll · Gantt charts · task dependencies and parent/child hierarchies · a custom workflow builder · file attachments in V1 (links only — revisit once the PII position is settled) · threaded comments (punches *are* the conversation) · integrations beyond a single outbound webhook · multi-tenancy · anything AI-flavoured.

---

## 12. V1 / V2 split

**V1 — build this:** roles and Cloudflare Access OTP login · ticket CRUD · the punch model with the immutability rules · deadlines with working-day maths and change control · My Tickets / team / admin views · stale flagging · the seven reports · CSV + Excel export · user lifecycle · audit log with integrity check · **access-event log with two-year retention** · encrypted backup · rate limiting.

**V2 — after it's in real use:** Auditor role · verification step on close · file attachments · SLA clocks with auto-escalation · saved filters · bulk operations · calendar view · recurring tickets · webhook out · digest email once delivery is solved.

**Never:** everything in §11.

---

## 13. Open decisions

These are pending research now in flight, or need a Principal call. They affect *how*, not *what* — §1–§12 stand regardless.

| # | Decision | Status |
|---|---|---|
| 1 | Build from scratch or fork an existing open-source app | Research in flight — effort estimate for both |
| 2 | Which free Postgres host, and whether an India region is available on a free tier | Research in flight |
| 3 | Whether a non-admin can register an app in the M365 tenant — if yes, company-tenant storage may be reachable without IT | Research in flight |
| 4 | Exact DPDP obligations, and whether SEBI's CSCRF reaches a firm this size | Research in flight |
| 5 | When to seek firm sanction — Principal's call on sequencing | **Principal** |
| 6 | Whether managers see all reports' tickets or only those they assigned | **Principal** |
