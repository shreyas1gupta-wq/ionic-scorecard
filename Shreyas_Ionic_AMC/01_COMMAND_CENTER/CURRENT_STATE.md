# CURRENT STATE — read me first (updated every session end)

## 750-SCORECARD MILESTONE — 2026-08-03 evening (DESK-100, parallel session)
**The 750-universe analyst-research build is COMPLETE: 751/751 pf_qual files on disk** (560 Hold /
191 Sell, 126 escalations → `09_PRODUCT/reports/ESCALATIONS_750_REVIEW.xlsx` for Principal
adjudication). Deliverable: `09_PRODUCT/reports/ANALYST_RECOMMENDATIONS_750.xlsx` (751×43, 4 sheets).
**pf_state initialized for the FULL universe (751 files)** — the Thursday weekly V1 router now runs
incrementally over everything. Talaulikar deck upgrade in flight (19 former No-View names now have
real scores; 5 remain outside the universe). **OPEN: technical-agent pass has never run (0/751 have
chart scores) — blocked on choosing the per-symbol multi-year price source; do NOT launch it against
an unverified path.** MF: NAV-refresh armed Sep-1; QFRA models stay Apr/Oct (next Oct-end). Full
detail in SESSION_JOURNAL 2026-08-03 entries.

## >>> RESUME HERE — 2026-08-03, session paused softly by the Principal <<<
**READ THIS BLOCK FIRST NEXT SESSION.**

### The one thing that changed everything today
**Budget-2026 STT hike CONFIRMED (2 independent sources), effective 1 April 2026:**
futures on sale value **0.02% -> 0.05% (+150%)**, options on premium 0.10% -> 0.15%, exercise
0.125% -> 0.15%. STT is not a line item in our futures cost, it IS the cost (non-STT residual only
1.97 pts). **NIFTY futures round trip 7.27 -> 14.47 index pts at spot 24,000 (1.99x).** Measured gross
edges cluster at 2-5 pts, so they are now 3.6x under the floor.
**Asymmetry:** futures 1.99x, options **1.027x** (STT is on PREMIUM not notional), MCX gold **1.00x**
(CTT not STT). **Gold is now 2.45x CHEAPER than NIFTY futures, reversing my own earlier "no cost
advantage" conclusion.** Four survivors died, including ICHIMOKU_TK (+2.442 -> -4.758), which had been
the only TradingView cell to clear a placebo. Evidence pack: `04_RND_LAB/results/STT_RECOST_20260803/`.

### FIRST ACTION NEXT SESSION — needs the Principal, not more research
**COST_STANDARDS.md amendment awaiting sign-off (APPROVED under D-021, so only he can change it).**
Recommended: futures STT 0.05% with the STT term computed from CONTEMPORANEOUS SPOT rather than a fixed
point value; options STT 0.15% of premium; an explicit MCX row noting CTT-not-STT. Until signed, every
quoted futures result carries a pre-April-2026 cost basis, and April-Jun 2026 held-out figures are
UNDER-COSTED (small in trade count, uniformly optimistic).

### SECOND ACTION — read three agent folders that were still running at pause
They bank to disk continuously, so their outputs should be present even though the session ended:
1. `04_RND_LAB/results/SELL_PLUS_TAIL_20260803/` — **the highest-value open build.** Short-premium core
   x long-put tail overlay (hedge ratio x moneyness x tenor), re-costed at new STT, net-hedge-positive
   discipline, max survivable notional under a COVID repeat. The case for it: selling is the edge
   (VRP +0.0605 vol pts at **t=32.14**, the strongest number in the book; realised short of straddle
   breakeven on 95.3% of trades; gamma/theta fell 1.15 -> 1.03 -> **0.83** post-Oct-2024) but a crash
   ruins it (20-day -37.01% = **3.70x the entire margin**; LD_SELL's real COVID cycles lost Rs42,545,
   worst trade -50.6% of its margin WITH a 2x stop armed). The fix is measured and nearly free: a plain
   5%-OTM long put held to expiry costs **-18 to -20 pts/yr at t=-0.69** and paid **+3,463 pts in the
   real 2020 crash**. PLEDGE_SAFE already showed it converting a FAILING COVID drawdown (-20.17%) into
   a PASSING one (-17.53%). And the STT hike makes an all-options book strictly better.
2. `04_RND_LAB/results/GOLD_VENUE_20260803/` — gold re-opened as the now-cheapest venue: time-of-day
   decomposition across the 14.5h MCX session, MCX-session gap behaviour, RR curve as a third test of
   the negative-excess-slope result. NOTE gold's standalone verdict was still NEGATIVE (gross 0.0149%
   vs its own 0.0246% cost) — only the venue RANKING moved.
3. `04_RND_LAB/results/OPEN_ITEMS_20260803/` — isolates how much of A6_vwap_proxy_continue's
   +4.153/t=2.576 was the 25.6% wrong-expiry drop_duplicates defect vs methodology; writes
   PUTCAL_LADDER's missing FINDINGS.md; spot-checks the no-pre-2010-index-data conclusion.

### Where the book actually stands (post-STT, honest)
- **SWEEP_E is the only clean survivor** of ~1,872 nominal cells (~40-55 effective independent trials):
  DSR 0.996-1.00, PBO 0.00. S1-F, the certified flagship, newly carries **PBO=33%**. OVERSHOOT fails
  DSR at ~0.00. CALENDAR fails at 0.58-0.70.
- **Portfolio: BALANCED — RE-COSTED 2026-08-03 (Vikram), recommendation HOLDS.** Historical (old-rate)
  Sharpe 1.81/Calmar 1.765/CAGR 10.29%/MaxDD -5.83%; **forward-costed (new STT throughout) Sharpe
  1.10/Calmar 1.034/CAGR 6.60%/MaxDD -6.38%** — still the best risk-adjusted of the three, but CAGR
  nearly halves. HIGH_CAGR's fitted weights independently moved AWAY from SWEEP (11.92x->5.02x
  documented size) and toward every options sleeve + BOOK once recosted, confirming the futures-vs-
  options asymmetry at the portfolio level — but HIGH_CAGR still trails BALANCED on Calmar/Sharpe, so
  the "don't run HIGH_CAGR as designed" call is reinforced, not reversed (capacity ask shrinks to ~5x,
  still unverified). CPPI drawdown-floor overlay re-tested: its Calmar benefit on HIGH_CAGR REVERSES
  post-recost (1.232->1.699 historically vs 0.671->0.633 forward) — no longer recommended.
  Full detail: `04_RND_LAB/results/PORTFOLIOS_RECOST_20260803/PORTFOLIOS_RECOST.md`.
- **Option buying is CLOSED** from four independent angles, with the mechanism dated to Oct-2024.
- **Scaling:** 1 lot until forward evidence. If scaling, 3-session hold + CPPI floor — NOT the
  high-frequency arm and NOT naive monthly addition. **Frequency is not what makes a strategy scalable;
  edge-to-drawdown ratio is** — a conclusion the STT hike independently confirms.

### Still owed
Capacity check on SWEEP (~5x post-recost, down from ~12x) before any HIGH_CAGR sizing. Acquire SENSEX
daily 1979+ (without it 2008, 2000 and 1992 stay untestable). ~~Re-cost THREE_PORTFOLIOS at new STT~~
DONE 2026-08-03. EVENT_FED paper-track at zero size through 4-6 FOMC cycles (era sign-flip unresolved).

### Corrections issued this run — six of my own numbers
73% CAGR portfolio (contaminated by an excluded sleeve) · the 106%->73.1% withdrawal (never existed) ·
SWING maxDD (neither prior number right) · the crash-data claim (wrong for 2 of 3 sleeves) ·
A6 VWAP-continue (wrong-expiry defect, re-test running) · gold's cost advantage (reversed by the STT
hike). Every one was surfaced by a control I had asked for, but they were my errors.

---


> **CORRECTION 2026-07-31:** an earlier claim that all three option-selling sleeves have no crash data is WRONG for two of three. Only OVERSHOOT (from 2021-06) lacks it; CALENDAR and LD_SELL span 2011-2026 with thin crash sampling. Detail in SESSION_JOURNAL.

## 2026-08-02 (DESK-100) — Financed/laddered long iron-fly KILLED (K-018, 32/32 cells); swing-level idea scoped
Principal's new option-buying variant (ATM straddle financed by a tight OTM short strangle,
weekly-rolled ladder, 4 vol-timing filters) tested despite strong prior art already flagging the
core mechanism as dead (`OPTBUY_CONVEXITY_20260731`, 2026-07-31). **Clean kill, all 32 cells**:
tighter wings (100-200pt) significantly NEGATIVE (t to -8.17) — the short strangle caps the payoff
on the one thing that could offset theta, so it's a worse buy, not a cheaper one. Widest wing
(300pt) just re-converges to the already-known fairly-priced naked-straddle result; best cell
(+8.49pts, t=1.11) fails its own placebo (p=0.088) and misses the honest Bonferroni bar
(t~4.20 needed at ~1,904-trial family size) by a mile. This is the 4th distinct vol-cheapness gate
to fail placebo on "time straddle-buying by IV vs RV" (after VIX-low/VIX-high/RV20-compression).
Found and fixed a small, harmless shared-cache bug along the way (4,447 exact-duplicate option
rows, 2024-07-01..05, flagged to Kavya). Full detail: `04_RND_LAB/results/IRONFLY_LADDER_20260802/
FINDINGS.md`, `04_RND_LAB/KILLED_IDEAS.md` K-018. **Separately**, Principal proposed a
support/resistance swing-high/low entry trigger — the firm already has an exact prior test
(`SWING_DELTA1_20260729`), a directional version of which reverses hard out-of-sample (best build
t_nw 1.858, held-out Sharpe -2.34 to -4.40 on every long variant). Reported as caution, not built.
**OPEN:** whether Principal wants the swing-level idea spec'd as a NEW intake (entry-timing filter
on the vol structure, not a directional bet, reusing SWING_DELTA1's existing level definition).

