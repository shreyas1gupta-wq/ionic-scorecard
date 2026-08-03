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
  ├─ RLS on every table; runtime role `crm_app` owns nothing, so policies bind it
  ├─ status_updates + audit_log: UPDATE/DELETE revoked AND trapped by triggers
  ├─ hash-chained audit_log, appended only via a lock-holding definer function
  ├─ access_events: 2-year retention, 6 months hot (CSCRF PR.AA 1(e))
  └─ nightly: pg_dump → age-encrypt → private GitHub repo + R2
```

### 2.1 Why Supabase Postgres and not Cloudflare D1

D1's location *hints* are `wnam`, `enam`, `weur`, `eeur`, `apac`, `oc` — **there is no India hint**, `apac` is the nearest, and the docs state that a hint *"does not guarantee that D1 runs in your preferred location"* `[DATA]`. Supabase can be pinned to `ap-south-1` `[DATA]`.

**A correction to my earlier reasoning.** I first justified this on CERT-In's 2022 Directions requiring ICT logs "within the Indian jurisdiction". The Direction does say that, but **CERT-In's own FAQ Q35 expressly disclaims the residency reading**: *"Is it required to store copy of logs in India only? Ans.: The logs may be stored outside India also as long as the obligation to produce logs to CERT-In is adhered to by the entities in a reasonable time."* `[DATA]` The regulator has reinterpreted it as a **producibility** obligation, not a localisation one. So there is no live legal requirement forcing India residency, and building a nightly export purely to satisfy one would have been engineering driven by a rule that does not exist as I stated it.

**What actually justifies the choice.** SEBI's CSCRF *did* require Regulatory Data to be stored within India, and SEBI put that requirement **in abeyance by circular 2024/184 of 31 December 2024, "till further notice"** `[DATA, secondary — fetch the circular before relying on it]`, explicitly because REs use third-party cloud providers storing data abroad. Meanwhile SEBI's June-2025 CSCRF FAQs, *for in-scope cloud services*, require MeitY-empanelled CSP infrastructure (FAQ 47), storage and processing including logs inside such data centres (FAQ 48), and that *"encryption keys and key management operations must be handled within the boundaries of India"* (FAQ 26) `[DATA]`. **Neither Cloudflare nor Supabase is a MeitY-empanelled CSP** `[UNVERIFIED — check the current list]`; Supabase's Mumbai region buys geography, not empanelment.

So the honest position is: **no localisation obligation binds today, but it rests on an abeyance that a single circular can lift.** That changes the recommendation from "either host is fine, Mumbai is nicer" to **"pick the option you can move, and record why the app is out of scope."** Which is precisely what the repository interface in §2 exists for — its value just went from convenience to insurance.

Honest caveats that go to whoever signs off, not into a claim: pinning the primary region does not prove where every replica and log line lives; Cloudflare terminates TLS globally; and Access authentication logs are Cloudflare-side with **only ~24 hours of retention on the free plan** `[DATA]` — which is why §8 now requires the app to write its own authentication-event rows.

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

Ten tables. Names in `snake_case`; all timestamps `timestamptz`, all dates plain `date` in IST semantics.

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

access_events    seq (bigserial) · occurred_at · employee_id · event (LOGIN|VIEW|EXPORT|ADMIN_ACTION)
                 entity · entity_id · ip · user_agent · archived_at
                 ── CSCRF: 2-year retention, ≥6 months hot. Append-only. See §8.

holidays         holiday_date (pk) · name · year          ── admin-maintained, no external API
categories       id · name · active
settings         key · value (jsonb)                       ── stale thresholds, session policy
dek_keyring      id · tier · subject_id · generation · kek_version · wrapped_dek · shredded_at
```

`access_events` is separate from `audit_log` deliberately. The audit log answers *"what changed"* and is hash-chained for tamper-evidence. Access events answer *"who looked at what"* — far higher volume, no chaining, and aged out to the encrypted archive at six months to stay inside the 500 MB free database. Merging them would either bloat the chain or under-retain the audit trail.

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

