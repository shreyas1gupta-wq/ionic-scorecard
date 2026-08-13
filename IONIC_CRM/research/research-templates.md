# Dimension: Free templates / code to start from — and FORK vs BUILD

**Research date: 2026-08-03.** All GitHub numbers below were pulled from the GitHub REST API
(`api.github.com/repos/{owner}/{repo}`) on that date. Free-tier limits and licences change —
re-verify before committing.

**Environment note discovered during research:** `raw.githubusercontent.com` times out through the
corporate proxy (6/6 attempts). `api.github.com` works fine. `gh` CLI is NOT installed on this
machine. Unauthenticated GitHub API is capped at 60 req/hr per IP, and the corporate NAT shares that
budget — I hit the cap mid-run. Anyone re-running this needs a GitHub token.

---

## A. What the user asked for by name: "Claude small business"

### There is no Anthropic CRM or ticketing template. Not on GitHub, not anywhere.

**[DATA]** "Claude for Small Business" is a real Anthropic product, announced **2026-05-13**, but it
is **not code and not a template**. It is a bundle of connectors and prebuilt workflows that run
*inside Claude Cowork*. Source: <https://www.anthropic.com/news/claude-for-small-business>
- Connectors named: PayPal, Intuit QuickBooks, HubSpot, Canva, Docusign, Google Workspace,
  Microsoft 365.
- Ships "15 ready-to-run agentic workflows" + "15 skills": payroll planning, month-end close,
  business pulse reporting, campaign management, invoice chasing, margin analysis, tax organisation,
  contract review, lead triage, content strategy.
- **[DATA]** The announcement contains no deployable web app, no GitHub repo, and no self-hosted
  ticketing system. It is cloud integrations with existing commercial SaaS.

**[INFERENCE]** It is therefore the wrong tool for this job in two ways: it is not a codebase you can
deploy, and it is gated behind a paid Claude subscription tier — which fails the zero-rupee
constraint regardless.

### What Anthropic *does* publish (checked, for completeness)

| Repo | Licence | Stars | Last push | Relevance |
|---|---|---|---|---|
| `anthropics/claude-quickstarts` | MIT | 17,364 | 2026-07-24 | No CRM/ticketing. Contains computer-use demo, **customer-support-agent** (an AI chat agent over a knowledge base — *not* a ticket system), financial-data-analyst, browser automation, autonomous coding agent |
| `anthropics/skills` | **no LICENSE file** (API `/license` → 404) | 165,928 | 2026-07-24 | Claude skills, not app code |

**[DATA]** I checked the `anthropics` org repo listing for CRM / ticketing / helpdesk / admin-dashboard
templates. There are none. The nearest business-domain repos are `financial-services`,
`claude-for-legal`, `knowledge-work-plugins` — all Claude plugin/skill suites, not web apps.

> **Say this plainly to the user:** the thing you had in mind does not exist as a template. I am not
> substituting something else and calling it that. `claude-quickstarts/customer-support-agent` is the
> closest-named artifact and it is an LLM support chatbot, not a ticket tracker — it would not save
> you any work here.

---

## B. Frontend admin / dashboard starters

All data from GitHub API, 2026-08-03.

| Repo | Licence | Stars | Last push | Archived | Verdict for a ticket CRUD app |
|---|---|---|---|---|---|
| `shadcn-ui/ui` | MIT | 120,386 | 2026-07-31 | No | **Best foundation.** Components+blocks are copy-in, you own the code |
| `ant-design/ant-design-pro` | MIT | 38,622 | 2026-07-29 | No | Capable but heavy Ant ecosystem lock-in; steep for a non-engineer |
| `refinedev/refine` | MIT | 35,451 | 2026-06-05 | No | See deep-dive below — powerful, real caveats |
| `mantinedev/mantine` | MIT | 31,524 | 2026-08-02 | No | Component lib (not admin template); very healthy |
| `satnaing/shadcn-admin` | MIT | 12,796 | 2026-07-21 | No | **UI-only, mock data.** Author states "This is not a starter project (template) though" |
| `Kiranism/next-shadcn-dashboard-starter` | MIT | 6,760 | 2026-07-29 | No | **Strongest ready starter** — see below |
| `creativetimofficial/material-tailwind` | MIT | 4,362 | 2026-04-28 | No | 214 open issues; component lib, not app scaffold |
| `tremorlabs/tremor` | Apache-2.0 | 3,543 | **2025-10-10** | No | ~10 months stale; charts/KPI only, not CRUD |
| `imbhargav5/nextbase-nextjs-supabase-starter` | MIT | 801 | 2026-07-01 | No | Next.js+Supabase base; upsold to paid kits |
| `horizon-ui/horizon-ui-chakra-nextjs` | MIT | 315 | **2025-01-13** | No | Effectively abandoned. Skip |
| `shadcn-ui/next-template` | **none** | 1,495 | 2025-07-28 | **ARCHIVED** | Dead. Skip |

