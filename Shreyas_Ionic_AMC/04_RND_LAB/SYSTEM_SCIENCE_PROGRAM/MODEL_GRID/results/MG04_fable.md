**PRE-MORTEM RISK MEMO — Short Index-Options Book (Paper)**
From: Risk | Date: 14 July 2026 | Written as if: July 2027, the morning after our worst week ever

**Premise.** Last week contained the Union Budget and the RBI MPC decision. The book — short NIFTY premium: defined-risk credit spreads plus naked strangles — lost **~14% of NAV in five sessions**, erasing roughly six months of expected theta. This is what killed it.

**Working assumptions (scale linearly):** NAV ₹1 cr; NIFTY ≈ 26,000; lot 75. Six naked strangles at ±4% strikes (~200 pts credit each, ₹90k total); spreads with aggregate max loss ₹6L; opening margin ~18–20% NAV; book vega ≈ –₹10k per India-VIX point; expected P&L +0.4–0.7% NAV/week.

**The kill chain, in order**
1. **We were short the event, not the market.** Event-week IV looked rich (weekly straddle ~2.5%), so we sold the "post-event crush." Two events in one week meant no crush after event #1 — IV stayed bid for event #2, and theta's promise was repaid as vega.
2. **The gap did the damage before any rule could fire.** Budget tax shock: –3.4% opening gap. Strangle puts went 8-delta to 45-delta overnight. No intraday trigger protects against an open.
3. **We rolled instead of closing** ("vol mean-reverts"), then the MPC surprised two days later: another –4.2%. India VIX 14 → 27. Strangle gamma/intrinsic ≈ –6% NAV; spreads pinned near full max loss on the put side ≈ –5%; vega mark ≈ –1.5%. Note: defined-risk caps the loss, not the probability of realizing it.
4. **Liquidity and margin finished it.** Short options ballooning ITM plus an ad-hoc exchange margin hike pushed utilization past 85%; forced covering into spreads 8–15× normal width added ~1.5–2% NAV of pure slippage, with weekly-expiry gamma compounding it.

**Quantified tail** (paper fills; add 30–50% for live):

| Weekly scenario | Rough odds | Book P&L |
|---|---|---|
| Normal event week, IV crush | base | +0.4 to +0.7% NAV |
| ±1× implied move | ~1 in 3 | +1% / –1.5% |
| –6%, VIX ~25 (budget shock) | ~1 in 15 event-weeks | **–5 to –7%** |
| –9% over 2 sessions, VIX ~30 (Jun-2024 class: NIFTY –5.9% in a day) | ~1 in 30–50 | **–10 to –13%** |
| –13% day, VIX 60–80 (Mar-2020 class) | ~once a decade | **–15 to –22%, realized at forced-exit prices** |

Asymmetry: the plausible worst week is **20–40× the expected weekly gain**. The strangles are ~15% of deployed margin but drive over half the tail loss.

**Pre-committed de-risk triggers** (mechanical; pre-staged as basket orders; not debatable in the moment)
1. **T-2 rule:** by the close two sessions before the first event, zero naked short options — buy wings or close. Budget up to 30% of open credit for wings; pay it.
2. **Size caps:** event-week margin ≤ 35% NAV; aggregate defined-risk max loss ≤ 8% NAV; net vega no shorter than –₹10k/VIX pt.
3. **Strike rule:** no short strike inside 1.25× the straddle-implied move; if IV expansion pulls one inside, exit same session.
4. **VIX triggers:** India VIX > 18 close or +20% intraday → cut short vega 50%; VIX > 24 → flat all short premium.
5. **Spot triggers:** index touches any short strike → close that structure within 15 minutes, not at max loss; intraday move > 1× implied → halve the book.
6. **P&L circuit:** –2% NAV day → halve; –3.5% day or –5% week → flat, 10-session trading halt, written post-mortem before restart.
7. **Per-position stop:** any short structure marking ≥ 2.5× credit received → close.
8. **Margin rule:** utilization > 50% for any reason (including exchange hikes) → cut below 40% same session; never add capital to defend short options in an event week.
9. **Two-event rule:** if event #1 moves > 1× implied, no short gamma into event #2. Period.
10. **Halt protocol:** if index circuit breakers trip, exit 50% of remaining short gamma within 30 minutes of reopen via staged limits, the rest by close — decided now.

**What cannot be hedged at acceptable cost**
- **The overnight gap itself.** Wings sized for a 2020-class move cost 25–40% of gross theta; full protection ≈ no strategy. Sizing (trigger 2) is the only real control.
- **Post-shock liquidity.** First-30-minute spreads widen 5–20×; stops guarantee exit, not price. Tail slippage of 1.5–2.5× theoretical is budgeted, not hedged.
- **Trading halts.** Nothing lets us act during a halt; reopen risk is naked.
- **Vol-of-vol and put skew.** No liquid India-VIX derivative; a put ladder that truly caps skew blowout bleeds ~2–4% NAV/year — more than half the strategy's expected return. Above VIX 24 we exit rather than hedge.
- **Exchange/broker action.** Ad-hoc margin hikes and RMS auto square-off are external and uninsurable; only low utilization mitigates.
- **The paper-to-live gap.** Every figure above assumes mid fills that will not exist in the tail; assume live losses ≥ 1.3–1.5× paper.
- **Us.** The largest residual risk is overriding this memo mid-week. Hence pre-staged orders and a signature on this page before the week begins.

**Bottom line.** The events don't kill this book; naked gamma held through clustered events on the false premise of a single IV crush does. Triggers 1, 2, and 9 are the difference between a bad week and the worst week.

---

Sanity check: re-read the ask — pre-mortem voice (loss already happened, 12 months out), numeric tail, exact pre-commit triggers, and honest unhedgeables are all covered in one page; the scenario arithmetic (strangle point losses × lot 75 × 6 lots + spread max loss + slippage) reconciles with the table's NAV percentages.

result: One-page pre-mortem memo delivered — a Budget+RBI-week gap through naked NIFTY strangles drives a –5% to –22% NAV tail (20–40× weekly expected gain), with 10 pre-committed de-risk triggers and an explicit list of unhedgeable risks (overnight gaps, post-shock liquidity, halts, skew, paper-to-live slippage).