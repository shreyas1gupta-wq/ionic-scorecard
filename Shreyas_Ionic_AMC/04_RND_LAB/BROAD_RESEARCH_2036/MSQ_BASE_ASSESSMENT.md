# MSQ_BASE — CURRENT-STATE ASSESSMENT
**Author:** Dhruv Kapoor (Technical Head, E-005). **Date:** 2026-07-18. **Tags:** [DATA]/[INFERENCE]/[OPINION] per entry.

## 0. Search result — no file/folder named "MSQ_BASE" exists in this repo [DATA]

Verified three independent ways, repo-wide (not scoped to one folder):
- `grep -rli "MSQ_BASE\|msq-base\|MSQBase"` across the whole tree → **0 genuine hits**.
- `Glob **/*MSQ*` → **0 files**.
- Case-insensitive `grep -rli "msq"` across all text files → 12 hits, **all false positives** —
  substring collisions inside third-party library code (`other2/.venv/Lib/site-packages/...` —
  `fontTools/agl.py`, `pygments` lexers, `scipy` test files, glyph-name tables). None are
  firm files, none reference a strategy.
- `git log --all --oneline --grep="MSQ" -i` → **0 commits**, ever.

**Conclusion: "MSQ_BASE" as a named entity does not exist on disk or in git history.** It is not
a typo-adjacent match either (no `MSQ-BASE`, `MSQBase`, `Msq_Base` variant found).

## 1. Best-match candidate: `swing_momentum/` (a.k.a. "Track-2" / roster's "small-cap momentum machine")

The task description — mid/small-cap momentum, Kelly-flavored sizing, trade management, NSE
cost/TCA — matches one real workstream closely enough that I judge this is what the memory note
was pointing at, under a name that never made it into any file or folder: `swing_momentum/` at
the repo root (root `CLAUDE.md` roster line: "Track-2 (small-cap momentum machine) is your build
partner with Quant"). I am assessing this candidate rather than inventing an MSQ_BASE that isn't
there. **[INFERENCE]** — flagging explicitly this is a best-guess mapping, not a confirmed
identity; if MSQ_BASE was something else entirely, it isn't anywhere I could find it.

Path: `swing_momentum/PLAN.md` (built 2026-06-16), `swing_momentum/RESULTS.md` (2026-06-17),
`swing_momentum/run_swing.py` (163 lines, the only real backtest engine that ran).

### What was PLANNED (PLAN.md, 7 phases, full detail on disk)
Universe: NSE equities + US stocks/ETFs + commodity-trend sleeve, ≤₹10Cr capacity-constrained,
5-12 names, 8-25% position size, pyramiding. Signal engine: RS rank, Minervini trend template,
VCP detector, Darvas box, CANSLIM overlay, composite leader score. Trade management: pivot entry,
hard stop below pivot (-5% to -8%), **R-based sizing** (risk-per-trade 0.5-1.0% equity /
stop-distance → shares, not literal Kelly), pyramiding on follow-through, profit-taking at
2R/3R, time stop, portfolio heat cap. Regime filter: Nifty vs 200/50DMA, distribution-day count,
breadth, follow-through-day. Backtest engine with realistic costs/fills. Validation: walk-forward,
regime-stratified, capacity test, DSR/PBO.

### What is actually BUILT vs. planned — real gap, verified by directory listing
- `swing_momentum/backtest/` — **empty** (0 files). `swing_momentum/signals/` — **empty** (0
  files). None of §FILE MAP's named modules (`signals/relative_strength.py`, `signals/vcp.py`,
  `backtest/regime.py`, `backtest/costs.py`, etc.) exist as separate files. [DATA — directory
  listing, both dirs contain only `.`/`..`]
- Everything that actually ran lives inline in one script: `run_swing.py` (Minervini trend
  template + RS rank + regime gate + weekly trailing stop, ~160 lines). This is a genuine,
  working, no-lookahead prototype — but it is Phase 1+2+partial-3+4+5 compressed into one file,
  not the modular system the plan describes. VCP, Darvas box, CANSLIM fundamentals overlay,
  pyramiding, time-stop, and profit-taking-at-2R/3R from §Phase 3 were **never implemented** —
  only "buy top-20 RS-ranked trend-template passers, hold with a 15% trailing stop" ran.

