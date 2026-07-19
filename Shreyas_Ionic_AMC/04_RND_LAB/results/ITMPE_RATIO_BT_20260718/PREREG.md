# PRE-REGISTRATION (v2, FINAL) — ITM-Sell / 2x-OTM-Same-Side-Hedge Premium-Ratio System
Filed: 2026-07-18, before results were written up. Owner: quant-head-arjun-rao persona (head-of-quant pass).
**Supersedes the v1 draft previously in this folder** (that draft only pre-registered a MONTHLY two-cell
design on 2021-2026; the Principal's final 2026-07-18 instruction is TWO SEPARATE STRATEGIES — monthly and
weekly, each in two-sided/bull-only form — four primary cells total, windows reported honestly and never
blended). v1's mechanics, cost model, and margin model are carried forward unchanged; only the cell
structure and windows are revised here.

Data basis: `DATA_MAP.md` (Data Officer) + `TRADER_FORENSICS.md` (sibling forensic pass on the real
Apr-2026 trades that motivated this build), same folder.

---

## 1. Strategy definition

**BULLISH state** (`bull = (close>20DMA) | (close>50DMA)`, i.e. OR of the two, primary signal): SELL 1 lot
of the monthly/weekly ITM PE whose real traded premium is closest to a target (Rs 500 monthly / Rs 220
weekly), HEDGE by BUYING 2 lots of an OTM PE, same expiry, **same side** (PE) — Principal confirmed
2026-07-18. Hedge strike chosen so its premium is closest to `hedge_frac × short_premium` (primary
`hedge_frac=15%`).

**BEARISH state** (`bear = NOT bull`): SELL 1 lot of the monthly/weekly ITM CE closest to the same premium
target, HEDGE by BUYING 2 lots of an OTM CE, same expiry, same side (CE) — Principal: *"if we are bearish
we sell call and hedge otm 2x ce"*.

## 2. FOUR primary cells (Principal 2026-07-18: "one on weekly and one on monthly, both separate")

