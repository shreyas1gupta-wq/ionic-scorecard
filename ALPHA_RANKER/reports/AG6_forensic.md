# AG6 — Forensic / Red-Flag Module (Phase 4) — Pilot Run

Code: `ALPHA_RANKER/src/forensic/forensic_checks.py`
Outputs: `ALPHA_RANKER/results/pilot_forensic_flags.csv` (180 rows, 10 symbols x 18 flags), `ALPHA_RANKER/results/pilot_forensic_score.csv`

Per 08_FORENSICS_REDFLAGS.md: this module emits raw ingredients only —
`(raw_signal, base_severity 0–3, modulation_note)` per flag, plus an
un-modulated aggregate. **It does not apply size_mult / regime_mult / offset**
— those live in the scoring engine's Step 6, which has the market-cap and
regime context this module doesn't. No flag was ever guessed: anywhere an
input was missing, the row is `insufficient-data` / `not-applicable` with the
reason stated, not a filled-in number.

## Aggregate scores (0–100, higher = worse; NOT yet size/regime-adjusted)

| Symbol | Score | Flags OK | Insuff. | N/A | Coverage |
|---|---|---|---|---|---|
| GRAVITA | 37.9 | 15/18 | 3 | 0 | 83% |
| TATASTEEL | 33.5 | 15/18 | 3 | 0 | 83% |
| TCS | 21.0 | 15/18 | 3 | 0 | 83% |
| HDFCBANK | 19.8 | 10/18 | 4 | 4 | 56% |
| HINDALCO | 15.0 | 10/18 | 8 | 0 | 56% |
| MARUTI | 9.1 | 15/18 | 3 | 0 | 83% |
| NESTLEIND | 6.1 | 7/18 | 11 | 0 | 39% |
| ASIANPAINT | 3.9 | 15/18 | 3 | 0 | 83% |
| INFY | 2.7 | 14/18 | 4 | 0 | 78% |
| SHAKTIPUMP | 0.0 | 1/18 | 17 | 0 | 6% |

**Read the score together with coverage, not alone.** SHAKTIPUMP's 0.0 means
almost nothing — only the promoter-holding flag had data (see Data Coverage
below), it is not "clean." NESTLEIND at 39% coverage is also thin. GRAVITA,
TATASTEEL, TCS, ASIANPAINT, MARUTI have the most trustworthy scores (83%
coverage, 15/18 flags computed).

Drivers worth a human look:
- **GRAVITA** (37.9): CFO/PAT divergence (avg gap 48.6% of PAT over FY22–26), Sloan/TATA accrual ~6–7% of assets, weak cash conversion (~47% avg), promoter holding down 6.5pp YoY (as of the stale 2023-09 snapshot — see caveat below). Consistent with a smaller, faster-growing name where several earnings-quality flags co-occur — exactly the size_mult case the doc calls out (recycling metals microcap-adjacent).
- **TATASTEEL** (33.5): DSRI 2.53x and receivables growing 171pp faster than sales FY20→21 (COVID-year base-effect candidate — flagged, not asserted as manipulation), tax-rate volatility (std 129% — driven by a loss-making/near-zero-PBT year, mechanically inflating the ratio), rising gross debt/EBITDA (2.7x→3.75x gross, cash unavailable so this is gross not net).
- **TCS/ASIANPAINT/INFY** (2.7–21.0): mostly clean earnings-quality; TCS's headline score is lifted mainly by one FY22→23 receivables/inventory-vs-sales divergence and DSRI — worth checking if it's a COVID-recovery low base rather than a real quality issue.

## Data coverage — honest accounting per flag category

