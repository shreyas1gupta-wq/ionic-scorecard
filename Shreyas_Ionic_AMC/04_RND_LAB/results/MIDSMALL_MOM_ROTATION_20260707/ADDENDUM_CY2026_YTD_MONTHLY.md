# Forward extension — CY2026 YTD + monthly returns (net of cost)
Arjun Rao · 2026-07-07 · frozen 2017->2026-01-22 backtest untouched; this chains frozen Jan-2026 daily returns with a forward run on fresh yfinance data through 2026-07-03.

## CY2026 YTD (Jan 1 -> 2026-07-03), net of all costs

| Series | CY2026 YTD |
|---|---|
| Variant A (mid+small, N500∖N200) | +20.2% |
| Variant B (full N500) | +13.9% |
| Nifty 500 (buy-hold, price index) | −2.4% |

Both variants massively beat the Nifty 500 in 2026 — but read how: the strategy sat in GOLD for essentially all of Jan-20 Apr (Smallcap 100 below its 200-EMA), exactly when equities fell (Nifty 500 −11.4% in March alone) and gold rallied. It re-entered equity on 2026-04-21 and rode the recovery. This year's outperformance is the regime filter + gold sleeve doing capital preservation, not momentum stock-picking — same verdict as the main backtest, shown live.

## Month-by-month 2026 (net of cost) + regime state mix

| Month | Var A | Var B | Nifty 500 | State mix (equity / gold / cash days) |
|---|---|---|---|---|
| Jan | +8.7% | +11.5% | −3.3% | 3 eq / 17 gold / 0 cash |
| Feb | +0.4% | +0.4% | +0.4% | 0 eq / 20 gold / 0 cash |
| Mar | −7.9% | −7.9% | −11.4% | 0 eq / 19 gold / 0 cash |
| Apr | +8.2% | +6.6% | +10.5% | 7 eq / 13 gold / 0 cash |
| May | +5.0% | +5.4% | −0.1% | 19 eq / 0 gold / 0 cash |
| Jun | +6.7% | +0.4% | +1.5% | 21 eq / 0 gold / 0 cash |
| Jul (stub, 3 days) | −1.4% | −2.1% | +1.3% | 3 eq / 0 gold / 0 cash |

State mix is identical for A and B (regime driven by Smallcap100 index, common to both). CY2026 to date: 69 gold days / 53 equity days / 0 cash days (57% gold, 43% equity) — a gold-heavy year. Zero cash days in 2026, so the YTD number does not depend on the 6.25% cash-carry assumption at all.

Reading the months:
- Jan-Mar: near-fully in gold. Feb flat, March −7.9% (gold fell) but still beat Nifty 500's −11.4% — the filter avoided the worst of the equity drop.
- Apr: 13 gold days + re-entry into equity on Apr-21 (7 equity days, 2 baskets — the ones reported in the April addendum). Underperformed the +10.5% Nifty rally because it was in gold for two-thirds of the month and re-entered late — the classic slow-200-EMA lag.
- May-Jun: fully in equity, biweekly rebalancing (Apr-29, May-14, May-29, Jun-12, Jun-29). Var A (midsmall) beat Var B in June (+6.7% vs +0.4%) — in the 2026 equity window, midsmall momentum outran full-cap, the opposite of the full 2017-2026 backtest where B dominated. Period-specific, not a reversal of the structural finding.

## Data sources & method
- Universe prices (Feb-2026 onward marking + signals): yfinance (.NS, auto_adjust), 2025-09-01 -> 2026-07-03, 498/502 names (99.2%), OHLCV, cached scratchpad/fx_ohlcv.pkl. Splice validated vs frozen panel over the 99-day overlap: median daily-return corr 1.000.
- Jan-2026 daily returns: taken verbatim from the frozen backtest series (panel/HF basis) — not recomputed.
- Smallcap 100 (regime 200-EMA), GOLDBEES (gold sleeve), Nifty 500 (benchmark): already on disk through 2026-07-03/06 — no pulls needed for these three.
- Method: exact frozen engine logic (regime state machine + biweekly rebalance + full COST_STANDARDS cost stack + execution_realism fill checks) forward from the verified 2026-01-22 GOLD state (matched the frozen timeline exactly), on a Rs1cr book, chained daily returns. 1-day execution lag preserved. Today is 2026-07-07 so all of this is historical, not a forward/live call.
- Bug caught & fixed mid-run: first forward pass initialized the book at a notional 1.0 instead of Rs1cr, making the flat Rs20/order brokerage 20x the whole book and producing a nonsensical -2418% April. Fixed by running on a Rs1cr book (returns are scale-invariant ratios otherwise, this only corrects flat-fee scaling); the frozen backtest already used Rs1cr and was never affected.

## Bottom line
2026 YTD is a strong year for the strategy (+20% Var A / +14% Var B vs −2% Nifty 500), and it's a textbook demonstration of what this strategy actually is — a drawdown-avoidance / gold-rotation overlay, not a stock-picker. The whole 2026 edge came from being in gold while equities fell Jan-March, not from the momentum baskets (which only ran from May onward).
