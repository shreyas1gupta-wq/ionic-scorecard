# SELL_PLUS_TAIL_20260803 -- PROGRESS

## Goal
Combined book: LD_SELL short-premium core (biweekly 0.10D naked strangle) + long-put tail overlay,
re-costed at new STT (0.15% premium, sell side, opening leg). Grid: hedge_ratio x {0,25,50,75,100%}
x moneyness x {3,5,7,10% OTM} x tenor x {1M,3M,6M}. Report CAGR/MaxDD/Calmar/Sharpe/carry/COVID per cell.

## Inputs (reused, not re-derived)
- Core trades: 04_RND_LAB/results/LONGDATED_SELLING_20260730/best_config_trades.csv (286 trades,
  2011-2026, biweekly 0.10D naked strangle stop2x). credit_pt=premium(pts,both legs), margin_rs=
  10%*spot*LOT, LOT=65 (verified: margin_rs/(0.10*spot_entry)=65.0). pl_rs_net currently has NO
  seller-side STT at all (only brokerage+slippage) -- confirmed by reading
  04_RND_LAB/results/BACKTEST_QUEUE_20260730/done/111_longdated_selling.py (leg_cost_rs = brokerage+
  slippage only; STT_EXERCISE_PCT applies only to LONG condor wings, never to naked short legs).
  STT_RECOST_20260803/recost.py explicitly left LD_SELL as "n/a (quoted as CAGR, re-cost at source)"
  -- this build IS that re-cost.
- Option chain: 04_RND_LAB/results/OPTBUY_CONVEXITY_20260731/cache/nifty_optidx_monthly.parquet
  (877,835 rows, monthly-only, 2016-01-28..2030 expiries, CONTRACTS>0 already, zero 0-contract rows
  verified) + monthly_expiry_list.parquet (140 expiries) + spot_vix_ext.parquet (2016-01-04..
  2026-07-03 daily spot/vix, from IRONFLY_LADDER cache).
- Engine template: TAIL_PUT_ROLL_20260802/engine_v2_spread.py (candidate_expiries multi-search,
  find_strike_price, era_of, cash-settle-at-intrinsic -- reused pattern, adapted to single PE leg).

## STT arithmetic (Part D)
STT lands on OPENING leg of a short = credit_pt * LOT * rate. Old 0.10%, new 0.15%.
This was NEVER charged in the original LD_SELL build -- so "recost" here means ADD IT, not delta it.
For the tail put (BUY to open): STT does not apply on buy-side opening (STT is sell-side/exercise
only) -- so the long put pays STT only if exercised ITM at settlement, which for a cash-settled
NSE index option is automatic exercise at expiry, so exercise-STT (0.15% of INTRINSIC, buyer side)
applies whenever the put finishes ITM. Applied in tail engine.

## Plan / steps
1. [DONE] Read all context files (STT_RECOST, PROTECTIVE_PUT, TAIL_PUT_ROLL, VALIDATION_DEBTS,
   OPTSELL_EXT). Confirmed LOT=65, margin=10% naked, credit_pt convention, STT gap.
2. [DONE] recost_core.py -- ran clean. checkpoints/core_trades_recost.csv, core_summary.csv,
   core_covid_2020_trades.csv. FULL 2011-2026 CAGR 16.25%->16.08% (new STT), MaxDD -69.71%->-69.82%
   (margin basis, unchanged convention as LD_SELL's own register entry). STT drag is small (~0.16pp
   CAGR) because it's 0.15% of PREMIUM not notional -- confirms Part D's "options rise ~1.03x" claim.
3. [DONE] tail_put_grid.py -- ran clean, 12 configs (3/5/7/10% OTM x 1M/3M/6M), all n_skip small
   (0-4), monthly-only + multi-candidate expiry search per landmine. checkpoints/tail_trades_*.csv
   (12 files) + tail_put_grid_summary.csv. Cheapest: 1M/10pct -149.85 pts/yr; priciest: 1M/3pct
   -379.02 pts/yr (freq x proximity-to-spot both drive cost, confirmed below in step 8).
