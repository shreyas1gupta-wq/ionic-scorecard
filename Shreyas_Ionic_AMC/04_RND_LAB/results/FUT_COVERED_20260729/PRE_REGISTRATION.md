# PRE-REGISTRATION — Futures Covered Call / Covered Put / Collar (weekly)
Owner: Aakash Jain (structurer) | Filed 2026-07-30, BEFORE any cell is run.

## Structures under test (all vs long fut + short CE / short fut + short PE / collar)
1. `naked_cc`  = Long NIFTY fut + Short CE @ delta d, margin = 10% x notional (unhedged: downside uncapped)
2. `naked_cp`  = Short NIFTY fut + Short PE @ delta d, margin = 10% x notional (unhedged: upside uncapped)
3. `collar`    = Long NIFTY fut + Short CE @ delta d + Long PE @ delta ~0.10 (tail), margin = 5% x notional (hedged: both sides bounded)

Deltas swept: d in {0.15, 0.25, 0.35}, BS delta computed from spot/strike/trailing-20d realized
vol/T-to-expiry (real IV not available without root-finding on every strike; realized-vol proxy is
consistent with the already-filed COVERED_CALL_NIFTY_20260729 memo's method). Actual traded option
CLOSE price at entry (real 1-min data) is what is booked as premium, never the BS model price
(model is for STRIKE SELECTION only, per the session's METHOD LAW).

Exit rules: (a) hold-to-expiry, cash-settle at underlying intrinsic (never the option settle print,
landmine #9); (b) buy back short leg at EOD close once it has decayed to <=50% of entry credit,
else fall back to the expiry-1 ITM-avoid-exercise rule, else let expire.

Directional conditioning: spot vs trailing-20d SMA (as of entry, PIT-safe) -> above = long-fut leg
(naked_cc/collar), below = short-fut leg (naked_cp). Compared against an always-long control. This
is a plain trend filter, NOT a re-run of the session's intraday 15-min sweep_priorday_reclaim
trigger (that trigger fires intraday and was never designed to set a WEEKLY direction) — flagged
explicitly as a distinct, low-complexity, single-parameter (20d SMA, canonical) adaptation for this
purpose, not a certified signal.

## Windows
- Build: 2021-05-24 .. 2025-12-31 (261 weekly expiries total in the option dataset; build subset only).
- Held out: 2026-01-01 .. 2026-06 — reported separately, NOTHING selected on it.
- Full-span futures-only leverage demo (no options): nifty_1min.parquet 2015-01 .. 2026-05 (spans
  COVID-2020 and 2015-16 correction) — used ONLY for the leverage-shock/buy-and-hold section, not
  for any option-verified P&L claim outside 2021-2026.

## Trials (every cell logged to TRIALS_LEDGER.csv, honest count)
Primary sweep: 3 structures x 3 deltas x hold-to-expiry x always-directional = 9 cells (naked_cc,
naked_cp each always-long/short respectively as their own standalone control; collar always-long).
Secondary: 50%-buyback exit at the recommended delta for naked_cc and collar = 2 cells.
Tertiary: signal-conditioned (SMA20 trend) vs always-long, at the recommended delta, hold-to-expiry,
for naked_cc-vs-naked_cp switch and collar-vs-(mirror collar on put side) = 2 cells.
Total pre-registered primary cells: 13. No cell will be added after results are seen.

## Kill / verdict criteria (fixed before running)
1. If naked_cc or naked_cp's realized maxDD-on-margin exceeds -60% in the build window (i.e., a
   single ordinary drawdown erodes more than 60% of the allocated margin capital), the naked-10%
   structure is UNINVESTABLE at that margin level, full stop — report it as such, do not soften it.
2. Collar is judged to genuinely dominate the naked version only if its Calmar (CAGR/|maxDD|) on
   margin capital is BOTH higher AND its maxDD is materially smaller (not just cheaper margin
   producing a higher CAGR on paper while carrying the same or worse tail).
3. Per Lessons Learned (S-04, 2026-07): the 50%-buyback rule is judged on RISK REDUCTION (tail p05,
   maxDD), never counted as a return-adder. If it costs CAGR but cuts tail risk, that is reported as
   a legitimate, separate trade-off, not a failure.
4. Faster (weekly vs the prior arm's monthly) compounding is judged to "genuinely compound better"
   only if weekly CAGR-on-margin exceeds monthly CAGR-on-notional by MORE than the incremental
   round-trip cost drag (futures 5-6.5pts/wk + option costs every roll) would predict from turnover
   alone — else it is friction dressed as frequency.
5. Any structure whose short-leg strike requires a chain snapshot with no valid (>0) traded price at
   entry is SKIPPED and logged, never backfilled or interpolated.

Signed off before running: Aakash Jain, 2026-07-30.