### V1 encrypts nothing — and that is now the right answer

**Superseded 2026-08-03 by the Principal's scope decision:** this holds *general internal task tickets*, not client-linked records. There is therefore no `client_ref` column in the schema, no encrypted column, no `dek_keyring` table, and no key-management surface in V1.

That is a real simplification, not a shortcut. The KEK escrow, rotation and crypto-shredding machinery below was the largest source of operational risk in the design — a lost or mis-rotated key makes data unrecoverable — and removing the field that needed it removes all of it. What protects the remaining data is RLS, Mumbai residency, and encryption at rest provided by the platform.

The design below is retained **unbuilt**, as the specification to follow *if* a client reference is ever added. Do not build it speculatively.

### The tradeoff this section originally documented

**Only `tickets.client_ref`.** Titles, descriptions and punch notes stay in cleartext.

This is a real tradeoff, not an oversight. `REQUIREMENTS.md` §6 promises full-text search across descriptions and punch notes. **Encryption and search are fundamentally in tension** — an encrypted column cannot be searched without either decrypting everything on every query or building a blind index that leaks the thing it indexes. For a tool whose daily usefulness depends on finding "that ticket about the audit query", search wins in V1.

What protects that cleartext instead: RLS, the no-client-PII policy, Mumbai residency, and the fact that a database dump requires credentials we control. What it does *not* protect against: a Supabase-side compromise. Stated plainly so the risk is accepted knowingly rather than assumed away.

Employee identity is handled by **pseudonymisation**, not encryption — an erasure request replaces `display_name` with `Former employee #NNN` and nulls the email, keeping the row id so historical attribution stays intact. Crypto-shredding a name the UI renders hundreds of times a day would be theatre.

---

## 8. Compliance posture

> **Revised 2026-08-03 after an adversarial verify pass overturned 18 claims across the research.** The corrections are recorded in `research/VERIFY_CORRECTIONS.md` and applied below. Four of my own statements were wrong; §8.2 names them rather than editing them away.

### 8.1 The single most important correction: DPDP is not in force. CSCRF and CERT-In are.

I built the first draft of this section substantially on DPDP. That was the wrong centre of gravity.

**DPDP Rules 2025 were notified 13/14 November 2025, and Rule 1(4) reads: *"Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after the date of publication of this Gazette."*** `[DATA]` Rules 6 and 8 sit inside that tranche, as do Act s.8 entirely and the s.12(3) erasure right. So **today there is no DPDP erasure right and no DPDP retention floor** — a delete button breaches nothing, and nothing compels retention. Substantive obligations arrive ~14 May 2027.

Getting the tense right matters. It is the difference between "we are non-compliant" and "we are pre-building".

**What binds today:**

| Regime | Status | What it demands here |
|---|---|---|
| **SEBI CSCRF** | **Live** — adoption deadlines already passed | The real regime. See §8.4. |
| **CERT-In Directions 2022** | **Live** | 180-day rolling ICT logs (storable **outside** India), NTP sync to NPL/NIC, a filed Annexure-II point of contact, 6-hour reporting for Data Breach / Data Leak |
| **IT Act s.43A + SPDI Rules 2011** | **Live** until DPDP s.44(2) retires them ~May 2027 | Genuinely light here. SPDI Rule 3 "sensitive personal data" means passwords, financial-instrument detail, health, biometrics and similar. **Employee name, work email and task history are not SPDI.** An honest de-escalation. |
| **DPDP Act + Rules 2025** | **Not yet** (~14 May 2027) | Design for it now — notice, purpose limitation, soft-delete + tombstone, 1-year log retention, a grievance intake with Rule 14(3)'s **90-day** response cap — because logs you never captured cannot be retrofitted. |

**⚠ Planning risk.** MeitY consulted in January 2026 on **advancing** Phase 3 from 18 months to 12 — putting it at **13 November 2026, about three months away** `[DATA on the consultation; current status UNVERIFIED]`. Re-check the e-Gazette before treating May 2027 as settled.