## 2026-08-02/03 (DESK-100) — PLEDGE_SAFE: Rs50L bond+Rs50L MF pledge-and-sell backtest, red-team caught a real bug, corrected verdict = yield ALONE fails the firm's own COVID bar, yield+protective-put PASSES it
Principal ask: pledge Rs50L G-sec (8%) + Rs50L equity MF as collateral, run options for yield "very
very safely." Reused S1-F (frozen spec) unchanged, sized via RISK_LIMITS.md's existing 40%-of-book
cap (0 breaches, 1,812 days verified). **Calm 2021-2026 (real NIFTY500 for the MF leg): combined
MaxDD -6.96% vs -9.81% baseline — yield HELPS.** COVID rerun first came back -23.34% (fails
RISK_LIMITS' own <20% COVID bar) — **red-team caught it was contaminated**: the reused covid_backcast
never applies F1/F2 vetoes, and the 2 worst days behind that number would both be vetoed live; also
caught a same-day sizing lookahead. **Corrected: yield-only COVID MaxDD -20.17% (still a real, narrow
breach + still worse than baseline).** Built a 50%-notional rolling protective put (real 2016-2026
option data, incl. actual COVID prices — paid +3,463pts in the real Feb-Apr-2020 window) per
Principal's mid-session follow-up allowing directional hedges: **yield+hedge corrected COVID MaxDD
-17.53% — PASSES the firm's bar and beats the passive baseline**, for ~0.5pt/yr CAGR cost in calm
markets. **Recommended: yield overlay + partial protective put, NOT yield alone.** Side-thread: PE
calendar ladder (buy-far/sell-near PE) confirmed DEAD at 45D/15D both roll timings; 90D/30D mildly
positive but underpowered (t=0.69) — forward-test candidate only, not in the recommended structure.
Put ratio spread: cheaper but doesn't help in a crash, real uncapped tail risk — not recommended.
Two background jobs (red-team, calendar Bash job) were lost to a process restart mid-session and
successfully resumed/relaunched — a resume-from-cache pattern (skip re-computing if `trades_*.csv`
already exists) was added, reusable for future long jobs. **OPEN: Principal decision on the
yield+hedge structure; 3 disclosed caveats unresolved (settlement/liquidity channel not modeled, no
GFC-class scenario testable — data starts 2015/2016, haircuts are labeled assumptions not a live
broker quote).** Full detail: SESSION_JOURNAL.md top entry + `04_RND_LAB/results/PLEDGE_SAFE_20260802/
FINDINGS.md`. Nothing committed to git yet.

## 2026-07-30/31 (DESK-100) — >100% CAGR hunt part 2: buying refused a 3rd time, regime-ML answered, candle system exposed as BETA
**HEADLINE: no single strategy reaches >100% CAGR at <25% MDD, and the reason is now measured four
independent ways.** (a) directional intraday edge is 2-5 index pts vs 5-6 pts futures cost; (b)
MFE/|MAE| = 0.92-1.32 across every signal family ⇒ no convexity for a buyer; (c) the 1:1.5
option-buying harvest is priced FAIRLY — hit rate 40-43% against the 44.7% needed to clear cost;
(d) the one 59%-CAGR candle system is ~60% index beta. **The portfolio route is still the only one
that works: ~73% CAGR at 25% MaxDD, Calmar 2.597, three independent constructions agreeing.**

**Option buying at the Principal's own spec (0.6 delta / ITM-100 / ITM-50, RR 1:1.5): 36,061 legs,
87 cells, 0 POSITIVE.** `GATED_BUYING_20260730`. Measured delta on the 0.60 rule = 0.602; ITM-50 =
0.590 ⇒ *0.6 delta and ITM-50 are the same instrument in practice*. Hit rate clusters at 40-43% and
breakeven at RR 1:1.5 is exactly 40.0%; clearing the 1.77-pt round trip needs 44.7%. The harvest is
priced fairly and the cost is the entire loss — not a tuning problem. The B2 IV/RV gate that cleared
its bar on the UNDERLYING (+4.584 pts, t=4.029) does NOT transfer to the option vehicle: CHEAP −0.99
≈ RICH −0.98, MID −0.45 beats both ⇒ noise at option level. Held-out 2026 worse (hit 30-37%).

**Regime-state ML built to spec — vol is predictable, direction is not.** `REGIME_ML_20260730`,
42,528 samples at 15-min, purged walk-forward + 5-day embargo + label-permutation placebo + held-out
from 2025-07. **Volatility bucket AUC 0.8528 OOS / 0.8742 HELD-OUT (strong, improves out of sample).
Choppy-vs-trending 0.5356 / 0.5055 held-out (coin flip).** No-trade head 0.6795 / 0.6917.
**I WITHDREW MY OWN HEADLINE HERE:** the first economic null (−0.0589 → +0.0089 gated, p=0.000) was
~17× inflated because the `tradeable` label was `winnable(long) OR winnable(short)`, crediting a
perfect direction choice the model never makes. Direction-committed rerun: the gate BEATS the
random-decline null 2015-2025 but **FAILS held-out** (−0.0045 at 80% decline). The placebo direction
gains nothing (p=0.23), so it is not merely a vol filter. **Usable for SIZING and the SELLING book,
never to rescue buying.** Also explains the earlier `REGIME_GATE_20260730` null result: that tested
monthly sleeve P&L at n=111-172 months; 15-min granularity gives 250× the observations.

**Candle formations × EMA/DMA: it works, but it is BETA.** `CANDLE_MTF_20260730`. 480 cells, best raw
t=9.90 → two self-caught defects. (1) OVERLAP: the signal fires on 11.7% of all 15-min bars with a
78-bar hold, so ~10 positions were open at once and the t-stat counted the same move ~10× (measured
2.9-10.7×); fixed to one-position-at-a-time, survived at t_NW 7.85 / CAGR 59.6%. (2) **BETA:
unconditional random LONG on any 15-min bar with the same 63-pt stop/trail/3-day hold earns +29.25
pts, exp_R 0.432** (random SHORT +13.57) on a sample where NIFTY went 8,294→23,714 (+186%). Against
matched-random entries, **7 of 8 formations are that wide trail in costume; only THREE_SOLDIERS adds
(+45.52 vs +26.81, p=0.000 ⇒ +18.7 pts incremental) = 41% of the headline, not 100%.**
**THE EMA/DMA ANSWER: the filters do NOT help** — held-out 2026 is +67.56 unfiltered vs **−44.06 with
the daily 10/20 DMA filter** (it inverts the result), +4.83 with 15-min 9/21. Retail band reached only
by the 1-session hold (13.0/mo, win 52.0%, RR 1.45). **STANDING RISK: this is a long-biased wide-trail
trend harvest with no bear segment in the data long enough to test it. Size as beta with a trend
overlay, not as market-neutral alpha.**

**Opening patterns: 0 of 75 survive; the 15-min U-shape actively LOSES.**
`OPENING_PATTERNS_20260730`, shapes built from 1-minute bars so a U inside the first candle is
resolvable. U_DOWN_UP_15m: −10.1 to −13.3 pts, win 32-37%, t_NW −2.00 to −3.09 across all five exits.
Best in family (inverted-U 30m) t_NW 1.23 against a 4.14 bar. Flipping it yields only +1.17 pts —
half the loss is cost. Best non-finding: narrow-OR then DOWNSIDE break, +9.94 pts, RR 1.54, improving
across eras (+8.07 → +18.50 → +41.38), but t_NW 2.60 at only 4.0 trades/month with 14 held-out
trades. Note the sign: downside opening breaks work, upside ones do not — opposite to the candle
result, consistent with a liquidity effect rather than drift.

**Indicator/levels debt DISCHARGED (the Principal had asked twice).** `INDICATOR_MINE_20260730`: only
**B2_vix_rv_divergence_LOW** cleared the t=3.8 Bonferroni bar at m=481 (+4.584 pts, t=4.029, placebo
p=0.000). `STRUCTURAL_EDGES_20260730`: **PCR predicts VOLATILITY (t = −8.9 to −13.2, clears placebo,
holdout sign matches) and NOT DIRECTION (t = 0.57-2.00, fails placebo)** — which independently
confirmed the Principal's ML thesis before he proposed it. **CRITICAL CAVEAT (`effect8`): PCR→vol t
was −13.48 pre-Oct-2024 and +0.09 post**; chain Herfindahl halved at the SEBI break (0.0558→0.0263,
KS p≈1e-178). Saty ATR Levels / Fibonacci / Elliott had NEVER been tested — now with a dedicated
agent; the measurable Saty core (`atr_consumed`, `dist_pc_atr`, `gap_atr`, `or30_atr`) went into the
regime ML and two landed top-5 for the vol head.

**Orthogonal alpha (agent, complete): one lead, sub-scale.** SHORT NIFTY intraday after extreme
overnight WTI crude crashes — n=229, +27.60 pts, 59.0% win, t=2.83, placebo p=0.008, **held-out 2026
LARGER (+81.6 pts, t=1.97)** — but **4.1 trades/month** and it misses its own 24-cell bar. Loosening
the threshold for frequency destroyed the held-out result (t 1.97→0.40) ⇒ genuinely confined to
extreme days. Forward-test candidate only. Everything else dead: SPX/VIX/USDINR/US10Y all t<1.4;
NIFTY-BANKNIFTY dispersion is momentum-not-reversion but ~1.3 pts against a 10-12 pt cost floor.
Breadth UNDERPOWERED-UNRESOLVED (PIT membership file ends Oct-2025). Highest-prior untested channel:
**same-morning Asian lead-lag (Nikkei/HSI)** — needs a D-009 data proposal.

**SHIPPED:** `04_RND_LAB/results/FINAL_RANKING_20260730/sleeve_performance.html` — all six sleeves +
portfolio, cumulative P&L with drawdown traces, OOS shading, colour-coded monthly heatmaps.

**OPEN / OWED:** weekly candle FORMATIONS as triggers (computed as columns, never tested — half of
that ask outstanding); catalogue `05_DATA_OFFICE/data/wti_crude_fred_daily.parquet` (D-009
spot-checked, not yet in DATA_CATALOG); 3 agents still running (master strategy table sorted by
Sharpe incl. rejected; TradingView indicators — `VORTEX|60min` t=4.071 with positive mean_net and low
concentration was never placebo-tested; price levels); and from earlier in the session: DSR/PBO at
634 trials, the SWING maxDD contradiction, and 2008/Black-Monday tail stress on daily data.

## 2026-07-28 (DESK-100) — Full audit found a CONFIRMED false-content bug already shipped; IPS page rebuilt v2 "best of both worlds"; PDF now on-request only
Two rounds today. **Round 1 (audit):** Principal asked for an 18%-cap on growth projection, the
biased MDD-scenario page removed, and a full redundant/safe/needs-changes audit + Haiku-vs-
Sonnet/Opus plan. 3 parallel Sonnet audits (D-023's cap respected, flagged since "many" were
asked for) covering ~47 modules found **`house_view_fit.py` was showing CONFIRMED FALSE CONTENT
to the Principal already** — a hardcoded "what the plan does" table claimed a foreign/gold sleeve
and 2 trims that don't exist in Anand Reddy's real data (100% cash, 0 trims). Fixed, plus ~15
more real bugs: an undisclosed hardcoded constant in `annex_mcap_migration.py`, a second flat-
rate anti-pattern in `annex_goal_mapping.py`, a hardcoded fake "Today" mix in `opportunity_set.py`,
a raw-jargon leak in `fund_actions.py`, dead crash-prone code in `funds_hybrid.py`, a backwards
`is_demo` default in 17 modules firm-wide, and crash-risk guards on 7 annexure modules for a
thin-equity/fund-heavy client. `annex_stress_scenarios.py` deleted outright (was only unwired
earlier the same day, not removed — caught mid-session). **Round 2 (IPS rebuild):** Principal
supplied a reference IPS image from another platform; `ips_summary.py` rebuilt v2 with much
richer coverage (single-scheme/AMC/locked-in/cash caps, market-cap bands, thematic/unlisted/
international-equity caps, fixed-income credit/duration, gold/silver bands) in our house visual
style, "Current" always computed live from real ctx (incl. a new look-through Equity/Debt split
blending direct equity + equity-oriented funds — Anand Reddy's real equity exposure is ~86% this
way, not the ~42% direct-only figure used elsewhere). IPS page UN-CUT (reverses yesterday's
removal — the old thin version was the problem, not the concept). `opportunity_set.py`'s
"Illustrative" mix now derives from real IPS targets when on file. Real finding: Single-scheme
concentration shows GAP at 17.9% — RELIANCE, already a Sell elsewhere in the deck, now with
quantitative IPS backing. **Gates: 78 slides, 0 crashes, 0/0 geometry, 0 tellscan, visual QA
throughout.** **New standing rule: PDF is no longer auto-generated — ask PPTX/PDF/both at the
end of each turn.** Full detail: SESSION_JOURNAL.md 2026-07-28 entries (both rounds). Ship:
`09_PRODUCT/reports/NDPMS_Portfolio_Review_AnandReddy_HNI_DEEP_DRAFT.pptx` (PDF not regenerated
this round). **OPEN:** Principal sign-off; book_scored/equity_book + fund_overlap/
scheme_overlap_full redundancy calls (flagged, not resolved); whether `deployment.py` should also
wire to real IPS bands; demo (ABXY) build couldn't be re-verified in this worktree (missing
untracked data file, pre-existing gap).

## 2026-07-27 (later still, DESK-100) — Principal feedback round: 5 PERMANENT template rules + tellscan.py + intake-workflow live
Principal reviewed the HNI_DEEP build below and issued a batch of corrections, all explicitly
permanent (applied to shared pr_template code, not just Anand Reddy). Rebuilt v10 = 78 slides,
0/0/0 gates. **(1)** Factor-fund rule reversed: factor ETFs default Hold now, except a named
Nifty 200 Momentum 30 fund which stays Sell (Anand Reddy: MOVALUE Sell→Hold, MOM30IETF stays
Sell). **(2)** 5 pages cut permanently (module stays in library, never renders by default):
ips_summary, group_concentration, cost, factor_profile, annex_currency_geo. **(3)**
"Redeem-to-Direct" now displays as "Switch" everywhere client-facing (internal code unchanged) —
flagged open risk: collides visually with the pre-existing different-meaning "Switch" verdict.
**(4)** scheme_overlap_full + growth_projection repositioned from Annexure into the main deck
(Fund Book / Recommendations sections respectively). **(5)** growth_projection's flat 12%/14%
assumption replaced with a real holdings-derived formula (EPS growth + fund CAGR + composition
volatility proxy) — zero LLM cost, same formula every build. **New:** `tellscan.py` — the
tell-scan is now a standing script (like check_geometry.py), not re-derived from memory each
session. **New (designed + partially wired into SKILL.md this session):** a Step-0 advisor
intake workflow — 2-4 questions, tier picker (Detailed/Medium/RM-Light mapped onto existing
presets), Recommended-vs-Customize checklist, parallel background research so wait time costs
nothing — full spec in `INTAKE_WORKFLOW_SPEC.md`, "Step 0" text merged live into SKILL.md.
Full detail: SESSION_JOURNAL.md 2026-07-27 (later still) entry. **OPEN:** Principal sign-off on
v10; the Switch/Redeem-to-Direct display collision; next-session candidates in
`TOKEN_TIME_OPTIMIZATION.md` (per-module render cache, diff-based visual QA) not yet built.

## 2026-07-27 (later, DESK-100) — Anand Reddy: complete HNI_DEEP tier built (82 slides), max-automation pass
Principal ask ("complete large deck, max automation, template use, haiku+sonnet split") went
beyond the RM_SIMPLE ship below to the full HNI_DEEP tier. Building the larger tier exercised
~57 modules vs RM_SIMPLE's 23 and surfaced real gaps the small tier never hit: 13 modules
crashed outright on missing real-data fields (fixed by wiring real pe/roe/growth/AMC/mcap-band
data two agents pulled from disk, plus honest "n/a"/graceful-degrade for stats that genuinely
don't exist yet — fund NAV history caps at 18 monthly points firm-wide, no IPS on file yet);
tell-scan found 151 internal-jargon hits (pf_qual/screener.in/analyst names/source citations) on
modules RM_SIMPLE never rendered, root-caused to `client_case` only being read by 2 of ~8
rationale-showing modules — fixed with a `_scrub_client_text()` function applied deck-wide; a
real accuracy bug (HDFC NIFTY 50 Index Fund showing a fabricated "0.0% CAGR" instead of "n/a"
for a fund whose 3y record was never independently benchmarked) caught only on the mandatory
visual QA pass, not any automated gate; 8 modules unconditionally printed "illustrative
synthetic book/demo" on 100% real client data (copy-pasted AZBY-demo language, never gated on
`is_demo`) — all fixed. **Gates: 82/82 render, 0/0 geometry x2, 0 tell-scan, visual QA on ~15
slides.** Ship: `09_PRODUCT/reports/NDPMS_Portfolio_Review_AnandReddy_HNI_DEEP_DRAFT.pptx/.pdf`
(DRAFT). Full detail: SESSION_JOURNAL.md 2026-07-27 (later) entry. **OPEN:** Principal sign-off;
whether the fund risk battery (Sortino/Calmar/drawdown) is worth a real daily-NAV pull for this
client (currently honest "n/a" — needs new data sourcing, not a code fix); the RM_SIMPLE entry's
still-open 10+-agent QA sweep + transfer-in-review DOCX apply here too.