### Notable individual findings

**`Kiranism/next-shadcn-dashboard-starter`** — MIT, 6,760 stars, pushed 2026-07-29. **[DATA]** Next.js
16 App Router, React 19, TS, Tailwind v4, shadcn/ui on Base UI. Includes data tables with server
prefetch + URL-synced search/filter/sort/pagination, TanStack Form + Zod with real create/update
mutations and cache invalidation, Kanban board, notifications, dark mode with six themes. Data is
mock. **No ticket/issue feature.** **Auth is Clerk** (passwordless, social, enterprise SSO).
**[INFERENCE]** This is the best-fitting free starter — the data-table and form plumbing is exactly
the tedious part of a ticket app. But the Clerk dependency must be ripped out to honour the decided
email-OTP model, and that touches routing/middleware/layout. Budget half a day to a day for the
extraction, and expect it to be the single fiddliest part of adopting this starter.

**`satnaing/shadcn-admin`** — **[DATA]** UI-only template with mock/local state, no backend, no DB;
partial Clerk integration; Vite + TanStack Router (**not** Next.js). The author explicitly says it is
not a starter project. **[OPINION]** Excellent to read for UI patterns, wrong thing to build a real
app on top of — and the Vite/TanStack-Router stack diverges from the Next.js-on-Cloudflare path.

**Tailwind Plus (formerly Tailwind UI) — CORRECTION to the brief.** **[DATA]** It is **entirely
paid**. No components are free. Personal ₹8,500 one-time, Team ₹25,000 (up to 25 seats), India PPP
pricing, lifetime access, 30-day refund. Source: <https://tailwindcss.com/plus>. Licence permits
commercial/SaaS use but bars derivative UI kits/resale. **This fails the zero-rupee constraint** —
the brief's phrase "Tailwind UI free components" is not accurate. Use **shadcn/ui blocks** instead:
MIT, free, and you own the copied source.

**Tremor** — **[DATA]** Core components Apache-2.0/MIT and free; repo last pushed 2025-10-10; npm
package `3.18.7` reportedly last published ~2 years ago; blocks moved from npm to copy-paste; premium
blocks/templates behind a paid plan. **[OPINION]** Signals are mixed and the project looks like it is
drifting. For KPI tiles on a ticket dashboard, shadcn/ui + Recharts covers it without adopting a
semi-stale dependency.

### `refinedev/refine` — deep dive (as requested)

**[DATA]** MIT (© 2021–present Refinedev), 35,451 stars, pushed 2026-06-05. A React meta-framework
for CRUD-heavy internal tools/admin panels.

- **Supabase data provider: YES.** One of 15+ supported backends (REST, GraphQL, NestJS CRUD,
  Airtable, Strapi, Supabase, …).
- **authProvider: YES.** First-class provider interface.
- **accessControlProvider: YES** — agnostic async `can({ resource, action, params })` → `CanResponse`.
  Supports RBAC/ABAC/ACL, integrates Casbin, CASL, Cerbos, AccessControl.js. Passes the whole
  resource metadata object, so ABAC on field values is possible. Auto-integrates with the UI: sider
  hides inaccessible resources, Edit/Delete buttons auto-disable, `hideIfUnauthorized: true` hides
  rather than disables.
