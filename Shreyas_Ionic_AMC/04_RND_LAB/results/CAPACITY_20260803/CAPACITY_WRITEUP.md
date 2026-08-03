# CAPACITY CHECK — HIGH_CAGR's SWEEP (11.9x) and BOOK/S1-F (7.9x) — 2026-08-03
**Tara Singh, Execution & TCA. Files: `adv_extract.py`, `adv_futures_daily.csv`, `adv_options_expiry_daily.csv`,
`adv_summary.json`, `stress_day_extract.py`, `stress_2020_futures_daily.csv`, `build_capacity_curves.py`,
`capacity_curves.csv`, `liquidity_zero_cross.json`, this file. All in `04_RND_LAB/results/CAPACITY_20260803/`.**

## 0. What each sleeve actually trades at 1x [DATA]

**SWEEP = SWEEP_E (`SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv`, 4,378 trades, 1,578 unique
active days — matches PORTFOLIOS.md section 1 exactly, confirming this is the correct source file).**
NIFTY FUTIDX, delta-1, LOT=75. Entry = a 15-min-bar "prior-day reclaim/continue" liquidity-sweep
signal (`sweep_signals`, copied verbatim from `EMA_INTRADAY_BUYING_20260729`); exit = 60-pt trail, held
up to 3 sessions (median hold 20.75 hrs). 1x = 1 lot. Span 2015-01-13..2026-05-14.
**Important correction made during this check:** `STT_RECOST_20260803`'s "Sweep prior-day reclaim (15m)"
cell (n=1232, net −0.531 new, DIES) is a **different, same-day/higher-frequency exit variant from the
EMA_INTRADAY_BUYING family sharing the same entry signal** — NOT the SWEEP_E (3-session) sleeve actually
weighted in HIGH_CAGR. Conflating the two would have wrongly declared SWEEP dead. Verified via unique-
active-day match (1,578) and independent per-trade recomputation below.