## 2026-07-27 (DESK-100) — FIRST REAL CLIENT DECK: Anand Reddy NDPMS review built + shipped (RM_SIMPLE)
First real (non-demo) portfolio review, built from `Anand Reddy.xlsx` (~Rs1.61cr, 27 equity + 26 fund lines) through the pr_template engine. Same 750-scorecard/QFRA methodology applied one-time to 9 out-of-universe names (Principal ruling); MF funds outside QFRA-1/2 coverage got real 3y/1y-vs-benchmark research via analyst/quant-head agents. **CRITICAL FIX before ship:** `sell_list.py`/`fund_actions.py` were rendering raw internal audit text (analyst names, "pf_qual"/"QFRA" codenames, "Principal"/"CIO" refs) straight onto client slides via a summary-field fallback — caught on a tellscan-equivalent grep sweep, fixed by adding explicit client-safe `client_case` text for all 15 Sell names + rewriting 2 funds' structural_reason; internal audit trail kept only as source comments. Also added `is_demo` ctx flag (9 shared modules) so demo/ABXY language can never leak into a real deck, and a new `data_notes` module for holdings that don't fit a normal Sell/Hold call. Ship: `09_PRODUCT/pr_template/out/AnandReddy_RM_SIMPLE.pptx` (23 slides), 0/0 geometry gates, visual QA pass. **OPEN for Principal/RM:** (1) MF-sheet header stray value Rs 8,61,415.04 — unexplained, excluded not guessed; (2) HDFC Overnight Fund's current value is blank on statement, shown at value_inr=0; (3) SBI Gilt + HDFC Gilt = same-factor duplication, consolidation candidate; (4) whether a STANDARD/HNI_DEEP tier build is also wanted (RM_SIMPLE was a judgment call under time pressure, not yet confirmed as final). **NOT YET DONE this session** (ran out of time): the 10+-agent parallel QA sweep and the transfer-in-review DOCX — both still pending, do next session before this deck is considered client-ready to send. Full detail: SESSION_JOURNAL.md 2026-07-27 entry.

## 2026-07-26 (DESK-100, latest) — Principal dispositions on the open ledger; **read `NEXT_WEEK_QUEUE.md` before touching any of it**
Principal ruled/deferred across the full open list from the last session in one pass — nothing executed this turn except doc/skill sync (explicitly low-risk, no code behavior changes). **RULED:** PK=3 quadrant never-sells is CONFIRMED CORRECT, not a bug — firm's own backtest shows quadrant-3 mean-reversion + lower forward underperformance; do not "fix" to SELL on {3,4} (qfra1-rerun skill updated). **RELIANCE stays SELL** — Principal reconfirmed directly; ESCALATIONS_BOARD.md + ESCALATIONS_FOR_PRINCIPAL.md RELIANCE entries were stale (pre-recheck "Hold") and are now marked RESOLVED/SELL to match the ratified `pf_qual_RELIANCE.json`. **CLARIFIED:** FACTOR_NAVS.xlsx is correct as-is (price/PRI, a different purpose) — the TRI fix is scoped ONLY to the MF Dashboard's Indices sheet, queued for next week. **DEFERRED — see `01_COMMAND_CENTER/NEXT_WEEK_QUEUE.md` for full detail on all 11 items:** QFRA-2 Sell backtest, category-wise-BM-in-graph (code), TRI Indices rebuild, weekly stock-run bundle (router patch + pf_state re-seed + earnings feed — pushed to week of 08-10, "short of tokens"), a new young-fund Hold-vs-"No View" verdict spec (confirm before building), save_mf_recommendations polish, QFRA2_current.csv relocation, cross-category --verify, adapter/save walk-back unification, Sanjay Kulkarni + analyst-desk persona updates. **DO NOT execute any queued item ahead of its stated timing band.**

## 2026-07-26 (DESK-100, latest) — FUND SWAP SHIPPED (_v2 decks) + MF RECS SAVED + WEEKLY STOCK CADENCE LIVE
**Final CEO decks:** `09_PRODUCT/reports/NDPMS_Portfolio_Review_ABXY_HNI_v2.pptx/.pdf` (73) + `NDPMS_Portfolio_Review_ABXY_RM_Lite.pptx/.pdf` (18). Fund book per Principal: ICICI Pru Multi-Asset = Direct + Hold; LIC Flexi replaced by HDFC Flexi Cap (Direct, Hold); 4 actions / 5 holds; 3-agent verify's 9 findings all fixed; gates 0/0/0. Old `..._HNI.pptx` (no _v2) is STALE and PowerPoint-locked — close + delete it. **MF recommendations saved** (one-time, Principal): `03_RESEARCH_DESK/MF_RECOMMENDATIONS/saved_2026-07-26/` — all 6 categories BUY/SELL/HOLD + QFRA-2 join + young-fund flags + NFO scan; anchors large=2025-05-31/rest=2025-01-31 (true June-end needs dashboard NAV backfill Feb-2025→Jun-2026 — OPEN decision). **Cadence:** funds Apr/Oct only (next Oct-end 2026); STOCKS WEEKLY Thu 16:30 (→Fri→Mon) via run_weekly_v1.py — in OPERATING_CALENDAR.

## 2026-07-26 (DESK-100) — NDPMS: CEO SWEEP CLEARED, FINAL DECKS PUBLISHED (PPTX+PDF), pipeline complete
CEO-facing pair lives at `09_PRODUCT/reports/NDPMS_Portfolio_Review_ABXY_HNI.pptx/.pdf` (75) and `NDPMS_Portfolio_Review_ABXY_RM_Lite.pptx/.pdf` (18) — 3-agent zero-defect sweep's 11 findings all fixed (tax-slide scoping + STCG case bug, group-conc basis, RELIANCE driver/summary coherence, 5 data-QA language leaks, CoPilot CTA out, LIC BAF naming), all 4 decks re-gated 0/0/0. PDF pipeline live: user-local LibreOffice 26.2.5 + `09_PRODUCT/scripts/pptx_to_pdf.py`. New pipeline pieces: `client_intake.py` (CAS-extract → client_ctx.json + exceptions.csv; profile JSON with goals/holding-ages/family/meeting-history), `fund_ctx_adapter.py` (QFRA-1 live-wired; QFRA-2 covers only its 40 curated funds — held funds outside = flagged gap, no fabrication), `modules/since_last_review.py` (renders only with meeting history), Apr/Oct auto-build in OPERATING_CALENDAR (sign-off gated). ndpms-deck skill = full playbook. OPEN: Principal sign-off on the pair; NSDL CAS PDF parser needs a sample statement; QFRA-2 run for held funds.

## 2026-07-25 (DESK-100) — NDPMS v9 template: MF RECHECK-ALL done, ship set = _v4
Every demo fund claim now verified against real data (dashboard to 2025-01-31 + web for hybrids). Bandhan Small Cap (top fund: 3y rank 1/23, +7pp) removed as demo Sell → PGIM India Small Cap (real worst-in-category). LIC Large Cap: closet-index claim removed (r²=0.77), NEG_ALPHA kept (real −5pp/3y). LIC BAF: cushioning smear removed (fund is ahead of benchmark since launch) → Trim on scale/record (₹761cr AUM, <4y). Standing rule in TEMPLATE_V9_SPEC: demo Sell/Trim wears a real fund name only if the real record supports it. Ship: `out/ABXY_Family_{HNI_DEEP 79, STANDARD 39, RM_SIMPLE 29}_v4.pptx` + `NDPMS_TEMPLATE_MASTER_v4.pptx` (108); all gates green. v3 and older superseded.

## 2026-07-25 (DESK-100) — NDPMS v9 template: v7-RESTORATION PASS DONE, ship set = _v3
Principal's 5 corrections + design-degradation fix vs Kordes v7 PDF, all shipped: cost slide = scheme TER only (no drag/PMS "extra you pay"); NO Buy recommendation anywhere (opportunity-set mix now "Illustrative", proceeds PARK in cash); transition-plan slides (deployment/before_after) in ANNEXURE; slide-34 quality-vs-price rebuilt (P/E-outlier axis cap, selective labels); **clickable cross-refs live** (stock table rows → rationale pages, back-links, REF column on priority actions — 48 slide-jumps verified). Commentary-bias rule (lines lean with the call) saved into `/agentic-fund-manager` Steps 2+3. Chart lib de-degraded per pixel audit (no ax.legend() law, NAVY-primary rule, halo/caption/chip helpers, waterfall/dumbbell/histogram fixes, dpi 240). v7 devices restored: divider mini-TOC, Sell-count pill on header rule, client signature line. **DATA FIX: v2 book double-counted TATATECH (a Sell) — true book = 47 stocks, 9 Sell / 38 Hold (DIXON replaces the dup).** Gates: 0 findings both geometry checkers × 4 decks, 0 tells, 0 Buy-words. Ship: `pr_template/out/ABXY_Family_{HNI_DEEP 79, STANDARD 39, RM_SIMPLE 29}_v3.pptx` + `NDPMS_TEMPLATE_MASTER_v3.pptx` (108). v2/v1 outputs superseded — delete once the Principal closes them in PowerPoint. Design inventories + chart audit banked in session scratchpad (v7_inventory_p01_28.md / p29_56.md / v9_chart_audit.md).

## URGENT FLAG #2 (2026-07-18, DESK-100 broad-research sweep) — DO NOT ACT ON `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/EXECUTION_SHEET_V2.md`
This legacy (read-only) execution sheet's four strategies (IVRV_ShortStraddle, Earnings_ShortVol, FF_Calendar, Short_Strangle) are CONFIRMED to be the SAME as register rows S-01/S-02/S-03/S-04 — but the sheet was assembled 2026-07-04 03:46-03:55, AFTER the corrections that killed/downgraded them already existed on disk (03:24-03:29), and still shows their OLD, pre-correction rosy numbers:
- **FF_Calendar/S-03 — WORST: 37 rows, several sitting in the auto-recommended TRADE block** — the CIO CLOSED this 2026-07-05 as STAYS-KILLED (forward −9.30 pts, loses money 2024+2025). Do not trade any FF_Calendar row from this sheet.
- **Short_Strangle/S-04 — STAGE-GATE BYPASS**: register certifies S-04 to PAPER-WATCH ONLY (no live capital, "paper measures first") — but the sheet supplies ~190 of 209 TRADE-block rows with real margin sizing (₹3.05cr) as if cleared for live capital.
- Earnings_ShortVol/S-02: 54 stale rows, but confined to DISCRETIONARY tier (lower risk, human would need to independently choose to act).
- IVRV/S-01: 0 occurrences in the sheet — contained, no action needed.
Angel is confirmed data-only (no real fills found) — this is a planning-artifact risk, not evidence of an actual live trade, but per the firm's own "NO real-money trades ever" hard rule, this sheet must not be used to place ANY trade until it is rebuilt against the CURRENT register verdicts. Full evidence: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/FORWARDCHECK_REGISTER_CROSSCHECK.md`. See also DECISIONS_LOG.md D-038.

