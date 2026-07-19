# S6 — NO-NEGATIVE-NEWS SCREEN (1M relative scorecard quality gate)
Owner: ml-expert-ishaan-gupta · 2026-07-18 · [DATA]/[INFERENCE] tagged inline

**Role in the scorecard:** this is a QUALITY GATE for the 1M relative scorecard's
momentum+earnings candidate list, not an alpha signal. Purpose: don't let the
1M leg buy into a name with fresh, material adverse news. FM lens applied:
every category below is something a PM would want flagged before sizing a
position, not a statistically-clever construct.

## 1. Data source + schema (verified on disk)
- Path: `datasets/india_fin_news/tier_segregated_news.csv` (1.19 GB, 125,511
  lines incl. header — **verified via `wc -l`**).
- Schema: `date, symbol, direct_news, sectoral_news, global_news`. `direct_news`
  is a `" || "`-joined concatenation of that symbol's headline+snippet items
  scraped for that calendar date from four sources (moneycontrol,
  businessstandard, economictimes, financialexpress — raw per-source files
  also on disk under `datasets/india_fin_news/raw/`).
- **[DATA] Grid, not article count:** the file is a complete daily grid of
  **55 symbols × 2,282 calendar days (2020-01-01 → 2026-03-31)** =
  125,510 rows — confirmed by `df.shape`, `nunique(symbol)==55`,
  `nunique(date)==2282`, and every symbol having exactly 2,282 rows. The
  `news_sentiment.csv` file (the "125K docs" cited in DATA_CATALOG.md) is
  row-aligned to this same grid — it is FinBERT tone scores derived from it,
  not 125K distinct articles. **The DATA_CATALOG "125K docs" description is
  misleading**; flagging for Kavya Reddy (Data Officer) to correct.
- Universe covered: **55 symbols only** — current-ish NIFTY50 constituents
  (ADANIENT, RELIANCE, TCS, HDFCBANK, ... full list in build script). This is
  **NOT NIFTY500 coverage.**
- I did not use `news_sentiment.csv` (pre-aggregated FinBERT pos/neu/neg tone)
  as the primary source, because generic negative *tone* is not the same as a
  specific adverse *event* (profit warning, fraud, auditor resignation, etc.)
  — the task calls for event-type detection, so I went to the underlying
  `direct_news` text and built a deterministic keyword/rule classifier on it.
  `sectoral_news`/`global_news` columns were NOT used — they are sector/market
  wide, not company-specific, and would false-positive every stock in a
  sector on the same day.

## 2. Method — deterministic rule-based severity tagging
Script: `ALPHA_RANKER/rnd/scorecard/build_no_negative_news_screen.py`. Pure
regex/keyword matching (case-insensitive) over `direct_news` text — no ML
model, no randomness, no LLM call, so it is trivially deterministic (same
input → same output, every run).

8 categories, each with a severity weight (3 = most severe, 1 = least):

