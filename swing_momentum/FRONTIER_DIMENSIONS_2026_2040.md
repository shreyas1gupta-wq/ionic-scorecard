# FRONTIER DIMENSIONS 2026–2040 — the god-tier expansion's frontier edge
Built 2026-06-17. EXTENDS `GOD_TIER_EXPANSION.md` (D1–D10) and rides the same Risk OS
(`OPERATING_STANDARD_2026.md`). Read AFTER PLAN.md + GOD_TIER_EXPANSION.md.

> **What this is:** the next-layer dimensions (D11+) found by adversarially generating
> 2024+ India-specific market-structure edges and scoring each /20 on
> Feasibility·Durability·Uncorrelation·Realness. Only ideas that scored **KEEP (≥14/20)**
> are dimensions here. The CUTs are documented (§5) — negative results are the point.
> These do NOT repeat D1–D10; they are venue/plumbing micro-mechanics those dimensions
> never touch. Every one is forward-capture research until live point-in-time data sizes it.

---

## 1. FRAMING — these are D11+, not a rehash
D1–D10 are fundamental/holding/factor edges (special-sits, microcap momentum, PEAD,
insider, ADR-NAV arb…). The frontier below is a different economic source: **order-flow
inside specific Indian venues and regulatory plumbing that did not exist or was not
exploitable before 2024–2026.** They sit furthest from the momentum core on the
correlation map (their P&L is mechanical friction, not direction/factor/vol), which is
exactly why they earn their place under the <0.3 cross-sleeve |rho| mandate.

Honest constraint that recurs everywhere: **the short leg is the binding constraint in
India** (F&O-only / SLB-only), and **tiny clean event samples (N<10)** make every
backtest overfit-prone. Treat all KEEPs as funded only after live validation.

---

## 2. THE KEEP LIST (D11+), grouped by lens

### LENS A — Borrow / lending plumbing (the strongest frontier source)

#### D11 — SLB borrow-fee-spike carry (+ optional squeeze overlay)  [16/20 — highest]
- **Thesis:** lend scarce names you already own into SLB fee spikes (event-hedging /
  arb-unwind / expiry demand) for pure capped-risk yield; optionally read the
  borrow-fee z-score + inventory-collapse signal to anticipate names where shorts are
  forced to cover into the monthly reverse leg.
- **Moat:** complexity + thin two-sided SLB books; large lenders (insurers/MFs) are sluggish.
- **Why small-capital:** SLB depth per name is tiny; a small inventory holder captures
  outsized fees; signal degrades if crowded; ≤₹10Cr sits below the depth ceiling.
- **Why uncorrelated:** lending-fee income is carry on owned inventory (faint underlying
  beta only); the squeeze overlay is borrow-market microstructure, orthogonal to equity beta/vol.
- **Access:** Kite (SLB lend/borrow segment) + NSE public SLB fee/inventory/OI feed.
- **Test:** scrape NSE SLB daily series (per-name fee, qty, open positions, reverse-leg
  dates). Carry leg: realized annualized lend yield net of charges vs fee-at-order.
  Signal leg: does fee z-score spike + inventory collapse predict positive return into
  reverse-leg date? Point-in-time SLB-eligible list (monthly churn).
- **Kill:** net lend yield < MMF alternative AND fee-spike has no forward predictability
  after costs (either leg can stand alone; both dead = kill).
- **Durability→2040:** SLB is India's only legal short-delivery channel and SEBI is
  expanding short-selling; sticky lendable supply keeps spikes structural. Compounds, not decays.

### LENS B — Corporate-action / demerger micro-mechanics

> CAUTION: D12 and D13 are the SAME family (demerger-stub dislocation) at two timetable
> points — they are positively correlated with each other, NOT independent. Run them as
> ONE demerger-microstructure budget, not two diversifiers.

