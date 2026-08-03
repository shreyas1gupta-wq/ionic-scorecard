# DIMENSION: Current free-tier facts for every candidate host / DB / email / storage / monitoring service

**Research date: 2026-08-03.** Every number below was fetched from the vendor's own live page on this date unless
explicitly marked otherwise. Free tiers change without notice — anything older than ~30 days should be re-checked
before it is relied on for a go-live decision.

**Method note:** where a vendor page returned HTTP 403/404 to direct fetch (Brevo pricing, Oracle FAQ, Backblaze
pricing, Turso locations), I say so and fall back to a *different page from the same vendor* where possible, or to
search-surfaced third-party trackers which I tag as lower-confidence. I have not silently substituted memory for any
number.

**Confidence tags:** `[DATA]` = read from a named primary source page on 2026-08-03. `[INFERENCE]` = my reasoning
from that data. `[OPINION]` = judgment. `[UNVERIFIED]` = could not confirm; what I'd need is stated.

---

## 0. EXECUTIVE ANSWER (read this if you read nothing else)

Three findings reorder the whole decision:

1. **Cloudflare Access One-time PIN removes the need for an email service in the login path entirely.**
   Cloudflare's own words: *"Cloudflare Access can send a one-time PIN (OTP) to approved email addresses as an
   alternative to integrating an identity provider."* `[DATA]` No IdP, no SSO tenant, no SMTP provider, no DNS
   records, no password storage, no OTP code for you to write. This is the single highest-leverage fact in this
   research and it directly answers the "no SSO available" constraint.
2. **It works on `*.pages.dev`, so you do not need control of `ionic.in` DNS.** Documented (under Known Issues) as
   a supported configuration. `[DATA]` This removes the dependency that would otherwise have blocked the whole plan.
3. **D1 cannot be pinned to India; Supabase Mumbai (ap-south-1) can.** D1's only location hints are
   `wnam/enam/weur/eeur/apac/oc` — *"There is no India-specific location hint"* and *"Providing a location hint does
   not guarantee that D1 runs in your preferred location."* `[DATA]` This is the one real trade-off between the two
   candidate stacks below.

**And one fact that shrinks a perceived problem:** DPDP Act 2023 s.16(1) is a *negative list*, not localisation:
*"The Central Government may, by notification, restrict the transfer of personal data by a Data Fiduciary for
processing to such country or territory outside India as may be so notified."* `[DATA]` No restricted-country list
has been notified. So "data must be in India" is **not** a DPDP requirement. (SEBI's own cyber framework is a
separate question — flagged as an open question for the compliance dimension, not asserted here.)

---

## 1. SUPABASE FREE TIER

Source: <https://supabase.com/pricing> (fetched 2026-08-03) unless noted.

| Item | Free plan value | Source |
|---|---|---|
| Database size | **500 MB** (Shared CPU, 500 MB RAM) | pricing page `[DATA]` |
| Egress | **5 GB** + 5 GB cached egress | pricing page `[DATA]` |
| Auth MAU | **50,000 monthly active users** | pricing page `[DATA]` |
| Active projects | **2** | pricing page `[DATA]` |
| Inactivity pause | **paused after 1 week of inactivity** | pricing page `[DATA]` |
| Automated backups | **none** | backups doc `[DATA]` |
| PITR | **not available** on Free | pricing page + backups doc `[DATA]` |
| File storage | **1 GB**, max upload **50 MB** | pricing page `[DATA]` |
| Edge Function invocations | 500,000 / month | pricing page `[DATA]` |
| Log retention | **1 day** (API & DB); auth audit logs **1 hour** | pricing page `[DATA]` |
| Support | Community only | pricing page `[DATA]` |
| DPA / SOC2 / ISO 27001 / HIPAA | **not included on Free** | pricing page `[DATA]` |

### 1a. India / Mumbai region on FREE specifically
`ap-south-1` **is listed** as an available region, and the regions doc contains **no statement restricting any
region by plan tier** — the only restriction mentioned is that *"General regions aren't yet supported for read
replicas or management via the API"*, which applies universally, not by plan.
Source: <https://supabase.com/docs/guides/platform/regions> `[DATA]`

**`[UNVERIFIED]`** — I could not confirm from inside the project-creation UI that a *Free* project may select
ap-south-1, because that requires an authenticated account. The documented position is that region choice is not
plan-gated. **What to check:** create a throwaway free project and confirm "South Asia (Mumbai) ap-south-1" is
selectable, before committing to this as the data-residency story. This is a 3-minute check and it is worth doing
first, because it is the load-bearing fact for the "data stays in India" claim.

### 1b. Inactivity pause — mechanics and the real risk
Primary source: <https://supabase.com/docs/guides/platform/free-project-pausing> `[DATA]`
- Trigger: *"A Free plan project is considered inactive if it does not receive sufficient user database activity
  over the past week."*
- What counts: *"Typically a few user requests to the database each day over the previous week is enough to keep
  the project from being paused."*
