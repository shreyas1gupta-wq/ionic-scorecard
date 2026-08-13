# Can GitHub be the datastore for the Ionic Wealth internal ticketing app?

**Research dimension:** GitHub-as-database vs GitHub-as-encrypted-backup
**Researched:** 2026-08-03. Every vendor limit below reflects what the cited page said on that date. Free-tier limits and legal rules change — re-verify before build.
**Epistemic tags:** [DATA] = verified from a named primary source · [INFERENCE] = my reasoning from that data · [OPINION] = judgment · UNVERIFIED = could not confirm.

---

## VERDICT UP FRONT

| Question | Verdict |
|---|---|
| GitHub as the app's **primary datastore** (commits = writes) | **NO.** Six independent blockers, at least two of them fatal on their own. |
| GitHub as an **encrypted backup target** | **YES.** This is the legitimate, defensible version of "our data on our GitHub." Use `age`, asymmetric, keys never on the server. |
| GitHub Pages as the **app host** | **NO.** Cannot be private on the Free plan at all, and it's static-only. |
| GitHub Actions as the **app backend** | **NO.** Cannot serve HTTP, and GitHub's own product terms forbid using Actions "as part of a serverless application." |

**The user's instinct is half right.** "Keep our data on our GitHub" is a good instinct about *control and offsite copies*, and a bad instinct about *where the live database lives*. The defensible translation is in §E.

---

# A. GitHub as PRIMARY datastore

## A1. Concurrency — the write model is compare-and-swap, and GitHub tells you to serialise

**[DATA]** `PUT /repos/{owner}/{repo}/contents/{path}` ("Create or update file contents") takes a `sha` parameter described as "the blob SHA of the file being replaced," and it is "required if you are updating a file." The endpoint documents **409 Conflict** as a possible response.
Source: https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28

**[DATA]** Same page, verbatim: *"If you use this endpoint and the 'Delete a file' endpoint in parallel, the concurrent requests will conflict and you will receive errors. You must use these endpoints serially instead."*

**[INFERENCE]** So the write semantics are:
- Same file, two concurrent writers → the second gets **409** because its `sha` is stale. This is optimistic concurrency control (CAS). It is *correct* — you do not get silent lost updates — but every writer must implement retry-with-refetch.
- Omit `sha` on an existing file → rejected (422), not an overwrite. So you cannot accidentally clobber via this endpoint.
- If instead you use the lower-level Git Data API (create blob → create tree → create commit → `PATCH /git/refs/heads/main`), the ref update is rejected as a non-fast-forward unless you pass `force: true`. **Passing `force: true` is exactly how you get silent lost updates.** Any tutorial that force-pushes is broken.

**[INFERENCE] What serialisation would actually be required:** a single-writer mutex in front of GitHub — on Cloudflare that means a Durable Object, or a queue with concurrency 1. **And that is the argument that ends the discussion:** the moment you have built a Durable Object that holds the write lock, you have a stateful, transactional, strongly-consistent store *already in your hands* (DO storage / D1), and you are using it to protect a slower, weaker store behind it. You are paying for a database in order to serialise writes to a non-database.

**[OPINION]** There is one variant that *does* dodge the conflict problem, and it is worth naming honestly because the user's design invites it: because the status log is **append-only**, you could write **one new file per status update** (`tickets/{id}/updates/{ulid}.json`). Unique paths → no CAS, no 409, no lock. That is the strongest possible version of GitHub-as-DB. It still dies on A2/A3 (read amplification and the 3,000-entry directory cap), but it is the only shape worth even considering, so evaluate any proposal against it, not against the naive "one big tickets.json."

## A2. Rate limits

All from https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api (fetched 2026-08-03), quoted verbatim:

**Primary [DATA]:**
- Authenticated personal access token: **"5,000 requests per hour"**
- GitHub App installation: **"5,000 requests per hour"** baseline; **"Installations that have more than 20 repositories receive another 50 requests per hour for each repository"** and same per user, capped at **"12,500 requests per hour."**
- `GITHUB_TOKEN` inside Actions: **"1,000 requests per hour per repository"** (15,000 on Enterprise Cloud).

**Secondary [DATA]:**
- **"No more than 100 concurrent requests are allowed"**
- **"No more than 900 points per minute"** for the REST API
- **"No more than 90 seconds of CPU time per 60 seconds of real time"**
- **⚠ "No more than 80 content-generating requests per minute and no more than 500 content-generating requests per hour"**
- Point values: **GET/HEAD/OPTIONS = 1 point; POST/PATCH/PUT/DELETE = 5 points**

**[INFERENCE] What this means for 10–50 employees:**
- The binding constraint is **500 content-generating requests per hour**. Every commit is content-generating. So the app has a hard ceiling of **500 writes/hour, ~12,000/day** across the whole company. Routine status punches (say 50 people × 5 updates/day = 250/day) fit comfortably.
- The 900-points/min rule caps you at **180 writes/minute** (5 points each).
- **The thing that will actually break it is not steady state — it is bursts and batch jobs.** One data migration, one backfill, one "re-index all tickets" loop, one buggy retry storm and you are rate-limited for the rest of the hour, i.e. **the app is down and no one can save work.** A database does not have a 500-writes-per-hour cliff.
- Read side is worse than it looks: a manager dashboard showing "everyone's current status" must read many files. Without a materialised index you burn 1 point per file per page load, against 5,000/hr shared by *all users* (single bot PAT = one shared bucket). 50 users × a dashboard that touches 100 files = 5,000 requests = **one hour of quota per page-load-round.**

**[DATA]** Separately, repository-level activity limits (https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits): Git read operations — *"The recommended maximum limit is 15 operations per second per repository"*; push rate — *"The recommended maximum limit is 6 pushes per minute per repository."*
**UNVERIFIED:** whether an API-created commit counts against the "6 pushes per minute" figure. The docs do not say. If it does, the real write ceiling is ~6/min, not 180/min. **This is the single most important thing to test before anyone builds this** — and the fact that it is undocumented is itself a reason not to build a business system on it.

## A3. Latency, repo size, file size

