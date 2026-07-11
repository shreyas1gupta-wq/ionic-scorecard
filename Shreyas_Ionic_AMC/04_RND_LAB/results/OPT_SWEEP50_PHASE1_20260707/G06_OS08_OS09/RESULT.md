# G06 — OS-08 & OS-09 (0DTE high-theta family) — Phase-1 triage
_Campaign OPT-SWEEP-50 · Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP pass, 1× COST_STANDARDS · NOT a certification_

## Setups
- **OS-08** 0DTE expiry-morning ATM short straddle. Sell 09:20 (next-liquid-quote = 09:20 bar open), flat 15:15 OR **1.5× credit** intraday stop (tracked at 1-min close, exit at first breach bar).
- **OS-09** 0DTE ~10Δ short strangle (wider). Strikes chosen by BS delta with VIX-as-IV & T→15:30. Flat 15:15 OR **2× credit** stop (defined stop = Phase-1 default, not tuned).

## Data lineage
- NIFTY index options 1-min: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 261 valid weekly+monthly expiries **2021-05-27 → 2026-06-02** (1 stub `2026-06-09` excluded by `chain.py`). Read via pyarrow filter (trading_day==expiry, strike∈spot±800).
- NIFTY spot 1-min: `.../hf_index_options_1m/index/NIFTY.parquet` (entry spot = first bar ≥09:20; auction guard applied).
- INDIA VIX daily (OS-09 strike selection): `datasets/index_daily/india_vix.parquet` (2016→2026).
- **N = 259 trades each** (2 dropped: stub + 1 no-fill). One 0DTE trade per expiry day. Trades CSVs + summary.json in this dir.

## Guards
`lib/guards.py` imported; auction filter (≥09:15), tz→naive IST (chain.py), next-liquid-quote fill, DROP on zero-vol/zero-price entry bar, `degenerate_flags` run. Costs = COST_STANDARDS 1× (₹20/order, STT 0.1% sell premium, exch 0.035%, GST, stamp, SEBI; slippage max(1 tick, 0.25% premium) both sides, liquid-index tier). Booked in **exit period** (single-day 0DTE — no cross-day smearing).

## Validation battery (Phase-1 subset)
| Metric | OS-08 straddle | OS-09 strangle |
|---|---|---|
| ₹-points/trade (net, 1×) | **+6.69** | **+3.68** |
| %-of-SPOT/trade | **+0.0298%** | **+0.0173%** |
| Median ₹-pts | 3.91 | 4.03 |
| Sharpe (per-trade) | 0.096 | 0.239 |
| **Sharpe (annualised, √52)** | **0.69** | **1.72** |
| Win rate | 51.0% | **74.1%** |
| Win/Loss size ratio | 1.21 | **0.74** |
| Stop-out rate | 40.5% | 25.9% |
| Avg credit (pts) | 111.4 | 10.7 |
| Ann. return on spot-notional | ~1.6% | ~0.9% |
| **Worst single-day (pts)** | **−135.9** | **−70.3** |
| Worst-day σ-distance | −2.0σ | **−4.8σ** |
| Worst day / avg credit | −1.2× | **−6.6×** |

**Regime split (kill-test on Sept-2025 break):**
| | OS-08 pre / post | OS-09 pre / post |
|---|---|---|
| N | 222 / 37 | 222 / 37 |
| ₹-pts/trade | +4.23 / +21.49 | +2.74 / +9.30 |
| Ann Sharpe | 0.45 / 1.92 | 1.39 / 3.30 |
| Median ₹-pts | **−0.66** / +15.21 | +3.48 / +7.23 |

**Yearly ₹-pts/trade:** OS-08 → 2021 +14.8, **2022 −5.1, 2023 −2.0**, 2024 +11.4, 2025 +13.5, 2026 +17.5 (2 losing years). OS-09 → +2.1/+2.7/+2.1/+2.8/+4.7/+12.4 (**positive every year**).

## Degenerate flags
- OS-08: none.
- OS-09: **tail-seller profile** — win 74% with W/L 0.74; `degenerate_flags` fired "Sharpe>4" (that 4.1 is a √252-over-annualisation artifact of the detector on a weekly series; honest √52 Sharpe = 1.72). Real read: **high standalone Sharpe masking a fat left tail** (CIO book rule #1).
- **Tail confirmed GENUINE, not artifact:** OS-08 worst days = 2022-02-24 (Russia invades Ukraine, ~−4.7% NIFTY) & 2024-04-18 (Iran-Israel). OS-09 worst = Jan-2025 & Dec-2024 selloffs. **Stops gapped through: 89→222 = 2.5× credit despite a 1.5× stop.** 0DTE stops are not protective; gamma gaps through. Worst 5 trades = ~35% of OS-08 gross P&L.

## Verdict — both KILL (do not advance to Phase-2)
Neither trips the pre-registered edge-sign kill (both positive in ₹-pts AND %-spot, survive next-liquid-quote fill). **But neither is close to the campaign bar (XIRR>50% AND Sharpe>2 post-cost)**, and both carry the disqualifying 0DTE left tail this group was told to police.

- **OS-08 — KILL.** Ann Sharpe 0.69 (≪2); ~1.6%/yr on notional (≪50% XIRR even leveraged); **lost money in 2022 AND 2023**; pre-Sept-2025 median trade is **negative** (mean carried by a few outliers); edge disproportionately in the 37-trade post-Sept window. Worst day −135.9 pts (>1× credit) blew through the 1.5× stop. A real but marginal VRP scalp, nowhere near the bar.
- **OS-09 — KILL (real edge, wrong shape).** Positive every year and ann Sharpe 1.72 is the best in this group — but still <2, return is a trivial ~0.9%/yr on spot, and the profile is textbook penny-in-front-of-steamroller: **74% win rate hiding a −4.8σ, 6.6×-credit worst day** that the 2× stop could not contain. [INFERENCE] survives 2× cost weakly (~+2.4 pts) so cost isn't the killer — the **tail is**. Standalone Sharpe here is largely short-vol regime beta; the honest Phase-2 test is incremental Sharpe over S-04/S-05, which it will not clear.

**Single weakest assumption (both):** that an intraday credit-stop caps the loss on 0DTE. It does not — every worst day gapped through the stop at 2–2.5× credit. Any resurrection must model gap-through / defined-risk wings, size ∝ 1/IV (A.4), and prove INCREMENTAL Sharpe over the existing short-vol book, not standalone.
