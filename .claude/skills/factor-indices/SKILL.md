---
name: factor-indices
description: Download/refresh official NIFTY factor-index closes (momentum/value/quality/lowvol/alpha + broad + equal-weight) from niftyindices.com — the validation benchmark for factor replication. Use for /factor-indices [start end], monthly refresh, or before any factor-replication work. HOME NETWORK ONLY (office proxy blocks the API).
---
# /factor-indices — owner: Kavya (data) / Manoj (ops)
1. Run: `python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/nifty_indices_download.py [DD-Mon-YYYY DD-Mon-YYYY] [--xlsx]` — 21 indices, merge-dedupe into `datasets/nifty_factor_indices/factor_indices_close.parquet`.
2. **Office proxy BLOCKS this API** (verified 2026-07-04) — run on the home-network day; script exits loudly if blocked.
3. After any refresh: /data-check freshness ping + catalog date update. Source approved by Principal (D-024; Principal-contributed scraper).
4. Downstream: factor-replication deviation harness (ideas/20260704_factor_index_replication.md).
