# Results — run-results convention (RESEARCH_SOP §run-engineering)
Every backtest run writes to `results/<strategy>/<run_id>/` where `run_id = YYYYMMDD_HHMM_<confighash8>`. Never overwrite a run dir — a re-run is a new `run_id`, always.

Each run dir contains:
- `config.json` — full params + data snapshot (paths, row counts, max dates); same config must reproduce to the rupee (seeds fixed).
- `metrics.json` — headline + validation-battery metrics (walk-forward, DSR, PBO, regime slices).
- `trades.csv` — full trade log.
- `equity.png` — equity curve.

`trades.csv` and `equity.png` are gitignored (bulky, regenerable from config); `config.json` and `metrics.json` are versioned — the config+metrics pair alone is enough to audit or reproduce a claimed result.
