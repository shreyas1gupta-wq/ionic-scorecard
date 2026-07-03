# OPS OPEN ISSUES — owner: Manoj Pillai (E-023). One row per defect; close with commit ref.

| # | Opened | Component | Defect | Severity | Owner | Status |
|---|---|---|---|---|---|---|
| OPS-1 | 2026-07-04 | execution_scanner.py | Back-month (25AUG) leg strikes generated from FRONT-month grid, not snapped to the listed chain -> M&M 3160 PE didn't exist (listed: 3120/3150/3200). Sheet shipped an untradeable instrument. FIX: snap every generated strike to nearest key in `chain` for THAT expiry; assert token exists before writing a leg. Interim: backfill_blank_pe.py remapped 3160->3150 (annotated in iv_source). | MED | Manoj | OPEN |
| OPS-2 | 2026-07-04 | execution_scanner.py | Back-month PE legs got NO quote at all (scanner prices front-month only) -> 8 blank live_price rows. FIX: include back-month tokens in the bulk_ltp pass. Interim: backfill_blank_pe.py (reusable). | MED | Manoj | OPEN |
| OPS-3 | 2026-07-04 | results tree | Stray `Shreyas_Ionic_AMC/results/` created by task briefs with relative paths; consolidated into canonical root `results/` same day. FIX: task briefs must give absolute paths (README rule added). | LOW | all | CLOSED (c7fa0c4+) |
