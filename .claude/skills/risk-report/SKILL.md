---
name: risk-report
description: Daily/weekly portfolio-risk snapshot — exposures, greeks, limit utilization, breaches (RP-32). Use for /risk-report, "book risk now", before any sizing decision.
---
# /risk-report — owner: Ritika Sharma (risk-manager-ritika-sharma)
1. Spawn Ritika: read PAPER_LEDGER open positions + RISK_LIMITS + STRATEGY_REGISTER.
2. RP-32 format: gross/net per book → aggregate delta/vega/theta → top-5 concentrations → limit utilization % → breaches+aging → regime one-liner (crash-blind caveat standing).
3. File to 07_RISK_OFFICE/ (dated); breaches ALSO to journal + CIO escalation.
