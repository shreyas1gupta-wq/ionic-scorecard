# Five Falsifiable Alpha Hypotheses — Indian Equity & Index Derivatives
**CIO consolidated verdict (Rajan Mehta, E-001).** Integrates A. Rao's draft (Head of Quant) and N. Bose's red-team (E-014). Tags: [DATA] / [INFERENCE] / [OPINION].

---

## Framing rulings (bind all five before any full backtest)

1. **Premium vs. alpha is stated honestly per idea.** [OPINION] Two of these (VRP, session-return split) are *risk premia* in their static form — you are paid to bear a risk others shed, so "who loses" is "no one; you rent risk cheaply." That is a real, harvestable P&L source but it is **beta, not alpha**, and it carries the fat left tail. The alpha claim lives ONLY in the *conditional/timing overlay*. Each idea below marks where the premium ends and the alpha claim begins. I will not let a static premium be memo'd as alpha (IC-1 precedent: register incremental edge, not headline).

2. **The draft's "diversified failure modes" claim is struck.** [INFERENCE] Costs/executability is a *shared* assassin across #2, #4, and #5-if-illiquid — a majority, not an outlier. The counterparties differ; the failure modes largely do not. We do NOT get tail-diversification from running these five. Front-load the cost/executability gate on #2, #4, #5 *before* the signal work — if a candidate can't clear 2× COST_STANDARDS-stressed costs on a real vehicle, kill it before building the signal.

3. **"No parameters" is struck** except for #4. #1 (event windows, +20d reversal), #2 (5-day look-back/forward), #3 (80th-pctile, 30-day horizon), #5 (surprise definition, decile cut) all embed researcher degrees of freedom. Every threshold enters the honest trials count and the DSR penalty. Pre-register thresholds before looking at returns.

