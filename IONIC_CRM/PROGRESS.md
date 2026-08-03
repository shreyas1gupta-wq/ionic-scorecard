# IONIC_CRM — Progress Checkpoint

**Goal:** Internal ticket/status-tracking web app for ~10–50 Ionic Wealth employees. Tickets with deadlines, append-only status punches, manager/admin dashboards. Zero rupees. Maximum defensible compliance posture.

**Last updated:** 2026-08-03

---

## Settled decisions

| # | Decision | Reasoning |
|---|---|---|
| D1 | **GitHub is NOT the database** | Git history is permanent → right-to-erasure becomes unachievable. No row-level access control (repo read = every ticket, all history). Concurrent writes = merge conflicts / lost writes. GitHub Pages is static-only and can't be access-gated on the free plan. |
| D2 | **GitHub IS the encrypted backup target** | Nightly encrypted dump committed to a private repo. Ciphertext in git history is harmless — permanence becomes an asset. Satisfies "our data on our GitHub" defensibly. |
| D3 | **Excel on the company drive is NOT the backend** | Single-file lock (no row-level lock, no atomic append, no transaction) → conflicted copies at 10–50 writers. File permissions are all-or-nothing → no per-user visibility. Unreachable from an internet-hosted app except via Graph, which needs IT. Silently editable → destroys the audit case. Scale is *not* the objection. |
| D4 | **Auth = admin-issued credentials + TOTP 2FA** | Reverses an earlier call for email OTP. Without DNS access to `ionic.in`, no third-party mailer can pass SPF/DKIM alignment, so M365 anti-spoofing junks the firm's own login emails. TOTP needs no email at all and resists phishing better than emailed codes. |
| D5 | **Tamper-evidence via hash-chained audit log + crypto-shredding for erasure** | Each entry hashes the previous → any edit/deletion of history is detectable. Daily root hash anchored externally. Erasure served by destroying a subject's key, not their rows — so immutability and deletability coexist. This is what git-as-database could never do. |
| D6 | **Data layer behind one repository interface** | Nothing touches the store directly. Makes a later migration to company-tenant storage one adapter, not a rewrite. This is what makes "build now, involve IT later" safe. |
| D7 | **No client PII, ever — `client_ref` is an opaque code** | Keeps the tool outside client-PII scope at zero cost now; expensive to retrofit. Policy not enforcement — mitigated by warnings + field encryption. |

## Confirmed context

- Company is on **Microsoft 365**. IT involvement **not** available for now (Principal's call) → graduation path to SharePoint List storage + Entra ID SSO exists for later.
- 10–50 users. Budget **₹0**, hard.
- Frontend must be a **proper website**, not a spreadsheet UI.
- Client-data exposure **unresolved** → designed out via D7.

---

## DONE

- [x] Options survey: no-code / off-the-shelf / build-and-host-free / self-host (4 routes, trade-offs)
- [x] GitHub-as-datastore question answered (D1, D2)
- [x] Excel-on-company-drive question answered (D3)
- [x] Auth model settled and an earlier error corrected (D4)
- [x] `REQUIREMENTS.md` written — technology-free, survives any research outcome

## IN FLIGHT

- [ ] Workflow `wf_a752f0e0-d12` (11 agents): DPDP obligations · SEBI record-retention + CSCRF applicability · GitHub-as-DB verification · free-tier limits · templates & fork-vs-build · features + security architecture. → `CRM_DESIGN_BRIEF.md`
- [ ] Workflow `wf_bc7f2dc7-7e1` (6 agents): Excel-via-Graph viability · SharePoint Lists as backend for a custom frontend · whether a non-admin can self-register an Entra app

Both write findings to the session scratchpad as `research-*.md`.

## NEXT STEP (exact)

1. Read the two workflow briefs when they land; note any claim they overturn, including my own.
2. Write `DESIGN.md`: architecture, data model, security controls, compliance posture, fork-vs-build verdict.
3. Principal reviews `REQUIREMENTS.md` + `DESIGN.md`.
4. Only then: implementation plan, then code.

## Open for Principal

- Sequencing of firm sanction (build-then-demo vs ask-first)
- Do managers see all reports' tickets, or only those they assigned?

---

## Output paths

- `IONIC_CRM/REQUIREMENTS.md` — what it must do (drafted)
- `IONIC_CRM/DESIGN.md` — how (pending research)
- `IONIC_CRM/PROGRESS.md` — this file
