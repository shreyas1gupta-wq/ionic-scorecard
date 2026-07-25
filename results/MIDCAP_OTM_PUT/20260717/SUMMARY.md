# MIDCPNIFTY ~5% OTM monthly PUT, 1 lot, held to expiry — 2026-07-17 (DESK-20, ad-hoc Principal check)
Data: **real** NSE F&O index bhavcopy 2022-2026. No synthetic prices. CONTRACTS>0 gated at entry; settlement via landmine-9 (expiry-day option SETTLE_PR = underlying settle). Costs: retail buy-side (₹20/leg, entry slip max(0.05, 2% prem), exch+GST ~0.05%, exercise STT 0.125% on intrinsic). Primary unit = index POINTS/lot (MIDCPNIFTY lot changed over time; ₹ at lot=120 labeled).

## TWO CAVEATS FIRST (these shape everything)
1. **Only 27 of 56 monthly cycles were tradeable; ALL of 2022 + most of 2023 skipped — "no traded PE at entry."** At ~30-DTE the 5%-OTM wing put had CONTRACTS=0 on the entry day in the early years (midcap monthly options were thin at the wings; matches the Kavya bhavcopy note). The gate correctly refused to fabricate a fill. So this is NOT a clean 2022-26 test — it is **Oct-2023 → Jun-2026, 27 real fills.**
2. **Early fills are not faithful 5%-OTM.** When the 5% wing didn't trade, "nearest traded strike to target" fell back toward ATM — several 2023-24 trades are actually 0.8-2.8% OTM (one slightly ITM), paying 240-290 pts for a near-ATM put. **Only 2025-2026 fills are genuine ~5% OTM (otm 4.6-5.4%, hundreds-thousands of contracts).** Judge the strategy on those; the early rows overstate premium paid.

## RESULT (27 tradeable months, Oct-2023 → Jun-2026)
| Metric | Value |
|---|---|
| Net P&L | **−951.7 pts/lot ≈ −₹114,198** (lot 120) |
| Gross (pre-cost) | −882.0 pts |
| Expired worthless | **81.5%** (22 of 27 months) |
| Net-profitable months | 18.5% (5 of 27) |
| Total premium paid | 3,009 pts; avg 111 pts/month |
| Avg net / month | −35.3 pts (the carry cost) |
| Best / worst month | +711 (Mar-26, midcap −8.7% into expiry) / −298 (Jul-24, near-ATM, worthless) |

**The 5 paydays:** Mar-2026 +711, Oct-2024 +449, Feb-2025 +254, Oct-2023 +143, Jan-2026 +22 — every one a sharp midcap drop into that expiry. All 22 other months bled the full premium.

## READ
- Textbook tail-hedge bleed: pay insurance monthly, ~4 in 5 expire worthless, rare crash expiry pays big. Over a window where midcaps were mostly in a strong bull, a standalone long-OTM-put book **lost money — as expected**. Not an alpha; it is insurance you pay for.
- The **useful number for hedge sizing**: carrying this protection cost ~35 pts/month ≈ ~0.3% of notional/month (~3-4%/yr) net, and it did fire (+711, +449) in the two real midcap air-pockets — consistent with our valuation-regime hedging study (annual/rolling put protection cuts DD at a few pp/yr cost).
- Standalone verdict: **NO** (bleeds in bull/sideways). As an overlay on a long-midcap book, it's a real, sized cost — quantified above.

## ADDENDUM 1 — year-restricted (Principal: "only 2020, 2022, 2025")
- **2020: IMPOSSIBLE** — 0 MIDCPNIFTY option rows (index F&O launched 2022-01-24; only NIFTY/BANKNIFTY/NIFTYIT had 2020 options). Refused to synthesize.
- **2022: UNTESTABLE** — even relaxing entry to the first liquid day in the first 7 days of each cycle, the 5%-OTM wing put never traded at monthly entry (0/11 months). Thin early midcap wings, not a bug.
- **2025: +204.6 pts/lot ≈ +₹24,551 (POSITIVE, the one clean year).** 11 months, 81.8% still worthless, but Jan-2025 (+627, bought 12500 put @75 → settle 11795) and Feb (+254) caught the H1 midcap selloff and paid for the whole year. Confirms the tail-hedge-pays-in-the-crash thesis where we can actually test it. `trades_2025.csv`.

