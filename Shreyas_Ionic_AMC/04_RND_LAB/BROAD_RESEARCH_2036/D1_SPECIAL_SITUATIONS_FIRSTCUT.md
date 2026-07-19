# D1 Special-Situations/Event-Driven — First-Cut Cheap Test
**By:** Prof. Aditya Verma (R&D), 2026-07-18. Roadmap task T2 (second half). Stage: **3-CHEAP-TEST**.
Code + raw outputs: `Shreyas_Ionic_AMC/04_RND_LAB/results/D1_SPECIAL_SITS_CHEAPTEST_20260718/`
(`d1_buyback_cheaptest.py`, `RESULTS.md`, `events_with_returns.csv`, `placebo_draws.csv`, `summary_by_window.csv`).

## [DATA] 1. What D1 originally proposed
`swing_momentum/GOD_TIER_EXPANSION.md` lines 38-44 (read verbatim, never edited — legacy file):
> **D1 — SPECIAL SITUATIONS / event-driven ★ top add, uncorrelated to momentum**
> Merger/acquisition arb (open-offer spread), demerger/spin-off value-unlock, buyback & tender-offer
> arb, rights-issue, delisting reverse-book-building, scheme-of-arrangement.
> Why small: spreads are tiny in ₹ terms → institutions skip; ≤₹10Cr captures them.
> Why uncorrelated: payoff driven by DEAL outcome/timeline, not market beta.
> Test: build India corporate-action/deal calendar; backtest open-offer & buyback spreads vs
> completion; downside = deal-break (define & cap). Convex where downside floored.

Six event types proposed, zero backtests ever run (confirmed by Devika's independent
`SWING_MOMENTUM_ASSESSMENT.md` read of the same folder). D1 was ranked the #1 build priority in
the sequencing section (`GOD_TIER_EXPANSION.md` line 112).

## [DATA] 2. Data reality check — what can actually isolate an event TYPE
Three candidate sources were checked directly (row counts verified, not assumed):

| Source | Rows | What it actually contains | Usable for D1? |
|---|---|---|---|
| `ALPHA_RANKER/rnd/panel/panel_pit.parquet` `disc_event_in_window_{1M,1Y,5Y}` | count col on 99,415-row panel | Confirmed by reading `build_panel_long.py` lines 84, 200-261: a **pure `\|1-day return\|>0.40` price-discontinuity counter** (split/bonus/data-error suspect flag), used ONLY to NaN contaminated forward-return targets. It carries **no event-type label whatsoever** — cannot tell a split from a buyback from a data error. | **No** — confirms the task brief's own prior: guard-only, not a signal source. |
| `datasets/derived/corporate_action_factors.parquet` | 613 | Read directly: cols are `symbol, ex_date, action_type, adjustment_factor, subject, dividend_amount`. `action_type` value_counts = **bonus 282 / split 281 / dividend 50 — exactly zero rows of any other type.** Keyword search of `subject` free text for buyback/demerger/merger/open-offer/delisting/scheme-of-arrangement/rights-issue/tender/amalgamation returned **0 hits on every single term.** | **No** — this is a price-adjustment-factor table (for computing adjusted close), not a special-situations event feed. |
| `datasets/nse_earnings_dates/board_meetings_all.json` | 94,136 | NSE board-meeting-intimation archive, 2020-01→2026-07, fields include `bm_purpose` (free-text) and `bm_timestamp` (NSE disclosure system timestamp — genuinely PIT). Keyword-scanned `bm_purpose`+`bm_desc`: **buyback 406 raw / 282 deduped events (177 symbols); rights issue 236; delisting 138; scheme-of-arrangement 101; merger 43; scheme-of-amalgamation 28; demerger 15.** | **Yes, for buyback (best-populated) — see §3.** The other five event types have SOME hits (15-236 rows) and could be mined the same way as a follow-up, cheaply, from data already on disk. |

**Verdict on the data-ask:** the task brief's expectation was correct — `disc_event_in_window` is
confirmed guard-only. But an actual event-level, PIT-timestamped, free-text-classifiable feed
**does exist on disk** (`board_meetings_all.json`, never previously mined for this purpose) and was
not previously known to carry special-situations content. This changes the deliverable from a pure
data-ask into a genuine first-cut test (below), because the "cheapest" event type (buyback board-
meeting intimations) has enough clean rows to run honestly.

## [DATA] 3. The cheap test actually run — buyback board-meeting intimations
**Event definition:** first NSE disclosure (`bm_timestamp`) that a board meeting will be held "to
consider a proposal for buyback of equity shares." This is the CONSIDERATION intimation, not
confirmation of approval or the buyback price — see limitations (§5).

**PIT anchor:** `bm_timestamp` (NSE's own disclosure-system timestamp), never `bm_date` (the
scheduled — future — board-meeting date; anchoring on `bm_date` would be a lookahead bug since the
meeting date is itself announced IN ADVANCE at `bm_timestamp`). Entry-day rule: disclosure ≤15:30
IST → same trading day is day-0; disclosure >15:30 IST → next trading day is day-0 (matches the
after-hours pattern of most filings sampled: 16:xx-22:xx).

