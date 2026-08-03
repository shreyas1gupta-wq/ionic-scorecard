# IONIC_CRM — Implementation Plan

**Companions:** `REQUIREMENTS.md` (what) · `DESIGN.md` (how) · `PROGRESS.md` (state)
**Date:** 2026-08-03

Each milestone states its **verification** — the command or observation that proves it is done. "It looks right" is not verification. Milestones marked **⛔ needs your accounts** cannot be completed by me; everything else can.

---

## Ordering principle

Build inward-out: **pure logic first, database guarantees second, UI last.** The reason is specific to this project — the properties that matter (append-only, tamper-evidence, correct deadline maths, row isolation) all live below the UI, and all of them are testable without a browser, a server, or a single account. If those are wrong, no amount of UI work matters. If they are right and proven, the UI is mechanical.

---

## M0 — Toolchain ✅ DONE

Node **v24.18.1** + npm **11.16.0** installed user-local at `%LOCALAPPDATA%\nodejs`, registered on the user PATH. No admin rights used. npm registry reachable through the corporate proxy (PONG ~1.5s).

Notes for reproducing on another machine: the MSI installer is unnecessary — the official zip extracted with `tar.exe` works and takes ~35s. `Expand-Archive` takes over five minutes on this file; do not use it. The proxy truncates long transfers and does not support byte-range resume, so download with retries and **gate on the published SHA-256** rather than trusting a completed-looking file. My first attempt produced a 35.45 MB file that failed its checksum.

**Verification:** `node --version` → `v24.18.1`; `npm ping` → PONG. ✅

---

## M1 — Domain core, zero infrastructure

Pure TypeScript. No database, no network, no framework. This is where the rules in `REQUIREMENTS.md` §4–§5 become code.

- Working-day arithmetic against an injected holiday set (never a global or an API call)
- `isOverdue`, computed from a passed-in "today" so it is testable and has no midnight bug
- Stale detection per priority (P1/P2/P3 thresholds)
- On-time evaluation against **both** original and current deadline
- Ticket reference generation (`TKT-2026-0001`)
- Status-transition validation — which moves are legal, and by which role
- The hash-chain functions: `computeRowHash(prev, fields)` and `verifyChain(rows)`, with the exact canonical serialisation from `DESIGN.md` §6

**Verification:** `npm test` green, with tests that specifically cover: a deadline landing on a Saturday; a deadline landing on a holiday; IST date boundaries around midnight UTC; every illegal status transition rejected; a chain with one row's payload altered detected; a chain with a middle row deleted **and resequenced** still detected.

That last test is the one that matters. If deleting a row and renumbering goes undetected, §6 is decorative.

---

## M2 — Schema and database-level guarantees

SQL migrations, tested against **PGlite** (Postgres compiled to WASM — real Postgres, no server, no install, no admin rights). If PGlite turns out not to support role switching well enough to prove RLS, this milestone falls back to a Supabase branch database and becomes ⛔.

- All nine tables from `DESIGN.md` §4
- `REVOKE UPDATE, DELETE` on `status_updates` and `audit_log` from every role including `service_role`
- The `forbid_mutation()` trigger as second layer
- `original_deadline` immutability trigger
- RLS policies for employee / manager / admin, with `FORCE ROW LEVEL SECURITY`
- Audit-log insert as a `SECURITY DEFINER` function; no role holds direct `INSERT`

**Verification:** a test suite that, for each of `anon`, `authenticated` and `service_role`, attempts `UPDATE` and `DELETE` on `status_updates` and asserts failure — six assertions, all of which must fail loudly. Plus: employee A cannot `SELECT` employee B's ticket; a manager can see a report's ticket; an admin sees all; an attempt to modify `original_deadline` raises.

---

## M3 — App shell and the repository seam

Next.js + shadcn/ui. Lift layout and data-table patterns from `Kiranism/next-shadcn-dashboard-starter` (MIT) and **strip Clerk** — we are not using it.

The important artefact is the **repository interface** from `DESIGN.md` §2. Two implementations from day one: the Postgres adapter, and an in-memory fake used by tests. If the fake is painful to write, the interface is wrong.

