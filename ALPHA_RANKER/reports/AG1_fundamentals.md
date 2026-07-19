# AG1 — Fundamental factor library (Quality / Growth / Value / Leverage), pilot-10

Generated: 2026-07-16. Source: `datasets/screener_deep/*.parquet` (annual, long format) + last Close from `ALPHA_RANKER/data/prices/*.parquet`. All scores are UNCALIBRATED cross-sectional relative percentiles among these 10 names only -- NOT absolute grades, NOT comparable outside this pilot set.

## Screener coverage
- Covered in screener_deep: 9/10 -> HDFCBANK, ASIANPAINT, NESTLEIND, TATASTEEL, HINDALCO, MARUTI, TCS, INFY, GRAVITA
- ABSENT from screener_deep (all 3 statements): SHAKTIPUMP -> fundamental row is fully NaN/missing for these, not zero-filled.

## Method notes / limitations (read before using scores)
- **Shares outstanding are not in any fundamentals source checked** (screener_deep, `datasets/earnings_pit/mc_fundamentals_parsed.parquet`, `datasets/india_stock_metadata`). Shares are [INFERENCE]-derived as `Net Profit / EPS` off the same year's reported figures (a real accounting identity, not a guess); if EPS<=0 or missing, the whole Value theme for that name is left missing rather than fabricated.
- **EV/EBITDA and debt/EBITDA are approximate**: EV = MCap + gross Borrowings with **no cash netting** (screener's condensed balance sheet has no standalone cash line) -> both ratios run rich for cash-heavy names (e.g. TCS/INFY) versus a true net-debt calc.
- **EBIT/EBITDA are computed schema-agnostically** as `PBT+Interest` / `+Depreciation` so bank and non-bank P&L layouts (which differ) are treated consistently.
- **HDFCBANK**: no Operating Profit/OPM% row exists for banks -> opm_level/trend/stability are missing for it; its leverage ratios (D/E, debt/EBITDA) are not economically comparable to non-financials (deposits, its core funding, aren't counted as Borrowings).
- **NESTLEIND**: broken/short annual series after an FY-end transition (only 2 usable Mar points) -> growth CAGRs (3y/5y) are correctly starved and left missing, not fabricated.
- **SHAKTIPUMP**: absent from screener_deep entirely -> its whole fundamental row is missing.
- Theme scores are the mean of that theme's AVAILABLE (non-missing) factor percentiles for each name -- factor counts per theme are in `pilot_fundamental_scores.csv` (n_quality_factors etc.) so a low count (thin evidence) is visible, not hidden inside an average.

## Per-symbol data notes
- **HDFCBANK**: Bank schema: no Operating Profit/OPM% row -> opm_level & opm_trend/stability left missing (Financing Margin% is not comparable to non-bank OPM%). EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'. HDFCBANK: leverage ratios (D/E, debt/EBITDA) are NOT comparable to non-financials -- deposits (a bank's core funding) are not counted as 'Borrowings'; interpret leverage theme for this name with caution.
- **ASIANPAINT**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **NESTLEIND**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **TATASTEEL**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **HINDALCO**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **MARUTI**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **TCS**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **INFY**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **GRAVITA**: EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names. debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.
- **SHAKTIPUMP**: ABSENT from screener_deep (all 3 statements) -> entire fundamental row missing.

## Outputs
- Raw factors: `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\pilot_fundamental_factors_raw.csv`
- Theme scores (0-100, uncalibrated, relative to pilot): `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\pilot_fundamental_scores.csv`

## Theme scores snapshot

|            |   Quality |   Growth |   Value |   Leverage |
|:-----------|----------:|---------:|--------:|-----------:|
| HDFCBANK   |      59   |     61.6 |    74.1 |       11.1 |
| ASIANPAINT |      67.9 |     37.3 |    11.1 |       51.9 |
| NESTLEIND  |      83.9 |     66.7 |     0   |       70.4 |
| TATASTEEL  |      28.8 |     44.6 |    63   |       14.8 |
| HINDALCO   |      29.4 |     57.8 |    74.1 |       18.5 |
| MARUTI     |      50.7 |     70   |    40.7 |       88.9 |
| TCS        |      80   |     42.9 |    44.4 |       66.7 |
| INFY       |      68.6 |     60.6 |    66.7 |       74.1 |
| GRAVITA    |      49.8 |     71   |    25.9 |       37   |
| SHAKTIPUMP |     nan   |    nan   |   nan   |      nan   |