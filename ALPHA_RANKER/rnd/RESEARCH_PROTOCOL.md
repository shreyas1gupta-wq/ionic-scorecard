# ALPHA_RANKER — Model-Improvement Research Protocol (anti-overfit spine)

> Goal: improve the 1M/1Y/5Y (and microcap) scoring models through many small, pre-registered
> experiments — WITHOUT overfitting or lookahead. The rule: **quality gate before quantity.** No
> factor changes the production weights until it survives the full gate on data it was never fit on.
> The Principal warned of "infinite scope + overfit risk" — this document is the discipline that answers it.

## 0. Non-negotiables (every experiment obeys these)
1. **Pre-registration.** Before running, each hypothesis declares: factor definition (exact formula), horizon, expected sign, economic rationale, and a KILL THRESHOLD. Stored in `rnd/backlog.json` BEFORE results exist. No post-hoc redefinition — a changed definition is a NEW id.
2. **No lookahead.** Features at date *t* use only data with `available_date <= t` (fundamentals) or bars `<= t` (price). Every factor is run through the **one-day-lag test**: shift the signal +1 trading day; if IC changes materially, it leaked. Forward returns are strictly *t → t+h*.
3. **Three-way data split, OOS touched once.** TRAIN (discovery) → VALIDATION (confirm) → OOS/holdout (final, single touch per factor). Walk-forward with **purge + embargo** = h days (so overlapping return windows can't leak across folds).
4. **Honest-trials accounting.** A global counter increments on every test. Significance is **deflated** (Deflated Sharpe Ratio; Benjamini-Hochberg FDR across each factor family). A factor that looks good after 200 trials must clear a far higher bar.
5. **Costs + capacity.** Every signal is scored net of turnover × COST_STANDARDS and checked for ADV capacity. A factor that only works gross, or needs untradeable turnover, is not an edge.
6. **Market/factor neutralization.** Judge factors on **residual (idiosyncratic) return**, not raw — strip market beta (and, where relevant, FF factor exposure) so we don't reward closet beta/size bets.
7. **Replace, don't just add.** Candidate improvements (e.g. 65DMA vs 50DMA) are tested as REPLACEMENTS and by **incremental** orthogonal value over the current model — never bolted on because they "also work."
8. **Red-team + reproducibility.** Every surviving factor gets an adversarial pass (placebo dates, shuffled labels, random-factor control) and must reproduce from its card + seed.

## 1. Data spine (built once, shared by all experiments)
- **PIT labeled panel** `rnd/panel/` : monthly (and weekly for 1M) observations per stock with
  - features known at *t* (price/vol/technical from `data/prices`; fundamentals from `MASTER_fundamentals_pit.parquet` gated on `available_date`; macro/US/flows as of *t*),
  - forward returns *r(t→t+21d / +252d / +1260d)*, both raw and **market-excess** and **residual** (see §2),
  - regime label at *t* (`results/regime_timeline.parquet`), sector, market-cap bucket.
- **Corporate actions**: use adjusted prices; verify no split/bonus discontinuities (guards).
- Universe = NIFTY-750 point-in-time (+ delisted where available, to fight survivorship).

## 2. Market & factor neutralization (built once)
- Rolling **CAPM beta** to NIFTF500 (trailing 252d, min 126) → residual return = r_stock − α − β·r_mkt.
- **Fama-French 6 for India**, built from our own universe (or proxied by `factor_navs` indices):
  Mkt, SMB (size), HML (value), RMW (profitability/quality), CMA (investment), **WML (momentum)**.
  Each stock's rolling factor betas become BOTH features (exposures) and the neutralization basis.
- **Volatility term structure**: realized vol 21/63/126/252d, downside deviation, idiosyncratic vol
  (resid of factor regression), beta, downside beta, vol-of-vol. Used as features AND risk-scaling.

## 3. The evaluation harness (single shared module — `rnd/lib/harness.py`)
Given a factor Series (per stock, per date) + horizon, returns a standard **result card**:
`IC` (Spearman, lag-tested), `IC_IR`, `decile_monotonicity`, long-short `t_stat` (Newey-West),
`ann_return_LS`, `turnover`, `net_of_cost`, `DSR`, `PBO` (CSCV), `regime_breakdown`,
`lag_test_delta`, `placebo_pass`, `honest_trial_no`. One code path = no per-agent divergence.

## 4. Verdicts
- **PROMOTE**: survives TRAIN→VAL→OOS, DSR>0 after deflation, PBO<0.5, lag-test clean, adds
  orthogonal book-level IR (RP-17), red-team pass. → candidate for weight-book (still needs IC memo).
- **PARK**: promising but fails one gate → refine definition (new id) or await more data.
- **KILL**: fails kill threshold or lag/placebo → logged in `rnd/KILLED.md` with reason (never retested as-is).

## 5. Controller loop (how the 10 agents stay fed)
- `rnd/backlog.json` = prioritized queue of pre-registered hypotheses (start ~50; grows).
- **Dispatcher** assigns the top *N≤10* untested items to worker agents. Each worker: builds its factor via the shared panel+harness (mechanical, cheap), writes `rnd/cards/<id>.json`, never touches weights.
- **Prioritizer (intelligent)**: an LLM pass that reads the latest cards + KILLED + FRAMEWORK_CATALOG and (a) spawns CHILD hypotheses of winners (refinements/interactions), (b) prunes dead branches, (c) re-ranks the queue by expected-alpha × orthogonality × cheapness. Bounded batch; no self-agreement drift (it must justify each promotion against a placebo).
- Loop until token budget or backlog exhaustion; **checkpoint every card to disk** so a restart resumes.
- Priority score = `w1·economic_prior + w2·orthogonality_to_current + w3·cheapness − w4·crowding − w5·overfit_risk`.

## 6. Themes in scope (from Principal + FRAMEWORK_CATALOG)
market-neutral/residual · FF6 betas · vol term-structure · **65DMA vs 50DMA (crowding/manipulation)** ·
momentum (12-1, residual, vol-scaled) · O'Neil CANSLIM · Minervini/Weinstein stage · value (EY/FCFY/EV-EBITDA/DCF) ·
quality (ROIC/accruals/Piotroski/gross-profitability/Greenblatt) · growth + acceleration + revisions ·
low-vol anomaly · size/marketcap · factor×regime interactions · seasonality/events · flow/delivery (when refreshed).

## 7. What "done" looks like per cycle
A ranked shortlist of PROMOTE-grade factors per horizon, each with a card + OOS evidence + red-team note,
folded into the weight book ONLY via `combine`/`weights` update + an IC memo. The models get better
monotonically and defensibly; nothing enters on in-sample shine.
