# Structuring Memo — Valuation×Momentum Sub-Regime Hedges (2026-07-08)
**From:** Aakash Jain (E-022), Derivatives Structurer | **Reviewing:** V3 engine output (owner Kabir Anand E-028)

## 1. Net-hedge-positive filter — VALIDATED, one flag
[DATA] Filter (engine_v3.py) bans exactly 4: `H_putratio_1x2_95_85` (net short 1 put), `P_ratio_2x1_95_85` (same shape), `P_riskrev_95_105` (short call, uncapped loss), `P_shortcall_102` (naked). All are short convexity. [OPINION] Sound — but it is a *sign* filter, not a *magnitude/capital* filter. That's the gap.

**Flag — `P_ratio_3x3_95_85` (and 3x-family):** 3x3 at 95/85 is NOT a distinct payoff — it is a plain 95/85 bear put spread **scaled 3×**. It tops play rankings purely because the backtester scales notional 3× on the same base: 3× margin and 3× premium for the same per-unit shape. [OPINION] Treat 3x1/3x2/3x3 as "the 1:1 structure × a leverage dial" — pick the multiplier from the capital budget, never from the ranking label. Do not size off "3x3 ranked #1"; re-derive at 1x and scale to the risk budget. (Same category error as the S-04 lesson: sizing levers are not return-adders.)

## 2. Executable vehicle per current sub-regime

### US S&P 500 — RICH_EXT → Annual Collar
[DATA] maxDD −7.1% vs −37.7% unhedged, CVaR5 +15.8pt, cost 0.82%/yr, Sortino 2.0.
- **Instrument: SPX index options** (cash-settled European; LEAPS to 12m liquid at 5-10% OTM). NOT ES futures options (American, worse long-dated liquidity); reserve ES for tactical delta only.
- **Strikes:** buy put 95%, sell call **105–110%** — [OPINION] bias to the wider 110 call given CAPE 41.8 with historically positive concurrent RICH returns; OTM call is cheap at 12m tenor so upside retention costs little.
- **Tenor:** annual LEAPS, roll 1×/yr (annual ≫ monthly — monthly pays skew 12×/yr).
- **Margin:** collar covered vs long index — incremental margin ≈ net premium, no naked-call margin.
- **Liquidity:** SPX is the deepest options market on earth — fully executable at institutional size; the ONE segment where far-dated OTM wings are no problem.

### India NIFTY 50 — CHEAP_FALL → Monthly Put-Spread Collar (95/85 put spread + short 105 call)
[DATA] maxDD −2.0% vs −2.7%, near-zero modeled cost, n=15.
- [OPINION] Note it's a 3-leg structure: the short 85% put **caps protection below 85%** — acceptable in CHEAP_FALL only because in-sample worst was shallow; if CHEAP_FALL coincides with a genuine crash leg the cap binds exactly where needed. Regime-dependent bet, keep light.
- **Instrument:** NIFTY index options, monthly expiry (last Tuesday), cash-settled European; strikes round to 50-pt grid, negligible basis.
- **Margin:** book as a single combo order for NSE combo-margin benefit (else short put draws standalone SPAN); Tara to confirm exact treatment.
- [INFERENCE] The near-zero modeled cost (0.0001) is suspiciously close to breakeven — **Tara live-quote sanity check needed** (BS-modeled costs may understate real skew drag).

### India broad (median stock RICH) — RICH_CALM → ATM Put Overlay
[DATA] maxDD −2.5% vs −7.8%, cost ~1.4%/yr, Sortino 3.6.
- **Instrument:** NIFTY 50 ATM monthly puts as **proxy** — [DATA/OPINION] **basis-risk flag:** the signal says the MEDIAN stock is rich while cap-weighted NIFTY50 is cheap; if the correction concentrates in mid/small names while the top-50 hold, the NIFTY put underpays exactly when the thesis plays out. A Midcap150/Nifty500 put would track the signal better — [INFERENCE] but liquidity drops materially vs NIFTY50; check live OI before committing size (likely monthly ATM only, no far-OTM wings).
- **Margin:** long put only — premium upfront, simplest profile in the memo.

## 3. India small-cap (no options exist) — executable answer
| Option | Beta/basis fit | Liquidity | Verdict |
|---|---|---|---|
| NIFTY/Midcap150 put proxy | Weak in calm, converges in crash (lucky asymmetry) | Deep / moderate | Partial opportunistic tail hedge only |
| Index futures short | Same basis risk, no premium decay | Deep (NIFTY); verify Midcap150 OI | Margin (~10-15% SPAN) + monthly roll load |
| **Exposure cut** | **Perfect by construction** | N/A | **Primary lever** |

**Recommendation: exposure cut primary + small NIFTY/Midcap150 put as a convexity kicker; NOT futures as the main tool.** [OPINION] Zero basis risk / zero cost stack beats hedging with a mismatched instrument when beta is unstable. Smallcap-NIFTY correlation spikes in crashes (COVID), so a cheap NIFTY put bought in the current FAIR regime is a sensible low-cost tail catch — buy it while calm, size small. [DATA] The engine's smallcap ATM-put "hedge" costs 4.45%/yr with basis risk already showing as tracking error — real drag, partial tool, not primary.

## 4. Mechanics caveats (one per segment)
- **US:** SPX European = zero early-exercise/assignment risk. If SPY is substituted for granularity, American-style assignment risk on the short call reappears (esp. ex-dividend) — **stick to SPX for the short leg**.
- **India roll:** roll all legs 2–3 days BEFORE monthly expiry, not on expiry day (pin risk, gamma-driven spread widening, IV distortion) — propose as house policy.
- **India STT trap:** ITM index options that expire/settle are charged STT on FULL settlement notional, not premium — can silently exceed the option's benefit. **Always square off ITM protective puts before expiry.**
- **Smallcap proxy:** basis mismatch crystallizes at every monthly roll, not just final unwind — periodic realized-beta re-check between smallcap book and proxy index is required, not optional.

## Open items
1. Kabir/Ritika: label 3x-family ranking rows as "base structure × N" so downstream sizing never treats the multiplier as edge.
2. Tara: live-quote sanity check on the near-zero modeled cost of the India monthly put-spread collar (BS-modeled basis).
