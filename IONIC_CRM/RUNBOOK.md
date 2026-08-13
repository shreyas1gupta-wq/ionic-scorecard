# IONIC_CRM — Runbook

Operating instructions for whoever is running this tool, whether or not they built it. Companion to `app/README.md` (how to get a working copy running) and `HANDOVER.md` (the succession position). Section numbers below (§8, §9, §10) refer to `DESIGN.md` unless stated otherwise.

**Status check before reading further:** as of `PROGRESS.md`'s last update, milestones M0–M7 are built and verified (409 tests, `tsc` clean, `next build` clean, 7 routes). **M8 (admin), M9 (backup/restore/chain anchor) and M10 (rate limiting/hardening) are not yet built**, and **M11 (deploy) has not happened** — there is no production database, no live Cloudflare Access application, and no Supabase project. Large parts of this runbook therefore describe the procedure to follow *once those milestones land*, not something you can run today. Each section says which applies.

---

## 1. Deploy procedure

**Not yet operable.** `src/server/db.ts`'s `getRepositories()` throws `NotConfiguredError` if `NODE_ENV=production`, on purpose — there is no production database adapter wired yet (milestone M11). `.env.example` marks `CRM_DATABASE_URL` as "not yet wired". Do not attempt a production deploy until M11 is built and the checks below have passed.

### What M11 will need