### 8.2 My own claims that were wrong

- **"Supabase Free includes no DPA" — WRONG.** The Supabase DPA carries no plan restriction and applies to Free by its own terms, with EU Standard Contractual Clauses (Modules Two and Three) and a *"without undue delay, and where feasible, within forty-eight (48) hours"* breach notice `[DATA]`. Entity: Supabase Pte. Ltd, Singapore. Genuinely paid-gated: SOC 2, ISO 27001, HIPAA — and **Platform Audit Logs**, which is the compliance-relevant one and reinforces that the app must keep its own audit table.
- **"CERT-In requires India-resident logs" — WRONG.** Producibility, not residency. See §2.1.
- **"GitHub Free has no audit log" — WRONG.** A GitHub Free *organisation* gets a web-UI audit log with **180 days** retention `[DATA]`; only *programmatic* access is Enterprise-gated. The real free-tier gaps are different: **no ruleset or branch-protection enforcement on private repos**, and no API export.
- **GitHub erasure is *worse* than I said** — which strengthens D1 rather than weakening it. Support *"won't remove non-sensitive data, and will only assist in the removal of sensitive data in cases where we determine that the risk can't be mitigated by rotating affected credentials"* `[DATA]`. An employee name in git history is neither. There is **no vendor path at all**, not merely a slow one.

### 8.3 Still true, and now load-bearing

- **DPDP s.16(1) is a negative list, not a localisation mandate** `[DATA]`, and no restricted-country list is notified. But s.16(2) preserves any Indian law imposing stricter transfer limits — CSCRF is that law, currently in abeyance (§2.1).
- **Supabase Free has no automated backups and no PITR** `[DATA]`; free users are told to `pg_dump` themselves. The encrypted-backup leg is **load-bearing**.
- **Supabase Free pauses after 1 week of inactivity** `[DATA]`. The keep-alive is an **availability dependency, not an optimisation** — and its own failure must be visible. A silent keep-alive is worse than none.
- **GitHub Actions' 2,000 free minutes/month is an account-wide pool**, not per-repository `[DATA]`. Moving to a company organisation gets a fresh pool.
- **`age` now has a post-quantum key format** (`AGE-SECRET-KEY-PQ-1`) with keys far longer than one line, which changes the paper-escrow mechanics; interop with the `typage` library is `[UNVERIFIED]`. **Pin the backup to classic X25519 recipients.**

### Adopted as good practice, not claimed as law
Hash-chained audit log · field encryption · access review · retention and purge · restore drills · least privilege.

### SEBI — resolved, and it is better news than expected

Primary sources parsed in full: PMS Regulations 2020, RA Regulations 2014, the 205-page CSCRF (Aug 2024), its Dec-2024 and Aug-2025 clarifications, CERT-In Directions 2022, and the SCORES circular.

**Record retention — and a correction that removes false comfort.** I first wrote that Reg 29's five-year duty attaches to "a closed reference to the Reg 27(1) enumeration". **That was wrong.** Reg 29 preserves *"the books of account and other records and documents mentioned under this chapter"*, and Regs 27 and 29 sit in **Chapter IV — General Obligations and Responsibilities, Regulations 21 to 34** `[DATA]`. That chapter also contains Reg 22 (client agreement and disclosure document), Reg 24(10) (*"proper and timely handling of complaints from his clients"*), Regs 30–31 (client-wise accounts, periodic reports to the client), Reg 33 (information to the Board including client names) and Reg 34 (compliance officer).

So the preserved set is **not a five-item list; it is an open-textured set defined by subject matter** — which is exactly the failure mode this design is trying to avoid. The correct rule is therefore *stronger* than what I wrote: the tracker escapes Reg 29 only if no ticket ever becomes

1. an investment-rationale record — Reg 27(1)(e), and its proviso demands custody *"under the hands of the Principal Officer"*, which an append-anything-by-anyone log structurally is not;
2. part of the client-complaint handling trail — Regs 24(10) / 11(d) / **34A**; or
3. evidence of a client report or client-wise account — Regs 30–31.