**Verification:** `npm run build` succeeds; the app boots locally; every domain test from M1 runs against the in-memory fake with no database present.

---

## M4 — Authentication

- Cloudflare Access JWT verification against the team certs endpoint, **failing closed**
- Email → `employees` row resolution; reject unless `status = ACTIVE`
- A **local-dev identity shim** so development works without a Cloudflare account, gated behind an env var that cannot be set in production
- `workers_dev = false` in `wrangler.toml`

**Verification (doable now):** unit tests for a missing token, an expired token, a wrong-audience token, a valid token for a non-allow-listed email, and a valid token for a `DEACTIVATED` employee — all rejected. The production build must fail to start if the dev shim env var is set.

**⛔ Verification (needs your accounts):** end-to-end OTP on `*.pages.dev`; the `workers.dev` URL returning non-200. These are checks 3 and 4 in `DESIGN.md` §9.

---

## M5 — Tickets, punches, deadline control

The core write paths. Every one goes through the repository and writes an audit entry.

- Ticket create / read / reassign-with-handover-note / cancel-with-reason
- **Punch insert** — the append-only path, with the "note required when Blocked" rule
- Correction punches referencing the punch they correct
- Deadline-change request → manager approval → applied, with the preceding-punch rule enforced **server-side**

**Verification:** integration tests proving a deadline change is rejected when no punch precedes it; a punch cannot be inserted with `actor_id` spoofed to another employee; a correction never mutates the original row.

---

## M6 — Views · M7 — Reports and export · M8 — Admin

`REQUIREMENTS.md` §6, §7, §9. Mechanical once M1–M5 hold.

Two things not to lose in the mechanical work: **mobile-responsive punching** (if it is awkward on a phone, people stop punching and the tool dies), and the **half-yearly access review recording that it happened** — the CSCRF obligation is the review, and the evidence is the audit entry.

**Verification:** reports cross-checked against hand-computed fixtures; export opens cleanly in Excel with dates as dates, not text.

---

## M9 — Backup, chain anchor, restore drill

- Scheduled `pg_dump` → `age` encryption → private GitHub repo + R2
- Daily chain root hash committed alongside it — this is what makes §6 meaningful against a privileged insider
- Documented restore procedure with **key escrow** so recovery survives your departure

**Verification:** a restore actually performed into a scratch database, and the row counts and the chain verification both pass on the restored copy. A backup that has never been restored is not a backup.

---

## M10 — Rate limiting and hardening

CSCRF requires *"rate limiting, throttling, and proper authentication and authorisation mechanisms"*. Cloudflare WAF rules plus per-route limits in the Worker. Security headers, CSP, Dependabot.

**Verification:** a script that exceeds a route's limit and gets throttled.

---

## M11 — ⛔ Deploy and pilot

Needs your Cloudflare and Supabase accounts, and the four §9 checks passing first.

Then: **three colleagues, two weeks, real tickets.** This row is not padding. Real users will find the ambiguities in the status workflow that neither of us can see from here — that is the entire point of a pilot, and it is where internal tools live or die.

---

## M12 — Handover and succession

The mitigation for the highest-severity non-technical risk in `DESIGN.md` §10: you are the single point of failure.

- README that a competent stranger can deploy from
- Repo under a **company** GitHub account, not a personal one
- **One colleague who has deployed it once**, before anyone needs them to
- Key escrow documented and tested

**Verification:** a colleague deploys to a scratch environment following only the README, with you not in the room.

---

## What I can do before you touch anything

M1, M2, M3, M5, M6, M7, M8, M10 and most of M4 need no accounts. That is the large majority of the build, and all of the parts where correctness is load-bearing.

What genuinely waits on you: the four §9 checks, then M11.

---

## Sequencing note

`DESIGN.md` §9's four checks are cheap now and expensive later, but they gate **deployment**, not development. If check 1 (Supabase Mumbai on free) or check 2 (Access seat count) fails, the fallbacks are already designed — a different region with the limitation documented, or the retained credentials-plus-TOTP auth design. Neither invalidates M1–M8. So there is no reason to wait.
