# COST STANDARDS — retail-conservative (Tara Singh owns)
> **STATUS: DRAFT — NOT BINDING until the Principal approves (D-020). Until approval, backtests must still USE these numbers and label results "draft-costs".**

## Per-order charges
| Item | Rate |
|---|---|
| Brokerage | ₹20 per executed order (discount broker) |
| STT — equity delivery | 0.1% both sides |
| STT — equity intraday | 0.025% sell side |
| STT — futures | 0.02% sell side |
| STT — options | 0.1% of premium, sell side (0.125% of intrinsic on exercise — avoid exercise; close positions) |
| Exchange txn — NSE equity | ~0.00297% |
| Exchange txn — options | ~0.035% of premium (NSE revised; verify annually) |
| GST | 18% on (brokerage + exchange txn + SEBI) |
| SEBI charges | ₹10/crore turnover |
| Stamp duty | 0.015% delivery buy · 0.003% intraday/options buy · 0.002% futures buy |

## Slippage floors (one-way, of traded value; DOUBLE for panic/exit-into-strength)
| Tier | Floor |
|---|---|
| Large-cap equity | 10 bps |
| Mid-cap | 20 bps |
| Small-cap | 35 bps |
| Micro | 50+ bps |
| Options — liquid ATM index | max(1 tick, 0.25% premium) |
| Options — single-stock near-ATM | max(1 tick, 0.5–1.5% premium) |
| Options — illiquid strikes (far OTM / far month) | 1–2% premium; **far-OTM single-stock wings: treat as UNTRADEABLE** (firm lesson: −883% stale-print artifact) |

## Liquidity & capacity
- Position ≤10% of 20-day ADV (≤5% micro-caps). Skip circuit-locked names. Options: standing OI or volume at the strike required (liquid_enough gate).
- Margin proxies: short strangle ~12% notional (SPAN+exposure); calendars = spread margin; short straddle-through-event ~14% notional. Worst-case MTM modeled, not average.

## Promotion rule
Every strategy must remain net-positive at **2× ALL of the above** before advancing to paper (RESEARCH_SOP gate 7). Paper reconciliation can only RAISE these numbers, never lower them without Principal sign-off.