**BOOK / S1-F = `STACKED_BOOK_20260711/book_daily_pnl.csv` "total" column (v1 build), of which S1-F is
one of four sub-legs** (midsmall equity 50L, breakout equity 50L, S1-F 3 lots, B1b futures 50L notional).
S1-F itself: weekly 0DTE NIFTY ATM naked short straddle, entry ~09:20, flat 15:25 (`STRATEGY_DOSSIER.md`
#5 / `STRATEGY_REGISTER.md`). Standalone registered sizing: 0.75×equity/dynamic margin ≈ 3-4 lots per
Rs10L **dedicated** slot (margin ≈ Rs2.7L/lot, 2026). Inside BOOK it runs at 3 lots against the FULL
structure (margin funded via **pledge of the 100L equity legs**, not separate cash — v1: 3 lots,
v3 full-deploy: 8 lots against Rs 30L-equivalent, per `stacked_book_v3.py`).

## 1. ADV-participation table — real bhavcopy volumes, verified [DATA]

Source: `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2025,2026}.parquet`
(1,144,686 + 689,704 rows, official NSE F&O bhavcopy; `CONTRACTS` = lots traded/day). Cross-validated
against the independent HF 1-min option-chain (`intraday_options_strategy/.../NIFTY/2026-05-19.parquet`,
via `chain.py` + `lib/chainlock.chain_slot`) — same order of magnitude on both sources, confirming
`CONTRACTS` is genuine lot count, not a units artifact (India's 0DTE NIFTY options are genuinely the
most-traded index-options contract in the world; tens of millions of lots on a single ATM strike on
expiry day is real, not a bug).

| Sleeve | Vehicle | Size | Lots | ADV (2026 YTD median) | Participation % | Flag |
|---|---|---|---|---|---|---|
| SWEEP (SWEEP_E) | NIFTY FUTIDX near-month | 1x registered | 1 | 85,664 lots/day | 0.00117% | OK |
| SWEEP (SWEEP_E) | NIFTY FUTIDX near-month | HIGH_CAGR AU=11.92 | 11.92 | 85,664 | 0.01391% | OK |
| SWEEP (generic instrument benchmark) | NIFTY FUTIDX near-month | 40-lot LOT_SCALING cap | 40 | 85,664 | 0.04669% | OK |
| S1-F/BOOK | NIFTY OPTIDX ATM 0DTE (tighter of CE/PE) | 1x registered standalone | 3.5 | 13,539,249 lots/expiry-day | 0.000026% | OK |
| S1-F/BOOK | NIFTY OPTIDX ATM 0DTE | **literal** 7.87×(3-4 lots) reading | 27.6 | 13,539,249 | 0.000204% | OK |
| S1-F/BOOK | NIFTY OPTIDX ATM 0DTE | 40-lot benchmark | 40 | 13,539,249 | 0.000295% | OK |
| S1-F/BOOK | NIFTY OPTIDX ATM 0DTE | **corrected** reading (§3): 0.787x native | 2.36 | 13,539,249 | 0.000017% | OK |

10%-ADV hard-cap crossing points (COST_STANDARDS "Liquidity & capacity"): SWEEP would need **8,566 lots**
to hit 10% ADV — **719x** the HIGH_CAGR ask. S1-F would need **1,353,925 lots** (median ADV) or, using
the single worst day in the full 2025-26 history (389,104 lots, tighter leg), **38,910 lots** — both
many orders of magnitude beyond anything discussed (40-lot benchmark included).
**Verdict: capacity/ADV is NOT the binding constraint for either sleeve at any size in scope (1x through
40 lots).** This is the opposite of what `THREE_PORTFOLIOS_20260731` and `LOT_SCALING_20260801` feared
in the absence of a real measurement, and it should be said plainly: NIFTY index futures and NIFTY 0DTE
options are both extraordinarily liquid relative to a sub-Rs1cr book. The volume-conditional thin-day
multiplier in `lib/execution_realism.slippage_multiplier` did fire on **5.07% of days** for NIFTY futures
in this window (ratio<0.5, 2x tier) and **never** hit the 3x/no-fill tier (0% of days <0.2 ratio) — so
the flat 0.25pt/side slippage `sweep_11yr.py` assumed is mildly optimistic on ~1 day in 20, never
catastrophically so, for this instrument.

## 2. Edge-vs-size curve — no participation-driven zero-crossing exists in scope [DATA]

COST_STANDARDS' "Dynamic slippage" model is a **thin-day multiplier relative to the instrument's own
20-day volume history**, plus a **hard ADV%-cap gate** — it is not a continuous market-impact-vs-
participation curve. Since participation stays negligible (<0.05% futures, <0.0003% options) at every
size discussed, that model predicts **no size-driven slippage increase** for SWEEP or S1-F between 1x
and 40 lots. Separately, per-lot **statutory** cost (brokerage/exchange/STT/stamp/SEBI) is flat-to-
improving with size, because the Rs20 brokerage is fixed per order (not per lot) while STT/exchange/
stamp scale linearly with quantity — so cost-per-lot never worsens with scale here.
**There is no participation-driven zero-crossing within any size the firm is contemplating for either
sleeve.** What DOES move net edge is the STT regime change, a fixed per-round-trip cost, size-independent:

Recomputed directly from `trades_E_swing3_trail60_1lot.csv` (4,378 trades, 1-lot), applying the
STT_RECOST_20260803 futures delta (+7.20 index points/RT at spot 24,000):
- **SWEEP_E: avg net edge/trade 10.941 pts (old STT, t=7.36) → 3.741 pts (new STT, t=2.52).**
  A 66% edge reduction, but **survives** — positive and still statistically significant. 56.3% of
  individual trades flip net-negative under the new cost (was 52.4%), consistent with a right-skewed,
  trail-exit distribution where a minority of large winners carry the average.
- **S1-F: 9.710 pts/expiry-day (old) → 9.655 (new).** Barely touched — options STT hits premium
  (1.027x ratio), not notional.

**The correct framing, and the one that matters most: HIGH_CAGR was never capacity-fictional — it is
cost-degraded.** SWEEP's edge did not die to size or liquidity; it lost two-thirds of its edge to a tax
change that applies identically at 1 lot or 1,000 lots. Do not conflate "capacity risk" with "cost-regime
risk" going forward — they are different failure modes with different remedies (the former needs smaller
size; the latter needs a bigger raw edge or a cheaper vehicle, e.g., shifting weight toward the options
leg, which the STT hike left almost untouched).

## 3. BOOK's capital-unit error — a genuine, file-verified correction [DATA, high confidence — needs FM/Quant sign-off]

