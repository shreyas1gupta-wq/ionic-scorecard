# Internal Ticket & Status CRM — Design

**Status:** DRAFT for Principal review
**Date:** 2026-08-03
**Companion:** `REQUIREMENTS.md` (what it must do). This document is *how*.

Every load-bearing claim is tagged `[DATA]` (verified against a named primary source), `[INFERENCE]` (reasoning from data), `[OPINION]` (judgment), or `[UNVERIFIED]` (must be checked before relying on it). Research files: session scratchpad `research-*.md`.

---

## 1. Verdict: build it. Do not fork.

Held firmly, and for one dominant reason: **the append-only status punch is the product**, and no existing tool provides it.

Every candidate task-tracker — Plane, Vikunja, Zammad, osTicket, FreeScout, Redmine — has *editable* comments. To fork one, we would patch someone else's ORM and UI to revoke edit and delete, then re-apply that patch against every upstream release forever. That is strictly worse than either alternative: we inherit their maintenance burden **and** write custom code, and the patch fights every upgrade.

In a build, append-only is a table with `UPDATE` and `DELETE` privileges revoked at the database role level. Enforced by Postgres, not by good intentions.

Supporting reasons: forking abandons the verified-free Cloudflare path for an unverified free VM with idle-reclamation; open-issue counts on the candidates (Plane 978, osTicket ~1,200, SuiteCRM 1,411) `[DATA]` are attack surface we would own with no IT behind us; and the scope here is genuinely small — six tables. Forking ERPNext to get it is using a shipping container to post a letter.

Two candidates died during research for a reason worth recording: **Peppermint was archived in July 2026** and **Focalboard is unmaintained** `[DATA]`. Both looked reasonable not long ago.

### Honest effort estimate

| Work | Estimate |
|---|---|
| Schema, append-only enforcement, RLS | 1–2 sessions |
| Auth wiring + allow-list | 1–2 sessions |
| Ticket CRUD, punch model, deadline control | 2–3 sessions |
| Manager/admin dashboards, server-side role visibility | 2–3 sessions |
| Audit viewer, retention/purge, backup | 1–2 sessions |
| Polish, deploy, pilot with real colleagues, fix what they break | 2–4 sessions |
| **Total** | **~10–15 focused sessions ≈ 40–80 hours** |

`[OPINION]` Roughly 4–8 weeks of evenings to something 10–50 people can rely on. Anyone promising a weekend is discounting the last row — and the last row is where internal tools live or die. Real users will find the ambiguities in the status workflow that we cannot see from here.

---

## 2. Architecture

```
Browser
  │  ONE path in: the custom hostname only. No workers.dev route.
  ▼
Cloudflare Access ── email One-Time PIN, allow-list = the employees table
  │                  Cloudflare sends the OTP from its own infrastructure
  │  injects Cf-Access-Jwt-Assertion
  ▼
Cloudflare Worker (Next.js via OpenNext)
  │  1. verify the Access JWT against the team certs endpoint — FAIL CLOSED
  │  2. resolve email → employees row; reject unless status = ACTIVE
  │  3. mint a short-lived user-scoped Postgres JWT (sub = employee.id)
  │  4. every query runs under that JWT, so RLS applies — defence in depth
  ▼
Supabase Postgres — ap-south-1 (Mumbai)
  ├─ RLS + FORCE ROW LEVEL SECURITY on every table
  ├─ status_updates: UPDATE/DELETE privileges revoked
  ├─ hash-chained audit_log
  └─ nightly: pg_dump → age-encrypt → private GitHub repo + R2
```

### 2.1 Why Supabase Postgres and not Cloudflare D1

D1's data-localisation jurisdictions are `eu` and `fedramp` only — **India is not available**, and its location *hints* (`apac` etc.) explicitly do not guarantee placement `[DATA]`. Supabase can be pinned to `ap-south-1` `[DATA]`.

This matters more than I expected, because research surfaced a rule I had not accounted for: **CERT-In's 2022 Directions require ICT-system logs to be maintained within Indian jurisdiction for a rolling 180 days** `[DATA]`. For a SEBI-regulated entity that is not a close call.

Honest caveat, and it goes to compliance rather than into a claim: pinning the primary region does not by itself prove where every replica and log line lives. Cloudflare terminates TLS globally, and Access authentication logs are Cloudflare-side. **Both facts get disclosed to whoever signs off, not smoothed over.** `[OPINION]`

### 2.2 The single most important control, and it is one line of config

Cloudflare Access enforces on a **hostname**. A Worker is *also* reachable at `<name>.<subdomain>.workers.dev` unless that is switched off. Leave it on and the entire authentication layer is bypassed by a URL nobody had to guess hard.

