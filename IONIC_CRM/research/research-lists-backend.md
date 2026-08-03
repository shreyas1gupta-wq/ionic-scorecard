# Dimension: Microsoft Lists / SharePoint List (or Google equivalent) as the real datastore behind a custom Next.js frontend

Research date: 2026-08-03. All vendor limits quoted from the vendor's own current docs pages (URLs inline).
Tags: **[DATA]** = verified against a named primary source. **[INFERENCE]** = my reasoning from cited facts. **[OPINION]** = judgement. **[UNVERIFIED]** = cannot confirm; states what to check.

---

## 0. Verdict in one paragraph

The Principal's instinct is half right and half wrong. He is right that a shared `.xlsx` is the wrong vehicle and that a SharePoint List is a genuinely better one — a List is a real backing store with typed columns, per-item version history, per-item ETag optimistic concurrency, item-level permissions, and a first-class REST API (Microsoft Graph) with delta sync. It is included at no extra cost in every standard M365 plan, and for an India-signup M365 tenant the data sits under Microsoft's contractual data-residency commitment. **But the route is not IT-free.** In a default-configured modern Entra tenant, Microsoft's own managed user-consent policy explicitly excludes `Sites.Read.All` and `Sites.ReadWrite.All` from what an ordinary employee may consent to. That means a normal user cannot self-serve a Graph app that reads/writes a SharePoint List. `Sites.Selected` — the least-privilege option — is *worse* for self-service, not better, because the second step (granting the app access to the specific site) requires `Sites.FullControl.All` or SharePoint-admin PowerShell. And the old self-serve escape hatch (SharePoint Add-in registration via `appregnew.aspx` + Azure ACS) stops working 2 April 2026. So: architecturally excellent, operationally gated on one IT ticket.

---

## 1. Is a SharePoint List a viable application datastore?

### 1.1 It is the same platform as "Microsoft Lists"
[DATA] Microsoft's SharePoint limits page, describing the 250 MB attachment limit: *"250 MB - File attached to a list item. Applies to Microsoft Lists and SharePoint lists - both based on same lists platform."*
Source: https://learn.microsoft.com/en-us/office365/servicedescriptions/sharepoint-online-service-description/sharepoint-online-limits
[INFERENCE] "Microsoft Lists" is a front-end experience over SharePoint lists. Anything true of SharePoint lists (licensing, Graph API, audit, retention) is true of Microsoft Lists. There is no separate "Lists database" to reason about.

