# DPDP Act 2023 + DPDP Rules 2025 — applied to an internal employee ticket/CRM system
**Firm:** Ionic Wealth (India, SEBI-registered, NDPMS + MF/advisory). 10–50 employees. Zero budget.
**App:** tickets with deadline + assignee; append-only status punches; manager dashboard. Email-OTP/magic-link login, allow-listed company addresses. Client identifiers stored only as an opaque `client_ref` code.
**Research date:** 2026-08-03. All vendor/legal facts reflect what I found on that date only.

## Primary sources actually read (not summaries)
| Source | What it is | How obtained |
|---|---|---|
| `THE DIGITAL PERSONAL DATA PROTECTION ACT, 2023 (No. 22 of 2023)` — India Code, 25pp | The Act, official text | Downloaded `https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf`, text-extracted locally (`scratchpad/dpdp_act_2023.txt`) |
| `G.S.R. 846(E)`, MeitY, New Delhi, 13 Nov 2025 — Digital Personal Data Protection Rules, 2025. Gazette of India Extraordinary Part II §3(i), Gazette ID `CG-DL-E-14112025-267650`, 18pp | The Rules, official gazette text | `https://www.dpdpa.com/DPDP_Rules_2025_English_only.pdf`, text-extracted locally (`scratchpad/dpdp_rules_2025.txt`); masthead + G.S.R. number + recital of draft G.S.R. 02(E) dated 3 Jan 2025 all present, so this is the genuine gazette page images |
| SEBI FAQs on CSCRF and Cloud Framework, Jun 2025, 23pp | SEBI's own FAQ | `https://www.sebi.gov.in/sebi_data/faqfiles/jun-2025/1749647139924.pdf` (`scratchpad/sebi_cscrf_faq.txt`) |
| CERT-In Directions under s.70B(6) IT Act, 28 Apr 2022, 8pp | The Directions, official | `https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf` (`scratchpad/certin_2022.txt`) |

Secondary (used only for commencement mapping and status-of-notifications): AZB & Partners, Shardul Amarchand Mangaldas, Internet Freedom Foundation, PIB, medianama, Chambers/NovoJuris/LKS/SNG commentary on s.7(i).

---

## 1. STATUS AND TIMELINE

### 1.1 What happened
- **[DATA]** DPDP Act 2023 = Act 22 of 2023. Passed Aug 2023 but **its substantive chapters were never brought into force for over two years.**
- **[DATA]** Draft DPDP Rules were published 3 Jan 2025 as **G.S.R. 02(E)** for 45 days of comments (recited in the final gazette). **6,915 stakeholder inputs** were received (PIB).
- **[DATA]** **Final Rules notified 13 Nov 2025** as **G.S.R. 846(E)**. So the answer to "have the Jan-2025 draft Rules been finalised?" is **yes — nine months ago as of today.** Alongside them MeitY issued commencement notifications for the Act and constituted the Data Protection Board of India (reported as the G.S.R. 843(E)/844(E)/845(E) series — *the mapping of each number to each instrument is [UNVERIFIED]; I verified only that 846(E) is the Rules*).

### 1.2 Phased commencement — verbatim from Rule 1
> **(2)** Rules 1, 2 and 17 to 21 shall come into force on the date of their publication in the Official Gazette.
> **(3)** Rule 4 shall come into force **one year** after the date of publication of this Gazette.
> **(4)** Rules 3, 5 to 16, 22 and 23 shall come into force **eighteen months** after the date of publication of this Gazette.

| Phase | Date | Rules live | Act sections live |
|---|---|---|---|
| 1 — institutional | 13/14 Nov 2025 | 1, 2, 17–21 (definitions, Board constitution, Board procedure, digital office, Board staff) | **[DATA]** rule text confirms Rules. **[secondary, AZB]** Act ss. 1(2), 2, 18–26, 35, 38–43, 44(1) & (3) |
| 2 — consent managers | ~13/14 Nov 2026 | Rule 4 + First Schedule | **[secondary]** ss. 6(9), 27(1)(d) |
| 3 — **everything that matters** | **~12–14 May 2027** | Rules 3, 5–16, 22–23 | **[secondary]** ss. 3–5, 6(1)–(8) & (10), **7–17**, 27 (ex-(1)(d)), **28–34** (incl. penalties), 36–37, 44(2) |

**[DATA] Exact-day caveat:** the gazette is *dated* 13 Nov 2025 but the e-gazette ID is `CG-DL-E-14112025`, i.e. published 14 Nov. Law firms accordingly print 12 May 2027 (AZB), 13 May 2027 (Mondaq/IFF) and 14 May 2027 (SAM). **Plan to 12 May 2027** internally; do not build a plan that lands on the last week.

### 1.3 What is live NOW vs future-dated — the decision-relevant conclusion
- **[DATA/INFERENCE] Nothing in the DPDP Act that imposes a duty on this firm is in force today (3 Aug 2026).** Notice (s.5), consent (s.6), legitimate uses (s.7), *all* Data Fiduciary obligations (s.8), children (s.9), SDF (s.10), Data Principal rights (ss.11–14), cross-border (s.16), **and the penalty chapter (ss.33–34)** are all Phase 3. Rule 6 (security), Rule 7 (breach notice), Rule 8 (retention), Rule 14 (rights) are all Phase 3.
- **[INFERENCE] Practical DPDP enforcement exposure for this app today ≈ zero.** The Board cannot impose a penalty for an obligation that has not commenced. The real deadline is **~12 May 2027 — about 9 months away.**
- **[DATA] BUT the *old* regime is still the live law today.** Act s.44(2)(a) omits **IT Act s.43A**, and s.44(2)(c) omits s.87(2)(ob) — the rule-making power under which the **SPDI Rules 2011** were made. **s.44(2) is Phase 3.** Therefore until ~May 2027, s.43A + the SPDI Rules 2011 remain in force and are the applicable personal-data-security law.
  - **[DATA]** SPDI Rules **Rule 4** requires a body corporate handling such information to provide/publish a **privacy policy** stating the type of information collected, the purpose, and the security practices used. *[UNVERIFIED: whether Rule 4 extends to plain "personal information" or only to sensitive personal data — secondary summaries conflict; I did not read the 2011 primary text. Immaterial to the recommendation: publish a policy either way, it costs nothing.]*
  - **[DATA]** SPDI Rule 8 gives an ISO/IEC 27001 (or approved code) safe harbour for "reasonable security practices". Not achievable at zero budget; irrelevant if you simply implement Rule 6 of DPDP Rules 2025 as the spec.
