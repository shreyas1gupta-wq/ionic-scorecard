# TECHNO-FUNDA PATTERNS — technical + fundamental as ONE process, not two silos

**Owner:** Dhruv Kapoor (Head of Technical, E-005). **Date:** 2026-07-18. **Mandate:** Principal, 2026-07-18,
techno-funda methodology thread (sibling to `FUND_MANAGER_PLAYBOOKS.md`, R2 owner Arjun Rao).
**Status:** methodology research only — NO stock picks, NO capital sizing, NO backtest run in this pass (two
concrete cheap-test candidates are proposed at the end for Quant/R&D to run).
**Cross-referenced:** `ALPHA_RANKER/rnd/scorecard/SCORECARD_FINAL_SUMMARY.md` + `S1_RELATIVE_1M_REPORT.md` (read
in full), `ALPHA_RANKER/rnd/wave4/REGIME_SPEC_V2.md` (read in full), this folder's `FUND_MANAGER_PLAYBOOKS.md`
(read in full), `Shreyas_Ionic_AMC/03_RESEARCH_DESK/ANALYST_CHECKLISTS.md` §Minervini, `07_RISK_OFFICE/RISK_LIMITS.md`.

Tags: **[DATA]** = read off a firm file/dataset, verified. **[INFERENCE]** = derived by combining sourced facts.
**[OPINION]** = my professional judgment as Head of Technical, not yet tested on this firm's data.

---

## 0. The core techno-funda claim, stated once

Fundamentals answer **"what to own."** Technicals answer **"when to own it."** A great business bought in Stage
4 is not a good trade; a mediocre business timed off a clean VCP breakout in Stage 2 can still lose money if the
business deteriorates under it. **The two are sequential filters on the SAME idea, not competing theses:**
fundamentals build the watchlist (quality/value/growth screens — Agrawal's QGLP, Smith's ROCE floor, ALPHA_RANKER's
7-leg relative scorecard), technicals decide the entry/exit date and the risk. Neither substitutes for the other.
This is the operating principle every section below cashes out into specifics for.

---

## 1. Minervini/Weinstein stage analysis as the base technical framework

**[OPINION/DATA — standard technical-analysis doctrine, Weinstein 1988 / Minervini 2013, cross-checked against
this firm's own `ANALYST_CHECKLISTS.md` §Minervini]**

Four stages, one 200-day-MA-centric state machine:

- **Stage 1 (basing/accumulation):** price chops sideways, 200MA flattening after a decline, volume dries up.
  No edge in buying here — the market hasn't decided direction. This is where a fundamentally-screened name
  SITS on the watchlist while its business improves quietly, invisible in the price.
- **Stage 2 (advancing/markup) — the ONLY stage for new buys:** close > 150MA > 200MA, 200MA rising, 50MA >
  150MA > 200MA, price ≥30% above the 52w low and within 25% of the 52w high, RS percentile ≥70 — this is
  literally the firm's own trend-template criteria (`ANALYST_CHECKLISTS.md` §Minervini, all 8 criteria, no
  partial passes). Every criterion must hold simultaneously; a name failing even one (e.g., close>150MA but
  50MA still below 150MA) is NOT in a confirmed Stage 2 — it is transitioning and gets no entry.
- **Stage 3 (topping/distribution):** price churns at highs, volume rises without further price progress,
  50MA starts to roll over. This is the "sell into strength" zone (§6) — the stage where a Stage-2 winner
  should be trimmed, not where a fresh position is opened.
- **Stage 4 (declining/markdown):** 200MA falling, close below all major MAs, RS percentile collapsing. Full
  exit / avoid zone regardless of how cheap the fundamentals look — this is precisely the trap the mandate
  names: **a fundamentally great business in Stage 4 is a value trap until the stage turns**, because a
  deteriorating tape usually means the market is pricing information (weakening demand, competitive share
  loss, credit stress) the trailing fundamentals haven't shown yet.

**How this maps onto a fundamentally-selected name — the actual workflow:**
1. Fundamental screen (analyst desk / ALPHA_RANKER relative scorecard) produces the WATCHLIST — names that
   pass on quality/value/growth grounds.