**Universe/prices:** `datasets/derived/pit_union_panel_v1/close_panel_price_v11.parquet`
(survivorship-safe PIT price panel, 2000-2026, 2,522 symbols — same Line-A-methodology panel the
roadmap names for T2 Part A). 282 deduped (symbol, meeting-date) events → 277 matched a panel
symbol → **252 events on 161 distinct symbols** had a full pre-event close + forward window.

**Placebo:** for every real event, 10 random non-event trading days drawn from the SAME symbol's
own history (excluding ±15 trading days around any real event for that symbol) — same-symbol
matching controls for that name's own vol/beta/typical drift, isolating the buyback-specific
effect rather than "this symbol tends to rise." 2,520 placebo draws, fixed seed (20260718),
deterministic.

**Results (close-to-close from day-0):**

| window | real mean | real median | real t (vs 0) | placebo mean | excess (real−placebo) | Welch t | p |
|---|---|---|---|---|---|---|---|
| +1d | +0.85% | +0.21% | 3.33 | +0.11% | **+0.74%** | 2.83 | **0.0049** |
| +5d | +2.01% | +0.94% | 3.77 | +0.77% | **+1.24%** | 2.25 | **0.0250** |
| +10d | +2.05% | +0.75% | 3.21 | +1.58% | +0.47% | 0.66 | 0.51 |
| +20d | +2.28% | +1.37% | 2.89 | +2.82% | −0.54% | −0.62 | 0.53 |

Anticipation window (t-5→t0, context only, NOT tradeable — occurs before public disclosure):
mean **+4.46%**, t=7.96. This is a large pre-announcement run-up (likely: buyback-announcing
companies already trending up for independent reasons, and/or market anticipation once a
results+buyback combo meeting is scheduled). It is excluded from the signal itself — using it
would be lookahead — but is filed here as an honest, load-bearing observation.

**Lag-robustness check (entry shifted +1 extra trading day, i.e., "what if you act one day
late"):**

| window | lag1 real mean | lag1 t (vs 0) | lag1 excess vs placebo | lag1 t | lag1 p |
|---|---|---|---|---|---|
| +1d | +0.17% | 0.65 | +0.06% | 0.22 | 0.83 |
| +5d | +1.25% | 2.39 | +0.48% | 0.89 | 0.37 |
| +10d | +1.09% | 1.81 | −0.49% | −0.72 | 0.47 |
| +20d | +1.78% | 2.26 | −1.04% | −1.19 | 0.23 |

## [INFERENCE] 4. Reading the result
- **The effect is real and concentrated, not spurious multi-day drift.** +1d and +5d excess over
  the same-symbol placebo are statistically significant (p=0.005, p=0.025) BEFORE the entry is
  lagged. Once entry is pushed back one extra trading day, the excess collapses to statistically
  indistinguishable from zero at every horizon (p=0.23-0.83). This is the expected signature of a
  genuine, quickly-priced-in announcement effect (not a multi-day drift you can still catch late),
  and it is reassuring on lookahead: if the +1d/+5d numbers had instead been an artifact of
  anchoring on the wrong (future) date, lagging by one MORE day should barely matter — instead it
  kills the effect almost completely, exactly consistent with "the edge lives in being present at
  the actual, correctly-dated disclosure moment," which is what a real reaction to real news looks
  like.
- **By +10d/+20d the excess over placebo fully evaporates and even inverts slightly** (−0.54% at
  +20d, not significant) — there is no post-announcement DRIFT here distinct from the stock's own
  baseline momentum; whatever the market has to say about a buyback-considering company, it says
  it within about a week.
- **Cost check** (COST_STANDARDS.md, APPROVED D-021): mid-cap equity delivery round-trip ≈ STT
  0.20% + slippage tier 20bps×2 (1x) + stamp/exchange/GST ≈0.03% ≈ **~0.6% round-trip at 1x, ~1.0%
  at the mandatory 2x stress.** Against the +1d excess (+0.74%), 1x cost roughly consumes the edge
  and 2x cost exceeds it — **the 1-day flip does not clear 2x cost.** Against the +5d excess
  (+1.24%), net is +~0.6% at 1x and **+~0.2% at 2x** — thin, positive, not gross. This is a
  **marginal-but-not-gross post-cost shortfall**, which per this program's own discipline (§DISCIPLINE
  item 4 in `BROAD_RESEARCH_ROADMAP.md`) is NOT an automatic kill trigger (only a "gross" shortfall
  is); it is a genuine capacity/execution-quality-dependent edge.
- **Per firm discipline (never kill on low-t/small-n alone if logic+effect sound):** n=252
  events/161 symbols over 6.5 years is small in absolute terms but is a NORMAL sample size for a
  low-frequency special-situations study (≈40 events/yr firm-wide, well inside the "<5 trades/mo"
  capacity-friendly band already used elsewhere in this program as a resurrection bar for
  event-driven signals) — this is not a reason to kill by itself, and the placebo-adjusted p-values
  at +1d/+5d clear conventional significance.

