# Bond + net-short NIFTY options overlay — 2026-07-17 (DESK-20, ad-hoc Principal check)
Spec (confirmed): corpus in **10%/yr bond**; every **6 months** BUY 7.5% OTM NIFTY put (always) + SELL 10% OTM NIFTY call (filtered), both ~6M expiry, held to expiry. **NO long equity → net-short tilt.** Real NIFTY bhavcopy + real Nifty-50 daily (2020-2026). Settle via landmine-9. Corpus ₹9.14L (1-lot notional), 11 semi-annual rolls, window 2020-01 → 2026-06.

## CAVEATS (small-sample, read before the numbers)
- **n = 11 semi-annual rolls** — illustrative, not statistically robust. A couple of rolls dropped (no fillable 6M put in the window).
- **6M 7.5%-OTM puts are THIN** (~1 traded strike near target); a retail 1-lot may not fill at CLOSE. Call filter samples are tiny (RSI/200SMA fired only 3 of 11).
- 10%/yr bond = your assumption (real AAA/G-sec ~7-8%). NIFTY lot=75 assumed (changed over time). Hold-to-expiry ignores intra-period MTM/margin on the short call.

## RESULT — every options variant UNDERPERFORMED the bond alone
| Variant | Total ret | CAGR | MaxDD | Calls sold | Call P&L |
|---|---|---|---|---|---|
| **Bond only (baseline)** | — | **10.0%** | ~0 | — | — |
| + put only (no call) | +45.8% | **~7.1%** | ~0 | 0 | — |
| + put + call, RSI>70 filter | +44.0% | 6.9% | −1.0% | 3 | −₹16k |
| + put + call, ALWAYS sell | +33.4% | 5.4% | −14.8% | 11 | −₹113k |
| + put + call, high-ATR filter | +33.4% | 5.4% | −15.0% | 6 | −₹113k |
| + put + call, below-200SMA filter | +27.3% | 4.5% | −15.0% | 3 | **−₹169k** |

**Contribution decomposition (₹, over 5.5yr):** bond **+499,808** (the engine) · long-put **−81,592** · short-call −16k to −169k depending on filter.

## WHAT IT TEACHES
1. **The overlay is a drag on the bond in a bull market.** Bond alone = 10% CAGR; the best overlay (put-only) = ~7.1%; always-sell-call = 5.4%. You paid ~3-5%/yr of the bond's 10% to run a net-short options book while NIFTY rose — the structure only wins in a sustained bear/crash, not the 2020-26 tape.
2. **The put paid ONCE (COVID, Jun-2020: +1,081 pts as NIFTY fell −15.5%) and bled the other 10 rolls** — net −₹82k ≈ −1.6%/yr. Genuine crash insurance, but 5.5 years of premium bleed exceeded the single payoff.
3. **The 200SMA filter is actively HARMFUL here — the standout finding.** "Sell the call only when spot < 200SMA" sold calls at market bottoms → straight into the sharpest recoveries (Jun-2020 → +34.7% → call −₹2,227/lot that roll). A trend filter that fires at the bottom is the worst possible call-selling trigger. **RSI>70 (sell only when overbought) was the least-bad** (−₹16k, but n=3 — likely partly luck).
4. **Best version = don't sell the call at all.** Over this window the short call hurt under every filter except RSI (which barely broke even); dropping it (put-only) preserved the most of the bond yield.

## VERDICT
As a standalone return vehicle vs a 10% bond: **NO** — it gave up 3-5pp/yr of the bond in a bull run. As a tail-hedged defensive sleeve it "works" only if you expect a sustained bear; the cost of carry is ~half the bond yield. If pursued: drop the short call (or gate it to overbought-only), and note the whole thing lives or dies on whether the next regime is the crash the put is waiting for. Artifacts: `periods.csv`, `metrics.json`.