### Real backtest numbers that exist (from `RESULTS.md`, re-derivable from `run_swing.py` +
`processed/eq_close.parquet` + `processed/membership.parquet` — not impressions) [DATA]

Two versions were run; the second is the one to cite, the first is flagged inflated in the
file itself:

| version | fix | full CAGR | OOS CAGR | MaxDD | note |
|---|---|---|---|---|---|
| V1 | none (biased) | +21.0% | +34.4% | 35.7% | **file's own words: "INFLATED, do not cite"** |
| V2 | survivorship (-50% delist loss realized) + price≥₹20 floor + 15% stop + tighter regime | +11.6% | +16.1% | 23.0% | the honest number |

V2 detail: IS (2005-~2019) CAGR +9.8%, Sharpe 0.34, MaxDD 21.0%, Calmar 0.47. OOS (~2019-2025)
CAGR +16.1%, Sharpe 0.60, MaxDD 23.0%, Calmar 0.70. Always-on (no regime gate) CAGR +21.7% but
MaxDD 73.4% — the file's own conclusion is that the regime filter is what makes this survivable,
not the stock-picking. Per-year: best +76% (2014), +62% (2021); worst -14% (2018), -11% (2022).
A companion test (`run_multistrat.py`) found stacking a mean-reversion sleeve on top made things
*worse* (correlation +0.57, risk-parity combo Sharpe 0.11 < momentum-alone 0.41) — a real,
documented negative result, correctly not discarded as "just a bad backtest."

**This CAGR/Sharpe/MaxDD table is the one real, honest, quotable result in the whole
workstream.** Everything downstream of it (Kelly sizing, TCA, the god-tier expansion sleeves) is
either unbuilt or built only as a plan section.

### Self-documented caveats already on file (RESULTS.md §HONEST CAVEATS, verbatim, not my read)
1. No liquidity/volume filter — close-only master, so illiquid names may be "tradable" in sim
   but not in reality. File calls this "THE biggest optimism source."
2. Survivorship handling is a blunt -50% assumed delist loss, not the realized delisting price.
3. MaxDD 35.7% (V1) exceeds the 25% target; V2's 23% barely clears it.
4. Weekly-close fills only, no intra-week stop execution, flat 30bps may be light for
   smaller/thinner names.
5. Bull-regime dependent — explicitly framed as a skill+regime bet, not a smooth compounder.

## 2. (a) Kelly-sizing methodology — assessment against the task's specific question

**Finding: `swing_momentum` does not use Kelly sizing at all.** `run_swing.py`'s actual
implementation is **equal-weight** across the top-20 RS-ranked eligible names (`port =
float(np.mean(vals))` — a flat 1/20 per name), not even the R-multiple/stop-distance sizing that
PLAN.md §3.3 specifies, let alone a Kelly fraction. The word "Kelly" appears in
`swing_momentum/GOD_TIER_EXPANSION.md` exactly once, and only as a one-line design principle
("Geometric compounding rewards concentration IF risk is capped (Kelly)") — there is no Kelly
formula, no win-rate/payoff-ratio estimation, and no robustness treatment anywhere in this
workstream. **The memory note's "Kelly sizing" characterization does not match what is actually
on disk here** — what exists is (i) a plan for R-based position sizing that was never coded, and
(ii) an equal-weight backtest that ran instead.

**Cross-read against `ALPHA_RANKER/rnd/scorecard/POSITION_SIZING_SPEC.md`** (Vikram Shah,
2026-07-18, same night) for consistency of approach, since that is the one place in the firm
tonight that *does* engage with Kelly rigorously: that spec explicitly **rejects continuous
Kelly** as a live formula for the same reason I'd flag here — it names the exact missing
ingredient (a win/loss-split magnitude column; `calibration_tables.parquet` only has blended
`hit_rate` / `mean_log_realized_return`, not separated by hit/miss) and observes that the
inter-bucket hit-rate spread (~8pp at 1Y) is *smaller than the within-bucket year-to-year noise*
(21-27pp std) — i.e., a continuous Kelly fraction would be false precision on noise, not signal.
It recommends a **step-ladder, Kelly-INFORMED (band ordering matches Kelly's ranking of
p·b-implied edge) but not Kelly-DERIVED (no live formula; table lookup only)**, capped at
quarter-Kelly if any Kelly-derived number is ever used, per Pabrai's own stated discipline.

