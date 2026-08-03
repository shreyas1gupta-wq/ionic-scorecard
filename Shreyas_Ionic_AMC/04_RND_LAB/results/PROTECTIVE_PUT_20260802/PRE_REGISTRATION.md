# PRE-REGISTRATION — PROTECTIVE_PUT_20260802
Written before running. Principal follow-up mid-session: "pe buying or ratio allowed if directional
some exposure needed" — widening the design space from market-neutral (calendar, dead per
PUTCAL_LADDER_20260802) to structures with deliberate directional (bearish) tilt, framed as
DOWNSIDE PROTECTION for the Rs 50L MF sleeve rather than pure yield generation.

## Two structures, NIFTY index only
1. **PROT_PUT**: BUY 1 PE, ~5% OTM (strike = round(spot*0.95/50)*50), ~30D target tenor, roll at
   T-5 (close at CLOSE, open a fresh rung). Pure long option — capped max loss = premium paid,
   uncapped upside (protection). Cost = 1 leg round-trip x 1.77 pts (COST_STANDARDS-derived,
   reused for comparability with PUTCAL_LADDER/IRONFLY_LADDER/OPTBUY_CONVEXITY).
2. **RATIO_1x2**: BUY 1 PE ~3% OTM + SELL 2 PE ~8% OTM, same expiry ~30D target, roll at T-5.
   Classic put ratio spread — cheaper (often net credit) but UNCAPPED risk beyond the short
   strikes if the market gaps hard through them (net short 1 put below the far strike). This is
   flagged explicitly as the opposite of "very safe" beyond that point — tested honestly, not
   dismissed, since the Principal explicitly allowed directional/ratio structures.

## Why real 2016-2026 data (not a backcast) covers this
`nifty_optidx_all_traded.parquet` spans 2016-01-04..2026-07-03 — unlike S1-F's real-fill sample
(2021+), this dataset's range INCLUDES the actual Feb-Apr 2020 COVID crash with real traded option
prices. A specific CRASH WINDOW (20-Feb to 10-Apr-2020) breakout is reported alongside the standard
era splits, directly comparable to the S1-F COVID backcast's own crash-window convention.

## Sizing frame
Tested at raw points/lot first (gate-4 convention: prove the edge/cost profile on its own terms
before wiring into portfolio sizing). If either structure looks like a genuine net-cost-effective
hedge (i.e., materially reduces crash-window losses for less than its calm-period drag costs), it
becomes a candidate overlay for the PLEDGE_SAFE_20260802 portfolio at some fraction of the Rs 50L MF
notional — not assumed here, decided after seeing numbers.

## Kill/caveat criteria
Not a yield-edge gate-4 (a hedge is EXPECTED to cost money in calm periods — that is not a kill).
Judge on: (a) whether crash-window payoff meaningfully offsets crash-window MF losses per rupee of
calm-period premium spent, (b) for RATIO_1x2 specifically, whether the uncapped tail beyond the
short strikes is ever actually breached in the sample (if it is, flag prominently — that is the
single biggest risk this structure can produce, working against "very very safe").
