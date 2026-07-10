# T4 trial ledger (DSR accounting, per triage pre-registration)
- Primary trials: 1 (score-gate monotonicity, frozen thresholds)
- Marginal trials: 5 (per-flag on/off spreads, reported for diagnosis only, no promotion off marginals)
- Flags implemented: 5 of 6 — OI-confirm DROPPED (deferred to T6 3-bar-lag build; pre-registered in triage)
- Documented spec deviations: VWAP -> session TWAP of typical price (index volume==0 on disk);
  volume flag -> dir-side ATM option 5-min volume vs 1.5x trailing 20-bar median (Kavya ask #3).
- Events restricted to bars with ATM front-weekly option coverage (coverage % in t4_result.json).
