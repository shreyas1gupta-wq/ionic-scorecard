# SEBI obligations touching an internal workflow / ticket system at a registered Portfolio Manager

**Research date: 2026-08-03.** Every free-tier limit, deadline and abeyance below reflects what was found on that date. SEBI circulars change; re-verify before relying.

**Tagging:** [DATA] = verified from a named primary/near-primary source. [INFERENCE] = my reasoning from that data. [OPINION] = judgment. UNVERIFIED = could not confirm.

**Primary sources actually parsed (not remembered):**

| Doc | Source fetched | Notes |
|---|---|---|
| SEBI (Portfolio Managers) Regulations, 2020 (consolidated, 61pp) | `apmiindia.org/storagebox/images/Circulars/PMS Regulation - 2020.pdf` | Full text extracted and read |
| SEBI (Research Analysts) Regulations, 2014 (gazette, 24pp) | `thc.nic.in/Central Governmental Regulations/…(Research Analysts) Regulations,2014.pdf` | Full text extracted; **2014 version — later amendments not checked** |
| CSCRF, Aug 20 2024 (205pp) | `ncdex.com/public/uploads/circulars/…(CSCRF)…_1724679211.pdf` (exchange reproduction of SEBI circular) | Full text extracted and searched |
| CSCRF Clarifications, Dec 31 2024 (3pp) | `cse-india.com/upload/upload/Dec_311224_2.pdf` | Read verbatim, in full |
| CSCRF Technical Clarifications, Aug 28 2025 (11pp) | `apmiindia.org/…/Technical Specifications to CSCRF for REs - 28th Aug'25.pdf` | Read verbatim, in full |
| CERT-In Directions u/s 70B, Apr 28 2022 (8pp) | `cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf` | Read the log/incident directions verbatim |
| SCORES circular, Sept 20 2023 (19pp) | `greatship.com/upload/investors/SEBI-CIRCULARS-SCORES-and-ODR.pdf` | Extracted and searched |
| SEBI (Investment Advisers) Regulations, 2013 Reg 19 | `taxtmi.com/article/detailed?id=2038` — **secondary reproduction** | SEBI's own HTML pages are wrappers with no text; SEBI PDF not parsed. Treat as near-primary; verify. |
| Cloud Services Framework, Mar 6 2023 | `taxguru.in/sebi/framework-adoption-cloud-services-sebi-regulated-entities.html` — **secondary reproduction** | Verify the addressee list against the SEBI PDF before relying on it |

Note: `sebi.gov.in/legal/...` HTML pages returned only title + breadcrumb metadata; the regulation/circular text lives in attached PDFs. This is why near-primary exchange/association reproductions were used.

---

## 1. RECORD MAINTENANCE & RETENTION

### 1.1 Portfolio Manager — SEBI (Portfolio Managers) Regulations, 2020 [DATA]

**Regulation 27(1)** — *"Maintenance of books of accounts, records, etc."* — "Every portfolio manager shall keep and maintain the following books of accounts, records and documents namely: -"

- (a) a copy of balance sheet at the end of each accounting period;
- (b) a copy of the profit and loss account for each accounting period;
- (c) a copy of the auditor's report on the accounts for each accounting period;
- (d) a statement of financial position and;
- (e) **"records in support of every investment transaction or recommendation which will indicate the data, facts and opinion leading to that investment decision"**
  - *Proviso:* "Provided that such a record shall be maintained under the hands of the Principal Officer of the portfolio manager."

**Regulation 27(2):** must intimate SEBI of the place where the books/records/documents are maintained.

**Regulation 27(3):** after each accounting period, furnish to SEBI copies of balance sheet, P&L "and such other documents for the preceding five accounting years as and when required by the Board."

**Regulation 29** — *"Maintenance of books of accounts, records and other documents"* — verbatim:
> "The portfolio manager shall preserve the books of account and other records and documents **mentioned under this chapter for a minimum period of five years**."

**Regulation 30(1)(a):** separate client-wise accounts. **Regulation 30(2):** "The books of account will be audited yearly by qualified auditor…" certificate to SEBI within six months of close of the accounting period if so specified.

**Regulation 35:** SEBI's right of inspection of "the books of account, records and documents of the portfolio manager", including "to ensure that the books of account are being maintained in the manner required" and "that the provisions of the Act, rules and regulations are being complied with."

**Regulation 40:** SEBI may appoint a qualified auditor to investigate the books of account or affairs.

**Regulation 11(d)** (condition of registration): "the portfolio manager shall take adequate steps for redressal of grievances of the investors **within one month** of the date of the receipt of the complaint and keep the Board informed about the **number, nature and other particulars of the complaints received**".

**Regulation 23(10)** (general responsibility): "The portfolio manager shall ensure proper and timely handling of complaints from his clients and take appropriate action immediately."

**The boundary — precisely.** Reg 29's preservation duty attaches to "the books of account and other records and documents **mentioned under this chapter**". It is a closed reference to the enumerated set (Reg 27(1)(a)-(e), plus the Reg 30 client-wise accounts). It is **not** a general "preserve everything internal for 5 years" rule. [DATA on the wording; [INFERENCE] on the scope reading.]

Therefore:
- An internal ticket/task tracker is **not** in the Reg 27(1) enumeration and, on its face, carries no 5-year preservation duty. [INFERENCE]
- **But Reg 27(1)(e) is the trapdoor.** It is drafted extremely widely — "the data, facts and opinion leading to that investment decision". If a ticket's status log contains the analysis, the reasoning, or the approval trail behind an investment transaction or recommendation, that ticket content *is* a Reg 27(1)(e) record: 5-year preservation (Reg 29), producible on SEBI inspection (Reg 35), and it must be "under the hands of the Principal Officer" — which an append-anything-by-anyone log structurally is not. [INFERENCE, high confidence]
- **Reg 11(d) is the second trapdoor.** "number, nature and other particulars of the complaints received" implies a complaints record. If client complaints get logged as tickets, that log becomes the complaint record. [INFERENCE]
- There is **no** SEBI provision I found that makes generic internal servicing/workflow/task records preservable records for a Portfolio Manager. [DATA — absence, based on a full-text search of the consolidated regulations for "preserv", "books of account", "maintain…record", "five years", "electronic form"]

### 1.2 Investment Adviser — SEBI (Investment Advisers) Regulations, 2013, Regulation 19 [DATA, secondary reproduction]