**Read-across for swing_momentum, if position sizing is ever built there:** the same objection
applies with more force. Momentum's per-name win-rate/payoff-ratio would need to be estimated
per RS-bucket/regime-state from a modest number of independent trade-years (weekly rebalance
over 2005-2025 is ~20 years but the trades within a year are highly autocorrelated — same
"effective sample smaller than 20" problem POSITION_SIZING_SPEC.md flags for the scorecard).
**A literal full/half-Kelly sizing layer would be over-fit to noise here for the same
structural reason it was rejected in ALPHA_RANKER tonight — this is a firm-wide, not
one-off, gap.** The honest and consistent next step, if this workstream is resumed, is not
"add Kelly," it is "add the same step-ladder-informed-by-effect-size-not-derived-from-it
discipline POSITION_SIZING_SPEC.md just worked out," rather than reinventing it.

## 3. (b) Trade-management / exit-rule assessment

PLAN.md §Phase 3 is a genuine, complete trade-management spec on paper: hard stop below pivot,
R-based initial sizing, pyramiding on follow-through with stop-to-breakeven, profit-taking at
2R/3R + "sell half on the way up," a time stop for failed breakouts, and a portfolio heat cap.
**What actually ran (`run_swing.py`) implements exactly one piece of this: a 15% weekly-close
trailing stop from the peak.** No pivot-based hard stop, no R-multiple, no pyramiding, no time
stop, no partial profit-taking exists in the executed code. So — genuine exit rule? **Partially:
yes, an exit rule exists and is real (the trailing stop, and it demonstrably matters — always-on
MaxDD 73% vs regime-gated 23% in the same file), but it is the shallowest version of what was
designed, not the full discipline.**

Cross-referencing the sibling gap flagged tonight in
`Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036.md` ("we built an entry
engine ... and never built the exit... no exit logic → no drawdown control → no capital
protection," §1, re: the fundamental scorecard program): **the same throughline applies here,
one level less severely.** swing_momentum at least has ONE mechanical exit (trailing stop) live
and backtested, unlike the pure-entry scorecard the roadmap describes — but it is missing four
of the five exit mechanisms its own plan called for (pivot-stop, time-stop, partial-profit-take,
pyramid-then-trail). If this workstream is resurrected, closing that gap (not adding more entry
signals — VCP/Darvas/CANSLIM) is the higher-value next step, matching the roadmap's own P2
finding that "the round-trip/exit gap is the highest-value buildable piece" for the sibling
program.

## 4. (c) NSE TCA / cost realism assessment

`run_swing.py` cost model: a single flat **`COST_BPS = 30`** applied to symmetric-difference
turnover each weekly rebalance (`cost = turn * (COST_BPS / 1e4)`) — brokerage+STT+slippage bundled
into one number, no per-instrument or per-liquidity-tier breakdown, no circuit-lock handling, no
volume-conditional slippage multiplier. There is no separate TCA module or file in
`swing_momentum/` at all — "NSE TCA" as its own workstream, distinct from this one flat cost
constant, **does not exist here either.**

Cross-checked against the firm's actual, approved cost standard —
`Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md`. **Correction to the task brief: this file
is not DRAFT.** It reads `STATUS: APPROVED (D-021, 2026-07-03 — Principal: "my approval on
everything okay continue")`, binding on all backtests. [DATA] The root `CLAUDE.md`'s
"once user-APPROVED... until then DRAFT" is conditional language describing the general gate, not
a statement that this specific file is still unapproved — the file itself already cleared that
gate.

Against the approved standard, swing_momentum's flat 30bps materially understates cost for
exactly the universe this strategy trades (mid/small-cap momentum names):
- COST_STANDARDS slippage floors are tiered — large-cap 10bps, **mid-cap 20bps, small-cap
  35bps, micro 50+bps** — one-way, before the "double for panic/exit-into-strength" rule. A flat
  30bps *round-trip* bundling brokerage+STT+slippage is below even the single-leg small-cap
  slippage floor alone, before adding brokerage/STT/exchange/GST on top.
  RESULTS.md's own caveat #4 ("30bps cost may be light for smaller names") independently reaches
  the same conclusion.
- COST_STANDARDS' dynamic rule (volume-conditional slippage multiplier: 1x/2x/3x/NO-FILL by
  day-volume vs 20d median, and **circuit-locked days = no fill, ever**) is entirely absent from
  `run_swing.py`. Momentum entries cluster on upper-circuit days precisely because the strategy
  buys strength — per COST_STANDARDS' own stated rationale, this is exactly the failure mode
  ("fixed slippage on exactly those days overstates every momentum backtest") the firm's cost
  standard was written to correct. `07_RISK_OFFICE/` has no strategy-specific execution-realism
  note for swing_momentum, but the general mechanism (`lib/execution_realism.py`,
  `fill_check()`) referenced in COST_STANDARDS and root `CLAUDE.md` landmine #7b was never
  wired into this backtest.
