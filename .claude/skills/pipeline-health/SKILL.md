---
name: pipeline-health
description: All scheduled jobs + pipelines health check — capture task, backfills, results-dir integrity, script guards. Use for /pipeline-health, weekly ops cadence, or after any data incident.
---
# /pipeline-health — owner: Manoj Pillai (ops-engineer-manoj-pillai)
1. Spawn Manoj (or main-loop): AngelDailyOptionCapture log health; 05_DATA_OFFICE/scripts/ guard imports present (L1-L7b); results/ dirs conform (config.json lineage complete); no orphaned scratchpad code.
2. Broken → fix ≤15min or file to CURRENT_STATE next-actions with owner. Report one table.