2. Technical desk stage-classifies every watchlist name BEFORE any timing call (charter requirement).
3. **Buy only Stage 2 names off the watchlist.** Stage 1 names go on a "wait for confirmation" queue (watch
   for the trend-template to complete). Stage 3/4 names on the watchlist are explicitly NOT bought no matter
   how attractive the fundamental score — they are held for monitoring only, re-approached if/when they
   re-enter Stage 1→2.
4. Existing Stage-2 holdings get "sell into strength" discipline as they show Stage-3 characteristics (§6),
   and forced exits on confirmed Stage-4 transition regardless of the fundamental thesis (§6, the technical
   stop-loss candidate).

This is the single cleanest technical/fundamental division of labor: fundamentals never override the stage,
and the stage never substitutes for a fundamental screen (a Stage-2 chart with a broken/fraudulent balance
sheet is not a buy either — the forensic gate in `ANALYST_CHECKLISTS.md` §Fundamental-forensic runs first).

---

## 2. VCP (volatility contraction pattern) as the low-risk entry trigger

**[OPINION — Minervini's proprietary framing of a much older "coiled spring" pattern, my professional read]**

**Mechanism:** as a stock bases (Stage 1 → Stage 2 transition), each successive pullback within the base should
be SHALLOWER than the last (e.g., a 25% pullback, then 15%, then 8%) AND occur on PROGRESSIVELY LOWER volume.
The logic: sellers who wanted out have been shaken out in earlier, deeper pullbacks; each subsequent dip attracts
fewer sellers because the remaining holders are more committed (or institutions have already accumulated a
position and are defending it). Supply is drying up. This is a **necessary, not sufficient**, precursor to a
breakout — the pattern describes decreasing SELLING pressure, not confirmed BUYING pressure; that confirmation
comes only from the breakout bar itself.

**Volume confirmation is the trigger, not the base shape alone:** a VCP without a volume surge on the breakout
day is not a validated signal — it is a chart pattern that MIGHT be real accumulation or might just be a stock
nobody is trading. The firm's own trend-template criterion 9 states this explicitly: "volume contracting through
the base, expanding on breakout." Concretely: breakout-day volume should be materially above the base's average
daily volume (a common operational threshold is ≥1.5–2× the 50-day average volume) with the price closing in the
upper half of the day's range, ideally clearing the base's pivot high. Absent that volume surge, treat the
"breakout" as a false start (a common trap — a low-volume poke above the pivot that fails within days) and do
not size into it.

**Pivot + stop mechanics (per this firm's memo format):** the pivot is the base's highest point (the level that,
once cleared on volume, confirms the breakout). The stop sits just below the base's most recent, tightest
contraction low — NOT the base's absolute low (that stop is too wide and defeats the point of waiting for a
tight VCP). Risk-per-share = pivot-adjacent entry − stop. Position size = (RISK_LIMITS max risk per position,
currently 1.0% of book equity per `07_RISK_OFFICE/RISK_LIMITS.md`) ÷ risk-per-share. A wide, sloppy base with no
real contraction forces either an oversized stop (breaching the risk limit at any sane position size) or an
undersized position (not worth the slot) — this is the actual risk-discipline value of demanding a genuine VCP
over any old-fashioned "breakout of a round number."

---

## 3. Earnings-driven technical setups — and the actionable question on `earn_1M`

**[DATA]** First, a load-bearing correction to the mandate's framing. I read `S1_RELATIVE_1M_REPORT.md` and the
build script lineage (`w6fg2_build.py`) closely: **`earn_1M` / `earnings_confirm_v2` is NOT a price-reaction or
market-surprise signal at all.** It is a purely fundamental, backward-looking flag — it fires (=1) only when
THREE PIT accounting conditions all hold simultaneously across multiple fiscal years: operating-growth
persistence, margin holding, and CWIP converting into assets (not stuck in perpetual capitalized construction).
It fires on ~5.9% of rows (8,509/143,907) precisely because demanding all three conditions, multi-year, is a
strict AND-gate. There is no "earnings surprise vs consensus," no gap, no volume, no price data anywhere in its
construction. The scorecard's own §2.1 blueprint language ("momentum + earnings-surprise carry the weight") is
therefore a naming/framing mismatch, not a build defect — worth flagging to Arjun Rao directly since it means
the S7 summary's "earnings leg" language is potentially misread by anyone who assumes it's a SUE/PEAD-style signal.

**Second, a hard prior-art constraint on the "add technical confirmation" idea.** `REGIME_SPEC_V2.md` layer G
already tested the PURE price-drift-after-earnings trade (PEAD) on this firm's data and killed it
unconditionally: IC ≈ −0.003 full-sample, dead in every regime with adequate n (CHOPPY IC −0.003 n=655; OTHER
IC −0.006 n=1966). **A naive "buyable gap-up" signal — buy stocks that gapped up on earnings and are drifting
higher — is mechanistically the same bet as PEAD, and PEAD is already a certified kill on this exact universe.**
Any proposal that amounts to "re-discover PEAD wearing a Minervini costume" should be rejected on prior art
alone, not re-tested from scratch.

**So the genuinely actionable question is narrower than "does volume confirm earnings":** does a
CONTEMPORANEOUS volume/price-action check, applied AS A FILTER on the existing fundamental `earnings_confirm_v2`
flag (not as an independent drift-capture bet), reduce the flag's inertness? My reasoning for why this is a
different claim from dead-PEAD:

- `earnings_confirm_v2` is inert (contributes ~zero incremental IC, drop-one makes IC/Sharpe marginally
  *higher*) not because the underlying economic idea (confirmed multi-year fundamental improvement should carry
  forward-return information) is wrong, but plausibly because **the market has often already priced the
  improvement by the time the multi-year confirmation is computable** — this is backward-looking, lagging
  confirmation, not a fresh surprise. A stock can pass `confirmed=1` on stale, well-known good news.
- Minervini/O'Neil's "institutional accumulation days" concept (a cluster of up-days on above-average volume,
  materially outnumbering down-volume days, in the weeks following a print) is a DIFFERENT claim from PEAD: it
  asks whether the market is CURRENTLY and ACTIVELY validating the name (real-time positioning), not whether
  price already drifted in the direction of a stale surprise. Gating `earnings_confirm_v2=1` names further —
  require BOTH the fundamental confirm AND live accumulation-volume evidence in the trailing 4-8 weeks — is a
  genuinely different (and narrower, rarer-firing) claim than "buy the post-earnings gap and ride it."
- This would almost certainly SHRINK the ~5.9% firing rate further (an AND-gate on an AND-gate), which cuts
  both ways: less dilution risk (the S7 finding was ~94% of rows sit at the inert neutral-0.5 filler value,
  which is the actual dilution mechanism), but a thinner effective sample raises the same low-t / DSR-thin-window
  concern the firm already flags on the 1Y/5Y relative legs.

**[OPINION] Verdict on point 3, stated plainly: PARTIALLY, and only in a specific form.** A raw price/volume
"buyable gap-up" overlay is very likely a relabeled version of the already-dead PEAD trade and should not be
built. A NARROWER volume-accumulation FILTER layered on top of the existing fundamental confirm flag (to
distinguish "market is actively re-rating this name right now" from "the flag fired on stale good news") is a
mechanistically distinct, non-prior-art-violating hypothesis, cheap to test with data already on disk
(`cube_close_long.parquet` for price, need a volume panel — flag to Kavya Reddy/Data Officer if the volume cube
isn't already built alongside the close cube), and worth a genuine cheap-test with the firm's standard hard
gates (placebo + lag-test) before it goes anywhere near a weight. **I would NOT promise it fixes earn_1M — I
would promise it is a well-posed, non-redundant test, distinct from the already-killed PEAD trade, that could
go either way.** Recommend Quant runs it as a bounded cheap-test (one hypothesis, one pre-registered kill
threshold), not folded silently into a re-weighting.

---

## 4. Relative strength (RS-line) methodology — O'Neil/IBD "the tape knows first"

**[OPINION with a testable claim flagged]**

O'Neil-style RS ranks a stock's own price performance against the broader index/universe (percentile rank of
trailing return, commonly 12-month or a blend of 3/6/12-month). The claim ("the tape knows first") is that
persistent relative outperformance often PRECEDES visible improvement in reported fundamentals — informed
buyers (analysts with channel checks, insiders, institutions front-running earnings) bid the stock up before
the numbers catch up. **Is this a testable claim distinct from ALPHA_RANKER's existing momentum leg, or is it
circular?**

Read honestly: **RS-as-used-in-the-trend-template (criterion 8, RS percentile ≥70 vs Nifty-500, 12m return rank)
is, by construction, the SAME statistical object as a 12-month momentum factor** — both are cross-sectional
ranks of trailing relative return. It is not circular in the sense of "meaningless," but it is NOT a
fundamentally distinct signal from `mom_1M`'s underlying momentum leg described in `REGIME_SPEC_V2.md` layer A.
Where RS methodology adds something the pure-momentum literature doesn't already carry in this firm's docs is
narrower and more structural:

- **RS as a QUALIFYING GATE within an already fundamentally-screened universe**, not as a standalone
  cross-sectional ranker over the whole market. Used this way (only rank/require RS≥70 among names that already
  passed a fundamental watchlist screen), it functions as confirmation that the market is agreeing with the
  fundamental thesis — genuinely different in USE from ranking the whole universe on momentum, even though the
  underlying statistic is the same math. This is consistent with how the firm already treats momentum: gated by
  regime (layer A) and by valuation-extremes (layer C), never used blind.
- **The "tape knows first" claim as a LEAD INDICATOR for fundamental re-rating** (RS turning up before the next
  1-2 reported quarters show acceleration) is a genuinely testable, falsifiable hypothesis distinct from
  contemporaneous momentum-predicts-momentum: does an RS percentile inflection (e.g., crossing from <50 to >70
  over 2-3 months) forecast a subsequent improvement in `quality_cfo_pat` or `_w6fg2` operating-growth metrics
  1-2 quarters later, net of the stock's own current momentum level? **This is NOT the same test as "does
  momentum predict returns"** — it is "does momentum predict FUNDAMENTALS," a lead-lag causality question the
  firm has not run. **[INFERENCE] I flag this as a genuinely open, non-circular, cheap-to-test question** — it
  would use only data already on disk (`cube_close_long` for RS, `capstone_legs`/`_w6fg2_scored` for the
  fundamental outcome) and answers a different question from anything in the current scorecard.

**Verdict: not circular, but also not free lunch.** The trend-template's RS gate is functionally a momentum
filter (already captured, don't double-count it as new information). The "tape leads fundamentals" causal claim
is a distinct, testable, currently-untested hypothesis worth a cheap-test slot — but it is a research item, not
something to assume true and build on top of.

---

## 5. How techno-funda changes across regimes — cross-referenced against REGIME_SPEC_V2

**[DATA + OPINION]** `REGIME_SPEC_V2.md` layer A already certifies, on this firm's own data, that clean
Stage-2/VCP-style trend-following behaves DIFFERENTLY by regime — this is not a hypothesis, it is the firm's
own certified finding, and the technical literature is directionally consistent with it:

- **BOOMING_BULL:** 12m (or 6m) skip-month momentum works cleanly (HIGH confidence, 13 episodes) — this is the
  textbook Stage-2/VCP regime: bases form, breakouts hold, "sell into strength" trims into genuine markup runs.
  Clean chart patterns are MOST reliable here.
- **NORMAL_CHOPPY:** momentum works but is noisier (MEDIUM confidence) — VCPs still form but false breakouts
  are more common; the volume-confirmation discipline (§2) matters more here, not less, because a chop regime
  is exactly where a low-volume "breakout" fails.
- **BEAR_OVERSOLD (breadth ≤20th pctile, downtrend):** **momentum is SUPPRESSED ENTIRELY** (all lookbacks
  IC<0, robust across all 9 episodes, HIGH confidence) — and this is where the mandate's cross-reference is
  exactly right: a genuine Stage-2 base-and-breakout is NOT what typically happens off a washed-out bottom.
  **What actually happens (layer B, this firm's CERTIFIED `rev5d` finding) is a sharp, mechanical, mean-reverting
  bounce (5-day reversal, 2.9x IC lift, drop-one-robust across all 12 episodes, survives 2× cost stress) — a
  V-shaped reflexive rally, not a clean multi-week base.** Classic Weinstein/Minervini stage theory describes
  Stage 1 as a multi-week-to-multi-month SIDEWAYS base preceding Stage 2 — that pattern assumes an orderly market.
  An oversold-extreme snapback is a DIFFERENT animal: fast, violent, driven by short-covering/dip-buying
  mechanics, not by a VCP's gradual supply-exhaustion. **Practical implication for the technical desk: do NOT
  apply trend-template/VCP logic to name a bottom in a breadth-washout regime — the certified play there is the
  reversal switch (layer B), which is a mean-reversion trade, not a stage-2 breakout trade.** Attempting to
  "buy the VCP breakout" during a bear-oversold bounce risks exactly the false-start failure mode described in
  §2 (the bounce IS the volume surge, but it's happening in Stage-1/4 chart geometry, not confirmed Stage 2).
- **Overbought-in-recovery ≠ froth-overbought (Principal's rule, already in ALPHA_RANKER's 1M relative leg):**
  the technical-literature analogue is real and supports this distinction. A stock that is "overbought" by RSI
  immediately off a Stage-4-to-Stage-1 turn (early recovery, still far below its highs) is mechanically
  different from a stock "overbought" after an extended Stage-2 run near 52w highs (late-cycle, distribution
  risk). Minervini's own framework implicitly encodes this: RSI/overbought readings are read IN CONTEXT of
  where price sits relative to the 52w range and the stage, never as a standalone mean-reversion sell signal.
  This cross-references cleanly with `REGIME_SPEC_V2` layer C (valuation-extreme gate) — both frameworks
  independently arrive at "the same raw statistic (overbought reading / momentum score) means different things
  depending on where you are in the cycle," which is exactly the design logic of a regime-conditional gate over
  a static threshold.

**Net: the technical-analysis literature does not contradict the firm's regime work — it independently arrives
at the same structural conclusion (momentum/pattern reliability is regime-conditional, not universal) via a
completely different empirical tradition (chart pattern taxonomy vs statistical IC certification). That
convergence is itself evidence worth noting, not proof — the two traditions could both be wrong in the same
direction. But it is consistent, not contradictory.**

---

## 6. Position management / trade management rules — a THIRD exit-discipline candidate

**[DATA]** `FUND_MANAGER_PLAYBOOKS.md` (read in full, this folder) identifies GAP 1 as ALPHA_RANKER's single
highest-value missing piece: **no sell/deceleration/valuation-ceiling exit trigger anywhere in the scorecard.**
Two candidates are already on record there:
1. **Jain's valuation-ceiling round-trip** — sell when a name's own valuation crosses from cheap-relative to
   rich-relative (fundamental, PE-based).
2. **Fisher's "3 reasons to sell"** — original thesis was wrong / no longer passes the quality checklist /
   distinctly better opportunity (qualitative, fundamental-deterioration based).

Both are FUNDAMENTAL exit triggers. The technical school offers a genuinely different, MECHANICAL,
price/volume-based answer to the same gap — no PE data, no qualitative judgment, cheap to build from data
already on disk (`cube_close_long.parquet` + a volume series). **Proposing this as candidate #3, comparable in
concreteness to the other two:**

**Candidate #3 — Minervini mechanical stop/trim discipline:**
- **(a) Initial hard stop, 7-8% below entry (or below the pivot if entry occurred at/near a VCP breakout).**
  This is the "get out and think" rule: a Stage-2 entry that immediately fails by 7-8% is a WRONG entry, full
  stop, no averaging down, no exception for "but the fundamentals are still good" — the technical failure is
  itself the signal, evaluated independently of the fundamental thesis. Position size at entry is set so that
  this stop distance × shares ≤ RISK_LIMITS' 1.0% of book equity per position — the stop is decided BEFORE the
  entry, sizing follows from it (never the reverse).
- **(b) Sell-into-strength trim, not a single all-or-nothing exit:** scale out 20-30% of a position after a
  "climax run" signature — e.g., the stock is up ≥25% in ≤3 weeks on an already-extended Stage-2 move, or gaps
  up sharply on high volume after already being well above its base (a "blow-off" bar). This locks in gains
  incrementally WITHOUT requiring a fundamental valuation ceiling to be crossed — it is a pace-of-advance
  signal, not a valuation signal, and fires faster than a PE-based ceiling typically would.
- **(c) Stage-transition full exit, independent of the fundamental thesis:** a confirmed Stage 2→3/4
  transition — close breaks below the 50MA on above-average volume, the 50MA crosses below the 150MA, and/or a
  cluster of "distribution days" (4-5 higher-volume down-days within a 3-4 week span) — is a full-exit trigger
  EVEN IF the fundamental thesis (quality/growth/value) is fully intact. This is the mechanism that directly
  answers the S7 absolute-scorecard finding that the current model has no drawdown control and loses to a
  random placebo on Calmar at every horizon (`SCORECARD_FINAL_SUMMARY.md` escalation #3): a mechanical,
  price-based stage-exit is a mechanism that would have started de-risking BEFORE a name's max-drawdown
  realized, without needing any fundamental deterioration to show up first.

**How this differs from — and complements — Jain and Fisher:** Jain's trigger needs the valuation to actually
get rich (can be slow, or never fire if a name just grinds down without ever re-rating). Fisher's trigger needs
a fundamental/qualitative judgment call (can lag — by the time growth "visibly" decelerates in reported
numbers, the stock may already be down 30-40%). The technical trigger needs NEITHER — it fires purely off price
and volume, which move faster than either valuation multiples or reported fundamentals. **[OPINION] My
recommendation: these three are not mutually exclusive candidates to pick ONE from — they are complementary
layers that should compose as an OR-gate (exit fires on whichever trips first), with the technical trigger
functioning as the fastest-reacting layer and Jain/Fisher as slower-moving confirmation or independent triggers
in their own right.** A name can be technically stopped out (c) while its fundamental thesis is still intact —
that is not a contradiction, it is the technical layer doing its job faster than the fundamental layer can.

---

## Fund-manager-honesty section — where techno-funda breaks in this firm's actual universe

**[OPINION, mandatory self-red-team per charter]**

1. **Small/micro-cap circuit-filter distortion directly corrupts the VCP read.** The firm's own landmine
   (documented in root `CLAUDE.md` §7b: "no fill on circuit-locked bars; slippage 2-3x on thin-volume days")
   means a stock frozen at the upper/lower circuit for several sessions shows near-zero traded volume — which,
   read naively, LOOKS EXACTLY LIKE a genuine tight-VCP low-volume contraction (supply drying up). It is not.
   It is a liquidity/circuit artifact, not institutional accumulation. **A VCP scanner run blind over the small/
   micro-cap universe without a circuit-day filter will systematically misclassify circuit-frozen names as
   clean setups.** This must be gated on CONTRACTS>0-style liquidity checks (the same discipline the firm
   already applies to F&O bhavcopy, landmine #9) before any VCP scan is trusted below the liquid large/mid-cap
   tier the pattern was originally developed on (US large-caps, Minervini/O'Neil's own track record).
2. **Breakout-day "volume surge" in a thin name can be a single large trade, not broad participation.** In a
   name trading ₹5-10L ADV, one institutional block can create a volume spike that satisfies a mechanical
   ">1.5x average volume" filter without representing genuine broad-based demand. The pattern was pattern-
   matched on liquid names where volume surges reflect many independent participants; extending it uncritically
   to illiquid small/microcaps overstates the confirmation's reliability. Recommend a minimum ADV floor (aligned
   with the firm's own COST_STANDARDS untradeable-tier definition) before sizing any VCP-breakout name, not just
   a volume-ratio threshold.
3. **The real tension the mandate names, stated plainly: "buyable gap-up" / volume-breakout chasing IS a
   momentum bet, and `REGIME_SPEC_V2` already found momentum crashes at valuation extremes and is suppressed
   entirely in BEAR_OVERSOLD.** A technical desk that scans for breakouts without checking the SAME
   valuation-extreme and regime gates the quant scorecard already applies to `mom_1M` is not adding an
   independent edge — it is re-running the momentum trade through a different-looking screen, exposed to
   exactly the same crash risk (layer C: momentum_weight=0 at richness<65 or ≥160; layer A: momentum IC<0 in
   BEAR_OVERSOLD, robust across 9/9 episodes). **Concretely: this desk's tech-scan output should be regime- and
   richness-gated before any timing verdict is issued, not run as a standalone signal.** I will apply this
   discipline going forward — a Stage-2/VCP "act" verdict issued during a certified BEAR_OVERSOLD regime or at a
   richness≥160 extreme should be downgraded to "wait" regardless of how clean the chart looks, per the firm's
   own certified findings. This is not a hypothetical — it is the same guardrail already wired into ALPHA_RANKER's
   momentum leg, and the technical desk has no standing to ignore it just because the entry signal LOOKS different.

---

## Actionable for ALPHA_RANKER — direct answers to the two questions posed

**Point 3 (does a volume/price confirmation sharpen the weak `earn_1M` leg)?** **Partially, in a narrow form
only.** `earnings_confirm_v2` is a fundamental (not price-reaction) flag — the mandate's framing of it as an
"earnings-surprise" leg is a naming mismatch worth flagging to Arjun Rao directly. A raw price/volume
"buyable-gap-up" overlay is mechanistically the same trade as PEAD, which `REGIME_SPEC_V2` layer G already
tested and killed (IC≈−0.003, dead in every regime with adequate n) — do not rebuild it. The genuinely distinct,
non-prior-art-violating hypothesis is a NARROWER one: gate the existing fundamental confirm flag further with a
contemporaneous institutional-accumulation volume signature (up-volume days outnumbering down-volume days in
the 4-8 weeks after the print) — testing whether the market is ACTIVELY re-rating the name now, vs the flag
having fired on stale, already-priced-in good news. This shrinks an already-sparse 5.9% firing rate further, so
it inherits the same thin-sample/low-t caution the firm already applies to the 1Y/5Y relative legs — recommend
it as a bounded, hard-gated cheap-test (placebo + lag-test, pre-registered kill threshold), not a silent
re-weight.

**Point 6 (technical stop-loss/trim rule as a third exit-discipline candidate):** propose Minervini's mechanical
stop/trim discipline as candidate #3 alongside Jain (valuation-ceiling) and Fisher (3-reasons): **(a)** 7-8%
hard stop below entry/pivot, position-sized so stop-distance × shares ≤ 1.0% of book equity (`RISK_LIMITS.md`);
**(b)** sell-into-strength trim (20-30%) on a climax-run signature (≥25% move in ≤3 weeks or a blow-off volume
bar); **(c)** full exit on a confirmed Stage 2→3/4 transition (50MA crosses below 150MA + distribution-day
cluster), independent of whether the fundamental thesis is intact. This is the fastest-reacting of the three
candidates (price/volume moves before valuation multiples or reported fundamentals do) and directly answers the
S7 finding that the current absolute scorecard has no drawdown control and loses to a random placebo on Calmar
at every horizon — recommend composing all three as an OR-gate (exit on whichever trips first) rather than
picking one, with the technical trigger as the fast layer and Jain/Fisher as slower fundamental confirmation.

**Standing caution to carry into any build:** any technical-breakout signal fed into ALPHA_RANKER must inherit
the SAME regime/valuation-extreme gating already certified for `mom_1M` (REGIME_SPEC_V2 layers A/C) — chasing
volume breakouts ungated is exposed to the identical momentum-crash risk the quant desk already found and fenced
off. And any VCP/volume scan run on the small/micro-cap universe needs a liquidity/circuit-day filter before its
output is trusted — circuit-frozen bars mimic genuine low-volume contraction but are a data artifact, not
institutional accumulation.
