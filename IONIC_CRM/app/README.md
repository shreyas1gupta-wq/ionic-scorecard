# IONIC_CRM

Internal ticket and status-tracking web app for Ionic Wealth's ~10–50 employees. Work gets a deadline, the person doing it records progress over time, and managers see the true state of everything without asking anyone. It is not a client-facing tool, not a sales CRM, and by design it must never hold client identifiers, investment reasoning, or client complaints — see `IONIC_CRM/HANDOVER.md` before adding any field that might change that.

**The one property everything else rests on: a status punch, once written, cannot be edited or deleted — by anyone, including an admin.** Corrections are new punches that reference the one they correct; the original stays visible. This is enforced in the database (privilege revokes plus triggers, `db/migrations/0002_append_only.sql`), not merely by application code, and is hash-chained so a deletion-and-renumbering attempt is detectable (`src/domain/hash-chain.ts`, `DESIGN.md` §6). If you find yourself adding a way to edit or delete a punch, stop — that would remove the reason this system exists.

For the full design reasoning (architecture, auth, data model, compliance posture, open risks) read `IONIC_CRM/DESIGN.md`. For what the system must do, `IONIC_CRM/REQUIREMENTS.md`. For build history and the mistakes made along the way, `IONIC_CRM/PROGRESS.md`. This README is only about getting a working copy running.

---

## 1. Prerequisites

- Windows, no admin rights required anywhere in this procedure.
- A corporate proxy that allows outbound HTTPS to `nodejs.org` and the npm registry. The npm registry has been confirmed reachable through the proxy (`npm ping` → PONG, ~1.5s). Large single-file downloads over this proxy are the one thing to watch — see below.

### Installing Node without admin rights

The version verified on this build is **Node v24.18.1 / npm 11.16.0**, installed user-local, not through the Windows installer (which needs admin).

1. Download the official Windows zip for the version you need from `https://nodejs.org/dist/v24.18.1/node-v24.18.1-win-x64.zip`, and download `https://nodejs.org/dist/v24.18.1/SHASUMS256.txt` alongside it.
2. **Verify the checksum before extracting anything.** The corporate proxy has been observed to truncate a long download without erroring and without supporting byte-range resume — one attempt produced a plausible-looking 35.45 MB file that silently failed its checksum. Extracting an unverified archive is how a subtly-corrupt Node install gets built and debugged for an hour before anyone suspects the download.

   ```powershell
   Get-FileHash node-v24.18.1-win-x64.zip -Algorithm SHA256
   # Compare the output against the matching line in SHASUMS256.txt.
   # If it does not match: delete the file and download again — do not extract it.
   ```

3. Extract with `tar.exe` (ships with Windows 10/11, no admin needed), **not** `Expand-Archive` — `Expand-Archive` has been measured taking over five minutes on this archive, against roughly 35 seconds for `tar.exe`:

   ```powershell
   tar.exe -xf node-v24.18.1-win-x64.zip
   ```

4. Move (or leave) the extracted `node-v24.18.1-win-x64` folder somewhere permanent — the verified location on this build is `%LOCALAPPDATA%\nodejs` — and add it to your **user** PATH (Control Panel → Environment Variables → User variables, no admin needed):

   ```powershell
   [Environment]::SetEnvironmentVariable('PATH', "$env:LOCALAPPDATA\nodejs;$env:PATH", 'User')
   ```

5. Open a new shell and confirm:

   ```powershell
   node --version   # v24.18.1
   npm --version    # 11.16.0
   npm ping         # PONG
   ```

   If `npm` appears to fail in PowerShell with a nonzero exit code but the output looks fine, check the actual text before concluding it failed — npm writes routine notices to stderr, which PowerShell can report as an error exit even on success.

---

## 2. Getting the app running

```powershell
cd app
npm install
copy .env.example .env.local
npm run dev
```

`npm run dev` is ready in a couple of seconds. Open the URL it prints (Next.js dev server).

### `.env.local`

Copy `.env.example` and keep the two development-identity variables set — they are what let the app run with no Cloudflare account:

```
CRM_ALLOW_DEV_IDENTITY=1
CRM_DEV_IDENTITY_EMAIL=alice@ionic.in
```

This is a genuine authentication bypass, so it is guarded three ways in `src/auth/config.ts`, the last of which is: **the app refuses to boot if either variable is set while `NODE_ENV=production`.** Do not try to work around that — see `IONIC_CRM/DESIGN.md` §3 for why an app-level session was rejected in favour of this shim plus Cloudflare Access in production.

Never commit `.env.local`. `.gitignore` blocks `.env*` except `.env.example` for exactly this reason.

### Seeded development accounts

Switching `CRM_DEV_IDENTITY_EMAIL` changes who you are signed in as. Seeded in `src/server/db.ts`:

| Email | Role | Notes |
|---|---|---|
| `admin@ionic.in` | ADMIN | |
| `manager@ionic.in` | MANAGER | manages alice and bob |
| `alice@ionic.in` | EMPLOYEE | reports to manager |
| `bob@ionic.in` | EMPLOYEE | reports to manager |

Seed tickets are deliberately chosen to cover the states that are easy to get wrong: a healthy ticket, an overdue one, a stale one (in progress but silent long enough to trip its priority's threshold), and one never touched since it was raised.

---

## 3. The two dev store modes

The server picks a repository implementation at startup (`src/server/db.ts`). Production is not wired yet (milestone M11 — needs a Supabase project; see `IONIC_CRM/DESIGN.md` §9 and `IONIC_CRM/RUNBOOK.md`), so in development you choose between:

| Mode | How | What it is | When to use it |
|---|---|---|---|
| **memory** (default) | nothing to set | An in-memory fake enforcing the same rules in TypeScript | Day-to-day UI and logic work. Starts instantly, costs almost no RAM. |
| **pglite** | `CRM_DEV_STORE=pglite` | A real PostgreSQL compiled to WebAssembly, running the actual migrations and the actual RLS policies, persisted to `.pgdata/` | Any change to a migration or an RLS policy |

```powershell
$env:CRM_DEV_STORE = "pglite"
npm run dev
```

**The honest limitation, stated plainly: the in-memory store cannot catch an RLS mistake.** It enforces authorization rules by re-implementing them in TypeScript — that's what `src/repo/contract.test.ts` exists to keep honest — but it has no SQL policy engine underneath it. If you change something in `db/migrations/`, particularly `0003_rls.sql`, the in-memory store will happily keep passing while the real database silently does something different. Run in `pglite` mode, or at minimum run `npm run test:db` and `npm run test:repo`, before trusting any policy or migration change.

`memory` is the default because it was measured, not assumed: on the development machine (2.3 GB free of 15.6 GB), loading PGlite inside the Turbopack dev server exhausted V8's allocator outright (`Fatal process out of memory: Zone`). A contract-verified fake that costs nothing was the better trade for the everyday loop.

---

## 4. Running tests

```powershell
npm test          # four separate processes — see below
npm run test:all  # everything in one process — faster, needs a machine with room
npm run typecheck # tsc --noEmit
npm run check     # typecheck && test && build
```

`npm test` runs `node scripts/test-all.mjs`, which launches four **separate vitest processes** in sequence (unit, database schema, repository contract, service rules) rather than one. This is deliberate, and worth understanding before "optimising" it away:

- Each database-backed suite loads a whole PostgreSQL compiled to WebAssembly (PGlite). PGlite reserves a large contiguous memory region, and **on Windows that counts against system commit charge, not just physical RAM** — a machine can show several gigabytes of free RAM and still fail, because commit charge is the actual constraint. The development machine showed 3.5 GB free RAM but only 1.8 GB free commit, and two suites back-to-back failed while each passed alone.
- The failure does **not** look like an out-of-memory error. It presents as `Fatal process out of memory: Zone` immediately followed by `ERR_IPC_CHANNEL_CLOSED` — the second message reads like a broken pipe or IPC bug, and chasing it as one will cost you the length of time it took to write this paragraph, twice over.
- Running suites as separate `npm run` scripts chained with `&&` makes it worse, not better: each nested `npm run` keeps its own long-lived node process alive for the duration of its child, adding to the same commit-charge pool. `scripts/test-all.mjs` spawns `npx vitest run <args>` directly for this reason, with a short pause between suites so Windows can reclaim commit charge before the next one starts.
- `scripts/test-all.mjs` also distinguishes **"could not run: out of memory"** from **"failed"** in its output — both exit non-zero, and conflating them sends you hunting for a bug that does not exist.

If `npm test` reports a suite could not run, close other memory-heavy applications and re-run, or run the affected suite alone (`npm run test:db`, `npm run test:repo`, `npm run test:service`). On a machine with more room, `npm run test:all` runs everything in one process and is simply faster.

`vitest.config.ts` also sets `fileParallelism: false` for the same underlying reason — running test *files* in parallel multiplies the same PGlite heaps within a single vitest invocation. Do not remove it as an "optimisation" without re-reading the comment above it.

As of the last verified run (`IONIC_CRM/PROGRESS.md`, milestone M7): **409 tests passing** (202 unit — domain + auth; 45 database schema; 112 repository contract; 50 service rules), `tsc --noEmit` clean, `next build` clean, 7 routes serving. Later milestones (M8 admin, M9 backup/restore) may have changed this count since — check `IONIC_CRM/PROGRESS.md` for the current state before relying on a specific number.

---

## 5. Project layout

```
app/
├── src/
│   ├── domain/    pure logic — no IO, no database, no framework
│   ├── auth/      Cloudflare Access JWT verification, dev-identity shim, config guards
│   ├── repo/      the repository seam — see below
│   ├── service/   business rules + audit, built on top of the repo seam
│   └── server/    per-request wiring: repository factory (db.ts), session (session.ts)
├── app/           Next.js routes (App Router) — the only layer that knows about HTTP
├── db/migrations/ SQL, applied to both PGlite (dev) and Postgres (production)
└── scripts/       test-all.mjs (see §4)
```

The dependency direction is one-way: **`domain` → `repo` → `service` → `app/`**. Nothing in `domain` imports anything below it; nothing in `repo` knows the rules in `service`; the Next.js routes in `app/` are the only place that reads a request or renders HTML.

- **`src/domain`** — IST date and working-day arithmetic (`calendar.ts`), the ticket status-transition table and overdue/stale logic (`tickets.ts`), the hash-chain functions (`hash-chain.ts`), reference generation (`ticket-ref.ts`), report math (`reports.ts`), CSV formula-injection defence (`csv.ts`). All of it is pure — no database, no clock read directly, no network — which is why it can be tested with hand-worked fixtures alone.
- **`src/repo`** — `types.ts` defines the ports (`TicketStore`, `AuditStore`, etc.) and the two error types every implementation must throw the same way. `postgres.ts` and `memory.ts` are the two implementations. `contract.test.ts` is **one suite of rules run against both** — currently 49 rules × 2 implementations = 98+ tests. This is what makes the in-memory fake trustworthy rather than merely convenient: a fake whose behaviour is *believed* to match the database is worse than no fake at all, because it makes the fast tests green while the real thing refuses. Divergence between the two implementations fails here, in a few seconds, instead of in production.
- **`src/service`** — where rules live that need more than one repository call to express correctly: a status change and its punch are one operation; a deadline cannot move until at least one punch exists; a reassignment's handover note is itself recorded as a punch. Every write here also appends to the audit chain.
- **`app/`** — Next.js routes and server actions. Server actions (`app/tickets/actions.ts`) are the only write path from the browser: each authenticates via `requireUser()`/`withUser()` (`src/server/session.ts`), runs inside a transaction with RLS in force, delegates the actual rule to `src/service`, and records an access event. None of them accept an actor id from the client — identity always comes from the verified request.

**Why the seam matters in practice:** if the data store ever has to move — into the company's M365 tenant, onto a different Postgres host, or because a compliance circular changes what's allowed — the work is a new implementation of `src/repo/types.ts`'s interfaces, not a rewrite of the application. Two design rules make this real rather than ceremonial (see the comment at the top of `src/repo/types.ts`): identity is bound once, at construction (`withActor`), so there is no code path that can forget to authorise; and the actor object carries an id and **no role** — role is always re-read from the store, so a caller can never simply assert "I am an admin".

---

## 6. The `node_modules` junction

`node_modules` lives outside this repo's OneDrive-synced folder, at `%LOCALAPPDATA%\ionic_crm\node_modules`, with a **Windows junction** left in this folder pointing to it. This was necessary because `node_modules` is tens of thousands of small files, and while it is `.gitignore`d, **gitignore does not stop OneDrive from trying to sync it** — left in place, it thrashes OneDrive sync continuously.

A Windows junction (not a symlink) was chosen because it needs no admin rights and OneDrive does not follow reparse points, so the real `node_modules` is invisible to OneDrive entirely.

### To recreate it on a fresh checkout

```powershell
# From the app/ directory:
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\ionic_crm\node_modules" | Out-Null
# If node_modules already exists here as a real folder (e.g. after `npm install`
# before setting this up), delete it first — do not try to merge into a junction.
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
New-Item -ItemType Junction -Path node_modules -Target "$env:LOCALAPPDATA\ionic_crm\node_modules"
npm install
```

(`cmd /c mklink /J node_modules "%LOCALAPPDATA%\ionic_crm\node_modules"` is the equivalent if `New-Item -ItemType Junction` is unavailable.)

### To undo it

```powershell
Remove-Item node_modules   # removes the junction only, not its target's contents
Move-Item "$env:LOCALAPPDATA\ionic_crm\node_modules" node_modules
```

**Verify which one you have before trusting either procedure**, especially if something else has touched this checkout recently:

```powershell
fsutil reparsepoint query node_modules
# "The file or directory is not a reparse point." -> it is currently a REAL folder, not a junction.
# Anything else printed -> it is a junction; the target is inside the output.
```

If `node_modules` is a real folder when you expected a junction (or vice versa), do not assume the mechanism above is currently in effect — check first, because a plain `npm install` run against a broken or missing junction will silently recreate `node_modules` as an ordinary folder inside OneDrive, which is the exact problem this section exists to avoid.