**A CRM used by an APM at an NDPMS house plausibly touches (2) and (3), not just (1).** The "closed enumeration" framing gave false comfort. `REQUIREMENTS.md` §8 has been widened accordingly.

**A third trapdoor if the firm holds RA registration.** SEBI (Research Analysts) Reg 25(1) was **amended on 16 December 2024**, inserting clause **(vii): *"records of communication including emails, call recordings etc. with all clients including prospective clients in such manner as may be specified"*** `[DATA]`. That is wider than Reg 27(1)(e) — it captures client-facing *correspondence*, not just investment reasoning, and expressly contemplates SEBI specifying the *manner* of maintenance. Any 2014-vintage citation of the RA Regulations is superseded.

**SEBI's outsourcing regime is the cleanest argument of all, and I had missed it.** The Guidelines on Outsourcing of Activities by Intermediaries (CIR/MIRSD/24/2011) apply to all registered intermediaries and name Portfolio Managers explicitly; CSCRF pulls them in at Annexure-F `[DATA]`. They require a *"clearly defined and legally binding written contract"*, that provider facilities and data *"shall be deemed to be those of the registered intermediary"* with SEBI holding a **right of access at any point of time**, audit and inspection rights, data-preservation covenants, country-risk and choice-of-law provisions, and a **separate contingency plan per outsourcing arrangement**.

A click-through free-tier ToS is a non-negotiated adhesion contract with none of that. **This — not CSCRF bucketing — is the decisive reason a free tier cannot host anything in scope, and equally the decisive reason to keep this app definitively out of scope.**

**CSCRF applicability.** Portfolio Managers **are** covered — they appear in the addressee list of the circular and both clarifications `[DATA]`. But the bucket matters enormously:

- A Portfolio Manager **can never be a Qualified RE** `[DATA + INFERENCE]`. So Cyber Capability Index, ISO 27001, red teaming, threat hunting and quarterly reviews never apply.
- At **≤ ₹3,000 cr AUM a Portfolio Manager is a Self-certification RE** — the band was widened threefold from < ₹1,000 cr `[DATA]`.
- **But a non-individual Investment Adviser is a Small-size RE by STATUS, with no AUM threshold** `[DATA]`. That is *strictly worse* than a sub-₹3,000 cr Portfolio Manager, so **the bucket cannot be inferred from the PM side alone** — it depends on the firm's full registration set.
- Self-certification REs face *"only VAPT audit … and no other audit is required"*, plus an Annexure-P self-certification signed by the MD/CEO/Board member/Partner/Proprietor `[DATA]`. **This relief is self-certification-only.** PR.IP.S14 (periodic cyber audit by a CERT-In empanelled auditor) is exempted by a sentence *after* Exemption Table 25, and **small-size REs get no such relief** `[DATA]`. Table 25 itself exempts only PR.IP.S3, S16 and S17.
- **PR.IP.S15 is not exempted for anyone, and it bites a self-built app directly**: for in-house developed software, *"REs shall ensure compliance … is submitted by CERT-In empanelled IS auditing organization"*, Applicability **All REs (Mandatory)** `[DATA]`. A hand-built tool inside scope attracts a recurring paid certification. That is the one genuinely unavoidable rupee cost in this whole project — and it applies only if the app is in scope.
- **Encryption at rest (PR.DS.S1) is in the exemption table** for self-certification and small-size REs `[DATA]`. We do it anyway. PR.DS.S2 is *not* exempted.
- **CSCRF does set a numeric log-retention period, and it is four times what I wrote.** PR.AA guideline 1(e): access logs *"shall be maintained and stored in a secure location for a time period not less than two (2) years (atleast 6 months in online mode and rest in archival mode)"*, Applicability **All REs (Mandatory)**, not in the exemption table `[DATA]`. I had said 180 days. **This is decision-controlling: essentially every zero-cost logging tier retains 7–90 days**, and Cloudflare Access free retains authentication logs for ~24 hours. See §8.5.
- **API security is required**: *"rate limiting, throttling, and proper authentication and authorisation mechanisms"* `[DATA]`.
- **Data Classification is live; only Data Localisation is in abeyance** `[DATA]`. I should not have implied both were suspended.
- Applying to **all REs**: annual cybersecurity-policy and risk-management-policy review, annual cyber training, **half-yearly access-rights and privileged-user reviews**, and an annual COOP review and recovery drill `[DATA]`.
- **SEBI has its own incident clock, parallel to CERT-In's.** CSCRF RS.CO guideline 1, All REs Mandatory: incidents falling under the CERT-In directions go to **SEBI within 6 hours** via `mkt_incidents@sebi.gov.in`, with details on the SEBI Incident Reporting Portal **within 24 hours**; all other incidents within 24 hours `[DATA]`. The practical trap is that *noticing* starts the clock, and a self-built app with no monitoring and no on-call rota has no reliable way to notice. **That is a staffing obligation, not a code obligation**, and it does not care that the URL is private.