| Item | Detail |
|---|---|
| Supabase project | Pinned to **`ap-south-1` (Mumbai)** — `DESIGN.md` §2.1. This is not a legal requirement today (CERT-In's residency reading was found to be wrong; see `DESIGN.md` §2.1 and §8.1), but it is the position recorded and the one to keep unless a Principal decision changes it. |
| Worker secrets (never in `wrangler.toml`, never in `.env` files that get committed) | `CRM_ACCESS_TEAM_DOMAIN`, `CRM_ACCESS_AUD`, `CRM_DATABASE_URL` — set with `wrangler secret put <NAME>`, one at a time |
| `wrangler.toml` `[vars]` | Only `NODE_ENV = "production"` belongs here in plain text. Anything else added to `[vars]` is visible in the dashboard and in this repo — it is not a place for anything secret. |

### Pre-build checks — `DESIGN.md` §9, and **check 0 first**

Run these before wiring anything. Each is cheap now; each is expensive to discover after users depend on the tool.

| # | Check | Why it comes first / matters | Est. time |
|---|---|---|---|
| **0** | **Pull Ionic Wealth's full SEBI registration set** (`sebi.gov.in/intermediaries` — Portfolio Manager / Investment Adviser / Research Analyst lists) and AUM from APMI's disclosures | **Do this before any of the others.** It determines the CSCRF bucket (self-certification vs small-size vs something worse), and therefore whether the firm's obligation is VAPT-only or VAPT-plus-annual-audit-plus-PR.IP.S15-certification. Every other compliance answer in this document is conditional on it, and it is public information resolvable in minutes — see `HANDOVER.md` for why this is still open. | 15 min |
| 1 | Create a throwaway Supabase free project; confirm **South Asia (Mumbai) `ap-south-1`** is actually selectable on the **Free** plan | Docs do not plan-gate regions in writing; unconfirmed from inside the UI at time of writing | 3 min |
| 2 | Cloudflare Zero Trust dashboard → billing → read the **current free seat entitlement** | Sources conflict (50 seats vs "no limit"); overage **blocks users at login**, it does not bill you — this is the one number that could break the whole plan for 10–50 people | 2 min |
| 3 | Stand up a stub on `*.pages.dev`, enable Access One-Time-PIN, confirm end-to-end: an allow-listed address receives a PIN **and lands in an `@ionic.in` inbox, not Junk**; a non-allow-listed address is refused | This is the entire authentication model for the app | 15 min |
| 4 | Confirm `workers_dev = false` actually takes effect: the `<name>.<subdomain>.workers.dev` URL returns a non-200 | See §2 below — this is the back-door check | 10 min |

**Fallbacks, already designed, if a check fails:** if check 1 fails, use the nearest available Supabase region with the residency limitation documented, or a self-hosted Postgres on a Mumbai VM. If check 2 shows fewer than the required seats, fall back to the retained admin-issued-credentials-plus-TOTP auth design (`DESIGN.md` §3, "second position") rather than Cloudflare Access.

---

## 2. The `workers_dev = false` rule

**This is the single highest-severity item in the entire design** (`DESIGN.md` §10 lists it as Critical, above every compliance risk).

Cloudflare Access enforces authentication on a **hostname**. A Cloudflare Worker is *also* reachable at `<name>.<subdomain>.workers.dev` by default, and that URL does **not** pass through Access. If that route is left enabled, the entire authentication layer is bypassed — not by a sophisticated attack, but by a URL that is trivially discoverable.

Three independent layers exist, and all three must hold at once — this is not a "pick one" situation:

1. **`workers_dev = false`** in `app/wrangler.toml`. It is already set, with a large comment above it explaining exactly this. **Never set it to `true` "to quickly test something."** Use a preview deployment behind the same Access policy instead.
2. **The JWT check fails closed.** No valid Access JWT → 403, no body. This is application code (`src/auth/access.ts`, `src/auth/identity.ts`) and is covered by the unit tests in `src/auth/auth.test.ts` (missing token, expired token, wrong audience, wrong issuer, tampered payload, `alg: none`, algorithm confusion, a token minted for a different Access application in the same Cloudflare team).
3. **An automated test that hits the live `workers.dev` URL and asserts a non-200 response.** This is check 4 in the pre-build checklist above (`⛔` in `PLAN.md` M4 — it needs a live deployment, so it cannot run before M11).

**Operationally:** after every deploy, before telling anyone the tool is live, hit the `workers.dev` URL yourself and confirm it does not serve the app. Do this every time, not just the first time — a future `wrangler.toml` edit that touches `[triggers]` or `[assets]` is a plausible place to accidentally revert this line.

---

## 3. Onboarding a person

**Current state: no admin UI exists yet.** `REQUIREMENTS.md` §9 specifies "admin adds the person's work email to the allow-list; first login emails a one-time PIN; there is no password to issue, store, reset or forget" as the intended flow, but milestone M8 (admin — users, roles, holiday calendar, audit-log viewer) had not shipped as of the last verified `PROGRESS.md` checkpoint. Until M8 ships with an admin screen for this, the allow-list **is** the `employees` table, and adding someone means inserting a row directly.

The authorization surface is deliberately narrow — `db/migrations/0004_identity.sql`'s `app.resolve_identity(email)` is the **only** pre-authentication query in the system, returns at most one row, and only for `status = 'ACTIVE'`. Whoever runs this insert is the allow-list, in practice.

| Step | Detail |
|---|---|
| 1 | Confirm the person's exact work email (`@ionic.in`) — `work_email` is unique and case/whitespace-normalized (`lower(trim(...))` in `app.resolve_identity`) |
| 2 | Insert into `employees`: `work_email`, `display_name`, `role` (`EMPLOYEE`/`MANAGER`/`ADMIN`), `manager_id` (if `EMPLOYEE` or `MANAGER` reporting to someone) |
| 3 | If production Cloudflare Access is live: confirm their email is also on the Access application's allow-list policy — **two separate allow-lists exist** (Cloudflare Access decides who gets a PIN at all; `employees.status = 'ACTIVE'` decides who the app recognises once they arrive) and both must include the person |
| 4 | First login: they get emailed a one-time PIN by Cloudflare's own infrastructure. No password is set, stored, or communicated by you. |
| 5 | Confirm they can see `/tickets` and it shows their own view correctly (own tickets; a manager also sees reports') |

Role changes are themselves meant to be audited (`REQUIREMENTS.md` §2: "nobody can change their own role"), and `db/migrations/0005_admin_guards.sql` is in progress at the database level to enforce that a person cannot alter their own `employees.role` row via trigger — check whether that migration has landed before relying on the rule being enforced anywhere other than by discipline.

---

## 4. Offboarding a person

**Never a hard delete** — `REQUIREMENTS.md` §9. A departed employee's tickets and punch history must remain intact and correctly attributed; deleting the row would break every punch and audit entry that names them as actor.

| Step | Detail |
|---|---|
| 1 | **Reassign their open tickets first.** `REQUIREMENTS.md` §9: "Open tickets must be reassigned before deactivation completes." Deactivating someone with open work still assigned to them leaves that work invisible to a live owner. |
| 2 | Set `employees.status = 'DEACTIVATED'` (with a reason, per `deactivated_reason`) rather than deleting the row. `deactivated_at` should be set to now. |
| 3 | **This takes effect immediately, with nothing else to remember.** `app.resolve_identity()` filters on `status = 'ACTIVE'` — the moment the row flips, the person's next request finds no identity and is rejected. There is no session to separately revoke on the app side (`DESIGN.md` §3: "no app session layer" — identity is re-asserted from the Access JWT on every request). |
| 4 | If production Cloudflare Access is live: also remove them from the Access application's allow-list, or use Access's *revoke user session* action, so their existing browser session (if any) is cut immediately rather than waiting for their next full re-authentication. Enabling seat-expiration at 1–2 months (`DESIGN.md` §3) is a safety net for this being forgotten, not a substitute for doing it. |
| 5 | If they held client-facing or sensitive tickets as raiser/watcher, confirm the handover note on any reassignment (step 1) actually says something useful to the new owner — a reassignment with an empty or perfunctory handover note defeats the point of requiring one. |

**Erasure requests:** the design is pseudonymisation, not deletion (`DESIGN.md` §7) — `display_name` becomes `Former employee #NNN`, email is nulled, the row id is kept so historical attribution stays intact. This machinery is specified but its build status should be confirmed against `PROGRESS.md` before promising it to anyone; do not assume it exists just because it is designed.

---

## 5. Recurring compliance obligations — calendar

These come from `DESIGN.md` §8's "Recurring obligations the tool must actively support" table, which applies under SEBI's CSCRF to **all** Regulated Entities, not conditionally. "Owner" below is a role, not a name, because no specific person has been assigned these in the documents read for this handover — assign a name before this calendar is operative.

| Obligation | Cadence | Owner (role) | What discharges it |
|---|---|---|---|
| Half-yearly access-rights and privileged-user review | **Every 6 months** | App admin | The `access_events`/user-list access-review report (`REQUIREMENTS.md` §9), plus an audit-log entry recording that the review happened and who did it — the review without that entry does not count, per `DESIGN.md` §8: "the half-yearly access review is the obligation people forget; making the tool *record that it happened* is worth more than the report itself." |
| Annual COOP review and recovery drill | **Annually** | App admin / whoever owns backups | A restore actually performed into a scratch database with row counts and chain verification checked (§6 below) — a backup never restored is not a backup, and a drill never logged is not a drill |
| Cybersecurity and risk-management policy review | **Annually** | Firm compliance, informed by app admin | A dated review entry in this runbook or the firm's policy register — this is a review date, not a tool feature |
| Cyber-security training | **Annually** | Firm-level, outside this tool | Not built by this app; tracked at the firm level |
| User-access log retention — 2 years, ≥6 months queryable online, remainder archival | **Continuous** | App admin | The `access_events` table (build status: confirm against `PROGRESS.md` — specified in `DESIGN.md` §4 and §8 but not confirmed built as of the last read); 6 months hot in Postgres, remainder archived into the encrypted backup |
| Own authentication-event log | **Continuous** | App admin | Same table — Cloudflare Access free retains auth logs ~24 hours, Supabase retains ~1 day (auth ~1 hour), so **if the app does not write these rows itself, "who logged in, when" is unrecoverable after about a day** |
| Incident reporting — SEBI 6 h + 24 h; CERT-In 6 h | **On occurrence** | Named incident owner (not yet assigned in the documents read) | See §7 below |
| VAPT by a CERT-In empanelled auditor | Per CSCRF bucket, determined by check 0 above | Firm compliance | Firm-level; the exact scope this app falls into against Annexure-L is explicitly untested in `DESIGN.md` §8.5 — "the next document to fetch" |
| PR.IP.S15 in-house-software certification | Per major release, **if the app is in scope** | Firm compliance | All-REs-mandatory, not exempted for anyone; the one clearly unavoidable rupee cost if in scope — contingent on check 0 |
| API rate limiting and throttling | Continuous | App admin / whoever deploys | Cloudflare WAF rules plus per-route limits in the Worker — **milestone M10, not built as of the last verified `PROGRESS.md` checkpoint** |

### Incident reporting clocks — the specific numbers

| Regulator | First notification | Follow-up | Address / method |
|---|---|---|---|
| **SEBI** | **6 hours** | Full details on the SEBI Incident Reporting Portal within **24 hours** | `mkt_incidents@sebi.gov.in` |
| **CERT-In** | **6 hours** | — | Per CERT-In Directions 2022 reporting channel |

Both clocks run in parallel, not instead of each other — an incident notifiable under the CERT-In Directions is separately reportable to SEBI within its own 6-hour window.

---

## 6. Backup and restore

**M9 is outstanding.** `PLAN.md` specifies M9 as: scheduled `pg_dump` → `age` encryption → private GitHub repo + R2; a daily chain-root-hash commit alongside it; a documented and **tested** restore procedure. `PROGRESS.md`'s "NEXT STEP" section lists M9 immediately after M8 — as of the last verified checkpoint it had not been built. `wrangler.toml` already reserves the cron slots for it (`30 21 * * *` / `0 22 * * *` UTC — 03:00 / 03:30 IST) with a comment naming the intended jobs, but the jobs themselves are not confirmed implemented; check the actual Worker code, not just the cron comment, before relying on this.

This is **load-bearing, not optional** (`PROGRESS.md` D2): Supabase Free has no automated backups and no point-in-time recovery — free users are explicitly told to `pg_dump` themselves. Without M9, there is no backup at all.

### The key-escrow problem

The nightly backup is encrypted with `age` before it goes to GitHub — ciphertext in permanent git history is the point (D2: "permanence becomes an asset"), but only if the decryption key survives independently of any one person.

- `age` now has a post-quantum key format (`AGE-SECRET-KEY-PQ-1`) with keys far longer than one line, which changes paper-escrow mechanics, and interop with the `typage` library was `[UNVERIFIED]` at design time. **The design pins the backup to classic X25519 recipients** specifically so the key can be written down and escrowed simply — do not "upgrade" this without re-solving the escrow problem first.
- **Recovery must survive the author's departure.** A key that lives only on the builder's laptop, in the builder's head, or in a password manager only the builder has access to is not escrow — it is a single point of failure with extra steps. `DESIGN.md` §10 names "documented and tested key escrow" as one of the four mitigations for the single-point-of-failure risk, and `HANDOVER.md` records its status honestly: **not done.**
- Whoever finishes M9 needs to also decide and document *where* the second copy of the decryption key lives (sealed physical copy with the Principal, a second person's password manager, a firm safe) and then **prove it works** by having someone other than the builder use only that copy to decrypt a real backup.

### Restore drill

Not yet performed (it depends on M9 existing). When it is:

1. Restore the most recent encrypted backup into a **scratch** database — never restore-test against anything live.
2. Decrypt with the escrowed key (§ above), not a copy sitting on the builder's own machine — this is what proves escrow actually works, not just that a backup exists.
3. Confirm row counts match expectations for the source.
4. Run the chain verification (§7 below) against the restored copy and confirm it passes.
5. Log the drill's date and result — the annual COOP obligation (§5) is discharged by a logged drill, not by the backup mechanism existing unused.

**A backup that has never been restored is not a backup** — stated as the verification criterion for M9 in `PLAN.md`, and worth repeating here because it is the exact failure mode that goes unnoticed until the day it matters.

---

## 7. Incident response

**The trap to understand before anything else: *noticing* an incident is what starts the SEBI and CERT-In clocks, and an unmonitored app cannot notice.** This is recorded in `DESIGN.md` §8 and §10 as explicitly **a staffing gap, not a code gap** — no amount of correct code closes it if nobody is watching. Do not treat this section as complete just because the app's authorisation logic is sound.

### What to do first

1. **Establish what happened** before anything else — do not act on a guess. Check the audit log (`audit_log`, admin-only, via the audit viewer once M8 ships, or directly via SQL until then) and `access_events` for the relevant window.
2. **Do not delete or "clean up" anything** while investigating. The append-only design means the evidence you need is already preserved; touching it (even with good intentions) is the one action that could look like a cover-up later.
3. **Preserve the current chain state** — run chain verification (§8 below) and record the result *before* any remediation, so there is a timestamped "state as found."

### Who reports

Not yet assigned in the documents read for this handover. `DESIGN.md` §8 calls this out directly: incident reporting is "a written runbook and a named owner" — the runbook is this document; **the named owner is an open item**. Do not treat this runbook as sufficient on its own — a runbook with no one assigned to execute it discharges nothing.

### The two clocks (repeated from §5, because this is where it matters operationally)

- **SEBI:** 6 hours to `mkt_incidents@sebi.gov.in`, plus full portal details within 24 hours.
- **CERT-In:** 6 hours.

Both clocks are measured from when the incident is noticed or reasonably should have been noticed, not from when it occurred — which is exactly why "an unmonitored app cannot notice" is not a technicality. Until monitoring and a named on-call owner exist, the honest position is that these clocks cannot be reliably met, and that should be said to whoever is accountable for the firm's regulatory position rather than quietly assumed to be fine.

---

## 8. When the audit chain fails verification

The audit log is hash-chained (`DESIGN.md` §6): each row's `row_hash` incorporates the previous row's hash, so deleting or altering any row — even with careful renumbering — breaks the chain at the following row. `src/domain/hash-chain.ts`'s `verifyChain()` is what checks this; it is proven (not merely asserted) against: a deleted-and-resequenced row, tail truncation (detected only via an external anchor), and a full privileged rewrite (undetectable *internally*, detected only by the external anchor) — see `PROGRESS.md` M1.

**If verification fails:**

1. **Do not re-run it hoping for a different answer, and do not attempt to "repair" the chain.** A broken chain is evidence; a repaired chain is evidence destroyed. Preserve the database and the failing verification output exactly as produced.
2. Identify the failure point: `verifyChain()` reports `checked` (how many rows agreed) and `failures` (specifically where it stopped agreeing). The first failure is the boundary between "known-good" and "compromised or corrupted" — everything after it is suspect regardless of whether it individually re-hashes correctly.
3. **Check the external anchor.** `DESIGN.md` §6: each day's final `row_hash` is meant to be committed to the private GitHub backup repo, specifically so that even a privileged database administrator who rewrites history cannot also rewrite yesterday's git commit. Compare the last-known-good anchor against the current chain state. If the anchor confirms an earlier state that the live chain no longer matches, that is your proof of tampering (or, less alarmingly, of restoring from a stale backup — rule that out first). **Confirm the anchor-publishing job has actually been running** before relying on it — `src/domain/anchor.ts` / `src/service/anchor-file.ts` exist in the tree at time of writing but their build/verification status should be checked against the current `PROGRESS.md`, not assumed from their presence.
4. If no anchor exists for the relevant period (e.g., M9 was not yet built when the divergence occurred), the honest position is that you cannot distinguish "tampered" from "a bug in the writer" with certainty — say so, rather than asserting either.
5. Treat a genuine, unexplained chain break as an incident under §7, not merely a data-integrity bug — the whole reason the chain exists is that a break in it is a compliance-relevant event, not just an engineering one.

---

## 9. Common failure modes

| Symptom | Actual cause | Fix |
|---|---|---|
| Supabase project simply stops responding after roughly a week of no activity | **Supabase Free pauses projects after ~1 week of inactivity** (`DESIGN.md` §8.3). This is an **availability dependency, not something to optimise away** — a silent keep-alive that itself fails is worse than no keep-alive, because it hides the problem instead of surfacing it. | A daily keep-alive ping is the intended mitigation (`DESIGN.md` §10). Confirm it exists and — importantly — confirm something alerts if *the keep-alive itself* stops running, not just if the database is paused. |
| `Fatal process out of memory: Zone`, or a test run dies with `ERR_IPC_CHANNEL_CLOSED` | **Windows commit charge exhaustion, not a lack of physical RAM.** Each PGlite (WASM Postgres) instance reserves a large contiguous memory region that counts against Windows commit charge specifically. A machine can report several GB of free RAM and still fail if free *commit* is low — the development machine once showed 3.5 GB free RAM but only 1.8 GB free commit. `ERR_IPC_CHANNEL_CLOSED` in particular reads like a broken IPC pipe or a Vite bug, not a memory problem — that is exactly why it costs people time. | Do not chase this as a code bug. Close other memory-heavy applications, run test suites separately (`npm run test:db`, `npm run test:repo`, `npm run test:service` instead of `npm run test:all`), or just use `npm test` (`scripts/test-all.mjs`), which already runs suites as separate sequential processes with a gap between them for this reason. See `app/README.md` §4 for the full explanation. |
| A server action's form submission appears to silently fail — no error shown, but nothing happened either | **`redirect()` in a Next.js server action works by throwing** an error carrying a `digest` property. If the action's error-handling swallows every exception generically, a *successful* action that ends in a redirect gets misclassified as a failure. `app/tickets/actions.ts`'s `run()` helper explicitly re-throws anything with a `digest` string for this reason — see the comment directly above it. | If you are writing a new server action, check for `err.digest` before treating a caught exception as a real failure. If you're debugging one that seems to "fail silently," check whether it actually redirected and the "failure" is this exact miscategorisation. |
| `tsc --noEmit` fails on a type that `vitest` happily ran past | `esbuild` (which `vitest` uses to transform TypeScript) **strips types without checking them** — a genuinely broken type (a real example encountered: `readonly readonly T[][]`) can pass every test while being invalid TypeScript. | Green tests are not proof the types compile. Run `npm run typecheck` (or `npm run check`, which includes it) before trusting a change, not just `npm test`. |
| Development dashboard shows nothing as stale/overdue when you expected it to | Check the **seed data**, not the staleness logic first. Only `IN_PROGRESS`/`BLOCKED` tickets can go stale by design (an untouched `OPEN` ticket is a scheduling problem, not a reporting-discipline one) — a seed that leaves everything in `OPEN` will show nothing stale regardless of whether the logic is correct. `src/server/db.ts`'s dev seed deliberately includes a healthy ticket, an overdue one, a stale one, and a never-touched one for exactly this reason — if you've modified the seed, confirm it still covers all four states. | Re-check the seed's ticket statuses before assuming the domain logic (`src/domain/tickets.ts`) is wrong. |
| A CSV export opens in Excel with garbled non-ASCII names, or a cell renders as a clickable link/formula you didn't write | Two distinct, deliberate mitigations in `src/domain/csv.ts`: a **UTF-8 BOM** is required or Excel assumes the system codepage; and cells starting with `=`, `+`, `-`, `@`, tab, or CR are prefixed with an apostrophe to defeat **CSV formula injection** (a ticket titled `=HYPERLINK(...)` could otherwise become a live exfiltration link when a colleague opens the export). If either symptom appears, check whether `csv.ts`'s escaping/BOM logic was bypassed rather than assuming Excel is at fault. | Confirm the export path always goes through `src/domain/csv.ts`, not a hand-rolled join. |
