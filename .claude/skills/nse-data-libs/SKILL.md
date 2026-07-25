---
name: nse-data-libs
description: Use when fetching NSE data in Python (historical equity/index/option EOD, F&O bhavcopy, live option chain) — before pip-installing nsepy / nsepython / jugaad-data, and to know which calls work on the office proxy vs need home network.
---

# NSE data libraries (jugaad-data / nsepython / nsepy)

Verified 2026-07-24 by EXECUTION (Python 3.14.5, `pip install --user`, corporate proxy + `truststore.inject_into_ssl()`). Rule reconfirmed: NSE archives/historical endpoints work on the office proxy; live `/api` soft-blocks to an empty payload with NO exception. Trust pip's version, not `__version__` (all three report stale attrs).

## USABLE now — `jugaad-data` (ADOPT)

`pip install --user jugaad-data`. Options-relevant paths work on the OFFICE network:

| Call | Verified |
|---|---|
| `derivatives_df(symbol, from_date, to_date, expiry_date, instrument_type="OPTIDX", option_type="CE", strike_price=18000)` | 15 rows real NIFTY 18000-CE EOD: OHLC, LTP, SETTLE PRICE, OI, CHANGE-IN-OI |
| `bhavcopy_fo_save(date, dir)` | full F&O bhavcopy (3.87 MB CSV) |
| `stock_df(symbol, from_date, to_date, series="EQ")` | 7 rows real SBIN EOD |

Free, independent cross-check / gap-fill for historical single-option EOD + F&O bhavcopy — complements Angel (broker API) and our own bhavcopy backfill. Carry-over landmine: on expiry day `SETTLE PRICE` is the UNDERLYING settlement, not the option price (CLAUDE.md #9) — cash-settle at intrinsic. Its LIVE `/api` calls (`NSELive().stock_quote`, `index_df`) are proxy-blocked here (JSONDecodeError = empty) → home network/VPN only.

## CONDITIONAL — `nsepython` (ADOPT-PARTIAL: home-net + assert non-empty)

`pip install --user nsepython`. `nse_optionchain_scrapper("NIFTY")` executed with no error but returned 0 option rows on the office network (anti-scraping soft-block → empty dict, no exception). Reachable but unverified for real data here — confirm a populated chain on home network before trusting. Value = free live NSE option-chain snapshots without Angel rate limits. Flag: silent-empty failure mode — any pipeline MUST assert `len(records["data"]) > 0`.

## TRAP — `nsepy` (SKIP, BROKEN on Python 3.14)

`get_history(...)` throws `ValueError: cannot remove local variables from FrameLocalsProxy` — PEP 667 changed `frame.f_locals` semantics in Py3.13+, and nsepy deletes locals through that proxy; it crashes in its own code before the network. Hard break, unmaintained (~2021). Don't install it on this interpreter.