Therefore, all three of:
1. `workers_dev = false` in `wrangler.toml`
2. the JWT check **fails closed** — no valid Access JWT returns 403 with no body
3. an automated test that hits the `workers.dev` URL and asserts non-200

`[INFERENCE]` This is the difference between an authenticated app and an app with a public back door.

---

## 3. Authentication — settled

**Cloudflare Access with email One-Time PIN.** No identity provider, no SSO tenant, no DNS records on `ionic.in`, no password storage, no OTP code of our own. Cloudflare's own documentation: *"Cloudflare Access can send a one-time PIN (OTP) to approved email addresses as an alternative to integrating an identity provider."* `[DATA]` It works on a `*.pages.dev` hostname `[DATA]`, so no control of the company domain is needed.

### Why this reverses the previous decision — and why it is now final

I have changed this call twice, so here is the full reasoning, once:

1. First position — email OTP via Brevo/Resend. **Wrong**, and for a real reason: without a DNS record on `ionic.in`, mail claiming to be from your domain fails SPF/DKIM alignment and Microsoft 365's own anti-spoofing junks it. Separately, Supabase's built-in mailer is rate-limited to roughly two emails per hour `[DATA]` — unusable.
2. Second position — admin-issued passwords + TOTP. Correct *given* that email was unavailable.
3. **Now — Cloudflare Access OTP.** The premise of position 2 was that no one could deliver OTP email. That premise was false: Cloudflare sends the PIN **from Cloudflare's own infrastructure**, so there is no SPF/DKIM problem to solve, because nothing pretends to come from `ionic.in`.

This is final because it strictly dominates: it deletes password storage, reset flows, Argon2 tuning, OTP generation, expiry and replay handling — an entire category of code, and therefore of bugs.

### Do not build an app session layer

With Access in front, identity is re-asserted on every request by a signed JWT. A second cookie session on top gives two sources of truth and a new bug class: Access session revoked, app session still alive. Session duration is configured in the Access policy; offboarding uses Access's own *revoke user session*. `[OPINION]`

This deletes §10's session-timeout requirement as app code — it becomes one Access setting.

### The seat cap is the real constraint

Cloudflare Zero Trust free is documented as *"Best for teams under 50 users"* `[DATA]`; a seat is consumed on any authentication event, one per user regardless of app count `[DATA]`. Marketing and trackers say **50 free seats**; one rendering of the plan table said "no user limit" `[UNVERIFIED]`.

You are 10–50 people. **This is the one number that could break the plan, and overage means users are blocked at login, not billed.** Mitigations: enable seat-expiration at 1–2 months so leavers auto-release `[DATA]`, and allow-list only actual users. Verification is item 2 in §9.

---

## 4. Data model

Nine tables. Names in `snake_case`; all timestamps `timestamptz`, all dates plain `date` in IST semantics.

```
employees        id · work_email (unique, citext) · display_name · role · manager_id
                 status (ACTIVE|DEACTIVATED) · created_at · deactivated_at · deactivated_reason

tickets          id · ref (TKT-2026-0001) · title · description · category_id · priority (P1|P2|P3)
                 assignee_id · raiser_id · status · deadline · original_deadline (immutable)
                 client_ref_enc (bytea) · created_at · closed_at · cancel_reason

ticket_watchers  ticket_id · employee_id

status_updates   id · seq · ticket_id · actor_id · created_at · status · note · blocked_reason
                 minutes_spent · next_action · next_action_by · corrects_update_id
                 ── THE PUNCH TABLE. Append-only, DB-enforced.

deadline_changes id · ticket_id · from_date · to_date · reason · requested_by · approved_by
                 decided_at · decision (PENDING|APPROVED|REJECTED)

audit_log        seq (bigserial) · occurred_at · actor_id · action · entity · entity_id
                 payload (jsonb) · prev_hash (bytea) · row_hash (bytea)

holidays         holiday_date (pk) · name · year          ── admin-maintained, no external API
categories       id · name · active
settings         key · value (jsonb)                       ── stale thresholds, session policy
dek_keyring      id · tier · subject_id · generation · kek_version · wrapped_dek · shredded_at
```

`original_deadline` is enforced immutable by trigger, not convention. It is the only honest basis for an on-time metric.

---

## 5. Append-only enforcement

Three layers, because this is the property everything else rests on.

```sql
-- 1. Privilege level. Note service_role too: it bypasses RLS but NOT table privileges.
REVOKE UPDATE, DELETE ON status_updates FROM authenticated, anon, service_role;
REVOKE UPDATE, DELETE ON audit_log      FROM authenticated, anon, service_role;

-- 2. Trigger level, in case a privilege is ever re-granted by a migration or the dashboard.
CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
  RAISE EXCEPTION 'append-only table: % not permitted on %', TG_OP, TG_TABLE_NAME;
END $$;

CREATE TRIGGER no_update BEFORE UPDATE OR DELETE ON status_updates
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();

-- 3. Test level: a test that attempts UPDATE and DELETE as every role and asserts failure.
```

