---
name: news-sweep
description: Parallel sector-analyst news/risk sweep over a list of stocks (before selling vol or sizing positions). Use for /news-sweep <stocks>, "check news risk", "any catalysts on these names".
---
# /news-sweep — sector risk flags
1. Bucket the names by sector; spawn the matching analysts IN PARALLEL (respect desk limits: DESK-100 ≤6, DESK-20 ≤2): meera (financials), karan (IT/new-age), sneha (pharma), rohan (industrials/defence), priya (consumer/auto); ananya covers the rest.
2. Each returns per stock: catalyst found (one line + date), earnings date if known, RISK FLAG HIGH/ELEVATED/NORMAL + one-line rationale (their persona files carry the sector lessons).
3. Merge into a single table + a macro note (expiry, RBI/Fed, tariff-type windows). Feed conviction scoring (`final_execution.py` NEWS overlay) and file the table into `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/`.