- **⚠ CRITICAL CAVEAT — [DATA], quoted from refine's own docs:** "Providing `accessControlProvider` to
  the `<Refine/>` component **won't enforce** access control by itself." You must manually wrap
  protected routes in `<CanAccess/>`. There is **no server-side enforcement** — it is a UI-layer
  concern only; backend access control is entirely your job.
  Source: <https://refine.dev/docs/authorization/access-control-provider/>
- **Inferencer — [DATA]:** supports `antd`, `material-ui`, `mantine`, `chakra-ui`, and a `headless`
  variant. It returns **a string of component code for List/Show/Create/Edit that you copy-paste**.
  refine's docs state explicitly: "Inferencer components are meant to be used in development
  environments. **They are not meant to be used in production environments.**" So it is a
  bootstrapping/scaffolding aid, not a code generator you ship.
- **shadcn/ui:** **not an official integration.** Official UI packages are Ant, MUI, Mantine, Chakra.
  shadcn works only via the headless variant + DIY wiring; there is a refine *blog post* on it and a
  third-party `ferdiunal/refine-shadcn` package (I could not verify that repo's health — API
  rate-limited; treat as **UNVERIFIED**).

**[OPINION] Fit for this project: poor, despite being a good framework.** Two reasons. (1) The
headline feature you'd adopt it for — role-based visibility — is explicitly UI-only, so for a
SEBI-regulated firm you'd still write every real authorisation rule in the database. A framework
that hides buttons but doesn't stop requests is a compliance trap, not a compliance feature. (2) The
shadcn path is unofficial, so you'd take on refine's abstractions *and* hand-wire the UI. For a
single ~6-table app built by a non-engineer, refine's concept count (resources, providers, hooks,
router bindings) is a real tax with little payoff.

### Ticketing-specific React/Next.js starters — [DATA] nothing usable

- `mvpstack/helpin` (Supabase + Next.js + Vercel support ticketing): 159 stars, **last push
  2023-01-11**, **NO LICENCE FILE**. No licence = all rights reserved = you have no legal right to
  reuse it. Dead and unusable.
- The `ticketing-system` / `helpdesk-ticketing` GitHub topics are dominated by student projects and
  abandoned repos. **[OPINION]** Nothing here beats starting from a clean dashboard starter.

---

## C. Fork-instead-of-build candidates

All data from GitHub API, 2026-08-03.

| Project | Licence (verified) | Stars | Last push | Status | Footprint |
|---|---|---|---|---|---|
| `makeplane/plane` | AGPL-3.0 | 55,394 | 2026-08-03 | Active, 978 open issues | **4GB min, 8GB rec** |
| `twentyhq/twenty` | AGPL-3.0 + custom exception + commercial carve-out | 54,139 | 2026-08-03 | Active | Heavy (Postgres+Redis+worker) |
| `frappe/erpnext` | GPL-3.0 | 37,541 | 2026-08-03 | Active | **4–8GB** |
| `chatwoot/chatwoot` | MIT **+ `enterprise/` dir under separate licence** | 35,422 | 2026-08-03 | Active | Heavy (Rails+PG+Redis+Sidekiq) |
| `kanboard/kanboard` | MIT | 9,763 | 2026-08-01 | Active | **Very light** (PHP+SQLite/MySQL) |
| `redmine/redmine` | GPL-2.0 | 6,008 | 2026-08-03 | Active since 2006 | Light-moderate (Ruby) |
| `zammad/zammad` | AGPL-3.0 | 5,822 | 2026-08-03 | Active, 451 open issues | **6GB + 4GB Elasticsearch** |
| `SuiteCRM/SuiteCRM` | AGPL-3.0 | 5,616 | 2026-07-31 | Active, 1,411 open issues | Moderate (LAMP), dated UX |
| `go-vikunja/vikunja` | AGPL-3.0 | 4,967 | 2026-08-03 | Active | **~50MB idle, ~200MB with PG** |
| `freescout-help-desk/freescout` | AGPL-3.0 | 4,454 | 2026-08-03 | Active, only 22 open issues | **Very light** (PHP/Laravel, shared hosting OK) |
| `osTicket/osTicket` | GPL-2.0 | 3,863 | 2026-06-17 | Slow, 1,200 open issues | Light (PHP/MySQL) |
| `frappe/helpdesk` | AGPL-3.0 | 3,280 | 2026-08-03 | Active | **4–8GB** (Frappe stack) |
| `espocrm/espocrm` | AGPL-3.0 | 3,186 | 2026-07-30 | Active | Moderate (PHP/MySQL) |
| `polonel/trudesk` | Other/NOASSERTION | 1,492 | 2026-05-11 | Low activity | Moderate (Node+MongoDB) |
| `kaleidos-ventures/taiga` | MPL-2.0 | 565 | **2023-12-13** | **Stale ~2.5yr** | Heavy |
| `Peppermint-Lab/peppermint` | Other/NOASSERTION | 3,157 | 2025-09-21 | **ARCHIVED 2026-07-17** | — |
| `mattermost-community/focalboard` | Other/NOASSERTION | 26,360 | 2026-05-18 | **UNMAINTAINED** | — |