### 1.2 Column types — real types, not spreadsheet cells
[DATA] Documented column types: Single line of text (255 chars), Multiple lines of text (63,999 chars), Number, Currency, Date and Time, Choice (dropdown/radio, optional fill-in), Yes/No, Person or Group (directory-backed), Lookup (references another list on the site), Hyperlink, Image, Calculated, Managed Metadata, Location. Validation includes max character count, min/max for numbers, default values.
Source: https://support.microsoft.com/en-us/office/list-and-library-column-types-and-options-0d8ddb7b-7dc7-414d-a283-ee9dca891df7
[OPINION] For a ticket CRM this is sufficient and actually *better* than a spreadsheet: `Person or Group` gives you a real assignee tied to Entra identity (no typo'd email strings), `Choice` gives you an enforced status enum, `Lookup` gives you referential linkage from a Status-Update item back to its Ticket item.

### 1.3 Concurrency — real optimistic concurrency, per item
[DATA] `PATCH /sites/{site-id}/lists/{list-id}/items/{item-id}` supports an `if-match` header: *"`etag`. If this request header is included and the eTag provided doesn't match the current eTag on the item, a `412 Precondition Failed` response is returned and the item will not be updated."*
Source: https://learn.microsoft.com/en-us/graph/api/listitem-update?view=graph-rest-1.0
[DATA] `listItem` exposes `eTag` as a read-only inherited property.
Source: https://learn.microsoft.com/en-us/graph/api/resources/listitem?view=graph-rest-1.0
[INFERENCE] **This is the single biggest architectural difference from a shared workbook.** Two people punching updates on two different tickets never contend; two people editing the same ticket produce a clean 412 you can surface as "someone changed this, reload". A shared `.xlsx` has no per-row concurrency primitive at all — the unit of contention is the whole file.

### 1.4 Version history — per item, deep
[DATA] `listItem` has a `versions` relationship returning a `listItemVersion` collection: *"The list of previous versions of the list item."* It also carries `createdBy`, `createdDateTime`, `lastModifiedBy`, `lastModifiedDateTime` as read-only server-set properties.
Source: https://learn.microsoft.com/en-us/graph/api/resources/listitem?view=graph-rest-1.0
[DATA] Version ceiling: *"50,000 major versions and 511 minor versions."*
Source: SharePoint limits page (above)
[INFERENCE] For an append-only "punch" model you do not actually need versioning of the ticket row — you write each punch as its own immutable item in an Updates list. But versioning is a free second line of defence: if someone does edit a ticket row, the prior value and the identity that changed it are retained server-side and are not deletable through the normal API surface.

### 1.5 Item-level permissions — and their real limits
[DATA] The setting lives at List Settings → Advanced Settings → Item-level Permissions, with a Read access group ("Read all items" / "Read items that were created by the user") and a Create-and-Edit group ("Create and edit all items" / "Create items and edit items that were created by the user").
Source (Microsoft Q&A, Microsoft-hosted but community-authored): https://learn.microsoft.com/en-us/answers/questions/2149614/item-level-permission-when-create-items-and-edit-i
[UNVERIFIED] I could not locate a first-party Microsoft *documentation* page (as opposed to Q&A) that specifies this setting's exact semantics. To verify: open any list's Advanced Settings in the tenant and read the in-product labels.

Documented limitations, all of which matter:
- [DATA] The setting only binds users at Contribute/Edit level. Users holding **Design** or **Full Control** see everything, because those levels include the *Override list behaviors* permission. A custom permission level that includes "Override list behaviors" also bypasses it.
  Source: https://learn.microsoft.com/en-us/answers/questions/1186814/ (and corroborated across SharePoint Diary / SharePoint Maven)
- [DATA] Breaking inheritance to make per-item ACLs is capped: *"The supported limit of unique permissions for items in a list or library is 50,000. However, the recommended general limit is 5,000."* And: *"When a list, library, or folder contains more than 100,000 items, you can't break permissions inheritance on the list, library, or folder."*
  Source: SharePoint limits page (above)
- [DATA] Assigning app permissions at list/item level *breaks inheritance*: *"Assigning application permissions to lists, list items, folders, or files breaks inheritance on the assigned resource, so be mindful of service limits for unique permissions."* Site-collection-level grants do not break inheritance.
  Source: https://learn.microsoft.com/en-us/graph/permissions-selected-overview
- [DATA] Reported operational stickiness: reverting item-level permissions back to default does not reliably restore visibility for Edit/Contribute users.
  Source: https://techcommunity.microsoft.com/discussions/sharepoint_general/item-level-permissions-stuck/3653199
- [INFERENCE, important] **If your custom frontend authenticates app-only, SharePoint's item-level permissions do nothing for you.** The app identity's role (read/write/owner/fullcontrol) is what is evaluated; your Next.js API routes become the sole authorization layer. Item-level permissions only bite in the delegated case, where *"both the application and user permissions are calculated and then intersected"* (Selected-permissions doc, above). Decide which model you want before you design authorization — do not assume SharePoint will enforce "assignee sees only their tickets" for you.

### 1.6 The 5,000 list view threshold — what actually breaks
[DATA] *"The number of items in this list exceeds the list view threshold, which is 5000 items. Tasks that cause excessive server load (such as those involving all list items) are currently prohibited."* … *"SharePoint Online uses the Large List Resource Throttling feature. By default, the list view threshold is configured at 5,000 items."*
Source: https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/items-exceeds-list-view-threshold
[DATA] It is a **per-operation** limit, not a storage limit: *"Specifies the maximum number of list or library items that a database operation, such as a query, can process at one time."* Filtered views on indexed columns return compliant subsets. The developer override to 20,000 exists only in SharePoint Server, **not** in SharePoint Online, where 5,000 cannot be changed.
Source: https://support.microsoft.com/en-us/office/manage-large-lists-and-libraries-b8588dae-9387-48c2-9248-c24122f07c59
[DATA] Yes, it affects programmatic access too — the same throttle governs queries regardless of client.
Source: same page
[DATA] Max items: *"A list can have up to 30 million items and a library can have up to 30 million files and folders."*
Source: SharePoint limits page (above)
[INFERENCE] For 10–50 employees this is a non-issue for years — but only if you build correctly from day one: index the columns you filter on (status, assignee, deadline), never issue an unfiltered "give me everything" query, and always page. A naive `GET /items?expand=fields` with no filter on a 6,000-item Updates list will start failing, and it will fail *later*, in production, which is the worst time.

### 1.7 Other structural limits worth knowing
[DATA] 2,000 lists and libraries combined per site collection; 2 million users per site collection; 25 TB max per site; 1,000 GB site metadata.
Source: SharePoint limits page (above)

### 1.8 Filtering/indexing via Graph — a real constraint
[DATA] *"You can apply the `$filter` (`eq`, `ne`, `lt`, `gt`, `le`, `ge`, and `startswith`) query parameter … Both **listItem** properties and fields can be filtered. When filtering on indexed fields, the service can only filter one indexed field at a time."* And: *"Note: Filtering works best on indexed columns."*
Source: https://learn.microsoft.com/en-us/graph/api/listitem-list?view=graph-rest-1.0
[DATA] The documented optional query parameters for listing items are `$filter` and `$expand` only. `$orderby` is **not** documented as supported for this method.
Source: same page
[INFERENCE] Consequences for a ticket dashboard: (a) you cannot compose a multi-condition indexed filter server-side — "open AND overdue AND assigned to me" must become one indexed predicate plus client-side narrowing; (b) sorting by deadline must be done in your app after fetch, or by pre-creating a SharePoint view; (c) "no SQL" is real — this is a single-table key-value-ish store with one-field indexed lookups, not a query engine.

---

## 2. Graph API for Lists — endpoints, throttling, batching, delta

### 2.1 Endpoints (all v1.0, GA)
[DATA] From the Graph `listItem` resource page:
- List items: `GET /sites/{site-id}/lists/{list-id}/items` (`?expand=fields(select=Col1,Col2)`)
- Get item: `GET .../items/{item-id}`
- Create: `POST .../items`
- Update fields: `PATCH .../items/{item-id}/fields`
- Delete: `DELETE .../items/{item-id}`
- Versions: `GET .../items/{item-id}/versions`
- Item permissions: `GET`/`POST .../items/{item-id}/permissions`
- Delta: `GET /sites/{siteId}/lists/{listId}/items/delta`
Sources: https://learn.microsoft.com/en-us/graph/api/resources/listitem?view=graph-rest-1.0 and https://learn.microsoft.com/en-us/graph/api/listitem-delta?view=graph-rest-1.0

### 2.2 Delta sync is supported and cheap
[DATA] `listItem: delta` is in v1.0. It returns `@odata.nextLink` pages then an `@odata.deltaLink` token; `?token=latest` gets a token without enumerating. Least-privileged permissions: `Sites.Read.All` (delegated and application). It emits `deleted` markers, and can return `410 Gone` with `resyncChangesApplyDifferences` / `resyncChangesUploadDifferences` requiring a full re-enumeration.
Source: https://learn.microsoft.com/en-us/graph/api/listitem-delta?view=graph-rest-1.0
[DATA] Delta is the cheapest read pattern: *"To help applications that follow the guidance, we lower the resource unit cost of delta requests with a token to 1 resource unit, although it's a multi-item query."*
Source: https://learn.microsoft.com/en-us/sharepoint/dev/general-development/how-to-avoid-getting-throttled-or-blocked-in-sharepoint-online

### 2.3 Throttling — actual published numbers
[DATA] SharePoint expresses limits in **resource units** (RU), with per-request cost: 1 RU = single-item query / delta-with-token / file download; 2 RU = multi-item query, **create, update, delete**, upload; 5 RU = any permission-resource operation including `$expand=permissions`.

Per-app-per-tenant (a tenant with 0–1,000 licences — which covers 10–50 employees):
| Scope | Window | Limit |
|---|---|---|
| Per app per tenant, Resource Units | 1 min | **1,250** |
| Per app per tenant, Resource Units | 24 h | **1,200,000** |
| Per app per tenant, Ingress / Egress | 1 h | 400 GB each |
| Tenant, Resource Units (all apps) | 5 min | 18,750 |
| Per user, Requests | 5 min | 3,000 |
| Per user, Delegation Token Request | 5 min | 50 |

Source: https://learn.microsoft.com/en-us/sharepoint/dev/general-development/how-to-avoid-getting-throttled-or-blocked-in-sharepoint-online
[DATA] Same page: *"you can estimate the request rate using an average of 2 resource units per request, and divide resource unit limits by 2 to get the estimated request rate."* Also: *"In batching, requests in a batch are evaluated individually by resource units"* (batching saves round trips, not quota). Also: *"multiple applications running against the same tenant share the same resource bucket."* Also: on 429/503 a `Retry-After` header is returned, and *"Throttled requests count towards usage limits, so failure to honor `Retry-After` may result in more throttling."* `RateLimit-Limit/Remaining/Reset` headers are returned in **beta**, best-effort, only when the app has consumed ≥80% of its 1-minute limit.
[DATA] Microsoft explicitly warns: *"Displayed limits are default values. Microsoft may change these limits at any time."* and *"Microsoft Reserves the right to lower limits on Unpaid/Unlicensed usage."*

[INFERENCE] Capacity arithmetic for this app: 1,250 RU/min ≈ 625 writes/min or 1,250 single-item reads/min; 1,200,000 RU/day ≈ 600,000 writes/day. For 50 employees punching, say, 10 updates a day each (500 writes/day) plus dashboard polling, you are using **well under 1%** of the daily budget. Throttling is not a capacity risk here. It *is* a risk if you write a naive dashboard that polls every ticket every 5 seconds for every open browser tab — that is how small apps get 429'd. Use delta + caching.

### 2.4 Lists vs the Excel/Workbook endpoints — is Lists meaningfully more robust?
[DATA] Graph's own service-specific throttling page gives Excel: *"Any: 5,000 requests per 10 seconds (per app for all tenants) / 1,500 requests per 10 seconds (per app per tenant)"*, and for SharePoint/OneDrive it does not enumerate limits at all, deferring to the SharePoint page.
Source: https://learn.microsoft.com/en-us/graph/throttling-limits
[INFERENCE — and this is where I disagree with the naive framing of the hypothesis] **On raw throttling numbers, the Excel endpoint is nominally more generous** (1,500 req/10s = 9,000/min per app per tenant) than SharePoint's ~625 writes/min. So "Lists is more robust because the API limits are higher" is **false**. Lists is more robust for four other reasons, all cited above:
1. Per-item ETag/`If-Match` concurrency (§1.3) — a workbook has no per-row concurrency primitive.
2. Server-set, non-forgeable `createdBy`/`lastModifiedBy` + per-item `versions` (§1.4) — a workbook cell has no author.
3. Item-level permissions and per-item permission APIs (§1.5) — a workbook is all-or-nothing at file level.
4. `delta` change feed with tokens and tombstones (§2.2) — there is no equivalent for workbook rows.
State it that way. Do not claim a throughput advantage that the docs contradict.

---

## 3. The IT dependency, precisely — and can a non-admin self-serve?

### 3.1 Step 1, app registration: usually yes, self-serve
[DATA] *"By default in Microsoft Entra ID, all users can register applications and manage all aspects of applications they create. Everyone also has the ability to consent to apps accessing company data on their behalf."* An admin can turn this off via Entra ID → Users → User settings → **Users can register applications = No**, in which case the user sees *"You don't have permission to register applications in the <directoryName> directory."*
Source: https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/delegate-app-roles
[UNVERIFIED for Ionic] Whether `Users can register applications` is still `Yes` in Ionic's tenant. **Check:** open https://entra.microsoft.com → App registrations → New registration. If it errors, IT is required at step 1 already. This is a 60-second test the Principal can run himself.

### 3.2 Step 2, consent to a Sites scope: **no, this is the blocker**
[DATA] Permission flags (from the Graph metadata-derived reference): `Sites.ReadWrite.All` — **delegated: admin consent NOT required; application: admin consent required**. `Sites.Selected` — **delegated: admin consent NOT required; application: admin consent required**.
Sources: https://graphpermissions.merill.net/permission/Sites.ReadWrite.All , https://graphpermissions.merill.net/permission/Sites.Selected (third-party site generated from Microsoft Graph service-principal metadata; treat the flag values as reliable but verify in the tenant's own consent screen)

[DATA — decisive] That flag is *not* the operative constraint, because Entra's tenant-wide user-consent policy overrides it. Microsoft's own page on app consent policies:
> *"The setting labeled 'Let Microsoft manage your consent settings,' the Microsoft managed policy, will update with Microsoft's latest recommended default consent settings. **This is also the default for a new tenant.** The setting's rules are currently: End users can consent for any user consentable delegated permissions EXCEPT: For Microsoft Graph: `Files.Read.All`, `Files.ReadWrite.All`, **`Sites.Read.All`, `Sites.ReadWrite.All`**, `Mail.Read`, …"*
Source: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-app-consent-policies
[INFERENCE] So in a default-configured modern tenant, an employee signing into his own app **cannot** grant it `Sites.ReadWrite.All` or even `Sites.Read.All` on his own behalf. He gets the "Need admin approval" screen. The only tenants where self-consent would work are ones still explicitly set to the legacy policy `microsoft-user-default-legacy` ("Allow user consent for apps … any permission that doesn't require admin consent").
[DATA] The built-in policy alternatives are `microsoft-user-default-low` ("only for permissions that you classify as *low impact*") and `microsoft-user-default-legacy`.
Source: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent
[UNVERIFIED for Ionic] Which consent policy Ionic's tenant uses. **Check:** build the app, hit the consent screen once. If it says "Need admin approval", you have your answer definitively, at zero cost.

### 3.3 `Sites.Selected` is least-privilege but *more* admin-dependent, not less
[DATA] Three steps are all mandatory: *"1. The application must be consented in Entra ID … 2. The application must be granted permissions to a list via a call to `POST /sites/{siteid}/lists/{listid}/permissions` with a specific role. 3. The application must acquire a valid token that contains the … scope … If any of the three steps are missed, the application doesn't have access."*
Source: https://learn.microsoft.com/en-us/graph/permissions-selected-overview
[DATA] Step 2 itself requires elevated permissions. Microsoft's table of "What permissions do I need to manage permissions?":
| Resource | Required resource permissions |
|---|---|
| site | `Sites.FullControl.All` (*"Because you can grant full control permissions to a site collection by using Sites.Selected, this requirement is necessarily high."*) |
| list | `Sites.FullControl.All`, `Sites.Selected`+FullControl, `Sites.Selected`+Owner |
Source: same page
[DATA] Roles assignable to an app: `read`, `write`, `owner`, `fullcontrol`. Admin retains two kill switches: `DELETE /sites/{id}/lists/{id}/permissions/{id}`, or revoke the scope in Entra.
Source: same page
[DATA] Search corroboration: *"Only Privileged Role Administrator and Global Administrator can consent to application permissions."* and *"By default, an app with Sites.Selected has no access to any site until an admin explicitly grants permissions for specific sites using SharePoint PowerShell."*
Source: https://learn.microsoft.com/en-us/graph/permissions-overview (via search summary), https://practical365.com/restrict-app-access-to-sharepoint-sites/
[DATA] Caution if you mix scopes: broader scopes present in the same token defeat the point — *"Higher-level scopes such as Sites.\* can be used to grant file-specific permissions, but lower scopes can never provide access to higher-level resources."* Community reporting is blunter: including `Sites.ReadWrite.All` alongside `Sites.Selected` makes `Sites.Selected` ineffective as a restriction.
Sources: permissions-selected-overview (above); https://learn.microsoft.com/en-us/answers/questions/5621045/

[INFERENCE] `Sites.Selected` + `write` on **one dedicated site**, app-only, is the correct security posture and the one to *ask IT for*. It is not a way to avoid asking.

### 3.4 The old self-serve loophole is closing
[DATA] *"Azure ACS for SharePoint Online has been retired as of November 27th, 2023 and will stop working from April 2nd, 2026"*; the SharePoint Add-In model retires **2 April 2026**; apps registered via `appregnew.aspx` and permissioned via `appinv.aspx` use ACS and *"will no longer function after the April 2, 2026 deadline"*; migration path is Entra ID app registration with a certificate.
Sources: https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/add-ins-and-azure-acs-retirements-faq , https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/retirement-announcement-for-azure-acs
[INFERENCE] Historically a *site owner* could mint app-only client-id/secret from within SharePoint without touching Entra. That door is shut ~4 months from now (as of Aug 2026 it is already past — see note). **Do not design around it.**
[UNVERIFIED] Today's date is 2026-08-03, i.e. **after** the stated 2 April 2026 cut-off. The docs pages fetched still describe the retirement in future/announced tense; I could not confirm from a current status page whether enforcement has fully landed. Either way the conclusion is the same: Entra app registration is the only supported route.

### 3.5 Bottom line on IT
[INFERENCE] **This route is not possible without IT in a normally-configured tenant.** The single ask is small and defensible, and can be written as a one-paragraph ticket:
> "Please register an Entra app `IonicTickets`, app-only, with Graph application permission `Sites.Selected` (not `Sites.ReadWrite.All`), grant admin consent, then grant that app the `write` role on exactly one site — `https://<tenant>.sharepoint.com/sites/IonicTickets` — via `POST /sites/{id}/permissions`. Issue a certificate (preferred) or client secret with a documented expiry. Access is revocable at any time by deleting the site permission."
That is one ticket, one site, revocable, least-privilege, auditable. [OPINION] An IT team that would refuse *that* would also refuse every other option except "use the spreadsheet", so it is a good early test of whether the whole project is viable inside the M365 tenant at all.

---

## 4. Licensing — what is genuinely free

### 4.1 Microsoft Lists / SharePoint lists: included, ₹0 extra
[DATA] SharePoint Online is *"Included in Microsoft 365/Office 365: Yes"* for Microsoft 365 Business (Basic, Standard, Premium), Microsoft 365 Enterprise (E3/E5), Office 365 (E1/E3/E5), and F1/F3.
Source: https://learn.microsoft.com/en-us/office365/servicedescriptions/sharepoint-online-service-description/sharepoint-online-limits
[DATA] Lists and SharePoint lists are *"both based on same lists platform"* (same page).
[INFERENCE] Therefore Lists carries no incremental licence cost on any plan the firm plausibly holds. Storage is drawn from the tenant pool (1 TB + 10 GB/licence); a ticket list's metadata footprint is negligible.
[UNVERIFIED] I could not find a first-party page that says in words "Microsoft Lists is included in Business Basic / E1 at no extra cost". The inference from the SharePoint service description is strong but it is an inference. Search results asserting per-plan Lists inclusion were third-party blogs and are not citable.

### 4.2 Microsoft Graph API access: ₹0
[INFERENCE] Graph carries no licence fee; usage is governed by throttling (§2.3), not billing. Nothing in the SharePoint throttling doc references paid tiers other than the caveat that Microsoft *"Reserves the right to lower limits on Unpaid/Unlicensed usage."*

### 4.3 Power Automate for reminder emails: free with standard connectors, and enough
[DATA] Power Automate request limits by licence: **Office 365 = 6,000 Power Platform Requests per user per 24 h** (official limit), with a more generous 10,000 per cloud flow during the current transition period. Compare Power Automate Premium at 40,000/user.
Source: https://learn.microsoft.com/en-us/power-platform/admin/api-request-limits-allocations
[DATA] Same page: *"Paid licensed users for Power Apps per app, **Microsoft 365 apps with Power Platform access** … 6,000"* requests/24 h. And: every action counts — *"Both successful and failed actions count toward these limits. Retries and requests from pagination also count."*
[DATA, weaker source] SharePoint, Outlook, Teams, Excel Online, OneDrive, Planner are **standard** connectors, included with any M365/O365 subscription; premium territory begins with Dataverse, SQL Server, Salesforce, ServiceNow, SAP, and **the HTTP connector for custom REST calls**. One premium connector makes the whole flow premium and requires a per-user or per-app licence for every user of the flow.
Source: search synthesis of https://www.spguides.com/standard-vs-premium-connectors-in-power-apps/ , https://microsoftnegotiations.com/blog/microsoft-power-platform-premium-connectors-licensing , https://comcomponent.com/en/blog/power-automate-license-connector-guide/ — **[UNVERIFIED against first-party docs]**. To verify: https://learn.microsoft.com/en-us/connectors/connector-reference/connector-reference-premium-connectors (authoritative premium list) and the Power Platform Licensing Guide PDF (https://go.microsoft.com/fwlink/?linkid=2085130).
[INFERENCE] A deadline-reminder flow that reads a SharePoint list on a schedule and sends Outlook mail uses **only standard connectors** → free. Budget arithmetic: a daily 8 a.m. flow scanning 300 open tickets and sending ~20 reminder mails is on the order of a few hundred actions/day — comfortably inside 6,000. **The trap to avoid is the HTTP connector**: if you reach for "HTTP" to call your own Next.js API from a flow, you have just made the flow premium and paid. Use the SharePoint + Outlook connectors only.
[OPINION] Better still: do reminders from your own app (a cron/scheduled job hitting Graph `sendMail` or an SMTP relay) and keep Power Automate out of the critical path entirely. It removes a licensing surface and a second thing that can break.

---

## 5. Auth synergy — does Entra sign-in kill the OTP requirement?

[INFERENCE] Yes, entirely, **if** the tenant is M365. MSAL sign-in with Entra ID gives you: identity you did not invent, MFA/Conditional Access enforced by the firm's existing policy, group-based role assignment (Managers group → admin dashboard), automatic revocation on offboarding (disable the account and access dies), and zero credential storage on your side. A custom email-OTP flow gives you none of that and creates an authentication system a SEBI-regulated firm's auditor will ask about. **Entra sign-in is strictly better than email-OTP on both security and compliance posture, and it is free.**

[DATA] The scopes an interactive sign-in needs (`openid`, `profile`, `email`, `offline_access`, `User.Read`) are not on the Microsoft-managed exclusion list quoted in §3.2 — that list covers `Sites.*`, `Files.*`, `Mail.*`, `Calendars.*`, `Chat.*`, `Tasks.*`, `Contacts.*`, `People.Read`, and the Exchange legacy protocols.
Source: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-app-consent-policies
[INFERENCE] So **sign-in alone may be self-serve** (subject to §3.1 app-registration being enabled), while **data access is not**. That asymmetry gives you a clean architecture: use delegated Entra sign-in for *authentication* of users, and a separate app-only identity with `Sites.Selected`+`write` for *data access*, with your Next.js API routes doing authorization in between. Only the second piece needs the IT ticket.
[DATA caveat] *"Applications that require users to be assigned to the application must have their permissions consented by an administrator, even if the user consent policies for your directory would otherwise allow a user to consent on behalf of themselves."*
Source: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent
[INFERENCE] i.e. if you set "User assignment required" on the enterprise app (which you'd want, to restrict to allow-listed staff), you have re-introduced an admin consent requirement. Another reason the honest answer is "one IT ticket, unavoidable".

---

## 6. Compliance upside — and where the licence tier bites

### 6.1 Data residency for an India tenant
[DATA] India is a Microsoft 365 *Local Region Geography*: *"Tenants in certain Local Region Geographies have access to Advanced Data Residency … These Local Region Geographies are Australia, Austria, Brazil, Canada, Chile, Denmark, France, Germany, **India**, …"*
Source: https://learn.microsoft.com/en-us/microsoft-365/enterprise/o365-data-locations?view=o365-worldwide
[DATA] For SharePoint/OneDrive, the baseline commitment comes from **Product Terms**, with the required condition: *"Tenant has a sign-up country/region included in Local Region Geography, the European Union or the United States"*, and the commitment language lives in the Privacy and Security Product Terms under *"Location of Customer Data at Rest for Core Online Services."* A **separate, additional** commitment comes from the paid **Advanced Data Residency (ADR) add-on**, which requires (1) a Local/Expanded Local Region Geography signup, (2) *"a valid Advanced Data Residency subscription for all users in the Tenant"*, and (3) SharePoint data provisioned in that geography.
Source: https://learn.microsoft.com/en-us/microsoft-365/enterprise/m365-dr-service-spo?view=o365-worldwide
[DATA] ADR eligibility is enterprise-tier: search summary states customers must hold F1/F3/E3/E5-class licences and must cover **100% of paid licences** with ADR add-ons for the commitment to apply.
Source: search summary of https://learn.microsoft.com/en-us/microsoft-365/enterprise/advanced-data-residency?view=o365-worldwide — **[UNVERIFIED in detail]**, fetch that page before quoting eligibility to the Principal.
[DATA] How to check reality rather than theory: *"As a Tenant administrator you can find the actual data location, for committed data, by navigating to Admin→Settings→Org Settings→Organization Profile→Data Location."*
Source: m365-dr-service-spo (above)
[INFERENCE] The honest claim to make to the Principal: **if the tenant was signed up in India, SharePoint customer data at rest sits in the India geo under a contractual Product Terms commitment, at no extra cost — and this is verifiable in one screen in the admin centre.** ADR is only needed to extend commitments across more workloads and to get prioritised migration; it is a paid enterprise add-on and should not be assumed. Do **not** claim "data never leaves India" — the Product Terms language governs *customer data at rest for core online services*, not every telemetry/diagnostic pathway.
[UNVERIFIED for Ionic] Ionic's tenant signup country and current Data Location value. **Check:** ask IT for one screenshot of Org Settings → Data Location.

### 6.2 Audit logging — included, 180 days
[DATA] Purview **Audit (Standard)** is *"Enabled by default … for all organizations with the appropriate subscription"*, gives thousands of searchable events, the Purview portal search tool, the **Audit Search Graph API**, `Search-UnifiedAuditLog`, CSV export, Office 365 Management Activity API access, and **180-day retention** (raised from 90 days for logs generated on/after 17 Oct 2023).
Source: https://learn.microsoft.com/en-us/purview/audit-solutions-overview
[DATA] Plan coverage for Audit (Standard) per the Purview service description table columns: **Microsoft 365 E3/A3/A1/G3/F3/F1 | Office 365 E3/E1/A3/A1/G3/G1/F3 | Microsoft 365 Business Basic/Standard/Premium** — all "Yes".
Source: https://learn.microsoft.com/en-us/office365/servicedescriptions/microsoft-365-service-descriptions/microsoft-365-tenantlevel-services-licensing-guidance/microsoft-purview-service-description
[DATA] **Audit (Premium)** — 1-year retention, custom audit-log retention policies, intelligent insights, higher Management-API bandwidth — requires **Microsoft 365 E5/A5/G5, Office 365 E5/A5/G5, Purview Suite, or the "Purview Suite for Business Premium" add-on** (add-ons *"require a Microsoft 365 Business Premium base license and are capped at 300 seats total"*). 10-year retention needs a further per-user add-on.
Source: same page + audit-solutions-overview
[INFERENCE] **This is the strongest single compliance argument for the SharePoint route.** Every create/update/delete against the list — by a user *or* by your app's service principal — lands in the tenant's unified audit log automatically, retained 180 days, searchable by Compliance, and queryable via Graph. You did not build it, you cannot switch it off, and it is independent of your application's own logging. No free third-party tier gives you that.
[INFERENCE, honest limit] 180 days is short for a regulated firm that may want multi-year trails, and **extending it requires E5-class licensing**. If the firm needs longer, the answer is not "buy E5" — it is "your app also writes its own append-only audit rows into a second List, and that data lives as long as the List does". Do both.

### 6.3 Retention policies, DLP, eDiscovery — check the tier before claiming these
[DATA] **Retention policies** (organization-wide / location-wide / include-exclude): user rights come from *"Microsoft 365 E5/A5/G5/E3/A3/G3, Business Premium … Office 365 E5/A5/G5/E3/A3/G3"*, plus **SharePoint Plan 2** if the location is SharePoint/OneDrive. Adaptive-scope policies require **E5**.
Source: Purview service description (above)
[INFERENCE] **Business Basic and Business Standard are NOT in that list.** If Ionic is on Business Standard, you cannot claim retention policies as a compliance feature.
[DATA] **DLP for Exchange Online, SharePoint Online and OneDrive**: *"Microsoft 365 E5/A5/G5/E3/A3/G3, Microsoft 365 Business Premium, SharePoint Online Plan 2, OneDrive for Business (Plan 2), Exchange Online Plan 2"* and *"Office 365 E5/A5/G5/E3/A3/G3"*.
Source: same page
[INFERENCE] Again: **Business Basic/Standard are excluded.** Business Premium or E3 upward is the floor for DLP.
[DATA] **eDiscovery (Standard) for sites and files**: "Yes" for the E5-class column *and* for **"Microsoft Office 365 E3/A3/G3/F3, Microsoft 365 E3"**. eDiscovery (Premium) is "No" for E3. Business plans do not appear as columns in that table.
Source: same page
[INFERENCE/UNVERIFIED] Treat eDiscovery as available at E3 and above, and **unverified for Business plans** — the licensing table does not list them, which is a reason for caution, not a proof of absence.
[DATA] Sensitivity labelling: *"Scanner-based discovery is supported with a Microsoft 365 E3 license. Sensitivity labeling, including automatic or policy-based labeling, requires a Microsoft 365 E5 license or Microsoft 365 Information Protection and Governance (IPG)."*
Source: same page
[DATA] Hold ceiling: retention policies + eDiscovery holds count toward *"the 10,000 per tenant maximum for compliancy policies"*; SharePoint/OneDrive all-sites holds max 13, specific-location holds max 2,600.
Source: SharePoint limits page

[OPINION] **This is the section where it would be easiest to oversell.** The correct pitch to the Principal is: *"Data stays in the firm's own tenant; every write is captured in the tenant's unified audit log for 180 days at no extra cost and Compliance can search it without asking me. Retention policies, DLP and eDiscovery are available too — but only at Business Premium / E3 and above, so I need to know our licence tier before I promise them."* Anything stronger than that is a claim we cannot back.
[UNVERIFIED — highest-value open question] **Ionic's exact M365 SKU.** Everything in §6.3 flips on it. Ask IT: "which Microsoft 365 plan are our licences?" One line answer, decides four compliance claims.

---

## 7. Google Workspace equivalent

[DATA] **Google Tables is dead.** Support ended after **16 December 2025**; Google directs users to Google Sheets or **AppSheet**, with AppSheet the successor that preserves column types and relationships.
Source: https://techcrunch.com/2025/09/11/google-is-shutting-down-tables-its-airtable-rival/ (and corroborating coverage)
[INFERENCE] There is therefore **no Lists-analogue in Workspace**. The nearest architecture is Google Sheets as the store (which is the very thing the Principal is being talked out of) plus either AppSheet or Apps Script.

[DATA] **AppSheet free tier is prototyping only**: *"Invite up to 10 test users at no cost to use your apps and share feedback"*, and you must *"purchase a subscription"* once the app *"is ready to be deployed and shared with other users."*
Source: https://support.google.com/appsheet/answer/10106235
[DATA] Paid tiers per third-party pricing summaries start ~$5/user/month (Starter) up to ~$20/user/month (Enterprise Plus).
Source: search synthesis (g2, saasworthy, about.appsheet.com/pricing) — **[UNVERIFIED]**, check https://about.appsheet.com/pricing/ directly.
[INFERENCE] For 10–50 employees, AppSheet is **₹5,000–₹80,000+/month**. Against a hard zero-rupee budget, AppSheet is out. It also does not satisfy "a proper website frontend" — it is a no-code app shell, not a Next.js site.

[DATA] **Apps Script as backend — quotas (consumer / Google Workspace):** script runtime 6 min per execution (custom functions 30 s); triggers total runtime **90 min/day (consumer) vs 6 hr/day (Workspace)**; URL Fetch calls **20,000/day vs 100,000/day**; email recipients **100/day vs 1,500/day** (2,000/day within domain); simultaneous executions 30/user and 1,000/script; URL Fetch response cap 50 MB; quotas reset 24 h after first request and *"are subject to change without notice."*
Source: https://developers.google.com/apps-script/guides/services/quotas
[INFERENCE] Apps Script + Sheets *can* serve a ticket app of this size (1,500 emails/day is plenty for reminders), and Apps Script is free with Workspace. But it inherits the whole-file concurrency problem of Sheets, has no per-row ETag, no per-row permissions, no delta feed, and a 6-minute execution ceiling. Architecturally it is *worse* than the SharePoint List, not equivalent.

[DATA] **Google Workspace data residency does not include India:** *"Your location options are the United States, European Union (labeled Europe in the Google Admin console), or No preference."* Supported editions: Frontline Starter/Standard/Plus, Business Standard and Business Plus, Enterprise Standard and Plus, Education Standard and Plus, Enterprise Essentials Plus.
Source: https://knowledge.workspace.google.com/admin/compliance/choose-a-geographic-location-for-your-data
[INFERENCE — a genuinely decisive asymmetry] If Ionic is on Google Workspace, **you cannot pin data to India at all**; the best you get is US or EU. If Ionic is on M365 with an India signup, India residency is the baseline. For a SEBI-regulated Indian wealth manager, that is a real difference in compliance posture, and it means **the answer to this whole question depends on which email platform the firm actually runs.** Establish that first; it changes the recommendation.
[UNVERIFIED] Ionic's email platform. **Check:** look at the MX record for the company domain, or simply at the webmail the Principal logs into.

---

## 8. The honest downsides of a Next.js frontend on a SharePoint List backend

1. **Latency per call.** [INFERENCE] Every read and write is an HTTPS round trip from your server to Graph, which then hits SharePoint. [UNVERIFIED] I have no benchmark I can cite; anyone quoting "~200 ms" is guessing. **Measure it** before designing the UX: run 50 sequential `PATCH .../items/{id}/fields` calls from the actual hosting region and record p50/p95. Design decision that follows: never make the browser wait on a chain of Graph calls; batch, cache, and use `delta`.
2. **No joins, ever.** [DATA] Only `$filter`/`$expand` are documented for listing items; `$orderby` is not; and *"the service can only filter one indexed field at a time"* (§1.8). [INFERENCE] "Show me all tickets with their latest update and their assignee's name" is 2–3 API calls plus in-app joining, or a denormalised `LastUpdateSummary` column you maintain yourself. Sorting and multi-condition filtering happen in your code. This is fine at 50 employees and painful at 5,000.
3. **Throttling is shared and opaque.** [DATA] *"multiple applications running against the same tenant share the same resource bucket, and in rare occurrences can cause rate limiting when too many applications send requests at the time."* And the `RateLimit` headers are beta, best-effort, and only appear at ≥80% consumption. [INFERENCE] A migration tool or backup product someone else runs in the tenant can throttle *your* app. You must implement `Retry-After` honouring from day one, not later.
4. **Harder local development.** [INFERENCE] There is no local SharePoint. Every developer needs tenant credentials and network reach; offline development is impossible; the corporate proxy on the Principal's laptop is an additional failure mode. Compare Postgres: `docker run postgres` and you are working on a plane. Mitigation: a repository interface with an in-memory/SQLite implementation for local work and tests, and the Graph implementation only in deployed environments. This is real, ongoing engineering tax.
5. **Vendor lock-in, but the benign kind.** [INFERENCE] Your data model is a list of typed items; exporting to CSV/Postgres later is mechanical. The lock-in is in the *access layer* (Graph SDK calls scattered through the app), not the data. Isolate all Graph calls behind one module and the lock-in cost is a few hundred lines.
6. **Tamper-evidence is genuinely harder — and this is the deepest objection.** [INFERENCE] A hash-chained append-only log assumes the store only accepts appends. A SharePoint List is editable through the SharePoint/Lists web UI, Excel-export-and-edit, Power Automate, and any other app in the tenant. If any human with Contribute rights can edit an "immutable" punch row, your hash chain breaks and you cannot tell tampering from a legitimate admin edit. Two partial defences: (a) lock the list so only the app writes (§8.1 below), and (b) hash-chain anyway — each punch row stores `prev_hash` and `row_hash`, so an edit made outside your app *breaks the chain visibly* even if you cannot prevent it. Detection, not prevention. [OPINION] Say this plainly to the Principal: **on a store the tenant's admins can edit, you get tamper-*evident*, not tamper-*proof*. Only a store where no human has write access — i.e. a database whose credentials only the app holds — gets you closer to tamper-proof, and even then a DB admin can edit rows.** Neither option gives you real immutability without an external anchor.
7. **Two identities to reason about.** [INFERENCE] App-only writes attribute every change to the service principal, so `createdBy` on the list item is your app, not the employee — your own `PunchedBy` column becomes the real author field, and it is only as trustworthy as your API's authentication. Delegated writes attribute correctly but then every user needs the (admin-consented) Sites scope. Pick one deliberately.
8. **Secret rotation.** [INFERENCE] A client secret expires (Entra caps secret lifetimes) and your app dies silently on that day. A certificate is better and is what Microsoft's ACS-migration guidance recommends. Either way, this is a recurring IT dependency, not a one-time one — put the expiry in a calendar.

### 8.1 Can you lock the List so ONLY the app writes to it?
[INFERENCE, built on cited primitives] **Yes, substantially — and this is the design to use:**
- Put the lists on a **dedicated site collection** (a Communication site, not a Team/Group site), and do **not** add employees as site members. Employees have no SharePoint path to the data at all; they only ever see your Next.js UI. [DATA basis: site-collection-level app grants *"do not break inheritance because this is the root of permission inheritance"* — permissions-selected-overview.]
- Grant the app `Sites.Selected` with role `write` on that one site (roles available: read/write/owner/fullcontrol — permissions-selected-overview). Withhold `owner`/`fullcontrol` so the app cannot change permissions.
- Keep the site's own membership to IT/admins only. [INFERENCE] Those admins remain able to edit — that residual is irreducible, which is exactly point 6 above.
- Revocation is one call: `DELETE /sites/{siteid}/lists/{listid}/permissions/{id}` [DATA, permissions-selected-overview].
[INFERENCE] What you cannot do is stop a Global Admin or SharePoint Admin from editing. In *every* option (a), (b), (c) somebody with infrastructure rights can edit the store. The difference is only *who* that somebody is: Supabase's staff and whoever holds the service key (a); the firm's own IT (b); the firm's own IT again, plus the VM host's staff (c).

---

## 9. Three-option comparison for THIS project

| | (a) Supabase free tier Postgres | (b) SharePoint List in the firm's tenant + Next.js via Graph | (c) Self-hosted Postgres on a free always-on VM the firm controls |
|---|---|---|---|
| **Data control** | Client data sits on a third party's infrastructure under their DPA; region choice at project creation; you hold the keys but not the servers | Data never leaves the firm's own M365 tenant; India geo if the tenant signed up in India [DATA §6.1] | Data on a VM the firm nominally controls — but the VM sits on *some* cloud's free tier, so control is over the OS, not the metal |
| **Compliance posture** | You must build audit/retention/eDiscovery yourself; a SEBI-facing answer to "where is this data and who can read it" involves a vendor you'd have to onboard | Strongest: unified audit log on by default, 180 days, Audit(Standard) included in Business Basic upward [DATA §6.2]; retention/DLP/eDiscovery available at Business Premium/E3+ [DATA §6.3]; Purview/eDiscovery/DLP already in Compliance's existing toolset | Nothing included. Every audit, backup, retention and access-review control is yours to build and to defend |
| **IT dependency** | None to start. That is precisely why it is tempting and why it is a governance problem — you are onboarding a data processor by yourself | **One ticket, unavoidable**: Entra app registration + admin consent + site-level grant. No self-serve path in a default tenant [DATA §3.2] | None initially; but you own patching, TLS certs, backups, uptime, and the security posture of an internet-facing host holding client data forever |
| **Build effort** | Lowest. Real SQL, joins, transactions, migrations, RLS, generated REST/typed client, local Postgres for dev | Medium-high. No joins, one-indexed-field filters, no `$orderby`, client-side sorting, denormalisation, a repository abstraction so you can develop locally, plus `Retry-After` handling [DATA §1.8, §2.3] | Medium. Same SQL benefits as (a), plus all the ops work of running a box |
| **Reliability** | Free tiers pause/reclaim idle projects and change terms; you carry vendor-roadmap risk on a production internal tool | Microsoft SLA-backed service the firm already depends on for email; the risk is *your* app's throttling discipline, not the store [DATA §2.3] | A single free VM with no redundancy, no managed backups, and a provider that can end the free tier. Lowest reliability of the three unless someone actively babysits it |
| **Cost** | ₹0 until you exceed the free tier, then real money and a procurement conversation | ₹0 incremental — Lists, Graph, and standard-connector Power Automate are all included [DATA §4] | ₹0 until the free tier changes; hidden cost is engineering hours forever |

### What the Principal gives up in each
- **(a) Supabase:** he gives up *the ability to say client data stays on company infrastructure* — which is the one thing he explicitly asked for. He also gives up the tenant's free audit trail and quietly becomes the person who onboarded a foreign data processor without a DPA review. [OPINION] For a SEBI-regulated non-discretionary PMS, that is the option most likely to be objected to after the fact, and the objection would land on him personally.
- **(b) SharePoint List:** he gives up *independence*. He cannot ship without one IT action, and he gives up SQL — joins, transactions, `ORDER BY`, multi-column filters — which makes reporting features meaningfully harder forever. He also accepts that the store is editable by the firm's own admins, so his audit log is tamper-evident, not tamper-proof.
- **(c) Self-hosted Postgres:** he gives up *the compliance story he was trying to buy*. "On a free VM I set up" is not stronger than "in the company's Microsoft tenant" — it is weaker, because there is no audit log, no retention, no eDiscovery, no MFA-backed identity, and no vendor SLA, and he personally becomes the security operator of an internet-facing host holding staff and client-adjacent data. He also permanently owns uptime.

### The single trade-off he cannot escape
**Zero rupees plus zero IT involvement plus data on company infrastructure is not a reachable combination.** Data on company infrastructure means the company's identity and permission systems, and those are administered by IT — by definition. He can pick any two:
- **Company infrastructure + zero cost → one IT ticket** (option b).
- **Zero IT + zero cost → data on someone else's infrastructure** (option a), and he owns that decision when someone asks.
- **Zero IT + company-ish infrastructure → he personally becomes IT** (option c), which is the same dependency, just moved onto him, minus every compliance feature he wanted.

[OPINION] Recommend (b), and make the IT ask as small as it can possibly be: one Entra app, `Sites.Selected` only, one dedicated site, `write` role, certificate over secret, revocable in one API call. Ask for it in writing, in the exact words in §3.5. And before writing a line of code, get three facts that decide the whole design: (1) is the email platform M365 or Google, (2) what is the exact M365 SKU, (3) does `New registration` in the Entra portal succeed for the Principal's own account.

---

## 10. Open questions that must be answered before committing

| # | Question | How to check | What it decides |
|---|---|---|---|
| 1 | M365 or Google Workspace? | MX record for the company domain / which webmail is used | Whether option (b) exists at all. Google has no Lists analogue and **no India data region** [DATA §7] |
| 2 | Exact M365 SKU (Business Basic/Standard/Premium, E1/E3/E5)? | Ask IT, or M365 admin → Billing → Licenses | Whether retention policies, DLP, eDiscovery can be claimed [DATA §6.3] |
| 3 | Tenant signup country / Data Location value? | Admin → Settings → Org Settings → Organization Profile → **Data Location** [DATA §6.1] | Whether "data stays in India" is true |
| 4 | Is `Users can register applications` still Yes? | Try App registrations → New registration in entra.microsoft.com | Whether even the sign-in piece is self-serve [DATA §3.1] |
| 5 | Which user-consent policy is set? | Attempt the consent screen once; "Need admin approval" answers it | Confirms the §3.2 blocker in *this* tenant rather than in the default |
| 6 | Actual Graph round-trip latency from the hosting region | 50 sequential PATCHes, record p50/p95 | Whether the UX can be synchronous or must be optimistic-update |
| 7 | Premium-connector boundary, first-party confirmation | https://learn.microsoft.com/en-us/connectors/connector-reference/connector-reference-premium-connectors + Power Platform Licensing Guide PDF | Confirms reminder emails are genuinely ₹0 [UNVERIFIED §4.3] |
| 8 | ACS / Add-in retirement enforcement status as of Aug 2026 | SharePoint dev blog / Message Center | Only matters if someone proposes the legacy self-serve route — do not [§3.4] |

---

## Source list
- SharePoint limits (30M items, 50,000 unique scopes, 2,000 lists/site, 50,000 versions, Lists = same platform): https://learn.microsoft.com/en-us/office365/servicedescriptions/sharepoint-online-service-description/sharepoint-online-limits
- List view threshold = 5,000: https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/items-exceeds-list-view-threshold
- Threshold is per-operation; indexes; no SPO override: https://support.microsoft.com/en-us/office/manage-large-lists-and-libraries-b8588dae-9387-48c2-9248-c24122f07c59
- Column types: https://support.microsoft.com/en-us/office/list-and-library-column-types-and-options-0d8ddb7b-7dc7-414d-a283-ee9dca891df7
- Graph update listItem + `if-match` ETag: https://learn.microsoft.com/en-us/graph/api/listitem-update?view=graph-rest-1.0
- Graph listItem resource (eTag, createdBy, versions, permissions): https://learn.microsoft.com/en-us/graph/api/resources/listitem?view=graph-rest-1.0
- Graph list items + `$filter` limits: https://learn.microsoft.com/en-us/graph/api/listitem-list?view=graph-rest-1.0
- Graph listItem delta: https://learn.microsoft.com/en-us/graph/api/listitem-delta?view=graph-rest-1.0
- SharePoint throttling (RU costs, 1,250/min, 1.2M/24h, Retry-After, RateLimit beta): https://learn.microsoft.com/en-us/sharepoint/dev/general-development/how-to-avoid-getting-throttled-or-blocked-in-sharepoint-online
- Graph service-specific throttling (Excel 1,500/10s): https://learn.microsoft.com/en-us/graph/throttling-limits
- Selected permissions (3 steps, roles, Sites.FullControl.All to grant, inheritance break): https://learn.microsoft.com/en-us/graph/permissions-selected-overview
- Entra: users can register apps by default: https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/delegate-app-roles
- Entra user consent settings + built-in policies: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent
- Entra app consent policies — Microsoft-managed default EXCLUDES Sites.ReadWrite.All: https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-app-consent-policies
- Sites.Selected / Sites.ReadWrite.All consent flags (third-party, metadata-derived): https://graphpermissions.merill.net/permission/Sites.Selected , https://graphpermissions.merill.net/permission/Sites.ReadWrite.All
- ACS / Add-in retirement: https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/add-ins-and-azure-acs-retirements-faq , https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/retirement-announcement-for-azure-acs
- Power Platform request limits (Office 365 = 6,000/user/24h): https://learn.microsoft.com/en-us/power-platform/admin/api-request-limits-allocations
- M365 data locations, India a Local Region Geography: https://learn.microsoft.com/en-us/microsoft-365/enterprise/o365-data-locations?view=o365-worldwide
- SPO/OneDrive data residency, Product Terms vs ADR, how to check Data Location: https://learn.microsoft.com/en-us/microsoft-365/enterprise/m365-dr-service-spo?view=o365-worldwide
- Purview Audit Standard vs Premium, 180 days: https://learn.microsoft.com/en-us/purview/audit-solutions-overview
- Purview service description — plan lists for Audit, retention, DLP, eDiscovery, labelling: https://learn.microsoft.com/en-us/office365/servicedescriptions/microsoft-365-service-descriptions/microsoft-365-tenantlevel-services-licensing-guidance/microsoft-purview-service-description
- Apps Script quotas: https://developers.google.com/apps-script/guides/services/quotas
- Google Workspace data regions (US/EU only): https://knowledge.workspace.google.com/admin/compliance/choose-a-geographic-location-for-your-data
- AppSheet free tier = prototyping, paid to deploy: https://support.google.com/appsheet/answer/10106235
- Google Tables shutdown (support ends 16 Dec 2025): https://techcrunch.com/2025/09/11/google-is-shutting-down-tables-its-airtable-rival/
