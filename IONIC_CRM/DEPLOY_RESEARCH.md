# Deployment research — the one decision-critical unknown

**Question:** can this app's per-request authorisation transaction

```sql
BEGIN;
SELECT set_config('app.employee_id', $1, true);
SET LOCAL ROLE crm_app;
-- queries, RLS in force
COMMIT;
```

survive a Cloudflare Worker → Supabase Postgres path, and does `@opennextjs/cloudflare` support Next 16?

All sources fetched **2026-08-03**. Verified against `app/package.json` (`next ^16.2.12`, `react ^19.2.8`), `app/wrangler.toml`, `app/src/repo/postgres.ts` (`withActor`, `SqlClient.transaction`), `app/src/server/db.ts` (M11 throw site).

---

## RECOMMENDATION

**Cloudflare Workers is the right target. The authorisation model is safe. But it is not free.**

1. `@opennextjs/cloudflare` **does support Next 16** — *"All minor and patch versions of Next.js 16 and the latest minors of Next.js 14 and 15 are supported."* `[DATA]` No change of deployment target needed. This was the single biggest risk and it is cleared.
2. Use **`pg` (node-postgres) ≥ 8.16.3** with `nodejs_compat` (already set in `wrangler.toml`), connecting to **Supabase's Supavisor Shared Pooler in SESSION mode, port 5432** — not the direct connection, not transaction mode, and **not Hyperdrive at launch**. Session mode *"mirrors a direct connection"* `[DATA]`, is documented as available on **Free** and **IPv4** `[DATA]`, and gives an unambiguous real SQL session, so `SET LOCAL ROLE` has zero pooling caveats.
3. **Budget $5/month for Workers Paid.** Workers **Free** caps a Worker at **3 MiB gzipped** and **10 ms CPU per invocation** `[DATA]`. OpenNext's own troubleshooting page exists specifically because Next apps hit the 3 MiB wall. A Next 16 SSR render on 10 ms CPU is not realistic. `[INFERENCE]` The database layer is genuinely free; the compute layer is not.
4. **Do not use Hyperdrive yet.** It is free and it does preserve `SET` inside a transaction — but Cloudflare explicitly lists *"Any modification to per-session state not explicitly documented"* as unsupported, does not name `SET LOCAL ROLE`, and explicitly discourages the exact one-transaction-per-request pattern this app is built on. Add it later as a latency optimisation, behind the assertion guard in §"Silent RLS break", never as a launch dependency.
5. **There is no materially simpler free target.** Every genuinely-free Node-process host either sleeps, is scale-to-zero, disclaims production use, or requires a card anyway (§Rejected). Moving off Workers to save $5/month would cost more in reliability than it saves.

### Exact `CRM_DATABASE_URL` shape

```
postgresql://<USER>:<PASSWORD>@aws-<N>-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
                                └──────────── Shared Pooler, SESSION mode ────────────┘ └── port 5432, NOT 6543 ──┘
```

- Host family: `aws-[region].pooler.supabase.com` `[DATA]`. The `aws-<N>-` prefix digit and the session-mode **username form are project-specific — copy the string verbatim from Supabase Dashboard → Project Settings → Database → Connection string → "Session pooler".** Do not hand-assemble it. `[OPINION — this is the failure-avoidance instruction, not a fact claim]`
- **Port 5432 on the pooler host.** 6543 is transaction mode; 5432 on `db.<ref>.supabase.co` is the direct connection (IPv6-only on Free).
- Set it as a Worker secret: `wrangler secret put CRM_DATABASE_URL` (already the documented name in `wrangler.toml`).

### What plugs into `db.ts`

`src/repo/postgres.ts` needs a `SqlClient` with `transaction<T>(fn: (tx: SqlRunner) => Promise<T>)`. `pg`'s `client.query()` already returns `{ rows }`, which is exactly `SqlRunner.query`'s shape — the adapter is thin:

- construct `new Client({ connectionString, ssl: ... })` **inside the request handler**, never module scope — *"I/O objects created in the context of one request handler cannot be accessed from a different request's handler"* `[DATA]`, so a module-level client throws on the second request;
- `await client.connect()`; `BEGIN` / `COMMIT` / `ROLLBACK` around `fn`; `client.end()` in `finally`;
- `SqlRunner.exec(sql)` → `client.query(sql)` (this is what carries `set local role crm_app`).

`postgres` (postgres.js) is the viable alternative — it has *"built-in support for the TCP socket API in Cloudflare Workers"* from **3.4.0 or later** `[DATA]` and `sql.begin()` — but it returns arrays rather than `{ rows }`, so it needs a mapping layer `pg` does not. `[OPINION]` Prefer `pg`: fewer lines between the contract and the driver, and it is the driver Cloudflare's own tutorials use.

---

## THE SILENT RLS BREAK — read this before writing the adapter

This is the failure mode that passes a smoke test and voids authorisation in production.

**Mechanism.** If `SET LOCAL ROLE crm_app` fails to take effect — because a pooler split the statements across connections, because the driver used an implicit-transaction/auto-commit path instead of emitting a real `BEGIN`, or because a future code path issues a query after `COMMIT` — then queries run as the **connecting role** with `app.employee_id` unset. If that connecting role owns the tables or is a superuser, **Postgres exempts it from RLS**, so every query succeeds and returns *all* rows. The app works. Every user sees everything. Nothing errors.

`[INFERENCE]` Three defences, all cheap, all required:

1. **Connect as a login role that owns nothing.** Not `postgres`. A dedicated `crm_connect` role with no table privileges of its own and only the right to `SET ROLE crm_app`. Then a failed `SET LOCAL ROLE` produces a permission error — a loud failure instead of a silent bypass. This is the single highest-value mitigation because it inverts the failure direction.
2. **`ALTER TABLE ... FORCE ROW LEVEL SECURITY`** on every table, so table ownership is not an RLS escape hatch even if defence 1 is misconfigured.
3. **Assert inside the transaction**, immediately after the two setup statements: `select current_user, current_setting('app.employee_id', true)` and throw unless `current_user = 'crm_app'` and the GUC equals `actor.employeeId`. One round trip per request, and it converts the entire class of pooling surprises into a hard error. Put it in `withActor` in `src/repo/postgres.ts`, so it cannot be forgotten per-call-site.

**Two more places the pooling subtlety bites:**

- **Transaction mode (port 6543) is the trap.** It *would* preserve `SET LOCAL` inside an explicit transaction — but *"Transaction mode does not support prepared statements"* `[DATA]`, and any statement that escapes the explicit transaction silently loses both the GUC and the role. Session mode removes the whole question. Choosing 6543 because a blog post said "use transaction mode for serverless" is the likeliest way this goes wrong.
- **Hyperdrive resets between transactions by design.** *"When a connection is returned to the pool, the connection is RESET such that the SET commands will not take effect on subsequent queries"* and *"A single Worker invocation may obtain multiple connections"* `[DATA]`. This is correct behaviour and actually protects against cross-user GUC leakage, but it means anything outside `withActor`'s transaction has no identity at all.

`[DATA]` The existing `withActor` and `resolveIdentity` in `src/repo/postgres.ts` are both already correct on this point — every statement is inside `client.transaction`, and `set_config(..., true)` is transaction-scoped. The risk is entirely in the adapter that has not been written yet.

---

## EVIDENCE

