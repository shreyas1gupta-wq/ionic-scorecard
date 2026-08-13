# PURE-OPTIONS BOOK — beats BALANCED in-sample, but must run ALONGSIDE it, not instead
**2026-08-03 · DESK-100 · structuring memo, Aakash Jain**
*Written to disk by the coordinator: the subagent Write tool blocks filenames matching
findings/report/summary/analysis, so the agent returned its memo inline. Content is the agent's,
transcribed verbatim in substance. Working files in this folder: `build_pure_options_book.py`,
`run_log.txt`, `checkpoints/*.csv`, `PROGRESS.md`.*

## Why this construction was attempted
Budget 2026 raised futures STT 0.02% → 0.05% of sale value (effective 1-Apr-2026) while options STT
went 0.10% → 0.15% of **premium**. Re-costed at sleeve level, SWEEP lost **43.6%** of its net and BOOK
**34.3%**, while OVERSHOOT lost 6.5%, CALENDAR 0.9% and LD_SELL 0.2%. Every existing firm portfolio
mixes futures sleeves with options sleeves, so every one now carries a leg that was taxed twice as
hard. A pure-options book had never been built here.

## 1. Sleeve inventory, post-STT [DATA, natural 1x = Rs10L, forward-costed]

| Sleeve | Structure | Margin as % of its natural unit | CAGR / MaxDD / Calmar / Sharpe | STT hit | Crash data |
|---|---|---|---|---|---|
| **S1-F** (CERTIFIED, FROZEN D-030) | 0DTE ATM short straddle, 30% stop/leg, flat 15:25 | **81%** | 9.47% / −4.66% / 2.031 / 3.26 (2022-25, 208d) | +9.71 → +9.655 pt/day | **NONE real** — the spec's −16% MaxDD is a model backcast at corr 0.64, not measured |
| LD_SELL | Biweekly 0.10Δ naked strangle, 2× credit stop | 9.5% | 1.44 / −5.93 / 0.244 / 2.18 (2011-26, 286 cycles) | +0.25% of net | COVID −Rs43,196 over 4 cycles, **robustly negative** |
| CALENDAR | 1×1 ATM/ATM monthly, 3-day-early exit | 9.4% | 0.65 / −1.66 / 0.392 / 2.82 (2011-26, 178 cycles) | +0.94% | COVID −Rs4,144 / 2 cycles, **thin, unstable sign** |
| ROLLED_RATIO_CAL | Same family, rolled near leg | ~CALENDAR | 1.69 / **−12.41** / 0.136 / 2.44 (160 cycles) | +0.30% | thin — **TESTED AND EXCLUDED** |
| OVERSHOOT | 0-1DTE spike-sell, delta-hedged | 16.2% | 0.51 / −1.82 / 0.283 / 0.68 (2021-26, 913d) | +6.5% | **NONE, ever** — hard-capped |
| Long-put tail overlay | not adopted | — | — | — | no config is net-hedge-positive in cash (60/60 cells) |

### The SPAN-reality catch that would have produced an impossible backtest
**S1-F's bare margin already consumes ~81% of its own Rs10L natural allocation** (spec:
`lots = floor(0.75 × equity / margin)`), while LD_SELL, CALENDAR and OVERSHOOT sit at 9–16%. So S1-F
is **not capital-light and cannot share a leverage dial with the other three.** A first-pass
construction that did share the dial implied **Rs1.46 crore of S1-F margin alone inside a Rs1 crore
book** — physically impossible, and it would have backtested beautifully.
Fixed with a **two-tier build**: S1-F fixed at 30% of book capital at native sizing with no extra
leverage; LD_SELL (20%) / CALENDAR (35%) / OVERSHOOT (15%) form a genuinely gross-scalable "light pool"
whose bare margin sits idle most days. This was caught by structuring judgment, not by any statistical
test.

## 2. Shared variance factor: **CONFIRMED YES** — and monthly correlation hides it
- **Monthly** sleeve-sleeve correlation (2022-25 common window): every pair |r| < 0.21. *Looks*
  diversified.
- **Quarterly correlation is materially higher:** S1_F–ROLLED_RATIO_CAL **0.497**, LD_SELL–CALENDAR
  **0.447**, ROLLED_RATIO_CAL–LD_SELL 0.300, ROLLED_RATIO_CAL–OVERSHOOT 0.281. **Monthly noise masks a
  slower-moving common factor.**