- **[DATA] CERT-In Directions of 28 Apr 2022 are live and have been since 27 Jun 2022** — and they bite harder and sooner than DPDP. See §7.3.
- **[UNVERIFIED] Data Protection Board staffing:** the Board was established in law on 13 Nov 2025; MeitY invited applications for Chairperson/Members around 6 May 2026 with a further notification ~6 Jun 2026. Secondary sources conflict on whether members were actually appointed by mid-2026. Immaterial — penalties commence at Phase 3 regardless.

---

## 2. THE CENTRAL QUESTION — CONSENT OR LEGITIMATE USE?

### 2.1 The provision, verbatim (Act s.7, opening + clause (i))
> **7. Certain legitimate uses.—** A Data Fiduciary may process personal data of a Data Principal for any of following uses, namely:— … **(i)** for the purposes of employment or those related to safeguarding the employer from loss or liability, such as prevention of corporate espionage, maintenance of confidentiality of trade secrets, intellectual property, classified information or provision of any service or benefit sought by a Data Principal who is an employee.

And s.4(1): a person may process personal data "only … for a lawful purpose, (a) for which the Data Principal has given her consent; **or** (b) for certain legitimate uses." — the two grounds are **alternatives**.

### 2.2 Answer
**[DATA + INFERENCE] This app does NOT require consent. It sits squarely inside s.7(i) "for the purposes of employment".**

Assigning a task to an employee, recording a deadline, having the employee punch status updates, and letting a manager see the team's status is the archetype of employment-purpose processing: it is work allocation, supervision and accountability. It is also partly "safeguarding the employer from loss or liability" (an auditable record that work was assigned and tracked). Law-firm commentary is uniform that s.7(i) covers recruitment, attendance, payroll, statutory compliance and **performance evaluation** (Chambers/NovoJuris, LKS, SNG & Partners).

