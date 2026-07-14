**Verification protocol before a third-party quarterly fundamentals dataset (India, 2005–present, ~2000 companies, with announcement dates) is allowed near a backtest**

**1. Sampling and cross-checks against ground truth**
- Stratified random sample of 150–250 (company, quarter) pairs, stratified by market-cap decile, sector, and era (pre-2010 / 2010–2015 / 2015–2020 / 2020–present), since vendor data quality is rarely uniform across time or cap size.
- For each sampled row, pull the actual filed result (exchange filing / annual report / investor presentation) and diff every reported field: revenue, EPS, reported date. Track a field-level error rate, not just a pass/fail per row — some fields (revenue) are usually cleaner than derived ones (adjusted EPS, segment-level numbers).
- Cross-check a subset against a second independent source (a different data vendor, or the company's own investor-relations XBRL filing) to catch systematic vendor-specific errors that a single-source check would rubber-stamp.

**2. Testing that announcement dates are genuinely point-in-time**
- For the sampled rows, find the actual public disclosure date/time from the exchange filing system (NSE/BSE corporate announcements) and compare to the vendor's `available_date`/`announcement_date` field. Flag any row where vendor date is *earlier* than the true public filing date — this is the dangerous failure mode (it manufactures lookahead) versus vendor date being *later* (merely conservative/costly, not corrupting).
- Check for a suspicious pattern: is the vendor's announcement date suspiciously always "quarter-end + fixed N days" for every company (a strong tell they backfilled from a template/estimate rather than tracking the actual filing) rather than the genuinely variable real-world lag (which ranges roughly 15–60 days and varies company to company and quarter to quarter)?
- Explicitly test post-facto restatements: does the vendor overwrite a quarter's historical figures when a company later restates, losing the *originally reported* number? A backtest must use what was known at the time, not the eventually-restated "true" figure — verify the vendor exposes (or at least doesn't silently mutate) as-originally-reported values.

**3. Coverage and survivorship checks**
- Reconcile vendor company count and identifiers, quarter by quarter, against the historical NSE/BSE listed-universe count for that quarter — if the vendor's earliest years show materially fewer companies than the exchange's actual listed count for that period, that's a coverage gap concentrated in the past (classic survivorship signature).
- Explicitly check whether delisted/merged/renamed companies are present with their historical data intact, or whether they silently vanish from the dataset the moment they stop being "current" (query the vendor for 20–30 known-delisted names and confirm their historical quarters are still retrievable).
- Check for "look-ahead-friendly" gaps: quarters with suspiciously fewer NA/missing fields in early years than plausible given actual filing quality at the time (over-clean historical data is a red flag for backfilled/estimated figures).

**4. Quarantine / acceptance rules**
- Quarantine (do not admit to any backtest) any field/era/sector stratum where the sampled error rate exceeds a pre-set threshold (e.g., >2% of numeric fields materially wrong, or any confirmed instance of an `available_date` earlier than the true filing date).
- Accept only strata that pass both the value-accuracy check and the PIT-date check; document acceptance per (field, era, cap-bucket) rather than as a single dataset-wide yes/no, since it is normal for one vendor to be fine post-2015 and unreliable pre-2010.
- Re-run the full sampling check any time the vendor pushes a "data refresh" — a silent methodology change in a refresh is a common way clean data quietly becomes contaminated.