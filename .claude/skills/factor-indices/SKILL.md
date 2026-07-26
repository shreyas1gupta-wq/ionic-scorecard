---
name: factor-indices
description: Refresh official NIFTY factor-index closes (momentum/value/quality/lowvol/alpha + broad + equal-weight) AND rebuild the Principal's FACTOR_NAVS.xlsx (fixed column order, traded days only). Use for /factor-indices [start end], the 16th+29th monthly refresh, "update factor navs", or before any factor-replication work. Index leg from niftyindices needs HOME NETWORK (office proxy strips cookies); the NSE-official + AMFI legs work at the office.
---
# /factor-indices — owner: Kavya (data) / Manoj (ops)

## The deliverable: FACTOR_NAVS.xlsx (Principal's workbook)
`python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/build_factor_nav_excel.py`
→ `09_PRODUCT/reports/FACTOR_NAVS.xlsx`. RULES (Principal 2026-07-26, do not regress):
- **Column order FIXED, lead 8 first:** NAV Date | NIFTY 200 Momentum 30 | Nifty Midcap
  Momentum 50 | Nifty Smallcap Quality Momentum 100 | NIFTY 200 Quality 30 | GOLDBEES |
  HDFC Liquid Fund(G) | NIFTY 100 Low Vol 30 | NIFTY 200 VALUE 30 — everything else after.
- **TRADED DAYS ONLY:** a row exists only where an NSE index printed a close; weekend/
  holiday rows where just the liquid fund accrues are dropped (NSE special sessions —
  Muhurat etc. — legitimately keep their weekend dates). Filter is in the builder.
- If the target xlsx is open in Excel, the builder versions up (_v2) — never fight the
  lock; delete the stale copy once the Principal closes his.

## Data layers (merged in the builder, newest wins)
1. **SEED** `datasets/nifty_factor_indices/factor_navs_seed.csv` — Principal's own
   history (2005-04-01 → 2026-01-05; copied from Mf_qfra2 into the firm tree).
2. **NSE-official parquet (PRIMARY index extension, OFFICE-OK)**
   `datasets/index_daily/nse_official_all_indices.parquet` — EOD-maintained, carries
   ALL factor indices; mapped by normalized name (`NSE_ALIAS` in the builder).
3. **niftyindices downloader (secondary)** `nifty_indices_download.py [start end]` —
   the Principal's reference scraper, firm-adapted (truststore + parquet; headers
   synced EXACTLY to his reference incl. Sec-Fetch-* + Accept-Encoding).
   **Office proxy STRIPS COOKIES → the site's anti-bot serves an HTML shell
   (root-caused 2026-07-26: warm-up GET returns 0 cookies). HOME NETWORK ONLY.**
4. **AMFI daily NAVs (OFFICE-OK)** for GOLDBEES + HDFC Liquid Fund(G) — per-house
   history in **30-day chunks** (90-day chunks time out on the proxy), cached under
   `datasets/mf_nav/daily_cache/`. **House codes probed empirically: HDFC=9,
   Nippon India=21** (mf= param). Filter = Regular Growth plan only (no IDCW/Direct/
   premium/bonus/unclaimed).

## Cadence
**16th + 29th of every month, 08:33** (OPERATING_CALENDAR §automatable; session cron
re-armed by DESK-100). Each run: builder (always works for NSE+AMFI legs) + the
niftyindices leg only when off-proxy; flag a blocked index leg in CURRENT_STATE.

## Gotchas that already bit (2026-07-26)
- Extension windows must anchor to the ORIGINAL seed cut captured BEFORE any layer
  extends the frame — the first extension advances index.max() and starves the next
  (bit twice: GOLDBEES then HDFC Liquid fetched 1 row).
- A failed/partial fetch that caches even one row poisons the resume (cache max-date
  skips everything) — delete the scheme's daily_cache parquet to force refetch.
- After any refresh: /data-check freshness ping + catalog date update. Source approved
  by Principal (D-024; Principal-contributed scraper).

## Downstream
- Factor-replication deviation harness (ideas/20260704_factor_index_replication.md).
- **TRI rebuild of MF Dashboard Indices sheet** (critical audit finding 2026-07-26:
  sheet is PRI — SELLs suppressed ~1.2-1.5pp/yr) — needs the niftyindices TRI leg or
  an equivalent official TRI source, BEFORE the Oct-end QFRA run.
