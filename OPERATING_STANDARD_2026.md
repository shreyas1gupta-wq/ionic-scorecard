# OPERATING STANDARD — how a top-2026 trader actually wins
Built 2026-06-16. The professional layer wrapping all tracks. Read after RESUME_TOMORROW.md.

## CORE TRUTH (recheck of our plans)
Our plans are strong on SIGNALS. But signals are the *commodity* part — elite 2026
operations win on **RISK, EXECUTION, EDGE-RENEWAL, and PROCESS**, not on one more
indicator. A mediocre edge run with elite risk/execution beats a great edge run sloppily.
This doc adds the 8 systems that were UNDER-SPECIFIED in the track plans. Each is a
sub-plan to build alongside the strategies.

---

## SYSTEM 1 — RISK OPERATING SYSTEM (the real differentiator) ★ build FIRST
A single risk layer above ALL sleeves/markets. Most blow-ups are risk failures, not
signal failures.
- [ ] Position limits: max % equity/name, max % per sleeve, max gross & net exposure.
- [ ] Portfolio HEAT cap: sum of open risk (Σ stop-distance×size) ≤ 2–3% equity.
- [ ] VOL TARGETING: scale total exposure to a target portfolio vol (e.g., 12–15% ann);
      auto de-lever when realized vol rises (the single highest-value overlay).
- [ ] CORRELATION-REGIME monitor: track realized cross-sleeve corr; when it spikes
      (crisis convergence) cut gross — diversification assumption is breaking exactly then.
- [ ] DRAWDOWN circuit-breakers (layered): per-sleeve kill at trailing Sharpe<−1; book-
      level −X% → halve, −2X% → quarter, −3X% → flat & STOP for review. Hysteresis.
- [ ] TAIL budget: daily VaR/ES (95/99) + worst-case scenario loss cap; pre-commit max
      daily/weekly/monthly loss → hard stop trading when hit.
- [ ] STRESS scenarios: 2008/2020-COVID/2018-vol-spike/election-gap/flash-crash replays
      on the live book; size so the worst survivable scenario < ruin.
- [ ] Margin/liquidity stress: can you exit in 1 day at ≤20% ADV? SPAN-spike survival?

## SYSTEM 2 — EXECUTION & TCA (basis points = real money at our turnover)
- [ ] Order policy per instrument: limit-join vs cross vs market (we have this for options;
      extend to equities/ETFs/commodities). Never sweep illiquid books.
- [ ] Market-impact model: participation cap (≤10–20% ADV), slice large orders (freeze qty).
- [ ] TCA: log intended vs filled price; slippage per trade; fill-ratio of passive orders;
      feed REAL measured slippage back into backtest costs (close the sim↔live loop).
- [ ] Timing: avoid first/last 5 min noise unless the edge needs it; US ADRs/ETFs at
      liquid windows; FX conversion cost tracked for US sleeve.

## SYSTEM 3 — EDGE-DECAY & LIFECYCLE management (alpha dies; plan for it)
- [ ] Live edge-health dashboard: rolling 30/60d Sharpe, hit-rate, avg-R per sleeve vs
      backtest expectation; flag divergence (statistical break test: CUSUM / page-hinkley).