4. [DONE] combine_book.py -- ran clean, 60 cells (12 structures x 5 ratios) -> cells.csv. Reports
   BOTH margin-basis (k=1x bare 10% margin, matches LD_SELL's own registered convention) and
   notional-basis (k=10x, fully-collateralized) -- flagged in-script that neither extreme is the
   realistic operating point, hence step 8.
5. [DONE] Net-hedge-positive statement: hedge_pays_for_itself_full_sample=False and
   crash_pays_for_own_carry=False for ALL 60/60 cells -- no config is net-hedge-positive in
   absolute Rs over the observed 2016-2026 sample (expected: insurance costs money; one COVID
   window cannot repay a decade of premium in cash terms). Reported as a firm-level conclusion,
   not asserted away.
6. [DONE] capital_multiple_scan.py (NEW script, not in original plan list but required to answer
   Parts C/E honestly) -- two things neither recost_core/tail_put_grid/combine_book computed:
   (a) k-scan: min capital multiple (capital = k x bare 10% margin) needed per cell to clear BOTH
   the firm's 25% MaxDD ceiling AND RISK_LIMITS' 20% COVID bar -- reuses combine_book.py's exact
   event-generation logic against the SAME cached checkpoints, no re-extraction.
   (b) pessimistic-bound (VALIDATION_DEBTS' measured -37.01% 20-day move, 0%-OTM/ATM conservative
   bound) crash-stress-with-hedge table at 10% vs 5% margin, by hedge_ratio x moneyness.
   Outputs: checkpoints/capital_multiple_scan.csv, checkpoints/pessimistic_stress_with_hedge.csv.
   KEY FINDING: min k for compliance is ~3.2-4x bare margin (i.e. run at ~32-40% capital/notional,
   NOT the exchange-implied 10x) -- and this floor is set by NON-COVID 2021-22 stop-defeat
   drawdowns (maxdd_date shifts from 2020-03-18 unhedged to 2022-01/04/07/08 once ANY hedge ratio
   is added), which a downside PUT does not touch. So the hedge does NOT lower the minimum required
   capital; it only converts the COVID-window outcome from loss to breakeven/gain AT a given k.
7. [DONE] Far-OTM vs near-OTM open question (Part F) -- answered directly using tail_put_grid_summary
   (annual cost by moneyness/tenor) + OPTSELL_EXT's exact row-5 numbers (condor wing ~3%-OTM,
   SAME-EXPIRY as core i.e. 12/30/60d tenors averaged, REJECTED: CAGR -13.6% vs +20.0% naked, Sharpe
   0.02 vs 0.92, maxDD -64.3% vs -36.2%). See return-to-parent message for the answer.
8. [DONE] Returned findings directly to parent per harness instruction (no FINDINGS.md written --
   report-file ban overrides the original plan's step 7; PROGRESS.md is the only checkpoint file).

## Session 2 close-out (this pass)
All of recost_core.py / tail_put_grid.py / combine_book.py were ALREADY COMPLETE on disk when this
pass started (cells.csv had all 60 rows, checkpoints/ had all 16 files) -- the prior agent had
finished the compute, just not steps 5-7 (synthesis) or the k-scan needed to make Parts C/E honest.
Nothing was re-run. Only new file added: capital_multiple_scan.py (+2 checkpoint CSVs).

## Key numbers already in hand (do not re-derive)
- Worst 20d NIFTY move: -37.01% (2020-03-23), = 3.70x a 10% margin. tail_stress.csv.
- LD_SELL COVID(2020): net -Rs42,545/27 trades, worst single trade -50.6% of that trade's margin,
  WITH 2x-credit stop armed (gap risk defeats stops).
- PROTECTIVE_PUT PROT_PUT (5% OTM ~30D, T-5 roll): -19.66 pts/rung net, t=-0.69 (NOT stat-sig
  different from 0 as a drag); crash window (20Feb-10Apr-2020) +3,463 pts (n=2).
- TAIL_PUT_ROLL EXPIRY (passive) hold, 5/10%OTM SPREAD structure, 6M: -18.1 pts/yr headline BUT
  Addendum2 shows ex-3-winners the other 18 cycles average -206.2 pts/yr (11x more expensive) --
  quote median/ex-winner view (~100-200pts/yr) for forward planning, not the lucky realized mean.
  My tail structure here is a NAKED PUT (task says "long-put tail overlay", not spread) so it will
  cost MORE than the spread's -18.1 (no short leg financing it) but keep the FULL tail payoff
  (matches PROTECTIVE_PUT's own preference for the plain long put over the spread).
- OPTSELL_EXT row5: near-OTM (3%) same-expiry condor hedge REJECTED -- held CAGR -13.6% vs naked
  +20.0%, Sharpe 0.022 vs 0.923, maxDD WORSE not better (-64.3% vs -36.2%) despite half margin.
  Open question I must resolve: does a FAR-OTM (5-10%) tail PUT (not a 3%-OTM condor WING) behave
  differently? Hypothesis: yes, because the condor's 3%-OTM wing is providing margin relief, not
  crash protection (too close, caps upside too), whereas a 5-10% OTM put is priced for and pays out
  in an actual crash. Test this directly in step 4.

## Output paths
04_RND_LAB/results/SELL_PLUS_TAIL_20260803/{recost_core.py, tail_put_grid.py, combine_book.py,
cells.csv, FINDINGS.md, checkpoints/*.csv}
