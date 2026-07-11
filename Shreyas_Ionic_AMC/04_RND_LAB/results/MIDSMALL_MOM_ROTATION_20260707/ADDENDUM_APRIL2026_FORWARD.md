# Forward extension — April 2026 holdings
Arjun Rao · 2026-07-07 · same engine, incremental forward extension of the frozen 2017 -> 2026-01-22 backtest (backtest itself untouched).

## Regime path (pure function of Nifty Smallcap100 vs 200EMA, no stock prices needed)

| Window | State | Why |
|---|---|---|
| Apr 1 - Apr 20 | GOLD (out of equity) | Smallcap100 below 200EMA since mid-Jan; gold 3M return +10.8% (>0) -> gold, not cash |
| Apr 16/17/20 | (still gold) | Smallcap100 closed above 200EMA 3 consecutive days -> re-entry armed |
| Apr 21 | -> EQUITY (re-entry) | fresh top-15 picked, decision as-of Apr-20 close |
| Apr 21 - Apr 28 | EQUITY | holding re-entry basket |
| Apr 29 | EQUITY (biweekly rebalance) | new top-15, decision as-of Apr-28 close |

April 2026 = 13 days gold, 7 days equity — a mixed month with two equity baskets (unlike April 2025, which was fully out of equity).

## Variant A — mid+small (NIFTY500 minus NIFTY200), equal-weight 1/15

**Basket 1 - re-entry, held from 2026-04-21** (decision as-of 2026-04-20; eligible universe 298):
KIRLOSENG, MCX, GESHIP, THERMAX, SCHNEIDER, VTL, GVT&D, APARINDS, WELCORP, ANANDRATHI, INOXINDIA, ATHERENERG, KSB, ANGELONE, HFCL

**Basket 2 - rebalance, held from 2026-04-29** (decision as-of 2026-04-28):
KIRLOSENG, VTL, GVT&D, SCHNEIDER, WELCORP, GESHIP, HFCL, DATAPATTNS, MCX, APARINDS, AARTIIND, KSB, LLOYDSME, THERMAX, FINCABLES
(11 of 15 carried over from Basket 1; ANANDRATHI/INOXINDIA/ATHERENERG/ANGELONE out, DATAPATTNS/AARTIIND/LLOYDSME/FINCABLES in)

## Variant B — full NIFTY500, equal-weight 1/15

**Basket 1 - re-entry, held from 2026-04-21** (decision as-of 2026-04-20; eligible universe 497):
KIRLOSENG, NATIONALUM, POWERINDIA, VEDL, ABB, BHARATFORG, MCX, GESHIP, THERMAX, CUMMINSIND, SCHNEIDER, VTL, FEDERALBNK, GVT&D, APARINDS

**Basket 2 - rebalance, held from 2026-04-29** (decision as-of 2026-04-28):
POWERINDIA, KIRLOSENG, NATIONALUM, BHARATFORG, ABB, VTL, GVT&D, SCHNEIDER, WELCORP, GESHIP, ADANIENSOL, ADANIPOWER, BHEL, HFCL, DATAPATTNS

A vs B: B pulls in the largecap momentum leaders A excludes (NATIONALUM, VEDL, ABB, POWERINDIA, BHARATFORG, ADANIPOWER, BHEL, CUMMINSIND — all Nifty200 members). Shared theme: capital goods / power / industrials / metals momentum (KIRLOSENG, GVT&D, SCHNEIDER, THERMAX, APARINDS, GESHIP common to both). No zero-volume/no-fill names; all liquid (ADTV ~Rs13cr-880cr/day).

## Data sources

| Series | Source | Coverage |
|---|---|---|
| Universe stock prices | yfinance (.NS, auto_adjust=True), 2025-09-01 -> 2026-05-01 | 498/502 (99.2%); failed AKZOINDIA, GSPL, LTIM (ticker quirks), DUMMYHDLVR (dummy artifact in membership file, not a real stock) |
| Nifty Smallcap 100 (regime 200EMA) | already on disk, nse_official_all_indices.parquet, through 2026-07-06 | no pull needed |
| Gold (GOLDBEES) | already on disk, goldbees_daily.parquet, through 2026-07-03 | no pull needed |

Splice validation: yfinance vs frozen panel over 99-day overlap (2025-09 -> 2026-01-22): median daily-return corr 1.000, 100% of 497 names >0.95 — no discontinuity. Cached at scratchpad/fx_yf_close.parquet + fx_yf_vol.parquet.

Same 1-day execution lag as the main backtest (signal on decision-date close, executed next trading day). Today is 2026-07-07 so all of April 2026 is historical, nothing forward-looking. Frozen 2017->2026-01-22 backtest and its files were not modified.

## Caveats
1. Universe snapshot used is Sep-2025 (membership file's last snapshot) — if NSE's Mar-2026 semi-annual reconstitution changed a few names, immaterial for a top-15 cut but flagged.
2. yfinance is dividend+split adjusted vs the panel's price basis; negligible over a 6-month signal window (validated corr 1.000).
3. Full circuit-lock fill detection (needs intraday OHLC bands) not applied to this forward snapshot — checked execution-day volume instead (all non-zero); second-order given liquidity.
4. The Apr-21 re-entry basket is held only ~6 trading days before the Apr-29 rebalance largely replaces it — a live illustration of the high-turnover fragility flagged in the main report.