### 2.3 **DO NOT build a consent checkbox.** This is the single most important design consequence.
**[INFERENCE — high confidence, reasoning from the Act's text]** Adding "I consent to my data being processed" would be a *compliance downgrade*, not an upgrade:
1. **s.6(4)** — where consent is the basis, the Data Principal has a right to withdraw it **at any time, with ease comparable to how it was given.** **s.6(6)** then obliges the Fiduciary to *cease processing*. An employee could withdraw consent and, on the face of it, demand you stop tracking their tasks. Under s.7(i) there is no withdrawal right at all.
2. **s.6(10)** — where consent is the basis and a question arises in a proceeding, **the burden of proof is on the Data Fiduciary** to prove valid notice *and* valid consent. You would be manufacturing an evidentiary burden you do not have.
3. **s.6(1)** requires consent to be "free" — consent obtained from an employee by an employer is the textbook case of consent that is not free. A consent-based employee tool is arguably built on an invalid ground.
4. **[DATA]** Consent-based processing is what drags in the **Rule 3** notice-content rules, the **Rule 14** rights machinery, and (optionally) Consent Managers. None of that is triggered by s.7(i).

**Design rule: the app has no consent UI, no consent table, no consent timestamp. The lawful basis is a constant: `legal_basis = 'DPDP s.7(i) employment'`, recorded once in documentation, not per-user.**

### 2.4 The boundary — precisely what s.7(i) does and does not buy you
**s.7(i) is a lawful *ground*, not an *exemption*.** The exemptions are in s.17 and none of them apply here. So:

**Still fully applicable under s.7(i):** every duty in **s.8** — s.8(1) responsibility, s.8(3) accuracy where data drives a decision affecting the person, s.8(4) technical & organisational measures, **s.8(5) security**, **s.8(6) breach notification**, **s.8(7) erasure when purpose is served**, s.8(9) published contact person, **s.8(10) grievance mechanism** — plus **s.13** (grievance redressal right) and **s.14** (nomination). Also s.4(1)'s "lawful purpose" and the purpose-boundedness of s.7 itself.

**Outside s.7(i) — no lawful ground, therefore unlawful, [INFERENCE] on an untested boundary:**
| Falls outside | Why |
|---|---|
| **Client personal data in a ticket** | s.7(i) is about *employees*. A client is not the employer's employee. Client PII in a ticket has **no s.7(i) ground** — it would need the client's consent or another s.7 limb. **This is the single strongest legal reason the `client_ref` opaque-code design must be enforced in code, not policy.** |
| Data collected "just in case" (personal mobile, home address, DOB, marital status, photo) not needed to run the ticket system | s.4(1) demands a lawful purpose; s.7 is bounded by "for the purposes of employment". Processing beyond the employment purpose has no ground. |
| Publishing employee productivity/ticket stats externally (brand content, marketing, investor decks with named staff) | Not an employment purpose and not loss/liability protection. |
| Sharing task history with third parties for non-employment reasons | Same. |
| Retaining employee task history indefinitely after they leave, beyond what a law requires | s.8(7) requires erasure once the purpose is no longer served, "unless retention is necessary for compliance with any law". |
| Broad covert monitoring dressed up as "loss or liability" | The clause's own examples are all narrow and specific (espionage, trade secrets, IP, classified information). There is active constitutional criticism of s.7(i) as "surveillance by design" (Indian Constitutional Law & Philosophy, Feb 2026). A ticket tracker is fine; keystroke/screenshot/location surveillance bolted onto it is where this argument breaks. |

### 2.5 A precise textual point worth knowing (and then ignoring in practice)
**[DATA]** ss.11 and 12 are drafted narrowly:
> **s.11(1)** "The Data Principal shall have the right to obtain from the Data Fiduciary **to whom she has previously given consent, including consent as referred to in clause (a) of section 7** …"
> **s.12(1)** "… her personal data **for the processing of which she has previously given consent, including consent as referred to in clause (a) of section 7** …"
> **Rule 14(2)** "…she may make a request to the Data Fiduciary **to whom she has previously given consent** …"

s.7(**i**) is not s.7(**a**). **[INFERENCE]** On a literal reading, an employee has **no s.11 access right and no s.12 correction/erasure right** against an employer processing purely under s.7(i). Law-firm commentary flags exactly this as an unresolved conflict (Bar & Bench / NovoJuris: the Act "does not clarify … which one is to prevail"), and at least one commentary argues the literal reading "would undermine the very intent of Sections 8, 10, 11, 12 and 13".

**[OPINION] Do not build the product on this argument.** It is (a) untested, (b) hostile to your own staff, and (c) irrelevant because s.8(10) + s.13 grievance redressal **do** apply unconditionally, and s.8(3) accuracy applies because ticket/status records *are* used to make decisions affecting the employee. Access and correction cost about two screens. Build them. Where the literal reading genuinely helps: **erasure**. You can decline an employee's "delete my whole task history" demand and stand on s.8(7)'s "unless retention is necessary for compliance with any law" + Rule 8(3)'s one-year floor + SEBI record-keeping — without contorting the product.

---

## 3. OBLIGATIONS → PRODUCT FEATURES

### 3.1 Notice (s.5 + Rule 3) — legally NOT required here; do it anyway
**[DATA]** s.5(1): "**Every request made to a Data Principal under section 6 for consent** shall be accompanied or preceded by a notice…". The notice duty is textually **hooked to a consent request**. No consent request → **no statutory s.5 notice obligation** for s.7(i) processing. Rule 3 likewise governs "the notice given by the Data Fiduciary" for informed *consent*.

**[OPINION] Publish an employee privacy notice regardless** — it is free, it is the artefact that proves purpose limitation to a regulator/auditor, and SPDI Rule 4 (live today) points the same way. Use Rule 3's content list as the template, because it is the government's own idea of adequate:
- an **itemised description** of the personal data held (not "your data" — an actual field list);
- the **specified purpose(s)** of processing, and the lawful basis (s.7(i) employment);
- how to **exercise rights / raise a grievance**, with a named person and email;
- how to **complain to the Data Protection Board**;
- retention periods and who the processors are (**[DATA]** IFF's criticism is that Rule 3 does *not* mandate recipient categories, retention periods or cross-border safeguards — so disclosing them is best practice above the legal floor, and cheap goodwill).

**Feature:** one static `/privacy` page, version-stamped, linked from the login screen and the footer. ~300 words. No cookie banner needed (an internal tool with a session cookie and no third-party analytics is not doing consent-based tracking — **[INFERENCE]**; and cookie consent is not a DPDP concept at all).

### 3.2 Purpose limitation + data minimisation → schema-level
- **Feature:** a hard, documented field inventory. Employee record = `{display_name, work_email, role, active}`. Nothing else. No employee ID photo, no phone, no DOB, no personal email.
- **Feature — the critical one:** a server-side guard on every free-text field (`ticket.title`, `ticket.body`, `status_punch.note`) that **rejects or masks** strings matching PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), Aadhaar-shaped 12-digit runs, 10-digit mobile numbers, email addresses, and IFSC/account-number patterns. Reject with a message ("use the client_ref code"), do not silently store.
- **Feature:** `client_ref` is a foreign key to an opaque code, `CHECK` constrained to a code format, with **no** client-name column anywhere in this database. The client-code→client-name mapping lives in the firm's existing regulated systems, not here.
- **[INFERENCE]** If this guard is not in code, the design intent ("only opaque client codes") will fail within weeks of real use, and at that point the app is processing client PII with no lawful ground — which is a materially worse legal position than the employee data ever was.

### 3.3 Accuracy (s.8(3)) vs the append-only log — resolvable, and the append-only design actually wins
**[DATA]** s.8(3): where personal data is likely to be "used to make a decision that affects the Data Principal", the Fiduciary "shall ensure its completeness, accuracy and consistency." A ticket/status record used for performance review is exactly that.
**[DATA]** s.12(2): on request, the Fiduciary shall correct inaccurate/misleading data, complete incomplete data, and update data.

**Feature:** never mutate a status punch. Add `status_punch.supersedes_id` + `correction_note`, so a correction is a **new append-only row that points at the row it corrects**, and every view renders "latest effective, with correction history". This satisfies "correction, completion, updating" without breaking immutability, and is *better* evidence than an editable log.

### 3.4 Retention and erasure — the biggest trap in the whole Rules
**Act side:**
> **s.8(7)** "…unless retention is necessary for compliance with any law…, (a) erase personal data, upon the Data Principal withdrawing her consent **or as soon as it is reasonable to assume that the specified purpose is no longer being served, whichever is earlier**; and (b) cause its Data Processor to erase…"
> **s.8(8)** the purpose is deemed no longer served if the Data Principal neither approaches the Fiduciary for the purpose nor exercises her rights, "for such time period as may be prescribed".

**Rules side — Rule 8, and this is where people get it wrong:**
- **[DATA] Rule 8(1) + Third Schedule do NOT apply to this firm.** The Third Schedule fixes a 3-year erasure trigger for exactly **three classes**: an e-commerce entity with **≥ 2 crore** registered users in India; an online gaming intermediary with **≥ 50 lakh** registered users; a social media intermediary with **≥ 2 crore** registered users. A 10–50 person wealth manager's internal tool is none of these. **So there is no prescribed automatic erasure clock for you.** (Nor the Rule 8(2) "48 hours before erasure, warn the user" duty, which hangs off Rule 8(1).)
- **[DATA] Rule 8(3) DOES apply to every Data Fiduciary**, verbatim:
  > "Without prejudice to sub-rules (1) and (2), a Data Fiduciary shall retain, in respect of any processing of personal data undertaken by it or on its behalf by a Data Processor, such personal data, associated traffic data and other logs of the processing **for a minimum period of one year** from the date of such processing, for the purposes as specified in the Seventh Schedule, after which the Data Fiduciary shall cause such personal data and logs to be erased, unless further retention is required for compliance with any other law…"
  Its own Illustration Case 1 spells out the consequence: the platform "must retain the order details, personal data, and logs … for at least one year from the date of the transaction, **even if X deletes her account**." (Seventh Schedule purposes = State access for sovereignty/security, performance of legal functions, and SEBI-style assessment of fiduciaries.)
- **[DATA] Rule 6(1)(e)** independently requires retaining logs **and personal data** for **one year** to enable breach detection/investigation/remediation, "unless compliance with any law … requires otherwise."

**[INFERENCE] Net product rule: you must NOT implement instant hard-delete.** A "delete my data" button that immediately `DELETE`s rows would breach Rule 8(3) and Rule 6(1)(e). Correct design:
1. **Soft-delete / redact-on-request**: mark the row deleted and null out or tokenise the identifying fields in the *application* views, while the underlying record + audit log survive to the one-year floor.
2. **A scheduled purge job** that hard-deletes rows whose processing date is > 1 year old **and** whose purpose is spent **and** which no other law requires you to keep.
3. **Feature:** a `retention_policy` table with, per data class, `{purpose, min_retain_until, legal_hold_reason, purge_after}` — because a SEBI-regulated firm will have record-keeping obligations that override the DPDP erasure duty via s.8(7)'s "unless retention is necessary for compliance with any law". *(Which SEBI record-keeping periods apply is out of scope for this dimension — see §8 open questions.)*
4. **Feature:** an **offboarding** routine, since s.8(7)'s "purpose no longer served" plainly bites when an employee leaves: revoke the allow-list entry, close/reassign open tickets, then let the retention clock run. Do not simply leave ex-employees active.

### 3.5 Data Principal rights — the mechanics
| Right | Act | Applies here? | Feature |
|---|---|---|---|
| **Access** (summary of data + processing activities; identities of other Fiduciaries/Processors it was shared with) | s.11 | **[INFERENCE]** literally hooked to consent/s.7(a), so arguably not — **build it anyway** | "My data" page: their profile fields, their tickets, their full status-punch history, list of processors (host, DB, email sender). One read-only screen + a JSON/CSV export. |
| **Correction / completion / updating** | s.12(1)–(2) | Same caveat; **build it** (also needed for s.8(3) accuracy) | The `supersedes_id` correction flow in §3.3, plus self-service edit of own `display_name`. |
| **Erasure** | s.12(3) — erase "unless retention of the same is necessary for the specified purpose or for compliance with any law" | Same caveat, **and** the Act's own carve-out plus Rule 8(3)/6(1)(e) let you decline for ≥1 year | A request *form*, not a delete button. Logged, with a templated response citing the retention basis. Redaction now, purge later. |
| **Grievance redressal** | **s.13 + s.8(10) — applies unconditionally, no consent hook** | **Yes, definitely** | In-app "raise a data grievance" form → ticket to the named DPO-equivalent; SLA timer; audit trail of response. **[DATA] Rule 14(3):** publish the grievance-response period, which must be "a reasonable period **not exceeding ninety days**". Publish e.g. 15 days and mean it. |
| **Nominate** (someone to exercise rights on death/incapacity) | s.14 + Rule 14(4) "in accordance with the terms of service" | Yes, but | **[OPINION]** no UI needed for a 10–50 person internal tool. One line in the privacy notice: "to nominate an individual under s.14, write to <email>". A DB column is over-engineering. |
| Publish the *means* of making requests + the identifier needed | **Rule 14(1)** | Yes | A "Your data rights" section in the privacy notice stating: use this in-app form or email X, and identify yourself by your **work email** (the Rule 14(5) "identifier"). |
| Published contact person | **s.8(9) + Rule 9** | Yes | Business contact info of the DPO **if applicable** (it isn't — DPO is SDF-only) **or a person who can answer questions about processing.** Must be published on the site **and repeated in every response** to a rights communication. Name a real human (the APM or the compliance officer), not `info@`. |

### 3.6 Consent Manager — **not relevant to this project. Skip entirely.**
**[DATA]** Rule 4 + First Schedule Part A: a Consent Manager must be **a company incorporated in India**, with **net worth ≥ ₹2 crore**, sound financials, independently certified interoperable consent platform, registered with the Board. It is a licensed *business* (think account-aggregator-style intermediary), not a compliance artefact a data fiduciary must buy or become. It exists to let individuals manage **consent**; this app has no consent-based processing. Rule 4 is also the only Phase-2 item (~Nov 2026) — irrelevant to you.

### 3.7 Reasonable security safeguards — what the law ACTUALLY specifies
This is the most useful part of the Rules for a builder, because it is a checkable list rather than "be reasonable". **Rule 6(1)** verbatim requires, **at the minimum**:

| Rule 6(1) | Text | Zero-budget implementation |
|---|---|---|
| (a) | "appropriate data security measures, such as securing of personal data through **encryption, obfuscation, masking or the use of virtual tokens** mapped to that personal data" | TLS everywhere (free on the host); DB at-rest encryption (managed Postgres gives this); `client_ref` **is** your "virtual token mapped to that personal data" — this clause is direct legal cover for the opaque-code design; mask work emails to non-admins in the UI |
| (b) | "appropriate measures to **control access** to the computer resources" | Row-level security / server-side authorisation on every query; role model (assignee / manager / admin); allow-list check at OTP issuance **and** at session validation; MFA-by-construction (the magic link *is* possession-of-mailbox) |
| (c) | "**visibility** on the accessing of such personal data, through appropriate **logs, monitoring and review**, for enabling detection of unauthorised access, its investigation and remediation" | An `access_log` table: who viewed/exported which employee's data, when. **Reads must be logged, not just writes** — this clause is about *accessing*. Plus a weekly admin review screen (the "review" word is in the rule) |
| (d) | "reasonable measures for **continued processing** … such as by way of **data-backups**" | Automated daily logical DB dump to a second location; documented restore test. Free tiers do **not** guarantee backups — verify per vendor |
| (e) | "retain such **logs and personal data for a period of one year**" | The retention floor in §3.4 |
| (f) | "appropriate provision in the **contract** … between such Data Fiduciary and such a Data Processor … for taking reasonable security safeguards" | Accept and **archive a dated PDF** of each vendor's DPA/security terms. See §4 |
| (g) | "appropriate **technical and organisational** measures to ensure effective observance" | The organisational half is not code: a named owner, a one-page written security policy, an offboarding checklist, and a documented incident runbook |

**[OPINION]** Rule 6 is a gift: it is a 7-item spec you can literally tick off in a README, and it is cheap. Every item is achievable at ₹0. Build to Rule 6 now and you are simultaneously compliant with SPDI Rule 8's "reasonable security practices" today and with s.8(5) from May 2027.

### 3.8 Personal-data-breach notification — no size threshold, and the definition is broader than you think
**[DATA]** s.2(u): "**personal data breach**" = "any unauthorised processing of personal data **or accidental disclosure, acquisition, sharing, use, alteration, destruction or loss of access** to personal data, that compromises the confidentiality, integrity or availability of personal data."
→ **[INFERENCE]** a botched migration that destroys the status log, or an outage that loses access to it, is a *personal data breach*. Not just hacks.

**[DATA]** s.8(6) + **Rule 7** — two separate notifications, **no de minimis, no "risk of harm" filter, no minimum record count**:

**(1) To each affected Data Principal** — "On becoming aware of any personal data breach … **without delay**", via her user account or a registered channel, "in a concise, clear and plain manner", containing: (a) description incl. **nature, extent and timing**; (b) **consequences relevant to her**; (c) mitigation measures implemented/being implemented; (d) **safety measures she may take**; (e) **business contact information of a person who can respond to her queries**.

**(2) To the Data Protection Board** — two stages:
- **without delay**: description incl. nature, extent, **timing and location** of occurrence, and **likely impact**;
- **within 72 hours** of becoming aware (extendable only on a **written** request the Board may allow): updated/detailed description; broad facts, circumstances and reasons; mitigation measures; **any findings on who caused it**; remedial measures to prevent recurrence; and **a report on the intimations given to affected Data Principals**.

**Features:**
- A `breach_register` table (discovered_at, description, extent, affected user ids, notified_at_principals, notified_at_board_initial, notified_at_board_detailed, root cause, remediation).
- **Pre-written templates** for both notifications, with the five Rule 7(1) elements as mandatory fields, stored in the repo. You cannot draft these inside 72 hours (or 6 hours — §7.3) from scratch.
- A "notify all affected" mailer that pulls addresses from the affected-user list, because Rule 7(1) requires per-principal intimation "through her user account or any mode of communication registered by her."
- The **named contact person** from §3.5 must be embedded in the template — Rule 7(1)(e) requires it.

---

## 4. WHO IS WHO — FIDUCIARY, PROCESSOR, BUILDER

**[DATA]** s.2(i) Data Fiduciary = "any person who **alone or in conjunction with other persons determines the purpose and means** of processing of personal data." s.2(k) Data Processor = "any person who **processes personal data on behalf of** a Data Fiduciary." s.2(s) "person" includes a company and "every artificial juristic person".

| Party | Role | Consequence |
|---|---|---|
| **Ionic Wealth (the company)** | **Data Fiduciary.** It decides why employee task data is processed and how. | Carries 100% of the legal obligations and 100% of the penalty exposure. |
| **Cloudflare (Workers/Pages/D1/R2), Supabase, the email/OTP sender (Resend/Brevo/SES etc.)** | **Data Processors** — they process employee personal data on the firm's behalf. | No direct DPDP duties of their own. Need a contract with security provisions (Rule 6(1)(f)). |
| **GitHub** | **Not a processor if the repo contains only code.** Becomes a processor the moment personal data is committed. | See gotcha in §8. |
| **The APM building it** | **Neither.** An employee acting for the Fiduciary — he is *inside* the Fiduciary, not a separate person. He is also a **Data Principal** himself (his own employee record). | **[INFERENCE]** He cannot personally be the Fiduciary, and cannot be made personally liable under DPDP for the firm's non-compliance (the Act penalises "a person" who breaches — the Fiduciary). But he also cannot be the accountability owner: **[DATA]** s.8(1) makes the Fiduciary responsible "**irrespective of any agreement to the contrary**". The firm must formally own this system, not treat it as one person's side project. |

**Contract obligation toward the processor:**
- **[DATA]** s.8(2): a Fiduciary may involve a Processor "for any activity related to offering of goods or services to Data Principals **only under a valid contract**." **[INFERENCE]** Note the scope limiter: an internal employee tool is arguably *not* "offering of goods or services to Data Principals", so s.8(2)'s mandate may not literally bite.
- **[DATA]** It does not matter, because **Rule 6(1)(f)** independently requires "appropriate provision in the contract entered into between such Data Fiduciary and such a Data Processor, **wherever applicable**, for taking reasonable security safeguards." And Rule 8(3)'s Illustration Case 2 says the Fiduciary "is required to ensure that the [cloud provider] also retains the data and associated logs for at least one year."
- **[INFERENCE] Practical meaning at ₹0:** the vendor's clickwrap ToS + published DPA/security addendum **is** your contract. You cannot negotiate a free tier. So the compliance act is: **for each vendor, download and date-stamp (a) the ToS, (b) the DPA, (c) the security/sub-processor page, into `/compliance/vendors/` in the repo.** Then verify three things per vendor: a DPA actually exists and covers the free tier; the ToS permit business use; the sub-processor list is published (you need it for the s.11 access answer, which asks for "the identities of all other Data Fiduciaries and Data Processors with whom the personal data has been shared").
- **[INFERENCE]** You cannot push liability to Cloudflare. s.8(1) is explicit. Vendor selection is therefore a risk decision the *firm* signs off on, not an IT detail.

---

## 5. SIGNIFICANT DATA FIDUCIARY — could a 10–50 person firm ever be one?

**[DATA]** s.10(1): "**The Central Government may notify** any Data Fiduciary or class of Data Fiduciaries as Significant Data Fiduciary, on the basis of an assessment of such relevant factors as it may determine, including — (a) the volume and sensitivity of personal data processed; (b) risk to the rights of Data Principal; (c) potential impact on the sovereignty and integrity of India; (d) risk to electoral democracy; (e) security of the State; and (f) public order." And s.2(z) confirms SDF status exists only "as may be notified by the Central Government".

**[DATA/INFERENCE] Answer: SDF status is *conferred by government notification*, not self-assessed against a headcount or a record-count threshold. There is no numeric trigger in the Act or the Rules.** A 10–50 person firm processing a few dozen employee records will not plausibly be notified. **[secondary, as at search date]** no SDF list has been notified yet; commentary expects designations from ~2027 and aimed at large platforms and large financial/health/telecom entities.

**Extra duties if ever designated — Act s.10(2) + Rules Rule 13:**
- **[DATA] s.10(2)(a)** appoint a **Data Protection Officer** who **(i)** represents the SDF, **(ii)** is **based in India**, **(iii)** is an individual **responsible to the Board of Directors** or similar governing body, and **(iv)** is the contact point for grievance redressal.
- **[DATA] s.10(2)(b)** appoint an **independent data auditor**.
- **[DATA] Rule 13(1)–(2)** — **once every 12 months**: a **Data Protection Impact Assessment** *and* an **audit**, and the person carrying them out must **furnish a report of significant observations to the Board**.
- **[DATA] Rule 13(3)** due diligence that technical measures "including **algorithmic software**" it uses do not risk Data Principals' rights.
- **[DATA] Rule 13(4)** measures ensuring that personal data **specified by the Central Government** (on a committee's recommendation) and its traffic data **is not transferred outside India** — i.e. hard localisation, but only for SDFs and only for government-specified classes.

**[OPINION] Practical consequence: DPIA, independent audit, and a DPO-in-India are SDF-only duties. Do not let a compliance vendor sell them to a 45-person firm as universal DPDP requirements.** What *is* universal is s.8(9)/Rule 9's much lighter duty: publish "the business contact information of the Data Protection Officer, **if applicable**, or **a person who is able to answer** … the questions of the Data Principal". Name a person; you do not need a DPO.

---

## 6. PENALTIES — the actual schedule

**[DATA]** s.33(1): the Board may impose the penalty in the Schedule only if, on conclusion of an inquiry, it determines the breach is **"significant"**. Verbatim Schedule (to s.33(1)):

| # | Failure | Maximum penalty |
|---|---|---|
| 1 | Breach of the obligation to take **reasonable security safeguards** to prevent a personal data breach — **s.8(5)** | **may extend to ₹250 crore** |
| 2 | Breach of the obligation to give the Board or affected Data Principal **notice of a personal data breach** — **s.8(6)** | **may extend to ₹200 crore** |
| 3 | Breach of additional obligations **in relation to children** — s.9 | may extend to ₹200 crore |
| 4 | Breach of additional obligations of a **Significant Data Fiduciary** — s.10 | may extend to ₹150 crore |
| 5 | Breach of the **duties of a Data Principal** — s.15 | may extend to **₹10,000** |
| 6 | Breach of a **voluntary undertaking** accepted by the Board under s.32 | up to the extent applicable to the breach in respect of which s.28 proceedings were instituted |
| 7 | **Breach of any other provision** of the Act or the rules | **may extend to ₹50 crore** |

**Reading it correctly:**
- **[DATA]** These are **maxima**, and s.33(2) obliges the Board to have regard to: nature/gravity/duration; type and nature of the personal data affected; whether the breach is **repetitive**; whether the person **gained or avoided loss**; whether and how promptly they **mitigated**; proportionality and deterrence; and **"the likely impact of the imposition of the monetary penalty on the person."** **[INFERENCE]** For a 45-person firm with a self-built internal tool that keeps no client PII, discloses promptly and has documented Rule 6 controls, realistic exposure is orders of magnitude below the caps — the caps are calibrated to large platforms.
- **[DATA]** The two largest heads (₹250cr, ₹200cr) are **security** and **breach notification** — i.e. exactly §3.7 and §3.8. That is where to spend effort.
- **[DATA]** Penalties go to the **Consolidated Fund of India** (s.34). **[INFERENCE]** DPDP creates **no private right of compensation** for the individual — an aggrieved employee's route is grievance → Board (s.13(3) requires exhausting the internal grievance mechanism first), not damages. This makes a working internal grievance mechanism a genuinely effective shield.
- **[DATA]** No imprisonment provision for Data Fiduciaries under DPDP.
- **[DATA]** ss.33–34 are **Phase 3 (~May 2027)**; not enforceable today.
- **[DATA]** s.37: if the Board reports two or more penalty impositions on the same Fiduciary, the Central Government may order **blocking** of its service. Not a realistic risk for an internal tool.

---

## 7. CROSS-BORDER TRANSFER — and the sectoral overrides that actually bind

### 7.1 DPDP itself: permissive, blacklist model
**[DATA]** s.16(1): "The Central Government **may, by notification, restrict** the transfer of personal data by a Data Fiduciary for processing to such country or territory outside India as may be so notified."
**[DATA]** s.16(2): "Nothing contained in this section shall restrict the applicability of any law … in force in India that provides for a **higher degree of protection for or restriction on** transfer of personal data … outside India."
**[DATA]** Rule 15: "Any personal data processed by a Data Fiduciary under the Act **may be transferred outside the territory of India** subject to the restriction that the Data Fiduciary shall meet such requirements as the Central Government may, by general or special order, specify in respect of making such personal data available to **any foreign State, or to any person or entity under the control of or any agency of such a State**."

**[DATA/INFERENCE] Conclusion: DPDP is a *negative-list* (blacklist) regime — the opposite of the EU adequacy/whitelist model. Transfers abroad are permitted by default. There is no adequacy assessment, no SCC requirement, no transfer impact assessment, no localisation mandate for ordinary Data Fiduciaries.** Rule 15's only bite is a future government order about making data available to a **foreign State or its agencies** — which is about government access, not about where you host. **[secondary, as at search date]** **no country has been notified/restricted under s.16(1).**
→ **Hosting the app on Cloudflare (and a DB on Supabase) outside India does not breach DPDP.** Note also **[DATA] Rule 13(4)**: hard localisation exists only for **SDFs** and only for government-specified data classes.

### 7.2 SEBI — the override that could matter, currently in abeyance
s.16(2) expressly preserves stricter sectoral law, and this firm is a SEBI-registered portfolio manager.
- **[DATA]** SEBI's **CSCRF** (circular `SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113`, **20 Aug 2024**) applies to SEBI Regulated Entities including **Portfolio Managers**, tiered (MII / Qualified / Mid-size / Small-size / Self-certification) by size — **[secondary]** Portfolio Managers are tiered by AUM, and Investment Advisers / Research Analysts largely sit in the **self-certification** tier. Thresholds were revised by `SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2025/60` dated 30 Apr 2025 (referenced in SEBI's own FAQ).
- **[DATA — SEBI's own FAQ, Jun 2025, Q26, verbatim]** "…The framework mandates that **encryption keys and key management operations must be handled within the boundaries of India** … REs should assess and verify the key management architecture of their CSPs and adopt solutions like Bring Your Own Key (BYOK)… **It may be noted that SEBI is doing an active consultation to finalise the guidelines related to Data Localisation requirements.**"
- **[secondary]** The CSCRF data-localisation control (**PR.DS.S2** — host Indian-securities-market data within India) is reported to be **in abeyance** pending that consultation, with an exemption for IT/cyber data sent to international SOCs/SaaS subject to annual IT-Committee classification and Board approval.
- **[DATA — SEBI FAQ, verbatim]** the CSCRF "controls shall apply **only to IT infrastructure, network, application, software, etc. being used for SEBI RE related activities**."
  → **[INFERENCE]** An internal admin/HR ticket tool that holds **no client PII and no securities-market data** has a genuine argument for being outside CSCRF's control scope. **That argument collapses the moment tickets describe client portfolio actions** — which is exactly the risk the `client_ref` design is meant to contain. The purity of the "no client data" rule is therefore doing double duty: it keeps you out of DPDP client-PII scope **and** out of the SEBI CSCRF/localisation argument.
- **[UNVERIFIED]** SEBI's **Cloud Framework** (`SEBI/HO/ITD/ITD_VAPT/P/CIR/2023/033`, 6 Mar 2023) — secondary sources say it requires use of **MeitY-empanelled** CSPs and India-based data centres, HSM/KMS key control, and gave existing arrangements 12 months to comply. **I did not read its primary text. If it does mandate MeitY-empanelled CSPs, that is fatal to Cloudflare/Supabase free tiers for anything in RE scope.** This must be verified by the SEBI dimension before a hosting decision is locked.
- **[INFERENCE] RBI is irrelevant here.** RBI's storage-of-payment-system-data localisation (2018) binds payment system operators/participants. This app processes no payment data.

### 7.3 CERT-In — the *live* localisation and breach obligation, today
This is the finding most likely to be missed, because it is not DPDP and it is not SEBI.
**[DATA — CERT-In Directions under s.70B(6) IT Act, 28 Apr 2022, effective 27 Jun 2022, verbatim]**
- **(ii)** "Any service provider, intermediary, data centre, **body corporate** and Government organisation shall mandatorily report cyber incidents as mentioned in **Annexure I** to CERT-In **within 6 hours of noticing** such incidents or being brought to notice about such incidents." (via `incident@cert-in.org.in`, 1800-11-4949)
- **Annexure I** reportable types include **iii. Unauthorised access of IT systems/data**, **xi. Data Breach**, **xii. Data Leak** — **no severity or size threshold**.
- **(iii)** designate a **Point of Contact** to interface with CERT-In (Annexure II format).
- **(iv)** "All … body corporate … shall mandatorily **enable logs of all their ICT systems and maintain them securely for a rolling period of 180 days** and the same shall be **maintained within the Indian jurisdiction.**"
- **(i)** synchronise system clocks to **NPL/NIC** NTP (or a source that does not deviate from them).

**[INFERENCE] Consequences for this build, and they are the sharpest constraints in this whole document:**
1. **A 6-hour breach clock is live today**, versus DPDP's 72 hours from May 2027. Your incident runbook must be written to 6 hours, with a pre-drafted email and a named PoC, **before go-live**.
2. **180 days of ICT logs must sit within Indian jurisdiction.** Cloudflare/Supabase free tiers give you neither an India-resident log store you control nor guaranteed retention. **Mitigation at ₹0:** have the app write its own structured audit/access log (§3.7(c)) and run a scheduled nightly export of that log to a location within Indian jurisdiction (an India-region store, or an encrypted archive on firm-controlled storage/the firm's own Microsoft 365/Google tenant if that tenant is India-resident — *tenant region is [UNVERIFIED] and must be checked*). Keep 180 days minimum; Rule 6(1)(e)/8(3) will want 365 anyway, so **just set the log retention floor at 1 year and satisfy both.**
3. Note the neat alignment: DPDP Rule 6(1)(c) wants access logs, Rule 6(1)(e)/8(3) want one year, CERT-In wants 180 days **in India**. **One design — an app-level append-only access/audit log, exported nightly to India-held storage, retained 12 months — satisfies all three.** Build that once.

---

## 8. MINIMUM DEFENSIBLE COMPLIANCE POSTURE — developer checklist

**Legally required *today* (Aug 2026)** — SPDI Rules 2011 + CERT-In are in force; DPDP's duties are not:
- [ ] **Publish a privacy policy/notice** (SPDI Rule 4): what data, why, how secured. One static page.
- [ ] **Named Point of Contact filed with CERT-In** (Annexure II) + a **6-hour incident runbook** with a pre-written report email.
- [ ] **Enable app + platform logs, 180 days minimum, a copy held within Indian jurisdiction.** NTP-sane timestamps (UTC stored, IST displayed).
- [ ] "Reasonable security practices" — no defined floor absent ISO 27001; build to DPDP Rule 6 below and you exceed it.

**Legally required by ~12 May 2027** — build these now, they are all cheap:
- [ ] **No consent UI.** Document the lawful basis once: **DPDP s.7(i), employment purposes.** (§2.3)
- [ ] **Employee privacy notice** using the Rule 3 content pattern: itemised field list, purposes, lawful basis, retention, processors, how to exercise rights, how to complain to the Board. Version-stamped.
- [ ] **Named contact person published** on the site and **repeated in every rights response** (s.8(9)/Rule 9). A human, not a shared mailbox. No DPO required (SDF-only).
- [ ] **Field inventory enforced in the schema.** Employees: display name, work email, role, active. Nothing more.
- [ ] **Server-side PII guard** on all free-text fields rejecting PAN / 12-digit Aadhaar-shaped / 10-digit mobile / email / account-number patterns. `client_ref` opaque codes only; **no client-name column exists in this DB.** (§3.2)
- [ ] **Append-only status log + correction-by-supersession** (`supersedes_id`, `correction_note`) — satisfies s.8(3) accuracy and s.12(2) without mutable history. (§3.3)
- [ ] **Rule 6(1) security, all seven items**: TLS + at-rest encryption + masking; server-side authorisation/RLS + allow-list checked at issuance *and* session validation; **access logging of reads**, with a weekly admin review screen; automated daily backup with a tested restore; 1-year log/data floor; archived vendor DPAs; a one-page written security policy with a named owner. (§3.7)
- [ ] **Retention engine, not a delete button**: soft-delete/redact on request; `retention_policy` table with `min_retain_until` + `legal_hold_reason`; scheduled purge only past the **1-year floor** (Rule 8(3), Rule 6(1)(e)); documented offboarding routine on employee exit. (§3.4)
- [ ] **"My data" page** — own profile, own tickets, own full status history, list of processors, JSON/CSV export. (s.11, built voluntarily)
- [ ] **Rights + grievance form**, with a published response SLA **≤ 90 days** (Rule 14(3) — publish 15 days), an SLA timer, and an audit trail. Publish the *means* of requesting and the identifier required = work email (Rule 14(1), 14(5)). (§3.5)
- [ ] **Nomination**: one sentence in the notice. No UI.
- [ ] **Breach machinery**: `breach_register` table; a **72-hour/6-hour** dual-clock runbook; templates for (a) per-principal intimation carrying all five Rule 7(1) elements and (b) the Board's initial + detailed reports; a "notify all affected" mailer. (§3.8)
- [ ] **Vendor pack**: `/compliance/vendors/<vendor>/{tos,dpa,security,subprocessors}-YYYY-MM-DD.pdf` for the host, DB and email sender. Confirm per vendor: DPA covers the free tier; ToS permit business use; sub-processor list published.
- [ ] **Firm-level ownership memo** — one page signed by the firm (not the builder) stating that the company is the Data Fiduciary for this system, naming the contact person and the system owner. s.8(1) makes this unavoidable. (§4)

**Explicitly NOT required — do not build, do not buy:**
- Consent flows, consent records, consent withdrawal, cookie banners.
- A Consent Manager integration (₹2cr net-worth licensed entity; consent-only; irrelevant).
- A DPIA, an independent data audit, or a DPO based in India (**SDF-only**, s.10 / Rule 13).
- Third Schedule automatic 3-year erasure + 48-hour pre-erasure warning (applies only to ≥2cr-user e-commerce, ≥50L-user gaming, ≥2cr-user social media).
- Data localisation of the application/database under DPDP (no country restricted; localisation is SDF-only). *SEBI Cloud Framework remains the open question.*
- Adequacy assessments / SCCs / transfer impact assessments — not DPDP concepts.

---

## 9. GOTCHAS
1. **A consent checkbox makes it worse.** It manufactures a s.6(4) withdrawal right, a s.6(6) cease-processing duty, and a s.6(10) burden of proof — and employer-obtained consent is not "free" under s.6(1) anyway.
2. **You cannot lawfully hard-delete on request inside one year.** Rule 8(3) (all Fiduciaries) + Rule 6(1)(e) impose a 1-year retention *floor* on personal data, traffic data and logs. A naive "Delete my data → DELETE FROM" button is itself a Rules breach.
3. **CERT-In's 180-day-logs-within-India is live today** and free-tier foreign hosting does not deliver it. This, not DPDP, is the real localisation constraint.
4. **6 hours, not 72.** CERT-In's clock is live and 12x tighter than DPDP's. Without a pre-written template and a filed PoC you will miss it on day one.
5. **One client name typed into a ticket note breaks the entire legal architecture** — s.7(i) covers employees only, so client PII in this DB has *no* lawful ground, and it also drags the app into SEBI CSCRF scope. This must be a server-side validator, not a line in a policy doc.
6. **Committing the employee allow-list to GitHub** turns the repo into a personal-data store with an immutable history you cannot erase (and makes GitHub a processor). Load the allow-list from env/DB; add a pre-commit/secret-scan check.
7. **Magic-link/OTP email creates a second personal-data store you don't control.** The email vendor becomes a Data Processor; delivery logs contain every employee's work email and login times. It needs a DPA, and it must appear in the s.11 processor list.
8. **"Personal data breach" includes accidental destruction and loss of access** (s.2(u)) — a bad migration or a dropped table is reportable, not just an intrusion.
9. **You cannot contract liability to Cloudflare/Supabase.** s.8(1): the Fiduciary is responsible "irrespective of any agreement to the contrary". Processors carry no direct DPDP duties.
10. **The two biggest penalty heads are security (₹250cr) and breach notification (₹200cr)** — the two things a solo builder is most likely to under-invest in. Everything else defaults to the ₹50cr residual head.
11. **The 18-month date is 12, 13 or 14 May 2027 depending on the source.** Don't plan to the last day.
12. **Deferring because "penalties aren't live until 2027" is a trap**: retrofitting access logging, encryption, a retention engine and an append-only correction model into a live system costs far more than building them now, and the CERT-In/SPDI obligations bind today regardless.
13. **s.11/s.12 rights arguably don't attach to s.7(i) processing** — a real textual argument, but untested and adversarial toward staff. Use it to justify declining *erasure*; do not use it to skip building access and correction.
14. **Don't let a compliance vendor sell you SDF duties.** DPIA, independent audit and a DPO-in-India are s.10/Rule 13 obligations for government-notified entities only.

---

## 10. OPEN QUESTIONS
1. **SEBI Cloud Framework (6 Mar 2023) primary text — does it mandate MeitY-empanelled CSPs and/or India-located data centres for SEBI REs?** If yes, and if this app is held to be in RE scope, Cloudflare/Supabase free tiers may be unusable. Highest-impact unresolved item. Needs the SEBI dimension.
2. **Is this app inside SEBI CSCRF's scope at all?** SEBI's FAQ limits controls to IT "being used for SEBI RE related activities". An HR/admin ticket tool with no client or market data is arguably out. Requires a documented, firm-signed scoping determination — and it only holds if the no-client-PII rule is technically enforced.
3. **CSCRF tier for this firm**: which of Qualified / Mid-size / Small-size / Self-certification does Ionic Wealth's PMS AUM place it in (per the 30 Apr 2025 revised thresholds)? Determines the depth of every control.
4. **Which SEBI record-keeping periods apply to internal work records that reference client activity?** This is the legal hook for s.8(7)'s "unless retention is necessary for compliance with any law" and it sets the `min_retain_until` values. Unresolved.
5. **Is the firm's company-email tenant (M365 or Google) India-resident?** Determines whether nightly log export "within Indian jurisdiction" (CERT-In (iv)) can use existing free infrastructure.
6. **Has the firm already filed a CERT-In Point of Contact** as a body corporate? If yes, reuse it; if no, this app's launch is a good forcing function.
7. **Exact Phase-3 date** — 12 vs 13 vs 14 May 2027. Resolve against the S.O./G.S.R. commencement notification text (I verified G.S.R. 846(E) = the Rules; the Act's commencement notification number is unverified).
8. **DPB staffing status as at Aug 2026** — secondary sources conflict on whether Chairperson/Members are appointed. Immaterial to planning but worth a one-line check before any statement is made externally.
9. **SPDI Rule 4's exact scope** (personal information vs sensitive personal data only). Read the 2011 primary text if the privacy-policy obligation ever needs to be defended as strictly legally required rather than best practice.
10. **Free-tier DPA availability** — does Cloudflare's DPA, Supabase's DPA and the chosen email vendor's DPA each apply to the free tier? Rule 6(1)(f) needs a contract with security provisions; a free tier with no DPA is a gap.