| # | Claim | Source | Fetched | Tag |
|---|---|---|---|---|
| 1 | *"All minor and patch versions of Next.js 16 and the latest minors of Next.js 14 and 15 are supported."* | https://opennext.js.org/cloudflare | 2026-08-03 | `[DATA]` |
| 2 | *"Next.js 14 support will be dropped Q1 2026."* | https://opennext.js.org/cloudflare | 2026-08-03 | `[DATA]` |
| 3 | *"You must use Wrangler version `3.99.0` or later to deploy Next.js apps using `@opennextjs/cloudflare`."* | https://opennext.js.org/cloudflare/get-started | 2026-08-03 | `[DATA]` |
| 4 | Install is `npm install @opennextjs/cloudflare@latest`; needs `nodejs_compat` **and** compatibility date *"`2024-09-23` or later"*. `wrangler.toml` already has `nodejs_compat` and `2026-08-03`. | https://opennext.js.org/cloudflare/get-started · https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/ | 2026-08-03 | `[DATA]` |
| 5 | `global_fetch_strictly_public` appears in OpenNext's example flags alongside `nodejs_compat`; not present in our `wrangler.toml`. | https://opennext.js.org/cloudflare/get-started | 2026-08-03 | `[DATA]` |
| 6 | Workers **Free**: CPU *"10 milliseconds of CPU time per invocation"*; requests *"100,000 per day"*. | https://developers.cloudflare.com/workers/platform/pricing/ | 2026-08-03 | `[DATA]` |
| 7 | Workers **Free** Worker size **3 MB gzipped**; memory 128 MB; 50 subrequests/request. | https://developers.cloudflare.com/workers/platform/limits/ | 2026-08-03 | `[DATA]` |
| 8 | OpenNext's own error text: *"The Cloudflare Account you are deploying to is on the Workers Free plan, which limits the size of each Worker to 3 MiB"* / *"When you subscribe to the Workers Paid plan, each Worker can be up to 10 MiB."* | https://opennext.js.org/cloudflare/troubleshooting | 2026-08-03 | `[DATA]` |
| 9 | Workers **Paid** = min **$5 USD/month**, *"30 million CPU milliseconds included per month"*. | https://developers.cloudflare.com/workers/platform/pricing/ | 2026-08-03 | `[DATA]` |
| 10 | *"Requests to static assets are free and unlimited."* | https://developers.cloudflare.com/workers/platform/pricing/ | 2026-08-03 | `[DATA]` |
| 11 | *"Hyperdrive is included in both the Free and Paid Workers plans."* Free: **100,000 database queries/day**. | https://developers.cloudflare.com/hyperdrive/platform/pricing/ | 2026-08-03 | `[DATA]` |
| 12 | Hyperdrive went free on the Workers free plan: *"we're making Hyperdrive available on the free plan of Cloudflare Workers!"* — post dated **8 April 2025**. Confirms the "this changed at some point" suspicion; the change was in our favour. | https://blog.cloudflare.com/how-hyperdrive-speeds-up-database-access/ | 2026-08-03 | `[DATA]` |
| 13 | *"The Hyperdrive connection pooler operates in **transaction mode**, where the client that executes the query communicates through a single connection for the duration of a transaction."* | https://developers.cloudflare.com/hyperdrive/concepts/how-hyperdrive-works/ | 2026-08-03 | `[DATA]` |
| 14 | *"Hyperdrive supports SET statements for the duration of a transaction or a query."* — **this is why our pattern survives transaction-mode pooling: everything is inside one explicit transaction.** | same as 13 | 2026-08-03 | `[DATA]` |
| 15 | *"When a connection is returned to the pool, the connection is RESET such that the SET commands will not take effect on subsequent queries."* | same as 13 | 2026-08-03 | `[DATA]` |
| 16 | *"A single Worker invocation may obtain multiple connections to perform its database operations and may need to SET any configurations for every query or transaction."* | same as 13 | 2026-08-03 | `[DATA]` |
| 17 | *"It is not recommended to wrap multiple database operations with a single transaction to maintain the SET state. Doing so will affect the performance and scaling of Hyperdrive, as the connection cannot be reused by other Worker isolates for the duration of the transaction."* — Cloudflare explicitly discourages this app's architecture. Correctness is unaffected; scaling advice only. | same as 13 | 2026-08-03 | `[DATA]` |
| 18 | Hyperdrive **unsupported** for Postgres includes *"Any modification to per-session state not explicitly documented"*, plus `PREPARE`/`DEALLOCATE`/`EXECUTE`, advisory locks, `LISTEN`/`NOTIFY`. `SET LOCAL ROLE` is **not** explicitly named. | https://developers.cloudflare.com/hyperdrive/reference/supported-databases-and-features/ | 2026-08-03 | `[DATA]` |
| 19 | Hyperdrive supports Postgres *"9.0 to 17.x"*; **Supabase listed as supported**; TLS required, *"not support insecure plain text connections"*. | same as 18 | 2026-08-03 | `[DATA]` |
| 20 | Hyperdrive limits: max query duration **60 s**; origin connections **~20 (Free)** / ~100 (Paid); 10 configs (Free); idle connection timeout 10 min. | https://developers.cloudflare.com/hyperdrive/platform/limits/ | 2026-08-03 | `[DATA]` |
| 21 | *"Hyperdrive can only connect to public IP addresses."* | https://developers.cloudflare.com/hyperdrive/observability/troubleshooting/ | 2026-08-03 | `[DATA]` |
| 22 | *"Having query traffic written as transactions can limit performance... the connection must be held for the duration of the transaction, which limits connection multiplexing."* | same as 21 | 2026-08-03 | `[DATA]` |
| 23 | Cloudflare on Supabase: *"When connecting to Supabase from Hyperdrive, you should use the **Direct connection** connection string rather than the pooled connection strings."* Also: use *"node-postgres (pg)"* or *"Postgres.js"*, not supabase-js. The page **never mentions IPv6**. | https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/postgres-database-providers/supabase/ | 2026-08-03 | `[DATA]` |
| 24 | Supabase connection matrix: direct `db.[project-id].supabase.co:5432`; Shared Pooler **session** `aws-[region].pooler.supabase.com:5432`; Shared Pooler **transaction** `aws-[region].pooler.supabase.com:6543`. | https://supabase.com/docs/guides/database/connecting-to-postgres | 2026-08-03 | `[DATA]` |
| 25 | Both Shared Pooler modes are tabled as **Free** and **IPv4**; Shared Pooler is *"multi-tenant, available on every project"* and *"IPv4-only on every tier"*. Dedicated Pooler (PgBouncer) is **Paid**, transaction mode only. | same as 24 | 2026-08-03 | `[DATA]` |
| 26 | *"Transaction mode does not support prepared statements."* | same as 24 | 2026-08-03 | `[DATA]` |
| 27 | Direct connections support *"IPv6, or on IPv4 if the project has the IPv4 add-on"* — i.e. **the Supabase Free direct connection is IPv6-only**. | same as 24 | 2026-08-03 | `[DATA]` |
| 28 | Session mode *"mirrors a direct connection"*; transaction mode releases the connection after each query; session mode *"supports prepared statements"* and is *"IPv4 compatible"*. | https://supabase.com/docs/guides/troubleshooting/supavisor-faq-YyP5tI | 2026-08-03 | `[DATA]` |
| 29 | IPv4 add-on is **Pro plan and above**, ~$0.0055/hour (~$4/month), and is **not dual-stack** — enabling it replaces the AAAA record with an A record. | https://supabase.com/docs/guides/platform/ipv4-address (via search synthesis of the Supabase troubleshooting/IPv4 pages) | 2026-08-03 | `[DATA — secondary rendering; verify on the page before quoting to the Principal]` |
| 30 | `pg` on Workers: *"Make sure you are using `pg` (`node-postgres`) version `8.16.3` or higher."* With `nodejs_compat` and a compatibility date ≥ 2024-09-23. | https://developers.cloudflare.com/workers/tutorials/postgres/ | 2026-08-03 | `[DATA]` |
| 31 | Hyperdrive tutorial states *"pg 8.13.0 or later is recommended"*; connection string read as `env.HYPERDRIVE.connectionString`; config created with `npx wrangler hyperdrive create <NAME> --connection-string="..."`. Take the **higher** floor (8.16.3). | https://developers.cloudflare.com/hyperdrive/get-started/ | 2026-08-03 | `[DATA]` |
| 32 | postgres.js: *"Postgres.js has built-in support for the TCP socket API in Cloudflare Workers"*, requires *"Postgres.js 3.4.0 or later"*; documents `sql.begin()`, `sql.savepoint()`. | https://github.com/porsager/postgres | 2026-08-03 | `[DATA]` |
| 33 | Workers I/O rule: *"I/O objects created in the context of one request handler cannot be accessed from a different request's handler"* — clients must be created per request, not at module scope. | https://opennext.js.org/cloudflare/troubleshooting | 2026-08-03 | `[DATA]` |
| 34 | Error 1102 *"Worker exceeded resource limits"* = CPU or memory exceeded; OpenNext issue #598 *"[BUG] First time load results in Error 1102"* (opened 22 Apr 2025, now **closed**). Corroborating but **not** proof that Next 16 SSR always exceeds 10 ms on Free. | https://github.com/opennextjs/opennextjs-cloudflare/issues/598 | 2026-08-03 | `[INFERENCE]` |