### Disqualified outright

- **Peppermint — [DATA] archived by the owner on 2026-07-17, now read-only, no successor named.**
  Licence is non-standard ("Other"). This was the closest-fitting candidate on paper (Next.js +
  Postgres + Prisma, ticket creation with markdown + file uploads, client history log). It is now a
  dead end: no security patches. **Do not adopt.**
- **Focalboard — [DATA]** README carries "This repository is currently not maintained." Mattermost
  moved on to `mattermost/mattermost-plugin-boards`. Skip.
- **Taiga — [DATA]** `kaleidos-ventures/taiga` last pushed 2023-12-13. Skip.

### Licence reality check — AGPL for internal self-hosting

This is the point most commentary gets wrong in both directions, so here is the licence text logic.

**[DATA]** AGPL-3.0 §13 "Remote Network Interaction" triggers **only if you modify the Program** and
the modified version is reachable over a network. The obligation is to offer the Corresponding Source
to "**all users interacting with it remotely through a computer network**."
**[DATA]** AGPL-3.0 §0 defines conveying as "any kind of propagation that enables other parties to
make or receive copies," and states: "**Mere interaction with a user through a computer network, with
no transfer of a copy, is not conveying.**"

**[INFERENCE] Practical upshot for this project:**
1. Running an **unmodified** AGPL app for your own staff triggers **no** §13 duty beyond source
   already being public upstream.
2. If you **do** modify it, you must offer source **to the people who use it** — i.e. your own
   colleagues. There is **no duty to publish to the public**. Putting the modified repo where those
   employees can reach it satisfies this.
3. Internal use is not "conveying," so GPL-style distribution obligations do not fire.

**So: AGPL is not a blocker for internal-only deployment.** Do not let anyone scare you off Plane,
Vikunja, or FreeScout on licence grounds. **[OPINION]** The genuine reasons to decline these are
operational (RAM, patching, upgrade burden), not legal.

**Caveats I will not paper over:**
- **[DATA]** One professional source (VanL, CEO of OSPOCO, an open-source compliance consultancy)
  argues contractors/staffing-agency personnel with network access can be argued to trigger
  distribution obligations "even if the software never leaves the building," and cautions against
  rules of thumb. Sources genuinely disagree on where the employee/third-party line sits.
- This is my reading of licence text, **not legal advice**. A SEBI-regulated entity redistributing
  nothing and modifying nothing is in the safest possible position; the moment you fork-and-patch,
  loop in whoever signs off on IP.
- **Watch the carve-outs, not the headline licence.** Chatwoot is MIT *except* `enterprise/` which is
  under separate terms. Twenty is AGPL *plus* a "Twenty Application Exception" *plus*
  `/* @license Enterprise */` files under a Twenty.com Commercial Licence. Both are more accurately
  described as **source-available**. Deleting or avoiding those directories matters if you fork.

### Feature-fit against our actual requirements