**The conditional nobody should miss.** The CSCRF exemption table applies to self-certification and small-size REs *"provided they are onboarded to Market SOC"* `[DATA]`. Whether the firm is inside or outside that mandate is determined by clauses 2.2, 2.6, 2.7 and 3 of **circular 2025/60 of 30 April 2025** — an instrument I omitted from the chain and which nobody has read. Until it is, whether the Exemption Table relief (including the PR.DS.S1 encryption relief) is available **at all** is undetermined.

**SEBI's Cloud Services Framework does not bind a Portfolio Manager.** Its addressee list names exchanges, clearing corporations, depositories, brokers, DPs, AMCs/MFs, QRTAs and KRAs — **not** portfolio managers `[DATA, secondary reproduction — verify against the SEBI PDF]`.

### 8.5 The strategic conclusion — reversed

I wrote: *"the clean way through is to keep the app out of CSCRF scope by design."* **That is wrong, and the verify pass was right to kill it.**

CSCRF scope is set by **what the system is used for, and by segregation** — not by whether client PII sits in it. SEBI's June-2025 CSCRF FAQ Q8: *"The controls shall apply only to IT infrastructure, network, application, software, etc. being used for SEBI RE related activities."* `[DATA]` **An internal ticketing app whose tickets track NDPMS and advisory deliverables is being used for SEBI-RE-related activities, with or without client names.** The `client_ref`-only design buys no scope exemption. It still earns its keep — on breach-impact and Reg-29 grounds — but not this one.

**The correct target is: in scope, classified non-critical.** FAQ Q10 allows an RE to classify internet-facing but business-non-critical tools (*"survey forms, loan calculators, etc."*) as non-critical on a documented risk assessment, with the Board/Partners/Proprietor approving the critical-systems list; FAQ Q9 permits a **manual or spreadsheet IT-asset inventory** for lean REs `[DATA]`. So: in scope, non-critical, listed in the asset inventory, risk assessment written down.

**And there is one hard architectural rule I had not stated.** FAQ Q27: audit coverage is limited to systems under SEBI purview *"only if infrastructure/software/applications are properly segregated. If there are any ancillary/connected systems used for accessing/communicating with systems under SEBI purview, those systems should also be covered under audit against CSCRF."* `[DATA]`

Therefore, as a design constraint with teeth: **no integration, no data feed, no shared credential, and no link between this app and any SEBI-purview system.** Segregation is the control that keeps it non-critical and out of audit scope.

**This creates a genuine tension with the graduation path in §2** — moving storage into the M365 tenant, or adopting Entra ID SSO, are exactly the kind of couplings Q27 contemplates. An identity provider is arguably infrastructure rather than a SEBI-purview application, but I am not confident enough to assert that, and it is the sort of question a compliance officer should answer rather than a developer. **Flagged, not resolved** — §11 item 7.