#### D12 — Demerger phantom-stub gap (parent ex-value vs child listing lag)  [15/20]
- **Thesis:** on the record-date pre-open discovery session the parent is stripped of the
  demerged value immediately, but the child lists ~3–6 weeks later. Model implied stub
  value (scheme valuation, listed peers, prior first-print discounts) and position in the
  PARENT / listed peers ahead of the child's dislocated listing print (no F&O, no index, no
  passive demand day-1). Refs: ITC/ITC Hotels, Tata Motors CV/PV, HUL/Kwality, Raymond Realty.
- **Moat:** complexity; one-off stubs don't fit systematic universes, so quants skip them.
- **Why small-capital:** ₹20–200cr listing-day books; ≤₹10Cr fits without footprint;
  institutions move the print.
- **Why uncorrelated:** payoff keyed to scheme timetable (record date + lag), not beta —
  carries only residual small/mid-cap beta in the hold window.
- **Access:** Kite cash (parent + peers; child from listing day). No options.
- **Test:** survivorship-safe event table of all NSE/BSE demergers 2018–25 from exchange
  corporate-action archives (NOT a live screen). Capture parent pre-open adj %, swap ratio,
  days-to-listing, child first-print vs SOTP. Backtest parent drift, child open→close,
  parent-vs-peer pair; subtract STT + modeled first-day impact; exclude names that lacked
  the liquidity you'd have needed.
- **Kill:** across ≥20 demergers the child listing gap has no stable sign after costs, OR
  SEBI compresses listing lag to <5 trading days, OR T+0/instant child listing mandated.
- **Durability→2040:** conglomerate unbundling is structurally accelerating; listing lag is
  hard plumbing. RISK: sign is NOT stable (some stubs gap up, some down) and the clean
  sample is <10 — research-grade lead, not a proven edge.

#### D13 — Nifty demerger-stub forced-exclusion sell (post-Dec-2025 methodology)  [14/20, borderline]
- **Thesis:** NSE Indices (eff. 15-Dec-2025) RETAINS the demerged co. through the event then
  EXCLUDES the newly listed stub a fixed few sessions post-listing → a known-date,
  known-direction, price-insensitive passive SELL into a thin stub with no offsetting passive
  buy. Be the liquidity provider on the exclusion date at a quantified discount; harvest the
  5–20 session reversion as the overhang clears. (ITC Hotels precedent ≈ ₹1,500cr forced sell.)
- **Moat:** forced-flow; rules-bound price-insensitive seller.
- **Why small-capital:** sit on the bid through the exclusion print and reverse over weeks; a
  large LP becomes the marginal price and erases the edge.
- **Why uncorrelated:** index-rule mechanics on a fixed date for one name; reversion clusters
  on the calendar, not the market.
- **Access:** Kite cash; capped via sizing + hard stop below fair-value band.
- **Test:** catalog every Nifty/Sensex demerger-driven exclusion under the new rule + analog
  forced-exclusions (DVR removals, F&O exits, free-float reweights) as proxies. Event-study
  open/close + T+1..T+20 reversion; size forced volume = passive AUM × stub index weight vs ADV;
  validate the estimate against observed exclusion-day volume spikes.
- **Kill:** reversion absent/negative after costs, OR NSE phases exclusions gradually (smooths
  the impulse), OR exclusion-day volume shows institutions already pre-positioned (no residual).
- **Durability→2040:** passive AUM growth makes the impulse LARGER, but methodology is brand-new
  and explicitly mutable. RISK: the most TELEGRAPHED trade in the room (every event desk read the
  same note) and effectively N≈1 — keep small, monitored, hard reversion-absent kill.

### LENS C — Closing-auction venue (greenfield)

#### D14 — Closing Auction Session (CAS) equilibrium dislocation  [14/20, marginal — research-only]
- **Thesis:** from Aug-2026 NSE replaces the VWAP close with a single-price call auction
  (3:15–3:35pm) for F&O-eligible stocks, seeded by the 3:00–3:15 VWAP reference; SL/iceberg
  banned in-window. Passive/MOC imbalance dumps into a thin auction book → the clear deviates
  from reference and snaps back at the next open. Edge: pre-position in continuous trade against
  predicted imbalance and unwind into the print / T+1 open.