| Requirement | Best fork fit | Reality |
|---|---|---|
| Ticket w/ deadline + assignee | Vikunja, Redmine, Plane | Native in all three |
| **Append-only status log, never overwritten** | **none** | **[INFERENCE] This is the gap.** Vikunja/Plane/Redmine comments are editable/deletable by the author. Helpdesk-model tools (osTicket, Zammad, FreeScout) have effectively append-only threads, but their model is "customer emails in, agent replies" — not "manager assigns, assignee punches periodic status" |
| Manager/admin all-status dashboard | Plane, Redmine | Plane's views are good; Redmine's are dated but functional |
| Email-OTP login, no SSO | **Plane** | **[DATA]** Plane self-hosted supports login "with codes sent over email," requires SMTP, configured at `/god-mode`. Also supports passwords, Google/GitHub OAuth, OIDC, SAML, LDAP. Vikunja/Redmine/osTicket are password or OIDC — **no passwordless email option**, which contradicts the decided login model |
| Allow-list signup | Plane (`ENABLE_SIGNUP=false`) | **⚠ [DATA]** Plane issue #1792 reports magic-link signin creating new accounts **despite** `ENABLE_SIGNUP=false`. Old issue, probably fixed, but **UNVERIFIED on current version** — this is exactly the bug class that would breach an allow-list. Test it explicitly before trusting it |
| Audit trail / immutable history | Redmine, Zammad | **UNVERIFIED for Plane** — I could not confirm whether Plane Community has an audit log or whether activity history is immutable. Plane's docs do not state which features are gated to paid editions |
| Retention / purge policy | **none** | No candidate ships configurable retention/purge. Custom work either way |

**[DATA]** Plane editions: Cloud, Community (self-hosted), Commercial (self-hosted), Airgapped.
Community is "at par with the Free tier of the Cloud edition." Plane's own edition docs **do not
specify** which features are gated — I could not determine whether SSO/OIDC, custom roles, or audit
logs are paid-only. Treat as **UNVERIFIED**.

### The hosting problem that decides this

**[DATA]** Minimum footprints: Plane 4GB (8GB rec) — <https://developers.plane.so/self-hosting/methods/docker-compose>.
Zammad 2 cores + 6GB, +4GB if Elasticsearch same host; 6 cores + 6GB (+6GB ES) for up to 40 agents —
<https://docs.zammad.org/en/latest/prerequisites/hardware.html>. Frappe Helpdesk 4–8GB.
Vikunja ~50MB idle / ~200MB with Postgres, whole setup ~1GB. FreeScout: PHP/Laravel, PHP 7.1–8.x,
MySQL/MariaDB/Postgres, runs on shared hosting, no stated CPU/RAM minimum.

**[INFERENCE] This is the crux.** The firm has settled on Cloudflare's free tier (commercial use
explicitly permitted, push-to-GitHub deploys). **Cloudflare Workers/Pages cannot host any of these
forks** — they are Docker/PHP/Rails/Ruby/Go-binary apps needing a persistent VM, a real filesystem,
and a managed database. Choosing a fork means abandoning the settled hosting decision.

