# PORTFOLIOS RE-FIT — BOOK unit fix + SWEEP-edge fix applied together
**2026-08-03 · Vikram Shah (FM). Script: `refit.py` in this folder (`04_RND_LAB/results/PORTFOLIOS_REFIT_20260803/`).
Inputs read: `CAPACITY_20260803/CAPACITY_WRITEUP.md`, `PORTFOLIOS_RECOST_20260803/PORTFOLIOS_RECOST.md`,
`STT_RECOST_20260803/FINDINGS.md`, and the underlying data files each of those cites. Outputs:
`refit_results.json`, `au_labels.csv`, `run_log2.txt`.**

## 0. Two bugs found and fixed while reproducing this, stated loudly before any headline number

**Bug A — BOOK's $ P&L math was NEVER actually wrong; the AU LABEL was.** Verified numerically:
`hist['BOOK']` (loaded from `FINAL_RANKING_20260730/all_sleeves_daily.json`) sums to Rs864,397.88 over
942 days; the raw `STACKED_BOOK_20260711/book_daily_pnl.csv` "total" column sums to Rs8,643,978.85 over
the identical 942 days — **exactly 10.0000x**. So the stored "BOOK" series really is the raw P&L
pre-divided by 10 ("Rs10L-equivalent," per `chart_data.json`'s own note). The portfolio build's scale
factor is `w × (TOTAL_CAPITAL/NATURAL_CAP) = w×10`. Applied to the ÷10 series: `w×10×(raw/10) = w×raw`
— i.e. the code's dollar contribution from BOOK **already equals** `w × raw_Rs1cr_pnl`, which is the
mathematically correct contribution for a sleeve whose true native/tested size is Rs1cr. **The CAGR/MaxDD
numbers already published for BOOK and for the 3 mandates in `PORTFOLIOS_RECOST.md` are NOT invalidated
by the unit bug** — the bug lives entirely in the descriptive AU-multiple used to describe capacity
headroom (mislabeled `w×10` "AU at Rs10L-native" should read `w×1` "AU at Rs1cr-native," exactly per
`CAPACITY_WRITEUP.md` §3). This is good news for the historical numbers and bad news for how the AU
figure was being used to argue "BOOK is over-capacity" — it never was.

**Bug B — found only by re-deriving this, NOT in the task brief: the fitted-search AND the naive-weight
gross-scaling step can BOTH push an individual sleeve's weight past its own stated per-mandate cap.**
`scan_weights`'s `gross` multiplier and the noise-refinement loop's `gross_r` multiplier are applied
*after* a per-sleeve clip, so a sleeve sitting at its cap can be pushed back over it. Confirmed on-disk:
the already-published `PORTFOLIOS_RECOST.md` HIGH_CAGR FORWARD weights show **BOOK "AU"=11.23x, i.e.
w=1.123 (112.3%) — over its own stated 50% cap**; BALANCED's NAIVE weights show **CALENDAR "AU"=5.25x,
i.e. w=0.525 (52.5%) — over its own stated 35% cap** (0.35 capped × the 1.5 gross-multiplier ceiling =
0.525, exact match). Fixed here by re-clipping to the per-sleeve cap after every gross-rescale step, in
both the fitted search and the naive path. **This is a real methodological defect in
`build_portfolios.py`'s inherited machinery, independent of the task's two named corrections — flagging
for Quant Head Arjun Rao to patch upstream** (`THREE_PORTFOLIOS_20260731/build_portfolios.py` lines
~340-350 and ~368-378, and its copy in `PORTFOLIOS_RECOST_20260803/recost_and_rebuild.py`).

**SWEEP's forward edge — a genuine discrepancy between the task's instructed number and my own
already-published number, flagged rather than silently resolved either way.** Verified directly against
`SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv` (4,378 trades):
- OLD-STT avg net edge: **10.941 pts/trade** (t=7.36) — matches CAPACITY_WRITEUP exactly.
- FORWARD, flat-spot-24000 method (Tara Singh / CAPACITY_WRITEUP, applies TODAY's spot uniformly to
  every trade back to 2015): **3.741 pts/trade** (t=2.52) — the task's instructed basis.
- FORWARD, real-per-trade-contemporaneous-spot method (already used in `PORTFOLIOS_RECOST.md`'s own
  `recost_and_rebuild.py`, same convention used for every other sleeve's recost that session — b1b,
  LD_SELL, CALENDAR all used exact/contemporaneous values, not today's): **6.512 pts/trade**.
The gap exists because SWEEP's 11.3-year trade history has a mean entry spot of 14,759 — only 61% of
today's ~24,000 — so a flat-today's-spot assumption materially overstates the STT bite on the ~87% of
trades that occurred before 2024. **I am using 3.741 for the headline re-fit below per the explicit
task instruction**, and reporting the 6.512-basis result alongside throughout as a cross-check — the
qualitative conclusions (BALANCED still wins, honest max CAGR ballpark) are not sensitive to which one
is used; a couple of points of LOW_RISK/HIGH_CAGR CAGR are. **This should get a Quant Head ruling on
which convention is house-standard before either number is quoted as final.**

## 1. BOOK's weight in TRUE native multiples — what changes

| Mandate | BOOK weight (%) | Mislabeled AU (old, ÷Rs10L) | **True AU (÷Rs1cr)** | Asking for MORE than before? |
|---|---|---|---|---|
| LOW_RISK | 25.0% | 2.50x | **0.250x** | Cap unchanged; naive economics alone (no cap) would want **37.3%** (0.373x) — yes, more |
| HIGH_CAGR | 50.0% (at cap) | 5.00x | **0.500x** | **Yes** — fitted search pins BOOK at its cap both before and after; once the cap is loosened (capacity confirmed non-binding), it runs to **100% (1.000x, fully native-sized)** and is still pressing against that ceiling |
| BALANCED | 22.7% | 2.27x | **0.227x** | No — BALANCED's own Calmar-optimum sits at 22.7% regardless of cap, below even the original 35% ceiling; not cap-constrained either way |

**Every mandate that touches its BOOK cap is now asking for the same or more BOOK, never less.** The
old "7.9x over-capacity" framing is fully retired — at true native units BOOK never exceeds 1.0x (its
own tested size) in any mandate, even in the uncapped exploration.

## 2. SWEEP's forward edge — headline table uses 3.741 pts/trade (task's instructed basis)

## 3. THE RE-FIT: three variants, both corrections in, cap-bug fixed

**(A) Same CAP_TABLE as before (0.50/0.35/0.25 ceilings on BOOK unchanged) — isolates the SWEEP-edge
correction and the cap-bug fix, nothing else:**

| Mandate | CAGR% | MaxDD% | Calmar | Sharpe | Weights (chosen) |
|---|---|---|---|---|---|
| LOW_RISK | 6.89 | -7.87 | 0.875 | 1.00 | SWEEP 25/CAL 20/OV 8/LD 10/BOOK 25 (NAIVE, unchanged) |
| HIGH_CAGR | 12.86 | -13.98 | 0.92 | 1.03 | SWEEP 50/CAL 50/OV 0.3/LD 35/BOOK **50** (FITTED, all at cap except OVERSHOOT) |
| BALANCED | 5.14 | -3.66 | **1.405** | 1.38 | SWEEP 1.9/CAL 35/OV 15/LD 20/BOOK **22.7** (FITTED — flips from NAIVE, see §5) |

**(B) Caps on SWEEP and BOOK loosened 2x (0.50→1.0 for BOOK, 0.25/0.50/0.35→0.50/1.0/0.70) — the
"capacity confirmed non-issue, size on economics alone" scenario. CALENDAR/OVERSHOOT/LD_SELL caps left
UNTOUCHED (their caps are crash-risk/thin-sample driven, unrelated to capacity, per the task's explicit
carry-forward instruction):**

| Mandate | CAGR% | MaxDD% | Calmar | Sharpe | Weights (chosen) |
|---|---|---|---|---|---|
| LOW_RISK | 8.62 | -8.91 | 0.967 | 1.12 | SWEEP 24.7/CAL 20/OV 8/LD 10/BOOK **37.3** (NAIVE) |
| HIGH_CAGR | **19.49** | **-24.77** | 0.787 | 1.07 | SWEEP **73.2**/CAL 16.7/OV 8/LD 35/BOOK **100** (FITTED — BOOK at its new ceiling, still pressing) |
| BALANCED | 5.14 | -3.66 | 1.405 | 1.38 | unchanged — its optimum never touches the cap |

**(C) Cross-check on the 6.512-pt SWEEP basis (real-per-trade-spot), same two cap regimes** — HIGH_CAGR:
13.51%/-13.70%/Calmar 0.986 (original caps) or 20.36%/-24.92%/Calmar 0.817 (loosened); LOW_RISK/BALANCED
move by ≤1pp in the same direction. Confirms the qualitative story is not sensitive to the SWEEP-basis
choice; the ~1-7pp CAGR gap between (A)/(B) columns above and the 3.741-vs-6.512 cross-check is the
known, flagged discrepancy from §0, not a new issue.

## 4. THE HONEST MAXIMUM CAGR

**Replaces HIGH_CAGR's original 30.44% (uncorrected) and the STT-only-recost's 16.50% (correct on cost,
but computed under a cap-bug that let BOOK silently run to 112% of book and CALENDAR to 52.5% elsewhere
— i.e. that 16.50% was never actually achieved inside its own stated caps either).**

- **If the firm keeps today's CAP_TABLE unchanged (no capacity-based re-authorization): 12.86% CAGR,
  -13.98% MaxDD, Calmar 0.92** — a genuinely conservative, cap-respecting number, using the task's
  instructed SWEEP basis.
- **If SWEEP/BOOK caps are loosened on the capacity desk's own evidence (719x ADV headroom for SWEEP,
  BOOK confirmed under- not over-deployed): 19.49% CAGR, -24.77% MaxDD, Calmar 0.787** — this is the
  honest maximum on economics alone. MaxDD sits right at HIGH_CAGR's own 25% risk-budget ceiling — the
  binding constraint is the mandate's own drawdown tolerance, not liquidity, not BOOK's native size, and
  not SWEEP's capacity. Getting more CAGR from here would need a bigger MDD budget, not more capital
  headroom (there is no more capital-headroom constraint left to relax).
- Note the trade **is not free**: Calmar is slightly worse in the loosened scenario (0.787 vs 0.92) —
  more CAGR bought with proportionally more drawdown, a real CIO-level choice, not a pure improvement.

## 5. Does BALANCED still win ordinally? YES — and by a similar or wider margin

| Mandate | Calmar (both corrections in, original caps) | Sharpe |
|---|---|---|
| LOW_RISK | 0.875 | 1.00 |
| HIGH_CAGR | 0.92 (orig caps) / 0.787 (loosened) | 1.03 / 1.07 |
| **BALANCED** | **1.405** | **1.38** |

BALANCED beats both alternatives on Calmar and Sharpe under every cap regime tested — same ordinal
verdict as the STT-only recost (1.034 vs 0.685/0.671), now on a cleaner base.

**One flagged change: BALANCED flips from NAIVE to FITTED once the cap-bug is fixed.** The
previously-published NAIVE result benefited from CALENDAR silently running to 52.5% (over its own 35%
cap); once properly capped, NAIVE's Calmar drops enough that the FITTED alternative clears the required
+10%-OOS-improvement bar. **This FITTED choice is well-supported, not a red flag**: its OOS/IS ratio is
0.875 (BALANCED-fitted retains 87.5% of in-sample Calmar out-of-sample), actually BETTER than what NAIVE
would have scored (0.604) in this same corrected setup — the opposite of the usual "naive is more robust"
pattern, worth Sameer Bhat's independent sign-off given it reverses a standing preference. HIGH_CAGR's
FITTED choice is the more fragile one: OOS/IS = 0.571 vs 0.829 for NAIVE at HIGH_CAGR — FITTED is chosen
there purely because it clears the CAGR objective by >10%, not because it's more stable; flagging this
explicitly per the firm's "report the OOS/IS ratio for anything fitted" rule.

## 6. CPPI verdict, re-checked after the BOOK unit fix — CHANGES for HIGH_CAGR specifically

| Mandate | Static Calmar | CPPI Calmar | Verdict |
|---|---|---|---|
| LOW_RISK | 0.875 | 0.793 | HURTS (consistent with the STT-only finding: 0.685→0.661 hurts) |
| **HIGH_CAGR (original caps)** | 0.92 | **1.365** | **HELPS — reverses the STT-only-recost verdict (0.671→0.633 hurt)** |
| HIGH_CAGR (loosened caps) | 0.787 | 0.77 | ~neutral / mild hurt |
| BALANCED | 1.405 | 1.405 | no-op (drawdown never reaches the 6% CPPI trigger under the corrected, properly-capped weights) |

**The CPPI reversal on HIGH_CAGR is real and traces directly to the cap-bug fix, not to the BOOK-unit
relabeling by itself.** The previously-published FORWARD HIGH_CAGR portfolio (BOOK silently at 112% of
book) had a materially different drawdown profile than the properly-capped 50%-BOOK portfolio computed
here — properly capped, the CPPI floor genuinely helps again (Calmar 0.92→1.365, MaxDD -13.98%→-8.83%
for -0.8pp of CAGR), much like the ORIGINAL pre-STT-recost finding (1.232→1.699 helps). Once the caps
are loosened to the capacity-justified level (BOOK back up near 100%, higher drawdown), CPPI's benefit
fades to roughly neutral. **Net: CPPI is worth re-arming for HIGH_CAGR IF the firm keeps today's caps;
it stops being clearly worth it if the caps are loosened to the "honest maximum" scenario.** BALANCED
and LOW_RISK verdicts are unchanged in direction from the STT-only recost.

## 7. Carried forward unchanged (per instruction, re-confirmed, not re-litigated)
S1_GAPFADE stays EXCLUDED. OVERSHOOT stays hard-capped (no crash data, 2021-06 onward only) — its cap
was NOT one of the two loosened above. CALENDAR/LD_SELL caps unchanged on thin-crash-sampling grounds (4
and 7 COVID observation days across 178/286 lifetime cycles) — also not touched by the loosening, which
was scoped deliberately to SWEEP/BOOK only (the two sleeves the capacity desk actually measured).
Naive/equal-risk preferred over fitted except where fitted clearly and robustly beats naive OOS — this
rule is exactly what flipped BALANCED to FITTED once its NAIVE comparator was properly capped (§5), and
exactly what keeps LOW_RISK NAIVE (fitted never clears the bar there).

## Files
`refit.py` (full pipeline, 4 variants) · `refit_results.json` (all numbers) · `au_labels.csv`
(BOOK true-AU by mandate/variant) · `run_log2.txt` (execution trace, both cap-bug fixes applied).