## ADDENDUM 2 — the OPPOSITE trade: SELL ~5% OTM CALL monthly, 1 lot, held to expiry (`ce_sell_trades.csv`)
Same real data, same cadence. **NAKED short call = undefined upside risk; hold-to-expiry IGNORES mid-month MTM/margin calls — so these losses are the OPTIMISTIC path.** Sell-side costs (STT 0.1% of premium, exch+GST, brokerage, entry slippage).
| Scope | Net pts/lot | ≈₹ (lot 120) | Win% | Kept-full% | Worst month |
|---|---|---|---|---|---|
| All tradeable (2023-10→2026-06, 30 mo) | **−801.2** | −96,142 | 76.7% | 66.7% | −708 (Apr-2026, midcap +12% rally) |
| 2025 (11 mo) | **+209.6** | +25,147 | 81.8% | 81.8% | −228 (Apr-2025) |
| 2022 / 2020 | untestable / impossible | — | — | — | — |
- Classic short-vol shape: **wins small ~77% of months, then gets run over by sharp UP months** (Apr-2026 sold 13100 call @172 → midcap ripped to 13976 → paid 876 intrinsic; May/Jun-2024 post-election rallies −335/−315). Negative overall because 2023-26 midcaps had violent rallies. The 77% win rate is the picking-up-pennies illusion — negative expectancy, huge losers.
- **Margin reality (critical):** naked call selling needs ~₹1.5-2L margin/lot; −96k must be read against that capital, and Apr-2026's −708 would very likely have triggered a mid-month margin call / forced exit BEFORE expiry — the real path is worse than this backtest shows.

## The pairing (what it actually teaches)
- **Buy 5% OTM put monthly:** −952 pts overall (bleeds in the bull), +204 in 2025 (the crash paid).
- **Sell 5% OTM call monthly:** −801 pts overall (rallies run it over), +209 in 2025.
- BOTH lost money over 2023-26; BOTH were positive in 2025 — because 2025 was a down-then-grind-up year (sharp H1 fall rewards put-buyers AND leaves calls unbreached; gradual recovery rarely breached the 5% call). Neither is a standalone edge — both are regime bets. Call-selling additionally carries the undefined-risk/margin-call landmine the hold-to-expiry math flatters.
- Reverse-strategy note (per firm default): the informative reverses are put-SELL (collect premium in the bull, blow up in the Jan-2025 crash) and call-BUY (bleed, pay in rallies) — not run here; available on request.

## ADDENDUM 3 — return-stack: LONG Midcap Momentum 50 ETF corpus + SELL 1-lot ~5% OTM MIDCPNIFTY put monthly
Principal's "pledge the ETF, sell puts on top" idea. Underlying = **Nifty Midcap Momentum 50 index NAV + 0.40%/yr ETF-expense drag** (real ETF proxy; on-disk `etf_momentum50.parquet` REJECTED — only 0.916 return-corr to the Midcap Momentum 50 index = a different momentum flavor, would have been the wrong underlying). Window **2024-02 → 2026-02** (~2yr, capped by index NAV end + put-liquidity start), corpus = ₹12.36L (1-lot notional), 23 puts. `etf_putsell_trades.csv` / `etf_putsell_metrics.json`.
| | Total ret | CAGR | **MaxDD** | Vol |
|---|---|---|---|---|
| ETF only | +17.5% | 8.1% | **−25.8%** | 20.3% |
| **ETF + put-sell overlay** | **+22.0%** | **10.1%** | **−30.3%** | 20.8% |
| Overlay adds | +4.5pp | +2.0pp | **−4.5pp DEEPER** | +0.5pp |
- Put leg standalone: collected ₹212k premium over 23 months, **net +₹56k** after payouts, 82.6% expired worthless — mildly POSITIVE (selling puts in a mostly-up midcap market, unlike buy-put and sell-call which lost).
- **But the overlay DEEPENED the worst drawdown −25.8% → −30.3%** — exactly the correlated-risk trap: in the Jan-Feb 2025 midcap crash the ETF fell AND the short puts paid out (−₹75.8k + −₹31.3k = −₹107k across two expiries), stacking losses on the same event. It's **leverage dressed as income, not a hedge.** Calmar barely moved (0.31→0.33): the extra ~2pp/yr return was bought with ~4.5pp more downside.
- **The killer the hold-to-expiry math HIDES (flag loudly):** this is the Kirubakaran pledge-and-sell structure, and its real failure mode is a margin spiral — in the Jan-2025 crash the pledged ETF collateral FALLS (pledge value drops ~25%) at the exact moment the short put goes deep ITM and its SPAN margin SPIKES → forced liquidation risk mid-month, before the +₹56k "hold-to-expiry" outcome is ever realized. My realized-at-expiry curve understates the intra-crash combined drawdown (real MTM accrues the put loss through January, coincident with the ETF trough, so true peak-to-trough is worse than −30.3%).
- Verdict: return-stacking that works in calm/up months and bites hard in the one crash — same lesson as KIRU-combined and the firm's monthly-correlation landmine (both legs are long midcap beta; they are NOT diversifying). If pursued, the honest fixes are (a) size the put far smaller than the ETF corpus (not 1:1), (b) a defined-risk put SPREAD not a naked short put, (c) an explicit margin-buffer rule so a pledge-value drop can't force liquidation.

## Honest limits
Fill realism is shaky for the thin early wings (some entries had 5-11 contracts total — a retail 1-lot might not fill at CLOSE). Held-to-expiry only (no "roll at 50% loss" or "monetize the spike" management, which is how tail hedges are actually run and would change the P&L). Entry ref = near-month FUTIDX close (small basis vs spot, immaterial at 5%). Artifacts: `trades.csv`, `metrics.json` in this dir.
