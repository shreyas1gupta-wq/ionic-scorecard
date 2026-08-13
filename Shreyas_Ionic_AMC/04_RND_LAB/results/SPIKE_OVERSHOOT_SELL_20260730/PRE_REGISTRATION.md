# PRE-REGISTRATION — Spike Overshoot Sell (Principal's own observation)
Vikram Shah (FM), 2026-07-30. Written BEFORE any measurement/backtest is run. Do not edit
after results land — amendments go in a dated addendum below the line.

## Hypothesis (Principal's words)
0.2-0.4 delta NIFTY weekly options get inflated 3-10 pts over fair value on a sudden large
move; mean reversion (10-30pt pullback) + the excess decaying gives a seller bonus points.
Two sources: (a) vol/overshoot crush, (b) directional mean-reversion. Trade vol (delta-neutral)
AND direction (unhedged), both hedged/unhedged on margin.

## Data / tools
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/{index/NIFTY.parquet, options/NIFTY/*.parquet}`
  via `chain.py` (read-only, reused not edited).
- Pricing: hand-vectorized Black-Scholes (numpy + scipy.stats.norm) per `options-python-libs`
  skill guidance (py_vollib_vectorized is broken on this stack); anchor-verified against
  vollib (S=K=100,t=.25,r=5%,sig=20% -> price 4.6150, delta 0.5695) before use.
- **r = 6.5% flat** [ASSUMPTION, stated loudly — not fitted, not varied by era]. q=0 (index
  dividend yield ignored, [INFERENCE] immaterial at 0-7 DTE).
- LOT=75. Costs Rs25/lot/side/leg (SHARED_CONTEXT authoritative for this mandate). Futures
  round-trip cost 5.5 index pts (mid of the 5.0-6.5 range) for the delta-hedge leg, scaled by
  hedge ratio.
- Margin: naked 10% of notional (S*75), hedged/defined-risk 5% of notional (Principal ruling
  2026-07-29 22:56) — dynamic, recomputed at each trade's entry spot.

## Trigger — TWO definitions, both tested, report which detects the overshoot better
A) **Sigma-move**: 15-min log return z-score vs trailing 20-trading-day mean of daily
   15-min-return stdev (shift(1), causal — never includes the trigger day itself).
   Thresholds tested 1.5 / 2.0 / 2.5 sigma (primary 2.0). Also a 5-min variant.
B) **Intraday-vol-percentile jump** (Principal correction 2026-07-30): trailing 30-min
   realized vol (1-min log-return stdev) percentile-ranked against its own trailing
   20-trading-day distribution of same-window values (causal). Trigger at >=90th pctile.
Cooldown 30 min between triggers on the same day (avoid multi-counting one spike).
Each event tagged by which definition(s) fired.

## Delta-band selection and fair value (this is the core empirical claim)
- Band membership uses the OBSERVED post-spike IV & spot at the trigger bar close t0
  (delta_obs, |delta| in [0.20,0.40]) — i.e. what a trader's screen would show right then.
- Fair value = BS price at t0's spot/time-to-expiry using the PRE-SPIKE IV (mean of the
  option's own quotes over [t0-10min, t0-1min], volume>0 required, >=3 valid bars else drop).
- excess_pts = observed price at t0 − fair value. Reported by delta bucket (0.20-0.30 /
  0.30-0.40), move-size bucket, DTE band (0-1 / 2-7), same-direction-as-move vs opposite side,
  and pre-Oct-2024 vs post-Oct-2024 (mechanism-shift check per Principal's Oct-2024 vol-response
  inversion finding elsewhere in the session).
- **IV/RV ratio at spike** = observed IV at t0 / realized vol over the 15-30min window
  ENDING at t0 (annualized), the cleanest single "is the option rich vs what the underlying
  actually did" statement.

## Entry mechanisms — head-to-head, a headline result
A) **Market-next-bar**: fill at t0+1min OPEN (or first volume>0 bar within 5 min; else DROP).
B) **Resting sell-limit** (Principal correction): limit = fair_value(t0,iv_pre) + X,
   X in {2,3,5,8} pts, live from t0+1min. Fill iff bar HIGH >= limit (reported both with and
   without a +1-tick haircut for queue-priority optimism). Max wait 30 min / EOD; **no fill
   within the window = DROP the trade, never assume a fill (D-031)**. Report fill rate per X,
   time-to-fill distribution, and P&L — vs market-next-bar on the SAME event universe.

## Structures (all 4, dynamic margin)
1. Naked directional short (10% margin) — same side as the move, unhedged.
2. Vertical credit spread, near wing ~150pt further OTM (5% margin).
3. Vertical credit spread, far wing ~300pt further OTM (5% margin).
4. Delta-neutral vol trade: short option + static futures hedge sized to entry delta (5%
   margin) — isolates crush from direction. [SIMPLIFICATION: hedge set once at entry, not
   dynamically re-hedged intraperiod — full gamma-scalp is out of scope this pass.]

## P&L decomposition (exact identity, no residual)
total_pnl = (excess_entry − excess_exit) [vol-crush] + (fair_value_entry − fair_value_exit)
[directional+theta, at CONSTANT pre-spike IV]. Reported in points, per structure, per era.

## Conditioning buckets (Principal ask — report ALL, with n, never just the good ones)
IV percentile (event iv_pre ranked vs trailing expanding distribution of earlier events'
iv_pre) · intraday-vol percentile (the trigger-B state) · price vs 20DMA/50DMA (prior-day
close, causal) · RSI14 daily (prior-day, causal, <30/30-70/>70) · IV/RV-at-spike tertiles.
A conditional cell only counts as a real finding if it (a) has a stated mechanism, (b) holds
in BOTH pre- and post-Oct-2024 halves, (c) has n large enough to matter.

## Kill / tier criteria (Principal-corrected structure — HARD kills only for fake results)
**HARD KILLS:** fails its own placebo (block-permuted trigger timestamps within-day, same
count/day — live effect must exceed placebo); any lookahead/same-bar fill; >30% of net profit
in 1-2 trades (FRAGILE, disqualifies CERTIFIED tier); **maxDD > 25%** of margin-capital; any
zero/thin-volume fill counted as executed.
**FREQUENCY-DEPENDENT ROBUSTNESS GATE:** n<100 -> top-decile-exclusion (best 5/10/20% removed,
must stay net-positive). n>=100 -> cost-stress (net at 1x/1.5x/2x/3x modeled cost + breakeven
multiple). Report both regardless, apply the one matching this trade's own frequency.
**SOFT (sets claim tier, never kills):** t-stat, Bonferroni (m=466, bar p<0.000107), DSR/PBO.
Tiers: CERTIFIED / FORWARD-TEST CANDIDATE / UNDERPOWERED-UNRESOLVED / DEAD.

## Splits (mandatory, never select on 2026)
Build 2021-05..2025-12 vs held-out 2026-01..2026-06-03. Pre-Oct-2024 vs post-Oct-2024 —
**headline** (2025-2026 is the Principal's stated priority).

## Trials
This mandate adds new cells to the firm ledger (2 triggers x 3-4 thresholds x 2 entry methods
x 4 X-values x 5 holding periods x 4 structures x ~6 conditioning cuts — logged honestly in
the SUMMARY with an exact count; firm cumulative before this mandate = 466).

## Tail (mandatory, quantify not assert)
Worst single trade (pts & Rs) per structure, full loss distribution, named dates
2021-11-26 (Omicron) / 2022-02-24 (Ukraine) / 2024-06-04 (election) + every >2.5-sigma
continuation day, worst-loss/average-gain ratio.