- Unpause: manual — Dashboard → select project → *"Resume project and confirm"*.
- Window: *"You can restore a paused project for up to 1 year after it was paused."*
- The production checklist restates it as a discretionary right: *"We may pause applications on the Free Plan that
  exhibit low activity in a 7-day period to save on server resources."*
  (<https://supabase.com/docs/guides/platform/going-into-prod>) `[DATA]`

`[INFERENCE]` For a 10–50 person internal CRM used on working days, organic traffic clears the "few requests a
day" bar easily on weekdays. The genuine exposure is **long holiday shutdowns** (Diwali week, year-end) and the
period **before adoption** while only you are using it. A once-daily keep-alive ping is the standard mitigation
and costs nothing (see §8).

`[DATA]` Third-party reporting (simplebackups.com, answeroverflow) states that after 90 days paused the one-click
restore is disabled and you must download a backup and restore into a fresh project. **I could not confirm this
90-day sub-rule from any Supabase page** — the Supabase doc only states the 1-year window. Tagging the 90-day
claim **`[UNVERIFIED]`**. Either way the operational conclusion is the same: do not let it pause for months.

### 1c. Backups on Free — the sharpest deficiency
Verbatim from <https://supabase.com/docs/guides/platform/backups> `[DATA]`:
> *"We automatically back up all Pro, Team, and Enterprise Plan projects on a daily basis"*

and Free-plan users are instead told to *"regularly export their data using the Supabase CLI `db dump` command"* and
*"maintain off-site backups."* Pro gets 7 days of daily backups; PITR is a paid add-on at roughly **$100/mo (7-day)
to $400/mo (28-day)** `[DATA]`.

`[OPINION]` This is the one place where "free" genuinely costs you something real, and it is also the one place
where the fix is genuinely free: a nightly `supabase db dump` pushed to a private GitHub repo *is* your backup, it
*is* off-site, it *is* version-history'd, and it happens to be exactly what the Principal asked for ("keep data on
our GitHub"). See §9 for why GitHub is a good **backup** target and a bad **primary** store.

### 1d. Row Level Security
RLS is a PostgreSQL feature and is available on all plans including Free `[INFERENCE from DATA]`. The production
checklist makes it an explicit instruction rather than an upsell: *"Ensure you have enabled row level security (RLS)
on all tables from the Database > Tables section of the Supabase Dashboard."* `[DATA]`

### 1e. Built-in email rate limit — a hard blocker for OTP login
Verbatim, <https://supabase.com/docs/guides/auth/auth-smtp> `[DATA]`:
> *"Currently this value is set to 2 messages per hour."*
> *"The default SMTP service is provided as best-effort only and intended for the following non-production use
> cases"* — listed as exploring Supabase Auth, testing templates with project team members, and *"Building toy
> projects, demos or any non-mission-critical application."*
> *"No SLA guarantee on message delivery or uptime for the default SMTP service."*

And from the production checklist `[DATA]`: *"As of 3 Sep 2024, this has been updated to 2 emails per hour. You can
only change this with your own custom SMTP setup."*

**Conclusion: custom SMTP is mandatory if Supabase Auth sends your magic links.** 2 emails/hour cannot serve
10 people, let alone 50. This is not a soft recommendation — it is a functional ceiling.

### 1f. DPA and corporate entity
- **Contracting entity: SUPABASE PTE. LTD., a Singapore entity**, 65 Chulia Street #38-02/03, OCBC Centre,
  Singapore 049513. Confirmed identically on both <https://supabase.com/terms> and
  <https://supabase.com/legal/dpa>. `[DATA]`
- **Governing law: California**, *"This Agreement will be governed by the internal substantive laws of the State of
  California"*; arbitration seated in Singapore, London or San Francisco depending on customer location. `[DATA]`
- **A publicly published DPA exists** at <https://supabase.com/legal/dpa>, incorporating **EU SCCs Module Two
  (controller–processor) and Module Three (processor–subprocessor), plus UK and Swiss addenda**; breach
  notification *"without undue delay, and where feasible, within forty-eight (48) hours"*; deletion of all copies
  on expiry of the retention period; and a prohibition on Supabase *"selling Covered Data or otherwise making
  Covered Data available to any third party for monetary or other valuable consideration."* `[DATA]`
- **The DPA text contains no mention of India or the DPDP Act.** `[DATA]`
- **AMBIGUITY, flagged rather than resolved:** the pricing page lists "DPA" among features **not** included on
  Free, while the DPA document itself states no plan restriction. `[UNVERIFIED]` — **what to check:** email
  Supabase support/privacy and ask in writing whether the published DPA applies to a Free-plan customer. Get the
  answer in writing. `[OPINION]` A compliance file that says "our processor's own pricing page says we don't get a
  DPA" is a bad artifact to hand a SEBI inspector; a one-line email reply resolving it is a good one.

`[OPINION]` On DPDP suitability as a Data Processor: Supabase is a Singapore entity running on AWS, offering SCCs
and a 48-hour breach clock, capable of hosting in Mumbai. That is a defensible processor posture. The gap is not
the DPA's substance — it is (a) whether it contractually attaches on the Free plan, and (b) that DPDP requires the
*Data Fiduciary* (Ionic Wealth) to have a processor contract in place, which is a document you must actually hold,
not merely a URL that exists.

---

## 2. CLOUDFLARE — Pages, Workers, D1, KV, Durable Objects

### 2a. Workers Free
Source: <https://developers.cloudflare.com/workers/platform/limits/> and
<https://developers.cloudflare.com/workers/platform/pricing/> (both fetched 2026-08-03) `[DATA]`

| Item | Free | Paid ($5/mo) |
|---|---|---|
| Requests | **100,000 / day** (resets midnight UTC) | No limit |
| **Static-asset requests** | **free and unlimited — do NOT count toward the daily limit** | same |
| CPU time per request | **10 ms** | 5 min (configurable) |
| CPU time per Cron Trigger invocation | **10 ms** | — |
| Subrequests per request | **50** | 10,000 |
| Worker script size | **3 MB gzipped** (64 MB uncompressed) | 10 MB gzipped |
| Workers per account | 100 | 500 |
| Memory per isolate | 128 MB | 128 MB |
| **Cron Triggers per account** | **5** | 250 |
| Cron / DO-alarm / queue-consumer wall duration | 15 min | 15 min |
| Env vars | 64 per Worker, 5 KB each | 128 |

Verbatim on static assets: *"Requests to static assets are free and unlimited."* `[DATA]` — this materially
changes the arithmetic: only your API calls burn the 100k/day, not page loads.

**Cron Triggers ARE available on Free** (5 per account) `[DATA]` — so deadline digests can run natively without
GitHub Actions.

### 2b. Pages Free
Source: <https://developers.cloudflare.com/pages/platform/limits/> `[DATA]`

| Item | Free | Pro |
|---|---|---|
| Builds | **500 / month** | 5,000 |
| Concurrent builds | **1** | 5 |
| Files per deployment | **20,000** | 100,000 |
| Max single asset size | **25 MiB** | same |
| Projects per account | 100 (*"This limit is not routinely increased"*) | same |
| Custom domains per project | 100 | 250 |
| Build timeout | 20 minutes | same |
| Bandwidth | **not stated on the limits page** | — |

`[INFERENCE]` Bandwidth: the Pages limits page states no bandwidth cap, and the Workers pricing page states static
asset requests are "free and unlimited." Treat Pages bandwidth as effectively uncapped for a 50-user internal app.
`[UNVERIFIED]` for an explicit "unlimited bandwidth" sentence — I did not find one on a Cloudflare docs page today.

500 builds/month = ~16/day `[INFERENCE]`. For a solo builder iterating hard, this is the limit you are most likely
to actually brush against in month one. Batch commits; don't push every keystroke.

### 2c. D1 Free
Sources: <https://developers.cloudflare.com/d1/platform/limits/> and `/d1/platform/pricing/` `[DATA]`

| Item | Free | Paid |
|---|---|---|
| Databases per account | **10** | 50,000 |
| Max size per database | **500 MB** | 10 GB |
| Storage per account | **5 GB** | 5 GB included, then $0.75/GB-mo |
| **Rows read / day** | **5 million** | 25 bn/mo included |
| **Rows written / day** | **100,000** | 50 M/mo included |
| Queries per Worker invocation | **50** | 1,000 |
| Time Travel (PITR) | **7 days** | 30 days |
| Max SQL statement | 100 KB | same |
| Max query duration | 30 s | same |
| Max row/string | 2 MB | same |
| Max columns per table | 100 | same |

On exceeding a daily limit: *"the system will not permit further database queries. The D1 API returns error
messages to your application indicating the limits have been surpassed."* `[DATA]` — i.e. **the app goes read-fail,
it does not degrade gracefully.** You must handle this error path explicitly.

**Time Travel 7 days on Free is a genuinely valuable free-tier feature** `[OPINION]` — it is point-in-time restore
by another name, and Supabase Free has no equivalent at all.

### 2d. D1 data location — the India blocker
Source: <https://developers.cloudflare.com/d1/configuration/data-location/> `[DATA]`
Available hints: `wnam` (Western North America), `enam` (Eastern North America), `weur` (Western Europe),
`eeur` (Eastern Europe), `apac` (Asia-Pacific), `oc` (Oceania).
> *"There is no India-specific location hint available."*
> *"Providing a location hint does not guarantee that D1 runs in your preferred location. Instead, it will run in
> the nearest possible location (by latency) to your preference."*

South America, Africa and the Middle East are not supported at all. `[DATA]`

`[INFERENCE]` With `apac`, your D1 primary most likely lands in Singapore or Japan, and you cannot contractually
guarantee even that. If anyone at the firm needs to state in writing where the data physically sits, D1 cannot
support that statement and Supabase-Mumbai can.

### 2e. Workers KV Free
Source: <https://developers.cloudflare.com/kv/platform/limits/> `[DATA]`

| Item | Free | Paid |
|---|---|---|
| Reads | 100,000 / day | unlimited |
| **Writes (different keys)** | **1,000 / day** | unlimited |
| Writes to the *same* key | 1 / second | 1 / second |
| Storage | 1 GB / account, 1 GB / namespace | same per-namespace |
| Namespaces | 1,000 | same |
| Max key / value / metadata | 512 B / 25 MiB / 1,024 B | same |

**1,000 writes/day is the tightest number in the entire Cloudflare free tier.** `[OPINION]` Do not put sessions,
audit events, or status punches in KV. KV is for config and rarely-changing lookup data only.

### 2f. Durable Objects Free
Source: <https://developers.cloudflare.com/durable-objects/platform/pricing/> `[DATA]`
- **Available on Workers Free**, but *"Only Durable Objects with SQLite storage backend are available."*
- 100,000 requests/day; 13,000 GB-s/day; **5 M SQLite rows read/day; 100,000 rows written/day; 5 GB SQL stored.**
- *"if you exceed any single free tier limit, further operations of that type will fail with an error"*; daily
  limits reset 00:00 UTC.

`[OPINION]` Not needed for this app. Mentioned only so it isn't rediscovered later as a "maybe we should have."

### 2g. R2 Free
Source: <https://developers.cloudflare.com/r2/pricing/> `[DATA]`
- **10 GB-month storage**, **1 M Class A ops/month**, **10 M Class B ops/month**.
- Egress: *"Egressing directly from R2, including via the Workers API, S3 API, and r2.dev domains does not incur
  data transfer (egress) charges and is free."*
- **Trap:** *"The free tier exclusively applies to Standard storage; it does not extend to Infrequent Access
  storage."* — do not "optimise" attachments into Infrequent Access; you will start paying.

### 2h. Commercial use on Cloudflare free
The brief treats this as settled; here is what I could and could not confirm as primary text.
- <https://www.cloudflare.com/terms/> (Self-Serve Subscription Agreement): **there is no Section 2.8** in the
  current agreement. The free-services provision is **§2.6 "Free & Trial Services"**, which says only *"We may
  offer free or trial versions of the Services ('Free Services') from time to time."* — **no non-commercial-use
  restriction.** `[DATA]`
- **A real restriction that does exist and is worth knowing:** §2.2.1(h) prohibits customers from
  *"process[ing] or collect[ing] personal or business credit card information on any web property that is
  receiving Free Services."* `[DATA]`
  `[INFERENCE]` A ticketing CRM collects no card data, so this is satisfied — but it permanently rules out ever
  bolting a payment feature onto this same free property.
- <https://www.cloudflare.com/supplemental-terms/> did not render its service-specific sections to fetch.
  `[UNVERIFIED]` for Workers/Pages-specific supplemental terms text. **What to check:** read the Service-Specific
  Terms for the Developer Platform section directly in a browser and save a PDF for the compliance file.
- `[OPINION]` The affirmative "commercial use allowed" phrasing circulating online traces to Cloudflare marketing
  copy and third-party trackers, not to a quotable clause. The defensible statement is the negative one, and it is
  the one that matters: **the agreement imposes no non-commercial limitation on free Workers/Pages.**

### 2i. India data-locality controls
Source: <https://developers.cloudflare.com/data-localization/> and `/data-localization/regional-services/` `[DATA]`
- Data Localization Suite is an *"Enterprise-only paid add-on."*
- *"Regional Services is an Enterprise add-on. Contact your account team to confirm your account has the required
  entitlements."*
- **Not free. Not available at any self-serve price point.** `[DATA]` — expectation in the brief confirmed.
- Whether India is among the supported Regional Services regions: `[UNVERIFIED]` — the docs pages I fetched do not
  publish the region list. Moot anyway, since it is Enterprise-only.

---

## 3. CLOUDFLARE ZERO TRUST / ACCESS (FREE)

### 3a. Seat count
- Cloudflare's own Access product page (<https://www.cloudflare.com/sase/products/access/>):
  *"Best for teams under 50 users or enterprise proof-of-concept tests."* `[DATA]`
- Seat management doc (<https://developers.cloudflare.com/cloudflare-one/identity/users/seat-management/>) `[DATA]`:
  - On exceeding the limit: *"additional users who attempt to log in are blocked."*
  - *"A user consumes a seat when they perform an authentication event."* For Access this is any Access
    authentication event, including an App Launcher login.
  - *"The user will occupy and consume a single seat regardless of the number of applications accessed or login
    events from their user account."*
  - *"you can remove a single user or all users at any time, and those users will immediately stop counting against
    the seat count"* — **no cooldown**, unlike some competitors.
  - Seat-expiration policies can auto-release inactive users, configurable between one month and one year.
- Third-party pricing trackers (costbench, zerotrustcost, controld, Cloudflare Community threads) consistently
  state **50 free seats**, full ZTNA + secure web gateway, 24-hour log retention, and **$7/user/month** for the
  next tier up. `[DATA — third-party, lower confidence]`
- **`[UNVERIFIED]` on the exact primary-source number.** The Access page's own comparison table did not render a
  clean "Users" cell to fetch, and one render suggested "No user limit" for Free, which contradicts everything
  else. **What to check:** open the Zero Trust dashboard billing page after signup; it shows current seats vs
  entitlement. Do this before onboarding user #40.

`[OPINION]` **This is the biggest single risk in the recommended stack.** The firm is described as 10–50 employees.
The free ceiling is ~50. At 10–30 users this is comfortable; at 45+ you are one hiring round from users being
*silently blocked at login* — and the failure mode is "the new joiner can't log in," which will land on you, not
on IT. Two mitigations: (1) enable seat-expiration at 1–2 months so leavers auto-release; (2) allow-list only
people who actually need the tool, not the whole company.

### 3b. Email one-time PIN with no IdP — confirmed
Source: <https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/> `[DATA]`
> *"Cloudflare Access can send a one-time PIN (OTP) to approved email addresses as an alternative to integrating an
> identity provider."*
- User enters their email and selects **Send login code**; if the address is permitted by an Access policy, the
  code arrives by email.
- *"This secure PIN expires 10 minutes after the initial request."*
- Single-use: *"Requesting a new PIN invalidates the previous PIN."*
- *"OTP is no longer added automatically, but you can set it up at any time"* — **it is not on by default; you must
  enable it.**

`[INFERENCE]` This is exactly the login model already decided (email OTP to an allow-listed company
address, no passwords stored), delivered by the platform, at zero cost, with **Cloudflare sending the mail** — so
no Brevo/Resend in the auth path, no DNS records on `ionic.in`, and no OTP-generation/expiry/replay code for you to
write and get wrong.

### 3c. Can it gate a Pages app? And a self-hosted origin via Tunnel?
- **Preview deployments:** built into Pages project settings — *"In your project's settings, you can require
  visitors to authenticate to view preview deployment."* `[DATA]`
- **But by default that is preview-only:** *"Note that this will only protect your preview deployments ... and not
  your `*.pages.dev` domain or custom domain."* `[DATA]`
  (<https://developers.cloudflare.com/pages/configuration/preview-deployments/>)
- **`*.pages.dev` CAN be protected**, per <https://developers.cloudflare.com/pages/platform/known-issues/> `[DATA]`:
  in the auto-created Access application's Public hostname → Subdomain field, *"delete the wildcard (`*`) and select
  **Save**."*
- **Custom domains** need their own Access application: Zero Trust → Access controls → Applications → new
  **Self-hosted and private** app → *"Select **Add public hostname** and select your custom domain from the
  _Domain_ dropdown menu."* With the warning: *"If you do not configure an Access policy for your custom domain, an
  Access authentication will render but not work for your custom domain visitors."* `[DATA]`

**`[INFERENCE]` — decisive consequence: you can ship a fully access-gated app on a `*.pages.dev` hostname without
ever touching `ionic.in` DNS.** That defuses the "platform not known / no tenant admin / may not control DNS"
constraint completely. Note the docs file this under *Known Issues*, so treat it as supported-but-fiddly and
**test it end-to-end before onboarding anyone** — including from a non-allow-listed address, to confirm denial.

### 3d. Cloudflare Tunnel — free and unlimited?
`[UNVERIFIED]`. The Tunnel doc page (<https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/>)
contains **no pricing, plan, tunnel-count or bandwidth statements at all.** I will not assert "free and unlimited"
without a page saying so. **What to check:** the Zero Trust plan comparison table's networking row, or create a
tunnel on a free account and observe. `[OPINION]` Tunnel is not needed for the recommended stack (Pages is already
on Cloudflare's edge); it only matters for the maximum-data-control alternative in §11.

### 3e. Credit-card gotcha
Source: <https://developers.cloudflare.com/cloudflare-one/setup/> `[DATA]`
> *"If you chose the **Zero Trust Free plan**, this step is still needed but you will not be charged."*

**Payment details are requested during Zero Trust onboarding even on the Free plan.** `[DATA]`
`[OPINION]` This collides with the brief's "no credit-card-required-then-charged services" rule. It is a
card-on-file-with-no-charge, not a trial-that-converts — Cloudflare states plainly you will not be charged, and
overage behaviour is *blocking*, not billing. But it is a real friction point and the Principal should be told
before signup, not after, because it may require using a personal card for a company tool — which is its own small
governance problem worth raising.

---

## 4. ORACLE CLOUD ALWAYS FREE

Source: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm> and
<https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm> (both fetched 2026-08-03) `[DATA]`

| Resource | Always Free allowance |
|---|---|
| ARM Ampere A1 (VM.Standard.A1.Flex) | **2 OCPUs + 12 GB RAM total**; 1,500 OCPU-hours + 9,000 GB-hours/month |
| AMD micro (VM.Standard.E2.1.Micro) | **2 instances**, 1/8 OCPU burstable, 1 GB RAM each |
| Block volume | **200 GB total** (boot + block); boot default 50 GB; 5 volume backups |
| Object storage | 20 GB combined (Always-Free-only account); 50,000 API requests/month |
| Autonomous Database | 2 instances, 20 GB each, 1 OCPU, max 20 sessions |
| Load balancer | Flexible LB, 10 Mbps min/max; 16 listeners, 16 backend sets |
| **Outbound data transfer** | **10 TB / month** |

### 4a. The idle-reclaim trap — verbatim
> *"Idle Always Free compute instances may be reclaimed by Oracle. Oracle will deem virtual machine and bare metal
> compute instances as idle if, during a 7-day period, the following are true:*
> - *CPU utilization for the 95th percentile is less than 20%*
> - *Network utilization is less than 20%*
> - *Memory utilization is less than 20% (applies to A1 shapes only)"* `[DATA]`

All three thresholds must be met across a 7-day window. `[DATA]`

`[INFERENCE]` **A 50-user internal ticketing app will trivially sit under 20% CPU on 2 OCPUs, under 20% network,
and under 20% of 12 GB RAM — all three, continuously.** This app is close to a worst-case fit for the reclaim
heuristic. It is *not* like Supabase's pause (reversible, data intact, one click); reclamation takes the instance.
The community workaround is to burn artificial CPU to stay above 20%, which is both absurd and arguably
against the spirit of the terms.

### 4b. Region availability for Always Free
> *"You must create the Always Free compute instances in your home region."* `[DATA]`
> *"During sign-up, choose the home region carefully. You can provision Always Free Autonomous AI Databases and
> compute instances only in the home region."* `[DATA]`
> *"The Free Tier and Always Free resources are not available in US Government Cloud regions."* `[DATA]`
- A1 shapes: any availability domain except South Korea North (Chuncheon). E2.1.Micro: one AD in the home region.

`[INFERENCE]` Mumbai and Hyderabad are commercial OCI regions, so selecting either as your **home region** at
signup should yield Always Free resources there. **`[UNVERIFIED]`** for (a) an Oracle page explicitly naming
Mumbai/Hyderabad as Always-Free-eligible, and (b) **A1 capacity availability** — "Out of host capacity" errors when
launching Always Free A1 in Indian regions are widely reported but I have no primary source and did not verify.
**What to check:** attempt an A1 launch in Mumbai and see.

### 4c. Credit card and auto-conversion
> *"For security purposes, most users need a mobile phone number and a credit card to create an account. Your credit
> card will not be charged unless you upgrade your account."* `[DATA]`
> *"After your trial ends, your account remains active. There is no interruption to the availability of the Always
> Free Resources you have provisioned."* `[DATA]`
> *"Paid resources that were provisioned with your credits during your free trial are reclaimed by Oracle unless you
> upgrade your account."* `[DATA]`
> *"If you have more OCI Ampere A1 Compute instances provisioned than are available for an Always Free tenancy, all
> existing OCI Ampere A1 Compute instances are disabled and then deleted after 30 days, unless you upgrade to a paid
> account."* `[DATA]`

**Good news: it does NOT auto-convert to paid.** The trial degrades to Always Free. `[DATA]` The real danger is the
opposite direction: over-provisioning during the $300 trial and having those resources **disabled then deleted**
when the trial ends.

India sign-up reliability: `[UNVERIFIED]` — no primary source found. Do not repeat anecdotes as fact.

### 4d. VERDICT — is it safe to run a company-internal tool on it?
**`[OPINION]` No. Do not use Oracle Always Free for this.** Three independent reasons, each sufficient:
1. The idle-reclaim heuristic is a near-perfect description of this app's load profile, and the penalty is
   destruction of the instance rather than a reversible pause.
2. You would own the entire stack — OS patching, Postgres, TLS, backups, firewall, upgrades — on a work laptop with
   no admin rights and a corporate proxy, as an Assistant Portfolio Manager, not as IT. An unpatched
   internet-facing VM holding employee data is a *worse* compliance posture than a managed processor with a DPA,
   not a better one. Self-hosting reads as "more control" and functions as "more unmanaged risk."
3. Card-on-file plus a trial-to-Always-Free transition with silent 30-day deletion of over-provisioned resources
   is exactly the class of hazard the zero-budget constraint is meant to avoid.

`[OPINION]` The only scenario where Oracle earns a look is if a legal requirement forces India-resident,
firm-controlled infrastructure. Even then, Oracle Always Free is the wrong instrument — that requirement implies a
budget conversation, not a free VM.

---

## 5. ALTERNATIVE FREE POSTGRES / SQLITE

### 5a. Neon — <https://neon.com/pricing> and `/docs/introduction/regions` `[DATA]`
| Item | Free plan |
|---|---|
| Storage | **0.5 GB per project** |
| Compute | **100 CU-hours per project**; autoscale up to 2 CU (8 GB RAM) |
| Scale to zero | **after 5 min** |
| Egress | **5 GB per project** |
| Projects / branches | 100 projects; 10 branches per project |
| PITR / history retention | **6 hours** (1 GB limit) |

- **Hard stop, verbatim:** *"Hitting any Free monthly limit (100 CU-hours, 0.5 GB storage, 5 GB egress) suspends
  compute until the next billing month."* `[DATA]` — not throttling. **Suspension until the next month.**
- **No India region.** Available: `aws-us-east-1`, `us-east-2`, `us-west-2`, `eu-central-1`, `eu-west-2`,
  `ap-southeast-1` (Singapore), `ap-southeast-2` (Sydney), `sa-east-1`. Azure regions deprecated to new projects.
  `[DATA]`
- *"Projects on the Free plan that have been inactive for 90 days or more are subject to deletion as of
  October 5, 2026."* `[DATA]` — **deletion, not pause.** Note the date: this is a *newly announced* policy, live in
  two months. Anyone relying on remembered Neon behaviour is now wrong.

`[OPINION]` 100 CU-hours/month is the killer. A shared internal app kept warm to avoid cold starts will consume
compute hours continuously; the moment it trips, the database is **down until the calendar flips**. That is an
unacceptable failure mode for a work-tracking tool, and it is strictly worse than Supabase's pause (which is
one-click reversible and does not wait for a billing cycle). Nearest Neon region is Singapore. **Not recommended.**

### 5b. Turso — <https://turso.tech/pricing> `[DATA]`
| Item | Free plan |
|---|---|
| Databases | **100** |
| Storage | **5 GB** |
| Rows read | **500 million / month** |
| Rows written | **10 million / month** |
| Syncs | 3 GB / month |
| PITR | 1 day |
| Next tier | Developer, **$4.99/month** |

- 2025 changes `[DATA — turso.tech blog via search, lower confidence]`: cold starts removed for the Free tier as of
  **31 Mar 2025**; **databases archived after 10 days of inactivity** on Free; edge replicas discontinued for new
  users; new Developer plan at $4.99 with 2.5 bn rows read/month.
- **Mumbai:** `bom` / `aws-ap-south-1` "AWS AP South (Mumbai)" is reported available. `[UNVERIFIED]` — the
  locations doc 404'd at both paths I tried. **What to check:** `curl https://api.turso.tech/v1/locations` with a
  bearer token, which is the authoritative list per Turso's own API reference.

`[OPINION]` Turso's row allowances are **far** more generous than D1's (500 M/month read vs D1's 5 M/day ≈ 150
M/month; 10 M/month written vs D1's 100 k/day ≈ 3 M/month) and it plausibly has Mumbai. It is the strongest
*technical* free SQLite option. Against it: smaller company, more plan churn in the last 18 months than any other
vendor here, and 10-day archiving. Worth keeping as the documented fallback if D1's write ceiling ever bites.

### 5c. Ruled out
| Service | Status | Source `[DATA]` |
|---|---|---|
| **Fly.io** | **No free tier for new orgs.** *"All organizations (except for Linked Organizations) require a credit card on file."* Legacy free allowances honoured only for pre-sunset plans (3× shared-cpu-1x 256 MB, 3 GB volumes). Launch/Scale plans purchased before **7 Oct 2024** grandfathered. | fly.io/docs/about/pricing |
| **Render** | Free web service *"spins down ... after 15 minutes without receiving any inbound traffic"*, ~1 min cold start, 750 instance-hours/month. **Free Postgres is fatal:** *"Free Render Postgres databases expire 30 days after creation"*, deleted after a 14-day grace period; no backups on free. | render.com/docs/free |
| **Railway** | **No free tier.** Trial = *"free one-time grant of $5"*; Hobby = **$5/month**. Post-paid card required. | docs.railway.com/reference/pricing/plans |
| **Xata** | **No free-forever cloud tier.** Now a Postgres branching platform: *"a 14-day free trial"*, then *"Add a credit card ... to keep using Xata on Pay As You Go."* Free option = self-host the open source. | xata.io/pricing |

**India region on FREE, across all candidates:** Supabase `ap-south-1` **yes** (documented, no plan gate stated);
Turso Mumbai **probable but unverified**; Cloudflare D1 **no India hint at all**; Neon **no India region**;
Fly/Render/Railway/Xata **no free tier to speak of**.

---

## 6. FREE TRANSACTIONAL EMAIL

The decisive question for this project is not volume — it is **"can I send without touching `ionic.in` DNS?"**

| Service | Free allowance | DNS required to send? | Card? | Verdict |
|---|---|---|---|---|
| **Brevo** | **300 emails/day**; up to 100,000 contacts; transactional email + REST API + SMTP + outbound webhooks all on Free | **NO** — single-sender verification by emailed 6-digit code | No | **Best fit** |
| **Resend** | **3,000/month AND 100/day**; 1 domain; 30-day data retention | **YES** — *"You must add and verify at least one domain to send and receive emails with Resend"* | No | Blocked if no DNS |
| **MailerSend** | **500 emails/month**; 1 domain; API + SMTP; 1 template | not stated | **YES, card required on Free** | Too small + card |
| **Amazon SES** | **No perpetual free tier.** *"up to $200 in AWS Free Tier credits"*, 6 months to use, expiring within 12 months | yes | yes | **Out** |
| **Zoho ZeptoMail** | **No free-forever.** 1 credit = 10,000 emails; *"first credit is on us ... valid for 1 month"* | yes | yes | **Out** |

### 6a. Brevo — why it wins, with the exact mechanism
- Free plan: **"300 daily email sends"**, and *"Unused email sends don't carry over to the next day"*; up to
  **100,000 contacts**; transactional emails, API, SMTP and outbound webhooks included on Free (inbound webhooks
  are Professional-tier).
  Source: <https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans> `[DATA]`
  (Brevo's `/pricing/` page would not render to fetch; I used their own help centre instead.)
- **No-DNS sender verification, verbatim** from
  <https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email> `[DATA]`:
  > *"If your sender domain is not authenticated, you'll be prompted to verify it by entering the 6-digit code sent
  > to the sender address"*
  You paste the code, click **Verify sender**, done. Domain authentication is framed as advice, not a gate:
  *"We recommend authenticating your domain before creating a sender."*
- `[DATA]` Third-party: the 300/day is shared across marketing and transactional sends; 1,000 requests/second API
  rate limit.

### 6b. Deliverability risk of an unverified sender — say this plainly
`[DATA]` Brevo warns: *"A warning icon will appear next to the DKIM signature and/or DMARC status of your sender if:
Your sender domain has not been authenticated, or You are using a free sender domain."*
`[DATA]` Since **1 Feb 2024** Gmail and Yahoo require bulk-sender authentication, and Microsoft announced
equivalent standards on **5 May 2025**.

`[INFERENCE]` Mail sent as `something@ionic.in` through Brevo **without** SPF/DKIM records on `ionic.in` will fail
DMARC alignment. If `ionic.in` publishes `p=reject` or `p=quarantine`, those mails will be **rejected or
junked — including by the firm's own Microsoft 365/Google tenant**, which is precisely where all 50 recipients are.
This is the most likely silent failure in the entire build: it will look like "the app doesn't send emails."

**Two clean ways out, both free:**
1. **`[OPINION]` Preferred: use Cloudflare Access OTP for login, so no login email is ever sent by you.** Cloudflare
   sends the PIN from its own authenticated infrastructure. Brevo then only carries *deadline digests* — nice-to-have
   mail whose failure is survivable and diagnosable, not the thing standing between staff and the app.
2. Send digests from a Brevo-verified address you actually control (or a subdomain like
   `crm-notify.ionic.in` if DNS access ever materialises), and **never** spoof the corporate domain unaligned.

**Which can reliably send OTPs to ~50 users with no DNS changes?** Strictly on the "no DNS" test: **Brevo only.**
But the better answer is **don't put email in the login path at all** — §3b.

---

## 7. FREE FILE STORAGE FOR TICKET ATTACHMENTS

| Service | Free storage | Free ops | Egress | Traps |
|---|---|---|---|---|
| **Cloudflare R2** | **10 GB-month** | 1 M Class A + 10 M Class B / month | **Free, always** — *"does not incur data transfer (egress) charges and is free"* | Free tier is **Standard class only**, not Infrequent Access |
| **Supabase Storage** | **1 GB**, max upload **50 MB** | — | shares the project's **5 GB/month** egress | Tiny; competes with your DB for the same egress budget |
| **Backblaze B2** | **first 10 GB** free | Class A free; Class B & C free for first **2,500/day each** | free up to **3× average monthly storage**, then $0.01/GB | The 3× multiplier means a small bucket earns a small egress allowance |

`[DATA]` R2 and Supabase figures are from the vendors' own docs pages. **Backblaze:** `backblaze.com/cloud-storage/pricing`
returned **HTTP 403** to direct fetch; figures above are from Backblaze's own pricing and transaction-pricing pages
as surfaced in search, plus third-party trackers. Tag as `[DATA — indirect]`; **re-verify in a browser** before
relying on the 2,500/day transaction figure. Storage beyond 10 GB is $0.005/GB-month ($6/TB-month).

`[OPINION]` **R2.** 10× Supabase's storage, egress unconditionally free with no multiplier arithmetic, same account
and same `wrangler` toolchain as the rest of the recommended stack, and no third vendor to add to the compliance
register. Backblaze's "3× average monthly storage" egress rule is the trap to name explicitly: a 2 GB bucket earns
only ~6 GB/month of free downloads, and a handful of colleagues re-downloading attachments can exceed it.

---

## 8. FREE UPTIME / ERROR MONITORING AND FREE CRON

| Service | Free tier | Source `[DATA]` |
|---|---|---|
| **Cloudflare Cron Triggers** | **5 per account**; **10 ms CPU per invocation**; 15 min wall duration | workers/platform/limits |
| **cron-job.org** | *"Jobs can be executed with frequencies up to once per minute"*; *"absolutely free and financed entirely by voluntary donations"*; no card | cron-job.org |
| **GitHub Actions** | **2,000 min/month** + 500 MB Packages (Free, personal **and** org); public repos don't consume minutes, **private repos do** | docs.github.com billing |
| **UptimeRobot** | **50 monitors**, **5-min interval**, HTTP/port/ping/keyword/API/UDP/DNS/SSL+domain-expiry, email alerts, **1** basic status page, **3 months** log retention, only 5 integrations, no notify/login seats | uptimerobot.com/pricing |
| **Sentry Developer** | **5 k errors**, 5 M spans, 50 replays, **1** cron monitor, **1** uptime monitor, **ONE user**, **30-day** retention, unlimited projects, 10 dashboards | sentry.io/pricing |

### 8a. GitHub Actions `schedule` reliability — and a correction to the brief's assumption
Verbatim from
<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows> `[DATA]`:
> *"The `schedule` event can be delayed during periods of high loads of GitHub Actions workflow runs. High load
> times include the start of every hour."*
> *"The shortest interval you can run scheduled workflows is once every 5 minutes."*
> *"In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred
> in 60 days."*

**Correction worth flagging:** the 60-day auto-disable is stated for **public repositories only.** `[DATA]` This
project's repo will be **private**, so on the current wording that clause does not apply to it. The brief's premise
("disabled after repo inactivity") is true for public repos and **not established for private ones**.
`[UNVERIFIED]` whether any equivalent private-repo rule exists — I found none. **What to check:** GitHub's
"Disabling and enabling a workflow" page for any private-repo inactivity clause.

`[OPINION]` The delay warning, though, is real and remains disqualifying for a *keep-alive* job: "delayed during
high load, especially at the start of every hour" plus a 5-minute floor is fine for a nightly digest and wrong for
anything you depend on firing punctually.

### 8b. Sentry's real constraint
`[OPINION]` 5,000 errors/month is generous for a 50-user internal app; **"ONE user"** is the actual limit. Only
you can log in. Fine for a solo builder; it means Sentry cannot be the shared operational dashboard if a
colleague ever co-maintains this. Note it now so it isn't a surprise at handover — and note that a single-user
error tool is a **bus-factor-of-one** in an app the firm will come to depend on.

---

## 9. "CAN WE KEEP THE DATA ONLY ON OUR GITHUB?" — direct answer

Source: <https://docs.github.com/en/get-started/learning-about-github/githubs-plans> `[DATA]`
- GitHub Free: **unlimited private repositories**, **unlimited collaborators**, 2,000 Actions min/month, 500 MB
  Packages storage.
- **No branch protection and no required reviewers on private repos on Free** — those need Pro (personal) or Team
  (organisation).
- **Audit log is GitHub Enterprise Cloud only.** SAML is Enterprise only.

`[OPINION]` **GitHub is an excellent backup and audit-evidence target and a bad primary datastore.** Concretely:
- A Git repo has no concurrency control, no row locking, and no query engine. Two people punching a status update
  at the same moment produce a merge conflict, not two rows. This breaks the core append-only-status-log feature.
- Every write needs a commit + push, which is slow, and the corporate proxy makes it slower.
- Git history is **immutable and total**: one accidental commit containing a client name is permanently in the
  history of every clone forever. For a firm whose entire design intent is "opaque `client_ref` only, never PII,"
  a store that cannot forget is the wrong shape.
- **The Free-plan gaps above undercut the compliance story specifically:** you cannot enforce branch protection or
  required reviewers on a private repo, and you get no audit log. So "the data is safe because it's in our GitHub"
  is weaker than it sounds — on Free, a single compromised token can rewrite history with no audit trail.

**What GitHub *should* do here, and does superbly:** hold the code, drive deploys (push-to-deploy, which suits the
no-admin-rights/proxy environment), and receive a **nightly encrypted logical dump** of the database into a private
repo. That gives off-site, version-histories, firm-controlled backups — filling the single worst gap in the
Supabase Free tier (§1c) — while a real database keeps serving concurrent writes.

---

## 10. MASTER COMPARISON TABLE

Verdict column is `[OPINION]`; all numbers `[DATA]` as sourced above, on 2026-08-03.

| Layer | Candidate | Key free numbers | India region? | Fatal flaw / verdict |
|---|---|---|---|---|
| Static + API host | **Cloudflare Pages + Workers** | 100 k req/day (static assets unlimited & uncounted); 500 builds/mo; 1 concurrent build; 10 ms CPU; 5 cron triggers | edge is global; no data residency control | **USE.** 10 ms CPU is the real design constraint |
| | Vercel Hobby | — | — | **Excluded by ToS** (settled by the firm) |
| DB | **Supabase Postgres Free** | 500 MB DB; 5 GB egress; 50 k MAU; 2 projects; pause after 1 wk; **no backups**; 1-day logs | **YES — ap-south-1 documented, no plan gate stated** | **USE** if data residency matters. No backups → nightly dump to GitHub is mandatory, not optional |
| | **Cloudflare D1** | 500 MB/DB; 5 GB/acct; **5 M rows read/day, 100 k written/day**; 7-day Time Travel | **NO India hint; location not guaranteed** | Strong 2nd. Time Travel beats Supabase Free. Kills the India story |
| | Turso | 5 GB; 500 M rows read/mo; 10 M written/mo; archived after 10 days idle | Mumbai **probable, unverified** | Viable fallback; most plan churn of any vendor here |
| | Neon | **0.5 GB**; 100 CU-h/mo; **limit → compute suspended till next month**; 90-day idle deletion from 5 Oct 2026 | **NO** (nearest Singapore) | **Reject.** Month-long outage as a failure mode |
| | Render PG / Railway / Xata / Fly | Render free PG **expires 30 days after creation**; Railway $5/mo; Xata 14-day trial; Fly card required | — | **Reject all** |
| Auth | **Cloudflare Access + One-time PIN** | **~50 seats**; OTP with **no IdP**; PIN valid 10 min, single-use | n/a | **USE.** Seat cap ≈ headcount ceiling; card-on-file at onboarding |
| | Supabase Auth magic link | 50 k MAU, but **2 emails/hour** on built-in SMTP | — | Needs custom SMTP to function at all |
| Email | **Brevo** | **300/day**; 100 k contacts; API+SMTP on free; **6-digit sender verification, no DNS** | — | **USE for digests only.** DMARC alignment risk if spoofing `ionic.in` |
| | Resend | 3,000/mo **and** 100/day; 1 domain | — | **Domain DNS verification mandatory** → blocked without DNS |
| | MailerSend / SES / ZeptoMail | 500/mo + card / credits only / 1-month trial credit | — | **Reject all** |
| Files | **Cloudflare R2** | **10 GB**; 1 M Class A + 10 M Class B/mo; **egress free** | — | **USE.** Standard class only |
| | Supabase Storage | 1 GB; 50 MB max upload; shares 5 GB egress | yes | Too small |
| | Backblaze B2 | 10 GB; egress free to **3× avg storage** | — | 3× multiplier trap |
| Cron | **Cloudflare Cron Triggers** | 5/account; 10 ms CPU; 15 min wall | — | **USE** for digests |
| | cron-job.org | down to 1-minute frequency; donation-funded | — | **USE** for the Supabase keep-alive ping |
| | GitHub Actions schedule | 2,000 min/mo; 5-min floor; **delayed at high load** | — | Nightly dump only; never for keep-alive |
| Monitoring | **UptimeRobot** | 50 monitors; 5-min checks; email alerts; 3-mo logs | — | **USE** |
| | Sentry Developer | 5 k errors; 30-day retention; **ONE user** | — | **USE**, accept single-seat |
| Code + backup | **GitHub Free (private)** | unlimited private repos + collaborators; 2,000 Actions min | — | **USE for code + dumps, never as the DB.** No branch protection / audit log on Free |

### 10a. Does the free tier actually fit 50 users? `[INFERENCE]`
- **Workers requests:** 50 users × ~40 API calls/working day ≈ **2,000/day against 100,000** — ~2% used, and page
  loads don't count at all. Enormous headroom.
- **D1 rows written** (if D1): a status punch writing ~4 rows → ~25,000 punches/day of headroom. Fine.
- **D1 rows read:** 5 M/day sounds huge and is the one you can actually blow. An unindexed manager dashboard doing
  a full scan of a 50,000-row status table, refreshed 100×/day, is exactly 5 M. **Index and paginate from day one.**
- **KV writes: 1,000/day.** Never route sessions or audit events here.
- **Workers CPU: 10 ms.** The binding constraint on the dashboard. Aggregate in SQL, return narrow paginated JSON;
  do not pull rows into JS and reduce them there.
- **Brevo: 300/day.** One digest per user per day = 50. Comfortable.
- **Supabase 500 MB / 5 GB egress.** Text tickets are tiny; attachments go to R2, so neither binds.

**Conclusion: capacity is not the risk.** The risks are the **~50 Access seats**, the **absence of Supabase Free
backups**, and the **10 ms CPU** ceiling.

---

## 11. RECOMMENDED STACK

### PRIMARY RECOMMENDATION — "Cloudflare front, Mumbai data" `[OPINION]`

| Layer | Choice | Why |
|---|---|---|
| Repo + CI | GitHub Free, **private** repo | Push-to-deploy suits no-admin-rights + proxy; unlimited private repos |
| Frontend + API | **Cloudflare Pages + Pages Functions/Workers** | Free, commercial use unrestricted by the agreement, static assets unlimited and uncounted |
| **Auth** | **Cloudflare Access, One-time PIN, allow-list of company addresses** | Email OTP with **no IdP, no SSO tenant, no DNS, no passwords, no OTP code to write.** Gate `*.pages.dev` so no `ionic.in` DNS is needed |
| Database | **Supabase Postgres Free, `ap-south-1` (Mumbai)**, RLS on every table | Only candidate with a documented India region on Free; RLS gives per-row authorisation |
| Attachments | **Cloudflare R2** (10 GB, free egress) | 10× Supabase Storage, no egress arithmetic |
| Backups | **Nightly `supabase db dump` → GitHub Actions → private repo** (encrypted) | Fills the single worst Free-tier gap; delivers the Principal's "data on our GitHub" ask in the form where it actually works |
| Keep-alive | **cron-job.org** daily ping to a trivial read endpoint | Defeats the 1-week pause during holiday shutdowns |
| Digests | **Cloudflare Cron Trigger → Brevo API** (300/day) | Cron on free; Brevo needs no DNS |
| Uptime | UptimeRobot (5-min HTTP monitor, email alert) | 50 monitors free |
| Errors | Sentry Developer | 5 k errors/mo; accept single seat |

**Why this shape:** it puts **authentication** — the part where a hand-rolled mistake is unrecoverable and the part
this builder is least equipped to own — entirely on Cloudflare's platform, and puts **personal data** in Mumbai
under a processor that publishes a DPA with SCCs. Every component is free-forever with no trial clock. Total
recurring cost: ₹0.

**The three things to verify before writing application code** (each is load-bearing; each is quick):
1. That a **Free** Supabase project can select `ap-south-1`. (§1a)
2. That **Access OTP actually gates the `*.pages.dev` production hostname** end-to-end — including that a
   non-allow-listed address is *denied*. (§3c)
3. Your **current Access seat entitlement** in the Zero Trust billing page, against planned headcount. (§3a)

If (1) fails, the India story collapses and D1 becomes as good a choice as Supabase — at which point prefer D1 for
its 7-day Time Travel and one-vendor simplicity. If (2) fails, you need one DNS record on a domain you control.

### ALTERNATIVE — "maximum data control" `[OPINION]`

Interpreting "maximum data control" as *fewest third parties holding firm data, and the firm able to state exactly
where each byte lives*:

| Layer | Choice |
|---|---|
| Frontend + API | Cloudflare Pages + Workers (unchanged) |
| Auth | Cloudflare Access + One-time PIN (unchanged) |
| **Database** | **Cloudflare D1** (`apac` hint) — data stays inside the *same* vendor as the app |
| Attachments | Cloudflare R2 — same vendor again |
| Backups | Nightly `wrangler d1 export` → private GitHub repo, **plus** D1's built-in 7-day Time Travel |
| Everything else | As primary |

**What you gain:** exactly **two** processors (Cloudflare + GitHub) instead of four; one legal agreement to file
instead of three; no Brevo in the login path *or* the data path; and D1's **7-day Time Travel**, a real
point-in-time restore that Supabase Free simply does not offer.

**What you give up, and it is the crux:** **you can no longer say the data is in India.** D1 has no India location
hint and no location guarantee. `[DATA]`

`[OPINION]` So the two options trade *residency* against *vendor minimisation*, and the tie-break is a legal
question I have deliberately not answered: **does any SEBI requirement applicable to Ionic Wealth compel
India-resident storage?** DPDP s.16 does **not** (§0). If SEBI's cyber framework does, the primary recommendation
is mandatory. If it does not, the maximum-data-control variant is the cleaner build and the easier compliance file.
Route this to the compliance dimension before choosing.

**Explicitly rejected as the "maximum control" answer: self-hosting on Oracle Always Free.** It reads as maximum
control and delivers maximum unmanaged risk — see §4d. An unpatched internet-facing VM administered part-time by a
portfolio manager, subject to a documented reclaim policy this app's load profile satisfies almost perfectly, is a
worse custodian of employee data than a managed processor with a DPA.

---

## 12. WHAT I COULD NOT VERIFY — consolidated

| # | Claim | Status | What would settle it |
|---|---|---|---|
| 1 | Free-plan Supabase projects may select `ap-south-1` | Docs list it, no plan gate stated; UI unconfirmed | Create a throwaway free project, read the region dropdown |
| 2 | Supabase 90-day paused-project restore cliff | `[UNVERIFIED]` — third-party only; Supabase doc says 1 year | Supabase support in writing |
| 3 | Whether the published Supabase DPA attaches on Free | **Contradiction** between pricing page and DPA text | Email Supabase privacy/support; keep the reply |
| 4 | Exact Zero Trust free seat count | 50 per Cloudflare marketing + trackers; plan table cell unreadable, one render said "no user limit" | Zero Trust dashboard billing page post-signup |
| 5 | Cloudflare Tunnel free-tier limits | `[UNVERIFIED]` — Tunnel doc has no pricing text at all | Zero Trust plan comparison networking row |
| 6 | Cloudflare Workers/Pages **supplemental** service-specific terms | Page wouldn't render | Read Service-Specific Terms in a browser; save PDF for the compliance file |
| 7 | Cloudflare Pages explicit "unlimited bandwidth" statement | Inferred from "static assets free and unlimited"; no direct sentence found | Cloudflare Pages pricing/FAQ page |
| 8 | Always Free eligibility + **A1 capacity** in Mumbai/Hyderabad | Home-region rule confirmed; India naming and capacity unverified | Attempt an A1 launch with Mumbai as home region |
| 9 | Turso Mumbai (`aws-ap-south-1`) availability | `[UNVERIFIED]` — locations doc 404'd | `curl https://api.turso.tech/v1/locations` |
| 10 | Backblaze B2 free figures | `[DATA — indirect]`; pricing page returned 403 | Open pricing page in a browser |
| 11 | Any **private**-repo equivalent of the 60-day scheduled-workflow auto-disable | None found; docs say "In a public repository" | GitHub "Disabling and enabling a workflow" docs |
| 12 | cron-job.org job-count and timeout limits | Not stated on the homepage | cron-job.org docs/ToS |
| 13 | Whether SEBI rules compel India-resident storage for this firm | **Out of my dimension — not researched** | Compliance dimension; SEBI CSCRF text |

---

## 13. GOTCHAS, RANKED BY HOW BADLY THEY BITE

1. **Supabase built-in SMTP = 2 emails/hour.** `[DATA]` Anyone who builds magic-link login on Supabase Auth without
   custom SMTP ships something that works for exactly two people per hour. Sidestep it entirely with Access OTP.
2. **Cloudflare Access ~50 free seats, and overage means users are *blocked at login*.** `[DATA]` The firm is 10–50
   people. Enable seat expiry (1–2 months) so leavers auto-release; allow-list only actual users.
3. **Supabase Free has zero backups.** `[DATA]` Not "shorter retention" — *none*. Without the nightly dump, one bad
   migration is total, unrecoverable data loss.
4. **Neon suspends compute until the next billing month** on any free-limit breach. `[DATA]` Month-long outage.
5. **Render's free Postgres expires 30 days after creation.** `[DATA]` A tutorial-grade trap.
6. **Oracle Always Free idle-reclaim: <20% CPU + <20% network + <20% memory over 7 days.** `[DATA]` This app meets
   all three continuously; the penalty is losing the instance.
7. **Workers Free CPU = 10 ms per request.** `[DATA]` Aggregate in SQL, paginate, never reduce large result sets in
   JS.
8. **D1 free daily limits fail hard**, returning errors rather than throttling `[DATA]`; and **5 M rows read/day is
   reachable** by one unindexed dashboard query on a refresh loop.
9. **KV = 1,000 writes/day.** `[DATA]` Tightest number in the stack. Config only.
10. **Sending as `@ionic.in` through Brevo without SPF/DKIM will fail DMARC** and can be junked by the firm's own
    tenant. `[INFERENCE from DATA]` The failure looks like "the app doesn't send email."
11. **Cloudflare Zero Trust asks for payment details even on Free** — *"this step is still needed but you will not
    be charged."* `[DATA]` Tell the Principal before signup.
12. **§2.2.1(h): no credit-card data on any property receiving Free Services.** `[DATA]` Fine now; permanently
    forecloses adding payments to this property.
13. **GitHub Free gives no branch protection on private repos and no audit log.** `[DATA]` Weakens any
    "GitHub is our audit trail" claim.
14. **GitHub Actions `schedule` is delayed at high load, especially on the hour.** `[DATA]` Never use it for the
    Supabase keep-alive.
15. **Neon free projects idle 90+ days are deleted from 5 Oct 2026**; **Turso archives free DBs after 10 days
    idle.** `[DATA]` New policies — remembered knowledge about either vendor is now stale.
16. **Supabase Free = 2 active projects.** `[DATA]` A separate staging project consumes your whole allowance.
17. **R2's free tier is Standard class only.** `[DATA]` "Optimising" attachments to Infrequent Access starts a bill.
18. **Cloudflare Pages: 500 builds/month, 1 concurrent.** `[DATA]` The limit a solo builder is likeliest to hit in
    week one.
19. **Sentry Developer = ONE user.** `[DATA]` Bus-factor of one on error visibility.
20. **Backblaze free egress = 3× average monthly storage.** `[DATA — indirect]` A small bucket earns a small
    allowance.

---

## SOURCES (all fetched 2026-08-03)

**Supabase:** [pricing](https://supabase.com/pricing) · [regions](https://supabase.com/docs/guides/platform/regions) ·
[auth SMTP](https://supabase.com/docs/guides/auth/auth-smtp) · [backups](https://supabase.com/docs/guides/platform/backups) ·
[going into prod](https://supabase.com/docs/guides/platform/going-into-prod) ·
[free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing) ·
[DPA](https://supabase.com/legal/dpa) · [terms](https://supabase.com/terms)

**Cloudflare:** [Workers limits](https://developers.cloudflare.com/workers/platform/limits/) ·
[Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) ·
[Pages limits](https://developers.cloudflare.com/pages/platform/limits/) ·
[D1 limits](https://developers.cloudflare.com/d1/platform/limits/) ·
[D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) ·
[D1 data location](https://developers.cloudflare.com/d1/configuration/data-location/) ·
[KV limits](https://developers.cloudflare.com/kv/platform/limits/) ·
[Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/) ·
[R2 pricing](https://developers.cloudflare.com/r2/pricing/) ·
[One-time PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/) ·
[seat management](https://developers.cloudflare.com/cloudflare-one/identity/users/seat-management/) ·
[Zero Trust setup](https://developers.cloudflare.com/cloudflare-one/setup/) ·
[Access product page](https://www.cloudflare.com/sase/products/access/) ·
[Pages preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/) ·
[Pages known issues](https://developers.cloudflare.com/pages/platform/known-issues/) ·
[Data Localization](https://developers.cloudflare.com/data-localization/) ·
[Regional Services](https://developers.cloudflare.com/data-localization/regional-services/) ·
[Self-Serve Subscription Agreement](https://www.cloudflare.com/terms/)

**Oracle:** [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) ·
[Free Tier overview](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)

**Other DB:** [Neon pricing](https://neon.com/pricing) · [Neon regions](https://neon.com/docs/introduction/regions) ·
[Turso pricing](https://turso.tech/pricing) · [Xata pricing](https://xata.io/pricing) ·
[Fly.io pricing](https://fly.io/docs/about/pricing/) · [Render free](https://render.com/docs/free) ·
[Railway plans](https://docs.railway.com/reference/pricing/plans)

**Email:** [Brevo plans (help centre)](https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans) ·
[Brevo sender creation](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email) ·
[Resend pricing](https://resend.com/pricing) · [Resend domains](https://resend.com/docs/dashboard/domains/introduction) ·
[MailerSend pricing](https://www.mailersend.com/pricing) · [SES pricing](https://aws.amazon.com/ses/pricing/) ·
[ZeptoMail pricing](https://www.zoho.com/zeptomail/pricing.html)

**Ops:** [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) ·
[GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) ·
[GitHub workflow triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) ·
[cron-job.org](https://cron-job.org/en/) · [UptimeRobot pricing](https://uptimerobot.com/pricing/) ·
[Sentry pricing](https://sentry.io/pricing/)

**Legal:** [DPDP Act 2023 s.16 (Indian Kanoon)](https://indiankanoon.org/doc/172647580/)