**Latency — measured, not remembered.** [DATA] I measured 5 sequential HTTPS calls to `api.github.com/rate_limit` from this exact machine (Windows 11 work laptop, corporate proxy) on 2026-08-03:

```
time_namelookup time_connect time_appconnect time_starttransfer time_total code
0.4736          0.4756       0.7101        0.8292             0.8293     200
0.1382          0.1397       0.3223        0.3425             0.3427     200
0.0825          0.0842       0.2235        0.2439             0.2442     200
0.0699          0.0712       0.1645        0.1871             0.1872     200
0.0407          0.0423       0.1549        0.1779             0.1780     200
```
Cold first call **829 ms** (DNS 474 ms). Warm-DNS, new-TLS-connection reads settle at **~180–240 ms**.

**[INFERENCE]** A single logical write costs:
- Contents API: GET current sha (~180 ms, or cached) + PUT that creates a blob, tree, commit and moves the ref server-side. A commit-creating PUT is materially heavier than a `rate_limit` GET. Realistic **~400–900 ms per write**, and it is *serialised* if you took the lock in A1.
- Git Data API path: 4 sequential round trips (blob → tree → commit → ref) = **~0.8–2.0 s**.

Compare: a D1/SQLite write is sub-10 ms. **[OPINION]** A CRM where clicking "Save update" takes ~1 second on a good day and queues behind other users' saves will be perceived as broken by colleagues, and perceived-broken internal tools get abandoned. That is a product risk, not just an engineering one.

**Repo and file limits** [DATA] (https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits, verbatim):
- Single object size: *"The recommended maximum limit is 1MB. This is enforced at 100MB."*
- Push size: *"This limit is enforced at 2GB"*
- On-disk size (`.git`): **10 GB** recommended maximum
- **Directory width (entries in a single directory): 3,000** — ⚠ directly fatal to the "one file per status update" pattern above; you hit it after 3,000 updates in any one folder and must shard by date/hash.
- Maximum directory depth: 50
- Branches: 5,000 recommended max
- Diff caps: 300 files max per diff, 500 KB / 20,000 lines per file

**UNVERIFIED:** the widely-repeated "GitHub Free = 2 GB per repo, Team = 4 GB, Enterprise = 5 GB" figures. I found these only on third-party blogs (gitprotect.io, Medium), **not** on any docs.github.com page. GitHub's own primary page gives the 10 GB on-disk guidance and no per-plan repo quota. Do not plan against the 2 GB number as fact.

**[INFERENCE]** Git never forgets. Every version of every ticket file is a permanent blob. 250 writes/day ≈ 91,000 commits/year. The repo grows monotonically forever and **cannot be shrunk without rewriting history** — which is precisely the operation §B says you must avoid. So the datastore has a built-in, unfixable growth ratchet.

## A4. GitHub Actions — minutes, storage, and whether it can serve a request

