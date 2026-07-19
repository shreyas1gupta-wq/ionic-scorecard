# 13 — Execution Pipeline (the phased subplan tree for the $100 session)

Work top-to-bottom. Each phase has a **gate** — don't advance until it passes. After every task: update `PROGRESS.md`, write outputs to disk, commit. Respect max 3 parallel agents, scripts-over-agents for compute, no lookahead, no silent assumptions.

Suggested tree:
```
ALPHA_RANKER/
├── data/            (raw + curated PIT datasets)
├── src/factors/     (one module per factor, PIT-guarded)
├── src/themes/      (theme aggregation)
├── src/regime/      (classifier + regime_state)
├── src/cascade/     (oversight adjustments)
├── src/forensic/    (08 battery)
├── src/scoring/     (composite → P → [-100,100])
├── src/agents/      (orchestration prompts/configs)
├── weights/         (weight book YAML, versioned)
├── results/         (backtest, calibration, IC/DSR/PBO)
└── reports/         (per-stock outputs + one-pagers)
```

## Phase 0 — Data infrastructure  *(gate: 10-stock pilot loads clean, D-009 passes)*
- 0.1 Confirm env (Python path, encoding, proxy, truststore). Build PIT **NIFTY-750 universe** (extend firm NIFTY500 PIT xlsx → 750; survivorship-free).
- 0.2 **screener.in scraper** (Principal logs in): financials/quarterly/shareholding/concall links → cache raw to disk. Pilot = 10 stocks (3 large-quality, 3 cyclical, 2 IT, 2 microcap).
- 0.3 yfinance OHLCV (.NS) + NSE bhavcopy/delivery% for the pilot; verify vs known closes (D-009).
- 0.4 Macro pulls (RBI/FRED/Stooq/MOSPI) → `data/macro/`.
- 0.5 Freeze **data contracts** (schemas) into `09` appendix. Wire firm landmine guards into every loader.
- 0.6 Concall/annual-report fetch for pilot (company sites; `markitdown` PDFs).

## Phase 1 — Factor library  *(gate: every factor PIT-guarded + lookahead-audited on pilot)*
- 1.1 Technicals/momentum/mean-reversion factors (`04`).
- 1.2 Flow/positioning factors (delivery%, F&O OI/PCR/basis, bulk deals).
- 1.3 Growth/earnings-revision factors (`05`).
- 1.4 Valuation factors (own-history + peer percentiles) (`05`/`06`).
- 1.5 Quality/balance-sheet factors (`05`/`06`).
- 1.6 Relative-scoring engine (peer/own-history/sector/cap normalization) — the anti-cutoff core.

## Phase 2 — Regime classifier + oversight cascade  *(gate: regime_state.json reproduces known past regimes)*
- 2.1 Regime classifier (trend×vol×valuation×rate/credit×flow) — rules first (`02`§4).
- 2.2 Cascade adjustments global→national→sector; structural-vs-cyclical headwind classifier (`03`).
- 2.3 Sector tailwind/headwind scores; disruption axis.

## Phase 3 — Forensic module  *(gate: reproduces flags on 3–4 known blow-ups, e.g. historical frauds)*
- 3.1 Earnings-quality (accruals, Beneish, CFO/PAT) (`08`A/F).
- 3.2 Balance-sheet & related-party & governance (`08`B/C).
- 3.3 Compliance/insider/M&A flags (`08`D/E).
- 3.4 Severity model (size×regime×offset) → forensic score + flag list; hard-veto vs heavy-penalty lists.

## Phase 4 — Concall/management engine  *(gate: promise-vs-delivery tracked across ≥4 quarters for pilot)*
- 4.1 Transcript parse → guidance items, tone, red-flag phrases (`10` rubric).
- 4.2 Promise-tracking store; credibility score.

## Phase 5 — Scoring & synthesis  *(gate: full contract emitted for pilot with explainability)*
- 5.1 Theme aggregation (`02`§2).
- 5.2 Composite with **prior** weights per horizon (`02`§3).
- 5.3 Cascade + forensic overlays; cross-horizon coupling (`02`§5,6,9).
- 5.4 Output contract + `top_drivers` (SHAP) + 1-para thesis per lens.

## Phase 6 — Backtest & calibration  *(gate: IC>0 & positive decile spread net of costs; DSR/PBO acceptable; lookahead audit PASS)*
- 6.1 PIT walk-forward harness (purged/embargoed CV) per lens (`11`).
- 6.2 IC, decile spreads, hit-rate, regime-conditional IC.
- 6.3 **Score→probability calibration** (isotonic/Platt per horizon×regime) → back the engine's p_up/win_rate/return_dist.
- 6.4 DSR/PBO, OOS-hygiene, red-team + lookahead audit. External sanity vs factor-index closes.

## Phase 7 — The 1000+ test R&D iteration program  *(gate: weight book earns off priors with logged evidence)*  ← the heart of the build
- 7.1 Mine `12` reading list → one-pagers → replications (candidate factors).
- 7.2 Ablation & orthogonality: does each factor add incremental IC over existing themes?
- 7.3 Cross-validated weight fit per (horizon×regime), regularized & interpretable; monotonicity constraints from theory.
- 7.4 Regime-conditioning validation; red-flag severity calibration on default/blow-up history.
- 7.5 Iterate: promote survivors (with evidence) → weight book; kill failures → KILLED_IDEAS. Track honest trial count; deflate for multiple testing.
- 7.6 ML upgrade of regime classifier (HMM/vol-state) if it beats rules OOS (ml-expert).

## Phase 8 — Microcap model  *(gate: forensic gate catches known microcap frauds; liquidity sizing enforced)*
- 8.1 Beyond-750 universe with liquidity/ASM-GSM screens.
- 8.2 Five-pillar scoring (`07`) with forensic-as-gate; promoter/governance heavy.
- 8.3 Liquidity-aware sizing; basket construction; small-n honesty.

## Phase 9 — Productionize  *(gate: one clean end-to-end run per lens on full universe)*
- 9.1 Batch run cadence: 1M month-end, 1Y/5Y/microcap semi-annual + quarterly track.
- 9.2 Per-stock reports + one-pagers to `reports/`; permanent track record for self-calibration.
- 9.3 Human-review dashboard; override logging; alert-driven re-scores (forensic/bulk-deal/guidance triggers).
- 9.4 Freeze specs+params, pin git hash (firm D-030); schedule crons.

## Dependencies / parallelism
- Phase 0 blocks all. Phases 1–4 can partly parallelize (≤3 agents) once contracts freeze. Phase 5 needs 1–4. Phase 6 needs 5. Phase 7 is the long iterative loop after 6. Phase 8 reuses 0–7 infra. Phase 9 last.
- **Checkpoint discipline:** treat `PROGRESS.md` as source of truth; every phase writes results to disk so a token limit or a login switch never loses work.
