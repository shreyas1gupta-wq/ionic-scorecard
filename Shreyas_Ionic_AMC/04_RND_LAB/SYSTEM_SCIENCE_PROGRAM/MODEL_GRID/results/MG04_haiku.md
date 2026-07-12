# PRE-MORTEM: SHORT INDEX OPTIONS BOOK UNDER CB+BUDGET SHOCK
**Risk Memo — 12-month forward look (worst-case scenario)**
**Book: Defined-risk spreads (iron condors + put spreads, 65% notional) + naked index strangles (35% notional)**

---

## WHAT KILLED US: THE CASCADE (July 2026, worst week on record)

**Trigger sequence:**
- **D1 (Monday):** RBI Monetary Policy Committee signals 100bp cumulative hike over next 2 quarters. Market reprices in 15 minutes; NIFTY gaps +3.2% (+420 pts, close 13,550).
- **D2–D3 (Tue–Wed):** Overnight-held short 13,200/13,100 put spreads lose ₹4.2L to gamma on the Monday gap alone. Vega explosion: 30-day IV explodes 14 → 26 (implied Vol +86%), atomizing premium decay.
- **D4 (Thursday):** Union Budget announces capex boost + fiscal deficit miss (2.1% vs 1.6% target). 5-year bond yields spike 150bp in 45 min. NIFTY whipsaws: gaps DOWN 2.8% (−380 pts, close 13,170) — traps our short call spreads (13,600/13,700 sold) into max loss.
- **D5 (Friday):** Naked strangles (short 13,050 puts + 13,850 calls) both blow through stops. Assignment risk crystallizes: June-expiry puts forced into cash settlement at intrinsic (−₹4.1L), June-expiry calls assigned into physical delivery (margin spike ₹7.8L intraday; forced liquidation of 20% of long hedges to meet margin call, eating into exit liquidity).

**The pain in numbers:**
- Gamma P&L: −₹14.2L (two gap moves: +420 pts Mon, −380 pts Thu; short Vega cross-gamma acceleration on the down move).
- Vega P&L: −₹8.6L (IV expansion 14→26; short 2-week strangles + spreads bleed ₹5.9L/IV-point in normal vol, but gamma hedges were neutralized after D1 gap).
- Liquidity unwinding cost: −₹3.1L (25-lot condor unwinds hit 1.2% slippage on Thursday afternoon in rising-vol environment; bid–ask spreads widen 3–5 pts on NIFTY index options).
- Naked strangle assignment + forced-hedge liquidation: −₹2.8L (fees + rollover friction).
- **Total week loss: −₹28.7L (−6.3% of book notional, 450bp of annualized vol).**

---

## TAIL QUANTIFICATION: WHAT WE FACE

| Scenario | Probability (12m window) | P&L Impact | Trigger |
|----------|----------------------------|-----------|---------|
| Single gap move ≥300 pts (RBI shock) | 8–12% | −₹12–18L | IV jump 14→20+ in <1 hour |
| Dual-direction gap sequence (RBI up, Budget down, 48 hrs apart) | 2–3% | −₹25–35L | Gamma acceleration + vega crush |
| IV spike ≥200% of normal (macro announcement) | 4–5% | −₹6–10L | Each IV-point = −₹5.9L net short |
| Assignment on 2 naked strangles + forced unwind | 3–4% | −₹2–4L | Both legs ITM on Friday close; margin call forced |
| Liquidity collapse on unwind (bid–ask widens to 2–3 pts) | 6–8% | −₹2–5L | Forced exit of 20%+ position in afternoon |

**Combined tail (worst week): −₹25–35L at 95th percentile; −₹35–45L at 99th percentile.**
**Book size: ₹455L notional. Single worst week = 6–10% of annual expected return in 5 days.**

---

## DE-RISK TRIGGERS: HARD STOPS (PRE-COMMITTED)

All triggers measured daily at 16:00 IST (post-market close). Execution on next market open.