| Category | Severity | Examples of trigger phrases |
|---|---|---|
| FRAUD_ACCOUNTING | 3 | fraud, forensic audit, accounting discrepancy/irregularity, Hindenburg, whistleblower, stock manipulation, siphoning/diversion of funds |
| AUDITOR_RESIGNATION | 3 | auditor resigns/steps down/withdraws |
| REGULATORY_ACTION | 2 | SEBI bars/order/penalty, RBI bans/restricts, ED/CBI raids, license cancelled |
| CREDIT_DOWNGRADE | 2 | rating-agency (CRISIL/ICRA/CARE/Moody's/S&P/Fitch) downgrade, outlook to negative, default on interest/repayment |
| PROMOTER_ISSUE | 2 | promoter pledge INCREASE/invocation, promoter stake sale, promoter/founder resignation or arrest |
| GUIDANCE_CUT | 2 | guidance cut, profit warning, missed estimates, loss widens |
| LITIGATION | 1 | lawsuit, class action, court order against, fined |
| MGMT_EXIT | 1 | CEO/CFO/MD resignation |

Output fields per (date, symbol):
- `negative_severity_raw` — max severity of same-day hits (0 if none).
- `negative_severity_trail20` — rolling max of `negative_severity_raw` over a
  **trailing 20-row window (current day + up to 19 prior rows in the daily
  grid), per symbol**. This is the field meant to gate a 1M-horizon
  candidate list (a profit warning from 3 weeks ago should still keep a name
  out, not just on the day it broke).
- `no_negative_news_flag` = `negative_severity_trail20 == 0` (True = passes
  the gate).
- `negative_event_categories` — pipe-joined category tags for audit.
- `matched_snippet` — ±60 chars around the highest-severity match, for
  human audit trail.
- `direct_news_available` — whether this (symbol, date) had ANY direct-news
  text at all (coverage flag, see §4).

## 3. PIT handling
- The source `date` column has no intraday timestamp — **treated
  conservatively as EOD-available per requirement**: a hit on date `T` is only
  safe to use for a decision made at or after `T`'s close, i.e. usable for a
  **T+1** entry decision, never a same-day-open decision. This must be
  enforced by whoever joins this table into the scorecard (lag by 1 trading
  day before using `no_negative_news_flag` as an entry filter).
- `negative_severity_trail20` is a per-symbol trailing rolling-max over the
  row-ordered date grid — it only ever looks backward (verified: pandas
  `.rolling(window=20, min_periods=1)` is right-aligned/backward by
  construction; also spot-checked below that pre-event windows are clean).
- No forward fill, no shifting into the future at any step.

## 4. Default / coverage semantics (explicit, per requirement)
Two categories of "not flagged" must NOT be conflated:
1. **Genuinely clean**: `direct_news_available == True` and
   `negative_severity_trail20 == 0` → real signal, stock had news coverage
   and none of it was adverse. Safe to treat as "clean."
2. **No coverage**: `direct_news_available == False` for that date, OR the
   (symbol, date) pair simply has **no row** in this table because the
   symbol is one of the ~445 NIFTY500 names outside the 55-symbol universe.
   **Default decision (documented, not silent): treat as "clean" (no
   penalty) for scorecard purposes**, because the alternative (blocking a
   stock for lack of data) would silently gut the candidate universe down to
   55 names. **This is a deliberate default, not a verified fact** — a name
   in category 2 has NOT been checked for bad news; it is passed by default,
   not certified clean. [INFERENCE] Anyone using this gate must know ~89% of
   NIFTY500 by count gets a free pass here purely from lack of data, not
   because they're actually clean.
- Within the 55 covered symbols, `direct_news_available` is itself very
  uneven — 56.7% of (symbol,date) rows have any direct-news text at all, and
  per-symbol coverage ranges from **0% (INDIGO, SBILIFE — never got a single
  direct-news hit in 2,282 days, an entity-matching gap upstream, not a
  "clean" signal) to 97% (RELIANCE)**. ADANIENT is only 2.8% covered despite
  being one of the most newsworthy names in the sample period — the
  Hindenburg episode (see §5) still surfaces correctly, but this shows the
  scrape/tagging is sparse even for high-profile names.

## 5. Spot-checks (known real-world adverse events)
Verified against the built table (`ALPHA_RANKER/rnd/scorecard/no_negative_news_screen.parquet`):

| Case | Symbol | Real event date | Fires on | Pre-event window clean? |
|---|---|---|---|---|
| Hindenburg fraud/manipulation allegations | ADANIENT | 2023-01-24 | 2023-01-25 (sev 3, FRAUD_ACCOUNTING) — correct, next available news day | 2023-01-01→01-19: all severity 0 — yes |
| Hindenburg fallout + S&P outlook cut | ADANIPORTS | 2023-01-24 / 2023-02-03 | 2023-01-25, 01-27, 01-31 (sev 3, FRAUD_ACCOUNTING); 02-03/02-04 (sev 2, CREDIT_DOWNGRADE, S&P Global outlook-to-negative) | same window clean pre-event |
| Auditor resignation (related-party concerns) | ADANIPORTS | 2023-08-12 | 2023-08-12 (sev 3, AUDITOR_RESIGNATION) | clean before |
| Derivatives accounting discrepancy (₹1,577cr), CEO exit | INDUSINDBK | 2025-03-10 disclosure | 2025-03-11 through 03-18 (sev 3, FRAUD_ACCOUNTING; CEO resignation tagged MGMT_EXIT on 04-29/04-30) | 2025-02-15→03-04: all severity 0 — yes (one earlier, DISTINCT, correctly-caught promoter-pledge-increase flag on 2025-02-24, sev 2, which is a real separate red flag, not a false positive) |

No case fired before its real-world trigger date; all fired on/after the
first news day. This is the requirement-#4 spot-check.

**Precision fix made during build (documented so it isn't silently lost):**
v1 of CREDIT_DOWNGRADE used a bare `downgrad(e|ed|es)` pattern and matched
674 rows — sampling showed most were **brokerage stock-rating opinions**
("JPMorgan downgrades to Neutral", "Nuvama downgrades to Hold"), not actual
credit-rating actions. Similarly v1 PROMOTER_ISSUE matched bare "promoter
pledge" mentions and caught pledge **reductions** (good news, e.g. "Sun
Pharma reduced promoter pledging... shares rose 16%") as if they were bad
news. Both were tightened: CREDIT_DOWNGRADE now requires an actual rating
agency name (CRISIL/ICRA/CARE/Moody's/S&P/Fitch) adjacent to "downgrade" or
explicit "credit rating"/"default" language; PROMOTER_ISSUE now requires
directional language (increase/invocation/high-level) rather than any
mention. Post-fix: CREDIT_DOWNGRADE hits dropped 674→109, all 15 manually
sampled were genuine agency actions or defaults (one residual false positive
found: a Fitch **US sovereign** downgrade item filed under ITC's direct-news
feed by the upstream scraper — a source-side entity-tagging error, not a
lexicon bug; rare in sampling, left as a documented residual limitation).

## 6. Known limitations (state plainly, not overstate coverage)
1. **Universe = 55 symbols, not NIFTY500.** This screen is currently only
   meaningful for large-cap names already in the source data. For the
   remaining ~445 NIFTY500 names in the 1M scorecard's candidate list, this
   gate has **zero information** and defaults to "pass" by construction
   (§4) — it is NOT verifying them clean. **This is a genuine data-ask**:
   a NIFTY500-wide news feed (or a cheaper proxy — e.g., NSE/BSE corporate
   announcements + exchange filings, which ARE point-in-time and
   broad-coverage) is needed before this gate can do its job across the
   full 1M scorecard universe. Flagging to Data Officer / R&D head.
2. **Within the 55, coverage is uneven and occasionally zero** (INDIGO,
   SBILIFE — see §4); treat any "clean" read on those two names as
   "unverified," not "confirmed clean."
3. **Rule-based lexicon, not exhaustive.** It targets the categories named in
   the task (profit warning, regulatory action, auditor resignation, fraud,
   credit downgrade, promoter issue, litigation, guidance cut) but a
   keyword list will always miss novel phrasings and can still have residual
   false positives from upstream mis-tagged news (§5). It is a screen, not a
   certified event database — treat hits as "worth a human look before
   buying," which matches its role as a quality gate, not a scored alpha
   input.
4. **Text field is EOD-dated only** (§3) — no intraday timestamp, so same-day
   use for an open-of-day decision is NOT PIT-safe and must be avoided; a
   1-day lag is required by the consumer.
5. Determinism is at the algorithm level (pure regex, no randomness) — same
   input file reprocessed will produce identical values in every field;
   I have not separately certified byte-identical parquet file hashes across
   pyarrow versions, only value-identical output.

## 7. Files
- Build script (regenerable): `ALPHA_RANKER/rnd/scorecard/build_no_negative_news_screen.py`
- Output: `ALPHA_RANKER/rnd/scorecard/no_negative_news_screen.parquet`
  (125,510 rows × 8 cols: date, symbol, direct_news_available,
  negative_event_categories, negative_severity_raw,
  negative_severity_trail20, no_negative_news_flag, matched_snippet)

## 8. Verdict
**Usable, narrowly.** Ships as a real gate for the 55 large-cap names it
covers (spot-checks pass, lookahead-clean, false-positive bugs found and
fixed). **Not yet a NIFTY500-wide gate** — that requires broader-coverage
news/announcement data (data-ask, §6.1). Recommend S1 (1M scorecard
assembler) wire this in as an optional bonus penalty/exclusion for covered
names only, and NOT rely on it as a universe-wide filter until the data gap
is closed.