Corrections are a new row with `corrects_update_id` set. The original stays visible, with the correction shown beside it.

---

## 6. Tamper-evident audit log

Each row hashes the previous one, so any edit or deletion of history is detectable.

```
row_hash = SHA-256(
    prev_hash                                    -- 32 bytes; genesis = 32 zero bytes
 || 0x1F || seq::text
 || 0x1F || occurred_at   as ISO-8601 UTC, microsecond precision
 || 0x1F || coalesce(actor_id::text, '')
 || 0x1F || action || 0x1F || entity || 0x1F || coalesce(entity_id::text, '')
 || 0x1F || canonical_json(payload)               -- keys sorted, no insignificant whitespace
)
```

`0x1F` (unit separator) is the field delimiter specifically because it cannot occur in any of the fields — concatenating without a delimiter lets two different records hash identically.

Written only by a `SECURITY DEFINER` function. No role holds a direct `INSERT`.

**Verification** walks the chain recomputing each hash. A deleted row shows as a `seq` gap *and* a hash mismatch at the following row — deleting a row and renumbering still breaks the chain, because `seq` is inside the hash.

**External anchoring** is what makes this meaningful against a privileged insider: the final `row_hash` of each day is committed to the private GitHub backup repo. Git's own immutability now works *for* us. A database administrator who rewrites history cannot also rewrite yesterday's commit. `[INFERENCE]`

---

## 7. Encryption — narrow, and honest about the cost

**WebCrypto `AES-256-GCM` inside the Worker.** Built into the runtime, no dependency, no bundle weight `[DATA]`.

**Rejected, with reasons:**
- **pgsodium / Supabase Transparent Column Encryption.** Supabase itself *"does not recommend"* these on its platform citing *"high level of operational complexity and misconfiguration risk"*; pgsodium is pending deprecation; column encryption was pulled from the dashboard for having *"sharp edges"* and causing *"unrecoverable issues"* `[DATA]`. Building a compliance story on a deprecated extension the vendor warns against is a trap.
- **`pgcrypto` with the key in SQL.** The key travels in query text and lands in `pg_stat_statements` and query logs `[INFERENCE]`.
- **libsodium WASM.** Unnecessary; WebCrypto covers AES-GCM, HMAC and HKDF natively `[DATA]`.
- **Supabase Vault** — correct for *secrets*, not row data `[DATA]`.

**Envelope design.** A KEK of 32 random bytes lives only as a Cloudflare Worker secret, never in the database and never in git (Workers secrets are *"not visible within Wrangler or Cloudflare dashboard after you define them"* `[DATA]`). It wraps two tiers of data key: an **identity DEK per employee** — the unit of erasure — and a rotating **content DEK**.

Ciphertext columns are versioned from day one: `0x01 || kek_version(u8) || dek_generation(u16 BE) || iv(12) || ciphertext||tag`. A bare blob is a decision you regret at the first key rotation.

### What is actually encrypted in V1, and the tradeoff I am not hiding

**Only `tickets.client_ref`.** Titles, descriptions and punch notes stay in cleartext.

This is a real tradeoff, not an oversight. `REQUIREMENTS.md` §6 promises full-text search across descriptions and punch notes. **Encryption and search are fundamentally in tension** — an encrypted column cannot be searched without either decrypting everything on every query or building a blind index that leaks the thing it indexes. For a tool whose daily usefulness depends on finding "that ticket about the audit query", search wins in V1.

What protects that cleartext instead: RLS, the no-client-PII policy, Mumbai residency, and the fact that a database dump requires credentials we control. What it does *not* protect against: a Supabase-side compromise. Stated plainly so the risk is accepted knowingly rather than assumed away.

Employee identity is handled by **pseudonymisation**, not encryption — an erasure request replaces `display_name` with `Former employee #NNN` and nulls the email, keeping the row id so historical attribution stays intact. Crypto-shredding a name the UI renders hundreds of times a day would be theatre.

---

## 8. Compliance posture

