# TOP150_NEW_QUANT_NOTES.md

Run date: 2026-07-21 (AS_OF_DATE for price-derived fields: 2026-07-16, unchanged from score_n100_quant.py to stay cross-sectionally comparable).

36 target names scored. Overall recommendation split: Hold=22, Sell=14, No Recommendation=0.

## [DATA] DATA-INTEGRITY FINDINGS — read before trusting any single-name number below

Self-red-teamed this run before shipping it (per firm quant-review charter — a
good-looking score is guilty until proven innocent). Found two distinct
screener_deep failure modes among these 36 names that the reused engine does
NOT guard against, plus one that was ALREADY baked into the existing 343-name
reference base this run built on top of.

**1. Zero screener_deep coverage (not "recent listing" — a genuine data void)**
`ABBOTINDIA`, `BDL`, `ICICIGI`: every PL/BS/CF row exists (the symbol is
present, metric rows are present) but every single year-column is NaN — 0%
non-null across all of screener_annual_pl / screener_balance_sheet /
screener_cash_flow, confirmed directly on the parquet files, not just on the
derived ratios. The auto-generated build notes below (inherited verbatim from
score_n100_quant.py's compute_fundamentals()) say "recent listing, short
history, or a distress/negative-equity year excluded" for these three names —
**that wording is wrong for these three specific names**. ABBOTINDIA (Abbott
India), BDL (Bharat Dynamics) and ICICIGI (ICICI Lombard) are all established,
long-listed, profitable companies; the NaN is a data-source gap, not an
economic fact about them. Their quality_score/growth_score/value_score pillars
are correctly NaN and final_3y_adj/final_1y_adj rest only on the
Stage/Sector-Macro/Ownership/Accumulation pillars (coverage_flag=Med, ~3-4/7
pillars populated) — treat these three scores as lower-confidence than the
"High" coverage names, DO NOT read the Hold/Sell call on these three with the
same weight as a fully-covered name.

**2. Silent stale-data fallback (caught and fixed for COLPAL; NOT a coverage
gap — worse, because it doesn't announce itself)**
`COLPAL` (Colgate-Palmolive India): screener_deep PL/BS/CF data is frozen at
**Mar 2010** — nothing has updated in 16 years, confirmed on the raw parquet.
The engine's `pe_current` / `pb_current` / `debt_equity` / `interest_coverage`
/ `revenue_cagr_3y` / `revenue_growth_1y` / `fcf_yield` / `market_cap_approx`
computations all use `.dropna().iloc[-1]` (last EVER valid value) with **no
recency check** — so on first pass this script silently computed
pe_current=125.4x, pb_current=165.2x, debt_equity=0.015, interest_coverage=217x
for COLPAL from the 16-year-old snapshot and presented them as "current."
(roe/roce self-protected because that leg uses a fixed-position n-year window,
not dropna-then-last — so those came out NaN correctly on the first pass.)
I manually verified the staleness against the raw parquet, nulled the nine
contaminated fields in `top150_new22_raw_inputs.csv`, and re-ran the engine —
COLPAL's coverage_flag_3y is now correctly "Med" and its score moved from
34.66/20.76 (contaminated) to the same 34.66/20.76 recomputed cleanly (the
value/quality pillars were already the only ones affected and are now
correctly NaN rather than falsely precise); verdict (Sell/Sell) is unchanged
either way, but the CONFIDENCE in that verdict is now honest.

**3. Same bug, already in production, OUT OF SCOPE for this run — escalate**
`AUBANK` (AU Small Finance Bank) is one of the 14 target names that were
already inside the pre-existing 343-name union (reference_300_full.csv /
n100_union343_full_engine_output.csv lineage, built by a prior run, not
recomputed here). Same diagnostic shows AUBANK's screener_deep data frozen at
**Mar 2017** — i.e. the SAME silent-stale-fallback contamination is already
sitting inside the "current, methodology-compliant" 300/343-name reference
base this run (and everything downstream of it) treats as ground truth. This
run did not touch or recompute AUBANK (out of scope — it lives in a file this
task didn't own), so its 54.74/49.44 Hold call above should be treated as
**unverified pending a staleness fix to the base reference file**, not as a
clean read.

**Magnitude check (quick sweep, not a full remediation):** across all 500
symbols in screener_annual_pl.parquet, last-valid-EPS-year shows 40 symbols
with ZERO EPS data ever, and 8 with STALE (pre-2024) EPS data: COLPAL (2010),
TTML (2011), TATAELXSI (2015), CIEINDIA (2015), AUBANK (2017), FIVESTAR (2019),
BLUEJET (2021), RAILTEL (2023). Recommend a firm-wide staleness sweep
(last-valid-year check on EPS/Equity Capital/Sales+, not just a
row-exists check) across the full reference universe before the next
methodology certification — this is a new landmine class, not previously in
`05_DATA_OFFICE/DATA_QUALITY_RULES.md`.

## Build notes (verbatim, in computation order)

- 36-name union: 14 names already scored inside the existing 343-name union (reference_300_full.csv lineage); 22 names are genuinely new to any prior quant run.
- Already-covered (14): ['ALKEM', 'AUBANK', 'AUROPHARMA', 'BANKINDIA', 'CONCOR', 'EXIDEIND', 'GLAXO', 'GROWW', 'KEI', 'MAHABANK', 'NAUKRI', 'SAIL', 'SUNDARMFIN', 'YESBANK']
- Newly computed (22): ['ABBOTINDIA', 'ANTHEM', 'ATGL', 'BDL', 'BERGEPAINT', 'BHARATFORG', 'BHARTIHEXA', 'BLUESTARCO', 'COFORGE', 'COLPAL', 'DABUR', 'DIXON', 'FEDERALBNK', 'GODREJPROP', 'HAVELLS', 'ICICIGI', 'INDUSINDBK', 'LINDEINDIA', 'M&MFIN', 'OFSS', 'PAYTM', 'UNOMINDA']