**[DATA]** GitHub Free includes *"2,000 minutes per month"* of Actions and *"500 MB GitHub Packages storage"* (https://docs.github.com/en/get-started/learning-about-github/githubs-plans). The billing page gives Free: **2,000 minutes/month, 500 MB artifact storage, 10 GB cache storage per repository**, and *"GitHub Actions usage is free for public repositories that use standard GitHub-hosted runners"* — i.e. the 2,000-minute meter is what applies to **private** repos. Paid overage rates: Linux 2-core $0.006/min, Windows $0.010/min, macOS $0.062/min.
Source: https://docs.github.com/en/billing/concepts/product-billing/github-actions

**[DATA] Zero-budget safety, and this is genuinely good news:** *"If your account does not have a valid payment method on file, usage is blocked once you use up your quota."* **[INFERENCE]** With no card on file, Actions **fails closed rather than billing** — which satisfies the hard "no credit-card-then-charged" constraint. Keep no payment method on the account, deliberately.

**[DATA] Can Actions serve a live HTTP request? No — and it is contractually forbidden, not merely impractical.** GitHub's Terms for Additional Products and Features state, as prohibited use of Actions:
> *"If using GitHub-hosted runners, any other activity unrelated to the production, testing, deployment, or publication of the software project associated with the repository where GitHub Actions are used."*

and

> *"Any activity that places a burden on our servers, where that burden is disproportionate to the benefits provided to users (for example, don't use Actions as a content delivery network or **as part of a serverless application**, but a low benefit Action could be ok if it's also low burden)."*

Source: https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features

**[INFERENCE]** This kills the specific clever design people reach for — "Cloudflare front end calls `repository_dispatch`, an Action serialises the write and commits." That is textbook "Actions as part of a serverless application." Technically it also cannot serve a synchronous response: Actions has no inbound routing, no listening port, and workflow dispatch is fire-and-forget with tens-of-seconds queue latency.

**[DATA] Scheduled-workflow decay trap (matters for the *backup* design in §D):** *"In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days."* Shortest interval is *"once every 5 minutes."* Scheduled workflows *"run on the latest commit on the default branch"* and *"can be delayed during periods of high loads."*
Source: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
Note the docs sentence is scoped to *public* repositories; community reports say private repos behave the same but I could not confirm that in the docs — **UNVERIFIED for private repos.**
**[INFERENCE]** For a backup cron this is a silent-failure risk: a backup job that stops running without alerting is worse than no backup. It self-heals *if and only if* each run actually commits something (the commit is repository activity). See §D12 — this is one concrete reason to prefer non-deterministic encryption, which guarantees every run produces a differing file and therefore a real commit.

**So what hosts the app?** [INFERENCE] Not GitHub. Cloudflare Workers (already settled as the platform in the project brief). Free-plan Workers limits [DATA] (https://developers.cloudflare.com/workers/platform/limits/): **100,000 requests/day, 10 ms CPU per request, 50 subrequests/request, 128 MB memory, 3 MB worker size, 5 Cron Triggers per account.** For 10–50 staff, 100k req/day is ample. The 10 ms CPU limit is fine for DB-backed CRUD (waiting on I/O is not CPU time) but is a real constraint on anything crypto-heavy in the request path.

## A5. GitHub Pages — cannot be private on Free. This is decisive.

**[DATA]** GitHub Free (personal and organizations) includes *"GitHub Pages in public repositories"* — GitHub's own plan page lists Pages for **public repos only** on Free.
Source: https://docs.github.com/en/get-started/learning-about-github/githubs-plans

**[DATA]** Publishing a Pages site **privately requires GitHub Enterprise Cloud**: *"To publish a GitHub Pages site privately, your organization must use GitHub Enterprise Cloud."* Access control for Pages (site visible only to people with repo read access) is an Enterprise Cloud feature; there is no private-Pages option on Free, Pro, or Team.
Sources: https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site · https://github.blog/changelog/2021-01-21-access-control-for-github-pages/

**[DATA]** Pages limits: published site ≤ **1 GB**; soft bandwidth limit **100 GB/month**; soft limit **10 builds/hour**.
Source: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

**[DATA]** Pages is static — *"a static site hosting service that takes HTML, CSS, and JavaScript files straight from a repository"* — no server-side execution.
Source: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

**[DATA] And it is contractually barred for this use anyway:**
> *"GitHub Pages is not intended for or allowed to be used as a free web hosting service to run your online business, e-commerce site, or any other website that is primarily directed at either facilitating commercial transactions or providing commercial software as a service (SaaS)."*

Source: https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features

**[INFERENCE] Bottom line on Pages:** three independent nos. (1) On Free you cannot publish Pages from a private repo at all, so the *only* Pages site you could stand up is world-readable. (2) Even on paid tiers below Enterprise Cloud the *site* is public. (3) An internal CRM for a SEBI-regulated wealth manager is a tool for running the business, which the Pages terms exclude. **Cloudflare for hosting is the right call and this is the evidence for it** — it is not a preference, it is the only compliant option in the free-tier universe here.

---

# B. The ERASURE problem

## B6. How hard is it to truly delete personal data from git history?

**[DATA]** GitHub's own guidance, verbatim: *"If you only rewrite your history and force push it, the commits with sensitive data may still be accessible elsewhere"* — specifically *"In any clones or forks of your repository"* and *"Directly via their SHA-1 hashes in cached views on GitHub."*

To actually purge it you must *"Contact us through the GitHub Support portal"* with the repository name, number of affected pull requests, and commit details; Support will then *"Dereference or delete any affected PRs on GitHub"* and *"Run a garbage collection on the server to expunge the sensitive data."*

The recommended tool is **git-filter-repo, at least version 2.47, with the `--sensitive-data-removal` flag.** Force-pushing means *"forcibly updating all branches, tags, and refs and you are discarding any changes others may have made to those refs."* GitHub also notes *"clueful users with an existing clone will notice the history divergence and can use it to quickly and easily find the sensitive data still in their clone."*
Source: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

**[INFERENCE]** The full honest cost of one erasure request, if ticket data lives in git:
1. Identify every commit touching that person's data — across renamed paths, merges, and any file that mentions them.
2. `git filter-repo --sensitive-data-removal` → rewrites **every downstream commit SHA.**
3. Force-push. Every open PR is broken; every teammate's clone diverges and must be re-cloned.
4. **Open a support ticket with GitHub and wait** for server-side GC and PR dereferencing. You do not control this step's timing — and DPDP will impose response timelines. You are outsourcing a legal deadline to a vendor's support queue.
5. Chase every clone and fork. On a work laptop fleet with no admin rights and no MDM, **you cannot enumerate the clones, let alone purge them.** BFG Repo-Cleaner is the older alternative tool; GitHub's current page names git-filter-repo, not BFG. Note also that on GitHub a fork network shares an object store, so a commit that reached any fork stays reachable from siblings — **UNVERIFIED** in current docs, but the standard reason to disable forking on a data-bearing repo.
6. **The whole procedure is not idempotent, not automatable, and not something you can run for the 4th erasure request in a month.**

## B7. Consequence under DPDP — and the crucial nuance almost everyone gets wrong

**The retention/erasure duties:**

**[DATA]** DPDP Act 2023 **s.8(7)**, verbatim: *"A Data Fiduciary shall, unless retention is necessary for compliance with any law for the time being in force,— (a) erase personal data, upon the Data Principal withdrawing her consent or as soon as it is reasonable to assume that the specified purpose is no longer being served, whichever is earlier; and (b) cause its Data Processor to erase any personal data that was made available by the Data Fiduciary for processing to such Data Processor."* s.8(8) deems the purpose no longer served if the Data Principal neither approaches the Fiduciary nor exercises rights *"for such time period as may be prescribed."*
Source: https://www.dpdpa.com/dpdpa2023/chapter-2/section8.html

**[DATA]** **s.12(1)**: the right to correction/completion/updating/erasure is framed as belonging to a Data Principal *"for the processing of which she has previously given consent."* s.12 also carries an erasure right subject to exceptions where data is *"retained as mandated by any law."*
Source: https://www.dpdpa.com/dpdpa2023/chapter-3/section12.html
⚠ Caveat: dpdpa.com is a convenience reproduction, not the Gazette. **Verify final wording against the MeitY/Gazette text before relying on the consent-scoping point.**

**[DATA]** **s.7(i)** makes it a *legitimate use* — no consent needed — to process personal data *"for the purposes of employment or those related to safeguarding the employer from loss or liability, such as prevention of corporate espionage, maintenance of confidentiality of trade secrets, intellectual property, classified information or provision of any service or benefit sought by a Data Principal who is an employee."*
Source: https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html

**[INFERENCE] — this materially de-fangs, but does not remove, the erasure exposure:**
- Employee names, work emails and task history in an internal ticketing tool are processed **for employment purposes under s.7(i)**, not on consent. Since the s.12 right to erasure is textually tied to processing *"for which she has previously given consent,"* **an employee most likely cannot demand erasure of their own task history from an internal work system.** So the nightmare scenario ("a departing colleague DPDP-notices us and we must rewrite git history") is *weaker* than the scary framing suggests.
- **But s.8(7) still bites.** Its wording is not limited to consent-based processing: the trigger is *"as soon as it is reasonable to assume that the specified purpose is no longer being served."* An ex-employee's ticket history has a purpose end-date. So there is a **proactive retention-limit purge duty** even with no request from anyone, subject only to the "necessary for compliance with any law" carve-out.
- Retention *periods* under s.8(8) are "as may be prescribed" — the prescribed periods in DPDP Rules 2025 attach to specified large classes (large e-commerce / online gaming / social media). **[INFERENCE]** A 10–50-person wealth manager is nowhere near those thresholds, so **no fixed statutory purge clock currently applies to this app** — the duty is the general "purpose served" test, which you satisfy with your own documented retention policy. UNVERIFIED as to the exact Schedule thresholds; confirm against the notified Rules.

**[DATA] Timing runway:** DPDP Rules 2025 were notified **13 November 2025**. Rules 1, 2 and 17–21 took effect immediately; consent-manager provisions at 12 months (13 Nov 2026); **the bulk of substantive obligations at 18 months — from ~13 May 2027.**
Sources: https://www.privacyworld.blog/2025/11/india-passes-the-digital-personal-data-protection-rules-ushering-in-a-new-digital-age-in-india/ · https://www.ilflaw.com/publications/digital-personal-data-protection-rules-2025-notified/ (secondary/law-firm sources; **verify against the MeitY notification**)
**[OPINION]** There is real runway. That is an argument for designing this correctly now while it is cheap, not for ignoring it.

**The counter-obligation that flips the analysis:**

**[DATA]** SEBI (Portfolio Managers) Regulations, 2020: a portfolio manager *"shall preserve the books of account and other records and documents ... for a minimum period of five years."*
Source: https://www.sebi.gov.in/legal/regulations/feb-2023/securities-and-exchange-board-of-india-portfolio-managers-regulations-2020-last-amended-on-february-07-2023-_69223.html (regulation number reported as 29 in secondary sources — **verify the exact regulation number in the SEBI text**)

**[INFERENCE]** For any ticket that evidences regulated activity (a client instruction, a review, an investment-rationale step), **retention for 5 years is legally required**, which lands squarely in the s.8(7) *"unless retention is necessary for compliance with any law"* carve-out. So the picture is not "delete everything fast." It is: **regulated-work records must be kept 5 years; everything else must be purgeable on a schedule you define.** Any design that cannot do *both* is wrong — and git history can do only the first.

**[DATA] And the flip side — immutability is explicitly required, not merely nice:** DPDP Rules 2025 **Rule 6** (reasonable security safeguards) requires, as a minimum set: encryption/obfuscation/masking of personal data, access controls, logging and monitoring of access and processing, measures for continued processing including **backups**, and **retention of logs for one year** for detection, investigation and remediation.
Sources: https://ksandk.com/data-protection-and-data-privacy/dpdp-rule-6-and-indias-new-cybersecurity-compliance-standard/ · https://tsaaro.com/blogs/dpdp-rules-2025-explained-full-overview-and-practical-summary (both secondary summaries; **I could not obtain verbatim Rule 6 text — get the Gazette PDF before quoting it to anyone**)

### Is git history a compliance ASSET or a LIABILITY?

**[OPINION] Both, and they are separable — that separation is the whole design insight.**

- **Asset:** an append-only, hash-chained record is exactly what Rule 6's logging/monitoring requirement and the user's own "never overwritten" requirement want. Tamper-evidence is genuinely valuable to a SEBI-regulated firm.
- **Liability:** the same immutability makes *targeted deletion* a multi-day, vendor-dependent, un-repeatable operation you cannot fully complete.

**How to get the asset without the liability — three moves:**

1. **Separate the event from the identity.** The immutable log stores a **pseudonymous actor ID** (`emp_7f3a…`) plus timestamp and status text. The `actor_id → name/email` mapping lives in **exactly one mutable row** in the database. Erasure or retention-purge = delete that one row. The immutable history survives intact for audit but is no longer attributable to a person. This is standard tokenisation / crypto-shredding.
   ⚠ **Caveat you must not skip:** free-text status updates will contain names anyway ("spoke to Rahul about…"). Pseudonymising the actor field does nothing about free text. Mitigations: keep the status field short and structured, warn in the UI, and accept that free text is the residual risk. **[OPINION]** This is the honest weak point of the whole scheme and should be stated to the Principal rather than glossed.
2. **Put the immutable log in the database, not in git.** You get append-only semantics in SQL with an INSERT-only table, no UPDATE/DELETE grants, and a `prev_hash` column chaining each row to its predecessor. Tamper-evident, *and* individual rows are deletable when law requires it. **[OPINION] This is the key realisation: the user wants git's immutability *property*, and you can have that property in SQL without any of git's costs.**
3. **Anchor it externally for tamper-evidence.** Periodically (e.g. daily) commit just the **hash-chain head** — a single hex string, no personal data — to the GitHub repo. Now you have a git-timestamped, immutable proof that the log has not been retroactively edited, while the log itself stays purgeable. Cheap, and it is the genuinely clever version of "our audit trail is on our GitHub."

---

# C. Access control

## C8. Private repo access is all-or-nothing

**[DATA/INFERENCE]** A collaborator with read access does `git clone` and receives **the entire repository and its complete history**, by git's design. There is **no row-level, per-user, or per-field restriction inside a repository. None. This cannot be worked around.** Git's unit of authorisation is the repository.

**[INFERENCE]** For this app that means: any employee who could read the data repo could read **every ticket for every colleague, plus every historical version** — the exact opposite of the requirement ("assignees see their own; managers/admins see everyone"). Role-based visibility is impossible on a git backend. On its own this is disqualifying for GitHub-as-DB.

**[DATA] ⚠ Personal-account repos cannot grant read-only at all**, verbatim: *"A repository owned by a personal account has two permission levels: the repository owner and collaborators"* … *"In a private repository, repository owners can only grant write access to collaborators. Collaborators can't have read-only access to repositories owned by a personal account."* GitHub's own advice: *"If you require more granular access to a repository owned by your personal account, consider transferring the repository to an organization."*
Source: https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-personal-account-settings/permission-levels-for-a-personal-account-repository

**[INFERENCE] Actionable regardless of which design wins:** put the repo in a **GitHub Free organization**, never a personal account. On a personal account every collaborator you add can rewrite or delete the data. Free orgs include *"Team access controls for managing groups"* [DATA, plans page], so read-only repository roles are available there. **[OPINION]** Also: an org-owned repo survives the builder leaving the company; a personal repo walks out with them. For a firm asset that matters more than the permissions detail.

**Audit / access log:**

**[DATA]** The organization audit log: *"Only owners can access an organization's audit log"*; *"The audit log lists events triggered by activities that affect your organization within the last 180 days"*; and *"Organizations that use GitHub Enterprise Cloud can interact with the audit log using the GraphQL API and REST API."* Git events specifically are retained **7 days** (per the Enterprise Cloud docs).
Sources: https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/reviewing-the-audit-log-for-your-organization · https://docs.github.com/en/enterprise-cloud@latest/admin/concepts/security-and-compliance/audit-log-for-an-enterprise

**[INFERENCE]**
- The audit-log **UI** appears available to org owners on all plans (that page states no plan gate) — but **programmatic access is Enterprise Cloud only**, so you cannot automate monitoring or export it into a compliance record on Free.
- **Git clone/fetch events are retained only 7 days and are surfaced through Enterprise-tier tooling.** So on GitHub Free you effectively **cannot prove who cloned the repository.** For a breach investigation under DPDP Rule 6 — which wants a year of access logs — that is a straight gap. **[OPINION]** This is the quiet, underrated finding: not "someone might read it" but "you would never be able to demonstrate whether they did."
- 180-day audit retention also falls short of Rule 6's one-year log expectation, so the app must keep its **own** access log regardless of what GitHub does.

## C9. Free-plan security features for private repos — the tamper-evidence claim collapses

**[DATA] Branch protection / rulesets:** *"Rulesets are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud."* Protected branches: same pattern — public repos on Free, private repos only on Pro/Team/Enterprise.
Sources: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets · https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

**[DATA] Secret scanning / push protection:** *"Public repositories: Secret scanning runs automatically for free."* *"Organization-owned private and internal repositories: Available with GitHub Secret Protection enabled on GitHub Team or GitHub Enterprise Cloud."* GitHub Secret Protection is a paid product (per active committer) on Team and Enterprise Cloud.
Sources: https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning · https://github.com/security/advanced-security/secret-protection

**[INFERENCE] — this is the finding that should change the user's mind about git-as-audit-trail:**
On a **Free private repo** you get **no branch protection, no required reviews, no force-push protection, no required signed commits, no secret scanning, and no audit-log API.** Therefore:
- **Anyone with write access — and on a personal-account repo that is *every* collaborator — can `git push --force` and rewrite the entire "immutable" history**, and there is no protection to block it and no accessible log to detect it.
- **So the "tamper-evident audit trail" benefit that motivates putting data in git does not actually exist on the free tier.** You take on 100% of git's erasure liability and receive a fraction of its tamper-evidence value. **[OPINION] That asymmetry is the strongest single argument against the user's plan, and it is the one to lead with.**
- Partial mitigations if any data does live in a Free private repo: require **signed commits by convention** and verify locally; keep the hash-chain-head anchor from §B7 so tampering is detectable out-of-band; keep an **offline mirror** so a force-push cannot destroy the record.
- Also note **no secret scanning on private repos** means a leaked token or key committed by accident is silently yours to find.

---

# D. The LEGITIMATE pattern: GitHub as an ENCRYPTED BACKUP target

## D10. Tool comparison for committing encrypted dumps

| | **age** | **SOPS** | **git-crypt** | **plain gpg** |
|---|---|---|---|---|
| Maturity / status | v1.x stable; **BSD-3-Clause**; *"simple, modern and secure file encryption tool, format, and Go library ... small explicit keys, post-quantum support, no config options, UNIX-style composability"* [DATA] | **CNCF sandbox project** since 2023 [DATA] | **v0.8.0 released 23 Sep 2025**; project self-describes as *"aims to be bug-free and reliable"* but not fully mature [DATA] | Decades old, very mature, notoriously complex UX |
| Works on a **binary** dump? | **Yes** — arbitrary binary, stdin/stdout; docs show piping `tar` straight into it [DATA] | Yes — *"supports YAML, JSON, ENV, INI and BINARY formats"* [DATA] | Yes (transparent filter on tracked files) | Yes |
| **Windows, no admin rights?** | **Yes** — prebuilt binaries, plus Chocolatey/Scoop/winget [DATA]. Single static exe: drop it in a user folder, no installer [INFERENCE] | Single Go binary; Windows binaries not stated on the repo page — **UNVERIFIED**, but Go release binaries are the norm [INFERENCE] | **Weak** — C++, no official Windows binaries; needs compiling (repo has `coprocess-win32.cpp`, `util-win32.cpp`) [DATA]. **Effectively blocked on a no-admin work laptop** [INFERENCE] | Gpg4win installer, **may require admin** [INFERENCE] |
| Runs from **Actions / Cloudflare cron?** | Actions: yes (install binary). **Cloudflare Workers: yes, via `age-encryption` (typage)** — see below | Actions yes; Workers no (CLI) | Actions awkward; **Workers no** — needs git filters + a working tree | Actions yes; Workers no |
| Key management | **Asymmetric X25519.** Multiple recipients via repeated `-r`; *"Every recipient will be able to decrypt the file"* [DATA]. Passphrase mode via `-p` [DATA] | Pluggable: age, PGP, AWS/GCP/Azure/HuaweiCloud KMS, Vault [DATA] | **Symmetric shared key** in the repo, unlocked per clone | Keyring + agent + pinentry + trust model |
| Leakage | Non-deterministic (fresh file key per encryption) → no identical-file leak, no dedup [INFERENCE] | Encrypts **values**, leaves **keys/structure in plaintext** by design [INFERENCE from its "editor of encrypted files" model] | ⚠ *"AES-256 in CTR mode with a synthetic IV derived from the SHA-1 HMAC of the file"*; leaks *"whether two files are identical or not"*; does **not** encrypt *"file names, commit messages, symlink targets, gitlinks, or other metadata"* and *"does not hide when a file does or doesn't change, the length of a file, or the fact that two files are identical"* [DATA] | Fine (randomised session key) |
| Fatal caveat | none material here | Structure-preserving = wrong tool for a whole-DB dump | *"cannot be used securely unless the entire repository is protected against tampering"* (`.gitattributes` can be edited to disable encryption) [DATA] — **and §C9 says you get no branch protection on a Free private repo, so you cannot satisfy that precondition** [INFERENCE] | Operational complexity is the failure mode |

Sources: https://github.com/FiloSottile/age · https://github.com/getsops/sops · https://github.com/AGWA/git-crypt

**[DATA] The Workers-side enabler:** `age-encryption` on npm (FiloSottile/typage) is a TypeScript implementation of the age format. It *"depends only on the noble cryptography libraries, and uses the Web Crypto API when available"*, operates on `Uint8Array`, is BSD-3-Clause, supports native age recipients / passphrases / ASCII armour, targets ES2023, and is *"compatible with Node.js 20+, Bun, Deno, and all recent browsers."* Files encrypted in the browser decrypt with the CLI and vice-versa.
Sources: https://github.com/FiloSottile/typage · https://www.npmjs.com/package/age-encryption
⚠ **UNVERIFIED: Cloudflare Workers is not on typage's stated compatibility list.** It is plausible (Workers supports WebCrypto and ES modules) but **must be tested with a throwaway Worker before the design depends on it.** Fallback if it fails: a GitHub Actions scheduled job that pulls a D1 export via the REST API and encrypts with the age CLI — accepting the 60-day-idle caveat from §A4, which the non-determinism in §D12 mitigates.

**[OPINION] Recommendation: `age`.** CLI for humans on the Windows laptop, typage inside the Worker cron, same format both ends. Reject git-crypt (no Windows binary without a compiler, deterministic-encryption leakage, and its own security precondition is unmeetable on GitHub Free). Reject SOPS for the dump (structure-preserving is the wrong shape) but **SOPS is a good choice for the app's own config secrets** if that need arises. Reject gpg (complexity is the risk).

## D11. Key escrow — where the decryption key lives

**[OPINION] The design, and the property that makes it work:**

age is **asymmetric**. The backup job needs only **public keys**. Therefore **the automated system is structurally incapable of decrypting its own backups.** That single property is the entire security argument, and it is why age beats every symmetric option here.

```
D1 export (SQL)  →  gzip  →  age -r PUB_builder -r PUB_escrow -r PUB_breakglass
                                  →  commit ciphertext to private GitHub repo
```

| Recipient | Private key location | Purpose |
|---|---|---|
| `PUB_builder` | Builder's password manager + a printed copy at home | Day-to-day restores |
| `PUB_escrow` | **Printed on paper**, sealed envelope, company safe, held by Compliance/Finance — not the builder | Builder leaves / is unavailable |
| `PUB_breakglass` | Printed, sealed, **second physical location** | Fire/theft at location 1 |

**Why paper works:** [DATA] age keys are one short line (`AGE-SECRET-KEY-1…`). **[INFERENCE]** They are trivially printable and hand-transcribable — no HSM, no key server, no cost. This is the free-tier-compatible escrow mechanism.

Satisfying the two stated requirements:
- **(a) useless to an attacker with repo access** — the repo holds only ciphertext; no private key is on Cloudflare, on GitHub, in the repo, in Actions secrets, or in Worker secrets. Full compromise of both providers yields ciphertext. ✅
- **(b) restorable if the builder leaves** — the sealed escrow envelope plus a plaintext `RESTORE.md` in the repo (see D13) means Compliance can restore without the builder. ✅ **[OPINION]** This is not a nice-to-have; a backup only one departing employee can read is not a company backup, and for a regulated firm that is a governance finding waiting to happen.

⚠ **[INFERENCE] The residual risk, stated plainly:** the Worker holds a fine-grained GitHub PAT with `contents: write` on that repo. An attacker with that token cannot *read* your data but **can overwrite or delete the backups** — and §C9 means there is no branch protection to stop a force-push. Mitigations: (1) unique filename per backup, never overwrite; (2) scope the PAT to that one repo, `contents: write` only, short expiry, rotated; (3) **a monthly `git clone --mirror` to an encrypted external drive kept offline.** Without (3) you do not have a backup, you have a second copy that the same attacker can delete.

## D12. Is committing ciphertext to a private repo safe and defensible?

**[OPINION] Yes — and note the security rests on the encryption, not on the repo being private.** Repo privacy is defence-in-depth. If you would not be comfortable with the file being public, the encryption is not doing its job.

Caveats, each with a mitigation:

1. **Deterministic encryption / structure leakage** — not an issue for age (fresh random file key each run, so no identical-file leak). It *is* an issue for git-crypt [DATA, §D10] and for SOPS (plaintext keys/structure). Another reason for age.
2. **No delta compression.** [INFERENCE] Non-deterministic ciphertext means every backup is a full, incompressible blob — git cannot delta them. So repo size grows linearly at (dump size × frequency). **Mitigation: `gzip` *before* `age`** (age does not compress). A ticketing DB for 50 staff is small; SQL dumps typically compress ~10:1, so expect ~200 KB–2 MB per daily backup ⇒ **~70–700 MB/year**, comfortably inside the 10 GB on-disk guidance. **Still write down a rotation policy** (e.g. daily→30 days, weekly→1 year, monthly→5 years to match SEBI) and when the repo eventually gets large, **start a new repo per year and archive the old one — never rewrite history.**
   ⚠ Sub-caveat: compress-then-encrypt leaks the *compressed* size, which correlates with data volume. Acceptable here (compression-oracle attacks need attacker-chosen plaintext mixed into the same stream, which does not apply to a whole-DB dump). Pad to fixed size buckets only if someone insists.
3. **Filename leakage.** [INFERENCE] Name files `backup-YYYY-MM-DDTHHMM.sql.gz.age` — reveals only cadence. **Never put ticket IDs, employee names, or `client_ref` codes in paths or commit messages.** Commit messages are plaintext forever and are *not* covered by any encryption tool [DATA: git-crypt explicitly does not encrypt commit messages].
4. **Size leakage.** Reveals growth and activity level. Low sensitivity; accept.
5. **⚠ Key rotation can silently destroy old backups.** [INFERENCE] Adding a new recipient does **not** re-encrypt existing files — old ciphertext remains decryptable only by the *old* recipient set. **If you rotate keys and destroy the old private key, every backup made before the rotation becomes permanently unrecoverable.** Rules: **never destroy an escrowed private key**; and on rotation, run a one-off local re-wrap (decrypt with an escrow key, re-encrypt to the new recipient set, commit as new files). Document the recipient set used, per backup, in the manifest.
6. **Cross-border transfer.** [INFERENCE] GitHub is a US processor. DPDP s.16 permits transfer except to countries the Central Government restricts; no restricting notification is known to me — **UNVERIFIED, confirm current status.** Strong supporting position: only ciphertext leaves India and GitHub holds no key, so GitHub is arguably not processing personal data in intelligible form. **[OPINION]** Defensible, not settled — and it is a materially better position than shipping plaintext tickets to a US provider, which is what the naive GitHub-as-DB plan actually does.
7. **Happy accident worth exploiting.** [INFERENCE] Because age output differs on every run, each backup **always** produces a real commit — which counts as repository activity and therefore keeps a scheduled Actions workflow from being auto-disabled at 60 days idle (§A4). A deterministic scheme producing byte-identical output would commit nothing and could let the cron silently die.

**Backup source mechanics** [DATA]: Cloudflare D1 can be exported to a `.sql` file via `wrangler d1 export` (schema and/or data, `--no-data` / `--no-schema`), and there is a REST endpoint **`POST /accounts/{account_id}/d1/database/{database_id}/export`** with `output_format: "polling"` — an in-progress export *"must be continually polled or will automatically cancel"*, and on completion the response carries a `SignedURL` *"available for one hour."* Caveats: export is unsupported for virtual tables, *"running exports block other database requests"*, and numeric values are affected by JavaScript's 52-bit precision.
Sources: https://developers.cloudflare.com/d1/best-practices/import-export-data/ · https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/export/ · https://developers.cloudflare.com/workflows/examples/backup-d1/
**[INFERENCE]** The polling requirement means the export cannot be a fire-and-forget call from a 10 ms-CPU Worker; use Cloudflare Workflows (Cloudflare publishes a "back up D1" Workflows example) or run the export from a scheduled GitHub Actions job. **Run backups outside business hours** because exports block other queries. The 52-bit precision note is a reason to store money as integer paise, not floats.

**Also — you already have a free first line of defence** [DATA]: D1 **Time Travel** is point-in-time recovery, *"always on"*, no configuration, no extra cost — **7 days of retention on the free plan** (30 days on paid), restorable to any bookmark/timestamp.
Source: https://developers.cloudflare.com/d1/reference/time-travel/
**[INFERENCE]** Time Travel covers "I ran a bad UPDATE an hour ago." It does **not** cover account loss, malicious admin, or vendor exit, and 7 days is short. So it complements the GitHub backup; it does not replace it.

## D13. Restore drill

**The manifest (do this at backup time or the drill cannot verify anything).** Alongside each `.age` file, commit a **plaintext** `manifest-<ts>.json` containing: timestamp, per-table **row counts** (aggregates, not personal data), **SHA-256 of the plaintext** (pre-encryption), gzip and age tool versions, the recipient list used, and the D1 bookmark. This lets you verify a restore is complete without decrypting, and detects silent truncation.

**The drill, step by step:**
1. **Quarterly**, on a scheduled date, logged.
2. Clean machine / empty folder. Download `age` and `sqlite3` from pinned URLs in `RESTORE.md`.
3. `git clone` the backup repo (proves the repo itself is intact, not just one file).
4. Open the **sealed escrow envelope** and use that key — **not** the builder's key. Testing with the builder's key tests nothing about escrow.
5. `age --decrypt -i escrow.key backup-<ts>.sql.gz.age | gunzip > restore.sql`
6. `sha256sum restore.sql` → **must equal the manifest hash.**
7. `sqlite3 restored.db < restore.sql` locally; and separately `wrangler d1 execute <scratch-db> --file restore.sql` to prove it loads into a real D1.
8. Verify: per-table row counts match the manifest; `max(created_at)` matches the backup timestamp; a **known canary ticket** (a permanent dummy ticket with fixed text) is present and correct.
9. Record elapsed wall-clock time — that is your real RTO, and the number to quote to the Principal.
10. Sign off in `RESTORE_DRILL_LOG.md`: date, who ran it, which key, elapsed time, anomalies.

**[OPINION] How you *prove* it works — the only test that counts:** at least once, the drill must be completed by **someone other than the builder**, using only the sealed envelope and the written `RESTORE.md`, with the builder unavailable and not answering questions. Anything less proves the builder can restore, which was never in doubt. Keep `RESTORE.md` in the repo root in plaintext (commands, pinned tool download URLs, versions, where the envelopes are, who holds them — **no secrets**). A backup procedure that lives only in the builder's head is a single point of failure with a notice period.

---

# E. VERDICT

## GitHub as the database: **NO.** Do not build this.

Six blockers. **Any two of #1, #3, #5 alone would be enough.**

1. **No per-user access control.** Repo read access = full clone of all data and all history. Row-level or role-based visibility inside a repo is **impossible**. The app's core requirement (assignees see their own, managers see all) cannot be expressed. And on a **personal-account** private repo you cannot even grant read-only — every collaborator gets write [DATA].
2. **Writes need an external mutex.** GitHub docs mandate serial writes and return 409 on stale-sha; the only lost-update-free alternative is force-push, which *is* the lost update. Building the serialiser hands you a real database — at which point GitHub is a slower store hiding behind a faster one.
3. **The immutability is a liability with no compensating asset on the free tier.** Erasure requires history rewrite + force-push + **a GitHub Support ticket you don't control the timing of** + chasing clones you cannot enumerate — while on a Free private repo you get **no branch protection, no force-push protection, no required signed commits, no secret scanning, no audit-log API, and only 7-day git-event retention.** So the "tamper-evident audit trail" that justified the whole idea **does not actually exist there.** You take all the deletion pain and get little of the integrity benefit.
4. **Hard cliffs at the wrong scale.** 500 content-generating requests/hour, 180 writes/min, 3,000 entries per directory, plus a *recommended* 6 pushes/min/repo whose applicability to API commits is **undocumented**. Steady state fits 50 people; one migration or retry storm takes the app down for an hour.
5. **Nothing on GitHub can host it.** Pages on Free is **public-repos-only**, static, and its terms bar running your business on it; private Pages is **Enterprise Cloud**. Actions cannot serve HTTP and GitHub's terms explicitly say don't use it *"as part of a serverless application."*
6. **~1 s serialised writes** (measured 180–240 ms per bare API round trip from this laptop; 400–900 ms for a commit-creating PUT) versus <10 ms for SQLite/D1, in a repo that grows forever and can only be shrunk by the one operation §B tells you never to do.

## GitHub as encrypted backup: **YES.** This is the version to build.

```
Cloudflare Worker/Workflow (cron, nightly, out of hours)
  → POST /accounts/{acct}/d1/database/{db}/export  (poll → SignedURL, 1 h)
  → gzip
  → age -r PUB_builder -r PUB_escrow -r PUB_breakglass      (public keys only)
  → PUT /repos/{org}/ticketing-backups/contents/backups/backup-<ts>.sql.gz.age
  → PUT manifest-<ts>.json   (row counts, sha256 of plaintext, versions, recipients)
```
Plus: private repo in a **GitHub Free organization** (never a personal account); fine-grained PAT scoped to `contents: write` on that one repo; three age recipients with **private keys only on paper in sealed envelopes**; `RESTORE.md` in plaintext at the repo root; **monthly `git clone --mirror` to an encrypted offline drive**; quarterly restore drill run by someone who is not the builder.

## The version of "our data on our GitHub" that IS defensible

Tell the Principal this, plainly: **the instinct is right about control and wrong about mechanism.** "Our data on our GitHub" should mean *we hold our own encrypted offsite copy and our own git-timestamped integrity proof*, not *GitHub is our database*. Concretely:

| Layer | Where | Why |
|---|---|---|
| **Live data** | Cloudflare D1 (free: 5 GB, 5 M rows read/day, 100 k rows written/day) | Real transactions, real row-level access control, ~ms writes |
| **Append-only status log** | An INSERT-only D1 table with a `prev_hash` chain | The "never overwritten" property the user wants — **without** git's undeletable-personal-data problem |
| **Integrity anchor** | Daily commit of the hash-chain **head only** (one hex string, zero personal data) to the private repo | Git-timestamped tamper-evidence, all of the audit benefit, none of the erasure liability |
| **Offsite backup** | Nightly `age`-encrypted dump in the private GitHub org repo | "Our data on our GitHub" — genuinely, and safely |
| **Air-gapped copy** | Monthly `git clone --mirror` to an encrypted external drive | Because the token that writes the backups can also delete them, and there is no branch protection on Free |
| **Fast rollback** | D1 Time Travel — always on, free, 7 days | Undo a bad query without touching backups |
| **Code + change control** | The private repo | This is what git is *actually* excellent at, and it is a real compliance asset (change control) |

That is 3 copies, 2 media, 1 offsite — real 3-2-1 — at ₹0, on a Windows laptop with no admin rights, entirely push-to-GitHub driven.

**And the retention design that satisfies both regulators at once:** pseudonymous `actor_id` in the immutable log, the `actor_id → person` mapping in **one deletable row**; tickets flagged as regulated-work retained **5 years** per SEBI PMS Regs (the s.8(7) "necessary for compliance with any law" carve-out); everything else purged on a written retention schedule per DPDP s.8(7). Deleting the mapping row de-attributes the immutable history without rewriting anything. **Git history cannot do this. A SQL table can.**

---

## Open questions / what I could not verify

1. **Do API-created commits count against the "6 pushes per minute per repository" recommended limit?** Undocumented. Also matters for a very frequent backup cadence.
2. **Verbatim Rule 6 text of DPDP Rules 2025** — I only obtained law-firm summaries (encryption, access control, logging, backups, 1-year log retention). Get the Gazette/MeitY PDF before quoting it.
3. **Does the s.12 erasure right really attach only to consent-based processing?** My reading of s.12(1) says yes, which would exclude employee task history processed under s.7(i) — a load-bearing conclusion resting on a non-Gazette reproduction (dpdpa.com). **Verify against the official text.**
4. **Does typage / `age-encryption` run on Cloudflare Workers?** Not on its stated compatibility list. Test with a throwaway Worker before the design depends on it.
5. **Per-plan repository storage quotas** (the "Free = 2 GB" claim) — third-party blogs only, absent from GitHub docs.
6. **Does the 60-day scheduled-workflow auto-disable apply to private repos?** GitHub's sentence says "In a public repository."
7. **Is the org audit-log UI truly available on GitHub Free for organizations?** The docs page states no plan gate but does not affirm Free either. Check on the actual org.
8. **SEBI PMS Regulations record-retention regulation number** (secondary sources say Reg 29) and whether internal task-tracking tickets fall within "books of account and other records and documents" at all.
9. **DPDP s.16 cross-border status for the US** — no restricting notification known to me; confirm current position.
10. **⚠ Free-text status updates will contain client and colleague names** regardless of pseudonymised actor IDs. The `client_ref`-code-only design controls structured fields, not prose. This is the largest residual data-sensitivity risk in the whole app and it belongs in front of the Principal, not in a footnote.
11. **Cloudflare Zero Trust free tier is widely reported as capped at 50 users with 24-hour log retention** (secondary sources only — controld.com, costbench.com; **UNVERIFIED against Cloudflare docs**). If true: 50 users is *exactly* this firm's stated upper bound, i.e. zero headroom, and 24-hour log retention would not satisfy Rule 6's 1-year expectation, so the app must keep its own access log. Flagging for the hosting/auth dimension.