`THREE_PORTFOLIOS_20260731/build_portfolios.py` states: *"NATURAL_CAP = Rs 10,00,000 ... confirmed
explicit for SWEEP/BOOK"* — i.e., BOOK's "1x" = Rs10L, same as SWEEP. **This is verifiably wrong for BOOK.**

Evidence: `FINAL_RANKING_20260730/book_level_metrics.csv` row `BASELINE_existing_book_only` uses
`capital_rs = 10,000,000` — **that is Rs 1 CRORE** (10,000,000 = 1,00,00,000 in Indian notation), not
Rs10L — and reports **CAGR 16.90%, maxDD −19.24%**. `THREE_PORTFOLIOS_20260731/PORTFOLIOS.md` section 1
quotes BOOK's standalone metric as **"CAGR 16.9, MaxDD −19.24"** — an exact digit-for-digit match. Since
CAGR/MaxDD are *ratios* of P&L to capital, getting the identical percentage under two different *stated*
capital bases is only possible if the same capital base actually produced both — i.e., BOOK's true native
unit is **Rs1 crore**, not Rs10L, and `NATURAL_CAP` mislabels it by exactly 10x. The mislabel traces to
`chart_data.json`'s own note ("existing 4-sleeve firm book, **scaled to Rs10L equivalent**") which does
not match how `book_level.py` actually computed the number it's describing.

This also reconciles structurally: BOOK's v1 build is 100L of **directly-held equity** (midsmall+breakout)
whose F&O margin (3-lot S1F + 50L B1b notional, well under a ~75L pledge headroom per `stacked_book_v3.py`)
is funded by **pledging that same equity**, not incremental cash — so the true capital footprint to run
"1x BOOK" genuinely is ~Rs1cr, matching the verified CAGR base exactly.