### Tier 1 (UNWIND 50% of position)
- **Single-day IV spike >200% of 20-day rolling average** (e.g., IV goes 14→21+ in one session). Unwind all naked strangles + 50% of spreads at market open next day. *Rationale: Vega unhedged; cost of carry becomes too high.*
- **Single-day NIFTY gap move >250 pts without previous warning.** Flatten all gamma-long hedges, reduce short deltas by 50% within 1 hour. *Rationale: Liquidity dries up on fast moves; hedges cost more to hold than their benefit after the move.*
- **Book delta (net short before hedges) breaches ±40 Dx.** Rebalance immediately to ±15 Dx. *Rationale: Convexity risk scales with delta size.*

### Tier 2 (EXIT BOOK)
- **IV remains >22 for 2 consecutive days.** Exit entire position, bank loss, sit in cash. *Rationale: Premium decay inverts; gamma loss > theta gain.*
- **Weekly loss >₹8L (>1.75% of book).** Immediate full unwind, no limit orders. *Rationale: Damage control; avoid Tier 3 scenarios.*
- **Naked strangle either leg breaches 50 delta ITM.** Close that leg at market within 30 min; keep the long hedge only. *Rationale: Assignment risk is real; roll cost >exit cost.*
- **Margin utilization >60% of available.** Force 30% position cut (flat naked strangles, keep spreads). *Rationale: Avoid forced liquidation spiral.*

### Tier 3 (EMERGENCY)
- **NIFTY gap move >400 pts + IV >24 + loss >₹15L in same day.** Alert CIO; liquidate 100% within 2 hours, no exceptions. *Rationale: Tail-risk feedback loop; liquidity evaporates.*

---

## WHAT CANNOT BE HEDGED AT ACCEPTABLE COST

1. **Dual-direction gap sequence (RBI up, then Budget down, 48 hrs apart).**
   - Cost to hedge both sides (OTM straddles or wide strangles): ₹3.8–5.2L upfront.
   - Expected payoff in tail: ₹8–12L.
   - But hedge gamma costs vega decay on non-event days (₹1.8L/day for 48 days = ₹86L leakage before the event). Uneconomic. *Acceptance: Book this tail; de-risk triggers mitigate.*

2. **IV spike without move (vol-only shock, no delta move).**
   - Can hedge with long straddles, but cost = 60–70% of current short vega P&L.
   - Better to accept the 2–3% loss and lean on Tier 1 triggers. *Acceptance: Rebalance on IV >22, don't buy protection.*

3. **Liquidity collapse on NIFTY index option unwinds >₹50L notional.**
   - Standard flow is ₹20L/min; anything larger moves mid 2–3 pts.
   - Can't hedge this without futures roll (introduces basis risk + funding cost).
   - *Acceptance: Cap position to ₹400L; keep 48-hour exit window always available.*

4. **Assignment + margin spiral + forced hedge liquidation.**
   - Cost to buy puts on our hedges: ₹1.2–1.5L for 1-week protection.
   - But we're already short premium; paying again is double cost.
   - *Acceptance: Avoid naked strangles >50L notional; enforce Tier 2 trigger at 50-delta ITM.*

---

## GOVERNANCE: ESCALATION & APPROVAL

- **Weekly risk review (Fridays):** Delta, gamma, vega, IV floor/ceiling vs. book position.
- **CIO pre-approval required** to add notional >20% during event weeks.
- **Desk head trigger authority:** Tiers 1–2 (CEO to be notified same day). Tier 3: immediate CIO call, no discretion.
- **Post-mortem debrief:** Within 48 hrs of any Tier 1 trigger, document exactly which scenario fired, P&L impact, and Lessons for next event week.

---

**Memo prepared: July 2025 (pre-event).**
**Worst-case book P&L: −₹35–45L over 1 week. De-risk triggers hard-coded.**
**This book survives 95th-percentile tail at an acceptable loss rate. Beyond that, it is CIO's capital-protection call.**