- [ ] Auto-demote a sleeve whose live stats break from backtest (don't average down on a
      dying edge — the #1 quant failure).
- [ ] Continuous discovery: the Track-3 research loop runs perpetually to replace decaying
      edges. Maintain an edge PIPELINE (research → paper → live → retire).
- [ ] Crowding watch: is our edge getting arbitraged? (spread compression, signal half-life).

## SYSTEM 4 — AI-AUGMENTED RESEARCH PIPELINE (the 2026 differentiator)
Use LLM/agents as research force-multipliers (we already have the harness):
- [ ] Daily automated brief: LLM scan of news/filings/earnings/regulatory for held &
      watchlist names → flagged events, surprise, narrative shifts (Track3 H5).
- [ ] Anomaly scanner: nightly job flags unusual price/vol/OI/flow across the universe.
- [ ] Agentic hypothesis loop: generate→cheap-test→adversarially-verify→kill, logged.
- [ ] Backtest-audit-as-default: every new sleeve goes through an adversarial audit
      workflow (like results\AUDIT.md) before capital. NO un-audited edge trades live.
- [ ] Guardrail: AI assists research; it does NOT override risk limits or trade discretion.

## SYSTEM 5 — DATA-EDGE ADDITIONS (India-specific flows we're NOT yet using) ★ high value
These are OBSERVABLE institutional/structural flows — moat B (constrained participants),
uniquely accessible in India. Add as Track-3 hypotheses (H8+):
- [ ] **FII/DII daily flows** (NSE/SEBI publish cash + F&O): the dominant Indian flow
      driver. Test as a regime & directional signal. → new H8.
- [ ] Bulk/block deals, promoter pledging/buying (SAST), insider/SAST disclosures.
- [ ] Index-rebalance front-running (Nifty/Sensex reconstitution = forced passive flows).
- [ ] MF monthly holdings deltas; F&O participant-wise OI (NSE publishes client/FII/DII/pro).
- [ ] Corporate-action & event calendar (results, ex-dates) for event-aware risk.

## SYSTEM 6 — TAX & CAPITAL EFFICIENCY (after-tax is the only return that matters)
- [ ] India: F&O = business income (offset expenses); equity STCG/LTCG holding-period
      optimization; tax-loss harvesting; advance-tax planning.
- [ ] US (LRS): TCS on remittance (adjustable), 25% dividend withholding, foreign-asset
      cap-gains (24m LTCG), FX gain/loss. Model NET; the US sleeve clears a higher hurdle.
- [ ] Entity/structuring question (HUF/firm) — flag for a CA; don't optimize prematurely.

## SYSTEM 7 — ANTIFRAGILITY / TAIL HEDGE (survive the 1-in-10-yr first)
- [ ] Standing tail-hedge budget (small, continuous): cheap far-OTM puts / long-gamma
      (Track3 H3) sized to pay in a crash — accept the bleed as insurance.
- [ ] Crisis-alpha sleeve: trend-following / long-vol that profits in dislocations
      (commodity-trend + long-gamma are negatively correlated to the short-vol & momentum books).
- [ ] Barbell: bulk in robust edges + small convex bets; never a position that can ruin you.

## SYSTEM 8 — PROCESS & PSYCHOLOGY (systematized, not vibes)
- [ ] Pre-trade playbook per setup (entry/stop/size/exit pre-defined → no live improvisation).
- [ ] Automated post-trade journal + weekly review (what worked, rule violations, slippage).
- [ ] Override discipline: discretionary overrides of the system logged & reviewed (they're
      usually wrong — measure it).
- [ ] Equity-curve governor: shrink size after loss-streaks / when own performance breaks.

---

## WORLD-CLASS BENCHMARKS (what "elite" means — aim, stay honest)
- Net Sharpe (after ALL costs/tax/slippage) ≥ 2 at the BOOK level = excellent; ≥3 =
  world-class & usually capacity-limited (fits us).
- Calmar (CAGR/MaxDD) ≥ 1.5; MaxDD < 20–25%; % profitable months ≥ 70%.
- Consistency > peak return: smooth equity curve compounds; lumpy blows up.
- Capacity-aware: our edges are small-capacity by design (≤₹10Cr) — that IS the moat;
  measure & respect where each decays. Don't chase scale that kills the edge.

## MATURITY ROADMAP
1. Foundation: data + risk OS + execution + audit-as-default (build BEFORE scaling size).
2. Validate each sleeve (OOS, audit, capacity) → paper → small live.
3. Compose via the cross-asset risk-parity allocator; monitor live edge health.
4. Continuous discovery (Track3 loop) replaces decaying edges; tail hedge always on.
5. Scale ONLY while metrics hold and within capacity ceilings.

## RECHECK — gaps found in the existing track plans (now addressed here)
- No unified risk OS across sleeves/markets → SYSTEM 1. (Was only per-strategy DD governor.)
- No execution/TCA loop closing sim↔live slippage → SYSTEM 2.
- No edge-decay detection / lifecycle → SYSTEM 3 (critical: edges die).
- FII/DII & participant-wise OI flows MISSING from Track3 → SYSTEM 5 / new H8 (big India gap).
- No explicit tax model (esp. US/LRS net) → SYSTEM 6.
- No standing tail hedge / crisis-alpha mandate → SYSTEM 7.
- Process/override discipline not systematized → SYSTEM 8.

## ACTION (fold into tracks; build order)
RISK OS (S1) + audit-as-default (S4) FIRST → then execution/TCA (S2) → then add FII/DII
flow hypothesis (H8) → edge-health monitor (S3) → tail hedge (S7) → tax model (S6).
Signals without these are how good traders become ex-traders.