- **Moat:** new-modality; zero crowding on a day-one venue.
- **Why small-capital:** single-stock CAS books are shallow; a few lakh meaningfully captures
  the imbalance premium; a large fund moving the clear IS the edge's destruction.
- **Why uncorrelated:** auction-design friction, not direction/factor/vol. Caveat: imbalance days
  cluster on rebal/expiry dates → inherits some calendar overlap with the existing book's busy days.
- **Access:** Kite (cash + the new CAS window; F&O 3:30–3:40 extended session as hedge overlay).
- **Test:** CANNOT backtest pre-launch (no folklore — a virtue). From Aug-2026 build a paper
  harness capturing every F&O name's 3:00–3:15 reference, broadcast indicative/imbalance during
  3:15–3:35, the final clear, and the T+1 09:15 open. Measure (a) clear−reference vs imbalance,
  (b) overnight reversion clear→open. Forward-only walk-forward; trade only after ≥40 stable sessions.
- **Kill:** after 60 sessions no monotonic imbalance→dislocation relationship (efficient auction),
  OR median reversion < round-trip cost (~6–8 bps), OR exchange adds collars capping dislocation.
- **Durability→2040:** call-auction closes are permanent global structure; single-stock imbalance
  friction persists while passive AUM grows. RISK: day-one dislocations are fattest and compress
  fast; collars are likely → fund only after live data; the "supply liquidity inside the auction"
  framing oversells control you won't have (you're a price-taker at the single clear).

---

## 3. HIGH-CONVICTION TOP 6 (build order)
Only 4 frontier ideas survived; the shortlist is therefore ranked across the frontier KEEPs
PLUS the two best existing-book neighbors they should be built alongside for shared plumbing:
1. **D11 — SLB fee-spike carry** (16) — the one genuinely fundable, capped-risk, Kite-native
   edge. Carry leg first (low effort, immediate), squeeze overlay as optional research.
2. **D12 — Demerger phantom-stub gap** (15) — best datable micro-mechanic; build the
   exchange-archive event table first (also feeds D13).
3. **D13 — Forced-exclusion sell** (14) — shares D12's data; deploy as a small monitored
   position, NOT a second independent bet (correlated with D12).
4. **D14 — CAS dislocation** (14) — cheap optionality: stand up the paper-capture harness on
   day one (Aug-2026), spend zero capital until ≥40 sessions confirm.
5. **D1 special-situations** (existing) — the natural fundamental parent of D12/D13; shared
   corporate-action calendar.
6. **D9 insider/smart-money** (existing) — shares the SLB/short-interest plumbing with D11.

---

## 4. SPECULATIVE / WATCH (2030s) — new-venue optionality
- **D14 CAS** lives here until live data graduates it (currently funded as research only).
- New single-stock & longer-dated options + new indices → more imbalance surfaces for
  CAS-style and forced-flow edges.
- GIFT-City / 24×7 / tokenized & perpetual venues → fresh day-one order-flow surfaces; build
  the data pipe now, deploy nothing until a venue is live and uncrowded.
- AI-herding forced cascades (extends H1/H2) — model the crowd's mechanical moves around the
  new auctions as everyone runs similar imbalance models.

---

