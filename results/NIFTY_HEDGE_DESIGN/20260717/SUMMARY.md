# NIFTY holdings — best options overlay for max Sharpe / least MDD (2026-07-17, DESK-20)
Design test: LONG 1-lot NIFTY + monthly ~30-DTE overlay, held to expiry. Real NIFTY bhavcopy + Nifty-50 daily, **2020-2026, 91 monthly cycles**, **DAILY mark-to-market of every option leg** (v1 stepped-at-expiry version was wrong — it missed the intra-month put cushion and inflated hedged-vol; discarded). Costs: slip max(0.05,0.5% prem), ₹20/leg, STT 0.1% sell / 0.125% exercise, exch+GST. Settle via landmine-9. Corpus ≈ ₹9L (1 lot).

## RESULTS (ranked; near-month NIFTY options are liquid → fills realistic, unlike far-dated wings)
| Overlay | CAGR | Vol | **Sharpe** | Sortino | **MaxDD** |
|---|---|---|---|---|---|
| Buy & hold NIFTY (baseline) | 10.9% | 18.0% | 0.32 | 0.37 | −37.6% |
| Covered call (sell 3% OTM CE) | 9.0% | 16.3% | 0.22 | 0.23 | −36.2% |
| **Tail put (buy 10% OTM PE)** | 10.6% | 14.8% | **0.33** | **0.44** | **−21.9%** |
| Protective put (buy 5% OTM PE) | 8.7% | 14.4% | 0.21 | 0.30 | −19.8% |
| **Collar (buy 5% PE + sell 5% CE)** | 7.9% | 13.4% | 0.16 | 0.20 | **−17.7%** |
| Put-spread + call (buy5/sell2 PE + sell8 CE) | 12.4% | 19.8% | 0.37 | 0.42 | −40.0% |

## RECOMMENDATION (depends on which objective)
**#1 — Best all-round hedge = systematic 10% OTM monthly puts ("Tail put").** It *dominates* buy-and-hold: same Sharpe (0.33 vs 0.32), **much better Sortino (0.44 vs 0.37)**, MaxDD cut **42%** (−21.9% vs −37.6%), and barely any return give-up (10.6% vs 10.9% CAGR). The 10%-OTM put is cheap enough that the monthly bleed is tiny, yet it catches the crash. This is the "most protection per rupee of carry" — the answer to "max Sharpe *and* less drawdown."
**#2 — If you want the smallest possible drawdown = Collar 5%/5%.** Halves MaxDD to −17.7% and gives the lowest vol (13.4%), but the 5% call cap costs ~3pp/yr of CAGR in a bull → Sharpe drops to 0.16. Choose only if capital preservation strictly beats return.
**#3 — Protective put 5%** sits between: −19.8% MaxDD, keeps full upside (no cap → Sortino 0.30 > collar's 0.20), CAGR 8.7%.

## HONEST CAVEAT — the result is regime-dependent
The put-based overlays win **because 2020-26 contained the COVID crash** (plus the 2024-election and 2025 dips). In a crash-free stretch the long puts would bleed and *reduce* Sharpe. So "buy puts" is not free alpha — it's insurance that looks great in a sample that had a fire. The robust, honest read: **the 10% tail put is the cheapest way to cut tail risk with negligible return drag, and it improves risk-adjusted return whenever a crash occurs within the holding period.** The covered call and put-spread+call *harvest premium* (higher CAGR/Sharpe in calm-to-up markets) but do NOT protect — the put-spread's "best Sharpe 0.37" comes with the *worst* drawdown (−40%), so it fails a hedging goal.

## Concrete rule for the winner (Tail put)
Each month, on the first session after expiry, buy 1 lot of the ~10%-OTM NIFTY put on the near-month (~30-DTE) expiry (nearest 50-strike with CONTRACTS>0), hold to expiry, roll. Budget ~0.3-0.5% of notional/month in premium; it pays for itself only in down months — size it as insurance, not income.
Artifacts: `metrics_v2.json`, `cycles.csv`.
