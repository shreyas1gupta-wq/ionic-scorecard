# A4-CARD RESULTS — COVID replication on REAL 2011–2021 option settles (the priority experiment)
**Run 2026-07-11 · spec frozen pre-run @ f923851 · 127 monthly cycles, 0 skips, 2011-01→2021-07 · RUN_CARD.json + cycles CSV here**

## VERDICT vs FROZEN BARS: **COVID-SURVIVABLE** (neither kill bar hit)
- **Bar (a):** COVID-window (Feb–Jun 2020) per-lot drawdown **805 pts vs 766 pts worst 2011–2019 stretch = 1.05×** (kill bar: >3×). The crash was a *normal-range* outcome for this structure.
- **Bar (b):** full-period expectancy +3.7 pts/cycle > 0 (t=0.32 — i.e., ~zero, see honesty section).
- The actual crash cycle (entered Feb-2020, expiring 26-Mar-2020 — through the bottom): **−544 pts on a ~730-pt premium.** Every 2020 month traded; Oct-2020 (−412) was nearly as bad as the crash itself.

## What this proves (and doesn't)
1. **The structure survives a COVID-class event on real prices.** Without the SL, the same cycle's raw path shows losses an order of magnitude larger (the pre-fix bug accidentally demonstrated the unstopped counterfactual: −11k to −15k pt outcomes). The 30% per-leg stop converts catastrophe into a normal bad month. This closes the biggest open caveat on S1-F's registration ("no COVID-class day in the real option sample") with *real* 2020 settles — stronger evidence than the BS-model backcast (corr 0.64) it supplements.
2. **It does NOT create a tradeable monthly strategy** (declared in the card): expectancy ≈ 0 (t=0.32), equity sim ₹10L→₹9.7L over 10.5y, maxDD −43% at spec sizing. Consistent with A1/C2: raw premium without the 0DTE concentration ≈ zero edge. The monthly proxy exists only to answer the survival question — which it did.

## Honest limits
- Daily-settle granularity: SL fills at next-day settle; intraday breaches invisible (declared daily proxy). Real 2020 margin spikes could have forced earlier exits — direction unclear.
- Lot 75 uniform + 15%-notional margin are modern conventions applied backward (declared).
- Two data traps found and fixed DURING this run (both now permanent rules):
  - **LANDMINE #9:** bhavcopy expiry-day option SETTLE_PR = the UNDERLYING's final settlement level, not the option price. First run produced −15,428-pt "losses" (buying back a put at the full index level). Fix: never read expiry-day option settles; cash-settle at intrinsic from underlying.
  - **Untraded-but-priced weeklies:** far weekly expiries are listed with model settles but CONTRACTS=0 (2020 vintage especially). Gate on CONTRACTS>0 AND fall back to the liquid expiry — first version skipped 8 months of 2020 entirely, which would have gutted the verdict's honesty.
- AST scanner: 6 advisory flags, triaged false-positive (.min() calls are drawdown *reporting*).

Trials ledger: +1. S1-F evidence pack: this result should be appended at next docx refresh (supersedes "modeled-only" COVID caveat with "real-settle monthly proxy survived at 1.05× normal-era drawdown").