## 5. BRUTAL HONESTY — what was CUT and why (negative results)
| Idea | /20 | Fatal flaw |
|---|---|---|
| **T+0 / T+1 dual-settlement basis arb** | 11 | The hedge leg doesn't exist for retail: shorting the rich T+1 leg needs SLB borrow, brokers don't net the two cycles, and ~10–20bps round-trip cost swamps a sub-10bps basis. Folklore "two prices = arb" trap. |
| **Circuit-limit reopening snap-back** | 10 | Negative-skew falling-knife: "capped downside" is FALSE (next circuit can gap/halt to zero); LC locks cluster in market crashes → hidden crash-beta; UC short needs unavailable borrow; fraud/halt-to-zero tail dominates. |
| **Pre-open POS indicative-fade** | 10 | Right mechanism, wrong operator: your fill IS the open; you can't transact against the gamed indicative after 9:08; co-located HFT arbitrages single-stock opens vs GIFT Nifty in microseconds — retail is structurally last. |
| **Tick/odd-lot illiquid-book queue capture** | 9 | The adverse-selection market-making mirage: no maker rebate or latency edge in Indian cash equity; your fills are picked off by informed flow; inventory blows out in stress (crash-beta). |
| **SGB discount→redemption convergence** | 13 | Most genuinely REAL payoff here (sovereign-guaranteed), but a melting ice cube: scheme discontinued (no new tranches since FY24, runoff to ~2032), and books so thin (lakhs/day) that a ≤₹10Cr operator IS the market. Capacity ≈ a personal-account curiosity. |
| **CIRP resulting-entity acquisition right** | 13 | Real legal mechanic, but the pre-knowable, deep-discount, listing-retained subset is a handful of anecdotes — a convex lottery, not a repeatable edge; plan terms usually unknowable pre-NCLT. |
| **SME→mainboard migration front-run** | n/a | Review truncated before a final score; preliminarily weak — SME-segment returns are heavily beta/sentiment-driven (not the claimed orthogonality), the access-gate window compresses as data propagates, and exit liquidity into "expanded liquidity" is often illusory. Not promoted. |
| **Buyback deemed-loss harvesting; Rights-entitlement lapse / partly-paid pair** | unscored | Candidate JSON arrived truncated; not adversarially scored, so NOT promoted. Re-supply full text to score. (Buyback idea is account-level tax optimization, not a market edge; rights-RE is a real terminal-day forced-seller mechanic worth a future pass.) |

**Cross-cutting skeptic flags:** (a) D12 & D13 are one correlated demerger exposure, not two
bets. (b) Every frontier idea leans on N<10 clean samples — overfit-prone; live point-in-time
capture before sizing. (c) The recurring killer across CUTs is the missing/uneconomic SHORT
LEG and hidden CRASH-BETA masquerading as "uncorrelated, capped-risk."

---

## 6. HOW THESE COMPOSE WITH THE BOOK (under the Risk OS)
- **Correlation map:** D11 carry is orthogonal to everything (plumbing income). D12/D13/D14 are
  event/auction friction — orthogonal to the momentum core, short-vol, and pairs. The watch-items
  are the lowest-beta of all. This pulls the **target avg cross-sleeve |rho| toward <0.3**, but
  ONLY if D12+D13 are budgeted as ONE sleeve and D14's calendar overlap (rebal/expiry clustering)
  is risk-netted against the existing book's busy days.
- **Role:** D11 carry = a steady diversifying yield on inventory the momentum/microcap sleeves
  already hold (synergy, not new capital). D12–D14 = lumpy, calendar-clustered event diversifiers
  that fire when momentum may be quiet.
- **Wrapped by the Risk OS:** each sleeve gets defined/capped downside (hard stop below a
  fair-value band; D14 caps at premium/sizing), a survivorship-free archive backtest, a capacity
  cap (≤₹10Cr — D11 and the SGB-class ideas prove capacity is the binding moat), and a live
  edge-decay monitor with the kill-criteria above wired as automated triggers. Frontier sleeves
  stay RESEARCH-funded until live data clears their kill bar; none can ruin the book.

---
RESULT: KEEP = 4 (D11 SLB fee-spike carry, D12 demerger phantom-stub gap, D13 forced-exclusion
sell, D14 CAS dislocation). CUT = 7 (T+0/T+1 basis arb, circuit reopening snap-back, pre-open POS
fade, tick/odd-lot queue capture, SGB convergence, CIRP acquisition right, SME-migration front-run).