Finally, the boundary question nobody has tested: **CSCRF Annexure-L defines VAPT scope**, and neither the researcher nor the verifier opened it. So the claim that an actively-iterated in-house app generates recurring VAPT events is asserted, not shown — and the cheaper counter-argument (the app sits outside the declared VAPT scope) is untested. That is the next document to fetch.

### The SharePoint route — architecturally excellent, and now confirmed IT-gated

Your instinct was half right. A SharePoint List genuinely *is* the better vehicle: typed columns, **per-item ETag optimistic concurrency** (a clean `412 Precondition Failed` instead of a lost write), per-item version history to 50,000 versions, `Person or Group` columns bound to real Entra identities rather than typed email strings, and `Lookup` for referential linkage `[DATA]`. For an India-signup M365 tenant the data sits under Microsoft's contractual residency commitment. It is included in every standard M365 plan at no extra cost.

**But it cannot be done without IT, and the escape hatch has closed.** Microsoft's default managed user-consent policy explicitly excludes `Sites.Read.All` and `Sites.ReadWrite.All` from what an ordinary employee may consent to `[DATA]`. `Sites.Selected` — the least-privilege option — is *worse* for self-service, because granting the app access to a specific site requires `Sites.FullControl.All` or SharePoint-admin PowerShell. And the old self-serve route (SharePoint Add-in registration via `appregnew.aspx` with Azure ACS) **stopped working on 2 April 2026** `[DATA]` — four months ago.

Also worth knowing before anyone relies on it: item-level permissions are **bypassed by any user holding Design or Full Control** `[DATA]`.

So the graduation path in §2 stands, and it is genuinely worth taking — it is one IT ticket, not a rebuild, which is exactly what §2's repository interface protects.

---

### Recurring obligations the tool must actively support

These apply to **all** REs under CSCRF `[DATA]`, so they become build items and runbook entries rather than good intentions:

| Obligation | Cadence | What the tool provides |
|---|---|---|
| **User-access log retention — 2 years, ≥6 months queryable** | Continuous | **New build item.** See below; this is the biggest single change from the verify pass. |
| Own authentication-event log | Continuous | **New build item.** Cloudflare Access free retains auth logs ~24 h, so "who logged in, when, from where" must be written by the app at first request or it is unrecoverable. |
| Access-rights and privileged-user review | **Half-yearly** | The §9 access-review report, plus an audit entry recording that the review happened and who did it |
| COOP review and recovery drill | Annual | The documented restore drill, with its result logged |
| Cybersecurity and risk-management policy review | Annual | A runbook section with a review date, not a feature |
| Cyber-security training | Annual | Firm-level, outside this tool |
| Incident reporting — SEBI 6 h + 24 h, CERT-In 6 h | On occurrence | A written runbook and a named owner. **Requires monitoring that makes "noticing" possible** — otherwise the clock starts and nobody hears it. |
| VAPT via a CERT-In empanelled auditor | Per bucket | Firm-level; scope boundary untested (Annexure-L) |
| PR.IP.S15 in-house-software certification | Per major release, if in scope | Firm-level, paid, **All REs mandatory and not exempted** |
| API rate limiting and throttling | Continuous | Cloudflare WAF rules plus per-route limits in the Worker |

**The 2-year log requirement changes the design.** Free-tier observability retains 7–90 days; Supabase Free retains API and database logs for **1 day** and auth audit logs for **1 hour** `[DATA]`; Cloudflare Access free, ~24 hours. None of these can hold two years of access logs.

So access events must live in **our own table**, not a vendor's log pipeline — which the append-only design already gives us the machinery for. Concretely: a `access_events` table (who, when, from where, what they read or wrote), retained **6 months hot in Postgres** and the remainder **archived into the nightly encrypted backup**, giving the required "6 months online, rest archival" split. The 500 MB free database is the binding constraint, so the archival cut is not optional at the two-year horizon.

The half-yearly access review is the obligation people forget. Making the tool *record that it happened* is worth more than the report itself.

---

## 9. Verify before building — four checks, under an hour

Each is cheap now and expensive to discover later.