4. **Certification bar is regime-appropriate, not one-size.** The blanket "≥30 trades/parameter × 5 regime slices, DSR>0.95, PBO<25%" is *infeasible* for low-n event studies (#1) and *inflated by overlapping windows* for #3. Rulings: pool universes to lift n; **cluster standard errors on the true independent unit** (rebalance date, not name; non-overlapping blocks, not daily); state an honestly-derived lower bar for genuine low-n events rather than quoting a bar we cannot meet. A placebo (random-date / label-shuffle) is mandatory **at the screen stage**, not deferred to cert.

5. **Standing discipline (all five):** PIT `available_date` only, P&L booked in the EXIT period, stable denominators, 2× cost stress, ADV participation cap, one-day-lag lookahead test. All data is free from NSE archives / India VIX history / the firm's PIT earnings parquet — with two acknowledged exceptions flagged below (#1 announcement-date archive, #5 surprise proxy).

---

## 1. Index-reconstitution demand shock — *structural forced flow* (RESIZE: keep as research, not as the draft framed it)

- **Mechanism / who loses:** [INFERENCE] On NIFTY 50 / Next 50 adds, index and ETF trackers are forced to buy near the effective-date close, price-inelastic; deletions mirror. The forced passive flow is the loser. Discretionary front-runners buy the announcement and unwind into effective-date demand. **Magnitude prior:** Indian passive AUM tracking NIFTY is far smaller than DM, so the premium is proportionally smaller and, per DM evidence, likely decaying — run a crowding-check before conviction.
- **Cheapest kill test:** Event study, equal-weight, pooled **NIFTY50 + Next50 + MidCap150** adds/deletes to lift n. Cumulative abnormal return announcement→effective, and effective→+20d (post-inclusion reversal). **Cluster SEs on the rebalance date, not the name** (all names in a cycle share one effective date → the independent n is ~distinct rebalance dates, not name count — pseudo-replication kills naive t-stats). Add a **random-non-event-date placebo**: if random dates show similar "abnormal" return, the benchmark model is broken.
- **Data:** NSE index-maintenance press releases (change list + effective + **announcement** dates) + daily bhavcopy. **Caveat that voids the "all free" claim:** a PIT-clean *announcement-date* archive (esp. pre-2018) requires scraping old releases; an error here is direct lookahead. This is the least-clean data claim in the set — verify the archive before trusting any announcement→effective window.
- **What kills it:** No significant announcement→effective abnormal return net of 2× costs after date-clustering; OR the whole move is realized as an announcement-day jump (unarbitrageable by a small team); OR no post-effective reversal (the flow-pressure story fails); OR the placebo shows comparable "abnormal" returns.
- **Weakest link:** capturability *after* public announcement, plus small/decaying Indian passive AUM. If the move is all in the announcement gap, it's a chart, not a trade.

## 2. F&O security-in-ban crowding reversal — *positioning* (RESIZE: phenomenon-only test; executability is the real kill)

- **Mechanism / who loses:** [INFERENCE] A stock enters the F&O ban when market-wide OI breaches 95% of the limit — a hard, public marker of one-sided leveraged crowding. Crowded leveraged retail (long if price↑ + OI↑ into the ban) is the loser; forced unwinds + no-new-entry supply drive a subsequent reversal.
- **The correct assassin (draft named the wrong one):** [INFERENCE, VERIFY vs NSE F&O regs] During the ban, **NO fresh F&O positions** are permitted — only reduction of existing. So "short the crowded-long name on ban-entry day" *cannot be entered in F&O in the very window the signal fires.* Cash-market short for retail is intraday-only (can't hold 5 days); SLB is thin/expensive precisely for these speculative mid-caps. The downward-reversal leg is near-unexecutable for a small team; only the crowded-short→long-reversal leg (cash delivery) is tradeable. The edge is **asymmetric**, and a fixed 5-day forward window straddles the ban's own variable exit — incoherent with "enter on ban-entry."
- **Cheapest test — demoted to PHENOMENON CONFIRMATION only:** On ban-entry days, condition forward 5-day return on **both prior-return sign AND ΔOI** (draft dropped ΔOI, which is in the bhavcopy — use it, or you're testing a weaker proxy than your own mechanism). Add an OI-sign / label shuffle placebo.
- **The ACTUAL kill (separate executability gate):** demonstrate a vehicle (SLB or cash) that can hold the crowded-long short for the required horizon at a cost that leaves net edge. If no such vehicle exists, the trade is **dead regardless of a real phenomenon.**
- **Data:** NSE "Securities in ban period" list + bhavcopy (price + OI). Free.
- **What kills it:** No forward reversal conditioned on entry direction + ΔOI; OR reversal < round-trip cost at 2× stress; OR no holdable vehicle for the tradeable leg. Any one = dead.

## 3. VIX-conditioned variance risk premium — *index derivatives* (APPROVE static premium as beta; alpha claim = the timing overlay only)

- **Mechanism / who loses:** Structural buyers of index optionality (insurers, hedgers) overpay for protection, so implied variance sits above subsequent realized. The chronic insurance buyer is the loser. **Category ruling:** static IV−RV positivity is one of the most robust facts in finance — but it is **compensation for bearing crash risk (premium/beta), not alpha.** The alpha claim rests entirely on the *conditional* overlay (harvest more after a VIX spike).
- **Cheapest kill test — and the two traps that must be fixed AT THE SCREEN:**
  - Compute IV−RV_fwd (India VIX today − realized 30d fwd Nifty vol). **Overlapping-window trap:** 30d-fwd computed daily gives ~30-day-autocorrelated observations; naive significance is wildly overstated. **Mandatory at the screen stage: non-overlapping windows or block bootstrap** (the draft deferred bootstrap to cert — pull it forward to here).
  - **Convention trap:** India VIX is annualized risk-neutral IV; the realized leg MUST match (annualization, 252 vs 365, close-to-close estimator). VRP is conventionally *variance* (IV²−RV²). Decide the convention *before* looking — a mismatch manufactures a spread of either sign.
  - Then the overlay: is the spread larger following VIX > 80th pctile than unconditionally? **The 80th pctile is itself a tuned parameter** (why not 75/90) — pre-register or grid-and-penalize.
- **Conditional confound to disclose:** after a spike, VIX mean-reverts down AND realized often collapses, so IV−RV_fwd is *mechanically* large post-spike — that's a vol-mean-reversion trade with the **fattest left tail (the next gap)**, not a cleaner premium. Size to the crash path, not the average.
- **Data:** India VIX daily + Nifty daily closes. Free.
- **What kills it:** IV−RV not significantly positive on **non-overlapping** data (kills the whole idea); OR post-spike conditional spread not larger than unconditional (kills only the *timing/alpha* overlay — static short-vol beta may survive but is registered as premium, not alpha).
- **Tail-risk note (CIO):** a positive spot spread is necessary, not sufficient. Any book here books P&L in the exit period and is stress-replayed on Mar-2020 before a single rupee of size.

## 4. Overnight vs. intraday session return split — *session risk premium* (APPROVE as premium; "who loses" corrected)

- **Mechanism / who loses — CORRECTED:** [INFERENCE] For Nifty and large caps most drift accrues close-to-open (overnight, when global risk-premium and news accrue); open-to-close is flat-to-negative. **The draft's "day-traders are the losing side" is wrong — this is not a wealth transfer.** The overnight leg is *compensation for bearing gap/overnight risk.* Honest answer to "who loses": no one is exploited; you are paid to hold risk intraday traders shed. **So static long-overnight is leveraged beta, NOT alpha.** The alpha claim exists only if a conditional/timing overlay beats static bearing.
- **Cheapest kill test:** Decompose Nifty daily return into overnight (prev-close→open) and intraday (open→close) over 10+ yrs; compare cumulative return and Sharpe. **Genuine strength: this decomposition is parameter-free** — the one idea in the set that is.
- **Execution mirage (the real killer):** there is **no instrument that trades at the index print.** You'd hold NIFTY futures or NIFTYBEES — each adds basis/dividend/expense drift, its own open-auction print, and a wide close spread. "MTM at official open" ≠ fillable. ~252 round-trips/yr at the two widest-spread moments + STT/turnover drag is what kills it, not the raw spread. **Landmine:** the "open" must be the real first traded level ≥09:15, never the 09:00 pre-open-auction print.
- **Data:** Nifty daily OHLC + the actual vehicle's (futures/ETF) auction-executable prints. Free.
- **What kills it:** Overnight-minus-intraday Sharpe not materially positive; OR it does not survive on the *actual vehicle* at auction-executable prices net of STT and daily round-trip cost. If only the static leg survives, it is registered as a premium, not alpha.

## 5. PEAD with a liquidity kill-switch — *earnings underreaction cross-section* (APPROVE design; two undisclosed leaks to close)

- **Mechanism / who loses:** [INFERENCE] Post-earnings-announcement drift — large positive surprises keep drifting for weeks because the marginal investor under-reacts/anchors. The slow-updating investor is the loser. Firm scar tissue: our prior "PEAD edge" was illiquidity contamination, so falsification is baked into the design.
- **Cheapest kill test (this IS the kill):** Run the long-short PEAD portfolio restricted to **top-decile ADV** names. If drift exists in the full universe but vanishes in the most-liquid subset, it is not *harvestable*.
- **Two leaks the draft's discipline didn't name — close them:**
  - **Surprise-definition confound:** a seasonal-random-walk SUE conflates *growth* with *surprise* (high-growth names "beat" YoY every quarter), so an SRW-SUE long-short can silently collapse into a **price/earnings-momentum factor.** Momentum-neutralize before crediting any drift to underreaction — this also protects the "materially different from the others" claim.
  - **Imputed-date lookahead:** `available_date` is exact for 86.2%; the imputed **13.8%** can stamp availability *earlier* than the true public date = trading on pre-release earnings. **Run the kill test on the exact-date subset only.**
  - Add a **cross-sectional SUE-label shuffle placebo** → drift must go to zero.
- **Interpretation ruling:** "vanishes in top-ADV ⇒ microstructure noise" is an overreach. Large caps are most-covered/most-efficient, so PEAD is weakest there *by construction.* A liquid-only null means **"not harvestable," not "not real."** For a trading firm, uncapturable = dead — operationally fine — but we do NOT mislabel a genuine small-cap underreaction as noise in the memo.
- **Data:** PIT earnings `available_date` (firm holds the parquet) + bhavcopy for price/ADV. Surprise via analyst estimate if available, else a pre-registered SUE proxy. Free/held.
- **What kills it:** Liquid-only, momentum-neutralized, exact-date-only decile spread not significantly positive net of 2× costs; OR drift concentrated in bottom-ADV; OR placebo not ≈0. Any one = the edge was illiquidity or a momentum re-label, not underreaction.

---

## Honest scorecard (CIO)

- **Distinct alpha mechanisms:** closer to **3, not 5.** #3 and #4 are risk *premia* whose alpha lives only in a fragile conditional overlay; #1's *tradeable* leg (post-effective reversal) and #2 are both "mean-reversion after forced/crowded flow" sharing the mid-cap-cost assassin. Genuinely distinct *alpha* stories: underreaction (#5), and the two conditional overlays (#3 timing, #4 timing) if they survive. This is disclosed, not hidden.
- **Shared assassin:** costs/executability, across #2, #4, #5-if-illiquid. No tail-diversification is claimed.
- **Sequencing [OPINION]:** run #3 and #4 first — cheapest to falsify (index closes + VIX, hours of work), *with* the overlapping-window/convention fixes at the screen. Then #1 (needs the announcement-date archive verified first). Front-load the executability gate on #2 and the cost model on #5 before any signal build.

**VERDICT: APPROVE the research plan for pipeline intake (Gate-1)** conditional on: (a) #2 reframed as phenomenon-test + separate executability kill; (b) #1 date-clustered with a lowered, honestly-derived low-n bar; (c) the "diversified failure modes" and "no parameters" claims dropped; (d) #3/#4 static legs registered as *premia*, alpha only in the overlays; (e) placebo battery + non-overlapping bootstrap instantiated at the SCREEN stage per idea. No result quoted downstream until the two VERIFY items (NSE ban mechanics, announcement-date archive) are file-confirmed.
