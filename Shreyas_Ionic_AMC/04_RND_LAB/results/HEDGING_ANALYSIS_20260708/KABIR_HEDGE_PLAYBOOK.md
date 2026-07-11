# Hedging Playbook — valuation × momentum sub-regimes
**Owner: Kabir Anand (E-028), Head of Hedging & Tail Risk · 2026-07-08 · net-hedge-positive discipline enforced**

Governing rule (hard): every overlay is **net-neutral or net-hedge-positive — never net-short protection**. The programmatic filter allowed 20 structures and **banned 4** (`H_putratio_1x2_95_85`, `P_ratio_2x1_95_85`, `P_riskrev_95_105`, `P_shortcall_102`). The 3:1/3:2/3:3 put ratios survive — they *buy more than they sell* (net-long convexity). Only "sell 2 to fund 1" is banned. Evidence: the banned 1×2 ratio deepened the COVID-India drawdown to **−50% vs −37% unhedged** — a "hedge" that amplified the loss. [DATA]

## 1. Sub-regime playbook
| Sub-regime | Objective | Recommended (net-hedge-positive) | Tenor | Why — and why net-short is rejected |
|---|---|---|---|---|
| **CHEAP_FALLING** (cheap, 12m<0) | Cheap insurance while the knife falls; don't over-pay | Put-spread-collar (defined) or ATM put | Monthly/Qtrly | Still-falling tape = keep protection but cheap; short-tail ratios blow up exactly on the continuation leg down. |
| **CHEAP_RECOVERING** (cheap, 6/12m>0) | Stay long the rebound, floor the downside | **Long ATM put** (keeps full upside) | Monthly/Qtrly | The rebound is the prize — a collar would cap it. Long put is net-hedge-positive and uncaps upside. [DATA: India large-cap CHEAP_RECOV maxDD −28.7%→−5.7%] |
| **FAIR** | Cheap tail cover, minimal drag | Annual collar (or ATM put if upside sacred) | Annual > semi | Nothing urgent; finance the put with an upside call you're relaxed about giving. |
| **RICH_CALM** (rich, not extended) | Systematic tail protection, low carry | **Annual collar 95/105** | Annual | Best risk-adjusted protection: US maxDD −48%→−6.7%, Sortino 3.5. Selling premium here = short the very tail the valuation flags. |
| **RICH_EXTENDED** (rich + overbought) | Maximum tail defense; add convexity | **Annual collar 95/105** + small **1×2 put backspread** kicker | Annual | Expensive *and* euphoric = highest asymmetric downside. Collar caps carry; backspread (net-long) pays in a crash. Never fund it by selling downside. [DATA: US RICH_EXT maxDD −38%→−7%, cost ~0.8%/yr] |

## 2. Current call by segment (2026-07)
- **U.S. S&P 500 — RICH_EXTENDED (CAPE 41.8, overbought).** [DATA] The single most dangerous quadrant. Put on the **annual collar 95/105** as the core (tail −38%→−7% for ~0.8%/yr) and a **small 1×2 put backspread** as a convex crash kicker. Do not sell premium. This is the highest-conviction hedge in the book right now. [OPINION]
- **India NIFTY 50 — CHEAP_FALLING (P/B 3.19 cheap, 12m<0).** [DATA] Large-caps are genuinely cheap but the tape is still soft — hold a **cheap monthly/quarterly defined put-spread-collar**, light. In-sample India large-cap drawdowns in this state were small (−2.7%), so don't over-hedge; the bigger risk is the broad/median market, not the index. [INFERENCE]
- **India broad market — RICH_CALM (true median stock ~25.6× vs NIFTY-50 21×).** [DATA] The headline index masks that the *typical* stock is in its rich quartile. Overlay a **monthly/quarterly ATM NIFTY put** on broad/mid exposure (maxDD −7.8%→−2.5%). This is the India action item the cap-weighted lens hides. [OPINION]
- **India small-cap — FAIR, but ~20% vol and −40%+ drawdowns.** [DATA] ATM-put overlay tests best of any cell (maxDD −40%→−9%) **but no liquid small-cap options exist in India** — so the *executable* hedge is NIFTY/Midcap index puts (accept beta & basis risk), index-futures short, or simply cutting exposure when the median-PE signal turns RICH. Treat the modeled small-cap option as illustrative. [DATA/OPINION]

## 3. Three things I'm watching
1. **US RICH_EXTENDED is the standing risk** — extended + expensive historically precedes the fat-tail entries (1929/2000/2008). Keep the collar rolled; do not let it lapse chasing the last of the rally. [OPINION]
2. **India's two lenses disagree** — NIFTY-50 says cheap, median stock says rich. Trust breadth for the broad/mid book; the hedge belongs there, not on the large-cap index. Escalate India large-cap to a full collar only if P/B > ~4.0 or it flips to RICH_EXTENDED. [INFERENCE]
3. **IV level at entry is everything** — every strong hedge outcome (COVID) came from protection bought while VIX/iVIX was low. If iVIX/VIX spikes first, the collar's short-call side cheapens the put — prefer collars/backspreads over outright puts once vol is already elevated. [DATA]

*Caveats: full-sample regime thresholds (hindsight for the lines only); India sub-regime cells are small (n often <20) — directional, MC-corroborated, not certified; costs DRAFT.*
