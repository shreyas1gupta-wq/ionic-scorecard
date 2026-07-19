# Cross-Asset / ETF Macro Sleeve — Honest Current-State Assessment

**Author:** Cyrus Daruwalla, Macro & Events Strategist (E-021)
**Date:** 2026-07-18
**Trigger:** `ALPHA_RANKER/rnd/wave4/RESEARCH_QUEUE.md` §QUEUED item 1 is stamped `[LAUNCHED]` with no
disposition recorded in the queue itself — this memo traces what actually happened to it.

---

## 1. Verdict up front: it WAS built, tested, and honestly killed/parked — just never marked in the queue

The queue entry is stale, not the research. `ALPHA_RANKER/rnd/wave4/ETF_SLEEVE.md` (Vikram Shah,
2026-07-17 — same day the queue item was flagged `[LAUNCHED]`) is a complete Gate-2/3 cheap-test
cycle: real data fetched (9 of 10 intended assets — microcap blocked, not fabricated), a real
backtest with a **self-caught lookahead bug** (signal-at-t applied to the contemporaneous return,
inflating Sharpe to 3.01 — caught and fixed before any number was accepted, D-035 discipline
correctly applied), drop-one, era-split, and three filed verdict cards. This is NOT "silently
abandoned" — it is a completed, disclosed research pass that the standing queue file simply never
got updated to reflect. **Action for whoever owns RESEARCH_QUEUE.md next: change item 1 from
`[LAUNCHED]` to `[DONE — see ETF_SLEEVE.md, KILL as active rotation / diversifier value untested]`.**

## 2. What's actually built vs just planned

| Component | Status | Evidence |
|---|---|---|
| Data — gold/silver/Nifty50/copper/Nasdaq/S&P500 | **BUILT**, real history | `datasets/etf_gold_silver/*.parquet`, `datasets/etf_universe/COPPER_HG.parquet`, `QQQ.parquet`, `SPY.parquet` |
| Data — India midcap/smallcap/momentum/lowvol ETFs | **BUILT**, but short (2.3–4.4y) | `datasets/etf_universe/MIDCAP_ETF_A.parquet` etc., D-009 identity-checked (one near-miss caught: a smart-beta smallcap product rejected as mislabeled) |
| Data — India microcap ETF | **BLOCKED**, correctly not fabricated | no ticker resolves to a genuine microcap tracker |
| TS-momentum (1M) | **TESTED — KILL** | IC −0.075/−0.122 (both windows, both negative = anti-persistent, not trend); rotation Sharpe 0.30–0.38 vs buy-hold 0.72–1.38 |
| TS-momentum + relative-strength (1Y) | **TESTED — NOT-VALIDATED / DO NOT SIZE** | IC +0.054/+0.112, same-sign both windows (best-surviving factor) but rotation Sharpe 0.68–0.77 vs buy-hold 0.70–1.38 (buy-hold wins, decisively in the honest n=53 window) |
| Carry (spot-vs-252d-trend proxy) | **TESTED — soft prior only** | IC +0.068/+0.053, same-sign, weak; never isolated into its own backtest, only as an ingredient of the 1Y IC table |
| Valuation-vs-own-history (price-percentile proxy), 1M & 1Y | **TESTED — KILL, sign-flips** | IC near-zero, flips sign between windows at both horizons |
| Valuation-vs-own-history, 5Y | **KILL as constructed + genuine DATA GAP** | true 5Y-forward test possible only for SP500/NASDAQ/COPPER; 0 completed 5Y-forward observations for gold/silver/momentum/lowvol/smallcap (all <5.5y history) |
| Vol regime scoring | **NOT DONE** in this sleeve (rv(252d ann.) reported as a descriptive stat only, not tested as a factor) | ETF_SLEEVE.md §4 table |
| Rotation-as-active-strategy | **KILLED** on current evidence | §5 allocation memo: "Edge... NOT ESTABLISHED... proposed size ZERO" |
| Gold/global-equity as a **passive diversifier** (not rotation) vs the firm's short-vol book | **FLAGGED as plausible, NEVER TESTED** | explicitly deferred: "a static/blended cross-asset holding... may still be worth a separate, much smaller research pass" |
| Related but separate: copper/gold ratio & gold-vs-equity 1m-momentum as a **sizing signal** for the stock model (not the ETF sleeve itself) | **TESTED — MAYBE/CANDIDATE, failed lag-stability gate** | `ALPHA_RANKER/rnd/wave4/MACRO_XASSET.md` §1 (my own prior-session memo) — routed to Sameer Bhat for era-split/PBO; no evidence that follow-up ran |