Records to be maintained under Reg 19(1):
- Know-your-client records of the client
- Risk profiling and risk assessment of the client
- Suitability assessment of the advice being provided
- Copies of agreements with clients, if any
- **Investment advice provided, whether written or oral**
- **Rationale for arriving at investment advice, duly signed and dated**
- A register/record containing list of clients, date of advice, nature of the advice, products/securities in which advice was rendered, and fee

Retention: "All records shall be maintained either in physical or electronic form and **preserved for a period of minimum of five years**." Where a dispute has been raised, records are kept till resolution of the dispute or until further intimation from SEBI. Where records required to be signed are kept in electronic form, they must be digitally signed. **Regulation 20:** yearly compliance audit by an ICAI or ICSI member.

Also relevant (from SEBI's *Guidelines for Investment Advisers*, Sept 2020 — **secondary source only, primary circular not fetched, treat as UNVERIFIED on detail**): IAs must maintain records of interactions with clients (physical record signed by client, telephone recording, email from registered email id, record of SMS, or any other legally verifiable record), for five years, running from the first interaction with the client.

**Why this matters here:** the IA record set is materially *wider* than the PM set — it explicitly captures **advice given orally** and **rationale**. If the entity building the tool also holds an IA registration, the "no rationale in tickets" discipline becomes much more important. [INFERENCE]

### 1.3 Research Analyst — SEBI (Research Analysts) Regulations, 2014, Regulation 25 [DATA, verbatim from 2014 gazette]

> "25. (1) Research analyst or research entity shall maintain the following records:
> (i) research report duly signed and dated;
> (ii) research recommendation provided;
> (iii) rationale for arriving at research recommendation;
> (iv) record of public appearance.
> (2) All records shall be maintained either in physical or electronic form and **preserved for a minimum period of five years**:
> Provided that where records are required to be duly signed and are maintained in electronic form, such records shall be **digitally signed**.
> (3) Research analyst or research entity shall conduct **annual audit** in respect of compliance with these regulations from a member of Institute of Chartered Accountants of India or Institute of Company Secretaries of India."

**CAVEAT:** this is the 2014 gazette text. The RA Regulations were amended on Dec 16 2024 and Feb 10 2025. I did **not** verify whether Reg 25 was amended. UNVERIFIED whether the 2026 text differs.

### 1.4 Adjacent retention rules (not SEBI record regs, but bind the firm)

- **CERT-In Directions u/s 70B(6) of the IT Act, dated Apr 28 2022, Direction (iv)** [DATA, verbatim]: "All service providers, intermediaries, data centres, body corporate and Government organisations shall mandatorily enable logs of all their ICT systems and maintain them securely **for a rolling period of 180 days** and the same shall be **maintained within the Indian jurisdiction**. These should be provided to CERT-In along with reporting of any incident or when ordered / directed by CERT-In." Also Direction (ii): incident reporting to CERT-In **within 6 hours** of noticing. This binds any Indian **body corporate**, independent of SEBI registration. [INFERENCE on applicability to Ionic Wealth as a company]
- **PMLA s.12 / PML (Maintenance of Records) Rules, 2005** — five-year retention of transaction records and client-identity records for "reporting entities" (which includes SEBI intermediaries). **UNVERIFIED** — I did not parse the primary text; verify s.12(3)/(4) and Rule 6 before relying. Relevant only if the tool ever holds client identity or transaction data.
- **DPDP Act 2023** — separate dimension; employee personal data is in scope regardless. Not researched here.

---

## 2. CSCRF — WHO IS COVERED, AND IN WHICH BUCKET

### 2.1 The framework and the five buckets [DATA]

**Circular SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113 dated August 20, 2024** — "Cybersecurity and Cyber Resilience Framework (CSCRF) for SEBI Regulated Entities (REs)", 205 pages, Version 1.0.

Five categories (CSCRF §2, "Thresholds for REs' categorization", p.39): **(i) MIIs, (ii) Qualified REs, (iii) Mid-size REs, (iv) Small-size REs, (v) Self-certification REs**.

Mechanics [DATA, verbatim]: "The category of REs shall be decided at the beginning of the financial year based on the data of the previous financial year. Once the category of RE is decided, RE shall remain in the same category throughout the financial year irrespective of any changes in the parameters during the financial year."

**Portfolio Managers ARE covered.** They appear in the addressee list of the CSCRF circular, the Dec-2024 clarifications and the Aug-2025 technical clarifications ("All Portfolio Managers", plus APMI). [DATA]

### 2.2 Portfolio Manager thresholds — ORIGINAL vs CURRENT [DATA]

**Original (CSCRF Table 11, p.42, Aug 2024) — SUPERSEDED:**

| Self-certification | Small-size | Mid-size | Qualified |
|---|---|---|---|
| AUM < Rs 1,000 cr | Rs 1,000 cr – < Rs 3,000 cr | Rs 3,000 cr and above | N.A. |

**CURRENT — revised by circular SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2025/119 dated Aug 28 2025, Part C, Table 1:**

| Criteria | Qualified REs | Mid-size REs | Small-size REs | Self-certification REs |
|---|---|---|---|---|
| AUM | **N.A.** | Rs 10,000 cr and above | > Rs 3,000 cr and < Rs 10,000 cr | **Rs 3,000 cr and below** |

Two things follow: **a Portfolio Manager can never be a Qualified RE** (and therefore never faces CCI, ISO 27001, red teaming, threat hunting, quarterly reviews); and the self-certification band was widened threefold, from <Rs 1,000 cr to ≤Rs 3,000 cr. [DATA + INFERENCE]

### 2.3 Investment Advisers and Research Analysts [DATA, CSCRF pp.41-42]

- **Individual IAs:** "shall be excluded from submission of compliance with CSCRF."
- **Non-individual IAs:** "shall be categorized as **Small-size REs**." (No AUM threshold — a one-person-plus-company IA is Small-size by status.)
- **RAs not registered in any other RE category:** "shall be excluded from submission of compliance with CSCRF." However SEBI's SaaS advisory of Nov 3 2020 ("Advisory for Financial Sector Organizations regarding Software as a Service (SaaS) based solutions") applies, under which a declaration in respect of SaaS must be submitted.
- **Institutional RAs registered in another RE category:** classified per their other/group-entity category.
- Reporting authority for IAs' VAPT and cyber audit reports = **BASL** (not SEBI directly). For "MIIs and rest of the REs" (so, Portfolio Managers) = **SEBI**. [DATA, CSCRF Tables 17 & 23]

### 2.4 Deadlines — the actual chain [DATA]

| Circular | Date | Effect |
|---|---|---|
| 2024/113 | Aug 20 2024 | CSCRF issued; effective **Jan 1 2025** |
| **2024/184** | **Dec 31 2024** | Regulatory forbearance till **Mar 31 2025** for requirements effective Jan 1 2025, provided the RE demonstrates "meaningful steps taken / progress made". KRAs and DPs extended to **Apr 1 2025**. **Data Localisation [PR.DS.S2] kept in abeyance until further notification.** |
| 2025/45 | Mar 28 2025 | Extension (contents not verified) |
| 2025/60 | Apr 30 2025 | Clarifications (contents not verified; cited in 2025/119 for Market-SOC clauses 2.2, 2.6, 2.7, 3) |
| FAQs | Jun 11 2025 | FAQs on CSCRF **and** the Framework for Adoption of Cloud Services (`sebi.gov.in/sebi_data/faqfiles/jun-2025/1749647139924.pdf`) — **NOT READ, see open questions** |
| **2025/96** | **Jun 30 2025** | Deadline extended to **Aug 31 2025** for REs **other than** MIIs, KRAs and QRTAs [DATA via Taxmann; SEBI primary not parsed] |
| **2025/119** | **Aug 28 2025** | Technical clarifications + PM/MB re-categorisation. "immediate effect" |
| AI Vulnerability Detection Advisory, ref HO/13/19/12(1)2026-ITD-1_CIMGI/10873/2026 | **May 5 2026** | Advisory to be read with CSCRF: immediate OS/app patching (virtual patching if unavailable), VA with traditional + AI-based tools, API inventory + strong auth/authorisation + rate limiting + whitelisting, documented change management, SIEM+SOAR / Market-SOC. Sources disagree on whether it is binding. **[DATA on existence via 4 independent secondary legal sources; SEBI primary page NOT fetched — verify]** |

**Bottom line on timing [INFERENCE]:** as of 2026-08-03 the CSCRF *adoption* deadline (Aug 31 2025) has long passed and there is no blanket extension in force that I found. What is live is the **recurring cycle**: annual VAPT (commencing Q1 of the FY), annual cyber audit for those who must do one, annual policy reviews, annual cybersecurity training, half-yearly access reviews. So the firm should already be inside a CSCRF cadence — a new app lands into an existing audit cycle, not a greenfield one.

---

## 3. WHAT CSCRF CONCRETELY DEMANDS THAT HITS AN IN-HOUSE WEB APP

### 3.1 The single most important clause: "Critical Systems" [DATA, CSCRF Definitions p.26, as clarified Aug 2025 §6.1]

> "Entities shall identify and classify their critical IT systems. Following systems shall be included in critical systems (both on premise and cloud):
> a. Any system, if compromised, that will have an adverse impact on core and critical business operations.
> b. Stores/ transmits data as per regulatory requirements.
> c. Devices/ network through which critical systems are connected (through trusted channels).
> **d. Internet facing applications/ systems.**
> **e. Client facing application/ systems.**
> f. All the ancillary systems used for accessing/ communicating with critical systems either for operations or for maintenance."

Aug 28 2025 clarification §6.1 re-writes (f): **"Any other system which is on the same network segment where systems mentioned in para (a) to (e) are deployed."**

**This is the finding that kills the comfortable hypothesis.** Limb (d) is unqualified by data sensitivity. An internet-facing web app deployed by a covered RE is a critical system **even if it holds nothing but employee task data**. [INFERENCE, high confidence — the text contains no data-sensitivity qualifier on (d)]

Consequences of being a critical system, for a Portfolio Manager in the self-certification or small-size bucket:
- In **VAPT scope** (Annexure-L includes "VA of Applications-Internal & External", "External Penetration Testing-Infrastructure & Application", "API Security Testing", "VAPT of Cloud implementation and deployments", "Configuration audit").
- In **MFA scope** (below).
- In **RTO/RPO scope**: 2-hour RTO, 15-minute RPO (below).
- In the **asset inventory** (ID.AM), and therefore visible to the cyber auditor and to SEBI inspection.

### 3.2 MFA — mandated, but the standard is imprecise [DATA]

- PR.AA guidelines: "All critical systems shall have MFA implemented for all users accessing from untrusted network to trusted network."
- "All critical systems accessible over the internet shall have multi-factor security (such as VPNs, Firewall controls, etc.) and MFA."
- "MFA shall be enabled for all users and systems that connect using online/ internet facility and also particularly for VPNs, webmail, and accounts that access critical systems from non-trusted environments to trusted environments."
- Annexure-H (application security): "For added security, a multi-factor (e.g.: two-factor) authentication scheme **may** be used… In case of IBTs and SWSTs, a minimum of two-factors in the authentication flow are **mandatory**."

**So: yes, CSCRF mandates MFA for internet-facing critical systems.** [DATA]

**Design implication [OPINION]:** an email magic-link / email-OTP-only login is a **single** factor (control of a mailbox). It is knowledge-of-nothing + possession-of-mailbox. Calling it MFA would be a stretch that a CERT-In empanelled auditor may well not accept. If the app is in CSCRF scope, expect "MFA not implemented" as a VAPT/audit observation — note that CSCRF's own worked example of "Absence of security control" is literally **"MFA not implemented"** (Table 20, p.50). Mitigations: add TOTP for admin/manager roles, or restrict access to the corporate network so it is not "internet facing" in the first place.

### 3.3 Audit logs and their retention — CSCRF sets NO number; CERT-In does [DATA]

CSCRF PR.AA.S8-S9 and guidelines:
- "A comprehensive log management policy shall be documented and implemented."
- "User logs shall be uniquely identified and stored for a specified period." (no number given)
- Log types to be collected: "system logs, application logs, network logs, database logs, security logs, performance logs, **audit trail logs**, and event logs."
- "**Strong log retention policy shall be implemented as per government guidelines/ policies/ laws/ circulars/ regulations, etc. issued by SEBI/ GoI such as IT Act 2000, Digital Personal Data Protection Act (DPDP) 2023, and as required by CERT-In, NCIIPC or any other government agency.**"
- "REs shall use auditing/ logging systems on different OS to acquire and store audit/logging data." — applicability: "All REs except small, self-[certification]" (i.e. this specific one is relaxed for the smallest buckets).
- "A comprehensive data-disposal and data-retention policy shall be documented and implemented."

**I searched the full 205-page CSCRF for a numeric log retention period and there is none.** [DATA — absence]

**The operative number is CERT-In's: 180 days rolling, within Indian jurisdiction** (Direction (iv), Apr 28 2022 — quoted verbatim in §1.4 above). This is a hard requirement, is **not** in abeyance, and binds the firm as a body corporate regardless of CSCRF bucket. [DATA + INFERENCE]

**Design implication [OPINION]:** the append-only status log the user wants is a *business* record, not an audit log. Both are needed: (1) the append-only ticket status log, and (2) a separate technical audit trail (who logged in, from where, who read/changed what) retained ≥180 days in India.

### 3.4 VAPT — frequency, scope, who may do it, and the "major release" trigger [DATA]

- **Auditor:** "Unless otherwise specified, all audits mentioned in CSCRF have to be conducted by **CERT-In empanelled IS auditing organization**." An empanelled auditor may audit the same RE for a maximum of three consecutive years, then a two-year cooling off.
- **Frequency (Table 18):** REs identified as 'Protected systems' / CII by NCIIPC → at least twice a year (one per half). **"Rest of the REs" → at least once**, and "VAPT activity shall commence in the first quarter of the financial year."
- **Timelines (Table 19):** report submitted after IT Committee approval within **1 month** of completion; findings closed within **3 months** of report submission; revalidation completed within **5 months** of completion of VAPT. Open items past 3 months need IT Committee approval and must close before the next VAPT.
- **Reporting authority:** SEBI (for Portfolio Managers); BASL (for IAs); exchanges/depositories (for brokers/DPs).
- **Submission format:** Aug 2025 §6.7 — submit the *summary* per the CSCRF format; "at no point of time, REs shall submit the explicit vulnerabilities unless and otherwise asked for the details by SEBI."
- **"Major Change/ Major Release" trigger (CSCRF p.27):** "CSCRF has mandated VAPT after every major release." The list includes "Implementation of a new SEBI circular", "Changes in core versions of software", and — directly relevant — **"Any changes in policy of login and/ or password management."**

**Self-certification REs get the lightest treatment [DATA, CSCRF §4.4.6, verbatim]:**
> "REs categorised as self-certification shall be required to conduct **only VAPT audit** through CERT-In empanelled IS auditing organisation and **no other audit is required** to be conducted. Self-certification (format attached at Annexure-P) shall be submitted for compliance with the applicable CSCRF provisions signed by RE's authorised signatory (MD/ CEO/ Board member/ Partners/ Proprietor)."

**Cyber audit frequency (Table 21):** MIIs & Qualified REs (blank in extract — half-yearly per §4.1 Table 15 pattern); Mid-size and Small-size REs providing IBT or algo trading → at least twice a year; **"Rest of the REs" → at least once in a year**. Cyber audit covers 100% of critical systems and 25% of non-critical systems on a sample basis.

### 3.5 SOC / Market SOC — mandatory onboarding for the small buckets [DATA]

- CSCRF: "Bombay Stock Exchange (BSE) and National Stock Exchange (NSE) have been mandated to setup Market SOC. Further, **small-size REs and Self-certification REs have been mandated to be onboarded on the Market SOC.**" Market SOC set-up timeline was Jan 1 2025; mandatory for NSE and BSE, optional for NSDL/CDSL.
- SOC functional efficacy: MIIs and Qualified REs half-yearly; "Other REs who are utilizing third-party managed SOC or Market SOC services" → annually, obtained from the SOC service provider.
- Aug 2025 §6.9 + FAQ Q.60: an RE in the small-size/self-certification bucket that **already has its own SOC** may leverage it instead of Market SOC, but must still submit the SOC efficacy report periodically.

**Critically [DATA]:** the CSCRF **Exemption Table (§8.1, p.77)** says the long list of exempted standards applies to self-certification and small-size REs **"provided they are onboarded to Market SOC."** The exemptions are *conditional*. An RE that skipped Market SOC arguably owes the full standard set.

### 3.6 Data classification, encryption, localisation [DATA]

**PR.DS.S1** (Data Security Standard 1): "Data-at-rest and Data-in-transit shall be protected. Strong data protection measures (for both at-rest and in-transit data), with industry standard encryption algorithms, shall be put in place by all REs." Guideline: "Data shall be encrypted in motion, at rest and in-use by using strong encryption methods… REs shall use industry standard, strong encryption algorithms (e.g., RSA, AES, etc.)."
→ **PR.DS.S1 IS in the exemption table** for self-certification and small-size REs (item 29 of Table 25). [DATA] So mandatory encryption-at-rest is *not* a CSCRF obligation for the smallest PM buckets (subject to Market SOC onboarding). [INFERENCE] It remains best practice and is likely required by DPDP "reasonable security safeguards" — different dimension.

**PR.DS.S2** (data classification + India localisation): "REs shall classify their data into Regulatory Data and IT and Cybersecurity Data as defined in this framework. REs shall keep the Regulatory Data and IT and Cybersecurity Data available and easily accessible in legible and usable form, within the legal boundaries of India."
→ **PR.DS.S2 is NOT in the exemption table** — so on the face of CSCRF it applies even to self-certification REs. [DATA]
→ **BUT it is in abeyance.** See §4.

**"Regulatory Data" definition [DATA, CSCRF Box Item 9 / Definitions p.28] — very wide:**
> "a. Data related to core and critical activities of the RE, as well as any **supporting/ ancillary data impacting core and critical activities**
> b. Data with respect to **communication between investors and REs through applications** (eg. chat communication, messages, emails etc.).
> c. Data that is required by the laws/ regulations/ circulars, etc. issued by SEBI and Govt. of India from time to time.
> d. Data that is deemed necessary or sensitive by the RE/ SEBI/ central or state government."

**"IT and Cybersecurity Data"** = logs and metadata about IT systems, *provided* they contain no Regulatory Data and no sensitive data (network architecture, vulnerability details, admin/privileged user details, password hashes, system configuration), and "it should not be ordinarily possible to generate Regulatory Data from IT and Cybersecurity Data."

**Design implication [INFERENCE]:** limb (a) — "supporting/ancillary data impacting core and critical activities" — is broad enough to capture an operational task tracker used to run client servicing. That is a real argument, not a stretch. Limb (b) captures anything that is investor↔RE communication. A ticket app that stores *only* internal employee tasks with opaque references is the strongest position; one that stores client correspondence is squarely Regulatory Data.

### 3.7 Software certification — the clause that most directly hits a hand-built app [DATA]

**PR.IP.S15:** "All software services in the form of SaaS/ Hosted services, COTS, customized COTS, **in-house developed software**, etc. shall be **certified for application security and functional audit**."

**PR.IP.S5:** "If the source code of software/ application is not owned by the REs, then in such a case, the REs shall obtain an undertaking/ certificate from the third-party service providers stating that their software/ application is free of known vulnerabilities, malwares, malicious/ fraudulent code and any covert channels."

**PR.IP.S2:** "A System Development Life Cycle to manage systems shall be implemented." **PR.IP.S3** (SDLC-adjacent config change control) — S3 *is* exempted for small/self-cert; **S15 and S13 are NOT.** [DATA, from the Table 25 code list: exempted PR.IP items are S3, S14, S16, S17 only]

**Design implication [OPINION]:** if this app is in CSCRF scope, "we wrote it ourselves over a weekend, on a free tier, and it isn't certified for application security" is a direct non-compliance with PR.IP.S15 that a cyber auditor will find. This — more than hosting location — is the sharpest CSCRF edge for a hand-built internal tool.

### 3.8 API security, RTO/RPO, other [DATA]

- CSCRF §(g) of the overview: "Application Programming Interface (API) security and Endpoint security solutions shall be implemented with **rate limiting, throttling, and proper authentication and authorisation mechanisms**." Reinforced by the May 2026 AI advisory.
- **RC.RP.S2 as clarified (Aug 2025 §6.10):** "Resumption within two hours (i.e. **two-hour RTO**)… REs shall design and test its systems and processes to enable the safe resumption of critical operations within two hours of a disruption, even in the case of extreme but plausible scenarios." And "**RPO for critical systems shall be 15 minutes**".
- **PR.DS.S4** (all REs): "REs shall enforce effective data protection, backup, and recovery measures"; block admin rights on end-user machines by default.
- **PR.IP.S8** (all REs): implement, test and maintain data backups; periodic restoration drills.
- **Zero trust** — PR.AA.S4 is exempted for small/self-cert; and Aug 2025 §6.2 softened it to "REs shall implement suggested strategies/ methodologies such as Zero-trust networks, segmentation, no single point of failure, high availability, etc.", IT-Committee approved.
- **Mobile app security** (PR.AA.S16) — Aug 2025 §6.3: "recommendatory (not mandatory)".
- **ISO 27001** — Aug 2025 §6.11: "Qualified REs are **encouraged and recommended (not mandatory)** to obtain ISO 27001 certification." Never applied to PMs anyway.
- **IT Committee** — required for all REs **except** small-size and self-certification REs (which are exempt from the quarterly-meeting periodicity, Table 15 item 5). But note many clarified obligations ("approved by IT Committee") assume one exists.
- **CCI (Cyber Capability Index)** — MIIs (third-party, half-yearly) and Qualified REs (self-assessment, annually) only. **Never a Portfolio Manager** (PM Qualified = N.A.). [DATA + INFERENCE]
- **Red teaming, threat hunting** — MIIs and Qualified REs only. Never a PM. [DATA + INFERENCE]

---

## 4. SEBI CLOUD FRAMEWORK — DOES DATA HAVE TO SIT IN INDIA?

This is the question that decides whether a free Supabase/Cloudflare tier is permissible. The answer has three layers and they do not all point the same way.

### 4.1 The SEBI Cloud Services Framework, Mar 6 2023 — does NOT list Portfolio Managers [DATA, secondary]

**Circular SEBI/HO/ITD/ITD_VAPT/P/CIR/2023/033, dated March 6, 2023**, "Framework for Adoption of Cloud Services by SEBI Regulated Entities (REs)". Addressed to **eight** categories:

> "Stock Exchanges, Clearing Corporations, Depositories, Stock Brokers through Exchanges, Depository Participants through Depositories, Asset Management Companies (AMCs)/Mutual Funds (MFs), Qualified Registrars to an Issue and Share Transfer Agents, KYC Registration Agencies (KRAs)"

**Portfolio Managers, Investment Advisers and Research Analysts are NOT in that list.** [DATA via taxguru reproduction — **flagged for primary verification**, this is load-bearing]

What it requires of those eight:
- "The data should reside/be processed **within the legal boundaries of India**." For foreign investors, "REs shall keep the original data/transactions/logs, available and easily accessible in legible and usable form, within the legal boundaries of India."
- "The cloud services shall be taken **only from the Ministry of Electronics and Information Technology (MeitY) empaneled CSPs**. The CSP's data center should hold a valid **STQC** (or any other equivalent agency appointed by Government of India) audit status."
- Expunging clause in the CSP agreement (secure permanent erasure of the RE's data in disks, backups, logs on demand); contingency and exit strategies.
- Immediate effect for new/proposed cloud onboarding; existing arrangements to be revised within 12 months, with milestone updates at 1, 3 and 12 months.

### 4.2 CSCRF pulls the cloud circular in — but ambiguously [DATA]

**PR.IP.S13:** "**For applicable cloud instances of REs**, SEBI circular 'Framework for Adoption of Cloud Services by SEBI Regulated Entities (REs)' shall be complied with."

CSCRF **Annexure-J** ("Framework for Adoption of Cloud Services") contains no independent text — it is a single pointer to the Mar 6 2023 circular and its URL.

**The ambiguity, stated honestly [INFERENCE]:** "applicable cloud instances" can be read (i) narrowly — the cloud circular applies to those REs to which it is addressed, so a PM has no "applicable cloud instances"; or (ii) broadly — CSCRF now imports the cloud circular for every RE's cloud usage. The narrow reading is supported by the fact that SEBI kept a *separate, differently-addressed* circular rather than folding its substance into CSCRF, and by CSCRF's own separate and weaker **"Hosted Service"** definition (§4.4 below) which uses "**at least equivalent standard of** MeitY Empanelment" rather than requiring actual empanelment. **I could not resolve this.** The Jun 11 2025 FAQs are titled "FAQs on CSCRF **and Framework for Adoption of Cloud Services by SEBI REs**" — that document, which I did not read, is the place this is most likely answered.

### 4.3 CSCRF's own India-storage rule is IN ABEYANCE [DATA — verbatim from primary]

Circular **SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/184, December 31, 2024**, para 2.3, quoted in full:

> "**2.3. Data Security Standard with regard to Data Localisation:**
> Based on the feedback received on the provisions of Data Localisation, a need is felt for further consultations. Accordingly, the guidelines and provisions with regard to Data Localisation [Data Security standard (PR.DS.S2)] **has been kept in abeyance until further notification**."

**Still in abeyance as at Aug 28 2025** [DATA]: circular 2025/119 Table 1 item 1 refers to "Data Classification (Regulatory Data, and IT and Cybersecurity Data) and Data Localisation (**currently in abeyance** vide SEBI circular SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/184 dated December 31, 2024)".

**No lifting notification found as at 2026-08-03.** [DATA — absence, from searching; not conclusive. Verify against SEBI's circular list before relying.]

**A drafting wrinkle worth flagging [INFERENCE]:** the Dec-2024 circular abates "Data Localisation [PR.DS.S2]". The Aug-2025 circular's table labels "Data Classification **and** Data Localisation" as currently in abeyance. Since PR.DS.S2 contains *both* the classification duty and the localisation duty in one standard, it is arguable that the classification duty is also suspended — but the Dec-2024 text only names "Data Localisation". Safest reading: **classify anyway; do not rely on the localisation abeyance as permanent.**

### 4.4 The provision that actually bites a free tier: "Hosted Service" [DATA, CSCRF Definitions p.27]

> "**Hosted Service** — Any IT/ SaaS provider rendering IT services/ SaaS solutions hosted on IT infrastructure either owned or controlled and managed by the service provider shall be broadly construed as hosted services. Hosted services have to fulfil the following technical specifications:
> 1. Data center that hosts IT services/ SaaS solutions shall be **ANSI/ TIA-942 rated-4 standard certified or equivalent (e.g. Tier 4)** with complete fault tolerance and redundancy for every component.
> 2. IT infrastructure shall atleast be of **equivalent standard of MeitY Empanelment** of Cloud Service offerings of Cloud Service Providers (CSPs) and audited by a **STQC empanelled cloud audit organisation or equivalent established international agency**.
> 3. **Summary of VAPT reports shall be made available to the REs and to the SEBI on demand.**
> 4. **If the data center is operated from outside the legal boundaries of India, then a copy of REs' data in human/ application readable form shall be maintained within the legal boundaries of India.**
> 5. Hosted service provider shall ensure that there is **no "Kill Switch"** available in the Application, which would remotely disable the functioning of the solution.
> 6. There shall be an explicit and unambiguous delineation/ demarcation of responsibilities… between the RE and Hosted service provider. The aforementioned delineation of responsibilities **shall be added explicitly in the agreement (as an annexure) signed between the RE and the CSP**."

### 4.5 Net answer on hosting [INFERENCE / OPINION]

1. **There is currently no in-force SEBI rule requiring a Portfolio Manager to store all its data in India.** PR.DS.S2's localisation limb is in abeyance, and the Mar-2023 cloud circular's data-residency + MeitY-empanelment mandate is not addressed to Portfolio Managers. [INFERENCE from two [DATA] points — subject to the PR.IP.S13 ambiguity in §4.2]
2. **But CERT-In independently requires 180 days of ICT logs within Indian jurisdiction** for any body corporate. That is a hard, live, non-SEBI constraint that a globally-distributed free tier may not satisfy. [DATA + INFERENCE]
3. **And item 4 of the Hosted Service spec requires an India-resident readable copy** whenever the hosting data centre is outside India — which is a *localisation-lite* rule that sits in CSCRF's *definitions*, not in the abated PR.DS.S2, so the abeyance arguably does not touch it. [INFERENCE — genuinely arguable both ways]
4. **The practical blockers on a free tier are contractual, not geographic:** items 2, 3, 5 and 6 above require a *signed agreement* with a delineation-of-responsibilities annexure, STQC-or-equivalent audit evidence, and VAPT summaries on demand. Free-forever self-serve tiers give you click-through terms, no negotiated annexure, and no audit artefacts. Plus PR.IP.S15 requires the in-house app itself to be certified for application security and functional audit. [INFERENCE, high confidence]
5. **Therefore [OPINION]:** the free-tier question is answered less by "is India-storage required" (currently: no, for a PM) and more by "can you produce the CSCRF paperwork for a hosted service and an application-security certification for your own code" (currently: no, on a self-serve free tier). The clean way through is to keep the app **out of CSCRF scope by design** (see §7), not to argue the hosting rules.

---

## 5. GRIEVANCE / COMPLAINT HANDLING (relevant only if this tool ever touches client complaints)

**Circular SEBI/HO/OIAE/IGRD/CIR/P/2023/156 dated September 20, 2023** — "Redressal of investor grievances through the SEBI Complaint Redressal (SCORES) Platform and linking it to Online Dispute Resolution platform". Addressed to "All SEBI Registered Intermediaries" and to the **Association of Portfolio Managers in India** among the Designated Bodies. [DATA]

Key obligations [DATA, from the extracted circular]:
- Entities "shall resolve the complaint within **21 calendar days** of receipt of the complaint" and "upload the ATR [Action Taken Report] on SCORES within **21 calendar days** of receipt of the Complaint."
- The ATR is auto-forwarded to the relevant **Designated Body** (Schedule II) — for Portfolio Managers, APMI. The Designated Body monitors ATRs, may seek clarifications, conducts first review, and maintains MIS.
- Escalation clocks run from ATR submission (a 15-day window for the complainant/Designated Body to seek review appears in the circular).
- Designated Bodies were to comply by December 4, 2023.

**Interaction with the PM Regulations [INFERENCE]:** Reg 11(d) gives "one month" to redress and requires the PM to keep SEBI informed of the "number, nature and other particulars of the complaints received". The SCORES circular's **21 calendar days** is stricter for SCORES-routed complaints. Any tool used for complaints must be built to the 21-day clock, not the one-month one.

**ODR:** the SCORES circular is expressly linked to SEBI's Online Dispute Resolution framework (circular dated Jul 31 2023). Not verified in detail — UNVERIFIED.

**Record-keeping:** the SCORES circular's express record duties fall on **Designated Bodies** (MIS), not on entities. The entity's record duty comes from **Reg 11(d)** (particulars of complaints received, reportable to SEBI) and from the practical need to evidence the ATR. [INFERENCE]

**Implication:** if client complaints are logged as tickets, the ticket log becomes a complaint record that SEBI/APMI can call for, on a 21-day clock, with reportable particulars. That is a materially heavier compliance posture than employee task tracking. **Keep complaints out of this tool.** [OPINION]

---

## 6. THE KEY DISTINCTION: (a) firm-level / (b) tool-if-client-data / (c) not applicable

### (a) Applies to the FIRM regardless of whether this tool exists

| Obligation | Source | Detail |
|---|---|---|
| Preserve enumerated books/records 5 years | PM Regs 27, 29 | Balance sheet, P&L, auditor's report, statement of financial position, investment-decision rationale records |
| Client-wise accounts + yearly audit | PM Reg 30 | Certificate to SEBI within 6 months of period close if specified |
| Submit to SEBI inspection of books/records | PM Reg 35, 40 | |
| Grievance redressal ≤1 month + report complaint particulars to SEBI | PM Reg 11(d), Reg 23(10) | |
| SCORES: resolve + ATR within 21 calendar days | Circular 2023/156, Sep 20 2023 | Designated Body for PMs = APMI |
| CSCRF, in the AUM-determined bucket | Circular 2024/113 + 2025/119 | ≤Rs 3,000 cr AUM ⇒ Self-certification RE |
| Annual VAPT by CERT-In empanelled auditor, commencing Q1 of FY | CSCRF §4.3, Table 18 | Self-cert REs: VAPT is the *only* audit required |
| Annual cyber audit (unless self-certification bucket) | CSCRF §4.4, Table 21 | "Rest of the REs" at least once a year |
| Market SOC onboarding | CSCRF Box Item 11; Aug-2025 §6.9 | Mandatory for small-size and self-certification REs; own SOC may be leveraged |
| Annual: cybersecurity policy review, risk-management policy, cybersecurity training; half-yearly access-rights and privileged-user reviews; annual COOP review and recovery drill | CSCRF Table 15 | Applies to "All REs" / "Other REs" |
| Self-certification return (Annexure-P) signed by MD/CEO/Board member/Partner/Proprietor | CSCRF §4.4.6 | |
| 180-day ICT logs, within India; 6-hour incident reporting | CERT-In Directions, Apr 28 2022, (ii) & (iv) | Binds any Indian body corporate |
| PMLA/KYC record retention | PMLA s.12; PML(MoR) Rules 2005 | **UNVERIFIED** period — believed 5 years |

### (b) Applies to THIS TOOL only if it holds client-related records

| Trigger in the tool | Consequence |
|---|---|
| A ticket carries data/facts/opinion behind an **investment transaction or recommendation** | Becomes a **PM Reg 27(1)(e)** record ⇒ 5-year preservation (Reg 29), producible on Reg 35 inspection, and required to be "under the hands of the Principal Officer" — which a free-for-all append log is not |
| The tool is used for **client complaints** | Becomes a complaint record; 21-day SCORES clock; Reg 11(d) particulars reportable to SEBI/APMI |
| The tool holds **client identity or transaction data** | PMLA/KYC retention; and squarely "Regulatory Data" |
| The tool holds **investor↔RE communication** (chat/message/email content) | Expressly "Regulatory Data", CSCRF Box Item 9(b) |
| The tool becomes the evidence that a **supervisory control operated** | Becomes an audit artefact the cyber auditor / SEBI inspection will call for |
| The firm also holds an **IA registration** and advice or its rationale lands in a ticket | IA Reg 19: advice (even oral) and rationale (signed and dated) ⇒ 5 years; digitally signed if electronic |

### (c) Does NOT apply at all (to a Portfolio Manager building this)

| Not applicable | Why | Confidence |
|---|---|---|
| SEBI Cloud Services Framework Mar-2023 (MeitY empanelment, STQC, mandatory India residency) | Addressed to 8 RE categories; Portfolio Managers and IAs are not among them | [DATA] on the addressee list (secondary source); **weakened by the PR.IP.S13 "applicable cloud instances" ambiguity** — treat as likely-not-applicable, not settled |
| CSCRF data localisation (PR.DS.S2 localisation limb) | Kept in abeyance until further notification, Dec 31 2024; still in abeyance as at Aug 28 2025 | [DATA], verbatim from primary |
| Cyber Capability Index (CCI) | MIIs and Qualified REs only; PM Qualified = N.A. | [DATA] |
| ISO 27001 certification | MIIs/Qualified REs only — and now "encouraged and recommended (not mandatory)" even for them | [DATA] |
| Red teaming, threat hunting, quarterly access reviews | MIIs and Qualified REs only | [DATA] |
| Cyber audit (as distinct from VAPT) | Self-certification REs: "no other audit is required" | [DATA] |
| Mobile app security guidelines | "recommendatory (not mandatory)" per Aug-2025 §6.3 | [DATA] |
| Encryption-at-rest as a CSCRF mandate | PR.DS.S1 is in the exemption table for self-cert and small-size REs (conditional on Market SOC onboarding) | [DATA]. Still best practice; DPDP may require it separately |
| Quarterly IT Committee meetings | Table 15 item 5 excludes small-size and self-certification REs | [DATA] |
| SEBI RA record duties | Only if the firm holds an RA registration | [DATA] |

### 6.1 Testing the hypothesis "a tool holding only employee task data sits almost entirely outside SEBI's scope"

**Verdict: the hypothesis is HALF right, and it fails on one specific clause.** [INFERENCE]

**Where it holds:** SEBI's *record-keeping* regime is a closed enumeration. PM Reg 29 preserves only what "this chapter" enumerates. Employee task data is not in Reg 27(1), not in IA Reg 19, not in RA Reg 25. So a tool holding only employee task data creates **no new record-retention obligation, no new inspection exposure over its content, and no new reporting duty.** That part of the hypothesis survives.

**Where it fails:** CSCRF's *cybersecurity* regime is **not** keyed to data sensitivity. The "Critical Systems" definition catches "**d. Internet facing applications/ systems**" flatly, and the Aug-2025 clarification extends the net to "any other system which is on the same network segment where systems mentioned in para (a) to (e) are deployed". Add **PR.IP.S15** ("in-house developed software… shall be certified for application security and functional audit"), which does not care what the software does. So an internet-facing, in-house-built app on a covered RE's estate is inside CSCRF scope **on the basis of its architecture, not its contents.**

**The escape route, and why it is weak:** the Aug-2025 **Principle of Exclusivity** says "The scope of CSCRF shall be limited to only those systems/ applications/ infrastructure/ processes which are exclusively used for SEBI regulated activities." Read alone, that would put an employee-task tool outside scope. But the principle sits in **Part A: "Principles for SEBI REs under multiple regulators' purview"** and its stated rationale is REs that are also RBI-regulated banks. Relying on it for a single-regulator Portfolio Manager is an **arguable but unsupported** stretch. [INFERENCE — this is the single most important legal ambiguity in this dimension, and it is the one worth putting to the Compliance Officer in writing]

---

## 7. PRACTICAL: WHAT KEEPS THIS TOOL OUT OF SCOPE, AND WHAT DRAGS IT IN

### 7.1 Keeps it OUT of SEBI regulated-records scope

1. **Opaque client references only.** No client name, PAN, folio, account number, holding, or amount. The `client_ref` → client mapping lives in the existing regulated system, never in this app, and never in a ticket title. Enforce it as **input validation**, not policy: reject PAN-shaped strings, reject 10+ digit numbers, cap field lengths.
2. **No investment rationale, ever.** This is the Reg 27(1)(e) / IA Reg 19 trapdoor. Design the status "punch" as *structured status codes + a short next-action field* with a hard character cap, not a free-text narrative box. Show an inline warning: "do not paste research, recommendations, or reasoning here."
3. **No client complaints.** Hard-code the absence of a "complaint" ticket type, and put it in the app's own README/usage note. Complaints stay in the compliance/SCORES workflow.
4. **Pointer, not system of record.** A ticket should say *"refresh the IPS for client_ref 4471; the record itself lives in <regulated system>"*. The moment the ticket log *is* the evidence, retention flips from your choice to 5 years and SEBI's inspection right attaches.
5. **Short, documented retention + disposal.** CSCRF requires a data-retention and data-disposal policy of all REs anyway. Pick 12–24 months for tickets, write it down, and implement the deletion. A short retention is affirmative evidence that this is not a books-and-records system.
6. **Keep it off the internet if you can.** Limb (d) of Critical Systems is "internet facing applications/ systems". An app reachable only from the corporate network / via the firm's existing VPN is a materially different classification argument than a public URL. This is the highest-leverage single design decision. [OPINION]
7. **Get a written classification decision BEFORE building.** A one-page memo from the Compliance Officer / Principal Officer stating (i) the firm's CSCRF bucket, (ii) whether this app is in or out of CSCRF scope, and (iii) on what basis, is the cheapest control available and the only thing that protects the builder personally. An APM building shadow IT on the regulated estate without it is the real risk here, not the hosting tier. [OPINION]

### 7.2 Drags it IN

1. **A public internet URL** ⇒ Critical System by CSCRF limb (d) ⇒ VAPT scope, MFA, 2h RTO / 15min RPO, asset inventory, PR.IP.S15 certification.
2. **Sharing a network segment** with any system in limbs (a)–(e) ⇒ caught by the clarified limb (f).
3. **Any client-identifying field**, or any free-text that in practice carries client detail ⇒ Regulatory Data; and if it carries decision reasoning ⇒ Reg 27(1)(e).
4. **Complaint handling** ⇒ SCORES record, 21-day clock, reportable particulars.
5. **Being cited in an audit** as evidence a control operated ⇒ becomes an audit record with its own production duty.
6. **Storing investor↔RE messages** ⇒ Regulatory Data, Box Item 9(b), expressly.
7. **The firm crossing Rs 3,000 cr AUM** ⇒ next financial year the bucket moves from Self-certification (VAPT only) to Small-size (annual cyber audit as well), and the exemption list applies only if Market SOC onboarding is done.

### 7.3 If it lands IN scope, the concrete bill

- Annual VAPT by a **CERT-In empanelled** IS auditing organisation, covering application VA (internal + external), external PT, API security testing, and cloud-deployment VAPT (Annexure-L). Report within 1 month of completion; findings closed within 3 months; revalidation within 5 months. Re-VAPT after every "major release" — including **"any changes in policy of login and/ or password management"**.
- **MFA** that an auditor will accept. Email magic-link alone is unlikely to qualify. Add TOTP at least for admin/manager roles.
- **Application-security and functional-audit certification** of the in-house code (PR.IP.S15).
- **180-day audit logs, in India** (CERT-In), separate from the business status log.
- **2-hour RTO / 15-minute RPO** design and testing — which no free tier will underwrite.
- Inclusion in the asset inventory, the risk register, and the self-certification return (Annexure-P) signed by the MD/CEO.

**[OPINION] The honest read:** none of this is prohibitive *if* the firm already runs a CSCRF cadence and the app is folded into the existing annual VAPT. What is not survivable is building it quietly, on a public URL, and having a CERT-In empanelled auditor discover an uncertified in-house internet-facing application with single-factor login and no SLA. The compliance cost of doing this properly is mostly *paperwork the firm already produces*; the cost of doing it invisibly is an audit observation with the builder's name on it.

---

## 8. OPEN QUESTIONS (the decisive unknowns)

1. **Ionic Wealth's Portfolio Manager AUM as at the previous financial-year end.** This single number sets the CSCRF bucket: ≤Rs 3,000 cr ⇒ Self-certification RE (VAPT only, no cyber audit); >Rs 3,000 cr and <Rs 10,000 cr ⇒ Small-size RE (annual cyber audit too); ≥Rs 10,000 cr ⇒ Mid-size RE. **UNVERIFIED — I did not look up the firm's AUM and will not guess.** Everything category-dependent above hinges on it.
2. **Which SEBI registrations the entity actually holds.** PM only? PM + non-individual IA (⇒ that entity is Small-size RE by status, regardless of AUM)? Any RA registration? Mutual-fund *distribution* under an ARN is not a SEBI IA registration — do not conflate them.
3. **Is the firm or its group under any other regulator (e.g. RBI)?** If yes, the **Principle of Exclusivity** (Aug-2025 §5.2) is squarely available and is the strongest argument for putting an employee-task tool outside CSCRF scope. If SEBI is the only regulator, that argument is much weaker.
4. **Is the firm onboarded to Market SOC?** The CSCRF Exemption Table's relief for small-size and self-certification REs is expressly conditional on it.
5. **The Jun 11 2025 CSCRF FAQs** (`sebi.gov.in/sebi_data/faqfiles/jun-2025/1749647139924.pdf`) — titled "FAQs on CSCRF **and Framework for Adoption of Cloud Services**". Not read. This is the most likely place to resolve whether the Mar-2023 cloud circular reaches Portfolio Managers via PR.IP.S13.
6. **Has the PR.DS.S2 data-localisation abeyance been lifted since Aug 28 2025?** I found no lifting notification, but absence-of-search-result is not proof. Check SEBI's circular list for ITD-1/ITD_CSC_EXT circulars issued Sept 2025 – Aug 2026.
7. **Was RA Regulation 25 amended** by the Dec 16 2024 / Feb 10 2025 amendments? My verbatim text is the 2014 gazette.
8. **Is the May 5 2026 AI Vulnerability Detection Advisory binding or advisory?** Secondary sources disagree — one says the obligations are "enforceable" under s.11(1), another says it "frames recommendations rather than binding mandates". SEBI primary not fetched.
9. **The Mar-2023 cloud circular's addressee list** is load-bearing for the "free tier is permissible" conclusion and I have it only from a secondary reproduction. Verify against the SEBI PDF.
10. **The firm's own IT/InfoSec policy and shadow-IT rules.** [OPINION] For a 10–50 person app built by an APM, internal policy is almost certainly the binding constraint that bites first — long before SEBI does. Ask before building.
