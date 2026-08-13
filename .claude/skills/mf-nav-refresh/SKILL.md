---
name: mf-nav-refresh
description: Pull the latest official AMFI NAVs for all Indian mutual funds (13,900+ schemes) into datasets/mf_nav/ — nav_latest.parquet cross-section + permanent month-end history — with auto-pruning so storage never grows. Use for /mf-nav-refresh, "refresh NAVs", before any qfra1/qfra2 run, or on the monthly data cadence.
---
# /mf-nav-refresh — owner: Kavya (data) · ~0 tokens, script does everything
```
python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_nav_refresh.py [--digest]
```
- Source: `portal.amfiindia.com/spages/NAVAll.txt` (official; VERIFIED working on the office proxy 2026-07-25, ~14k schemes).
- Outputs in `datasets/mf_nav/`: `nav_latest.parquet` (full cross-section) · `nav_monthend.parquet` (permanent month-end history, one row set per month, tiny) · gz raw snapshot.
- **Retention (Principal rule): raw snapshots auto-deleted after 180 days**; month-end history kept forever; defunct/side-pocketed 0-NAV rows dropped at parse.
- D-009 checks built in: row-count floor, NAV-range sanity, <2% of schemes moving >15% between refreshes (else the run aborts loudly).
- Token discipline: never read the parquet into chat — scripts consume it; `--digest` writes a 6-line `NAV_DIGEST.md` if the model needs a summary. Any agentic processing of these files = Haiku.
- Downstream: `/qfra1-rerun` (capture-ratio engine), `/qfra2-rerun` (long-term SIP), `/mf-lookthrough`.

## Automation (Principal 2026-07-26)
Runs automatically on the 1st of every month, 08:10 (OPERATING_CALENDAR §automatable; DESK-100 re-arms the session cron at start). Month-end history must accrue monthly even though the fund models run at Apr-end/Oct-end (Principal 2026-07-26).