**Net: the sleeve is a completed cheap-test, correctly killed as an active strategy, not an
incomplete or ghosted piece of work.** The one real gap is the untested diversifier/allocation
question, and the crisis-hedge thesis being asserted rather than tested (addressed in §4 below).

## 3. Is the gold/cash de-risk wiring actually built, or still a design intention?

Checked `ALPHA_RANKER/rnd/wave4/REGIME_SPEC_V2.md` (Arjun Rao, 2026-07-17) directly against the
memory note. **Answer: still a design intention, explicitly and honestly labeled as such.**

- The absolute/crisis-state layer rule is: richness (valuation gauge) ≥160 → route to gold/cash
  via the ETF sleeve. Quote: *"This state has never printed in 21 years of Indian market history
  on the gauges built so far — it ships as a precautionary rule with a clear, disclosed empirical
  gap."*
- The ≥160 threshold itself was **"shape-matched to the Principal's illustrative bands, not fit to
  data"** — max reached in 21y of India history is ≈122–139. It is a real rule sitting in the spec
  (not vaporware), but it has literally never fired, so there is zero empirical evidence for what
  actually happens to the book if it does.
- The breadth-based faster tactical trigger (layer E, the one that COULD plausibly fire more
  often) is explicitly flagged as **not yet backtested as a book-level exposure scalar** — only
  validated as an oversold-mean-reversion switch conditioner, a different use.
- So: the plumbing (rule → route to ETF sleeve → buy gold/cash) exists on paper and is correctly
  status-labeled "PRECAUTIONARY... NOT yet Gate-4/IC-adopted." It has not been built as a tested,
  triggerable mechanism, and per §2 above, even the target destination (the ETF sleeve's gold leg)
  has only been tested as a rotation strategy (killed) — never as "what happens to a gold holding
  specifically during the crisis episodes this rule is meant to catch."

## 4. First-pass cheap test I ran myself: does gold actually decouple during India equity crises?

This is the one concrete, cheap, well-scoped gap the sleeve's own resurrection conditions named:
*"re-test using raw index histories across a window containing a real drawdown (2020 COVID / 2022
hikes) before concluding the crash-protection thesis is false, not just untested."* The sleeve
builder used `goldbees_daily.parquet` (starts 2021-01-11 — misses COVID entirely). An **extended
file already sits on disk, unused by that memo**: `datasets/etf_gold_silver/goldbees_daily_ext.parquet`
(2013-01-01 → 2026-07-03, 3,341 rows) — no new fetch needed, just a file nobody had cross-referenced.

Method: daily returns, gold (GOLDBEES, tz-fixed) vs Nifty50 (NIFTYBEES), 2013–2026, n=3,339 days.
Diagnostic only (characterizing realized historical behavior in known stress windows), not a PIT
trading signal — no lookahead concern, same class of test as `/stress-replay`.

| Test | Result |
|---|---|
| Full-sample daily return correlation | **−0.037** (near-zero, if anything slightly negative) |
| Correlation on Nifty-down days only (n=1,520) | **−0.029** — does NOT converge toward +1 |
| Mean gold return on Nifty's worst 2% days (n=67) | **+0.29%** vs Nifty's own mean of **−2.91%** |
| COVID crash window (2020-01-20 → 2020-03-24) | Gold **+4.1%**, Nifty **−35.2%** |
| 2022 H1 drawdown (Jan–Jun 2022) | Gold **+5.6%**, Nifty **−10.9%** |