| Category | Flags in spec | Computable this pilot | Blocking gap |
|---|---|---|---|
| CFO/PAT divergence, cash conversion | Yes | 8–9/10 symbols | SHAKTIPUMP has **zero** rows in screener_deep (BS/CF/PL) — entirely absent, not just thin |
| Sloan accruals (ΔNWC-based) | **No — proxy substituted** | 9/10 (asset-scaled proxy) | Neither `screener_deep` (compact BS, no current-asset/liability split) nor `mc_fundamentals_parsed` (`CURRENT ASSETS`/`CURRENT LIABILITIES` populated only 99/3968 rows firm-wide, 0 for this pilot) carries the working-capital split the classic Sloan formula needs. Reported the well-known `(PAT-CFO)/avg(TotalAssets)` asset-scaled variant instead and labeled it explicitly as not the NWC decomposition. |
| Beneish DSRI, SGI, TATA | Yes | 7–9/10 | Needs `mc_fundamentals_parsed`, which only covers 7 of 10 pilot symbols (missing NESTLEIND, HINDALCO, SHAKTIPUMP entirely) and only 3–5 non-contiguous fiscal years per symbol (2019–2023) |
| Beneish GMI | Partial | 6/10 | Same mc_fundamentals gap; also **not-applicable for HDFCBANK** (no COGS concept for a bank) |
| Beneish AQI | **No — insufficient-data for all 10** | 0/10 | Requires the same current-asset/PPE split as Sloan; genuinely absent everywhere checked |
| Beneish composite M-score | **Not computed, by design** | 0/10 | Composite needs 8 inputs; DEPI/SGAI/LVGI have no source columns in `screener_deep` or `mc_fundamentals_parsed` at all — fabricating a composite from 4 of 8 terms would misstate the model. Standalone components reported instead. |
| Other-income dependence, tax-rate anomaly | Yes | 8–9/10 | Full screener PL coverage; HDFCBANK's "other income" flag reported but marked not-standard (banks' other income is core fee/treasury income, not a one-off) |
| Receivables/inventory growth vs sales | Yes | 6–7/10 | mc_fundamentals-gated (same coverage gap as above); consecutive-year pairs only |
| Interest cover, debt/EBITDA | Yes | 7–8/10 | Both **not-applicable for HDFCBANK** (bank leverage/interest-expense metrics don't mean what they mean for an industrial); debt/EBITDA uses gross debt (not net) wherever `mc_fundamentals_parsed.Cash And Cash Equivalents` is unavailable for that symbol/year — labeled `gross_debt` explicitly in the CSV rather than silently mislabeled as net |
| Contingent liabilities / net worth | Yes | 6/10 | mc_fundamentals-gated |
| Promoter holding & trend | Yes | 10/10 (level+YoY) | **All 10 computed, but the whole shareholding_changes.parquet dataset is stale firm-wide — max quarter_end across the entire dataset is 2023-12-01, ~2.5 years old as of today (2026-07-16).** Every promoter row carries an explicit `[DATA] STALE` note; treat as historical context, not current positioning. |
| Promoter pledge % | **No — insufficient-data for all 10** | 0/10 | No pledge-% column in any dataset checked: `datasets/derived/shareholding_changes.parquet`, `datasets/earnings_pit/quarterly_shareholding_pit.parquet`, `datasets/kaggle_indian_financials/{quarterly,yearly}_shareholding.parquet` all lack it; `datasets/screener_dump_20260704/screener/excel_reports/` exists but is **empty (0 files)** — the intended pledge-disclosure source was never populated. Schema hook (`symbol, quarter_end, pledge_pct`) is ready for D-033 ingestion once a real source is found. |

## Notable data-quality findings surfaced during this build (not fabricated flags — genuine dataset facts)

1. **SHAKTIPUMP has no coverage in `screener_deep` or `mc_fundamentals_parsed` at all** — only the promoter-shareholding dataset has it. 17 of 18 flags are `insufficient-data` for this symbol. Its forensic score of 0.0 must not be read as "clean"; it is "unmeasured."
2. **`datasets/derived/shareholding_changes.parquet` is stale for the whole dataset**, not just the pilot — last quarter_end anywhere in the file is 2023-12-01. This should go into `05_DATA_OFFICE/DATA_QUALITY_RULES.md` as a known gap if not already there.
3. **HDFCBANK's promoter holding shows a -25.64pp drop to 0.00% in the 2023-09 quarter.** [INFERENCE] This coincides with the HDFC Ltd → HDFCBANK reverse merger (completed Jul-2023) and is very likely a promoter-classification reclassification artifact (HDFCBANK has no controlling promoter post-merger), not organic selling. Flagged in the CSV note; should be verified against the actual merger scheme before any downstream consumer treats it as a governance red flag.
4. **Bank-inapplicable metrics**: for HDFCBANK, `cash_conversion_cfo_ebitda`, `GMI`, `interest_cover_trend`, and `debt_to_ebitda_trend` are marked `not-applicable` rather than computed on numbers that don't carry the same meaning for a financial institution (interest is a funding cost, not debt service on top of an operating business; no COGS concept exists).
5. **Net vs gross debt labeling**: `mc_fundamentals_parsed.Cash And Cash Equivalents` is only populated for the 7 symbols/sparse years also covered by that dataset. Where cash wasn't available, `debt_to_ebitda_trend` used **gross** borrowings and the CSV `raw_value` says so explicitly (`gross_debt (cash unavailable...)`) rather than silently calling it net debt.

## Severity model (as designed, not yet applied)

Per flag, `flag_points = base_severity (0–3) × badness (0–1)`, where badness is
a documented linear map from the raw ratio to a 0–1 "how bad" score (thresholds
in code comments per flag, e.g. CFO/PAT gap: 0 at ≤0%, 1 at ≥50%). The
aggregate score is `100 × Σ(base_severity×badness) / Σ(base_severity)` over
flags with `data_status=='ok'` only — a severity-weighted average badness,
**not yet multiplied by size_mult / regime_mult / offset** per the doc's
severity formula. That modulation is the scoring engine's job at Step 6, using
market-cap and regime context this module doesn't have. Hard-veto flags
(auditor resignation, confirmed fraud, covenant breach + going-concern doubt)
have **no source data at all** in the checked datasets for this pilot and are
therefore not scored — no veto was fabricated in their absence.