## [DATA/INFERENCE] 5. Honest limitations (why this is a first-cut, not a certified pass)
1. **The data only captures the INTIMATION-to-consider stage**, not confirmed board approval, the
   buyback price, size, or record date. We have not verified what fraction of these 282 intimations
   actually resulted in an approved/completed buyback — assumed (not confirmed) to be a large
   majority based on general market convention that boards rarely file "will consider buyback"
   without near-certain intent; this is an [INFERENCE], not a checked fact.
2. **No liquidity/ADV or circuit-lock realism applied** (landmine #7b) — buyback-considering firms
   skew mid/small-cap, exactly where thin-volume slippage multipliers and circuit-lock no-fills
   matter most. A same-day/next-day entry, which this test assumes is achievable at the close, may
   not be realistically fillable at size for the thinnest names in the sample.
3. **Close-to-close proxy for entry.** Some disclosures land pre-market (e.g., 08:59 IST,
   observed in the raw data) — for those, day-0's own close already partially reflects the news,
   understating (conservatively, not lookahead) the true capturable pop for that subset.
4. **Only 1 of 6 proposed D1 event types tested.** Merger/acquisition open-offer arb, demerger/
   spin-off, rights-issue, delisting, and scheme-of-arrangement remain untested. The SAME
   `board_meetings_all.json` free-text field has non-trivial hit counts for several of them
   (rights issue 236, delisting 138, scheme-of-arrangement 101, merger 43, demerger 15 raw
   mentions) — these are the natural, cheap next step (see §6), not a new data ask.
5. **No DSR/PBO computed** — correctly not owed at cheap-test stage per this program's own
   convention (Gate-4 item), and appropriate here since this is one construction, not a searched
   family.

## 6. Stage-gate verdict
**Stage: 3-CHEAP-TEST — PASS-WITH-FLAGS, NOT KILLED.** Real, statistically significant (p<0.05),
economically small, cost-thin, execution-timing-sensitive announcement-day effect on buyback
board-meeting intimations. Distinct from a data artifact (survives the lag-robustness check
exactly the way a real, correctly-dated event effect should) and distinct from ordinary momentum
(the same-symbol placebo, not a market-wide placebo, is the arbiter here, per the program's
same-exit-placebo convention).

**Honest trials count:** 1 construction (buyback-only, +1/+5/+10/+20d windows, one lag variant) —
this is the family's FIRST test, not a searched grid.

**Next cheapest step (in priority order):**
1. Extend the SAME `board_meetings_all.json` mining to the other 5 keyword-filterable event types
   (rights issue, delisting, scheme-of-arrangement, merger, demerger) — zero new data needed, same
   script pattern, cheap.
2. Apply liquidity/ADV + circuit-lock realism (`lib/execution_realism.py`) to the buyback result
   specifically before any capital conversation — the +5d net-of-2x-cost edge (~+0.2%) is thin
   enough that fill realism could plausibly erase it.
3. Spot-check a sample of the 282 intimations against actual buyback outcomes (approved vs
   withdrawn, and price vs market at announcement) to confirm the assumption in limitation §5.1 —
   this is a Data Officer (Kavya) D-009-style verification pass, not new data acquisition.

## 7. Data-ask (for the 5 untested D1 event types, if a cleaner source is wanted later)
If the Principal/Data Officer wants a materially better feed than free-text board-meeting mining
(which has no confirmed-outcome, price, or size fields), the precise ask is:
- **Buyback:** SEBI/BSE-NSE buyback-record filings with `record_date`, `buyback_price`,
  `buyback_size`, `method` (tender/open-market), `opening_date`, `closing_date`, `completion_status`.
- **Demerger/spin-off:** scheme-of-arrangement filings with `record_date`, `share_entitlement_ratio`,
  `effective_date`, resulting-entity listing date.
- **Open-offer/delisting:** `offer_price`, `offer_size`, `acquirer`, `trigger_date`,
  `completion/withdrawal status`.
- **Merger/scheme-of-arrangement:** `announcement_date`, `swap_ratio`, `regulatory-approval
  milestones`, `effective_date`.
All of the above are Data Officer D-009 (external-source verification) + Principal-approval items
per this firm's charter (scraping/new-data proposals are proposed, never auto-fetched by R&D) —
flagged here as a precise spec, not fetched.

## Files
- Legacy source (read-only, unedited): `swing_momentum/GOD_TIER_EXPANSION.md` (D1, lines 38-44),
  `swing_momentum/PLAN.md`.
- Data checks: `ALPHA_RANKER/rnd/lib/build_panel_long.py` (disc-event guard logic, lines 84,
  200-261), `datasets/derived/corporate_action_factors.parquet`,
  `datasets/nse_earnings_dates/board_meetings_all.json`.
- Cheap-test code + outputs: `Shreyas_Ionic_AMC/04_RND_LAB/results/D1_SPECIAL_SITS_CHEAPTEST_20260718/`
  (`d1_buyback_cheaptest.py`, `RESULTS.md`, `events_with_returns.csv`, `placebo_draws.csv`,
  `summary_by_window.csv`).
- Price panel used: `datasets/derived/pit_union_panel_v1/close_panel_price_v11.parquet`.