**Consequence for the weight the user asked about:** at HIGH_CAGR's stated BOOK weight of 78.67%
(Rs78.7L of a Rs1cr fund), the correct reading is Rs78.7L ÷ **Rs1cr (true native unit)** = **0.787x
BOOK's native size — UNDER its documented size, not 7.9x over it.** The "7.9x" figure in
`PORTFOLIOS.md` and in this task's framing comes from dividing by the mislabeled Rs10L unit
(Rs78.7L ÷ Rs10L = 7.87). Scaling S1-F's lot count with BOOK's *true* 0.787x factor gives **≈2.36 lots**
(3 lots native × 0.787), not the 23.6–31.5 lots implied by applying 7.87x to STRATEGY_REGISTER's
*standalone* "3-4 lots/Rs10L" figure — those are two different denominators (S1-F's own dedicated-Rs10L
sizing vs. S1-F's pledge-funded sizing inside the Rs1cr BOOK bundle) and should not be cross-multiplied.
**This does not change the ADV-participation verdict** (negligible either way — see table above) but it
substantially changes the capital-feasibility picture: BOOK in HIGH_CAGR is not over-capacity, it is
plausibly *under*-deployed relative to its own tested structure. **Flagging for `PORTFOLIOS_RECOST_20260803`
and for FM Vikram/Quant Arjun to confirm before this unit correction is adopted** — it revises a headline
figure in an FM-authored document and needs a second pair of eyes, not just mine.

## 4. Exit liquidity on a 2020-03-23-class day [DATA where measurable; explicit gaps flagged]

Source: `fo_bhavcopy_hist/fo_idx_2020.parquet` (1,306,496 rows), the only intraday-adjacent record this
firm holds for that date — **no 1-min tick data exists here for March 2020** (HF options start 2021-05;
a HF NIFTY futures 1-min file does exist per `SWEEP_11YR_20260729` back to 2015, but was not re-pulled
for this check — see gap note below).

**Futures (SWEEP's vehicle):** pre-crash ADV20 (2020-02 into 2020-03-22) = 311,314 lots/day.
- 2020-03-23 (worst day, −12.98%): volume = 380,464 lots = **1.22x** ADV20 — a mild *increase*, not a
  collapse.
- 2020-03-13 (publicly documented market-wide 45-min halt day): volume = 740,076 lots = **2.38x** ADV20.
- Across the entire acute window (2020-03-09 to 2020-03-27), daily volume ranged **0.98x–2.38x** ADV20
  and **never** dropped below the 0.5x/0.2x thresholds that trigger `slippage_multiplier`'s 2x/3x tiers
  or a no-fill flag.
**This is the honest, somewhat counter-intuitive finding: on the worst day in NIFTY's history, volume did
not collapse — it spiked, because everyone was trying to exit at once.** The firm's approved dynamic-
slippage model is built to catch THIN days; it would not have flagged 2020-03-23 as elevated-slippage at
all by its own volume test. The real risk on a day like that is **one-sided flow / adverse selection and
overnight gap risk**, not thin volume — a different failure mode the current model does not price.
COST_STANDARDS' own separate rule *does* apply here and should be invoked explicitly: **slippage floors
"DOUBLE for panic/exit-into-strength."** That is the correct lever for this scenario, not the thin-day
multiplier.

**Options (S1-F's vehicle):** NIFTY had live weekly 0DTE expiries through the crash (2020-03-05/12/19/26).
2020-03-23 itself was not an expiry day (Thursday expiries then); the nearest 0DTE days bracketing the
crash: **2020-03-19** ATM straddle volume = 475,941 (CE) + 602,821 (PE) ≈ **1.08M lots**; **2020-03-26**
≈ 209,365 + 68,383 ≈ **278K lots**. Far smaller than 2026's tens-of-millions (pre-retail-options-boom
era) but still 4-5 orders of magnitude above anything S1-F needs (2.4-31.5 lots per the two readings
above) — options exit liquidity was not a binding constraint even in 2020-vintage crash conditions.

**Circuit-lock risk — a real gap, stated plainly:** `lib/execution_realism.circuit_locked()` is built for
**equity-style continuous price bands** (checks close pinned at ±5/10/20% vs prev_close). NIFTY index
futures/options do not trade under that regime — they are subject to **market-wide trading halts**
(10%/15%/20% index-move triggers with SEBI-specified halt durations depending on time of day), a
different mechanism this detector does not model at all. Whether a halt fired intraday on 2020-03-23
specifically, and for how long, **cannot be established from the daily-bhavcopy data this firm holds**
— that needs NSE's official halt-announcement archive or intraday tick/order-book data for that date,
neither of which is in the data catalog. [INFERENCE, moderate confidence, unverified: a >10% single-day
move of the kind 2020-03-23 recorded very likely crossed at least one market-wide halt threshold
intraday, based on the public 10/15/20% circuit-breaker rule, but I am not asserting this as fact from
data in hand.] **What would settle it:** NSE's circular/announcement archive for March 2020, or intraday
tick data for NIFTY futures/index on 2020-03-09 through 2020-03-27 — worth a data-catalog ticket if the
firm wants a quantified halt-duration answer rather than this qualified one.
**Net exit-liquidity statement:** at every size level discussed (1x through 40 lots, both sleeves),
volume-based exit liquidity was NOT the constraint on 2020-03-23 or its surrounding window — the
constraint, if any, would have been a market-wide halt (unquantifiable from data held) and/or gap-through
risk on the FUTURES leg specifically (S1-F is a same-day, flat-by-15:25 structure with ~0 overnight gap
exposure per its own beta-to-NIFTY of −0.004 to −0.013, per STRATEGY_DOSSIER — it is structurally
insulated from this particular tail in a way SWEEP, which can hold 3 sessions, is not).

## 5. Method notes
- All lot/notional math uses NIFTY LOT=75 (current, per `sweep_11yr.py`/`stacked_book_v3.py`).
  `LOT_SCALING_20260801/lot_scaling.py` uses LOT=65 for its own SOLDIERS strategy — a documented
  inconsistency across scripts, noted but not resolved here (does not affect participation-rate math,
  which is lot-count-to-lot-count and unit-agnostic; only affects rupee-notional conversions quoted
  elsewhere in that report).
- ADV window = 2026 YTD (Jan-Jul), 27 expiry days for options, 375 days for futures near-month series;
  2025 data loaded alongside for the rolling 20d ADV calc at the start of the window.
- STT delta (+7.20 pts/RT at spot 24,000) taken directly from `STT_RECOST_20260803/recost.py`'s own
  computation (`d_fut`), applied to SWEEP_E's raw per-trade points — not re-derived independently.