**[DATA] Honest reading:** across the two genuine India-equity crisis episodes this sleeve's own
memo said were needed to test the thesis, gold decoupled cleanly and positively both times —
opposite of "correlations converge to 1 in crisis" (that convergence claim is true for
risk-assets against each other, not for gold against equities, which is exactly the mechanism a
crisis hedge needs). This is a genuinely new, cheap result: it directly fills resurrection
condition #1 from `ETF_SLEEVE.md` and gives the REGIME_SPEC_V2.md gold/cash routing rule its
**first actual empirical support**, separate from and stronger than the TS-momentum-rotation
result (correctly killed — momentum profitability and crisis-decorrelation are different
mechanisms, and conflating them is exactly the error the sleeve author avoided by testing them
separately). It does not certify the routing rule (n=2 episodes, no DSR/PBO, not Gate-4) — but it
moves "crisis hedge" from asserted-but-untested to directionally-confirmed-on-the-two-cases-we-have.

**This does NOT resurrect the killed rotation strategy** — TS-momentum chasing gold's own recent
return remains wrong-signed per §2. It supports a *static/passive* gold allocation as a portfolio
diversifier, which is exactly the untested idea the sleeve memo flagged and deferred.

## 5. Connection to tonight's CYCLES_AND_REGIMES_METHODOLOGY — does it change gold sizing?

Reviewed `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/CYCLES_AND_REGIMES_METHODOLOGY.md`.
The relevant finding: **commodity capex-underinvestment / inventory-to-use ratios** are rated
"USABLE AS CONTEXT, moderate confidence" — checkable, leading indicators (capex/sales decline in
commodity producers, falling inventory-to-use, years ahead of price) — explicitly distinguished
from the "supercycle" narrative label, which is rejected as vendor-marketing-driven.

**Does this connect usefully to the ETF sleeve's gold leg? Yes, but via a different mechanism than
the one already tested — worth flagging, not yet worth building:**

- The ETF sleeve tested gold as a **momentum/valuation/carry asset** (all weak-to-killed) and,
  per §4 above, as a **crisis-hedge/decorrelation asset** (directionally supported).
- The cycles memo's own India-specific read: *"India is a large net commodity importer (oil +
  gold dominate the import bill); a genuine multi-year commodity upcycle is a CAD-widening/
  INR-depreciation/RBI-hawkish risk."* This is a **third, mechanically distinct** gold rationale —
  not "gold as crisis hedge" (equity decorrelation) but "gold as an INR-devaluation hedge," driven
  by the same capex-underinvestment/inventory-to-use leading indicators the cycles memo already
  greenlit for commodity-desk monitoring generally.
- This has **not been tested anywhere in the current research** — MACRO_XASSET.md tested
  copper/gold RATIO as a sizing signal for the stock model (CANDIDATE, failed lag-stability gate,
  parked for Sameer Bhat), which is adjacent but not the same question (a relative-price signal,
  not an INR/import-bill-linked gold-sizing rule).
- [OPINION, tag per protocol] worth a cheap follow-up, not a build: does gold's forward return (or
  its crisis-decorrelation strength) vary with the commodity-producer capex/sales and
  inventory-to-use series the cycles memo already validated as checkable? That would give the
  gold leg of the ETF sleeve a genuine, non-momentum, non-valuation SECOND rationale beyond "it
  decoupled twice" — a structural (import-bill/currency) one instead of a purely
  historical-correlation one. It is cheap because the leading indicators are already rated usable
  and the gold price series is already on disk (the `_ext` file found in §4).

## 6. What's untested (the honest gap list)

1. Gold/cross-asset holding as a **static portfolio diversifier** (not rotation) against the
   firm's short-vol book — flagged by the sleeve author, never built or measured.
