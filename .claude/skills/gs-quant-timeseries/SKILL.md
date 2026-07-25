---
name: gs-quant-timeseries
description: Use when computing technical indicators (RSI, moving averages, volatility, MACD, Bollinger Bands, rolling beta/correlation, drawdown, z-score) on price series — before hand-rolling the formula, and before assuming any gs_quant "ratio" function (Sharpe/Sortino/Calmar/Treynor/skew/information_ratio) works without Goldman Sachs Marquee credentials.
---

# gs-quant (Goldman Sachs open-source) timeseries functions

`gs_quant.timeseries` ships a real, credential-free subset alongside institutional-only functions with deceptively plain names. Verified 2026-07-22 on this machine (`pip install --user gs-quant`, no sudo, no GsSession). Don't re-derive what's already here — see [[token-wise]] §10 for the reuse convention.

## USABLE now, no credentials, pure pandas Series in/out

| Function | Signature | Notes |
|---|---|---|
| `returns(series, obs=1, type=Returns.SIMPLE)` | price → period returns | `type=Returns.LOG` for log returns |
| `volatility(x, w=Window, returns_type=Simple, annualization_factor=None)` | rolling annualized realized vol | |
| `moving_average(x, w=Window)` | SMA | |
| `relative_strength_index(x, w=14)` | RSI, returns DataFrame | |
| `macd(x, m=12, n=26, s=1)` | MACD line | |
| `bollinger_bands(x, w=Window, k=2)` | upper/lower bands, returns DataFrame | |
| `beta(x, b, w=Window, prices=True)` | rolling beta of x vs benchmark b | both plain Series, no GS Asset needed |
| `correlation(x, y, w=Window, ...)` | rolling correlation | |
| `zscores(x, w=Window)` | rolling z-score of level | |
| `max_drawdown(x, w=Window)` | rolling max drawdown | the REAL drawdown function (see trap below) |
| `percentiles(x, y=None, w=Window)` | rolling percentile rank | |

`Window(size, ramp)` from `gs_quant.timeseries` controls the rolling window (e.g. `Window(60, 0)` = 60-period, no ramp-up skip). All of the above take a plain `w=int` too.

## TRAP — same-sounding names that need Goldman Marquee infra, NOT usable here

| Function | Why it fails for us |
|---|---|
| `sharpe_ratio(series, currency=...)` | internally fetches a **live risk-free curve** via `GsDataApi` → throws `MqUninitialisedError` without a `GsSession`. No float-rate override exposed at this level. |
| `sortino_ratio`, `calmar_ratio`, `treynor_measure`, `drawdown_length`, `skewness`, `information_ratio` | all require a GS Marquee **`report_id`** (a hosted portfolio report) — not a local calc at all, credentials or not. |
| `skew(asset, tenor, strike_reference, distance, ...)` | this is the **options volatility-skew measure** (needs a GS tradable `Asset`), NOT statistical skewness. For real skewness use plain `pandas.Series.skew()` — no gs_quant needed. |

Confirmed by direct signature inspection + a live call that hit `GsDataApi.get_market_data` and errored `GsSession is not initialised`. Don't re-trust the function name — check the signature (`Asset`/`report_id`/`Currency` args = institutional-only) before wiring it in.

For Sharpe/Sortino/max-drawdown on our own backtests, use the firm's existing verified implementations (e.g. `lib/execution_realism.py`, or the metrics helpers already in `STOCK_SCORECARD_750_CHEAPTEST_V2`'s backtest scripts) rather than gs_quant's report-bound versions.

## Worked example

`Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/scorecard_common.py` wraps `rsi`/`pct_returns`/`sma`/`realized_volatility` from this module with a `HAVE_GS_QUANT` try/except fallback (hand-rolled formula if the package is missing) — copy that pattern rather than importing gs_quant directly into a new script.

Install: `pip install --user gs-quant` (user-local, no admin needed on this laptop).
