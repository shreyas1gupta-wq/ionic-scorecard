# UNI-A -- Universe Fundamental + Catalyst engine

Generated 2026-07-16. Source: `data/fundamentals/consolidated/*.parquet` (built from `data/fundamentals/screener_live/*.json` via `consolidate_screener.py`), + `top_ratios` (screener's own TTM Market Cap/Price/P-E/Book-Value/ROCE/ROE) + last Close from `data/prices/*.parquet` as price fallback. **Data is STILL LANDING** -- this run covers whatever is scraped as of generation time; re-run after the fleet finishes for the full 750.

## Coverage
- Universe file (`symbols_750.txt`): 751 symbols.
- Consolidated/scraped (have >=1 fundamentals table): 749 (99.7% of the 750 list).
- Of those, on the official 750 list: 749; scraped but NOT on the current 750 list (renames/edge cases, kept & scored anyway): 0.
- Not yet scraped (0 tables) -- fully absent from these outputs, not zero-filled: 2.
- Bank/NBFC ("financial") schema detected (no Sales/Operating-Profit rows): 71/749 scored names.
- Fundamental theme non-null factor coverage (mean n_factors out of max 23): 21.2.
- Catalyst theme: 749/749 names have >=1 usable quarterly catalyst factor; mean factors used = 10.8 / 11.

## Bank/NBFC ("financial") schema handling
- Detected by absence of an `Operating Profit` row in `profit_loss` for that symbol (screener shows `Revenue`/`Financing Profit`/`Financing Margin %` instead of `Sales`/`Operating Profit`/`OPM %`).
- For these names: `opm_level/trend/stability` left missing (Financing Margin % is not the same economic quantity as non-bank OPM %); `ROCE` and all three Leverage factors (D/E, interest-cover, debt/EBITDA) are marked N/A -- not computed, because deposits/borrowings are the core funding mechanism for these businesses, not leverage in the sense the metric is meant to capture for a manufacturer/services company.
- `ROE`, Growth, Value, and Catalyst themes ARE computed for banks/NBFCs (those concepts remain meaningful) using `Revenue` in place of `Sales` for growth calcs.
- Shareholding: banks/NBFCs generally carry no `Promoters` row (widely held, e.g. HDFCBANK shows only FIIs/DIIs/Government/Public) -- this affects any downstream promoter-holding factor, not this fundamental/catalyst script directly.

## Method notes (carried over from the pilot, still apply)
- Value theme now PREFERS screener's own TTM `top_ratios` (Stock P/E, Book Value, Market Cap) over the derived-shares approach; the Net-Profit/EPS shares identity is only used as a fallback when `top_ratios` lacks the field. EV/EBITDA still has NO cash netting (screener's condensed balance sheet has no standalone cash line) -> runs rich for cash-heavy names.
- All theme scores are cross-sectional PERCENTILES (0-100) over the currently-covered universe (not a fixed pilot list) -- as coverage grows toward 750, re-running this script re-percentiles against the larger set; scores are NOT stable/comparable across runs with different coverage.
- No lookahead: each symbol uses only its own latest scraped annual/quarterly period; no forward-filling or cross-symbol imputation.
- Missing stays missing (NaN) everywhere; nothing is fabricated or zero-filled. Per-factor completeness (`n_quality_factors` etc, `n_catalyst_factors`) travels with every score so a thin-evidence average is visible, not hidden.

## Sanity check -- top/bottom 10 per theme

### Quality
**Top 10:** WEBELSOLAR (83.6), ENRIN (82.4), SANOFICONR (81.5), NESTLEIND (81.0), HDFCAMC (80.0), ICICIAMC (79.9), IEX (79.7), NAM-INDIA (79.6), TIPSMUSIC (78.9), COLPAL (78.8)
**Bottom 10:** ABREL (1.8), VIPIND (2.4), TEJASNET (3.7), PWL (4.3), KITEX (7.0), ALOKINDS (7.4), NETWORK18 (7.8), BAJAJELEC (8.1), EQUITASBNK (8.3), INDIACEM (8.4)

### Growth
**Top 10:** SPARC (99.6), SKYGOLD (95.9), JSLL (95.6), BSE (94.8), MCX (94.8), MANORAMA (94.5), NSLNISP (94.4), V2RETAIL (93.9), WEBELSOLAR (93.5), PWL (93.0)
**Bottom 10:** ABREL (2.0), RPOWER (4.4), ALOKINDS (5.8), ELECTCAST (9.2), AARTIPHARM (9.6), AFCONS (10.5), GHCL (11.3), TATACHEM (11.4), SKFINDIA (11.4), ACI (11.6)

### Value
**Top 10:** ASHOKA (99.6), PNB (98.5), CENTRALBK (98.5), BANKINDIA (98.5), BANKBARODA (98.3), KTKBANK (98.3), TMPV (98.0), UNIONBANK (97.9), IOC (97.8), IDEA (97.7)
**Bottom 10:** ALOKINDS (0.0), FACT (0.5), NYKAA (1.0), BAYERCROP (1.0), CUPID (1.1), TATAELXSI (1.5), SCHNEIDER (2.7), POWERINDIA (2.9), MTARTECH (3.0), PTCIL (3.1)

### Leverage
**Top 10:** FORCEMOT (98.5), MMTC (98.5), SBILIFE (98.1), KSCL (98.1), NBCC (98.1), MOIL (98.1), BSE (98.1), MAHSCOOTER (98.1), NIACL (98.1), LICI (98.1)
**Bottom 10:** VIPIND (1.9), GODREJIND (2.1), INDIGO (3.1), PURVA (3.3), PIRAMALFIN (3.4), SWSOLAR (3.4), ADANIGREEN (3.4), RBA (3.6), ABREL (3.8), TARC (4.1)

### Catalyst
**Top 10:** SPARC (94.1), SPLPETRO (91.1), HINDCOPPER (90.7), ATLANTAELE (90.0), PTCIL (89.5), KIRLPNU (88.4), TIMKEN (88.2), SIGNATURE (88.0), MCX (87.8), JIOFIN (87.5)
**Bottom 10:** OLAELEC (4.6), SAMMAANCAP (5.1), UTIAMC (6.9), TATACHEM (7.0), AFCONS (8.3), MFSL (8.8), DRREDDY (9.6), ZEEL (10.2), RALLIS (10.6), VIPIND (10.6)

## Outputs
- `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\universe_fundamental_scores.parquet` -- symbol x Quality/Value/Growth/Leverage + n_factors + is_bank_nbfc_schema
- `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\universe_catalyst_scores.parquet` -- symbol x theme_catalyst + key raw catalyst factors
- `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\universe_fundamental_factors_raw.csv` -- raw (pre-percentile) fundamental factor values, for audit