| # | Check | Why it is load-bearing | Time |
|---|---|---|---|
| **0** | **Pull Ionic Wealth's SEBI registration set** from `sebi.gov.in/intermediaries` (Portfolio Managers / Investment Advisers / Research Analysts lists) and its AUM from APMI's disclosures | **Do this first.** It determines the CSCRF bucket, and therefore whether the app attracts VAPT only or VAPT plus an annual cyber audit plus PR.IP.S15 certification. Every other compliance answer is contingent on it. It is public information. | 15 min |
| 1 | Create a throwaway Supabase free project; confirm **South Asia (Mumbai) ap-south-1** is selectable on the **Free** plan | The docs do not plan-gate regions, but I could not confirm it from inside the UI `[UNVERIFIED]`. | 3 min |
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
| Investment reasoning, a client complaint, or client-report evidence typed into a punch note → tool becomes a Chapter IV record | **High** | `REQUIREMENTS.md` §8; inline warnings; stated when the tool is introduced. Widened after the verify pass — the preserved set is subject-matter-defined, not a closed list |
| No API rate limiting — a CSCRF requirement, and a real abuse vector | Medium | Cloudflare WAF rate-limit rules + per-route limits in the Worker |
| **Access logs not retained 2 years** — CSCRF All-REs mandatory, and no free tier does it | **High** | Own `access_events` table, 6 months hot + archival into the encrypted backup (§8 recurring obligations) |
| **An incident occurs and nobody notices**, so the 6-hour SEBI and CERT-In clocks run silently | **High** | Monitoring + a named owner + a written runbook. This is a staffing gap, not a code gap, and it cannot be closed by writing more code |
| **SEBI localisation abeyance is lifted** by a future circular | Medium | The repository interface (D6) is the insurance. Record why the app is out of scope, and keep the store movable |
| **Any integration or shared credential with a SEBI-purview system** pulls the app into CSCRF audit scope as a connected system | Medium | Hard rule: no integrations, no data feeds, no shared credentials (§8.5). Tension with the Entra SSO graduation path — §11 item 7 |
| Free-tier ToS cannot satisfy SEBI outsourcing requirements (right of access, audit, data preservation) | Medium | Only tolerable while the app is out of scope for regulated records. If it ever holds them, the hosting must change |
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
| 5 | **What is Ionic Wealth's full SEBI registration set — PM, non-individual IA, RA?** | **This one determines every other CSCRF answer and it is publicly resolvable in minutes** — SEBI publishes registered-intermediary lists by category, and APMI publishes member AUM. It matters because a non-individual IA is a Small-size RE *by status with no AUM threshold*, which is worse than a sub-₹3,000 cr PM: Small-size gets **no** cyber-audit exemption. Until this is pulled, self-certification vs small-size, VAPT-only vs VAPT-plus-audit, and whether the whole Exemption Table applies are all undetermined. **This should be the first lookup, not a closing caveat.** |
| 6 | **Is the firm onboarded to SEBI's Market SOC?** | A fact, not a preference. Every CSCRF exemption is conditional on it. Determined by clauses 2.2, 2.6, 2.7 and 3 of circular 2025/60 (30-Apr-2025), which nobody has read. |
| 7 | **Does adopting Entra ID SSO, or moving storage into the M365 tenant, pull this app into CSCRF audit scope as a "connected system"?** | FAQ Q27 says ancillary or connected systems get pulled in absent proper segregation. An identity provider is arguably infrastructure rather than a SEBI-purview application, but I am not confident enough to assert it. **A compliance officer should answer this, not a developer** — and the answer decides whether the §2 graduation path is available at all. |

---

## 12. Sources

Supabase pricing · regions · free-project-pausing · going-into-prod · backups docs · Cloudflare Workers/Pages/D1 limits · Cloudflare Zero Trust plans · Access One-time PIN · seat management · DPDP Act 2023 s.16(1) · CERT-In Directions 2022 · shadcn/ui and `Kiranism/next-shadcn-dashboard-starter` repo metadata. Full citations with fetch dates in the `research-*.md` files.
