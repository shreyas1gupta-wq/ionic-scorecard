---
name: options-python-libs
description: Use when pricing options / computing Greeks or implied vol, or backtesting an options strategy in Python on this machine — before pip-installing a pricing or options-backtest package, before trusting py_vollib_vectorized's "vectorized" speed claim, and before reaching for backtrader for anything options.
---

# Options Python libraries (pricing / Greeks / IV / backtesting)

Verified 2026-07-24 by EXECUTION on this machine — Python 3.14.5, numpy 2.3.5, pandas 3.0.3, scipy 1.17.1, numba 0.66.0; `pip install --user`, no sudo. Verdicts are from running the code, not the README. Don't re-derive Black-Scholes — it's here and cross-checked three ways (anchor: BS call S=K=100 t=0.25 r=5% σ=20% → price 4.6150, delta 0.5695).

## USABLE now

| Package | Install | Gives | Verified |
|---|---|---|---|
| `vollib` | `pip install --user vollib` | BS / BS-Merton / Black-76 price, IV (Jäckel), analytical Greeks | price 4.6150, IV→0.200000, delta 0.5695 — matches QuantLib + mibian |
| `QuantLib` | `pip install --user QuantLib` | American/exotic pricing, curves/term-structure, day-count/calendars, `BlackVarianceSurface` (vol surface) | installs on 3.14 via cp39-abi3 wheel; Euro Greeks match vollib; American early-ex premium computed |

Import from `vollib.black_scholes` — NOT `py_vollib.*` (py_vollib works but emits a DeprecationWarning pointing to `vollib`). vollib is the default for daily vanilla index/stock-option Greeks. Reach for QuantLib only when you need a vol-surface object, American/exotic payoff, or rigorous curves — NSE index & single-stock options are European-settled [INFERENCE], so vanilla work rarely needs it.

## TRAP — installs fine, does NOT deliver here

| Package | Why it fails for us |
|---|---|
| `py_vollib_vectorized` | Its whole point — vectorized array IV/Greeks — is BROKEN on our stack: every array call throws `numba.core.errors.TypingError: cannot type infer runaway recursion` (numba 0.66.0 / Py3.14 can't type its recursive `black()`). Broken for float / list-str / np-object alike. Import also monkeypatches the `py_vollib` namespace (scalar survives; scalar-only defeats the point). BS Greeks are closed-form → hand-vectorize with numpy + `scipy.stats.norm`. Revisit only if numba fixes recursive-jit typing. |
| `mibian` | Works (callPrice 4.6150, matches vollib) but strictly dominated: release 0.1.3 (2016), unmaintained, single-thread, clunky API (rate %, time in DAYS, vol %), fewer Greeks. Prefer vollib. |
| `backtrader` (options) | Zero options support — full namespace scan (core+indicators+analyzers) finds no strike/expiry/greek/straddle symbols; commission model is stock+futures-margin only. Fine for equity/futures; not an options backtester. |

## Options backtesting — `optopsy` (ADOPT-PARTIAL, reconnaissance only)

`pip install --user optopsy`. Genuinely options-native (singles, verticals, straddles, strangles, condors, butterflies, calendars, diagonals) and runs on pandas 3.0.3. Input = EOD chain DataFrame: `underlying_symbol, underlying_price, option_type, expiration, quote_date, strike, bid, ask`; filters are `**kwargs` (e.g. `long_calls(chain, max_entry_dte=50, exit_dte=7, otm_pct_interval=0.05, max_otm_pct=0.15)`). Output = return-distribution buckets by DTE × OTM% — verified 18 non-empty buckets.

GOTCHAS (verified): (1) SILENTLY returns an empty DataFrame when filters match nothing — always `assert len(result) > 0`. (2) Parametric distribution-bucketer, NOT path-dependent — no intraday stops, no COST_STANDARDS slippage, no circuit/ADV fill realism; fills at bid/ask mid. (3) Feeding our data needs ETL: index options in `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/` are 1-min OHLC with no bid/ask & no joined spot → resample to EOD, synth bid/ask from `close`±spread, join spot per `quote_date`, rename cols. Use for strategy-SHAPE triage; the firm's guarded harness stays the certification path.

Trust pip's version, not `__version__` (optopsy's attr reports 2.0.3 while pip installs 2.2.0).
