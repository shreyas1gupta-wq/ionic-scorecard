# Dimension: A shared .xlsx (company drive / OneDrive / SharePoint / Google Drive) as the application database

**Question asked:** "Can a common Excel in backend for data saving using company drive not suffice?"
**Scope:** internal ticket/task CRM, 10–50 employees, append-only status punches, manager dashboard, zero budget, SEBI-regulated Indian wealth manager, Windows laptop with no admin rights, corporate proxy, email platform unknown, no tenant-admin cooperation assumed.

**Epistemic tags:** [DATA] = verified against a named primary source. [INFERENCE] = my reasoning from verified facts. [OPINION] = judgment. [UNVERIFIED] = could not confirm; what to check is stated.

---

## HEADLINE VERDICT

**No — not as the system of record for this app.** Two of the blockers are not engineering problems:

1. **Auth is a fork with no good branch.** To have a web app write to a tenant workbook you must either (a) use *delegated* permissions — which means every one of the 10–50 users must be able to open the file themselves, which destroys the audit trail and the row-level access story; or (b) use *application* (app-only) permissions — every one of which is documented as **"Admin consent required: Yes"** [DATA]. There is no third path. Same shape on Google (restricted-scope/internal-app trust and service-account sharing both land on the admin).
2. **Microsoft's own connector documentation states that the thing you want to do is not supported:** *"Simultaneous file modifications made by other connectors, or manual edits are not supported. Users should avoid writing data to a single Excel file from multiple clients concurrently (Excel Desktop, Excel Web, Power Automate, LogicApps or Power Apps). This can cause possible merge conflicts and data inconsistency."* [DATA]

Everything else (throttling, session expiry, 30-second write-visibility delays, whole-file reads) is survivable with careful engineering. Those two are not.

**But the Principal's instinct is not wrong, and there is a real answer hiding inside it:** he wants the data to stay in the company's own tenant, on infrastructure the firm already pays for, with no third-party free tier. That instinct is correct and achievable. The right object is a **SharePoint/Microsoft List** (or Dataverse) in the same tenant — *not a workbook*. Same drive, same tenant, same zero rupees, but with per-item version history, item-level permissions, and 30M-item capacity. See "The honest alternative" at the end.

---

## A. THE NETWORK-SHARE / LOCAL-DRIVE CASE

### A1. Can an internet-hosted app (Cloudflare Pages/Workers) reach `\\server\share\tickets.xlsx`?

**No. Not "difficult" — architecturally no.** [DATA + INFERENCE]

Plainly: `\\fileserver\share` resolves to a private address (RFC1918: 10.x, 172.16–31.x, 192.168.x) that exists only inside the office LAN. Cloudflare's edge runs in Cloudflare data centres on the public internet. There is no route from a Cloudflare data centre to your office's private address space. Nothing about the code matters; the packet has nowhere to go. Additionally SMB (TCP 445) is a stateful file-sharing protocol that no serverless edge runtime speaks, and corporate firewalls block inbound 445 as a matter of standard practice (it is the WannaCry/EternalBlue port).

Cloudflare's own product answer confirms the gap rather than closing it: to let a Worker reach a private resource you must run **Cloudflare Tunnel (`cloudflared`) on a machine inside the network** and then define a VPC Service — *"Once your tunnel is connected, you will need to ensure it can access the services that you want your Workers to have access to. The tunnel should be installed on a machine that can reach the internal resources you want to expose"* [DATA — Cloudflare Workers VPC docs, developers.cloudflare.com/workers-vpc/configuration/tunnel/]. Note what that means: the tunnel exposes **HTTP/TCP services**, not SMB file semantics. You would still have to write and host an HTTP shim *inside* the office that does the actual file I/O. At that point you have not avoided hosting a server inside the office — you have hosted one and added a tunnel. That is case A2.

[OPINION] For a SEBI-regulated firm, an employee-installed unmanaged ingress tunnel from the public internet into the corporate LAN, created by an APM without IT's knowledge, is a materially worse compliance position than any SaaS free tier. This should not be presented to the Principal as a clever workaround. It is the kind of thing that ends careers in an audit.

### A2. If the "app" runs on a machine inside the office — what changes, what breaks?

