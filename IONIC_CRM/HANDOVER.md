# IONIC_CRM — Handover and Succession

This document exists because of one line in `DESIGN.md` §10: **"You are the single point of failure. High severity."** Everything below is either that risk stated precisely, the state of its mitigations, or the things a successor needs to know before touching this system — none of it is aspirational, and status claims below are checked against `PROGRESS.md` and the repository as it stands, not against what was planned.

---

## 1. The risk, stated plainly

One person — an Assistant Portfolio Manager, not a full-time engineer, building this in evenings alongside a real job — designed, built, and holds the only working knowledge of an internal system that up to 50 people may come to depend on for tracking deadline-bound work. That person also holds, or will hold, the only copy of the decryption key for the only backup of the only copy of the data (§4 below), and is the only person who has ever run any part of this stack.

If that person leaves, is unavailable, or is simply busy at the moment something breaks, there is currently **no one else who can operate, debug, or recover this system.** That is not a hypothetical: it is the exact condition the four mitigations below were specified to prevent, and none of the four is complete yet.

The stated success criterion for this milestone is: *a colleague can deploy this to a scratch environment following only the README, with the author not in the room.* That has not happened. What follows is the honest distance from it.

---

## 2. The four mitigations — current status

From `DESIGN.md` §10's risk table, row "You are the single point of failure":