### Confirmed
- **DPDP s.16(1) is a negative list, not a localisation mandate.** *"The Central Government may, by notification, restrict the transfer of personal data … to such country or territory outside India as may be so notified"* `[DATA]`. No restricted-country list has been notified. **"Data must be in India" is not a DPDP requirement.**
- **CERT-In 2022 Directions** require ICT-system logs maintained within Indian jurisdiction for a rolling **180 days** `[DATA]`. This, not DPDP, is what drives the Mumbai decision.
- **Supabase Free includes no DPA, no SOC 2, no ISO 27001** `[DATA]`. Under DPDP the firm is Data Fiduciary and Supabase is a Data Processor, and a processor relationship normally rests on a contract. **On the free tier there is no such contract.** This is a genuine gap, it cannot be engineered around, and it is an argument for eventually moving the store into the M365 tenant.
- **Supabase Free has no automated backups and no PITR** `[DATA]`; free users are directed to export via `pg_dump` themselves. The encrypted-backup leg is therefore **load-bearing, not a nice-to-have**.
- **Supabase Free pauses after ~1 week of inactivity** `[DATA]`, restorable for up to a year. A daily keep-alive ping mitigates it. Real exposure: long holiday shutdowns and the pre-adoption period when only one person is using it.

### Adopted as good practice, not claimed as law
Hash-chained audit log · field encryption · access review · retention and purge · restore drills · least privilege.

### Still open
SEBI's applicability — record-retention periods and whether the CSCRF cybersecurity framework reaches a firm this size, and in which bucket. Research in flight. **Nothing in this design depends on the answer**; it can only add obligations (MFA, VAPT cadence, log-retention periods), all of which layer on.

---

## 9. Verify before building — four checks, under an hour

Each is cheap now and expensive to discover later.

| # | Check | Why it is load-bearing | Time |
|---|---|---|---|
| 1 | Create a throwaway Supabase free project; confirm **South Asia (Mumbai) ap-south-1** is selectable on the **Free** plan | The docs do not plan-gate regions, but I could not confirm it from inside the UI `[UNVERIFIED]`. This is the entire data-residency story. | 3 min |
| 2 | Zero Trust dashboard → billing; read **current seat entitlement** | Sources conflict between 50 and unlimited `[UNVERIFIED]`. Overage blocks users at login. | 2 min |
| 3 | Stand up a stub on `*.pages.dev`, enable Access OTP, confirm end-to-end that an allow-listed address gets a PIN **and a non-listed one is refused** | The whole auth model. Also confirms OTP mail reaches an `@ionic.in` inbox rather than Junk. | 15 min |
| 4 | Confirm `workers_dev = false` takes effect and the `workers.dev` URL returns non-200 | §2.2. This is the back-door check. | 10 min |

If check 1 fails, the fallback is Supabase in the nearest available region with the residency limitation documented, or a self-hosted Postgres on a Mumbai VM. If check 2 shows fewer than 50 seats, auth falls back to the §3 position-2 design (admin-issued credentials + TOTP), which is why that design is recorded rather than deleted.

---

## 10. Risks

| Risk | Severity | Control |
|---|---|---|
| `workers.dev` route left enabled → auth bypassed entirely | **Critical** | §2.2, all three layers, with a test |
| Access seat cap below headcount → users blocked at login | High | Verify (§9.2); seat expiry; fallback auth design retained |
| Supabase free: no DPA, no backups, no PITR | High | Own encrypted backups; disclose the DPA gap; M365-tenant migration path |
| **You are the single point of failure** | High | Repo owned by a **company** GitHub account, not a personal one; a real README; one colleague who has deployed it once before you need them to |
| Free project paused over a holiday shutdown | Medium | Daily keep-alive ping |
| Client PII typed into a free-text field | Medium | Policy + inline warning + the fact it is cleartext, stated in §7 |
| IDOR — the most likely real bug in an app like this | Medium | Authorisation in RLS, never only in the UI; the Worker never uses `service_role` for a user request |
| Tool becomes load-bearing while unsanctioned | Medium | Principal's sequencing call (§11) |

On `service_role`: it **bypasses RLS entirely**. It is used only for migrations and backups, never on a request path. `[DATA]`

---

## 11. Open decisions for the Principal

| # | Decision | Note |
|---|---|---|
| 1 | Do managers see all of their reports' tickets, or only those they personally assigned? | Changes the RLS policy materially |
| 2 | When to seek firm sanction | Build-then-demo is designed for; the concern is 40 people depending on an invisible tool |
| 3 | Accept cleartext punch notes in exchange for working search (§7)? | My recommendation: yes for V1 |
| 4 | Repo under a company GitHub account or your personal one? | Recommendation: company, from the first commit — retrofitting ownership is awkward |

---

## 12. Sources

Supabase pricing · regions · free-project-pausing · going-into-prod · backups docs · Cloudflare Workers/Pages/D1 limits · Cloudflare Zero Trust plans · Access One-time PIN · seat management · DPDP Act 2023 s.16(1) · CERT-In Directions 2022 · shadcn/ui and `Kiranism/next-shadcn-dashboard-starter` repo metadata. Full citations with fetch dates in the `research-*.md` files.
