# C1-CARD RESULTS — Overnight transfer (US session → NIFTY opening gap)
**Run 2026-07-11 · card frozen BEFORE run · n=2,798 days (2015-01→2026-05) · panel CSV in this folder**

## STAGE 1: **PASS** — the transfer model is real
`gap% = +0.047 + 0.270·SPXret (t=16.4) − 0.009·ΔVIX (t=−1.0)`, **R² = 0.215** (bar: kill <0.15; literature prior ~0.3).
- A 1% S&P overnight move transfers ~0.27% into the NIFTY open. Era-stable: R² 0.153 (2015-19) / 0.252 (2020-22) / 0.192 (2023-26).
- ΔVIX adds nothing once SPX return is in (t=−1.0) — the S&P move subsumes the vol signal at daily granularity.

## STAGE 2: **PARK** — no value as an S1 veto
|predicted gap| > 0.75% flagged only 7 of 258 S1 days; those days averaged **+19.1 pts (better than the +10.8 mean)** and 0 of S1's worst-10 days were caught (lead bar needed ≥3 + mean improvement).
**Why (and why this is good news):** S1 enters at 09:20 — *after* the gap has resolved. A predictable gap is already in the entry price, and big-gap mornings overpay sellers (the seller's-paradox pattern again). S1-F's existing F2 veto (prior-day |move|>1.5%) already covers the risk channel. No S1-F v1.1 proposal.

## What the PASS is actually for (future streams, not S1)
The banked gap model (coefficients + panel) is an input for: overnight-holding risk sizing (any future position held past 15:30 can be conditioned on the live US session), morning-momentum studies, and event-window risk (Ritika's pre-open checks). It lives in this folder; refresh = rerun script (SPX/VIX autoupdate from CBOE).

Trials ledger: +2 (stage-1 regression, stage-2 veto study).