| # | Mitigation | Current status |
|---|---|---|
| 1 | Repo owned by a **company** GitHub account, not a personal one | **Not done — and worse than "not yet done."** This project currently lives inside a larger folder (`NIFTY 500`) whose git remote is `github.com/shreyas1gupta-wq/ionic-scorecard.git` — a **personal** account, and a repository whose own name (`ionic-scorecard`) belongs to a *different* product entirely. As of this writing, `IONIC_CRM/app/`, `IONIC_CRM/research/`, and `IONIC_CRM/PLAN.md` are **untracked** — not committed to any git history at all, personal or otherwise. There is no company-owned repository for this project to be moved *to* yet; that decision (open item #4 below) has not been made, let alone executed. |
| 2 | A real README | **Written today, as this milestone, and untested.** `app/README.md` now exists and covers the setup path end-to-end. Writing it is necessary but not sufficient for the mitigation — the mitigation is proven only when someone who is not the author successfully uses it unaided, which is mitigation #3. |
| 3 | **One colleague who has deployed it at least once** | **Not done.** Milestone M11 (deploy) has not happened at all yet — there is no live Cloudflare Access application, no Supabase project, no production deployment for anyone to have run, let alone a colleague other than the author. This mitigation cannot be completed before M11, and has a dependency the other three don't: it needs a second person's time, not just the author's. |
| 4 | Documented and tested **key escrow** | **Not done.** The backup mechanism itself (milestone M9 — encrypted `pg_dump` to a private repo, daily chain-anchor commit) has not been built yet, so there is no key to escrow. `DESIGN.md` §8.3 records the decision to pin the `age` backup encryption to classic X25519 keys specifically *because* the newer post-quantum key format is unwieldy for paper escrow — but that is a design constraint on the *eventual* escrow, not an escrow that exists. Nobody but the author currently has, or could get, a copy of any decryption key, because none has been generated in an operational context yet. See `RUNBOOK.md` §6 for what still needs deciding (where the second copy physically lives) and proving (that someone other than the author can use only that copy to decrypt a real backup). |

**Bottom line: zero of the four mitigations are complete.** Two (#1, #4) are blocked on decisions or milestones that have not happened; one (#2) was completed today but is unverified; one (#3) cannot start until deployment exists.

---

## 3. The scope boundary — and why it is load-bearing

`REQUIREMENTS.md` §8 names this "the most important section in the document," and that is not rhetorical. The tool must never hold five categories of data. A successor who does not understand *why* — and adds "one helpful field" because a colleague asks for it — will not just create a minor compliance wrinkle. They will pull the entire application into SEBI's Chapter IV preserved-records regime, which this design is deliberately built to sit outside of.

| # | Must never hold | SEBI reference | What happens if it does |
|---|---|---|---|
| 1 | Client identifiers (names, PAN, account numbers, portfolio values, contact details) | — (general PII/segregation discipline) | Turns a general task tracker into a client-record system with no compliance apparatus built for it |
| 2 | Investment reasoning behind any decision | **PMS Reg 27(1)(e)** — records "in support of every investment transaction or recommendation," proviso requires custody "under the hands of the Principal Officer" | The punch note becomes a Reg 27(1)(e) record: **5-year preservation**, producible on SEBI inspection under Reg 35, and required to be in the Principal Officer's custody specifically — which an append-anything-by-any-employee log structurally is not and cannot become |
| 3 | Client complaints | **PMS Reg 11(d)** / **24(10)** | The tool becomes the firm's SEBI complaints register, with SCORES reporting obligations attached |
| 4 | Evidence that a client report or client-wise account was produced, checked, or sent | **PMS Regs 30–31**, both inside the same Chapter IV (Regs 21–34) that Reg 29 preserves for 5 years | A ticket that merely *evidences* a deliverable existing is itself inside the preserved set — tickets may reference that a deliverable exists, never its content or sign-off |
| 5 | Client correspondence, **if the firm holds Research Analyst registration** | **RA Reg 25(1)(vii)**, added 16-Dec-2024 | Wider than #2 — captures client-facing correspondence generally, and lets SEBI specify how it must be kept |

**Why this is five categories and not the "three" some earlier notes mention:** `DESIGN.md` §8.2 records a correction made during an adversarial verify pass — an earlier draft described the preserved set as "a closed enumeration," which was wrong and gave false comfort. Reg 29 preserves everything by *subject matter* across the whole of Chapter IV, not a short list. A ticketing tool used by an APM at an NDPMS house plausibly touches categories 3 and 4, not only 2. The widened scope in `REQUIREMENTS.md` §8 reflects that correction; do not revert to the three-category framing.

**What this does *not* buy**, and a successor should not assume otherwise: staying out of these five categories does **not** put the app outside SEBI's cybersecurity framework (CSCRF). CSCRF scope follows *what the system is used for* — a tracker whose tickets are about NDPMS/advisory deliverables is in scope whether or not client names appear in it. The realistic target, per `DESIGN.md` §8.5, is **in scope, classified non-critical** — a different and lesser set of obligations, not an exemption.

**Structural reinforcement, current as of this build:** as of milestone M2, the Principal narrowed V1's scope to *general internal task tickets, not client-linked records* — so the schema (`db/migrations/0001_schema.sql`) has **no `client_ref` column at all**, and consequently no encryption, no key-management surface, no `dek_keyring` table. This is stronger than a policy: today the schema cannot hold a client reference even by accident. **A successor should understand what re-adding that field would cost**: it would not just reopen the SEBI-scope question above, it would reopen the entire encryption/key-management design in `DESIGN.md` §7 (KEK, per-employee DEK, rotation, crypto-shredding) that was deliberately removed as "the largest source of operational risk in the design — a lost or mis-rotated key makes data unrecoverable." Adding the field back means rebuilding the exact risk this handover document is about.

**Honest limitation, stated in `REQUIREMENTS.md` §8.6 and worth repeating here:** none of this is enforced by the software beyond the missing column. Nothing stops a person typing a client's name or the reasoning behind a trade into a free-text title or punch note. The mitigations are an inline warning (not yet confirmed built), the rule stated at first login, and an admin who can see and act on violations (once M8 admin exists). **The boundary is ultimately held by the people using the tool, not by the code**, and whoever introduces this tool to the firm needs to say that out loud, not assume the schema does the whole job.

---

## 4. Open decisions still needing the Principal

From `DESIGN.md` §11 and `REQUIREMENTS.md` §13, unresolved as of the last verified checkpoint:

| # | Decision | Why it matters |
|---|---|---|
| **0 / 5** | **What is Ionic Wealth's full SEBI registration set — Portfolio Manager, non-individual Investment Adviser, Research Analyst?** | **This should be resolved before anything else on this list**, and `DESIGN.md` calls it out as check 0 for exactly that reason: it is public information (`sebi.gov.in/intermediaries` for the registration category, APMI's disclosures for AUM), resolvable in minutes, and it determines the entire CSCRF obligation set. A non-individual Investment Adviser is a **Small-size RE by status, with no AUM threshold** — which is *worse* than a sub-₹3,000cr Portfolio Manager, because Small-size REs get no cyber-audit exemption that Self-certification REs get. Until this is pulled, whether the firm's obligation is VAPT-only or VAPT-plus-annual-audit-plus-PR.IP.S15-certification is genuinely undetermined, and every downstream compliance answer in `DESIGN.md` §8 is conditional on it. This is a fifteen-minute lookup that has been open since the design was written. |
| 1 | Do managers see all of their reports' tickets, or only the ones they personally assigned? | Changes the RLS policy materially — this is not a UI preference, it is a row-visibility rule enforced in the database |
| 2 | When to seek firm sanction for this tool | The build-then-demo sequencing is designed for, but 40+ people coming to depend on a tool the firm has not formally sanctioned is its own risk, independent of the technical one |
| 3 | Accept cleartext punch notes in exchange for working full-text search? | Design recommendation is yes, for V1 — encryption and search are in genuine tension (an encrypted column needs either full decrypt-on-every-query or a blind index that leaks what it indexes) — but this is recorded as a recommendation, not a decision made |
| 4 | Repo under a company GitHub account, or the author's personal one? | Recommendation is company, from the first commit — retrofitting ownership later is awkward. See §2 row 1: as of this writing the code is not committed *anywhere*, so this decision is now blocking the very first commit, not a later migration |
| 6 | Is the firm onboarded to SEBI's Market SOC? | Every CSCRF self-certification/small-size exemption (including the encryption-at-rest relief this app already exceeds voluntarily) is conditional on Market SOC onboarding per circular 2025/60 (30-Apr-2025), clauses 2.2/2.6/2.7/3 — nobody has read that circular yet |
| 7 | Does adopting Entra ID SSO, or moving storage into the company's M365 tenant, pull this app into CSCRF audit scope as a "connected system"? | The natural graduation path away from the current Cloudflare/Supabase stack runs directly into this question, and `DESIGN.md` §8.5 says explicitly: "a compliance officer should answer this, not a developer" |

---

## 5. Inventory — what is done, what is not, what is deliberately excluded

### Done and verified (per `PROGRESS.md`'s own verification claims)

| Milestone | What | Verification claimed |
|---|---|---|
| M0 | Node/npm toolchain, user-local, no admin | `node --version` / `npm ping` confirmed |
| M1 | Domain core — calendar/IST maths, ticket transitions, hash chain | 107 tests, `tsc --noEmit` clean |
| M2 | Schema + RLS + append-only enforcement (PGlite) | 152 tests (107 + 45 database) |
| M3 | Repository seam — Postgres + in-memory, one contract suite over both | 206 tests |
| M3+M4+M5 (logic) | Auth (Cloudflare Access JWT verification), core service rules | 342 tests, `tsc`/`next build` clean, app runs |
| M5 | Tickets/punches/deadline UI routes, server actions | 349 tests, end-to-end RLS proof from real HTTP requests (own ticket → 200, someone else's → 404, nonexistent → 404, indistinguishable) |
| M6 | Team board, stale flagging, category picker | 363 tests |
| M7 | Reports, CSV/Excel export, on-time-vs-original-deadline metric | **409 tests**, `tsc` clean, `next build` clean, 7 routes serving |

### Not done

| Milestone | What | Status |
|---|---|---|
| M8 | Admin — users, roles, holiday calendar, half-yearly access review, audit-log viewer with chain verification | Not shipped as of the last verified checkpoint. (Note: database migrations and rules for some admin invariants — self-role-change prevention, no-hard-delete, deactivation-waits-for-handover — were observed present in the repository while this handover was being written; their completion and test status should be re-checked against the current `PROGRESS.md` before relying on them, since other work was visibly in progress concurrently with this document.) |
| M9 | Encrypted backup, daily chain anchor, access-event archival, restore drill | Not shipped as of the last verified checkpoint. Some related source files were observed present (`src/domain/anchor.ts`, `src/service/anchor-file.ts`) while this document was being written — again, confirm current status against `PROGRESS.md` rather than this document, which reflects a point in time. |
| M10 | Rate limiting, CSP/security-header hardening beyond what `next.config.ts` already sets, Dependabot | Not shipped as of the last verified checkpoint |
| M11 | Deploy — Supabase project, Cloudflare Access application, the four §9 pre-build checks, a real pilot with three colleagues over two weeks | Not started. This is the dependency behind mitigation #3 (§2) and the entire "Recurring obligations" calendar in `RUNBOOK.md` §5 being currently unactionable rather than merely undone. |
| — | The four handover mitigations themselves (§2) | Zero of four complete |

### Deliberately excluded — do not add these without re-opening the design

Named in `REQUIREMENTS.md` §11 so they do not creep back in through a well-meaning feature request: client-facing access · sales pipeline / leads / deals · billing or invoicing · timesheets for payroll · Gantt charts · task dependencies and parent/child hierarchies · a custom workflow builder · file attachments in V1 (links only) · threaded comments (the punch record *is* the conversation, by design) · integrations beyond a single outbound webhook · multi-tenancy · anything AI-flavoured · a `client_ref` field or any client-linked record (§3 above) · an application-level session layer (identity is re-asserted per request from the Access JWT — see `DESIGN.md` §3) · any integration, data feed, or shared credential with a SEBI-purview system (the segregation rule in `DESIGN.md` §8.5 that keeps this tool classified non-critical).

If a future request looks like it is asking for one of these "just this once," the correct response is to reopen `REQUIREMENTS.md`/`DESIGN.md` and record a new decision — not to quietly build it into a punch note or a free-text field.