**[UNVERIFIED — flagging to the hosting dimension, I did not confirm against Oracle's own docs]**
The only credible free-forever VM is Oracle Cloud Always Free. Secondary sources (blogs, gists) say:
ARM Ampere A1 was 4 OCPU/24GB, **reduced to 2 OCPU/12GB for free-tier users from June 2026**; Oracle
**reclaims instances idle below 10% CPU and 10% network over 7 days**; "Out of Capacity" errors on
signup are notoriously common. All from secondary sources — verify on Oracle's primary docs. A card
is required at signup, which brushes against the user's stated constraint.

**[OPINION]** Even if Oracle works, the fork route hands a portfolio manager a Linux VM to patch, a
Postgres to back up, TLS certs to renew, and an instance that gets reclaimed if the app is quiet over
a weekend — for a 10-50 person internal tool. That is the real cost, and it is not zero.

---

## D. Verdict: BUILD. Do not fork.

**[OPINION], and I hold it firmly.** Reasons, in the order that actually matters:

1. **The one feature that defines this app is the one no fork provides.** The append-only status punch
   *is* the product — it is what makes the log trustworthy for a regulated firm. Every task-tracker
   candidate has editable comments. To fork, you would patch someone else's ORM and UI to revoke edit
   and delete, then re-apply that patch against every upstream release forever. That is strictly worse
   than both alternatives: you inherit their maintenance burden **and** write custom code, and your
   patch fights every upgrade. In a build, append-only is ~15 lines: a `status_updates` table with
   `UPDATE` and `DELETE` privileges revoked at the database role level. Enforced by Postgres, not by
   good intentions.
2. **Hosting.** Forking abandons the settled, verified, genuinely-free Cloudflare path for an
   unverified free VM with idle-reclamation and a documented 2026 downgrade.
3. **Auth.** Only Plane matches the decided email-OTP model, and its allow-list enforcement has an
   open-issue history I could not clear. Supabase/PocketBase give you email OTP as a first-class,
   documented primitive.
4. **Surface area = risk.** Plane has 978 open issues, Zammad 451, osTicket 1,200, SuiteCRM 1,411.
   You would be responsible for patching a large third-party attack surface holding employee data,
   with no IT team behind you. A ~6-table app you wrote has a surface you can actually reason about.
5. **Scope is genuinely small.** Tickets, assignees, deadlines, append-only updates, a dashboard.
   This is not an ERP. Forking ERPNext or SuiteCRM to get it is using a shipping container to post a
   letter.

### Recommended stack

- **Frontend:** Next.js + **shadcn/ui** (MIT, 120k stars, pushed 2026-07-31) — copy-in components, you
  own the code, no dependency to go stale. Lift layout/data-table/form patterns from
  `Kiranism/next-shadcn-dashboard-starter` (MIT, Next.js 16, actively maintained), and **strip Clerk**.
- **Backend/auth:** Supabase (email OTP + Postgres **Row Level Security**, so authorisation is enforced
  in the database, not the UI) **or** PocketBase.
  - **[DATA] PocketBase**: MIT, 60,427 stars, pushed 2026-08-02, **native email OTP**, OAuth2, MFA,
    single binary, built-in admin dashboard, per-collection API rules. **Currently v0.39.10 — pre-1.0**,
    and it needs a persistent host, so it does **not** fit the Cloudflare model. Note both facts.
- **Do NOT use refine** — its access control is UI-only by its own documentation, and its shadcn
  support is unofficial.
- **Do NOT buy Tailwind Plus** — paid, and shadcn/ui blocks cover the need free.

### Honest effort estimate — build route

For a portfolio manager, not a full-time engineer, working with Claude Code, on a Windows laptop with
no admin rights:

| Work | Estimate |
|---|---|
| Schema + append-only enforcement (revoke UPDATE/DELETE, RLS policies) | 1–2 sessions |
| Email OTP + allow-list gate | 1–2 sessions |
| Ticket CRUD + assignee + deadline | 2–3 sessions |
| Manager/admin dashboard + role-based visibility (server-side) | 2–3 sessions |
| Audit view, retention/purge job | 1 session |
| Polish, deploy, pilot with real colleagues, fix what they break | 2–4 sessions |
| **Total** | **~10–15 focused sessions ≈ 40–80 hours** |

**[OPINION]** Spread over evenings/weekends that is roughly 4–8 weeks to something 10-50 people can
genuinely rely on. Anyone promising a weekend is discounting the last two rows — and the last two rows
are where internal tools actually live or die. The pilot row in particular is not padding: real users
will find the ambiguities in your status workflow that you cannot see.

### Ongoing maintenance reality

- **Build route:** dependency/security updates ~1–2 hrs/month. No OS, no DB server, no TLS to manage
  if you stay on Cloudflare + managed Postgres. You understand 100% of the code, so bugs are
  tractable. **Main risk: you are the single point of failure** — if you leave the firm or get busy,
  nobody else can maintain it. Mitigate now: a real README, the repo owned by a company GitHub
  account rather than your personal one, and one colleague who has deployed it once.
- **Fork route:** ~2–5 hrs/month steady state (OS patching, `docker compose pull` + migrations, DB
  backups you must test-restore, cert renewal, monitoring that the free VM is still alive), **plus
  incident time**, **plus merge-conflict work on every upgrade** if you patched it for append-only.
  Upstream also moves without asking you: Peppermint was archived in July 2026 and Focalboard went
  unmaintained — both were reasonable-looking picks not long ago.

### If the user insists on forking anyway

Ranked, with reasons:
1. **Vikunja** (AGPL-3.0, ~200MB, actively pushed 2026-08-03) — lightest thing that actually models
   tasks with due dates, assignees, comments. Cost: no passwordless email login, comments not
   append-only.
2. **Plane** (AGPL-3.0, very active) — best feature and auth fit, **but 4GB minimum** and an unresolved
   allow-list question. Only viable if a 4GB+ VM genuinely exists for free.
3. **FreeScout** (AGPL-3.0, PHP, shared-hosting-friendly, only 22 open issues — a healthy signal) —
   cheapest to host by far, but it is a shared-inbox email helpdesk; the internal-assignment workflow
   would be a misfit.
4. **Redmine** (GPL-2.0, maintained since 2006) — the best audit/journal story and genuinely battle-
   tested, at the cost of a dated UI and password-based login.

Not recommended at any point: Zammad (10GB with Elasticsearch), Frappe Helpdesk / ERPNext (4–8GB),
SuiteCRM (1,411 open issues), Twenty / Chatwoot (source-available carve-outs, heavy), Peppermint
(archived), Focalboard (unmaintained), Taiga (stale), Trudesk (non-standard licence, low activity).

---

## Open questions / what I could not verify

1. **Plane Community feature gating** — are audit logs, custom roles, or OIDC paid-only? Plane's own
   edition docs do not say.
2. **Plane `ENABLE_SIGNUP=false` + magic link** — is issue #1792 (magic link creating accounts despite
   signup being disabled) fixed on current release? Must be tested directly, not assumed.
