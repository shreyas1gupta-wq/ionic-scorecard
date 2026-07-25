---
name: mf-lookthrough
description: Compute a client book's TRUE exposure by looking through mutual-fund monthly portfolios — combined direct+fund stock/sector exposure, the double-pay table (stocks held both directly and inside funds), concentration, and debt-risk flags (>10% issuer look-through; >10% debt sleeve with below-AA paper; scored-universe leverage-gate issuers). Use for /mf-lookthrough <client csv>, "look through the funds", NDPMS reviews (feeds the deck's sector scope-tags and overlap slide), or when fund disclosures land.
---
# /mf-lookthrough — owner: MF desk + Kavya (data)

## Two commands (script does everything; agents only for triage = Haiku)
```
python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_lookthrough.py ingest
python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_lookthrough.py run <client_holdings.csv>
```
1. **ingest** — drop AMC monthly portfolio workbooks (.xls/.xlsx, any layout with an ISIN header row) into `datasets/mf_holdings/incoming/`; the parser auto-finds the header, maps ISIN / instrument / %NAV / rating / industry, normalizes to parquet. **Retention (Principal): raw drops deleted after 180 days; normalized snapshots keep the last 6 month-ends + quarter-ends thereafter** — storage never balloons.
2. **run** — client CSV (`type[stock|fund], name, isin, value_inr`) → writes `<client>_lookthrough.csv` (full exposure table) + `<client>_LOOKTHROUGH.md` (compact digest: book split, double-pay list, flags) — the .md is what the model reads (token-cheap).

## Debt-risk FLAGS (per Principal 2026-07-25 — flags only, NOT a fixed-income framework)
- Any single debt **issuer > 10%** of the client book on look-through.
- **Debt sleeve > 10%** of book AND it contains below-AA paper (word-bounded rating match — AA+/AAA never false-positive).
- Issuer trips the **scored-universe leverage/coverage gate** (D/E > 2.5 or interest cover < 2, non-financials) with >3% look-through weight.

## Tax-inertia rule (Principal 2026-07-25 — applies wherever fund switches are recommended)
Units held **>5y** (stronger at **>10y**) carry embedded LTCG large enough to offset switching alpha → **raise the fund's sell/switch bar**: switch only on a structural reason (plan cost, mandate, closet-indexing), not a performance gap. **Stocks are exempt from this inertia** — single-name risk dominates the tax cost, so equity Sell guidance stays unchanged (tax shown, threshold not raised). Wired into the NDPMS deck (`fund_actions`/`tax_impact`) and the `agentic-fund-manager` mechanical layer.

## Relations
NAV data: `/mf-nav-refresh` · recommendations: `/qfra2-rerun` (LT) + `/qfra1-rerun` (ST) · consumes: NDPMS deck template (`09_PRODUCT/pr_template`) for the duplication slide + sector scope-tags. Scheme matching is normalization-based (letters-only prefix) — check the digest's scheme count when a new AMC's file format first lands.