What genuinely works without admin rights [INFERENCE, based on standard Windows behaviour]:
- A user-mode process (Python/Node) can bind a port above 1024 without elevation.
- Other machines on the same LAN can reach it by IP:port, if host-based firewall rules permit (adding a Windows Firewall inbound rule *does* normally require elevation — so even LAN reachability is not guaranteed on a locked-down build). **[UNVERIFIED — needs a 5-minute test on the actual laptop: start a listener, curl it from a colleague's machine.]**
- User-level Scheduled Tasks ("at logon") can restart it.

What breaks:
- **No Windows Service.** Installing a service requires admin. So the process dies at logout/reboot/patch cycle. A logon-triggered task only runs while that user is logged in. In practice: the app is down whenever the laptop is asleep, on VPN, being patched, or in a bag.
- **Single point of failure holding the only copy of the data.** The ticket database lives on one personal work laptop. Disk failure, theft, or a re-image = total data loss. No backup story, no encryption-at-rest story, no "data under company control" story — it is under *one employee's* control, which is worse than SaaS from a governance standpoint. [OPINION]
- **The corporate proxy is not the problem here** (it governs outbound, and LAN traffic is usually direct), but **inbound from outside the office is**: NAT + corporate firewall means no work-from-home access without the tunnel from A1.
- **Availability expectations.** A ticket system with deadlines that is unreachable half the time will be abandoned by users inside two weeks. [OPINION]

### A3. File locking on Windows/SMB — what actually happens with two writers?

- **Excel desktop's mechanism is an "owner file", not a lock on the data.** Office creates a temp owner file named tilde-dollar plus the truncated filename (e.g. `~$ckets.xlsx`) holding the opener's logon name; when a second user opens the file, Office finds that owner file and reports the document as locked/read-only [DATA — Microsoft Support, "The document is locked for editing by another user", support.microsoft.com/en-us/topic/-the-document-is-locked-for-editing-by-another-user-error-message-when-you-try-to-open-a-document-in-word-10b92aeb-2e23-25e0-9110-370af6edb638]. This is advisory and fragile: if Excel crashes or the network drops, the owner file is orphaned and the file stays "locked" by a phantom user until someone deletes it manually.
- **Co-authoring does not work on a network share.** Microsoft's requirement is explicit: the workbook must be in *"OneDrive, OneDrive for Business, or a SharePoint Online library"*, and *"SharePoint On-Premises sites (sites that are not hosted by Microsoft) do not support co-authoring"* [DATA — support.microsoft.com/en-us/office/collaborate-on-excel-workbooks-at-the-same-time-with-co-authoring-7152aa8b-b791-414c-a3bb-3024e46fb104]. A UNC path is neither. So the multi-writer story on a file share is sequential-only by design.
- **There is no atomic append and no row-level lock in the .xlsx format or in SMB.** [INFERENCE, high confidence] SMB offers opportunistic locks and byte-range locks on *bytes*, and an .xlsx is a ZIP container of XML parts — appending a row changes `sheet1.xml`, the shared-strings table, dimension metadata and the ZIP central directory. Every programmatic writer in practice (openpyxl, pandas, xlsxwriter) therefore does **read-entire-file → mutate in memory → write a new file → replace**. Two writers doing that concurrently produce last-writer-wins: the loser's rows vanish silently, or, if the replace interleaves with a read, a corrupt archive. There is no compare-and-swap primitive to build on.
- You *can* hand-roll a mutex (atomic exclusive-create of a `.lock` file via `O_EXCL`/`CREATE_NEW`, which SMB does honour), then handle stale-lock timeouts, retry storms, and SMB2 client-side caching. [OPINION] The moment you are writing that code you have decided to implement a database engine, badly, to avoid using a database. That is the wrong trade at any budget.

**A-case verdict: dead.** Either the file is unreachable from the app (A1), or the app lives on a laptop that is a compliance and availability liability (A2), and in both cases the write path has no concurrency primitive (A3).

---

## B. THE ONEDRIVE / SHAREPOINT + MICROSOFT GRAPH CASE (the serious version)

This is the only technically credible version of "Excel as backend", so it deserves the detail.

### B4. The Graph Workbook API — it exists, and what it can and cannot do

**It exists and it is a first-class API.** [DATA — learn.microsoft.com/en-us/graph/api/resources/excel]
- *"You can use Microsoft Graph to allow web and mobile applications to read and modify Excel workbooks stored in OneDrive for Business, SharePoint site or Group drive."*
- Full CRUD on worksheets, ranges, **tables** (`POST /workbook/tables/{id}/rows` to add a row — a genuine server-side append), columns, charts, named items, filters, sorts, and even workbook functions.
- **.xlsx only:** *"The Excel REST API supports only Office Open XML file formatted workbooks. The `.xls` extension workbooks aren't supported."*
- **Business tenants only:** *"Support for workbooks stored in OneDrive Consumer platform is still not available. At this time, only the files stored in business platform are supported by Excel REST APIs."* → a personal OneDrive is out; this requires a work tenant.

**Session model** [DATA — same page]:
- Three modes: persistent session (changes saved), non-persistent session (changes discarded on expiry), sessionless (one-off, inefficient).
- Session passed as `workbook-session-id` header.
- **Expiry:** *"Typically the persistent session expires after about 5 minutes of inactivity. Non persistent session expires after about 7 minutes of inactivity."* An expired session returns **404**, and the client must create a new one. [INFERENCE] For a web app with bursty traffic this means constant session churn plus a 404-retry code path that must not be mistaken for "file not found".
- Session creation is a documented long-running operation (`Prefer: respond-async`, poll every ~30s, *"maximum interval should be no more than 4 minutes"*) — i.e. opening a workbook can take minutes on the server side [DATA].

**Range/size ceilings** [DATA — same page]:
- *"If the range size exceeds the upper limitation (5M cells), some properties return null as the value."*
- Writing to an unbounded range (`A:B`) is *"not allowed"*.
- *"Large Range implies a Range of a size that is too large for a single API call... we recommend that you read or write for large Range in multiple smaller range sizes."*
- Underlying Excel worksheet limits still apply: **1,048,576 rows × 16,384 columns**, **32,767 characters per cell** [DATA — support.microsoft.com/en-us/office/excel-specifications-and-limits-1672b34d-7043-467e-8e27-269d656771c3]. The 32,767-char cell cap is a real constraint for free-text status punches, though generous.

**Throttling — Excel-specific** [DATA — learn.microsoft.com/en-us/graph/throttling-limits]:
| Scope | Limit |
|---|---|
| Excel, per app per tenant | **1,500 requests / 10 seconds** |
| Excel, per app across all tenants | **5,000 requests / 10 seconds** |
| Global Graph, per app all tenants | 130,000 requests / 10 seconds |

[INFERENCE] 1,500/10s is *not* the binding constraint for 50 users. The binding constraint is the next item.

**Concurrent writes are explicitly discouraged — this is the decisive quote** [DATA — learn.microsoft.com/en-us/graph/workbook-best-practice, §"Throttling and concurrency"]:
> *"We don't recommend increasing concurrency when using Excel APIs (for example, parallelizing the requests to the same workbook), especially for write requests. Instead... we recommend sequential usage in the most common case: for each workbook, only send the next request after receiving a successful response to the current request."*
>
> *"Concurrent write requests to the same workbook don't usually run in parallel (although in some cases they do); rather, they are often the cause of throttling, timeout (when requests are queued on servers), merge conflict (when concurrent sessions are involved) and other types of failures. They also complicate error handling; for example, when you receive a failure response, there is no way to confirm the status of other pending requests, which makes it difficult to determine or to recover the state of the workbook."*

Read that last sentence again in the context of a ticket system: **on a failed write you cannot determine whether the punch was recorded.** For an append-only status log that is meant to be evidence, "we don't know if it saved" is not an acceptable failure mode.

[INFERENCE] The engineering consequence: you must funnel every write in the entire application through a **single serialised queue** — one in-flight write per workbook, globally. That is buildable (a single-worker queue with a durable backlog), but you have now built a write-ahead log and a lock manager in front of a spreadsheet, and your durability guarantee is only as good as the queue, which itself needs storage… which is the database you were avoiding.

**Also documented on the Excel-Online-connector path** (Power Automate/Logic Apps/Power Apps, i.e. the "no-code Graph" route — the numbers are connector-specific, not raw Graph, and I am labelling them as such) [DATA — learn.microsoft.com/en-us/connectors/excelonlinebusiness/]:
- *"Simultaneous file modifications made by other connectors, or manual edits are not supported. Users should avoid writing data to a single Excel file from multiple clients concurrently (Excel Desktop, Excel Web, Power Automate, LogicApps or Power Apps). This can cause possible merge conflicts and data inconsistency."*
- *"An Excel file may be locked for an update or delete up to 6 minutes since the last use of the connector."* → six-minute write windows where the file is unavailable.
- *"Changes committed by operations such as Add a row, Update a row, Delete a row do not always take affect immediately after successful response... Delays up to 30 seconds are expected due to underlying backend service limitations."* → **read-after-write is not consistent.** A user punches a status, the dashboard refreshes, the punch is not there for up to 30 seconds. Users will punch again. You now have duplicates in your evidence log.
- *"The maximum size of an Excel file that is supported by the Excel Online (Business) connector is 25 MB."* and *"The maximum supported size of each connector request is 5 MB."*
- *"In the case of multiple matches in operations such as Update a row and Delete a row, only the first row will be updated/deleted."* → no primary keys, no uniqueness enforcement.
- *"A range is limited to five million cells."*; *"The key column field is case-sensitive."*; *"Pivot tables aren't supported due to Graph API limitations."*
- Connector throttling: **100 API calls per connection per 60 seconds**.
- And a quietly devastating one for audit purposes: *"An Excel file may be modified and a new version may be visible in Version history of the file even when a 'read-only' action is executed. This behavior is by design due to internal save mechanisms of the connector's backend service."* → your version history fills with spurious versions from reads, which both destroys its evidentiary value and burns through any version-count limit.

### B5. Does Microsoft steer developers away from workbook-as-database?

**Yes, though mostly by implication in the reference docs and explicitly in product guidance rather than as a single "do not do this" sentence.** Ranked by strength of evidence:

1. **Strongest and most binding** — the connector doc's flat statement that concurrent/multi-client writes to one workbook *"are not supported"* and cause *"merge conflicts and data inconsistency"* [DATA, quoted above]. That is Microsoft describing your exact architecture as unsupported.
2. **Graph best-practice** — the "don't parallelise, go sequential per workbook, failures leave state indeterminate" passage [DATA, quoted above].
3. **Microsoft's own Power Platform blog** on moving beyond Excel/SharePoint lists to Dataverse: Excel *"lacks granular security controls, making it difficult to enforce who can see or edit specific data"*, *"lacks enterprise-grade data protection, with no automatic backups or recovery"*, and has *"limited real-time multi-user collaboration, with permissions and synchronization issues"* [DATA — microsoft.com/en-us/power-platform/blog/2025/02/10/transforming-data-management-with-dataverse/]. Same page notes SharePoint lists' *"5,000-item threshold"* and lack of *"enforcement of referential integrity"*. This is Microsoft marketing Dataverse, so discount for motive — but the three Excel criticisms are exactly the three that matter here, and they are Microsoft's words.
4. [UNVERIFIED] I did **not** find a single canonical Microsoft Learn page titled to the effect of "do not use Excel as an application database". The widely-quoted line *"Excel is an excellent prototyping tool, but should never be used as the backend for a production app used by more than one person simultaneously"* surfaced in search results attributed loosely to Microsoft/Power Apps guidance but I could not confirm it on a microsoft.com URL. **Do not quote that sentence to the Principal as Microsoft's.** The three sources above are sufficient and are verified.

### B6. Permissions and consent — THE DECISIVE ITEM

**App registration itself: usually self-service.** *"By default in Microsoft Entra ID, all users can register applications and manage all aspects of applications they create. Everyone also has the ability to consent to apps accessing company data on their behalf."* An admin can turn this off via **Entra ID > Users > User settings > "Users can register applications" = No**, after which you get *"You don't have permission to register applications in the <directoryName> directory"* and need the **Application Developer** role granted to you [DATA — learn.microsoft.com/en-us/entra/identity/role-based-access-control/delegate-app-roles].

[OPINION] For a SEBI-regulated financial firm, the odds that "users can register applications" has been left at the permissive default are meaningfully below 100%, and the odds that "users can consent to apps" has been left permissive are lower still — restricting user consent is a standard hardening step. This must be *tested*, not assumed: try to open the App registrations blade and click New registration. That single click answers the question in 30 seconds.

**Consent requirements per scope** [DATA — learn.microsoft.com/en-us/graph/permissions-reference]:

| Permission | Type | Admin consent required |
|---|---|---|
| `Files.Read` | Delegated | **No** |
| `Files.ReadWrite` | Delegated | **No** |
| `Files.Read` (app) | Application | **Yes** |
| `Files.ReadWrite` (app) | Application | **Yes** |
| `Files.Read.All` | Application only | **Yes** |
| `Files.ReadWrite.All` | Application only | **Yes** |
| `Sites.Read.All` | Application only | **Yes** |
| `Sites.ReadWrite.All` | Application only | **Yes** |
| `Sites.Selected` | Application only | **Yes** |

**This table is the whole argument.** Two branches, both bad:

- **Branch (a): delegated `Files.ReadWrite`.** No admin consent. Every user signs in with their Microsoft work account and the app acts *as them*. Consequences: (i) the login model is no longer "email OTP to an allow-list" — it is Entra sign-in, i.e. you have SSO whether you wanted it or not, and the OTP design becomes pointless; (ii) **the workbook must be shared with all 10–50 users**, because the app can only touch files *that user* can access — so every user can open the ticket database in Excel and edit any row, which annihilates the audit trail (see D9); (iii) `Files.ReadWrite` delegated grants the app read/write to **that user's entire OneDrive**, not just your one file, on every sign-in — for a wealth manager, an APM-built app holding write access to every colleague's OneDrive is a serious finding waiting to happen [OPINION]; (iv) tokens expire, so background/scheduled work (reminders, deadline sweeps) has no identity to run as without a refresh-token-hoarding hack.
- **Branch (b): application (app-only) permissions.** The app holds its own identity, no user needs file access, audit trail preserved, background jobs work. Every single relevant scope says **Admin consent required: Yes**. `Sites.Selected` — the correctly-scoped, least-privilege option that limits the app to one SharePoint site — *also* requires admin consent, **plus** an admin/site-permission grant per site via Graph. So the least-privilege, most-compliant design is the one most dependent on IT.

There is no configuration that gives you app-only access without an administrator. [DATA, from the table above]

### B7. Co-authoring vs programmatic writes, and "conflicted copy"

- Co-authoring requires the file in OneDrive/SharePoint Online and formats `.xlsx`/`.xlsm`/`.xlsb`; *"co-authoring does not support the Strict Open XML Spreadsheet format"* [DATA — Microsoft co-authoring support page].
- The classic "locked" failure is a version mismatch: *"the most common one is because someone has opened the file with a version of Excel that doesn't support co-authoring. If just one person does this, then everyone else will get the 'locked' error"* [DATA — same page]. [INFERENCE] Read that against your app: **one user opening the ticket workbook in an old desktop Excel can lock out the entire application.** You cannot prevent this if the file is shared with users (Branch (a)).
- **Merge conflicts from concurrent programmatic writes are documented** — the connector page's *"possible merge conflicts and data inconsistency"* and the Graph best-practice page's *"merge conflict (when concurrent sessions are involved)"* [DATA, both quoted above].
- **On OneDrive "conflicted copy" files specifically:** these are produced by the OneDrive *sync client* reconciling divergent local and cloud versions. [INFERENCE] A pure server-side Graph write does not involve the sync client and so should not itself mint a `-conflicted copy` file; the realistic trigger is a user with the file synced locally editing it in desktop Excel while the app writes server-side. **[UNVERIFIED — I did not find a Microsoft doc that explicitly enumerates the conditions under which programmatic Graph writes generate conflict files. To confirm: sync the file locally, edit offline in Excel, write via Graph, reconnect, observe.]** The honest framing for the Principal is: Microsoft documents merge conflicts and data inconsistency as expected outcomes of exactly this pattern, and does not promise you which artefact you will get.

**B-case verdict: technically real, operationally hostile, and gated on an administrator you may not have.**

---

## C. THE GOOGLE WORKSPACE EQUIVALENT

### C8. Google Sheets API as an app backend

**Quotas** [DATA — developers.google.com/workspace/sheets/api/limits]:
| Metric | Limit |
|---|---|
| Read requests / minute / project | 300 |
| Read requests / minute / **user** / project | 60 |
| Write requests / minute / project | 300 |
| Write requests / minute / **user** / project | 60 |
Plus: *"Provided that you stay within the per-minute quotas, there's no limit to the number of requests that you can make per day."* Exceeding returns **429**. Max ~2 MB payload; 180-second per-request processing ceiling.

[INFERENCE] **The per-user quota is the trap.** If you use a *service account* to do all the writing (the normal server-side design), every write in the whole application is attributed to that one identity, so the effective app-wide write ceiling is **60 writes/minute**, not 300 — and the project ceiling of 300/min is the hard wall regardless. For 50 users doing occasional ticket punches this is genuinely adequate. It is *not* adequate for a dashboard that polls, or for any bulk import/migration, or for a retry storm. You must cache reads aggressively and batch writes.

**Size ceiling** [DATA — support.google.com/drive/answer/37603]: *"Up to 10 million cells or 18,278 columns (column ZZZ) for spreadsheets that are created in or converted to Google Sheets"* — and the 10M cells is the budget for the **whole spreadsheet across all tabs**, not per tab. Cells over 50,000 characters are dropped on Excel→Sheets conversion.

**Concurrency:** Google provides no transactions, no row-level locks, and no compare-and-swap on the Sheets API. `values.append` is a server-side append (reasonably safe for pure log-writes); any **read-modify-write** — e.g. "set ticket 47's status to Closed" — is a textbook lost-update race. The strongest evidence that Google expects you to solve this yourself is that Apps Script ships a **LockService** whose stated purpose is *"prevents concurrent access to sections of code... useful for managing shared resources and preventing collisions"*, including a script-wide lock that *"cannot be executed simultaneously regardless of the identity of the user"* [DATA — developers.google.com/apps-script/reference/lock]. A platform that needs an explicit mutex library for spreadsheet writes is telling you what it does not guarantee. [INFERENCE]

**Does Google document Sheets as suitable for an application database?** [UNVERIFIED] I found no official Google page either endorsing or prohibiting it. Third-party blogs claiming Google says "Sheets is not a database" did not survive checking — **do not attribute that to Google.** What *is* verified: the quota table above, the 10M-cell ceiling, and the existence of LockService. Draw the conclusion from those, not from a fabricated quote.

**If the frontend were an Apps Script web app** (a genuinely free, in-tenant, no-external-hosting option worth knowing about) [DATA — developers.google.com/apps-script/guides/services/quotas]: script runtime **6 min/execution**; simultaneous executions **30/user** and **1,000/script**; trigger total runtime **6 hr/day** (Workspace) vs 90 min/day (consumer); UrlFetch **100,000/day** (Workspace). [INFERENCE] Those numbers are compatible with a 10–50-person ticket app. The 6-minute execution cap kills long batch jobs but not CRUD.

**Auth — the same fork as Microsoft, differently shaped:**
- Google Workspace admins control app access centrally: *"Google Workspace administrators can use API access controls to enable or restrict access to Google Workspace APIs for customer-owned and third-party applications and service accounts"*, and can *"block apps, limit their access to certain services, or revoke access entirely, which renders associated refresh tokens invalid"* [DATA — developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace].
- For **internal** apps hitting restricted APIs, the admin must act: *"If you build internal apps (owned by your organization), you can trust all apps to access restricted Google Workspace APIs"* via a **"Trust internal apps" checkbox** in the Admin console [DATA — knowledge.workspace.google.com/admin/apps/control-which-third-party-and-internal-apps-access-google-workspace-data]. Apps can be set Trusted / Limited / Blocked.
- **Domain-wide delegation** (the mechanism that lets a service account act as users) is admin-only: *"it allows administrators to pre-authorize apps, bypassing user consent"* [DATA — same Google production-readiness page].
- **Service account without DWD:** you create a service account in a Google Cloud project and simply **share the sheet with its `…@….iam.gserviceaccount.com` address** like any other collaborator. This is the one genuinely admin-free-ish path — *but*: [INFERENCE, high confidence, **UNVERIFIED — needs a live test**] that address is **outside your Workspace domain**, so if the admin has restricted external sharing on Drive (standard hardening at a financial firm), the share will be blocked. Also [UNVERIFIED] whether users at this org can create Google Cloud projects at all — admins can restrict that too.
- Scope note [UNVERIFIED]: `https://www.googleapis.com/auth/spreadsheets` is generally treated as a *sensitive* (not *restricted*) scope, which affects verification requirements; I did not confirm its current classification on Google's scope-classification page. Check before relying on "no verification needed".

**C-case verdict: same two blockers, plus a tighter write ceiling (60/min effective) and a lower size ceiling (10M cells total).** The one advantage over Microsoft: the service-account-plus-share pattern *might* squeeze past without an admin, if external sharing is open. That is a coin flip on a setting you don't control, and it is still an editable spreadsheet (see D).

---

## D. THE COMPLIANCE ANGLE — where this actually dies

### D9. An editable spreadsheet as the system of record

**Can anyone with file access silently alter a past row? Yes.** [DATA/INFERENCE] If a user can open the workbook — which Branch (a) delegated auth *requires* — they can retype any historical status punch, change a deadline, or delete a row, using Excel, with no application-level record that they did so. "Append-only" is a property of your *code path*, not of the file. A file that any user can edit is not an append-only ledger; it is a mutable document with an app in front of it that politely only appends.

**Does version history mitigate it? Partially, and it is weaker than it looks:**
- **Granularity is per-file, not per-row.** [INFERENCE] SharePoint/OneDrive versions a whole workbook. To prove "who changed ticket 47's status on 14 July", you must download two adjacent versions of the entire file and diff them by hand. There is no per-row author/timestamp/before-after unless *you* write those columns yourself — and if the file is user-editable, those columns are forgeable too.
- **Ordinary users can delete versions.** Deleting a version requires only **Full Control or Contribute**; viewing requires Full Control, Contribute, or Read [DATA — support.microsoft.com/en-us/office/what-permissions-do-i-need-for-sharepoint-versioning-95bce34c-db77-4fd4-8449-9ad7ce0363c0]. **Contribute is what a normal editor has.** So in Branch (a), every user who can edit the file can also delete its version history — including the versions containing their own edit. That is not an audit trail; that is a self-service eraser.
- Mitigation exists but is admin-ish: create a custom permission level with **Delete Versions** removed. [DATA — this is standard SharePoint permission-level configuration, referenced in Microsoft Q&A guidance on preventing version-history deletion.] Note this is a **site-collection owner** action, not necessarily tenant admin — so it may be reachable without IT if the firm gives site ownership to the requester. [UNVERIFIED — depends on the firm's SharePoint governance.]
- **Version limits truncate history.** How far back you can go is bounded by the library's version-count setting; if the library keeps 20 versions, older states are gone. [DATA — Microsoft/SharePoint versioning guidance.] Combine with the connector behaviour *"a new version may be visible in Version history of the file even when a 'read-only' action is executed"* [DATA] and you get: **spurious read-generated versions burn through your version budget and evict the real evidence.**
- Recycle-bin retention is 93 days for deleted items [DATA — SharePoint retention behaviour]; the second-stage bin is reachable only by site collection admins/owners.
- Admins can purge history. A tenant/site admin can delete versions, files, and libraries. [INFERENCE] That is true of every system, but a real audit trail is *append-only to the actor*, and here the actor set that can erase includes ordinary Contribute users.

[OPINION] For a SEBI-regulated non-discretionary PMS, the specific failure mode that matters is: a client-related task, a missed deadline, a dispute, and an internal record whose history could have been edited by the very person whose conduct is in question, with no tamper-evidence. Whether or not this ticket system is *itself* a prescribed regulatory record, it will be pulled into any inspection or dispute that touches the workflows it tracks. **[UNVERIFIED — the exact SEBI record-preservation obligations (e.g. SEBI (Portfolio Managers) Regulations record-keeping and retention period, SEBI (Intermediaries) Regulations) should be confirmed with the compliance officer rather than assumed from memory. I have deliberately not stated a retention period or regulation number I could not verify.]** The defensible general principle, which needs no citation: *a system of record whose past rows are editable by its users, and whose change history is deletable by its users, has no audit trail.*

### D10. Row-level access control — is there any?

**No. None. And the protection features are cosmetic, on Microsoft's own account.**

- Microsoft states it plainly: **"Worksheet level protection is not intended as a security feature. It simply prevents users from modifying locked cells within the worksheet."** and *"Protecting a worksheet is not the same as protecting an Excel file or a workbook with a password."* [DATA — support.microsoft.com/en-us/excel/protect-a-worksheet]
- **An .xlsx is a ZIP of XML.** [INFERENCE, well established and trivially demonstrable] Sheet protection is an attribute in the sheet XML and workbook protection is an attribute in the workbook XML. Anyone who can read the file can rename it to `.zip`, delete the `<sheetProtection>` element, re-zip, and open it fully editable — no password cracking required, because the password only gates the *UI*, it does not encrypt anything. Hidden sheets, hidden columns, and "very hidden" sheets are likewise flags, not encryption. The only genuine cryptographic boundary in Excel is **file-level encryption** ("Encrypt with Password"), which is all-or-nothing: it locks *everyone* out, including your app, unless the app holds the password — at which point the password is in your code and protects nothing.
- **Therefore the only real security boundary is the file ACL** — per-file, never per-row. To give user A visibility of only their own tickets you would need one file per user (no manager dashboard, N-way sync, absurd) or the app as sole file-holder (Branch (b), which needs admin consent).
- Google Sheets is the same story: **protected ranges are editor-level conveniences, not confidentiality boundaries** [INFERENCE]; anyone with view access to the spreadsheet can read every tab's data via the API or by download. Sheets does not offer row-level read security.
- **Contrast, for the Principal's benefit:** SharePoint/Microsoft Lists *does* support item-level permissions and per-item version history natively — with the documented caveat that *"when a list, library, or folder contains more than 100,000 items, you can't break permissions inheritance"* [DATA — Microsoft list-limits guidance]. Lists hold up to **30 million items**, with a fixed **5,000-item list view threshold** that shapes how you query but not how much you can store [DATA — support.microsoft.com/en-us/sharepoint/lists/data-and-lists/list-view-threshold-for-large-lists-and-libraries; learn.microsoft.com SharePoint limits guidance].

---

## E. VERDICT

### Blockers that cannot be engineered around

1. **App-only Graph access requires an administrator. Every relevant scope is "Admin consent required: Yes"** — `Files.ReadWrite` (application), `Files.ReadWrite.All`, `Sites.ReadWrite.All`, and even least-privilege `Sites.Selected` [DATA]. No amount of clever code changes this. Google's equivalents (Trust internal apps for restricted scopes; domain-wide delegation) are likewise admin-gated [DATA].
2. **The admin-free alternative (delegated auth) requires giving all 10–50 users direct file access, which destroys the audit trail** — because users with Contribute can edit any historical row *and* delete the version history that would prove it [DATA]. The two branches are mutually exclusive: you can have no-IT-dependency **or** an audit trail, never both.
3. **No row-level access control exists, and sheet/workbook protection is explicitly not a security feature** per Microsoft [DATA]; an .xlsx is a ZIP whose protection flags can be stripped [INFERENCE]. A wealth manager's internal ticket data (which will inevitably name clients) has no confidentiality boundary finer than the whole file.
4. **Concurrent writes to one workbook are documented as unsupported and as producing merge conflicts and data inconsistency; and on failure "there is no way to confirm the status of other pending requests"** [DATA]. You can serialise writes to dodge this, but you cannot make a failed write tell you whether it landed — unacceptable for an evidentiary append-only log.
5. **Read-after-write is not consistent** (up to 30-second propagation on the documented connector path; file lockouts up to 6 minutes) [DATA]. Users will double-punch. Duplicates in the ledger are a data-integrity problem you cannot suppress from the client.
6. **For the network-share variant specifically: there is no route from a public-internet app to a private LAN path, no atomic append, and no row-level lock** — and the only fixes are an always-on unmanaged machine plus an unmanaged ingress tunnel, which is a worse compliance posture than what it replaces [DATA + OPINION].

### Conditions under which a shared workbook WOULD be fine

I want to be fair — this is not "spreadsheets are bad". A workbook backend is genuinely appropriate when **all** of these hold:
- **Single writer.** One process, or one person, writes. Many readers is fine.
- **Writes are appends only, low frequency** (order of a few per minute, not per second), and **no read-modify-write** of existing rows.
- **Everyone who can see the file is allowed to see all of it** — no row-level confidentiality requirement.
- **The workbook is not the system of record**, or the record is not evidentiary. Reporting layer, cache, export target, config file, scratch log: all fine. Ledger of who-did-what-when for a regulated firm: not fine.
- **Rows in the low tens of thousands**, well clear of 5M cells per range / 10M cells per Google spreadsheet / 25 MB connector ceiling.
- **Nobody opens it in desktop Excel while the app is running.**
- **A human is the frontend** (Excel itself, or Power BI reading it) rather than a multi-user web app.

Concretely for this project: a workbook is a perfectly good **weekly export / management reporting artefact** produced *from* the real store. It is a bad **store**.

### The honest alternative that keeps the Principal's actual requirement

His requirement was never "Excel". It was *"our data, our tenant, no third-party free tier, zero rupees, proper website frontend."* All four survive if the object changes:

- **SharePoint / Microsoft List in the company tenant** (if M365). Same drive, same tenant, already licensed, ₹0. Gives you what the workbook cannot: **per-item version history**, **item-level permissions**, 30M-item capacity, real columns and types, and a REST/Graph surface designed for concurrent multi-user writes rather than one documented as not supporting them. Caveats to be honest about: the 5,000-item **list view threshold** shapes queries [DATA], breaking permission inheritance is blocked above 100,000 items [DATA], and a *custom* web frontend against it still needs the same app registration and, for app-only access, the same admin consent [DATA]. **What changes is that the no-admin fallback becomes acceptable:** with delegated auth against a List, users editing directly is survivable because the List versions every item and can be locked down per item — whereas with a workbook, the same fallback is fatal.
- **The zero-friction version:** the built-in Lists/SharePoint UI plus a Power Automate reminder flow is a working ticket system with deadlines, assignees, append-only comment history, and a manager view, with no code and no app registration at all. It is not the bespoke website he asked for, but it is a real website, and it is a two-day build that buys time to do the custom frontend properly.
- **If the tenant turns out to be Google Workspace:** the analogous move is AppSheet or a proper datastore, not a Sheet — but the admin dependency is the same, so establish which tenant exists before designing anything.

### The three things to check before any further design (each is minutes, not days)

1. **Which email platform / tenant is it?** Everything above forks on M365 vs Google Workspace vs plain hosting. Currently unknown, and it is the root of the dependency tree.
2. **Open Entra "App registrations" and click "New registration".** If it succeeds, self-service app registration is on. If you get *"You don't have permission to register applications in the <directoryName> directory"*, IT is required for **any** custom-frontend option, workbook or List, and that reframes the whole project.
3. **Ask IT one narrow question** rather than a broad one: *"can we have a SharePoint site and an app registration with `Sites.Selected` scoped to just that one site?"* That is the least-privilege ask, it is small, it is easy for a security-conscious admin to say yes to, and it unlocks the good architecture. It is a far better first request than "please grant `Files.ReadWrite.All`", which any competent admin will refuse.

---

## SOURCES (all verified by direct fetch unless marked)

- Microsoft Graph Excel/Workbook API reference — https://learn.microsoft.com/en-us/graph/api/resources/excel
- Excel API best practices (concurrency, sessions, throttling) — https://learn.microsoft.com/en-us/graph/workbook-best-practice
- Microsoft Graph throttling limits — https://learn.microsoft.com/en-us/graph/throttling-limits
- Microsoft Graph permissions reference (admin-consent table) — https://learn.microsoft.com/en-us/graph/permissions-reference
- Entra ID: delegate app management / "Users can register applications" — https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/delegate-app-roles
- Excel Online (Business) connector: known issues, limits, concurrency warning — https://learn.microsoft.com/en-us/connectors/excelonlinebusiness/
- Excel co-authoring requirements — https://support.microsoft.com/en-us/office/collaborate-on-excel-workbooks-at-the-same-time-with-co-authoring-7152aa8b-b791-414c-a3bb-3024e46fb104
- "Worksheet level protection is not intended as a security feature" — https://support.microsoft.com/en-us/excel/protect-a-worksheet
- Excel specifications and limits (1,048,576 rows; 32,767 chars/cell) — https://support.microsoft.com/en-us/office/excel-specifications-and-limits-1672b34d-7043-467e-8e27-269d656771c3
- SharePoint versioning permissions (Contribute can Delete Versions) — https://support.microsoft.com/en-us/office/what-permissions-do-i-need-for-sharepoint-versioning-95bce34c-db77-4fd4-8449-9ad7ce0363c0
- Document locked for editing / owner (~$) files — https://support.microsoft.com/en-us/topic/-the-document-is-locked-for-editing-by-another-user-error-message-when-you-try-to-open-a-document-in-word-10b92aeb-2e23-25e0-9110-370af6edb638
- SharePoint list view threshold — https://support.microsoft.com/en-us/sharepoint/lists/data-and-lists/list-view-threshold-for-large-lists-and-libraries
- Microsoft Power Platform blog, Excel/SharePoint limitations vs Dataverse — https://www.microsoft.com/en-us/power-platform/blog/2025/02/10/transforming-data-management-with-dataverse/
- Google Sheets API usage limits — https://developers.google.com/workspace/sheets/api/limits
- Google Drive/Sheets file size limits (10M cells) — https://support.google.com/drive/answer/37603
- Apps Script quotas — https://developers.google.com/apps-script/guides/services/quotas
- Apps Script LockService — https://developers.google.com/apps-script/reference/lock
- Google Workspace OAuth production readiness (admin API controls, DWD) — https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace
- Controlling third-party & internal app access (Trust internal apps) — https://knowledge.workspace.google.com/admin/apps/control-which-third-party-and-internal-apps-access-google-workspace-data
- Cloudflare Workers VPC / Tunnel for private-network access — https://developers.cloudflare.com/workers-vpc/configuration/tunnel/