| Cell | Cadence | Premium target | Structure | Window |
|---|---|---|---|---|
| **M-A** | Monthly | Rs 500 | Two-sided (always in market, side follows signal) | 2011-01 → 2026-07 (full history the bhavcopy supports) |
| **M-B** | Monthly | Rs 500 | Bull-only (flat/cash while bear) | 2011-01 → 2026-07 |
| **W-A** | Weekly | Rs 220 (sqrt-time equivalent of 500) | Two-sided | 2019-02-11 → 2026-07 (weeklies don't exist earlier) |
| **W-B** | Weekly | Rs 220 | Bull-only | 2019-02-11 → 2026-07 |

Windows are reported and killed/passed **separately, never blended** — the monthly cells' 2011-2020 slice
is real (options bhavcopy exists back to 2011; DATA_MAP's earlier "2011-2020 is degraded" caveat was about
*interim per-strike marks*, not entry/expiry feasibility — this build uses `CONTRACTS>0`-gated real prints
for every mark, with the untraded-strike fallback in §4 below, so the full history is used honestly, with
the substitution rate logged every cycle).

## 3. Mechanics (exact, as coded in `engine.py`)

1. **Monthly cadence**: cycle *j* = trading days from (monthly expiry *j-1*, exclusive] to monthly expiry
   *j* (inclusive); "monthly expiry" = `EXPIRY_DT == max(EXPIRY_DT)` within its `(year, month)` group
   (resolves correctly pre- and post-weekly-launch, handles Thursday-holiday shifts for free).
   **Weekly cadence**: cycle *j* = the same logic over **every** distinct listed `EXPIRY_DT` (a weekly IS
   the nearest listed expiry each week; the month's last weekly coincides with the monthly contract).
2. **Roll-day entry**: on the first trading day of the cycle, evaluate the signal at that day's close (DMA
   of closes is known at close — no lookahead) and enter: Cell A always enters (PE-hedged if bull, CE-hedged
   if bear); Cell B enters PE-hedged only if bull, else waits in cash.
3. **Weekly signal-check (monthly cadence only)**: every trading-day that is a Tuesday, re-evaluate the
   signal. If it now disagrees with the held side (Cell A) or calls for exit (Cell B, bull→bear) / entry
   (Cell B, in cash, bear→bull — checked **every day**, not just Tuesday, "fast in"): exit ALL legs of the
   current structure at the **next** trading day's real prices; Cell A immediately opens the opposite side
   the same day, Cell B goes to cash (slow out) or has already fast-entered. **Weekly-cadence cells do NOT
   re-apply this mid-cycle check** (a ~5-trading-day cycle makes roll-frequency and check-frequency the same
   thing) — disclosed simplification, unchanged from v1.
4. **Strike selection**: search the option chain for that (date, expiry, side), restricted to `CONTRACTS>0`
   (the honest liquidity gate) and the correct moneyness sign (ITM: `strike>spot` for PE / `strike<spot` for
   CE; OTM: reverse); pick the strike whose `CLOSE` is nearest the target premium. If no `CONTRACTS>0` row
   has the correct moneyness sign that day (rare — DATA_MAP's day-level rate is 100% in every scanned band),
   fall back to the nearest-premium `CONTRACTS>0` row of either sign, flagged `relaxed`/`substituted` in the
   ledger; substitution rate is reported per cell.
5. **Expiry**: cash-settle at intrinsic value from the UNDERLYING's close (`max(0,K-S)` PE / `max(0,S-K)` CE)
   — landmine #1, NEVER the expiry-day option `SETTLE_PR`/`CLOSE`. Roll to the next contract per rule 2.
6. **Costs** (`COST_STANDARDS.md`, D-021 approved): STT 0.10% of premium (sell-side transactions only —
   opening a short, or closing a long); exchange txn 0.035% of premium (both sides, every transaction);
   stamp duty 0.003% of premium (buy-side transactions only); SEBI Rs 10/crore turnover; slippage
   `max(1 tick=0.05, 0.25% premium)` one-way on every real market transaction (entry / pre-expiry exit /
   roll); GST 18% on (exchange txn + SEBI + brokerage). **Expiry cash-settlement is a formula-driven event,
   not a market order**: no slippage/brokerage/STT is charged again on the SHORT leg (already paid at open);
   a LONG hedge leg that expires ITM incurs the options-on-exercise STT of 0.125% of intrinsic value (the
   buyer-side "avoid exercise" rate flagged in COST_STANDARDS); a LONG leg expiring OTM costs nothing.
   **2x-cost stress**: every rate above (STT, exchange, stamp, slippage; GST recomputed on the stressed base)
   doubled, reported alongside the base case — per COST_STANDARDS' standing promotion rule.
7. **Lot size**: NIFTY's contract size verified from `Shreyas_Ionic_AMC/09_PRODUCT/fno_game/data/lot_sizes.json`
   for 2021-07 onward only (75→50→25→75→65 across that span, exact expiry-by-expiry). **Pre-2021 lot size is
   NOT independently verified in this environment** — no on-disk source found. Per the task's own fallback
   rule, **all P&L is computed and reported in NIFTY INDEX POINTS per 1 signal-unit (1 short lot + 2 long
   hedge lots)** — this is lot-size-invariant by construction (both numerator and denominator of every %
   metric scale identically with lot size), so the lot-size gap does not bias any reported % number. Rupee
   illustrations are given only where the verified 2021+ lookup applies, explicitly labeled.
8. **Margin** (the Principal's core economic point): `margin_hedged = max(worst_case_expiry_loss,
   exchange_style_estimate)` where `worst_case_expiry_loss = max(0, |K_short-K_hedge| - net_credit)` (the
   bounded max loss of the 1-short/2-long ratio structure, realized at spot=K_hedge at expiry — beyond
   K_hedge the 2 longs out-gain the short 2:1) and `exchange_style_estimate = max(0, 0.12×spot -
   2×hedge_premium)` (a simplified NSE-style ~12%-notional floor, offset by the hedge premium actually paid;
   not a real SPAN computation, disclosed as such). **`margin_naked = 0.13 × spot`** (SPAN+exposure point
   estimate inside the task's quoted 12-15% range) for the no-hedge benchmark. Margin-drop ratio and
   return-on-margin (hedged vs naked) reported side by side. Hedge-hold discipline: all legs are modeled as
   exiting simultaneously (never hedge-legs-first), so the margin benefit is never modeled as lost
   intraday — per task instruction.
9. **Equity / capital-base convention**: cycle-to-cycle **arithmetic** cumulative P&L against a **fixed
   capital base = average margin required over the window** — NOT geometric (cycle-over-cycle compounding)
   accounting. This is a deliberate, disclosed choice: a cycle can realize a mark-to-market loss LARGER than
   its own at-expiry worst-case bound (a mid-cycle signal-flip exit crystallizes a loss before the hedge's
   terminal convexity has caught up), which makes naive geometric compounding of per-cycle ROM
   mathematically fragile (a single cycle losing >100% of its margin sends compounding equity through zero).
   Where cumulative arithmetic equity would have gone ≤0 at any point, this is flagged **CAPITAL_WIPEOUT**
   and CAGR is reported as **undefined**, never fabricated. Daily MTM equity curves are built the same way:
   `equity(t) = capital_base + (realized P&L of all completed prior cycles) + (running gross MTM of the
   currently-open cycle)` — intra-cycle costs are recognized at the cycle's close/roll, not smoothed daily
   (disclosed simplification).
10. **Determinism**: no random elements in the primary/sensitivity backtest (strike selection, signal, costs
    are deterministic functions of the data). The one random element (placebo shuffle, kill criterion #2) is
    fixed at `seed=42`, `RandomState(42).permutation()` called in a fixed, logged order (100 draws per
    primary cell). The full M-A primary run is executed twice into independent processes and SHA-256
    byte-compared before any result is reported (see BACKTEST_REPORT.md §Determinism).

## 4. Kill criteria (pre-registered, apply to the FOUR primary cells, each on its own window)

A primary cell is KILLED if **any** of:
1. Net-of-cost return-on-margin < 0 over the full window (cumulative arithmetic return on the average-margin
   capital base, per §3.9).
2. Fails shuffled-signal placebo: the real signal's cumulative return-on-capital-base must beat ≥95 of 100
   random same-frequency permutations of the same boolean signal series over the same window (seed=42).
3. Fails one-day-lag test: cumulative return-on-capital-base collapses by >50% (or flips sign) when every
   entry/exit/roll fill is executed one trading day later than the real-time signal would allow.
4. The 2x-OTM hedge fails to materially reduce losses vs the naked short-only benchmark in the worst
   drawdown windows in-sample (COVID Mar-2020, 2022 H1 rate-hike selloff, Apr-2026 dip) — measured
   cycle-by-cycle, not averaged over calm periods.

## 5. Sensitivity grid (labeled, exploratory, never used to cherry-pick a "best" cell)

`signal ∈ {>20DMA, >50DMA, AND, OR}` × `monthly premium target ∈ {400,500,600}` × `hedge fraction ∈
{10%,15%,25%}` × `cell ∈ {two_sided, bull_only}` = 72 monthly combinations. `weekly premium target ∈
{150,220,300}` at the primary signal (OR) and hedge fraction (15%), both cells = 6 weekly combinations.
78 total, all run at cycle-resolution (not daily MTM, for compute-time reasons — disclosed; primary cells
get full daily MTM).

## 6. Additional reporting (Principal-requested, descriptive, not gating)

- Empirical premium→ITM-depth mapping over time (with India VIX as the IV proxy) for every entry, monthly
  and weekly.
- Bear-side legs' (short ITM CE in downtrends) standalone contribution — P&L, win rate, worst cycles —
  isolated from the two-sided cells' combined ledger.
- Hedged (Cell A / Cell B) vs NAKED short-only benchmark, both cadences — full-window averages AND the
  three named crash windows separately (the two answers are expected to differ, and did).
- Signal-gated vs **always-on** (same structure, permanently PE-hedged, no DMA gate at all) — does the DMA
  gate add value, per cadence.
- Weekly-vs-monthly head-to-head restricted to the overlapping 2019-02→2026-07 window: theta captured,
  costs paid, pin-risk episodes, ROM, MaxDD.

## 7. Known limitations disclosed up front

- Lot-size history pre-2021-07 unverified in this environment (§3.7) — all primary/kill-criterion numbers
  are lot-size-invariant % metrics; this does not bias them.
- Margin/SPAN formula (§3.8) is a documented approximation, not a real exchange SPAN file (none on disk).
- Equity-curve/capital-base convention (§3.9) is arithmetic-on-fixed-base, not geometric compounding — a
  deliberate, disclosed choice given cycles can realize losses beyond the at-expiry worst-case bound.
- Sensitivity grid (78 cells) run at cycle-resolution only, not daily MTM.
- Strike-substitution rate (untraded target strike) is logged per cycle and reported; DATA_MAP's band-wide
  liquidity caveats apply less here than to a naive band-average, since this build always searches for and
  reports the nearest *actually-traded* strike, but the substitution-rate column is the honest measure of
  how often that mattered.