### Corrections / additions to `research/research-infra.md`

- That file evaluated D1, Neon, Turso and Supabase but **never considered Hyperdrive**. Hyperdrive being free (since 8 Apr 2025) is a new, materially favourable fact.
- Its Workers-Free table (10 ms CPU, 3 MB gzipped) is **re-confirmed correct today**. What it did not draw out is the consequence: *those two numbers, together, make Workers Free unsuitable for OpenNext-hosted Next.js.* `[INFERENCE]`
- It did not surface the **Supabase Free direct connection being IPv6-only**, which is the fact that makes Cloudflare's own "use the Direct connection" advice unusable on our plan.

---

## REJECTED, WITH REASONS

### Database path

| Option | Rejected because |
|---|---|
| **Supabase REST / PostgREST HTTP API** | Cannot open a transaction or hold session state. Disqualified by the hard constraint before evaluation. `[INFERENCE]` |
| **Supabase direct connection** `db.<ref>.supabase.co:5432` | IPv6-only on Free (#27); the IPv4 add-on is Pro-and-above (#29); Hyperdrive's IPv6 support for origins is undocumented (#21 says only "public IP addresses"). This is exactly what Cloudflare tells you to use (#23) and it is the recommendation we must decline. |
| **Supavisor transaction mode** `:6543` | Works in principle — `SET LOCAL` survives inside an explicit transaction — but no prepared statements (#26), and any statement outside the transaction silently loses identity. No capacity argument for it at 10–50 users. Rejected as needless risk on the one thing that must not fail. |
| **Dedicated Pooler (PgBouncer)** | Paid plan only, and transaction mode only (#25). Both disqualifying. |
| **Hyperdrive at launch** | Free and probably fine (#11, #14) — but "Any modification to per-session state not explicitly documented" is unsupported (#18) and `SET LOCAL ROLE` is not named; and Cloudflare explicitly advises against one-transaction-per-request (#17). Deferred to a post-launch optimisation, gated on the §Silent-RLS-break assertion passing in production. |
| **Cloudflare D1** | Already settled in `DESIGN.md` §2.1: no India location hint, and it is SQLite — no roles, no RLS, no `SET LOCAL`. The authorisation model does not exist there. |
| **Neon** | No India region; free-limit breach *suspends compute until the next billing month*; free projects idle 90+ days deleted from 5 Oct 2026. (`research-infra.md` §5a, `[DATA]` as of 2026-08-03.) |
| **postgres.js instead of `pg`** | Not rejected — viable (#32). Ranked second only because `pg`'s `{ rows }` result shape matches `SqlRunner` with no mapping layer. |

### Deployment target — is there a materially simpler free host?

No. Every candidate fails at least one of (a) genuinely free, (b) commercial/internal-business use permitted, (c) supports a normal long-lived Postgres connection. All figures below from primary pages fetched 2026-08-03 unless marked.

| Host | Free-tier limits | Idle / spin-down | Commercial use | Verdict |
|---|---|---|---|---|
| **Vercel Hobby** | — | — | **Terms bar commercial use** (firm-established) | Rejected outright |
| **Render** free web service | 750 free instance-hours per workspace per month `[DATA]` | *"Render spins down a Free web service that goes 15 minutes without receiving any inbound traffic"*; restart *"takes about one minute"* `[DATA]` | Docs say *"Do not use them for production applications"* — a support disclaimer, not a licence ban. `render.com/terms` and `/acceptable-use` are JS-rendered and body text could not be retrieved `[UNVERIFIED]` | Rejected: a one-minute cold start on the first morning login, every day, for an internal tool people open in bursts |
| **Google Cloud Run** | *"2 million requests per month. 360,000 GB-seconds of memory, 180,000 vCPU-seconds of compute time. 1 GB of outbound data transfer from North America per month"* `[DATA]`; *"A Google Cloud billing account is necessary to access these always-free benefits"* and that requires a payment method `[DATA]` | Scale-to-zero by default; `min-instances > 0` is billed even while idle `[DATA — mechanism; exact rate UNVERIFIED]` | No restriction found `[UNVERIFIED — no clause quoted]` | Closest real alternative, and the honest fallback if Cloudflare is vetoed. Still needs a card, still cold-starts, and adds a second cloud vendor for zero architectural gain |
| **Azure App Service Free F1** | *"Shared (60 CPU minutes / day)"*, 1 GB RAM, 1 GB storage `[DATA]` | No "Always On" on F1; quota exhaustion suspends the app until UTC midnight `[DATA — quota; suspension behaviour UNVERIFIED verbatim]` | *"Use of free and shared plans for production workloads is not supported"*, *"There is no SLA for free and shared plans"* `[DATA]` | Rejected: 60 CPU-minutes/day is tighter than it sounds, and the app stops serving when it runs out |
| **Koyeb** | *"Each Free Instance provides 512MB of RAM, 0.1 vCPU, and 2GB of SSD"* `[DATA]`; card required — *"We require a credit card to prevent fraud and abuse"* `[DATA]` | *"They scale down to zero when they don't receive any traffic for 1 hour"* `[DATA]` | Docs: free instance *"should not be used for production applications"* `[DATA]` | Rejected: and the live pricing page no longer shows a free compute tier at all, so signup availability is doubtful `[UNVERIFIED]` |
| **Deno Deploy** | 1M requests/month, 15h CPU/month, 20 GB transfer, 20 apps `[DATA]` | Request-driven | — | Rejected: **Deno Deploy Classic — the variant with confirmed raw-TCP `Deno.connect` support — shut down 20 July 2026** `[DATA]`, and raw outbound TCP on the current platform could not be confirmed `[UNVERIFIED]`. Cannot bet an authorisation model on an unconfirmed socket API |
| **Oracle Cloud Always Free (A1 ARM VM)** | Allowance **halved on 2026-06-15** to *"the first 1,500 OCPU hours and 9,000 GB hours per month... equivalent to 2 OCPUs and 12 GB of memory"* `[DATA]`; card generally required | *"Oracle will deem virtual machine and bare metal compute instances as idle if, during a 7-day period... CPU utilization for the 95th percentile is less than 20%; Network utilization is less than 20%; Memory utilization is less than 20% (applies to A1 shapes only)"* `[DATA]` — reclamation, not suspension | No restriction found in Always Free docs `[UNVERIFIED — ToS not read]` | Rejected: a 10–50 user internal CRM will sit under 20% on all three metrics continuously. The penalty is losing the instance |
| **Northflank Sandbox** | Pricing page: *"Always-on-compute – no sleeping :)"*, 2 free services, 1 free database, 2 free cron jobs `[DATA]` | None claimed | A secondary summary says the free tier *"should not be used for production"* `[UNVERIFIED — not located on a primary Northflank page]`; card requirement ambiguous `[UNVERIFIED]` | The only host making a genuine always-on free claim. Worth a 15-minute signup check if the Principal refuses the $5 — but do not plan on it |
| Fly.io / Railway / Xata / Clever Cloud / Scalingo / Sevalla | No free tier for a server process (trial credits or paid-only) `[DATA]` | — | — | Rejected |
| Hugging Face Spaces / Zeabur | Sleep after inactivity (48 h / unstated) `[UNVERIFIED verbatim]` | Sleeps | Not checked | Rejected |

`[OPINION]` The comparison resolves cleanly. $5/month for Workers Paid buys: no cold start, a 10 MiB bundle ceiling, 30 million CPU-ms/month, Cloudflare Access already in front of it, and no second vendor. Every free alternative trades that for a daily cold start, a daily CPU quota, or an instance that can be reclaimed. For a tool whose whole purpose is that people actually use it every morning, that is the wrong trade.

---

## STILL UNVERIFIED

| # | Unknown | Why it matters | What would settle it |
|---|---|---|---|
| 1 | Whether Hyperdrive can connect to an **IPv6-only** origin | Would make Cloudflare's own "use the Direct connection" advice usable on Supabase Free. Currently the reason we take the pooler instead | Ask Cloudflare support, or create a Hyperdrive config against `db.<ref>.supabase.co:5432` and see whether it resolves. `hyperdrive/llms-full.txt` contains **no** occurrence of IPv6/IPv4/AAAA — Cloudflare simply does not document it |
| 2 | Whether `SET LOCAL ROLE` counts as *"per-session state not explicitly documented"* for Hyperdrive | Decides whether Hyperdrive can ever be layered in | The §Silent-RLS-break assertion (defence 3), run against a Hyperdrive binding in a preview deployment. That test is the answer — do not reason about it |
| 3 | Whether a Next 16 + React 19.2 OpenNext bundle for **this** app fits 3 MiB gzipped, and whether a page render fits 10 ms CPU | Decides whether Workers Free is even theoretically an option | `npx opennextjs-cloudflare build` and read the reported gzipped size. **Not run here — the machine is memory-constrained and the brief forbids builds** |
| 4 | Exact Supabase session-mode **username form** and the `aws-<N>-` host prefix for our project | Wrong username is the most common Supavisor connection failure | Copy the string from Dashboard → Settings → Database → Session pooler. Do not derive it |
| 5 | Supabase Free **Supavisor pool size** and max client connections | Hyperdrive alone can hold *~20 origin connections* on Free (#20). If Supabase Free's pool is smaller, Hyperdrive could exhaust it. Mitigable: Hyperdrive's connection count is configurable (min 5, per the 2025-07-02 changelog) | Read Dashboard → Settings → Database → Connection pooling → Pool size on the real project |
| 6 | Whether `global_fetch_strictly_public` is required for us (#5) | It is in OpenNext's example flags and absent from our `wrangler.toml` | OpenNext's flag reference; or first deploy |
| 7 | Render's actual ToS/AUP wording on commercial use | Only matters if Cloudflare is vetoed | Open `render.com/terms` in a real browser and search "commercial" |
| 8 | Cloud Run `min-instances` idle cost; Azure F1 "always free vs 12-month"; Northflank card + production terms | Only matters if Cloudflare is vetoed | Vendor pages in a browser / signup flow |
| 9 | Whether the nightly `pg_dump` cron in `wrangler.toml` is achievable at all | A Worker has no `pg_dump` binary, and cron invocations on Free also carry the 10 ms CPU cap. **The backup job, which is `DESIGN.md`'s answer to Supabase Free having zero backups, probably cannot live in the Worker.** Flagged here because `wrangler.toml` currently implies it can | Decide between GitHub Actions (with the caveat from `research-infra.md` §8a about `schedule` delays) or a Worker that streams SQL rather than shelling out to `pg_dump` |

---

*Scope note: this file was the only file created or modified. No build, test, or dev server was run.*