- Portfolio-vs-sleeve correlation at chosen weights (the Principal's preferred lens): LD_SELL 0.82/0.82
  (mo/qtr), CALENDAR 0.64/0.76, S1_F 0.28/0.54, OVERSHOOT 0.09/0.10. **Book variance is dominated by
  LD_SELL + CALENDAR**, both short gamma/vega on the same index.
- Structural, not merely data-mined: all four are short NIFTY gamma/vega.
- **`RISK_LIMITS.md` already pre-empts exactly this** — "Correlated-sleeve rule: S-01..S-04 share ONE
  combined VaR budget" and "vol-spike correlation: all four short-vol sleeves at worst month
  simultaneously." This build's evidence **supports keeping that rule, not relaxing it.** Pairwise
  monthly correlations understate true crash co-movement.

## 3. The book at compliant sizing
**ROLLED_RATIO_CAL tested and excluded** — not for correlation (0.12–0.31 sits inside the Principal's
acceptable 0.2–0.4 band) but because its own crash-era tail (standalone MaxDD −12.41% against
CALENDAR's −1.66%) cuts the light pool's maximum compliant gross from ~19.75× to ~6.75× for a much
thinner Sharpe gain.

**Recommended operating point** — conservative, roughly half the backtest-legal ceiling: S1-F fixed at
30%, light pool gross 5.0×. On the common window where all four sleeves are actually live
(2022-01-04 → 2025-12-30, the same convention BALANCED uses):

| | CAGR | MaxDD | Calmar | Sharpe | month-win | capital deployed |
|---|---|---|---|---|---|---|
| **pure-options book** | **9.30%** | **−3.42%** | **2.719** | **1.80** | 75% | 380% |

Over the full 2011-2026 union history (zero-filled pre-inception — the honest MaxDD read): CAGR 2.99%,
MaxDD −5.53%, Calmar 0.541. Much lower because S1-F and OVERSHOOT correctly contribute nothing for the
years before they existed.

## 4. Whole-book tail, three lenses

| lens | basis | loss as % of book capital |
|---|---|---|
| **A** — RISK_LIMITS "worst month, all sleeves simultaneously" | real, empirical | **−8.76%** |
| **B** — real COVID Feb–Apr 2020 | only 2 of 4 sleeves measured; **unmeasured is not safe** | −5.05% (understates) |
| **C** — pessimistic bound on the measured worst moves, naked legs only, ATM | forward-looking | 1d **−4.39%** · 5d **−6.43%** · 20d **−12.50%** |

Cross-check: at the light pool's full backtest-legal ceiling (gross 19.75×), Lens C's 20-day bound rises
to **~22.9%** of capital — independently converging with the historical MaxDD/COVID scan's own ~25%
ceiling. **Max survivable size:** the recommended operating point already banks a **2× margin of safety**
on the worst measured move (12.5% against the 25% ceiling). Pushing toward gross ≈19.75–20× is the
structural maximum where both lenses agree, but that scale is **capacity-unverified** (no capacity check
has been run on CALENDAR / OVERSHOOT / LD_SELL at 4–20× tested size) and **crash-blind for two of four
sleeves.** Not a size to run on backtest legality alone.

## 5. Honest comparison against BALANCED — and the verdict
BALANCED post-refit: CAGR 5.14%, MaxDD −3.66%, Calmar 1.405, Sharpe 1.38.

Over the fair common window the pure-options book **beats it on every metric** — CAGR 9.30% vs 5.14%,
MaxDD −3.42% vs −3.66%, Calmar **2.719 vs 1.405**, Sharpe **1.80 vs 1.38**. It also beats the firm's
honest ceiling across all mandates (19.49% CAGR at Calmar 0.787) on risk-adjusted terms.

**But that window contains no genuine vol-spike crash** — 2022 was a grind, not a gap. Both numbers are
"no-crash-observed" results.

### The crash-hedge trade-off, stated explicitly
BALANCED still carries **SWEEP, the only sleeve in the firm's entire corpus measured positive in all
four historical down-windows** — 2015-16 +Rs360k, 2018 +Rs76k, COVID +Rs321k, 2022 +Rs403k at natural
1× — even after losing 43.6% of its net to the STT hike. **None of the four pure-options sleeves has
this property:** LD_SELL is robustly negative in COVID, CALENDAR's crash sign is unstable, and S1-F and
OVERSHOOT have never seen a real crash at all.

**A short-premium book cannot be net long convexity without a long-premium leg elsewhere** — and
SELL_PLUS_TAIL already established that no put overlay is net-hedge-positive in cash (60/60 cells).

> **VERDICT: do not run pure-options as a replacement for the mixed book.** Run it as a parallel /
> satellite sleeve-group at the conservative operating point, while keeping SWEEP and BOOK's mixed
> exposure specifically for the crash-hedge property no options structure here has replicated.

## Four lines
1. S1-F, LD_SELL, CALENDAR and the tested-out ROLLED_RATIO_CAL are all short the same NIFTY variance
   factor — quarterly correlation shows it where monthly does not, and RISK_LIMITS already assumes it.
2. The book, built at compliant sizing with the SPAN-reality fix for S1-F, beats BALANCED's 1.405
   Calmar / 1.38 Sharpe bar in-sample at 2.719 / 1.80 — on a sample that has never seen a crash.
3. A repeat of the worst measured 20-day NIFTY move costs this book ~12.5% of capital at the
   recommended sizing and ~23% at the backtest-legal ceiling — survivable, not free, and unverified
   past 4–6× today's tested scale.
4. Run it alongside, not instead of, the mixed book: SWEEP is the firm's only demonstrated crash-payer
   and nothing in this options book replaces it.