3. **Oracle Cloud Always Free** current terms — needs verification against Oracle primary docs, not
   blogs. Owned by the hosting dimension.
4. **`ferdiunal/refine-shadcn`** health/licence — rate-limited before I could check. Moot if refine is
   dropped.
5. **Whether append-only is a stated firm/regulatory requirement or the user's own design preference.**
   This changes the verdict's weight considerably. My recommendation assumes it is a real requirement
   because it is the load-bearing reason to build rather than fork — worth confirming explicitly.
6. **Employee-data scope** — whether "employees as AGPL network users" matters at all depends on
   whether any contractor or third party ever gets access. Worth a one-line answer before forking.

## Sources

- <https://www.anthropic.com/news/claude-for-small-business>
- <https://github.com/anthropics/claude-quickstarts>
- <https://refine.dev/docs/authorization/access-control-provider/>
- <https://refine.dev/docs/packages/inferencer/>
- <https://tailwindcss.com/plus>
- <https://developers.plane.so/self-hosting/methods/docker-compose>
- <https://developers.plane.so/self-hosting/govern/authentication>
- <https://developers.plane.so/self-hosting/editions-and-versions>
- <https://docs.zammad.org/en/latest/prerequisites/hardware.html>
- <https://pocketbase.io/docs/authentication/>
- <https://opensource.org/license/agpl-v3> (AGPL §13 / §0 text)
- <https://ospo.co/blog/questions-and-answers-about-the-agpl/> (VanL, OSPOCO — dissenting view on internal use)
- <https://github.com/chatwoot/chatwoot/blob/develop/LICENSE>, <https://github.com/twentyhq/twenty/blob/main/LICENSE>, <https://github.com/redmine/redmine/blob/master/LICENSE.txt>
- <https://github.com/Peppermint-Lab/peppermint> (archive notice), <https://github.com/mattermost-community/focalboard> (unmaintained notice)
- GitHub REST API `/repos/{owner}/{repo}` for all licence/star/push/archived data, retrieved 2026-08-03
