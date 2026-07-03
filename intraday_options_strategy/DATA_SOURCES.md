# DATA SOURCES — what's obtainable for Nifty intraday options (honest map)

Scope boundary: **no dark-web / leaked / pirated data** — illegal and a malware/
poisoning risk, and unnecessary. Below is what's legitimately reachable.

## ACQUIRED (on disk, working)
| Source | What | Access | Status |
|---|---|---|---|
| Kaggle `debashis74017/nifty-50-minute-data` | 1-min Nifty50 + India VIX + BankNifty, 2015-2026 | kagglehub (anon) + truststore | ✅ used (underlying + VIX) |
| NSE F&O **EOD bhavcopy** (UDiFF + legacy) | daily per-strike/expiry settlement + OI, 399 days 2021-2026 | nsearchives.nseindia.com, cookie-primed | ✅ used → IV calibration m(DTE) |
| Angel One **scrip master** (public) | every NFO option token/strike/expiry/lotsize | margincalculator.angelbroking.com JSON, no auth | ✅ `angel_nfo_nifty.csv` (1,776 NIFTY opts) |

## INTRADAY OPTION CANDLES — the hard part (needed to confirm m(0DTE morning))
| Source | Verdict |
|---|---|
| **Angel One SmartAPI getCandleData** | ✅ best free path. Serves 1-min option candles for CURRENTLY-TRADABLE contracts (current + next few expiries), with YOUR creds. Ready: `data\angel_fetch_options.py hist`. Limit: NOT expired series. |
| **Angel One live recorder** (forward) | ✅ clean path for a full dataset: record ATM straddle quotes on expiry mornings during the paper month. Ready: `angel_fetch_options.py record`. |
| Zerodha `kite-history` (GitHub) | needs Kite creds; same forward-only build. |
| `openchart` (NSE charting, no auth) | ✗ this version's search returns only INDICES, not option contracts — couldn't get option tokens. Index/equity intraday works (`segment='IDX'`). |
| Stolo / TrueData / GDFL / iCharts | paid; full historical intraday F&O incl. expired series. The only way to get YEARS of expired intraday option ticks. |
| Dark web / "leaks" | ✗ declined — illegal, malware/poisoning risk. |

## Bottom line for the strategy
- **m(0DTE) is the #1 unverified input.** EOD bhavcopy gives DTE>=1 (extrapolated 0DTE m~0.96). To confirm the 09:20 expiry-morning premium directly we need INTRADAY option candles.
- **Free route:** Angel `hist` for the NEAREST live expiry (e.g. next Tuesday) right after it expires, + `record` forward each expiry → builds the real 0DTE dataset over the paper month at zero cost.
- **Fast route (if budget):** buy ~1-2 years of Nifty option 1-min from TrueData/GDFL → calibrate m(0DTE) immediately across regimes.
- Until then, the V3 result (0DTE short straddle, fund Sharpe ~2.9-3.4) stands on the extrapolated m with documented margin (survives to m~0.8).

## Config check flagged
Angel master shows NIFTY **lotsize = 65** (not the spec's 75). Per-lot P&L scales
linearly so Sharpe is unaffected, but capital/sizing in config.py should be set
to the current contract lot before live. Confirm against the latest NSE circular.