- No liquidity/ADV cap is applied (RESULTS.md caveat #1, already self-flagged as "THE biggest
  optimism source") — COST_STANDARDS requires position ≤10% of 20-day ADV (≤5% micro-caps);
  swing_momentum has no volume data in its close-only master to even check this.

**Net: the cost/TCA layer here is a placeholder, not a TCA study.** Given COST_STANDARDS'
"every strategy must remain net-positive at 2× ALL of the above before advancing to paper" rule,
and that swing_momentum's OOS Sharpe is already a modest 0.60 (Calmar 0.70) even under the
under-priced 30bps assumption, **this is a live promotion risk, not a paper concern** — the
result has not been shown to survive the firm's own approved cost floor, let alone the 2x
promotion stress test.

## 5. Single most valuable next step (recommendation, [OPINION] with reasoning)

**Re-run `run_swing.py`'s V2 result through the real COST_STANDARDS cost model
(volume-conditional slippage tiers + circuit-lock no-fill + 10%-ADV cap) before anything else** —
not adding VCP/Darvas/CANSLIM signal richness, not building a Kelly sizing layer, not resuming
the god-tier expansion. Reasoning, in the firm's own kill-criteria terms: logic and effect-size
here are sound (regime-gated trend-template momentum is a well-evidenced factor, and the OOS
Sharpe 0.60/Calmar 0.70 survived a legitimate survivorship-bias correction that halved the naive
number — that is exactly the kind of real-but-modest effect this firm's discipline says to keep,
not kill on small-n or a modest Sharpe alone). The genuine, documented risk is **cost-shortfall**
— one of the firm's explicit real-kill categories — and it is the cheapest possible test: no new
data pull is required (volume data already exists in the raw 2005-2021 CSVs per PLAN.md §1.2;
Angel SmartAPI or bhavcopy extends it), no new signal research, just re-running the existing
163-line backtest with the real cost function swapped in. If OOS Sharpe/Calmar survive 2x-tiered
small-cap slippage plus the ADV cap, this is a genuinely promotable Track-2 candidate; if they
don't, that's the honest, fast answer the task is asking for — cheaper than resurrecting the
unbuilt exit-management or Kelly-sizing layers only to find the entry edge itself doesn't clear
the firm's own cost bar.

## Files referenced
- `swing_momentum/PLAN.md`, `swing_momentum/RESULTS.md`, `swing_momentum/run_swing.py`,
  `swing_momentum/GOD_TIER_EXPANSION.md` (Kelly mention, one line)
- `swing_momentum/backtest/` and `swing_momentum/signals/` — confirmed empty via directory listing
- `ALPHA_RANKER/rnd/scorecard/POSITION_SIZING_SPEC.md` (full read — Kelly-informed step-ladder,
  §1.1's named data gap, quarter-Kelly ceiling)
- `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036.md` (§1 "entry engine,
  never built the exit" throughline, grepped)
- `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md` (full read — APPROVED D-021, slippage
  tiers, dynamic/circuit rule, 2x promotion gate)
- `Shreyas_Ionic_AMC/07_RISK_OFFICE/` directory listing (no swing_momentum-specific
  execution-realism note found)