2. **DSR/PBO/Red Team** pass on the one soft-surviving factor (1Y TS-momentum + carry) — explicitly
   deferred as "not worth running yet, sample too thin, too few real degrees of freedom" — correct
   call, but means even the best-surviving factor is pre-certification.
3. **Vol regime** as an explicit scored dimension for the ETF sleeve, per the original brief — not
   done; rv(252d) is reported descriptively only.
4. **Carry** was only measured as a spot-vs-252d-trend proxy pooled into the 1Y IC table, never
   isolated as its own standalone backtest the way TS-momentum and valuation were.
5. **Gold-INR/import-bill linkage** (§5) — genuinely new connection point, zero testing done.
6. **REGIME_SPEC_V2's breadth-as-exposure-scalar** (the faster-firing sibling of the never-fired
   richness≥160 gold/cash trigger) — not backtested at the book level, flagged as quant-head's own
   next test, unrelated to this sleeve directly but shares the same "de-risk trigger" plumbing.

## 7. Single most valuable next research step

**Extend the crisis-decorrelation test (§4) from a 2-episode diagnostic into a proper cheap-test
of gold as a STATIC (not rotating) portfolio diversifier against the firm's actual short-vol book
returns — using the already-on-disk `goldbees_daily_ext.parquet` (2013–2026) and the firm's own
S-01..S-05 paper/backtest P&L series.** This is the one item that is (a) cheap — data already
exists, no new fetch, (b) directly actionable — it is the exact "separate, much smaller research
pass focused on portfolio-construction value" the sleeve author asked for, (c) directly serves the
CIO's stated rationale for the whole ETF sleeve (a second true diversifier alongside the
equity/momentum book), and (d) does not require solving the untested richness≥160 trigger or
building a new rotation rule — a fixed small static gold allocation sized against the short-vol
book's own crisis-month P&L would test the diversification claim on its own terms, independent of
whether the precautionary regime-routing rule ever fires. Second-most-valuable, cheaper still: the
gold-INR/capex-underinvestment cross-check in §5, since the leading-indicator data is already
rated usable and would give the gold leg a structural (not just historical-correlation) second
rationale.

## 8. Discipline notes applied in this assessment

- No kill applied here or upstream for low-n/low-t/DSR/PBO alone — the 1Y TS-momentum+carry
  factor is correctly parked as a "soft prior," not killed, despite thin sample.
- Real kills found in the upstream work were legitimate ones: 1M momentum is **wrong-signed**
  (anti-persistent, not the trend the rule assumed) and the valuation-vs-history proxy **sign-flips**
  between windows (flat/unreliable effect) — both are on the firm's real-kill list (wrong-sign,
  flat-effect), not statistics-only kills.
- The §4 test here is diagnostic/historical (crisis-window realized behavior), not a forward
  trading signal — no PIT/lookahead exposure; tagged [DATA].
- The §5 connection is tagged [OPINION]/proposal only — no claim of a tested effect.

---
**Files referenced:** `ALPHA_RANKER/rnd/wave4/RESEARCH_QUEUE.md`, `ALPHA_RANKER/rnd/wave4/ETF_SLEEVE.md`,
`ALPHA_RANKER/rnd/cards/W4ETF_TSMOM_1M_core6.json`, `ALPHA_RANKER/rnd/cards/W4ETF_TSMOM_RS_1Y_core6.json`,
`ALPHA_RANKER/rnd/cards/W4ETF_valuation_meanrev_5Y.json`, `ALPHA_RANKER/rnd/wave4/REGIME_SPEC_V2.md`,
`ALPHA_RANKER/rnd/wave4/MACRO_XASSET.md`, `Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/CYCLES_AND_REGIMES_METHODOLOGY.md`,
`datasets/etf_gold_silver/goldbees_daily_ext.parquet`, `datasets/etf_gold_silver/niftybees_daily.parquet`.
