# Dimension: Feature Set + Zero-Cost Security Architecture
**Internal CRM / ticketing app — Ionic Wealth (SEBI-registered NDPMS + MF/advisory), 10–50 users, ₹0 budget**

Research date: **2026-08-03**. Every free-tier number below reflects what the cited page said **on 2026-08-03** and must be re-checked before build. Tags: `[DATA]` = verified from a named primary source, `[DATA-2]` = secondary source only (primary not retrievable), `[INFERENCE]` = my reasoning, `[OPINION]` = judgment, `UNVERIFIED` = could not confirm.

---

## 0. HEADLINE

Two findings dominate everything else in this dimension:

1. **Do not build your own login.** Cloudflare Access (Zero Trust) already implements email one-time-PIN as a *standalone* login method — no external IdP, no tenant admin, 10-minute single-use PINs, and it is enumeration-resistant *by design*. `[DATA]` Cloudflare sends the emails, so it consumes **zero** of your email quota, and unauthenticated traffic never reaches your app. That single decision deletes ~40% of the security work in the original plan (OTP generation, hashing, rate-limit tables, enumeration handling, session cookies, session rotation, idle timeout, device list) and replaces it with one job: **verify the `Cf-Access-Jwt-Assertion` JWT on every request, fail closed.**

2. **Field-level encryption is the wrong place to spend your effort here, and I will argue that explicitly.** The app must be able to decrypt everything to render a dashboard, so column encryption does **not** defend against the two most likely real breaches (an authorization bug / IDOR, and a curious insider with a valid login). It defends only against DB-dump theft, vendor breach, and a leaked backup. Encrypt a *narrow* set of columns for those cases; spend the freed effort on RLS + a systematic anti-IDOR discipline + a tamper-evident audit chain, which are what actually fail in apps like this. `[OPINION]`

---

## 1. VERIFICATION LEDGER (all free-tier numbers, with sources)