## URGENT FLAG #1 (2026-07-18, DESK-100 broad-research sweep) — S-05 "delta-hedged straddle" register claim UNVERIFIED, recommend FREEZE
Register row S-05 (`06_TRADING_DESK/STRATEGY_REGISTER.md`) carries "+5.9% CAGR, MaxDD 5%, 6/6 years positive" and its forward-test doc (`03_RESEARCH_DESK/forward_tests/S-05_forward.md`) is marked "paper-APPROVED, live NOW" — but that CAGR claim traces to ONE narrative sentence in `SESSION_JOURNAL.md:334`, with NO supporting script/CSV ever found. The forward-test's own signal log is EMPTY. A real-fill reconstruction of the same delta-hedged straddle family (`intraday_options_strategy/run_realfill_deltahedged.py`, unconditional/no filter) gives Sharpe **−0.83**, CAGR +1.3% — the opposite of the register's claim. **Recommend: do NOT build the missing automation / do not let this accrue forward-clock time until someone re-runs the real-fill script WITH its existing IV-gate filter + F1/F2 vetoes (~half-day job, all pieces already on disk) to reconcile.** Full detail: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/SHORTSTRADDLE_REGISTER_RECONCILIATION.md`. (Note: the FIRM'S ACTUAL LIVE naked-ATM-straddle strategy, S1-F, is unrelated to this concern — S1-F is real-fill validated, t=3.92, PF 1.79, n=259, and is NOT the strategy in question here.)
## WEEK PRIORITIES (set 2026-07-13 leaders meeting)
1. WS-4 Sonnet grid + blind grading + stats — Wed 07-15 (Arjun/desk; resume from ws4_battery/results/ws4run_20260713/PROGRESS.md) — **DONE, see 2026-07-16 entry below.**
2. ~~Publication pack (paper fill, charts LAST, style-lint, PDF + LinkedIn draft) — Sat 07-18~~ **CONTENT-COMPLETE 2026-07-16, ahead of schedule.** Both docs filled+linted+committed, 3 charts built, both docx outputs (full paper + LinkedIn attachment) assembled and image-verified. **Blocked on Principal review/spot-audit/arXiv decision — see 2026-07-16 entry. Nothing left for either desk to build here.**
3. Forward engines: S1-F Tue 09:12, S1-SX Thu 09:14; Tara reconcile + Ritika risk pack Fri 07-17. **S1F-001 14-Jul exit legs now logged** (see 2026-07-16 entry) — realized −₹5,767.
4. Cadence catch-up Tue: /macro-calendar, /pipeline-health, /find-skills
5. XBRL 2019-21 retry + D-009 gate Tue/Wed (Kavya; scripts in 05_DATA_OFFICE/scripts/)
BUDGET LAW THIS WEEK: Sonnet-only; graders haiku/second-account; org pool 25% floor is HARD.

## 2026-07-22→25 (DESK-100) — OBSIDIAN VAULT WORKING-LAYER built (portfolio DB + decision graph + EOD digest + templates)
The repo-as-vault now has a script-generated query layer. Open **HOME.md** at vault root. New surfaces: **PORTFOLIO_BOOK.base** (230 stock notes from pf_qual JSONs, 4 tabbed views — Holdings/Sells/Escalations/Full-universe); **01_COMMAND_CENTER/decisions/** (39 D-xxx notes; open any → Unlinked-mentions shows every file invoking it; ledger unchanged); **01_COMMAND_CENTER/daily/** (EOD digest, wired into EOD_ROUTINE); **templates/** (3). Generators in `05_DATA_OFFICE/scripts/{build_obsidian_book,build_decision_notes,obsidian_daily_digest}.py` — rerun on source change, generated trees never hand-edited. Fable-QA'd (6 auditors, 0 blockers; 3 minor fixed, 1 left = stale 360ONE narrative, an analyst re-score issue not a build issue). Full detail: SESSION_JOURNAL 2026-07-22→25 entry.

## 2026-07-25 (DESK-20) — PRIOR-ART CHECK: no NIFTY50 weekly/monthly options strategy meets 10% MDD / 30%+ CAGR yet
Principal ask: NIFTY 50 weekly+monthly options, managed daily/weekly, ~10% MDD / 30%+ CAGR — "find it." Two-agent /prior-art sweep: **nothing in the corpus clears both bars honestly.** Closest: **S1-F** (live paper, weekly 0DTE naked ATM straddle, real-fill t=3.92/PF1.79/n=259) at honest ~13-17% CAGR/~-5% MDD — Calmar ~2.6-3.4, same shape as the ask, just undersized. An in-sample S1-F config hits 28.8%/-9.9% (almost exactly the ask) but is **explicitly RETRACTED** by the firm's own quant desk (optimistic flat margin + ~150-cell in-sample tuning) — do not use it. Rest of the family (S-04 strangle near-breakeven, S-05 frozen/unverified, K-012 FF calendar killed, OPT-SWEEP-50's 4 marginal survivors, KIRU 0DTE SL-30 package at 1.7-3.1%/yr unlevered) all fall short or were never CAGR/MDD-scored — two prior dedicated hunts (OPT-SWEEP-50 07-07, KIRU 07-13) already came up empty in this exact instrument. KNOWLEDGE_BASE lesson 24 ceiling: realistic sustained NIFTY VRP-selling ~15-25% CAGR/Sharpe 0.9-1.2. **Recommended next step (Principal to choose): leverage/sizing-feasibility test on S1-F (~2x notional — does Calmar hold or does tail risk scale worse-than-linear), gated by Sameer+Tara+red-team.** Full detail + file citations: SESSION_JOURNAL.md 2026-07-25 entry.

### SAME-SESSION CONTINUATION (2026-07-25, DESK-20) — 3 strategies TESTED AND KILLED, engine audited, S1-F figure revised DOWN
Principal ran an open mandate this session (1DTE → MFT levels → new strategies from scratch → "just high sharpe"). Four verdicts, all pre-registered before their tests, all banked with scripts+data:
1. **1DTE — DOMINATED** (`results/DTE_1DTE_BACKTEST_20260725/`). Both entries tested. D−1-close: 4.16% CAGR / −16.86% MDD / Calmar 0.25, t=1.05. D−1-open: same return as 0DTE (12.51%) at **2.3x the drawdown** (−12.40%). 0DTE control reproduced the +10.73/t=3.92/PF1.79 headline exactly. Mechanism = overnight gap tail: 5.4% of nights gap THROUGH the 30% stop; worst 1DTE night −487 pts vs 0DTE's −104, incl. −201 on 2022-02-24 (Ukraine gap) which 0DTE never saw. **1DTE hands you 0DTE's crisis drawdown as your everyday drawdown.** No register row.
2. **MFT (multi-timeframe swing levels, 5/15-min) — KILLED** (`ideas/20260725_MFT_multitimeframe_levels.md`). n=4,896 touches over 10.4yrs, 100 placebos: expansion percentile **6**, reversion percentile **1** — both ~2sd BELOW random nearby prices; needed ≥90. Levels are marginally DULLER than arbitrary prices. **Banked positive finding: real levels get touched +41% more often than placebos (4,896 vs 3,472) — price is genuinely attracted to them, but attraction ≠ prediction.** No re-cutting; resurrection only via a mechanistically different level construction (volume-at-price / OI-derived).
3. **NS-1 (overnight theta via low-gamma strangle) — KILLED all 5 strike distances** (`ideas/20260725_NEW_STRATEGY_GENESIS.md`). Worst night 242–550x mean nightly gain (bar 3x); t=0.30–0.72. **Costs eat 55–84% of gross**; annualised 1–2.3% on margin. Zero-volume legs 0.0%, so this is economics not data. **Retires the whole "harvest the overnight" family** unless a design collects >>5 pts or uses <4 fills.
4. **ENGINE AUDIT after Principal challenged correctness — headline SURVIVES but is ~10% optimistic.** SL detected on 1-min CLOSE not HIGH costs **−1.03 pts/day (−9.6%)**: **+10.73 → +9.71, spec-true CAGR ≈11.4% not 12.57%.** Fill realism CLEAN (zero-volume 0.0%/0.2%, median volume 2.64M). Red-team found a real-but-immaterial margin lookahead (0.01pp) and an STT double-charge (conservative, biases DOWN). Autocorrelation, selection bias and partial-year flattery all REFUTED (NW t rises to 4.64; bootstrap 5th pctile +6.81).
**THE ONE UNRESOLVED, HIGHEST-CONSEQUENCE ITEM: DSR/PBO on S1-F's ~150 in-sample design cells.** Its Sharpe 2.15 sits ABOVE the firm's own documented NIFTY VRP ceiling of 0.9–1.2 (KNOWLEDGE_BASE lesson 24) — so either 0DTE+SL+filters is genuinely a different animal, or selection is inflating it. Bonferroni at m=150 needs |t|≈3.60 vs headline 3.92: clears, but not comfortably. **This single test decides whether the firm's best strategy is real.** Owner: Sameer Bhat. Also owed: exact revised CAGR/MDD re-run with high-triggered SL; rebuild the badly-constructed exit-vs-intrinsic test; volume-across-ALL-bars forward-fill check (bar density was a suspicious 366/366 on 100% of days).
**STILL OPEN, NOT YET TESTED (pre-registered in the genesis doc):** NS-2 NIFTY-vs-SENSEX vol relative value (the only genuinely factor-diversifying candidate; blocked on the SENSEX D-009), NS-3 NIFTY/BANKNIFTY implied-correlation reversion, NS-4 gold/equity tilt vs the banked 50/50 (OOS-split kill pre-registered). **Recommended next: the S1-F DSR run, then the iron-fly (defined-risk) conversion of S1-F — the only honest route to the Principal's 10% MDD, since the tail not the return is his binding constraint.**

### ↑ CORRECTED SAME DAY by Principal-ordered recheck of S-02/S-04/S1-F (primary-artifact trace, not register prose). Three corrections to the block above:
1. **S-02 and S-04 are SINGLE-STOCK options books (200+ tickers), NOT NIFTY 50 index** — verified from their configs (S-02 lineage `stock_earnings_vol.parquet`; S-04 `shortlist_shortvol.parquet`, 207-209 symbols, 5% OTM CE+PE, 14-DTE, buy-back at 50% credit). Listing them in the index-options family above was wrong. **Neither is on-mandate for an index-options ask at all.** S-04's register line "Weekly: Tara" = TCA review cadence, not a trade rule.
2. **S1-F honest figure is 13.4% CAGR / -4.4% MDD, not "13-17%/-5%".** The 13% anchor is REAL and reproduces — Tara re-executed `s1f_dynmargin_graph.py` (dynamic margin spot×75×0.15) and got `CAGR 13.4% | maxDD -4.4%`, matching spec + commit e3cdc56. **The 17% upper bound is PROSE-ONLY** — no script computes dyn-margin CAGR for the S1b/V2 variants that would justify it. Do not quote 17% as computed. The retracted 28.8%/-9.9% is confirmed as flat-₹1.1L hardcoded (`s1f_final_graph.py:36`). Corrected margin IS in code (incl. the live runner) — not a prose-only conclusion; the live S1F-001 ticket sized 2 lots per the corrected model (flat margin would have given 6), so the runner was hardened before go-live.
3. **S1-F structurally does NOT match the mandate**: NIFTY 50 index yes, but weekly-expiry 0DTE ONLY (no monthly tenor leg exists; month-closing expiries are traded identically), strict intraday 09:20 entry → 15:25 flat, "No re-entry". Never multi-day-managed. Distance to "weekly+monthly managed daily/weekly" is structural, not a tuning gap.
**TWO DEFECTS SURFACED (both now spawned as tasks):** (a) **S1-F forward clock is silently not accruing** — `06_TRADING_DESK/paper/s1f_paper_log.csv` has n=1 row ever (07-14, −₹5,767); the **07-21 Tuesday expiry never fired and logged no GO/SKIP row** (spec requires logging even on SKIP), file untouched since 07-15 — probable session-bound cron lapse. AND the log is **gitignored** (`.gitignore:38`), so a D-030-frozen forward test has no committed audit trail. (b) **S-04 has two on-disk artifacts that disagree**: `metrics_clean.json` "2024_25_mean_pct": 0.2058 vs `subsamples.csv` 2024 0.162 / 2025 0.081 (pool ≈0.11). Unresolved — needs quant adjudication before S-04 is sized. Also confirmed: S-04 has NO equity curve anywhere, so its CAGR/MDD would require a new overlap-aware portfolio backtest under the ₹1cr book cap; and its "managed-exit fill optimism" caveat is specifically that EOD close stands in for a live resting buy-back order (~5% zero-volume entry days; exit-leg volume not captured in the data at all).

## 2026-07-21 (DESK-100) — FULL NIFTY-750 QUANT RE-SCORE (TTM v7) + SCREENER REFRESH 500→750 (D-039)
Principal: "fix scores of all nifty 750" + "amend score to TTM" (Q1 FY27 landing). EXECUTED the full-750 run (was "method frozen, not started"). **`results/full750_scored.csv` = 751 names scored, 505 Hold / 246 Sell, coverage High 715/Med 34/Low 2** — now the single quant-truth source for the scorecard book.
- Screener refreshed 500→750 names + NEW `datasets/screener_deep/screener_quarterly_results.parquet` (through Jun-2026=Q1 FY27). Scraper rehomed to SOP contract (`05_DATA_OFFICE/scripts/scrape_screener_750.py`) + **stale-data landmine fixed** (dead legacy consolidated series → now picks most-recent variant; COLPAL/TATAELXSI/AUBANK verified current).
- **TTM amendment v7**: revenue_growth_1y→TTM YoY, PE→TTM-EPS (TTM-preferred, annual-fallback); rest of frozen engine unchanged. **AMENDS frozen v6.3 → needs Arjun+Nikhil sign-off before permanent; breaks V0 comparability.** Known gap: 12 Dec-FY names (ABB/SIEMENS/CRISIL/VBL) NaN fundamentals (engine Mar-only) → Med/Low flag protects them.
- CADENCE (Principal): each SUNDAY delta-scrape reporters + refresh commentary (token-efficient), not full re-pull.
- DEFERRED (low tokens, next session): top-250 research workflow (100 names, ~17+ saved, resumable) + top-250 V1 book build; wire the Sunday job. Resume state: `STOCK_SCORECARD_750/results/PROGRESS_750_QUANT_FIX.md`. Scripts: scrape_screener_750 / promote_screener_staging / build_full750_quant (all in 05_DATA_OFFICE/scripts/).

## 2026-07-20 (DESK-100) — NIFTY-100 COVERAGE: RESEARCH LAYER COMPLETE (66 new + 59 held = 125 files), QA'D; QUANT EXTENSION OPEN
Principal-ordered N100 build DONE at the research layer: official constituents fetched (datasets/index_constituents/, cataloged), 34 overlap names skipped (no-redo), **66 new names researched + QA'd + fixed: 27 Sell / 39 Hold, 4 new escalations (ADANIENSOL, BAJAJHLDNG + GRASIM holdco methodology gaps, DRREDDY coin-flip), 19 names growth<10%**. All saved as results/pf_qual_*.json + N100_RESEARCH_SUMMARY.csv. QA pass: Adani-DOJ overstatement corrected in 3 files (pending motion ≠ granted), Buy/TP language scrubbed (5 files), 3 growth numbers analyst-revised DOWN a band (ADANIGREEN 20→12, POWERGRID 11→7, INDIGO 13→9). Analyst Excel: empty technical columns now auto-hidden. Screener SOP refresh ledger fixed (next ~25-Aug; delta scope = holdings + N100). **OPEN (resume list in PROGRESS_PORTFOLIO_HOLDINGS.md §SESSION CLOSE): quant rows for 43/66 names (agent killed pre-save, task fully open, spec preserved) → 125-name analyst Excel rebuild; 36 total escalations awaiting Principal; canonical Excel convergence; Q1 prints 21-31 Jul watch list.**

## 2026-07-19 (DESK-100) — SCORECARD CLIENT LAYER v6.3: ANALYTICS ENGINE + DASHBOARD + PREMIUM THEME SHIPPED
Principal orders (18th evening) executed: NEW frozen pre-build step `09_PRODUCT/scripts/compute_portfolio_analytics.py` (sim backcast of today's mix vs Nifty-50-TRI-proxy: 3y CAGR 19.1% vs 8.7%, beta 1.04, alpha 9.9%/y, Sharpe 0.81 vs 0.21, maxDD -17.3%; 4-factor reg R2 .90, SIZE +0.34; PE pctiles N50 10th/Mid150 32nd/Small250 59th; outputs pf_analytics.json+series+corr). **Client workbook now v4**: At-a-Glance DASHBOARD (KPI cards + growth-of-100 chart), NEW Portfolio Analytics sheet (plain-words tables + top-15 corr heatmap + assumptions incl selection-bias honesty line), client premium theme (ionic_style C_* deep-blue palette, Principal-supplied; internal books keep house navy/gold), inline zero-tell HARD gate, and the approved mid/small VIEW line (Large≥90% trigger, never a Buy). Analyst book + "Portfolio Analytics (Full)" sheet (factor t-stats, [ESTIMATE] fwd-alpha). **Shipped as `CLIENT_RECOMMENDATIONS_v4.xlsx` + `ANALYST_RECOMMENDATIONS_v2.xlsx` (canonical names file-locked in Principal's open Excel — converge: close Excel, rerun both builders, delete _v2/_v3/_v4 spares).** FROZEN_METHODOLOGY.md -> v6.3. Parked for Principal: Option B "Add" layer (mid/small names) pending 750 run + ruling; mcap-mix module for the FM skill.

## 2026-07-18 (DESK-100, late) — SCORECARD PRODUCTION CHAIN FROZEN (v6) + IONIC WEALTH CLIENT LAYER LIVE
Principal rulings executed same-day: **client layer frozen** — Ionic Score (0.6×3Y+0.4×1Y + forward-growth/conviction adj ±10), **Sell/Trim/Hold** two-gate (Trim band 40-50 for >2.5% positions; concentration guidance not hard caps), Ionic Wealth 2-sheet client workbook (Recommendations + Before-vs-After). FROZEN artifacts: `STOCK_SCORECARD_750/SCRAPING_SOP.md`, `FROZEN_METHODOLOGY.md` v6, `ANALYST_KIT/SKILL.md` (portable, ships w/ analyst Excel), `.claude/skills/agentic-fund-manager/`. Live 59-book run through the new pipeline: **CLIENT_RECOMMENDATIONS.xlsx v3 shipped** — 11 Sell / 3 Trim (LT 12.97->8%, HINDUNILVR 7.76->6%, TCS 2.8->2%) / 45 Hold, freed 12.47%, book Ionic 51.7->52.9. FM actions: `results/pf_fm_actions.json` (Sanjay). **750-universe research: METHOD FROZEN, RUN NOT STARTED — explicit Principal go required.** Awaiting Principal: v3 workbook sign-off, 32 escalations, 750 go, Manoj to rehome the Screener scraper to SOP contract.

## 2026-07-18 (DESK-100) — PORTFOLIO HOLDINGS QUAL SCORING: ALL 59 DONE — 48 Hold / 11 Sell / 32 escalations awaiting Principal
The real-NDPMS holdings review (STOCK_SCORECARD_750 priority task) is COMPLETE: 51 stocks this session (5x10-parallel Sonnet batches + 1, Principal-authorized 10-parallel), sector-analyst personas, one agent per stock, all 59 `pf_qual_*.json` on disk + schema-validated. **Sells (11): TATAPOWER, POWERINDIA, JIOFIN, DEEPAKNTR, ASIANPAINT, POONAWALLA, BHEL, COCHINSHIP, HINDCOPPER, TATATECH, ANANDRATHI.** Consolidated: `04_RND_LAB/STOCK_SCORECARD_750/results/PORTFOLIO_QUAL_SUMMARY.csv` + `ESCALATIONS_FOR_PRINCIPAL.md` (32 cases verbatim, by position size). **AWAITING PRINCIPAL: adjudicate the 32 escalations** — biggest: RELIANCE (Hold vs quant Sell, hinges on H2-2026 Jio IPO), SUNPHARMA (pending $11.75bn Organon debt), PERSISTENT (all-debt Nagarro, ICRA watch-negative), TMCV (EUR3.8bn Iveco), plus 3 METHODOLOGY gaps to fix before the 750 rollout (demerger PE-blend, DTA-inflated PAT, captive-NBFC ROCE). **Step-4 deliverables BUILT:** `results/PORTFOLIO_RECOMMENDATIONS.xlsx` (4 sheets) + `09_PRODUCT/reports/PORTFOLIO_HOLDINGS_REVIEW_2026-07-18.docx` (builder: `09_PRODUCT/scripts/build_portfolio_recommendations.py`). Book split Rs 264.9L: Hold-clean 193.4L (26) / Hold-escalated 58.5L (22) / Sell 13.1L (11); no Sell in top-15 positions. Eight knife-edge names have Q1 prints 21–31 Jul (BANDHANBNK 21st, IDFCFIRSTB 25th, SUMICHEM 27th, BAJAJHFL 29-30th, MARUTI 31st, plus ITC/VBL/TMPV). Full detail: SESSION_JOURNAL top entry + PROGRESS_PORTFOLIO_HOLDINGS.md.

## 2026-07-18 (DESK-100) — ALPHA_RANKER SCORECARD RESET DONE + firm-methodology research night (R1-R9) + MASTER_ROADMAP_2036 — full detail in SESSION_JOURNAL top entry
Fable retired (org spend cap) → switched to Opus for review/blueprint/synthesis roles per Principal. Built + assembled + determinism-verified the two-scorecard reset: **1M relative = REAL** (usable); 1Y/5Y relative = FRAGILE-but-usable (thin-n disclosed, not gating); **entire ABSOLUTE scorecard NOT usable yet** (1M = FAKE/hard-gate KILL + math defect; 1Y/5Y = FRAGILE, weak/inverted calibration). Principal's evaluation-philosophy correction recorded (memory item #8: no fixed Calmar/Sharpe/BM bar — judge on consistency/accuracy/monotonicity + log-scale-intensity score-bucket calibration). **Diagnosed (R8) the 5Y inverted-U as a REAL effect**: the growth_longevity leg mistakes cyclical/commodity earnings peaks for durable growth — fix cheap-tested (R9), needs Principal/CIO ruling (blueprint locks the leg list). Caught+corrected an `earnings_confirm_v2` naming bug (R4: it's a fundamental confirmation flag, not a price-reaction surprise signal). Separately ran a 4hr firm-methodology research mandate → `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/` (10 legendary managers' playbooks, PMS/AIF/MF extension, cycles/regimes honesty-gated, techno-funda, AI future-edge). **HEADLINE FINDING (7 independent workstreams converged): ALPHA_RANKER has no exit/deceleration trigger** — spec'd (R7, 4-leg) + build started (B1) as `rnd/scorecard/exit_trigger_flags.parquet`, a separate overlay never blended into the scores. R6 (opus CIO-synthesis) named this "the round-trip gap" as the night's throughline in `MASTER_ROADMAP_2036.md` and gave a standing decision rule for when multi-agent fan-out is worth its cost vs a single call. **PENDING PRINCIPAL:** S3 growth-longevity leg ruling; pre-2017 quality_cfo_pat data-ask; whether to greenlight the R9 dampening fix as v2. Not committed to git.

## 2026-07-17 — NEW BUILD: STOCK_SCORECARD_750 (quantamental Nifty-750 scorer, DESK-100) — spec+plan done, Gate-3 cheap-test PASSED-NOT-KILLED, dual-horizon finalized, first real 25-stock sample delivered
Full cycle this session: brainstorm -> `MASTER_PLAN.md` (8 pillars: Quality/Growth/Value-Relative/DCF/Stage-Technical/Sector-Macro/Ownership-Flow/Accumulation + 2 overlay gates + regime tilt) -> `IMPLEMENTATION_PLAN.md` (12 TDD tasks) -> **2 independent reviews (data-quality + ops-robustness) caught that every loader's assumed schema was wrong vs the real ALPHA_RANKER/firm data files** (verified directly, not assumed) -> plan rewritten against real schemas (new `derived_ratios.py` design: raw Screener line items -> ROE/ROCE/PE/etc, since none are pre-computed).
**Gate-3 cheap-test (proper RESEARCH_SOP process — one-pager filed at `04_RND_LAB/ideas/20260717_stock_scorecard_750_forward_return_predictor.md`, pre-registered kill criteria BEFORE touching data):** Quality+Value 2-pillar stand-in vs 12M fwd returns, 47 monthly formations 2021-08→2025-06. Quintile spread +4.65pp, monotonic, **100th-percentile vs a randomized-score placebo (hard gate PASSED)** — but Newey-West t only 1.14 and **the entire edge is one 16-month 2022-23 India value/midcap regime**; ex that window the spread is negative and the last ~21 months are negative too. Per pre-registered rule (don't kill on weak t alone if placebo-clearing): **verdict = NOT KILLED, forward-test candidate**, not a strong endorsement. `IDEA_PIPELINE.md` board row updated to Gate-3-passed with the full caveat.
**Dual-horizon methodology finalized** (Principal ask): every stock now gets TWO independent scores — 3Y (fundamentals-tilted 63/37) and 1Y (technical-tilted, shorter windows, 40/60) — plus a locked 5-paragraph standardized commentary schema (`final_note`, `three_year_positive/negative`, `one_year_positive/negative`) for the future Phase-2 qualitative-research-agent layer (not built yet).
**First real sample delivered:** 25 random stocks (seed 20260717) scored against a 300-stock reference universe (3 parallel agents computed raw metrics on real data, DCF excluded from this quick pass, weights renormalized) → `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/STOCK_SCORECARD_750_sample25.xlsx` (Summary/3Y-Detail/1Y-Detail/Methodology sheets).
**Data-quality flags for Kavya (not yet resolved):** ownership-flow data (`shareholding_changes.parquet`) has zero coverage for 2 established names (LTM, JSWDULUX) despite full price history — looks like a symbol-mapping gap, not a genuine disclosure gap. `nse_symbol` join-key match-rate vs `key_symbol` still needs a formal D-009 check before the full 750-build trusts it blindly.
**Open before the full 750 build:** locate a real NIFTY index-level PE/PB time series (regime tilt is wired but inert/"Neutral" without it), re-add DCF pillar (excluded from this sample for speed), source promoter pledge % from elsewhere, run the full 12-task IMPLEMENTATION_PLAN.md build once Principal green-lights it. Nothing committed to git yet (not requested).

## 2026-07-16 EOD FLAG (DESK-100) — capture 15:45 INCOMPLETE, backup will heal
AngelDailyOptionCapture 15:45 run terminated (LastTaskResult 0xC000013A) at ~16:04 after only ~9/210 names (alphabetical, through ADANIGREEN; 17 parquets written, data current/max-ts today). Root cause: ~16:00–17:38 Angel connectivity outage (apiconnect read-timeouts; recovered ~17:38). **Non-expiry day for NSE F&O (expiries 07-28/08-25) → no contract-purge risk;** 20:00/23:00 idempotent backups pending and expected to complete the full 210-name snapshot — VERIFY the 20:00 backup wrote ~210 names. Index-close append (19:30) not yet due (index_daily max=07-15). Persistent flag unchanged: `datasets/earnings_pit/forthcoming_results.csv` still MISSING (Kavya) → earnings freshness ping impossible. 23 Angel OHLCV stragglers still queued.

## 2026-07-16 DATA LANDMINE (DESK-100, urgent → Kavya) — price panel DELISTED corruption
AMF Pine backtest surfaced a REAL corruption in `datasets/derived/pit_union_panel_v1/close_panel_price.parquet`: the `source=="DELISTED"` segment alternates day-to-day between TWO price scales for some 2020-era small/mid names (~981 corrupted (symbol,date) prints, 44 in N500 window; e.g. MAGMA 17.60↔1000.00 → fabricated +5,581% trade). It faked AMF's raw 49-53% CAGR (real ≈7%, loses to buy-hold). **EARN_MOM_SWEEP verified CLEAN (0 contamination — gates on liquid N500 PIT).** ACTION (Kavya): quarantine/patch the DELISTED two-scale prints before this panel is used in ANY other backtest — it will fabricate spurious results on any 2020-era delisted small/mid name. Detector + cleaned rerun in `04_RND_LAB/results/AMF_PINE_BT_20260716/clean_rerun.py`. Candidate new CLAUDE.md landmine #10 once patched.

## 2026-07-16 (night) — NEW VENTURE: XORLOG (root folder `Xorlog/`, separate from firm)
Principal-ordered startup project: India retail invest/trade platform (F&O journal + screener + BYOK AI research + honest backtester + execution helper). **v1.2 RESEARCH+PLAN NOW COMPLETE** (2026-07-16, DESK-20): 6 research files (added china_comparables + zero_cost_growth_tactics after 2 session-restart recoveries), 00_VISION_AND_PLAN, 02_FEATURE_BACKLOG (§A-H incl. new §G China-mined features), 04_DISTRIBUTION_ZERO_COST v1.0 (LinkedIn-23k conversion sequence + 12-week ₹0 calendar). Read `Xorlog/PROGRESS.md` first. Key rulings baked in: NO unlicensed advice (RA entity Phase 2; Dec-2024 amendment sweeps model-portfolio showcases), MVP wedge = F&O journal on free broker APIs, stack = Cloudflare+Supabase (~₹500-1.4k/mo). **Next = DESK-100's T1-T5 build queue (`Xorlog/HANDOFF_DESK100.md`).** Awaiting Principal: RA route (employment NOC issue), incorporation, name check, lawyer budget.

## 2026-07-16 (even later, DESK-100) — IC-memo Round-1 fan-out cheap-test: NO CHANGE, tested not assumed
Principal asked whether high token cost means switching the whole research flow to single-LLM calls. Ran a pre-registered n=2 cheap-test (Round-1's 3-persona fan-out vs 1 consolidated call, on 2 real pipeline ideas) rather than extending the WS-4 finding by assumption — WS-4 only tested sequential same-task re-verification (which lost), not parallel fan-out across different expertise domains. **Result: fan-out is NOT shown wasteful — 1 sample was a wash, 1 sample the fan-out clearly won (caught a real liquidity-drop-rule survivorship hazard the consolidated call missed entirely, invisible to DSR/PBO).** Cost ~3x consolidated (not 4.5x — parallel skips the sequential context-accumulation tax). **Round-1 stays as-is, no roster/skill change** — the opposite conclusion from D-036's Red Team move, on purpose. Full protocol + raw outputs + sealed grading in `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ic_memo_cheaptest/`.

## 2026-07-16 (later, DESK-100) — D-036: Red Team moved to Sonnet; rest of firm structure held as-is
**Principal order "upgrade our amc completely feel free to make all changes," acting on the WS-4 dashboard.** Re-checked the original 3-point pitch against the real files before executing — found it overshot on 2 of 3 points:
- Sameer Bhat (Overfit) + Farhan Qureshi (Compliance) were **already** Sonnet-primary — no change made.
- Gate-4/Gate-5 (RESEARCH_SOP.md) were **already** lean, separate gates, not a bloated chain — deliberately **not** collapsed into one pass; that would trade away the independent-sign-off/audit-trail property the benchmark's defect-count metric can't see.
- The one real gap: **Nikhil Bose (Red Team) Opus 4.8 → Sonnet 5 primary** (Opus kept as escalation-only). This is D-036, live immediately (CEO/CIO ratify at next board, D-025 precedent). No agents deleted, no other roster changes.
Files: CLAUDE.md, MODEL_ASSIGNMENTS.md, EVOLUTION_LOG.md, DECISIONS_LOG.md, RESEARCH_SOP.md, `.claude/agents/red-team-nikhil-bose.md`, `.claude/skills/red-team/SKILL.md`, `.claude/skills/ic-memo/SKILL.md`. Full reasoning: SESSION_JOURNAL 2026-07-16 (later) entry. **Watch item:** confirm Red Team's kill-rate/verdict quality holds on Sonnet over the next few live reviews.

## 2026-07-16 (DESK-100) — WS-4 publication pack CONTENT-COMPLETE; awaiting Principal
- **Primary study (pre-registered, blind-graded): bar NOT MET.** Opus-base A/B/C/C2 = 15/16, 16/16, 14/16, 14/16 — the firm's multi-agent pipeline did not beat a single LLM call on this battery, and cost ~4.5x the tokens. Disclosed honestly in the paper (§7 ethics commitment); NOT the public lead.
- **Public lead = two clean, non-fabricated wins** (Principal ruling 2026-07-15, "lead with clean wins"): (1) Sonnet 5 ties Fable 5 at 15/16 defects for ~1/10th the cost, Opus 4.8 is neither cheapest nor most accurate; (2) measured LLM-judge self-preference, quantified via neutral re-grade (Haiku-judge +1.00 to Haiku, Opus-judge +0.50 to Opus, leave-one-out corrected) — caught by accident while sanity-checking a ranking that looked wrong, now a standalone methodological finding.
- **Built this session:** paper draft fully filled (`09_PRODUCT/reports/SYSTEM_VS_LLM_PAPER_DRAFT.md`, §5.1-5.6 + limitations disclosing 2 real bugs found during grading), LinkedIn post v3 (`LINKEDIN_POST_DRAFT.md`, cost/accuracy+bias hook, system test = one soft non-claim line), both style-lint clean, 3 charts (`build_ws4_charts.py`), full paper docx (`build_ws4_paper_docx.py` → gitignored `.docx`, 8 tables + 3 charts, image-count-verified on readback after catching a first-build silent-failure bug), shorter LinkedIn-attachment docx (`build_ws4_linkedin_attachment.py` → gitignored `.docx`, exec summary + charts 1-2 ONLY, chart 3/negative-result deliberately excluded).
- **Awaiting Principal (cannot resolve myself):** (a) arXiv vs. internal-only publication decision; (b) his own ~20min grade spot-audit (`[pending author audit]` markers in the paper, esp. FP-on-clean-controls + the two grading-noise/self-preference findings); (c) sign-off that the paper (full disclosure) vs. LinkedIn (clean-wins emphasis) split, as scoped in the paper's header, matches his intent.
- Full detail, all files touched, and the S1F-001 exit-log side-item: SESSION_JOURNAL 2026-07-16 entry.

## 2026-07-15 (DESK-20) — BRAND DESK created (10_BRAND_DESK/), spec-now-build-later
- **New folder `10_BRAND_DESK/`** governs Shreyas's PUBLIC personal-brand writing (LinkedIn + Substack). Goal: reputation as a future capital allocator, built on his OWN models + a timestamped auditable track record. `BRAND_CHARTER.md` = its constitution.
- **Verified live profile (logged-in read):** linkedin.com/in/guptashreyas089, ~22,986 followers; existing quantamental lane; best format = document-backed market thesis. This is a re-launch/systematization, not a cold start.
- **Cadence:** LinkedIn Sun 17:00 IST, ≥2 substantive posts/mo across platforms, rolling 4-draft buffer, 1-2yr flexible roadmap. **STARTS NEXT MONTH (2026-08);** this week's Sunday item is still the AMC SYSTEM_VS_LLM post (own frozen PUBLICATION_PLAN rules, predates the desk).
- **Hard rules:** no stock calls (SEBI RA/IA), no Ionic client/AUM/strategy/PII/P&L, "Ionic colleagues must be OK seeing it" test, varied disclaimers, every falsifiable claim pre-registered+committed to `PUBLIC_TRACK_RECORD.md`, must sound like Shreyas not AI (`/style-lint` gate), Shreyas posts manually + final proofread — system delivers TEXT only, never auto-posts.
- **DEFERRED to a Fable-token session (Shreyas builds):** `brand-desk-lead` agent + `/brand-compliance-check`, `/brand-post`, `/track-record-review` skills — spec'd in `10_BRAND_DESK/NEW_AGENTS_SPEC.md`. Until built, pipeline runs via existing agents (rnd-head/librarian/macro/compliance-farhan/red-team/product-head) manually invoked.

**As of: 2026-07-13 (loop day), by DESK-100 — 10 cards/rulings adjudicated, 2 new landmines, wave-B closed, trials 249; prior states below still current**

## 2026-07-13 (late, DESK-20) — KIRU package adjudicated (Principal-ordered external-spec test)
- **Rotation (BeES ratio-Donchian) → K-016 NOT ADOPTED** (execution-bar illusion: same-bar 29.4% vs honest 9.8% CAGR; whipsaw drag 3.16pp/yr). **Banked: 50/50 monthly-rebal NIFTY-gold dominates (12.3%/10.5%vol/−21.5%DD, 2013-26 real ETFs) → Devika owns the strategic-gold-sleeve one-pager (K-011's unclaimed hypothesis now has evidence).**
- **0DTE SL-30 straddle: bars pass, edge +1.7%/yr notional unlevered** (podcast's 12% ⇒ ~7× leverage); SL-30 tail-cut is real; ≥0.45% filter dominates (3rd confirmation) → Vikram variant note vs S1-F, no register row. Combined "30%/yr" claim NOT REPRODUCED (honest 11.5-18.6%).
- NEW DATA: `etf_gold_silver/niftybees_daily.parquet` (2013-26) + `goldbees_daily_ext.parquet` (2013-26) — Kavya D-009 formalization pending. Trials +12 (ledger regen pending → ~261). Full: `results/KIRU_PKG/20260713/SUMMARY.md`.
- WS-4 Fable arms [HISTORICAL, superseded]: account-2 banked 6 armB cells 07-13 night before its spend limit; later sessions completed all arms + grading (see 07-16 entries — program COMPLETE, pack awaits Principal). KIRU 15:25-exec addendum: K-016 stands (15:25 execution = the 12.44%/−25.3%DD variant, not 29.4%).

## 2026-07-13 LOOP-DAY CONSOLIDATION (read this before starting new research)
- **Verdicts today (all pre-registered, freeze-commit-before-run):** CA-COLLAR NOT ARMORED (KB 25); CA-BOOK REGIME-PARK (KB 25a); GOLD-TREND NOT ADOPTED (1/4, GT-2 DENIED by Nikhil, signed-corr template fix); P1-R NOT-ADJUDICABLE (PIT landmine); Var-B red-team SURVIVES-AS-BETA (invested-days alpha t=0.16); breakout caveat de-staled (was already NOT CERTIFIED); VBT NOT ADOPTED (1/4; VIX-gate dominance = reusable component); TOM-VIX NOT ADOPTED 0/4 (post-pub decay caught in-house); PMS2-GARP ALL FAIL ~20pts below random (managers' alpha = uncodable gates; PMS #3/#4 parked pre-spend); decel-trap F&O put struck (existence test had failed).
- **NEW LANDMINES:** (a) PIT coverage — unified available_date ~zero pre-2020, growth panels live ~2022+; ALL fundamentals validation is 2022+ until Kavya sources pre-2020 quarterly announcements (BSE archive/NSE XBRL — OPEN TASK). (b) Correlation horizon — daily sleeve corr is an artifact; monthly/quarterly is the truth (stacked-book 0.08 daily -> 0.53 quarterly; only S1-F orthogonal in worst months). Frontier consequence: new sleeves must be DIFFERENT-FACTOR; equity variants cap Sharpe multiplier ~1.7x.
- **HONEST BOOK STATE:** 2 certified alphas (S1-F, B1b) + 2 labeled betas (midsmall Var-B w/ binding conditions, breakout). Zero red-team debt. Shadows in flight: P6 snapback, B1c DII-flow, S1-SX Thursday.
- **Wave-B CLOSED:** DII->B1c shadow; VIX-breadth->VBT killed; ToM->killed; INR-gold->data-ready (USDINR cataloged) but GT-2-fenced; filing-time->uncodable at date-precision, component-parked.
- **Reusable design components banked:** VIX-252d-percentile gate (VBT evidence); signed-corr bar (template law); growth-quality ranking requirements for any future fundamentals card (20-60% band, base-effect exclusion, QoQ trend).
- **D-034 (Principal):** portfolio-level adjudication — good sleeves may carry >25% standalone MDD if book contribution/XIRR/regime value is real; frozen-card bars still bind their own cards.
- Open forward engines: S1-F Tue 09:12, S1-SX Thu 09:14, IC-B1b Mon 09:33. Trials ledger 249.

## 2026-07-13 snapshot
- **D-034 (Principal): portfolio-level adjudication** — a good sleeve may carry >25% standalone MDD / lower CAGR-Sharpe if book contribution, XIRR, or regime-specific value is real. Frozen-card bars still bind their own verdicts.
- **CA-COLLAR NOT ARMORED** (KB 25): index collars cut CAGR 14.1→9.0 AND worsened DD 50.1→52.4 on the CA book — V-recovery whipsaw + hedge-basis mismatch. Do not retry static index collars on selection books; route factor-hedge designs to Kabir.
- **CA-BOOK REGIME-PARK** (KB 25a): CA (Sharpe ~0.7 in 2022-25) can't move the stacked-book frontier at DD parity despite Sharpe lift at v3+33% (1.90→2.17). Resurrection: CA forward Sharpe >1.0 or 2016-21 book window. Pure CA daily returns banked at `results/CACB_PMS1_20260712/ca_daily_returns.csv`.
- **RESOLVED SAME-DAY: stacked-book sleeve corr re-measured at monthly/quarterly horizon** — daily 0.08 -> monthly 0.27 -> quarterly 0.53 max; all pairs positive at quarterly; worst months cluster (Feb-22, Mar-24 equity sleeves crash together; only S1-F orthogonal in all 5 worst months). **Roadmap consequence: Sharpe multiplier caps ~1.7x at rho 0.35 — new sleeves must be different-FACTOR (vol/gold/macro/flow), not more equity variants.** Addendum 2 in STACKED_BOOK RESULTS.md; forward projections must use monthly+ corr.
- Trials ledger 231. Queue: PMS candidates #2-#4 cards, wave-3 factory, P7 variants, P1 rerun (nanmean OR-combine), midsmall Var-B red-team.

## 2026-07-11 snapshot
- **/eod flag (Sat):** earnings `forthcoming_results.csv` MISSING from datasets/earnings_pit -> Kavya: regenerate or correct EOD_ROUTINE path. 23 Angel OHLCV stragglers still queued.
- **INDEX_PROGRAM_2026**: citation pass banked → `04_RND_LAB/INDEX_PROGRAM_2026/RESEARCH_CITATIONS_20260711.md` (8 confirmed/3 refuted/4 leads + 93-claim appendix) + MASTER_PLAN ADDENDUM v1.2. Key: trials-registry is a DSR PREREQUISITE; holdout-touch cap; Stream-A VRP prior +1.1-1.2 net vol pts; NEW C2 card (day-night short-vol P&L decomposition, script-only, cheapest next experiment); weeklies data honesty (NIFTY weeklies only from 2019-02-11); SL-Limit-only order engine.
- **S1-F**: first paper ticket Tue 2026-07-14, cron armed (Tue 09:12); runner still flat-margin ₹1.1L — sanity-check lots vs ~₹2.7L/lot until hardened (Phase-0 #8).
- **Skills**: 78 total (+23 this session: superpowers suite, scrapling-official, find-skills, task-observer, impeccable, uipro/design suite, karpathy-guidelines). claude-mem BLOCKED (no Node.js). Weekly skill-discovery slot added Sun 19:30 (calendar + prompt spec).
- **Org monthly spend limit hit again** mid-workflow — agent-heavy work stays OFF until it resets; scripts-first + sequential rule in force.

## VALUATION-REGIME HEDGING STUDY delivered 2026-07-08 (Principal request)
`04_RND_LAB/results/HEDGING_ANALYSIS_20260708/` — NIFTY50 + S&P500, 3 CAPE/PB regimes (25-50-25), best
rollover hedge + overvalued-regime downside play, hist+MC. Deliverable=HEDGING_ANALYSIS_REPORT.docx (human),
SUMMARY.md=agent book. Data: real US Shiller CAPE+S&P500 1871-2026 (multpl) + CBOE VIX 1990- (fetched OK);
India NIFTY50/PE/PB/iVIX 2016- local. Options BS-modeled off VIX+skew (no real chains; Principal-authorized).
FINDINGS: NOW US deep-RICH (CAPE 41.8) but India CHEAP (PB 3.19) -> downside-risk is a US question today.
Best hedge=ANNUAL COLLAR (maxDD -52%->-15% @~3-4pp/yr; annual>>monthly). Best overvalued play=1x2 put
BACKSPREAD/bear put spread (convex, cheap); premium-selling ratios rejected (short the tail). COVID India
iVIX-14 entry: ATM put -37%->-1.5%. Standalone research, NOT a pipeline intake. See journal 2026-07-08.

**As of: 2026-07-07, by DESK-100 — CAMPAIGN OPT-SWEEP-50 closed early (org monthly API spend limit hit mid-sweep); prior state below still current**
**NEXT SESSION STARTS WITH:** (0) OPT-SWEEP-50 has 12/25 groups (23/49 setups) INCOMPLETE pending spend-limit reset — resume only if Principal wants the full picture, otherwise campaign closed against original mandate (bar not cleared); (0b) Kavya ticket needed: ~30-DTE monthly-contract NIFTY options coverage is broken/sparse (5 independent agents hit this); (1) re-arm cadence crons (CLAUDE.md protocol #4); (2) first /weekly-meet Mon 07-07; (3) I-016 diversifier stress-corr deliverable (binding pre-IC); (4) BT-11 v1.5 spec (entry/exit-only + two-stage stops + circuit fills); (5) D-028 retro-audit workflow resume; (6) S-04/S-05 paper first entries (~Jul-14 cycle); (7) FNO REPLAY GAME P1 build (see below — Principal-green-lit, P0 done); (8) FF near-month vehicle (below) -> Arjun Gate-3/4 build + Tara hedge-leg fill audit + Kavya/Arjun live-schema signal-computability check.

## FF SIGNAL NEAR-MONTH VEHICLE — SCOPED, not backtested (2026-07-07, Aakash)
K-012 calendar stays killed (CIO ruling 2026-07-05); signal graduated to a new liquidity-native-vehicle
intake owned by Aakash+Arjun. Scoping memo recommends a **near-month bear-call vertical** (SELL ATM CE /
BUY OTM CE, same expiry, liquidity-gated hedge strike) over a naked short call (undefined risk, rejected
on risk-shape) and over a strangle/PE variant (FF is CE-IV-only per the code — no validated put-side
signal; parked). Biggest open risk: hedge-leg liquidity is spot-checked only (6 names, encouraging but
not audit-grade) and rhymes with K-009's prior kill (far-OTM wings unpriceable, −883% artifact) — real
fill audit is Tara's next step. Memo + 8-item pre-registration spec: `04_RND_LAB/ideas/20260707_ff_signal_near_month_vehicle.md`.
IDEA_PIPELINE.md row updated (still 1-INTAKE — vehicle scoped). Not a Strategy Register row yet.

## CAMPAIGN OPT-SWEEP-50 (2026-07-07) — CLOSED EARLY, bar not cleared
Principal-commissioned hunt for a NIFTY option strategy w/ Sharpe>2 & XIRR>50% post-cost (SP500 leg dropped,
no data). 13/25 Phase-1 groups (26/49 setups) + Arjun's 4 concrete tests + Lakshmi's lit scan all completed
before the org hit its monthly API spend limit mid-sweep (10 groups failed on spend limit, 2 on infra
stalls) — Principal chose to stop and synthesize rather than wait/raise the limit. **Nothing cleared the bar
anywhere** (best honest ann. Sharpe ~1.0: OS-26 bear-call-spread regime-gated); matches Lakshmi's literature
verdict (realistic net Sharpe caps ~0.9-1.2). Four SURVIVE-fragile/marginal setups (OS-04, OS-20, OS-26, OS-35)
are small legitimate uplifts over the existing S-04/S-05 VRP book, not bar-clearing. Full table + 12 INCOMPLETE
(not killed) setups: `04_RND_LAB/results/OPT_SWEEP50_PHASE1_20260707/PHASE1_SYNTHESIS.md`.

## FNO REPLAY GAME (new Principal product, 2026-07-05) — **PLAYABLE** (P0+P1+P2 core done; launch `09_PRODUCT/fno_game/run_game.ps1`)
Intraday NIFTY-weekly-options replay simulator (random hidden day, 1-min bars, persistent ₹10L career
bankroll, trade-log analytics). **Build book = `09_PRODUCT/fno_game/ROADMAP.md`** — locked Principal
rulings L1–L11 (spread-aware fills, lot-65-uniform, hide-date-only, no lockout v1), full mechanics
formulas, phases P0–P6. P0 done: FastAPI stack verified, chart lib bundled, eligible pool 1,198/1,242
days built + gap-reviewed, lot history derived from bhavcopy (…→65 Jan-26), data_loader smoke-tested.
P1 = replay core (WS tick loop, blinding sanitizer, live chart); P2 = trading engine (needs Tara
spread-calibration vs Angel terminal). Either desk builds; ROADMAP is self-contained.
**2026-07-05 later-3: V1 COMPLETE & DEPLOYED (:8787, detached).** All phases P0-P6 done via 3 agent
rounds + QA (45/45 tests, leak suite, README). Full stack: chain w/ IV+Greeks+OI-percentile, payoff
canvas, margin preview, sizing calc, straddle/strangle presets, MKT/LMT/SL-M orders + cancel,
Orders/Trades/Log tabs, Day-P&L/free-margin/countdown chips, inline TP/SL edit, MAE/MFE+R per trade,
journal tags, Wilson-CI analytics w/ recognized-exclusion, CSV export, sound cues, D-1-continuation
chart w/ VWAP/EMA/RSI/CPR/OR15, unkillable tick loop, pause reasons. QA caught+fixed an export
blinding hole. v1.1 candidates in journal (visual QA, Tara spread calibration, reveal equity/MAE viz).

## REPO STRUCTURE CHANGE (2026-07-05, Manoj/Ops) — read before assuming root layout
Root decluttered per Principal order: `other2/` created at repo root, 6 items moved in (`.venv/`,
`working/`, `working101/`, an orphaned `factor_navs (1).xlsx`, and the two pre-firm-structure
planning docs `OPERATING_STANDARD_2026.md`/`PORTFOLIO_OF_EDGES.md` — full reasoning + rollback in
`other2/MANIFEST.md`). Root item count 29 -> 24. Nothing cataloged moved; `logs/`,
`stocks_data_cache.pkl`, `build_final_docs.py`, `intraday_options_strategy/` (still LIVE — do not
touch) all deliberately kept at root, see manifest for evidence.
**Root RENAME to `Shreyas_project_amc` is STAGED, NOT RUN.** `Shreyas_Ionic_AMC/99_OPS/{migrate_
root_rename.ps1, RENAME_RUNBOOK.md, HARDCODED_PATH_MANIFEST.csv}` are ready but require the WHEN
SAFE checklist (live process finished, cwd outside tree, OneDrive paused, fresh backup) before
anyone passes `-Execute`. Until that runs, every path in every doc is still correct as-is — do
NOT assume the folder has been renamed.

## 2026-07-05 NEW CAPABILITY + PRINCIPAL DELIVERABLES (both DONE)
- **EVALUATION_FRAMEWORK.md live** (`03_RESEARCH_DESK/`, Lakshmi +12): 6 modules (NAV forensics/holdings attribution/product-structure-tax/manager forensics/idea gates/live monitoring) + 0-100 rubric + 34 red-flags + verified data map + 60min/1day/IC-grade tiers. Prior-art: QFRA 2.0 (external, `Downloads/Mf_qfra2.../mr_x_framework`, skill qfra2-rerun) wired in for MF names; /attribution skill = extend for external NAVs (build gap, Neel). DATA_CATALOG gap → Kavya: 3 PIT files on disk uncataloged (ratios_pit, yearly_balance_sheet_pit, yearly_profit_loss_pit). Tax module pending Farhan sign-off.
- **AlphaGrep MAAF NFO analysis delivered** (Neel +15): `09_PRODUCT/reports/ALPHAGREP_MAAF_ANALYSIS_2026-07-05.docx` (8 sections, 14 meeting questions, RAG scorecard 4RED/3AMBER/1GREEN). Verified: 78% of claimed 13.9% CAGR = beta; their "NIFTY TRI" = PRICE index (~1.3pp flattery); maxDD mislabeled (COVID not GFC); gold +112.5% NFO-timing. Case-study #1 stub in framework. Pointer in 90_PRINCIPALS_DESK/active/.

## THREE NEW PRINCIPAL RULINGS 2026-07-05 (D-030/031/032 — DECISIONS_LOG + CLAUDE.md hard rules)
Forward-test FREEZE (in-test spec changes void the test; new version = new clock) · capacity ₹10L-10cr +
limit-order-or-skip ACCEPTABLE for exceptional personal-trading strategies (re-read I-017 capacity kill under
this lens; Tara's no-fill=drop convention = the honest limit-or-skip sim) · DUAL MANDATE: trading line
(personal, short-term) + investment line (personal/AMC, long-term: multibagger/contrarian/deep-value/quality).
Principal msg truncated "...best and" — continuation pending.

## K-012 FF-CALENDAR REVIEW — **CLOSED 2026-07-05: STAYS-KILLED-WITH-NEW-INTAKE (CIO ruling)**
Pre-registered v3 final gate FAILED (causal+gate+D+1+tiered 1×: fwd −0.03/₹100, BUILD −0.51, 2× −2.36; survivors PF 0.99). Signal REAL (100th pct vs matched placebos) / vehicle DEAD (61% un-exitable back-leg markets — CIO exitability veto). FF signal → NEW INTAKE, owner Aakash (liquidity-native vehicle, 5 pre-reg kills, full ~34-trial family DSR at Gate-4). Paper-tracking REJECTED; sizing ZERO. Full trail: `results/S-03/20260705_resurrection/` (4 legs + CIO_RULING.md); books updated (KILLED_IDEAS, REGISTER, PIPELINE, KB A.14-A.18). Detail below is historical:
### (historical) 3/3 LEGS LANDED 2026-07-05; v3 was the final gate
All in `results/S-03/20260705_resurrection/`. Verdicts:
1. **Nikhil (RED_TEAM_FF_RESURRECTION.md): EDGE-BEYOND-SIZING, overall FRAGILE** — FF 100th pct vs turnover-matched AND CE_be-matched placebos (sizing alone ≈ 0, FF adds all of +10.5); **CAUGHT NEW T9 LEAK**: v2 engine enters at argmax-FF day (non-causal; v1 was earliest-cross) — logged in LOOKAHEAD_CONTROLS T-log; cost bracket: survives 2× slip, dies ~3.3×.
2. **Sameer (SENSITIVITY_FF_SIZING.md): PLATEAU** — 30/30 cap×threshold cells forward-positive (+17..+26 per ₹100 his convention); equal-premium sizing is load-bearing, cap second-order; +30 family trials declared; recheck-script reproduction gap flagged (canonical sizing to be pinned: qty=min(100/CE_be, 6.0) — 3 independent reconstructions converged).
3. **Tara (FILL_AUDIT_FF.md): MARGINAL** — honest forward **+₹3.88/₹100 vs +₹10.04 headline (38.6% retained)**; binding constraint = FILL-RATE not cost: 61.3% of fwd signals have DEAD back-leg (zero vol, 82.5% zero OI; slippage only 5% of gap); survivors near-headline (PF 2.05); fix = ex-ante back-leg vol/OI gate.
**NEXT (in flight): Arjun v3 causal re-test** — earliest-cross entry (leak fix) + D+1 fills + ex-ante back-leg liquidity gate + canonical sizing + tiered slippage → `CAUSAL_RETEST.md`. THEN CIO synthesis rules on complete evidence (incl. DSR/PBO recompute at ~36+ family trials). Any hard FAIL = K-012 stays killed.

## IN FLIGHT AT WINDUP (harvest these FIRST next session)
1. **Sameer — S-04 Gate-4 sensitivity**: background compute checkpoints to `results/S-04/20260704_sensitivity/` (grid CSV first, then SENSITIVITY_REPORT.md). If report absent: re-run sensitivity_S04.py there or re-summon Sameer (agent now registered).
2. **Devika — Track-2 BT-11**: `results/T2-SIG11/20260704_bt11/` — bt11.py + **VERDICT.md landed at windup, UNREAD/UNFILED** — read, verify shuffle percentile honesty, file into pipeline/register.
3. **D-028 retro-audit workflow STOPPED to save tokens (no work lost)**: 4 sequential lookahead audits (S-01, factor-repl, scanner-chain, SIG-11). Resume via Workflow scriptPath+resumeFromRunId wf_b38e4890-f94 (script under .claude/projects/<slug>/d096bfac.../workflows/scripts/d028-lookahead-retro-audit-wf_b38e4890-f94.js) — or simpler: /lookahead-audit per target (skill exists). S-04's own lookahead audit deliberately excluded → assign to Sameer AFTER his sensitivity lands.

## Right now
- **FIRM FULLY OPERATIONAL.** Team 27 (E-001..E-027 incl. CEO Meher, Product Tanvi, Overfit Dr. Bhat), 49 skills, 60 prompts approved, WORK_LOG + LEADERBOARD live. **BACKUP VAULT live** (`C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP`, weekly task, keeps 5, outside OneDrive — `99_OPS/backup_firm.py`).
- **QUARTERLY_PLAN_2026Q3.md BINDING** + leaders'-meeting decisions D-M1..M10 (minutes in 08_BOARD_ROOM). Paper BOOK_EQUITY = **₹1 crore (D-026)**; deterministic risk ceiling live in execution_scanner (median 5 lots).
- **Strategy truth (STRATEGY_REGISTER) — the honest ledger of the four original sleeves is COMPLETE:**
  - S-01 IV/RV — SEND-BACK, paper-only FIREWALLED (+11.4pts incremental; DSR 0.687/PBO 55% FAIL via purgedcv)
  - S-02 earnings short-vol — **KILLED pre-IC** (denominator artifact #2; resurrection conditions registered)
  - S-03 FF calendar CE — **KILLED (K-012, 2026-07-04)** — denominator artifact #3 (pnl/back-premium); rupee-points truth: build +5.85 → **forward −9.30 (loses money 2024+2025)**. D-M2 IC CANCELLED. Honesty-probe #1 needs a new vehicle.
  - S-04 strangle — **THE ONLY SURVIVOR**: corruption purged, honest +0.22%/spot managed, **2×-cost CERTIFIED 12/12 cells → PAPER-WATCH** (watch managed-exit fill optimism first)
  - S-05 Track-1 straddle — paper-ready (P1 clear); openalgo pilot vehicle
  - S-06 momentum blend — re-run w/ PIT universe + approved costs pending
- **Track-2 honest status (2026-07-04 night):** SIG-11 built (10/10 PIT tests). BT-11 run TWICE — HF panel then UNION panel (survivorship-corrected): real selection edge +5-6.3pp/yr over honest null (shuffle pct 86/88), survivorship was ~4pp/yr (all in 2016). **BINDING CONSTRAINT: fails 2x COST_STANDARDS (N20 +1.03%)** — v1.5 path: trade only entries/exits (50% monthly overlap wasted as churn) + two-stage stops (KB lesson 10). Track-2 IC to rule on register status.
- **Factor replication first cut DONE**: LOWVOL30 via Angel data — corr 0.90/TE 5.9% in 2024 (13.4% overall = methodology gap) → data pipeline VALIDATED; D-M4 exact-methodology build targets TE<3%. Index data live: INDIA VIX 2016→, LOWVOL30/ALPHA50/VALUE20, 5 momentum ETFs (`datasets/index_daily/`).
- **HARD RULE (new)**: every per-trade edge reported in denominator-free RUPEE POINTS + %spot (3 sleeves died of denominator disease). purgedcv = canonical DSR/PBO (bars_per_year units guard).
- `AngelDailyOptionCapture` healthy. Execution-Sheet v2 live (258 trades, TRADE/DISCRETIONARY/BLOCKED blocks); 8 blank 25AUG-PE prices pending backfill.
- **WS-2 de-AI-ification style system BUILT (Tanvi, 2026-07-13):** `00_GOVERNANCE/STYLE_GUIDE.md` (**DRAFT, needs CEO+CIO joint approval D-025**) + `.claude/skills/style-lint/` (offline taxonomy + `scripts/lint.py`, tested clean) + `09_PRODUCT/scripts/docx_style_kit.py` (Georgia/Bahnschrift, 6-hex firm palette, three-line tables) + sample `09_PRODUCT/reports/_style_sample.docx`. Blind A/B round log empty pending approval + colleague raters. Full detail: SESSION_JOURNAL 2026-07-13 last entry.

## Approvals
**D-027 STANDING APPROVAL in force** (+ D-024/D-025): CEO+CIO jointly approve everything; Principal = tie-breaks + LIVE-capital + RISK_LIMITS-loosening ONLY. Permissions dontAsk. D-021/D-022 remain.

## ADOPTION QUEUE (from 3 scouts, 2026-07-04 — Manoj/Ops owns installs, ≤3 parallel, /prior-art first)
1. `pip install purgedcv` (proxy: truststore) → replace hand-rolled DSR/PBO in the validation battery (test vs Arjun's S-01 numbers first).
2. Evaluate **openalgo** (Angel-native paper-trading sandbox w/ margin sim) as the S-05/S-01 paper engine — biggest paper-desk upgrade candidate.
3. Swap any pandas-ta imports → pandas-ta-classic (original hijacked/abandoned); AUDIT for dead alphalens/pyfolio originals.
4. /retro refinement (FinCon): lessons route to the IMPLICATED persona only, broadcast only via propagation-check.
5. Deterministic risk ceiling (ai-hedge-fund pattern): hard non-overridable cap in execution_scanner (formalizes RISK_LIMITS 1%).
6. NOW-methods: Optiver RV features (IV/RV sleeve), JPX top-minus-bottom metric + LGBMRanker (Track-2), MiniLM embeddings (memo search).
7. KNOWLEDGE_BASE ref fix: mlfinlab is PAYWALLED since 2019 (keep-out); nsepy dead.

## COMPLETE TASK LEDGER (recheck 2026-07-04 — nothing skipped; owners per leaders' meeting)
**In flight/scheduled:** ~~D-M1 S-04 2x-cost certification~~ DONE 2026-07-04 ahead of schedule — SURVIVES 12/12 → paper-watch · ~~D-M2 S-03 IC~~ CANCELLED — S-03 killed pre-IC 2026-07-04 (K-012; honesty-probe #1 needs new vehicle) · ~~D-M3 Track-2 SIG-11~~ SIGNAL LAYER DONE 2026-07-04 (BT-11/COST-11 remain, Jul-31) · ~~D-M4 factor-replication flagship~~ **DATA-VALIDATION COMPLETE 2026-07-04 (6wk early): LOWVOL30 TE 4.58%/corr 0.956 (<=6% all eras) on union price panel; MOMENTM30 8.48% (floor = float-weights+constituents, home-net factsheets to close)** · D-M5 Sanjay screen v1 after Kavya's PIT-stamping ruling (Jul-31) · ~~D-M6 openalgo scoped eval (Manoj, Jul-18~~ DONE 2026-07-04, ahead of schedule: verdict PILOT-ONE-STRATEGY, see `Shreyas_Ionic_AMC/04_RND_LAB/openalgo_eval.md`; purgedcv INSTALLED 0.1.2 — acceptance test vs Arjun's S-01 numbers pending) · D-M7 home-net list + token-hacks rollout (Jul-11) · D-M8 compliance-audit #1 (Farhan, Jul-25) · D-M9 board meet + pack (CEO, Jul-31).
**Outstanding small items (unowned until now — assigned):** lastmonth_IVRV.csv regen post-IV-cap (Manoj — regenerate via build_final_docs) · Kavya's ETF independent cross-check completion · ~~23 Angel daily stragglers retry (Manoj, rate-limit aware)~~ DONE 2026-07-04, 23/23 recovered, 500/500 Nifty 500 · S-01 resurrection HF-hunt (time-boxed ≤3 days, Arjun/Kavya — CIO ruling 2e) · pandas-ta/alphalens dead-import audit (Manoj) · ~~deterministic risk ceiling in scanner (Manoj)~~ DONE 2026-07-04, `enforce_risk_ceiling()` in execution_scanner.py, --dry-run validated · Optiver-RV/JPX-metric/LGBMRanker/MiniLM method adoptions (owners: Arjun/Devika/Ishaan, post-SIG-11) · VRP 9-filter replication weekend job (Arjun) · FinCon retro-routing = already implemented via propagation-check (verified).
**Home-network day (location-blocked, NOT skipped):** /factor-indices pull (script ready) · index factsheets/constituents · FII/DII flows · broader constituents · 217 quarterly symbols.
**Awaiting Principal (only these):** LIVE-capital steps · RISK_LIMITS loosening · DhanHQ-paid data if the HF-hunt fails · tie-breaks under D-025.

## PIT UNION PANEL v1 -- DONE 2026-07-04 (Manoj). Two panels, not one -- see below.
Original brief asked for ONE union panel; build hit a 73% HF-vs-MASTER conflict rate (stop-rule
fired correctly per spec). Diagnosed against official NSE bhavcopy ground truth
(`datasets/nifty_stock_daily/1_bhavcopy.csv`): **HF/Delisted/Raw500 = PRICE basis** (as-traded,
94.8% exact match to bhavcopy); **Master xlsx = RETURN basis** (dividend-adjusted, 41.4% match,
smooth drift toward 1.0 approaching present -- classic total-return signature). Shipped as TWO
explicit panels instead of one silently-blended column:
- `datasets/derived/pit_union_panel_v1/close_panel_price.parquet` (HF+Delisted+Raw500, 2,511 syms)
- `datasets/derived/pit_union_panel_v1/close_panel_return.parquet` (HF core + Master/Delisted/Raw500
  ratio-spliced gap-fill, 2,556 syms) -- THIS is the one that hits the coverage target.
Coverage (N200 full-252d-history, the headline metric): 2006 59.9%(HF)->71.8%(return panel),
2014 83.6%->95.5%, 2018 87.9%->97.0%. Residual truly-absent names (nowhere on disk): COX&KINGS,
UNKNOWN (data-entry artifact) -- need external data if closed further.
Downstream flags: Arjun's factor-replication is CONSISTENT PRICE basis (no dividend-inflation
artifact -- that hypothesis is retired, his residual TE is coverage/methodology, not this).
BT-11 used HF = correct, PRICE basis is right for P&L backtests, no rework needed.
Full detail + conflict/splice/quarantine audit trail + D-028 self-audit (PASS):
`datasets/derived/pit_union_panel_v1/BUILD_REPORT.md`. Next (unowned): close COX&KINGS/UNKNOWN
via external source if Principal wants it; re-run BT-11 early slices + replication early era on
the return panel now that early-era coverage is fixed.

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates — D-009 gate).

