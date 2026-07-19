# Universe-scale Forensic + Cascade -- build report

Run 2026-07-16. Universe: `data/universe/nifty_total_market_750.csv` (751 symbols,
22 Industry groups). Fundamentals source: `data/fundamentals/consolidated/*.parquet`
(rebuilt this run via `src/lib/consolidate_screener.py` off 634 landed
`screener_live/*.json` files -> 619 symbols consolidated; 751-619=132 symbols
still awaiting a screener_live scrape as of this run -- **data is still landing**,
both scripts are written to just pick up more coverage on re-run with no code
change). Prices: `data/prices/*.parquet`, 751/751 symbols now landed.

## 1. Forensic engine (`src/forensic/universe_forensic.py`)

Reused `src/forensic/forensic_checks.py`'s flag taxonomy and severity/badness
scale (0-3 severity x 0-1 badness -> 0-100 score, higher=worse), rebuilt against
the live `screener_live` schema (different columns than the pilot's
`screener_deep`/`mc_fundamentals_parsed`). Bank/NBFC schema is detected
**per-symbol** from the metric names actually present (`Financing Profit` in
P&L or `Deposits` on the balance sheet) rather than from the `Industry` label,
since "Financial Services" (121 names) also contains non-bank-schema reporters
(e.g. general insurers use the normal Operating-Profit/OPM% schema).

Two flags are **direct schema upgrades** over the pilot: `ratios.Debtor Days` /
`Inventory Days` / `Cash Conversion Cycle` are now reported at full coverage
(vs. the pilot's sparse, non-contiguous `mc_fundamentals` receivables/inventory
series), and `cash_flow.CFO/OP` is screener's own cash-conversion ratio,
computed for bank-schema names too (unlike the pilot, which marked cash
conversion not-applicable for HDFCBANK). Two flags are explicit
**[INFERENCE substitution]**: DSRI uses the Debtor-Days ratio (mathematically
equivalent to Receivables/Sales ratio -- the 365/Sales terms cancel) and GMI
uses OPM%/Financing-Margin% in place of a true COGS-based gross margin (this
schema has no cost-of-materials column, only aggregate "Expenses"). Both are
tagged in the flag's `modulation_note`, not silently swapped in.

### Coverage
| | |
|---|---|
| Symbols in universe | 751 |
| Symbols with >=1 computed flag | 747 |
| Symbols with an aggregate score | 741 |
| Mean flag-coverage on scored symbols | 70.2% |
| Flag rows (symbol x flag) | 14,269 (19 flags/symbol) |
| data_status: ok / insufficient-data / not-applicable | 9,895 / 4,038 / 336 |

Flags still genuinely insufficient-data across the WHOLE universe (same
conclusion as the pilot, confirmed again on this newer source, not a lookup
bug): `AQI_asset_quality_index` (no current-asset/PPE split anywhere in this
schema), `beneish_M_score_composite` (needs AQI + DEPI/SGAI/LVGI, none of
which have source columns), `contingent_liabilities_to_networth` (no such
column in `screener_live` at all), `promoter_pledge_pct_and_trend` (no pledge
row in `shareholding` -- holders present are Promoters/FIIs/DIIs/Government/
Public/No. of Shareholders/Others only). All four have explicit
insufficient-data hooks ready for when a source lands.

`not-applicable` = 336 = 56 bank/NBFC-schema symbols x 6 flags
(receivables/inventory/CCC-trend, interest-cover, debt/EBITDA, DSRI) that
genuinely don't apply to a financial institution's income statement.

### Top/bottom sanity check (coverage>=50% only, to avoid thin-coverage noise)
**Worst 10 (highest forensic_risk_score):**
TI (FMCG) 79.7, PIRAMALFIN 75.3, MOTILALOFS 72.6, RVNL 71.8, NEOGEN 68.9,
LLOYDSENT 68.4, LOTUSDEV 67.6, KAYNES 66.6, KRN 66.1, ANGELONE 65.8.

**Best 10 (lowest forensic_risk_score):** PETRONET 0.8, SONATSOFTW 1.0,
CAMS 1.1, 3MINDIA 1.3, TENNIND 1.4, MASTEK 1.4, JSL 2.0, ROUTE 2.0,
HYUNDAI 2.2, BRITANNIA 2.3.