| Thing | Free-tier fact | Source | Tag |
|---|---|---|---|
| Cloudflare Workers | 100,000 requests/day; **10 ms CPU/request**; 50 subrequests/request; 64 env vars/secrets per Worker @ 5 KB each; script 3 MB gzipped; **5 Cron Triggers per account**; 128 MB memory | [developers.cloudflare.com/workers/platform/limits](https://developers.cloudflare.com/workers/platform/limits/) | `[DATA]` |
| Cloudflare D1 | 5 M rows read/day; **100,000 rows written/day**; 5 GB storage total | [d1/platform/pricing](https://developers.cloudflare.com/d1/platform/pricing/) | `[DATA]` |
| **D1 jurisdictions** | Only `eu` and `fedramp`. **India is not an available jurisdiction.** Set at creation only, cannot be changed | [changelog 2025-11-05](https://developers.cloudflare.com/changelog/post/2025-11-05-d1-jurisdiction/) | `[DATA]` |
| Cloudflare R2 | 10 GB-month storage; 1 M Class A ops; 10 M Class B ops; **egress free** | [r2/pricing](https://developers.cloudflare.com/r2/pricing/) | `[DATA]` |
| Cloudflare Turnstile | Unlimited challenges/verification requests; up to 20 widgets; 10 hostnames/widget; 7-day analytics | [turnstile/plans](https://developers.cloudflare.com/turnstile/plans/) | `[DATA]` |
| **Cloudflare free-plan rate limiting** | **1 rule only; counting characteristic = IP only; expression fields = Path and Verified Bot only; period fixed at 10 s; mitigation timeout 10 s; no custom counting expressions** | [waf/rate-limiting-rules](https://developers.cloudflare.com/waf/rate-limiting-rules/) | `[DATA]` |
| Cloudflare Access — one-time PIN | Standalone login method, **no external IdP required**. "This secure PIN expires 10 minutes after the initial request." Single-use — "Requesting a new PIN invalidates the previous PIN." "Cloudflare only sends the email if the user is allowed by an Access policy." Enumeration-resistant: "The login page will always say a code has been emailed to you, regardless of whether or not an email was sent." Note: "OTP is no longer added automatically, but you can set it up at any time." | [cloudflare-one/identity/one-time-pin](https://developers.cloudflare.com/cloudflare-one/identity/one-time-pin/) | `[DATA]` |
| Access JWT validation | JWT arrives in `Cf-Access-Jwt-Assertion` header (recommended) or `CF_Authorization` cookie ("not guaranteed to be passed"). JWKS at `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`. Validate `aud` (per-app AUD tag) and `iss`. Match `kid` against `public_certs[]`; docs warn: "Do not fetch the current key from `public_cert`, since your origin may inadvertently read an expired value from an outdated cache." Signing keys rotate every 6 weeks; previous key valid 7 days | [validating-json](https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/) | `[DATA]` |
| Access account limits | 500 applications/account; 1,000 rules per application; 500 reusable policies; 50 domains per application; 50 service tokens | [cloudflare-one/account-limits](https://developers.cloudflare.com/cloudflare-one/account-limits/) | `[DATA]` |
| **Zero Trust free seats = 50** | Widely reported as 50 users free, blocked beyond that until you pay. **I could NOT confirm this from a Cloudflare primary page** — `cloudflare.com/plans/zero-trust-services/` and the docs FAQ/account-limits pages do not state a free seat number; only secondary sources and a Cloudflare Community thread ("50 user limit on free plan") do | [community.cloudflare.com thread](https://community.cloudflare.com/t/50-user-limit-on-free-plan/546057) | `[DATA-2]` / partly **UNVERIFIED** |
| Access log retention on free | The audit-logs doc describes authentication logs and per-request logs but **states no retention period or plan tiering**. Secondary sources claim 24 h on free. **Treat as UNVERIFIED and assume it is short.** | [insights/logs/audit-logs](https://developers.cloudflare.com/cloudflare-one/insights/logs/audit-logs/) | **UNVERIFIED** |
| Workers secrets | "Secrets are a type of binding that allow you to attach encrypted text values to your Worker." "Secret values are not visible within Wrangler or Cloudflare dashboard after you define them." Set via `wrangler secret put`, dashboard, or `--secrets-file` (≤100 per request). Secrets Store is account-level and **beta**; no pricing stated | [workers/configuration/secrets](https://developers.cloudflare.com/workers/configuration/secrets/) | `[DATA]` |
| Workers Web Crypto | AES-GCM (encrypt/decrypt/generate/wrap), HMAC, SHA-256, PBKDF2, HKDF, Ed25519, ECDSA all supported. Non-standard extras: **`crypto.subtle.timingSafeEqual()`** and `crypto.DigestStream()`. MD5 present "for interacting with legacy systems" | [workers/runtime-apis/web-crypto](https://developers.cloudflare.com/workers/runtime-apis/web-crypto/) | `[DATA]` |
| Next.js on Workers (OpenNext) | App Router + Pages Router, SSR/SSG/PPR/ISR, route handlers, **standard middleware supported** (Node Middleware from 15.2+ **not** supported), requires the **Node.js runtime, not Edge runtime**. Worker size limit: **3 MiB compressed on free** (10 MiB paid) | [opennext.js.org/cloudflare](https://opennext.js.org/cloudflare) | `[DATA]` |
| Supabase free | 500 MB database; 500 MB RAM shared CPU; 5 GB egress; 1 GB file storage; 50,000 MAU; 500,000 edge function invocations; **"Free projects are paused after 1 week of inactivity"**; **limit of 2 active projects**; **no backups**; log retention 1 h (auth audit) / 1 day (API & DB) | [supabase.com/pricing](https://supabase.com/pricing) | `[DATA]` |
| Supabase region | `ap-south-1` (Mumbai) is a deployable region. No free-plan region restriction found | [github.com/orgs/supabase/discussions/4815](https://github.com/orgs/supabase/discussions/4815) | `[DATA-2]` |
| Supabase RLS | anon / authenticated / service_role roles. Explicit warning: "Supabase provides special 'Service' keys, which can be used to **bypass RLS**. These should never be used in the browser or exposed to customers." Perf: wrap in `(select auth.uid())` — "94.97% improvement"; index policy columns; always use `TO role` | [supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security) | `[DATA]` |
| Supabase column encryption | **Supabase recommends against it**: "Supabase does not recommend using either Server Key Management or Transparent Column Encryption on the Supabase platform due to their high level of operational complexity and misconfiguration risk." pgsodium is pending deprecation; column encryption removed from the dashboard because it "has sharp edges" and caused "unrecoverable issues" | [pgsodium docs](https://supabase.com/docs/guides/database/extensions/pgsodium), [discussion #27109](https://github.com/orgs/supabase/discussions/27109), [discussion #18849](https://github.com/orgs/supabase/discussions/18849) | `[DATA]` |
| Supabase pg_cron | Enabled on free/pro/team | [supabase.com/docs/guides/cron](https://supabase.com/docs/guides/cron) | `[DATA-2]` |
| Postgres RLS semantics | "Superusers and roles with the `BYPASSRLS` attribute always bypass the row security system... Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`." PERMISSIVE = OR, RESTRICTIVE = AND. "Referential integrity checks, such as unique or primary key constraints and foreign key references, **always bypass row security**" | [postgresql.org/docs/current/ddl-rowsecurity](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | `[DATA]` |
| GitHub Free — private repos | Includes: Community Support, **Dependabot alerts**, 2,000 Actions minutes/month, 500 MB Packages storage, 120 Codespaces core-hours. **Does not list** Dependabot security updates, secret scanning, push protection, code scanning, protected branches, rulesets, or required reviewers for private repos | [docs.github.com/…/githubs-plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) | `[DATA]` |
| GitHub branch protection / rulesets | "Protected branches are available in public repositories with GitHub Free… also available in public **and private** repositories with GitHub Pro, Team, Enterprise." Same for rulesets. → **No branch protection on a private repo on Free** | [docs.github.com about-protected-branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) | `[DATA]` |
| GitHub Actions billing | 2,000 minutes/month + 500 MB artifact storage on Free; minutes do not apply to public repos; **"If your account does not have a valid payment method on file, usage is blocked once you use up your quota"** → no surprise bill | [about-billing-for-github-actions](https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions) | `[DATA]` |
| Resend free | **3,000 emails/month AND "limited to 100 emails per day"**; 1 domain; 30-day data retention | [resend.com/pricing](https://resend.com/pricing) | `[DATA]` |
| Brevo free | ~300 emails/day reported (≈9,000/mo). **Could not fetch brevo.com/pricing — page returned no readable plan content.** | secondary only | **UNVERIFIED** |
| **M365 SMTP AUTH** | SMTP AUTH is **disabled by default** when Security Defaults are on, and disabled by default for new accounts created 2025–2026; enabling it requires tenant/Exchange admin. Basic auth for SMTP being turned off by default from Sept 2025 / Dec 2026 | [learn.microsoft.com authenticated-client-smtp-submission](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission) | `[DATA]` |
| **VirusTotal free API** | "The Public API is limited to **500 requests per day** and a rate of **4 requests per minute**." **"The Public API must not be used in commercial products or services."** Noncompliance → "immediate permanent ban" | [docs.virustotal.com/reference/public-vs-premium-api](https://docs.virustotal.com/reference/public-vs-premium-api) | `[DATA]` |
| India holidays — `date-holidays` npm | Code **ISC**; data **CC BY-SA 3.0**; India (IN) included with 28 state/UT subdivisions; rules in YAML compiled to JSON. Caveat in README: "islamic dates might not be correct as they are subject to the sighting of the moon" | [github.com/commenthol/date-holidays](https://github.com/commenthol/date-holidays) | `[DATA]` |
| India holidays — Nager.Date | Free REST API, no auth, IN supported, ~121 countries, subdivision detail, business-day helpers. "does not impose any rate limits" per aggregator write-ups | [date.nager.at/Api](https://date.nager.at/Api) | `[DATA-2]` |
| **CERT-In Directions 28-Apr-2022** | "All service providers, intermediaries, data centres, body corporate and Government organisations shall mandatorily **enable logs of all their ICT systems and maintain them securely for a rolling period of 180 days and the same shall be maintained within the Indian jurisdiction**." Cyber incidents reportable to CERT-In **within 6 hours** of becoming aware. Effective 27-Jun-2022 | [cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf](https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf) | `[DATA]` |
| DPDP Rules, 2025 | Notified **14-Nov-2025**; phased compliance with an ~18-month runway; Schedule-1 penalties (up to ₹250 crore) effective **13-May-2027** | [PIB press release PRID 2190014](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190014); [Wikipedia: DPDP Rules 2025](https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025) — **PIB page returned 403; the PIB PDF was image-based and not text-extractable** | `[DATA-2]` |
| SEBI CSCRF | Circular SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113 dated 20-Aug-2024; clarifications circular SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2025/60 dated 30-Apr-2025. Portfolio Managers: **Mid-size ≥ ₹10,000 cr; Small-size > ₹3,000 cr and < ₹10,000 cr; Self-certification ≤ ₹3,000 cr** (no Qualified tier for PMs). Standalone Investment Advisers exempt unless registered in another capacity. Self-certification REs exempt from periodic CERT-In-empanelled cyber audit; PMs in self-certification with <100 clients exempt from mandatory Market-SOC. Self-certification compliance date cited as 30-Jun-2025 | [sebi.gov.in circular index](https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html); [APMI-hosted clarifications PDF](https://www.apmiindia.org/storagebox/images/Circulars/Clarifications%20on%20CSCRF%20for%20SEBI%20Regulated%20Entities%20-%2030th%20April'25.pdf) — **both PDFs were binary/image and not text-extractable; thresholds come from secondary write-ups** | `[DATA-2]` |
| Crypto-shredding as erasure | Concept is sound and widely used. Claims that EDPB Guidelines 5/2019, the UK ICO and CNIL "explicitly recognize cryptographic erasure" appear only in **vendor blogs** in my searches. **UNVERIFIED against the regulators' own text.** Do not put that claim in a compliance document without checking the primary guidance | vendor blogs only | **UNVERIFIED** |

---

## PART A — FEATURES

### A.0 The triage rule I applied
A feature earns V1 only if **its absence forces someone to keep a parallel spreadsheet**. That is the whole point of the app: kill the shadow tracker. Everything else waits. `[OPINION]`

A 50-person wealth manager's ticket app fails for one of three reasons, in this order: (a) people stop punching because punching is slow, (b) the deadline logic is wrong so nobody trusts "overdue", (c) a manager can't get a one-screen answer on Monday morning. Feature triage should optimise exactly those three. `[OPINION]`

---

### A.1 V1 — build now

#### Ticket core
```
tickets
  id              uuid pk default gen_random_uuid()
  ref             text unique         -- 'TKT-2026-0143', human-quotable; generated from a sequence
  title           text not null       -- searchable, NOT encrypted (see B.1)
  body            text                -- markdown; NOT encrypted; policy: no client PII
  ticket_type     text not null       -- enum, 6 values max (see below)
  priority        smallint not null   -- 1=P1,2=P2,3=P3
  raiser_id       uuid not null references employees(id)
  assignee_id     uuid not null references employees(id)
  due_date        date not null       -- DATE, not timestamptz. See A.2
  client_ref_enc  bytea               -- opaque code, envelope-encrypted (B.1)
  client_ref_bidx bytea               -- blind index for equality lookup (B.1)
  state           text not null       -- see state machine
  reopen_count    smallint not null default 0
  created_at      timestamptz not null default now()
  first_closed_at timestamptz         -- for honest cycle-time
  closed_at       timestamptz         -- last close
  created_by_ip_hash bytea            -- HMAC, not raw IP (see B.7)
```

- **Types: exactly six, hard-coded.** e.g. `CLIENT_OPS`, `COMPLIANCE`, `REPORTING`, `DATA_OPS`, `INTERNAL`, `OTHER`. A user-editable type taxonomy is a V2 trap — it fragments reporting within a month. `[OPINION]`
- **Priority: exactly three.** P1/P2/P3. Five levels means everything is P2. `[OPINION]`
- **Single assignee, always.** Shared ownership = no ownership. Watchers (V2) cover "keep me informed".
- **`ref` is load-bearent** — people will paste "TKT-2026-0143" into email and chat. Generate it server-side from a Postgres sequence, never from a count.

**State machine (V1) — enforce in a DB trigger, not just in code:**
```
OPEN → IN_PROGRESS → DONE
OPEN|IN_PROGRESS → BLOCKED → IN_PROGRESS
OPEN|IN_PROGRESS → AWAITING_INPUT → IN_PROGRESS
OPEN|IN_PROGRESS|BLOCKED|AWAITING_INPUT → CANCELLED
DONE|CANCELLED → REOPENED → IN_PROGRESS
```
Six states. `AWAITING_INPUT` is distinct from `BLOCKED` on purpose: `AWAITING_INPUT` means "waiting on a named person", `BLOCKED` means "cannot proceed at all". They behave differently in SLA maths (V2) and in the manager's Monday view.

#### The status "punch" — the heart of the app
```
punches
  id              uuid pk
  ticket_id       uuid not null references tickets(id)
  seq             int  not null            -- per-ticket ordinal, unique(ticket_id, seq)
  author_id       uuid not null references employees(id)
  from_state      text not null
  to_state        text not null
  body            text not null            -- the update; required, min 10 chars
  blocked_reason  text                     -- REQUIRED iff to_state='BLOCKED'
  waiting_on_id   uuid                     -- REQUIRED iff to_state='AWAITING_INPUT'
  next_action     text                     -- REQUIRED unless to_state in (DONE, CANCELLED)
  next_action_by  date                     -- optional
  minutes_spent   int                      -- optional, self-reported, honest-effort field
  created_at      timestamptz not null default now()
  unique (ticket_id, seq)
```
**Append-only, enforced at the DB level, not in the ORM:**
```sql
REVOKE UPDATE, DELETE ON punches FROM app_user, authenticated, anon;
CREATE OR REPLACE FUNCTION punches_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'punches are append-only (attempted % on id=%)', TG_OP, OLD.id; END $$;
CREATE TRIGGER punches_no_mutate BEFORE UPDATE OR DELETE ON punches
  FOR EACH ROW EXECUTE FUNCTION punches_immutable();
```
Corrections happen by **adding a punch that supersedes**, with `body` starting `CORRECTION:`. Never by editing. This is the single most important design property for a regulated firm — the record of *what was known when* is the thing an auditor or an unhappy client actually asks for. `[OPINION]`

- **Required fields per status** (as above) are the mechanism that makes the log useful instead of a wall of "working on it". Enforce with a `CHECK` constraint, not client-side validation:
```sql
ALTER TABLE punches ADD CONSTRAINT punch_required_fields CHECK (
     (to_state <> 'BLOCKED'        OR blocked_reason IS NOT NULL)
 AND (to_state <> 'AWAITING_INPUT' OR waiting_on_id  IS NOT NULL)
 AND (to_state IN ('DONE','CANCELLED') OR next_action IS NOT NULL)
 AND length(btrim(body)) >= 10
);
```
- **Reassignment = a punch with a mandatory handover note.** Store `reassign_from_id`/`reassign_to_id` on the punch. A reassignment with an empty handover note is the #1 way work silently dies. `[OPINION]`
- **Reopen semantics:** `REOPENED` requires a reason in `body`; `reopen_count` increments; `first_closed_at` is never overwritten. Report both "cycle time to first close" and "cycle time to final close" — if you only report one, report the second, because the first is the number people game. `[OPINION]`

#### Deadlines done properly (this is where most in-house trackers are quietly wrong)
1. **Store `due_date` as `DATE`, not a timestamp.** A deadline of "3 Aug" is a calendar fact, not an instant. Storing `2026-08-03T00:00:00Z` guarantees a 5.5-hour bug. `[INFERENCE]`
2. **Store all event times as `timestamptz`** (Postgres stores UTC) and convert on read.
3. **Never compute "today" or "overdue" on the client.** One SQL expression, used everywhere:
```sql
-- server-side IST today
CREATE OR REPLACE FUNCTION ist_today() RETURNS date LANGUAGE sql STABLE AS
$$ SELECT (now() AT TIME ZONE 'Asia/Kolkata')::date $$;

-- never store is_overdue; derive it
CREATE VIEW ticket_view AS
SELECT t.*,
       (t.closed_at IS NULL AND t.due_date <  ist_today()) AS is_overdue,
       (t.closed_at IS NULL AND t.due_date =  ist_today()) AS is_due_today,
       (t.due_date - ist_today())                          AS days_to_due
FROM tickets t;
```
   Deriving instead of storing **eliminates the midnight bug entirely** — there is no nightly job that must fire at 00:00 IST for the dashboard to be right. `[INFERENCE]` This is the cheapest correctness win in the whole app.
4. **India has no DST** — one class of bug you get for free. `[DATA]`
5. **Cron offset trap:** Cloudflare Cron Triggers are UTC. 09:00 IST = **03:30 UTC**. A half-hour offset breaks naive `0 * * * *` scheduling. Write `30 3 * * *`, and put a comment saying why. `[INFERENCE]`
6. **Working-day arithmetic — own the calendar, don't call an API at request time.**
```
holidays
  d           date primary key
  label       text not null
  kind        text not null   -- 'GAZETTED' | 'EXCHANGE' | 'FIRM'
  source_note text not null   -- provenance: which circular/page, and who confirmed
  added_by    uuid, added_at timestamptz
```
```sql
CREATE OR REPLACE FUNCTION add_working_days(start_d date, n int) RETURNS date
LANGUAGE plpgsql STABLE AS $$
DECLARE d date := start_d; left_n int := n;
BEGIN
  WHILE left_n > 0 LOOP
    d := d + 1;
    IF extract(isodow from d) < 6
       AND NOT EXISTS (SELECT 1 FROM holidays h WHERE h.d = d) THEN
      left_n := left_n - 1;
    END IF;
  END LOOP;
  RETURN d;
END $$;
```
   **Where to get the calendar free, and how to keep it current:**
   - **Primary for this firm: the NSE trading-holiday list.** A wealth manager's operational deadlines track *market* days, not DoPT gazetted days (settlement, NAV, cut-offs). NSE publishes it annually; it is free and the firm already consumes NSE archives. → seed `kind='EXCHANGE'`. `[OPINION]`
   - **Secondary: DoPT gazetted list** via `india.gov.in/calendar` for actual office closures. `[DATA-2]`
   - **Code libraries (free, permissive):** `date-holidays` (code ISC, data CC BY-SA 3.0, IN + 28 subdivisions) `[DATA]`; **Nager.Date** REST API (no auth, IN supported, business-day helpers) `[DATA-2]`.
   - **My recommendation: do not depend on any of them at runtime.** Use one of them *once a year* to pre-populate, then have a named human (admin) confirm and lock the year in the `holidays` table. Indian floating holidays (moon-sighting-dependent Islamic dates — the `date-holidays` README warns about exactly this `[DATA]`), state-specific days, and firm-declared closures are things no free API gets right for *your* office. A ~15-minute annual admin task beats a silent wrong deadline. `[OPINION]`
   - Add an **admin nag**: if `max(d) from holidays where extract(year from d) = ist_today() year + 1` is null after 15-Dec, show a banner. Cheap, prevents the January surprise.
7. **Deadline changes are logged, immutably, with a reason — V1.** Approval workflow is V2.
```
due_date_changes
  id uuid pk, ticket_id uuid, old_due date, new_due date,
  reason text not null CHECK (length(btrim(reason)) >= 10),
  changed_by uuid, changed_at timestamptz default now(),
  approved_by uuid null, approved_at timestamptz null   -- V2 fills these
```
   Report `net_days_slipped = sum(new_due - old_due)` per person. This one number is more informative than on-time % because on-time % is trivially gamed by moving the date. **Show both, side by side, always.** `[OPINION]`

#### Views (V1)
- **My Tickets** — default landing, grouped: Overdue / Due today / This week / Later / Blocked.
- **Team board** — kanban by state, swimlanes by assignee. Manager and admin only.
- **Overdue & ageing report** — buckets 0–3 / 4–7 / 8–14 / 15+ days past due.
- **Per-person load** — open count and count-by-priority per assignee. Not "capacity" (that needs estimates nobody will enter honestly). `[OPINION]`
- **Full-text search** — Postgres native, free, no extra service:
```sql
ALTER TABLE tickets ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,''))) STORED;
CREATE INDEX tickets_fts_idx ON tickets USING gin(fts);
```
  Use `'simple'` not `'english'` — Indian names and firm jargon stem badly under the English dictionary. `[OPINION]`
- **Saved filters = URL query params.** Bookmarkable, zero storage, zero code. Ship this instead of a saved-views table. `[OPINION]`

#### Reporting (V1)
- Per-person: open count, closed-in-period, **on-time %** (closed on/before *original* due date and closed on/before *current* due date — two columns), median cycle time, net days slipped, punch cadence (median days between punches on open tickets — this is the "is this person actually updating?" metric).
- **CSV export** in V1 (a `Response` with `text/csv`, ~15 lines of code). **Excel export is V2** (SheetJS/`exceljs` adds bundle weight against the **3 MiB compressed** free Worker limit `[DATA]`).
- Ageing/overdue report, exportable.

#### Notifications (V1) — the email quota is the binding constraint
This is the sharpest cost constraint in the whole feature set and it is easy to miss:

- Resend free = **3,000/month AND 100/day** `[DATA]`. Fifty employees × one daily digest = **50 emails/day = half your daily quota**, before a single manager summary, assignment alert, or breach escalation. Add assignment notifications and you blow 100/day in a week.
- You **cannot** fall back on the company mail server: M365 SMTP AUTH is off by default and enabling it needs tenant admin, which the brief says you don't have `[DATA]`.
- Cloudflare Access sends the **login** emails itself, off your quota `[DATA]` — so protect the remaining quota for digests only.

**Therefore, V1 notification design:**
1. **In-app notification centre is the primary channel** — a `notifications` table, unread badge, zero marginal cost, no quota. This is V1's real answer.
2. **One email per user per day, maximum, and only if they have something actionable** (overdue, due today, newly assigned, or blocked-on-them). Suppress empty digests — that alone typically halves volume. `[INFERENCE]`
3. **One manager summary email per day.** So worst case ≈ 50 + 5 = 55/day, inside Resend's 100/day. But it is a 55% utilisation with no headroom — so:
4. **Ship a send-budget guard, not hope.** A `email_send_log` table, a hard daily counter, and a priority ordering: escalations > overdue digests > routine digests. When the budget is exhausted, drop routine digests and record the drop. Never let a quota overrun silently swallow an escalation email. `[OPINION]`
5. **Verify Brevo's current free limits before choosing** (reported ~300/day; I could not read Brevo's own pricing page — **UNVERIFIED**). If confirmed, Brevo's higher daily ceiling is worth the slightly worse DX for exactly this reason.
6. Set SPF/DKIM/DMARC on whatever sending domain you use — otherwise digests land in Junk and the app is dead in three weeks. Use a **subdomain** (`notify.<firm>.in`) so app sending cannot damage the corporate domain's reputation. Note: adding those DNS records may itself need whoever runs the firm's DNS. `[OPINION]`

#### Attachments (V1) — **links only. Do not accept uploads.**
This is a firm recommendation, and the reason is a verified legal/ToS wall, not squeamishness:
- **There is no zero-cost, commercially-licensed virus scanning.** VirusTotal's free Public API explicitly states "The Public API must not be used in commercial products or services", 500 req/day, 4 req/min, and threatens "immediate permanent ban" `[DATA]`. An internal app at a for-profit SEBI-registered firm is a commercial service. ClamAV is free software but needs a long-running host with a ~1 GB signature DB — Cloudflare Workers cannot run it and you have no free host that can. `[INFERENCE]`
- Storage itself is not the problem (R2 gives 10 GB free with free egress `[DATA]`). **Scanning and PII containment are.** The moment you accept uploads, a client's KYC PDF ends up in the ticket store, and your carefully-scoped "no client PII, only `client_ref`" design collapses. `[INFERENCE]`
- **V1 policy, stated in the UI at the point of use:** paste a link to the firm's existing sanctioned store (SharePoint / Google Drive / the ops share), where the company's own AV, DLP and retention already apply. Store the URL + a one-line description. Validate the host against an allow-list of firm domains so nobody links to a personal Drive.
- **If uploads are ever added (V2), the minimum bar:** R2 bucket, 10 MB cap, extension allow-list, **server-side magic-byte sniffing** (never trust `Content-Type`), rename to a UUID (never the user's filename), serve only through a Worker on a **separate hostname** with `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff`, and a signed short-TTL URL. And write down, explicitly, that files are unscanned. `[OPINION]`

#### Admin (V1)
- **Allow-list = the `employees` table**, and it must be the *same* list that drives the Cloudflare Access policy. Two lists drift; drift is how an ex-employee keeps access. **Concrete design: the app's employee table is the source of truth, and a Worker cron pushes it to the Access policy via the Cloudflare API** (an Access group of type "emails"), then reads it back and alarms on mismatch. This closes the single most likely real-world access failure. `[OPINION]`
- **Never hard-delete an employee row.** `status ∈ {ACTIVE, SUSPENDED, EXITED}`, `exited_at`, `exit_reason`. Foreign keys from `punches.author_id` mean a delete would orphan the audit trail; and the trail is the point. Deactivation = removed from Access allow-list + `status='EXITED'` + all open tickets forced into a reassignment queue.
- **Three roles only: `user`, `manager`, `admin`.** A permission matrix for 50 people is unfunded complexity. `[OPINION]`
- **Access review report (V1, and it is cheap):** a single page listing every ACTIVE employee, their role, last login, last punch, and whether they are in the live Access policy — with a "reviewed by / on" sign-off row that writes to the audit chain. Quarterly. This is the artefact a SEBI-facing auditor asks for and it takes an afternoon to build. `[OPINION]`
- **Impersonation: do not build it. Ever.** `[OPINION]` It is the single feature most likely to destroy the evidentiary value of the append-only log — the moment an admin can punch as someone else, no punch can be attributed with confidence. The legitimate need behind "let me see what they see" is satisfied by a **read-only "view as" report** that renders another user's dashboard *without any write path* and writes an audit event each time it is used. If a punch genuinely must be entered on someone's behalf, the admin punches as themselves with `on_behalf_of_id` set — visible in the UI as "Admin X recorded for Y".

#### Delivery (V1)
- **Mobile-responsive web, no PWA, no offline.** `[OPINION]` The punch flow is 3 fields; it works fine in a mobile browser. Offline punching means a client-side queue, clock-skew-tolerant ordering, and conflict resolution against an *append-only, sequence-numbered* log — that is a genuinely hard distributed-systems problem, for a benefit (punching from a basement with no signal) that 50 office-based employees will use approximately never. **Explicit NEVER.**
- Add a web-app-manifest + icons only if someone asks for a home-screen icon (30 minutes, no offline logic).

---

### A.2 V2 — later, in this order

| # | Feature | Why it waits | Trigger to build it |
|---|---|---|---|
| 1 | **SLA clocks per priority, pause on BLOCKED/AWAITING_INPUT** | Needs real punch data to calibrate; guessing SLAs day 1 produces noise everyone learns to ignore | After 6–8 weeks of real punches you can set SLAs from observed p75 |
| 2 | **Auto-escalation on breach + escalation matrix** | Depends on #1. Also consumes email quota | Once SLAs are calibrated and email budget guard is proven |
| 3 | **Watchers** | Nice, not load-bearing. Adds notification fan-out (quota!) | When someone actually complains they weren't kept informed |
| 4 | **Checklists / ticket templates per type** | Real value for recurring compliance work. Needs the type taxonomy to settle first | When the same 6-step checklist appears in 3+ ticket bodies |
| 5 | **Recurring tickets** | Genuinely valuable for monthly/quarterly compliance cadences. Needs the holiday calendar and a reliable cron (both V1 assets) | Once ≥5 recurring obligations are being manually re-raised |
| 6 | **Deadline-change approval** (manager must approve a slip) | V1 logs the reason, which is 80% of the value | If `net_days_slipped` shows the log alone isn't deterring slips |
| 7 | **Calendar view** | Pretty; the "due today / this week" list already answers the question | On request |
| 8 | **Bulk operations** | Dangerous before RLS + audit chain are battle-tested; a bulk mistake writes 200 audit rows | After 3 months of stable single-item ops |
| 9 | **Excel export** (SheetJS/exceljs) | Bundle size vs the 3 MiB compressed Worker limit `[DATA]` | If CSV genuinely isn't enough — consider generating in a GitHub Action instead of the Worker |
| 10 | **TOTP step-up for admin actions** (`otplib` + `@otplib/plugin-crypto-web`, edge-compatible `[DATA-2]`) | Access OTP is already a possession factor; step-up matters once admin can do destructive things | Before bulk ops or crypto-shred are exposed in the UI |
| 11 | **Teams webhook** (incoming webhook to one ops channel) | Free, no quota, and it *reduces* email pressure | Only if the firm is on Teams and someone will own the channel |
| 12 | **Attachments in R2** | Only with the full hardening in A.1, and only after the PII question (below) is resolved | Never, ideally |
| 13 | **Passkeys / WebAuthn** (SimpleWebAuthn) | See B.5 — real work, marginal gain over Access OTP | If the firm outgrows Access free seats and you must build auth yourself |
| 14 | **DSAR self-service export** | Manual export by admin is fine at 50 employees | If DSAR volume ever exceeds ~1/quarter |

---

### A.3 NEVER — explicit YAGNI list (write this list into the repo README so it survives you)

| Not building | Why |
|---|---|
| **Impersonation / login-as** | Destroys attribution in an append-only log. Read-only "view as" instead. `[OPINION]` |
| **Offline punch / sync queue** | Conflict resolution against a sequenced append-only log for a benefit nobody needs. `[OPINION]` |
| **Start/stop time tracking** | Self-reported `minutes_spent` on the punch captures 90% of the value. Timers get left running and the data becomes garbage that people then argue about. `[OPINION]` |
| **Gantt / dependencies / parent-subtask trees** | This is a *ticketing* app for deadline accountability, not a project planner. Dependencies double the state space and the "blocked by" relationship is already captured by `BLOCKED` + `blocked_reason`. If two tickets truly depend on each other, one line of free text says so. `[OPINION]` |
| **User-defined custom fields / workflow builder** | The classic in-house-tool death spiral: you end up maintaining a worse Jira with one developer who is also an APM. `[OPINION]` |
| **Per-user permission matrix / custom roles** | Three roles. 50 people. `[OPINION]` |
| **Email-to-ticket ingestion** | Inbound mail parsing, spoofing, threading, attachment extraction — enormous surface for a firm whose email platform is unknown and where the whole design depends on keeping client PII *out*. `[OPINION]` |
| **WhatsApp notifications** | WhatsApp Business API is not free-forever, and routing work-record notifications through WhatsApp creates a records-retention problem the firm does not want. `[OPINION]` |
| **Client-facing portal / external raisers** | Instantly puts client PII and possibly client identity in scope, and breaks the Cloudflare-Access-in-front model (external users aren't on your allow-list). Separate product, separate decision. `[OPINION]` |
| **Threaded comments/chat** | Punches *are* the comments. A parallel discussion channel that isn't part of the append-only record is exactly the failure the app exists to fix. `[OPINION]` |
| **AI summarisation of tickets** | Ships firm work-product to a third-party model. Not at ₹0, not without a DPA, not in V1. `[OPINION]` |
| **SSO / SAML config** | No tenant admin (given). Access OTP replaces it. `[DATA]` |
| **Hard delete of anything** | Everything is soft-state + audit chain. |
| **Storing client names, PAN, phone, email, folio, or account numbers — anywhere** | This is the load-bearing scope decision. Enforce it (see B.7). |

---

## PART B — SECURITY ARCHITECTURE

### B.0 Recommended stack, and one architecture decision that changes everything

```
Browser
  │  (only path in — apex + www; NO workers.dev route)
  ▼
Cloudflare Access  ← email one-time-PIN, allow-list = Access group synced from employees table
  │                  Cloudflare sends the OTP email (costs you no quota)
  │  adds Cf-Access-Jwt-Assertion
  ▼
Cloudflare Worker (Next.js via OpenNext, Node.js runtime)
  │  1. verify JWT against https://<team>.cloudflareaccess.com/cdn-cgi/access/certs  ← FAIL CLOSED
  │  2. resolve email → employees row; reject if status <> 'ACTIVE'
  │  3. mint a short-lived Supabase-compatible JWT (sub = employee.id, role = authenticated)
  │  4. all DB access via that JWT → RLS applies → defence in depth
  ▼
Supabase Postgres (region ap-south-1 / Mumbai)  ← RLS on every table, FORCE ROW LEVEL SECURITY
  │
  ├─ hash-chained audit_log (append-only, DB-enforced)
  └─ nightly: GitHub Actions → pg_dump → age-encrypt → R2 + Actions artifact
```

**Why Supabase Postgres and not Cloudflare D1:** D1's only data-localisation jurisdictions are `eu` and `fedramp` — **India is not available** `[DATA]`. CERT-In's 2022 Directions require ICT-system logs to be "maintained within the Indian jurisdiction" for a rolling 180 days `[DATA]`. Supabase can be pinned to `ap-south-1` (Mumbai) `[DATA-2]`. For a SEBI-regulated entity that is not a close call. `[INFERENCE]` (Caveat: pinning the *primary* region does not by itself prove where every replica/log lives — confirm with Supabase and record the answer in the DPDP/CSCRF file. Also note Cloudflare terminates TLS globally; Access authentication logs are Cloudflare-side. Flag both to compliance rather than asserting full residency.) `[OPINION]`

**The single most important control, and it is one line of config:** Cloudflare Access enforces on a **hostname**. A Worker is *also* reachable at `<name>.<subdomain>.workers.dev` unless you turn that off. If you leave it on, your entire authentication layer is bypassed by a URL nobody had to guess hard. **Disable `workers.dev` for the Worker (`workers_dev = false` in `wrangler.toml`), serve only on the custom hostname, and make the JWT check fail closed so that even if the route leaks, requests without a valid Access JWT get a 403 with no body.** `[INFERENCE]` Add an automated test that hits the workers.dev URL and asserts non-200.

**Corollary — do not build an app session layer.** With Access in front, identity is re-asserted on every request by a signed JWT. Building a second cookie session on top of that gives you two sources of truth and a new class of bug (Access session revoked, app session still alive). Configure session duration in the Access application policy; use Access's own "revoke user session" for offboarding. If you later must build your own auth (>50 seats), B.4 below is the spec. `[OPINION]`

---

### B.1 Field-level encryption — do it narrowly, and be honest about the cost

**Which approach:** **WebCrypto `AES-256-GCM` in the Worker.** `[DATA]` It is built into the runtime (no dependency, no bundle weight against the 3 MiB limit), and Workers even ship `crypto.subtle.timingSafeEqual()` for the comparisons you'll need `[DATA]`.

**What NOT to use, and why:**
- **pgsodium / Supabase Transparent Column Encryption: rejected.** Supabase itself says it "does not recommend using either Server Key Management or Transparent Column Encryption on the Supabase platform due to their high level of operational complexity and misconfiguration risk", pgsodium is pending deprecation, and column encryption was pulled from the dashboard because it "has sharp edges" and caused "unrecoverable issues" `[DATA]`. Building your compliance story on a deprecated extension the vendor warns against is a trap.
- **`pgcrypto` with the key passed in SQL: rejected.** The key travels in the query text and lands in `pg_stat_statements` and query logs. `[INFERENCE]`
- **libsodium (WASM): unnecessary.** WebCrypto covers AES-GCM/HMAC/HKDF natively `[DATA]`; a WASM blob costs bundle size you don't have.
- **Supabase Vault: use it for *secrets*, not for row data.** Vault stores encrypted secrets and survives the pgsodium deprecation (interface unchanged) `[DATA]`.

**Envelope design (two DEK tiers — this shape is chosen to make crypto-shredding actually work):**
```
KEK  = 32 random bytes, stored ONLY as a Cloudflare Worker secret (KEK_V2). Never in the DB, never in git.
       Workers secrets are "encrypted text values" and "not visible within Wrangler or Cloudflare
       dashboard after you define them" [DATA].

Tier 1 — IDENTITY DEK, one per employee (the erasure unit)
   wraps: employees.full_name, personal_email, phone, and any free-text the employee may later
          ask to be removed
Tier 2 — CONTENT DEK, one per generation (rotating), shared
   wraps: tickets.client_ref  (and nothing else, in V1)

dek_keyring
  id           uuid pk
  tier         text not null            -- 'IDENTITY' | 'CONTENT'
  subject_id   uuid null                -- employee id for IDENTITY, null for CONTENT
  generation   int  not null
  kek_version  int  not null            -- which KEK wrapped this DEK
  wrapped_dek  bytea not null           -- AES-GCM(KEK, dek): iv || ciphertext || tag
  created_at   timestamptz not null default now()
  shredded_at  timestamptz null         -- set when wrapped_dek is overwritten with zeros
  unique (tier, subject_id, generation)
```
**Ciphertext column format — version it from day one** (you will regret a bare blob):
```
bytea = 0x01 || kek_version(u8) || dek_generation(u16 BE) || iv(12 bytes) || ciphertext||tag
AAD (additional authenticated data) = utf8("<table>|<column>|<row_uuid>")
```
Binding the row id into the **AAD** is the bit people skip: without it, an attacker with write access can copy ciphertext from row A into row B and it still decrypts. With it, GCM authentication fails. `[INFERENCE]`

```js
// Worker — encrypt
const aad = new TextEncoder().encode(`tickets|client_ref|${ticketId}`);
const iv  = crypto.getRandomValues(new Uint8Array(12));
const ct  = await crypto.subtle.encrypt(
  { name: 'AES-GCM', iv, additionalData: aad, tagLength: 128 }, dekKey, plaintextBytes);
```
**Never reuse an (iv, key) pair.** 12 random bytes per encryption from `crypto.getRandomValues` is the standard, safe construction for AES-GCM at this volume. `[INFERENCE]`

**Rotation, and what breaks:**
- **KEK rotation is cheap** — it only re-wraps DEKs. Keep `KEK_V1` and `KEK_V2` as two secrets simultaneously; a job reads each `wrapped_dek`, unwraps with `kek_version`, re-wraps with the new KEK, bumps `kek_version`. **No row data is touched.** Delete `KEK_V1` only after `SELECT count(*) FROM dek_keyring WHERE kek_version = 1` is zero. This is exactly why the envelope exists.
- **DEK rotation is expensive** — it requires rewriting every ciphertext. Don't; instead start a new `generation` for new writes and leave old rows on the old generation (that's what `dek_generation` in the ciphertext header is for). Old generations stay readable until you deliberately shred them.
- **What breaks if you lose the KEK: everything encrypted, permanently.** There is no recovery. Mitigation: KEK escrow — print the KEK (base64) and seal it in the firm's physical document safe, and/or split it with Shamir among two directors. **A single Workers secret is a single point of catastrophic loss.** Any "encrypt everything" plan without a written, tested escrow is worse than no encryption because it will lose the firm its own records. `[OPINION]`

**The honest cost — what you can no longer do with an encrypted column:**
| Capability | Randomised AES-GCM | Deterministic | Blind index |
|---|---|---|---|
| Equality lookup (`WHERE col = ?`) | ✗ | ✓ | ✓ |
| `ORDER BY`, range, `<`/`>` | ✗ | ✗ | ✗ |
| `LIKE` / prefix / substring | ✗ | ✗ | ✗ |
| Full-text search | ✗ | ✗ | ✗ |
| `GROUP BY` / distinct count | ✗ | ✓ (leaks) | ✓ (leaks) |
| B-tree index useful | ✗ | ✓ | ✓ |
| Leaks which rows share a value | ✗ | ✓ | ✓ |

**Blind index (the only practical way to keep equality search):**
```
client_ref_bidx = leftmost 16 bytes of HMAC-SHA256( BIDX_KEY, NFKC(upper(trim(client_ref))) )
```
`BIDX_KEY` is a *separate* Worker secret from the KEK. Truncating to 16 bytes is a deliberate trade: it creates a few collisions, which slightly blurs frequency analysis, and you filter false positives after decrypting the small candidate set. `[INFERENCE]` **Be clear-eyed: a blind index leaks equality and frequency.** If `client_ref` values are drawn from a small guessable space, an attacker with the DB and a guess list can build a rainbow table of blind indexes — unless they lack `BIDX_KEY`, which is the whole point of keying it. So: **keyed HMAC, never a plain hash.**

**Therefore, my recommendation on scope — encrypt these and nothing else in V1:**
1. `tickets.client_ref` (+ blind index) — the one field most likely to be regulatorily sensitive.
2. `employees.full_name`, `personal_email`, `phone` (identity DEK) — the crypto-shred unit.
3. `punches.body` **only if** a "private note" flag exists; the default punch body stays plaintext.

**Explicitly do NOT encrypt** `tickets.title`, `tickets.body`, or `punches.body` in general. Encrypting them destroys full-text search, which is a feature people will use twenty times a day, in exchange for protection against a threat (DB dump theft) that is *already* mitigated by Supabase's at-rest encryption plus the fact that the app can decrypt anyway. Instead, enforce "no client PII in free text" by policy + a lightweight regex tripwire (PAN pattern `[A-Z]{5}[0-9]{4}[A-Z]`, 10-digit mobile, 12-digit Aadhaar, `@` email pattern) that **warns the author before submit and flags the punch for review**. A soft nudge at write time changes behaviour far more than encryption does. `[OPINION]`

---

### B.2 Tamper-evident audit log — concrete design

```sql
CREATE TABLE audit_log (
  seq            bigserial PRIMARY KEY,
  ts             timestamptz NOT NULL DEFAULT clock_timestamp(),
  actor_id       uuid,                       -- null for system
  actor_email_h  bytea NOT NULL,             -- HMAC-SHA256(AUDIT_HMAC_KEY, lower(email)); never raw
  action         text NOT NULL,              -- 'ticket.create','punch.append','due.change',
                                             -- 'employee.deactivate','role.change','key.shred',
                                             -- 'export.csv','viewas.open','access.review.signoff'
  entity         text NOT NULL,
  entity_id      uuid,
  payload_sha256 bytea NOT NULL,             -- hash of the canonical payload (payload itself may be
                                             -- stored in payload_json, or omitted if sensitive)
  payload_json   jsonb,
  req_id         uuid NOT NULL,              -- correlates all rows from one HTTP request
  ip_h           bytea,                      -- HMAC of IP, not the IP
  ua_h           bytea,
  prev_hash      bytea NOT NULL,             -- 32 bytes; genesis = 32 zero bytes
  row_hash       bytea NOT NULL              -- 32 bytes
);
```

**Exact hash input format — this must be byte-for-byte reproducible or the chain is worthless:**

```
canonical = JSON, UTF-8, NO whitespace, keys in THIS FIXED ORDER (not sorted — fixed),
            strings NFC-normalised, timestamps as RFC3339 with exactly 6 fractional digits and 'Z',
            bytea rendered as lowercase hex, nulls rendered as JSON null:

{"seq":<int>,"ts":"<RFC3339.uuuuuuZ>","actor_id":<"uuid"|null>,"actor_email_h":"<64hex>",
 "action":"<str>","entity":"<str>","entity_id":<"uuid"|null>,"payload_sha256":"<64hex>",
 "req_id":"<uuid>","ip_h":<"64hex"|null>,"ua_h":<"64hex"|null>,"prev_hash":"<64hex>"}

row_hash = SHA256( utf8(canonical) )
```
Design notes that matter:
- `prev_hash` is **inside** the hashed payload — that is what chains it. `[INFERENCE]`
- `seq` is inside the payload too, so a row cannot be renumbered.
- **Fixed key order, not alphabetical**, because "sorted" is ambiguous across languages/locales and you will have two implementations (the Worker that writes, and the verifier that reads). Write the order down once, in a shared constant, and add a golden-vector test:
  a hard-coded canonical string with a hard-coded expected SHA-256, asserted in CI forever.
- `payload_sha256` lets you hash *what happened* while keeping the payload out of the chain input — so you can later redact `payload_json` (e.g. crypto-shred) **without breaking the chain**. This is essential: a chain over the payload itself makes erasure impossible. `[INFERENCE]` This is the single design choice that reconciles "immutable audit log" with "right to erasure".

**Writing it — in the same transaction, serialised:**
```sql
CREATE OR REPLACE FUNCTION audit_append(...) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE prev bytea; canon text; new_seq bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('audit_log_chain'));   -- serialise chain appends
  SELECT row_hash INTO prev FROM audit_log ORDER BY seq DESC LIMIT 1;
  prev := coalesce(prev, repeat('\000',32)::bytea);
  new_seq := nextval('audit_log_seq_manual');
  canon := build_canonical(new_seq, ..., prev);                  -- must match the Worker's builder
  INSERT INTO audit_log(seq,...,prev_hash,row_hash)
  VALUES (new_seq,...,prev,digest(canon,'sha256'));
  RETURN new_seq;
END $$;
```
The **advisory lock** is not optional: two concurrent inserts both reading the same `prev_hash` fork the chain. At this app's volume the lock costs nothing. `[INFERENCE]`
Note `bigserial` + explicit sequence: a rolled-back transaction burns a sequence number and creates a *legitimate* gap. So the verifier must treat gaps as "investigate", not "proof of tampering" — **or** append rows outside the business transaction (an autonomous append via a separate connection) so gaps genuinely mean deletion. Pick one and document it; ambiguity here makes the whole control useless in an audit conversation. `[OPINION]`

**DB-level immutability:**
```sql
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_user, authenticated, anon, PUBLIC;
CREATE TRIGGER audit_no_mutate BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log
  EXECUTE FUNCTION raise_immutable();
```
**Be honest about the limit:** a Postgres superuser (which on a managed platform includes the vendor, and includes you via the SQL editor) can drop that trigger, rewrite rows, and recompute the whole chain. Hash-chaining alone does **not** protect against an attacker who controls the DB. That is exactly why you anchor. `[INFERENCE]`

**Anchoring (this is what makes it real):**
Daily at 03:30 UTC (09:00 IST), a Cloudflare Cron Trigger:
1. `SELECT seq, row_hash FROM audit_log ORDER BY seq DESC LIMIT 1` → `(N, H_N)`.
2. Verify the chain from the last anchor forward, in the Worker (independent implementation of `build_canonical`).
3. Publish the anchor to **three places outside the DB's blast radius**:
   - **A commit to a separate private GitHub repo `crm-audit-anchors`**, one line appended to `anchors.log`: `2026-08-03 seq=184213 root=9f3a...c1 count_today=412`. Git's own content addressing plus GitHub's commit timestamps make retroactive edits detectable, and the commit history is outside Supabase entirely.
   - **An email** to the compliance officer + the Principal with the same line.
   - **An R2 object** `anchors/2026-08-03.txt` (10 GB free, egress free `[DATA]`).
4. If verification fails, the job **pages loudly** (email to two humans) and writes nothing but the failure.

Now a DB admin who rewrites history must also rewrite a GitHub commit history they may not control, an email in two inboxes, and an R2 object. **Detection, not prevention** — but detection is what "tamper-evident" means, and it is achievable at ₹0. `[OPINION]`

**Detecting a deleted row:** (a) `seq` gap (with the caveat above), (b) `prev_hash` of row N+1 ≠ `row_hash` of row N, (c) the count between two daily anchors not matching `count_today`. Publishing the **daily row count** in the anchor is the cheap trick that catches deletion-plus-rechain within a day. `[INFERENCE]`

**A better version if you want it (V2):** a Merkle tree over each day's rows, publishing the day's root — the same idea as Certificate Transparency (RFC 6962) — which lets you prove a *single* record's inclusion without revealing the rest. Overkill for 50 users, but worth a line in the design doc so the auditor sees you knew. `[OPINION]`

---

### B.3 Postgres RLS — policies, and the trap

**Roles:** `user` (own tickets: raised by or assigned to), `manager` (own + direct/indirect reports), `admin` (all). Team structure via a closure so "manager sees team" works for nested teams:
```sql
CREATE TABLE employees (
  id uuid PRIMARY KEY, work_email citext UNIQUE NOT NULL,
  role text NOT NULL CHECK (role IN ('user','manager','admin')),
  manager_id uuid REFERENCES employees(id),
  status text NOT NULL CHECK (status IN ('ACTIVE','SUSPENDED','EXITED'))
);

-- who can this actor see? recursive, cached per-statement
CREATE OR REPLACE FUNCTION visible_employee_ids(actor uuid)
RETURNS TABLE(id uuid) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  WITH RECURSIVE me AS (
    SELECT e.id, e.role FROM employees e WHERE e.id = actor
  ), tree AS (
    SELECT e.id FROM employees e WHERE e.id = actor
    UNION
    SELECT c.id FROM employees c JOIN tree t ON c.manager_id = t.id
  )
  SELECT e.id FROM employees e
  WHERE (SELECT role FROM me) = 'admin'
     OR e.id IN (SELECT id FROM tree);
$$;
```

```sql
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;    -- <-- see below, this line matters

CREATE POLICY tickets_read ON tickets FOR SELECT TO authenticated
USING (
      assignee_id IN (SELECT id FROM visible_employee_ids((SELECT auth.uid())))
   OR raiser_id   IN (SELECT id FROM visible_employee_ids((SELECT auth.uid())))
);

CREATE POLICY tickets_insert ON tickets FOR INSERT TO authenticated
WITH CHECK ( raiser_id = (SELECT auth.uid()) );

-- narrow update: only assignee/raiser/manager, and never the immutable columns
CREATE POLICY tickets_update ON tickets FOR UPDATE TO authenticated
USING (
      assignee_id = (SELECT auth.uid())
   OR raiser_id   = (SELECT auth.uid())
   OR assignee_id IN (SELECT id FROM visible_employee_ids((SELECT auth.uid())))
)
WITH CHECK ( raiser_id = (SELECT raiser_id FROM tickets t WHERE t.id = tickets.id) );

-- nobody deletes tickets, ever
CREATE POLICY tickets_no_delete ON tickets FOR DELETE TO authenticated USING (false);

-- a RESTRICTIVE policy is an AND-gate: suspended/exited users see nothing, whatever else allows
CREATE POLICY tickets_active_only ON tickets AS RESTRICTIVE FOR ALL TO authenticated
USING ( EXISTS (SELECT 1 FROM employees e
                WHERE e.id = (SELECT auth.uid()) AND e.status = 'ACTIVE') );
```
```sql
-- punches: readable if the parent ticket is readable; insert only as yourself; no update/delete
ALTER TABLE punches ENABLE ROW LEVEL SECURITY; ALTER TABLE punches FORCE ROW LEVEL SECURITY;
CREATE POLICY punches_read ON punches FOR SELECT TO authenticated
  USING ( EXISTS (SELECT 1 FROM tickets t WHERE t.id = punches.ticket_id) );  -- tickets RLS cascades
CREATE POLICY punches_insert ON punches FOR INSERT TO authenticated
  WITH CHECK ( author_id = (SELECT auth.uid())
               AND EXISTS (SELECT 1 FROM tickets t WHERE t.id = punches.ticket_id) );
```

**The `(SELECT auth.uid())` wrapping is not cosmetic** — Supabase documents it as caching the function result per statement instead of per row, measuring a "94.97% improvement" `[DATA]`. On a 500 MB / shared-CPU free instance `[DATA]` that difference is the gap between a snappy board and a timeout.

**Index every column a policy touches** (`tickets.assignee_id`, `tickets.raiser_id`, `punches.ticket_id`, `employees.manager_id`) — Supabase's own guidance `[DATA]`.

**Traps, in order of how likely they are to bite:**

1. **`service_role` bypasses RLS completely.** Supabase: "special 'Service' keys, which can be used to bypass RLS… should never be used in the browser or exposed to customers" `[DATA]`. **If your Worker connects with the service key for convenience, every policy above is decoration.** This is the failure mode I'd bet on. Mitigation:
   - The request path uses a **minted per-user JWT** with `role: authenticated`, signed with the Supabase JWT secret held as a Worker secret. `sub` = employee uuid, short `exp` (e.g. 120 s), plus `email`. Then `auth.uid()` works and RLS is live.
   - The service key exists in **exactly one** place: a separate `admin-jobs` Worker (or GitHub Action) used only by cron jobs, with its own secret. Never imported by the request-handling code path. Enforce with a CI grep: **fail the build if `SERVICE_ROLE` appears anywhere under the request-handler directory.**
   - Note the residual risk honestly: the request Worker holds the JWT signing secret, so it *can* mint any user's token. That is inherent to a server-rendered app; the control is that it can only do so through your code, and every mint is audited.
   - If you connect directly with `postgres.js` instead of PostgREST, the equivalent is: `SET LOCAL ROLE app_user; SELECT set_config('request.jwt.claims', $1, true);` per transaction — and `app_user` must be created `NOBYPASSRLS` and must **not** own the tables.

2. **Table owners bypass RLS by default.** Postgres: "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE … FORCE ROW LEVEL SECURITY`" `[DATA]`. Hence `FORCE ROW LEVEL SECURITY` on every table — and never let the app's role own the tables.

3. **Superusers and `BYPASSRLS` roles always bypass** `[DATA]`. On managed Postgres that includes the vendor. RLS is not a control against the platform; the audit anchor (B.2) and field encryption (B.1) are.

4. **`SECURITY DEFINER` functions bypass the caller's RLS.** `visible_employee_ids` above is deliberately `SECURITY DEFINER` (it must read the whole employee tree) — so it must be audited line by line, must never take a "which user am I" argument from the client, and should be `REVOKE EXECUTE … FROM PUBLIC` then granted narrowly.

5. **Referential integrity bypasses RLS** — Postgres: FK and unique checks "always bypass row security" `[DATA]`. Practical leak: a unique constraint on `tickets.ref` lets an unauthorised user *probe* whether a ref exists by attempting an insert and reading the error. Return generic errors; never surface constraint names to the client.

6. **Views default to the view owner's rights.** If you build `ticket_view` (A.1), create it `WITH (security_invoker = true)` (Postgres 15+) or the view will happily leak past RLS.

7. **`count(*)` and aggregates leak too** — RLS filters them correctly, but *error messages, timing, and pagination totals* can still leak existence. Prefer returning **404 rather than 403** for objects the actor cannot see (see B.6).

---

### B.4 Auth hardening

**Primary recommendation: use Cloudflare Access OTP and inherit its properties.** What Access already gives you, verified:
- PIN "expires 10 minutes after the initial request"; single-use — "Requesting a new PIN invalidates the previous PIN" `[DATA]`.
- Allow-list enforced *before* the email is sent — "Cloudflare only sends the email if the user is allowed by an Access policy" `[DATA]`.
- **Enumeration resistance is built in and documented**: "The login page will always say a code has been emailed to you, regardless of whether or not an email was sent" `[DATA]`. This is the exact property most DIY implementations get wrong.
- Cloudflare absorbs the delivery, the rate limiting, and the abuse handling.

**What you must still do:**
1. **Verify the JWT server-side, every request, fail closed.** Header `Cf-Access-Jwt-Assertion` (the doc notes the `CF_Authorization` cookie is "not guaranteed to be passed") `[DATA]`. Fetch JWKS from `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`, select by `kid` from `public_certs[]`, and heed the explicit warning: "Do not fetch the current key from `public_cert`, since your origin may inadvertently read an expired value from an outdated cache" `[DATA]`. Validate `aud` against your app's AUD tag, `iss` against your team domain, and `exp`/`nbf`. Keys rotate every 6 weeks with a 7-day overlap `[DATA]` → cache JWKS for ≤1 hour and refetch on unknown `kid`. Use `jose` (small, works on Workers).
2. **Never trust `Cf-Access-Authenticated-User-Email` alone.** It is an unsigned header. If Access is bypassed, it is attacker-controlled. Derive identity **only** from the verified JWT's `email` claim. `[INFERENCE]` This is the most common Cloudflare Access implementation bug.
3. **Second gate in your own DB:** JWT valid ≠ authorised. Look up `employees` by email, require `status='ACTIVE'`, and reject otherwise. This gives you instant revocation even before the Access policy sync runs.
4. **Absolute + idle timeout** are configured as the Access application's session duration; pick short (e.g. 8 h absolute) and rely on Access, not on your own cookie. OWASP's guidance for reference: idle timeout "2-5 minutes for high-value applications and 15-30 minutes for low risk applications", absolute "between 4 and 8 hours" `[DATA]`. For an internal tracker on office machines, 8 h absolute / 60 min idle is a defensible middle; write the reasoning down.
5. **Device/session list + remote revoke:** use Access's own user-session revocation rather than building it. Add a page that *lists* recent logins from your `audit_log` (`action='auth.login'`, with `ip_h`/`ua_h`) so a user can spot something wrong, and a "report this" button that emails the admin.

**DIY spec (only if you must — >50 seats, or Access is ruled out):**
- **Code:** 8 characters from Crockford base32 (excludes I/L/O/U) ≈ 41 bits, or 6 digits (~20 bits) *only* with strict throttling. Generate with `crypto.getRandomValues`, never `Math.random`.
- **Store `HMAC-SHA256(OTP_PEPPER, code)`, never the code.** Pepper is a Worker secret. Compare with `crypto.subtle.timingSafeEqual` `[DATA]`.
- **Single-use:** `consumed_at timestamptz`, set in the *same* UPDATE that verifies (`UPDATE … WHERE id=$1 AND consumed_at IS NULL RETURNING …`) so concurrent redemptions cannot both win.
- **Expiry 10 minutes**, `attempts smallint` with hard fail at 5, and invalidate all prior codes for that email on a new request.
- **Rate limits — and note you cannot lean on Cloudflare's free WAF for this.** Free-plan rate limiting is **1 rule, IP-only counting, Path/Verified-Bot fields only, fixed 10-second period** `[DATA]` — useless for "3 OTPs per email per 15 minutes". So implement in the app: a `rate_events(bucket_key, window_start, count)` table in Postgres with an upsert, keyed on `otp:email:<hmac>`, `otp:ip:<hmac>`, and a global `otp:all`. Suggested: 3/email/15 min, 10/email/day, 10/IP/hour, plus a global circuit breaker that trips at ~3× the expected daily volume and alerts. (Workers KV is *not* the right store here: KV free write limits are low and rate-limit counters are write-heavy — **UNVERIFIED** exact KV free write cap, so avoid the dependency.) Cloudflare also has a native Workers rate-limiting binding, but **UNVERIFIED** whether it is on the free plan — check before relying on it.
- **Exponential backoff + identical timing** for unknown emails: do the same amount of work (a dummy HMAC) and return the same response and same latency band, whether or not the email exists.
- **Turnstile on the request-code form** — free, unlimited verifications, 20 widgets `[DATA]`.
- **Cookies:** `__Host-` prefixed session cookie, `Secure`, `HttpOnly`, `SameSite=Lax` (`Strict` breaks the email-link return journey — use `Lax` and a separate CSRF token), `Path=/`, no `Domain`. ≥64 bits of entropy for the session id (OWASP: "at least 64 bits of entropy") `[DATA]`; use 256 bits, it's free. **Regenerate the session id on every privilege change** — OWASP: "The session ID must be renewed or regenerated by the web application after any privilege level change" `[DATA]`. Send `Clear-Site-Data` on logout `[DATA]`.
- **Email delivery is a genuine single point of failure.** With Access, Cloudflare owns it and your quota is untouched — a strong argument for Access. In a DIY build, the SPOF is real: Resend's 100/day `[DATA]` means a single Monday-morning login rush plus digests can lock the firm out of its own tracker. Break-glass plan, written down: one admin account with a TOTP-only login path (no email), sealed recovery codes in the physical safe.

---

### B.5 Zero-cost MFA beyond email OTP

| Option | Cost | Realistic here? | Verdict |
|---|---|---|---|
| **Access email OTP** | ₹0 | Yes — already the primary | Baseline. It is a *possession* factor (control of the mailbox), so the mailbox's own MFA is doing real work here. Note the dependency: **your app's security floor is the security of the company mailbox.** Say that out loud to whoever owns email. `[OPINION]` |
| **TOTP (RFC 6238)** via `otplib` + `@otplib/plugin-crypto-web` (explicitly edge/Workers-compatible) or `otpauth` | ₹0, MIT-class licences | Yes, and it is ~150 lines: QR enrolment (generate the `otpauth://` URI, render QR client-side), store the shared secret **encrypted with the identity DEK**, ±1 step window, replay protection by storing `last_used_step`, 10 single-use recovery codes hashed at rest | **Build it in V2, scoped to step-up for admin/destructive actions only** (bulk ops, role change, crypto-shred, export-all). Requiring TOTP for every login on a 50-person internal tracker will get you a wall of complaints and a shared secret in a WhatsApp group. `[OPINION]` |
| **WebAuthn / passkeys** via SimpleWebAuthn (`@simplewebauthn/server` + `/browser`) | ₹0 | Technically yes — platform authenticators (Windows Hello, Touch ID) need no admin rights, and it is the strongest phishing-resistant option. But: registration + recovery + multi-device + "I got a new laptop" support flows, and **UNVERIFIED** whether `@simplewebauthn/server` runs cleanly on the Workers runtime (its docs page didn't state runtime support — needs a spike) | **V2 at best, and only if you end up building your own auth.** On top of Access OTP the marginal security gain is small; the marginal support burden on a solo builder who is also an APM is not. `[OPINION]` |
| Hardware keys / SMS / push | Not ₹0 (SMS costs per message in India; push needs an app) | No | Excluded |

**Bottom line:** Access OTP + short session + TOTP step-up for admin = the right zero-cost MFA posture. Passkeys are a "nice to have" that a solo builder should not sign up for in V1. `[OPINION]`

---

### B.6 Defence in depth

**1. Cloudflare Access in front of everything — the highest-leverage control.**
Unauthenticated traffic never reaches the app; the OTP email is only sent to allow-listed users `[DATA]`. Free for up to 50 users per secondary sources (`[DATA-2]`, primary **UNVERIFIED** — confirm at signup, and note this is also the hard ceiling on headcount before this design costs money).
- One Access application on the app hostname, policy = Allow, include = an **email group synced from the `employees` table** (see A.1 Admin).
- A **second, stricter Access policy on `/admin/*`** requiring membership of an `admins` group — a whole extra gate before your code runs.
- `workers_dev = false`, plus a test asserting the workers.dev URL is unreachable.
- **UNVERIFIED but likely:** Access log retention on free is short (secondary sources say 24 h; the docs don't state it). **Do not rely on Cloudflare's logs as your audit trail** — CERT-In wants 180 days in Indian jurisdiction `[DATA]`. Your own `audit_log` in Mumbai-hosted Postgres is the compliance artefact; write an `auth.login` row on every successful JWT validation of a new session.

**2. WAF / rate limiting on free — set expectations correctly.**
Free rate limiting is **1 rule, IP-only, Path/Verified-Bot fields only, 10-second fixed period** `[DATA]`. That is not a security control for this app; it is a speed bump. **All meaningful rate limiting must be app-layer**, in Postgres (see B.4). Use the one free WAF rule on the login path as belt-and-braces. Free managed WAF rules (the Cloudflare Free Managed Ruleset) are worth enabling but don't know anything about your app's logic.

**3. Secrets management.**
- Workers secrets: "encrypted text values", "not visible within Wrangler or Cloudflare dashboard after you define them" `[DATA]`; 64 vars/Worker @ 5 KB `[DATA]` — ample.
- Secrets needed: `KEK_V<n>`, `BIDX_KEY`, `AUDIT_HMAC_KEY`, `OTP_PEPPER` (if DIY), `SUPABASE_JWT_SECRET`, `SUPABASE_URL`, `RESEND_API_KEY`, `CF_API_TOKEN` (for the Access-group sync, scoped to *just* that permission), `BACKUP_AGE_PUBKEY` (public — not secret).
- **Never in git.** Add `gitleaks` to CI (free, OSS) as your substitute for GitHub secret scanning, which is **not** included for private repos on Free `[DATA]`. Also add a pre-commit hook — but assume it will be bypassed and rely on CI.
- **Rotate on any offboarding of anyone who had Cloudflare dashboard access.** Written runbook, 30 minutes.
- Secrets Store is account-level but **beta** with no stated pricing `[DATA]` — don't depend on it yet.

**4. Dependency scanning and supply chain.**
- **Dependabot alerts ARE included for private repos on GitHub Free** `[DATA]`. Turn them on.
- **Secret scanning, push protection, code scanning/CodeQL, and Dependabot *security updates* are NOT listed for private repos on Free** `[DATA]`. Free substitutes in a GitHub Action (2,000 min/month, and usage is simply **blocked** rather than billed when exhausted `[DATA]`):
  - `npm audit --audit-level=high` (fails the build)
  - **`osv-scanner`** (OSS, Google) for lockfile vulnerabilities — better data than `npm audit` alone
  - **`gitleaks`** for secrets
  - `npm ci --ignore-scripts` where possible; commit the lockfile; pin GitHub Actions to **commit SHAs, not tags** (tag repointing is a real supply-chain vector)
  - `npm ls --all` diff on PRs to catch surprise transitive additions
- Keep the dependency count deliberately tiny. Every package is a person who can push to your production. For this app you need roughly: `next`, `jose`, `postgres`/`@supabase/supabase-js`, `zod`. Resist the rest. `[OPINION]`

**5. Security headers / CSP.**
Set in Next.js middleware (supported by OpenNext `[DATA]`) with a per-request nonce:
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-<random>' 'strict-dynamic';
  style-src 'self' 'nonce-<random>';
  img-src 'self' data:;
  connect-src 'self';
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
  report-uri /api/csp-report
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```
`frame-ancestors 'none'` + `SameSite` cookies is your clickjacking and most of your CSRF defence; add a double-submit CSRF token on state-changing routes anyway. Ship CSP in report-only first for a week, then enforce. Turnstile (if used) needs its own `script-src`/`frame-src` allowance — the one exception, added explicitly.

**6. IDOR — the bug you will actually ship. Five layers, in order.**
OWASP's core guidance: "implement access control checks for each object", "verify the user's permission every time an access attempt is made", scope queries to the user (`@current_user.projects`, not all projects), and GUIDs are defence-in-depth only — "access control is crucial even with these identifiers" `[DATA]`.

Concretely, for this app:
- **(i) RLS is the backstop.** Even if a handler forgets its check, the DB returns zero rows. This is *the* reason to do the minted-JWT work in B.3 rather than using the service key. Nothing else gives you a second chance.
- **(ii) One data-access module; no raw SQL in route handlers.** Make it structurally impossible to query without an actor:
```ts
// db/repo.ts — the ONLY file that talks to Postgres
type Actor = { employeeId: string; role: Role; readonly __brand: 'Actor' };
export async function withActor<T>(jwt: string, fn: (db: ScopedDb, a: Actor) => Promise<T>): Promise<T>
// every repo fn takes ScopedDb, which is only obtainable inside withActor
export function getTicket(db: ScopedDb, id: string)          // db carries the user's JWT
```
  Then a CI check: **fail the build if any file outside `db/` imports the Postgres client.** A 5-line grep in CI prevents the entire bug class better than any review discipline. `[OPINION]`
- **(iii) Never accept an identity from the client.** `assignee_id` may be *set* by a user, but "whose tickets am I viewing" comes only from the JWT. Validate every body with `zod` and **strip unknown keys** (`.strict()`) so mass-assignment can't set `raiser_id` or `role`.
- **(iv) Return 404, not 403, for objects the actor can't see.** 403 confirms existence. With RLS the query returns nothing, so 404 is also the *natural* result — align the code with the database's behaviour rather than fighting it. `[INFERENCE]`
- **(v) An authorization test matrix, run in CI.** Seed 5 fixtures: `userA`, `userB` (same team), `userC` (different team), `managerA` (manages A+B), `admin`. For **every** route × every fixture, assert the expected status. This is ~100 table-driven test cases and it is the single highest-value test suite in the project. OWASP's own testing advice is exactly this: multiple accounts with different scopes, attempting read/create/update/delete/export/admin `[DATA]`.
- **(vi) UUIDv7 ids everywhere** (sortable, non-sequential) — defence in depth only, per OWASP `[DATA]`.

---

### B.7 Compliance-driven jobs

**Applicable rules I could verify, and what they actually require of *this app*:**
- **CERT-In Directions, 28-Apr-2022:** logs of "all their ICT systems" maintained "for a rolling period of 180 days" and "within the Indian jurisdiction"; cyber incidents reportable **within 6 hours** `[DATA]`. → **Legally required** (for a body corporate in India): keep ≥180 days of app + auth logs in an India-hosted store, and have a named human + a written 6-hour reporting runbook. This is the strongest concrete driver for (a) Supabase Mumbai and (b) not relying on Cloudflare's short free log retention.
- **DPDP Act 2023 + DPDP Rules 2025** (notified 14-Nov-2025; phased, Schedule-1 penalties from 13-May-2027) `[DATA-2]`. → Employee personal data is in scope. Notice, purpose limitation, erasure-on-request, retention limits, breach notification, and a grievance route are the operative duties. Do **not** state specific Rule numbers or deadlines in a firm document without reading the notified Rules text — the PIB PDF I retrieved was image-only and I could not extract clauses. **Flag for the compliance officer.**
- **SEBI CSCRF** (circular 20-Aug-2024; clarifications 30-Apr-2025) applies to Portfolio Managers. Reported categorisation: PM Self-certification ≤ ₹3,000 cr AUM, Small-size > ₹3,000 cr and < ₹10,000 cr, Mid-size ≥ ₹10,000 cr; standalone IAs exempt unless registered otherwise; Self-certification REs exempt from CERT-In-empanelled periodic cyber audit; PMs in self-certification with <100 clients exempt from mandatory M-SOC `[DATA-2]`. → **An internal app used for client-work tracking sits inside the RE's IT estate**, so its access control, logging, and change management get pulled into the CSCRF self-certification. Practical consequence: keep a one-page control document for this app (owner, data classified, access review cadence, log retention, backup/restore evidence, VAPT status) so it can be dropped into the annual self-certification instead of being discovered during it. `[OPINION]` **Confirm the category and obligations with the firm's compliance officer — my thresholds are secondary-source.**
- **Best practice, not law:** hash-chained audit logs, field-level encryption, TOTP step-up, CSP, IDOR test matrix. Valuable; do not label them "required".

**Automated retention/purge job:**
```
retention_policy
  entity        text primary key   -- 'tickets','punches','audit_log','notifications',
                                   -- 'email_send_log','rate_events','due_date_changes'
  retain_days   int not null
  basis         text not null      -- 'statutory' | 'business' | 'minimisation'
  authority     text not null      -- the rule/decision that sets it, verbatim reference
  action        text not null      -- 'PURGE' | 'ANONYMISE' | 'NEVER'
```
Suggested starting values (**to be ratified by compliance, not by me**): `audit_log` = 2,555 days / NEVER-purge (≥180 days is the CERT-In floor `[DATA]`; SEBI record-keeping is typically longer — confirm); `tickets`/`punches` = 2,555 days (business record of client work); `notifications` = 90 days PURGE; `rate_events` = 30 days PURGE; `email_send_log` = 400 days; `ip_h`/`ua_h` = null-out after 180 days (minimisation — keep the audit row, drop the network identifiers once the CERT-In window closes). `[OPINION]`

Runner: **a Cloudflare Cron Trigger (5 free per account `[DATA]`) hitting an `/admin/jobs/run` route with a service token**, not `pg_cron`. Two reasons: (a) pg_cron on a free Supabase project stops silently when the project pauses after 7 days of inactivity `[DATA]` and the only symptom is a gap in the run history; (b) the same Worker cron **also keeps the project warm**, killing the pause problem. One cron, two jobs done. Every purge writes an `audit_log` row with counts. A job that deletes and doesn't record what it deleted is worse than no job. `[OPINION]`

**DSAR export:** `GET /admin/dsar/:employeeId` (admin-only, TOTP step-up, audited) returning a single JSON + CSV bundle: the employee row, tickets raised, tickets assigned, all punches authored, `due_date_changes` made, login events, notification history, and the retention policy applied to each. At 50 employees a manual admin-triggered export is correct; a self-service portal is over-build. Log every DSAR as `action='dsar.export'`.

**Right to erasure with an append-only log — crypto-shredding, honestly:**
1. **First, the legal shape**, because this is where people over-promise. An employee's work record — who was assigned what, when they updated it — is generally retained for legitimate business and statutory record-keeping reasons; DPDP-class erasure rights are typically **not** available against data a fiduciary is required or permitted to retain. So the erasure you should design for is **narrow: the employee's personal identifiers, not the work record.** State that in the notice up front. Get compliance to confirm. `[OPINION]` / **UNVERIFIED** as to the precise Rules wording.
2. **Mechanism:** the employee's `full_name`, `personal_email`, `phone` and any flagged private free-text are encrypted under that employee's **identity DEK** (B.1). Erasure = overwrite `dek_keyring.wrapped_dek` with zeros, set `shredded_at`, and append `action='key.shred'` to the audit chain. The ciphertext stays; it becomes unreadable. The employee's `id` and `work_email_hmac` remain, so `punches.author_id` still resolves — the author becomes a **stable pseudonym** rather than a named person. The audit trail survives intact.
3. **Why the chain doesn't break:** the chain hashes `payload_sha256`, not `payload_json` (B.2). You can null out or redact `payload_json` and the chain still verifies. Design this on day one; retrofitting it is a migration nightmare. `[INFERENCE]`
4. **Does crypto-shredding satisfy erasure?** Conceptually strong and widely used, but the claim that EDPB/ICO/CNIL "explicitly recognise" cryptographic erasure appeared only in **vendor blogs** in my searches — **UNVERIFIED against primary guidance.** Two conditions are non-negotiable regardless: **per-subject key isolation** (one DEK per employee, which is why Tier 1 exists) and **irreversible, auditable key destruction**. And see B.8: destruction is not irreversible if a backup still contains the wrapped key.
5. **Consent/notice at first login:** an interstitial on first login (and re-shown on version bump) stating what is collected, why, retention periods, who sees it, the grievance contact, and — importantly — that **status punches are permanent and visible to managers**. Store `notice_version`, `accepted_at`, `notice_sha256` per employee and write it to the audit chain. The `notice_sha256` is the bit that lets you later prove *which text* someone accepted. `[OPINION]`

---

### B.8 Backup & restore

**Supabase free has no backups at all** `[DATA]`. So this is entirely on you, and it is the most likely place this project quietly fails.

**Design:**
```
GitHub Actions, scheduled 21:00 UTC (02:30 IST) daily  [2,000 free min/month; blocked, not billed,
                                                        when exhausted [DATA]]
 1. pg_dump --no-owner --no-acl (exclude dek_keyring — see below) → dump.sql
 2. pg_dump only dek_keyring                                     → keys.sql
 3. age -R backup_recipients.txt dump.sql > dump.sql.age          (age: free, OSS, X25519)
 4. age -R backup_recipients.txt keys.sql > keys.sql.age
 5. sha256sum both, append to a manifest
 6. Destination A: upload as an Actions artifact (500 MB storage on Free [DATA], retention 14 days)
 7. Destination B: aws s3 cp → Cloudflare R2 (10 GB free, egress free [DATA])
    R2 paths:  db/YYYY/MM/DD/dump.sql.age      retain 35 days
               keys/YYYY/MM/DD/keys.sql.age    retain 7 days     <-- shorter, deliberately
 8. Append a line to the audit-anchors repo: date, byte sizes, sha256s, row counts
 9. On failure: email two humans. A silent backup failure is the default outcome; alerting is the job.
```
**What to back up:** the whole schema + data, plus `wrangler.toml`, migrations, and the **KEK escrow location** (not the KEK). Encrypted-at-rest via `age` with a public key; **the private key never touches CI** — it lives on a printout in the firm's safe and on one offline USB. That is what makes "the backup leaked" a non-event.

**The non-obvious bit — retention vs erasure interact through the backups, and this is where crypto-shredding usually breaks:**
If you crypto-shred an employee's DEK today but a 90-day-old backup still contains the *wrapped* DEK, then anyone who can restore that backup and holds the KEK can undo the erasure. Two mitigations, use both:
1. **Back up `dek_keyring` separately with a much shorter retention (7 days)** than the data (35 days). After a shred, the resurrectable window is ≤7 days, and you can state that in the privacy notice as the erasure completion time. `[INFERENCE]`
2. **Cap data-backup retention at 35 days** and say so in the retention policy, so shredded/purged data ages out of all copies within a month.
Note the tension with CERT-In's 180-day log retention `[DATA]`: that obligation is about **logs**, satisfied by the live `audit_log` in Mumbai, not by keeping 180 days of full DB snapshots. Keep the two concepts separate in the policy document or you will end up unable to erase anything. `[OPINION]`

**Restore drill — quarterly, with written success criteria** (an untested backup is not a backup):
1. Create a scratch Supabase project (you get 2 active free projects `[DATA]` — so either pause one or restore into a local Postgres via Docker; local is better and doesn't consume the quota).
2. `age -d` both files with the offline key. **Criterion: decryption succeeds and sha256 matches the manifest.**
3. Restore. **Criterion:** `count(*)` on `tickets`, `punches`, `audit_log` match the recorded counts for that night.
4. **Run the chain verifier over the restored `audit_log`. Criterion: chain verifies end-to-end AND the final `row_hash` equals the anchor published in the anchors repo for that date.** This is the drill's real payoff — it simultaneously tests the backup, the chain, and the anchor.
5. Decrypt one known `client_ref` with `KEK_V<current>`. **Criterion: plaintext matches expectation.**
6. **Criterion: total elapsed time < 2 hours** (this is your de-facto RTO — write it down; RPO is 24 h given daily dumps).
7. File the result (date, operator, timings, pass/fail) in the compliance folder and write an `audit_log` row. A dated restore-drill record is exactly the evidence CSCRF self-certification asks for. `[OPINION]`

---

### B.9 Threat model for THIS app

| # | Attacker / failure | Realistic? | Specific control |
|---|---|---|---|
| 1 | **Curious employee** reads a colleague's or another team's tickets | **Very likely** — the #1 real threat | RLS with `FORCE ROW LEVEL SECURITY` (B.3) + minted per-user JWT (never service key) + the repo/`ScopedDb` pattern + 404-not-403 + the CI authorization matrix (B.6). Every `SELECT` is filtered by the DB even if the handler is wrong. |
| 2 | **IDOR bug you ship yourself** | **Very likely** | Same as #1; RLS is specifically the second chance. Plus the CI grep banning DB access outside `db/`. |
| 3 | **Departing employee with repo access** pushes a backdoor or exfiltrates | Likely enough | **Offboarding runbook: remove from `employees` (→ Access group sync drops them), remove GitHub collaborator, rotate ALL Worker secrets, rotate the Cloudflare API token, revoke Access sessions.** Note the gap: **GitHub Free has no branch protection or rulesets on private repos** `[DATA]` — so you *cannot* enforce review. Compensating controls: keep the repo to **one owner and zero write collaborators**; require signed commits by convention and verify in CI; have the deploy Action refuse to deploy a commit whose author is not on an allow-list; and mirror the repo nightly to a second location so a force-push can be detected and recovered. `[OPINION]` |
| 4 | **Credential stuffing / password reuse** | **Structurally impossible** | No passwords stored anywhere (given). Access OTP only. This is a genuine design win — say it out loud. |
| 5 | **Phishing an OTP** | Plausible | 10-min single-use PIN `[DATA]`; short Access session; TOTP step-up on admin actions (V2); a login-events page users can inspect. Passkeys would fully solve it — the honest reason not to build them now is builder capacity, not security (B.5). |
| 6 | **The builder leaves the firm** — *this is the top systemic risk, and it is not a hacker* | **Highly likely on a 3–5 year view** | A `RUNBOOK.md` in the repo covering: how to deploy, where every secret lives, the KEK escrow location and how to use it, how to run the chain verifier, how to run a restore drill, the NEVER list, and how to re-create the Cloudflare Access app from scratch. **Two named humans must hold: Cloudflare account access, GitHub owner access, the KEK escrow, and the backup `age` private key.** Bus factor 1 on a KEK means the firm loses its own records. `[OPINION]` This deserves as much attention as any crypto in this document. |
| 7 | **Laptop loss / theft** | Plausible | No local data (web app). Short Access session + `Clear-Site-Data` on logout `[DATA]`. Revoke Access sessions + rotate secrets if the laptop had Wrangler credentials. Never store the backup `age` private key or the KEK escrow on the work laptop. |
| 8 | **Vendor breach (Supabase / Cloudflare)** | Low but non-zero | Field encryption on the narrow high-sensitivity set with the KEK held **outside** the DB (B.1) — this is the one threat column encryption genuinely addresses. Plus: no client PII by design, so the blast radius is employee names + internal task text. Audit anchors held outside Supabase detect DB-side tampering. |
| 9 | **Accidental public repo / leaked dump** | **Likely at least once** | `gitleaks` in CI (substituting for GitHub secret scanning, unavailable on private-repo Free `[DATA]`); no secrets in git, ever; **no data fixtures with real content** in the repo; encrypted-only backups so a leaked dump file is inert; a `.gitignore` that excludes `*.sql`, `*.dump`, `*.age`, `.env*`; and a CI check that fails on any file >1 MB. |
| 10 | **Malicious/compromised npm dependency** | Plausible | Tiny dependency count; lockfile committed; `osv-scanner` + `npm audit` + Dependabot alerts (free on private repos `[DATA]`); Actions pinned to commit SHAs; `--ignore-scripts` where feasible; CSP with `'strict-dynamic'` limits what injected script can reach. |
| 11 | **DB admin (or you) rewrites history to cover a missed deadline** | The scenario the audit chain exists for | Hash chain + `REVOKE`/trigger + **daily external anchor to a separate GitHub repo, email, and R2** (B.2). Prevention is impossible against a superuser; **detection within 24 hours** is achievable at ₹0 and is the honest claim to make. |
| 12 | **Free-tier rug-pull / silent limit change** | Moderate, over years | Everything is portable Postgres + a standard Next.js app; no vendor-proprietary data model. Nightly self-run encrypted dumps mean you can leave Supabase in an afternoon. Re-read every cited limits page each quarter (put it in the calendar). |
| 13 | **Supabase project auto-pauses after 7 days of inactivity and the app is "down"** `[DATA]` | **Near-certain during a holiday week** | The Cloudflare Cron Trigger that runs jobs also pings the DB, keeping it warm (B.7). Monitor and alert on it. |
| 14 | **Someone hits the Worker directly, bypassing Access** | **Likely if not explicitly prevented — and catastrophic** | `workers_dev = false`; JWT verification fails closed with a bare 403; a CI/monitoring test that asserts the workers.dev hostname is unreachable. |
| 15 | **Email quota exhausted → escalation emails silently dropped** | **Likely** given Resend's 100/day `[DATA]` | The send-budget guard with strict priority ordering (A.1 Notifications); dropped sends recorded and surfaced in-app; in-app notifications as the primary channel so email is never the only path. |

---

## PART C — GOTCHAS (traps, hidden costs, things that break later)

1. **Resend free is 100 emails/*day*, not just 3,000/month** `[DATA]`. 50 daily digests + a manager summary is already 55% of it. This, not storage or compute, is the constraint that shapes the notification feature set. Design the send-budget guard on day one.
2. **You cannot fall back on company email.** M365 SMTP AUTH is disabled by default and enabling it needs tenant/Exchange admin, which you don't have `[DATA]`. Any plan whose fallback is "just use the office SMTP server" is dead.
3. **Cloudflare's free WAF rate limiting cannot do what you need** — 1 rule, IP-only, Path-only fields, fixed 10-second window `[DATA]`. Every plan that says "Cloudflare will rate-limit the OTP endpoint" is wrong on the free plan. App-layer or nothing.
4. **`workers.dev` silently bypasses Cloudflare Access.** Access binds to a hostname. Leave the workers.dev route enabled and your entire auth layer has a documented side door.
5. **The unsigned `Cf-Access-Authenticated-User-Email` header is not authentication.** Trusting it instead of verifying the JWT is the single most common Access implementation bug.
6. **Using the Supabase `service_role` key from the request path makes every RLS policy decorative** `[DATA]`. Enforce with a CI grep, not with good intentions.
7. **Table owners bypass RLS unless you `ALTER TABLE … FORCE ROW LEVEL SECURITY`** `[DATA]`. Easy to forget on the 8th table, six months later.
8. **D1 cannot be pinned to India** — only `eu` and `fedramp` jurisdictions exist `[DATA]`. If you pick D1 because it's "the Cloudflare-native option", you have quietly created a data-residency problem against CERT-In's "within the Indian jurisdiction" log requirement `[DATA]`.
9. **Supabase free projects pause after 7 days of inactivity, and pg_cron dies with them** `[DATA]` — with no alert, just a gap in the run history. Every scheduled compliance job (purge, digest, anchor) inherits this failure mode unless the scheduler lives in Cloudflare.
10. **Supabase free has no backups** `[DATA]`. If you don't build the dump job, you have none. And an untested restore is not a backup — hence the quarterly drill with numeric criteria.
11. **Cloudflare Cron Triggers are UTC; IST is +05:30.** `0 * * * *` schedules land on the half-hour in IST. Also: only **5 cron triggers per account** on free `[DATA]` — account-wide, so other projects compete. Use one cron and an internal job table, not five crons.
12. **The Worker script limit is 3 MiB compressed on free** (10 MiB paid) `[DATA]`. A Next.js app plus `exceljs` plus a charting library will hit it. Budget bundle size as a first-class constraint; generate Excel in a GitHub Action if you need it.
13. **Workers CPU limit is 10 ms per request on free** `[DATA]`. Fine for SSR of a list, **not** fine for hashing a large export, verifying a long audit chain, or PDF generation in the request path. Push those to cron/Actions.
14. **Encrypting a column silently kills search, sort, and range queries on it** — and there is no free fix. Deterministic encryption or a blind index buys back equality only, and leaks equality and frequency. Decide per column, deliberately, and write the decision down.
15. **Losing the KEK destroys the encrypted data permanently.** An "encrypt everything" plan without a written, tested, two-person key escrow is a bigger risk to the firm than the breach it defends against.
16. **Crypto-shredding is undone by an old backup** that still contains the wrapped DEK. Separate the key backup with a much shorter retention, or your erasure is theatre.
17. **Hashing the audit payload itself (instead of a hash of it) makes erasure impossible.** Chain over `payload_sha256`, from row one.
18. **Two concurrent audit appends fork the chain.** Take an advisory lock. Also decide whether sequence gaps mean "rolled-back transaction" or "deleted row" — you cannot have both meanings and still make a claim in an audit.
19. **Canonical JSON must be byte-identical between the writer (Worker) and the verifier.** Key order, timestamp precision, Unicode normalisation, hex case. Lock it with a golden-vector test in CI or the chain will "fail" for the wrong reason at 2 a.m.
20. **There is no zero-cost, commercially-usable virus scanner.** VirusTotal's free API "must not be used in commercial products or services" `[DATA]`. Any attachment feature is either unscanned or not free.
21. **GitHub Free gives you no branch protection or rulesets on private repos** `[DATA]`, and no secret scanning or code scanning. Compensate in CI and in the offboarding runbook; don't assume the platform is guarding the repo.
22. **Free public-holiday APIs get Indian floating and regional holidays wrong.** `date-holidays`' own README flags moon-sighting-dependent Islamic dates `[DATA]`. A wrong holiday means a wrong deadline means the app loses credibility. Human-confirm the calendar annually.
23. **Storing `due_date` as a timestamp instead of a DATE** guarantees a 5.5-hour off-by-one. Store DATE; derive overdue in SQL against `(now() AT TIME ZONE 'Asia/Kolkata')::date`; never compute overdue on the client.
24. **On-time % is trivially gamed by moving the deadline.** If you ship it without `net_days_slipped` alongside, you have built a metric that rewards the behaviour you're trying to stop.
25. **`Cf-Access-Jwt-Assertion` keys rotate every 6 weeks** `[DATA]`. Cache JWKS but refetch on an unknown `kid`, and never hard-code a key — a hard-coded key means a total outage six weeks after launch.
26. **The Zero Trust free seat limit (widely reported as 50) is the hard ceiling on this entire architecture** and I could not confirm it from a Cloudflare primary page. At 51 employees, either you pay per seat or you build your own auth (B.4). Confirm the number before committing, and know the escape route.
27. **`SameSite=Strict` breaks the email-magic-link return journey.** Use `Lax` plus an explicit CSRF token.
28. **Referential integrity checks bypass RLS** `[DATA]` — so a unique constraint can be used as an existence oracle. Return generic errors; never leak constraint names.

---

## PART D — OPEN QUESTIONS (must be answered before build)

1. **Is the Cloudflare Zero Trust free plan really 50 seats, and what exactly happens at seat 51?** Unconfirmed from a Cloudflare primary page. This determines whether the whole "don't build auth" recommendation holds. → Create the free Zero Trust account and read the plan page in-dashboard; screenshot it with a date.
2. **Data sensitivity: is `client_ref` alone genuinely out of client-PII scope?** If a `client_ref` is trivially re-identifiable by any employee via another internal system, it is pseudonymous data, not anonymous, and the client-PII regime attaches. → Compliance officer must rule, in writing, before the first ticket is raised. Everything in Part B's scope decisions depends on this answer.
3. **Which CSCRF category is the firm in, and does an internal tracker fall inside the self-certification scope?** My thresholds are secondary-source. → Compliance officer, with the actual circular text.
4. **Does the firm accept Supabase (US company, AWS Mumbai region) as a processor for employee personal data, and what does the DPDP Rules 2025 text actually require by way of processor contract and cross-border conditions?** → Needs the notified Rules text read directly; the PIB PDF was image-only.
5. **Where does the CERT-In 180-day log obligation actually bite — is Cloudflare's edge (TLS termination, Access auth logs, short free retention) a gap?** → Needs a view from compliance plus a written statement of what is logged where.
6. **Who is the second key holder?** Two named humans must hold Cloudflare account access, GitHub ownership, the KEK escrow, and the backup `age` private key. Without this the project's biggest risk (B.9 #6) is unmitigated.
7. **Is the firm on Microsoft 365 or Google Workspace, and who administers DNS?** This determines whether you can set SPF/DKIM/DMARC on a `notify.` subdomain — without it, digests go to Junk and the notification feature is dead regardless of quota.
8. **Confirm Brevo's current free transactional limits** (I could not read their pricing page). If it really is ~300/day vs Resend's 100/day `[DATA]`, that alone decides the ESP and unlocks daily digests.
9. **Does `@simplewebauthn/server` run on the Workers runtime?** Needed only if passkeys are ever pursued. One afternoon spike.
10. **Is the Workers native rate-limiting binding available on the free plan?** If yes, it simplifies B.4's DIY path considerably. UNVERIFIED.
11. **Is crypto-shredding accepted as erasure under the DPDP Rules as notified?** The supporting EDPB/ICO/CNIL claims I found were vendor blogs only. → Read primary guidance, or take the conservative path (shred *and* null the plaintext columns).
12. **What is the firm's actual retention obligation for records of client-related work?** This sets `retention_policy.retain_days` and is the one number in this design that a compliance officer, not a builder, must supply.

---

## Sources

- [Cloudflare Workers limits](https://developers.cloudflare.com/workers/platform/limits/) · [Workers secrets](https://developers.cloudflare.com/workers/configuration/secrets/) · [Workers Web Crypto](https://developers.cloudflare.com/workers/runtime-apis/web-crypto/)
- [Cloudflare D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) · [D1 jurisdictions changelog](https://developers.cloudflare.com/changelog/post/2025-11-05-d1-jurisdiction/) · [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Cloudflare WAF rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/) · [Turnstile plans](https://developers.cloudflare.com/turnstile/plans/)
- [Access one-time PIN](https://developers.cloudflare.com/cloudflare-one/identity/one-time-pin/) · [Validating Access JWTs](https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/) · [Access policies](https://developers.cloudflare.com/cloudflare-one/policies/access/) · [Cloudflare One account limits](https://developers.cloudflare.com/cloudflare-one/account-limits/) · [Zero Trust audit logs](https://developers.cloudflare.com/cloudflare-one/insights/logs/audit-logs/) · [Community: 50 user limit on free plan](https://community.cloudflare.com/t/50-user-limit-on-free-plan/546057)
- [OpenNext Cloudflare adapter](https://opennext.js.org/cloudflare)
- [Supabase pricing](https://supabase.com/pricing) · [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) · [pgsodium (pending deprecation)](https://supabase.com/docs/guides/database/extensions/pgsodium) · [Discussion #27109 (TCE not recommended)](https://github.com/orgs/supabase/discussions/27109) · [Discussion #18849](https://github.com/orgs/supabase/discussions/18849) · [Supabase Cron](https://supabase.com/docs/guides/cron) · [Regions discussion #4815](https://github.com/orgs/supabase/discussions/4815)
- [PostgreSQL row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) · [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) · [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) · [Billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions) · [Dependabot alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts/about-dependabot-alerts)
- [Resend pricing](https://resend.com/pricing) · [Brevo pricing (unreadable)](https://www.brevo.com/pricing/)
- [Microsoft: enable/disable SMTP AUTH in Exchange Online](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission)
- [VirusTotal public vs premium API](https://docs.virustotal.com/reference/public-vs-premium-api)
- [date-holidays (GitHub)](https://github.com/commenthol/date-holidays) · [Nager.Date API](https://date.nager.at/Api) · [india.gov.in calendar](https://www.india.gov.in/calendar)
- [CERT-In Directions 28.04.2022 (PDF)](https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf)
- [PIB: DPDP Rules 2025 notified](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190014) (403 on fetch) · [Wikipedia: DPDP Rules, 2025](https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025)
- [SEBI CSCRF circular 20-Aug-2024](https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html) · [CSCRF clarifications 30-Apr-2025 (APMI-hosted PDF)](https://www.apmiindia.org/storagebox/images/Circulars/Clarifications%20on%20CSCRF%20for%20SEBI%20Regulated%20Entities%20-%2030th%20April'25.pdf)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) · [OWASP IDOR Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- [otplib](https://github.com/yeojz/otplib) · [@otplib/plugin-crypto-web](https://www.npmjs.com/package/@otplib/plugin-crypto-web) · [SimpleWebAuthn](https://simplewebauthn.dev/docs/)
