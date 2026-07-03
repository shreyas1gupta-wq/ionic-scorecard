---
name: data-check
description: Run Kavya Reddy's (Data Officer) verification protocol on a dataset — new-source D-009 gate, freshness ping, or schema audit. Use for /data-check <path|source>, "verify this data", or before ingesting anything new.
---

# /data-check — Data Officer protocol

1. Read `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_QUALITY_RULES.md` (landmines + protocol) and `DATA_CATALOG.md`.
2. For an EXISTING dataset: verify path, row count, date range vs catalog; run freshness rules (periods-per-year, not just max-date); check the dual-schema branch if under stocks_options/. Report drift; update the catalog entry.
3. For a NEW source (D-009 — Principal must have approved the fetch): sample 100 rows → schema/dtypes/nulls/dupes/date-monotonicity/PIT-safety; cross-check 5 values vs an independent source; verdict USE/QUARANTINE + draft catalog entry for Principal sign-off. NEVER bulk-ingest before the verdict.
4. Cheap tier (haiku) — this is mechanical; escalate to sonnet only on ambiguous verdicts. Log outcome in the journal if state-changing.