These read as plausible (large, well-covered names with clean cash conversion
and stable margins score low; names with reported leverage/working-capital
strain score high) but are **NOT** yet size/regime-adjusted -- that is the
downstream scoring engine's job, exactly as documented in the pilot.
A handful of symbols outside this list score 100 on ~5% coverage (1-2 flags
only, e.g. VOLTAMP, AVL, HOMEFIRST) -- these are thin-coverage artifacts from
still-landing data, correctly flagged by low `coverage_pct` so they won't be
mistaken for a thorough read; excluded from the sanity list above by design.

Outputs: `results/universe_forensic_flags.parquet` (14,269 rows),
`results/universe_forensic_score.parquet` (751 rows).

## 2. Oversight cascade (`src/cascade/universe_cascade.py`)

GLOBAL and NATIONAL layers are unchanged from the pilot (both read only from
`factor_navs`, never depended on the pilot's ticker list). **SECTOR is
rebuilt**: sector now comes from the real `Industry` column in
`nifty_total_market_750.csv` (22 industries) instead of the pilot's
`datasets/india_stock_metadata/india.csv` lookup, and each sector's
equal-weight RS composite is built from ALL of that industry's priced
constituents in `data/prices/` (751/751 symbols now priced), computed ONCE
per industry and looked up per symbol (not recomputed per stock).

### Sector self-reference fix -- confirmed
Pilot: 10 stocks, sectors as small as n_peers=1 (Finance had only HDFCBANK --
RS was self-referential by construction). Universe run:

| sector | n_peers |
|---|---|
| Financial Services | 121 |
| Capital Goods | 112 |
| Healthcare | 71 |
| Automobile and Auto Components | 48 |
| Consumer Services | 46 |
| Chemicals | 45 |
| FMCG | 45 |
| Consumer Durables | 41 |
| Information Technology | 36 |
| Services | 27 |
| Metals & Mining | 24 |
| Construction | 23 |
| Power | 21 |
| Oil Gas & Consumable Fuels | 17 |
| Realty | 17 |
| Construction Materials | 16 |
| Telecommunication | 13 |
| Textiles | 12 |
| Media Entertainment & Publication | 8 |
| Utilities | 4 |
| Diversified | 3 |
| **Forest Materials** | **1** (only remaining singleton) |

**21 of 22 sectors now have >=3 priced peers** (median sector size 24 peers);
only "Forest Materials" (1 symbol in the whole universe csv) is still a
singleton and is flagged explicitly in its `sector_rationale` as
self-referential, exactly as the pilot's convention required. This is the
requested fix -- self-reference is now the documented exception, not the rule.

### Sanity checks
- `global_adj` = -5.2pt and `national_adj` = +1.1pt for all 751 symbols
  (computed once, as expected for layers that don't vary by stock).
- `net_adj` range: -19.1 to +8.7 (mean -5.6, std 6.1) -- well inside the
  theoretical +-45 (3 active layers x +-15), consistent with a
  moderately-risk-off global/sector mix on this `asof`.
- Top net_adj: Metals & Mining names (VEDL, TATASTEEL, ASHAPURMIN, SARDAEN,
  SANDUMA) all +8.7, sector RS +12.8pt -- sector-driven, not name-specific
  (expected, since sector_adj is identical for every peer in a given sector
  on a given `asof`; stock-specific differentiation is the STOCK layer's job,
  still a placeholder).
- Bottom net_adj: Information Technology names (WIPRO, AFFLE, HEXT, INFY,
  INTELLECT) all -19.1, sector RS -15.0pt (capped) -- IT sector composite
  underperforming NIFTY500 by more than 15% over the lookback window.
- `has_price_data` True for all 751 rows.

Output: `results/universe_cascade_adjustments.parquet` (751 rows x 14 cols:
symbol, asof, sector, n_sector_peers, global/national/sector/stock/net_adj,
4 rationale strings, has_price_data).

## Caveats carried forward (unchanged from pilot, still true at universe scale)
- STOCK layer remains a 0-point placeholder -- 02_SCORING_ENGINE bottom-up
  composite is out of scope for this task.
- GLOBAL/NATIONAL are still proxy-based (`[INFERENCE/approx]`) pending true
  macro pulls (US10Y/DXY/Fed/VIX/crude/PMI; RBI/credit/FII-DII/CPI/IIP) into
  `05_DATA_OFFICE` -- same blocker as the pilot.
- Forensic flags are NOT size/regime-modulated here by design (scoring
  engine's job); a raw forensic_risk_score should not be read as a portfolio-
  level penalty on its own.
- 132/751 symbols still have zero screener_live coverage as of this run
  (data landing in progress) -- both scripts will pick these up automatically
  on the next run once `consolidate_screener.py` is re-run against a fuller
  `screener_live/` directory.
